"""Unit tests for the stall sweeper. Every GitHub call goes to FakeGitHub; nothing touches the
network.

Run from the repo root: python3 -m unittest discover -s tools/stall-sweeper/tests -v
"""

import contextlib
import datetime as dt
import importlib.util
import io
import os
import re
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    # dataclasses resolves annotations through sys.modules, so register before executing.
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


sw = load("sweeper", os.path.join(HERE, "..", "sweeper.py"))
gate = load("gate", os.path.join(ROOT, "tools", "auto-merge-gate", "gate.py"))

REPO = "ExpertPartners/expert-partners-skills"
WORKFLOW = "factory-chat-to-code-loop-builder-skills.yml"
NOW = dt.datetime(2026, 11, 3, 21, 0, tzinfo=dt.timezone.utc)
HEAD = "a" * 40
NEW_HEAD = "b" * 40
ALLISON = "AllisonGaddy"


def ago(minutes):
    return sw.iso(NOW - dt.timedelta(minutes=minutes))


def issue(number, *labels, title=None, author=ALLISON, created=600):
    return {
        "number": number,
        "title": title or f"Job: thing {number}",
        "user": {"login": author},
        "labels": [{"name": n} for n in labels],
        "body": "Files in scope\n- tools/x.py\n",
        "state": "open",
        "created_at": ago(created),
    }


def pr(number, closes, head=HEAD, author="factory-droid[bot]", draft=False, created=120):
    return {
        "number": number,
        "user": {"login": author},
        "body": f"Closes #{closes}\n\nwork",
        "head": {"ref": f"job/{closes}-work", "sha": head, "repo": {"full_name": REPO}},
        "draft": draft,
        "state": "open",
        "created_at": ago(created),
    }


def run(run_id, *, event="workflow_dispatch", title="Chat to Code Loop Builder - Skills", status="completed", started=120, updated=None):
    return {
        "id": run_id,
        "event": event,
        "display_title": title,
        "status": status,
        "created_at": ago(started),
        "run_started_at": ago(started),
        "updated_at": ago(updated if updated is not None else max(started - 5, 0)),
    }


def comment(body, login="github-actions[bot]", cid=None, at=None, updated=None):
    c = {"id": cid or abs(hash(body)) % 100000, "user": {"login": login}, "body": body}
    if at is not None:
        c["created_at"] = ago(at)
        c["updated_at"] = ago(updated if updated is not None else at)
    return c


def refusal(sha, *reasons):
    return comment(gate.refusal_body(gate.Decision(1, "refuse", list(reasons), sha)))


def thread(tid, path, title, resolved=False, author="chatgpt-codex-connector"):
    return {
        "id": tid, "isResolved": resolved, "path": path,
        "comments": {"nodes": [{
            "author": {"login": author},
            "body": f"**<sub><sub>![P1 Badge](https://img.shields.io/badge/P1-orange)</sub></sub>  {title}**\n\nDetails.",
            "url": f"https://github.com/{REPO}/pull/9#discussion_{tid}",
        }]},
    }


def finding_reason(t, sha=HEAD, raised=None):
    """The gate's own refusal line for a P1 Codex finding on thread t, raised on raised (the
    head by default), so rule 7 is tested against the wording the gate really writes."""
    first = t["comments"]["nodes"][0]
    f = gate.parse_finding({"id": 1, "body": first["body"], "original_commit_id": raised or sha, "html_url": first["url"]})
    f.resolved = t["isResolved"]
    reasons, _ = gate.blocking_findings([f], sha, None)
    assert len(reasons) == 1, reasons
    return reasons[0]


GUARD_T1 = thread("T1", "tools/x.py", "Guard the empty list")
GUARD_T2 = thread("T2", "tools/x.py", "Guard the empty list")


class FakeGitHub:
    """Holds the board and answers the calls the sweeper makes. An unexpected call fails."""

    def __init__(self, issues=(), prs=(), runs=(), comments=None, jobs=None, logs=None, timeline=None,
                 events=None, commits=None, reviews=None, threads=None, extra=None, pulls=None,
                 reactions=None, connector=False):
        self.issues = {i["number"]: i for i in issues}
        self.extra = {i["number"]: i for i in (extra or [])}
        self.prs = list(prs)
        self.pulls = dict(pulls or {})
        self.runs = list(runs)
        self.comments = {k: list(v) for k, v in (comments or {}).items()}
        self.jobs = jobs or {}
        self.logs = logs or {}
        self.timeline = timeline or {}
        self.events = events or {}
        self.commits = commits or {}
        self.reviews = reviews or {}
        self.threads = threads or {}
        self.reactions = {k: list(v) for k, v in (reactions or {}).items()}
        # A stand-in for the Codex connector: it puts its eyes on an @codex review comment
        # from a person and ignores one from a bot account, as it did live on Nov 4 2026.
        self.connector = connector
        self.calls = []

    def get(self, path, params=None):
        self.calls.append(("GET", path, params))
        parts = path.split("/")
        if path.startswith(f"/repos/{REPO}/issues/"):
            n = int(parts[-1])
            return self.issues.get(n) or self.extra[n]
        if path.startswith(f"/repos/{REPO}/pulls/"):
            return self.pulls[int(parts[-1])]
        if path.startswith(f"/repos/{REPO}/commits/"):
            return self.commits.get(parts[-1], {"commit": {"committer": {"date": ago(120)}}})
        raise AssertionError(f"unexpected GET {path}")

    def paginate(self, path, params=None, key=None):
        self.calls.append(("GET", path, params))
        parts = path.split("/")
        if path == f"/repos/{REPO}/issues":
            assert params["state"] == "open"
            return list(self.issues.values())
        if path == f"/repos/{REPO}/pulls":
            return list(self.prs)
        if path.endswith("/comments") and "/issues/" in path:
            return list(self.comments.get(int(parts[-2]), []))
        if path.endswith("/timeline"):
            return list(self.timeline.get(int(parts[-2]), []))
        if path.endswith("/events"):
            return list(self.events.get(int(parts[-2]), []))
        if path.endswith("/reviews"):
            return list(self.reviews.get(int(parts[-2]), []))
        if path.startswith(f"/repos/{REPO}/issues/comments/") and path.endswith("/reactions"):
            return list(self.reactions.get(int(parts[-2]), []))
        if path == f"/repos/{REPO}/actions/workflows/{WORKFLOW}/runs":
            assert key == "workflow_runs"
            return list(self.runs)
        if path.startswith(f"/repos/{REPO}/actions/runs/") and path.endswith("/jobs"):
            assert key == "jobs"
            return list(self.jobs.get(int(parts[-2]), []))
        raise AssertionError(f"unexpected paginate {path}")

    def text(self, path):
        self.calls.append(("GET", path, None))
        return self.logs[int(path.split("/")[-2])]

    def graphql(self, query, variables):
        self.calls.append(("GRAPHQL", query, variables))
        assert query.startswith("query"), "the sweeper only reads through GraphQL"
        nodes = self.threads.get(variables["p"], [])
        return {"repository": {"pullRequest": {"reviewThreads": {
            "nodes": nodes, "pageInfo": {"hasNextPage": False, "endCursor": None}}}}}

    def _issue(self, n):
        return self.issues.get(n) or self.extra.get(n)

    @staticmethod
    def _check(method, path, body):
        ok = (
            (method == "POST" and re.fullmatch(rf"/repos/{REPO}/issues/\d+/(labels|comments)", path))
            or (method == "DELETE" and re.fullmatch(rf"/repos/{REPO}/issues/\d+/labels/(in-progress|waiting)", path))
            or (method == "PATCH" and re.fullmatch(rf"/repos/{REPO}/issues/\d+", path)
                and body == {"state": "closed", "state_reason": "completed"})
            or (method == "POST" and path == f"/repos/{REPO}/actions/workflows/{WORKFLOW}/dispatches")
        )
        assert ok, f"the sweeper made a write it must never make: {method} {path} {body}"

    def post(self, path, body):
        self._check("POST", path, body)
        self.calls.append(("POST", path, body))
        parts = path.split("/")
        if path.endswith("/labels"):
            item = self._issue(int(parts[-2]))
            have = {label["name"] for label in item["labels"]}
            item["labels"] += [{"name": n} for n in body["labels"] if n not in have]
        elif path.endswith("/comments"):
            posted = comment(body["body"], at=0)
            self.comments.setdefault(int(parts[-2]), []).append(posted)
            if self.connector and body["body"].startswith("@codex review") and not posted["user"]["login"].endswith("[bot]"):
                self.reactions.setdefault(posted["id"], []).append(codex_eyes())
        return None

    def patch(self, path, body):
        self._check("PATCH", path, body)
        self.calls.append(("PATCH", path, body))
        self._issue(int(path.split("/")[-1])).update(body)
        return {}

    def delete(self, path):
        self._check("DELETE", path, None)
        self.calls.append(("DELETE", path, None))
        parts = path.split("/")
        item = self._issue(int(parts[-3]))
        if parts[-1] not in {label["name"] for label in item["labels"]}:
            raise sw.GitHubError(404, "Label does not exist")
        item["labels"] = [label for label in item["labels"] if label["name"] != parts[-1]]

    # ------------------------------------------------ what happened

    def writes(self):
        return [c for c in self.calls if c[0] in ("POST", "PATCH", "DELETE", "PUT")]

    def dispatches(self):
        return [int(c[2]["inputs"]["issue"]) for c in self.writes() if c[1].endswith("/dispatches")]

    def labels(self, n):
        return {label["name"] for label in self._issue(n)["labels"]}

    def comment_bodies(self, n):
        return [c["body"] for c in self.comments.get(n, [])]


