# Acceptance report — 2026-09-07

> Historical 0.1.0 report. The user's 2026-09-08 instruction changes the default: queue only open issues belonging to the spec, then verify closed state. Mandatory do-spec tests/checkpoint commits below apply only to explicit legacy `external-checkpoint`. See [revised contract](ISSUE-CLOSED.md), [new targeted tests](../evidence/issue-completion-tests.txt), and [combined regression output](../evidence/tests-issue-closed-windows.txt).

**PRD v1.1 MVP is NOT complete.** This is a working local vertical slice with tested safety boundaries and explicitly blocked live paths. No requirement is removed by being listed as incomplete.

## Executed verification

Windows 11 Enterprise 10.0.26100 x64, Python 3.12.14, Git 2.55.0.windows.5, real Dagu 2.11.2.

```powershell
$env:PYTHONPATH='src'
$env:DO_SPEC_DAGU=(Resolve-Path '.tools/dagu.exe').Path
<python-3.12> -m unittest discover -s tests -v
```

Latest full result: **21 tests, 153.536 seconds, OK, no skipped tests**. [Captured output](../evidence/tests-windows.txt). These are 21 test methods with additional subcases, not a claim that all 64 PRD requirements passed.

Other executed commands:

- `python -m unittest discover -s tests -p test_process.py -v`: 6 passed, 5.870s; includes Windows Job Object kill-on-close on supervisor death.
- `python -m unittest discover -s tests -p test_boundaries.py -v`: 6 passed, 18.609s; actual Git with direct phase tests (Dagu dispatch mocked for these boundary cases). [Output](../evidence/boundaries-windows.txt).
- `python -m unittest discover -s tests -p test_tracker.py -v`: 4 methods passed, 4.506s; both synthetic protocols tested separately, no vendor/server certification.
- `python -m pip wheel --no-deps --no-build-isolation --wheel-dir dist .`: real wheel build. [Build log](../evidence/wheel-build.txt).
- `.venv/Scripts/python.exe -m pip install --no-deps dist/do_spec-0.1.0-py3-none-any.whl`, then installed `do-spec --help`. [Install log](../evidence/wheel-install.txt).
- `quick_validate.py skills/do-spec`: `Skill is valid!` after installing PyYAML 6.0.3 into ignored developer-only directory. Initial validator attempt failed because PyYAML was absent; it was not reported as success.
- Native tea version/api/issues/logins help: closed stdin + captured output, hard timeout, exit 0. [API help](../evidence/tea-api-help.stdout.log). No real login/issue operation.
- Real Dagu `validate`/`start` are invoked by every integration demo. Generated YAML has explicit predecessor dependencies and retries 0 at every DAG level.
- Dagu server startup and browser `/setup` observed. `Get-NetTCPConnection` found only `127.0.0.1:18080` for the server. No Web log/render/resume success is claimed before authenticated access.

Earlier expected/fixed failures: missing planner implementation (red test), invalid top-level Dagu name, missing child PYTHONPATH, synthetic CLI CP949 output rejected as non-UTF8, Windows long-path tempfile cleanup. Latest green output supersedes those failures without concealing them.

## Demonstrated local outcome

`test_failure_five_preserved_and_verify_only_resume` uses a real temporary Git repository, ten local Markdown tickets, fresh fake subprocesses and real Dagu parent/child runs under a space/Korean path.

1. Baseline passes. T1–T4 each pass external verification and receive one checkpoint.
2. T5 fake exits 0 but external verification exits 1. Product exit is 11; run FAILED. T6–T10 remain PENDING.
3. Invocation journal contains only 1–5 with separate session identifiers. There are no T6–T10 result sentinels. T5 uncommitted file remains. Source checkout HEAD/status are unchanged.
4. Human repair writes `ok` to T5 result. `verify-only` creates a new attempt, does not execute T1–T5 agents, and continues T6–T10 through real Dagu.
5. All ten become ACCEPTED. Journal contains exactly tickets 1–10 once. Git has exactly ten commits after baseline. Starting the same plan again is rejected.

The shell reproduction and installed-wheel commands are in [README](../README.md). Test double output is never described as an actual Cline/Codex smoke.

