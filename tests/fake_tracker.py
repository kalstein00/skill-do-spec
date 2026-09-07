"""Synthetic gh/tea operation protocol, not either vendor's flag schema."""
import argparse
import json
from pathlib import Path
import sys
import time
sys.stdout.reconfigure(encoding="utf-8")

p = argparse.ArgumentParser()
for name in ["db", "provider", "hostname", "instance", "repo", "account", "login", "operation", "number", "page"]:
    p.add_argument("--" + name)
a = p.parse_args()
db = Path(a.db)
data = json.loads(db.read_text(encoding="utf-8"))
with open(str(db) + ".journal", "a", encoding="utf-8") as f:
    f.write(json.dumps(vars(a)) + "\n")
if data.get("hang"):
    print('{"partial":', end="", flush=True)
    time.sleep(100)
context = {"kind": a.provider, "base_url": a.hostname or a.instance, "repository": a.repo, "account": a.account or a.login}
if data.get("wrong_login"):
    context["base_url"] = "https://wrong.example.invalid"
out = {"context": context}
number = int(a.number)
if a.operation == "read":
    out["issue"] = data["issues"][str(number)]
elif a.operation in {"list", "comments"}:
    items = list(data["issues"].values()) if a.operation == "list" else data.get("comments", {}).get(str(number), [])
    start = (int(a.page) - 1) * 2
    out.update(items=items[start:start+2], next_page=int(a.page)+1 if start+2 < len(items) else None)
    if data.get("invalid_page") == int(a.page):
        print("invalid")
        sys.exit(0)
elif a.operation == "comment":
    comments = data.setdefault("comments", {}).setdefault(str(number), [])
    comments.append({"id": len(comments)+1, "body": json.loads(sys.stdin.buffer.read())["body"]})
    db.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    if data.get("write_then_hang"):
        time.sleep(100)
elif a.operation == "close":
    data["issues"][str(number)]["state"] = "closed"
    db.write_text(json.dumps(data), encoding="utf-8")
print(json.dumps(out, ensure_ascii=False))