def failing_label_writes(gh):
    """Make every needs-allison label write fail, as a transient GitHub error would."""
    real_post = gh.post

    def post(path, body):
        if path.endswith("/labels") and "needs-allison" in body["labels"]:
            gh.calls.append(("POST", path, body))
            raise sw.GitHubError(502, "Bad Gateway")
        return real_post(path, body)

    gh.post = post
    return real_post


def codex_eyes():
    return {"user": {"login": "chatgpt-codex-connector[bot]"}, "content": "eyes"}


def removed_needs_allison(at=0):
    return {"event": "unlabeled", "label": {"name": "needs-allison"}, "created_at": ago(at)}


def sweep(gh, dry_run=False, repo=REPO, later=0):
    """later moves the sweep that many minutes past NOW, as the next scheduled sweeps would."""
    s = sw.Sweeper(gh, sw.Config(repo=repo, builder_workflow=WORKFLOW, ref="main", dry_run=dry_run),
                   NOW + dt.timedelta(minutes=later))
    with contextlib.redirect_stdout(io.StringIO()):
        s.sweep()
    assert not s.errors, s.errors
    return s


class CleanBoard(unittest.TestCase):
    def test_a_healthy_board_gets_no_writes(self):
        gh = FakeGitHub(
            issues=[
                issue(1, "job", "in-progress"),           # building right now
                issue(2, "job"),                           # has an open pull request under review
                issue(3, "job", "waiting"),                # waits on an open pull request
                issue(4, "job", "in-progress", title="Job: fresh"),
                {**issue(5), "title": "Not a job"},
            ],
            prs=[pr(20, 2, created=10), pr(21, 1)],
            runs=[run(1, event="issues", title="Job: fresh", status="in_progress", started=2)],
            comments={
                3: [comment("<!-- factory-overlap-check:v1 -->\nWaiting on #21, same file")],
                20: [], 21: [comment("<!-- codex-review-state:v1 " + '{"code_review": {"commit_sha": "%s"}}' % HEAD + " -->",
                                     login="chatgpt-codex-connector[bot]")],
            },
            extra=[{**pr(21, 1), "labels": [], "pull_request": {}}],
            events={4: [{"event": "labeled", "label": {"name": "in-progress"}, "created_at": ago(3)}]},
        )
        s = sweep(gh)
        self.assertEqual(gh.writes(), [])
        self.assertEqual(s.actions, [])
        self.assertEqual(sw.summarize(s), "No stalled jobs. 0 actions taken.")

    def test_empty_board(self):
        gh = FakeGitHub()
        s = sweep(gh)
        self.assertEqual(gh.writes(), [])
        self.assertEqual(s.actions, [])


class Rule1Unlabeled(unittest.TestCase):
    def test_labels_comments_once_and_dispatches(self):
        gh = FakeGitHub(issues=[issue(7)])
        s = sweep(gh)
        self.assertIn("job", gh.labels(7))
        self.assertEqual(gh.dispatches(), [7])
        self.assertEqual(len(gh.comment_bodies(7)), 1)
        self.assertIn("no job label and no parked label", gh.comment_bodies(7)[0])
        self.assertEqual(len(s.actions), 1)

    def test_comment_is_posted_only_once(self):
        gh = FakeGitHub(issues=[issue(7)], comments={7: [comment(f"earlier\n{sw.LABELED_MARK}")]})
        sweep(gh)
        self.assertEqual(len(gh.comment_bodies(7)), 1)
        self.assertEqual(gh.dispatches(), [7])

    def test_parked_is_left_alone(self):
        gh = FakeGitHub(issues=[issue(7, "parked")])
        sweep(gh)
        self.assertEqual(gh.writes(), [])

    def test_author_not_on_the_allowlist_is_left_alone(self):
        gh = FakeGitHub(issues=[issue(7, author="stranger")])
        sweep(gh)
        self.assertEqual(gh.writes(), [])

    def test_waits_for_the_builder_run_that_is_already_labeling_it(self):
        gh = FakeGitHub(issues=[issue(7, title="Job: new")],
                        runs=[run(1, event="issues", title="Job: new", status="in_progress", started=1)])
        sweep(gh)
        self.assertEqual(gh.writes(), [])


class Rule2Done(unittest.TestCase):
    def board(self, merged=True):
        merged_pr = {"number": 30, "merged": merged, "merge_commit_sha": "c" * 40}
        source = {"number": 30, "body": "Closes #8\n", "repository_url": f"https://api.github.com/repos/{REPO}",
                  "pull_request": {"merged_at": ago(20) if merged else None}}
        return FakeGitHub(
            issues=[issue(8, "job", "done")],
            timeline={8: [{"event": "cross-referenced", "source": {"type": "issue", "issue": source}}]},
            pulls={30: merged_pr},
        )

    def test_closes_as_completed_and_comments_the_merge_commit(self):
        gh = self.board()
        s = sweep(gh)
        self.assertEqual(gh.issues[8]["state"], "closed")
        self.assertEqual(gh.issues[8]["state_reason"], "completed")
        self.assertIn("c" * 40, gh.comment_bodies(8)[0])
        self.assertIn("#30", s.actions[0])
        self.assertEqual(gh.dispatches(), [])

    def test_unmerged_pull_request_does_nothing(self):
        gh = self.board(merged=False)
        sweep(gh)
        self.assertEqual(gh.writes(), [])


