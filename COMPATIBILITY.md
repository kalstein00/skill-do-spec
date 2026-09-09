# Compatibility evidence — 2026-09-07

## 2026-09-09 installed Cline and bundled Dagu

**Current result:** actual Windows x64 Cline 3.0.61 + bundled Dagu 2.11.2 + local fake tracker E2E passed. Exactly five distinct Cline sessions ran before the deliberate open issue 5 stopped successors (exit 11). After test-operator completion of issue 5, verify-only resumed to SUCCEEDED (exit 0), with ten distinct sessions total and no rerun of the original five. Nine sessions emitted actual successful verification output; the intentionally failed fifth was repaired outside the agent as part of the recovery test. See [full scope and reproduction](docs/REAL-CLINE-E2E.md). This certifies neither remote tracker writes, upstream implement skill invocation, Linux nor other Cline versions/architectures.

Later correction after user model setup: omitting `--data-dir` successfully used the saved provider/model and returned exactly `DO_SPEC_SMOKE_OK` (exit 0). The earlier isolated-data authentication error below does not describe the configured CLI's current authentication. The adapter must preserve the normal data directory and create fresh conversations by omitting `--id` instead. An actual file-write smoke with auto-approval false returned exit 0 but `finishReason: aborted` and no file: Cline requires interactive approval in that mode. The user explicitly authorized automatic tool approval only for the disposable local E2E sessions. No saved security/model/auth settings were changed. A version-scoped local adapter now checks session IDs, aborted output, and pins launcher/binary hashes. E2E results are recorded separately from the historical failed smoke.

Cline is now installed: npm package `cline` 3.0.61. Actual Windows invocation used Node with the installed `cline/bin/cline` wrapper (retaining its certificate handling), closed stdin, and the existing process Job Object supervisor. `--version` and `--help` exited 0. Help reports automatic approval defaults to true; the smoke explicitly used `--auto-approve false`, isolated `--data-dir`, `--json`, and a 45-second CLI timeout under a 55-second supervisor limit. No authentication, provider, endpoint or security setting was changed.

An actual model-session smoke requesting only `DO_SPEC_SMOKE_OK` exited 1 with authentication-class `Unauthorized` and requested Cline account reauthentication. No model completion occurred. Therefore real Cline end-to-end execution is BLOCKED, not passed, and the live runtime adapter remains gated. `--retries 0` was rejected by this installed CLI (requires >=1); it must not be treated as a supported no-retry contract. Raw Cline logs stay in ignored `.tools`, with no credential/config export into fixtures or public evidence. See `evidence/cline-live-smoke.json` for a sanitized summary.

Prepared skill binaries: `tools/dagu/2.11.2/windows-amd64/dagu.exe` and `linux-amd64/dagu`, upstream LICENSE files, and a SHA256 manifest. Windows executable SHA256 is `866aa991f48772b8492aa3a8483bcdb74a6f58cf187acf40d114b78525141bd9`; Linux is `14f4402c23978efd3e2dee172dc0f2bb15fffcf0817596d63be4873b3551ecb1`. The archives match the previously recorded official release archive hashes. Linux is packaged/hash-checked only, not executed on this Windows host. Explicit Dagu paths override the bundled executable; otherwise it precedes PATH/cache. Corruption fails closed before launch.

## 2026-09-08 policy revision (0.2.0)

The user's subsequent request replaces the default completion rule with **open-only spec queue / closed-state completion**. See [current contract](docs/ISSUE-CLOSED.md) and [current test output](evidence/issue-completion-tests.txt). The records below describe 0.1.0 and its legacy external-checkpoint policy. New local fixtures include mutable issue-state JSON; both synthetic gh/tea adapters now connect to discovery and completion reads. Real CLI/server profiles and Linux native execution remain unverified and gated. Existing immutable plans are not migrated; a changed runtime requires replanning. No real tracker writes or model calls were made for this revision.

Statuses apply to the stated boundary, not the entire product. See [acceptance](docs/ACCEPTANCE.md).

## Environment and pinned dependencies

