#!/usr/bin/env python3
"""Overlap check for Chat to Code builds (Decision Log 2026-11-02, Factory runs everything at
once, and No caps stop work).

A build starts right away unless a file in the issue's Files in scope is also in an open
builder pull request (its changed files) or in the Files in scope of another Job issue that is
truly building: labeled in-progress and open, neither parked nor done, or any of closed, parked
or done while the build job the gate recorded for it can still write. Shared files
(plugin.json, marketplace.json, CHANGELOG.md, AGENTS.md, lockfiles) count the same way and are
named as shared in the comment. A held issue gets "Waiting on #N, same
file". There is no cap on how many builds or open pull requests a repo may have.

One job has one writer. However many events start the builder for the same issue, only one
run builds it at a time, and a later build continues the job's open pull request instead of
opening another.

Five subcommands, run by .github/workflows/factory-builder-reusable.yml:

  check    Judge OVERLAP_ISSUE. A closed, parked or done issue never builds and is left as
           it is. When another run already builds this job (its recorded build, or an
           earlier claim, can still write), this run posts a receipt naming that run and does
           not build. A job whose builder pull request already merged is not built again
           unless it was reopened after that merge. A clear issue posts a claim, is labeled
           in-progress (and job), loses waiting, and its one comment records this run
           (GITHUB_RUN_ID) as its build. A held issue is labeled waiting and gets one comment
           saying what it waits on, edited in place when that changes. Writes
           start=true|false to GITHUB_OUTPUT.
  owner    First step of the build job. Fails unless the job is still open, not delivered,
           and its recorded build is this run, so a re-run of a run another admission has
           replaced never writes beside it. Writes pr, branch and head of the job's open
           authenticated builder pull request, or an explicitly resolved default head
           for new work, and a continuation note to OVERLAP_NOTE_FILE.
  verify   Before build secrets are supplied, confirms ownership and producer evidence
           again and checks that the selected immutable SHA is the local checkout.
  release  After a build the gate started, when no open builder pull request closes
           OVERLAP_ISSUE, drop its in-progress label so it holds nothing. A build that did not
           succeed (BUILD_RESULT) goes back to waiting, so it starts again on its own. A job
           that was closed, parked or done while it built always loses in-progress, and one
           whose pull request merged loses in-progress and waiting. A run that is no longer
           the job's recorded build changes nothing. Whenever in-progress is dropped,
           restart=true is written so the caller runs next.
  next     After a pull request or issue closes, in-progress is removed, or an issue gains
           or loses parked or done, dispatch the builder for every waiting Job issue that
           would start now, oldest first. Each one is claimed by removing its waiting label first,
           so two runs never dispatch the same job. A job still being built is not sent.
           OVERLAP_ISSUE, when set (by the release), is never sent, so a failing build does
           not restart itself in a loop. Writes dispatched=<n,n,...>.

OVERLAP_TOKEN (the workflow's own token) does every read and write, and reads build runs with
actions: read. Standard library only.
"""

from __future__ import annotations

import fnmatch
import json
import os
import re
import sys
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field

FACTORY_LOGIN = "factory-droid[bot]"
BUILDER_BRANCH_PREFIX = "job/"
COMMENT_AUTHOR = "github-actions[bot]"
JOB_LABEL = "job"
IN_PROGRESS_LABEL = "in-progress"
WAITING_LABEL = "waiting"
PARKED_LABEL = "parked"
DONE_LABEL = "done"
# A parked job is off Factory by Allison's logged decision, and a done job has merged, so
# neither is building even when a stale in-progress label is still on it.
NOT_BUILDING_LABELS = {PARKED_LABEL, DONE_LABEL}
# The job in factory-builder-reusable.yml that runs the droid. Called from a caller's job,
# the API names it "<caller job> / build".
BUILD_JOB = "build"

SHARED_BASENAMES = {
    "plugin.json",
    "marketplace.json",
    "changelog.md",
    "agents.md",
    "package-lock.json",
    "npm-shrinkwrap.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "bun.lockb",
    "bun.lock",
    "poetry.lock",
    "pipfile.lock",
    "uv.lock",
    "cargo.lock",
    "gemfile.lock",
    "composer.lock",
    "go.sum",
}

MARKER = "<!-- factory-overlap-check:v1 -->"
RUN_MARKER_RE = re.compile(r"<!-- factory-overlap-run:(\d+) -->")
# A gate posts a claim before its pause. Comment ids only grow, so of two gates for the same
# job the one whose claim is older wins, however their reads and writes interleave.
CLAIM_RE = re.compile(r"<!-- factory-overlap-claim:v1 run=(\d+) -->")
RECEIPT_MARKER = "<!-- factory-overlap-receipt:v1 -->"
# Only a plain branch name from this repo is ever handed to checkout.
BRANCH_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]*$")
CLOSES_RE = re.compile(r"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s+#(\d+)\b", re.IGNORECASE)
HEADING_RE = re.compile(r"^\s*#+\s+\S")
SCOPE_SECTION = "files in scope"
# Section names from .github/ISSUE_TEMPLATE/job.md and common additions, for bodies written
# with bare or bold labels instead of ## headings.
SECTION_NAMES = {
    "mission", "goal", "objective", "acceptance checks", "decisions already made",
    "out of scope", "not in scope", "constraints", "notes", "context", "background", "validation",
}
BACKTICK_RE = re.compile(r"`([^`]+)`")
BARE_FILENAMES = {"Makefile", "Dockerfile", "CODEOWNERS", "LICENSE", "Procfile", "Gemfile", "Brewfile"}


class GitHubError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(f"HTTP {status}: {message}")
        self.status = status
        self.message = message


