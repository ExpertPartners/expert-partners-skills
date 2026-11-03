#!/usr/bin/env python3
"""Overlap check for Chat to Code builds (Decision Log 2026-11-02, Factory runs everything at
once, and Claimed jobs return after one missed check, five open pull requests per repo).

A build starts right away unless one of these holds it:
  - a file in the issue's Files in scope is also in an open builder pull request (its
    changed files) or in the Files in scope of another in-progress Job issue. Shared files
    (plugin.json, marketplace.json, CHANGELOG.md, AGENTS.md, lockfiles) count the same way
    and are named as shared in the comment. The issue gets "Waiting on #N, same file".
  - the repo already has five open builder pull requests. The issue gets
    "Waiting, this repo has 5 open pull requests".

Two subcommands, run by .github/workflows/factory-builder-reusable.yml:

  check  Judge OVERLAP_ISSUE. A clear issue is labeled in-progress (and job) and loses
         waiting. A held issue is labeled waiting and gets one comment saying what it waits
         on, edited in place when that changes. Writes start=true|false to GITHUB_OUTPUT.
  next   After a pull request closes, find the oldest open Job issue labeled waiting that
         would start now and dispatch the builder workflow for it. Writes dispatched=<n>.

OVERLAP_TOKEN (the workflow's own token) does every read and write. Standard library only.
"""

from __future__ import annotations

