#!/usr/bin/env python3
"""Auto-merge gate for finished Chat to Code jobs (Decision Log 2026-11-01, Finished code
merges itself, except in Ember's repo). Copied from expert-partners-skills, with one addition.

A pull request is eligible when either
  - it is a Factory job pull request (author factory-droid[bot], body starting with
    Closes #N where #N is an issue labeled job), or
  - GATE_MERGE_LABEL is set and the pull request carries that label. Repos whose
    builders push as a person (Factory missions, Claude Code) mark finished work this way.
    The label counts only when its latest labeled event is by a login listed in
    GATE_MERGE_LABEL_ACTORS and came after the push that made the current head the
    branch tip. Pull requests opened by an app other than Factory are never enrolled this way.
Either way it merges only when every check on the head commit passed, the pull request
leaves plugin versions and the top of every CHANGELOG.md to the release step
(tools/release, fed by notes in .changeset/) and every note it adds is one that step can
read, Codex's code review covers that exact head and leaves no P0 or P1 finding open, and
GitHub says it can merge. P2 and lower findings never block on their own (AGENTS.md,
Review guidelines).

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
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol

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
# Codex marks each inline finding with a severity badge, e.g.
# ![P2 Badge](https://img.shields.io/badge/P2-yellow?style=flat).
SEVERITY_RE = re.compile(r"!\[(P\d+) Badge\]|img\.shields\.io/badge/(P\d+)-", re.IGNORECASE)
SECURITY_FINDING_MARKER = "codex-security-review-finding:v1"
# AGENTS.md, Review guidelines: only P0 and P1 findings block a merge.
BLOCKING_SEVERITIES = {"P0", "P1"}
BOLD_RE = re.compile(r"\*\*(.+?)\*\*", re.DOTALL)
BADGE_MARKUP_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)|</?sub>")

PR_EVENTS = {"pull_request", "pull_request_target", "pull_request_review"}

MARKETPLACE_PATH = ".claude-plugin/marketplace.json"
PLUGIN_MANIFEST_RE = re.compile(r"^plugins/([^/]+)/\.claude-plugin/plugin\.json$")
CHANGELOG_RE = re.compile(r"(^|/)CHANGELOG\.md$")
RELEASE_HINT = "The release step owns versions and CHANGELOG entries; add a note in `.changeset/` instead."
CHANGESET_NOTE_RE = re.compile(r"^\.changeset/[^/]+\.md$")
NOTE_BUMPS = ("patch", "minor", "major")
NOTE_KEY_RE = re.compile(r"""^\s*(?:"([^"]+)"|'([^']+)'|([A-Za-z0-9._-]+))\s*:\s*(\S+?)\s*$""")
NOTE_HINT = "The release step would refuse it and hold up every plugin's release; `.changeset/README.md` gives the format."

