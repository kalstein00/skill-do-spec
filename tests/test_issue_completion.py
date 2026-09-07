import json
import os
from pathlib import Path
import tempfile
import sys
import unittest
from unittest.mock import patch
from do_spec.core import Fault, read, write
from do_spec.demo import create
from do_spec import runtime


@unittest.skipUnless(os.environ.get('DO_SPEC_DAGU'), 'real Dagu required')
class IssueCompletionTests(unittest.TestCase):
    def project(self, root):
        return create(root, os.environ['DO_SPEC_DAGU'], 5)

    def close(self, project, *ids):
        path = read(project)['tracker']['state_file']
        db = read(path)
        for tid in ids:
            db['issues'][str(tid)]['state'] = 'closed'
        write(path, db)

    def test_queue_only_open_and_closed_dependencies_are_satisfied(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self.project(Path(tmp))
            self.close(p, 1, 2, 3, 4)
            plan = read(runtime.make_plan(p))
            self.assertEqual([t['id'] for t in plan['tickets']], list(map(str, range(5, 11))))
            self.assertEqual(plan['tickets'][0]['blocked_by'], [])
            self.assertEqual(plan['tickets'][0]['closed_blockers'], ['4'])
            self.assertEqual(len(plan['excluded']), 4)

    def test_no_open_is_successful_empty_queue(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self.project(Path(tmp))
            self.close(p, *range(1, 11))
            plan = runtime.make_plan(p)
            root = runtime.start(plan)
            self.assertEqual(read(root/'run.json')['status'], 'SUCCEEDED')
            self.assertFalse((Path(tmp)/'agent.jsonl').exists())

    def test_closed_is_success_without_external_checks_or_runtime_commit(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self.project(Path(tmp))
            c = read(p)
            c['tickets'] = c['tickets'][:1]
            c['checks'] = []
            write(p, c)
            with patch.object(runtime, 'execute'):
                root = runtime.start(runtime.make_plan(p))
            initial = read(root/'run.json')
            for phase in ['prepare', 'agent', 'verify', 'report', 'accept']:
                runtime.phase(root, '1', phase, initial['dispatch'])
            final = read(root/'run.json')
            self.assertEqual(final['tickets']['1']['status'], 'ACCEPTED')
            self.assertEqual(final['head'], initial['head'])
            self.assertEqual(final['tickets']['1']['attempts'][0]['closure']['state'], 'closed')

    def test_invalid_tracker_state_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self.project(Path(tmp))
            c = read(p)
            db = read(c['tracker']['state_file'])
            db['issues']['2']['state'] = 'unknown'
            write(c['tracker']['state_file'], db)
            with self.assertRaises(Fault):
                runtime.make_plan(p)

    def test_both_tracker_adapters_select_spec_open_members(self):
        for kind, transport in [('github', 'gh'), ('forgejo', 'tea')]:
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                p = self.project(Path(tmp))
                c = read(p)
                dbpath = c['tracker']['state_file']
                db = read(dbpath)
                base = 'https://' + kind + '.example.invalid'
                for item in c['tickets']:
                    issue = db['issues'][item['id']]
                    issue.update(id=int(item['id'])+1000, body=Path(item['path']).read_text(encoding='utf-8'), url=f"{base}/team/repo/issues/{item['id']}")
                db['issues']['1']['state'] = 'closed'
                db['issues']['10']['body'] = db['issues']['10']['body'].replace('#100', '#999')
                write(dbpath, db)
                c['tracker'] = {'kind': kind, 'transport': transport, 'base_url': base, 'repository': 'team/repo', 'account': 'selected', 'synthetic_contract': True,
                                'argv': [sys.executable, str(Path(__file__).with_name('fake_tracker.py')), '--db', dbpath], 'timeout': 5}
                write(p, c)
                plan = read(runtime.make_plan(p))
                self.assertEqual([t['id'] for t in plan['tickets']], list(map(str, range(2,10))))
                self.assertEqual([t['id'] for t in plan['excluded']], ['1'])
                self.assertEqual(runtime.require_closed(plan, '1', Path(tmp)/'observe')['state'], 'closed')
                with self.assertRaises(Fault):
                    runtime.require_closed(plan, '2', Path(tmp)/'observe')

    def test_closed_between_prepare_and_agent_is_not_executed(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self.project(Path(tmp))
            c = read(p)
            c['tickets'] = c['tickets'][:1]
            write(p, c)
            with patch.object(runtime, 'execute'):
                root = runtime.start(runtime.make_plan(p))
            dispatch = read(root/'run.json')['dispatch']
            runtime.phase(root, '1', 'prepare', dispatch)
            self.close(p, 1)
            with patch.object(runtime, 'run', side_effect=AssertionError('closed issue executed')):
                for phase in ['agent', 'verify', 'report', 'accept']:
                    runtime.phase(root, '1', phase, dispatch)
            self.assertEqual(read(root/'run.json')['tickets']['1']['status'], 'ACCEPTED')

    def test_nonzero_exit_does_not_override_closed_signal(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self.project(Path(tmp))
            c = read(p)
            c['tickets'] = c['tickets'][:1]
            write(p, c)
            with patch.object(runtime, 'execute'):
                root = runtime.start(runtime.make_plan(p))
            dispatch = read(root/'run.json')['dispatch']
            runtime.phase(root, '1', 'prepare', dispatch)
            def worker(*args, **kwargs):
                self.close(p, 1)
                return {'outcome': 'EXITED', 'exit_code': 9}
            with patch.object(runtime, 'run', side_effect=worker):
                runtime.phase(root, '1', 'agent', dispatch)
            for phase in ['verify', 'report', 'accept']:
                runtime.phase(root, '1', phase, dispatch)
            self.assertEqual(read(root/'run.json')['tickets']['1']['status'], 'ACCEPTED')

    def test_lookup_failure_after_worker_is_not_completion(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self.project(Path(tmp))
            c = read(p)
            c['tickets'] = c['tickets'][:1]
            write(p, c)
            with patch.object(runtime, 'execute'):
                root = runtime.start(runtime.make_plan(p))
            dispatch = read(root/'run.json')['dispatch']
            for phase in ['prepare', 'agent']:
                runtime.phase(root, '1', phase, dispatch)
            write(c['tracker']['state_file'], {'issues': {}})
            with self.assertRaises(Fault):
                runtime.phase(root, '1', 'verify', dispatch)
            self.assertEqual(read(root/'run.json')['status'], 'FAILED')

    def test_reopened_excluded_blocker_stops_before_agent(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self.project(Path(tmp))
            self.close(p, 1)
            with patch.object(runtime, 'execute'):
                root = runtime.start(runtime.make_plan(p))
            c = read(p)
            db = read(c['tracker']['state_file'])
            db['issues']['1']['state'] = 'open'
            write(c['tracker']['state_file'], db)
            with self.assertRaises(Fault):
                runtime.phase(root, '2', 'prepare', read(root/'run.json')['dispatch'])
            self.assertFalse((Path(tmp)/'agent.jsonl').exists())

    def test_real_dagu_open_five_stops_then_closed_verify_only(self):
        with tempfile.TemporaryDirectory(prefix='closed-queue ', delete=False) as tmp:
            p = self.project(Path(tmp))
            self.close(p, 1, 2)
            plan = runtime.make_plan(p)
            with self.assertRaises(Fault):
                runtime.start(plan)
            root = next((Path(tmp)/'state'/'runs').iterdir())
            self.assertEqual(read(root/'run.json')['reason'], 'ISSUE_STILL_OPEN')
            journal = Path(tmp)/'agent.jsonl'
            self.assertEqual([json.loads(x)['ticket'] for x in journal.read_text().splitlines()], ['3','4','5'])
            self.close(p, 5)
            runtime.resume(root, 'verify-only')
            self.assertEqual(read(root/'run.json')['status'], 'SUCCEEDED')
            self.assertEqual([json.loads(x)['ticket'] for x in journal.read_text().splitlines()], list(map(str, range(3,11))))