class GitHub:
    """Minimal REST client. Tests replace it with a fake that has the same methods."""

    def __init__(self, token: str, api_url: str = "https://api.github.com"):
        self.token = token
        self.api_url = api_url.rstrip("/")

    def _request(self, method: str, url: str, body=None):
        if not url.startswith("http"):
            url = self.api_url + url
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Accept", "application/vnd.github+json")
        req.add_header("Authorization", f"Bearer {self.token}")
        req.add_header("X-GitHub-Api-Version", "2022-11-28")
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read()
                link = resp.headers.get("Link", "") or ""
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")
            try:
                detail = json.loads(detail).get("message", detail)
            except ValueError:
                pass
            raise GitHubError(exc.code, detail) from None
        return (json.loads(raw) if raw else None), link

    def get(self, path: str, params: dict | None = None):
        if params:
            path += "?" + urllib.parse.urlencode(params)
        return self._request("GET", path)[0]

    def paginate(self, path: str, params: dict | None = None) -> list:
        query = dict(params or {})
        query.setdefault("per_page", 100)
        url = f"{path}?{urllib.parse.urlencode(query)}"
        items: list = []
        while url:
            data, link = self._request("GET", url)
            items.extend(data or [])
            url = next((p.split(";")[0].strip()[1:-1] for p in link.split(",") if 'rel="next"' in p), None)
        return items

    def post(self, path: str, body: dict):
        return self._request("POST", path, body)[0]

    def patch(self, path: str, body: dict):
        return self._request("PATCH", path, body)[0]

    def delete(self, path: str):
        return self._request("DELETE", path)[0]


# ---------------------------------------------------------------- pure logic


def section_name(line: str) -> str:
    """'## Files in scope', '**Files in scope:**', '__Files in scope__:' -> 'files in scope'."""
    s = re.sub(r"^\s*#+\s*", "", line).strip()
    s = s.strip("*_ ").rstrip(":").strip("*_ ").rstrip(":").strip()
    return s.lower()


def parse_scope(body: str | None) -> list[str]:
    """The paths listed under Files in scope, in order, without the (new) marks."""
    paths: list[str] = []
    in_scope = False
    for line in (body or "").splitlines():
        if not in_scope:
            in_scope = section_name(line) == SCOPE_SECTION
            continue
        stripped = line.strip()
        if HEADING_RE.match(line) or section_name(line) in SECTION_NAMES or stripped == "---":
            break
        if not stripped:
            continue
        item = re.sub(r"^(?:[-*+]|\d+[.)])\s+", "", stripped)
        ticked = BACKTICK_RE.findall(item)
        candidates = ticked if ticked else [item.split(None, 1)[0]]
        for cand in candidates:
            path = normalize(cand)
            if looks_like_path(path) and path not in paths:
                paths.append(path)
    return paths


def looks_like_path(path: str) -> bool:
    """Keeps prose and branch names out of the scope: a file has an extension or a known
    bare name, a directory ends in / or is a slashed path, a glob has a wildcard. Builder
    branch names (job/...) and URLs are not paths."""
    if not path or " " in path or "://" in path or path.startswith(BUILDER_BRANCH_PREFIX):
        return False
    last = path.rstrip("/").rsplit("/", 1)[-1]
    return (
        "/" in path
        or any(ch in path for ch in "*?[")
        or "." in last.lstrip(".") or (last.startswith(".") and len(last) > 1)
        or last in BARE_FILENAMES
    )


def is_glob(path: str) -> bool:
    return any(ch in path for ch in "*?[")


def as_directory(path: str) -> str | None:
    """The directory prefix a path stands for: 'tools/x/' as is, and 'tools/x' too, since a
    slashed entry with no extension may name a directory written without its trailing /."""
    if path.endswith("/"):
        return path
    last = path.rsplit("/", 1)[-1]
    if "/" in path and "." not in last and last not in BARE_FILENAMES and not is_glob(path):
        return path + "/"
    return None


def normalize(path: str) -> str:
    path = path.strip().strip("`\"'").rstrip(",;:")
    if path.endswith(".") and not path.endswith("/."):
        path = path[:-1]
    path = re.sub(r"\s*\(new\)\s*$", "", path, flags=re.IGNORECASE)
    while path.startswith("./"):
        path = path[2:]
    return path.lstrip("/")


# Each job writes its own note file in .changeset/ (any top-level .md there except
# README.md). A note collides only with the very same note, and two spellings of the
# folder itself (the folder, or a glob inside it) never hold each other. README.md and
# anything else in the folder keep the normal rules.
NOTE_DIR = ".changeset"


def is_note_file(path: str) -> bool:
    head, _, name = path.partition("/")
    return (head == NOTE_DIR and "/" not in name and name.lower().endswith(".md")
            and name.lower() != "readme.md" and not is_glob(name))


def is_note_folder(path: str) -> bool:
    return path in (NOTE_DIR, NOTE_DIR + "/") or (path.startswith(NOTE_DIR + "/") and is_glob(path))


def is_shared(path: str) -> bool:
    return path.rstrip("/").rsplit("/", 1)[-1].lower() in SHARED_BASENAMES


def paths_overlap(a: str, b: str) -> bool:
    """A note in .changeset/ collides only with the same note. Otherwise same file, one path inside the other's directory (a path ending in /), a glob match,
    or a shared file named without its directory (plugin.json) against any file of that name."""
    if is_note_file(a) or is_note_file(b):
        return a == b
    if is_note_folder(a) and is_note_folder(b):
        return False
    if a == b:
        return True
    if is_shared(a) and is_shared(b) and ("/" not in a or "/" not in b):
        return a.rsplit("/", 1)[-1].lower() == b.rsplit("/", 1)[-1].lower()
    for x, y in ((a, b), (b, a)):
        prefix = as_directory(x)
        if prefix and y.startswith(prefix):
            return True
        if is_glob(x) and fnmatch.fnmatchcase(y, x):
            return True
    return False


def overlapping(mine: list[str], theirs: list[str]) -> list[str]:
    """The paths from mine that collide with theirs, shared files included."""
    return [p for p in mine if any(paths_overlap(p, q) for q in theirs)]


def closes(body: str | None) -> set[int]:
    return {int(n) for n in CLOSES_RE.findall(body or "")}


def is_builder_pr(pr: dict) -> bool:
    login = (pr.get("user") or {}).get("login")
    ref = (pr.get("head") or {}).get("ref") or ""
    return login == FACTORY_LOGIN or ref.startswith(BUILDER_BRANCH_PREFIX)


@dataclass
class Holder:
    number: int
    kind: str  # "pr" or "issue"
    files: list[str]
    closes: set[int] = field(default_factory=set)