# One object from the GitHub REST or GraphQL API, decoded from JSON.
JSONDict = dict[str, Any]


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

    def _request(self, method: str, url: str, body: JSONDict | None = None) -> tuple[Any, str]:
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

    def get(self, path: str, params: JSONDict | None = None) -> Any:
        if params:
            path += "?" + urllib.parse.urlencode(params)
        return self._request("GET", path)[0]

    def paginate(self, path: str, key: str | None = None, params: JSONDict | None = None) -> list[JSONDict]:
        query = dict(params or {})
        query.setdefault("per_page", 100)
        url: str | None = f"{path}?{urllib.parse.urlencode(query)}"
        items: list[JSONDict] = []
        while url:
            data, link = self._request("GET", url)
            items.extend(data[key] if key else data)
            url = next((p.split(";")[0].strip()[1:-1] for p in link.split(",") if 'rel="next"' in p), None)
        return items

    def review_threads(self, repo: str, number: int) -> dict[int, bool]:
        """Whether each review thread on the pull request is resolved, keyed by the
        REST id of the thread's first comment."""
        owner, name = repo.split("/", 1)
        query = (
            "query($o:String!,$n:String!,$p:Int!,$a:String){repository(owner:$o,name:$n){"
            "pullRequest(number:$p){reviewThreads(first:100,after:$a){"
            "nodes{isResolved comments(first:1){nodes{databaseId}}} pageInfo{hasNextPage endCursor}}}}}"
        )
        resolved: dict[int, bool] = {}
        after: str | None = None
        while True:
            data, _ = self._request(
                "POST", self.api_url + "/graphql",
                {"query": query, "variables": {"o": owner, "n": name, "p": number, "a": after}},
            )
            if not data or data.get("errors"):
                raise GitHubError(502, f"review threads could not be read: {(data or {}).get('errors')}")
            threads = data["data"]["repository"]["pullRequest"]["reviewThreads"]
            for t in threads["nodes"]:
                first = ((t.get("comments") or {}).get("nodes") or [{}])[0] or {}
                if first.get("databaseId") is not None:
                    resolved[int(first["databaseId"])] = bool(t.get("isResolved"))
            if not threads["pageInfo"]["hasNextPage"]:
                return resolved
            after = threads["pageInfo"]["endCursor"]

    def post(self, path: str, body: JSONDict) -> Any:
        return self._request("POST", path, body)[0]

    def put(self, path: str, body: JSONDict) -> Any:
        return self._request("PUT", path, body)[0]

    def patch(self, path: str, body: JSONDict) -> Any:
        return self._request("PATCH", path, body)[0]


class GitHubAPI(Protocol):
    """The methods the gate calls on GitHub, met by GitHub and by the tests' fake."""

    def get(self, path: str, params: JSONDict | None = None) -> Any: ...

    def paginate(self, path: str, key: str | None = None, params: JSONDict | None = None) -> list[JSONDict]: ...

    def post(self, path: str, body: JSONDict) -> Any: ...

    def put(self, path: str, body: JSONDict) -> Any: ...

    def patch(self, path: str, body: JSONDict) -> Any: ...


@dataclass
class Config:
    repo: str
    gate_check_name: str = "auto-merge-gate"
    base_branch: str = "main"
    server_url: str = "https://github.com"
    merge_label: str = ""
    # Logins whose labeled event enrolls a pull request. Empty means none does.
    merge_label_actors: frozenset[str] = frozenset()


@dataclass
class Decision:
    pr: int
    action: str  # "skip" (left alone), "refuse" (eligible, a condition is not met), "merge"
    reasons: list[str] = field(default_factory=list)
    head_sha: str = ""
    issue: int | None = None
    comments: list[JSONDict] = field(default_factory=list)


def job_issue_number(body: str | None) -> int | None:
    m = CLOSES_RE.match((body or "").lstrip())
    return int(m.group(1)) if m else None


def latest_codex_state(comments: list[JSONDict]) -> JSONDict | None:
    """The codex-review-state JSON from Codex's most recently updated summary comment."""
    best: JSONDict | None = None
    best_at = ""
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


def has_clean_codex_receipt(comments: list[JSONDict], sha: str) -> bool:
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


def check_problems(gh: GitHubAPI, cfg: Config, sha: str) -> list[str]:
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


@dataclass
class Finding:
    """One inline finding Codex left on the pull request."""
    comment_id: int | None
    kind: str  # "code" or "security"
    severity: str | None  # "P0", "P1", "P2", ... or None when the badge cannot be read
    commit: str  # the commit Codex reviewed when it raised the finding
    title: str
    url: str = ""
    resolved: bool | None = None  # None when the thread state is unknown

    def describe(self) -> str:
        what = f"Codex {self.severity} {self.kind} finding" if self.severity else f"Codex {self.kind} finding with no readable severity"
        link = f" ({self.url})" if self.url else ""
        return f"{what} \"{self.title}\"{link}"


def finding_severity(body: str) -> str | None:
    """The one P-level badge on a finding, or None when there is none or more than one."""
    found = {(alt or url).upper() for alt, url in SEVERITY_RE.findall(body)}
    return found.pop() if len(found) == 1 else None


