"""Unit tests for the builder overlap check. Every GitHub call goes to FakeGitHub; nothing
touches the network.

Run from the repo root: python3 -m unittest discover -s tools/overlap-check/tests -v
"""

import importlib.util
import io
import json
import os
import random
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest import mock

HERE = os.path.dirname(__file__)
spec = importlib.util.spec_from_file_location("overlap_check", os.path.join(HERE, "..", "overlap_check.py"))
oc = importlib.util.module_from_spec(spec)
# dataclasses resolves annotations through sys.modules, so register before executing.
sys.modules["overlap_check"] = oc
spec.loader.exec_module(oc)

REPO = "ExpertPartners/expert-partners-skills"
BOT = {"login": "factory-droid[bot]", "id": 123, "type": "Bot", "html_url": "https://github.com/apps/factory-droid"}
DEFAULT_HEAD = "a" * 40
CFG = oc.Config(repo=REPO, settle_seconds=0)
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
NEVER_ASK = (
    "Never ask the user inside Factory. Put any question on the GitHub issue as a comment starting Q"
    "uestion for Allison, or on the job list as needs-allison with a line starting Recommend:, and keep working on everything else."
)


def job_body(*paths):
    lines = ["Goal: Factory never stalls", "", "## Mission", "Do a thing.", "", "## Files in scope"]
    lines += [f"- `{p}`" for p in paths]
    lines += ["", "## Acceptance checks", "- `tools/validate-job.sh` prints `validate-job: PASS`."]
    return "\n".join(lines)


def pr(number, files, closes=None, author="factory-droid[bot]", ref=None):
    return oc.Holder(number, "pr", list(files), {closes} if closes else set()), {
        "number": number,
        "user": {"login": author},
        "head": {"ref": ref or f"job/{closes or number}-work", "sha": f"{number:040x}", "repo": {"full_name": REPO}},
        "base": {"ref": "main", "repo": {"full_name": REPO}},
        "body": f"Closes #{closes}\n\nwork" if closes else "work",
        "files": list(files),
    }


def merged_pr(number, closes, merged_at="2026-11-04T01:21:00Z", ref=None):
    _, p = pr(number, ["tools/a.py"], closes=closes, ref=ref)
    return dict(p, state="closed", merged_at=merged_at, merge_commit_sha=f"{number:040x}"[::-1])


class FakeGitHub:
    """Holds issues, pull requests and comments, and answers the calls overlap_check makes."""

    def __init__(self, issues=(), prs=(), closed_prs=()):
        self.issues = {i["number"]: dict(i, labels=[{"name": n} for n in i.get("labels", [])]) for i in issues}
        self.prs = list(prs)  # open
        self.closed_prs = list(closed_prs)  # closed or merged, with merged_at when merged
        self.timeline = {}  # issue -> extra timeline events, such as reopened
        self.comments = {}
        self.calls = []
        self.next_comment_id = 100
        self.on_sleep = None
        self.runs = {}  # run id -> status, or a GitHubError to raise
        # run id -> the build job's status, None when the run lists no build job yet, or a
        # GitHubError to raise. A run not named here has a build job in the run's status.
        self.builds = {}
        self.activities = {}
        self.refs = {}
        # head sha -> compare status against any base, or an exception to raise. A head not
        # named here diverged from the base, so it does not contain it.
        self.compares = {}

    def get(self, path, params=None):
        self.calls.append(("GET", path, params))
        if path == "/users/factory-droid%5Bbot%5D":
            return dict(BOT)
        if path == f"/repos/{REPO}":
            return {"default_branch": "main"}
        if path == f"/repos/{REPO}/activity":
            branch = params["ref"].removeprefix("refs/heads/")
            if branch in self.activities:
                value = self.activities[branch]
                if isinstance(value, Exception):
                    raise value
                return value
            p = next(p for p in self.prs if p["head"]["ref"] == branch)
            return [{"ref": params["ref"], "after": p["head"]["sha"], "actor": dict(BOT), "activity_type": "branch_creation"}]
        if "/compare/" in path:
            base, head = path.split("/compare/", 1)[1].split("...")
            value = self.compares.get(head, "diverged")
            if isinstance(value, Exception):
                raise value
            return {"status": value, "base_commit": {"sha": base}}
        if "/git/ref/heads/" in path:
            branch = oc.urllib.parse.unquote(path.split("/git/ref/heads/", 1)[1])
            sha = self.refs.get(branch)
            if sha is None:
                sha = DEFAULT_HEAD if branch == "main" else next(p["head"]["sha"] for p in self.prs if p["head"]["ref"] == branch)
            return {"ref": f"refs/heads/{branch}", "object": {"sha": sha}}
        if "/actions/runs/" in path:
            jobs = path.endswith("/jobs")
            number = int(path.split("/actions/runs/", 1)[1].split("/")[0])
            status = self.runs.get(number)
            if status is None:
                raise oc.GitHubError(404, "Not Found")
            if isinstance(status, oc.GitHubError):
                raise status
            if not jobs:
                return {"id": number, "status": status}
            build = self.builds.get(number, status)
            if isinstance(build, oc.GitHubError):
                raise build
            listed = [{"name": "builder / gate", "status": "completed"},
                      {"name": "builder / release", "status": "queued"}]
            if build is not None:
                listed.insert(1, {"name": "builder / build", "status": build})
            return {"total_count": len(listed), "jobs": listed}
        if path.startswith(f"/repos/{REPO}/pulls/"):
            number = int(path.rsplit("/", 1)[-1])
            found = next((p for p in self.prs + self.closed_prs if p["number"] == number), None)
            if found is None:
                raise oc.GitHubError(404, "Not Found")
            return {k: v for k, v in found.items() if k != "files"}
        number = int(path.rsplit("/", 1)[-1])
        if number not in self.issues:
            raise oc.GitHubError(404, "Not Found")
        return self.issues[number]

    def paginate(self, path, params=None):
        self.calls.append(("GET", path, params))
        params = params or {}
        if path == f"/repos/{REPO}/pulls":
            return [{k: v for k, v in p.items() if k != "files"} for p in self.prs]
        if path.startswith(f"/repos/{REPO}/pulls/") and path.endswith("/files"):
            number = int(path.split("/")[-2])
            p = next(p for p in self.prs if p["number"] == number)
            return [{"filename": f} for f in p["files"]]
        if path == f"/repos/{REPO}/issues":
            want = set(params.get("labels", "").split(","))
            state = params.get("state", "open")
            found = [i for i in self.issues.values() if want <= {label["name"] for label in i["labels"]}
                     and state in ("all", i.get("state", "open"))]
            return sorted(found, key=lambda i: i["number"])
        if path.endswith("/comments"):
            return [dict(c) for c in self.comments.get(int(path.split("/")[-2]), [])]
        if path.endswith("/timeline"):
            # GitHub records a cross-reference on the issue for every pull request naming it.
            number = int(path.split("/")[-2])
            events = [{"event": "cross-referenced", "source": {"type": "issue", "issue": {
                "number": p["number"], "body": p["body"], "pull_request": {"url": "x"},
                "repository": {"full_name": REPO}}}}
                for p in self.prs + self.closed_prs if number in oc.closes(p.get("body"))]
            return events + list(self.timeline.get(number, []))
        raise oc.GitHubError(404, f"Not Found: {path}")

    def post(self, path, body):
        self.calls.append(("POST", path, body))
        parts = path.split("/")
        if path.endswith("/labels"):
            issue = self.issues[int(parts[-2])]
            have = {label["name"] for label in issue["labels"]}
            issue["labels"] += [{"name": n} for n in body["labels"] if n not in have]
        elif path.endswith("/comments"):
            self.next_comment_id += 1
            made = {"id": self.next_comment_id, "user": {"login": "github-actions[bot]"}, "body": body["body"]}
            self.comments.setdefault(int(parts[-2]), []).append(made)
            return dict(made)
        return {}

    def patch(self, path, body):
        self.calls.append(("PATCH", path, body))
        cid = int(path.rsplit("/", 1)[-1])
        for comments in self.comments.values():
            for c in comments:
                if c["id"] == cid:
                    c["body"] = body["body"]
        return {}

    def delete(self, path):
        self.calls.append(("DELETE", path, None))
        parts = path.split("/")
        if "/issues/comments/" in path:
            cid = int(parts[-1])
            for number, comments in self.comments.items():
                if any(c["id"] == cid for c in comments):
                    self.comments[number] = [c for c in comments if c["id"] != cid]
                    return None
            raise oc.GitHubError(404, "Not Found")
        issue = self.issues[int(parts[-3])]
        name = parts[-1]
        if name not in {label["name"] for label in issue["labels"]}:
            raise oc.GitHubError(404, "Label does not exist")
        issue["labels"] = [label for label in issue["labels"] if label["name"] != name]
        return None

    def labels(self, number):
        return {label["name"] for label in self.issues[number]["labels"]}

    def comment_bodies(self, number):
        return [c["body"] for c in self.comments.get(number, [])]

    def writes(self):
        return [c for c in self.calls if c[0] != "GET"]


def issue(number, *paths, labels=("job",)):
    return {"number": number, "body": job_body(*paths), "labels": list(labels)}


class GitHubDiagnostics(unittest.TestCase):
    def test_http_error_reports_only_method_and_path_as_request_context(self):
        endpoint = f"https://api.github.com/repos/{REPO}/issues/237/labels?private=query-value"
        failure = oc.urllib.error.HTTPError(endpoint, 403, "Forbidden", {},
                                            io.BytesIO(b'{"message":"Resource not accessible by integration"}'))
        client = oc.GitHub("credential-must-never-appear")
        with mock.patch.object(oc.urllib.request, "urlopen", side_effect=failure):
            with self.assertRaises(oc.GitHubError) as caught:
                client._request("POST", endpoint, {"private": "body-must-never-appear"})
        diagnostic = str(caught.exception)
        self.assertEqual(caught.exception.status, 403)
        self.assertIn(f"HTTP 403 POST /repos/{REPO}/issues/237/labels:", diagnostic)
        for private in ("query-value", "body-must-never-appear", "credential-must-never-appear", "Authorization", "https://"):
            self.assertNotIn(private, diagnostic)


class ParseScope(unittest.TestCase):
    def test_markdown_heading_with_backticks_and_new_marks(self):
        body = job_body(".github/workflows/a.yml", "tools/overlap-check/") + "\n"
        body = body.replace("`tools/overlap-check/`", "`tools/overlap-check/` (new)")
        self.assertEqual(oc.parse_scope(body), [".github/workflows/a.yml", "tools/overlap-check/"])

    def test_template_without_headings_numbered_with_trailing_notes(self):
        body = "\n".join([
            "Files in scope",
            "1. plugins/x/skills/y/SKILL.md, new, beside z",
            "2. plugins/x/.claude-plugin/plugin.json, version only",
            "3. plugins/x/references/ for any reference pages",
            "",
            "Acceptance checks",
            "1. something/else.md must not be read",
        ])
        self.assertEqual(oc.parse_scope(body), [
            "plugins/x/skills/y/SKILL.md", "plugins/x/.claude-plugin/plugin.json", "plugins/x/references/"])

    def test_prose_and_branch_names_are_not_paths(self):
        body = "\n".join([
            "## Files in scope",
            "- Files already changed on `job/141-business-brain-foundations`",
            "- `.claude-plugin/marketplace.json`",
            "- changelog for operating-doctrine if the repo keeps one",
            "## Acceptance checks",
        ])
        self.assertEqual(oc.parse_scope(body), [".claude-plugin/marketplace.json"])

    def test_bold_section_labels_end_the_scope(self):
        body = "\n".join([
            "**Files in scope**",
            "- `tools/release/notes.py`",
            "",
            "**Acceptance checks**",
            "1. `tools/validate-job.sh` prints `validate-job: PASS`.",
            "**Decisions already made**",
            "- Follow `AGENTS.md`",
        ])
        self.assertEqual(oc.parse_scope(body), ["tools/release/notes.py"])

    def test_bold_label_with_the_colon_inside(self):
        for heading in ("**Files in scope:**", "**Files in scope**:", "__Files in scope__", "### Files in scope:"):
            body = "\n".join([heading, "- `a/b.py`", "**Acceptance checks:**", "- `c/d.py`"])
            self.assertEqual(oc.parse_scope(body), ["a/b.py"], heading)

    def test_directory_without_a_trailing_slash_is_kept(self):
        body = "\n".join([
            "## Files in scope",
            "- `tools/auto-merge-gate`",
            "- skills/brand-voice for the voice notes",
            "- See https://example.com/a/b",
            "## Acceptance checks",
        ])
        self.assertEqual(oc.parse_scope(body), ["tools/auto-merge-gate", "skills/brand-voice"])

    def test_no_scope_section(self):
        self.assertEqual(oc.parse_scope("## Mission\nNothing listed."), [])
        self.assertEqual(oc.parse_scope(None), [])


class PathsOverlap(unittest.TestCase):
    def test_rules(self):
        self.assertTrue(oc.paths_overlap("a/b.py", "a/b.py"))
        self.assertTrue(oc.paths_overlap("tools/x/", "tools/x/tests/t.py"))
        self.assertTrue(oc.paths_overlap("tools/x/tests/t.py", "tools/x/"))
        self.assertTrue(oc.paths_overlap("plugins/*/plugin.json", "plugins/a/plugin.json"))
        self.assertTrue(oc.paths_overlap("plugin.json", "plugins/a/.claude-plugin/plugin.json"))
        self.assertFalse(oc.paths_overlap("tools/x", "tools/xy/a.py"))
        self.assertFalse(oc.paths_overlap("tools/x/a.py", "tools/x/b.py"))
        self.assertFalse(oc.paths_overlap("README.md", "tools/x/README.md"), "only shared files match by name")

    def test_directory_named_without_a_trailing_slash(self):
        self.assertTrue(oc.paths_overlap("tools/auto-merge-gate", "tools/auto-merge-gate/gate.py"))
        self.assertTrue(oc.paths_overlap("skills/brand-voice/SKILL.md", "skills/brand-voice"))
        self.assertFalse(oc.paths_overlap("tools/auto-merge-gate", "tools/auto-merge-gate-two/a.py"))

    def test_shared_files(self):
        for p in ("plugins/a/.claude-plugin/plugin.json", ".claude-plugin/marketplace.json",
                  "plugins/a/CHANGELOG.md", "AGENTS.md", "tools/x/package-lock.json", "uv.lock"):
            self.assertTrue(oc.is_shared(p), p)
        self.assertFalse(oc.is_shared("tools/x/gate.py"))


