import unittest
from do_spec.planner import order, parse_ticket
from do_spec.core import Fault


class PlannerTests(unittest.TestCase):
    def test_dependencies_override_numbers_and_stable_ties(self):
        ts = [{"id": "2", "blocked_by": ["9"]}, {"id": "4", "blocked_by": []}, {"id": "9", "blocked_by": []}]
        self.assertEqual([t["id"] for t in order(ts)], ["4", "9", "2"])

    def test_cycles_missing_duplicate_empty_rejected(self):
        for ts in [[], [{"id": "1", "blocked_by": ["2"]}], [{"id": "1", "blocked_by": ["1"]}], [{"id": "1"}, {"id": "1"}]]:
            with self.subTest(ts=ts), self.assertRaises(Fault):
                order(ts)

    def test_only_explicit_sections_are_relations(self):
        t = parse_ticket("7", "# Example #99\n\n## Parent\n#100\n\n## Blocked by\nNone\n\n## Acceptance criteria\nSee #42; produce a file\n", "100")
        self.assertEqual(t["blocked_by"], [])
        self.assertIn("#42", t["acceptance"])

    def test_parent_conflict_rejected(self):
        with self.assertRaises(Fault):
            parse_ticket("7", "# title\n## Parent\n#99\n## Blocked by\nNone\n## Acceptance criteria\nx", "100")
