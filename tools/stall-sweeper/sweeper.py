#!/usr/bin/env python3
"""Stall sweeper for the Chat to Code Loop (Decision Log 2026-11-03, Every code job on the job
board goes to Factory now, none sit waiting).

Runs on GitHub's own schedule every 10 minutes, and on manual dispatch, from
.github/workflows/factory-stall-sweeper-reusable.yml. For every open issue whose title begins
with Job: and whose author is on the builder's allowlist, it applies the first rule that fits:

  1. No job label and no parked label: add job, comment once why, dispatch the builder.
  2. done, and the pull request that closes it is merged: close it as completed and comment
     the merge commit.
  3. waiting, nothing it waits on still holds it, and no builder run in the last 30 minutes:
     dispatch the builder.
  4. job with no in-progress, no waiting, no open pull request and no builder run in the
     last 30 minutes: dispatch the builder.
  5. in-progress with no builder run in progress and no open pull request for 45 minutes:
     remove in-progress and dispatch the builder.
  6. Its factory-droid pull request is open and Codex has not reviewed the current head after
     30 minutes: comment @codex review once per head.
  7. Its pull request is refused by the auto-merge gate for a blocking Codex finding or a
     failing check, and no builder run started in the last 30 minutes: comment what to fix and
     dispatch the builder. When a Codex finding comes back after it was fixed (Decision Log
     2026-11-02, No caps stop work), it marks the job needs-allison with a Recommend: line
     instead and stops restarting it. Rule 4 does the same when a rebuild after a build with
     no pull request again ends with no pull request.

A parked job is never touched, nor its pull request. A job marked needs-allison is not
restarted. No issue is dispatched twice in one sweep, and none is dispatched while a builder
run for it is queued or in progress. Every write goes through an allowlist of label, comment,
close and workflow dispatch calls, so the sweeper cannot merge, push, or change settings,
rulesets or access. A repository named ember is refused before any call.

SWEEPER_TOKEN (the workflow's own token) does every read and write. Label changes made with it
start no workflow, which is why the builder is dispatched explicitly. SWEEPER_DRY_RUN=1 prints
what would happen and writes nothing. Standard library only.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field

FACTORY_LOGIN = "factory-droid[bot]"
CODEX_LOGIN = "chatgpt-codex-connector[bot]"
ACTIONS_LOGIN = "github-actions[bot]"
BUILDER_BRANCH_PREFIX = "job/"
JOB_PREFIX = "Job:"

JOB = "job"
IN_PROGRESS = "in-progress"
WAITING = "waiting"
PARKED = "parked"
DONE = "done"
NEEDS_ALLISON = "needs-allison"

# The same authors the builder accepts (factory-builder-reusable.yml). A builder dispatch
# skips that check, so the sweeper must never dispatch a Job: issue anyone else opened.
DEFAULT_AUTHORS = ("AllisonGaddy", "expertpartners", "expertpartners-ember", "expertpartners-aura")

RECENT_RUN = dt.timedelta(minutes=30)
IN_PROGRESS_QUIET = dt.timedelta(minutes=45)
CODEX_WAIT = dt.timedelta(minutes=30)
# A build can run 60 minutes after its gate, so look back far enough to see it.
RUN_LOOKBACK = dt.timedelta(hours=3)
ACTIVE_STATUSES = {"queued", "in_progress", "waiting", "requested", "pending"}

MARK = "factory-stall-sweeper:v1"
LABELED_MARK = f"<!-- {MARK} labeled -->"
CLOSED_RE = re.compile(rf"<!-- {MARK} closed pr=(\d+) -->")
CODEX_ASK_RE = re.compile(rf"<!-- {MARK} codex-review head=([0-9a-f]{{40}}) -->")
FIX_RE = re.compile(rf"<!-- {MARK} fix head=([0-9a-f]{{40}}) digest=([0-9a-f]+) findings=(\S*) -->")
RETURNED_RE = re.compile(rf"<!-- {MARK} returned head=([0-9a-f]{{40}}) -->")
REBUILT_MARK = f"<!-- {MARK} rebuilt-no-pr -->"
NO_PR_RETURNED_MARK = f"<!-- {MARK} no-pr-returned -->"

OVERLAP_MARK = "<!-- factory-overlap-check:v1 -->"
# The overlap check's release text after a build that succeeded without a pull request
# (tools/overlap-check/overlap_check.py, release_body).
NO_PR_RELEASE = "The build finished without opening a pull request"
WAITING_ON_RE = re.compile(r"^Waiting on #(\d+)\b", re.MULTILINE)
CLOSES_RE = re.compile(r"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s*:?\s+#(\d+)\b", re.IGNORECASE)
GATE_MARK_RE = re.compile(r"<!-- auto-merge-gate:v1 head=([0-9a-f]{40}) -->")
CODEX_STATE_RE = re.compile(r"<!--\s*codex-review-state:v1\s+(\{.*?\})\s*-->", re.DOTALL)
CODEX_RECEIPT_MARK = "codex-review-receipt:v1"
CODEX_REVIEWED_COMMIT_RE = re.compile(r"\*\*Reviewed commit:\*\*\s*`([0-9a-fA-F]{10,40})`")
OVERLAP_ISSUE_RE = re.compile(r"\bOVERLAP_ISSUE:\s*#?(\d+)\b")

# Gate refusal lines (tools/auto-merge-gate/gate.py) that a builder can fix. Pending checks,
# a review not done yet, GitHub still computing mergeability, or review evidence the gate
# could not read are not stalls a rebuild can clear.
CHECK_REASONS = (
    re.compile(r"^Check `.+` finished as \S+\.$"),
    re.compile(r"^Commit status `.+` is (?:failure|error)\.$"),
)
# A P0, P1 or unreadable-severity Codex finding the gate names as blocking (blocking_findings).
CODEX_REASONS = (
    re.compile(r"^Codex (?:P\d+ )?(?:code|security) finding\b.* blocks: "
               r"(?:Codex raised it on head \S+|its thread from \S+ is unresolved)\."),
)
REASON_TITLE_RE = re.compile(r'^Codex [^"]* finding[^"]* "(.*)"(?: \((https://\S+)\))? blocks: ')


class GitHubError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(f"HTTP {status}: {message}")
        self.status = status
        self.message = message


class RefusedWrite(Exception):
    """A write the sweeper is never allowed to make."""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class GitHub:
    """Minimal REST client. Tests replace it with a fake that has the same methods."""

    def __init__(self, token: str, api_url: str = "https://api.github.com"):
        self.token = token
        self.api_url = api_url.rstrip("/")

    def _req(self, method: str, url: str, body=None) -> urllib.request.Request:
        if not url.startswith("http"):
            url = self.api_url + url
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Accept", "application/vnd.github+json")
        req.add_header("Authorization", f"Bearer {self.token}")
        req.add_header("X-GitHub-Api-Version", "2022-11-28")
        if data is not None:
            req.add_header("Content-Type", "application/json")
        return req

    @staticmethod
    def _error(exc: urllib.error.HTTPError) -> GitHubError:
        detail = exc.read().decode("utf-8", "replace")
        try:
            detail = json.loads(detail).get("message", detail)
        except (ValueError, AttributeError):
            pass
        return GitHubError(exc.code, detail)

    def _request(self, method: str, url: str, body=None):
        try:
            with urllib.request.urlopen(self._req(method, url, body), timeout=30) as resp:
                raw = resp.read()
                link = resp.headers.get("Link", "") or ""
        except urllib.error.HTTPError as exc:
            raise self._error(exc) from None
        except (urllib.error.URLError, OSError) as exc:
            raise GitHubError(0, f"{method} {url} failed: {exc}") from None
        return (json.loads(raw) if raw else None), link

    def get(self, path: str, params: dict | None = None):
        if params:
            path += "?" + urllib.parse.urlencode(params)
        return self._request("GET", path)[0]

    def paginate(self, path: str, params: dict | None = None, key: str | None = None) -> list:
        query = dict(params or {})
        query.setdefault("per_page", 100)
        url = f"{path}?{urllib.parse.urlencode(query)}"
        items: list = []
        while url:
            data, link = self._request("GET", url)
            items.extend((data or {}).get(key, []) if key else (data or []))
            url = next((p.split(";")[0].strip()[1:-1] for p in link.split(",") if 'rel="next"' in p), None)
        return items

    def text(self, path: str) -> str:
        """A redirected download, such as a job log. The signed URL GitHub redirects to
        must be fetched without the API token."""
        opener = urllib.request.build_opener(_NoRedirect)
        try:
            with opener.open(self._req("GET", path), timeout=30) as resp:
                return resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            if exc.code not in (301, 302, 303, 307, 308):
                raise self._error(exc) from None
            location = exc.headers.get("Location")
        except (urllib.error.URLError, OSError) as exc:
            raise GitHubError(0, f"GET {path} failed: {exc}") from None
        try:
            with urllib.request.urlopen(location, timeout=60) as resp:
                return resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            raise GitHubError(exc.code, f"download of {path} failed") from None
        except (urllib.error.URLError, OSError, ValueError) as exc:
            raise GitHubError(0, f"download of {path} failed: {exc}") from None

    def graphql(self, query: str, variables: dict):
        data, _ = self._request("POST", self.api_url + "/graphql", {"query": query, "variables": variables})
        if not data or data.get("errors"):
            raise GitHubError(502, f"GraphQL query failed: {(data or {}).get('errors')}")
        return data["data"]

    def post(self, path: str, body: dict):
        return self._request("POST", path, body)[0]

    def patch(self, path: str, body: dict):
        return self._request("PATCH", path, body)[0]

    def delete(self, path: str):
        return self._request("DELETE", path)[0]


# ---------------------------------------------------------------- helpers


def parse_time(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))


def iso(t: dt.datetime) -> str:
    return t.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def minutes(delta: dt.timedelta) -> int:
    return int(delta.total_seconds() // 60)


def labels_of(item: dict) -> set[str]:
    return {label.get("name") for label in item.get("labels", [])}


def login_of(item: dict) -> str:
    return (item.get("user") or {}).get("login") or ""


def is_excluded_repo(repo: str) -> bool:
    # Decision Log 2026-11-01: Ember's repository is never touched by the loop's automation.
    return repo.split("/")[-1].lower() == "ember"


def closes(body: str | None) -> set[int]:
    return {int(n) for n in CLOSES_RE.findall(body or "")}


def pr_issues(pr: dict) -> set[int]:
    """Job issues a pull request belongs to: the ones its body closes, and the job/N- branch."""
    found = closes(pr.get("body"))
    m = re.match(r"^job/(\d+)-", (pr.get("head") or {}).get("ref") or "")
    if m:
        found.add(int(m.group(1)))
    return found


def is_builder_pr(pr: dict, repo: str) -> bool:
    """A pull request the loop opened. Anyone can open a fork pull request on a job/ branch,
    so only a branch in this repo counts, since pushing one takes write access."""
    head = pr.get("head") or {}
    if ((head.get("repo") or {}).get("full_name") or "").lower() != repo.lower():
        return False
    return login_of(pr) == FACTORY_LOGIN or (head.get("ref") or "").startswith(BUILDER_BRANCH_PREFIX)


def codex_reviewed(comments: list, sha: str) -> bool:
    """Codex's review summary or a clean receipt names this head. A review in progress on
    the head counts, so the sweeper never asks twice for the same commit."""
    for c in comments:
        if login_of(c) != CODEX_LOGIN:
            continue
        body = c.get("body") or ""
        m = CODEX_STATE_RE.search(body)
        if m:
            try:
                state = json.loads(m.group(1))
            except ValueError:
                state = {}
            if ((state.get("code_review") or {}).get("commit_sha") or "") == sha:
                return True
        if CODEX_RECEIPT_MARK in body and "Codex Security Review" not in body:
            r = CODEX_REVIEWED_COMMIT_RE.search(body)
            if r and sha.lower().startswith(r.group(1).lower()):
                return True
    return False


def gate_refusal(comments: list, sha: str) -> list[str] | None:
    """The reasons in the auto-merge gate's refusal comment for this head, or None."""
    for c in comments:
        if login_of(c) != ACTIONS_LOGIN:
            continue
        body = c.get("body") or ""
        m = GATE_MARK_RE.search(body)
        if m and m.group(1) == sha:
            return [line[2:].strip() for line in body.splitlines() if line.startswith("- ")]
    return None