class Evaluate(unittest.TestCase):
    def test_no_overlap_starts(self):
        a, _ = pr(10, ["tools/auto-merge-gate/gate.py"], closes=155)
        other = oc.Holder(160, "issue", [".github/CODEOWNERS"])
        v = oc.evaluate(158, ["tools/overlap-check/"], [a], [other])
        self.assertTrue(v.start)
        self.assertEqual(v.lines(), [])

    def test_ordinary_overlap_with_an_open_pull_request_waits(self):
        a, _ = pr(156, ["tools/auto-merge-gate/gate.py", "tools/auto-merge-gate/README.md"], closes=155)
        v = oc.evaluate(159, ["tools/auto-merge-gate/gate.py", "tools/release/"], [a], [])
        self.assertFalse(v.start)
        self.assertEqual(v.lines(), ["Waiting on #156, same file"])
        self.assertEqual(v.overlaps[0].paths, ["tools/auto-merge-gate/gate.py"])
        self.assertEqual(v.overlaps[0].shared, [])

    def test_ordinary_overlap_with_an_in_progress_job_waits(self):
        other = oc.Holder(155, "issue", ["tools/auto-merge-gate/tests/"])
        v = oc.evaluate(159, ["tools/auto-merge-gate/tests/test_release.py"], [], [other])
        self.assertFalse(v.start)
        self.assertEqual(v.lines(), ["Waiting on #155, same file"])

    def test_shared_file_overlap_waits_and_is_named_shared(self):
        a, _ = pr(147, ["plugins/research-ops/skills/source-hunter/scripts/stitch.py",
                        ".claude-plugin/marketplace.json"], closes=146)
        v = oc.evaluate(141, ["plugins/operating-doctrine/skills/bbf/SKILL.md", ".claude-plugin/marketplace.json"], [a], [])
        self.assertFalse(v.start)
        self.assertEqual(v.lines(), ["Waiting on #147, same file"])
        self.assertEqual(v.overlaps[0].shared, [".claude-plugin/marketplace.json"])
        body = oc.comment_body(v)
        self.assertIn("Waiting on #147, same file", body.splitlines())
        self.assertIn("`.claude-plugin/marketplace.json` (shared file)", body)

    def test_shared_file_named_without_its_directory_still_collides(self):
        other = oc.Holder(154, "issue", ["plugin.json"])
        v = oc.evaluate(159, ["plugins/research-ops/.claude-plugin/plugin.json"], [], [other])
        self.assertEqual(v.lines(), ["Waiting on #154, same file"])

    def test_changeset_notes_only_collide_on_the_same_note(self):
        other = oc.Holder(188, "issue", [".changeset/", ".changeset/188-build-standard.md"])
        v = oc.evaluate(189, [".changeset/", ".changeset/189-job-list-heartbeat.md"], [], [other])
        self.assertTrue(v.start, "separate note files in .changeset/ never hold each other")
        same = oc.Holder(190, "issue", [".changeset/189-job-list-heartbeat.md"])
        v = oc.evaluate(189, [".changeset/189-job-list-heartbeat.md"], [], [same])
        self.assertEqual(v.lines(), ["Waiting on #190, same file"])

    def test_changeset_folder_spellings_never_hold_each_other(self):
        other = oc.Holder(188, "issue", [".changeset/**", ".changeset/*.md"])
        v = oc.evaluate(189, [".changeset/", ".changeset/*.md"], [], [other])
        self.assertTrue(v.start)

    def test_changeset_readme_still_collides_with_the_folder(self):
        other = oc.Holder(188, "issue", [".changeset/README.md"])
        v = oc.evaluate(189, [".changeset/"], [], [other])
        self.assertEqual(v.lines(), ["Waiting on #188, same file"])

    def test_agents_md_is_shared(self):
        a = oc.Holder(152, "pr", ["AGENTS.md"], {151})
        v = oc.evaluate(157, ["AGENTS.md", ".github/workflows/questions-to-job-list.yml"], [a], [oc.Holder(151, "issue", ["AGENTS.md"])])
        self.assertEqual(v.lines(), ["Waiting on #152, same file"], "the issue behind #152 is not named twice")
        self.assertEqual(v.overlaps[0].shared, ["AGENTS.md"])

    def test_every_blocker_is_named(self):
        a = oc.Holder(152, "pr", ["AGENTS.md"], {151})
        other = oc.Holder(159, "issue", ["AGENTS.md", "tools/release/"])
        v = oc.evaluate(157, ["AGENTS.md"], [a], [other])
        self.assertEqual(v.lines(), ["Waiting on #152, same file", "Waiting on #159, same file"])

    def test_own_pull_request_and_own_issue_never_block(self):
        own = oc.Holder(142, "pr", ["plugins/operating-doctrine/CHANGELOG.md"], {141, 153})
        me = oc.Holder(153, "issue", ["plugins/operating-doctrine/CHANGELOG.md"])
        v = oc.evaluate(153, ["plugins/operating-doctrine/CHANGELOG.md"], [own], [me])
        self.assertTrue(v.start)

    def test_five_or_more_open_pull_requests_do_not_hold_a_job(self):
        # Decision Log 2026-11-02, No caps stop work: only a file collision holds a build.
        for count in (5, 6, 12):
            prs = [oc.Holder(n, "pr", [f"tools/t{n}/a.py"], {n + 100}) for n in range(1, count + 1)]
            v = oc.evaluate(158, ["tools/overlap-check/"], prs, [])
            self.assertTrue(v.start, count)
            self.assertEqual(v.lines(), [])
            self.assertEqual(v.open_prs, count)
            self.assertNotIn("open pull requests", oc.comment_body(v))

    def test_many_open_pull_requests_hold_only_on_overlap(self):
        prs = [oc.Holder(n, "pr", [f"tools/t{n}/a.py"], {n + 100}) for n in range(1, 8)]
        v = oc.evaluate(158, ["tools/t3/a.py"], prs, [])
        self.assertFalse(v.start)
        self.assertEqual(v.lines(), ["Waiting on #3, same file"])
        self.assertNotIn("Waiting, this repo has", oc.comment_body(v))


class BuilderPullRequests(unittest.TestCase):
    def test_which_pull_requests_are_builder_ones(self):
        self.assertTrue(oc.is_builder_pr({"user": {"login": "factory-droid[bot]"}, "head": {"ref": "fix"}}))
        self.assertTrue(oc.is_builder_pr({"user": {"login": "AllisonGaddy"}, "head": {"ref": "job/12-x"}}))
        self.assertFalse(oc.is_builder_pr({"user": {"login": "AllisonGaddy"}, "head": {"ref": "fix"}}))

    def test_people_pull_requests_neither_block_nor_count(self):
        _, mine = pr(20, ["tools/overlap-check/x.py"], author="AllisonGaddy", ref="allison/tweak")
        prs = [pr(n, [f"tools/t{n}/a.py"], closes=n + 100)[1] for n in range(1, 5)]
        gh = FakeGitHub([issue(158, "tools/overlap-check/")], prs + [mine])
        self.assertTrue(oc.run_check(gh, CFG, 158, sleep=lambda s: None))

    def test_closes_reads_every_keyword(self):
        self.assertEqual(oc.closes("Closes #153\nCloses #141\nfixes #2, resolves #3"), {153, 141, 2, 3})


class RunCheck(unittest.TestCase):
    def test_clear_job_is_labeled_in_progress_and_loses_waiting(self):
        gh = FakeGitHub([issue(158, "tools/overlap-check/", labels=("job", "waiting"))])
        self.assertTrue(oc.run_check(gh, CFG, 158, sleep=lambda s: None))
        self.assertEqual(gh.labels(158), {"job", "in-progress"})
        self.assertEqual(gh.comment_bodies(158), [], "a clear job gets no new comment")

    def test_held_job_is_labeled_waiting_with_one_comment(self):
        _, blocker = pr(156, ["tools/auto-merge-gate/gate.py"], closes=155)
        gh = FakeGitHub([issue(159, "tools/auto-merge-gate/gate.py")], [blocker])
        self.assertFalse(oc.run_check(gh, CFG, 159, sleep=lambda s: None))
        self.assertEqual(gh.labels(159), {"job", "waiting"})
        bodies = gh.comment_bodies(159)
        self.assertEqual(len(bodies), 1)
        self.assertEqual(bodies[0].splitlines()[1], "Waiting on #156, same file")

        # Checked again with nothing changed: no second comment, no edit.
        before = len(gh.writes())
        self.assertFalse(oc.run_check(gh, CFG, 159, sleep=lambda s: None))
        self.assertEqual(len(gh.comment_bodies(159)), 1)
        self.assertFalse([c for c in gh.writes()[before:] if c[0] in ("PATCH",) or c[1].endswith("/comments")])

    def test_waiting_comment_is_edited_when_the_reason_changes_and_on_start(self):
        _, blocker = pr(156, ["tools/auto-merge-gate/gate.py"], closes=155)
        gh = FakeGitHub([issue(159, "tools/auto-merge-gate/gate.py")], [blocker])
        oc.run_check(gh, CFG, 159, sleep=lambda s: None)
        gh.prs = [pr(163, ["tools/auto-merge-gate/gate.py"], closes=160)[1]]
        self.assertFalse(oc.run_check(gh, CFG, 159, sleep=lambda s: None))
        self.assertEqual(len(gh.comment_bodies(159)), 1)
        self.assertIn("Waiting on #163, same file", gh.comment_bodies(159)[0])
        self.assertNotIn("Waiting on #156, same file", gh.comment_bodies(159)[0])
        gh.prs = []
        self.assertTrue(oc.run_check(gh, CFG, 159, sleep=lambda s: None))
        self.assertEqual(len(gh.comment_bodies(159)), 1)
        self.assertIn("Started.", gh.comment_bodies(159)[0])
        self.assertEqual(gh.labels(159), {"job", "in-progress"})

    def test_a_job_held_after_an_earlier_start_drops_in_progress(self):
        _, blocker = pr(156, ["AGENTS.md"], closes=151)
        gh = FakeGitHub([issue(157, "AGENTS.md", labels=("job", "in-progress"))], [blocker])
        self.assertFalse(oc.run_check(gh, CFG, 157, sleep=lambda s: None))
        self.assertEqual(gh.labels(157), {"job", "waiting"})

    def test_two_jobs_judged_at_once_only_the_older_builds(self):
        # Both runs take their first look before either is labeled in-progress, so both
        # see a clear path. Each run's pause is when the other run's label lands.
        newer = FakeGitHub([issue(157, "AGENTS.md"), issue(159, "AGENTS.md")])
        self.assertFalse(oc.run_check(newer, CFG, 159, sleep=lambda s: newer.post(
            f"/repos/{REPO}/issues/157/labels", {"labels": ["in-progress"]})))
        self.assertEqual(newer.labels(159), {"job", "waiting"})
        self.assertIn("Waiting on #157, same file", newer.comment_bodies(159)[0])

        older = FakeGitHub([issue(157, "AGENTS.md"), issue(159, "AGENTS.md")])
        self.assertTrue(oc.run_check(older, CFG, 157, sleep=lambda s: older.post(
            f"/repos/{REPO}/issues/159/labels", {"labels": ["in-progress"]})))
        self.assertEqual(older.labels(157), {"job", "in-progress"})

    def test_a_job_already_building_holds_an_older_one(self):
        gh = FakeGitHub([issue(157, "AGENTS.md"), issue(159, "AGENTS.md", labels=("job", "in-progress"))])
        self.assertFalse(oc.run_check(gh, CFG, 157, sleep=lambda s: None))
        self.assertIn("Waiting on #159, same file", gh.comment_bodies(157)[0])

    def test_a_started_build_records_its_run_in_one_comment(self):
        cfg = oc.Config(repo=REPO, settle_seconds=0, run_id="9001")
        gh = FakeGitHub([issue(201, "tools/overlap-check/")])
        self.assertTrue(oc.run_check(gh, cfg, 201, sleep=lambda s: None))
        self.assertEqual(len(gh.comment_bodies(201)), 1)
        self.assertIn("Started.", gh.comment_bodies(201)[0])
        self.assertEqual(oc.recorded_run(gh, cfg, 201), "9001")
        # A later build records its own run in the same comment.
        gh.issues[201]["labels"] = [{"name": "job"}]
        self.assertTrue(oc.run_check(gh, oc.Config(repo=REPO, settle_seconds=0, run_id="9002"), 201,
                                     sleep=lambda s: None))
        self.assertEqual(len(gh.comment_bodies(201)), 1)
        self.assertEqual(oc.recorded_run(gh, cfg, 201), "9002")

    def test_issue_with_no_scope_starts(self):
        gh = FakeGitHub([{"number": 170, "body": "## Mission\nNo list.", "labels": ["job"]}])
        self.assertTrue(oc.run_check(gh, CFG, 170, sleep=lambda s: None))


class RunNext(unittest.TestCase):
    def test_dispatches_the_oldest_waiting_job_that_can_start(self):
        _, blocker = pr(156, ["tools/auto-merge-gate/gate.py"], closes=155)
        gh = FakeGitHub([
            issue(159, "tools/auto-merge-gate/gate.py", labels=("job", "waiting")),
            issue(161, "tools/other/a.py", labels=("job", "waiting")),
            issue(162, "tools/more/a.py", labels=("job", "waiting")),
            issue(163, "tools/unrelated/a.py", labels=("job",)),
        ], [blocker])
        sent = []
        self.assertEqual(oc.run_next(gh, CFG, sent.append), [161, 162])
        self.assertEqual(sent, [161, 162], "every waiting job that can start is sent")
        self.assertEqual(gh.writes(), [
            ("DELETE", f"/repos/{REPO}/issues/161/labels/waiting", None),
            ("DELETE", f"/repos/{REPO}/issues/162/labels/waiting", None),
        ], "next writes nothing but the claims")
        self.assertEqual(gh.labels(159), {"job", "waiting"})

    def test_two_colliding_waiting_jobs_are_not_sent_together(self):
        gh = FakeGitHub([
            issue(159, "AGENTS.md", labels=("job", "waiting")),
            issue(161, "AGENTS.md", labels=("job", "waiting")),
        ])
        sent = []
        self.assertEqual(oc.run_next(gh, CFG, sent.append), [159])
        self.assertEqual(gh.labels(161), {"job", "waiting"})

    def test_a_job_another_run_already_claimed_is_not_sent_again(self):
        gh = FakeGitHub([issue(159, "tools/a.py", labels=("job", "waiting"))])
        sent = []
        # Both runs list #159 as waiting before either claims it.
        listing = gh.paginate(f"/repos/{REPO}/issues", {"labels": "job,waiting"})
        self.assertEqual(oc.run_next(gh, CFG, sent.append), [159])
        with mock.patch.object(gh, "paginate", side_effect=lambda path, params=None: (
                listing if path == f"/repos/{REPO}/issues" and "waiting" in (params or {}).get("labels", "")
                else FakeGitHub.paginate(gh, path, params))):
            self.assertEqual(oc.run_next(gh, CFG, sent.append), [])
        self.assertEqual(sent, [159], "the second run finds the claim gone and sends nothing")

    def test_a_failed_dispatch_puts_the_claim_back(self):
        gh = FakeGitHub([issue(159, "tools/a.py", labels=("job", "waiting"))])

        def fail(number):
            raise oc.GitHubError(500, "boom")

        with self.assertRaises(oc.GitHubError):
            oc.run_next(gh, CFG, fail)
        self.assertEqual(gh.labels(159), {"job", "waiting"})

    def test_starts_again_once_the_blocking_pull_request_closes(self):
        _, blocker = pr(156, ["tools/overlap-check/overlap_check.py"], closes=155)
        others = [pr(n, [f"tools/t{n}/a.py"], closes=n + 100)[1] for n in range(1, 7)]
        gh = FakeGitHub([issue(158, "tools/overlap-check/", labels=("job", "waiting"))], others + [blocker])
        sent = []
        self.assertEqual(oc.run_next(gh, CFG, sent.append), [])
        gh.prs = others  # #156 merged; six other open pull requests do not hold it
        self.assertEqual(oc.run_next(gh, CFG, sent.append), [158])
        self.assertEqual(sent, [158])

    def test_workflow_file_from_ref(self):
        self.assertEqual(
            oc.workflow_file("ExpertPartners/x/.github/workflows/factory-chat-to-code-loop-builder-skills.yml@refs/heads/main"),
            "factory-chat-to-code-loop-builder-skills.yml")


