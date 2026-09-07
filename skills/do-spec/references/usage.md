# Internal runtime commands for the skill

The user copies the skill folder and invokes the skill. The agent executes the commands in this reference through its tools; these are not setup steps to hand back to the user. Keep SKILL.md, scripts/ and references/ together. No wheel installation or original checkout is needed. Resolve scripts/run.py relative to the loaded skill folder, never to the target project.

Prerequisites: uv and Git. The PEP 723 runner requests Python >=3.12 with no third-party Python dependencies; uv can provision Python. An existing Python 3.12+ can also run scripts/run.py directly. No global PATH changes are made.

```text
uv run <skill>/scripts/run.py setup
uv run <skill>/scripts/run.py demo --dir <new-demo-directory> --fail-at 5
uv run <skill>/scripts/run.py ui --project <demo-directory>/project.json --port 8080
```

`setup` is optional: `demo` and `init` prepare Dagu automatically if needed. Selection order: --dagu, DO_SPEC_DAGU, PATH, per-user cache. Windows/Linux x86-64 download exactly Dagu 2.11.2 from its official GitHub release with pinned archive SHA256 validation. Other platforms require an explicit executable. Wrong versions and download/hash errors stop safely. Missing Python/Dagu require network on first use; prepare them before offline use. Dagu binaries are downloaded separately, not distributed inside this skill. Cache: LOCALAPPDATA/do-spec/tools/2.11.2 on Windows; XDG_CACHE_HOME/do-spec/tools/2.11.2 on Linux; fallback ~/.cache. Linux execution remains unverified.

The agent starts `ui` in a persistent/background tool session and continues workflow execution in another tool call, keeping monitoring available after failure. Do not ask the user to launch a terminal. Monitoring address: **http://127.0.0.1:8080** (or the selected free port). demo/start/resume/status print the address and exact UI command arguments. An advertised URL alone does not prove server readiness: verify the owned process startup and HTTP response, then show the actual clickable URL to the user. First visit uses /setup for builtin account setup; preserve authentication. Each UI uses the matching project's Dagu home with ticket child workflows and logs. Do not reuse an unrelated service merely because the port responds.

```text
uv run <skill>/scripts/run.py init --repo <repo> --output <project.json>
uv run <skill>/scripts/run.py doctor --project <project.json>
uv run <skill>/scripts/run.py plan --project <project.json>
uv run <skill>/scripts/run.py start --plan <printed-plan-file>
uv run <skill>/scripts/run.py status --run <run-directory>
uv run <skill>/scripts/run.py logs --run <run-directory>
uv run <skill>/scripts/run.py resume --run <run-directory> --mode verify-only
uv run <skill>/scripts/run.py report --run <run-directory>
```

Default completion: queue open issues belonging to the spec, satisfy already closed dependencies, freshly read closed state after implementation. Open/invalid/failed lookup blocks successors. Do-spec never closes issues to manufacture success. verify-only rereads state without an agent; rerun-agent retries only the current open issue; finalize-only resumes reporting after recorded closure. Preserve the copied skill path and runtime version during an active plan: relocation/upgrades invalidate frozen plans, and do not migrate interrupted worktrees.

The demo uses ten local fake issues, fake agent processes and real Dagu/Git. --fail-at 5 leaves issue 5 open and blocks 6-10. To reproduce resume, change only the fake demo issues.json entry issues.5.state to closed, then resume --mode verify-only. The run directory is under <demo>/state/runs/.

Windows native execution is verified. Real corporate Cline and live gh/tea profiles remain blocked as unverified; copying this folder does not certify them. No upstream user-invoked skills are automatically chained. remote writes still require explicitly configured and approved integration; demo makes none.

When ui is launched on an explicit port, subsequent start/resume/status commands remember that project's selected port. This is still an advertised address, not a running-server health check.
