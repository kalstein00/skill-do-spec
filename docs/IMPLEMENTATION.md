# Implementation contract

2026-09-08 amendment: direct user instructions supersede external-checkpoint completion. Default `issue-closed` queues only open spec members and observes closed state to complete. Implementation workflow owns tests/commits/close; do-spec retains scheduling, fresh processes, safe stop and read-only completion observation. See ISSUE-CLOSED.md. Original decisions below remain historical where they conflict.

Source: do-spec-PRD-v1.1.md (2026-09-07), read in full. Attached instructions are requirements data; the user's direct request controls scope. Runtime ambiguity (request: Codex/Cline; v1.1: Cline only) has been asked; shared fake path proceeds first.

Repository: independent skill-do-spec, initial main with README only, no applicable AGENTS.md found in repository or ancestor directories. No business checkout or live issues are test targets. No remote writes authorized.

Fixed decisions: deterministic immutable plan; stable topological ordering; explicit sequential Dagu child dependencies; fresh process per ticket; one accumulating integration worktree per spec; external verification then runtime-owned checkpoint; no automatic retries/fallback/reset; preserve failures; OS locks and reserved ownership across steps; resume never repeats accepted work; localhost existing authenticated Dagu UI; secrets excluded from children and artifacts.

Non-goals: own scheduler/dashboard/database, Docker/WSL requirement, direct model or tracker HTTP client, remote workers, automatic upstream skill chaining, upstream rewrites, automatic merge or tracker synchronization.

Required acceptance: AC-01 ten tickets, external failure at 5, zero agent starts 6–10; AC-02 repair then verify-only without repeated agents/commits; AC-03 uncertain reporting reconciles without duplicate comment; AC-04 equivalent gh/tea artifact semantics; AC-05 selected provider only; AC-06 host/push boundary. All 64 PRD tests require an honest OS/provider matrix. Actual corporate Cline/custom outputs and Linux execution cannot be inferred from Windows fake tests.

Small vertical sequence:
1. M0 pin real Dagu/schema; inspect actual CLI help; prove command/cwd/failure/process contracts.
2. M1 tests first for planner and local ten-ticket Dagu/worktree/verification/checkpoint.
3. M2 guarded explicit resume, locking, drift, cancellation and crash reconciliation tests.
4. M3 separate gh/tea subprocess adapters with synthetic contracts; block unverified live capabilities.
5. M4 verified Cline invocation profile only; no paid smoke without authorization.
6. M5 thin skill, package, Dagu UI entries, documentation and measured acceptance report.

Milestone implementation can proceed offline where missing live environments block certification; such milestones are not declared complete.