import fnmatch
import json
import os
import re
import sys
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
PR_CAP = 5

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
CLOSES_RE = re.compile(r"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s+#(\d+)\b", re.IGNORECASE)
SCOPE_HEADING_RE = re.compile(r"^\s*(?:#+\s*)?\**files in scope\**\s*:?\s*$", re.IGNORECASE)
HEADING_RE = re.compile(r"^\s*#+\s+\S")
# Bare section names from .github/ISSUE_TEMPLATE/job.md, for bodies written without ## headings.
SECTION_NAMES = {
    "mission", "goal", "objective", "acceptance checks", "decisions already made",
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


def parse_scope(body: str | None) -> list[str]:
    """The paths listed under Files in scope, in order, without the (new) marks."""
    paths: list[str] = []
    in_scope = False
    for line in (body or "").splitlines():
        if SCOPE_HEADING_RE.match(line):
            in_scope = True
            continue
        if not in_scope:
            continue
        stripped = line.strip()
        if HEADING_RE.match(line) or stripped.rstrip(":").lower() in SECTION_NAMES or stripped == "---":
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
    bare name, a directory ends in /, a glob has a wildcard."""
    if not path or " " in path:
        return False
    last = path.rstrip("/").rsplit("/", 1)[-1]
    return (
        path.endswith("/")
        or any(ch in path for ch in "*?[")
        or "." in last.lstrip(".") or (last.startswith(".") and len(last) > 1)
        or last in BARE_FILENAMES
    )


def normalize(path: str) -> str:
    path = path.strip().strip("`\"'").rstrip(",;:")
    if path.endswith(".") and not path.endswith("/."):
        path = path[:-1]
    path = re.sub(r"\s*\(new\)\s*$", "", path, flags=re.IGNORECASE)
    while path.startswith("./"):
        path = path[2:]
    return path.lstrip("/")


def is_shared(path: str) -> bool:
    return path.rstrip("/").rsplit("/", 1)[-1].lower() in SHARED_BASENAMES


def paths_overlap(a: str, b: str) -> bool:
    """Same file, one path inside the other's directory (a path ending in /), a glob match,
    or a shared file named without its directory (plugin.json) against any file of that name."""
    if a == b:
        return True
    if is_shared(a) and is_shared(b) and ("/" not in a or "/" not in b):
        return a.rsplit("/", 1)[-1].lower() == b.rsplit("/", 1)[-1].lower()
    for x, y in ((a, b), (b, a)):
        if x.endswith("/") and y.startswith(x):
            return True
        if any(ch in x for ch in "*?[") and fnmatch.fnmatchcase(y, x):
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
    capped: bool = False
    scope: list[str] = field(default_factory=list)

    def lines(self) -> list[str]:
        out = [f"Waiting on #{o.number}, same file" for o in self.overlaps]
        if self.capped:
            out.append(f"Waiting, this repo has {PR_CAP} open pull requests")
        return out


def evaluate(issue: int, scope: list[str], prs: list[Holder], issues: list[Holder], cap: int = PR_CAP) -> Verdict:
    """Judge one job. prs are open builder pull requests, issues are other in-progress Job issues.

    A pull request that closes this issue is this job's own earlier work, so it neither
    collides nor counts toward the cap. An issue whose overlapping pull request is already
    named is not named again.
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
    capped = len(prs) >= cap
    return Verdict(not found and not capped, found, len(prs), capped, scope)


def comment_body(v: Verdict) -> str:
    if v.start:
        return "\n".join([
            MARKER,
            "Started. No other build touches these files and the repo is under "
            f"{PR_CAP} open pull requests.",
        ])
    lines = [MARKER, *v.lines(), ""]
    for o in v.overlaps:
        what = "pull request" if o.kind == "pr" else "in-progress job"
        named = ", ".join(f"`{p}`{' (shared file)' if is_shared(p) else ''}" for p in o.paths)
        lines.append(f"- #{o.number} ({what}): {named}")
    if v.capped:
        lines.append(f"- {v.open_prs} builder pull requests are open, the cap is {PR_CAP}.")
    lines += [
        "",
        "This build starts on its own when a pull request in this repo closes and nothing "
        "above still holds it.",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------- GitHub side


@dataclass
class Config:
    repo: str
    settle_seconds: float = 10.0
    cap: int = PR_CAP


def labels_of(item: dict) -> set[str]:
    return {label.get("name") for label in item.get("labels", [])}


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


def in_progress_issues(gh, cfg: Config) -> list[Holder]:
    found = gh.paginate(
        f"/repos/{cfg.repo}/issues",
        {"state": "open", "labels": f"{JOB_LABEL},{IN_PROGRESS_LABEL}"},
    )
    return [
        Holder(int(i["number"]), "issue", parse_scope(i.get("body")))
        for i in found
        if "pull_request" not in i
    ]


def judge(gh, cfg: Config, issue: dict, only_older_issues: bool = False) -> Verdict:
    number = int(issue["number"])
    issues = in_progress_issues(gh, cfg)
    if only_older_issues:
        issues = [i for i in issues if i.number < number]
    return evaluate(number, parse_scope(issue.get("body")), open_builder_prs(gh, cfg), issues, cfg.cap)


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
    first = judge(gh, cfg, issue)
    report(number, first)
    if not first.start:
        hold(gh, cfg, number, first, labels)
        return False
    add_labels(gh, cfg, number, [JOB_LABEL, IN_PROGRESS_LABEL])
    # Two jobs judged at the same moment both see a clear path, label themselves
    # in-progress and would collide. After a pause each looks again, and only the newer
    # issue yields to an older one, so exactly one of them builds.
    sleep(cfg.settle_seconds)
    second = judge(gh, cfg, issue, only_older_issues=True)
    if not second.start:
        report(number, second, again=True)
        hold(gh, cfg, number, second, labels | {IN_PROGRESS_LABEL})
        return False
    if WAITING_LABEL in labels:
        remove_label(gh, cfg, number, WAITING_LABEL)
    upsert_comment(gh, cfg, number, comment_body(second), create=False)
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


def run_next(gh, cfg: Config, dispatch) -> int | None:
    """Dispatch the oldest waiting Job issue that would start now. Writes nothing else."""
    waiting = gh.paginate(
        f"/repos/{cfg.repo}/issues",
        {"state": "open", "labels": f"{JOB_LABEL},{WAITING_LABEL}", "sort": "created", "direction": "asc"},
    )
    for issue in sorted((i for i in waiting if "pull_request" not in i), key=lambda i: int(i["number"])):
        v = judge(gh, cfg, issue)
        number = int(issue["number"])
        if v.start:
            dispatch(number)
            print(f"overlap-check: dispatched the builder for waiting job #{number}.")
            return number
        print(f"overlap-check: waiting job #{number} still waits: {'; '.join(v.lines())}")
    print("overlap-check: no waiting job can start yet.")
    return None


def workflow_file(workflow_ref: str) -> str:
    """owner/repo/.github/workflows/name.yml@refs/heads/main -> name.yml"""
    path = workflow_ref.split("@", 1)[0]
    return path.rsplit("/", 1)[-1]


def write_output(key: str, value: str) -> None:
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as fh:
            fh.write(f"{key}={value}\n")


def main(argv: list[str]) -> int:
    if len(argv) != 1 or argv[0] not in ("check", "next"):
        print("usage: overlap_check.py check|next", file=sys.stderr)
        return 2
    cfg = Config(
        repo=os.environ["GITHUB_REPOSITORY"],
        settle_seconds=float(os.environ.get("OVERLAP_SETTLE_SECONDS", "10")),
    )
    gh = GitHub(os.environ["OVERLAP_TOKEN"], os.environ.get("GITHUB_API_URL", "https://api.github.com"))

    if argv[0] == "check":
        number = int(os.environ["OVERLAP_ISSUE"])
        try:
            start = run_check(gh, cfg, number)
        except GitHubError as exc:
            print(f"::error::overlap-check: #{number} could not be checked: {exc}")
            write_output("start", "false")
            # Leave the job where the next closed pull request will pick it up again.
            try:
                add_labels(gh, cfg, number, [JOB_LABEL, WAITING_LABEL])
            except GitHubError:
                pass
            return 1
        write_output("start", "true" if start else "false")
        return 0

    workflow = workflow_file(os.environ["BUILDER_WORKFLOW_REF"])
    ref = os.environ.get("BUILDER_REF") or "main"

    def dispatch(number: int) -> None:
        gh.post(
            f"/repos/{cfg.repo}/actions/workflows/{urllib.parse.quote(workflow)}/dispatches",
            {"ref": ref, "inputs": {"issue": str(number)}},
        )

    try:
        number = run_next(gh, cfg, dispatch)
    except GitHubError as exc:
        print(f"::error::overlap-check: waiting jobs could not be checked: {exc}")
        return 1
    write_output("dispatched", str(number or ""))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