def is_check_reason(reason: str) -> bool:
    return any(p.search(reason) for p in CHECK_REASONS)


def is_codex_reason(reason: str) -> bool:
    return any(p.search(reason) for p in CODEX_REASONS)


def _plain(line: str) -> str:
    line = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", line)
    line = re.sub(r"<[^>]+>", "", line)
    line = line.replace("*", "").replace("`", "")
    return re.sub(r"\s+", " ", line).strip().lower()


def finding_title(body: str) -> str:
    """The title line of a Codex finding, without badges, markup or case. It is the line with
    the severity badge; a security finding puts a marker and a heading above it."""
    lines = (body or "").splitlines()
    badge = next((line for line in lines if re.search(r"!\[P\d Badge\]", line)), None)
    if badge is not None and _plain(badge):
        return _plain(badge)
    return next((_plain(line) for line in lines if _plain(line)), "")


@dataclass
class Finding:
    thread: str
    path: str
    title: str
    url: str
    resolved: bool = False

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(f"{self.path}\n{self.title}".encode()).hexdigest()[:12]


def blocking_threads(threads: list[Finding], reasons: list[str]) -> list[Finding]:
    """The Codex threads behind the findings the gate says block, matched by the link the
    gate quotes, or by title when it quotes none. A finding raised on the current head blocks
    even when its thread is resolved, because resolving a thread does not fix the code."""
    urls, titles = set(), set()
    for r in reasons:
        m = REASON_TITLE_RE.match(r) if is_codex_reason(r) else None
        if m and m.group(2):
            urls.add(m.group(2))
        elif m:
            titles.add(_plain(m.group(1)))
    return [t for t in threads if (t.url and t.url in urls) or t.title in titles]


