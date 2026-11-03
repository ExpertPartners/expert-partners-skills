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
LABELED = "contains(fromJSON('{}'), github.event.issue.user.login)"


def gate(first, second):
    """A gate job shaped like the one in factory-builder-reusable.yml."""
    return f"""jobs:
  gate:
    if: >-
      github.event_name == 'workflow_dispatch' ||
      (github.event.action == 'labeled' && github.event.label.name == 'job' &&
        {first} &&
        !(github.event.sender.login == 'factory-droid[bot]' && startsWith(github.event.issue.title, 'Job:'))) ||
      (github.event.action == 'opened' && startsWith(github.event.issue.title, 'Job:') &&
        {second} &&
        !contains(github.event.issue.labels.*.name, 'job'))
    runs-on: ubuntu-latest
  release:
    needs: gate
    if: always() && needs.gate.outputs.start == 'true'
    runs-on: ubuntu-latest
"""


def workflow(first, second):
    return gate(LABELED.format(first), LABELED.format(second))


def caller(uses):
    return f"jobs:\n  builder:\n    uses: {uses}\n"


class Allowlist(unittest.TestCase):
    def test_both_full_passes(self):
        self.assertEqual(check.problems("w.yml", workflow(FULL, FULL)), [])

    def test_missing_from_first_fails(self):
        got = check.problems("w.yml", workflow(NO_AURA, FULL))
        self.assertEqual(got, ["w.yml: job gate: allowlist 1 is missing expertpartners-aura"])

    def test_missing_from_second_fails(self):
        got = check.problems("w.yml", workflow(FULL, NO_AURA))
        self.assertEqual(got, ["w.yml: job gate: allowlist 2 is missing expertpartners-aura"])

    def test_every_required_account_is_checked(self):
        for account in check.REQUIRED:
            short = [a for a in check.REQUIRED if a != account]
            got = check.problems("w.yml", workflow(FULL, str(short).replace("'", '"')))
            self.assertEqual(len(got), 1, account)
            self.assertTrue(got[0].endswith(f"missing {account}"), got[0])

    def test_extra_account_is_not_a_failure(self):
        extra = FULL.replace("]", ',"someone-else"]')
        self.assertEqual(check.problems("w.yml", workflow(extra, FULL)), [])

    def test_login_case_does_not_matter(self):
        self.assertEqual(check.problems("w.yml", workflow(FULL.replace("AllisonGaddy", "allisongaddy"), FULL)), [])

    def test_function_name_case_does_not_hide_an_allowlist(self):
        lower = f"Contains(fromJson('{NO_AURA}'), github.event.issue.user.login)"
        got = check.problems("w.yml", gate(lower, LABELED.format(FULL)))
        self.assertEqual(got, ["w.yml: job gate: allowlist 1 is missing expertpartners-aura"])

    def test_path_rewritten_as_equality_fails(self):
        eq = "github.event.issue.user.login == 'AllisonGaddy'"
        got = check.problems("w.yml", gate(LABELED.format(FULL), eq))
        self.assertEqual(len(got), 1)
        self.assertIn("job gate: an event path in its if: is not gated", got[0])

    def test_path_with_allowlist_removed_fails(self):
        got = check.problems("w.yml", gate("true", LABELED.format(FULL)))
        self.assertEqual(len(got), 1)
        self.assertIn("not gated", got[0])

    def test_negated_allowlist_is_not_a_gate(self):
        got = check.problems("w.yml", gate("!" + LABELED.format(FULL), LABELED.format(FULL)))
        self.assertEqual(len(got), 1)
        self.assertIn("not gated", got[0])

    def test_allowlist_in_an_or_is_not_a_gate(self):
        loose = f"(github.event.action == 'labeled' || {LABELED.format(FULL)})"
        got = check.problems("w.yml", gate(loose, LABELED.format(FULL)))
        self.assertEqual(len(got), 1)
        self.assertIn("not gated", got[0])

    def test_commented_out_allowlists_do_not_count(self):
        text = f"""jobs:
  gate:
    # contains(fromJSON('{FULL}'), github.event.issue.user.login)
    if: github.event_name == 'workflow_dispatch' || github.event.issue.user.login != ''
    # contains(fromJSON('{FULL}'), github.event.issue.user.login)
    runs-on: ubuntu-latest
"""
        got = check.problems("w.yml", text)
        self.assertEqual(len(got), 1)
        self.assertIn("not gated", got[0])

    def test_no_allowlist_fails(self):
        got = check.problems("w.yml", "jobs:\n  run:\n    if: github.event_name == 'workflow_dispatch'\n")
        self.assertEqual(len(got), 1)
        self.assertIn("no job gates on github.event.issue.user.login", got[0])

    def test_bad_json_fails(self):
        got = check.problems("w.yml", workflow('["AllisonGaddy",]', FULL))
        self.assertEqual(got, ["w.yml: job gate: allowlist 1 is not a JSON list of logins"])

    def test_bad_yaml_fails(self):
        got = check.problems("w.yml", "jobs: [\n")
        self.assertEqual(len(got), 1)
        self.assertIn("not valid YAML", got[0])


class Handoff(unittest.TestCase):
    def test_hand_off_to_this_repos_reusable_builder_passes(self):
        self.assertEqual(check.problems("c.yml", caller("./.github/workflows/factory-builder-reusable.yml")), [])
        canonical = "ExpertPartners/expert-partners-skills/.github/workflows/factory-builder-reusable.yml@main"
        self.assertEqual(check.problems("c.yml", caller(canonical)), [])

    def test_hand_off_anywhere_else_fails(self):
        for uses in (
            "OtherOrg/other/.github/workflows/factory-builder-reusable.yml@main",
            "ExpertPartners/expert-partners-skills/.github/workflows/factory-builder-reusable.yml@old-tag",
            "ExpertPartners/expert-partners-skills/.github/workflows/factory-builder-reusable.yml",
            "./.github/workflows/other-builder.yml",
        ):
            got = check.problems("c.yml", caller(uses))
            self.assertEqual(len(got), 1, uses)
            self.assertIn("no job gates", got[0])

    def test_commented_out_hand_off_does_not_count(self):
        text = "# uses: ./.github/workflows/factory-builder-reusable.yml\njobs:\n  other:\n    runs-on: ubuntu-latest\n"
        self.assertEqual(len(check.problems("c.yml", text)), 1)

    def test_only_hand_offs_fails(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "caller.yml")
            with open(path, "w", encoding="utf-8") as f:
                f.write(caller("./.github/workflows/factory-builder-reusable.yml"))
            self.assertEqual(check.main([path]), 1)


class Discovery(unittest.TestCase):
    def test_both_workflow_suffixes_are_scanned(self):
        with tempfile.TemporaryDirectory() as d:
            wf = os.path.join(d, ".github", "workflows")
            os.makedirs(wf)
            names = ["factory-builder-reusable.yml", "factory-builder-extra.yaml",
                     "factory-chat-to-code-loop-builder-x.yaml", "ci.yml"]
            for name in names:
                open(os.path.join(wf, name), "w").close()
            got = [os.path.basename(p) for p in check.builder_paths(d)]
            self.assertEqual(got, sorted(names[:3]))

    def test_main_exit_codes(self):
        with tempfile.TemporaryDirectory() as d:
            good = os.path.join(d, "good.yml")
            bad = os.path.join(d, "bad.yaml")
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
