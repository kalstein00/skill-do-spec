import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
from .core import Fault

PIN = "2.11.2"
PHASES = ["prepare", "agent", "verify", "checkpoint", "report", "accept"]


def command(args):
    # Values here are generated IDs and locally trusted absolute executable paths,
    # never ticket text or web parameters. Reject shell expansions on Windows.
    if os.name == "nt":
        if any(any(c in a for c in '%!&|<>^`$\r\n') for a in args):
            raise Fault("UNSAFE_ENGINE_PATH", code=2)
        return subprocess.list2cmdline(args)
    return shlex.join(args)


def validate_binary(executable):
    p = subprocess.run([executable, "version"], capture_output=True, timeout=10)
    if p.returncode or p.stdout.decode().strip() != PIN:
        raise Fault("DAGU_VERSION_UNVERIFIED", f"requires {PIN}")


def generate(root, plan, state):
    root = Path(root).resolve()
    docs, steps = [], []
    phase_names = [p for p in PHASES if p != 'checkpoint'] if plan['config'].get('completion') == 'issue-closed' else PHASES
    prior = None
    for ticket in plan["tickets"]:
        tid = ticket["id"]
        child = "ticket-" + tid
        steps.append({"name": child, "action": "dag.run", "with": {"dag": child}, "depends": [prior] if prior else []})
        prior = child
        phases = []
        for i, phase in enumerate(phase_names):
            args = [sys.executable, str(Path(__file__).with_name("entry.py")), "_phase", "--run", str(root), "--ticket", tid, "--phase", phase, "--dispatch", state["dispatch"]]
            phases.append({"name": phase, "run": command(args), "depends": [phase_names[i-1]] if i else []})
        docs.append({"name": child, "description": f'{tid}: {ticket["title"]} | {plan["tracker"]["kind"]} | phase receipts in {root.name}',
                     "working_dir": state["worktree"], "retry_policy": {"limit": 0}, "steps": phases})
    parent = {"description": "Approved fixed sequential plan " + plan["hash"],
              "working_dir": state["worktree"], "retry_policy": {"limit": 0}, "steps": steps}
    path = root / ("do-spec-" + root.name + ".yaml")
    path.write_text("\n---\n".join(json.dumps(x, ensure_ascii=False, indent=2) for x in [parent, *docs]), encoding="utf-8")
    home = Path(plan["config"]["state_dir"]) / "dagu"
    dags = home / "dags"
    dags.mkdir(parents=True, exist_ok=True)
    (dags / path.name).write_bytes(path.read_bytes())
    # Fixed registered entries avoid interpolating arbitrary browser input into
    # shell commands. Every action still passes runtime ownership/phase guards.
    for action in ["pause", "stop", "verify-only", "rerun-agent", "finalize-only", "continue"]:
        args = [sys.executable, str(Path(__file__).with_name("entry.py"))]
        if action in {"pause", "stop"}:
            args += [action, "--run", str(root)]
        else:
            args += ["resume", "--run", str(root), "--mode", action]
        entry = {"description": f"Request {action} for do-spec run {root.name}; runtime guards apply. See actual execution DAG for outcome.",
                 "retry_policy": {"limit": 0}, "steps": [{"name": action, "run": command(args)}]}
        (dags / f"{action}-{root.name}.yaml").write_text(json.dumps(entry, indent=2), encoding="utf-8")
    return path
