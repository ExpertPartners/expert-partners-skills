#!/usr/bin/env python3
"""Auto-merge gate for finished Chat to Code jobs (Decision Log 2026-11-01, Finished code
merges itself, except in Ember's repo). Copied from expert-partners-skills, with one addition.

A pull request is eligible when either
  - it is a Factory job pull request (author factory-droid[bot], body starting with
    Closes #N where #N is an issue labeled job), or
  - GATE_MERGE_LABEL is set and the pull request carries that label. Repos whose
    builders push as a person (Factory missions, Claude Code) mark finished work this way.
Either way it merges only when every check on the head commit passed, the pull request
leaves plugin versions and the top of every CHANGELOG.md to the release step
(tools/release, fed by notes in .changeset/) and every note it adds is one that step can
read, Codex's code review covers that exact head with no unresolved findings, and GitHub
says it can merge.

Two subcommands, run by .github/workflows/auto-merge-gate.yml:

  plan   Evaluate the pull requests the triggering event points at (or every open one).
         Posts or updates the one refusal comment per head commit, and writes the numbers
         that may merge to GITHUB_OUTPUT as merge=<n> <n>.
  merge  Re-evaluate each number in GATE_MERGE_PRS and squash-merge the ones that still
         pass, pinned to the evaluated head commit, then label the job issue done and
         comment the merge commit on it.

GATE_TOKEN (the workflow's own token) does every read, comment and label. MERGE_TOKEN
(the merge token the workflow passes in) is used for the merge call and nothing else.
Standard library only.
"""

from __future__ import annotations

import base64
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
CODEX_RECEIPT_MARKER = "codex-review-receipt:v1"
CODEX_CLEAN_RE = re.compile(r"Codex Review:\s*Didn['\u2019]t find any major issues", re.IGNORECASE)
# At least 10 hex, so a head pushed later cannot cheaply be made to share an
# older receipt's prefix. Codex names 10.
CODEX_REVIEWED_COMMIT_RE = re.compile(r"\*\*Reviewed commit:\*\*\s*`([0-9a-fA-F]{10,40})`")

PR_EVENTS = {"pull_request", "pull_request_target", "pull_request_review"}

MARKETPLACE_PATH = ".claude-plugin/marketplace.json"
PLUGIN_MANIFEST_RE = re.compile(r"^plugins/([^/]+)/\.claude-plugin/plugin\.json$")
CHANGELOG_RE = re.compile(r"(^|/)CHANGELOG\.md$")
RELEASE_HINT = "The release step owns versions and CHANGELOG entries; add a note in `.changeset/` instead."
CHANGESET_NOTE_RE = re.compile(r"^\.changeset/[^/]+\.md$")
NOTE_BUMPS = ("patch", "minor", "major")
NOTE_KEY_RE = re.compile(r"""^\s*(?:"([^"]+)"|'([^']+)'|([A-Za-z0-9._-]+))\s*:\s*(\S+?)\s*$""")
NOTE_HINT = "The release step would refuse it and hold up every plugin's release; `.changeset/README.md` gives the format."


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

    def unresolved_threads(self, repo: str, number: int) -> int:
        """How many review threads on the pull request are still unresolved."""
        owner, name = repo.split("/", 1)
        query = (
            "query($o:String!,$n:String!,$p:Int!,$a:String){repository(owner:$o,name:$n){"
            "pullRequest(number:$p){reviewThreads(first:100,after:$a){"
            "nodes{isResolved} pageInfo{hasNextPage endCursor}}}}}"
        )
        count, after = 0, None
        while True:
            data, _ = self._request(
                "POST", self.api_url + "/graphql",
                {"query": query, "variables": {"o": owner, "n": name, "p": number, "a": after}},
            )
            if not data or data.get("errors"):
                raise GitHubError(502, f"review threads could not be read: {(data or {}).get('errors')}")
            threads = data["data"]["repository"]["pullRequest"]["reviewThreads"]
            count += sum(1 for t in threads["nodes"] if not t.get("isResolved"))
            if not threads["pageInfo"]["hasNextPage"]:
                return count
            after = threads["pageInfo"]["endCursor"]

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
    merge_label: str = ""


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


def has_clean_codex_receipt(comments: list, sha: str) -> bool:
    """Whether Codex posted a clean code review receipt for this head.

    When Codex's code review finds nothing it posts a codex-review-receipt:v1
    comment instead of updating its summary. The receipt names the reviewed
    commit by an abbreviated sha of at least 10 hex, or the full sha.
    Security review receipts carry the same marker but are not a code review,
    so they never count here."""
    sha = sha.lower()
    for c in comments:
        if (c.get("user") or {}).get("login") != CODEX_LOGIN:
            continue
        body = c.get("body") or ""
        if CODEX_RECEIPT_MARKER not in body or "Codex Security Review" in body:
            continue
        if not CODEX_CLEAN_RE.search(body):
            continue
        m = CODEX_REVIEWED_COMMIT_RE.search(body)
        if m and sha and sha.startswith(m.group(1).lower()):
            return True
    return False


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