Installed-wheel reproduction also completed: `.venv/Scripts/do-spec.exe demo --dir .demo/release-fail5 --dagu .tools/dagu.exe --fail-at 5` reported product error 11; after the explicit T5 repair, `resume --mode verify-only` exited **0**. A separate assertion verified SUCCEEDED, agent starts exactly 1–10, ten commits after baseline, and two T5 attempts. See [summary](../evidence/demo-summary.json), [before state](../evidence/demo-before-resume.json), [before invocation journal](../evidence/demo-before-agent.jsonl), [after state](../evidence/demo-after-resume.json), [resume output](../evidence/resume-cli.stdout.txt).

Final wheel SHA256: `d01b673e908ba2385782011589f4677afeab6ae7eeaf412252b569eb697f6f03`. Skill zip is separate and contains only the skill and its usage reference. The installed-wheel verification uses only local synthetic data.

## Milestones and concrete remaining work

| Milestone | Implemented here | Remaining / blocker |
|---|---|---|
| M0 | Actual Windows Dagu/schema/child execution; bounded tea/gh help; synthetic input/CLI tests | Native Linux host unavailable; actual user skills/helpers/golden artifacts absent; Cline absent; live tracker server profiles absent |
| M1 | Local plan, worktree, fake process, external checks, checkpoint, child phase logs; CLI AC-01 | Authenticated Web ticket/log inspection awaits local account setup; full AC-01 Web proof incomplete |
| M2 | Explicit resume modes/aliases, atomic state, project reservation/OS lock, phase guards, durable commit intent reconciliation | Full UI Stop/Retry/pause/restart end-to-end matrix not run; general stale-child reconciliation is deliberately blocked; no automatic stale-owner takeover |
| M3 | Two concrete **synthetic** CLI adapter scaffolds; pagination, explicit contexts, bounded errors, comment reconciliation, close guard | Real gh/tea API argv/normalization and discovery/report runtime wiring remain to implement and certify. No actual server/auth/redirect/push mapping provided. Synthetic behavior is not completion of AC-03–06 |
| M4 | Cline version/help evidence collector; unknown runtime/launcher and live profile fail-closed behavior | Actual noninteractive Cline execution builder, approval/headless/fresh-session/rules discovery and optional reviewer still need supplied CLI and authorized smoke. Runtime ambiguity requested from user remains unresolved |
| M5 | Thin skill, wheel, skill zip, local CLI/docs, fixed safe run action DAGs | Full registered parameterized Web plan/start flows not implemented; authenticated UI demo and Linux acceptance missing; Cline skill discovery untested |

Additional missing requirements: configurable no-op evidence/manual acceptance mapping; baseline custom verification boundaries and nested groups; triage/closed/external-blocker receipts; native tracker relations and complete upstream mapping; remote drift detection; push/comment/close runtime and uncertain push reconciliation; known-secret streaming redaction beyond environment separation; full strict nested configuration schema; disk quotas/free-space and RSS/log-latency measurements; verified Windows npm `.cmd` launcher (safely blocked); actual detached Cline contract; complete Linux process-group death/restart validation; `logs --follow`; complete process identity adoption checks. These are implementation gaps or missing evidence, **not reclassified as P1**.

No business repository or real issue was modified. Only generated fixture repositories received commits. Product repository changes remain local; no push or PR was created.

## PRD T-01–T-64 traceability / OS-provider matrix

`V` = stated local boundary verified; `P` = partial/synthetic test, not full requirement; `U` = unverified/unimplemented; `—` = not directly exercised in that column. Linux columns mean native hosts; no WSL substitute. A local V does not certify a tracker end-to-end path.

