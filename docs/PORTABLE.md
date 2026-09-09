# Portable skill verification

Historical source-only distribution report below. The 2026-09-09 prepared ZIP also contains Windows/Linux Dagu binaries, their licenses and manifest; build with `scripts/bundle_skill.py --with-dagu`. The skill agent now owns the persistent UI tool session instead of asking the user to launch a terminal. Cline's version-scoped local adapter and its current E2E evidence supersede the earlier all-Cline-blocked statement; Linux and remote tracker integration remain unverified.

Commands executed on Windows with Python 3.12.14, uv 0.10.9, Git 2.55.0.windows.5 and actual Dagu 2.11.2:

```powershell
.venv/Scripts/python.exe scripts/bundle_skill.py
$env:PYTHONPATH='src'
$env:DO_SPEC_DAGU=(Resolve-Path .tools/dagu.exe).Path
.venv/Scripts/python.exe -m unittest discover -s tests -v
```

Portable tests cover exact bundled-source equality, isolated copied-path invocation (including Korean/space characters), hash mismatch before executable launch, explicit unsupported version without network fallback, and honest monitoring URL output. The skill-creator quick_validate.py check also passed.

For the additional real uv smoke run, only skills/do-spec was copied to a fresh directory under the Windows temporary directory; PYTHONPATH was removed. The uv executable was .tools/uv-runtime/bin/uv.exe and UV_PYTHON selected the existing bundled Python. No do-spec wheel was installed in uv's script environment.

```text
uv run --offline <copied-skill>/scripts/run.py --help
uv run --offline <copied-skill>/scripts/run.py setup
uv run --offline <copied-skill>/scripts/run.py demo --dir <new-demo> --fail-at 5
uv run --offline <copied-skill>/scripts/run.py ui --project <demo>/project.json --port 18081
uv run --offline <copied-skill>/scripts/run.py resume --run <printed-run> --mode verify-only
```

setup downloaded and checked pinned Windows Dagu into the user cache. Here --offline applies to uv; Dagu setup used network. Demo exited 11 (expected ISSUE_STILL_OPEN). Before resume, agent.jsonl contained exactly 1,2,3,4,5. Only the fake issue 5 state was edited to closed. verify-only exited 0, final state SUCCEEDED, and the journal contained exactly 1..10 once each. UI answered HTTP 200 at /setup and the listener was 127.0.0.1:18081. Builtin authentication stayed enabled; no account was created automatically.

Evidence: ../evidence/portable-demo.txt, portable-resume.txt, portable-resume-proof.txt, portable-ui.txt, and tests-portable-windows.txt. All tracker and agent operations in this smoke run were local fakes. Linux execution and live Cline/gh/tea remain unverified. A separate UI terminal is required; printing an address does not automatically launch the server.

Rebuild after editing src/do_spec with scripts/bundle_skill.py before copying the folder. Never update or relocate the skill during an active immutable plan. The ZIP allowlist includes only .py and .md files, excluding caches, downloaded binaries, auth, and run state.

Final results: full suite 36 tests passed in 253.473s. Afterwards, monitoring output was adjusted to remember the project's selected UI port and use ASCII-escaped JSON for Unicode paths on Windows consoles; the final portable suite passed 6 tests in 0.330s (5 repeated plus 1 new test). No additional full-suite run is claimed after that UI-only adjustment. Copied-folder fail-stop/resume and HTTP evidence above precede that final output adjustment; execution/planner code was unchanged.
