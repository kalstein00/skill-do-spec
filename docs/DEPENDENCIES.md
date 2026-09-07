# Dependencies and license boundaries

do-spec uses Python's standard library and launches external executables. It does not embed or redistribute Dagu, Git, tea, gh, or agent binaries. `.tools` is an ignored developer download directory, not a distribution artifact.

| Dependency | Selected/tested version | Role | License notice |
|---|---|---|---|
| Python | 3.12.14 | Runtime, required 3.12+ | PSF License |
| setuptools | 84.0.0 | Wheel build only | MIT |
| Dagu | 2.11.2 | External engine and existing UI | Downloaded release LICENSE: GNU GPL v3; inspect release licensing before redistribution |
| Git | 2.55.0.windows.5 | External worktree/checkpoint | GPL v2 |
| GitHub CLI | 2.100.0 | CLI help inspection, future live contract | MIT |
| tea | 0.15.1 | CLI help inspection, future live contract | MIT; verify upstream notice for redistribution |
| Cline | not installed | Intended live CLI contract; currently blocked | User-installed distribution terms apply |

No paid orchestration tier is required. Real agent/model charges and corporate policy are separate. This repository does not choose a publication license on the owner's behalf; do not assume permission to publish proprietary source merely because it is present locally.

Portable runner: uv 0.10.9 was used for Windows verification (MIT/Apache-2.0). uv is a user prerequisite, not bundled. The skill bundles only do-spec Python source. setup/demo/init can download pinned Dagu into the user cache; they do not redistribute its binary inside the ZIP. Python dependencies remain empty. The downloaded archive is hash-checked before extraction/execution. Offline environments can supply --dagu explicitly.