@dataclass
class Overlap:
    number: int
    kind: str
    paths: list[str]

    @property
    def shared(self) -> list[str]:
        return [p for p in self.paths if is_shared(p)]


@dataclass
class Verdict:
    start: bool
    overlaps: list[Overlap] = field(default_factory=list)
    open_prs: int = 0
    scope: list[str] = field(default_factory=list)

    def lines(self) -> list[str]:
        return [f"Waiting on #{o.number}, same file" for o in self.overlaps]


def evaluate(issue: int, scope: list[str], prs: list[Holder], issues: list[Holder]) -> Verdict:
    """Judge one job. prs are open builder pull requests, issues are other in-progress Job issues.

    A pull request that closes this issue is this job's own earlier work, so it never
    collides. An issue whose overlapping pull request is already named is not named again.
    """
    prs = [p for p in prs if issue not in p.closes]
    found: list[Overlap] = []
    named_by_pr: set[int] = set()
    for p in prs:
        hit = overlapping(scope, p.files)
        if hit:
            found.append(Overlap(p.number, "pr", hit))
            named_by_pr |= p.closes
    for i in issues:
        if i.number == issue or i.number in named_by_pr:
            continue
        hit = overlapping(scope, i.files)
        if hit:
            found.append(Overlap(i.number, "issue", hit))
    return Verdict(not found, found, len(prs), scope)