def count_open_threads(unresolved_threads) -> tuple[int | None, str | None]:
    """(open thread count or None, read error message or None)."""
    try:
        return (unresolved_threads() if unresolved_threads else None), None
    except GitHubError as exc:
        return None, exc.message


def security_problems(state: dict | None, sha: str) -> list[str]:
    security = (state or {}).get("security_review") or {}
    if security.get("commit_sha") == sha and security.get("has_unresolved_findings") is True:
        return [f"Codex security review on {sha[:7]} left unresolved findings."]
    return []


def codex_problems(state: dict | None, sha: str, unresolved_threads=None, clean_receipt: bool = False) -> list[str]:
    """unresolved_threads is a callable returning the number of unresolved
    review threads on the pull request. It is only called in the cases that
    need it, see below. clean_receipt says Codex posted a clean code review
    receipt for this head (has_clean_codex_receipt)."""
    short = sha[:7]
    if clean_receipt and ((state or {}).get("code_review") or {}).get("commit_sha") != sha:
        # The receipt stands in only for a summary that is missing or still on
        # an older commit. A summary that covers this head keeps deciding.
        # The receipt says nothing about findings left open on earlier commits,
        # and the summary it replaces may be stale, so every review thread must
        # be resolved before it counts.
        open_threads, error = count_open_threads(unresolved_threads)
        if open_threads != 0:
            if error:
                why = f"the review threads could not be read ({error})"
            elif open_threads is None:
                why = "the review threads could not be checked"
            else:
                why = f"{open_threads} review thread(s) are still unresolved"
            return [f"Codex posted a clean code review receipt for {short}, but {why}."] + security_problems(state, sha)
        state = dict(state or {}, code_review={
            "commit_sha": sha, "status": "completed", "has_unresolved_findings": False,
        })
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
    elif code.get("has_unresolved_findings") is None and code.get("has_any_findings") is True:
        # Once a pull request has ever had findings, Codex reports null instead
        # of false even after every finding is fixed and its thread resolved.
        # Then the threads themselves decide: every one must be resolved.
        open_threads, error = count_open_threads(unresolved_threads)
        if error:
            problems.append(f"Codex code review on {short} reported no open findings, but the review threads could not be read ({error}).")
        if open_threads is None:
            if not problems:
                problems.append(f"Codex code review on {short} did not report has_unresolved_findings: false.")
        elif open_threads > 0:
            problems.append(f"Codex code review on {short} has {open_threads} unresolved review thread(s).")
    elif code.get("has_unresolved_findings") is not False:
        problems.append(f"Codex code review on {short} did not report has_unresolved_findings: false.")
    problems += security_problems(state, sha)
    return problems


def mergeable_problems(pr: dict) -> list[str]:
    mergeable = pr.get("mergeable")
    if mergeable is None:
        return ["GitHub is still computing whether the pull request can merge."]
    if mergeable is not True:
        return [f"GitHub reports the pull request is not mergeable (mergeable_state: {pr.get('mergeable_state')})."]
    return []


class FileContentError(ValueError):
    """A changed file whose content the gate cannot judge. It refuses that one pull
    request instead of failing the run, so one odd file never holds up the others."""


def file_text(gh, cfg: Config, path: str, ref: str) -> str:
    data = gh.get(f"/repos/{cfg.repo}/contents/{urllib.parse.quote(path)}?ref={ref}")
    # Directories, symlinks, submodules and files over 1 MB come back without base64 content.
    if not isinstance(data, dict) or data.get("encoding") != "base64":
        raise FileContentError(f"`{path}` at {ref[:7]} is not a text file the gate can read, so it cannot be checked.")
    try:
        return base64.b64decode(data.get("content") or "").decode("utf-8")
    except ValueError:
        raise FileContentError(f"`{path}` at {ref[:7]} is not UTF-8 text, so it cannot be checked.") from None