class StoppedJobs(unittest.TestCase):
    """Only a job that is truly building holds files. Closed, parked and done jobs hold
    nothing, whatever other labels they carry (Nov 3: #179 sat behind parked #201, and
    merged jobs kept in-progress beside done)."""

    OTHER_LABELS = (("job", "in-progress"), ("job", "in-progress", "waiting"), ("in-progress", "needs-allison"))

    def test_a_closed_issue_never_holds_files(self):
        for labels in self.OTHER_LABELS:
            closed = dict(issue(130, "tools/overlap-check/", labels=labels), state="closed")
            self.assertFalse(oc.holds_files(dict(closed, labels=[{"name": n} for n in labels])), labels)
            gh = FakeGitHub([closed, issue(179, "tools/overlap-check/overlap_check.py")])
            self.assertEqual(oc.in_progress_issues(gh, CFG), [], labels)
            self.assertTrue(oc.run_check(gh, CFG, 179, sleep=lambda s: None), labels)
            self.assertEqual(gh.labels(179), {"job", "in-progress"})

    def test_a_parked_issue_never_holds_files(self):
        for labels in self.OTHER_LABELS:
            parked = issue(201, "tools/overlap-check/", labels=labels + ("parked",))
            self.assertFalse(oc.holds_files(dict(parked, labels=[{"name": n} for n in parked["labels"]])), labels)
            gh = FakeGitHub([parked, issue(179, "tools/overlap-check/overlap_check.py")])
            self.assertEqual(oc.in_progress_issues(gh, CFG), [], labels)
            self.assertTrue(oc.run_check(gh, CFG, 179, sleep=lambda s: None), labels)

    def test_a_done_issue_never_holds_files(self):
        for labels in self.OTHER_LABELS:
            done = issue(206, "tools/overlap-check/", labels=labels + ("done",))
            self.assertFalse(oc.holds_files(dict(done, labels=[{"name": n} for n in done["labels"]])), labels)
            gh = FakeGitHub([done, issue(179, "tools/overlap-check/overlap_check.py")])
            self.assertEqual(oc.in_progress_issues(gh, CFG), [], labels)
            self.assertTrue(oc.run_check(gh, CFG, 179, sleep=lambda s: None), labels)

    def test_an_open_in_progress_job_still_holds_files(self):
        building = issue(205, "tools/overlap-check/", labels=("job", "in-progress"))
        self.assertTrue(oc.holds_files(dict(building, labels=[{"name": n} for n in building["labels"]])))
        gh = FakeGitHub([building, issue(179, "tools/overlap-check/overlap_check.py")])
        self.assertFalse(oc.run_check(gh, CFG, 179, sleep=lambda s: None))
        self.assertIn("Waiting on #205, same file", gh.comment_bodies(179)[0])

    def test_179_waiting_on_parked_201_is_sent_by_the_restart(self):
        scope = "tools/overlap-check/overlap_check.py"
        gh = FakeGitHub([
            dict(issue(130, scope, labels=("job", "in-progress", "done")), state="closed"),
            issue(164, scope, labels=("job", "in-progress", "done")),
            issue(179, scope, labels=("job", "waiting")),
            issue(201, scope, labels=("job", "in-progress", "parked")),
        ])
        sent = []
        self.assertEqual(oc.run_next(gh, CFG, sent.append), [179])
        self.assertEqual(sent, [179], "its only blockers are closed, parked or done")
        self.assertEqual(gh.writes(), [("DELETE", f"/repos/{REPO}/issues/179/labels/waiting", None)])

        # The same board with #201 really building still holds #179.
        gh = FakeGitHub([issue(179, scope, labels=("job", "waiting")),
                         issue(201, scope, labels=("job", "in-progress"))])
        self.assertEqual(oc.run_next(gh, CFG, [].append), [])

    def test_a_parked_or_done_waiting_job_is_not_sent(self):
        for label in ("parked", "done"):
            gh = FakeGitHub([issue(201, "tools/a.py", labels=("job", "waiting", label))])
            sent = []
            self.assertEqual(oc.run_next(gh, CFG, sent.append), [], label)
            self.assertEqual(gh.writes(), [], label)
            self.assertIn("waiting", gh.labels(201))

    def test_a_waiting_job_is_sent_once_parked_or_done_is_removed(self):
        for label in ("parked", "done"):
            gh = FakeGitHub([issue(201, "tools/a.py", labels=("job", "waiting", label))])
            self.assertEqual(oc.run_next(gh, CFG, [].append), [], label)
            gh.issues[201]["labels"] = [{"name": "job"}, {"name": "waiting"}]
            sent = []
            self.assertEqual(oc.run_next(gh, CFG, sent.append), [201], label)
            self.assertEqual(sent, [201], label)

    def test_a_closed_parked_or_done_job_never_builds(self):
        # Building a stopped job would let a colliding job build beside it unseen, since a
        # stopped job holds no files.
        boards = {
            "closed": dict(issue(201, "tools/a.py", labels=("job", "waiting")), state="closed"),
            "parked": issue(201, "tools/a.py", labels=("job", "waiting", "parked")),
            "done": issue(201, "tools/a.py", labels=("job", "in-progress", "done")),
        }
        for kind, stopped in boards.items():
            gh = FakeGitHub([stopped])
            before = gh.labels(201)
            self.assertFalse(oc.run_check(gh, CFG, 201, sleep=lambda s: None), kind)
            self.assertEqual(gh.writes(), [], kind)
            self.assertEqual(gh.labels(201), before, kind)

    def test_label_names_are_read_without_regard_to_case(self):
        building = {"number": 205, "labels": [{"name": "Job"}, {"name": "In-Progress"}]}
        self.assertTrue(oc.holds_files(building))
        parked = {"number": 201, "labels": [{"name": "In-Progress"}, {"name": "Parked"}]}
        self.assertFalse(oc.holds_files(parked))
        gh = FakeGitHub([issue(201, "tools/a.py", labels=("job", "Done"))])
        self.assertFalse(oc.run_check(gh, CFG, 201, sleep=lambda s: None))
        self.assertEqual(gh.writes(), [])

    def test_an_open_builder_pull_request_still_holds_its_files(self):
        # The pull request is the real collision guard, even when its job issue is parked or done.
        _, blocker = pr(211, ["tools/overlap-check/overlap_check.py"], closes=201)
        gh = FakeGitHub([
            issue(179, "tools/overlap-check/overlap_check.py", labels=("job", "waiting")),
            issue(201, "tools/overlap-check/", labels=("job", "in-progress", "parked")),
        ], [blocker])
        self.assertEqual(oc.run_next(gh, CFG, [].append), [])
        self.assertFalse(oc.run_check(gh, CFG, 179, sleep=lambda s: None))
        self.assertEqual(gh.comment_bodies(179)[0].splitlines()[1], "Waiting on #211, same file")


class ParkedWhileBuilding(unittest.TestCase):
    """Parking a job, or marking it done, does not stop a build already running for it. Its
    files stay held until that build can no longer write, and only then does waiting work
    start."""

    SCOPE = "tools/overlap-check/overlap_check.py"

    def start_201(self, label):
        cfg = oc.Config(repo=REPO, settle_seconds=0, run_id="9001")
        gh = FakeGitHub([issue(179, self.SCOPE, labels=("job", "waiting")), issue(201, "tools/overlap-check/")])
        self.assertTrue(oc.run_check(gh, cfg, 201, sleep=lambda s: None))
        gh.runs[9001] = "in_progress"
        gh.post(f"/repos/{REPO}/issues/201/labels", {"labels": [label]})
        return gh

    def test_a_parked_or_done_build_still_running_holds_until_its_release(self):
        for label in ("parked", "done"):
            gh = self.start_201(label)
            # The redispatch that marking #201 starts sends nothing while #201 still builds.
            self.assertEqual(oc.run_next(gh, CFG, [].append), [], label)
            self.assertEqual(gh.labels(179), {"job", "waiting"}, label)
            self.assertFalse(oc.run_check(gh, CFG, 179, sleep=lambda s: None), label)
            self.assertIn("Waiting on #201, same file", gh.comment_bodies(179)[0], label)

            # The build job ends. The release runs in the same workflow run, which is still
            # in progress, and frees #201 so the restart it starts sends #179.
            self.assertEqual(oc.run_release(gh, CFG, 201, "success"), "stopped", label)
            self.assertNotIn("in-progress", gh.labels(201), label)
            self.assertNotIn("waiting", gh.labels(201), label)
            self.assertIn("holds no files", gh.comment_bodies(201)[0], label)
            sent = []
            self.assertEqual(oc.run_next(gh, CFG, sent.append), [179], label)
            self.assertEqual(sent, [179], label)

    def test_a_parked_build_with_its_pull_request_still_releases_in_progress(self):
        gh = self.start_201("parked")
        gh.prs = [pr(214, ["tools/overlap-check/README.md"], closes=201)[1]]
        self.assertEqual(oc.run_release(gh, CFG, 201, "success"), "stopped")
        self.assertNotIn("in-progress", gh.labels(201))
        self.assertEqual(oc.run_next(gh, CFG, [].append), [179], "the pull request holds only its own files")

    def test_a_run_that_ended_without_its_release_holds_nothing(self):
        gh = self.start_201("parked")
        gh.runs[9001] = "completed"
        self.assertEqual(oc.run_next(gh, CFG, [].append), [179])

    def test_a_run_that_cannot_be_read_keeps_holding(self):
        gh = self.start_201("parked")
        gh.runs[9001] = oc.GitHubError(403, "Resource not accessible by integration")
        self.assertEqual(oc.run_next(gh, CFG, [].append), [])
        gh.runs.pop(9001)  # a deleted run is gone and writes nothing
        self.assertEqual(oc.run_next(gh, CFG, [].append), [179])

    def test_a_job_parked_during_the_pause_does_not_build(self):
        cfg = oc.Config(repo=REPO, settle_seconds=0, run_id="9001")
        gh = FakeGitHub([issue(201, "tools/overlap-check/")])
        self.assertFalse(oc.run_check(gh, cfg, 201, sleep=lambda s: gh.post(
            f"/repos/{REPO}/issues/201/labels", {"labels": ["parked"]})))
        self.assertEqual(gh.labels(201), {"job", "parked"})
        self.assertIsNone(oc.recorded_run(gh, cfg, 201))

    def test_a_restart_runs_after_the_release_of_a_stopped_job(self):
        gh = self.start_201("parked")
        code, out = Main.run_main(self, gh, ["release"], OVERLAP_ISSUE="201", GITHUB_RUN_ID="9001", BUILD_RESULT="success")
        self.assertEqual((code, out), (0, "restart=true\n"))
        # A release that keeps in-progress, because the job's own pull request holds its
        # files, frees nothing and restarts nothing.
        _, own = pr(166, ["tools/a.py"], closes=159)
        kept = FakeGitHub([issue(159, "tools/a.py", labels=("job", "in-progress"))], [own])
        code, out = Main.run_main(self, kept, ["release"], OVERLAP_ISSUE="159", BUILD_RESULT="success")
        self.assertEqual((code, out), (0, "restart=false\n"))


class ActiveWriter(unittest.TestCase):
    """Only GitHub Actions state proves a writer has stopped: the recorded run is gone or
    completed, or its latest build job is completed. Whether the issue is open, closed,
    parked or done says nothing about whether its droid can still push."""

    SCOPE = "tools/overlap-check/overlap_check.py"
    STATES = ("open", "closed", "parked", "done")
    WORKFLOW = "ExpertPartners/x/.github/workflows/factory-chat-to-code-loop-builder-skills.yml@refs/heads/main"

    def building_201(self, state):
        """#201 starts a build in run 9001, its droid is writing, and then it is left open,
        closed, parked or marked done. #179 waits on the same file."""
        cfg = oc.Config(repo=REPO, settle_seconds=0, run_id="9001")
        gh = FakeGitHub([issue(179, self.SCOPE, labels=("job", "waiting")), issue(201, "tools/overlap-check/")])
        self.assertTrue(oc.run_check(gh, cfg, 201, sleep=lambda s: None))
        gh.runs[9001] = "in_progress"
        if state == "closed":
            gh.issues[201]["state"] = "closed"
        elif state != "open":
            gh.post(f"/repos/{REPO}/issues/201/labels", {"labels": [state]})
        return gh

    def test_an_active_writer_holds_its_files_under_every_issue_state(self):
        for state in self.STATES:
            gh = self.building_201(state)
            self.assertEqual([h.number for h in oc.in_progress_issues(gh, CFG)], [201], state)
            # The redispatch that closing, parking or marking #201 starts sends nothing.
            self.assertEqual(oc.run_next(gh, CFG, [].append), [], state)
            self.assertEqual(gh.labels(179), {"job", "waiting"}, state)
            self.assertFalse(oc.run_check(gh, CFG, 179, sleep=lambda s: None), state)
            self.assertIn("Waiting on #201, same file", gh.comment_bodies(179)[0], state)

    def test_a_job_closed_while_its_build_runs_holds_until_the_build_ends(self):
        gh = self.building_201("closed")
        self.assertEqual(oc.run_next(gh, CFG, [].append), [])
        gh.builds[9001] = "completed"
        self.assertEqual(oc.run_next(gh, CFG, [].append), [179])

    def test_release_after_the_build_ends_then_the_waiting_job_resumes(self):
        for state in self.STATES:
            gh = self.building_201(state)
            # The droid has stopped. The run stays in progress while its release job runs.
            gh.builds[9001] = "completed"
            code, out = Main.run_main(self, gh, ["release"], OVERLAP_ISSUE="201", GITHUB_RUN_ID="9001", BUILD_RESULT="success")
            self.assertEqual((code, out), (0, "restart=true\n"), state)
            self.assertNotIn("in-progress", gh.labels(201), state)
            # The restart step in the same release job sends #179.
            code, out = Main.run_main(self, gh, ["next"], OVERLAP_ISSUE="201", BUILDER_WORKFLOW_REF=self.WORKFLOW)
            self.assertEqual((code, out), (0, "dispatched=179\n"), state)
            self.assertNotIn("waiting", gh.labels(179), state)

    def test_a_stopped_job_holds_nothing_once_its_build_job_ends(self):
        for state in ("closed", "parked", "done"):
            gh = self.building_201(state)
            gh.builds[9001] = "completed"
            self.assertEqual(oc.run_next(gh, CFG, [].append), [179], state)
        # An open job still holds through in-progress until its release, as before.
        gh = self.building_201("open")
        gh.builds[9001] = "completed"
        self.assertEqual(oc.run_next(gh, CFG, [].append), [])

    def test_what_proves_a_writer_has_stopped(self):
        cases = [
            ("in_progress", "in_progress", True),
            ("in_progress", "queued", True),
            ("in_progress", "waiting", True),
            ("in_progress", None, True),  # the build job is not listed yet
            ("in_progress", "completed", False),  # only the release job is left
            ("queued", "queued", True),  # a re-run: the newest attempt builds again
            ("completed", "completed", False),
        ]
        for run, build, writing in cases:
            gh = self.building_201("parked")
            gh.runs[9001], gh.builds[9001] = run, build
            self.assertEqual(oc.build_is_running(gh, CFG, 201), writing, (run, build))
            jobs_calls = [c for c in gh.calls if c[1].endswith("/actions/runs/9001/jobs")]
            if run != "completed":
                self.assertEqual(jobs_calls[-1][2]["filter"], "latest", (run, build))

        gh = self.building_201("parked")
        gh.runs.pop(9001)  # a deleted run writes nothing
        self.assertFalse(oc.build_is_running(gh, CFG, 201))
        gh = self.building_201("parked")
        gh.builds[9001] = oc.GitHubError(502, "Bad Gateway")
        self.assertTrue(oc.build_is_running(gh, CFG, 201), "an unreadable build job keeps holding")

    def test_a_failed_build_restarts_the_others_but_not_itself(self):
        gh = self.building_201("open")
        gh.builds[9001] = "completed"
        code, out = Main.run_main(self, gh, ["release"], OVERLAP_ISSUE="201", GITHUB_RUN_ID="9001", BUILD_RESULT="failure")
        self.assertEqual((code, out), (0, "restart=true\n"))
        self.assertEqual(gh.labels(201), {"job", "waiting"})
        code, out = Main.run_main(self, gh, ["next"], OVERLAP_ISSUE="201", BUILDER_WORKFLOW_REF=self.WORKFLOW)
        self.assertEqual((code, out), (0, "dispatched=179\n"))
        self.assertEqual(gh.labels(201), {"job", "waiting"}, "not sent by its own release")

        alone = FakeGitHub([issue(201, "tools/a.py", labels=("job", "waiting"))])
        code, out = Main.run_main(self, alone, ["next"], OVERLAP_ISSUE="201", BUILDER_WORKFLOW_REF=self.WORKFLOW)
        self.assertEqual((code, out), (0, "dispatched=\n"))
        code, out = Main.run_main(self, alone, ["next"], BUILDER_WORKFLOW_REF=self.WORKFLOW)
        self.assertEqual((code, out), (0, "dispatched=201\n"), "any other restart still sends it")