def comment_body(v: Verdict, run_id: str = "", continues: dict | None = None) -> str:
    if v.start:
        lines = [MARKER, "Started. No other build touches these files."]
        if continues:
            head = ((continues.get("head") or {}).get("sha") or "")[:12]
            lines.append(f"This build continues pull request #{continues['number']}"
                         f"{f' at {head}' if head else ''} instead of opening another.")
        if run_id:
            lines.append(f"<!-- factory-overlap-run:{run_id} -->")
        return "\n".join(lines)
    lines = [MARKER, *v.lines(), ""]
    for o in v.overlaps:
        what = "pull request" if o.kind == "pr" else "in-progress job"
        named = ", ".join(f"`{p}`{' (shared file)' if is_shared(p) else ''}" for p in o.paths)
        lines.append(f"- #{o.number} ({what}): {named}")
    lines += [
        "",
        "This build starts on its own when a pull request or job issue in this repo closes, "
        "a job loses its in-progress label, or a job is marked parked or done, and nothing "
        "above still holds it.",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------- GitHub side


@dataclass
class Config:
    repo: str
    settle_seconds: float = 10.0
    run_id: str = ""
    reopened: bool = False


def labels_of(item: dict) -> set[str]:
    # GitHub matches label names without regard to case, so a repo whose label is spelled
    # In-Progress or Parked must be read the same as the lowercase names above.
    return {(label.get("name") or "").casefold() for label in item.get("labels", [])}


def open_builder_prs(gh, cfg: Config) -> list[Holder]:
    holders = []
    for pr in gh.paginate(f"/repos/{cfg.repo}/pulls", {"state": "open"}):
        if not is_builder_pr(pr):
            continue
        files: list[str] = []
        for f in gh.paginate(f"/repos/{cfg.repo}/pulls/{pr['number']}/files"):
            for key in ("filename", "previous_filename"):
                if f.get(key) and f[key] not in files:
                    files.append(f[key])
        holders.append(Holder(int(pr["number"]), "pr", files, closes(pr.get("body"))))
    return holders


def is_stopped(issue: dict) -> bool:
    """Closed, parked or done: the job is not building, whatever other labels it has."""
    return issue.get("state") == "closed" or bool(labels_of(issue) & NOT_BUILDING_LABELS)


def holds_files(issue: dict, build_running=lambda issue: False) -> bool:
    """Only a job that is truly building holds its Files in scope. build_running(issue) says
    whether the build job recorded for a closed, parked or done job can still write."""
    if "pull_request" in issue or IN_PROGRESS_LABEL not in labels_of(issue):
        return False
    if is_stopped(issue):
        # Closing a job, parking it or marking it done cancels nothing, so a droid already
        # running for it can still push. Its files stay held until that build job has ended.
        return build_running(issue)
    return True


def recorded_run(gh, cfg: Config, number: int) -> str | None:
    """The build run the gate recorded in the issue's overlap comment when it last started."""
    for c in gh.paginate(f"/repos/{cfg.repo}/issues/{number}/comments"):
        if (c.get("user") or {}).get("login") == COMMENT_AUTHOR and MARKER in (c.get("body") or ""):
            found = RUN_MARKER_RE.search(c.get("body") or "")
            return found.group(1) if found else None
    return None


def build_is_running(gh, cfg: Config, number: int) -> bool:
    """Whether the build the gate recorded for this job can still write."""
    run_id = recorded_run(gh, cfg, number)
    return run_id is not None and run_is_live(gh, cfg, run_id, number)


def run_is_live(gh, cfg: Config, run_id: str, number: int) -> bool:
    """Whether the build job of run_id can still write. Only GitHub Actions state proves a
    writer has stopped, never the issue's state or labels: the run is gone (404), the run is
    completed, or the latest attempt's build job is completed. Anything else, an unreadable
    answer included, counts as still writing."""

    def unreadable(exc: GitHubError) -> bool:
        print(f"::warning::overlap-check: build run {run_id} of #{number} could not be read "
              f"({exc}), so #{number} still holds its files.")
        return True

    try:
        run = gh.get(f"/repos/{cfg.repo}/actions/runs/{run_id}")
    except GitHubError as exc:
        return False if exc.status == 404 else unreadable(exc)
    if (run or {}).get("status") == "completed":
        return False
    # The run stays in progress while its release job runs, after the droid has stopped, so
    # the build job itself decides. filter=latest follows a re-run to its newest attempt.
    try:
        jobs = (gh.get(f"/repos/{cfg.repo}/actions/runs/{run_id}/jobs",
                       {"filter": "latest", "per_page": 100}) or {}).get("jobs") or []
    except GitHubError as exc:
        return unreadable(exc)
    builds = [j for j in jobs if (j.get("name") or "").split("/")[-1].strip() == BUILD_JOB]
    # No build job listed yet means it has not been created, not that it has ended.
    return not builds or any(j.get("status") != "completed" for j in builds)


def in_progress_issues(gh, cfg: Config) -> list[Holder]:
    # Closed issues too: one closed while its droid still runs keeps in-progress until the
    # release, and holds its files until then.
    found = gh.paginate(
        f"/repos/{cfg.repo}/issues",
        {"state": "all", "labels": f"{JOB_LABEL},{IN_PROGRESS_LABEL}"},
    )

    def running(i: dict) -> bool:
        return build_is_running(gh, cfg, int(i["number"]))

    holders = [Holder(int(i["number"]), "issue", parse_scope(i.get("body"))) for i in found if holds_files(i, running)]
    # A re-run of a failed build writes again after its release put the job back to waiting,
    # so a waiting job whose recorded build can still write holds its files too.
    seen = {int(i["number"]) for i in found}
    for i in gh.paginate(f"/repos/{cfg.repo}/issues", {"state": "open", "labels": f"{JOB_LABEL},{WAITING_LABEL}"}):
        if int(i["number"]) not in seen and "pull_request" not in i and running(i):
            holders.append(Holder(int(i["number"]), "issue", parse_scope(i.get("body"))))
    return holders


# ---------------------------------------------------------------- one job, one writer


def head_branch(pr: dict | None, repo: str) -> str | None:
    """The pull request's branch when a build can check it out: a plain name in this repo."""
    head = (pr or {}).get("head") or {}
    ref = head.get("ref") or ""
    if (head.get("repo") or {}).get("full_name") != repo or not BRANCH_RE.match(ref) or ".." in ref:
        return None
    return ref


def trusted_head(gh, cfg: Config, pr: dict) -> bool:
    try:
        return authenticated_head(gh, cfg, pr)
    except Exception as exc:
        # An unreadable activity is a technical hold on this PR only, never proof
        # of absence, and must not prevent independent waiting jobs from running.
        print(f"::warning::Factory head provenance could not be read ({type(exc).__name__}); continuation refused.")
        return False


def authenticated_head(gh, cfg: Config, pr: dict) -> bool:
    """GitHub's latest ref activity authenticates the producer of this exact head.

    Do not filter activities by actor or activity type: doing so hides a later human
    push or deletion. One descending result is sufficient; no missing page is skipped.
    A PR author, commit email, branch prefix or collaborator permission is not evidence.
    """
    branch = head_branch(pr, cfg.repo)
    sha = (pr.get("head") or {}).get("sha") or ""
    if not branch or not re.fullmatch(r"[0-9a-f]{40}", sha):
        return False
    bot = gh.get("/users/factory-droid%5Bbot%5D")
    if not (bot.get("login") == FACTORY_LOGIN and bot.get("type") == "Bot"
            and isinstance(bot.get("id"), int) and bot["id"] > 0
            and bot.get("html_url") == "https://github.com/apps/factory-droid"):
        return False
    ref = f"refs/heads/{branch}"
    latest = gh.get(f"/repos/{cfg.repo}/activity", {"ref": ref, "direction": "desc", "per_page": 1})
    if not isinstance(latest, list) or len(latest) != 1:
        return False
    activity = latest[0]
    actor = activity.get("actor") or {}
    if not (activity.get("ref") == ref and activity.get("after") == sha
            and activity.get("activity_type") in {"push", "force_push", "branch_creation"}
            and all(actor.get(k) == bot[k] for k in ("id", "login", "type"))):
        return False
    current = gh.get(f"/repos/{cfg.repo}/git/ref/heads/{urllib.parse.quote(branch, safe='')}")
    return current.get("ref") == ref and (current.get("object") or {}).get("sha") == sha


def default_head(gh, cfg: Config) -> str:
    branch = gh.get(f"/repos/{cfg.repo}")["default_branch"]
    if not BRANCH_RE.fullmatch(branch) or ".." in branch:
        raise ValueError("invalid default branch")
    ref = gh.get(f"/repos/{cfg.repo}/git/ref/heads/{urllib.parse.quote(branch, safe='')}")
    sha = (ref.get("object") or {}).get("sha") or ""
    if ref.get("ref") != f"refs/heads/{branch}" or not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("default branch has no immutable head")
    return sha


@dataclass
class Delivery:
    """The builder pull requests that close one job."""
    open: list[dict] = field(default_factory=list)  # oldest first
    merged: list[dict] = field(default_factory=list)  # newest merge first
    reopened_after_merge: bool = False
    target: dict | None = None  # the open pull request a new build continues

    @property
    def winner(self) -> dict | None:
        """The merged pull request that already delivered this job, unless the job was reopened
        after that merge. A merged result wins over any pull request still open beside it."""
        if not self.merged or self.reopened_after_merge:
            return None
        return self.merged[0]


def from_repo(source: dict, repo: str) -> bool:
    return ((source.get("repository") or {}).get("full_name") == repo
            or (source.get("repository_url") or "").endswith(f"/repos/{repo}"))


def job_delivery(gh, cfg: Config, number: int) -> Delivery:
    """Open builder pull requests that close the job, from the pull request list, and merged
    ones, from the issue's timeline, where GitHub records every pull request that names it."""
    opened = sorted(
        (p for p in gh.paginate(f"/repos/{cfg.repo}/pulls", {"state": "open"})
         if is_builder_pr(p) and head_branch(p, cfg.repo) and number in closes(p.get("body"))),
        key=lambda p: int(p["number"]))
    reopened: list[str] = []
    candidates: set[int] = set()
    for event in gh.paginate(f"/repos/{cfg.repo}/issues/{number}/timeline"):
        if event.get("event") == "reopened":
            reopened.append(event.get("created_at") or "")
        elif event.get("event") == "cross-referenced":
            source = (event.get("source") or {}).get("issue") or {}
            if "pull_request" in source and from_repo(source, cfg.repo) and number in closes(source.get("body")):
                candidates.add(int(source["number"]))
    merged = []
    for n in sorted(candidates - {int(p["number"]) for p in opened}):
        p = gh.get(f"/repos/{cfg.repo}/pulls/{n}") or {}
        if p.get("merged_at") and is_builder_pr(p) and number in closes(p.get("body")):
            merged.append(p)
    merged.sort(key=lambda p: p["merged_at"], reverse=True)
    after = bool(merged) and any(t > merged[0]["merged_at"] for t in reopened)
    # Only the oldest existing PR is eligible. Never bypass its owner by starting a
    # newer PR or creating a duplicate when its current head is not authenticated.
    target = opened[0] if opened and trusted_head(gh, cfg, opened[0]) else None
    return Delivery(opened, merged, after, target)


def trust_wait(gh, cfg: Config, number: int, delivery: Delivery) -> None:
    remove_label(gh, cfg, number, IN_PROGRESS_LABEL)
    add_labels(gh, cfg, number, [JOB_LABEL, WAITING_LABEL])
    upsert_comment(gh, cfg, number, "\n".join([
        MARKER,
        f"Existing pull request #{delivery.open[0]['number']} remains with its current owner. "
        "Its current head has no matching authenticated Factory ref activity. "
        "Factory will not execute this head with build secrets or create another pull request. "
        "The current owner can finish it; automatic continuation requires a verified Factory-produced head.",
    ]))


def live_owner(gh, cfg: Config, number: int, before: int | None = None) -> str | None:
    """Another run that already builds this job and can still write: its recorded build, or a
    claim posted before this run's claim (any claim when before is None)."""
    for c in gh.paginate(f"/repos/{cfg.repo}/issues/{number}/comments"):
        if (c.get("user") or {}).get("login") != COMMENT_AUTHOR:
            continue
        body = c.get("body") or ""
        found = RUN_MARKER_RE.search(body) if MARKER in body else None
        if found is None and (before is None or int(c["id"]) < before):
            found = CLAIM_RE.search(body)
        run = found.group(1) if found else None
        if run and run != cfg.run_id and run_is_live(gh, cfg, run, number):
            return run
    return None


def run_url(cfg: Config, run_id: str) -> str:
    server = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
    return f"{server}/{cfg.repo}/actions/runs/{run_id}"


def post_claim(gh, cfg: Config, number: int) -> int | None:
    """Claim the job for this run. Returns the claim's comment id."""
    if not cfg.run_id:
        return None
    body = "\n".join([f"<!-- factory-overlap-claim:v1 run={cfg.run_id} -->",
                      f"Run {cfg.run_id} is checking whether it may build this job."])
    made = gh.post(f"/repos/{cfg.repo}/issues/{number}/comments", {"body": body}) or {}
    if made.get("id"):
        return int(made["id"])
    for c in gh.paginate(f"/repos/{cfg.repo}/issues/{number}/comments"):
        if c.get("body") == body:
            return int(c["id"])
    return None


def drop_claim(gh, cfg: Config, claim_id: int | None) -> None:
    """A claim only matters while its gate decides. The Started comment carries the lease
    from then on, so the claim is removed."""
    if claim_id is None:
        return
    try:
        gh.delete(f"/repos/{cfg.repo}/issues/comments/{claim_id}")
    except GitHubError as exc:
        if exc.status != 404:
            raise


def follow(gh, cfg: Config, number: int, owner: str, claim_id: int | None = None) -> None:
    """Leave the job to the run already building it, with a receipt naming that run. The
    job's labels and its comment belong to that run, so neither changes."""
    me = cfg.run_id or "unknown"
    body = "\n".join([
        RECEIPT_MARKER,
        f"<!-- factory-overlap-follow:v1 run={me} owner={owner} -->",
        f"Run {me} did not build this job, because run {owner} is already building it "
        f"({run_url(cfg, owner)}). One job has one writer, so this run follows that build.",
    ])
    print(f"overlap-check: #{number} is already being built by run {owner}, so run {me} follows it and does not build.")
    if claim_id is not None:
        gh.patch(f"/repos/{cfg.repo}/issues/comments/{claim_id}", {"body": body})
    else:
        gh.post(f"/repos/{cfg.repo}/issues/{number}/comments", {"body": body})


def delivered_body(winner: dict, run_id: str | None, still_open: list[dict] | None = None) -> str:
    sha = winner.get("merge_commit_sha") or ""
    lines = [
        MARKER,
        f"Already delivered. Pull request #{winner['number']} merged this job into main"
        f"{f' as {sha}' if sha else ''}, so it is not built again. To build more on top of "
        "that work, reopen this issue or open a new Job issue.",
    ]
    if still_open:
        names = ", ".join(f"#{p['number']}" for p in still_open)
        lines.append(f"Pull request {names} also closes this job and is still open. It is left as it is.")
    if run_id:
        lines.append(f"<!-- factory-overlap-run:{run_id} -->")
    return "\n".join(lines)


def deliver(gh, cfg: Config, number: int, winner: dict, still_open: list[dict], labels: set[str],
            run_id: str | None) -> None:
    for name in (IN_PROGRESS_LABEL, WAITING_LABEL):
        if name in labels:
            remove_label(gh, cfg, number, name)
    upsert_comment(gh, cfg, number, delivered_body(winner, run_id, still_open))
    print(f"overlap-check: #{number} was already delivered by merged pull request #{winner['number']}, so it does not build again.")


def continuation_note(number: int, d: Delivery, repo: str) -> str:
    """What the droid must do differently because the job already has a pull request."""
    lines: list[str] = []
    if d.target:
        t = d.target
        head = (t.get("head") or {}).get("sha") or "unknown"
        lines.append(
            f"This job already has open pull request #{t['number']} on branch {head_branch(t, repo)} "
            f"(head {head} when this build was admitted), and this checkout is that branch. "
            "Continue that pull request instead of the branch and pull request steps above: keep "
            "its commits, add your commits on top, push them to the same branch so the same pull "
            f"request updates, and update the body of #{t['number']} with each acceptance check. "
            "Do not open another pull request or branch for this job, do not force-push, and do "
            "not close any pull request or delete any branch.")
        others = [p for p in d.open if p is not t]
        if others:
            names = ", ".join(f"#{p['number']}" for p in others)
            lines.append(f"Pull requests {names} also close #{number}. Leave them as they are and "
                         f"name them in #{t['number']} so a person can decide which work to keep.")
    if d.merged and not d.target:
        m = d.merged[0]
        lines.append(f"Pull request #{m['number']} already merged earlier work for this job into main, "
                     "and the job was reopened after that merge. Build only what is still missing, "
                     f"on top of main, and say in your pull request that #{m['number']} delivered the earlier part.")
    return "\n\n".join(lines)


def run_owner(gh, cfg: Config, number: int) -> tuple[bool, str, Delivery | None]:
    """Whether this run may write for the job now. The gate's admission is the lease: the
    job's comment names the run it admitted, and only that run builds."""
    issue = gh.get(f"/repos/{cfg.repo}/issues/{number}")
    if is_stopped(issue):
        return False, f"#{number} is closed, parked or done, so this run does not build it.", None
    recorded = recorded_run(gh, cfg, number)
    if not cfg.run_id or recorded != cfg.run_id:
        return False, (f"#{number} was admitted for run {recorded or 'none'}, not this run "
                       f"({cfg.run_id or 'unknown'}), so this run does not write. Dispatch the "
                       "builder for the job instead of re-running this run."), None
    d = job_delivery(gh, cfg, number)
    if d.winner:
        return False, (f"#{number} was already delivered by merged pull request "
                       f"#{d.winner['number']}, so this run does not build it again."), d
    if d.target:
        return True, f"run {cfg.run_id} owns #{number} and continues pull request #{d.target['number']}.", d
    if d.open:
        return False, "existing pull request head is not authenticated as Factory-produced; leave it with its current owner.", d
    return True, f"run {cfg.run_id} owns #{number}.", d


def judge(gh, cfg: Config, issue: dict, only_older_issues: bool = False) -> Verdict:
    number = int(issue["number"])
    issues = in_progress_issues(gh, cfg)
    if only_older_issues:
        issues = [i for i in issues if i.number < number]
    return evaluate(number, parse_scope(issue.get("body")), open_builder_prs(gh, cfg), issues)


def add_labels(gh, cfg: Config, number: int, names: list[str]) -> None:
    gh.post(f"/repos/{cfg.repo}/issues/{number}/labels", {"labels": names})


def remove_label(gh, cfg: Config, number: int, name: str) -> None:
    try:
        gh.delete(f"/repos/{cfg.repo}/issues/{number}/labels/{urllib.parse.quote(name)}")
    except GitHubError as exc:
        if exc.status != 404:
            raise


def upsert_comment(gh, cfg: Config, number: int, body: str, create: bool = True) -> None:
    """One overlap comment per issue, edited in place when what it says changes."""
    for c in gh.paginate(f"/repos/{cfg.repo}/issues/{number}/comments"):
        if (c.get("user") or {}).get("login") == COMMENT_AUTHOR and MARKER in (c.get("body") or ""):
            if c.get("body") != body:
                gh.patch(f"/repos/{cfg.repo}/issues/comments/{c['id']}", {"body": body})
            return
    if create:
        gh.post(f"/repos/{cfg.repo}/issues/{number}/comments", {"body": body})


def hold(gh, cfg: Config, number: int, v: Verdict, labels: set[str]) -> None:
    if IN_PROGRESS_LABEL in labels:
        remove_label(gh, cfg, number, IN_PROGRESS_LABEL)
    add_labels(gh, cfg, number, [JOB_LABEL, WAITING_LABEL])
    upsert_comment(gh, cfg, number, comment_body(v))


def run_check(gh, cfg: Config, number: int, sleep=time.sleep) -> bool:
    """True when the build may start. Leaves the issue labeled for what happened."""
    issue = gh.get(f"/repos/{cfg.repo}/issues/{number}")
    labels = labels_of(issue)
    if cfg.reopened and issue.get("state") != "closed" and "done" in labels and "parked" not in labels:
        owner = live_owner(gh, cfg, number)
        if owner:
            follow(gh, cfg, number, owner)
            return False
        remove_label(gh, cfg, number, "done")
        issue = gh.get(f"/repos/{cfg.repo}/issues/{number}")
        labels = labels_of(issue)
    if is_stopped(issue):
        # A stopped job holds no files, so building it would let a colliding job build
        # beside it unseen. Parked is the only way a job stays off Factory.
        print(f"overlap-check: #{number} is closed, parked or done, so it does not build. "
              "Reopen it or remove parked or done to build it.")
        return False
    # One job has one writer. An opened, labeled, dispatched or re-run event for a job another
    # run is still building follows that run instead of starting a second droid.
    owner = live_owner(gh, cfg, number)
    if owner:
        follow(gh, cfg, number, owner)
        return False
    delivery = job_delivery(gh, cfg, number)
    if delivery.winner:
        deliver(gh, cfg, number, delivery.winner, delivery.open, labels, recorded_run(gh, cfg, number))
        return False
    if delivery.open and not delivery.target:
        trust_wait(gh, cfg, number, delivery)
        return False
    first = judge(gh, cfg, issue)
    report(number, first)
    if not first.start:
        hold(gh, cfg, number, first, labels)
        return False
    claim_id = post_claim(gh, cfg, number)
    add_labels(gh, cfg, number, [JOB_LABEL, IN_PROGRESS_LABEL])
    # Two jobs judged at the same moment both see a clear path, label themselves
    # in-progress and would collide. After a pause each looks again, and only the newer
    # issue yields to an older one, so exactly one of them builds. Two runs for the same
    # job settle the same way on their claims: the older live claim builds.
    sleep(cfg.settle_seconds)
    owner = live_owner(gh, cfg, number, before=claim_id)
    if owner:
        follow(gh, cfg, number, owner, claim_id)
        return False
    second = judge(gh, cfg, issue, only_older_issues=True)
    if not second.start:
        drop_claim(gh, cfg, claim_id)
        report(number, second, again=True)
        hold(gh, cfg, number, second, labels | {IN_PROGRESS_LABEL})
        return False
    # Recording this run first means a release from an older run of this job, from here on,
    # sees it has been replaced and leaves the labels alone.
    upsert_comment(gh, cfg, number, comment_body(second, cfg.run_id, delivery.target), create=bool(cfg.run_id))
    drop_claim(gh, cfg, claim_id)
    now = gh.get(f"/repos/{cfg.repo}/issues/{number}")
    if WAITING_LABEL in labels_of(now):
        remove_label(gh, cfg, number, WAITING_LABEL)
    # A job parked or marked done before this run was recorded as its build would hold
    # nothing while the droid writes, so it must not build. From here on the record keeps
    # its files held until the run ends.
    if is_stopped(now):
        print(f"overlap-check: #{number} was closed, parked or done before its build began, so it does not build.")
        remove_label(gh, cfg, number, IN_PROGRESS_LABEL)
        upsert_comment(gh, cfg, number, stopped_body(), create=False)
        return False
    if IN_PROGRESS_LABEL not in labels_of(now):
        add_labels(gh, cfg, number, [JOB_LABEL, IN_PROGRESS_LABEL])
    return True


def report(number: int, v: Verdict, again: bool = False) -> None:
    when = " on the second look" if again else ""
    scope = ", ".join(v.scope) or "nothing listed"
    print(f"overlap-check: #{number} files in scope: {scope}")
    if not v.scope:
        print(f"::warning::overlap-check: #{number} lists no Files in scope, so overlap cannot be checked.")
    if v.start:
        print(f"overlap-check: #{number} starts ({v.open_prs} open builder pull requests).")
    else:
        print(f"overlap-check: #{number} waits{when}: {'; '.join(v.lines())}")


def claim(gh, cfg: Config, number: int) -> bool:
    """Take a waiting job for one dispatch by removing its waiting label. GitHub answers 404
    when the label is already gone, so when two runs race for the same job only the first
    removal succeeds and only that run dispatches it."""
    try:
        gh.delete(f"/repos/{cfg.repo}/issues/{number}/labels/{urllib.parse.quote(WAITING_LABEL)}")
    except GitHubError as exc:
        if exc.status == 404:
            return False
        raise
    return True


def run_next(gh, cfg: Config, dispatch, skip: set[int] = frozenset()) -> list[int]:
    """Dispatch every waiting Job issue that would start now, oldest first. Only a job that is
    truly building holds files, so a job held by a closed, parked or done one starts. A job dispatched
    in this pass holds its files for the later ones, so two colliding jobs are never sent
    together. Writes nothing but the claim, and puts the claim back if the dispatch fails."""
    waiting = gh.paginate(
        f"/repos/{cfg.repo}/issues",
        {"state": "open", "labels": f"{JOB_LABEL},{WAITING_LABEL}", "sort": "created", "direction": "asc"},
    )
    prs = open_builder_prs(gh, cfg)
    holders = in_progress_issues(gh, cfg)
    building = {h.number for h in holders}
    sent: list[int] = []
    for issue in sorted((i for i in waiting if "pull_request" not in i), key=lambda i: int(i["number"])):
        number = int(issue["number"])
        if number in skip:
            print(f"overlap-check: waiting job #{number} was just released, so this pass does not send it.")
            continue
        if is_stopped(issue):
            print(f"overlap-check: waiting job #{number} is closed, parked or done, so it is not sent.")
            continue
        if number in building:
            print(f"overlap-check: waiting job #{number} is still being built (in-progress, or its "
                  "recorded build can still write), so it is not sent again.")
            continue
        delivery = job_delivery(gh, cfg, number)
        if delivery.open and not delivery.target and not delivery.winner:
            trust_wait(gh, cfg, number, delivery)
            continue
        v = evaluate(number, parse_scope(issue.get("body")), prs, holders)
        if not v.start:
            print(f"overlap-check: waiting job #{number} still waits: {'; '.join(v.lines())}")
            continue
        if not claim(gh, cfg, number):
            print(f"overlap-check: waiting job #{number} was already taken by another run.")
            continue
        try:
            dispatch(number)
        except Exception:
            add_labels(gh, cfg, number, [JOB_LABEL, WAITING_LABEL])
            raise
        holders.append(Holder(number, "issue", v.scope))
        sent.append(number)
        print(f"overlap-check: dispatched the builder for waiting job #{number}.")
    if not sent:
        print("overlap-check: no waiting job can start yet.")
    return sent


def stopped_body() -> str:
    return "\n".join([
        MARKER,
        "This job is closed, parked or done and no build is running for it, so it holds no files.",
    ])


def release_body(result: str, run_id: str = "") -> str:
    # The run stays recorded, so a re-run of this same run may build again, and any other
    # run sees from Actions that this one has stopped writing.
    record = [f"<!-- factory-overlap-run:{run_id} -->"] if run_id else []
    if result == "success":
        return "\n".join([
            MARKER,
            "The build finished without opening a pull request for this job, so it no longer "
            "holds its files. Add the job label again or dispatch the builder to build it again.",
            *record,
        ])
    return "\n".join([
        MARKER,
        f"The build did not finish (result: {result or 'unknown'}), so this job no longer holds "
        "its files and waits to start again. It starts on its own when a pull request or job "
        "issue in this repo closes, a job loses its in-progress label, or a job is marked "
        "parked or done.",
        *record,
    ])


def run_release(gh, cfg: Config, number: int, result: str) -> str:
    """After a build the gate started. Returns kept, released, waiting, stopped, delivered or
    superseded."""
    issue = gh.get(f"/repos/{cfg.repo}/issues/{number}")
    recorded = recorded_run(gh, cfg, number) if cfg.run_id else None
    if recorded and recorded != cfg.run_id:
        # A later gate admitted another run for this job. Its labels and comment are that
        # run's now, and this release must not free its files or queue it again.
        print(f"overlap-check: #{number} is now built by run {recorded}, not this run ({cfg.run_id}); nothing changes.")
        return "superseded"
    if is_stopped(issue):
        # The build can no longer write, so a job closed, parked or done while it built stops
        # holding now. A pull request it opened still holds its own changed files.
        remove_label(gh, cfg, number, IN_PROGRESS_LABEL)
        if issue.get("state") != "closed":
            upsert_comment(gh, cfg, number, stopped_body(), create=False)
        print(f"overlap-check: #{number} is closed, parked or done and its build ended; in-progress removed.")
        return "stopped"
    delivery = job_delivery(gh, cfg, number)
    if delivery.winner:
        # Queuing a delivered job again would only start a build that must not write. A pull
        # request still open beside the merged one holds its own changed files.
        deliver(gh, cfg, number, delivery.winner, delivery.open, labels_of(issue), cfg.run_id)
        return "delivered"
    if delivery.open and not delivery.target:
        trust_wait(gh, cfg, number, delivery)
        return "waiting"
    if delivery.open:
        print(f"overlap-check: #{number} has an open pull request, which holds its files.")
        return "kept"
    remove_label(gh, cfg, number, IN_PROGRESS_LABEL)
    if result == "success":
        upsert_comment(gh, cfg, number, release_body("success", cfg.run_id))
        print(f"overlap-check: #{number} built with no pull request; in-progress removed.")
        return "released"
    add_labels(gh, cfg, number, [JOB_LABEL, WAITING_LABEL])
    upsert_comment(gh, cfg, number, release_body(result, cfg.run_id))
    print(f"overlap-check: #{number} build ended {result or 'unknown'}; back to waiting.")
    return "waiting"


def workflow_file(workflow_ref: str) -> str:
    """owner/repo/.github/workflows/name.yml@refs/heads/main -> name.yml"""
    path = workflow_ref.split("@", 1)[0]
    return path.rsplit("/", 1)[-1]


def write_output(key: str, value: str) -> None:
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as fh:
            fh.write(f"{key}={value}\n")


def issue_number() -> int:
    """OVERLAP_ISSUE as a number; a manual dispatch may type it as #158."""
    return int(os.environ.get("OVERLAP_ISSUE", "").strip().lstrip("#"))


def main(argv: list[str]) -> int:
    if len(argv) != 1 or argv[0] not in ("check", "next", "owner", "verify", "release"):
        print("usage: overlap_check.py check|next|owner|verify|release", file=sys.stderr)
        return 2
    cfg = Config(
        repo=os.environ["GITHUB_REPOSITORY"],
        settle_seconds=float(os.environ.get("OVERLAP_SETTLE_SECONDS", "10")),
        run_id=os.environ.get("GITHUB_RUN_ID", ""),
        reopened=os.environ.get("OVERLAP_REOPENED") == "true",
    )
    gh = GitHub(os.environ["OVERLAP_TOKEN"], os.environ.get("GITHUB_API_URL", "https://api.github.com"))

    if argv[0] == "check":
        number = None
        try:
            number = issue_number()
            start = run_check(gh, cfg, number)
        except Exception as exc:  # any failure must leave the job where a restart finds it
            print(f"::error::overlap-check: #{number or os.environ.get('OVERLAP_ISSUE')} could not be checked: {exc!r}")
            write_output("start", "false")
            if number is not None:
                try:
                    remove_label(gh, cfg, number, IN_PROGRESS_LABEL)
                    add_labels(gh, cfg, number, [JOB_LABEL, WAITING_LABEL])
                except Exception:
                    pass
            return 1
        write_output("start", "true" if start else "false")
        return 0

    if argv[0] in ("owner", "verify"):
        try:
            number = issue_number()
            owns, why, delivery = run_owner(gh, cfg, number)
        except Exception as exc:  # unproven ownership never writes
            print(f"::error::overlap-check: #{os.environ.get('OVERLAP_ISSUE')} ownership could not be confirmed: {exc!r}")
            return 1
        if not owns:
            print(f"::error::overlap-check: {why}")
            return 1
        print(f"overlap-check: {why}")
        target = delivery.target if delivery else None
        if argv[0] == "verify":
            try:
                expected = os.environ.get("OVERLAP_EXPECTED_HEAD", "")
                local = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
                expected_pr = os.environ.get("OVERLAP_EXPECTED_PR", "")
                expected_branch = os.environ.get("OVERLAP_EXPECTED_BRANCH", "")
                if not re.fullmatch(r"[0-9a-f]{40}", expected) or local != expected:
                    raise ValueError("caller checkout differs from the admitted immutable head")
                if target:
                    if (str(target["number"]) != expected_pr or head_branch(target, cfg.repo) != expected_branch
                            or target["head"]["sha"] != expected):
                        raise ValueError("continuation head changed after selection")
                elif expected_pr or expected_branch:
                    raise ValueError("continuation pull request disappeared after selection")
            except Exception as exc:
                print(f"::error::overlap-check: immutable checkout could not be revalidated: {exc!r}")
                return 1
            return 0
        write_output("pr", str(target["number"]) if target else "")
        write_output("branch", head_branch(target, cfg.repo) or "" if target else "")
        write_output("head", target["head"]["sha"] if target else default_head(gh, cfg))
        note = continuation_note(number, delivery, cfg.repo) if delivery else ""
        path = os.environ.get("OVERLAP_NOTE_FILE", "")
        if note and path:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(note + "\n")
        write_output("note", "true" if note and path else "false")
        return 0

    if argv[0] == "release":
        try:
            outcome = run_release(gh, cfg, issue_number(), os.environ.get("BUILD_RESULT", ""))
        except Exception as exc:
            print(f"::error::overlap-check: #{os.environ.get('OVERLAP_ISSUE')} could not be released: {exc!r}")
            return 1
        # Removing in-progress with the workflow's own token starts no restart, so the caller
        # runs next itself whenever the release freed this job's files.
        write_output("restart", "false" if outcome in ("kept", "superseded") else "true")
        return 0

    workflow = workflow_file(os.environ["BUILDER_WORKFLOW_REF"])
    ref = os.environ.get("BUILDER_REF") or "main"

    def dispatch(number: int) -> None:
        gh.post(
            f"/repos/{cfg.repo}/actions/workflows/{urllib.parse.quote(workflow)}/dispatches",
            {"ref": ref, "inputs": {"issue": str(number)}},
        )

    try:
        skip = {issue_number()} if os.environ.get("OVERLAP_ISSUE", "").strip() else set()
        sent = run_next(gh, cfg, dispatch, skip)
    except Exception as exc:
        print(f"::error::overlap-check: waiting jobs could not be checked: {exc!r}")
        return 1
    write_output("dispatched", ",".join(str(n) for n in sent))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
