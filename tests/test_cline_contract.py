import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from do_spec.cline import command, session, validate
from do_spec.core import Fault


class ClineContractTests(unittest.TestCase):
    def test_unverified_architecture_fails_before_launch(self):
        with patch('do_spec.cline.platform.machine', return_value='ARM64'), patch('do_spec.cline.subprocess.run') as launch:
            with self.assertRaisesRegex(Fault, 'CLINE_PROFILE_UNVERIFIED'):
                validate({'contract': 'cline-3.0.61-local'})
            launch.assert_not_called()

    def test_fresh_session_preserves_credentials_and_disables_approval_by_default(self):
        argv = command({'argv': ['node.exe', 'cline'], 'timeout': 60}, 'worktree')
        self.assertNotIn('--id', argv)
        self.assertNotIn('--data-dir', argv)
        self.assertNotIn('--provider', argv)
        self.assertEqual(argv[argv.index('--auto-approve') + 1], 'false')
        self.assertEqual(argv[argv.index('--retries') + 1], '1')

    def test_zero_exit_aborted_is_distinct_from_completion(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / 'cline.log'
            log.write_text('\n'.join(json.dumps(r) for r in [
                {'type': 'hook_event', 'hookEventName': 'agent_start', 'taskId': 'session-1'},
                {'type': 'run_result', 'finishReason': 'aborted'}]))
            self.assertEqual(session(log), {'id': 'session-1', 'finish_reason': 'aborted'})

    def test_missing_result_or_multiple_sessions_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / 'cline.log'
            for records in [[], [{'type': 'run_result', 'finishReason': 'completed'}], [
                {'type': 'hook_event', 'hookEventName': 'agent_start', 'taskId': 'one'},
                {'type': 'hook_event', 'hookEventName': 'agent_start', 'taskId': 'two'},
                {'type': 'run_result', 'finishReason': 'completed'}]]:
                log.write_text('\n'.join(json.dumps(r) for r in records))
                with self.assertRaises(Fault):
                    session(log)
