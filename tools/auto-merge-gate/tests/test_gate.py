"""Unit tests for the auto-merge gate. Every GitHub call goes to FakeGitHub; nothing touches the network.

Run from the repo root: python3 -m unittest discover -s tools/auto-merge-gate/tests -v
"""

import base64
import copy
import importlib.util
import json
import os
import sys
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "gate", os.path.join(os.path.dirname(__file__), "..", "gate.py"))
gate = importlib.util.module_from_spec(spec)
# dataclasses resolves annotations through sys.modules, so register before executing.
sys.modules["gate"] = gate
spec.loader.exec_module(gate)

REPO = os.environ.get("GATE_TEST_REPO", "ExpertPartners/expert-partners-skills")
HEAD = "a" * 40
OLD = "b" * 40
CFG = gate.Config(repo=REPO)
GOOD_NOTE = "---\noperating-doctrine: minor\n---\n\nAdds the release step.\n"


def codex_comment(sha=HEAD, status="completed", unresolved=False, security_unresolved=None, updated="2026-11-01T10:00:00Z"):
    state = {
        "code_review": {"commit_sha": sha, "has_any_findings": unresolved, "has_unresolved_findings": unresolved, "status": status},
        "security_review": {"commit_sha": sha, "has_any_findings": security_unresolved, "has_unresolved_findings": security_unresolved, "status": "completed"},
    }
    body = (
        "<!-- codex-pull-request-review-summary -->\n"
        f"<!-- codex-review-state:v1 {json.dumps(state, separators=(',', ':'))} -->\n"
        "## Codex Review Summary\n"
    )
    return {"id": 900, "user": {"login": "chatgpt-codex-connector[bot]"}, "body": body, "created_at": updated, "updated_at": updated}


def passing_routes(number=7, issue=126):
    return {
        f"/repos/{REPO}/pulls/{number}": {
            "number": number, "state": "open", "draft": False,
            "user": {"login": "factory-droid[bot]"},
            "base": {"ref": "main"}, "head": {"sha": HEAD},
            "body": f"Closes #{issue}\n\nAcceptance checks ...",
            "mergeable": True, "mergeable_state": "blocked",
        },
        f"/repos/{REPO}/issues/{issue}": {"number": issue, "labels": [{"name": "job"}, {"name": "in-progress"}]},
        f"/repos/{REPO}/issues/{number}/comments": [codex_comment()],
        f"/repos/{REPO}/commits/{HEAD}/check-runs": [
            {"name": "brand + classification lint (changed files)", "status": "completed", "conclusion": "success"},
            {"name": "gitleaks secret scan (full history)", "status": "completed", "conclusion": "success"},
            {"name": "validate + regenerate skills-graph.json", "status": "completed", "conclusion": "skipped"},
            {"name": "move-contract", "status": "completed", "conclusion": "neutral"},
            {"name": "auto-merge-gate", "status": "in_progress", "conclusion": None},
        ],
        f"/repos/{REPO}/commits/{HEAD}/status": {"state": "pending", "statuses": []},
        f"/repos/{REPO}/pulls/{number}/files": [{"filename": ".changeset/126-change.md", "status": "added"}],
        f"/repos/{REPO}/contents/.changeset/126-change.md?ref={HEAD}": content(GOOD_NOTE),
        f"/repos/{REPO}/contents/.claude-plugin/marketplace.json?ref={HEAD}": content(market()),
        f"/repos/{REPO}/pulls": [],
    }


class FakeGitHub:
    def __init__(self, routes, put_result=None, put_error=None):
        self.routes = copy.deepcopy(routes)
        self.calls = []
        self.put_result = put_result
        self.put_error = put_error

    def _route(self, path):
        if path not in self.routes:
            raise gate.GitHubError(404, f"Not Found: {path}")
        return copy.deepcopy(self.routes[path])

    def get(self, path, params=None):
        self.calls.append(("GET", path, None))
        return self._route(path)

    def paginate(self, path, key=None, params=None):
        self.calls.append(("GET", path, None))
        return self._route(path)

    def post(self, path, body):
        self.calls.append(("POST", path, body))
        return {"id": 1}

    def put(self, path, body):
        self.calls.append(("PUT", path, body))
        if self.put_error:
            raise self.put_error
        return self.put_result

    def patch(self, path, body):
        self.calls.append(("PATCH", path, body))
        return {}

    def writes(self):
        return [c for c in self.calls if c[0] != "GET"]


class Base(unittest.TestCase):
    def fake(self, routes):
        return FakeGitHub(routes)

    def evaluate(self, routes, number=7):
        return gate.evaluate(self.fake(routes), CFG, number)

    def assert_left_alone(self, routes, fragment):
        gh = self.fake(routes)
        merger = FakeGitHub({})
        self.assertEqual(gate.run_plan(gh, CFG, "pull_request_target", {"pull_request": {"number": 7}}), [])
        self.assertEqual(gate.run_merge(gh, merger, CFG, [7]), [])
        d = gate.evaluate(gh, CFG, 7)
        self.assertEqual(d.action, "skip")
        self.assertIn(fragment, d.reasons[0])
        self.assertEqual(gh.writes(), [], "a pull request the gate does not consider gets no comment")
        self.assertEqual(merger.calls, [])

    def assert_refused(self, routes, fragment):
        gh = self.fake(routes)
        merger = FakeGitHub({})
        ready = gate.run_plan(gh, CFG, "pull_request_target", {"pull_request": {"number": 7}})
        self.assertEqual(ready, [])
        self.assertEqual(merger.calls, [])
        writes = gh.writes()
        self.assertEqual(len(writes), 1, writes)
        method, path, body = writes[0]
        self.assertEqual((method, path), ("POST", f"/repos/{REPO}/issues/7/comments"))
        self.assertIn(f"<!-- auto-merge-gate:v1 head={HEAD} -->", body["body"])
        self.assertIn(fragment, body["body"])
        return body["body"]


class LeftAlone(Base):
    def test_draft(self):
        routes = passing_routes()
        routes[f"/repos/{REPO}/pulls/7"]["draft"] = True
        self.assert_left_alone(routes, "draft")

    def test_wrong_author(self):
        routes = passing_routes()
        routes[f"/repos/{REPO}/pulls/7"]["user"] = {"login": "AllisonGaddy"}
        self.assert_left_alone(routes, "author is AllisonGaddy")

    def test_issue_without_job_label(self):
        routes = passing_routes()
        routes[f"/repos/{REPO}/issues/126"]["labels"] = [{"name": "in-progress"}]
        self.assert_left_alone(routes, "does not carry the job label")

    def test_body_not_starting_with_closes(self):
        routes = passing_routes()
        routes[f"/repos/{REPO}/pulls/7"]["body"] = "Some work.\nCloses #126"
        self.assert_left_alone(routes, "Closes #N")

    def test_closes_points_at_a_pull_request(self):
        routes = passing_routes()
        routes[f"/repos/{REPO}/issues/126"]["pull_request"] = {"url": "x"}
        self.assert_left_alone(routes, "is a pull request")

    def test_closed_pull_request(self):
        routes = passing_routes()
        routes[f"/repos/{REPO}/pulls/7"]["state"] = "closed"
        self.assert_left_alone(routes, "not open")

    def test_base_not_main(self):
        routes = passing_routes()
        routes[f"/repos/{REPO}/pulls/7"]["base"] = {"ref": "release"}
        self.assert_left_alone(routes, "base is not main")