class RunRelease(unittest.TestCase):
    def test_failed_build_without_a_pull_request_goes_back_to_waiting(self):
        gh = FakeGitHub([issue(159, "tools/a.py", labels=("job", "in-progress"))])
        self.assertEqual(oc.run_release(gh, CFG, 159, "failure"), "waiting")
        self.assertEqual(gh.labels(159), {"job", "waiting"})
        self.assertIn("did not finish (result: failure)", gh.comment_bodies(159)[0])

        # It no longer holds an overlapping job, and the next restart sends it again.
        other = FakeGitHub([issue(159, "tools/a.py", labels=("job", "waiting")), issue(161, "tools/a.py")])
        self.assertTrue(oc.run_check(other, CFG, 161, sleep=lambda s: None))

    def test_cancelled_build_is_released_too(self):
        gh = FakeGitHub([issue(159, "tools/a.py", labels=("job", "in-progress"))])
        self.assertEqual(oc.run_release(gh, CFG, 159, "cancelled"), "waiting")
        self.assertNotIn("in-progress", gh.labels(159))

    def test_successful_build_without_a_pull_request_stops_holding(self):
        gh = FakeGitHub([issue(159, "tools/a.py", labels=("job", "in-progress"))])
        self.assertEqual(oc.run_release(gh, CFG, 159, "success"), "released")
        self.assertEqual(gh.labels(159), {"job"}, "not queued again, so a finished run never loops")

    def test_a_build_with_its_pull_request_keeps_its_labels(self):
        _, own = pr(166, ["tools/a.py"], closes=159)
        for result in ("success", "failure"):
            gh = FakeGitHub([issue(159, "tools/a.py", labels=("job", "in-progress"))], [own])
            self.assertEqual(oc.run_release(gh, CFG, 159, result), "kept")
            self.assertEqual(gh.writes(), [])


class Main(unittest.TestCase):
    def run_main(self, gh, argv, **env):
        with tempfile.NamedTemporaryFile("r", suffix=".out") as out:
            # GITHUB_RUN_ID is set on a real runner, so each test names the run it plays.
            base = {"GITHUB_REPOSITORY": REPO, "OVERLAP_TOKEN": "t", "GITHUB_OUTPUT": out.name,
                    "OVERLAP_SETTLE_SECONDS": "0", "GITHUB_RUN_ID": ""}
            with mock.patch.dict(os.environ, {**base, **env}), mock.patch.object(oc, "GitHub", return_value=gh):
                code = oc.main(argv)
            return code, open(out.name, encoding="utf-8").read()

    def test_a_network_error_leaves_the_job_waiting_without_in_progress(self):
        gh = FakeGitHub([issue(159, "tools/a.py", labels=("job", "in-progress"))])
        real_get = gh.get
        gh.get = mock.Mock(side_effect=TimeoutError("timed out"))
        code, out = self.run_main(gh, ["check"], OVERLAP_ISSUE="159")
        gh.get = real_get
        self.assertEqual(code, 1)
        self.assertEqual(out, "start=false\n")
        self.assertEqual(gh.labels(159), {"job", "waiting"})

    def test_issue_typed_with_a_hash(self):
        gh = FakeGitHub([issue(159, "tools/a.py")])
        code, out = self.run_main(gh, ["check"], OVERLAP_ISSUE="#159")
        self.assertEqual((code, out), (0, "start=true\n"))

    def test_unreadable_issue_input_does_not_start(self):
        code, out = self.run_main(FakeGitHub(), ["check"], OVERLAP_ISSUE="abc")
        self.assertEqual((code, out), (1, "start=false\n"))


class Workflows(unittest.TestCase):
    """The caller and the reusable workflow keep the allowlist and the hand-off to the check."""

    def read(self, name):
        with open(os.path.join(ROOT, ".github", "workflows", name), encoding="utf-8") as fh:
            return fh.read()

    def test_reusable_workflow_keeps_the_author_allowlist(self):
        text = self.read("factory-builder-reusable.yml")
        self.assertEqual(
            text.count('["AllisonGaddy","expertpartners","expertpartners-ember","expertpartners-aura"]'), 3)
        self.assertIn("workflow_call:", text)
        self.assertIn('python3 "$script" check', text)
        self.assertIn('python3 "$script" next', text)
        self.assertIn("needs.gate.outputs.start == 'true'", text)

    def test_reusable_workflow_has_no_pull_request_cap(self):
        text = self.read("factory-builder-reusable.yml")
        self.assertNotIn("open pull requests", text)
        self.assertNotIn("pull request cap", text)

    def test_overlap_check_comes_only_from_main(self):
        # A ref the caller or a pull request could set would let pull request code run in
        # the privileged pull_request_target redispatch job.
        text = self.read("factory-builder-reusable.yml")
        checkouts = [block.split("      - name:", 1)[0] for block in text.split("uses: actions/checkout@v4")[1:]]
        tools = [block for block in checkouts if "sparse-checkout: tools/overlap-check" in block]
        self.assertEqual(len(tools), 4, "gate, build owner check, release and redispatch")
        for block in tools:
            self.assertIn("repository: ExpertPartners/expert-partners-skills\n", block)
            self.assertIn("ref: main\n", block)
            self.assertIn("persist-credentials: false\n", block)
        self.assertNotIn("tools_ref", text)

    def test_build_confirms_ownership_before_it_checks_out_or_writes(self):
        text = self.read("factory-builder-reusable.yml")
        build = text.split("  build:", 1)[1].split("  release:", 1)[0]
        steps = [line.strip()[len("- name: "):] for line in build.splitlines() if line.strip().startswith("- name: ")]
        self.assertEqual(steps[:3], ["Checkout the overlap check", "Confirm this run still owns the job", "Checkout"])
        self.assertIn('python3 "$script" owner', build)
        self.assertIn("ref: ${{ steps.owner.outputs.head }}", build)
        self.assertLess(steps.index("Revalidate immutable checkout before build secrets"), steps.index("Verify and configure Factory ledger access"))
        self.assertLess(steps.index("Revalidate immutable checkout before build secrets"), steps.index("Install Factory Droid"))
        self.assertLess(steps.index("Write automation prompt"), steps.index("Continue the job's existing pull request"))
        self.assertLess(steps.index("Continue the job's existing pull request"), steps.index("Run Factory Droid"))
        self.assertIn("if: steps.owner.outputs.note == 'true'", build)
        permissions = build.split("    permissions:\n", 1)[1].split("    steps:", 1)[0]
        self.assertEqual(sorted(line.strip() for line in permissions.splitlines() if ":" in line and not line.strip().startswith("#")),
                         ["actions: read", "contents: read", "id-token: write", "issues: read", "pull-requests: read"],
                         "the build's own token gains reads only")
        # The access preflight stays exactly where it was, after the caller checkout.
        self.assertLess(steps.index("Checkout"), steps.index("Assert clean caller checkout before access setup"))
        self.assertLess(steps.index("Verify and configure Factory ledger access"), steps.index("Run Factory Droid"))

    def test_failed_builds_are_released(self):
        text = self.read("factory-builder-reusable.yml")
        self.assertIn("needs: [gate, build]", text)
        self.assertIn("if: always() && needs.gate.outputs.start == 'true'", text)
        self.assertIn("BUILD_RESULT: ${{ needs.build.result }}", text)
        self.assertIn('python3 "$script" release', text)

    def test_redispatch_permissions_cover_actual_claim_restore_and_technical_wait_writes(self):
        text = self.read("factory-builder-reusable.yml").split("  redispatch:", 1)[1]
        permissions = text.split("    permissions:\n", 1)[1].split("    steps:", 1)[0]
        granted = dict(line.strip().split(": ", 1) for line in permissions.splitlines()
                       if ": " in line and not line.strip().startswith("#"))
        self.assertEqual(granted, {"actions": "write", "contents": "read", "issues": "write", "pull-requests": "read"})
        gh = FakeGitHub([issue(237, "x/a.py", labels=("job", "waiting"))])
        for name in ("post", "patch", "delete"):
            method = getattr(gh, name)
            def authorized(path, *args, _method=method):
                if "/issues/" in path and granted["issues"] != "write":
                    raise oc.GitHubError(403, "Resource not accessible by integration")
                return _method(path, *args)
            setattr(gh, name, authorized)
        self.assertEqual(oc.run_next(gh, CFG, NOOP), [237])
        self.assertIn(("DELETE", f"/repos/{REPO}/issues/237/labels/waiting", None), gh.writes())
        gh.post(f"/repos/{REPO}/issues/237/labels", {"labels": ["waiting"]})
        with self.assertRaises(RuntimeError):
            oc.run_next(gh, CFG, mock.Mock(side_effect=RuntimeError("dispatch failed")))
        self.assertIn("waiting", gh.labels(237), "failed dispatch can restore its claim")
        p = pr(240, ["x/a.py"], closes=237)[1]
        gh.prs = [p]
        gh.activities[p["head"]["ref"]] = []
        self.assertEqual(oc.run_next(gh, CFG, NOOP), [])
        self.assertTrue(gh.comment_bodies(237), "a provenance wait can write its precise receipt")


    def test_restarts_on_closed_issues_and_removed_in_progress(self):
        text = self.read("factory-builder-reusable.yml")
        self.assertIn("(github.event_name == 'issues' && github.event.action == 'closed')", text)
        self.assertIn("github.event.label.name == 'in-progress'", text)
        caller = self.read("factory-chat-to-code-loop-builder-skills.yml")
        for kind in ("labeled", "opened", "closed", "unlabeled"):
            self.assertIn(f"      - {kind}\n", caller)

    def test_restarts_when_parked_or_done_is_added_or_removed(self):
        # A blocker that gets parked or done while a stale in-progress stays on it holds
        # nothing, so its waiting jobs must be reconsidered right then. A waiting job that
        # loses parked or done is back in line and must be reconsidered too.
        text = self.read("factory-builder-reusable.yml")
        redispatch = text.split("  redispatch:", 1)[1].split("runs-on:", 1)[0]
        self.assertIn(
            "(github.event_name == 'issues' &&\n"
            "        (github.event.action == 'labeled' || github.event.action == 'unlabeled') &&\n"
            "        (github.event.label.name == 'parked' || github.event.label.name == 'done'))",
            redispatch)
        gate = text.split("  gate:", 1)[1].split("runs-on:", 1)[0]
        self.assertNotIn("parked", gate, "marking a job parked or done must never build it")

    def test_parked_or_done_builds_are_read_and_restart_after_release(self):
        text = self.read("factory-builder-reusable.yml")
        gate = text.split("  gate:", 1)[1].split("  build:", 1)[0]
        self.assertIn("      actions: read\n", gate)
        release = text.split("  release:", 1)[1].split("  redispatch:", 1)[0]
        self.assertIn("      actions: write\n", release)
        self.assertIn("if: steps.release.outputs.restart == 'true'", release)
        self.assertIn("overlap_check.py next", release)
        self.assertIn("BUILDER_WORKFLOW_REF: ${{ github.workflow_ref }}", release)
        restart = release.split("if: steps.release.outputs.restart == 'true'", 1)[1]
        self.assertIn("OVERLAP_ISSUE: ${{ github.event.issue.number || github.event.inputs.issue }}", restart,
                      "the restart never sends the job it just released")

    def test_every_builder_workflow_carries_the_never_ask_line(self):
        for name in ("factory-builder-reusable.yml", "factory-chat-to-code-loop-builder-skills.yml"):
            self.assertIn(NEVER_ASK, self.read(name), name)

    def test_skills_caller_is_small_and_passes_the_key(self):
        text = self.read("factory-chat-to-code-loop-builder-skills.yml")
        self.assertIn("uses: ./.github/workflows/factory-builder-reusable.yml", text)
        self.assertIn("FACTORY_API_KEY: ${{ secrets.FACTORY_API_KEY }}", text)
        self.assertNotIn("droid exec", text)



NOOP = lambda s: None


def run_cfg(run_id):
    return oc.Config(repo=REPO, settle_seconds=0, run_id=str(run_id))


def receipts(gh, number):
    return [b for b in gh.comment_bodies(number) if oc.RECEIPT_MARKER in b]


def claims(gh, number):
    return [b for b in gh.comment_bodies(number) if oc.CLAIM_RE.search(b)]


