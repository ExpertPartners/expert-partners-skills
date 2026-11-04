"""Unit tests for the builder overlap check. Every GitHub call goes to FakeGitHub; nothing
touches the network.

Run from the repo root: python3 -m unittest discover -s tools/overlap-check/tests -v
"""

import importlib.util
import os
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(__file__)
spec = importlib.util.spec_from_file_location("overlap_check", os.path.join(HERE, "..", "overlap_check.py"))
oc = importlib.util.module_from_spec(spec)
# dataclasses resolves annotations through sys.modules, so register before executing.
sys.modules["overlap_check"] = oc
spec.loader.exec_module(oc)

REPO = "ExpertPartners/expert-partners-skills"
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
        "head": {"ref": ref or f"job/{closes or number}-work"},
        "body": f"Closes #{closes}\n\nwork" if closes else "work",
        "files": list(files),
    }


class FakeGitHub:
    """Holds issues, pull requests and comments, and answers the calls overlap_check makes."""

    def __init__(self, issues=(), prs=()):
        self.issues = {i["number"]: dict(i, labels=[{"name": n} for n in i.get("labels", [])]) for i in issues}
        self.prs = list(prs)
        self.comments = {}
        self.calls = []
        self.next_comment_id = 100
        self.on_sleep = None
        self.runs = {}  # run id -> status, or a GitHubError to raise
        # run id -> the build job's status, None when the run lists no build job yet, or a
        # GitHubError to raise. A run not named here has a build job in the run's status.
        self.builds = {}

    def get(self, path, params=None):
        self.calls.append(("GET", path, params))
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
            return list(self.comments.get(int(path.split("/")[-2]), []))
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
            self.comments.setdefault(int(parts[-2]), []).append(
                {"id": self.next_comment_id, "user": {"login": "github-actions[bot]"}, "body": body["body"]})
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
        code, out = Main.run_main(self, gh, ["release"], OVERLAP_ISSUE="201", BUILD_RESULT="success")
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
            code, out = Main.run_main(self, gh, ["release"], OVERLAP_ISSUE="201", BUILD_RESULT="success")
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
        code, out = Main.run_main(self, gh, ["release"], OVERLAP_ISSUE="201", BUILD_RESULT="failure")
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
            base = {"GITHUB_REPOSITORY": REPO, "OVERLAP_TOKEN": "t", "GITHUB_OUTPUT": out.name,
                    "OVERLAP_SETTLE_SECONDS": "0"}
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
            text.count('["AllisonGaddy","expertpartners","expertpartners-ember","expertpartners-aura"]'), 2)
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
        self.assertEqual(text.count("ref: main"), 3)
        self.assertNotIn("tools_ref", text)

    def test_failed_builds_are_released(self):
        text = self.read("factory-builder-reusable.yml")
        self.assertIn("needs: [gate, build]", text)
        self.assertIn("if: always() && needs.gate.outputs.start == 'true'", text)
        self.assertIn("BUILD_RESULT: ${{ needs.build.result }}", text)
        self.assertIn('python3 "$script" release', text)

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


if __name__ == "__main__":
    unittest.main()
