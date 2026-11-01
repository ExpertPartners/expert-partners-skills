"""Unit tests for the auto-merge gate. Every GitHub call goes to FakeGitHub; nothing touches the network.

Run from the repo root: python3 -m unittest discover -s tools/auto-merge-gate/tests -v
"""

import copy
import importlib.util
import json
import os
import sys
import unittest

spec = importlib.util.spec_from_file_location(
    "gate", os.path.join(os.path.dirname(__file__), "..", "gate.py"))
gate = importlib.util.module_from_spec(spec)
# dataclasses resolves annotations through sys.modules, so register before executing.
sys.modules["gate"] = gate
spec.loader.exec_module(gate)

REPO = "ExpertPartners/expert-partners-skills"
HEAD = "a" * 40
OLD = "b" * 40
CFG = gate.Config(repo=REPO)


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
    def evaluate(self, routes, number=7):
        return gate.evaluate(FakeGitHub(routes), CFG, number)

    def assert_left_alone(self, routes, fragment):
        gh = FakeGitHub(routes)
        merger = FakeGitHub({})
        self.assertEqual(gate.run_plan(gh, CFG, "pull_request_target", {"pull_request": {"number": 7}}), [])
        self.assertEqual(gate.run_merge(gh, merger, CFG, [7]), [])
        d = gate.evaluate(gh, CFG, 7)
        self.assertEqual(d.action, "skip")
        self.assertIn(fragment, d.reasons[0])
        self.assertEqual(gh.writes(), [], "a pull request the gate does not consider gets no comment")
        self.assertEqual(merger.calls, [])

    def assert_refused(self, routes, fragment):
        gh = FakeGitHub(routes)
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


if __name__ == "__main__":
    unittest.main()