class Refused(Base):
    def test_failing_check(self):
        routes = passing_routes()
        routes[f"/repos/{REPO}/commits/{HEAD}/check-runs"][1]["conclusion"] = "failure"
        self.assert_refused(routes, "Check `gitleaks secret scan (full history)` finished as failure.")

    def test_pending_check(self):
        routes = passing_routes()
        routes[f"/repos/{REPO}/commits/{HEAD}/check-runs"][0].update(status="in_progress", conclusion=None)
        self.assert_refused(routes, "Check `brand + classification lint (changed files)` is in_progress, not completed.")

    def test_cancelled_check(self):
        routes = passing_routes()
        routes[f"/repos/{REPO}/commits/{HEAD}/check-runs"][0]["conclusion"] = "cancelled"
        self.assert_refused(routes, "finished as cancelled")

    def test_failing_commit_status(self):
        routes = passing_routes()
        routes[f"/repos/{REPO}/commits/{HEAD}/status"]["statuses"] = [{"context": "deploy/preview", "state": "failure"}]
        self.assert_refused(routes, "Commit status `deploy/preview` is failure.")

    def test_pending_commit_status(self):
        routes = passing_routes()
        routes[f"/repos/{REPO}/commits/{HEAD}/status"]["statuses"] = [{"context": "deploy/preview", "state": "pending"}]
        self.assert_refused(routes, "Commit status `deploy/preview` is pending.")

    def test_no_checks_reported_yet(self):
        routes = passing_routes()
        routes[f"/repos/{REPO}/commits/{HEAD}/check-runs"] = [{"name": "auto-merge-gate", "status": "in_progress", "conclusion": None}]
        self.assert_refused(routes, "No checks have reported on the head commit yet.")

    def test_codex_not_yet_on_head(self):
        routes = passing_routes()
        routes[f"/repos/{REPO}/issues/7/comments"] = [codex_comment(sha=OLD)]
        self.assert_refused(routes, f"Codex has not reviewed head {HEAD[:7]} yet (its last code review covered {OLD[:7]}).")

    def test_codex_never_commented(self):
        routes = passing_routes()
        routes[f"/repos/{REPO}/issues/7/comments"] = []
        self.assert_refused(routes, "no Codex review summary")

    def test_codex_review_still_running(self):
        routes = passing_routes()
        routes[f"/repos/{REPO}/issues/7/comments"] = [codex_comment(status="in_progress")]
        self.assert_refused(routes, "is in_progress, not completed")

    def test_codex_open_findings(self):
        routes = passing_routes()
        routes[f"/repos/{REPO}/issues/7/comments"] = [codex_comment(unresolved=True)]
        self.assert_refused(routes, f"Codex code review on {HEAD[:7]} left unresolved findings.")

    def test_codex_findings_unknown(self):
        routes = passing_routes()
        routes[f"/repos/{REPO}/issues/7/comments"] = [codex_comment(unresolved=None)]
        self.assert_refused(routes, "did not report has_unresolved_findings: false")

    def test_codex_open_security_findings(self):
        routes = passing_routes()
        routes[f"/repos/{REPO}/issues/7/comments"] = [codex_comment(security_unresolved=True)]
        self.assert_refused(routes, "Codex security review")

    def test_codex_state_from_someone_else_is_ignored(self):
        routes = passing_routes()
        forged = codex_comment()
        forged["user"] = {"login": "someone"}
        routes[f"/repos/{REPO}/issues/7/comments"] = [forged]
        self.assert_refused(routes, "no Codex review summary")

    def test_latest_codex_summary_wins(self):
        routes = passing_routes()
        routes[f"/repos/{REPO}/issues/7/comments"] = [
            codex_comment(unresolved=True, updated="2026-11-01T12:00:00Z"),
            codex_comment(unresolved=False, updated="2026-11-01T09:00:00Z"),
        ]
        self.assert_refused(routes, "left unresolved findings")

    def test_not_mergeable(self):
        routes = passing_routes()
        routes[f"/repos/{REPO}/pulls/7"].update(mergeable=False, mergeable_state="dirty")
        self.assert_refused(routes, "not mergeable (mergeable_state: dirty)")

    def test_mergeable_still_computing(self):
        routes = passing_routes()
        routes[f"/repos/{REPO}/pulls/7"]["mergeable"] = None
        self.assert_refused(routes, "still computing")

    def test_lists_every_unmet_condition(self):
        routes = passing_routes()
        routes[f"/repos/{REPO}/commits/{HEAD}/check-runs"][1]["conclusion"] = "failure"
        routes[f"/repos/{REPO}/issues/7/comments"] = [codex_comment(unresolved=True)]
        routes[f"/repos/{REPO}/pulls/7"]["mergeable"] = False
        body = self.assert_refused(routes, "finished as failure")
        self.assertIn("left unresolved findings", body)
        self.assertIn("not mergeable", body)


class RefusalCommentOncePerHead(Base):
    def failing_routes(self):
        routes = passing_routes()
        routes[f"/repos/{REPO}/commits/{HEAD}/check-runs"][1]["conclusion"] = "failure"
        return routes

    def test_same_reasons_same_head_posts_nothing(self):
        routes = self.failing_routes()
        d = self.evaluate(routes)
        routes[f"/repos/{REPO}/issues/7/comments"].append(
            {"id": 55, "user": {"login": "github-actions[bot]"}, "body": gate.refusal_body(d)})
        gh = FakeGitHub(routes)
        gate.run_plan(gh, CFG, "pull_request_target", {"pull_request": {"number": 7}})
        self.assertEqual(gh.writes(), [])

    def test_changed_reasons_edit_the_one_comment(self):
        routes = self.failing_routes()
        routes[f"/repos/{REPO}/issues/7/comments"].append(
            {"id": 55, "user": {"login": "github-actions[bot]"},
             "body": f"<!-- auto-merge-gate:v1 head={HEAD} -->\nolder reasons"})
        gh = FakeGitHub(routes)
        gate.run_plan(gh, CFG, "pull_request_target", {"pull_request": {"number": 7}})
        writes = gh.writes()
        self.assertEqual(len(writes), 1)
        self.assertEqual(writes[0][:2], ("PATCH", f"/repos/{REPO}/issues/comments/55"))
        self.assertIn("finished as failure", writes[0][2]["body"])

    def test_new_head_gets_a_new_comment(self):
        routes = self.failing_routes()
        routes[f"/repos/{REPO}/issues/7/comments"].append(
            {"id": 55, "user": {"login": "github-actions[bot]"},
             "body": f"<!-- auto-merge-gate:v1 head={OLD} -->\nold head"})
        self.assert_refused(routes, "finished as failure")

    def test_marker_from_another_author_does_not_silence_the_gate(self):
        routes = self.failing_routes()
        d = self.evaluate(routes)
        routes[f"/repos/{REPO}/issues/7/comments"].append(
            {"id": 56, "user": {"login": "someone"}, "body": gate.refusal_body(d)})
        self.assert_refused(routes, "finished as failure")


