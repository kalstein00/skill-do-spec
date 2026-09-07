from pathlib import Path
import sys
from .core import Fault, write
from . import git as g


def create(root, dagu, fail_at=0, completion='issue-closed'):
    root = Path(root).resolve()
    if root.exists() and any(root.iterdir()):
        raise Fault("DEMO_DIRECTORY_NOT_EMPTY", str(root), 2)
    repo = root / "source"
    repo.mkdir(parents=True)
    g.git(repo, "init", "-b", "main")
    g.git(repo, "config", "user.name", "do-spec fixture")
    g.git(repo, "config", "user.email", "fixture@example.invalid")
    (repo / "verify.py").write_text('from pathlib import Path\nimport sys\nbad = [str(p) for p in Path("results").glob("*.txt") if p.read_text() != "ok"]\nprint("external verification:", bad or "passed")\nsys.exit(bool(bad))\n', encoding="utf-8")
    (repo / "CONTEXT.md").write_text("Synthetic offline fixture. Each result must equal ok. No remote actions.\n", encoding="utf-8")
    g.git(repo, "add", "--", "verify.py", "CONTEXT.md")
    g.git(repo, "commit", "-m", "Green fixture baseline")
    inputs = root / "inputs"
    inputs.mkdir()
    (inputs / "spec.md").write_text("# Local demo\nProduce one independently verifiable result per ticket.\n", encoding="utf-8")
    tickets = []
    for i in range(1, 11):
        path = inputs / f"{i}.md"
        blocker = f"#{i-1}" if i > 1 else "None"
        path.write_text(f"# Result {i}\n\n## Parent\n#100\n\n## Blocked by\n{blocker}\n\n## Acceptance criteria\nresults/{i}.txt contains ok.\n", encoding="utf-8")
        tickets.append({"id": str(i), "path": str(path)})
    project = root / "project.json"
    tracker = {'kind': 'local', 'state_file': str(root / 'issues.json')}
    write(root / 'issues.json', {'issues': {str(i): {'number': i, 'state': 'open'} for i in range(1, 11)}})
    tracker_args = ['--tracker-state', str(root / 'issues.json')] if completion == 'issue-closed' else []
    write(project, {"schema_version": 1, "repo": str(repo), "state_dir": str(root / "state"), "dagu": str(Path(dagu).resolve()),
                    "spec": str(inputs / "spec.md"), "parent": "100", "tickets": tickets,
                    "tracker": tracker, "completion": completion, "reporting": "local-only", "context": ["CONTEXT.md"],
                    "agent": {"kind": "fake", "argv": [sys.executable, str(Path(__file__).with_name("fake_agent.py")), "--journal", str(root / "agent.jsonl"), "--fail-at", str(fail_at), *tracker_args], "timeout": 30},
                    "checks": [{"name": "fixture-acceptance", "argv": ["{python}", "verify.py"], "timeout": 30}],
                    "allowed_paths": ["results"], "protected_paths": ["verify.py", "CONTEXT.md"], "max_prompt_bytes": 256000})
    return project
