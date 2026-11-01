#!/usr/bin/env python3
"""Auto-merge gate for finished Chat to Code jobs. README.md beside this file explains it.

Two subcommands, run by .github/workflows/auto-merge-gate.yml:

  plan   Evaluate the pull requests the triggering event points at (or every open one).
         Posts or updates the one refusal comment per head commit, and writes the numbers
         that may merge to GITHUB_OUTPUT as merge=<n> <n>.
  merge  Re-evaluate each number in GATE_MERGE_PRS and squash-merge the ones that still
         pass, pinned to the evaluated head commit, then label the job issue done and
         comment the merge commit on it.

GATE_TOKEN (the workflow's own token) does every read, comment and label. MERGE_TOKEN
(the EP Skills Graph Bot app token) is used for the merge call and nothing else.
Standard library only.
"""

from __future__ import annotations

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
GATE_COMMENT_AUTHOR = "github-actions[bot]"
JOB_LABEL = "job"
DONE_LABEL = "done"
OK_CONCLUSIONS = {"success", "neutral", "skipped"}

CLOSES_RE = re.compile(r"Closes #(\d+)\b")
CODEX_STATE_RE = re.compile(r"<!--\s*codex-review-state:v1\s+(\{.*?\})\s*-->", re.DOTALL)
MARKER_RE = re.compile(r"<!-- auto-merge-gate:v1 head=([0-9a-f]{40}) -->")

PR_EVENTS = {"pull_request", "pull_request_target", "pull_request_review"}


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

    def paginate(self, path: str, key: str | None = None, params: dict | None = None) -> list:
        query = dict(params or {})
        query.setdefault("per_page", 100)
        url = f"{path}?{urllib.parse.urlencode(query)}"
        items: list = []
        while url:
            data, link = self._request("GET", url)
            items.extend(data[key] if key else data)
            url = next((p.split(";")[0].strip()[1:-1] for p in link.split(",") if 'rel="next"' in p), None)
        return items

    def post(self, path: str, body: dict):
        return self._request("POST", path, body)[0]

    def put(self, path: str, body: dict):
        return self._request("PUT", path, body)[0]

    def patch(self, path: str, body: dict):
        return self._request("PATCH", path, body)[0]


@dataclass
class Config:
    repo: str
    gate_check_name: str = "auto-merge-gate"
    base_branch: str = "main"
    server_url: str = "https://github.com"


@dataclass
class Decision:
    pr: int
    action: str  # "skip" (left alone), "refuse" (eligible, a condition is not met), "merge"
    reasons: list[str] = field(default_factory=list)
    head_sha: str = ""
    issue: int | None = None
    comments: list = field(default_factory=list)


def job_issue_number(body: str | None) -> int | None:
    m = CLOSES_RE.match((body or "").lstrip())
    return int(m.group(1)) if m else None


def latest_codex_state(comments: list) -> dict | None:
    """The codex-review-state JSON from Codex's most recently updated summary comment."""
    best, best_at = None, ""
    for c in comments:
        if (c.get("user") or {}).get("login") != CODEX_LOGIN:
            continue
        m = CODEX_STATE_RE.search(c.get("body") or "")
        if not m:
            continue
        try:
            state = json.loads(m.group(1))
        except ValueError:
            continue
        at = c.get("updated_at") or c.get("created_at") or ""
        if best is None or at >= best_at:
            best, best_at = state, at
    return best


def check_problems(gh, cfg: Config, sha: str) -> list[str]:
    problems: list[str] = []
    reported = 0
    runs = gh.paginate(f"/repos/{cfg.repo}/commits/{sha}/check-runs", key="check_runs")
    for run in runs:
        name = run.get("name", "")
        if name == cfg.gate_check_name:
            continue
        reported += 1
        status, conclusion = run.get("status"), run.get("conclusion")
        if status != "completed":
            problems.append(f"Check `{name}` is {status}, not completed.")
        elif conclusion not in OK_CONCLUSIONS:
            problems.append(f"Check `{name}` finished as {conclusion}.")
    combined = gh.get(f"/repos/{cfg.repo}/commits/{sha}/status", {"per_page": 100}) or {}
    for st in combined.get("statuses", []):
        if st.get("context") == cfg.gate_check_name:
            continue
        reported += 1
        if st.get("state") != "success":
            problems.append(f"Commit status `{st.get('context')}` is {st.get('state')}.")
    if reported == 0:
        problems.append("No checks have reported on the head commit yet.")
    return problems


