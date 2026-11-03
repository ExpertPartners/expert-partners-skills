import importlib.util
import os
import tempfile
import unittest

HERE = os.path.dirname(__file__)
spec = importlib.util.spec_from_file_location("check_allowlist", os.path.join(HERE, "..", "check_allowlist.py"))
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)

FULL = '["AllisonGaddy","expertpartners","expertpartners-ember","expertpartners-aura"]'
NO_AURA = '["AllisonGaddy","expertpartners","expertpartners-ember"]'


def workflow(first, second):
    return f"""jobs:
  run:
    if: >-
      github.event_name == 'workflow_dispatch' ||
      (github.event.action == 'labeled' &&
        contains(fromJSON('{first}'), github.event.issue.user.login)) ||
      (github.event.action == 'opened' &&
        contains(fromJSON('{second}'), github.event.issue.user.login))
"""


class Allowlist(unittest.TestCase):
    def test_both_full_passes(self):
        self.assertEqual(check.problems("w.yml", workflow(FULL, FULL)), [])

    def test_missing_from_first_fails(self):
        got = check.problems("w.yml", workflow(NO_AURA, FULL))
        self.assertEqual(len(got), 1)
        self.assertIn("w.yml:6:", got[0])
        self.assertIn("missing expertpartners-aura", got[0])

    def test_missing_from_second_fails(self):
        got = check.problems("w.yml", workflow(FULL, NO_AURA))
        self.assertEqual(len(got), 1)
        self.assertIn("w.yml:8:", got[0])

    def test_every_required_account_is_checked(self):
        for account in check.REQUIRED:
            short = [a for a in check.REQUIRED if a != account]
            got = check.problems("w.yml", workflow(FULL, str(short).replace("'", '"')))
            self.assertEqual(len(got), 1, account)
            self.assertTrue(got[0].endswith(f"missing {account}"), got[0])

    def test_extra_account_is_not_a_failure(self):
        extra = FULL.replace("]", ',"someone-else"]')
        self.assertEqual(check.problems("w.yml", workflow(extra, FULL)), [])

    def test_no_allowlist_fails(self):
        got = check.problems("w.yml", "jobs:\n  run:\n    if: github.event_name == 'workflow_dispatch'\n")
        self.assertEqual(len(got), 1)
        self.assertIn("no contains(fromJSON", got[0])

    def test_caller_that_hands_off_passes(self):
        caller = "jobs:\n  builder:\n    uses: ./.github/workflows/factory-builder-reusable.yml\n"
        self.assertEqual(check.problems("caller.yml", caller), [])
        remote = caller.replace("./", "ExpertPartners/expert-partners-skills/").rstrip() + "@main\n"
        self.assertEqual(check.problems("caller.yml", remote), [])

    def test_only_hand_offs_fails(self):
        with tempfile.TemporaryDirectory() as d:
            caller = os.path.join(d, "caller.yml")
            with open(caller, "w", encoding="utf-8") as f:
                f.write("jobs:\n  builder:\n    uses: ./.github/workflows/factory-builder-reusable.yml\n")
            self.assertEqual(check.main([caller]), 1)

    def test_bad_json_fails(self):
        got = check.problems("w.yml", workflow('["AllisonGaddy",]', FULL))
        self.assertEqual(len(got), 1)
        self.assertIn("not a JSON list", got[0])

    def test_main_exit_codes(self):
        with tempfile.TemporaryDirectory() as d:
            good = os.path.join(d, "good.yml")
            bad = os.path.join(d, "bad.yml")
            with open(good, "w", encoding="utf-8") as f:
                f.write(workflow(FULL, FULL))
            with open(bad, "w", encoding="utf-8") as f:
                f.write(workflow(FULL, NO_AURA))
            self.assertEqual(check.main([good]), 0)
            self.assertEqual(check.main([good, bad]), 1)

    def test_repo_builders_pass(self):
        self.assertEqual(check.main([]), 0)


if __name__ == "__main__":
    unittest.main()