class Merges(Base):
    def test_merge_case(self):
        routes = passing_routes()
        reader = FakeGitHub(routes)
        merger = FakeGitHub({}, put_result={"sha": "c" * 40, "merged": True})

        ready = gate.run_plan(reader, CFG, "pull_request_target", {"pull_request": {"number": 7}})
        self.assertEqual(ready, [7])
        self.assertEqual(reader.writes(), [], "a passing pull request gets no refusal comment")

        merged = gate.run_merge(reader, merger, CFG, ready)
        self.assertEqual(merged, ["c" * 40])

        self.assertEqual(merger.calls, [
            ("PUT", f"/repos/{REPO}/pulls/7/merge", {"merge_method": "squash", "sha": HEAD}),
        ])
        self.assertFalse([c for c in reader.calls if c[0] == "PUT"], "the workflow token never merges")
        writes = reader.writes()
        self.assertEqual(writes[0], ("POST", f"/repos/{REPO}/issues/126/labels", {"labels": ["done"]}))
        self.assertEqual(writes[1][:2], ("POST", f"/repos/{REPO}/issues/126/comments"))
        self.assertIn("c" * 40, writes[1][2]["body"])
        self.assertEqual(len(writes), 2)

    def test_merge_step_rechecks_and_refuses_if_head_changed(self):
        routes = passing_routes()
        routes[f"/repos/{REPO}/issues/7/comments"] = [codex_comment(sha=OLD)]
        reader = FakeGitHub(routes)
        merger = FakeGitHub({}, put_result={"sha": "c" * 40})
        self.assertEqual(gate.run_merge(reader, merger, CFG, [7]), [])
        self.assertEqual(merger.calls, [])
        self.assertEqual(reader.writes()[0][:2], ("POST", f"/repos/{REPO}/issues/7/comments"))

    def test_github_refuses_the_merge(self):
        routes = passing_routes()
        reader = FakeGitHub(routes)
        merger = FakeGitHub({}, put_error=gate.GitHubError(409, "Head branch was modified. Review and try the merge again."))
        self.assertEqual(gate.run_merge(reader, merger, CFG, [7]), [])
        writes = reader.writes()
        self.assertEqual(len(writes), 1)
        self.assertEqual(writes[0][:2], ("POST", f"/repos/{REPO}/issues/7/comments"))
        self.assertIn("Head branch was modified", writes[0][2]["body"])

    def test_excluded_repository_is_never_touched(self):
        cfg = gate.Config(repo="ExpertPartners/Ember")
        reader = FakeGitHub(passing_routes())
        merger = FakeGitHub({}, put_result={"sha": "c" * 40})
        self.assertEqual(gate.run_plan(reader, cfg, "schedule", {}), [])
        self.assertEqual(gate.run_merge(reader, merger, cfg, [7]), [])
        self.assertEqual(reader.calls, [])
        self.assertEqual(merger.calls, [])


class Targets(unittest.TestCase):
    def test_pull_request_events_target_their_pull_request(self):
        gh = FakeGitHub({})
        for name in ("pull_request_target", "pull_request", "pull_request_review"):
            self.assertEqual(gate.target_prs(gh, CFG, name, {"pull_request": {"number": 9}}), [9])

    def test_issue_comment_on_an_issue_is_ignored(self):
        gh = FakeGitHub({})
        self.assertEqual(gate.target_prs(gh, CFG, "issue_comment", {"issue": {"number": 4}}), [])
        self.assertEqual(gate.target_prs(gh, CFG, "issue_comment", {"issue": {"number": 4, "pull_request": {}}}), [4])

    def test_dispatch_with_number(self):
        self.assertEqual(gate.target_prs(FakeGitHub({}), CFG, "workflow_dispatch", {}, " 12 "), [12])

    def test_schedule_and_check_suite_sweep_open_factory_pull_requests(self):
        gh = FakeGitHub({f"/repos/{REPO}/pulls": [
            {"number": 1, "draft": False, "user": {"login": "factory-droid[bot]"}},
            {"number": 2, "draft": True, "user": {"login": "factory-droid[bot]"}},
            {"number": 3, "draft": False, "user": {"login": "AllisonGaddy"}},
        ]})
        for name in ("schedule", "check_suite", "workflow_dispatch"):
            self.assertEqual(gate.target_prs(gh, CFG, name, {}), [1])

    def test_api_error_is_reported_not_swallowed(self):
        errors = []
        gate.run_plan(FakeGitHub({}), CFG, "pull_request_target", {"pull_request": {"number": 7}}, "", errors)
        self.assertEqual(len(errors), 1)


class CodexParsing(unittest.TestCase):
    def test_reads_the_real_summary_shape(self):
        body = (
            "<!-- codex-pull-request-review-summary -->\n"
            '<!-- codex-review-state:v1 {"code_review":{"commit_sha":"8562c853f24363c01944ab8b1d0d3ea1f7599445",'
            '"has_any_findings":true,"has_unresolved_findings":true,"status":"completed"},"security_review":'
            '{"commit_sha":"8562c853f24363c01944ab8b1d0d3ea1f7599445","has_any_findings":null,'
            '"has_unresolved_findings":null,"status":"completed"}} -->\n'
            '<!-- codex-security-review:v1 {"headSha":"8562c853f24363c01944ab8b1d0d3ea1f7599445"} -->\n'
            "## Codex Review Summary\n"
        )
        state = gate.latest_codex_state([{"user": {"login": "chatgpt-codex-connector[bot]"}, "body": body}])
        self.assertEqual(state["code_review"]["commit_sha"], "8562c853f24363c01944ab8b1d0d3ea1f7599445")
        self.assertIs(state["code_review"]["has_unresolved_findings"], True)

    def test_job_issue_number(self):
        self.assertEqual(gate.job_issue_number("Closes #126\nmore"), 126)
        self.assertIsNone(gate.job_issue_number("Fixes #126"))
        self.assertIsNone(gate.job_issue_number(None))


def codex_receipt(sha=HEAD, clean=True, security=False, login="chatgpt-codex-connector[bot]", created="2026-11-02T23:18:09Z"):
    """The receipt shapes Codex posts on a pull request, copied from pull request #145."""
    if security:
        middle = (
            "### \U0001f6e1\ufe0f Codex Security Review \u00b7 _Automatically triggered_\n\n"
            "Security review completed. No security issues were found in this pull request.\n"
        )
    elif clean:
        middle = "Codex Review: Didn't find any major issues. More of your lovely PRs please.\n"
    else:
        middle = "### \U0001f4a1 Codex Review\n\nHere are some automated review suggestions for this pull request.\n"
    body = (
        "<!-- codex-review-receipt:v1 -->\n\n"
        f"{middle}\n"
        f"**Reviewed commit:** `{sha[:10]}`\n\n"
        "<details> <summary>\u2139\ufe0f About Codex in GitHub</summary>\n<br/>\n</details>"
    )
    return {"id": 901, "user": {"login": login}, "body": body, "created_at": created, "updated_at": created}