class LockedGitHub(FakeGitHub):
    """FakeGitHub for runs on separate threads. Each call is atomic, as each REST call is, and a
    short random pause before it lets the runs interleave differently every time."""

    def __init__(self, *args, jitter=0.0, **kwargs):
        super().__init__(*args, **kwargs)
        self.lock = threading.Lock()
        self.jitter = jitter
        self.claim_gate = None  # a Barrier every claim waits on before it is posted

    def _call(self, method, *args):
        if self.jitter:
            threading.Event().wait(random.random() * self.jitter)
        with self.lock:
            return method(self, *args)

    def get(self, *a):
        return self._call(FakeGitHub.get, *a)

    def paginate(self, *a):
        return self._call(FakeGitHub.paginate, *a)

    def post(self, path, body):
        if self.claim_gate and "factory-overlap-claim" in (body or {}).get("body", ""):
            self.claim_gate.wait(timeout=5)
        return self._call(FakeGitHub.post, path, body)

    def patch(self, *a):
        return self._call(FakeGitHub.patch, *a)

    def delete(self, *a):
        return self._call(FakeGitHub.delete, *a)


def race(gh, gates, sleep=NOOP):
    """Run each (run id, issue) gate on its own thread at once. Returns run id -> started."""
    results, errors = {}, []

    def one(run_id, number):
        try:
            results[run_id] = oc.run_check(gh, run_cfg(run_id), number, sleep=sleep)
        except Exception as exc:  # surfaced below
            errors.append(exc)

    threads = [threading.Thread(target=one, args=g) for g in gates]
    for t in threads:
        t.start()
    for t in threads:
        t.join(10)
    if errors:
        raise errors[0]
    return results


class OneJobOneWriter(unittest.TestCase):
    """However many events start the builder for one issue, one run builds it at a time, and
    every other run leaves a receipt naming the run it follows."""

    SCOPE = ".github/workflows/skills-graph.yml"

    def test_issue_237_replay_a_dispatch_during_the_build_follows_it(self):
        # Nov 4: run 41749627386 (job label) started #237 at 00:49:21. A manual dispatch,
        # run 41749736944, passed its own gate at 00:50:19 because a job's own in-progress
        # never held itself, and its droid opened the competing pull request #242.
        first, second = "41749627386", "41749736944"
        gh = FakeGitHub([issue(237, self.SCOPE)])
        self.assertTrue(oc.run_check(gh, run_cfg(first), 237, sleep=NOOP))
        gh.runs[int(first)] = "in_progress"
        before = len(gh.writes())
        self.assertFalse(oc.run_check(gh, run_cfg(second), 237, sleep=NOOP))
        self.assertEqual([(c[0], c[1]) for c in gh.writes()[before:]],
                         [("POST", f"/repos/{REPO}/issues/237/comments")],
                         "the follower writes its receipt and nothing else: no claim, no label")
        self.assertEqual(oc.recorded_run(gh, CFG, 237), first, "the first run keeps the job")
        self.assertEqual(gh.labels(237), {"job", "in-progress"})
        [receipt] = receipts(gh, 237)
        self.assertIn(f"Run {second} did not build this job, because run {first} is already building it", receipt)
        self.assertIn(f"/actions/runs/{first}", receipt)
        # Even reached by a re-run of failed jobs, the second run's build step refuses.
        owns, why, _ = oc.run_owner(gh, run_cfg(second), 237)
        self.assertFalse(owns)
        self.assertIn(f"admitted for run {first}", why)

        # The first run opens #240 and ends. Allison's review finding then re-runs the
        # second run in full, which continues #240 instead of opening another.
        gh.prs = [pr(240, [self.SCOPE], closes=237, ref="job/237-skills-graph-race-safe-writer")[1]]
        gh.builds[int(first)] = "completed"
        self.assertEqual(oc.run_release(gh, run_cfg(first), 237, "success"), "kept")
        gh.runs[int(first)] = "completed"
        self.assertTrue(oc.run_check(gh, run_cfg(second), 237, sleep=NOOP))
        self.assertIn("This build continues pull request #240", gh.comment_bodies(237)[0])
        owns, why, d = oc.run_owner(gh, run_cfg(second), 237)
        self.assertTrue(owns, why)
        self.assertEqual(d.target["number"], 240)
        note = oc.continuation_note(237, d, REPO)
        self.assertIn("open pull request #240 on branch job/237-skills-graph-race-safe-writer", note)
        self.assertIn("Do not open another pull request or branch for this job", note)

    def test_near_simultaneous_events_for_one_job_start_one_build(self):
        # Both gates take every look before either claims, then both claim, then both settle.
        gh = LockedGitHub([issue(245, self.SCOPE)])
        gh.claim_gate = threading.Barrier(2)
        settle = threading.Barrier(2)
        for run in (501, 502):
            gh.runs[run] = "in_progress"
        results = race(gh, [("501", 245), ("502", 245)], sleep=lambda s: settle.wait(timeout=5))
        self.assertEqual(sorted(results.values()), [False, True], results)
        winner = next(r for r, started in results.items() if started)
        loser = next(r for r, started in results.items() if not started)
        self.assertEqual(oc.recorded_run(gh, CFG, 245), winner)
        [receipt] = receipts(gh, 245)
        self.assertIn(f"Run {loser} did not build this job, because run {winner} is already building it", receipt)
        self.assertEqual(claims(gh, 245), [], "the winner's claim is gone and the loser's became its receipt")
        self.assertEqual(gh.labels(245), {"job", "in-progress"})

    def test_any_interleaving_of_three_events_starts_exactly_one_build(self):
        for seed in range(40):
            random.seed(seed)
            gh = LockedGitHub([issue(245, self.SCOPE, labels=("job", "waiting"))], jitter=0.002)
            for run in (601, 602, 603):
                gh.runs[run] = "in_progress"
            results = race(gh, [("601", 245), ("602", 245), ("603", 245)],
                           sleep=lambda s: threading.Event().wait(random.random() * 0.004))
            started = [r for r, ok in results.items() if ok]
            self.assertEqual(len(started), 1, (seed, results))
            self.assertEqual(oc.recorded_run(gh, CFG, 245), started[0], seed)
            self.assertEqual(len(receipts(gh, 245)), 2, seed)
            self.assertEqual(claims(gh, 245), [], seed)
            self.assertEqual(gh.labels(245), {"job", "in-progress"}, seed)

    def test_distinct_jobs_still_build_at_once(self):
        gh = LockedGitHub([issue(301, "tools/a/x.py"), issue(302, "tools/b/y.py")])
        settle = threading.Barrier(2)
        for run in (701, 702):
            gh.runs[run] = "in_progress"
        results = race(gh, [("701", 301), ("702", 302)], sleep=lambda s: settle.wait(timeout=5))
        self.assertEqual(results, {"701": True, "702": True}, "a claim on one job never holds another")
        self.assertEqual(receipts(gh, 301) + receipts(gh, 302), [])
        self.assertEqual(oc.recorded_run(gh, CFG, 301), "701")
        self.assertEqual(oc.recorded_run(gh, CFG, 302), "702")

    def test_colliding_jobs_judged_at_once_still_start_only_the_older(self):
        gh = LockedGitHub([issue(301, "AGENTS.md"), issue(302, "AGENTS.md")])
        gh.claim_gate = threading.Barrier(2)  # both first looks come before either label
        settle = threading.Barrier(2)
        results = race(gh, [("701", 301), ("702", 302)], sleep=lambda s: settle.wait(timeout=5))
        self.assertEqual(results, {"701": True, "702": False})
        self.assertIn("Waiting on #301, same file", gh.comment_bodies(302)[0])

    def test_a_claim_or_record_from_a_run_that_stopped_holds_nothing(self):
        gh = FakeGitHub([issue(245, self.SCOPE)])
        gh.post(f"/repos/{REPO}/issues/245/comments", {"body": "<!-- factory-overlap-claim:v1 run=77 -->\nRun 77 ..."})
        gh.post(f"/repos/{REPO}/issues/245/comments", {"body": oc.comment_body(oc.Verdict(True), "78")})
        gh.runs[78] = "in_progress"
        gh.builds[78] = "completed"  # only its release is left, so it no longer writes
        # Run 77 crashed during its gate and is gone.
        self.assertTrue(oc.run_check(gh, run_cfg(79), 245, sleep=NOOP))
        self.assertEqual(oc.recorded_run(gh, CFG, 245), "79")
        self.assertEqual(receipts(gh, 245), [])

    def test_an_unreadable_owner_run_still_counts_as_writing(self):
        gh = FakeGitHub([issue(245, self.SCOPE)])
        self.assertTrue(oc.run_check(gh, run_cfg(80), 245, sleep=NOOP))
        gh.runs[80] = oc.GitHubError(502, "Bad Gateway")
        self.assertFalse(oc.run_check(gh, run_cfg(81), 245, sleep=NOOP))
        self.assertEqual(oc.recorded_run(gh, CFG, 245), "80")

    def test_a_full_re_run_of_the_admitted_run_is_the_same_writer(self):
        gh = FakeGitHub([issue(245, self.SCOPE)])
        self.assertTrue(oc.run_check(gh, run_cfg(90), 245, sleep=NOOP))
        gh.runs[90] = "in_progress"
        self.assertTrue(oc.run_check(gh, run_cfg(90), 245, sleep=NOOP), "attempt 2 of run 90 is still run 90")
        self.assertEqual(receipts(gh, 245), [])


class ExistingPullRequest(unittest.TestCase):
    """A later build of a job with an open builder pull request continues that pull request."""

    BRANCH = "job/237-skills-graph-race-safe-writer"

    def admitted(self, prs, run="900"):
        gh = FakeGitHub([issue(237, ".github/workflows/skills-graph.yml")], prs)
        self.assertTrue(oc.run_check(gh, run_cfg(run), 237, sleep=NOOP))
        return gh

    def test_review_findings_continue_the_open_pull_request(self):
        _, open_pr = pr(240, [".github/workflows/skills-graph.yml"], closes=237, ref=self.BRANCH)
        gh = self.admitted([open_pr])
        code, out = Main.run_main(self, gh, ["owner"], OVERLAP_ISSUE="237", GITHUB_RUN_ID="900",
                                  OVERLAP_NOTE_FILE=os.devnull)
        self.assertEqual(code, 0)
        self.assertEqual(out, f"pr=240\nbranch={self.BRANCH}\nhead={240:040x}\nnote=true\n")
        # The release keeps the job on its pull request, which holds its files.
        code, out = Main.run_main(self, gh, ["release"], OVERLAP_ISSUE="237", GITHUB_RUN_ID="900", BUILD_RESULT="success")
        self.assertEqual((code, out), (0, "restart=false\n"))
        self.assertEqual(gh.labels(237), {"job", "in-progress"})

    def test_with_two_open_pull_requests_the_oldest_is_continued_and_the_other_kept(self):
        _, a = pr(240, ["x/a.py"], closes=237, ref=self.BRANCH)
        _, b = pr(242, ["x/b.py"], closes=237, ref="job/237-skills-graph-reliable")
        gh = self.admitted([b, a])
        owns, _, d = oc.run_owner(gh, run_cfg(900), 237)
        self.assertTrue(owns)
        self.assertEqual(d.target["number"], 240)
        note = oc.continuation_note(237, d, REPO)
        self.assertIn("Pull requests #242 also close #237. Leave them as they are", note)
        self.assertIn("do not close any pull request or delete any branch", note)
        self.assertNotIn("DELETE", {c[0] for c in gh.writes() if "/git/refs" in c[1] or "/pulls/" in c[1]})

    def test_a_pull_request_from_another_repository_is_never_checked_out(self):
        _, fork = pr(240, ["x/a.py"], closes=237)
        fork["head"]["repo"] = {"full_name": "someone/fork"}
        gh = self.admitted([fork])
        code, out = Main.run_main(self, gh, ["owner"], OVERLAP_ISSUE="237", GITHUB_RUN_ID="900")
        self.assertEqual(out, f"pr=\nbranch=\nhead={DEFAULT_HEAD}\nnote=false\n")
        self.assertIsNone(oc.head_branch(dict(fork, head={"ref": "job/1-x; rm -rf /", "repo": {"full_name": REPO}}), REPO))
        self.assertIsNone(oc.head_branch(dict(fork, head={"ref": "job/../main", "repo": {"full_name": REPO}}), REPO))

    def test_no_pull_request_builds_as_before(self):
        gh = self.admitted([])
        with tempfile.TemporaryDirectory() as d:
            note = os.path.join(d, "note.txt")
            code, out = Main.run_main(self, gh, ["owner"], OVERLAP_ISSUE="237", GITHUB_RUN_ID="900", OVERLAP_NOTE_FILE=note)
            self.assertEqual((code, out), (0, f"pr=\nbranch=\nhead={DEFAULT_HEAD}\nnote=false\n"))
            self.assertFalse(os.path.exists(note))

    def test_the_branch_handed_to_checkout_is_the_pull_request_head(self):
        # A temporary origin with main and the job's pull request branch. The branch the owner
        # check hands to checkout must check out at the head the pull request reports, and a
        # continuation commit pushed there moves that same branch, with no new branch.
        with tempfile.TemporaryDirectory() as d:
            env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.invalid",
                       GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.invalid")

            def git(*args, cwd=d):
                return subprocess.run(["git", *args], cwd=cwd, env=env, check=True,
                                      capture_output=True, text=True).stdout.strip()

            origin, work = os.path.join(d, "origin.git"), os.path.join(d, "work")
            git("init", "-q", "--bare", "-b", "main", origin)
            git("clone", "-q", origin, work)
            git("commit", "-q", "--allow-empty", "-m", "main", cwd=work)
            git("push", "-q", "origin", "HEAD:main", cwd=work)
            git("checkout", "-q", "-b", self.BRANCH, cwd=work)
            git("commit", "-q", "--allow-empty", "-m", "first build", cwd=work)
            git("push", "-q", "origin", self.BRANCH, cwd=work)
            head = git("rev-parse", "HEAD", cwd=work)

            _, open_pr = pr(240, ["x/a.py"], closes=237, ref=self.BRANCH)
            open_pr["head"]["sha"] = head
            gh = self.admitted([open_pr])
            note = os.path.join(d, "note.txt")
            code, out = Main.run_main(self, gh, ["owner"], OVERLAP_ISSUE="237", GITHUB_RUN_ID="900", OVERLAP_NOTE_FILE=note)
            self.assertEqual(code, 0)
            outputs = dict(line.split("=", 1) for line in out.splitlines())
            self.assertIn(head, open(note, encoding="utf-8").read())

            build = os.path.join(d, "build")
            git("clone", "-q", origin, build)
            git("checkout", "-q", "--detach", outputs["head"], cwd=build)
            self.assertEqual(git("rev-parse", "HEAD", cwd=build), outputs["head"])
            # Execute the actual verification shell step against the pinned real checkout.
            # The trusted API check is replaced by a bounded stand-in here; its failure
            # cases are exercised above against the real Python implementation.
            verifier = os.path.join(d, "trusted-verifier.py")
            with open(verifier, "w", encoding="utf-8") as fh:
                fh.write("import os, subprocess, sys\nassert sys.argv[1] == 'verify'\n"
                         "assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip() == os.environ['OVERLAP_EXPECTED_HEAD']\n")
            subprocess.run(["bash", "-e", "-o", "pipefail", "-c", BuildStepCommands().step("Revalidate immutable checkout before build secrets")],
                           cwd=build, env=dict(env, FACTORY_CONTINUATION_CHECK=verifier,
                                               OVERLAP_EXPECTED_HEAD=head, OVERLAP_EXPECTED_BRANCH=outputs["branch"]), check=True,
                           capture_output=True)
            self.assertEqual(git("status", "--porcelain", cwd=build), "", "branch attachment preserves clean access preflight")
            git("commit", "-q", "--allow-empty", "-m", "fix review finding", cwd=build)
            git("push", "-q", "origin", "HEAD", cwd=build)
            heads = git("for-each-ref", "--format=%(refname:short)", "refs/heads", cwd=origin).split()
            self.assertEqual(sorted(heads), sorted(["main", self.BRANCH]))
            self.assertEqual(git("rev-parse", f"{self.BRANCH}~1", cwd=origin), head, "the old head is kept")