def finding_title(body: str) -> str:
    """The finding's headline: the bold text that carries its badge, else the first bold text."""
    bold = [m.group(1) for m in BOLD_RE.finditer(body)]
    for text in sorted(bold, key=lambda b: "Badge" not in b):
        title = " ".join(BADGE_MARKUP_RE.sub("", text).split())
        if title:
            return title[:120]
    first = next((line.strip() for line in body.splitlines() if line.strip() and not line.strip().startswith("<!--")), "")
    return first[:120] or "(no text)"


def parse_finding(comment: JSONDict) -> Finding:
    body = comment.get("body") or ""
    return Finding(
        comment_id=comment.get("id"),
        kind="security" if SECURITY_FINDING_MARKER in body else "code",
        severity=finding_severity(body),
        commit=comment.get("original_commit_id") or comment.get("commit_id") or "",
        title=finding_title(body),
        url=comment.get("html_url") or "",
    )


def codex_findings(gh: GitHubAPI, cfg: Config, number: int, sha: str) -> tuple[list[Finding], str | None]:
    """Every inline finding Codex left, with whether its thread is resolved, and a note
    saying why thread states are unknown (None when they were all read)."""
    comments = gh.paginate(f"/repos/{cfg.repo}/pulls/{number}/comments")
    found = [
        parse_finding(c) for c in comments
        if (c.get("user") or {}).get("login") == CODEX_LOGIN and not c.get("in_reply_to_id")
    ]
    if all(f.commit == sha for f in found):
        # Findings on this head block on severity alone, so their threads never matter.
        return found, None
    reader = getattr(gh, "review_threads", None)
    if reader is None:
        return found, "the review threads could not be checked"
    try:
        resolved = reader(cfg.repo, number)
    except GitHubError as exc:
        return found, f"the review threads could not be read ({exc.message})"
    for f in found:
        f.resolved = resolved.get(f.comment_id)
    return found, "its review thread was not found"


def blocking_findings(findings: list[Finding], sha: str, note: str | None, kind: str | None = None) -> tuple[list[str], int]:
    """(why each P0, P1 or unreadable finding blocks, how many findings are open).

    A finding is open when Codex raised it on this head (resolving its thread does
    not fix the code) or its thread is unresolved. P2 and lower never block on
    their own, open or not (AGENTS.md, Review guidelines)."""
    short = sha[:7]
    problems: list[str] = []
    open_count = 0
    for f in findings:
        if kind and f.kind != kind:
            continue
        on_head = f.commit == sha
        if not on_head and f.resolved is True:
            continue
        if on_head or f.resolved is False:
            open_count += 1
        if f.severity is not None and f.severity not in BLOCKING_SEVERITIES:
            continue
        gap = "" if f.severity else " The gate cannot read its severity, so this is a gap in the review evidence, not a pass."
        if on_head:
            problems.append(f"{f.describe()} blocks: Codex raised it on head {short}.{gap}")
        elif f.resolved is False:
            problems.append(f"{f.describe()} blocks: its thread from {f.commit[:7] or 'an earlier commit'} is unresolved.{gap}")
        else:
            problems.append(
                f"{f.describe()} from {f.commit[:7] or 'an earlier commit'} may still be open: "
                f"{note or 'its review thread could not be checked'}.{gap}"
            )
    return problems, open_count


def unexplained(kind: str, sha: str, findings: list[Finding], note: str | None) -> str:
    """Codex says findings of this kind are unresolved, but none the gate can read is open."""
    short = sha[:7]
    if note and any(f.kind == kind and f.resolved is None and f.commit != sha for f in findings):
        why = f"{note}, so the gate cannot tell which are open"
    else:
        why = f"the gate found no open Codex {kind} finding comment to read their severity from"
    return f"Codex {kind} review on {short} reports unresolved findings, but {why}."


