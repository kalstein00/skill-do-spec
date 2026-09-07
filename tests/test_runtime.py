import json
import os
from pathlib import Path
import tempfile
import unittest
from do_spec.core import Fault, read
from do_spec.demo import create
from do_spec.runtime import make_plan, start, resume, phase
from do_spec import git as g


@unittest.skipUnless(os.environ.get("DO_SPEC_DAGU"), "real Dagu path required")
class RuntimeTests(unittest.TestCase):
    def test_failure_five_preserved_and_verify_only_resume(self):
        # Preserve real Dagu artifacts for inspection. Windows Dagu history paths
        # can exceed MAX_PATH; default tempfile recursive cleanup is not reliable.
        with tempfile.TemporaryDirectory(prefix="do-spec 한글 space ", delete=False) as tmp:
            project = create(Path(tmp), os.environ["DO_SPEC_DAGU"], 5, completion='external-checkpoint')
            plan_path = make_plan(project)
            source = read(project)["repo"]
            baseline = g.head(source)
            with self.assertRaises(Fault):
                start(plan_path)
            root = next((Path(tmp) / "state" / "runs").iterdir())
            state = read(root / "run.json")
            self.assertEqual(state["status"], "FAILED")
            self.assertEqual([v["status"] for v in state["tickets"].values()], ["ACCEPTED"]*4 + ["FAILED"] + ["PENDING"]*5)
            wt = Path(state["worktree"])
            journal = [json.loads(line) for line in (Path(tmp) / "agent.jsonl").read_text().splitlines()]
            self.assertEqual([e["ticket"] for e in journal], ["1", "2", "3", "4", "5"])
            self.assertEqual(len({e["session"] for e in journal}), 5)
            self.assertEqual(g.head(source), baseline)
            self.assertEqual(g.git(source, "status", "--porcelain"), "")
            self.assertIn("results/5.txt", g.changes(wt))
            for i in range(6, 11):
                self.assertFalse((wt / "results" / f"{i}.txt").exists())
            with self.assertRaises(Fault):
                phase(root, "6", "agent", state["dispatch"])
            (wt / "results" / "5.txt").write_text("ok", encoding="utf-8")
            resume(root, "verify-only")
            final = read(root / "run.json")
            self.assertEqual(final["status"], "SUCCEEDED")
            journal = [json.loads(line) for line in (Path(tmp) / "agent.jsonl").read_text().splitlines()]
            self.assertEqual([e["ticket"] for e in journal], [str(i) for i in range(1, 11)])
            self.assertEqual(g.git(wt, "rev-list", "--count", f"{baseline}..HEAD"), "10")
            with self.assertRaises(Fault) as duplicate:
                start(plan_path)
            self.assertEqual(duplicate.exception.reason, "PLAN_ALREADY_STARTED")