class AuthenticatedContinuation(unittest.TestCase):
    def setup_pr(self):
        p = pr(240, ["x/a.py"], closes=237)[1]
        gh = FakeGitHub([issue(237, "x/a.py"), issue(238, "y/b.py", labels=("job", "waiting"))], [p])
        return gh, p

    def activity(self, p, **changes):
        return dict({"ref": f"refs/heads/{p['head']['ref']}", "after": p["head"]["sha"],
                     "actor": dict(BOT), "activity_type": "push"}, **changes)

    def verify(self, gh, p, local=None, expected=None):
        with mock.patch.object(oc.subprocess, "check_output", return_value=(local or p["head"]["sha"]) + "\n"):
            return Main.run_main(self, gh, ["verify"], GITHUB_RUN_ID="900", OVERLAP_ISSUE="237",
                                 OVERLAP_EXPECTED_PR="240", OVERLAP_EXPECTED_BRANCH=p["head"]["ref"],
                                 OVERLAP_EXPECTED_HEAD=expected or p["head"]["sha"])[0]

    def test_genuine_factory_branch_creation_push_and_force_push(self):
        for kind in ("branch_creation", "push", "force_push"):
            with self.subTest(kind=kind):
                gh, p = self.setup_pr()
                gh.activities[p["head"]["ref"]] = [self.activity(p, activity_type=kind)]
                self.assertTrue(oc.run_check(gh, run_cfg(900), 237, sleep=NOOP))
                self.assertEqual(self.verify(gh, p), 0)
                call = next(c for c in gh.calls if c[1].endswith("/activity"))
                self.assertEqual(call[2], {"ref": f"refs/heads/{p['head']['ref']}", "direction": "desc", "per_page": 1})
                self.assertNotIn("actor", call[2], "a human's later push must not be hidden")
                self.assertNotIn("activity_type", call[2], "branch creation and deletion must remain visible")

    def test_live_github_activity_schema_accepts_factory_and_rejects_later_maintainer(self):
        # Sanitized field subset captured from authenticated GitHub.com responses on
        # 2026-11-04 with API versions 2022-11-28 and 2026-03-10. The docs' response
        # example uses pusher/push_type; the actual endpoint returns actor/activity_type.
        # Keep the real ref, immutable commits and producer IDs as the regression.
        factory = {"id": 48911552142, "activity_type": "branch_creation",
                   "ref": "refs/heads/job/245-one-branch-per-job",
                   "after": "11d5357e7ee3ade474f3ebaf793adb89d1b0770a",
                   "actor": {"id": 138933559, "login": "factory-droid[bot]", "type": "Bot"}}
        maintainer = {"id": 48916879999, "activity_type": "push", "ref": factory["ref"],
                      "after": "698cbcc30093723e1808f20cae4a723bf53298ee",
                      "actor": {"id": 99103536, "login": "AllisonGaddy", "type": "User"}}
        gh, p = self.setup_pr()
        p["head"]["ref"] = factory["ref"].removeprefix("refs/heads/")
        with mock.patch.dict(BOT, factory["actor"]):
            for record, expected in ((factory, True), (maintainer, False)):
                with self.subTest(producer=record["actor"]["login"]):
                    p["head"]["sha"] = record["after"]
                    gh.activities[p["head"]["ref"]] = [record]
                    self.assertEqual(oc.trusted_head(gh, CFG, p), expected)
            # Never guess schema aliases from an example or trust a bot pusher while
            # the endpoint supplies no authenticated activity_type/actor evidence.
            p["head"]["sha"] = factory["after"]
            gh.activities[p["head"]["ref"]] = [{"ref": factory["ref"], "after": factory["after"],
                                                "push_type": "normal", "pusher": factory["actor"]}]
            self.assertFalse(oc.trusted_head(gh, CFG, p))

    def test_branch_prefix_and_pr_author_do_not_authenticate_the_latest_push(self):
        for author in ("factory-droid[bot]", "collaborator"):
            with self.subTest(author=author):
                gh, p = self.setup_pr()
                p["user"]["login"] = author
                gh.activities[p["head"]["ref"]] = [self.activity(p, actor={"id": 456, "login": "collaborator", "type": "User"})]
                self.assertFalse(oc.run_check(gh, run_cfg(900), 237, sleep=NOOP))
                self.assertEqual(gh.labels(237), {"job", "waiting"})
                self.assertIn("remains with its current owner", gh.comment_bodies(237)[0])
                self.assertFalse(oc.run_owner(gh, run_cfg(900), 237)[0])
                self.assertEqual(oc.run_next(gh, CFG, NOOP), [238], "an independent job still starts")
                self.assertEqual(len(gh.prs), 1, "no duplicate PR created")

    def test_missing_ambiguous_stale_or_unreadable_activity_is_never_trust(self):
        gh, p = self.setup_pr()
        cases = [[], [self.activity(p), self.activity(p)], [self.activity(p, after="b" * 40)],
                 [self.activity(p, ref="refs/heads/main")], [self.activity(p, activity_type="branch_deletion")],
                 [self.activity(p, actor=dict(BOT, id=456))], None,
                 oc.GitHubError(403, "Forbidden"), TimeoutError("unreadable latest page")]
        for latest in cases:
            with self.subTest(latest=type(latest).__name__):
                gh.activities[p["head"]["ref"]] = latest
                self.assertFalse(oc.trusted_head(gh, CFG, p))
        gh.activities[p["head"]["ref"]] = oc.GitHubError(403, "Forbidden")
        self.assertEqual(oc.run_next(gh, CFG, NOOP), [238])

    def test_canonical_bot_identity_cannot_be_guessed_from_login(self):
        gh, p = self.setup_pr()
        original = gh.get
        for wrong in (dict(BOT, type="User"), dict(BOT, id=0), dict(BOT, html_url="https://example.invalid")):
            with self.subTest(wrong=wrong):
                gh.get = lambda path, params=None: wrong if path.startswith("/users/") else original(path, params)
                self.assertFalse(oc.trusted_head(gh, CFG, p))

    def test_changed_ref_cannot_reuse_older_app_activity(self):
        gh, p = self.setup_pr()
        gh.refs[p["head"]["ref"]] = "b" * 40
        self.assertFalse(oc.trusted_head(gh, CFG, p))

    def test_head_mutation_after_selection_is_rejected_even_if_factory_pushed_it(self):
        gh, p = self.setup_pr()
        self.assertTrue(oc.run_check(gh, run_cfg(900), 237, sleep=NOOP))
        old = p["head"]["sha"]
        p["head"]["sha"] = "b" * 40
        self.assertEqual(self.verify(gh, p, local=old, expected=old), 1)

    def test_untrusted_mutation_after_selection_and_wrong_local_checkout_are_rejected(self):
        gh, p = self.setup_pr()
        self.assertTrue(oc.run_check(gh, run_cfg(900), 237, sleep=NOOP))
        self.assertEqual(self.verify(gh, p, local="b" * 40), 1)
        gh.activities[p["head"]["ref"]] = [self.activity(p, actor=dict(BOT, id=999))]
        self.assertEqual(self.verify(gh, p), 1)

    def test_default_checkout_is_explicit_and_new_pr_after_selection_cannot_duplicate(self):
        gh, p = self.setup_pr()
        gh.prs = []
        self.assertTrue(oc.run_check(gh, run_cfg(900), 237, sleep=NOOP))
        with mock.patch.object(oc.subprocess, "check_output", return_value=DEFAULT_HEAD + "\n"):
            env = dict(GITHUB_RUN_ID="900", OVERLAP_ISSUE="237", OVERLAP_EXPECTED_PR="",
                       OVERLAP_EXPECTED_BRANCH="", OVERLAP_EXPECTED_HEAD=DEFAULT_HEAD)
            self.assertEqual(Main.run_main(self, gh, ["verify"], **env)[0], 0)
            gh.prs = [p]
            self.assertEqual(Main.run_main(self, gh, ["verify"], **env)[0], 1)

    def test_fork_never_becomes_continuation_or_keeps_the_issue_in_progress(self):
        gh, p = self.setup_pr()
        p["head"]["repo"] = {"full_name": "attacker/fork"}
        self.assertTrue(oc.run_check(gh, run_cfg(900), 237, sleep=NOOP))
        self.assertEqual(oc.job_delivery(gh, CFG, 237).open, [])
        self.assertEqual(oc.run_release(gh, run_cfg(900), 237, "success"), "released")
        self.assertEqual(gh.labels(237), {"job"})

    def test_untrusted_release_drops_stale_in_progress_without_dropping_real_file_holds(self):
        gh, p = self.setup_pr()
        self.assertTrue(oc.run_check(gh, run_cfg(900), 237, sleep=NOOP))
        gh.activities[p["head"]["ref"]] = []
        self.assertEqual(oc.run_release(gh, run_cfg(900), 237, "failure"), "waiting")
        self.assertEqual(gh.labels(237), {"job", "waiting"})
        gh.issues[239] = dict(issue(239, "x/a.py"), labels=[{"name": "job"}])
        self.assertFalse(oc.run_check(gh, run_cfg(901), 239, sleep=NOOP), "the actual open PR still holds its files")
        self.assertTrue(oc.run_check(gh, run_cfg(902), 238, sleep=NOOP))

    def test_explicit_reopen_resumes_done_but_preserves_parked_and_live_owners(self):
        for labels, live, start in ((["job", "done"], False, True), (["job", "done", "parked"], False, False),
                                    (["job", "done"], True, False)):
            with self.subTest(labels=labels, live=live):
                gh = FakeGitHub([issue(237, "x/a.py", labels=labels)])
                if live:
                    gh.comments[237] = [{"id": 100, "user": {"login": oc.COMMENT_AUTHOR},
                                         "body": f"{oc.MARKER}\n<!-- factory-overlap-run:800 -->"}]
                    gh.runs[800] = "in_progress"
                cfg = oc.Config(REPO, 0, "900", reopened=True)
                self.assertEqual(oc.run_check(gh, cfg, 237, sleep=NOOP), start)
                self.assertEqual("done" in gh.labels(237), not start)


class MergedWinner(unittest.TestCase):
    """A job whose builder pull request merged is delivered. Nothing builds it again unless it
    was reopened after that merge."""

    def test_a_dispatch_after_the_merge_does_not_build_again(self):
        gh = FakeGitHub([issue(237, "x/a.py", labels=("job", "waiting"))], closed_prs=[merged_pr(240, 237)])
        self.assertFalse(oc.run_check(gh, run_cfg(1000), 237, sleep=NOOP))
        self.assertEqual(gh.labels(237), {"job"}, "not waiting, so no restart sends it again")
        self.assertIn("Already delivered. Pull request #240 merged this job into main", gh.comment_bodies(237)[0])
        self.assertEqual(claims(gh, 237), [])
        self.assertFalse([c for c in gh.writes() if c[0] == "POST" and c[1].endswith("/labels")], "never in-progress")
        self.assertEqual(oc.run_next(gh, CFG, [].append), [])

    def test_the_merged_result_wins_over_a_redundant_open_pull_request(self):
        # After #240 merged, #242 was still open for the same job.
        _, redundant = pr(242, ["x/a.py"], closes=237, ref="job/237-skills-graph-reliable")
        gh = FakeGitHub([issue(237, "x/a.py")], [redundant], closed_prs=[merged_pr(240, 237)])
        self.assertFalse(oc.run_check(gh, run_cfg(1000), 237, sleep=NOOP))
        body = gh.comment_bodies(237)[0]
        self.assertIn("Pull request #240 merged", body)
        self.assertIn("Pull request #242 also closes this job and is still open. It is left as it is.", body)
        self.assertEqual([c for c in gh.writes() if c[0] == "DELETE"], [], "nothing is closed or deleted")

    def test_a_closed_unmerged_pull_request_is_not_a_delivery(self):
        _, closed = pr(242, ["x/a.py"], closes=237)
        gh = FakeGitHub([issue(237, "x/a.py")], closed_prs=[dict(closed, state="closed", merged_at=None)])
        self.assertTrue(oc.run_check(gh, run_cfg(1000), 237, sleep=NOOP))

    def test_a_job_reopened_after_its_merge_builds_on_top_of_it(self):
        gh = FakeGitHub([issue(237, "x/a.py")], closed_prs=[merged_pr(240, 237, merged_at="2026-11-04T01:21:00Z")])
        gh.timeline[237] = [{"event": "reopened", "created_at": "2026-11-04T01:00:00Z"}]
        self.assertFalse(oc.run_check(gh, run_cfg(1000), 237, sleep=NOOP), "reopened before the merge")
        gh.timeline[237].append({"event": "reopened", "created_at": "2026-11-04T03:00:00Z"})
        self.assertTrue(oc.run_check(gh, run_cfg(1001), 237, sleep=NOOP))
        owns, _, d = oc.run_owner(gh, run_cfg(1001), 237)
        self.assertTrue(owns)
        self.assertIn("Pull request #240 already merged earlier work", oc.continuation_note(237, d, REPO))

    def test_a_build_after_its_job_merged_does_not_write_and_its_release_does_not_queue_it(self):
        gh = FakeGitHub([issue(237, "x/a.py")])
        self.assertTrue(oc.run_check(gh, run_cfg(1000), 237, sleep=NOOP))
        gh.closed_prs = [merged_pr(240, 237)]  # another path merged the job meanwhile
        code, _ = Main.run_main(self, gh, ["owner"], OVERLAP_ISSUE="237", GITHUB_RUN_ID="1000")
        self.assertEqual(code, 1)
        code, out = Main.run_main(self, gh, ["release"], OVERLAP_ISSUE="237", GITHUB_RUN_ID="1000", BUILD_RESULT="failure")
        self.assertEqual((code, out), (0, "restart=true\n"))
        self.assertEqual(gh.labels(237), {"job"})
        self.assertIn("Already delivered", gh.comment_bodies(237)[0])
        self.assertEqual(oc.recorded_run(gh, CFG, 237), "1000", "provenance stays")


