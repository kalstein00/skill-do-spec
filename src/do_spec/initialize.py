from pathlib import Path
from .core import Fault, write
from . import git as g


def initialize(repo, output, dagu):
    repo, output = Path(repo).resolve(), Path(output).resolve()
    if output.exists():
        raise Fault("CONFIG_ALREADY_EXISTS", str(output), 2)
    g.common(repo)
    context = [p for p in ["AGENTS.md", "CLAUDE.md", "CONTEXT.md", "CONTEXT-MAP.md", "docs/agents/issue-tracker.md", "docs/agents/domain.md", "docs/agents/triage-labels.md"] if (repo/p).is_file()]
    write(output, {"schema_version": 1, "draft": True, "repo": str(repo), "state_dir": str(output.parent / "do-spec-state"),
                   "dagu": str(Path(dagu).resolve()), 'completion': 'issue-closed', "tracker": {"kind": "local", 'state_file': 'SET_LOCAL_ISSUE_STATE_PATH'}, "spec": "SET_SPEC_PATH", "parent": "SET_PARENT_ID", "tickets": [],
                   "agent": {"kind": "cline", "timeout": 3600, "argv": []}, "checks": [], "allowed_paths": [], "protected_paths": [],
                   "context": context, "reporting": "local-only", "max_prompt_bytes": 256000})
    return output