def holder_finished(item: dict) -> bool:
    """Whether a holder the overlap check named still holds the waiting job's files. A job
    issue holds them only while it carries in-progress, the same test the overlap check
    uses; an open pull request holds them until it closes."""
    if item.get("state") == "closed" or labels_of(item) & {PARKED, DONE}:
        return True
    return "pull_request" not in item and IN_PROGRESS not in labels_of(item)


def waited_on(comments: list) -> list[int]:
    """The issues and pull requests the overlap check says this job waits on."""
    for c in reversed(comments):
        body = c.get("body") or ""
        if login_of(c) == ACTIONS_LOGIN and OVERLAP_MARK in body:
            return [int(n) for n in WAITING_ON_RE.findall(body)]
    return []


# ---------------------------------------------------------------- builder runs


UNKNOWN = -1


@dataclass
class Run:
    id: int
    event: str
    title: str
    status: str
    started: dt.datetime
    updated: dt.datetime

    @property
    def active(self) -> bool:
        return self.status in ACTIVE_STATUSES


class BuilderRuns:
    """Recent runs of the builder workflow, tied to the job issue each one builds.

    An issues-event run carries the issue title. A dispatched run carries no issue at all,
    so its issue is read from the OVERLAP_ISSUE line in its gate job's log, once that job
    has finished. Logs are read only when a rule needs them, and once per sweep."""

    def __init__(self, gh, repo: str, workflow: str, now: dt.datetime, titles: dict[str, set[int]]):
        self.gh, self.repo, self.titles, self.now = gh, repo, titles, now
        found = gh.paginate(
            f"/repos/{repo}/actions/workflows/{urllib.parse.quote(workflow)}/runs",
            {"created": f">={iso(now - RUN_LOOKBACK)}"},
            key="workflow_runs",
        )
        self.runs = []
        for r in found:
            if r.get("event") not in ("issues", "workflow_dispatch"):
                continue
            started = parse_time(r.get("run_started_at") or r.get("created_at"))
            self.runs.append(Run(int(r["id"]), r["event"], r.get("display_title") or "", r.get("status") or "",
                                 started, parse_time(r.get("updated_at")) or started))
        self._issue: dict[int, set[int]] = {}

    def _gate_job(self, run: Run) -> dict | None:
        jobs = self.gh.paginate(f"/repos/{self.repo}/actions/runs/{run.id}/jobs", key="jobs")
        return next((j for j in jobs if (j.get("name") or "").split("/")[-1].strip() == "gate"), None)

    def issues_of(self, run: Run) -> set[int]:
        """The job issues a run builds: empty when it builds none, {UNKNOWN} when it may
        be building one that cannot be named yet."""
        if run.id in self._issue:
            return self._issue[run.id]
        found: set[int] = set()
        if run.event == "issues":
            found = set(self.titles.get(run.title, set()))
            # An issue closing or losing in-progress also starts the builder, which then
            # only restarts waiting jobs. Its gate is skipped, so it built nothing.
            if found and not run.active:
                gate = self._gate_job(run)
                if gate and gate.get("conclusion") == "skipped":
                    found = set()
        else:
            gate = self._gate_job(run)
            if gate and gate.get("status") == "completed" and gate.get("conclusion") != "skipped":
                try:
                    m = OVERLAP_ISSUE_RE.search(self.gh.text(f"/repos/{self.repo}/actions/jobs/{gate['id']}/logs"))
                except GitHubError:
                    m = None
                if m:
                    found = {int(m.group(1))}
                elif run.active:
                    found = {UNKNOWN}
            elif run.active:
                found = {UNKNOWN}
        self._issue[run.id] = found
        return found

    def unknown_active(self) -> bool:
        return any(r.active and UNKNOWN in self.issues_of(r) for r in self.runs if r.event == "workflow_dispatch")

    def relevant(self, run: Run) -> bool:
        """Whether any rule can be decided by this run: it is active, started inside
        RECENT_RUN, or ended inside IN_PROGRESS_QUIET. Older finished runs are never mapped,
        which keeps log downloads, and the shared hourly API budget, small."""
        return (run.active or run.started >= self.now - RECENT_RUN
                or run.updated >= self.now - IN_PROGRESS_QUIET)

    def for_issue(self, number: int, title: str) -> list[Run]:
        out = []
        for r in self.runs:
            if r.event == "issues" and r.title != title:
                continue
            if not self.relevant(r):
                continue
            if number in self.issues_of(r):
                out.append(r)
        return out