class Rule3Waiting(unittest.TestCase):
    def board(self, holder_state="closed", holder_labels=()):
        holder = {**issue(40, *holder_labels), "state": holder_state}
        return FakeGitHub(
            issues=[issue(9, "job", "waiting")],
            extra=[holder],
            comments={9: [comment("<!-- factory-overlap-check:v1 -->\nWaiting on #40, same file\n\n- #40 (pull request): `a`")]},
        )

    def test_everything_it_waits_on_is_closed(self):
        gh = self.board()
        sweep(gh)
        self.assertEqual(gh.dispatches(), [9])
        self.assertNotIn("waiting", gh.labels(9))

    def test_parked_or_done_holders_count_as_finished(self):
        for labels in (("job", "parked"), ("job", "done")):
            gh = self.board("open", labels)
            sweep(gh)
            self.assertEqual(gh.dispatches(), [9], labels)

    def test_a_holder_that_no_longer_exists_holds_nothing(self):
        gh = self.board()
        del gh.extra[40]
        real_get = gh.get

        def get(path, params=None):
            if path.endswith("/issues/40"):
                raise sw.GitHubError(404, "Not Found")
            return real_get(path, params)

        gh.get = get
        sweep(gh)
        self.assertEqual(gh.dispatches(), [9])

    def test_open_holder_keeps_it_waiting(self):
        gh = self.board("open", ("job", "in-progress"))
        sweep(gh)
        self.assertEqual(gh.writes(), [])

    def test_an_open_pull_request_holder_keeps_it_waiting(self):
        gh = self.board("open")
        gh.extra[40]["pull_request"] = {}
        sweep(gh)
        self.assertEqual(gh.writes(), [])

    def test_a_job_holder_that_lost_in_progress_holds_nothing(self):
        gh = self.board("open", ("job", "needs-allison"))
        sweep(gh)
        self.assertEqual(gh.dispatches(), [9])

    def test_a_failed_build_is_not_restarted_on_every_sweep(self):
        # A failed build goes back to waiting with no holder named.
        gh = FakeGitHub(
            issues=[issue(9, "job", "waiting")],
            comments={9: [comment("<!-- factory-overlap-check:v1 -->\nThe build did not finish (result: failure).")]},
            runs=[run(5, started=20)],
            jobs={5: [{"id": 50, "name": "builder / gate", "status": "completed", "conclusion": "success"}]},
            logs={50: "OVERLAP_ISSUE: 9"},
        )
        sweep(gh)
        self.assertEqual(gh.writes(), [])
        gh = FakeGitHub(
            issues=[issue(9, "job", "waiting")],
            comments={9: [comment("<!-- factory-overlap-check:v1 -->\nThe build did not finish (result: failure).")]},
            runs=[run(5, started=40, updated=35)],
            jobs={5: [{"id": 50, "name": "builder / gate", "status": "completed", "conclusion": "success"}]},
            logs={50: "OVERLAP_ISSUE: 9"},
        )
        sweep(gh)
        self.assertEqual(gh.dispatches(), [9], "after 30 minutes it is tried again")

    def test_another_run_claimed_it_first(self):
        gh = self.board()
        real_delete = gh.delete

        def raced(path):
            gh.issues[9]["labels"] = [{"name": "job"}]
            return real_delete(path)

        gh.delete = raced
        sweep(gh)
        self.assertEqual(gh.dispatches(), [])


class Rule4Idle(unittest.TestCase):
    def test_idle_job_is_dispatched(self):
        gh = FakeGitHub(issues=[issue(10, "job")], runs=[run(5, event="issues", title="Job: thing 10", started=90)],
                        jobs={5: [{"id": 50, "name": "builder / gate", "status": "completed", "conclusion": "success"}]})
        sweep(gh)
        self.assertEqual(gh.dispatches(), [10])

    def test_a_run_in_the_last_30_minutes_holds_it(self):
        gh = FakeGitHub(issues=[issue(10, "job")], runs=[run(5, started=12)],
                        jobs={5: [{"id": 50, "name": "builder / gate", "status": "completed", "conclusion": "success"}]},
                        logs={50: "2026-11-03T20:48:00Z   OVERLAP_ISSUE: 10\n"})
        sweep(gh)
        self.assertEqual(gh.writes(), [])

    def test_a_skipped_issue_event_run_is_not_a_build(self):
        gh = FakeGitHub(issues=[issue(10, "job")], runs=[run(5, event="issues", title="Job: thing 10", started=5)],
                        jobs={5: [{"id": 50, "name": "builder / gate", "status": "completed", "conclusion": "skipped"}]})
        sweep(gh)
        self.assertEqual(gh.dispatches(), [10])

    def test_needs_allison_is_not_restarted(self):
        gh = FakeGitHub(issues=[issue(10, "job", "needs-allison")])
        sweep(gh)
        self.assertEqual(gh.writes(), [])

    NO_PR = "<!-- factory-overlap-check:v1 -->\nThe build finished without opening a pull request for this job, so it no longer holds its files."

    def test_a_build_with_no_pull_request_is_rebuilt_once_with_a_note(self):
        gh = FakeGitHub(issues=[issue(10, "job")], comments={10: [comment(self.NO_PR, at=60)]})
        s = sweep(gh)
        self.assertEqual(gh.dispatches(), [10])
        self.assertIn(sw.REBUILT_MARK, gh.comment_bodies(10)[-1])
        self.assertIn("without a pull request", s.actions[0])

    def test_a_rebuild_that_again_opens_no_pull_request_goes_to_allison(self):
        gh = FakeGitHub(issues=[issue(10, "job")], comments={10: [
            comment(self.NO_PR, at=180, updated=40),
            comment(f"restarted\n\n{sw.REBUILT_MARK}", at=120),
        ]})
        s = sweep(gh)
        self.assertEqual(gh.dispatches(), [])
        self.assertIn("needs-allison", gh.labels(10))
        self.assertTrue(gh.comment_bodies(10)[-1].startswith("Recommend: "))
        self.assertIn("needs-allison", s.actions[0])
        gh.calls.clear()
        sweep(gh)
        self.assertEqual(gh.writes(), [], "a needs-allison job is not restarted again")

    def test_a_rebuild_still_on_its_way_is_not_escalated(self):
        gh = FakeGitHub(issues=[issue(10, "job")], comments={10: [
            comment(self.NO_PR, at=180),
            comment(f"restarted\n\n{sw.REBUILT_MARK}", at=120),
        ]})
        sweep(gh)
        self.assertEqual(gh.dispatches(), [10], "the rebuild never ran, so it is sent again")
        self.assertNotIn("needs-allison", gh.labels(10))

    def test_removing_needs_allison_allows_one_more_rebuild(self):
        gh = FakeGitHub(issues=[issue(10, "job")], comments={10: [
            comment(self.NO_PR, at=180, updated=90),
            comment(f"restarted\n\n{sw.REBUILT_MARK}", at=120),
            comment(f"Recommend: look\n\n{sw.NO_PR_RETURNED_MARK}", at=60),
        ]}, events={10: [removed_needs_allison(at=30)]})
        sweep(gh)
        self.assertEqual(gh.dispatches(), [10])
        self.assertIn(sw.REBUILT_MARK, gh.comment_bodies(10)[-1])

    def test_the_recommendation_is_posted_before_the_label(self):
        gh = FakeGitHub(issues=[issue(10, "job")], comments={10: [
            comment(self.NO_PR, at=180, updated=40),
            comment(f"restarted\n\n{sw.REBUILT_MARK}", at=120),
        ]})
        sweep(gh)
        writes = [c[1] for c in gh.writes()]
        self.assertEqual(writes, [f"/repos/{REPO}/issues/10/comments", f"/repos/{REPO}/issues/10/labels"])

    def test_a_failed_label_write_is_finished_by_the_next_sweep(self):
        gh = FakeGitHub(issues=[issue(10, "job")], comments={10: [
            comment(self.NO_PR, at=180, updated=40),
            comment(f"restarted\n\n{sw.REBUILT_MARK}", at=120),
        ]})
        real_post = failing_label_writes(gh)
        s = sw.Sweeper(gh, sw.Config(repo=REPO, builder_workflow=WORKFLOW, ref="main"), NOW)
        with contextlib.redirect_stdout(io.StringIO()):
            s.sweep()
        self.assertTrue(s.errors, "the failed label write is reported")
        self.assertTrue(gh.comment_bodies(10)[-1].startswith("Recommend: "), "Allison is told first")
        self.assertNotIn("needs-allison", gh.labels(10))
        gh.post = real_post
        gh.calls.clear()
        s = sweep(gh)
        self.assertEqual(gh.dispatches(), [], "the job is not rebuilt")
        self.assertIn("needs-allison", gh.labels(10))
        self.assertEqual(sum(b.startswith("Recommend: ") for b in gh.comment_bodies(10)), 1, "one recommendation")
        self.assertIn("needs-allison", s.actions[0])


