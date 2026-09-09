import os
import sys
import tempfile
from pathlib import Path
import argparse
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'src'))
from do_spec.demo import create
from do_spec.core import read, write

parser = argparse.ArgumentParser(description='Prepare a disposable real-Cline/local-tracker E2E fixture; does not launch agents.')
parser.add_argument('--allow-local-tool-approval', action='store_true', help='Confirm authorization for tool auto-approval in this disposable fixture only')
parser.add_argument('--node', required=True)
parser.add_argument('--cline-wrapper', required=True)
args = parser.parse_args()
if not args.allow_local_tool_approval:
    parser.error('Explicit authorization for local fixture tool approval is required')
root = Path(tempfile.mkdtemp(prefix='do-spec-real-cline-'))
skill = root / 'skill'
import zipfile
with zipfile.ZipFile(REPO / 'dist/do-spec-skill.zip') as archive:
    archive.extractall(skill)
runner = skill / 'do-spec' / 'scripts' / 'run.py'
dagu = skill / 'do-spec' / 'tools' / 'dagu' / '2.11.2' / 'windows-amd64' / 'dagu.exe'
# First-use extraction through the copied runner; no separate installation hook.
import subprocess
setup_env = os.environ.copy()
setup_env.pop('DO_SPEC_DAGU', None)
subprocess.run([sys.executable, str(runner), 'setup'], check=True, stdout=subprocess.DEVNULL, env=setup_env)
project = create(root / 'fixture', dagu, 5)
config = read(project)
config['agent'] = {'kind': 'cline', 'contract': 'cline-3.0.61-local',
                   'argv': [str(Path(args.node).resolve()), str(Path(args.cline_wrapper).resolve())],
                   'auto_approve': True, 'timeout': 150}
write(project, config)
spec = Path(config['spec'])
spec.write_text(f'''# Disposable real-Cline E2E
You are implementing one synthetic ticket in a disposable worktree. No remote tracker is involved.
For the current ticket N, create results/N.txt containing exactly ok (no newline).
Validate the file and run the existing verify.py with this Python executable: {sys.executable}
After validation passes, use Python to read and update this local fake tracker JSON: {config['tracker']['state_file']}
Change ONLY issues[str(N)].state to closed, preserving all other fields and issues.
Never run fake_agent.py, spawn agents, select another ticket, access credentials, use remote services/tools, or commit/push/switch branches.
SPECIAL NEGATIVE CASE: ticket 5 deliberately represents failure. For ticket 5 do not create output, run tools, or close the issue. Report INJECTED_FAILURE_5 and stop. The orchestrator must prevent tickets 6-10 from starting.
Do not inspect other user directories; all work is restricted to this fixture/worktree and the exact fake tracker file above.
''', encoding='utf-8')
(root / 'fixture' / 'inputs' / '5.md').write_text('# Injected failure\n\n## Parent\n#100\n\n## Blocked by\n#4\n\n## Acceptance criteria\nThis negative E2E case must remain open. Do not create files or close this issue. Report INJECTED_FAILURE_5 without tools.\n', encoding='utf-8')
import json
print(json.dumps({'root': str(root), 'runner': str(runner), 'project': str(project)}))