def listed_versions(path: str, text: str) -> dict:
    """Plugin name to version for a marketplace file or a plugin manifest."""
    try:
        data = json.loads(text)
    except ValueError:
        raise FileContentError(f"`{path}` is not valid JSON, so the gate cannot read the plugins in it.") from None
    plugins = data.get("plugins", []) if isinstance(data, dict) else None
    if not isinstance(data, dict) or (path == MARKETPLACE_PATH and not isinstance(plugins, list)):
        raise FileContentError(f"`{path}` is not the JSON object it should be, so the gate cannot read the plugins in it.")
    if path == MARKETPLACE_PATH:
        return {p["name"]: p.get("version") for p in plugins if isinstance(p, dict) and isinstance(p.get("name"), str)}
    return {PLUGIN_MANIFEST_RE.match(path).group(1): data.get("version")}


def note_problem(text: str) -> tuple[str | None, list[str]]:
    """Why the release step would refuse this .changeset note (None when it reads it), and
    the plugins it names. Mirrors parse_note_text in tools/release/release.py. The gate
    cannot import it, because the workflow checks out only tools/auto-merge-gate, so
    tests/test_gate.py runs both on the same notes to keep them in step."""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if lines[0].strip() != "---":
        return "must start with a --- line, then one plugin: bump line per plugin, then ---", []
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        return "has an opening --- with no closing ---", []
    names: list[str] = []
    for raw in lines[1:end]:
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        m = NOTE_KEY_RE.match(raw)
        if not m:
            return f"has a line it cannot read, {raw.strip()!r}; write it as <plugin>: patch|minor|major", []
        name = m.group(1) or m.group(2) or m.group(3)
        bump = m.group(4).strip("\"'").lower()
        if bump not in NOTE_BUMPS:
            return f"asks for {bump!r} for {name}; use patch, minor or major", []
        if name in names:
            return f"names {name} twice", []
        names.append(name)
    if not names:
        return "names no plugin", []
    body = "\n".join(lines[end + 1:]).strip()
    if not body:
        return "says nothing about the change; write it below the closing ---", []
    if any(line.startswith("## ") for line in body.split("\n")):
        return "has a `## ` heading in its text, which would start a second CHANGELOG entry; use `###` or lower", []
    return None, names


def note_problems(gh, cfg: Config, notes: list, head: str) -> list[str]:
    """A note the release step cannot read would stop every plugin's release on main,
    so the gate refuses it here, before it can merge."""
    problems: list[str] = []
    named: list[tuple[str, str]] = []
    for f in notes:
        path = f["filename"]
        try:
            problem, names = note_problem(file_text(gh, cfg, path, head))
        except FileContentError as exc:
            problems.append(str(exc))
            continue
        if problem:
            problems.append(f"`{path}` {problem}. {NOTE_HINT}")
        named += [(path, name) for name in names]
    if not named:
        return problems
    try:
        known = listed_versions(MARKETPLACE_PATH, file_text(gh, cfg, MARKETPLACE_PATH, head))
    except FileContentError as exc:
        return problems + [str(exc)]
    for path, name in named:
        if name not in known:
            problems.append(f"`{path}` names {name}, which is not a plugin in `{MARKETPLACE_PATH}`. {NOTE_HINT}")
    return problems


def changelog_shape(text: str) -> tuple[list[str], int]:
    """The top entry (everything above the second ## heading) and how many entries there are."""
    lines = text.splitlines()
    heads = [i for i, line in enumerate(lines) if line.startswith("## ")]
    return lines[: heads[1] if len(heads) > 1 else len(lines)], len(heads)


def release_file_problems(gh, cfg: Config, number: int, pr: dict) -> list[str]:
    """A pull request may not edit a plugin version or the top of a CHANGELOG.md.
    Brand new plugins and edits to older CHANGELOG entries are allowed."""
    files = [f for f in gh.paginate(f"/repos/{cfg.repo}/pulls/{number}/files") if f.get("status") != "removed"]
    watched = [
        f for f in files
        if f.get("filename") == MARKETPLACE_PATH
        or PLUGIN_MANIFEST_RE.match(f.get("filename", ""))
        or CHANGELOG_RE.search(f.get("filename", ""))
    ]
    # The release step reads every top-level .changeset/*.md except the README.
    notes = [
        f for f in files
        if CHANGESET_NOTE_RE.match(f.get("filename", "")) and f["filename"].rsplit("/", 1)[-1].lower() != "readme.md"
    ]
    if not watched and not notes:
        return []
    head = (pr.get("head") or {}).get("sha", "")
    problems: list[str] = []
    if watched:
        # Compare against the merge base, not the base tip, so a release that landed on
        # main after the branch was cut is not mistaken for an edit by this branch.
        compare = gh.get(f"/repos/{cfg.repo}/compare/{(pr.get('base') or {}).get('sha', '')}...{head}")
        merge_base = compare["merge_base_commit"]["sha"]
        for f in watched:
            try:
                problems += release_file_change(gh, cfg, f, head, merge_base)
            except FileContentError as exc:
                problems.append(str(exc))
    return problems + note_problems(gh, cfg, notes, head)