class CodexReceipt(Base):
    """Codex posts a codex-review-receipt:v1 comment, not a summary, when its code review is clean."""

    # What the fake GraphQL thread read returns: a count, an exception to raise, or None for no reader.
    threads = 0

    def fake(self, routes):
        gh = FakeGitHub(routes)
        threads = self.threads
        if threads is None:
            return gh

        def unresolved_threads(repo, n):
            if isinstance(threads, Exception):
                raise threads
            return threads

        gh.unresolved_threads = unresolved_threads
        return gh

    def receipt_routes(self, *comments):
        routes = passing_routes()
        routes[f"/repos/{REPO}/issues/7/comments"] = list(comments)
        routes[f"/repos/{REPO}/pulls/7/reviews"] = []
        return routes

    def test_clean_receipt_for_head_merges(self):
        reader = self.fake(self.receipt_routes(codex_receipt()))
        merger = FakeGitHub({}, put_result={"sha": "c" * 40, "merged": True})
        ready = gate.run_plan(reader, CFG, "pull_request_target", {"pull_request": {"number": 7}})
        self.assertEqual(ready, [7])
        self.assertEqual(reader.writes(), [], "a passing pull request gets no refusal comment")
        self.assertEqual(gate.run_merge(reader, merger, CFG, ready), ["c" * 40])
        self.assertEqual(merger.calls, [
            ("PUT", f"/repos/{REPO}/pulls/7/merge", {"merge_method": "squash", "sha": HEAD}),
        ])

    def test_clean_receipt_for_head_beats_a_summary_on_an_older_commit(self):
        routes = self.receipt_routes(codex_comment(sha=OLD, unresolved=True), codex_receipt())
        self.assertEqual(self.evaluate(routes).action, "merge")

    def test_clean_receipt_with_the_full_sha_counts(self):
        receipt = codex_receipt()
        receipt["body"] = receipt["body"].replace(f"`{HEAD[:10]}`", f"`{HEAD}`")
        self.assertEqual(self.evaluate(self.receipt_routes(receipt)).action, "merge")

    def test_clean_receipt_with_a_curly_apostrophe_counts(self):
        receipt = codex_receipt()
        receipt["body"] = receipt["body"].replace("Didn't", "Didn\u2019t")
        self.assertEqual(self.evaluate(self.receipt_routes(receipt)).action, "merge")

    def test_clean_receipt_for_an_older_commit_refuses(self):
        self.assert_refused(self.receipt_routes(codex_receipt(sha=OLD)), f"Codex has not reviewed head {HEAD[:7]} yet")

    def test_older_receipt_does_not_count_for_a_new_head_after_a_summary_on_the_old_one(self):
        routes = self.receipt_routes(codex_comment(sha=OLD), codex_receipt(sha=OLD))
        self.assert_refused(routes, f"its last code review covered {OLD[:7]}")

    def test_security_only_receipt_refuses(self):
        self.assert_refused(self.receipt_routes(codex_receipt(security=True)), "no Codex review summary")

    def test_receipt_with_suggestions_refuses(self):
        self.assert_refused(self.receipt_routes(codex_receipt(clean=False)), "no Codex review summary")

    def test_receipt_from_someone_else_refuses(self):
        self.assert_refused(self.receipt_routes(codex_receipt(login="someone")), "no Codex review summary")

    def test_receipt_without_a_reviewed_commit_refuses(self):
        receipt = codex_receipt()
        receipt["body"] = receipt["body"].replace(f"**Reviewed commit:** `{HEAD[:10]}`", "")
        self.assert_refused(self.receipt_routes(receipt), "no Codex review summary")

    def test_a_summary_on_this_head_still_decides(self):
        routes = self.receipt_routes(codex_comment(unresolved=True), codex_receipt())
        self.assert_refused(routes, f"Codex code review on {HEAD[:7]} left unresolved findings.")

    def test_a_summary_on_this_head_with_null_findings_still_reads_threads(self):
        state = codex_comment()
        state["body"] = state["body"].replace('"has_unresolved_findings":false', '"has_unresolved_findings":null').replace('"has_any_findings":false', '"has_any_findings":true')
        routes = self.receipt_routes(state, codex_receipt())
        routes[f"/repos/{REPO}/pulls/7/reviews"] = []
        reader = FakeGitHub(routes)
        reader.unresolved_threads = lambda repo, n: 1
        d = gate.evaluate(reader, CFG, 7)
        self.assertEqual(d.action, "refuse")
        self.assertTrue(any("1 unresolved review thread" in r for r in d.reasons))

    def test_security_findings_on_head_still_block_a_clean_receipt(self):
        routes = self.receipt_routes(codex_comment(sha=OLD), codex_receipt())
        state = routes[f"/repos/{REPO}/issues/7/comments"][0]
        state["body"] = state["body"].replace(
            f'"security_review":{{"commit_sha":"{OLD}","has_any_findings":null,"has_unresolved_findings":null',
            f'"security_review":{{"commit_sha":"{HEAD}","has_any_findings":true,"has_unresolved_findings":true')
        self.assert_refused(routes, "Codex security review")

    def test_clean_receipt_still_needs_green_checks(self):
        routes = self.receipt_routes(codex_receipt())
        routes[f"/repos/{REPO}/commits/{HEAD}/check-runs"][1]["conclusion"] = "failure"
        self.assert_refused(routes, "finished as failure")

    def test_clean_receipt_still_needs_mergeable(self):
        routes = self.receipt_routes(codex_receipt())
        routes[f"/repos/{REPO}/pulls/7"].update(mergeable=False, mergeable_state="dirty")
        self.assert_refused(routes, "not mergeable")

    def test_reads_the_real_receipt_shape(self):
        head = "42b26d90b13bf57d8b7fdde0fd15c31d3d808308"
        body = (
            "<!-- codex-review-receipt:v1 -->\n\n"
            "Codex Review: Didn't find any major issues. More of your lovely PRs please.\n\n"
            "**Reviewed commit:** `42b26d90b1`\n\n"
            "<details> <summary>\u2139\ufe0f About Codex in GitHub</summary>\n<br/>\n\n"
            "[Your team has set up Codex to review pull requests in this repo](https://chatgpt.com/codex/cloud/settings/general).\n"
            "</details>"
        )
        comments = [{"user": {"login": "chatgpt-codex-connector[bot]"}, "body": body}]
        self.assertTrue(gate.has_clean_codex_receipt(comments, head))
        self.assertFalse(gate.has_clean_codex_receipt(comments, "42b26d90b2" + head[10:]))
        self.assertEqual(gate.codex_problems(None, head, lambda: 0, True), [])

    def test_clean_receipt_with_an_open_thread_refuses(self):
        self.threads = 1
        self.assert_refused(self.receipt_routes(codex_receipt()),
                            f"Codex posted a clean code review receipt for {HEAD[:7]}, but 1 review thread(s) are still unresolved.")

    def test_clean_receipt_does_not_wave_through_open_findings_from_an_older_commit(self):
        # Codex left a finding on OLD, then posted a clean receipt for HEAD before
        # refreshing its summary. The finding's thread is still open.
        self.threads = 1
        routes = self.receipt_routes(codex_comment(sha=OLD, unresolved=True), codex_receipt())
        self.assert_refused(routes, "1 review thread(s) are still unresolved")

    def test_clean_receipt_counts_once_older_findings_are_resolved(self):
        routes = self.receipt_routes(codex_comment(sha=OLD, unresolved=True), codex_receipt())
        self.assertEqual(self.evaluate(routes).action, "merge")

    def test_clean_receipt_when_threads_cannot_be_read_refuses(self):
        self.threads = gate.GitHubError(502, "down")
        self.assert_refused(self.receipt_routes(codex_receipt()), "but the review threads could not be read (down).")

    def test_clean_receipt_without_a_thread_reader_refuses(self):
        self.threads = None
        self.assert_refused(self.receipt_routes(codex_receipt()), "but the review threads could not be checked.")

    def test_codex_findings_on_this_head_block_a_clean_receipt(self):
        routes = self.receipt_routes(codex_receipt())
        routes[f"/repos/{REPO}/pulls/7/reviews"] = [
            {"id": 2, "user": {"login": "chatgpt-codex-connector[bot]"}, "commit_id": HEAD}]
        routes[f"/repos/{REPO}/pulls/7/reviews/2/comments"] = [{"id": 21}]
        self.assert_refused(routes, "1 review thread(s) are still unresolved")

    def test_receipt_naming_fewer_than_10_hex_refuses(self):
        for length in (7, 9):
            receipt = codex_receipt()
            receipt["body"] = receipt["body"].replace(f"`{HEAD[:10]}`", f"`{HEAD[:length]}`")
            self.assertFalse(gate.has_clean_codex_receipt([receipt], HEAD), length)
            self.assertEqual(self.evaluate(self.receipt_routes(receipt)).action, "refuse", length)

    def test_receipt_naming_a_sha_that_is_not_a_prefix_refuses(self):
        receipt = codex_receipt()
        receipt["body"] = receipt["body"].replace(f"`{HEAD[:10]}`", f"`{HEAD[:9]}b`")
        self.assert_refused(self.receipt_routes(receipt), "no Codex review summary")

    def test_security_findings_on_head_are_reported_with_an_open_thread(self):
        self.threads = 1
        routes = self.receipt_routes(codex_comment(sha=OLD), codex_receipt())
        state = routes[f"/repos/{REPO}/issues/7/comments"][0]
        state["body"] = state["body"].replace(
            f'"security_review":{{"commit_sha":"{OLD}","has_any_findings":null,"has_unresolved_findings":null',
            f'"security_review":{{"commit_sha":"{HEAD}","has_any_findings":true,"has_unresolved_findings":true')
        body = self.assert_refused(routes, "1 review thread(s) are still unresolved")
        self.assertIn("Codex security review", body)