class Rule5StuckInProgress(unittest.TestCase):
    def board(self, label_at, runs=(), jobs=None, logs=None):
        return FakeGitHub(
            issues=[issue(11, "job", "in-progress")],
            events={11: [{"event": "labeled", "label": {"name": "in-progress"}, "created_at": ago(label_at)}]},
            runs=runs, jobs=jobs, logs=logs,
        )

    def test_quiet_for_45_minutes_is_restarted(self):
        gh = self.board(50)
        s = sweep(gh)
        self.assertNotIn("in-progress", gh.labels(11))
        self.assertEqual(gh.dispatches(), [11])
        delete = next(i for i, c in enumerate(gh.writes()) if c[0] == "DELETE")
        dispatch = next(i for i, c in enumerate(gh.writes()) if c[1].endswith("/dispatches"))
        self.assertLess(delete, dispatch, "the label goes before the dispatch, so the new build keeps its own")
        self.assertIn("50 minutes", s.actions[0])

    def test_not_yet_45_minutes(self):
        gh = self.board(20)
        sweep(gh)
        self.assertEqual(gh.writes(), [])

    def test_a_run_in_progress_holds_it(self):
        gh = self.board(120, runs=[run(6, status="in_progress", started=60)],
                        jobs={6: [{"id": 60, "name": "builder / gate", "status": "completed", "conclusion": "success"}]},
                        logs={60: "  OVERLAP_ISSUE: 11\n"})
        sweep(gh)
        self.assertEqual(gh.writes(), [])

    def test_a_run_that_ended_recently_restarts_the_clock(self):
        gh = self.board(120, runs=[run(6, started=60, updated=10)],
                        jobs={6: [{"id": 60, "name": "builder / gate", "status": "completed", "conclusion": "success"}]},
                        logs={60: "  OVERLAP_ISSUE: 11\n"})
        sweep(gh)
        self.assertEqual(gh.writes(), [])


class Rule6CodexReview(unittest.TestCase):
    def board(self, committed=40, comments=(), reviews=(), draft=False):
        return FakeGitHub(
            issues=[issue(12, "job")],
            prs=[pr(60, 12, draft=draft, created=90)],
            comments={60: list(comments), 12: []},
            commits={HEAD: {"commit": {"committer": {"date": ago(committed)}}}},
            reviews={60: list(reviews)},
        )

    def test_asks_codex_once_per_head(self):
        gh = self.board()
        s = sweep(gh)
        self.assertEqual(len(gh.comment_bodies(60)), 1)
        self.assertTrue(gh.comment_bodies(60)[0].startswith("@codex review"))
        self.assertIn(HEAD, gh.comment_bodies(60)[0])
        self.assertIn("40 minutes", s.actions[0])
        gh.calls.clear()
        sweep(gh)
        self.assertEqual(gh.writes(), [], "the second sweep sees its own comment for this head")

    def test_new_head_gets_a_new_ask(self):
        gh = self.board(comments=[comment(f"@codex review\n\n<!-- {sw.MARK} codex-review head={NEW_HEAD} -->")])
        sweep(gh)
        self.assertEqual(len(gh.comment_bodies(60)), 2)

    def test_too_soon(self):
        gh = self.board(committed=10)
        sweep(gh)
        self.assertEqual(gh.writes(), [])

    def test_codex_already_reviewed_the_head(self):
        state = comment('<!-- codex-review-state:v1 {"code_review": {"commit_sha": "%s", "status": "completed"}} -->' % HEAD,
                        login="chatgpt-codex-connector[bot]")
        receipt = comment(f"<!-- codex-review-receipt:v1 -->\nCodex Review: Didn't find any major issues\n**Reviewed commit:** `{HEAD[:10]}`",
                          login="chatgpt-codex-connector[bot]")
        review = {"user": {"login": "chatgpt-codex-connector[bot]"}, "commit_id": HEAD}
        for kwargs in ({"comments": [state]}, {"comments": [receipt]}, {"reviews": [review]}):
            gh = self.board(**kwargs)
            sweep(gh)
            self.assertEqual(gh.writes(), [], kwargs)

    def test_draft_is_not_nudged(self):
        gh = self.board(draft=True)
        sweep(gh)
        self.assertEqual(gh.writes(), [])