class ReopenedAfterMerge(unittest.TestCase):
    """Work reopened after a merge builds on the merged result. A pull request left open beside
    that merge, whose head lacks it, is never continued and never makes the job wait."""

    LEFTOVER = "job/237-skills-graph-reliable"

    def reopened(self, open_prs):
        gh = FakeGitHub([issue(237, "x/a.py")], open_prs, closed_prs=[merged_pr(240, 237)])
        gh.timeline[237] = [{"event": "reopened", "created_at": "2026-11-04T03:00:00Z"}]
        return gh

    def test_a_leftover_factory_pr_is_not_continued_and_the_build_starts_from_main(self):
        _, leftover = pr(242, ["x/a.py"], closes=237, ref=self.LEFTOVER)
        gh = self.reopened([leftover])
        self.assertTrue(oc.trusted_head(gh, CFG, leftover), "its head is genuinely Factory-produced")
        self.assertTrue(oc.run_check(gh, run_cfg(1001), 237, sleep=NOOP))
        compare = next(c for c in gh.calls if "/compare/" in c[1])
        self.assertEqual(compare[1], f"/repos/{REPO}/compare/{merged_pr(240, 237)['merge_commit_sha']}...{leftover['head']['sha']}")
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "note.txt")
            code, out = Main.run_main(self, gh, ["owner"], OVERLAP_ISSUE="237", GITHUB_RUN_ID="1001", OVERLAP_NOTE_FILE=path)
            self.assertEqual((code, out), (0, f"pr=\nbranch=\nhead={DEFAULT_HEAD}\nnote=true\n"))
            with open(path, encoding="utf-8") as fh:
                note = fh.read()
        self.assertIn("Pull request #240 already merged earlier work", note)
        self.assertIn("Pull requests #242 also close #237 but do not contain the merged work", note)
        self.assertIn(f"({self.LEFTOVER}) as they are, never push to those branches", note)
        self.assertNotIn("this checkout is that branch", note)
        with mock.patch.object(oc.subprocess, "check_output", return_value=DEFAULT_HEAD + "\n"):
            code, _ = Main.run_main(self, gh, ["verify"], GITHUB_RUN_ID="1001", OVERLAP_ISSUE="237", OVERLAP_EXPECTED_PR="",
                                    OVERLAP_EXPECTED_BRANCH="", OVERLAP_EXPECTED_HEAD=DEFAULT_HEAD)
        self.assertEqual(code, 0, "the pinned main checkout is revalidated")
        # A failed build goes back to waiting; the leftover does not keep the issue in-progress.
        self.assertEqual(oc.run_release(gh, run_cfg(1001), 237, "failure"), "waiting")
        self.assertEqual(gh.labels(237), {"job", "waiting"})
        self.assertEqual([c for c in gh.writes() if "/pulls" in c[1] or "/git/" in c[1]], [], "nothing closed or deleted")

    def test_a_pr_that_contains_the_merge_is_continued_beside_the_leftover(self):
        _, leftover = pr(242, ["x/a.py"], closes=237, ref=self.LEFTOVER)
        _, follow_up = pr(250, ["x/a.py"], closes=237, ref="job/237-follow-up")
        gh = self.reopened([follow_up, leftover])
        gh.compares[follow_up["head"]["sha"]] = "ahead"
        self.assertTrue(oc.run_check(gh, run_cfg(1001), 237, sleep=NOOP))
        owns, why, d = oc.run_owner(gh, run_cfg(1001), 237)
        self.assertTrue(owns, why)
        self.assertEqual(d.target["number"], 250)
        self.assertEqual([p["number"] for p in d.predates_merge], [242])
        note = oc.continuation_note(237, d, REPO)
        self.assertIn("this checkout is that branch", note)
        self.assertIn("Pull requests #242 also close #237 but do not contain the merged work", note)
        self.assertEqual(oc.run_release(gh, run_cfg(1001), 237, "success"), "kept")

    def test_an_unreadable_comparison_is_a_wait_never_a_continuation_or_a_duplicate(self):
        for answer in (oc.GitHubError(502, "Bad Gateway"), TimeoutError("timed out"), "unexpected"):
            with self.subTest(answer=answer):
                _, leftover = pr(242, ["x/a.py"], closes=237, ref=self.LEFTOVER)
                gh = self.reopened([leftover])
                gh.issues[238] = dict(issue(238, "y/b.py"), labels=[{"name": "job"}, {"name": "waiting"}])
                gh.compares[leftover["head"]["sha"]] = answer
                self.assertFalse(oc.run_check(gh, run_cfg(1001), 237, sleep=NOOP))
                self.assertEqual(gh.labels(237), {"job", "waiting"})
                self.assertIn("could not be shown to contain the merged result", gh.comment_bodies(237)[0])
                self.assertIsNone(oc.job_delivery(gh, CFG, 237).target)
                self.assertEqual(oc.run_next(gh, CFG, NOOP), [238], "an independent job still starts")

    def test_a_merged_fork_pr_on_a_job_branch_is_not_a_delivery(self):
        fork = merged_pr(240, 237)
        fork["head"] = dict(fork["head"], repo={"full_name": "someone/fork"})
        gh = FakeGitHub([issue(237, "x/a.py", labels=("job", "waiting"))], closed_prs=[fork])
        self.assertIsNone(oc.job_delivery(gh, CFG, 237).winner)
        self.assertTrue(oc.run_check(gh, run_cfg(1001), 237, sleep=NOOP))


class ReleaseLease(unittest.TestCase):
    """An older run's release never undoes a newer admission of the same job, wherever the new
    gate's writes fall between the release's first read and its writes."""

    def failed_build(self):
        gh = FakeGitHub([issue(245, "tools/a.py")])
        self.assertTrue(oc.run_check(gh, run_cfg(900), 245, sleep=NOOP))
        gh.runs[900], gh.builds[900] = "in_progress", "completed"  # its release job runs now
        gh.runs[901], gh.builds[901] = "in_progress", None  # a new gate, no build job yet
        return gh

    def test_a_gate_admitted_after_the_release_read_its_lease_keeps_its_admission(self):
        gh = self.failed_build()
        real = gh.paginate
        admitted = []

        def paginate(path, params=None):
            out = real(path, params)
            if path.endswith("/timeline") and not admitted:
                # The release has read its lease and the job's delivery. A new gate now
                # claims, pauses, records run 901 and sets its labels before the release writes.
                admitted.append(None)
                admitted[0] = oc.run_check(gh, run_cfg(901), 245, sleep=NOOP)
            return out

        gh.paginate = paginate
        self.assertEqual(oc.run_release(gh, run_cfg(900), 245, "failure"), "superseded")
        self.assertEqual(admitted, [True])
        self.assertEqual(gh.labels(245), {"job", "in-progress"}, "the new build still holds its files")
        self.assertEqual(oc.recorded_run(gh, CFG, 245), "901")
        owns, why, _ = oc.run_owner(gh, run_cfg(901), 245)
        self.assertTrue(owns, why)

    def test_a_release_during_a_new_gates_pause_yields_without_writing(self):
        gh = self.failed_build()
        outcome = []

        def pause(_):
            before = len(gh.writes())
            code, out = Main.run_main(self, gh, ["release"], OVERLAP_ISSUE="245", GITHUB_RUN_ID="900", BUILD_RESULT="failure")
            outcome.append((code, out))
            self.assertEqual(gh.writes()[before:], [], "the deciding gate owns every write")

        self.assertTrue(oc.run_check(gh, run_cfg(901), 245, sleep=pause))
        self.assertEqual(outcome, [(0, "restart=false\n")])
        self.assertEqual(gh.labels(245), {"job", "in-progress"})
        self.assertEqual(oc.recorded_run(gh, CFG, 245), "901")
        self.assertTrue(oc.run_owner(gh, run_cfg(901), 245)[0])

    def test_a_claim_from_a_run_that_ended_does_not_block_the_release(self):
        gh = self.failed_build()
        gh.post(f"/repos/{REPO}/issues/245/comments", {"body": "<!-- factory-overlap-claim:v1 run=901 -->\nRun 901 is checking."})
        gh.runs[901] = "completed"
        self.assertEqual(oc.run_release(gh, run_cfg(900), 245, "failure"), "waiting")
        self.assertEqual(gh.labels(245), {"job", "waiting"})
        self.assertEqual(oc.recorded_run(gh, CFG, 245), "900", "provenance stays")


class FailedBeforeBuild(unittest.TestCase):
    """A build that fails before the droid writes (preflight, provider wait) goes back to
    waiting with its run still recorded. Re-running that same run may build again; a newer
    admission replaces it; neither ever makes two writers or retries itself at once."""

    SCOPE = "tools/overlap-check/overlap_check.py"
    X = "41756696385"  # #245's first run, refused at the ledger preflight

    def failed_once(self):
        gh = FakeGitHub([issue(245, self.SCOPE), issue(250, self.SCOPE, labels=("job",))])
        self.assertTrue(oc.run_check(gh, run_cfg(self.X), 245, sleep=NOOP))
        gh.runs[int(self.X)] = "in_progress"
        gh.builds[int(self.X)] = "completed"  # the build job failed after eight seconds
        code, out = Main.run_main(self, gh, ["release"], OVERLAP_ISSUE="245", GITHUB_RUN_ID=self.X, BUILD_RESULT="failure")
        self.assertEqual((code, out), (0, "restart=true\n"))
        self.assertEqual(gh.labels(245), {"job", "waiting"})
        self.assertIn("did not finish (result: failure)", gh.comment_bodies(245)[0])
        self.assertEqual(oc.recorded_run(gh, CFG, 245), self.X, "the run stays recorded")
        return gh

    def test_a_failed_run_is_not_a_false_live_owner(self):
        gh = self.failed_once()
        # Its release is still running, but its build job ended, so it writes nothing.
        self.assertEqual([h.number for h in oc.in_progress_issues(gh, CFG)], [])
        self.assertTrue(oc.run_check(gh, run_cfg(250250), 250, sleep=NOOP), "#250 no longer waits on it")

    def test_its_release_never_restarts_itself_at_once(self):
        gh = self.failed_once()
        code, out = Main.run_main(self, gh, ["next"], OVERLAP_ISSUE="245", BUILDER_WORKFLOW_REF=ActiveWriter.WORKFLOW)
        self.assertEqual((code, out), (0, "dispatched=\n"))

    def test_re_running_the_failed_run_builds_with_one_writer(self):
        gh = self.failed_once()
        # "Re-run failed jobs" repeats build and release, not the gate.
        gh.runs[int(self.X)], gh.builds[int(self.X)] = "in_progress", "in_progress"
        owns, why, _ = oc.run_owner(gh, run_cfg(self.X), 245)
        self.assertTrue(owns, why)
        # While it writes it holds its files, though it is labeled waiting.
        self.assertFalse(oc.run_check(gh, run_cfg(250250), 250, sleep=NOOP))
        self.assertIn("Waiting on #245, same file", gh.comment_bodies(250)[0])
        # No restart sends it again, and a dispatch that does arrive follows it.
        self.assertEqual(oc.run_next(gh, CFG, [].append), [])
        self.assertIn("waiting", gh.labels(245))
        self.assertFalse(oc.run_check(gh, run_cfg(245245), 245, sleep=NOOP))
        self.assertIn(f"because run {self.X} is already building it", receipts(gh, 245)[0])
        # The re-run opens its pull request and ends.
        gh.prs = [pr(260, [self.SCOPE], closes=245)[1]]
        gh.builds[int(self.X)] = "completed"
        self.assertEqual(oc.run_release(gh, run_cfg(self.X), 245, "success"), "kept")

    def test_a_newer_admission_replaces_the_failed_run(self):
        gh = self.failed_once()
        gh.runs[int(self.X)] = "completed"
        sent = []
        self.assertEqual(oc.run_next(gh, CFG, sent.append), [245], "any later restart sends it")
        self.assertTrue(oc.run_check(gh, run_cfg(7777), 245, sleep=NOOP))
        gh.runs[7777] = "in_progress"
        self.assertEqual(oc.recorded_run(gh, CFG, 245), "7777")
        # Someone re-runs the old failed run after that. It must not write beside 7777.
        gh.runs[int(self.X)], gh.builds[int(self.X)] = "in_progress", "in_progress"
        code, _ = Main.run_main(self, gh, ["owner"], OVERLAP_ISSUE="245", GITHUB_RUN_ID=self.X)
        self.assertEqual(code, 1)
        before = gh.labels(245)
        code, out = Main.run_main(self, gh, ["release"], OVERLAP_ISSUE="245", GITHUB_RUN_ID=self.X, BUILD_RESULT="failure")
        self.assertEqual((code, out), (0, "restart=false\n"))
        self.assertEqual(gh.labels(245), before, "the old run's release leaves 7777's labels alone")
        self.assertEqual(oc.recorded_run(gh, CFG, 245), "7777")

    def test_ownership_that_cannot_be_read_never_writes(self):
        gh = self.failed_once()
        gh.get = mock.Mock(side_effect=TimeoutError("timed out"))
        code, _ = Main.run_main(self, gh, ["owner"], OVERLAP_ISSUE="245", GITHUB_RUN_ID=self.X)
        self.assertEqual(code, 1)

    def test_a_parked_job_is_not_built_by_a_re_run(self):
        gh = self.failed_once()
        gh.post(f"/repos/{REPO}/issues/245/labels", {"labels": ["parked"]})
        owns, why, _ = oc.run_owner(gh, run_cfg(self.X), 245)
        self.assertFalse(owns)
        self.assertIn("closed, parked or done", why)


