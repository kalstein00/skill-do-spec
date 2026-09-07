from pathlib import Path
import sys
import tempfile
import unittest
from do_spec.core import Fault, read, write
from do_spec.tracker import GitHubGhAdapter, ForgejoTeaAdapter, key


class TrackerTests(unittest.TestCase):
    def setup_adapter(self, root, kind, **options):
        base = "https://" + kind + ".example.invalid:8443/instance"
        profile = {"kind": kind, "transport": {"github": "gh", "forgejo": "tea"}[kind], "base_url": base, "repository": "team/repo", "account": "explicit-user", "synthetic_contract": True,
                   "argv": [sys.executable, str(Path(__file__).with_name("fake_tracker.py")), "--db", str(root / "db.json")], "timeout": .5}
        write(root / "db.json", {"issues": {str(i): {"number": i, "id": i+1000, "body": "한글 "*1000, "state": "open", "url": f"{base}/team/repo/issues/{i}"} for i in range(1, 7)}, **options})
        cls = GitHubGhAdapter if kind == "github" else ForgejoTeaAdapter
        return cls(profile, root / "logs")

    def test_both_providers_complete_three_pages_and_full_body(self):
        for kind in ["github", "forgejo"]:
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                a = self.setup_adapter(Path(tmp), kind)
                self.assertEqual(len(a.list_issues()), 6)
                self.assertEqual(len(a.issue(1)["body"]), 3000)

    def test_both_saved_comment_timeout_reconcile_without_duplicate(self):
        for kind in ["github", "forgejo"]:
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                a = self.setup_adapter(root, kind, write_then_hang=True)
                with self.assertRaises(Fault):
                    a.ensure_comment(1, "한글 & ; $()", "run-ticket", approved=True)
                receipt = a.ensure_comment(1, "한글 & ; $()", "run-ticket", approved=True)
                self.assertEqual(receipt["id"], 1)
                self.assertEqual(len(read(root/"db.json")["comments"]["1"]), 1)

    def test_partial_and_login_mismatch_and_hang_fail_closed(self):
        for kind in ["github", "forgejo"]:
            for option in [{"invalid_page": 2}, {"wrong_login": True}, {"hang": True}]:
                with self.subTest(kind=kind, option=option), tempfile.TemporaryDirectory() as tmp:
                    a = self.setup_adapter(Path(tmp), kind, **option)
                    with self.assertRaises(Fault):
                        a.list_issues()

    def test_keys_include_provider_port_prefix_and_writes_require_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = self.setup_adapter(Path(tmp), "forgejo")
            self.assertIn(":8443/instance", key(a.profile, 1))
            other = {**a.profile, "kind": "github"}
            self.assertNotEqual(key(a.profile, 1), key(other, 1))
            with self.assertRaises(Fault):
                a.ensure_comment(1, "x", "y")