def security_problems(
    state: JSONDict | None, sha: str, load: Callable[[], tuple[list[Finding] | None, str | None]]
) -> list[str]:
    security = (state or {}).get("security_review") or {}
    if security.get("commit_sha") != sha or security.get("has_unresolved_findings") is not True:
        return []
    short = sha[:7]
    found, note = load()
    if found is None:
        return [f"Codex security review on {short} reports unresolved findings, but {note}, so the gate cannot read their severity."]
    problems, open_count = blocking_findings(found, sha, note, "security")
    if not problems and open_count == 0:
        problems.append(unexplained("security", sha, found, note))
    return problems


def codex_problems(
    state: JSONDict | None,
    sha: str,
    findings: Callable[[], tuple[list[Finding], str | None]] | None = None,
    clean_receipt: bool = False,
) -> list[str]:
    """findings is a callable returning (list of Finding, note), see codex_findings.
    It is called at most once, and only when the aggregate state says findings
    exist. clean_receipt says Codex posted a clean code review receipt for this
    head (has_clean_codex_receipt).

    The aggregate booleans in Codex's summary are not a severity. When they say a
    finding exists, each finding decides: P0, P1 and unreadable ones block, P2 and
    lower do not."""
    short = sha[:7]
    loaded: list[tuple[list[Finding] | None, str | None]] = []

    def load() -> tuple[list[Finding] | None, str | None]:
        if not loaded:
            if findings is None:
                loaded.append((None, "the review comments could not be checked"))
            else:
                try:
                    loaded.append(findings())
                except GitHubError as exc:
                    loaded.append((None, f"the review comments could not be read ({exc.message})"))
        return loaded[0]

    problems: list[str] = []
    if clean_receipt and ((state or {}).get("code_review") or {}).get("commit_sha") != sha:
        # The receipt stands in only for a summary that is missing or still on
        # an older commit. A summary that covers this head keeps deciding.
        # The receipt says nothing about findings left open on earlier commits,
        # and the summary it replaces may be stale, so every finding is read.
        found, note = load()
        if found is None:
            return [f"Codex posted a clean code review receipt for {short}, but {note}."] + security_problems(state, sha, load)
        problems += blocking_findings(found, sha, note)[0]
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
    unresolved = code.get("has_unresolved_findings")
    if code.get("status") != "completed":
        problems.append(f"Codex code review on {short} is {code.get('status')}, not completed.")
    elif unresolved is True or (unresolved is None and code.get("has_any_findings") is True):
        # Once a pull request has ever had findings, Codex reports null instead
        # of false even after every finding is fixed and its thread resolved.
        found, note = load()
        if found is None:
            if unresolved is True:
                problems.append(f"Codex code review on {short} reports unresolved findings, but {note}, so the gate cannot read their severity.")
            else:
                problems.append(f"Codex code review on {short} did not report has_unresolved_findings: false, and {note}.")
        else:
            blockers, _ = blocking_findings(found, sha, note)
            problems += blockers
            # True claims a finding is open now, so one must be found to read its severity.
            if unresolved is True and not blockers and blocking_findings(found, sha, note, "code")[1] == 0:
                problems.append(unexplained("code", sha, found, note))
    elif unresolved is not False:
        problems.append(f"Codex code review on {short} did not report has_unresolved_findings: false.")
    problems += security_problems(state, sha, load)
    return list(dict.fromkeys(problems))


def mergeable_problems(pr: JSONDict) -> list[str]:
    mergeable = pr.get("mergeable")
    if mergeable is None:
        return ["GitHub is still computing whether the pull request can merge."]
    if mergeable is not True:
        return [f"GitHub reports the pull request is not mergeable (mergeable_state: {pr.get('mergeable_state')})."]
    return []


class FileContentError(ValueError):
    """A changed file whose content the gate cannot judge. It refuses that one pull
    request instead of failing the run, so one odd file never holds up the others."""