# ---------------------------------------------------------------- the sweep


@dataclass
class Config:
    repo: str
    builder_workflow: str
    ref: str = "main"
    authors: tuple = DEFAULT_AUTHORS
    dry_run: bool = False


@dataclass
class Sweeper:
    gh: object
    cfg: Config
    now: dt.datetime
    actions: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    dispatched: set[int] = field(default_factory=set)
    parked: set[int] = field(default_factory=set)

    def __post_init__(self):
        self._runs: BuilderRuns | None = None
        self._comments: dict[int, list] = {}
        self.titles: dict[str, set[int]] = {}
        self.prs: list[dict] = []

    # ------------------------------------------------ writes

    def _allowed(self, method: str, path: str, body) -> bool:
        repo = re.escape(self.cfg.repo)
        if method == "POST" and re.fullmatch(rf"/repos/{repo}/issues/\d+/comments", path):
            return True
        if method == "POST" and re.fullmatch(rf"/repos/{repo}/issues/\d+/labels", path):
            return set(body.get("labels", [])) <= {JOB, WAITING, NEEDS_ALLISON}
        if method == "DELETE":
            m = re.fullmatch(rf"/repos/{repo}/issues/\d+/labels/([^/]+)", path)
            return bool(m) and urllib.parse.unquote(m.group(1)) in {IN_PROGRESS, WAITING}
        if method == "PATCH" and re.fullmatch(rf"/repos/{repo}/issues/\d+", path):
            return body == {"state": "closed", "state_reason": "completed"}
        if method == "POST" and re.fullmatch(rf"/repos/{repo}/actions/workflows/[^/]+/dispatches", path):
            return set(body) == {"ref", "inputs"} and set(body["inputs"]) == {"issue"}
        return False

    def write(self, number: int, method: str, path: str, body=None):
        """Every write the sweeper makes. number is the issue or pull request it touches."""
        if number in self.parked:
            raise RefusedWrite(f"#{number} is parked; the sweeper never touches a parked job")
        if not self._allowed(method, path, body):
            raise RefusedWrite(f"{method} {path} is not a write the sweeper may make")
        if self.cfg.dry_run:
            return None
        if method == "POST":
            return self.gh.post(path, body)
        if method == "PATCH":
            return self.gh.patch(path, body)
        return self.gh.delete(path)

    def comment(self, number: int, body: str) -> None:
        self.write(number, "POST", f"/repos/{self.cfg.repo}/issues/{number}/comments", {"body": body})
        self._comments.setdefault(number, []).append(
            {"user": {"login": ACTIONS_LOGIN}, "body": body, "created_at": iso(self.now)})

    def add_labels(self, number: int, names: list[str]) -> None:
        self.write(number, "POST", f"/repos/{self.cfg.repo}/issues/{number}/labels", {"labels": names})

    def remove_label(self, number: int, name: str) -> bool:
        """False when the label was already gone, which is how two runs racing for the same
        waiting job learn that the other one took it."""
        try:
            self.write(number, "DELETE", f"/repos/{self.cfg.repo}/issues/{number}/labels/{urllib.parse.quote(name)}")
        except GitHubError as exc:
            if exc.status == 404:
                return False
            raise
        return True

    def dispatch(self, number: int) -> None:
        self.write(
            number, "POST",
            f"/repos/{self.cfg.repo}/actions/workflows/{urllib.parse.quote(self.cfg.builder_workflow)}/dispatches",
            {"ref": self.cfg.ref, "inputs": {"issue": str(number)}},
        )
        self.dispatched.add(number)

    def act(self, line: str) -> None:
        self.actions.append(line)

    def note(self, line: str) -> None:
        self.notes.append(line)
        print(f"stall-sweeper: {line}")

    # ------------------------------------------------ reads

    def runs(self) -> BuilderRuns:
        if self._runs is None:
            self._runs = BuilderRuns(self.gh, self.cfg.repo, self.cfg.builder_workflow, self.now, self.titles)
        return self._runs

    def comments(self, number: int) -> list:
        if number not in self._comments:
            self._comments[number] = self.gh.paginate(f"/repos/{self.cfg.repo}/issues/{number}/comments")
        return self._comments[number]

    def my_comments(self, number: int) -> list[str]:
        return [c.get("body") or "" for c in self.comments(number) if login_of(c) == ACTIONS_LOGIN]

    def why_not_dispatch(self, issue: dict) -> str | None:
        number = int(issue["number"])
        if number in self.dispatched:
            return "it was already dispatched in this sweep"
        runs = self.runs()
        if any(r.active for r in runs.for_issue(number, issue.get("title") or "")):
            return "a builder run for it is queued or in progress"
        if runs.unknown_active():
            return "a dispatched builder run that has not named its job yet is queued or in progress"
        return None

    def started_recently(self, issue: dict, window: dt.timedelta) -> bool:
        cutoff = self.now - window
        return any(r.started >= cutoff for r in self.runs().for_issue(int(issue["number"]), issue.get("title") or ""))

    def held(self, issue: dict, rule: str) -> bool:
        why = self.why_not_dispatch(issue)
        if why:
            self.note(f"#{issue['number']} {rule}, but not dispatched: {why}.")
        return bool(why)

    # ------------------------------------------------ the rules

    def sweep(self) -> list[str]:
        if is_excluded_repo(self.cfg.repo):
            print(f"stall-sweeper: {self.cfg.repo} is excluded; nothing to do.")
            return []
        issues = [
            i for i in self.gh.paginate(f"/repos/{self.cfg.repo}/issues", {"state": "open", "sort": "created", "direction": "asc"})
            if "pull_request" not in i and (i.get("title") or "").startswith(JOB_PREFIX)
        ]
        self.parked = {int(i["number"]) for i in issues if PARKED in labels_of(i)}
        for i in issues:
            self.titles.setdefault(i.get("title") or "", set()).add(int(i["number"]))
        self.prs = [p for p in self.gh.paginate(f"/repos/{self.cfg.repo}/pulls", {"state": "open"})
                    if is_builder_pr(p, self.cfg.repo)]
        for p in self.prs:
            if pr_issues(p) & self.parked:
                self.parked.add(int(p["number"]))
        for issue in sorted(issues, key=lambda i: int(i["number"])):
            number = int(issue["number"])
            if number in self.parked:
                continue
            if login_of(issue) not in self.cfg.authors:
                continue
            try:
                self.sweep_issue(issue)
            except GitHubError as exc:
                self.errors.append(f"#{number}: {exc}")
                print(f"::error::stall-sweeper: #{number} could not be swept: {exc}")
        return self.actions

    def sweep_issue(self, issue: dict) -> None:
        labels = labels_of(issue)
        if JOB not in labels:
            return self.rule_unlabeled(issue)
        if DONE in labels:
            return self.rule_done(issue)
        number = int(issue["number"])
        prs = [p for p in self.prs if number in pr_issues(p)]
        if prs:
            for pr in prs:
                self.rule_codex_review(issue, pr)
            for pr in prs:
                self.rule_refused(issue, pr)
            return None
        if NEEDS_ALLISON in labels:
            return None
        if WAITING in labels:
            return self.rule_waiting(issue)
        if IN_PROGRESS in labels:
            return self.rule_stuck_in_progress(issue)
        return self.rule_idle(issue)

    def rule_unlabeled(self, issue: dict) -> None:
        number = int(issue["number"])
        if self.held(issue, "has no job label"):
            return
        self.add_labels(number, [JOB])
        if not any(LABELED_MARK in b for b in self.my_comments(number)):
            self.comment(number, "\n".join([
                "The stall sweeper added the job label. This issue's title begins with Job: but it "
                "had no job label and no parked label, so no builder would ever pick it up. The "
                "builder has been started for it. Add the parked label to keep a job off the board.",
                "",
                LABELED_MARK,
            ]))
        self.dispatch(number)
        self.act(f"#{number} labeled job and dispatched: its title begins with Job: but it had no job label.")

    def merged_pr(self, number: int) -> dict | None:
        best = None
        for e in self.gh.paginate(f"/repos/{self.cfg.repo}/issues/{number}/timeline"):
            src = (e.get("source") or {}).get("issue") or {}
            if e.get("event") != "cross-referenced" or not (src.get("pull_request") or {}).get("merged_at"):
                continue
            if not (src.get("repository_url") or "").endswith(f"/repos/{self.cfg.repo}"):
                continue
            if number not in closes(src.get("body")):
                continue
            if best is None or src["pull_request"]["merged_at"] > best["pull_request"]["merged_at"]:
                best = src
        if best is None:
            return None
        return self.gh.get(f"/repos/{self.cfg.repo}/pulls/{best['number']}")

    def rule_done(self, issue: dict) -> None:
        number = int(issue["number"])
        pr = self.merged_pr(number)
        if not pr or not pr.get("merged"):
            return
        sha = pr.get("merge_commit_sha") or ""
        if not any((m := CLOSED_RE.search(b)) and int(m.group(1)) == int(pr["number"]) for b in self.my_comments(number)):
            self.comment(number, "\n".join([
                f"Closed by the stall sweeper. This job is done and pull request #{pr['number']} "
                f"was merged as {sha}.",
                "",
                f"<!-- {MARK} closed pr={pr['number']} -->",
            ]))
        self.write(number, "PATCH", f"/repos/{self.cfg.repo}/issues/{number}", {"state": "closed", "state_reason": "completed"})
        self.act(f"#{number} closed as completed: pull request #{pr['number']} merged as {sha[:7]}.")

    def rule_waiting(self, issue: dict) -> None:
        number = int(issue["number"])
        holders = waited_on(self.comments(number))
        for h in holders:
            try:
                item = self.gh.get(f"/repos/{self.cfg.repo}/issues/{h}")
            except GitHubError as exc:
                # A deleted or transferred holder holds nothing.
                if exc.status in (404, 410):
                    continue
                raise
            if not holder_finished(item):
                return
        # A build that failed goes back to waiting with no holder. Restarting it on every
        # sweep would rebuild a failing job every 10 minutes, so it gets the same pause as rule 4.
        if self.started_recently(issue, RECENT_RUN):
            return
        if self.held(issue, "waits on nothing open"):
            return
        # The overlap check's restart claims a job the same way, so only one of them sends it.
        if not self.cfg.dry_run and not self.remove_label(number, WAITING):
            self.note(f"#{number} was taken by another run before this sweep could dispatch it.")
            return
        try:
            self.dispatch(number)
        except Exception:
            if not self.cfg.dry_run:
                self.add_labels(number, [JOB, WAITING])
            raise
        on = ", ".join(f"#{h}" for h in holders) or "nothing"
        self.act(f"#{number} dispatched: it was waiting on {on}, and nothing it waits on is still open.")

    def no_pr_release_at(self, number: int) -> dt.datetime | None:
        """When the overlap check last said a build finished without a pull request, or None
        when its comment says something else now."""
        for c in reversed(self.comments(number)):
            body = c.get("body") or ""
            if login_of(c) == ACTIONS_LOGIN and OVERLAP_MARK in body:
                if NO_PR_RELEASE not in body:
                    return None
                return parse_time(c.get("updated_at") or c.get("created_at"))
        return None

    def last_no_pr_mark(self, number: int) -> tuple[str, dt.datetime] | None:
        last = None
        for c in self.comments(number):
            body = c.get("body") or ""
            if login_of(c) != ACTIONS_LOGIN:
                continue
            kind = REBUILT_MARK if REBUILT_MARK in body else NO_PR_RETURNED_MARK if NO_PR_RETURNED_MARK in body else None
            at = parse_time(c.get("created_at"))
            if kind and at and (last is None or at >= last[1]):
                last = (kind, at)
        return last

    def rule_idle(self, issue: dict) -> None:
        number = int(issue["number"])
        if self.started_recently(issue, RECENT_RUN):
            return
        released = self.no_pr_release_at(number)
        last = self.last_no_pr_mark(number) if released else None
        if released and last and last[0] == REBUILT_MARK and released > last[1]:
            # The sweeper already rebuilt this job once after a build with no pull request,
            # and that rebuild ended the same way. Another rebuild would repeat it every 30
            # minutes, so it goes to Allison (Decision Log 2026-11-02, No caps stop work).
            self.escalate(number, "\n".join([
                "Recommend: look at why the builder finishes this job without opening a pull "
                "request. The stall sweeper rebuilt it after a build with no pull request, and "
                "the rebuild ended the same way, so the sweeper stopped restarting it. Remove "
                "needs-allison to let the sweeper build it again.",
                "",
                NO_PR_RETURNED_MARK,
            ]), f"#{number} marked needs-allison: its build ended without a pull request again after a rebuild.")
            return
        if last and last[0] == NO_PR_RETURNED_MARK and not self.needs_allison_removed_since(number, last[1]):
            self.relabel(number, "its build ended without a pull request again after a rebuild")
            return
        if self.held(issue, "is idle"):
            return
        if released:
            self.comment(number, "\n".join([
                "The stall sweeper restarted the builder, because the last build finished without "
                "opening a pull request. If this build ends the same way, the sweeper marks the "
                "job needs-allison instead of restarting it again.",
                "",
                REBUILT_MARK,
            ]))
        self.dispatch(number)
        why = "its last build finished without a pull request" if released else "labeled job with no build, no pull request"
        self.act(f"#{number} dispatched: {why} and no builder run in 30 minutes.")

    def needs_allison_removed_since(self, number: int, at: dt.datetime | None) -> bool:
        """Whether someone removed needs-allison after the sweeper's escalation comment. With
        no removal, a missing label means the sweeper's own label write failed after the
        comment, so the escalation is finished instead of the job restarting."""
        for e in self.gh.paginate(f"/repos/{self.cfg.repo}/issues/{number}/events"):
            if e.get("event") != "unlabeled" or (e.get("label") or {}).get("name") != NEEDS_ALLISON:
                continue
            when = parse_time(e.get("created_at"))
            if at is None or (when and when >= at):
                return True
        return False

    def escalate(self, number: int, body: str, action: str) -> None:
        # The Recommend: comment goes first. If the label write then fails, the next sweep
        # finds the comment and adds the label; the other order could halt the job silently.
        self.comment(number, body)
        self.add_labels(number, [NEEDS_ALLISON])
        self.act(action)

    def relabel(self, number: int, why: str) -> None:
        self.add_labels(number, [NEEDS_ALLISON])
        self.act(f"#{number} marked needs-allison: {why} (its Recommend: comment was posted, the label was not).")

    def in_progress_since(self, number: int) -> dt.datetime | None:
        at = None
        for e in self.gh.paginate(f"/repos/{self.cfg.repo}/issues/{number}/events"):
            if e.get("event") == "labeled" and (e.get("label") or {}).get("name") == IN_PROGRESS:
                at = parse_time(e.get("created_at"))
        return at

    def rule_stuck_in_progress(self, issue: dict) -> None:
        number = int(issue["number"])
        runs = self.runs().for_issue(number, issue.get("title") or "")
        if any(r.active for r in runs):
            return
        quiet = [t for t in [self.in_progress_since(number), *(r.updated for r in runs)] if t]
        since = max(quiet) if quiet else parse_time(issue.get("created_at"))
        if since and self.now - since < IN_PROGRESS_QUIET:
            return
        if self.held(issue, "is stuck in progress"):
            return
        # Removed before the dispatch, so this removal can never strip the label the new build adds.
        self.remove_label(number, IN_PROGRESS)
        self.dispatch(number)
        idle = f"{minutes(self.now - since)} minutes" if since else "an unknown time"
        self.act(f"#{number} in-progress removed and dispatched: no builder run and no pull request for {idle}.")

    def rule_codex_review(self, issue: dict, pr: dict) -> None:
        if login_of(pr) != FACTORY_LOGIN or pr.get("draft"):
            return
        number, sha = int(pr["number"]), (pr.get("head") or {}).get("sha") or ""
        comments = self.comments(number)
        if any((m := CODEX_ASK_RE.search(b)) and m.group(1) == sha for b in self.my_comments(number)):
            return
        if codex_reviewed(comments, sha):
            return
        commit = self.gh.get(f"/repos/{self.cfg.repo}/commits/{sha}") or {}
        committed = parse_time((((commit.get("commit") or {}).get("committer")) or {}).get("date"))
        times = [t for t in (committed, parse_time(pr.get("created_at"))) if t]
        since = max(times) if times else None
        if since and self.now - since < CODEX_WAIT:
            return
        reviews = self.gh.paginate(f"/repos/{self.cfg.repo}/pulls/{number}/reviews")
        if any(login_of(r) == CODEX_LOGIN and r.get("commit_id") == sha for r in reviews):
            return
        self.comment(number, f"@codex review\n\n<!-- {MARK} codex-review head={sha} -->")
        waited = f"{minutes(self.now - since)} minutes" if since else "over 30 minutes"
        self.act(f"#{number} (job #{issue['number']}) asked Codex to review head {sha[:7]}, unreviewed for {waited}.")

    def codex_threads(self, pr_number: int) -> list[Finding]:
        """Every review thread Codex opened on the pull request, resolved or not."""
        owner, name = self.cfg.repo.split("/", 1)
        query = (
            "query($o:String!,$n:String!,$p:Int!,$a:String){repository(owner:$o,name:$n){"
            "pullRequest(number:$p){reviewThreads(first:100,after:$a){"
            "nodes{id isResolved path comments(first:1){nodes{author{login} body url}}}"
            " pageInfo{hasNextPage endCursor}}}}}"
        )
        found, after = [], None
        while True:
            data = self.gh.graphql(query, {"o": owner, "n": name, "p": pr_number, "a": after})
            threads = data["repository"]["pullRequest"]["reviewThreads"]
            for t in threads["nodes"]:
                first = ((t.get("comments") or {}).get("nodes") or [{}])[0]
                if ((first.get("author") or {}).get("login") or "") not in (CODEX_LOGIN, "chatgpt-codex-connector"):
                    continue
                found.append(Finding(t["id"], t.get("path") or "", finding_title(first.get("body") or ""),
                                     first.get("url") or "", bool(t.get("isResolved"))))
            if not threads["pageInfo"]["hasNextPage"]:
                return found
            after = threads["pageInfo"]["endCursor"]

    def rule_refused(self, issue: dict, pr: dict) -> None:
        if login_of(pr) != FACTORY_LOGIN or pr.get("draft"):
            return
        number, pr_number = int(issue["number"]), int(pr["number"])
        if NEEDS_ALLISON in labels_of(issue):
            return
        sha = (pr.get("head") or {}).get("sha") or ""
        reasons = gate_refusal(self.comments(pr_number), sha)
        fix = [r for r in (reasons or []) if is_check_reason(r) or is_codex_reason(r)]
        if not fix:
            return
        if self.started_recently(issue, RECENT_RUN):
            return
        threads = self.codex_threads(pr_number) if any(is_codex_reason(r) for r in fix) else []
        findings = blocking_threads(threads, fix)
        if self.held(issue, f"has pull request #{pr_number} refused by the auto-merge gate"):
            return

        asked: dict[str, set[str]] = {}
        for body in self.my_comments(number):
            m = FIX_RE.search(body)
            for pair in (m.group(3).split(",") if m and m.group(3) else []):
                fp, _, thread = pair.partition(":")
                asked.setdefault(fp, set()).add(thread)
        resolved = {t.thread: t.resolved for t in threads}
        # A finding came back only when every thread the builder was asked to fix for it is
        # resolved and Codex opened a new one. A second thread beside a still-open first one
        # is the same unfixed finding, so it is sent back again, not escalated.
        returned = [
            f for f in findings
            if f.fingerprint in asked and f.thread not in asked[f.fingerprint]
            and all(resolved.get(t) is True for t in asked[f.fingerprint])
        ]
        escalated = [parse_time(c.get("created_at")) for c in self.comments(number)
                     if login_of(c) == ACTIONS_LOGIN and (m := RETURNED_RE.search(c.get("body") or "")) and m.group(1) == sha]
        # Once escalated at this head, reaching here with needs-allison removed by someone
        # clears those findings for another round. With no removal, the label write failed.
        if escalated:
            known = [t for t in escalated if t]
            if not self.needs_allison_removed_since(number, max(known) if known else None):
                self.relabel(number, f"a Codex finding on pull request #{pr_number} came back after it was fixed")
                return
        elif returned:
            listed = "; ".join(f"`{f.path}`: {f.title}" for f in returned)
            self.escalate(number, "\n".join([
                f"Recommend: decide how pull request #{pr_number} should fix {listed}. This Codex "
                "finding came back after the builder fixed it, so the stall sweeper stopped "
                "restarting the builder for it (Decision Log 2026-11-02, No caps stop work).",
                "",
                *[f"- {f.url}" for f in returned if f.url],
                "",
                f"<!-- {MARK} returned head={sha} -->",
            ]), f"#{number} marked needs-allison: a Codex finding on pull request #{pr_number} came back after it was fixed.")
            return

        digest = hashlib.sha256("\n".join(sorted(fix) + sorted(f.thread for f in findings)).encode()).hexdigest()[:16]
        if not any((m := FIX_RE.search(b)) and m.group(1) == sha and m.group(2) == digest for b in self.my_comments(number)):
            lines = [
                f"The stall sweeper restarted the builder to fix pull request #{pr_number} at head "
                f"`{sha[:7]}`. The auto-merge gate refused it for:",
                "",
                *[f"- {r}" for r in fix],
            ]
            if findings:
                lines += ["", "Codex findings that block the merge:", ""]
                lines += [f"- `{f.path}`: {f.title}{f' ({f.url})' if f.url else ''}" for f in findings]
            lines += [
                "",
                "Push the fixes to the same branch and resolve each Codex thread you fixed.",
                "",
                f"<!-- {MARK} fix head={sha} digest={digest} findings={','.join(f'{f.fingerprint}:{f.thread}' for f in findings)} -->",
            ]
            self.comment(number, "\n".join(lines))
        self.dispatch(number)
        self.act(f"#{number} dispatched to fix pull request #{pr_number}: {'; '.join(fix)}")