| Component | Observed version/path | Verified boundary |
|---|---|---|
| OS | Windows 11 Enterprise x64, 10.0.26100 | Native process execution; no WSL/Docker |
| Python | 3.12.14, bundled runtime and local `.venv` | CLI/tests/wheel build; system WindowsApps python was an alias |
| Git | 2.55.0.windows.5, `C:/Program Files/Git/cmd/git.exe` | Real fixture worktrees, checkpoint and crash intent reconciliation |
| Dagu | 2.11.2, repository `.tools/dagu.exe` | Actual `version`, `schema`, `validate`, `start`, child failures, cwd, per-phase logs, server startup |
| gh | 2.100.0, `C:/Program Files/GitHub CLI/gh.exe` | `--version`, `api --help` only; no real issue/network/auth smoke |
| tea | 0.15.1, repository `.tools/tea.exe` | Official binary SHA matches published checksum; closed-stdin captured version/api/issues/logins help each exit 0 <1s |
| Codex | 0.153.2, npm launcher discovered | `--version`, `exec --help` inspected at user request; never used as ticket runtime |
| Cline public/corporate | Not found on PATH | UNVERIFIED; no flags invented, no settings altered, no paid smoke |
| Linux native | No Linux host available | UNVERIFIED for all real binary/process/UI/gh/tea combinations |
| Build | setuptools 84.0.0 | Actual wheel build |
| Skill validator | PyYAML 6.0.3 in ignored `.tools/devdeps` | `quick_validate.py`: Skill is valid; not a Cline discovery smoke |

Development Python path: `C:/Users/hj0712.jo/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe`. Paths are machine observations, not portable defaults.

## Checksums and provenance

