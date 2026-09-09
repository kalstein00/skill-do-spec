"""Version-scoped Cline CLI adapter; existing authentication stays in place."""
import json
import os
from pathlib import Path
import platform
import subprocess
from .core import Fault, digest, read
from .process import run


CONTRACT = 'cline-3.0.61-local'


def tool_files(agent):
    wrapper = Path(agent['argv'][1])
    cached = wrapper.parent / '.cline'
    binary = cached if cached.is_file() else None
    arch = {'amd64': 'x64', 'x86_64': 'x64', 'arm64': 'arm64'}.get(platform.machine().lower())
    if not arch:
        raise Fault('CLINE_PROFILE_UNVERIFIED', 'unknown architecture')
    if binary is None:
        for parent in [wrapper.parent, *wrapper.parent.parents]:
            candidate = parent / 'node_modules' / '@cline' / ('cli-windows-' + arch) / 'bin' / 'cline.exe'
            if candidate.is_file():
                binary = candidate
                break
    if binary is None:
        raise Fault('CLINE_BINARY_NOT_FOUND')
    return [*agent['argv'], str(wrapper.parent / 'ca-certs.cjs'), str(wrapper.parent.parent / 'package.json'), str(binary)]


def validate(agent):
    if os.name != 'nt' or platform.machine().lower() not in {'amd64', 'x86_64'} or agent.get('contract') != CONTRACT:
        raise Fault('CLINE_PROFILE_UNVERIFIED', 'only the explicit Windows x64 3.0.61 local contract is available')
    argv = agent.get('argv', [])
    if len(argv) != 2 or Path(argv[0]).name.lower() != 'node.exe' or Path(argv[1]).name != 'cline':
        raise Fault('CLINE_LAUNCHER_INVALID', 'use the installed Node executable and cline/bin/cline wrapper')
    if not all(Path(p).is_absolute() and Path(p).is_file() for p in argv):
        raise Fault('CLINE_LAUNCHER_INVALID')
    if os.environ.get('CLINE_BIN_PATH'):
        raise Fault('CLINE_BINARY_OVERRIDE_UNVERIFIED')
    if type(agent.get('auto_approve', False)) is not bool:
        raise Fault('CLINE_APPROVAL_INVALID')
    package = read(Path(argv[1]).parent.parent / 'package.json')
    result = subprocess.run([*argv, '--version'], stdin=subprocess.DEVNULL, capture_output=True, timeout=15)
    if package.get('name') != 'cline' or package.get('version') != '3.0.61' or result.returncode or result.stdout.strip() != b'3.0.61':
        raise Fault('CLINE_VERSION_UNVERIFIED')
    tool_files(agent)


def command(agent, worktree):
    # No --id means a new conversation. --data-dir would also isolate credentials.
    # All dynamic ticket content is supplied over stdin, never as CLI flags.
    return [*agent['argv'], '--json', '--auto-approve', str(agent.get('auto_approve', False)).lower(),
            '--retries', '1', '--timeout', str(max(1, int(agent['timeout']) - 5)), '--cwd', str(worktree),
            'Implement only the current ticket in the supplied JSON input. Honor its boundary. Do not spawn agents or select another ticket.']


def session(log):
    records = []
    for line in Path(log).read_text(encoding='utf-8', errors='replace').splitlines():
        if line.startswith('{'):
            try:
                records.append(json.loads(line))
            except ValueError:
                raise Fault('CLINE_OUTPUT_INVALID')
    ids = {r['taskId'] for r in records if r.get('type') == 'hook_event' and r.get('hookEventName') == 'agent_start' and r.get('taskId')}
    results = [r for r in records if r.get('type') == 'run_result']
    if len(ids) != 1 or len(results) != 1:
        raise Fault('CLINE_SESSION_UNVERIFIED')
    return {'id': next(iter(ids)), 'finish_reason': results[0].get('finishReason')}


def inspect(executable, directory):
    path = Path(executable).resolve()
    directory = Path(directory)
    records = {}
    for name, argv in [("version", [str(path), "--version"]), ("help", [str(path), "--help"])]:
        result = run(argv, directory, directory / name, timeout=10)
        records[name] = {"outcome": result["outcome"], "exit_code": result["exit_code"],
                         "output_hash": digest(Path(str(directory / name) + ".stdout.log").read_bytes())}
    return {"runtime": "cline", "status": "UNVERIFIED", "os": platform.platform(), "executable": str(path),
            "executable_hash": digest(path.read_bytes()), "observations": records,
            "missing": ["authorized noninteractive completion smoke", "fresh session semantics", "approval preservation", "process-tree cancellation", "rules/skills discovery"]}