def release_file_change(gh, cfg: Config, f: dict, head: str, merge_base: str) -> list[str]:
    path = f["filename"]
    added = f.get("status") == "added"
    before_path = f.get("previous_filename") or path
    if CHANGELOG_RE.search(path):
        if added:
            return [f"`{path}` is a new CHANGELOG. {RELEASE_HINT}"]
        old_top, old_count = changelog_shape(file_text(gh, cfg, before_path, merge_base))
        new_top, new_count = changelog_shape(file_text(gh, cfg, path, head))
        if new_count > old_count:
            return [f"`{path}` adds a CHANGELOG entry. {RELEASE_HINT}"]
        if new_top != old_top:
            return [f"`{path}` edits the top CHANGELOG entry. {RELEASE_HINT}"]
        return []
    after = listed_versions(path, file_text(gh, cfg, path, head))
    before = {} if added else listed_versions(path, file_text(gh, cfg, before_path, merge_base))
    return [
        f"`{path}` changes the {name} version from {before[name]} to {after[name]}. {RELEASE_HINT}"
        for name in sorted(set(before) & set(after))
        if before[name] != after[name]
    ]


def evaluate(gh, cfg: Config, number: int) -> Decision:
    pr = gh.get(f"/repos/{cfg.repo}/pulls/{number}")

    def skip(why: str) -> Decision:
        return Decision(number, "skip", [why])

    if pr.get("state") != "open":
        return skip("not open")
    if pr.get("draft"):
        return skip("draft")
    author = (pr.get("user") or {}).get("login")
    if (pr.get("base") or {}).get("ref") != cfg.base_branch:
        return skip(f"base is not {cfg.base_branch}")
    labelled = bool(cfg.merge_label) and cfg.merge_label in {
        label.get("name") for label in pr.get("labels", [])
    }
    issue_number = None
    issue_number = None
    job_problem = None
    if author == FACTORY_LOGIN and job_issue_number(pr.get("body")) is not None:
        candidate = job_issue_number(pr.get("body"))
        # A read failure is never a reason to switch routes. It is raised, so
        # run_plan and run_merge report it and fail the run, and the next
        # sweep retries.
        issue = gh.get(f"/repos/{cfg.repo}/issues/{candidate}")
        if issue is not None:
            if "pull_request" in issue:
                job_problem = f"#{candidate} is a pull request, not a job issue"
            elif JOB_LABEL not in {label.get("name") for label in issue.get("labels", [])}:
                job_problem = f"issue #{candidate} does not carry the {JOB_LABEL} label"
            else:
                issue_number = candidate
        # Either route is enough. A labelled pull request whose Closes #N is
        # not a job issue still goes through the label route.
        if job_problem and not labelled:
            return skip(job_problem)
    elif not labelled:
        if author != FACTORY_LOGIN:
            why = f"author is {author}, not {FACTORY_LOGIN}"
        else:
            why = "body does not start with Closes #N"
        if cfg.merge_label:
            why += f", and it does not carry the {cfg.merge_label} label"
        return skip(why)

    sha = (pr.get("head") or {}).get("sha", "")
    comments = gh.paginate(f"/repos/{cfg.repo}/issues/{number}/comments")
    reasons = check_problems(gh, cfg, sha)
    reasons += release_file_problems(gh, cfg, number, pr)
    threads = getattr(gh, "unresolved_threads", None)

    def open_threads():
        # Resolving a thread is not the same as fixing it. A Codex review on
        # this exact head that still carries findings keeps the gate shut.
        reviews = gh.paginate(f"/repos/{cfg.repo}/pulls/{number}/reviews")
        for review in reviews:
            if (review.get("user") or {}).get("login") != CODEX_LOGIN or review.get("commit_id") != sha:
                continue
            found = gh.paginate(f"/repos/{cfg.repo}/pulls/{number}/reviews/{review['id']}/comments")
            if found:
                return len(found)
        return threads(cfg.repo, number) if threads else None

    reasons += codex_problems(latest_codex_state(comments), sha, open_threads, has_clean_codex_receipt(comments, sha))
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
    if d.issue is None:
        return sha
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
    def wanted(p: dict) -> bool:
        if (p.get("user") or {}).get("login") == FACTORY_LOGIN:
            return True
        return bool(cfg.merge_label) and cfg.merge_label in {
            label.get("name") for label in p.get("labels", [])
        }

    return [int(p["number"]) for p in open_prs if not p.get("draft") and wanted(p)]


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
        merge_label=os.environ.get("GATE_MERGE_LABEL", ""),
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
