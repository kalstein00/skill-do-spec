"""Model-free test double; no real tracker or agent settings are read."""
import argparse
import json
import os
from pathlib import Path
import sys
import uuid


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--journal", required=True)
    p.add_argument("--fail-at", type=int, default=0)
    p.add_argument('--tracker-state')
    args = p.parse_args()
    packet = json.loads(sys.stdin.buffer.read())
    tid = packet["ticket"]["id"]
    with open(args.journal, "a", encoding="utf-8") as f:
        f.write(json.dumps({"ticket": tid, "pid": os.getpid(), "session": uuid.uuid4().hex, "cwd": str(Path.cwd())}) + "\n")
    result = Path("results")
    result.mkdir(exist_ok=True)
    (result / f"{tid}.txt").write_text("broken" if int(tid) == args.fail_at else "ok", encoding="utf-8")
    if args.tracker_state and int(tid) != args.fail_at:
        path = Path(args.tracker_state)
        db = json.loads(path.read_text(encoding='utf-8'))
        db['issues'][tid]['state'] = 'closed'
        temporary = path.with_name(path.name + '.tmp')
        temporary.write_text(json.dumps(db), encoding='utf-8')
        os.replace(temporary, path)
    gate = 'tracker closed check' if args.tracker_state else 'external verification'
    print(f"fake agent ticket {tid}: process completed ({gate} still required)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
