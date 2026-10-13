import importlib.util
import os
import unittest

spec = importlib.util.spec_from_file_location(
    "drift", os.path.join(os.path.dirname(__file__), "..", "drift-check.py"))
drift = importlib.util.module_from_spec(spec)
spec.loader.exec_module(drift)

LIST = """Marketplace `openai-bundled`
PLUGIN   STATUS   VERSION  SOURCE
code-review@openai-bundled  installed, enabled  1  /x
Marketplace `expert-partners`
/root/marketplace.json

PLUGIN                       STATUS              VERSION  SOURCE
operating-doctrine@expert-partners  installed, enabled  2.56.0   /x
research-ops@expert-partners        not installed                /x
systems-map@expert-partners         installed, disabled 0.6.1    /x
Marketplace `other`
foo@other  installed, enabled  9  /x
"""

JOBROW = [drift.JOB, "HQ", "job", "Not started", "w", "n", "2026-10-01", "2026-10-01"]


class Drift(unittest.TestCase):
    def test_parse_codex_list_only_reads_our_block(self):
        got = drift.parse_codex_list(LIST)
        self.assertEqual(got, {"operating-doctrine": "2.56.0", "research-ops": None, "systems-map": "0.6.1"})

    def test_missing_in_claude_code(self):
        self.assertEqual(drift.missing_in_claude_code({"a": "1", "b": "2", "c": "3"}, {"b": "2"}), ["a", "c"])

    def test_marketplace_versions(self):
        raw = '{"plugins":[{"name":"a","version":"1.0.0"},{"name":"b"}]}'
        self.assertEqual(drift.versions_from_marketplace(raw), {"a": "1.0.0", "b": ""})

    def test_nothing_behind_and_no_row_is_silent(self):
        self.assertEqual(drift.plan_row([["Job"]], [], "abcdef123", "2026-10-13")[0], "none")

    def test_behind_appends_one_row(self):
        action, n, vals = drift.plan_row([["Job"]], ["Codex has x 1, repo has 2"], "abcdef123", "2026-10-13")
        self.assertEqual((action, n), ("append", None))
        self.assertEqual(vals[0], drift.JOB)
        self.assertIn("Codex has x 1", vals[5])
        self.assertEqual(len(vals), 8)

    def test_behind_updates_the_existing_row_instead_of_adding(self):
        action, n, vals = drift.plan_row([["Job"], JOBROW], ["Codex behind"], "abcdef123", "2026-10-13")
        self.assertEqual((action, n), ("update", 2))
        self.assertEqual(vals[6], "2026-10-01")
        self.assertEqual(vals[7], "2026-10-13")

    def test_all_match_closes_an_open_row_quietly(self):
        action, n, vals = drift.plan_row([["Job"], JOBROW], [], "abcdef123", "2026-10-13")
        self.assertEqual((action, n, vals[3]), ("update", 2, "Done"))

    def test_done_row_stays_alone_when_all_match(self):
        done = list(JOBROW)
        done[3] = "Done"
        self.assertEqual(drift.plan_row([["Job"], done], [], "abcdef123", "2026-10-13")[0], "none")


if __name__ == "__main__":
    unittest.main()
