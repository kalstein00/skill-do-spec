from contextlib import contextmanager
from pathlib import Path
import os
import tempfile
import unittest
from unittest.mock import patch
from do_spec.core import Fault, read, write, inside
from do_spec.demo import create
from do_spec import runtime, git as g


@unittest.skipUnless(os.environ.get("DO_SPEC_DAGU"), "real Dagu version check required")
class BoundaryTests(unittest.TestCase):
    @contextmanager
    def setup_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = create(Path(tmp), os.environ["DO_SPEC_DAGU"], completion='external-checkpoint')
            c = read(project)
            c["tickets"] = c["tickets"][:1]
            write(project, c)
            plan = runtime.make_plan(project)
            with patch.object(runtime, "execute"):
                root = runtime.start(plan)
            state = read(root / "run.json")
            def phase(name):
                runtime.phase(root, "1", name, state["dispatch"])
            yield root, Path(state["worktree"]), phase

    def test_protected_verifier_change_fails_before_checkpoint(self):
        with self.setup_run() as (root, wt, phase):
            phase("prepare")
            phase("agent")
            baseline = g.head(wt)
            (wt / "verify.py").write_text("pass")
            with self.assertRaises(Fault):
                phase("verify")
            self.assertEqual(g.head(wt), baseline)
            self.assertEqual(read(root/"run.json")["tickets"]["1"]["failed_phase"], "verify")

    def test_change_after_verification_is_not_committed(self):
        with self.setup_run() as (root, wt, phase):
            for name in ["prepare", "agent", "verify"]:
                phase(name)
            before = g.head(wt)
            (wt/"results"/"1.txt").write_text("unverified")
            with self.assertRaises(Fault):
                phase("checkpoint")
            self.assertEqual(g.head(wt), before)

    def test_commit_then_crash_reconciles_exact_intent_without_new_commit(self):
        with self.setup_run() as (root, wt, phase):
            for name in ["prepare", "agent", "verify"]:
                phase(name)
            real_git = g.git
            def crashing(repo, *args, **kwargs):
                result = real_git(repo, *args, **kwargs)
                if args[0] == "commit":
                    raise Fault("SIMULATED_CRASH", code=15)
                return result
            with patch.object(g, "git", side_effect=crashing), self.assertRaises(Fault):
                phase("checkpoint")
            commit = g.head(wt)
            self.assertEqual(runtime.reconcile_checkpoint(root), commit)
            self.assertEqual(g.head(wt), commit)
            self.assertEqual(read(root/"run.json")["tickets"]["1"]["status"], "REPORT_PENDING")

    def test_raw_retry_cannot_reenter_agent(self):
        with self.setup_run() as (root, wt, phase):
            phase("prepare")
            phase("agent")
            with self.assertRaises(Fault):
                phase("agent")
            self.assertEqual(len((root.parents[2]/"agent.jsonl").read_text().splitlines()), 1)

    def test_unexpected_agent_commit_is_preserved(self):
        with self.setup_run() as (root, wt, phase):
            phase("prepare")
            phase("agent")
            g.git(wt, "add", "--", "results/1.txt")
            g.git(wt, "commit", "-m", "unapproved agent commit")
            unexpected = g.head(wt)
            with self.assertRaises(Fault):
                phase("verify")
            self.assertEqual(g.head(wt), unexpected)

    def test_plan_drift_and_path_escape_are_rejected(self):
        with self.setup_run() as (root, wt, phase):
            plan = read(root/"plan.json")
            Path(plan["config"]["spec"]).write_text("changed")
            with self.assertRaises(Fault):
                phase("prepare")
            with self.assertRaises(Fault):
                inside(root, "../../outside")
