import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from do_spec import bootstrap
from do_spec.cli import monitoring
from do_spec.core import Fault

ROOT = Path(__file__).resolve().parents[1]


class PortableTests(unittest.TestCase):
    def test_bundle_contains_exact_runtime(self):
        sources = ROOT / 'src' / 'do_spec'
        bundled = ROOT / 'skills' / 'do-spec' / 'scripts' / 'runtime' / 'do_spec'
        self.assertEqual({p.name for p in sources.glob('*.py')}, {p.name for p in bundled.glob('*.py')})
        for source in sources.glob('*.py'):
            self.assertEqual(source.read_bytes(), (bundled / source.name).read_bytes(), source.name)

    def test_copied_skill_runs_without_installed_package(self):
        import shutil
        import os
        with tempfile.TemporaryDirectory(prefix='portable-') as tmp:
            dest = Path(tmp) / '복사 skill'
            shutil.copytree(ROOT / 'skills' / 'do-spec', dest, ignore=shutil.ignore_patterns('__pycache__'))
            env = os.environ.copy()
            env.pop('PYTHONPATH', None)
            result = subprocess.run([sys.executable, '-I', str(dest / 'scripts' / 'run.py'), '--help'], cwd=tmp, env=env, capture_output=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(b'setup', result.stdout)

    def test_hash_mismatch_never_installs_or_executes(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(bootstrap, 'cache_home', return_value=Path(tmp)), patch.object(bootstrap.shutil, 'which', return_value=None), patch.dict('os.environ', {'DO_SPEC_DAGU': ''}), patch.object(bootstrap.platform, 'system', return_value='Windows'), patch.object(bootstrap.platform, 'machine', return_value='AMD64'), patch.object(bootstrap.urllib.request, 'urlopen', return_value=io.BytesIO(b'wrong archive')), patch.object(bootstrap, 'validate_binary') as execute:
            with self.assertRaisesRegex(Fault, 'DAGU_DOWNLOAD_HASH_MISMATCH'):
                bootstrap.resolve()
            execute.assert_not_called()
            self.assertFalse((Path(tmp) / 'dagu.exe').exists())

    def test_explicit_version_failure_never_falls_back_to_download(self):
        with patch.object(bootstrap, 'validate_binary', side_effect=Fault('DAGU_VERSION_UNVERIFIED')), patch.object(bootstrap.urllib.request, 'urlopen') as network:
            with self.assertRaises(Fault):
                bootstrap.resolve('wrong-dagu')
            network.assert_not_called()

    def test_monitoring_does_not_claim_server_is_running(self):
        with contextlib.redirect_stderr(io.StringIO()) as output:
            monitoring('project.json', 18081)
        info = json.loads(output.getvalue())
        self.assertEqual(info['monitoring_url'], 'http://127.0.0.1:18081')
        self.assertEqual(info['monitoring_status'], 'start-ui-in-another-terminal')
        self.assertIn('--project', info['ui_command_argv'])
        with self.assertRaises(Fault):
            monitoring('project.json', 0)

    def test_monitoring_remembers_project_port_and_preserves_unicode(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / '프로젝트.json'
            project.write_text(json.dumps({'state_dir': 'state'}), encoding='utf-8')
            (root / 'state').mkdir()
            (root / 'state' / 'monitoring.json').write_text('{"port":18081}')
            with contextlib.redirect_stderr(io.StringIO()) as output:
                info = monitoring(project)
            self.assertEqual(info['monitoring_url'], 'http://127.0.0.1:18081')
            self.assertTrue(output.getvalue().isascii())
            self.assertIn(str(project), json.loads(output.getvalue())['ui_command_argv'])
