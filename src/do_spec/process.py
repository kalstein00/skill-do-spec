"""Bounded streaming subprocesses. Windows suspended spawn + kill-on-close Job."""
import ctypes
import os
from pathlib import Path
import signal
import subprocess
import threading
import time
from .core import Fault, write

TRACKER_KEYS = {"GH_TOKEN", "GITHUB_TOKEN", "GH_ENTERPRISE_TOKEN", "GITHUB_ENTERPRISE_TOKEN", "GH_HOST", "GH_REPO", "TEA_TOKEN", "GITEA_TOKEN", "FORGEJO_TOKEN", "TEA_LOGIN"}


def clean_env():
    return {k: v for k, v in os.environ.items() if k.upper() not in TRACKER_KEYS}


class WinJob:
    def __init__(self):
        from ctypes import wintypes as w
        self.k = ctypes.WinDLL("kernel32", use_last_error=True)
        self.k.CreateJobObjectW.restype = w.HANDLE
        self.k.CreateJobObjectW.argtypes = [ctypes.c_void_p, w.LPCWSTR]
        self.k.SetInformationJobObject.argtypes = [w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD]
        self.k.AssignProcessToJobObject.argtypes = [w.HANDLE, w.HANDLE]
        self.k.TerminateJobObject.argtypes = [w.HANDLE, w.UINT]
        self.k.CloseHandle.argtypes = [w.HANDLE]
        self.k.QueryInformationJobObject.argtypes = [w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD, ctypes.c_void_p]
        class Basic(ctypes.Structure):
            _fields_ = [("process_time", ctypes.c_int64), ("job_time", ctypes.c_int64), ("flags", w.DWORD), ("min_ws", ctypes.c_size_t), ("max_ws", ctypes.c_size_t), ("active", w.DWORD), ("affinity", ctypes.c_size_t), ("priority", w.DWORD), ("scheduling", w.DWORD)]
        class IO(ctypes.Structure):
            _fields_ = [(n, ctypes.c_uint64) for n in ["r", "w", "o", "rb", "wb", "ob"]]
        class Extended(ctypes.Structure):
            _fields_ = [("basic", Basic), ("io", IO), ("process_mem", ctypes.c_size_t), ("job_mem", ctypes.c_size_t), ("peak_process", ctypes.c_size_t), ("peak_job", ctypes.c_size_t)]
        self.handle = self.k.CreateJobObjectW(None, None)
        info = Extended()
        info.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not self.handle or not self.k.SetInformationJobObject(self.handle, 9, ctypes.byref(info), ctypes.sizeof(info)):
            raise Fault("PROCESS_CONTAINMENT_FAILED", str(ctypes.get_last_error()))

    def assign_resume(self, process):
        if not self.k.AssignProcessToJobObject(self.handle, int(process._handle)):
            process.kill()
            process.wait()
            raise Fault("PROCESS_CONTAINMENT_FAILED", str(ctypes.get_last_error()))
        # Popen closes the initial thread handle; resume the suspended process only
        # after assigning it to the job. No child can escape during an assignment race.
        n = ctypes.WinDLL("ntdll")
        n.NtResumeProcess.argtypes = [ctypes.c_void_p]
        n.NtResumeProcess.restype = ctypes.c_long
        if n.NtResumeProcess(int(process._handle)) != 0:
            self.kill()
            raise Fault("PROCESS_RESUME_FAILED")

    def kill(self):
        if not self.k.TerminateJobObject(self.handle, 12):
            raise Fault("PROCESS_TERMINATION_UNCERTAIN", code=15)
        deadline = time.monotonic() + 5
        while self.active():
            if time.monotonic() > deadline:
                raise Fault("PROCESS_TERMINATION_UNCERTAIN", code=15)
            time.sleep(.02)

    def active(self):
        class Accounting(ctypes.Structure):
            _fields_ = [("times", ctypes.c_int64 * 4), ("faults", ctypes.c_uint32), ("total", ctypes.c_uint32), ("active", ctypes.c_uint32), ("terminated", ctypes.c_uint32)]
        data = Accounting()
        if not self.k.QueryInformationJobObject(self.handle, 1, ctypes.byref(data), ctypes.sizeof(data), None):
            raise Fault("PROCESS_QUERY_FAILED", code=15)
        return data.active

    def close(self):
        self.k.CloseHandle(self.handle)


