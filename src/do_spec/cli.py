import argparse
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
from contextlib import redirect_stdout
from .core import Fault, read, write
from . import runtime


def progress(function, *args):
    with redirect_stdout(sys.stderr):
        return function(*args)


def monitoring(project, port=None):
    project = Path(project).resolve()
    if port is None and project.is_file():
        config = read(project)
        home = (project.parent / config["state_dir"]).resolve()
        if (home / "monitoring.json").is_file():
            port = read(home / "monitoring.json")["port"]
    port = 8080 if port is None else port
    if type(port) is not int or not 1 <= port <= 65535:
        raise Fault("INVALID_UI_PORT")
    runner = Path(__file__).resolve().parents[2] / "run.py"
    prefix = ["uv", "run", str(runner)] if runner.is_file() else [sys.executable, "-m", "do_spec"]
    result = {"monitoring_url": f"http://127.0.0.1:{port}",
              "monitoring_status": "start-ui-in-another-terminal",
              "ui_command_argv": [*prefix, "ui", "--project", str(Path(project).resolve()), "--port", str(port)]}
    # ASCII JSON preserves Unicode paths even through Windows legacy consoles.
    print(json.dumps(result), file=sys.stderr, flush=True)
    return result


def main(argv=None):
    p = argparse.ArgumentParser(prog="do-spec")
    subs = p.add_subparsers(dest="command", required=True)
    setup = subs.add_parser("setup")
    setup.add_argument("--dagu")
    init = subs.add_parser("init")
    for name in ["repo", "output", "dagu"]:
        init.add_argument("--" + name, required=name != "dagu")
    demo = subs.add_parser("demo")
    demo.add_argument("--dir", required=True)
    demo.add_argument("--dagu")
    demo.add_argument("--fail-at", type=int, choices=range(0, 11), default=0)
    plan = subs.add_parser("plan")
    plan.add_argument("--project", required=True)
    start = subs.add_parser("start")
    start.add_argument("--plan", required=True)
    for name in ["status", "report", "pause", "stop", "logs", "reconcile-checkpoint"]:
        sub = subs.add_parser(name)
        sub.add_argument("--run", required=True)
    resume = subs.add_parser("resume")
    resume.add_argument("--run", required=True)
    resume.add_argument("--mode", required=True, choices=["rerun-agent", "verify-only", "finalize-only", "repair", "report-only", "continue"])
    phase = subs.add_parser("_phase")
    for key in ["run", "ticket", "phase", "dispatch"]:
        phase.add_argument("--" + key, required=True)
    doctor = subs.add_parser("doctor")
    doctor.add_argument("--project")
    doctor.add_argument("--dagu")
    doctor.add_argument("--cline")
    ui = subs.add_parser("ui")
    ui.add_argument("--project", required=True)
    ui.add_argument("--port", type=int, default=8080)
    args = p.parse_args(argv)
    try:
        if args.command == "setup":
            from .bootstrap import resolve
            print(json.dumps({"dagu": resolve(args.dagu), "version": "2.11.2"}))
        elif args.command == "init":
            from .initialize import initialize
            from .bootstrap import resolve
            print(json.dumps({"draft": str(initialize(args.repo, args.output, resolve(args.dagu)))}))
        elif args.command == "demo":
            from .demo import create
            from .bootstrap import resolve
            project = create(args.dir, resolve(args.dagu), args.fail_at)
            monitoring(project)
            plan_path = runtime.make_plan(project)
            result = progress(runtime.start, plan_path)
            print(json.dumps({"project": str(project), "plan": str(plan_path), "run": str(result)}))
        elif args.command == "plan":
            print(json.dumps({"plan": str(runtime.make_plan(args.project))}))
        elif args.command == "start":
            monitoring(read(args.plan)["project"])
            print(json.dumps({"run": str(progress(runtime.start, args.plan))}))
        elif args.command == "_phase":
            runtime.phase(args.run, args.ticket, args.phase, args.dispatch)
        elif args.command == "resume":
            monitoring(read(Path(args.run) / "plan.json")["project"])
            mode = {"repair": "rerun-agent", "report-only": "finalize-only"}.get(args.mode, args.mode)
            print(json.dumps({"run": str(progress(runtime.resume, args.run, mode))}))
        elif args.command == "status":
            monitoring(read(Path(args.run) / "plan.json")["project"])
            print(json.dumps(read(Path(args.run) / "run.json"), ensure_ascii=False, indent=2))
        elif args.command == "reconcile-checkpoint":
            print(json.dumps({"commit": runtime.reconcile_checkpoint(args.run)}))
        elif args.command == "report":
            print(runtime.report(args.run))
        elif args.command in {"pause", "stop"}:
            root = Path(args.run).resolve()
            state = read(root / "run.json")
            if state["status"] != "RUNNING":
                raise Fault("RUN_NOT_RUNNING", code=2)
            (root / args.command).touch()
            print(json.dumps({"requested": args.command, "run": str(root), "status": "request-pending"}))
        elif args.command == "logs":
            for log in sorted(Path(args.run).rglob("*.log")):
                print(str(log))
        elif args.command == "doctor":
            result = {"os": platform.platform(), "python": sys.version, "executable": sys.executable, "tools": {}}
            names = ["git"]
            if args.project:
                c = read(args.project)
                try:
                    _, c = runtime.config(args.project)
                    result["configuration"] = "SUPPORTED_LOCAL_CONTRACT"
                except Fault as e:
                    result["configuration"] = {"status": "BLOCKED", "reason": e.reason}
                args.dagu = str((Path(args.project).resolve().parent / c["dagu"]).resolve())
                if c["agent"]["kind"] == "cline":
                    # Use the validated native launcher, not the npm .ps1 shim.
                    supported = result['configuration'] == 'SUPPORTED_LOCAL_CONTRACT'
                    result['tools']['cline'] = {'argv': c['agent'].get('argv', []),
                                                'version': '3.0.61' if supported else None,
                                                'status': 'SUPPORTED_LOCAL_CONTRACT' if supported else 'UNVERIFIED'}
                if c["tracker"]["kind"] != "local":
                    names.append({"github": "gh", "forgejo": "tea"}[c["tracker"]["kind"]])
            if args.cline:
                from .cline import inspect
                import tempfile
                directory = Path(tempfile.mkdtemp(prefix="do-spec-cline-doctor-"))
                result["cline"] = inspect(args.cline, directory)
            if args.dagu:
                from .engine import validate_binary
                validate_binary(args.dagu)
                result["dagu"] = {"path": args.dagu, "version": "2.11.2", "status": "SUPPORTED_VERSION"}
            for name in names:
                path = shutil.which(name)
                result["tools"][name] = {"path": path, "status": "UNVERIFIED" if path else "BLOCKED"}
                if path:
                    r = subprocess.run([path, "--version"], capture_output=True, timeout=10)
                    result["tools"][name]["version"] = r.stdout.decode("utf-8", "replace").strip()
            print(json.dumps(result, ensure_ascii=False, indent=2))
            if isinstance(result.get("configuration"), dict) or any(t["status"] == "BLOCKED" for t in result["tools"].values()):
                return 3
        elif args.command == "ui":
            info = monitoring(args.project, args.port)
            _, c = runtime.config(args.project)
            home = Path(c["state_dir"]) / "dagu"
            config_file = home / "config.yaml"
            home.mkdir(parents=True, exist_ok=True)
            if not config_file.exists():
                config_file.write_text('{"host":"127.0.0.1","auth":{"mode":"builtin"},"metrics":"private"}', encoding="utf-8")
            # This tool owns only JSON-compatible YAML; unknown existing config
            # needs manual validation rather than silently changing its security.
            settings = read(config_file)
            if settings.get("auth", {}).get("mode") not in {"builtin", "basic"} or settings.get("host", "127.0.0.1") != "127.0.0.1":
                raise Fault("DAGU_SECURITY_CONFIGURATION_INVALID")
            env = os.environ.copy()
            env["DAGU_HOME"] = str(home)
            write(Path(c["state_dir"]) / "monitoring.json", {"port": args.port})
            print(json.dumps({"monitoring_url": info["monitoring_url"], "monitoring_status": "starting", "first_visit": info["monitoring_url"] + "/setup"}), flush=True)
            return subprocess.call([c["dagu"], "server", "--host", "127.0.0.1", "--port", str(args.port), "--dags", str(home / "dags")], env=env)
        return 0
    except (Fault, OSError, ValueError, subprocess.SubprocessError) as e:
        code = e.code if isinstance(e, Fault) else 3
        print(json.dumps({"error": str(e), "exit_code": code}, ensure_ascii=False), file=sys.stderr)
        return code
