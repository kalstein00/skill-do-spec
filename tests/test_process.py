import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from do_spec.process import run, clean_env
from do_spec.core import Fault, lock


class ProcessTests(unittest.TestCase):
    def test_unicode_large_input_and_two_streams(self):
        with tempfile.TemporaryDirectory(prefix="공백 path ") as tmp:
            payload = ('한글 & ; $() "\r\n' * 10000).encode()
            r = run([sys.executable, "-c", "import sys; b=sys.stdin.buffer.read(); sys.stdout.buffer.write(b); sys.stderr.buffer.write(b)"], tmp, Path(tmp)/"io", 10, payload=payload)
            self.assertEqual(r["exit_code"], 0)
            self.assertEqual((Path(tmp)/"io.stdout.log").read_bytes(), payload)
            self.assertEqual((Path(tmp)/"io.stderr.log").read_bytes(), payload)

    def test_timeout_kills_descendant(self):
        with tempfile.TemporaryDirectory() as tmp:
            sentinel = Path(tmp) / "escaped"
            child = "import time; from pathlib import Path; time.sleep(2); Path('escaped').touch()"
            code = f"import subprocess,sys,time; subprocess.Popen([sys.executable,'-c',{child!r}]); time.sleep(20)"
            r = run([sys.executable, "-c", code], tmp, Path(tmp)/"tree", .4)
            self.assertEqual(r["outcome"], "TIMEOUT")
            time.sleep(2)
            self.assertFalse(sentinel.exists())

    def test_unverified_shell_launcher_blocked(self):
        with self.assertRaises(Fault):
            run(["cline.cmd"], ".", "unused", 1)

    @unittest.skipUnless(os.name == "nt", "Windows kill-on-close test")
    def test_supervisor_crash_closes_job(self):
        with tempfile.TemporaryDirectory() as tmp:
            code = "from do_spec.process import run; import sys; run([sys.executable,'-c',\"import time; from pathlib import Path; time.sleep(3); Path('escaped').touch()\"],sys.argv[1],sys.argv[1]+'/child',20)"
            env = os.environ.copy()
            env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1]/"src")
            p = subprocess.Popen([sys.executable, "-c", code, tmp], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                deadline = time.monotonic()+5
                while not (Path(tmp)/"child.process.json").exists():
                    if time.monotonic() > deadline:
                        self.fail("supervisor did not start child")
                    time.sleep(.05)
                p.kill()
                p.wait(timeout=5)
                time.sleep(3)
                self.assertFalse((Path(tmp)/"escaped").exists())
            finally:
                if p.poll() is None:
                    p.kill()
                    p.wait()

    def test_tracker_environment_case_insensitive(self):
        from unittest.mock import patch
        with patch.dict(os.environ, {"gh_token": "do-not-leak", "TEA_TOKEN": "also-secret", "CLINE_CONFIG": "keep"}):
            e = clean_env()
            self.assertNotIn("gh_token", e)
            self.assertNotIn("TEA_TOKEN", e)
            self.assertEqual(e["CLINE_CONFIG"], "keep")

    def test_os_lock_excludes_second_process(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "lock"
            code = "from do_spec.core import lock; import sys\nwith lock(sys.argv[1]): pass"
            with lock(path):
                env = os.environ.copy()
                env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
                p = subprocess.run([sys.executable, "-c", code, str(path)], capture_output=True, env=env)
                self.assertNotEqual(p.returncode, 0)
                self.assertIn(b"LOCK_CONFLICT", p.stderr)