def run(argv, cwd, log, timeout=30, payload=None, env=None, stop=None, limit=64 * 1024 * 1024, tee=False):
    if not argv or Path(argv[0]).suffix.lower() in {".cmd", ".bat", ".ps1"}:
        raise Fault("UNVERIFIED_LAUNCHER", "configure verified native executable/runtime entry")
    log = Path(log)
    log.parent.mkdir(parents=True, exist_ok=True)
    job = WinJob() if os.name == "nt" else None
    p = None
    started = time.time()
    overflow = threading.Event()
    cancelled = threading.Event()
    old_handlers = {}
    def handle_signal(*_):
        cancelled.set()
    if threading.current_thread() is threading.main_thread():
        for sig in (signal.SIGINT, signal.SIGTERM):
            old_handlers[sig] = signal.signal(sig, handle_signal)
    def terminate():
        if job:
            job.kill()
        else:
            try:
                os.killpg(p.pid, signal.SIGTERM)
                time.sleep(0.2)
                os.killpg(p.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
    try:
        p = subprocess.Popen(argv, cwd=cwd, stdin=subprocess.PIPE if payload is not None else subprocess.DEVNULL,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False,
                             env=env if env is not None else clean_env(), start_new_session=os.name != "nt",
                             creationflags=0x4 if job else 0)
        if job:
            job.assign_resume(p)
        identity = {"pid": p.pid, "started_at": started, "argv_executable": argv[0], "cwd": str(cwd)}
        write(str(log) + ".process.json", identity)
        def drain(stream, suffix):
            total = 0
            with open(str(log) + suffix, "wb") as target:
                while block := stream.read1(8192):
                    total += len(block)
                    if total > limit:
                        overflow.set()
                        break
                    target.write(block)
                    target.flush()
                    if tee:
                        import sys
                        output = sys.stderr if suffix == ".stderr.log" else sys.stdout
                        output.write(block.decode("utf-8", "replace"))
                        output.flush()
            stream.close()
        threads = [threading.Thread(target=drain, args=(p.stdout, ".stdout.log")), threading.Thread(target=drain, args=(p.stderr, ".stderr.log"))]
        for t in threads:
            t.start()
        def feed():
            try:
                p.stdin.write(payload)
                p.stdin.close()
            except (BrokenPipeError, OSError):
                pass
        if payload is not None:
            feeder = threading.Thread(target=feed)
            feeder.start()
        reason = "EXITED"
        while p.poll() is None:
            if cancelled.is_set() or (stop and Path(stop).exists()):
                reason = "CANCELLED"
            elif time.time() - started > timeout:
                reason = "TIMEOUT"
            elif overflow.is_set():
                reason = "LOG_LIMIT_EXCEEDED"
            if reason != "EXITED":
                terminate()
                break
            time.sleep(0.03)
        p.wait(timeout=5)
        if reason == "EXITED" and job and job.active():
            reason = "DETACHED_PROCESS"
        # Always reap descendants, including early-detaching helpers holding pipes.
        terminate()
        for t in threads:
            t.join(5)
        if any(t.is_alive() for t in threads):
            raise Fault("PROCESS_TERMINATION_UNCERTAIN", code=15)
        result = {**identity, "ended_at": time.time(), "exit_code": p.returncode, "outcome": reason, "tree_termination": "CONFIRMED_JOB_EMPTY" if job else "GROUP_SIGNALLED_UNVERIFIED"}
        write(str(log) + ".process.json", result)
        return result
    finally:
        if job:
            job.close()
        for sig, handler in old_handlers.items():
            signal.signal(sig, handler)
