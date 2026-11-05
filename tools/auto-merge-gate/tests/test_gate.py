"""Unit tests for the auto-merge gate. Every GitHub call goes to FakeGitHub; nothing touches the network.

Run from the repo root: python3 -m unittest discover -s tools/auto-merge-gate/tests -v
"""

import base64
import copy
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

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
        f"/repos/{REPO}/pulls/{number}/comments": [],
    }


def finding_comment(cid, severity="P2", sha=HEAD, security=False, login="chatgpt-codex-connector[bot]",
                    title="Parse global pip options before install", reply_to=None, badge=True):
    """An inline finding in the shape Codex posts, copied from pull requests #214 and #108."""
    mark = f"**<sub><sub>![{severity} Badge](https://img.shields.io/badge/{severity}-yellow?style=flat)</sub></sub>  " if badge else "**"
    if security:
        body = (
            "<!-- codex-security-review-finding:v1 -->\n\n"
            "### \U0001f6e1\ufe0f Codex Security Review \u00b7 _Automatically triggered_\n\n"
            f"{mark}Security: {title}**\n\nDetails.\n\nUseful? React with \U0001f44d / \U0001f44e."
        )
    else:
        body = f"{mark}{title}**\n\nDetails.\n\nUseful? React with \U0001f44d / \U0001f44e.\n\n<!-- codex-code-review-finding:v1 -->"
    return {
        "id": cid, "user": {"login": login}, "body": body, "commit_id": HEAD, "original_commit_id": sha,
        "in_reply_to_id": reply_to, "path": "tools/x.py",
        "html_url": f"https://github.com/{REPO}/pull/7#discussion_r{cid}",
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

    def test_codex_open_findings_it_cannot_find(self):
        routes = passing_routes()
        routes[f"/repos/{REPO}/issues/7/comments"] = [codex_comment(unresolved=True)]
        self.assert_refused(routes, f"Codex code review on {HEAD[:7]} reports unresolved findings, but the gate found no open Codex code finding comment")

    def test_codex_open_p1_finding(self):
        routes = passing_routes()
        routes[f"/repos/{REPO}/issues/7/comments"] = [codex_comment(unresolved=True)]
        routes[f"/repos/{REPO}/pulls/7/comments"] = [finding_comment(31, "P1")]
        self.assert_refused(routes, f"Codex P1 code finding \"Parse global pip options before install\" "
                                    f"(https://github.com/{REPO}/pull/7#discussion_r31) blocks: Codex raised it on head {HEAD[:7]}.")

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
        self.assert_refused(routes, "reports unresolved findings")

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
        self.assertIn("reports unresolved findings", body)
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

    # What the fake GraphQL thread read returns: {first comment id: resolved},
    # an exception to raise, or None for no reader.
    threads = {}

    def fake(self, routes):
        gh = FakeGitHub(routes)
        threads = self.threads
        if threads is None:
            return gh

        def review_threads(repo, n):
            if isinstance(threads, Exception):
                raise threads
            return threads

        gh.review_threads = review_threads
        return gh

    def receipt_routes(self, *comments, findings=()):
        routes = passing_routes()
        routes[f"/repos/{REPO}/issues/7/comments"] = list(comments)
        routes[f"/repos/{REPO}/pulls/7/comments"] = list(findings)
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
        self.assert_refused(routes, f"Codex code review on {HEAD[:7]} reports unresolved findings")

    def test_a_summary_on_this_head_with_null_findings_still_reads_threads(self):
        state = codex_comment()
        state["body"] = state["body"].replace('"has_unresolved_findings":false', '"has_unresolved_findings":null').replace('"has_any_findings":false', '"has_any_findings":true')
        routes = self.receipt_routes(state, codex_receipt(), findings=[finding_comment(41, "P1", sha=OLD)])
        reader = FakeGitHub(routes)
        reader.review_threads = lambda repo, n: {41: False}
        d = gate.evaluate(reader, CFG, 7)
        self.assertEqual(d.action, "refuse")
        self.assertTrue(any(f"its thread from {OLD[:7]} is unresolved" in r for r in d.reasons), d.reasons)

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
        self.assertEqual(gate.codex_problems(None, head, lambda: ([], None), True), [])

    def test_clean_receipt_with_an_open_p1_thread_refuses(self):
        self.threads = {41: False}
        routes = self.receipt_routes(codex_receipt(), findings=[finding_comment(41, "P1", sha=OLD)])
        self.assert_refused(routes, f"Codex P1 code finding \"Parse global pip options before install\" "
                                    f"(https://github.com/{REPO}/pull/7#discussion_r41) blocks: its thread from {OLD[:7]} is unresolved.")

    def test_clean_receipt_with_an_open_p2_thread_merges(self):
        self.threads = {41: False}
        routes = self.receipt_routes(codex_receipt(), findings=[finding_comment(41, "P2", sha=OLD)])
        self.assertEqual(self.evaluate(routes).action, "merge")

    def test_clean_receipt_does_not_wave_through_open_findings_from_an_older_commit(self):
        # Codex left a finding on OLD, then posted a clean receipt for HEAD before
        # refreshing its summary. The finding's thread is still open.
        self.threads = {41: False}
        routes = self.receipt_routes(codex_comment(sha=OLD, unresolved=True), codex_receipt(),
                                     findings=[finding_comment(41, "P1", sha=OLD)])
        self.assert_refused(routes, f"its thread from {OLD[:7]} is unresolved")

    def test_clean_receipt_counts_once_older_findings_are_resolved(self):
        self.threads = {41: True}
        routes = self.receipt_routes(codex_comment(sha=OLD, unresolved=True), codex_receipt(),
                                     findings=[finding_comment(41, "P1", sha=OLD)])
        self.assertEqual(self.evaluate(routes).action, "merge")

    def test_clean_receipt_when_threads_cannot_be_read_refuses(self):
        self.threads = gate.GitHubError(502, "down")
        routes = self.receipt_routes(codex_receipt(), findings=[finding_comment(41, "P1", sha=OLD)])
        self.assert_refused(routes, f"from {OLD[:7]} may still be open: the review threads could not be read (down).")

    def test_clean_receipt_without_a_thread_reader_refuses(self):
        self.threads = None
        routes = self.receipt_routes(codex_receipt(), findings=[finding_comment(41, "P1", sha=OLD)])
        self.assert_refused(routes, "may still be open: the review threads could not be checked.")

    def test_clean_receipt_when_review_comments_cannot_be_read_refuses(self):
        routes = self.receipt_routes(codex_receipt())
        del routes[f"/repos/{REPO}/pulls/7/comments"]
        self.assert_refused(routes, f"Codex posted a clean code review receipt for {HEAD[:7]}, but the review comments could not be read")

    def test_codex_findings_on_this_head_block_a_clean_receipt(self):
        routes = self.receipt_routes(codex_receipt(), findings=[finding_comment(21, "P1")])
        self.assert_refused(routes, f"blocks: Codex raised it on head {HEAD[:7]}.")

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
        self.threads = {41: False}
        routes = self.receipt_routes(codex_comment(sha=OLD), codex_receipt(), findings=[finding_comment(41, "P1", sha=OLD)])
        state = routes[f"/repos/{REPO}/issues/7/comments"][0]
        state["body"] = state["body"].replace(
            f'"security_review":{{"commit_sha":"{OLD}","has_any_findings":null,"has_unresolved_findings":null',
            f'"security_review":{{"commit_sha":"{HEAD}","has_any_findings":true,"has_unresolved_findings":true')
        body = self.assert_refused(routes, f"its thread from {OLD[:7]} is unresolved")
        self.assertIn("Codex security review", body)



LABEL_ACTOR = "AllisonGaddy"
LCFG = gate.Config(repo=REPO, merge_label="auto-merge", merge_label_actors=frozenset({LABEL_ACTOR}))
PUSHED_AT = "2026-11-05T17:12:26Z"
LABELLED_AT = "2026-11-05T19:30:00Z"


def label_event(event="labeled", actor=LABEL_ACTOR, at=LABELLED_AT, name="auto-merge"):
    """An issue event in the shape GET /repos/{repo}/issues/{n}/events returns."""
    return {"event": event, "actor": {"login": actor}, "created_at": at, "label": {"name": name}}


def push_activity(sha, ref, at=PUSHED_AT):
    """A repository activity entry in the shape GET /repos/{repo}/activity returns."""
    return {"after": sha, "ref": f"refs/heads/{ref}", "timestamp": at, "activity_type": "push", "actor": {"login": "AllisonGaddy"}}


def enroll(routes, number, sha, ref, events=None, pushed_at=PUSHED_AT):
    """An enrollment actor added the label after the push that made sha the head of ref."""
    routes[f"/repos/{REPO}/pulls/{number}"]["head"].update(ref=ref, repo={"full_name": REPO})
    routes[f"/repos/{REPO}/issues/{number}/events"] = events if events is not None else [
        {"event": "review_requested", "actor": {"login": "AllisonGaddy"}, "created_at": "2026-11-05T17:13:00Z"},
        label_event("labeled", name="needs-review", at="2026-11-05T17:14:00Z"),
        label_event(),
    ]
    routes[f"/repos/{REPO}/activity"] = [push_activity(sha, ref, pushed_at)]
    return routes


def labelled_routes(number=7, author="AllisonGaddy", labels=("auto-merge",)):
    routes = passing_routes(number)
    pr = routes[f"/repos/{REPO}/pulls/{number}"]
    pr["user"] = {"login": author}
    pr["body"] = "Job 100052. Prompt Builder."
    pr["labels"] = [{"name": n} for n in labels]
    return enroll(routes, number, HEAD, f"job/{number}")


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


class ParamsFake(FakeGitHub):
    """Also records the query parameters of each get."""

    def get(self, path, params=None):
        self.calls.append(("GET", path, params))
        return self._route(path)


class EnrollmentActor(unittest.TestCase):
    """The label counts only from an enrollment actor, and only for the head it was added on."""

    def assert_left_alone(self, routes, fragment, cfg=LCFG):
        gh = FakeGitHub(routes)
        merger = FakeGitHub({}, put_result={"sha": "c" * 40})
        self.assertEqual(gate.run_plan(gh, cfg, "pull_request_target", {"pull_request": {"number": 7}}), [])
        self.assertEqual(gate.run_merge(gh, merger, cfg, [7]), [])
        d = gate.evaluate(gh, cfg, 7)
        self.assertEqual(d.action, "skip")
        self.assertIn(fragment, d.reasons[0])
        self.assertEqual(gh.writes(), [], "a pull request that is not enrolled gets no comment")
        self.assertEqual(merger.calls, [])

    def assert_refused(self, routes, fragment):
        gh = FakeGitHub(routes)
        merger = FakeGitHub({}, put_result={"sha": "c" * 40})
        self.assertEqual(gate.run_plan(gh, LCFG, "pull_request_target", {"pull_request": {"number": 7}}), [])
        self.assertEqual(gate.run_merge(gh, merger, LCFG, [7]), [])
        self.assertEqual(merger.calls, [])
        d = gate.evaluate(gh, LCFG, 7)
        self.assertEqual(d.action, "refuse")
        self.assertTrue(any(fragment in r for r in d.reasons), d.reasons)
        posted = [w for w in gh.writes() if w[0] == "POST"]
        self.assertTrue(posted and fragment in posted[0][2]["body"], gh.writes())
        return d

    def test_an_enrollment_actor_label_after_the_push_merges(self):
        gh = ParamsFake(labelled_routes())
        self.assertEqual(gate.evaluate(gh, LCFG, 7).action, "merge")
        self.assertIn(("GET", f"/repos/{REPO}/activity", {"ref": "refs/heads/job/7", "direction": "desc", "per_page": 1}), gh.calls)

    def test_a_triage_user_cannot_enroll(self):
        routes = labelled_routes()
        routes[f"/repos/{REPO}/issues/7/events"] = [label_event(actor="triage-helper")]
        self.assertTrue(gate.Config(repo=REPO).merge_label_actors == frozenset())
        self.assertNotIn("triage-helper", LCFG.merge_label_actors)
        self.assert_left_alone(routes, "the auto-merge label was added by triage-helper, who is not an enrollment actor")

    def test_an_app_that_can_label_cannot_enroll(self):
        routes = labelled_routes()
        routes[f"/repos/{REPO}/issues/7/events"] = [label_event(actor="label-bot[bot]")]
        self.assert_left_alone(routes, "added by label-bot[bot], who is not an enrollment actor")

    def test_the_latest_labeled_event_decides(self):
        routes = labelled_routes()
        routes[f"/repos/{REPO}/issues/7/events"] = [
            label_event(at="2026-11-05T19:00:00Z"),
            label_event("unlabeled", actor="triage-helper", at="2026-11-05T19:10:00Z"),
            label_event(actor="triage-helper", at="2026-11-05T19:20:00Z"),
        ]
        self.assert_left_alone(routes, "added by triage-helper")

    def test_a_label_with_no_labeled_event_does_not_enroll(self):
        for events in ([], [label_event(), label_event("unlabeled", at="2026-11-05T19:40:00Z")]):
            with self.subTest(events=len(events)):
                routes = labelled_routes()
                routes[f"/repos/{REPO}/issues/7/events"] = events
                self.assert_left_alone(routes, "no labeled event for the auto-merge label was found")

    def test_no_configured_actor_means_no_enrollment(self):
        cfg = gate.Config(repo=REPO, merge_label="auto-merge")
        self.assert_left_alone(labelled_routes(), f"added by {LABEL_ACTOR}, who is not an enrollment actor", cfg)

    def test_actor_logins_compare_without_case(self):
        routes = labelled_routes()
        routes[f"/repos/{REPO}/issues/7/events"] = [label_event(actor="allisongaddy")]
        self.assertEqual(gate.evaluate(FakeGitHub(routes), LCFG, 7).action, "merge")

    def test_a_push_after_the_label_needs_a_fresh_label(self):
        routes = labelled_routes()
        routes[f"/repos/{REPO}/activity"] = [push_activity(HEAD, "job/7", "2026-11-05T19:45:00Z")]
        d = self.assert_refused(routes, f"{LABEL_ACTOR} added the auto-merge label at {LABELLED_AT}, before head {HEAD[:7]} was pushed at 2026-11-05T19:45:00Z. Remove the label and add it again to enroll this head.")
        self.assertEqual(len(d.reasons), 1, "every other condition still passes")
        relabelled = copy.deepcopy(routes)
        relabelled[f"/repos/{REPO}/issues/7/events"] += [
            label_event("unlabeled", at="2026-11-05T19:50:00Z"), label_event(at="2026-11-05T19:51:00Z"),
        ]
        self.assertEqual(gate.evaluate(FakeGitHub(relabelled), LCFG, 7).action, "merge")

    def test_a_label_in_the_same_second_as_the_push_does_not_count(self):
        routes = labelled_routes()
        routes[f"/repos/{REPO}/activity"] = [push_activity(HEAD, "job/7", LABELLED_AT)]
        self.assert_refused(routes, "Remove the label and add it again")

    def test_an_unseen_push_waits(self):
        for activity in ([], [push_activity(OLD, "job/7", "2026-11-05T19:45:00Z")]):
            with self.subTest(entries=len(activity)):
                routes = labelled_routes()
                routes[f"/repos/{REPO}/activity"] = activity
                self.assert_refused(routes, f"The gate cannot see the push that made {HEAD[:7]} the head of `job/7` yet.")

    def test_a_missing_timestamp_is_not_a_pass(self):
        routes = labelled_routes()
        routes[f"/repos/{REPO}/activity"][0]["timestamp"] = None
        self.assert_refused(routes, "was pushed at an unknown time")

    def test_a_fork_head_is_refused(self):
        for repo, shown in ({"full_name": "someone/fork"}, "someone/fork"), (None, "a deleted repository"):
            with self.subTest(shown):
                routes = labelled_routes()
                routes[f"/repos/{REPO}/pulls/7"]["head"]["repo"] = repo
                self.assert_refused(routes, f"enrolls only branches in {REPO}, where the gate can see each push, and this head is in {shown}.")

    def test_dependency_updates_are_never_enrolled(self):
        self.assert_left_alone(
            labelled_routes(author="dependabot[bot]"),
            "author is the app dependabot[bot], and the auto-merge label enrolls only work pushed by a person or Factory",
        )

    def test_a_factory_job_pull_request_does_not_read_label_events(self):
        routes = passing_routes()
        routes[f"/repos/{REPO}/pulls/7"]["labels"] = [{"name": "auto-merge"}]
        gh = FakeGitHub(routes)
        d = gate.evaluate(gh, LCFG, 7)
        self.assertEqual((d.action, d.issue), ("merge", 126))
        self.assertNotIn(("GET", f"/repos/{REPO}/issues/7/events", None), gh.calls)

    def test_unreadable_events_fail_the_run(self):
        routes = labelled_routes()
        del routes[f"/repos/{REPO}/issues/7/events"]
        errors = []
        self.assertEqual(gate.run_plan(FakeGitHub(routes), LCFG, "pull_request_target", {"pull_request": {"number": 7}}, errors=errors), [])
        self.assertEqual(len(errors), 1)

    def test_actors_are_read_from_the_environment(self):
        env = {"GITHUB_REPOSITORY": REPO, "GATE_MERGE_LABEL_ACTORS": " AllisonGaddy,  Other\nThird "}
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertEqual(gate.config_from_env().merge_label_actors, frozenset({"AllisonGaddy", "Other", "Third"}))
        with mock.patch.dict(os.environ, {"GITHUB_REPOSITORY": REPO}, clear=True):
            self.assertEqual(gate.config_from_env().merge_label_actors, frozenset())


class ResolvedThreadsRoute(unittest.TestCase):
    """Codex reports null, not false, once a pull request has ever had findings."""

    def _state(self, unresolved=None, any_findings=True, sha=HEAD, status="completed"):
        return {"code_review": {"commit_sha": sha, "has_any_findings": any_findings,
                                "has_unresolved_findings": unresolved, "status": status},
                "security_review": {}}

    @staticmethod
    def _found(*findings, note=None):
        return lambda: (list(findings), note)

    @staticmethod
    def _finding(severity="P1", sha=OLD, resolved=True, kind="code"):
        return gate.Finding(41, kind, severity, sha, "A finding", "https://example.test/41", resolved)

    def test_null_with_all_threads_resolved_passes(self):
        self.assertEqual(gate.codex_problems(self._state(), HEAD, self._found(self._finding())), [])

    def test_null_with_an_open_p1_thread_refuses(self):
        p = gate.codex_problems(self._state(), HEAD, self._found(self._finding(resolved=False)))
        self.assertEqual(p, [f"Codex P1 code finding \"A finding\" (https://example.test/41) blocks: its thread from {OLD[:7]} is unresolved."])

    def test_null_with_an_open_p2_thread_passes(self):
        self.assertEqual(gate.codex_problems(self._state(), HEAD, self._found(self._finding("P2", resolved=False))), [])

    def test_null_without_a_finding_reader_refuses(self):
        p = gate.codex_problems(self._state(), HEAD, None)
        self.assertTrue(p and "did not report has_unresolved_findings: false" in p[0])

    def test_null_when_review_comments_cannot_be_read_refuses(self):
        def boom():
            raise gate.GitHubError(502, "down")
        p = gate.codex_problems(self._state(), HEAD, boom)
        self.assertEqual(len(p), 1)
        self.assertIn("the review comments could not be read (down)", p[0])

    def test_null_when_a_p1_thread_cannot_be_read_refuses(self):
        p = gate.codex_problems(self._state(), HEAD, self._found(
            self._finding(resolved=None), note="the review threads could not be read (down)"))
        self.assertEqual(len(p), 1)
        self.assertIn("may still be open: the review threads could not be read (down).", p[0])

    def test_true_with_every_finding_resolved_is_an_evidence_gap(self):
        p = gate.codex_problems(self._state(unresolved=True), HEAD, self._found(self._finding()))
        self.assertTrue(p and "reports unresolved findings, but the gate found no open Codex code finding comment" in p[0], p)

    def test_null_without_any_findings_still_refuses(self):
        p = gate.codex_problems(self._state(any_findings=None), HEAD, self._found())
        self.assertTrue(p and "did not report" in p[0])

    def test_null_on_an_older_head_still_waits(self):
        p = gate.codex_problems(self._state(sha=OLD), HEAD, self._found())
        self.assertTrue(p and "has not reviewed head" in p[0])

    def test_null_while_review_running_refuses(self):
        p = gate.codex_problems(self._state(status="running"), HEAD, self._found())
        self.assertTrue(p and "not completed" in p[0])

    def test_evaluate_reads_threads_only_when_needed(self):
        routes = passing_routes()
        reader = FakeGitHub(routes)
        calls = []
        reader.review_threads = lambda repo, n: calls.append(n) or {}
        self.assertEqual(gate.evaluate(reader, CFG, 7).action, "merge")
        self.assertEqual(calls, [], "a false state never needs the thread read")
        self.assertFalse([c for c in reader.calls if c[1].endswith("/pulls/7/comments")], "nor the review comments")
        routes[f"/repos/{REPO}/issues/7/comments"] = [codex_comment()]
        state_comment = routes[f"/repos/{REPO}/issues/7/comments"][0]
        state_comment["body"] = state_comment["body"].replace('"has_unresolved_findings":false', '"has_unresolved_findings":null').replace('"has_any_findings":false', '"has_any_findings":true')
        routes[f"/repos/{REPO}/pulls/7/comments"] = [finding_comment(41, "P1", sha=OLD)]
        reader = FakeGitHub(routes)
        reader.review_threads = lambda repo, n: calls.append(n) or {41: True}
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
        routes[f"/repos/{REPO}/pulls/7/comments"] = [finding_comment(11, "P1", sha=OLD)]
        return routes

    def reader(self, routes, threads):
        reader = FakeGitHub(routes)
        reader.review_threads = lambda repo, n: threads
        return reader

    def test_findings_on_an_older_head_resolved_merges(self):
        self.assertEqual(gate.evaluate(self.reader(self._null_routes(), {11: True}), CFG, 7).action, "merge")

    def test_p1_findings_on_this_head_block_even_when_resolved(self):
        routes = self._null_routes()
        routes[f"/repos/{REPO}/pulls/7/comments"] += [finding_comment(21, "P1"), finding_comment(22, "P0", title="Second")]
        d = gate.evaluate(self.reader(routes, {11: True, 21: True, 22: True}), CFG, 7)
        self.assertEqual(d.action, "refuse")
        self.assertEqual(len(d.reasons), 2, d.reasons)
        self.assertIn(f"Codex P1 code finding \"Parse global pip options before install\" (https://github.com/{REPO}/pull/7#discussion_r21) blocks: Codex raised it on head {HEAD[:7]}.", d.reasons)
        self.assertIn(f"Codex P0 code finding \"Second\" (https://github.com/{REPO}/pull/7#discussion_r22) blocks: Codex raised it on head {HEAD[:7]}.", d.reasons)


PR214_HEAD = "77c12b54898a379d600463ebe2bf0e20a21fcedd"


def pr214_routes():
    """Pull request #214 as it stood on 2026-11-03: Codex's completed review of the head
    reports has_unresolved_findings true, and its three findings on that head are all P2.
    claude[bot] also left two optional threads. Bodies are copied, trimmed."""
    routes = passing_routes()
    routes[f"/repos/{REPO}/pulls/7"]["head"]["sha"] = PR214_HEAD
    for suffix in ("check-runs", "status"):
        routes[f"/repos/{REPO}/commits/{PR214_HEAD}/{suffix}"] = routes.pop(f"/repos/{REPO}/commits/{HEAD}/{suffix}")
    routes[f"/repos/{REPO}/contents/.changeset/126-change.md?ref={PR214_HEAD}"] = content(GOOD_NOTE)
    routes[f"/repos/{REPO}/contents/.claude-plugin/marketplace.json?ref={PR214_HEAD}"] = content(market())
    summary = {
        "id": 6615828876, "user": {"login": "chatgpt-codex-connector[bot]"}, "updated_at": "2026-11-03T21:32:23Z",
        "body": (
            "<!-- codex-pull-request-review-summary -->\n"
            '<!-- codex-review-state:v1 {"code_review":{"commit_sha":"77c12b54898a379d600463ebe2bf0e20a21fcedd",'
            '"has_any_findings":true,"has_unresolved_findings":true,"status":"completed"},"security_review":'
            '{"commit_sha":"77c12b54898a379d600463ebe2bf0e20a21fcedd","has_any_findings":null,'
            '"has_unresolved_findings":null,"status":"completed"}} -->\n'
            '<!-- codex-security-review:v1 {"blockingSeverityThreshold":"P0","headSha":"77c12b54898a379d600463ebe2bf0e20a21fcedd",'
            '"mergeGateEnabled":false,"pullRequestNumber":214,"status":"completed"} -->\n'
            "## Codex Review Summary\n"
        ),
    }
    security_receipt = codex_receipt(sha=PR214_HEAD, security=True)
    routes[f"/repos/{REPO}/issues/7/comments"] = [summary, security_receipt]
    findings = [
        finding_comment(4460685575, "P2", PR214_HEAD, title="Parse global pip options before install"),
        finding_comment(4460685589, "P2", PR214_HEAD, title="Scope pending exceptions to the recorded finding"),
        finding_comment(4460685601, "P2", PR214_HEAD, title="Install every newly added requirements lock"),
    ]
    claude = [dict(finding_comment(n, "P2", PR214_HEAD, login="claude[bot]"),
                   body="\U0001f7e1 (optional) A workflow line that chains a second install ...") for n in (4460455272, 4460455280)]
    routes[f"/repos/{REPO}/pulls/7/comments"] = claude + findings
    return routes


def with_threads(routes, threads):
    gh = FakeGitHub(routes)
    gh.review_threads = lambda repo, n: threads
    return gh


class SeverityThreshold(Base):
    """AGENTS.md, Review guidelines: block only on P0 and P1. The summary's
    has_unresolved_findings is an aggregate, not a severity."""

    def test_pr214_p2_only_review_on_head_does_not_block(self):
        routes = pr214_routes()
        # Every thread is still open, Codex's and claude[bot]'s alike.
        reader = with_threads(routes, {4460685575: False, 4460685589: False, 4460685601: False,
                                       4460455272: False, 4460455280: False})
        merger = FakeGitHub({}, put_result={"sha": "c" * 40, "merged": True})
        ready = gate.run_plan(reader, CFG, "pull_request_target", {"pull_request": {"number": 7}})
        self.assertEqual(ready, [7], gate.evaluate(reader, CFG, 7).reasons)
        self.assertEqual(reader.writes(), [], "no refusal comment")
        self.assertEqual(gate.run_merge(reader, merger, CFG, ready), ["c" * 40])
        self.assertEqual(merger.calls, [
            ("PUT", f"/repos/{REPO}/pulls/7/merge", {"merge_method": "squash", "sha": PR214_HEAD})])

    def test_pr214_with_one_finding_raised_to_p1_blocks_and_names_it(self):
        routes = pr214_routes()
        routes[f"/repos/{REPO}/pulls/7/comments"][-1] = finding_comment(
            4460685601, "P1", PR214_HEAD, title="Install every newly added requirements lock")
        d = gate.evaluate(FakeGitHub(routes), CFG, 7)
        self.assertEqual(d.action, "refuse")
        self.assertEqual(d.reasons, [
            "Codex P1 code finding \"Install every newly added requirements lock\" "
            f"(https://github.com/{REPO}/pull/7#discussion_r4460685601) blocks: Codex raised it on head 77c12b5."])

    def test_p0_blocks(self):
        routes = pr214_routes()
        routes[f"/repos/{REPO}/pulls/7/comments"].append(finding_comment(5, "P0", PR214_HEAD, title="Drops every check"))
        d = gate.evaluate(FakeGitHub(routes), CFG, 7)
        self.assertEqual(d.action, "refuse")
        self.assertTrue(any(r.startswith("Codex P0 code finding \"Drops every check\"") for r in d.reasons), d.reasons)

    def test_p3_does_not_block(self):
        routes = pr214_routes()
        routes[f"/repos/{REPO}/pulls/7/comments"].append(finding_comment(5, "P3", PR214_HEAD))
        self.assertEqual(gate.evaluate(FakeGitHub(routes), CFG, 7).action, "merge")

    def test_an_open_p1_from_an_older_commit_blocks_and_a_resolved_one_does_not(self):
        routes = pr214_routes()
        routes[f"/repos/{REPO}/pulls/7/comments"].append(finding_comment(5, "P1", OLD, title="Old one"))
        d = gate.evaluate(with_threads(routes, {5: False}), CFG, 7)
        self.assertEqual(d.reasons, [
            f"Codex P1 code finding \"Old one\" (https://github.com/{REPO}/pull/7#discussion_r5) blocks: its thread from {OLD[:7]} is unresolved."])
        self.assertEqual(gate.evaluate(with_threads(routes, {5: True}), CFG, 7).action, "merge")

    def test_a_finding_with_no_severity_badge_is_an_evidence_gap(self):
        routes = pr214_routes()
        routes[f"/repos/{REPO}/pulls/7/comments"].append(finding_comment(5, sha=PR214_HEAD, title="No badge", badge=False))
        d = gate.evaluate(FakeGitHub(routes), CFG, 7)
        self.assertEqual(d.action, "refuse")
        self.assertEqual(d.reasons, [
            f"Codex code finding with no readable severity \"No badge\" (https://github.com/{REPO}/pull/7#discussion_r5) "
            "blocks: Codex raised it on head 77c12b5. The gate cannot read its severity, so this is a gap in the review evidence, not a pass."])

    def test_a_finding_with_two_different_badges_is_an_evidence_gap(self):
        routes = pr214_routes()
        twice = finding_comment(5, "P2", PR214_HEAD)
        twice["body"] += "\n![P1 Badge](https://img.shields.io/badge/P1-orange?style=flat)"
        routes[f"/repos/{REPO}/pulls/7/comments"].append(twice)
        d = gate.evaluate(FakeGitHub(routes), CFG, 7)
        self.assertTrue(any("no readable severity" in r for r in d.reasons), d.reasons)

    def test_p1_from_someone_else_is_not_trusted_review_evidence(self):
        routes = pr214_routes()
        routes[f"/repos/{REPO}/pulls/7/comments"].append(finding_comment(5, "P1", PR214_HEAD, login="someone"))
        self.assertEqual(gate.evaluate(FakeGitHub(routes), CFG, 7).action, "merge")

    def test_forged_p2_findings_cannot_explain_an_unresolved_summary(self):
        routes = pr214_routes()
        for c in routes[f"/repos/{REPO}/pulls/7/comments"]:
            c["user"] = {"login": "someone"}
        self.assert_refused_at(routes, "Codex code review on 77c12b5 reports unresolved findings, but the gate found no open Codex code finding comment")

    def test_codex_replies_are_not_findings(self):
        routes = pr214_routes()
        routes[f"/repos/{REPO}/pulls/7/comments"].append(
            finding_comment(5, sha=PR214_HEAD, title="Thanks, fixed.", badge=False, reply_to=4460685575))
        self.assertEqual(gate.evaluate(FakeGitHub(routes), CFG, 7).action, "merge")

    def test_p2_findings_do_not_stand_in_for_missing_stale_or_incomplete_review(self):
        cases = {
            "missing": ([], "Codex has not reviewed head 77c12b5 yet (no Codex review summary on this pull request)."),
            "stale": ([codex_comment(sha=OLD, unresolved=True)], f"Codex has not reviewed head 77c12b5 yet (its last code review covered {OLD[:7]})."),
            "incomplete": ([codex_comment(sha=PR214_HEAD, status="in_progress", unresolved=True)], "Codex code review on 77c12b5 is in_progress, not completed."),
            "untrusted": ([dict(codex_comment(sha=PR214_HEAD, unresolved=False), user={"login": "someone"})],
                          "Codex has not reviewed head 77c12b5 yet (no Codex review summary on this pull request)."),
        }
        for name, (comments, reason) in cases.items():
            with self.subTest(name):
                routes = pr214_routes()
                routes[f"/repos/{REPO}/issues/7/comments"] = comments
                d = gate.evaluate(FakeGitHub(routes), CFG, 7)
                self.assertEqual(d.action, "refuse")
                self.assertEqual(d.reasons, [reason])

    def test_security_p1_blocks(self):
        routes = self.security_routes()
        routes[f"/repos/{REPO}/pulls/7/comments"].append(
            finding_comment(6, "P1", PR214_HEAD, security=True, title="Protect the main-bypass App key from branch workflows"))
        d = gate.evaluate(FakeGitHub(routes), CFG, 7)
        self.assertEqual(d.action, "refuse")
        self.assertEqual(d.reasons, [
            "Codex P1 security finding \"Security: Protect the main-bypass App key from branch workflows\" "
            f"(https://github.com/{REPO}/pull/7#discussion_r6) blocks: Codex raised it on head 77c12b5."])

    def test_security_p2_alone_does_not_block(self):
        routes = self.security_routes()
        routes[f"/repos/{REPO}/pulls/7/comments"].append(
            finding_comment(6, "P2", PR214_HEAD, security=True, title="Require trusted approval for resolved Codex findings"))
        self.assertEqual(gate.evaluate(FakeGitHub(routes), CFG, 7).action, "merge")

    def test_security_unresolved_with_no_finding_to_read_is_an_evidence_gap(self):
        d = gate.evaluate(FakeGitHub(self.security_routes()), CFG, 7)
        self.assertEqual(d.reasons, [
            "Codex security review on 77c12b5 reports unresolved findings, but the gate found no open Codex security finding comment to read their severity from."])

    def test_security_unresolved_when_comments_cannot_be_read_refuses(self):
        routes = self.security_routes()
        summary = routes[f"/repos/{REPO}/issues/7/comments"][0]
        summary["body"] = summary["body"].replace(
            '"has_any_findings":true,"has_unresolved_findings":true,"status":"completed"},"security_review"',
            '"has_any_findings":false,"has_unresolved_findings":false,"status":"completed"},"security_review"')
        del routes[f"/repos/{REPO}/pulls/7/comments"]
        d = gate.evaluate(FakeGitHub(routes), CFG, 7)
        self.assertEqual(len(d.reasons), 1, d.reasons)
        self.assertTrue(d.reasons[0].startswith("Codex security review on 77c12b5 reports unresolved findings, but the review comments could not be read"))

    def security_routes(self):
        routes = pr214_routes()
        summary = routes[f"/repos/{REPO}/issues/7/comments"][0]
        summary["body"] = summary["body"].replace(
            '"has_any_findings":null,"has_unresolved_findings":null', '"has_any_findings":true,"has_unresolved_findings":true')
        return routes

    def assert_refused_at(self, routes, fragment):
        d = gate.evaluate(FakeGitHub(routes), CFG, 7)
        self.assertEqual(d.action, "refuse")
        self.assertTrue(any(fragment in r for r in d.reasons), d.reasons)


class FindingParsing(unittest.TestCase):
    def test_reads_the_real_finding_shapes(self):
        code = finding_comment(1, "P2", title="Parse global pip options before install")
        f = gate.parse_finding(code)
        self.assertEqual((f.kind, f.severity, f.commit, f.title), ("code", "P2", HEAD, "Parse global pip options before install"))
        sec = gate.parse_finding(finding_comment(2, "P1", OLD, security=True, title="Pin the recorder handoff"))
        self.assertEqual((sec.kind, sec.severity, sec.commit, sec.title), ("security", "P1", OLD, "Security: Pin the recorder handoff"))

    def test_older_findings_without_a_marker_still_carry_a_badge(self):
        body = "**<sub><sub>![P1 Badge](https://img.shields.io/badge/P1-orange?style=flat)</sub></sub>  Old shape**\n\nText."
        self.assertEqual(gate.finding_severity(body), "P1")
        self.assertEqual(gate.finding_title(body), "Old shape")

    def test_severity_is_none_without_a_badge(self):
        self.assertIsNone(gate.finding_severity("**Something** without a badge"))


class ReviewThreadsQuery(unittest.TestCase):
    def test_maps_first_comment_ids_to_resolution_across_pages(self):
        pages = [
            {"data": {"repository": {"pullRequest": {"reviewThreads": {
                "nodes": [{"isResolved": True, "comments": {"nodes": [{"databaseId": 11}]}},
                          {"isResolved": False, "comments": {"nodes": []}}],
                "pageInfo": {"hasNextPage": True, "endCursor": "c1"}}}}}},
            {"data": {"repository": {"pullRequest": {"reviewThreads": {
                "nodes": [{"isResolved": False, "comments": {"nodes": [{"databaseId": 12}]}}],
                "pageInfo": {"hasNextPage": False, "endCursor": None}}}}}},
        ]
        gh = gate.GitHub("t")
        sent = []
        gh._request = lambda method, url, body=None: (sent.append(body["variables"]["a"]) or pages.pop(0), "")
        self.assertEqual(gh.review_threads(REPO, 7), {11: True, 12: False})
        self.assertEqual(sent, [None, "c1"])

    def test_graphql_errors_raise(self):
        gh = gate.GitHub("t")
        gh._request = lambda method, url, body=None: ({"errors": [{"message": "nope"}]}, "")
        with self.assertRaises(gate.GitHubError):
            gh.review_threads(REPO, 7)


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


class FakeResponse:
    def __init__(self, raw, link=""):
        self.raw = raw
        self.headers = {"Link": link} if link else {}

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return self.raw


class RestClient(unittest.TestCase):
    """The real GitHub client, with urlopen replaced so no request leaves the process."""

    def setUp(self):
        self.sent = []
        self.replies = []
        patcher = mock.patch.object(gate.urllib.request, "urlopen", side_effect=self.fake_urlopen)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.gh = gate.GitHub("synthetic-token", "https://api.example.test/")

    def fake_urlopen(self, req, timeout):
        self.sent.append(req)
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply

    def test_relative_path_gets_api_url_and_auth_headers(self):
        self.replies.append(FakeResponse(b'{"ok": true}'))
        self.assertEqual(self.gh.get("/repos/o/r", {"state": "open"}), {"ok": True})
        req = self.sent[0]
        self.assertEqual(req.full_url, "https://api.example.test/repos/o/r?state=open")
        self.assertEqual(req.get_method(), "GET")
        self.assertEqual(req.get_header("Authorization"), "Bearer synthetic-token")
        self.assertEqual(req.get_header("Accept"), "application/vnd.github+json")
        self.assertEqual(req.get_header("X-github-api-version"), "2022-11-28")
        self.assertIsNone(req.data)
        self.assertIsNone(req.get_header("Content-type"))

    def test_writes_send_json_and_empty_reply_is_none(self):
        for call, method in ((self.gh.post, "POST"), (self.gh.put, "PUT"), (self.gh.patch, "PATCH")):
            with self.subTest(method=method):
                self.replies.append(FakeResponse(b""))
                self.assertIsNone(call("/x", {"a": 1}))
                req = self.sent[-1]
                self.assertEqual(req.get_method(), method)
                self.assertEqual(json.loads(req.data), {"a": 1})
                self.assertEqual(req.get_header("Content-type"), "application/json")

    def test_http_error_carries_status_and_github_message(self):
        self.replies.append(urllib.error.HTTPError(
            "https://api.example.test/x", 422, "Unprocessable", {}, io.BytesIO(b'{"message": "Validation Failed"}')))
        with self.assertRaises(gate.GitHubError) as ctx:
            self.gh.get("/x")
        self.assertEqual((ctx.exception.status, ctx.exception.message), (422, "Validation Failed"))

    def test_http_error_with_plain_text_body_keeps_the_text(self):
        self.replies.append(urllib.error.HTTPError(
            "https://api.example.test/x", 502, "Bad Gateway", {}, io.BytesIO(b"upstream down")))
        with self.assertRaises(gate.GitHubError) as ctx:
            self.gh.put("/x", {})
        self.assertEqual((ctx.exception.status, ctx.exception.message), (502, "upstream down"))

    def test_paginate_follows_next_links_until_the_last_page(self):
        nxt = '<https://api.example.test/items?page=2>; rel="next", <https://api.example.test/items?page=2>; rel="last"'
        self.replies += [
            FakeResponse(b'{"items": [1, 2]}', nxt),
            FakeResponse(b'{"items": [3]}', '<https://api.example.test/items?page=1>; rel="prev"'),
        ]
        self.assertEqual(self.gh.paginate("/items", key="items", params={"state": "open"}), [1, 2, 3])
        self.assertEqual([r.full_url for r in self.sent], [
            "https://api.example.test/items?state=open&per_page=100",
            "https://api.example.test/items?page=2",
        ])


class EntryPoint(unittest.TestCase):
    """main() wiring: arguments, environment, GITHUB_OUTPUT and the merge-token rule."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="gate-main-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.event = os.path.join(self.tmp, "event.json")
        with open(self.event, "w", encoding="utf-8") as fh:
            json.dump({"pull_request": {"number": 7}}, fh)
        self.output = os.path.join(self.tmp, "output")
        self.env = {
            "GITHUB_REPOSITORY": REPO, "GATE_TOKEN": "synthetic-read", "GITHUB_API_URL": "https://api.example.test",
            "GITHUB_EVENT_PATH": self.event, "GITHUB_EVENT_NAME": "pull_request_target", "GITHUB_OUTPUT": self.output,
        }


    def run_main(self, argv, env, plan=None, merge=None):
        with mock.patch.dict(os.environ, env, clear=True), \
             mock.patch.object(gate, "run_plan", side_effect=plan) as run_plan, \
             mock.patch.object(gate, "run_merge", side_effect=merge) as run_merge, \
             mock.patch("sys.stderr", new_callable=io.StringIO):
            return gate.main(argv), run_plan, run_merge

    def test_unknown_or_missing_subcommand_is_a_usage_error(self):
        for argv in ([], ["deploy"], ["plan", "merge"]):
            with self.subTest(argv=argv):
                code, run_plan, run_merge = self.run_main(argv, self.env)
                self.assertEqual(code, 2)
                run_plan.assert_not_called()
                run_merge.assert_not_called()

    def test_plan_writes_ready_numbers_and_reads_the_event(self):
        code, run_plan, _ = self.run_main(["plan"], self.env, plan=lambda *a: [7, 9])
        self.assertEqual(code, 0)
        gh, cfg, event_name, event, dispatch, _errors = run_plan.call_args.args
        self.assertEqual((gh.token, gh.api_url), ("synthetic-read", "https://api.example.test"))
        self.assertEqual((cfg.repo, cfg.base_branch, cfg.merge_label), (REPO, "main", ""))
        self.assertEqual((event_name, event, dispatch), ("pull_request_target", {"pull_request": {"number": 7}}, ""))
        with open(self.output, encoding="utf-8") as fh:
            self.assertEqual(fh.read(), "merge=7 9\n")

    def test_plan_fails_the_run_when_an_evaluation_errored(self):
        def plan(gh, cfg, name, event, dispatch, errors):
            errors.append("#7: HTTP 502: down")
            return []
        code, _, _ = self.run_main(["plan"], self.env, plan=plan)
        self.assertEqual(code, 1)
        with open(self.output, encoding="utf-8") as fh:
            self.assertEqual(fh.read(), "merge=\n")

    def test_merge_refuses_without_a_merge_token(self):
        for token in (None, ""):
            with self.subTest(token=token):
                env = dict(self.env, GATE_MERGE_PRS="7")
                if token is not None:
                    env["MERGE_TOKEN"] = token
                code, _, run_merge = self.run_main(["merge"], env)
                self.assertEqual(code, 1)
                run_merge.assert_not_called()

    def test_merge_uses_the_merge_token_only_for_the_merger(self):
        env = dict(self.env, MERGE_TOKEN="synthetic-merge", GATE_MERGE_PRS="7 12")
        code, _, run_merge = self.run_main(["merge"], env, merge=lambda *a: ["c" * 40])
        self.assertEqual(code, 0)
        gh, merger, cfg, numbers, _errors = run_merge.call_args.args
        self.assertEqual((gh.token, merger.token, numbers), ("synthetic-read", "synthetic-merge", [7, 12]))

    def test_merge_fails_the_run_when_a_pull_request_errored(self):
        def merge(gh, merger, cfg, numbers, errors):
            errors.append("#7: HTTP 409: conflict")
            return []
        env = dict(self.env, MERGE_TOKEN="synthetic-merge", GATE_MERGE_PRS="7")
        self.assertEqual(self.run_main(["merge"], env, merge=merge)[0], 1)


WORKFLOW = Path(__file__).resolve().parents[3] / ".github" / "workflows" / "auto-merge-gate.yml"
# Pull request #284: a Codex continuation of job #282, pushed as AllisonGaddy, reviewed and
# green at this head, and skipped by run 42072890922 only because of its author.
PR284_HEAD = "1d72ba03eb137da636a878d1b41747fc72d4776a"
PR284_BODY = "The native failure fixture reads the complete effective marketplace registration ...\n\nCloses #282\n"
PR284_FILES = [
    {"filename": f"tools/foundations-native-fixture/{n}", "status": "added"}
    for n in ("README.md", "run.py", "server.py", "tests/test_fixture.py")
]
PR284_SKIP_REASON = "author is AllisonGaddy, not factory-droid[bot]"


def load_workflow():
    import yaml  # requirements-tooling.txt; the gate itself stays standard library only

    with open(WORKFLOW, encoding="utf-8") as fh:
        wf = yaml.safe_load(fh)
    # YAML 1.1 reads the bare key on as True.
    wf["on"] = wf.pop(True, wf.get("on"))
    return wf


def gate_step(wf, subcommand):
    steps = [s for s in wf["jobs"]["gate"]["steps"] if f"gate.py {subcommand}" in (s.get("run") or "")]
    assert len(steps) == 1, f"expected one step running gate.py {subcommand}, found {len(steps)}"
    return steps[0]


def workflow_config(subcommand, drop=()):
    """The Config gate.py builds from the literal env the workflow gives that step."""
    env = {
        k: str(v) for k, v in gate_step(load_workflow(), subcommand)["env"].items()
        if "${{" not in str(v) and k not in drop
    }
    env["GITHUB_REPOSITORY"] = REPO
    with mock.patch.dict(os.environ, env, clear=True):
        return gate.config_from_env()


def pr284_routes(routes=None, labels=("auto-merge",)):
    """Routes for pull request #7 and job #126, rewritten as #284 by a person closing #282."""
    default_files = routes is None
    text = json.dumps(routes or passing_routes()).replace(HEAD, PR284_HEAD)
    text = text.replace("/pulls/7", "/pulls/284").replace("/issues/7/", "/issues/284/").replace("/issues/126", "/issues/282")
    routes = json.loads(text)
    pr = routes[f"/repos/{REPO}/pulls/284"]
    pr.update(number=284, user={"login": "AllisonGaddy"}, body=PR284_BODY, labels=[{"name": n} for n in labels])
    if default_files:
        routes[f"/repos/{REPO}/pulls/284/files"] = copy.deepcopy(PR284_FILES)
    # 1d72ba0 was pushed to job/282 at 17:12:26Z (repository activity); the label is
    # what Root adds once this repair is on main.
    return enroll(routes, 284, PR284_HEAD, "job/282")


LABELED_284 = {"action": "labeled", "label": {"name": "auto-merge"}, "pull_request": {"number": 284}}


class WorkflowEnrollment(unittest.TestCase):
    """The workflow turns on the merge label route, the same way in plan and merge."""

    def test_plan_and_merge_steps_carry_the_same_literal_label(self):
        wf = load_workflow()
        plan, merge = gate_step(wf, "plan")["env"], gate_step(wf, "merge")["env"]
        self.assertEqual(plan.get("GATE_MERGE_LABEL"), "auto-merge")
        self.assertEqual(merge.get("GATE_MERGE_LABEL"), plan.get("GATE_MERGE_LABEL"))
        for key in ("GATE_CHECK_NAME", "GATE_BASE_BRANCH"):
            self.assertEqual(plan[key], merge[key], key)
        self.assertEqual(plan.get("GATE_MERGE_LABEL_ACTORS"), LABEL_ACTOR)
        self.assertEqual(merge.get("GATE_MERGE_LABEL_ACTORS"), plan.get("GATE_MERGE_LABEL_ACTORS"))
        self.assertEqual(workflow_config("plan"), workflow_config("merge"))
        self.assertEqual(workflow_config("plan").merge_label, "auto-merge")
        self.assertEqual(workflow_config("plan").merge_label_actors, frozenset({LABEL_ACTOR}))

    def test_actors_set_on_plan_alone_never_merge(self):
        reader = FakeGitHub(pr284_routes())
        merger = FakeGitHub({}, put_result={"sha": "c" * 40})
        self.assertEqual(gate.run_plan(reader, workflow_config("plan"), "pull_request_target", LABELED_284), [284])
        no_actors = workflow_config("merge", drop=("GATE_MERGE_LABEL_ACTORS",))
        self.assertEqual(gate.run_merge(reader, merger, no_actors, [284]), [])
        self.assertEqual(merger.calls, [])

    def test_the_label_alone_no_longer_enrolls(self):
        """Codex P1 on 5d49e1a: any triage user could add the label, and it stayed on
        through later pushes. Under the workflow's config neither enrolls #284 now."""
        cfg = workflow_config("plan")
        triage = pr284_routes()
        triage[f"/repos/{REPO}/issues/284/events"] = [label_event(actor="triage-helper")]
        d = gate.evaluate(FakeGitHub(triage), cfg, 284)
        self.assertEqual(d.action, "skip")
        self.assertEqual(d.reasons, ["the auto-merge label was added by triage-helper, who is not an enrollment actor (GATE_MERGE_LABEL_ACTORS)"])
        pushed_later = pr284_routes()
        pushed_later[f"/repos/{REPO}/activity"] = [push_activity(PR284_HEAD, "job/282", "2026-11-05T19:45:00Z")]
        reader = FakeGitHub(pushed_later)
        merger = FakeGitHub({}, put_result={"sha": "c" * 40})
        self.assertEqual(gate.run_plan(reader, cfg, "pull_request_target", LABELED_284), [])
        self.assertEqual(gate.run_merge(reader, merger, workflow_config("merge"), [284]), [])
        self.assertEqual(merger.calls, [])
        self.assertIn("Remove the label and add it again to enroll this head.", reader.writes()[0][2]["body"])

    def test_a_run_for_another_label_never_takes_the_shared_slot(self):
        wf = load_workflow()
        group = " ".join(wf["concurrency"]["group"].split())
        label = gate_step(wf, "plan")["env"]["GATE_MERGE_LABEL"]
        self.assertEqual(group, (
            "${{ github.event_name == 'pull_request_target' && github.event.action == 'labeled' && "
            f"github.event.label.name != '{label}' && format('auto-merge-gate-other-label-{{0}}', github.run_id) || "
            "'auto-merge-gate' }}"
        ))
        self.assertIs(wf["concurrency"]["cancel-in-progress"], False)

    def test_workflow_only_changes_run_these_tests(self):
        with open(WORKFLOW.parent / "tooling-coverage.yml", encoding="utf-8") as fh:
            import yaml

            cov = yaml.safe_load(fh)
        on = cov.get("on", cov.get(True))
        for event in ("pull_request", "push"):
            self.assertIn(".github/workflows/auto-merge-gate.yml", on[event]["paths"], event)

    def test_adding_the_label_starts_a_run_and_other_labels_do_not(self):
        wf = load_workflow()
        self.assertIn("labeled", wf["on"]["pull_request_target"]["types"])
        self.assertNotIn("pull_request", wf["on"], "pull request code must never run with secrets")
        cond = " ".join(wf["jobs"]["gate"]["if"].split())
        label = gate_step(wf, "plan")["env"]["GATE_MERGE_LABEL"]
        self.assertIn(f"(github.event.action != 'labeled' || github.event.label.name == '{label}')", cond)
        self.assertIn("github.repository == 'ExpertPartners/expert-partners-skills'", cond)
        self.assertIn("(github.event_name != 'issue_comment' || github.event.issue.pull_request)", cond)
        cfg = workflow_config("plan")
        self.assertEqual(gate.target_prs(FakeGitHub({}), cfg, "pull_request_target", LABELED_284), [284])

    def test_main_only_checkout_and_merge_credential_are_unchanged(self):
        wf = load_workflow()
        steps = wf["jobs"]["gate"]["steps"]
        checkout = steps[0]
        self.assertTrue(checkout["uses"].startswith("actions/checkout@"))
        self.assertEqual(checkout["with"], {"ref": "main", "persist-credentials": False, "sparse-checkout": "tools/auto-merge-gate"})
        mint = next(s for s in steps if s.get("id") == "app-token")
        self.assertEqual(mint["if"], "steps.plan.outputs.merge != ''")
        self.assertEqual(mint["with"], {
            "client-id": "${{ vars.SKILLS_GRAPH_APP_CLIENT_ID }}",
            "private-key": "${{ secrets.SKILLS_GRAPH_APP_PRIVATE_KEY }}",
            "permission-contents": "write",
        })
        plan, merge = gate_step(wf, "plan"), gate_step(wf, "merge")
        self.assertNotIn("MERGE_TOKEN", plan["env"])
        self.assertEqual(merge["env"]["MERGE_TOKEN"], "${{ steps.app-token.outputs.token }}")
        self.assertEqual(merge["if"], "steps.plan.outputs.merge != ''")
        self.assertEqual(merge["env"]["GATE_MERGE_PRS"], "${{ steps.plan.outputs.merge }}")

    def test_pr284_before_the_repair_is_skipped_for_its_author(self):
        cfg = workflow_config("plan", drop=("GATE_MERGE_LABEL",))
        self.assertEqual(cfg.merge_label, "")
        gh = FakeGitHub(pr284_routes())
        event = {"issue": {"number": 284, "pull_request": {}}}
        self.assertEqual(gate.run_plan(gh, cfg, "issue_comment", event), [])
        d = gate.evaluate(gh, cfg, 284)
        self.assertEqual((d.action, d.reasons), ("skip", [PR284_SKIP_REASON]))
        self.assertEqual(gh.writes(), [])

    def test_pr284_after_the_repair_merges_pinned_to_its_head(self):
        reader = FakeGitHub(pr284_routes())
        merger = FakeGitHub({}, put_result={"sha": "c" * 40, "merged": True})
        ready = gate.run_plan(reader, workflow_config("plan"), "pull_request_target", LABELED_284)
        self.assertEqual(ready, [284])
        self.assertEqual(gate.run_merge(reader, merger, workflow_config("merge"), ready), ["c" * 40])
        self.assertEqual(merger.calls, [
            ("PUT", f"/repos/{REPO}/pulls/284/merge", {"merge_method": "squash", "sha": PR284_HEAD}),
        ])
        # The label route never treats the author as Factory, so it does not touch job #282.
        self.assertEqual(reader.writes(), [])
        self.assertIsNone(gate.evaluate(reader, workflow_config("merge"), 284).issue)

    def test_a_label_set_on_plan_alone_never_merges(self):
        reader = FakeGitHub(pr284_routes())
        merger = FakeGitHub({}, put_result={"sha": "c" * 40})
        self.assertEqual(gate.run_plan(reader, workflow_config("plan"), "pull_request_target", LABELED_284), [284])
        unlabelled_merge = workflow_config("merge", drop=("GATE_MERGE_LABEL",))
        self.assertEqual(gate.run_merge(reader, merger, unlabelled_merge, [284]), [])
        self.assertEqual(merger.calls, [])

    def test_pr284_without_the_label_is_still_left_alone(self):
        gh = FakeGitHub(pr284_routes(labels=()))
        d = gate.evaluate(gh, workflow_config("plan"), 284)
        self.assertEqual(d.action, "skip")
        self.assertEqual(d.reasons, [f"{PR284_SKIP_REASON}, and it does not carry the auto-merge label"])

    def test_the_label_route_keeps_every_refusal(self):
        cfg = workflow_config("plan")
        sha = PR284_HEAD[:7]

        def draft(r):
            r[f"/repos/{REPO}/pulls/284"]["draft"] = True

        def foreign_base(r):
            r[f"/repos/{REPO}/pulls/284"]["base"]["ref"] = "release"

        def no_checks(r):
            r[f"/repos/{REPO}/commits/{PR284_HEAD}/check-runs"] = [{"name": "auto-merge-gate", "status": "in_progress"}]

        def stale_review(r):
            r[f"/repos/{REPO}/issues/284/comments"] = [codex_comment(sha=OLD)]

        def finding(severity):
            def apply(r):
                r[f"/repos/{REPO}/issues/284/comments"] = [codex_comment(sha=PR284_HEAD, unresolved=True)]
                r[f"/repos/{REPO}/pulls/284/comments"] = [finding_comment(5, severity, PR284_HEAD, title="Guard the head")]
            return apply

        cases = [
            ("draft", draft, "skip", "draft"),
            ("foreign base", foreign_base, "skip", "base is not main"),
            ("no checks", no_checks, "refuse", "No checks have reported on the head commit yet."),
            ("stale review", stale_review, "refuse", f"Codex has not reviewed head {sha} yet"),
            ("P0", finding("P0"), "refuse", f"Codex P0 code finding \"Guard the head\""),
            ("P1", finding("P1"), "refuse", f"Codex P1 code finding \"Guard the head\""),
        ]
        for name, change, action, fragment in cases:
            with self.subTest(name):
                routes = pr284_routes()
                change(routes)
                reader = FakeGitHub(routes)
                merger = FakeGitHub({}, put_result={"sha": "c" * 40})
                self.assertEqual(gate.run_plan(reader, cfg, "pull_request_target", LABELED_284), [])
                self.assertEqual(gate.run_merge(reader, merger, workflow_config("merge"), [284]), [])
                self.assertEqual(merger.calls, [])
                d = gate.evaluate(reader, cfg, 284)
                self.assertEqual(d.action, action)
                self.assertTrue(any(fragment in r for r in d.reasons), d.reasons)

    def test_the_label_route_keeps_the_release_file_rule(self):
        routes = pr284_routes(release_routes([(MANIFEST, "modified")], {MANIFEST: manifest()}, {MANIFEST: manifest("0.6.8")}))
        reader = FakeGitHub(routes)
        merger = FakeGitHub({}, put_result={"sha": "c" * 40})
        self.assertEqual(gate.run_plan(reader, workflow_config("plan"), "pull_request_target", LABELED_284), [])
        self.assertEqual(gate.run_merge(reader, merger, workflow_config("merge"), [284]), [])
        self.assertEqual(merger.calls, [])
        d = gate.evaluate(reader, workflow_config("plan"), 284)
        self.assertIn(f"`{MANIFEST}` changes the brand-voice version from 0.6.7 to 0.6.8. {gate.RELEASE_HINT}", d.reasons)

    def test_a_push_after_plan_stops_the_merge(self):
        routes = pr284_routes()
        reader = FakeGitHub(routes)
        self.assertEqual(gate.run_plan(reader, workflow_config("plan"), "pull_request_target", LABELED_284), [284])
        moved = "d" * 40
        reader.routes[f"/repos/{REPO}/pulls/284"]["head"]["sha"] = moved
        reader.routes[f"/repos/{REPO}/activity"] = [push_activity(moved, "job/282", "2026-11-05T19:45:00Z")]
        reader.routes[f"/repos/{REPO}/commits/{moved}/check-runs"] = routes[f"/repos/{REPO}/commits/{PR284_HEAD}/check-runs"]
        reader.routes[f"/repos/{REPO}/commits/{moved}/status"] = routes[f"/repos/{REPO}/commits/{PR284_HEAD}/status"]
        merger = FakeGitHub({}, put_result={"sha": "c" * 40})
        self.assertEqual(gate.run_merge(reader, merger, workflow_config("merge"), [284]), [])
        self.assertEqual(merger.calls, [])
        refusal = reader.writes()[0]
        self.assertEqual(refusal[:2], ("POST", f"/repos/{REPO}/issues/284/comments"))
        self.assertIn(f"Codex has not reviewed head {moved[:7]} yet", refusal[2]["body"])
        self.assertIn(f"before head {moved[:7]} was pushed at 2026-11-05T19:45:00Z", refusal[2]["body"])

    def test_github_rejects_a_merge_whose_head_moved_mid_run(self):
        reader = FakeGitHub(pr284_routes())
        merger = FakeGitHub({}, put_error=gate.GitHubError(409, "Head branch was modified. Review and try the merge again."))
        self.assertEqual(gate.run_merge(reader, merger, workflow_config("merge"), [284]), [])
        self.assertEqual(merger.calls, [
            ("PUT", f"/repos/{REPO}/pulls/284/merge", {"merge_method": "squash", "sha": PR284_HEAD}),
        ])
        writes = reader.writes()
        self.assertEqual(len(writes), 1)
        self.assertIn("Head branch was modified", writes[0][2]["body"])

    def test_ember_stays_excluded_with_the_workflow_label(self):
        cfg = gate.Config(repo="ExpertPartners/ember", merge_label=workflow_config("plan").merge_label)
        reader = FakeGitHub(pr284_routes())
        merger = FakeGitHub({}, put_result={"sha": "c" * 40})
        self.assertEqual(gate.run_plan(reader, cfg, "pull_request_target", LABELED_284), [])
        self.assertEqual(gate.run_merge(reader, merger, cfg, [284]), [])
        self.assertEqual((reader.calls, merger.calls), ([], []))


if __name__ == "__main__":
    unittest.main()
