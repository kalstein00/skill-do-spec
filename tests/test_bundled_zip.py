import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from do_spec import bootstrap
from do_spec.core import Fault


class BundledZipTests(unittest.TestCase):
    def fixture(self, root, member='dagu.exe'):
        archive = root / 'windows-amd64.zip'
        with zipfile.ZipFile(archive, 'w') as z:
            z.writestr(member, b'fake test executable')
            z.writestr('../outside.txt', b'must never be extracted')
        manifest = {'binaries': {'windows-amd64/dagu.exe': hashlib.sha256(b'fake test executable').hexdigest()},
                    'bundled_archives': {archive.name: hashlib.sha256(archive.read_bytes()).hexdigest()}}
        (root / 'manifest.json').write_text(json.dumps(manifest))
        return archive

    def test_first_use_extracts_only_binary_and_reuses_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root)
            with patch.object(bootstrap, 'bundled_home', return_value=root), patch.object(bootstrap.platform, 'system', return_value='Windows'), patch.object(bootstrap.platform, 'machine', return_value='AMD64'), patch.object(bootstrap, 'validate_binary'), patch.object(bootstrap.urllib.request, 'urlopen') as network:
                path = Path(bootstrap.bundled_binary())
                stamp = path.stat().st_mtime_ns
                with patch.object(bootstrap.zipfile, 'ZipFile', side_effect=AssertionError('must reuse')):
                    self.assertEqual(bootstrap.bundled_binary(), str(path))
                self.assertEqual(path.stat().st_mtime_ns, stamp)
                self.assertFalse((root.parent / 'outside.txt').exists())
                network.assert_not_called()

    def test_corrupt_archive_stops_before_launch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = self.fixture(root)
            archive.write_bytes(b'corrupt')
            with patch.object(bootstrap, 'bundled_home', return_value=root), patch.object(bootstrap.platform, 'system', return_value='Windows'), patch.object(bootstrap.platform, 'machine', return_value='AMD64'), patch.object(bootstrap, 'validate_binary') as execute:
                with self.assertRaisesRegex(Fault, 'DAGU_BUNDLED_ARCHIVE_HASH_MISMATCH'):
                    bootstrap.bundled_binary()
                self.assertFalse((root / 'windows-amd64' / 'dagu.exe').exists())
                execute.assert_not_called()

    def test_missing_exact_member_cannot_extract_traversal_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root, '../dagu.exe')
            with patch.object(bootstrap, 'bundled_home', return_value=root), patch.object(bootstrap.platform, 'system', return_value='Windows'), patch.object(bootstrap.platform, 'machine', return_value='AMD64'), patch.object(bootstrap, 'validate_binary') as execute:
                with self.assertRaisesRegex(Fault, 'DAGU_BUNDLED_ARCHIVE_INVALID'):
                    bootstrap.bundled_binary()
                execute.assert_not_called()
