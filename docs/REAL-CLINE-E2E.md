# Real Cline / bundled Dagu E2E — 2026-09-09

**Final result: PASSED within the local-tracker scope.** First run exited 11 at issue 5; issues 6–10 had zero attempts. Verify-only recovery exited 0 with SUCCEEDED. Ten unique real Cline session IDs and process IDs were recorded; the first five were unchanged after recovery. All ten output files contain `ok`, and all local issues are closed. Nine implementation sessions have observed `external verification: passed` tool output; the intentionally failed ticket 5 was repaired by the test operator before resume. See `evidence/real-cline-e2e-before.json`, `evidence/real-cline-e2e-after.json`, and `evidence/real-cline-ui.json`.

Scope: Windows native, installed Cline 3.0.61 using the user's saved model configuration, actual Dagu 2.11.2 extracted with the copied skill, actual Git worktree, and ten disposable local JSON issues. The worker is the real Cline CLI, not fake_agent.py. No real issue service or work repository is modified. Upstream `implement` skill discovery/invocation and remote gh/tea are not certified by this fixture.

The user explicitly authorized automatic tool approval for these disposable E2E sessions only. The adapter otherwise defaults to false. Model/provider/key arguments are not overridden. Each ticket starts a new process without `--id`. `--data-dir` is deliberately absent: it isolates credentials/settings, not just conversation history. The initial isolated-data authentication failure is historical and does not mean the user's configured account is invalid.

Observed CLI boundary: a noninteractive write with `--auto-approve false` exited 0 with `finishReason: aborted` and created no file. The adapter records/validates the session envelope and treats aborted output as a stop. For the explicitly approved fixture it passes true per invocation. It records each Cline task ID and rejects a reused ID. Node, wrapper, certificate helper, package metadata and resolved CLI binary are hashed into the immutable plan. Unsupported CLI versions and non-Windows Cline profiles fail closed.

The negative fixture instructs ticket 5 to remain open without implementing anything. Tickets 1–4 implement and validate their own files and close only their own local issue. The runtime must exit 11 at ticket 5, with no sessions or attempts for 6–10. The recovery test simulates an operator completing ticket 5, then runs verify-only; it must preserve the first five session IDs/PIDs and launch only 6–10.

Reproduction in a developer checkout (requires an already configured Cline):

```powershell
python scripts/bundle_skill.py --with-dagu
$fixture = python scripts/prepare_cline_e2e.py --allow-local-tool-approval --node '<absolute-node.exe>' --cline-wrapper '<absolute-cline/bin/cline>' | ConvertFrom-Json
$plan = uv run $fixture.runner plan --project $fixture.project | ConvertFrom-Json
uv run $fixture.runner start --plan $plan.plan
```

Expected first exit: 11, ISSUE_STILL_OPEN. The preparation command creates a new temporary fixture; it does not call a model. Supply the approval flag only after authorization for this local test scope. Raw agent logs remain inside the disposable run, not in public evidence.

Start the monitor in a persistent execution session:

```powershell
uv run $fixture.runner ui --project $fixture.project --port 18083
```

To simulate completion of ticket 5 and resume the same run:

```powershell
$run = (Get-ChildItem (Join-Path $fixture.root 'fixture/state/runs') -Directory | Select-Object -First 1).FullName
$state = Get-Content (Join-Path $run 'run.json') -Raw | ConvertFrom-Json
[System.IO.File]::WriteAllText((Join-Path $state.worktree 'results/5.txt'), 'ok')
$dbPath = Join-Path $fixture.root 'fixture/issues.json'
$db = Get-Content $dbPath -Raw | ConvertFrom-Json
$db.issues.'5'.state = 'closed'
$db | ConvertTo-Json -Depth 10 | Set-Content -Encoding utf8 $dbPath
uv run $fixture.runner resume --run $run --mode verify-only
uv run $fixture.runner status --run $run
```

Sanitized first-stop evidence: `evidence/real-cline-e2e-before.json`. It records exactly five distinct real Cline sessions and pending issues 6–10. The authenticated UI's setup endpoint responded HTTP 200 on 127.0.0.1:18083; account setup was not bypassed.

Regression command: `python -m unittest discover -s tests -v` with PYTHONPATH=src and DO_SPEC_DAGU pointing at the skill's Windows binary: 44 passed in 291.576s. This suite mixes synthetic agent/tracker tests and adapter unit tests; the separate live run above is the real-model E2E. Subsequent changes fixed doctor to use the installed native Node wrapper instead of the npm PowerShell shim and explicitly blocked unverified ARM64 profiles. Doctor was checked against the installed CLI; four final adapter tests and eight portable tests cover these final changes. No second full-suite pass after those corrections is claimed. Skill validation also passed.

Earlier bundled-Dagu/fake-agent testing exposed Windows error 5 during an atomic metadata replacement. The failure and rejected verify-only recovery were preserved; rerun-agent admission skipped the already closed issue without starting another agent. Atomic replacement now retries only Windows sharing/access denials for a bounded 0.62 seconds, preserving the old file if denial persists. Both transient and persistent failure tests passed. This is not an automatic agent retry.