LCFG = gate.Config(repo=REPO, merge_label="auto-merge")


def labelled_routes(number=7, author="AllisonGaddy", labels=("auto-merge",)):
    routes = passing_routes(number)
    pr = routes[f"/repos/{REPO}/pulls/{number}"]
    pr["user"] = {"login": author}
    pr["body"] = "Job 100052. Prompt Builder."
    pr["labels"] = [{"name": n} for n in labels]
    return routes


class LabelRoute(unittest.TestCase):
    """Repos whose builders push as a person mark finished work with a label."""

    def test_labelled_pull_request_by_a_person_merges(self):
        reader = FakeGitHub(labelled_routes())
        merger = FakeGitHub({}, put_result={"sha": "c" * 40, "merged": True})
        ready = gate.run_plan(reader, LCFG, "pull_request_target", {"pull_request": {"number": 7}})
        self.assertEqual(ready, [7])
        merged = gate.run_merge(reader, merger, LCFG, ready)
        self.assertEqual(merged, ["c" * 40])
        self.assertEqual(reader.writes(), [], "no job issue, so nothing is labeled or commented")

    def test_unlabelled_pull_request_by_a_person_is_left_alone(self):
        d = gate.evaluate(FakeGitHub(labelled_routes(labels=())), LCFG, 7)
        self.assertEqual(d.action, "skip")
        self.assertIn("auto-merge label", d.reasons[0])

    def test_label_is_ignored_when_the_repo_sets_no_label(self):
        d = gate.evaluate(FakeGitHub(labelled_routes()), CFG, 7)
        self.assertEqual(d.action, "skip")

    def test_labelled_still_needs_codex_on_head(self):
        routes = labelled_routes()
        routes[f"/repos/{REPO}/issues/7/comments"] = [codex_comment(sha=OLD)]
        d = gate.evaluate(FakeGitHub(routes), LCFG, 7)
        self.assertEqual(d.action, "refuse")
        self.assertTrue(any("Codex has not reviewed head" in r for r in d.reasons))

    def test_labelled_still_needs_green_checks(self):
        routes = labelled_routes()
        routes[f"/repos/{REPO}/commits/{HEAD}/check-runs"][0]["conclusion"] = "failure"
        d = gate.evaluate(FakeGitHub(routes), LCFG, 7)
        self.assertEqual(d.action, "refuse")

    def test_labelled_draft_is_left_alone(self):
        routes = labelled_routes()
        routes[f"/repos/{REPO}/pulls/7"]["draft"] = True
        self.assertEqual(gate.evaluate(FakeGitHub(routes), LCFG, 7).action, "skip")

    def test_sweep_includes_labelled_pull_requests(self):
        routes = labelled_routes()
        routes[f"/repos/{REPO}/pulls"] = [
            {"number": 7, "draft": False, "user": {"login": "AllisonGaddy"}, "labels": [{"name": "auto-merge"}]},
            {"number": 8, "draft": False, "user": {"login": "AllisonGaddy"}, "labels": []},
            {"number": 9, "draft": True, "user": {"login": "AllisonGaddy"}, "labels": [{"name": "auto-merge"}]},
        ]
        self.assertEqual(gate.target_prs(FakeGitHub(routes), LCFG, "schedule", {}), [7])

    def test_ember_is_excluded_even_with_the_label(self):
        cfg = gate.Config(repo="ExpertPartners/ember", merge_label="auto-merge")
        self.assertEqual(gate.run_plan(FakeGitHub({}), cfg, "schedule", {}), [])


class ResolvedThreadsRoute(unittest.TestCase):
    """Codex reports null, not false, once a pull request has ever had findings."""

    def _state(self, unresolved=None, any_findings=True, sha=HEAD, status="completed"):
        return {"code_review": {"commit_sha": sha, "has_any_findings": any_findings,
                                "has_unresolved_findings": unresolved, "status": status},
                "security_review": {}}

    def test_null_with_all_threads_resolved_passes(self):
        self.assertEqual(gate.codex_problems(self._state(), HEAD, lambda: 0), [])

    def test_null_with_an_open_thread_refuses(self):
        p = gate.codex_problems(self._state(), HEAD, lambda: 2)
        self.assertTrue(p and "2 unresolved review thread" in p[0])

    def test_null_without_a_thread_reader_refuses(self):
        p = gate.codex_problems(self._state(), HEAD, None)
        self.assertTrue(p and "did not report has_unresolved_findings: false" in p[0])

    def test_null_when_threads_cannot_be_read_refuses(self):
        def boom():
            raise gate.GitHubError(502, "down")
        p = gate.codex_problems(self._state(), HEAD, boom)
        self.assertEqual(len(p), 1)
        self.assertIn("could not be read", p[0])

    def test_true_still_refuses_even_with_threads_resolved(self):
        p = gate.codex_problems(self._state(unresolved=True), HEAD, lambda: 0)
        self.assertTrue(p and "left unresolved findings" in p[0])

    def test_null_without_any_findings_still_refuses(self):
        p = gate.codex_problems(self._state(any_findings=None), HEAD, lambda: 0)
        self.assertTrue(p and "did not report" in p[0])

    def test_null_on_an_older_head_still_waits(self):
        p = gate.codex_problems(self._state(sha=OLD), HEAD, lambda: 0)
        self.assertTrue(p and "has not reviewed head" in p[0])

    def test_null_while_review_running_refuses(self):
        p = gate.codex_problems(self._state(status="running"), HEAD, lambda: 0)
        self.assertTrue(p and "not completed" in p[0])

    def test_evaluate_reads_threads_only_when_needed(self):
        routes = passing_routes()
        reader = FakeGitHub(routes)
        calls = []
        reader.unresolved_threads = lambda repo, n: calls.append(n) or 0
        self.assertEqual(gate.evaluate(reader, CFG, 7).action, "merge")
        self.assertEqual(calls, [], "a false state never needs the thread read")
        routes[f"/repos/{REPO}/issues/7/comments"] = [codex_comment()]
        state_comment = routes[f"/repos/{REPO}/issues/7/comments"][0]
        state_comment["body"] = state_comment["body"].replace('"has_unresolved_findings":false', '"has_unresolved_findings":null').replace('"has_any_findings":false', '"has_any_findings":true')
        routes[f"/repos/{REPO}/pulls/7/reviews"] = []
        reader = FakeGitHub(routes)
        reader.unresolved_threads = lambda repo, n: calls.append(n) or 0
        self.assertEqual(gate.evaluate(reader, CFG, 7).action, "merge")
        self.assertEqual(calls, [7])