def codex_problems(state: dict | None, sha: str) -> list[str]:
    short = sha[:7]
    if state is None:
        return [f"Codex has not reviewed head {short} yet (no Codex review summary on this pull request)."]
    code = state.get("code_review") or {}
    reviewed = code.get("commit_sha") or ""
    if reviewed != sha:
        covered = reviewed[:7] if reviewed else "no commit"
        return [f"Codex has not reviewed head {short} yet (its last code review covered {covered})."]
    problems: list[str] = []
    if code.get("status") != "completed":
        problems.append(f"Codex code review on {short} is {code.get('status')}, not completed.")
    elif code.get("has_unresolved_findings") is True:
        problems.append(f"Codex code review on {short} left unresolved findings.")
    elif code.get("has_unresolved_findings") is not False:
        problems.append(f"Codex code review on {short} did not report has_unresolved_findings: false.")
    security = state.get("security_review") or {}
    if security.get("commit_sha") == sha and security.get("has_unresolved_findings") is True:
        problems.append(f"Codex security review on {short} left unresolved findings.")
    return problems


def mergeable_problems(pr: dict) -> list[str]:
    mergeable = pr.get("mergeable")
    if mergeable is None:
        return ["GitHub is still computing whether the pull request can merge."]
    if mergeable is not True:
        return [f"GitHub reports the pull request is not mergeable (mergeable_state: {pr.get('mergeable_state')})."]
    return []


def evaluate(gh, cfg: Config, number: int) -> Decision:
    pr = gh.get(f"/repos/{cfg.repo}/pulls/{number}")

    def skip(why: str) -> Decision:
        return Decision(number, "skip", [why])

    if pr.get("state") != "open":
        return skip("not open")
    if pr.get("draft"):
        return skip("draft")
    author = (pr.get("user") or {}).get("login")
    if author != FACTORY_LOGIN:
        return skip(f"author is {author}, not {FACTORY_LOGIN}")
    if (pr.get("base") or {}).get("ref") != cfg.base_branch:
        return skip(f"base is not {cfg.base_branch}")
    issue_number = job_issue_number(pr.get("body"))
    if issue_number is None:
        return skip("body does not start with Closes #N")
    try:
        issue = gh.get(f"/repos/{cfg.repo}/issues/{issue_number}")
    except GitHubError as exc:
        return skip(f"issue #{issue_number} could not be read ({exc})")
    if "pull_request" in issue:
        return skip(f"#{issue_number} is a pull request, not a job issue")
    if JOB_LABEL not in {label.get("name") for label in issue.get("labels", [])}:
        return skip(f"issue #{issue_number} does not carry the {JOB_LABEL} label")

    sha = (pr.get("head") or {}).get("sha", "")
    comments = gh.paginate(f"/repos/{cfg.repo}/issues/{number}/comments")
    reasons = check_problems(gh, cfg, sha)
    reasons += codex_problems(latest_codex_state(comments), sha)
    reasons += mergeable_problems(pr)
    action = "refuse" if reasons else "merge"
    return Decision(number, action, reasons, sha, issue_number, comments)


def refusal_body(d: Decision) -> str:
    lines = [
        f"<!-- auto-merge-gate:v1 head={d.head_sha} -->",
        f"The auto-merge gate has not merged this pull request at head `{d.head_sha[:7]}`. Not met yet:",
        "",
    ]
    lines += [f"- {r}" for r in d.reasons]
    lines += [
        "",
        "The gate checks again on the next pull request, review, comment or check event, and every 15 minutes.",
    ]
    return "\n".join(lines)


def post_refusal(gh, cfg: Config, d: Decision) -> None:
    """One comment per head commit: post it once, then only edit it if the reasons change."""
    body = refusal_body(d)
    for c in d.comments:
        if (c.get("user") or {}).get("login") != GATE_COMMENT_AUTHOR:
            continue
        m = MARKER_RE.search(c.get("body") or "")
        if m and m.group(1) == d.head_sha:
            if c.get("body") != body:
                gh.patch(f"/repos/{cfg.repo}/issues/comments/{c['id']}", {"body": body})
            return
    gh.post(f"/repos/{cfg.repo}/issues/{d.pr}/comments", {"body": body})


def merge(gh, merger, cfg: Config, d: Decision) -> str | None:
    try:
        result = merger.put(
            f"/repos/{cfg.repo}/pulls/{d.pr}/merge",
            {"merge_method": "squash", "sha": d.head_sha},
        )
    except GitHubError as exc:
        d.reasons = [f"GitHub refused the squash merge: {exc.message}"]
        post_refusal(gh, cfg, d)
        return None
    sha = (result or {}).get("sha", "")
    gh.post(f"/repos/{cfg.repo}/issues/{d.issue}/labels", {"labels": [DONE_LABEL]})
    gh.post(
        f"/repos/{cfg.repo}/issues/{d.issue}/comments",
        {
            "body": (
                f"Merged by the auto-merge gate. Pull request #{d.pr} was squash-merged into "
                f"{cfg.base_branch} as {sha} ({cfg.server_url}/{cfg.repo}/commit/{sha})."
            )
        },
    )
    return sha