def summarize(s: Sweeper) -> str:
    lines = [("Would: " if s.cfg.dry_run else "") + a for a in s.actions]
    count = len(s.actions)
    tail = "action" if count == 1 else "actions"
    if s.cfg.dry_run:
        lines.append(f"Dry run: {count} {tail} would be taken. Nothing was changed.")
    elif count:
        lines.append(f"{count} {tail} taken.")
    else:
        lines.append("No stalled jobs. 0 actions taken.")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    if argv not in ([], ["sweep"]):
        print("usage: sweeper.py [sweep]", file=sys.stderr)
        return 2
    repo = os.environ["GITHUB_REPOSITORY"]
    if is_excluded_repo(repo):
        print(f"stall-sweeper: {repo} is excluded; nothing to do.")
        return 0
    gh = GitHub(os.environ["SWEEPER_TOKEN"], os.environ.get("GITHUB_API_URL", "https://api.github.com"))
    ref = os.environ.get("SWEEPER_REF", "").strip() or (gh.get(f"/repos/{repo}") or {}).get("default_branch") or "main"
    authors = tuple(a.strip() for a in os.environ.get("SWEEPER_AUTHORS", "").split(",") if a.strip()) or DEFAULT_AUTHORS
    cfg = Config(
        repo=repo,
        builder_workflow=os.environ["SWEEPER_BUILDER_WORKFLOW"].strip(),
        ref=ref,
        authors=authors,
        dry_run=os.environ.get("SWEEPER_DRY_RUN", "").strip().lower() in ("1", "true", "yes"),
    )
    s = Sweeper(gh, cfg, dt.datetime.now(dt.timezone.utc))
    try:
        s.sweep()
    except (GitHubError, RefusedWrite) as exc:
        s.errors.append(str(exc))
        print(f"::error::stall-sweeper: {exc}")
    summary = summarize(s)
    print(summary)
    out = os.environ.get("GITHUB_STEP_SUMMARY")
    if out:
        with open(out, "a", encoding="utf-8") as fh:
            fh.write("## Factory stall sweeper\n\n" + "\n".join(f"- {line}" for line in summary.splitlines()) + "\n")
    return 1 if s.errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