class LabelFallbackAndHeadFindings(unittest.TestCase):
    def test_labelled_factory_pr_with_a_non_job_issue_uses_the_label_route(self):
        routes = labelled_routes(author="factory-droid[bot]")
        routes[f"/repos/{REPO}/pulls/7"]["body"] = "Closes #126\n\nwork"
        routes[f"/repos/{REPO}/issues/126"]["labels"] = []
        d = gate.evaluate(FakeGitHub(routes), LCFG, 7)
        self.assertEqual(d.action, "merge")
        self.assertIsNone(d.issue)

    def test_labelled_factory_pr_whose_issue_cannot_be_read_waits(self):
        routes = labelled_routes(author="factory-droid[bot]")
        routes[f"/repos/{REPO}/pulls/7"]["body"] = "Closes #126\n\nwork"
        del routes[f"/repos/{REPO}/issues/126"]
        with self.assertRaises(gate.GitHubError):
            gate.evaluate(FakeGitHub(routes), LCFG, 7)
        errors = []
        ready = gate.run_plan(FakeGitHub(routes), LCFG, "pull_request_target", {"pull_request": {"number": 7}}, errors=errors)
        self.assertEqual(ready, [])
        self.assertEqual(len(errors), 1, "the failed read fails the run")

    def test_unlabelled_factory_pr_with_a_non_job_issue_is_still_skipped(self):
        routes = passing_routes()
        routes[f"/repos/{REPO}/issues/126"]["labels"] = []
        self.assertEqual(gate.evaluate(FakeGitHub(routes), LCFG, 7).action, "skip")

    def _null_routes(self):
        routes = passing_routes()
        c = routes[f"/repos/{REPO}/issues/7/comments"][0]
        c["body"] = c["body"].replace('"has_unresolved_findings":false', '"has_unresolved_findings":null').replace('"has_any_findings":false', '"has_any_findings":true')
        routes[f"/repos/{REPO}/pulls/7/reviews"] = [
            {"id": 1, "user": {"login": "chatgpt-codex-connector[bot]"}, "commit_id": OLD},
        ]
        routes[f"/repos/{REPO}/pulls/7/reviews/1/comments"] = [{"id": 11}]
        return routes

    def test_findings_on_an_older_head_resolved_merges(self):
        reader = FakeGitHub(self._null_routes())
        reader.unresolved_threads = lambda repo, n: 0
        self.assertEqual(gate.evaluate(reader, CFG, 7).action, "merge")

    def test_findings_on_this_head_block_even_when_resolved(self):
        routes = self._null_routes()
        routes[f"/repos/{REPO}/pulls/7/reviews"].append(
            {"id": 2, "user": {"login": "chatgpt-codex-connector[bot]"}, "commit_id": HEAD})
        routes[f"/repos/{REPO}/pulls/7/reviews/2/comments"] = [{"id": 21}, {"id": 22}]
        reader = FakeGitHub(routes)
        reader.unresolved_threads = lambda repo, n: 0
        d = gate.evaluate(reader, CFG, 7)
        self.assertEqual(d.action, "refuse")
        self.assertTrue(any("2 unresolved review thread" in r for r in d.reasons))

    def test_a_clean_codex_review_on_this_head_does_not_block(self):
        routes = self._null_routes()
        routes[f"/repos/{REPO}/pulls/7/reviews"].append(
            {"id": 3, "user": {"login": "chatgpt-codex-connector[bot]"}, "commit_id": HEAD})
        routes[f"/repos/{REPO}/pulls/7/reviews/3/comments"] = []
        reader = FakeGitHub(routes)
        reader.unresolved_threads = lambda repo, n: 0
        self.assertEqual(gate.evaluate(reader, CFG, 7).action, "merge")


MERGE_BASE = "d" * 40
BASE_TIP = "e" * 40
MARKET = {"name": "expert-partners", "plugins": [
    {"name": "operating-doctrine", "source": "./plugins/operating-doctrine", "version": "2.78.0", "description": "d"},
    {"name": "brand-voice", "source": "./plugins/brand-voice", "description": "d", "version": "0.6.7"},
]}
MANIFEST = "plugins/brand-voice/.claude-plugin/plugin.json"
LOG = "plugins/operating-doctrine/CHANGELOG.md"
OLD_LOG = "## 2.78.0 - 2026-11-02\n\nNewest.\n## 2.77.0 - 2026-11-01\n\nOlder.\n"


def market(**versions):
    data = json.loads(json.dumps(MARKET))
    for p in data["plugins"]:
        if p["name"] in versions:
            p["version"] = versions[p["name"]]
    return json.dumps(data, indent=2) + "\n"


def manifest(version="0.6.7"):
    return json.dumps({"name": "brand-voice", "version": version}, indent=2) + "\n"


def content(text):
    raw = text if isinstance(text, bytes) else text.encode()
    return {"type": "file", "encoding": "base64", "content": base64.b64encode(raw).decode()}


def release_routes(files, before=None, after=None, routes=None):
    """files is a list of (filename, status). before and after map a path to its text
    at the merge base and at the head."""
    routes = routes or passing_routes()
    routes[f"/repos/{REPO}/pulls/7"]["base"]["sha"] = BASE_TIP
    routes[f"/repos/{REPO}/pulls/7/files"] = [{"filename": n, "status": s} for n, s in files]
    routes[f"/repos/{REPO}/compare/{BASE_TIP}...{HEAD}"] = {"merge_base_commit": {"sha": MERGE_BASE}}
    for ref, texts in ((MERGE_BASE, before or {}), (HEAD, after or {})):
        for path, text in texts.items():
            routes[f"/repos/{REPO}/contents/{path}?ref={ref}"] = content(text)
    return routes