def file_text(gh: GitHubAPI, cfg: Config, path: str, ref: str) -> str:
    data = gh.get(f"/repos/{cfg.repo}/contents/{urllib.parse.quote(path)}?ref={ref}")
    # Directories, symlinks, submodules and files over 1 MB come back without base64 content.
    if not isinstance(data, dict) or data.get("encoding") != "base64":
        raise FileContentError(f"`{path}` at {ref[:7]} is not a text file the gate can read, so it cannot be checked.")
    try:
        return base64.b64decode(data.get("content") or "").decode("utf-8")
    except ValueError:
        raise FileContentError(f"`{path}` at {ref[:7]} is not UTF-8 text, so it cannot be checked.") from None


def listed_versions(path: str, text: str) -> dict[str, object]:
    """Plugin name to version for a marketplace file or a plugin manifest."""
    try:
        data = json.loads(text)
    except ValueError:
        raise FileContentError(f"`{path}` is not valid JSON, so the gate cannot read the plugins in it.") from None
    plugins = data.get("plugins", []) if isinstance(data, dict) else None
    if not isinstance(data, dict) or (path == MARKETPLACE_PATH and not isinstance(plugins, list)):
        raise FileContentError(f"`{path}` is not the JSON object it should be, so the gate cannot read the plugins in it.")
    # plugins is always a list here for the marketplace, the check above made sure.
    if path == MARKETPLACE_PATH and isinstance(plugins, list):
        return {p["name"]: p.get("version") for p in plugins if isinstance(p, dict) and isinstance(p.get("name"), str)}
    manifest = PLUGIN_MANIFEST_RE.match(path)
    if manifest is None:
        raise FileContentError(f"`{path}` is neither the marketplace file nor a plugin manifest, so the gate cannot read the plugins in it.")
    return {manifest.group(1): data.get("version")}


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


def note_problems(gh: GitHubAPI, cfg: Config, notes: list[JSONDict], head: str) -> list[str]:
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


def release_file_problems(gh: GitHubAPI, cfg: Config, number: int, pr: JSONDict) -> list[str]:
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


def release_file_change(gh: GitHubAPI, cfg: Config, f: JSONDict, head: str, merge_base: str) -> list[str]:
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


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def label_enrollment(gh: GitHubAPI, cfg: Config, number: int, pr: JSONDict) -> tuple[str, str] | None:
    """None when the merge label enrolls this head, else ("skip" or "refuse", why).

    Any user or app with triage access can add a label, and a label stays on through
    later pushes. So the label counts only when its latest labeled event is by an
    enrollment actor and came after the push that made the current head the tip."""
    label = cfg.merge_label
    author = (pr.get("user") or {}).get("login") or ""
    if author.endswith("[bot]") and author != FACTORY_LOGIN:
        # Dependency updates and other app pull requests are merged by a person
        # (tools/dependency-policy/README.md), never through the label.
        return "skip", f"author is the app {author}, and the {label} label enrolls only work pushed by a person or Factory"
    events = gh.paginate(f"/repos/{cfg.repo}/issues/{number}/events")
    last = next(
        (e for e in reversed(events)
         if e.get("event") in ("labeled", "unlabeled") and (e.get("label") or {}).get("name") == label),
        None,
    )
    if last is None or last.get("event") != "labeled":
        return "skip", f"no labeled event for the {label} label was found"
    actor = (last.get("actor") or {}).get("login") or "an unknown actor"
    if actor.casefold() not in {a.casefold() for a in cfg.merge_label_actors}:
        return "skip", f"the {label} label was added by {actor}, who is not an enrollment actor (GATE_MERGE_LABEL_ACTORS)"
    head = pr.get("head") or {}
    sha, ref = head.get("sha", ""), head.get("ref", "")
    head_repo = (head.get("repo") or {}).get("full_name")
    if head_repo != cfg.repo:
        return "refuse", (
            f"The {label} label enrolls only branches in {cfg.repo}, where the gate can see each push, "
            f"and this head is in {head_repo or 'a deleted repository'}."
        )
    # Repository activity is GitHub's own push record, newest first. A commit's dates
    # are set by whoever made it, so they cannot say when it became the head.
    activity = gh.get(
        f"/repos/{cfg.repo}/activity", {"ref": f"refs/heads/{ref}", "direction": "desc", "per_page": 1}
    ) or []
    latest = activity[0] if activity else {}
    if latest.get("after") != sha:
        return "refuse", f"The gate cannot see the push that made {sha[:7]} the head of `{ref}` yet."
    labelled_at, pushed_at = last.get("created_at") or "", latest.get("timestamp") or ""
    if not labelled_at or not pushed_at or parse_time(labelled_at) <= parse_time(pushed_at):
        return "refuse", (
            f"{actor} added the {label} label at {labelled_at or 'an unknown time'}, before head {sha[:7]} "
            f"was pushed at {pushed_at or 'an unknown time'}. Remove the label and add it again to enroll this head."
        )
    return None