class Rule6CodexAcknowledgement(unittest.TestCase):
    """A review request is delivered only when the Codex connector acknowledges it."""

    def board(self, comments=(), reactions=None, head=HEAD):
        return FakeGitHub(
            issues=[issue(12, "job")],
            prs=[pr(60, 12, head=head, created=90)],
            comments={60: list(comments), 12: []},
            commits={head: {"commit": {"committer": {"date": ago(40)}}}},
            reactions=reactions,
            connector=True,
        )

    @staticmethod
    def ask(sha=HEAD, attempt=1, at=20, cid=601):
        tag = f" attempt={attempt}" if attempt > 1 else ""
        return comment(f"@codex review\n\n<!-- {sw.MARK} codex-review head={sha}{tag} -->", cid=cid, at=at)

    def asks(self, gh):
        return [b for b in gh.comment_bodies(60) if b.startswith("@codex review")]

    def blockers(self, gh):
        return [b for b in gh.comment_bodies(60) if b.startswith("Review service blocker")]

    def test_a_request_from_a_bot_identity_is_ignored_and_not_counted_as_delivered(self):
        gh = self.board()
        sweep(gh)
        self.assertEqual(len(self.asks(gh)), 1)
        posted = gh.comments[60][-1]
        self.assertTrue(posted["user"]["login"].endswith("[bot]"))
        self.assertEqual(gh.reactions.get(posted["id"], []), [], "the connector ignores a bot's request")
        gh.calls.clear()
        s = sweep(gh, later=10)
        self.assertTrue(any(c[1].endswith(f"/issues/comments/{posted['id']}/reactions") for c in gh.calls),
                        "the sweeper checks for the acknowledgement instead of assuming it")
        self.assertEqual(len(self.asks(gh)), 2, "an ignored request is not marked done")
        self.assertIn("did not acknowledge", s.actions[0])
        self.assertIn("github-actions[bot]", s.actions[0])

    def test_an_acknowledged_request_is_not_asked_again(self):
        gh = self.board(comments=[self.ask()], reactions={601: [codex_eyes()]})
        for later in (0, 10, 60):
            sweep(gh, later=later)
            self.assertEqual(gh.writes(), [], f"once per head, {later} minutes later")

    def test_a_review_state_comment_for_the_head_is_an_acknowledgement(self):
        state = comment('<!-- codex-review-state:v1 {"code_review": {"commit_sha": "%s", "status": "running"}} -->' % HEAD,
                        login="chatgpt-codex-connector[bot]")
        gh = self.board(comments=[self.ask(), state])
        sweep(gh, later=30)
        self.assertEqual(gh.writes(), [])
        self.assertFalse(any(c[1].endswith("/reactions") for c in gh.calls), "no reaction read is needed")

    def test_an_unacknowledged_request_is_retried_once_then_reported_as_a_blocker(self):
        gh = self.board()
        sweep(gh)
        self.assertEqual(len(self.asks(gh)), 1)
        self.assertIn(f"codex-review head={HEAD} -->", self.asks(gh)[0])
        # The next sweep finds no acknowledgement and asks once more.
        s = sweep(gh, later=10)
        self.assertEqual(len(self.asks(gh)), 2)
        self.assertIn(f"codex-review head={HEAD} attempt=2 -->", self.asks(gh)[1])
        self.assertEqual(self.blockers(gh), [])
        self.assertIn("asked Codex again", s.actions[0])
        # The retry is ignored too, so the sweep after reports a blocker instead of asking again.
        s = sweep(gh, later=20)
        self.assertEqual(len(self.asks(gh)), 2, "retried only once")
        blockers = self.blockers(gh)
        self.assertEqual(len(blockers), 1)
        self.assertIn(f"head `{HEAD[:7]}`", blockers[0])
        self.assertIn("github-actions[bot]", blockers[0])
        self.assertIn(f"codex-blocked head={HEAD}", blockers[0])
        self.assertIn("review service blocker", s.actions[0])
        self.assertEqual(gh.dispatches(), [])
        # Reported once; later sweeps leave it alone.
        gh.calls.clear()
        sweep(gh, later=30)
        self.assertEqual(gh.writes(), [])

    def test_the_retry_waits_for_the_acknowledgement_window(self):
        gh = self.board(comments=[self.ask(at=2)])
        sweep(gh)
        self.assertEqual(gh.writes(), [])
        self.assertFalse(any(c[1].endswith("/reactions") for c in gh.calls))

    def test_a_late_acknowledgement_of_the_first_request_stops_the_blocker(self):
        gh = self.board(comments=[self.ask(at=30), self.ask(attempt=2, at=20, cid=602)],
                        reactions={601: [codex_eyes()]})
        sweep(gh)
        self.assertEqual(gh.writes(), [])

    def test_a_codex_review_on_the_head_stops_the_retry(self):
        gh = self.board(comments=[self.ask()])
        gh.reviews[60] = [{"user": {"login": "chatgpt-codex-connector[bot]"}, "commit_id": HEAD}]
        sweep(gh)
        self.assertEqual(gh.writes(), [])

    def test_a_new_head_after_a_blocker_starts_over(self):
        blocked = comment(f"Review service blocker: x\n\n<!-- {sw.MARK} codex-blocked head={HEAD} -->", cid=603, at=30)
        gh = self.board(comments=[self.ask(at=50), self.ask(attempt=2, at=40, cid=602), blocked], head=NEW_HEAD)
        sweep(gh)
        self.assertEqual(len(self.asks(gh)), 3)
        self.assertIn(f"codex-review head={NEW_HEAD} -->", self.asks(gh)[-1])