| Test | Windows local/core | Windows gh | Windows tea | Linux gh | Linux tea | Evidence / gap |
|---|---|---|---|---|---|---|
| T-01 | V | U | U | U | U | Real Dagu fail5 |
| T-02 | P | U | U | U | U | Ten accepted after resume; clean all-success separate case pending |
| T-03 | V | — | — | U | U | Dependency order test |
| T-04 | V | — | — | U | U | Stable ready tie-break |
| T-05 | V | — | — | U | U | Cycle/missing/duplicate/empty |
| T-06 | V | P | P | U | U | Explicit section parser only |
| T-07 | — | P | P | U | U | Synthetic three pages |
| T-08 | — | P | P | U | U | Synthetic invalid middle page; real 403 pending |
| T-09 | — | U | U | U | U | Native relation negotiation absent |
| T-10 | — | U | U | U | U | Cross-source native conflicts absent |
| T-11 | U | U | U | U | U | Closed/external receipt planner absent |
| T-12 | V | U | U | U | U | Agent zero + verifier nonzero |
| T-13 | P | U | U | U | U | Exit-code gate implemented; dedicated fake failure mode pending |
| T-14 | P | — | — | U | U | Empty checks blocked; full schema-error suite pending |
| T-15 | V | — | — | U | U | Protected verifier / unexpected commit tests |
| T-16 | V | — | — | U | U | Fresh fake journal/context; real Cline pending |
| T-17 | P | — | — | U | U | No installed Cline; blocked |
| T-18 | P | — | — | U | U | Windows remaining-job detection; real detach smoke absent |
| T-19 | P | — | — | U | U | Concurrent binary streams; RSS target unmeasured |
| T-20 | V | — | — | U | U | Large Unicode stdin + Korean/space cwd |
| T-21 | V | P | P | U | U | Stdin shell characters preserved |
| T-22 | P | — | — | U | U | Batch launcher rejected, not supported |
| T-23 | V | — | — | U | U | Timeout descendants, no escaped sentinel |
| T-24 | U | — | — | U | U | Authenticated Dagu UI stop pending |
| T-25 | P | — | — | U | U | Supervisor death closes Windows job; full restart matrix pending |
| T-26 | P | — | — | U | U | OS cross-process lock; full simultaneous Dagu admission pending |
| T-27 | P | — | — | U | U | Direct phase duplicate and order guard; raw UI Retry pending |
| T-28 | P | — | — | U | U | Actual commit + simulated crash exception; exact intent reconcile |
| T-29 | — | P | P | U | U | Synthetic saved-comment/timeout/reconcile |
| T-30 | V | U | U | U | U | Real Dagu verify-only |
| T-31 | P | — | — | U | U | Local spec/config/runtime hash drift; remote drift absent |
| T-32 | — | U | U | U | U | Remote progress normalization absent |
| T-33 | P | — | — | U | U | No-op stopped; approval/evidence policy absent |
| T-34 | U | U | U | U | U | Full known-secret log redaction absent |
| T-35 | — | U | U | U | U | Real CLI redirect behavior unverified |
| T-36 | P | — | — | U | U | Traversal rejection; full junction suite absent |
| T-37 | P | — | — | U | U | One loopback listener observed |
| T-38 | P | — | — | U | U | Guards implemented, full missing-identity suite pending |
| T-39 | P | — | — | U | U | Byte limit gate implemented, overflow suite pending |
| T-40 | P | P | P | U | U | Local reporting only; real report/push absent |
| T-41 | P | — | — | U | U | Synthetic local shape, user variant absent |
| T-42 | — | P | P | U | U | No parent mutation implementation |
| T-43 | U | U | U | U | U | Unsupported group classification incomplete |
| T-44 | P | P | P | U | U | This matrix; no Linux host |
| T-45 | P | — | — | U | U | No Codex runtime dependency; Cline absent |
| T-46 | — | P | — | U | U | Synthetic selected adapter only |
| T-47 | — | — | P | U | U | Synthetic selected adapter only |
| T-48 | — | P | P | U | U | Key preserves provider/port/path |
| T-49 | — | — | P | U | U | Synthetic wrong login; actual login metadata pending |
| T-50 | — | — | P | U | U | Synthetic path has no network; real run absent |
| T-51 | — | — | P | U | U | Synthetic closed-stdin hang hard timeout |
| T-52 | P | P | P | U | U | Parent/context mismatch rejection |
| T-53 | — | U | U | U | U | Real customized golden inputs absent |
| T-54 | — | P | P | U | U | Synthetic invalid JSON middle page |
| T-55 | — | — | U | U | U | Real body normalization absent |
| T-56 | P | P | P | U | U | Live unsupported gate; no HTTP fallback |
| T-57 | — | P | P | U | U | Issue URL exact-context validation; full discovery absent |
| T-58 | P | P | P | U | U | Case-insensitive tracker env removal |
| T-59 | — | P | P | U | U | Both synthetic comment timeout paths independently tested |
| T-60 | — | U | U | U | U | Real push intentionally unavailable |
| T-61 | P | P | P | U | U | Synthetic Unicode/shell character stdin |
| T-62 | P | — | — | U | U | Other runtime blocked; reviewer not implemented |
| T-63 | — | U | U | U | U | Native capability/auth distinction incomplete |
| T-64 | P | U | U | U | U | Local mapping/config hash drift; real variant absent |