class BuildStepCommands(unittest.TestCase):
    """Run the build job's new shell steps for real, with a stand-in for the check."""

    WORKFLOW = os.path.join(ROOT, ".github", "workflows", "factory-builder-reusable.yml")

    def step(self, name):
        with open(self.WORKFLOW, encoding="utf-8") as fh:
            text = fh.read()
        step = text.split("      - name: " + name + "\n", 1)[1].split("\n      - name:", 1)[0]
        lines = []
        for line in step.split("        run: |\n", 1)[1].splitlines():
            if line and not line.startswith("          "):
                break
            lines.append(line[10:])
        return "\n".join(lines)

    def test_the_owner_step_leaves_the_caller_checkout_clean(self):
        with tempfile.TemporaryDirectory() as d:
            workspace, runner_temp = os.path.join(d, "ws"), os.path.join(d, "tmp")
            os.mkdir(runner_temp)
            subprocess.run(["git", "init", "-q", workspace], check=True)
            stub = os.path.join(workspace, ".factory-builder-tools", "tools", "overlap-check", "overlap_check.py")
            os.makedirs(os.path.dirname(stub))
            with open(stub, "w", encoding="utf-8") as fh:
                fh.write("import os, sys\nopen(os.environ['RECEIPT'], 'w').write(sys.argv[1] + ' ' + os.environ['OVERLAP_NOTE_FILE'])\n")
            env = dict(os.environ, GITHUB_WORKSPACE=workspace, RUNNER_TEMP=runner_temp, RECEIPT=os.path.join(d, "receipt"), GITHUB_ENV=os.path.join(d, "env"))
            subprocess.run(["bash", "-e", "-o", "pipefail", "-c", self.step("Confirm this run still owns the job")],
                           cwd=workspace, env=env, check=True)
            with open(os.path.join(d, "receipt"), encoding="utf-8") as fh:
                self.assertEqual(fh.read(), f"owner {runner_temp}/factory-continuation.txt")
            status = subprocess.run(["git", "status", "--porcelain=v1", "--untracked-files=all"], cwd=workspace,
                                    check=True, capture_output=True).stdout
            self.assertEqual(status, b"", "the access preflight's clean-checkout assertion still holds")

    def test_the_owner_step_fails_the_build_when_the_check_refuses(self):
        with tempfile.TemporaryDirectory() as d:
            workspace, runner_temp = os.path.join(d, "ws"), os.path.join(d, "tmp")
            os.mkdir(runner_temp)
            stub = os.path.join(workspace, ".factory-builder-tools", "tools", "overlap-check", "overlap_check.py")
            os.makedirs(os.path.dirname(stub))
            with open(stub, "w", encoding="utf-8") as fh:
                fh.write("import sys\nsys.exit(1)\n")
            result = subprocess.run(["bash", "-e", "-o", "pipefail", "-c", self.step("Confirm this run still owns the job")],
                                    cwd=workspace, env=dict(os.environ, GITHUB_WORKSPACE=workspace, RUNNER_TEMP=runner_temp))
            self.assertNotEqual(result.returncode, 0)

    def test_revalidation_refusal_stops_before_branch_attachment(self):
        with tempfile.TemporaryDirectory() as d:
            subprocess.run(["git", "init", "-q", d], check=True)
            stub = os.path.join(d, "verify.py")
            with open(stub, "w", encoding="utf-8") as fh:
                fh.write("import sys\nsys.exit(1)\n")
            result = subprocess.run(["bash", "-e", "-o", "pipefail", "-c", self.step("Revalidate immutable checkout before build secrets")],
                                    cwd=d, env=dict(os.environ, FACTORY_CONTINUATION_CHECK=stub, OVERLAP_EXPECTED_BRANCH="job/1-work"),
                                    capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn(b"git switch", result.stderr, "the failure came from the verifier, before branch attachment")

    def test_the_continuation_note_is_appended_to_the_prompt(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "factory-automation-prompt.txt"), "w", encoding="utf-8") as fh:
                fh.write("base prompt")
            with open(os.path.join(d, "factory-continuation.txt"), "w", encoding="utf-8") as fh:
                fh.write("Continue #240.\n")
            subprocess.run(["bash", "-e", "-o", "pipefail", "-c", self.step("Continue the job's existing pull request")],
                           env=dict(os.environ, RUNNER_TEMP=d), check=True)
            with open(os.path.join(d, "factory-automation-prompt.txt"), encoding="utf-8") as fh:
                self.assertEqual(fh.read(), "base prompt\n\nContinue #240.\n")

    def test_reopened_job_is_allowed_by_caller_gate_and_written_droid_prompt(self):
        with open(self.WORKFLOW, encoding="utf-8") as fh:
            workflow = fh.read()
        with open(os.path.join(ROOT, ".github", "workflows", "factory-chat-to-code-loop-builder-skills.yml"), encoding="utf-8") as fh:
            self.assertIn("      - reopened\n", fh.read())
        gate = workflow.split("  gate:", 1)[1].split("    runs-on:", 1)[0]
        self.assertIn("github.event.action == 'reopened'", gate)
        value = next(line.split("FACTORY_AUTOMATION_PROMPT: ", 1)[1] for line in workflow.splitlines()
                     if "FACTORY_AUTOMATION_PROMPT: " in line)
        prompt = json.loads(value)
        allowed = "by an existing issue carrying the job label being reopened and admitted by the gate"
        self.assertIn(allowed, prompt.split("otherwise exit with no changes", 1)[0])
        with tempfile.TemporaryDirectory() as d:
            subprocess.run(["bash", "-e", "-o", "pipefail", "-c", self.step("Write automation prompt")],
                           env=dict(os.environ, RUNNER_TEMP=d, FACTORY_AUTOMATION_PROMPT=prompt), check=True)
            with open(os.path.join(d, "factory-automation-prompt.txt"), encoding="utf-8") as fh:
                self.assertEqual(fh.read(), prompt)


if __name__ == "__main__":
    unittest.main()


class ActiveOwnerErrorRecovery(unittest.TestCase):
    def owned(self):
        gh = FakeGitHub([issue(245, "x/a.py")])
        self.assertTrue(oc.run_check(gh, run_cfg(80), 245, sleep=NOOP))
        gh.runs[80] = "in_progress"
        return gh

    def test_follower_receipt_post_failure_preserves_the_existing_owner(self):
        gh = self.owned()
        before = list(gh.writes())
        original = gh.post
        def fail_receipt(path, body):
            if oc.RECEIPT_MARKER in body.get("body", ""):
                raise oc.GitHubError(503, "Receipt unavailable")
            return original(path, body)
        gh.post = fail_receipt
        code, output = Main.run_main(self, gh, ["check"], OVERLAP_ISSUE="245", GITHUB_RUN_ID="81")
        self.assertEqual((code, output), (0, "start=false\n"))
        self.assertEqual(gh.labels(245), {"job", "in-progress"})
        self.assertEqual(oc.recorded_run(gh, CFG, 245), "80")
        self.assertEqual(gh.writes(), before)

    def test_unreadable_ownership_never_authorizes_label_cleanup(self):
        gh = self.owned()
        before = list(gh.writes())
        gh.paginate = mock.Mock(side_effect=TimeoutError("Owner metadata unavailable"))
        code, output = Main.run_main(self, gh, ["check"], OVERLAP_ISSUE="245", GITHUB_RUN_ID="81")
        self.assertEqual((code, output), (1, "start=false\n"))
        self.assertEqual(gh.labels(245), {"job", "in-progress"})
        self.assertEqual(gh.writes(), before)

    def test_follow_receipt_patch_failure_leaves_labels_and_owner_untouched(self):
        gh = FakeGitHub([issue(245, "x/a.py", labels=("job", "in-progress"))])
        gh.post(f"/repos/{REPO}/issues/245/comments", {"body": oc.comment_body(oc.Verdict(True), "80")})
        gh.post(f"/repos/{REPO}/issues/245/comments", {"body": "<!-- factory-overlap-claim:v1 run=81 -->"})
        before = list(gh.writes())
        gh.patch = mock.Mock(side_effect=oc.GitHubError(503, "Receipt unavailable"))
        oc.follow(gh, run_cfg(81), 245, "80", claim_id=101)
        self.assertEqual(gh.labels(245), {"job", "in-progress"})
        self.assertEqual(oc.recorded_run(gh, CFG, 245), "80")
        self.assertEqual(gh.writes(), before)


    def test_takeover_between_error_cleanup_writes_preserves_new_owner(self):
        gh = FakeGitHub([issue(245, "x/a.py", labels=("job", "in-progress"))])
        original = gh.delete
        def new_owner_after_delete(path):
            result = original(path)
            if path.endswith("/labels/in-progress"):
                gh.post(f"/repos/{REPO}/issues/245/comments", {"body": oc.comment_body(oc.Verdict(True), "82")})
                gh.runs[82] = "in_progress"
                gh.post(f"/repos/{REPO}/issues/245/labels", {"labels": ["in-progress"]})
            return result
        gh.delete = new_owner_after_delete
        with mock.patch.object(oc, "run_check", side_effect=TimeoutError("Failed gate")):
            code, output = Main.run_main(self, gh, ["check"], OVERLAP_ISSUE="245", GITHUB_RUN_ID="81")
        self.assertEqual((code, output), (1, "start=false\n"))
        self.assertEqual(gh.labels(245), {"job", "in-progress"})
        self.assertEqual(oc.recorded_run(gh, CFG, 245), "82")
        self.assertFalse(any(c[0] == "POST" and "waiting" in (c[2] or {}).get("labels", []) for c in gh.writes()))

    def test_error_cleanup_preserves_parked_and_done_stops(self):
        for label in ("parked", "done"):
            gh = FakeGitHub([issue(245, "x/a.py", labels=("job", label))])
            with mock.patch.object(oc, "run_check", side_effect=TimeoutError("Failed gate")):
                code, output = Main.run_main(self, gh, ["check"], OVERLAP_ISSUE="245", GITHUB_RUN_ID="81")
            self.assertEqual((code, output), (1, "start=false\n"))
            self.assertEqual(gh.labels(245), {"job", label})
            self.assertEqual(gh.writes(), [])


class DeliveryDefaultBase(unittest.TestCase):
    def test_retargeted_pr_keeps_ownership_after_reopen_and_before_newer_pr(self):
        earlier = merged_pr(230, 237)
        retargeted = pr(240, ["x/a.py"], closes=237)[1]
        retargeted["base"]["ref"] = "release"
        newer = pr(241, ["x/a.py"], closes=237)[1]
        gh = FakeGitHub([issue(237, "x/a.py")], [retargeted, newer], [earlier])
        gh.timeline[237] = [{"event": "reopened", "created_at": "2026-11-04T02:00:00Z"}]
        gh.compares[newer["head"]["sha"]] = "ahead"
        delivery = oc.job_delivery(gh, CFG, 237)
        self.assertEqual([p["number"] for p in delivery.open], [240, 241])
        self.assertIsNone(delivery.target)
        self.assertEqual(delivery.predates_merge, [])
        self.assertFalse(oc.run_check(gh, run_cfg(1000), 237, sleep=NOOP))
        self.assertEqual(gh.labels(237), {"job", "waiting"})

    def test_nondefault_open_pr_waits_without_a_duplicate_gate_or_owner(self):
        for base in ({"ref": "release", "repo": {"full_name": REPO}},
                     {"ref": "main", "repo": {"full_name": "outside/repo"}}, {}):
            with self.subTest(base=base):
                p = pr(240, ["x/a.py"], closes=237)[1]
                p["base"] = base
                gh = FakeGitHub([issue(237, "x/a.py")], [p])
                self.assertFalse(oc.run_check(gh, run_cfg(1000), 237, sleep=NOOP))
                self.assertEqual(gh.labels(237), {"job", "waiting"})
                self.assertEqual(claims(gh, 237), [])
                self.assertIsNone(oc.recorded_run(gh, CFG, 237))
                self.assertEqual(oc.run_release(gh, CFG, 237, "success"), "waiting")
                self.assertFalse(oc.run_owner(gh, run_cfg(1000), 237)[0])

    def test_open_nondefault_or_crossrepo_bases_cannot_be_continued(self):
        for base in ({"ref": "release", "repo": {"full_name": REPO}},
                     {"ref": "main", "repo": {"full_name": "outside/repo"}}, {}):
            with self.subTest(base=base):
                p = pr(240, ["x/a.py"], closes=237)[1]
                p["base"] = base
                gh = FakeGitHub([issue(237, "x/a.py")], [p])
                delivery = oc.job_delivery(gh, CFG, 237)
                self.assertEqual([p["number"] for p in delivery.open], [240],
                                 "ineligible continuation still preserves existing ownership")
                self.assertIsNone(delivery.target)
                self.assertEqual(oc.open_builder_prs(gh, CFG)[0].files, ["x/a.py"],
                                 "base eligibility does not discard actual file holds")

    def test_merged_nondefault_or_crossrepo_bases_do_not_deliver(self):
        for base in ({"ref": "release", "repo": {"full_name": REPO}},
                     {"ref": "main", "repo": {"full_name": "outside/repo"}}, {}):
            with self.subTest(base=base):
                p = merged_pr(240, 237)
                p["base"] = base
                gh = FakeGitHub([issue(237, "x/a.py")], closed_prs=[p])
                self.assertIsNone(oc.job_delivery(gh, CFG, 237).winner)
                self.assertTrue(oc.run_check(gh, run_cfg(1000), 237, sleep=NOOP))
                self.assertNotIn("done", gh.labels(237))

    def test_current_default_is_read_instead_of_assuming_main(self):
        p = pr(240, ["x/a.py"], closes=237)[1]
        p["base"]["ref"] = "trunk"
        gh = FakeGitHub([issue(237, "x/a.py")], [p])
        original = gh.get
        gh.get = lambda path, params=None: {"default_branch": "trunk"} if path == f"/repos/{REPO}" else original(path, params)
        self.assertEqual(oc.job_delivery(gh, CFG, 237).target["number"], 240)


class FailedGateClaimRecovery(unittest.TestCase):
    def test_newer_claim_cannot_follow_a_failed_gate_or_strand_in_progress(self):
        gh = FakeGitHub([issue(245, "x/a.py")])
        gh.runs.update({80: "in_progress", 81: "in_progress"})
        gh.builds.update({80: None, 81: None})
        original_judge = oc.judge
        def failure_after_newer_claim(api, cfg, current, only_older_issues=False):
            if cfg.run_id == "80" and only_older_issues:
                oc.post_claim(gh, run_cfg(81), 245)
                raise TimeoutError("failed gate before admission")
            return original_judge(api, cfg, current, only_older_issues)
        with mock.patch.object(oc, "judge", side_effect=failure_after_newer_claim):
            code, out = Main.run_main(self, gh, ["check"], OVERLAP_ISSUE="245", GITHUB_RUN_ID="80")
        self.assertEqual((code, out), (1, "start=false\n"))
        self.assertEqual(gh.labels(245), {"job", "waiting"})
        self.assertFalse(any("run=80" in b for b in claims(gh, 245)))
        self.assertIsNone(oc.live_owner(gh, run_cfg(81), 245, before=102))
        self.assertTrue(oc.run_check(gh, run_cfg(81), 245, sleep=NOOP))
        self.assertEqual(gh.labels(245), {"job", "in-progress"})
        self.assertEqual(receipts(gh, 245), [])

    def test_failed_claim_removal_refuses_label_cleanup(self):
        gh = FakeGitHub([issue(245, "x/a.py")])
        original_delete = gh.delete
        def failed_delete(path):
            if "/issues/comments/" in path:
                raise oc.GitHubError(503, "claim deletion unavailable")
            return original_delete(path)
        gh.delete = failed_delete
        original_judge = oc.judge
        def failed_second(api, cfg, current, only_older_issues=False):
            if only_older_issues:
                raise TimeoutError("failed gate")
            return original_judge(api, cfg, current, only_older_issues)
        with mock.patch.object(oc, "judge", side_effect=failed_second):
            code, out = Main.run_main(self, gh, ["check"], OVERLAP_ISSUE="245", GITHUB_RUN_ID="80")
        self.assertEqual((code, out), (1, "start=false\n"))
        self.assertEqual(gh.labels(245), {"job", "in-progress"})

    def test_newer_gate_admitted_after_claim_drop_keeps_its_labels(self):
        gh = FakeGitHub([issue(245, "x/a.py")])
        gh.runs.update({80: "in_progress", 81: "in_progress"})
        original_judge, original_delete = oc.judge, gh.delete
        def failed_second(api, cfg, current, only_older_issues=False):
            if cfg.run_id == "80" and only_older_issues:
                raise TimeoutError("failed gate")
            return original_judge(api, cfg, current, only_older_issues)
        def admit_after_delete(path):
            result = original_delete(path)
            if path.endswith("/issues/comments/101"):
                self.assertTrue(oc.run_check(gh, run_cfg(81), 245, sleep=NOOP))
            return result
        gh.delete = admit_after_delete
        with mock.patch.object(oc, "judge", side_effect=failed_second):
            code, out = Main.run_main(self, gh, ["check"], OVERLAP_ISSUE="245", GITHUB_RUN_ID="80")
        self.assertEqual((code, out), (1, "start=false\n"))
        self.assertEqual(gh.labels(245), {"job", "in-progress"})
        self.assertEqual(oc.recorded_run(gh, CFG, 245), "81")
        self.assertFalse(any(c[0] == "POST" and "waiting" in (c[2] or {}).get("labels", [])
                             for c in gh.writes()))