class Rule7Refused(unittest.TestCase):
    REVIEWED = comment('<!-- codex-review-state:v1 {"code_review": {"commit_sha": "%s"}} -->' % HEAD,
                       login="chatgpt-codex-connector[bot]")

    def board(self, reasons, issue_comments=(), threads=(), runs=(), jobs=None, logs=None, labels=("job",)):
        return FakeGitHub(
            issues=[issue(13, *labels)],
            prs=[pr(70, 13)],
            comments={70: [self.REVIEWED, refusal(HEAD, *reasons)], 13: list(issue_comments)},
            threads={70: list(threads)},
            runs=runs, jobs=jobs, logs=logs,
        )

    def test_failing_check_is_sent_back_with_what_to_fix(self):
        gh = self.board(["Check `brand + classification lint (changed files)` finished as failure.",
                         "Codex has not reviewed head aaaaaaa yet (its last code review covered no commit)."])
        s = sweep(gh)
        self.assertEqual(gh.dispatches(), [13])
        body = gh.comment_bodies(13)[0]
        self.assertIn("finished as failure", body)
        self.assertNotIn("has not reviewed", body, "only what the builder can fix is listed")
        self.assertIn("#70", s.actions[0])
        self.assertFalse(any(c[0] == "GRAPHQL" for c in gh.calls), "no Codex reason, no thread read")

    def test_unresolved_codex_findings_are_listed(self):
        gh = self.board([finding_reason(GUARD_T1)],
                        threads=[thread("T1", "tools/x.py", "Guard the empty list"),
                                 thread("T0", "tools/y.py", "Old one", resolved=True)])
        sweep(gh)
        body = gh.comment_bodies(13)[0]
        self.assertIn("`tools/x.py`: guard the empty list", body)
        self.assertNotIn("old one", body)
        self.assertEqual(gh.dispatches(), [13])

    def test_pending_reasons_are_not_a_stall(self):
        gh = self.board(["Check `ci` is in_progress, not completed.",
                         "GitHub is still computing whether the pull request can merge."])
        sweep(gh)
        self.assertEqual(gh.writes(), [])

    def test_a_recent_builder_run_holds_it(self):
        gh = self.board(["Check `ci` finished as failure."], runs=[run(8, started=15)],
                        jobs={8: [{"id": 80, "name": "builder / gate", "status": "completed", "conclusion": "success"}]},
                        logs={80: "OVERLAP_ISSUE: 13"})
        sweep(gh)
        self.assertEqual(gh.writes(), [])

    def test_a_finding_that_comes_back_goes_to_allison(self):
        first = self.board([finding_reason(GUARD_T1)],
                           threads=[thread("T1", "tools/x.py", "Guard the empty list")])
        sweep(first)
        asked = first.comment_bodies(13)[0]
        # The builder fixed it and resolved T1; Codex then raised the same finding again as T2 on a new head.
        gh = FakeGitHub(
            issues=[issue(13, "job")],
            prs=[pr(70, 13, head=NEW_HEAD)],
            comments={70: [refusal(NEW_HEAD, finding_reason(GUARD_T2, NEW_HEAD))],
                      13: [comment(asked)]},
            threads={70: [thread("T1", "tools/x.py", "Guard the empty list", resolved=True),
                          thread("T2", "tools/x.py", "Guard the empty list")]},
            commits={NEW_HEAD: {"commit": {"committer": {"date": ago(5)}}}},
        )
        s = sweep(gh)
        self.assertEqual(gh.dispatches(), [], "rule 7 stops instead of looping")
        self.assertIn("needs-allison", gh.labels(13))
        self.assertTrue(gh.comment_bodies(13)[-1].startswith("Recommend: "))
        self.assertIn("needs-allison", s.actions[0])
        gh.calls.clear()
        sweep(gh)
        self.assertEqual(gh.writes(), [], "a needs-allison job is not restarted again")

    def test_a_finding_still_open_on_its_old_thread_is_sent_back_again(self):
        first = self.board([finding_reason(GUARD_T1)],
                           threads=[thread("T1", "tools/x.py", "Guard the empty list")])
        sweep(first)
        gh = FakeGitHub(
            issues=[issue(13, "job")],
            prs=[pr(70, 13, head=NEW_HEAD)],
            comments={70: [refusal(NEW_HEAD, finding_reason(GUARD_T1, NEW_HEAD, raised=HEAD))],
                      13: [comment(first.comment_bodies(13)[0])]},
            threads={70: [thread("T1", "tools/x.py", "Guard the empty list")]},
            commits={NEW_HEAD: {"commit": {"committer": {"date": ago(5)}}}},
        )
        sweep(gh)
        self.assertEqual(gh.dispatches(), [13])
        self.assertNotIn("needs-allison", gh.labels(13))

    def test_a_second_thread_beside_a_still_open_first_one_is_sent_back(self):
        first = self.board([finding_reason(GUARD_T1)],
                           threads=[thread("T1", "tools/x.py", "Guard the empty list")])
        sweep(first)
        gh = FakeGitHub(
            issues=[issue(13, "job")],
            prs=[pr(70, 13, head=NEW_HEAD)],
            comments={70: [refusal(NEW_HEAD, finding_reason(GUARD_T1, NEW_HEAD, raised=HEAD),
                                   finding_reason(GUARD_T2, NEW_HEAD))],
                      13: [comment(first.comment_bodies(13)[0])]},
            threads={70: [thread("T1", "tools/x.py", "Guard the empty list"),
                          thread("T2", "tools/x.py", "Guard the empty list")]},
            commits={NEW_HEAD: {"commit": {"committer": {"date": ago(5)}}}},
        )
        sweep(gh)
        self.assertEqual(gh.dispatches(), [13], "nothing was fixed, so nothing came back")
        self.assertNotIn("needs-allison", gh.labels(13))
        self.assertFalse(any(b.startswith("Recommend: ") for b in gh.comment_bodies(13)))

    def test_a_recorded_thread_that_is_gone_is_not_proof_of_a_fix(self):
        first = self.board([finding_reason(GUARD_T1)],
                           threads=[thread("T1", "tools/x.py", "Guard the empty list")])
        sweep(first)
        gh = FakeGitHub(
            issues=[issue(13, "job")],
            prs=[pr(70, 13, head=NEW_HEAD)],
            comments={70: [refusal(NEW_HEAD, finding_reason(GUARD_T2, NEW_HEAD))],
                      13: [comment(first.comment_bodies(13)[0])]},
            threads={70: [thread("T2", "tools/x.py", "Guard the empty list")]},
            commits={NEW_HEAD: {"commit": {"committer": {"date": ago(5)}}}},
        )
        sweep(gh)
        self.assertEqual(gh.dispatches(), [13])
        self.assertNotIn("needs-allison", gh.labels(13))

    def test_removing_needs_allison_after_a_return_sends_it_back(self):
        first = self.board([finding_reason(GUARD_T1)],
                           threads=[thread("T1", "tools/x.py", "Guard the empty list")])
        sweep(first)

        def board():
            return FakeGitHub(
                issues=[issue(13, "job")],
                prs=[pr(70, 13, head=NEW_HEAD)],
                comments={70: [refusal(NEW_HEAD, finding_reason(GUARD_T2, NEW_HEAD))],
                          13: [comment(first.comment_bodies(13)[0])]},
                threads={70: [thread("T1", "tools/x.py", "Guard the empty list", resolved=True),
                              thread("T2", "tools/x.py", "Guard the empty list")]},
                commits={NEW_HEAD: {"commit": {"committer": {"date": ago(5)}}}},
            )
        gh = board()
        sweep(gh)
        self.assertIn("needs-allison", gh.labels(13))
        escalated = gh.comments[13]
        # Allison decides and removes needs-allison.
        gh = board()
        gh.comments[13] = list(escalated)
        gh.events[13] = [removed_needs_allison()]
        s = sweep(gh)
        self.assertEqual(gh.dispatches(), [13])
        self.assertNotIn("needs-allison", gh.labels(13))
        self.assertFalse(any("needs-allison" in a for a in s.actions), "no action it did not take")

    def test_a_failed_label_write_after_a_return_is_finished_by_the_next_sweep(self):
        first = self.board([finding_reason(GUARD_T1)],
                           threads=[thread("T1", "tools/x.py", "Guard the empty list")])
        sweep(first)
        gh = FakeGitHub(
            issues=[issue(13, "job")],
            prs=[pr(70, 13, head=NEW_HEAD)],
            comments={70: [refusal(NEW_HEAD, finding_reason(GUARD_T2, NEW_HEAD))],
                      13: [comment(first.comment_bodies(13)[0])]},
            threads={70: [thread("T1", "tools/x.py", "Guard the empty list", resolved=True),
                          thread("T2", "tools/x.py", "Guard the empty list")]},
            commits={NEW_HEAD: {"commit": {"committer": {"date": ago(5)}}}},
        )
        real_post = failing_label_writes(gh)
        s = sw.Sweeper(gh, sw.Config(repo=REPO, builder_workflow=WORKFLOW, ref="main"), NOW)
        with contextlib.redirect_stdout(io.StringIO()):
            s.sweep()
        self.assertTrue(s.errors)
        self.assertTrue(gh.comment_bodies(13)[-1].startswith("Recommend: "), "Allison is told first")
        self.assertNotIn("needs-allison", gh.labels(13))
        gh.post = real_post
        gh.calls.clear()
        s = sweep(gh)
        self.assertEqual(gh.dispatches(), [], "the builder is not restarted")
        self.assertIn("needs-allison", gh.labels(13))
        self.assertEqual(sum(b.startswith("Recommend: ") for b in gh.comment_bodies(13)), 1, "one recommendation")
        self.assertIn("needs-allison", s.actions[0])

    UNREADABLE = [
        gate.unexplained("code", HEAD, [], None),
        gate.codex_problems({"code_review": {"commit_sha": HEAD, "status": "completed", "has_unresolved_findings": True}},
                            HEAD, None)[0],
    ]

    def test_review_evidence_the_gate_cannot_read_does_not_restart_the_builder(self):
        for reason in self.UNREADABLE:
            gh = self.board([reason], threads=[thread("T0", "tools/y.py", "Old one", resolved=True)])
            sweep(gh)
            self.assertEqual(gh.writes(), [], reason)

    def test_a_p2_finding_never_restarts_the_builder(self):
        p2 = gate.Finding(1, "code", "P2", HEAD, "Nit", "https://example.invalid/1")
        self.assertEqual(gate.blocking_findings([p2], HEAD, None)[0], [], "the gate does not block on a P2")
        gh = self.board(gate.codex_problems(
            {"code_review": {"commit_sha": HEAD, "status": "completed", "has_unresolved_findings": True}},
            HEAD, lambda: ([p2], None)))
        sweep(gh)
        self.assertEqual(gh.writes(), [])

    def test_a_finding_on_the_head_whose_thread_was_resolved_is_still_sent_back(self):
        resolved = thread("T1", "tools/x.py", "Guard the empty list", resolved=True)
        gh = self.board([finding_reason(resolved)], threads=[resolved])
        sweep(gh)
        self.assertEqual(gh.dispatches(), [13], "resolving a thread does not fix the code")
        self.assertIn("`tools/x.py`: guard the empty list", gh.comment_bodies(13)[0])

    def test_a_failing_check_beside_unreadable_evidence_is_still_sent_back(self):
        gh = self.board(["Check `ci` finished as failure.", *self.UNREADABLE])
        sweep(gh)
        self.assertEqual(gh.dispatches(), [13])
        body = gh.comment_bodies(13)[0]
        self.assertIn("finished as failure", body)
        self.assertNotIn("severity", body)

    def test_security_findings_on_one_file_have_their_own_titles(self):
        body = ("<!-- codex-security-review-finding:v1 -->\n\n### 🛡️ Codex Security Review · _Automatically triggered_\n\n"
                "**<sub><sub>![P2 Badge](https://img.shields.io/badge/P2-yellow?style=flat)</sub></sub> "
                "Security: Authenticate PRs before suppressing recovery**\n\nDetails.")
        self.assertEqual(sw.finding_title(body), "security: authenticate prs before suppressing recovery")

    def test_refusal_for_an_older_head_is_ignored(self):
        gh = FakeGitHub(issues=[issue(13, "job")], prs=[pr(70, 13, head=NEW_HEAD)],
                        comments={70: [self.REVIEWED, refusal(HEAD, "Check `ci` finished as failure.")], 13: []},
                        commits={NEW_HEAD: {"commit": {"committer": {"date": ago(5)}}}})
        sweep(gh)
        self.assertEqual(gh.writes(), [])