class ReleaseFiles(Base):
    """Builders add a note in .changeset/; the release step on main owns versions and CHANGELOG tops."""

    def test_changeset_note_alone_merges_reading_only_the_note_and_the_marketplace(self):
        note_path = ".changeset/159-one-owner.md"
        routes = release_routes([(note_path, "added"), ("tools/release/release.py", "added")],
                                after={note_path: GOOD_NOTE})
        gh = FakeGitHub(routes)
        self.assertEqual(gate.evaluate(gh, CFG, 7).action, "merge")
        self.assertEqual(sorted(c[1] for c in gh.calls if "/contents/" in c[1] or "/compare/" in c[1]), [
            f"/repos/{REPO}/contents/.changeset/159-one-owner.md?ref={HEAD}",
            f"/repos/{REPO}/contents/.claude-plugin/marketplace.json?ref={HEAD}",
        ])

    def test_plugin_manifest_version_edit_refuses(self):
        routes = release_routes([(MANIFEST, "modified")], {MANIFEST: manifest()}, {MANIFEST: manifest("0.6.8")})
        self.assert_refused(routes, f"`{MANIFEST}` changes the brand-voice version from 0.6.7 to 0.6.8.")

    def test_marketplace_version_edit_refuses(self):
        path = ".claude-plugin/marketplace.json"
        routes = release_routes([(path, "modified")], {path: market()}, {path: market(**{"operating-doctrine": "2.79.0"})})
        body = self.assert_refused(routes, "changes the operating-doctrine version from 2.78.0 to 2.79.0")
        self.assertIn("add a note in `.changeset/` instead", body)

    def test_marketplace_edit_that_keeps_every_version_merges(self):
        path = ".claude-plugin/marketplace.json"
        after = market().replace('"description": "d"', '"description": "new words"', 1)
        routes = release_routes([(path, "modified")], {path: market()}, {path: after})
        self.assertEqual(self.evaluate(routes).action, "merge")

    def test_removing_a_version_counts_as_an_edit(self):
        after = json.dumps({"name": "brand-voice"}, indent=2) + "\n"
        routes = release_routes([(MANIFEST, "modified")], {MANIFEST: manifest()}, {MANIFEST: after})
        self.assert_refused(routes, "changes the brand-voice version from 0.6.7 to None")

    def test_a_new_plugin_may_carry_its_first_version(self):
        path = ".claude-plugin/marketplace.json"
        data = json.loads(market())
        data["plugins"].append({"name": "new-plugin", "source": "./plugins/new-plugin", "version": "0.1.0"})
        new_manifest = "plugins/new-plugin/.claude-plugin/plugin.json"
        routes = release_routes(
            [(path, "modified"), (new_manifest, "added")],
            {path: market()},
            {path: json.dumps(data, indent=2) + "\n", new_manifest: '{"name": "new-plugin", "version": "0.1.0"}\n'})
        self.assertEqual(self.evaluate(routes).action, "merge")

    def test_branch_cut_before_a_release_is_judged_against_its_merge_base(self):
        # main has since released 0.6.8, but the branch never touched the version.
        routes = release_routes([(MANIFEST, "modified")], {MANIFEST: manifest()},
                                {MANIFEST: json.dumps({"name": "brand-voice", "version": "0.6.7", "description": "x"}, indent=2) + "\n"})
        routes[f"/repos/{REPO}/contents/{MANIFEST}?ref={BASE_TIP}"] = content(manifest("0.6.8"))
        self.assertEqual(self.evaluate(routes).action, "merge")

    def test_new_changelog_entry_refuses(self):
        after = "## 2.79.0 - 2026-11-03\n\nBuilder wrote this.\n" + OLD_LOG
        routes = release_routes([(LOG, "modified")], {LOG: OLD_LOG}, {LOG: after})
        self.assert_refused(routes, f"`{LOG}` adds a CHANGELOG entry.")

    def test_editing_the_top_changelog_entry_refuses(self):
        routes = release_routes([(LOG, "modified")], {LOG: OLD_LOG}, {LOG: OLD_LOG.replace("Newest.", "Newest, edited.")})
        self.assert_refused(routes, f"`{LOG}` edits the top CHANGELOG entry.")

    def test_editing_an_older_changelog_entry_merges(self):
        routes = release_routes([(LOG, "modified")], {LOG: OLD_LOG}, {LOG: OLD_LOG.replace("Older.", "Older, corrected.")})
        self.assertEqual(self.evaluate(routes).action, "merge")

    def test_a_new_changelog_refuses(self):
        path = "plugins/brand-voice/CHANGELOG.md"
        routes = release_routes([(path, "added")], {}, {path: "## 0.6.8 - 2026-11-03\n\nX.\n"})
        self.assert_refused(routes, f"`{path}` is a new CHANGELOG.")

    def test_removed_files_are_not_version_edits(self):
        routes = release_routes([(LOG, "removed"), (MANIFEST, "removed")])
        self.assertEqual(self.evaluate(routes).action, "merge")

    def test_invalid_json_refuses(self):
        routes = release_routes([(MANIFEST, "modified")], {MANIFEST: manifest()}, {MANIFEST: "{ not json"})
        self.assert_refused(routes, "is not valid JSON")

    def test_unreadable_file_fails_the_run_instead_of_merging(self):
        routes = release_routes([(MANIFEST, "modified")], {MANIFEST: manifest()}, {})
        errors = []
        self.assertEqual(gate.run_plan(FakeGitHub(routes), CFG, "pull_request_target",
                                       {"pull_request": {"number": 7}}, "", errors), [])
        self.assertEqual(len(errors), 1)

    def test_every_problem_is_listed_with_the_others(self):
        routes = release_routes([(MANIFEST, "modified"), (LOG, "modified")],
                                {MANIFEST: manifest(), LOG: OLD_LOG},
                                {MANIFEST: manifest("0.7.0"), LOG: "## 2.79.0 - x\n\nY.\n" + OLD_LOG})
        routes[f"/repos/{REPO}/commits/{HEAD}/check-runs"][1]["conclusion"] = "failure"
        body = self.assert_refused(routes, "changes the brand-voice version")
        self.assertIn("adds a CHANGELOG entry", body)
        self.assertIn("finished as failure", body)

    def test_label_route_is_held_to_the_same_rule(self):
        routes = release_routes([(MANIFEST, "modified")], {MANIFEST: manifest()}, {MANIFEST: manifest("0.6.8")},
                                routes=labelled_routes())
        d = gate.evaluate(FakeGitHub(routes), LCFG, 7)
        self.assertEqual(d.action, "refuse")
        self.assertTrue(any("changes the brand-voice version" in r for r in d.reasons))


class OddFileContent(Base):
    """A changed file the gate cannot judge refuses that pull request and never stops the run."""

    def assert_refused_in_the_run(self, routes, fragment):
        errors = []
        gh = FakeGitHub(routes)
        self.assertEqual(gate.run_plan(gh, CFG, "pull_request_target", {"pull_request": {"number": 7}}, "", errors), [])
        self.assertEqual(errors, [], "content problems are refusals, not run failures")
        self.assert_refused(routes, fragment)

    def test_manifest_that_is_a_json_list_refuses(self):
        routes = release_routes([(MANIFEST, "modified")], {MANIFEST: manifest()}, {MANIFEST: "[]\n"})
        self.assert_refused_in_the_run(routes, f"`{MANIFEST}` is not the JSON object it should be")

    def test_marketplace_that_is_json_null_refuses(self):
        path = ".claude-plugin/marketplace.json"
        routes = release_routes([(path, "modified")], {path: market()}, {path: "null\n"})
        self.assert_refused_in_the_run(routes, f"`{path}` is not the JSON object it should be")

    def test_marketplace_whose_plugins_is_not_a_list_refuses(self):
        path = ".claude-plugin/marketplace.json"
        routes = release_routes([(path, "modified")], {path: market()}, {path: '{"plugins": {"a": 1}}\n'})
        self.assert_refused_in_the_run(routes, f"`{path}` is not the JSON object it should be")

    def test_marketplace_plugin_with_an_odd_name_is_ignored(self):
        path = ".claude-plugin/marketplace.json"
        data = json.loads(market())
        data["plugins"].append({"name": ["not", "a", "name"], "version": "1.0.0"})
        routes = release_routes([(path, "modified")], {path: market()}, {path: json.dumps(data)})
        self.assertEqual(self.evaluate(routes).action, "merge")

    def test_changelog_that_is_not_utf8_refuses(self):
        routes = release_routes([(LOG, "modified")], {LOG: OLD_LOG}, {LOG: OLD_LOG.encode() + b"\xff\xfe"})
        self.assert_refused_in_the_run(routes, f"`{LOG}` at {HEAD[:7]} is not UTF-8 text")

    def test_changelog_that_is_a_symlink_refuses(self):
        routes = release_routes([(LOG, "modified")], {LOG: OLD_LOG})
        routes[f"/repos/{REPO}/contents/{LOG}?ref={HEAD}"] = {"type": "symlink", "target": "../x.md"}
        self.assert_refused_in_the_run(routes, f"`{LOG}` at {HEAD[:7]} is not a text file the gate can read")

    def test_one_odd_pull_request_does_not_stop_the_sweep(self):
        routes = release_routes([(MANIFEST, "modified")], {MANIFEST: manifest()}, {MANIFEST: "null"})
        for path, value in passing_routes(number=8, issue=127).items():
            routes.setdefault(path, value)
        routes[f"/repos/{REPO}/pulls"] = [
            {"number": n, "draft": False, "user": {"login": "factory-droid[bot]"}} for n in (7, 8)]
        errors = []
        gh = FakeGitHub(routes)
        self.assertEqual(gate.run_plan(gh, CFG, "schedule", {}, "", errors), [8])
        self.assertEqual(errors, [])
        self.assertEqual([c[1] for c in gh.writes()], [f"/repos/{REPO}/issues/7/comments"])


