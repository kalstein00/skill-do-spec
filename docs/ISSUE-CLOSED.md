# Completion contract revision — 2026-09-08

The user's direct request supersedes PRD v1.1's external-test/checkpoint completion rule: initially queue only open issues belonging to the spec, then treat the selected issue's closed state as completion. The default is now `completion: issue-closed` (also used when omitted in new configuration).

1. Read all candidates before filtering, identify spec membership only through the configured explicit Parent section (or local sidecar membership), and read current issue states. Closed spec members are recorded in `plan.excluded`; only open members enter the stable dependency order. Dependencies on excluded closed members are satisfied. Unknown/missing states or unresolved blockers fail closed.
2. Recheck before implementation. An issue closed while waiting is skipped without a fresh agent. An excluded dependency or completed predecessor that reopened blocks further work.
3. After normal worker termination, query the fixed tracker's exact issue. Closed is the success signal, independently of exit code, test output or existence of a commit. Open causes `ISSUE_STILL_OPEN` (exit 11). Lookup errors do not become success. Timeout/cancellation/unsafe Git branch changes remain operational stops.
4. The implementation workflow may make commits on the admitted integration branch. do-spec creates no checkpoint commit and runs no baseline/acceptance test command in this policy. The Dagu chain is prepare → agent → verify (tracker read) → report → accept. The observer never closes the issue itself. No new live mutation permission is inferred from ticket text.
5. `verify-only` rechecks tracker state with no agent. `rerun-agent` executes only the current still-open issue; if it closed after failure, it is skipped. `finalize-only` can reuse closure evidence for reporting, with a fresh closure check before acceptance. No-open plans succeed without agent/Dagu execution.

Local fixture states live in an explicit `tracker.state_file` JSON file outside the worktree: `{"issues":{"1":{"number":1,"state":"open"}}}`. This mutable status store is not a requirements snapshot. Local Markdown content and project config are still hashed. The bundled fake agent closes successful fixture issues and deliberately leaves `--fail-at` open. In real use, the user's implementation workflow is responsible for issue closure; the actual corporate implement skill and live CLI contract remain unverified.

GitHub/Forgejo discovery and completion reads are connected through their existing adapter interface and tested against each separate synthetic CLI. Real CLI/server profiles remain gated; this change does not pretend to complete live gh/tea support. No network or real issue writes are needed for regression tests.

`external-checkpoint` remains an explicit legacy policy so the old safety regression suite can run. New plans default to closure. Existing immutable plans are not migrated or reinterpreted; code/config changes still require replanning. If a run is already reserved, resume that run rather than stealing its lock or losing its worktree.

Version 0.1.0 reports remain historical evidence. Their assertions about mandatory runtime commits and tests describe the legacy policy, not this revised default.

## Executed validation

Windows native, Python 3.12.14, real Dagu 2.11.2; no live tracker/model calls.

- `PYTHONPATH=src DO_SPEC_DAGU=<dagu> python -m unittest discover -s tests -v`: **27 tests passed, 237.063s**. This includes the legacy regression suite and the initial six closure-policy tests. [Captured result](../evidence/tests-issue-closed-windows.txt).
- After adding four more edge cases, `python -m unittest discover -s tests -p test_issue_completion.py -v` with the same environment: **10 closure tests passed, 95.518s**. These overlap the six in the combined run; they are not 37 distinct tests. [Captured result](../evidence/issue-completion-tests.txt).
- Real Dagu: preclosed 1–2 excluded; agent starts only 3–5 before open T5 stops the run; externally closing T5 followed by verify-only completes 6–10 without repeating agent 5.
- Both synthetic gh/tea adapters select only open spec members; unrelated Parent is excluded, and closed blockers are satisfied. Invalid state, failed lookup, reopened blocker and closed-before-agent races are tested.
- Closed completion requires neither runtime test execution nor a new commit; normal worker exit 9 with confirmed closure also completes. Timeout/cancellation remain separate operational stops.
- 0.2.0 wheel built and installed; its 15 Python modules byte-match source. SHA256: `1c075a657c2987db688a6fc4ee6e08f37c4031c518ad9681154251d25ab8f739`. Skill validator passed; ZIP regenerated. Linux and live gh/tea/Cline remain unverified.