- Source PRD SHA256: `74cc8c79ee2f3fcff6ac718c4d235712e0a8dc3ce38960a2decf77d8df7ce45c`.
- Dagu Windows executable SHA256: `866aa991f48772b8492aa3a8483bcdb74a6f58cf187acf40d114b78525141bd9`.
- Dagu archive SHA256: `3e435358de147ee74ceb49d21220dc49f13325fb2e5ef2ffd130559737c61672`. Locally measured; the attempted release checksum filename returned 404, so no publisher checksum comparison is claimed.
- [Official Dagu release archive](https://github.com/dagucloud/dagu/releases/download/v2.11.2/dagu_2.11.2_windows_amd64.tar.gz).
- tea executable SHA256: `d59cda2463b9f0b1c29ff69834650ba8d8dfa327a79a38f2cfc6e28f61bcb166`, matches [publisher checksum](https://dl.gitea.com/tea/0.15.1/tea-0.15.1-windows-amd64.exe.sha256).
- [tea 0.15.1 official artifacts](https://dl.gitea.com/tea/0.15.1/) list Linux and Windows binaries. Listing is not Linux execution evidence.
- Runtime code, configuration, inputs and Dagu binary hashes are pinned in new plans. Changing them requires a new plan.

## Actual Dagu 2.11.2 contract differences

- `dagu schema dag` outputs the actual JSON schema. The raw GitHub schema path at this tag returned relative link text, not JSON; it was not used.
- `dagu schema config server` fails (`path server not found`) despite help examples. The full config schema was inspected instead.
- Entrypoint YAML **must not define `name`**. The file basename identifies the parent; subsequent inline child documents have names.
- Adopted syntax: `action: dag.run`, `with.dag`, explicit `depends`, child `working_dir`, ordinary `run`. No harness/cache/distributed worker/custom executor.
- Default DAG auto retry was observed as 3 in an exploratory failure. Generated parent, child and actions now use `retry_policy: {limit: 0}`.
- Child execution did not receive development `PYTHONPATH` as expected. Commands use an absolute package entry script; ticket text is stdin JSON, never shell interpolation.
- Server uses builtin auth and presents `/setup`. One Dagu listener was observed: `127.0.0.1:18080`. No worker/coordinator was started. Dagu intrinsically registers `/mcp` on that same authenticated HTTP server; do-spec neither connects to nor depends on it. No MCP listener/client was added separately. [Dagu route architecture](https://docs.dagu.sh/mcp/architecture).
- Web ticket/log rendering and UI actions remain UNVERIFIED pending the user's local admin setup. History files contain per-ticket/phase logs, including T5 verifier failure.
- History can exceed conventional Windows MAX_PATH. One otherwise successful E2E failed during tempfile cleanup; E2E now preserves artifacts. That run was recorded as failed.

## Tracker / customized artifact boundary

Repository/ancestor discovery found no AGENTS.md. The initial independent repository had only README. No customized `to-spec`, `to-tickets`, common tracker helper, or sanitized company golden outputs were present. Their real revisions/hashes and provider semantics remain UNVERIFIED.

Synthetic local Markdown uses explicit Parent/Blocked by/Acceptance criteria sections; aliases can be configured. This is a test contract, not a claim about user variants. Inputs are hashed and preserved. `tests/fake_tracker.py` uses a **synthetic operation protocol, not vendor gh/tea flags**. Both adapter classes exercise semantics against it; this does not complete M3. Live profiles fail with TRACKER_CLI_UNSUPPORTED/UNVERIFIED.

Actual tea help confirms `api --method`, `--data @-`, `--login`, `--repo`; response/redirect/login/server behavior was not tested. gh help is in `evidence/gh-api-help.txt`. No real remote writes, auth switching, company endpoint/token reads, or model calls occurred.

## Support matrix

| Combination | Fake semantics | Real tracker | Real Cline | Dagu E2E |
|---|---|---|---|---|
| Windows + local | Tested | N/A | UNVERIFIED | Tested |
| Windows + gh | Synthetic scaffold tested | Help only | UNVERIFIED | Remote AC-04 not run |
| Windows + tea | Synthetic scaffold tested | Version/help only | UNVERIFIED | Remote AC-04 not run |
| Linux + local/gh/tea | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED |

The request mentions Codex/Cline while v1.1 excludes Codex runtime. Clarification was requested; shared fake functionality proceeded without a Codex adapter. Neither live interpretation is silently certified.

## Portable skill distribution (2026-09-08)

The skill now contains scripts/run.py (PEP 723, Python >=3.12, dependencies=[]), a complete bundled do_spec package, and usage instructions. scripts/bundle_skill.py refreshes this package from src/do_spec and builds dist/do-spec-skill.zip with only Python/Markdown files. Runtime equality is regression-tested. Copying the folder needs no wheel installation. uv behavior follows https://docs.astral.sh/uv/guides/scripts/ . Developer verification uses uv 0.10.9 installed under ignored .tools, without global installation or PATH changes.

Bootstrap selects an explicit Dagu path, DO_SPEC_DAGU, PATH, or the user cache. Missing x86-64 Dagu is downloaded from the pinned official v2.11.2 release; wrong explicit versions never silently fall back. Archive SHA256 values were calculated from downloaded official release assets (not publisher-signed checksum verification):

- Windows amd64: 3e435358de147ee74ceb49d21220dc49f13325fb2e5ef2ffd130559737c61672
- Linux amd64: ccf33ff9d86e2463faeb7e7b30ebca82a96e8c76b6ea2e282adb506db69feb3d

Linux archive was downloaded and hashed only: Linux execution is still UNVERIFIED. Windows automatic download, extraction, version validation and copied-folder uv execution were exercised. Real Cline and live tracker profiles remain blocked. uv --offline controls uv's own downloads; pre-run setup or provide --dagu for fully offline execution.

Monitoring uses the existing authenticated Dagu server, started separately with ui. The CLI prints the URL even when a workflow fails. Server readiness is separate from the advertised URL. A copied-folder server answered HTTP 200 at http://127.0.0.1:18081/setup and listened only on 127.0.0.1. Account setup was not bypassed; authenticated browser navigation through ticket logs remains unverified in this run.

Full regression result: 36 tests passed in 253.473s (evidence/tests-portable-windows.txt). Final monitoring port/Unicode output adjustment: 6 portable tests passed in 0.330s (evidence/tests-portable-final.txt), including five repeated tests and one new case. See docs/PORTABLE.md for exact scope and reproduction commands.
