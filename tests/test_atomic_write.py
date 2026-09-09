import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from do_spec.core import write


@unittest.skipUnless(os.name == 'nt', 'Windows sharing violation semantics')
class AtomicWriteTests(unittest.TestCase):
    def denied(self):
        error = PermissionError('temporary sharing/access denial')
        error.winerror = 5
        return error

    def test_transient_denial_retries_only_replace(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'state.json'
            write(target, {'old': True})
            replace = os.replace
            calls = []
            def intermittent(source, dest):
                calls.append(1)
                if len(calls) <= 2:
                    self.assertEqual(json.loads(target.read_text()), {'old': True})
                    raise self.denied()
                replace(source, dest)
            with patch('do_spec.core.os.replace', side_effect=intermittent), patch('do_spec.core.time.sleep'):
                write(target, {'new': True})
            self.assertEqual(len(calls), 3)
            self.assertEqual(json.loads(target.read_text()), {'new': True})

    def test_persistent_denial_is_bounded_and_preserves_previous_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'state.json'
            write(target, {'old': True})
            with patch('do_spec.core.os.replace', side_effect=self.denied()) as replace, patch('do_spec.core.time.sleep'):
                with self.assertRaises(PermissionError):
                    write(target, {'new': True})
            self.assertEqual(replace.call_count, 6)
            self.assertEqual(json.loads(target.read_text()), {'old': True})
            self.assertEqual(list(Path(tmp).iterdir()), [target])