NOTE_PATH = ".changeset/170-x.md"


def note_routes(text, files=None, routes=None):
    files = files or [(NOTE_PATH, "added")]
    return release_routes(files, after={NOTE_PATH: text}, routes=routes)


class ChangesetNotes(Base):
    """A note the release step would refuse is refused before it can merge, so it never
    holds up every plugin's release on main."""

    def assert_note_refused(self, text, fragment):
        body = self.assert_refused(note_routes(text), f"`{NOTE_PATH}` {fragment}")
        self.assertIn("`.changeset/README.md` gives the format", body)

    def test_a_good_note_merges(self):
        self.assertEqual(self.evaluate(note_routes(GOOD_NOTE)).action, "merge")

    def test_a_note_naming_two_plugins_merges(self):
        text = '---\n"operating-doctrine": patch\nbrand-voice: MINOR\n---\n\nShared.\n'
        self.assertEqual(self.evaluate(note_routes(text)).action, "merge")

    def test_unknown_plugin_refuses(self):
        self.assert_note_refused("---\nno-such-plugin: patch\n---\n\nX.\n",
                                 "names no-such-plugin, which is not a plugin in `.claude-plugin/marketplace.json`")

    def test_bad_bump_refuses(self):
        self.assert_note_refused("---\nbrand-voice: feature\n---\n\nX.\n", "asks for 'feature' for brand-voice")

    def test_empty_text_refuses(self):
        self.assert_note_refused("---\nbrand-voice: patch\n---\n\n", "says nothing about the change")

    def test_missing_closing_line_refuses(self):
        self.assert_note_refused("---\nbrand-voice: patch\n\nX.\n", "has an opening --- with no closing ---")

    def test_missing_frontmatter_refuses(self):
        self.assert_note_refused("Just text.\n", "must start with a --- line")

    def test_no_plugin_named_refuses(self):
        self.assert_note_refused("---\n---\n\nX.\n", "names no plugin")

    def test_a_plugin_named_twice_refuses(self):
        self.assert_note_refused("---\nbrand-voice: patch\nbrand-voice: minor\n---\n\nX.\n", "names brand-voice twice")

    def test_an_unreadable_line_refuses(self):
        self.assert_note_refused("---\nbrand voice is patch\n---\n\nX.\n", "has a line it cannot read")

    def test_a_level_two_heading_in_the_text_refuses(self):
        self.assert_note_refused("---\nbrand-voice: patch\n---\n\nX.\n\n## Breaking changes\n\nY.\n",
                                 "has a `## ` heading in its text")

    def test_a_level_three_heading_in_the_text_merges(self):
        text = "---\nbrand-voice: patch\n---\n\nX.\n\n### Breaking changes\n\nY.\n"
        self.assertEqual(self.evaluate(note_routes(text)).action, "merge")

    def test_a_note_that_is_not_utf8_refuses_without_failing_the_run(self):
        routes = note_routes(b"---\nbrand-voice: patch\n---\n\n\xff\n")
        errors = []
        gate.run_plan(FakeGitHub(routes), CFG, "pull_request_target", {"pull_request": {"number": 7}}, "", errors)
        self.assertEqual(errors, [])
        self.assert_refused(routes, f"`{NOTE_PATH}` at {HEAD[:7]} is not UTF-8 text")

    def test_unreadable_marketplace_refuses(self):
        routes = note_routes(GOOD_NOTE)
        routes[f"/repos/{REPO}/contents/.claude-plugin/marketplace.json?ref={HEAD}"] = content("{ not json")
        self.assert_refused(routes, "`.claude-plugin/marketplace.json` is not valid JSON")

    def test_a_plugin_added_in_the_same_pull_request_is_known(self):
        path = ".claude-plugin/marketplace.json"
        data = json.loads(market())
        data["plugins"].append({"name": "new-plugin", "source": "./plugins/new-plugin", "version": "0.1.0"})
        routes = release_routes([(NOTE_PATH, "added"), (path, "modified")], {path: market()},
                                {path: json.dumps(data), NOTE_PATH: "---\nnew-plugin: minor\n---\n\nNew.\n"})
        self.assertEqual(self.evaluate(routes).action, "merge")

    def test_every_bad_note_is_listed(self):
        other = ".changeset/171-y.md"
        routes = release_routes([(NOTE_PATH, "added"), (other, "modified")],
                                after={NOTE_PATH: "Just text.\n", other: "---\nnope: patch\n---\n\nX.\n"})
        body = self.assert_refused(routes, f"`{NOTE_PATH}` must start with a --- line")
        self.assertIn(f"`{other}` names nope", body)

    def test_files_the_release_step_never_reads_are_not_read(self):
        files = [(".changeset/README.md", "modified"), (".changeset/readme.md", "added"),
                 (".changeset/sub/1-x.md", "added"), (".changeset/1-x.txt", "added"), (NOTE_PATH, "removed")]
        gh = FakeGitHub(release_routes(files))
        self.assertEqual(gate.evaluate(gh, CFG, 7).action, "merge")
        self.assertFalse([c for c in gh.calls if "/contents/" in c[1]])


RELEASE_PY = os.path.join(os.path.dirname(__file__), "..", "..", "release", "release.py")


@unittest.skipUnless(os.path.exists(RELEASE_PY), "tools/release/release.py is not in this checkout")
class NoteRulesMatchTheReleaseStep(unittest.TestCase):
    """The gate cannot import the release step, so both judge the same notes here."""

    NOTES = [
        GOOD_NOTE,
        '---\n"operating-doctrine": patch\n\'brand-voice\': "minor"\n---\n\nShared.\n',
        "---\r\nbrand-voice: patch\r\n---\r\n\r\nWindows line ends.\r\n",
        "---\rbrand-voice: patch\r---\r\rOld Mac line ends.\r",
        "  ---  \n# a comment\n\nbrand-voice:   major  \n ---\n\nSpaced.\n",
        "---\nbrand-voice: patch\n---\n\nX.\n\n### Fine heading\n",
        "---\nbrand-voice: patch\n---\n\n## Not fine\n",
        "---\nbrand-voice: patch\n---\n\nX.\n##no space is fine\n",
        "---\nbrand-voice: patch\n---\n\n   \n",
        "---\nbrand-voice: patch\n",
        "Just text.\n",
        "",
        "\ufeff---\nbrand-voice: patch\n---\n\nByte order mark.\n",
        "---\n---\n\nX.\n",
        "---\nbrand-voice: sideways\n---\n\nX.\n",
        "---\nbrand-voice: patch\nbrand-voice: patch\n---\n\nX.\n",
        "---\nbrand voice: patch\n---\n\nX.\n",
        "---\nbrand-voice:\n---\n\nX.\n",
    ]

    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("release_for_gate_tests", RELEASE_PY)
        cls.release = importlib.util.module_from_spec(spec)
        sys.modules["release_for_gate_tests"] = cls.release
        spec.loader.exec_module(cls.release)

    def test_same_verdict_and_same_plugins(self):
        for text in self.NOTES:
            with self.subTest(note=text):
                problem, names = gate.note_problem(text)
                try:
                    parsed = self.release.parse_note_text(Path("n.md"), text)
                except self.release.ReleaseError:
                    parsed = None
                self.assertEqual(problem is None, parsed is not None, problem)
                self.assertEqual(names, list(parsed.bumps) if parsed else [])


if __name__ == "__main__":
    unittest.main()