def evaluate(gh: GitHubAPI, cfg: Config, number: int) -> Decision:
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

    reasons: list[str] = []
    if issue_number is None:
        enrollment = label_enrollment(gh, cfg, number, pr)
        if enrollment and enrollment[0] == "skip":
            return skip(enrollment[1])
        if enrollment:
            reasons.append(enrollment[1])
    sha = (pr.get("head") or {}).get("sha", "")
    comments = gh.paginate(f"/repos/{cfg.repo}/issues/{number}/comments")
    reasons += check_problems(gh, cfg, sha)
    reasons += release_file_problems(gh, cfg, number, pr)
    reasons += codex_problems(
        latest_codex_state(comments), sha,
        lambda: codex_findings(gh, cfg, number, sha),
        has_clean_codex_receipt(comments, sha),
    )
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


def post_refusal(gh: GitHubAPI, cfg: Config, d: Decision) -> None:
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


def merge(gh: GitHubAPI, merger: GitHubAPI, cfg: Config, d: Decision) -> str | None:
    try:
        result = merger.put(
            f"/repos/{cfg.repo}/pulls/{d.pr}/merge",
            {"merge_method": "squash", "sha": d.head_sha},
        )
    except GitHubError as exc:
        d.reasons = [f"GitHub refused the squash merge: {exc.message}"]
        post_refusal(gh, cfg, d)
        return None
    sha: str = (result or {}).get("sha", "")
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


def target_prs(gh: GitHubAPI, cfg: Config, event_name: str, event: JSONDict, dispatch_pr: str = "") -> list[int]:
    if event_name in PR_EVENTS:
        return [int(event["pull_request"]["number"])]
    if event_name == "issue_comment":
        issue = event.get("issue") or {}
        return [int(issue["number"])] if "pull_request" in issue else []
    if event_name == "workflow_dispatch" and dispatch_pr.strip():
        return [int(dispatch_pr.strip())]
    # schedule, check_suite and a dispatch without a number sweep every open pull request.
    open_prs = gh.paginate(f"/repos/{cfg.repo}/pulls", params={"state": "open"})
    def wanted(p: JSONDict) -> bool:
        if (p.get("user") or {}).get("login") == FACTORY_LOGIN:
            return True
        return bool(cfg.merge_label) and cfg.merge_label in {
            label.get("name") for label in p.get("labels", [])
        }

    return [int(p["number"]) for p in open_prs if not p.get("draft") and wanted(p)]


def is_excluded_repo(repo: str) -> bool:
    # Decision Log 2026-11-01: Ember's repository never merges itself.
    return repo.split("/")[-1].lower() == "ember"


def run_plan(
    gh: GitHubAPI, cfg: Config, event_name: str, event: JSONDict, dispatch_pr: str = "", errors: list[str] | None = None
) -> list[int]:
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


def run_merge(gh: GitHubAPI, merger: GitHubAPI, cfg: Config, numbers: list[int], errors: list[str] | None = None) -> list[str]:
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
        merge_label_actors=frozenset(re.split(r"[\s,]+", os.environ.get("GATE_MERGE_LABEL_ACTORS", ""))) - {""},
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