class Safety(unittest.TestCase):
    """Acceptance check 2: no merge, push, settings, rulesets or access, no parked job, no ember."""

    def test_ember_is_refused_before_any_call(self):
        for repo in ("ExpertPartners/ember", "someone/Ember"):
            gh = FakeGitHub(issues=[issue(7)])
            s = sweep(gh, repo=repo)
            self.assertEqual(gh.calls, [], repo)
            self.assertEqual(s.actions, [])

    def test_main_refuses_ember_without_a_token(self):
        env = {"GITHUB_REPOSITORY": "ExpertPartners/ember"}
        with mock.patch.dict(os.environ, env, clear=True), contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(sw.main([]), 0)
        self.assertIn("excluded", out.getvalue())

    def test_parked_job_and_its_pull_request_are_never_touched(self):
        gh = FakeGitHub(
            issues=[issue(14, "job", "in-progress", "parked")],
            prs=[pr(80, 14)],
            comments={80: [refusal(HEAD, "Check `ci` finished as failure.")]},
            events={14: [{"event": "labeled", "label": {"name": "in-progress"}, "created_at": ago(300)}]},
        )
        sweep(gh)
        self.assertEqual(gh.writes(), [])
        self.assertFalse(any("/80/" in c[1] or "/14/" in c[1] for c in gh.calls), "not even read")

    def test_a_pull_request_from_a_fork_or_a_stranger_never_holds_a_job(self):
        fork = {**pr(81, 16, author="stranger"), "head": {"ref": "job/16-x", "sha": HEAD, "repo": {"full_name": "stranger/fork"}}}
        gh = FakeGitHub(issues=[issue(16, "job")], prs=[fork])
        sweep(gh)
        self.assertEqual(gh.dispatches(), [16], "the idle job is still restarted")
        self.assertFalse(sw.is_builder_pr(fork, REPO))
        self.assertTrue(sw.is_builder_pr(pr(82, 16), REPO))
        self.assertTrue(sw.is_builder_pr({**pr(83, 16, author=ALLISON)}, REPO), "a branch in this repo needs write access")

    def test_a_network_error_becomes_a_github_error(self):
        import urllib.error
        client = sw.GitHub("t", "https://example.invalid")
        with mock.patch.object(sw.urllib.request, "urlopen", side_effect=urllib.error.URLError("reset")):
            with self.assertRaises(sw.GitHubError):
                client.get("/x")
        with mock.patch.object(sw.urllib.request, "urlopen", side_effect=TimeoutError("slow")):
            with self.assertRaises(sw.GitHubError):
                client.get("/x")

    def test_write_allowlist(self):
        s = sw.Sweeper(FakeGitHub(), sw.Config(repo=REPO, builder_workflow=WORKFLOW), NOW)
        refused = [
            ("PUT", f"/repos/{REPO}/pulls/1/merge", {"merge_method": "squash"}),
            ("POST", f"/repos/{REPO}/git/refs", {"ref": "refs/heads/x", "sha": HEAD}),
            ("PATCH", f"/repos/{REPO}/git/refs/heads/main", {"sha": HEAD}),
            ("PUT", f"/repos/{REPO}/contents/a.py", {"content": ""}),
            ("PATCH", f"/repos/{REPO}", {"allow_auto_merge": True}),
            ("POST", f"/repos/{REPO}/rulesets", {}),
            ("PUT", f"/repos/{REPO}/collaborators/x", {}),
            ("PUT", f"/repos/{REPO}/branches/main/protection", {}),
            ("PATCH", f"/repos/{REPO}/issues/1", {"title": "x"}),
            ("PATCH", f"/repos/{REPO}/issues/1", {"state": "closed", "state_reason": "not_planned"}),
            ("POST", f"/repos/{REPO}/issues/1/labels", {"labels": ["done"]}),
            ("DELETE", f"/repos/{REPO}/issues/1/labels/parked", None),
            ("POST", f"/repos/{REPO}/actions/workflows/x.yml/dispatches", {"ref": "main", "inputs": {"issue": "1", "x": "y"}}),
            ("POST", "/repos/other/repo/issues/1/comments", {"body": "x"}),
            ("PUT", f"/repos/{REPO}/pulls/1/update-branch", {}),
        ]
        for method, path, body in refused:
            with self.assertRaises(sw.RefusedWrite, msg=f"{method} {path}"):
                s.write(1, method, path, body)

    def test_the_fake_has_no_way_to_merge_or_push(self):
        # FakeGitHub has no put method and checks every write it receives (see _check), so
        # every board in this file proves the sweeper only labels, comments, closes and
        # dispatches.
        self.assertFalse(hasattr(FakeGitHub(), "put"))
        with self.assertRaises(AssertionError):
            FakeGitHub().post(f"/repos/{REPO}/git/refs", {})