def target_prs(gh, cfg: Config, event_name: str, event: dict, dispatch_pr: str = "") -> list[int]:
    if event_name in PR_EVENTS:
        return [int(event["pull_request"]["number"])]
    if event_name == "issue_comment":
        issue = event.get("issue") or {}
        return [int(issue["number"])] if "pull_request" in issue else []
    if event_name == "workflow_dispatch" and dispatch_pr.strip():
        return [int(dispatch_pr.strip())]
    # schedule, check_suite and a dispatch without a number sweep every open pull request.
    open_prs = gh.paginate(f"/repos/{cfg.repo}/pulls", params={"state": "open"})
    return [
        int(p["number"])
        for p in open_prs
        if not p.get("draft") and (p.get("user") or {}).get("login") == FACTORY_LOGIN
    ]


def is_excluded_repo(repo: str) -> bool:
    # Decision Log 2026-11-01: Ember's repository never merges itself.
    return repo.split("/")[-1].lower() == "ember"


def run_plan(gh, cfg: Config, event_name: str, event: dict, dispatch_pr: str = "", errors: list | None = None) -> list[int]:
    if is_excluded_repo(cfg.repo):
        print(f"auto-merge-gate: {cfg.repo} is excluded; nothing to do.")
        return []
    errors = [] if errors is None else errors
    ready: list[int] = []
    for number in target_prs(gh, cfg, event_name, event, dispatch_pr):
        try:
            d = evaluate(gh, cfg, number)
        except GitHubError as exc:
            errors.append(f"#{number}: {exc}")
            print(f"::error::auto-merge-gate: #{number} could not be evaluated: {exc}")
            continue
        print(f"auto-merge-gate: #{number} {d.action}: {'; '.join(d.reasons) or 'all conditions met'}")
        if d.action == "refuse":
            post_refusal(gh, cfg, d)
        elif d.action == "merge":
            ready.append(number)
    return ready


def run_merge(gh, merger, cfg: Config, numbers: list[int], errors: list | None = None) -> list[str]:
    if is_excluded_repo(cfg.repo):
        print(f"auto-merge-gate: {cfg.repo} is excluded; nothing to do.")
        return []
    errors = [] if errors is None else errors
    merged: list[str] = []
    for number in numbers:
        try:
            d = evaluate(gh, cfg, number)
        except GitHubError as exc:
            errors.append(f"#{number}: {exc}")
            print(f"::error::auto-merge-gate: #{number} could not be evaluated: {exc}")
            continue
        if d.action == "refuse":
            print(f"auto-merge-gate: #{number} no longer passes: {'; '.join(d.reasons)}")
            post_refusal(gh, cfg, d)
            continue
        if d.action == "skip":
            print(f"auto-merge-gate: #{number} left alone: {'; '.join(d.reasons)}")
            continue
        sha = merge(gh, merger, cfg, d)
        if sha:
            print(f"auto-merge-gate: #{number} squash-merged as {sha}")
            merged.append(sha)
        else:
            print(f"auto-merge-gate: #{number} merge refused: {'; '.join(d.reasons)}")
    return merged


def config_from_env() -> Config:
    return Config(
        repo=os.environ["GITHUB_REPOSITORY"],
        gate_check_name=os.environ.get("GATE_CHECK_NAME", "auto-merge-gate"),
        base_branch=os.environ.get("GATE_BASE_BRANCH", "main"),
        server_url=os.environ.get("GITHUB_SERVER_URL", "https://github.com"),
    )


def main(argv: list[str]) -> int:
    if len(argv) != 1 or argv[0] not in ("plan", "merge"):
        print("usage: gate.py plan|merge", file=sys.stderr)
        return 2
    cfg = config_from_env()
    api_url = os.environ.get("GITHUB_API_URL", "https://api.github.com")
    gh = GitHub(os.environ["GATE_TOKEN"], api_url)

    if argv[0] == "plan":
        with open(os.environ["GITHUB_EVENT_PATH"], encoding="utf-8") as fh:
            event = json.load(fh)
        errors: list[str] = []
        ready = run_plan(
            gh, cfg, os.environ["GITHUB_EVENT_NAME"], event, os.environ.get("GATE_DISPATCH_PR", ""), errors
        )
        out = os.environ.get("GITHUB_OUTPUT")
        if out:
            with open(out, "a", encoding="utf-8") as fh:
                fh.write(f"merge={' '.join(str(n) for n in ready)}\n")
        return 1 if errors else 0

    merge_token = os.environ.get("MERGE_TOKEN", "")
    if not merge_token:
        print("auto-merge-gate: MERGE_TOKEN is empty; refusing to merge with any other token.", file=sys.stderr)
        return 1
    numbers = [int(n) for n in os.environ.get("GATE_MERGE_PRS", "").split()]
    errors = []
    run_merge(gh, GitHub(merge_token, api_url), cfg, numbers, errors)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