class OneDispatchPerIssue(unittest.TestCase):
    """Acceptance check 3."""

    def test_two_refused_pull_requests_for_one_job_dispatch_it_once(self):
        gh = FakeGitHub(
            issues=[issue(15, "job")],
            prs=[pr(90, 15), {**pr(91, 15), "head": {"ref": "job/15-again", "sha": HEAD, "repo": {"full_name": REPO}}}],
            comments={90: [Rule7Refused.REVIEWED, refusal(HEAD, "Check `ci` finished as failure.")],
                      91: [Rule7Refused.REVIEWED, refusal(HEAD, "Check `ci` finished as failure.")], 15: []},
        )
        sweep(gh)
        self.assertEqual(gh.dispatches(), [15])

    def test_a_dispatched_run_for_the_issue_holds_it(self):
        gh = FakeGitHub(issues=[issue(16, "job")], runs=[run(9, status="in_progress", started=45)],
                        jobs={9: [{"id": 90, "name": "builder / gate", "status": "completed", "conclusion": "success"}]},
                        logs={90: "##[group]Run python3 x\nenv:\n  OVERLAP_ISSUE: 16\n"})
        sweep(gh)
        self.assertEqual(gh.writes(), [])

    def test_a_queued_dispatch_that_names_no_issue_yet_holds_every_dispatch(self):
        gh = FakeGitHub(issues=[issue(16, "job"), issue(17)], runs=[run(9, status="queued", started=1)], jobs={9: []})
        s = sweep(gh)
        self.assertEqual(gh.writes(), [])
        self.assertTrue(any("has not named its job" in n for n in s.notes))

    def test_a_run_for_another_issue_does_not_hold_this_one(self):
        gh = FakeGitHub(issues=[issue(16, "job")], runs=[run(9, status="in_progress", started=5)],
                        jobs={9: [{"id": 90, "name": "builder / gate", "status": "completed", "conclusion": "success"}]},
                        logs={90: "OVERLAP_ISSUE: 99"})
        sweep(gh)
        self.assertEqual(gh.dispatches(), [16])

    def test_old_finished_runs_are_never_mapped(self):
        gh = FakeGitHub(issues=[issue(16, "job")], runs=[run(9, started=150, updated=100)])
        sweep(gh)
        self.assertEqual(gh.dispatches(), [16])
        self.assertFalse(any("/actions/runs/9/" in c[1] or "/logs" in c[1] for c in gh.calls),
                         "a run no rule can use costs no API call")

    def test_many_stalled_jobs_each_go_once(self):
        gh = FakeGitHub(issues=[issue(n, "job") for n in (18, 19, 20)] + [issue(21)])
        sweep(gh)
        self.assertEqual(sorted(gh.dispatches()), [18, 19, 20, 21])


class DryRun(unittest.TestCase):
    """Acceptance check 4."""

    def test_dry_run_reports_and_writes_nothing(self):
        gh = FakeGitHub(
            issues=[issue(7), issue(10, "job"), issue(9, "job", "waiting")],
            comments={9: [comment("<!-- factory-overlap-check:v1 -->\nWaiting on #40, same file")]},
            extra=[{**issue(40), "state": "closed"}],
        )
        s = sweep(gh, dry_run=True)
        self.assertEqual(gh.writes(), [])
        self.assertEqual(len(s.actions), 3)
        summary = sw.summarize(s)
        self.assertTrue(all(line.startswith("Would: ") for line in summary.splitlines()[:-1]))
        self.assertIn("Nothing was changed", summary)

    def test_main_writes_the_run_summary(self):
        gh = FakeGitHub(issues=[issue(10, "job")])
        with tempfile.TemporaryDirectory() as tmp:
            summary = os.path.join(tmp, "summary.md")
            env = {"GITHUB_REPOSITORY": REPO, "SWEEPER_TOKEN": "t", "SWEEPER_BUILDER_WORKFLOW": WORKFLOW,
                   "SWEEPER_REF": "main", "SWEEPER_DRY_RUN": "true", "GITHUB_STEP_SUMMARY": summary}
            with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(sw, "GitHub", return_value=gh), \
                    contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(sw.main([]), 0)
            with open(summary, encoding="utf-8") as fh:
                written = fh.read()
        self.assertIn("Would: #10 dispatched", written)
        self.assertIn("1 action would be taken", out.getvalue())
        self.assertEqual(gh.writes(), [])


class GateFormat(unittest.TestCase):
    def test_reads_the_gate_refusal_it_was_written_for(self):
        reasons = ["Check `ci` finished as failure.", finding_reason(GUARD_T1)]
        self.assertEqual(sw.gate_refusal([refusal(HEAD, *reasons)], HEAD), reasons)
        self.assertIsNone(sw.gate_refusal([refusal(HEAD, *reasons)], NEW_HEAD))

    def test_fixable_reasons_match_the_gate_wording(self):
        old = "c" * 40
        on_head = gate.Finding(1, "code", "P1", HEAD, "Guard it", "https://example.invalid/1")
        open_thread = gate.Finding(2, "code", "P0", old, "Old one", "https://example.invalid/2", resolved=False)
        unreadable = gate.Finding(3, "code", None, HEAD, "No badge", "https://example.invalid/3")
        security = gate.Finding(4, "security", "P1", HEAD, "Security: check it", "https://example.invalid/4")
        state = {"code_review": {"commit_sha": HEAD, "status": "completed", "has_unresolved_findings": True},
                 "security_review": {"commit_sha": HEAD, "has_unresolved_findings": True}}
        reasons = gate.codex_problems(state, HEAD, lambda: ([on_head, open_thread, unreadable, security], None))
        self.assertEqual(len(reasons), 4, reasons)
        for r in reasons:
            self.assertTrue(sw.is_codex_reason(r), r)
            self.assertIsNotNone(sw.REASON_TITLE_RE.match(r), r)
        self.assertEqual(sw.REASON_TITLE_RE.match(reasons[0]).groups(), ("Guard it", "https://example.invalid/1"))
        may_be_open = gate.Finding(5, "code", "P1", old, "Unknown", "https://example.invalid/5")
        self.assertFalse(sw.is_codex_reason(gate.blocking_findings([may_be_open], HEAD, "its review thread was not found")[0][0]))
        self.assertFalse(sw.is_codex_reason(gate.unexplained("code", HEAD, [], None)))
        self.assertFalse(sw.is_codex_reason(gate.codex_problems(None, HEAD)[0]))
        self.assertFalse(sw.is_check_reason(gate.mergeable_problems({"mergeable": None})[0]))


class Workflows(unittest.TestCase):
    def read(self, name):
        with open(os.path.join(ROOT, ".github", "workflows", name), encoding="utf-8") as fh:
            return fh.read()

    def test_caller_runs_every_10_minutes_and_by_hand_with_dry_run(self):
        text = self.read("factory-stall-sweeper.yml")
        self.assertIn('cron: "*/10 * * * *"', text)
        self.assertIn("workflow_dispatch:", text)
        self.assertIn("dry_run:", text)
        self.assertIn("uses: ./.github/workflows/factory-stall-sweeper-reusable.yml", text)
        self.assertIn(f"builder_workflow: {WORKFLOW}", text)

    def test_reusable_never_gets_contents_write_and_skips_ember(self):
        for name in ("factory-stall-sweeper.yml", "factory-stall-sweeper-reusable.yml"):
            text = "\n".join(line for line in self.read(name).splitlines() if not line.lstrip().startswith("#"))
            self.assertNotIn("contents: write", text, name)
            self.assertNotIn("administration", text, name)
            self.assertNotIn("secrets.", text, name)
        text = self.read("factory-stall-sweeper-reusable.yml")
        self.assertIn("workflow_call:", text)
        self.assertIn("!endsWith(github.repository, '/ember')", text)
        self.assertIn("sparse-checkout: tools/stall-sweeper", text)
        self.assertIn("ref: main", text)
        self.assertIn("SWEEPER_TOKEN: ${{ github.token }}", text)


if __name__ == "__main__":
    unittest.main()
