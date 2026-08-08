#!/usr/bin/env python3
"""
ruling-provenance-lint.py -- Ruling provenance gate (L6 Gatekeeper).

Enforces the format defined in aura doctrine/ruling-of-record-format.md, itself
authored under aura intake/2026-08-07-ruling-rulings-become-citable-records-and-
rules-carry-proven.md. That ruling's origin: on 2026-08-07 a commit
(expert-partners-skills a7740b8) struck two real rulings of Allison's, citing
only the string "Addendum ruled by Allison 2026-08-07" with no file anywhere
backing it. Nothing could tell a real ruling from a fabricated one, because
neither had ever produced an artifact. This gate makes that distinction
checkable at commit time instead of discoverable by a live git trace weeks
later.

Three checks, all ERRORs (fail the commit):

  1. CITATION RESOLVES -- every ruling citation found in a changed file (the
     phrase "ruling of record" followed by a path, or a machine-readable
     RULED-BY marker) must resolve to a real file on the cited repo's main
     branch at commit time. An authority-claim phrase ("Ruled by Allison",
     "Re-ruled by Allison") with no citation nearby is the same failure --
     an authority asserted with nothing behind it.

  2. SUPERSESSION NAMES ITSELF -- a diff that removes or rewrites a line
     carrying a ruling citation must, in the same file's diff, add a line
     matching /supersed/ AND a new resolvable citation authorizing the
     change. Silent replacement of a cited rule is the failure this closes.

  3. DISCLOSURE FILED -- a commit that trips check 2 must also add a new
     file under intake/ whose name or leading content marks it as a
     disclosure of that supersession. Superseding a ruling is not itself
     the failure; superseding one without telling Allison is.

Scope, stated honestly (mirrors skill-description-lint's own candor):
  Check 2 fires when the CITATION LINE ITSELF (the marker or the "ruling of
  record" sentence) is removed or rewritten. It does not detect a rule's
  surrounding prose changing while its citation line survives untouched --
  catching that would require parsing rule boundaries, not just diff lines,
  and is out of scope for this pass. A rule discovered to need marking gets
  marked when it is next touched (aura doctrine/ruling-of-record-format.md,
  "What this does not solve").

  This gate does not retroactively validate existing rules. Provenance is
  required from adoption forward. Most rule text estate-wide carries no
  citation today and is not swept; only DIFFS are checked.

Citation forms recognized (either satisfies check 1):
  Prose (the estate's existing convention, unchanged):
    ruling of record: aura intake/2026-08-07-ruling-<slug>.md
    ruling of record at aura intake/2026-08-05-ruling-<slug>.md
  Machine-readable marker (required going forward for any rule newly
  adopting provenance, aura doctrine/ruling-of-record-format.md):
    <!-- RULED-BY: aura/intake/2026-08-07-ruling-<slug>.md date:2026-08-07 -->
  A bare repo-relative path (no "aura" prefix) is read as same-repo.

Resolution:
  A same-repo path is checked against the working tree (pre-commit) or the
  checked-out tree (CI). A cross-repo path (today, always "aura") is checked
  against a live source in this priority order:
    1. --aura-path DIR, an already-checked-out aura tree (CI wires this via
       the existing SKILLS_GRAPH_TOKEN secret, the same credential the
       skills-graph workflow already uses to check out aura read-only).
    2. RULING_LINT_AURA_CLONE env var, a local aura clone with an `origin`
       remote -- resolved LIVE via `git ls-remote` + `git show`, never by
       reading the clone's possibly-stale local main.
    3. `gh api repos/ExpertPartners/aura/contents/<path>?ref=main`, when the
       `gh` CLI is authenticated (the estate's normal dev-machine state).
  If none of the three can answer, the citation FAILS closed -- unresolvable
  is not a pass, per the parent ruling's "fails when a cited path does not
  resolve." A verification failure and a missing file report the same way.

Usage:
  python3 .ep/ruling-provenance-lint.py --pre-commit [FILE ...]
      Check staged changes (git diff --cached) against HEAD. FILE args are
      informational only (pre-commit passes them); the diff scope decides
      what is actually checked, matching this repo's other local hooks.

  python3 .ep/ruling-provenance-lint.py --ci BASE_SHA HEAD_SHA
      Check the diff between two commits (CI wiring, mirrors ci.yml's
      existing changed-files pattern).

  python3 .ep/ruling-provenance-lint.py --selftest
      Prove all three checks against deliberate failing and passing
      fixtures, offline (no network, no git diff -- pure fixture data).

  --aura-path DIR   pre-resolved aura checkout for cross-repo citations
  --repo NAME       override current-repo name (default: read from `git
                     remote get-url origin`)

Escape hatch:
  A file that legitimately discusses this gate's own syntax as documentation
  (this script's own docstring being the standing example: it quotes "Ruled
  by Allison" and example paths as illustrations, not as authority claims)
  puts the literal token `ruling-provenance-lint: ignore-file` anywhere in
  its text to skip check 1 entirely for that file. Check 2/3 are diff-shaped
  across the whole commit and are not file-scoped, so the token does not
  touch them.

Exit code: 0 = clean, 1 = at least one breach, 2 = bad invocation / could not
verify (fails closed, per the parent ruling).
"""

# ruling-provenance-lint: ignore-file -- this docstring quotes its own
# trigger phrase and example paths as documentation, not as authority claims.

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

TRIGGER_RE = re.compile(r"\bre-?ruled\s+by\s+allison\b|\bruled\s+by\s+allison\b", re.IGNORECASE)
SUPERSEDE_RE = re.compile(r"supersed", re.IGNORECASE)

# A citation path: optional repo prefix ("aura " or "aura/"), then
# intake/<name>.md or decisions/<name>.md.
_PATH_CORE = r"(?:intake|decisions)/[A-Za-z0-9_.\-]+\.md"
CITATION_RE = re.compile(
    r"(?:\b(?P<repo>[A-Za-z][A-Za-z0-9_.\-]*)[ /])?(?P<path>" + _PATH_CORE + r")"
)
MARKER_RE = re.compile(r"RULED-BY:\s*" + r"(?:(?P<repo>[A-Za-z][A-Za-z0-9_.\-]*)/)?(?P<path>" + _PATH_CORE + r")" + r"(?:\s+date:(?P<date>\d{4}-\d{2}-\d{2}))?")

KNOWN_REPOS = {"aura", "expert-partners-skills", "second-brain", "allison-claude-doctrine"}
IGNORE_FILE_TOKEN = "ruling-provenance-lint: ignore-file"


@dataclass
class Citation:
    repo: str | None   # None means "current repo"
    path: str
    line_no: int
    line_text: str

    def key(self) -> tuple[str, str]:
        return (self.repo or "<self>", self.path)


@dataclass
class Finding:
    check: str
    file: str
    line: int
    message: str


@dataclass
class DiffHunk:
    file: str
    removed: list[tuple[int, str]] = field(default_factory=list)  # (old line no, text)
    added: list[tuple[int, str]] = field(default_factory=list)    # (new line no, text)
    is_new_file: bool = False


# ---------------------------------------------------------------------------
# Citation extraction
# ---------------------------------------------------------------------------

def extract_citations(text: str) -> list[Citation]:
    """Find every ruling citation in a block of text (one file's worth, or a
    commit message). Recognizes the marker form and the prose form."""
    out: list[Citation] = []
    lines = text.splitlines()
    for i, line in enumerate(lines):
        for m in MARKER_RE.finditer(line):
            out.append(Citation(m.group("repo"), m.group("path"), i, line))
        if re.search(r"ruling of record", line, re.IGNORECASE):
            # Look for a path on this line or the next one (prose commonly
            # wraps: "...ruling of record:\naura intake/....md").
            window = "\n".join(lines[i:i + 2])
            for m in CITATION_RE.finditer(window):
                repo = m.group("repo")
                if repo and repo not in KNOWN_REPOS and repo.lower() not in ("at", "record"):
                    # A stray word directly before the path that isn't a repo
                    # name (e.g. "record aura intake/..." double-matches
                    # "record" as repo) -- only accept known repo names as a
                    # repo prefix, else treat the path as same-repo/bare.
                    repo = None
                elif repo and repo.lower() in ("at", "record"):
                    repo = None
                out.append(Citation(repo, m.group("path"), i, line))
    return out


def find_unbacked_triggers(text: str, citations: list[Citation]) -> list[int]:
    """Line numbers where 'Ruled by Allison' (or a variant) appears with no
    citation anywhere in the same or next 4 lines."""
    lines = text.splitlines()
    cited_lines = set()
    for c in citations:
        for offset in range(-4, 5):
            cited_lines.add(c.line_no + offset)
    bad = []
    for i, line in enumerate(lines):
        if TRIGGER_RE.search(line) and i not in cited_lines:
            bad.append(i)
    return bad


# ---------------------------------------------------------------------------
# Resolution
# ---------------------------------------------------------------------------

def current_repo_name(repo_root: Path, override: str | None) -> str:
    if override:
        return override
    try:
        url = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=repo_root, capture_output=True, text=True, check=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return repo_root.name
    m = re.search(r"/([^/]+?)(?:\.git)?$", url)
    return m.group(1) if m else repo_root.name


def resolve_same_repo(repo_root: Path, path: str) -> tuple[bool, str]:
    p = repo_root / path
    if p.is_file():
        return True, f"found in working tree: {path}"
    return False, f"not found in working tree: {path}"


def resolve_aura_path(path: str, aura_path: str | None) -> tuple[bool, str]:
    # 1. Pre-resolved checkout (CI wiring).
    if aura_path:
        p = Path(aura_path) / path
        if p.is_file():
            return True, f"found in checked-out aura tree: {path}"
        return False, f"not found in checked-out aura tree ({aura_path}): {path}"

    # 2. Local clone with a live remote check.
    import os
    local_clone = os.environ.get("RULING_LINT_AURA_CLONE")
    if local_clone and Path(local_clone).is_dir():
        try:
            ls = subprocess.run(
                ["git", "ls-remote", "origin", "refs/heads/main"],
                cwd=local_clone, capture_output=True, text=True, check=True, timeout=15,
            ).stdout.strip()
            sha = ls.split()[0] if ls else None
            if sha:
                show = subprocess.run(
                    ["git", "show", f"{sha}:{path}"],
                    cwd=local_clone, capture_output=True, text=True, timeout=15,
                )
                if show.returncode == 0:
                    return True, f"found live on aura origin/main ({sha[:8]}): {path}"
                return False, f"not found on aura origin/main ({sha[:8]}): {path}"
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError, IndexError):
            pass  # fall through to gh api

    # 3. gh api.
    if shutil.which("gh"):
        try:
            r = subprocess.run(
                ["gh", "api", f"repos/ExpertPartners/aura/contents/{path}", "--jq", ".sha"],
                capture_output=True, text=True, timeout=20,
            )
            if r.returncode == 0 and r.stdout.strip():
                return True, f"found via gh api (aura, main): {path}"
            return False, f"gh api reports not found (aura, main): {path}"
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            pass

    return False, f"COULD NOT VERIFY (no --aura-path, no RULING_LINT_AURA_CLONE, no gh): {path}"


def resolve_citation(c: Citation, repo_root: Path, current_repo: str, aura_path: str | None) -> tuple[bool, str]:
    target_repo = c.repo or current_repo
    if target_repo == current_repo:
        return resolve_same_repo(repo_root, c.path)
    if target_repo == "aura":
        return resolve_aura_path(c.path, aura_path)
    return False, f"unknown target repo '{target_repo}' for path {c.path} (no resolver wired)"


# ---------------------------------------------------------------------------
# Check 1: citations resolve, triggers are backed
# ---------------------------------------------------------------------------

def check1(file_rel: str, text: str, repo_root: Path, current_repo: str, aura_path: str | None) -> list[Finding]:
    findings: list[Finding] = []
    citations = extract_citations(text)
    seen: set[tuple[str, str]] = set()
    for c in citations:
        if c.key() in seen:
            continue
        seen.add(c.key())
        ok, msg = resolve_citation(c, repo_root, current_repo, aura_path)
        if not ok:
            findings.append(Finding("citation-resolves", file_rel, c.line_no + 1,
                                     f"ruling citation does not resolve, {msg}"))
    for line_no in find_unbacked_triggers(text, citations):
        findings.append(Finding("citation-resolves", file_rel, line_no + 1,
                                 "authority-claim phrase ('Ruled by Allison' or a variant) "
                                 "with no ruling citation in the same or next 4 lines"))
    return findings


# ---------------------------------------------------------------------------
# Diff parsing (unified diff -> per-file removed/added lines)
# ---------------------------------------------------------------------------

def parse_unified_diff(diff_text: str) -> list[DiffHunk]:
    hunks: dict[str, DiffHunk] = {}
    current_file: str | None = None
    old_line = new_line = 0
    is_new_file = False
    for line in diff_text.splitlines():
        if line.startswith("diff --git"):
            current_file = None
            is_new_file = False
        elif line.startswith("new file mode"):
            is_new_file = True
        elif line.startswith("+++ "):
            path = line[4:].strip()
            if path == "/dev/null":
                current_file = None
                continue
            current_file = path[2:] if path.startswith("b/") else path
            hunks.setdefault(current_file, DiffHunk(current_file, is_new_file=is_new_file))
        elif line.startswith("@@"):
            m = re.match(r"@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@", line)
            if m:
                old_line = int(m.group(1))
                new_line = int(m.group(2))
        elif current_file is not None:
            if line.startswith("-") and not line.startswith("---"):
                hunks[current_file].removed.append((old_line, line[1:]))
                old_line += 1
            elif line.startswith("+") and not line.startswith("+++"):
                hunks[current_file].added.append((new_line, line[1:]))
                new_line += 1
            elif line.startswith(" "):
                old_line += 1
                new_line += 1
    return list(hunks.values())


def get_diff(mode: str, base: str | None, head: str | None, repo_root: Path) -> str:
    if mode == "pre-commit":
        cmd = ["git", "diff", "--cached", "-U3"]
    else:
        cmd = ["git", "diff", "-U3", f"{base}..{head}"]
    return subprocess.run(cmd, cwd=repo_root, capture_output=True, text=True, check=True).stdout


def new_files_in_diff(diff_text: str) -> list[str]:
    return [h.file for h in parse_unified_diff(diff_text) if h.is_new_file]


# ---------------------------------------------------------------------------
# Check 2: supersession names itself. Check 3: disclosure filed.
# ---------------------------------------------------------------------------

def check2_and_3(hunks: list[DiffHunk], all_new_files: list[str], repo_root: Path) -> list[Finding]:
    findings: list[Finding] = []
    any_supersession = False

    for h in hunks:
        removed_citation_lines = [
            (ln, txt) for ln, txt in h.removed
            if extract_citations(txt) or TRIGGER_RE.search(txt)
        ]
        if not removed_citation_lines:
            continue

        added_text = "\n".join(txt for _, txt in h.added)
        names_supersession = bool(SUPERSEDE_RE.search(added_text))
        new_citations = extract_citations(added_text)
        cites_new_authority = len(new_citations) > 0

        if not (names_supersession and cites_new_authority):
            for ln, txt in removed_citation_lines:
                findings.append(Finding(
                    "supersession-names-itself", h.file, ln,
                    "a line carrying a ruling citation or authority claim was removed or "
                    "rewritten without the same file's diff naming what it supersedes "
                    "(a line matching /supersed/) and citing a new resolvable ruling"
                ))
        else:
            any_supersession = True

    if any_supersession:
        disclosure_filed = any(
            "disclosure" in f.lower() or "supersed" in f.lower()
            for f in all_new_files if f.startswith("intake/")
        )
        if not disclosure_filed:
            findings.append(Finding(
                "disclosure-filed", "(commit)", 0,
                "this commit supersedes a ruling of Allison's (check 2 fired) but adds no "
                "new intake/ file whose name marks it as a disclosure of that supersession"
            ))

    return findings


# ---------------------------------------------------------------------------
# Selftest -- deliberate failing and passing fixtures, offline
# ---------------------------------------------------------------------------

FIXTURE_GOOD_CITED_TEXT = (
    "Ruled by Allison 2026-08-07. Some rule text here.\n"
    "ruling of record: aura intake/2026-08-07-ruling-rulings-become-citable-records-and-rules-carry-proven.md\n"
    "<!-- RULED-BY: aura/intake/2026-08-07-ruling-rulings-become-citable-records-and-rules-carry-proven.md date:2026-08-07 -->\n"
)

FIXTURE_BAD_UNBACKED_TEXT = (
    "Ruled by Allison 2026-08-07, this changes everything and nobody can say why.\n"
    "Just a normal paragraph after it, no path anywhere nearby at all, padding padding.\n"
)

FIXTURE_BAD_FAKE_PATH_TEXT = (
    "Re-ruled by Allison 2026-08-07.\n"
    "ruling of record: aura intake/1999-01-01-ruling-does-not-exist-and-never-will.md\n"
)


def selftest() -> int:
    ok = True
    repo_root = Path.cwd()

    print("ruling-provenance-lint: --selftest (offline, fixture data)\n")

    # Check 1a: good text resolves cleanly against real aura main.
    f = check1("fixture.md", FIXTURE_GOOD_CITED_TEXT, repo_root, "expert-partners-skills", None)
    label = "check1/good-citation (expect 0 findings, live network to aura)"
    if f:
        print(f"  FAIL {label}: {[fi.message for fi in f]}")
        ok = False
    else:
        print(f"  PASS {label}")

    # Check 1b: trigger with no citation anywhere nearby -> must fail.
    f = check1("fixture.md", FIXTURE_BAD_UNBACKED_TEXT, repo_root, "expert-partners-skills", None)
    label = "check1/unbacked-trigger (expect >=1 finding)"
    if f:
        print(f"  PASS {label}: {f[0].message}")
    else:
        print(f"  FAIL {label}: expected a finding, got none")
        ok = False

    # Check 1c: citation present but path does not exist -> must fail.
    f = check1("fixture.md", FIXTURE_BAD_FAKE_PATH_TEXT, repo_root, "expert-partners-skills", None)
    label = "check1/nonexistent-path (expect >=1 finding)"
    if f:
        print(f"  PASS {label}: {f[0].message}")
    else:
        print(f"  FAIL {label}: expected a finding, got none")
        ok = False

    # Check 2/3: a synthetic hunk that removes a cited line with no
    # supersession language and no new citation -> must fail check 2.
    bad_hunk = DiffHunk(
        file="plugins/operating-doctrine/skills/pin/SKILL.md",
        removed=[(10, "ruling of record: aura intake/2026-08-07-ruling-rulings-become-citable-records-and-rules-carry-proven.md")],
        added=[(10, "just some unrelated replacement text")],
    )
    f = check2_and_3([bad_hunk], [], repo_root)
    label = "check2/silent-supersession (expect a supersession-names-itself finding)"
    hits = [x for x in f if x.check == "supersession-names-itself"]
    if hits:
        print(f"  PASS {label}: {hits[0].message}")
    else:
        print(f"  FAIL {label}: expected a finding, got none")
        ok = False

    # Check 2 pass case: removal IS accompanied by supersession language and
    # a new (real, resolvable) citation -- must produce zero check-2 findings,
    # but check 3 must fire because no disclosure file was added.
    good_hunk = DiffHunk(
        file="plugins/operating-doctrine/skills/pin/SKILL.md",
        removed=[(10, "ruling of record: aura intake/2026-08-03-ruling-pin-v41-carry-back-names-verified-archive-verdict.md")],
        added=[(10, "This supersedes the prior ruling. "
                    "ruling of record: aura intake/2026-08-07-ruling-rulings-become-citable-records-and-rules-carry-proven.md")],
    )
    f = check2_and_3([good_hunk], [], repo_root)  # no new intake/ file passed
    hits2 = [x for x in f if x.check == "supersession-names-itself"]
    hits3 = [x for x in f if x.check == "disclosure-filed"]
    label = "check2/proper-supersession (expect 0 check-2 findings)"
    if not hits2:
        print(f"  PASS {label}")
    else:
        print(f"  FAIL {label}: {[x.message for x in hits2]}")
        ok = False
    label = "check3/missing-disclosure (expect a disclosure-filed finding)"
    if hits3:
        print(f"  PASS {label}: {hits3[0].message}")
    else:
        print(f"  FAIL {label}: expected a finding, got none")
        ok = False

    # Check 3 pass case: same supersession, but a disclosure file was filed.
    f = check2_and_3([good_hunk], ["intake/2026-08-08-disclosure-pin-supersession.md"], repo_root)
    hits3b = [x for x in f if x.check == "disclosure-filed"]
    label = "check3/disclosure-present (expect 0 disclosure findings)"
    if not hits3b:
        print(f"  PASS {label}")
    else:
        print(f"  FAIL {label}: {[x.message for x in hits3b]}")
        ok = False

    print()
    if ok:
        print("ruling-provenance-lint: selftest clean, all fixtures behaved as expected.")
        return 0
    print("ruling-provenance-lint: selftest FAILED, see above.")
    return 1


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def find_repo_root(start: Path) -> Path:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=start, capture_output=True, text=True, check=True,
        ).stdout.strip()
        return Path(out)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return start


def run_live(mode: str, base: str | None, head: str | None, aura_path: str | None, repo_override: str | None) -> int:
    repo_root = find_repo_root(Path.cwd())
    current_repo = current_repo_name(repo_root, repo_override)
    diff_text = get_diff(mode, base, head, repo_root)
    hunks = parse_unified_diff(diff_text)
    new_files = new_files_in_diff(diff_text)

    findings: list[Finding] = []
    for h in hunks:
        added_text = "\n".join(txt for _, txt in h.added)
        if not added_text.strip():
            continue
        full_path = repo_root / h.file
        if full_path.is_file():
            try:
                if IGNORE_FILE_TOKEN in full_path.read_text(encoding="utf-8"):
                    continue
            except (UnicodeDecodeError, OSError):
                pass
        findings.extend(check1(h.file, added_text, repo_root, current_repo, aura_path))

    findings.extend(check2_and_3(hunks, new_files, repo_root))

    if not findings:
        print(f"ruling-provenance-lint: clean. {len(hunks)} file(s) in diff, 0 breaches.")
        return 0

    print(f"ruling-provenance-lint: {len(findings)} breach(es) across {len({f.file for f in findings})} file(s).\n")
    for f in findings:
        print(f"  ERROR [{f.check}] {f.file}:{f.line}: {f.message}")
    return 1


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Ruling provenance gate.")
    parser.add_argument("files", nargs="*", help="ignored; scope comes from the diff")
    parser.add_argument("--pre-commit", action="store_true")
    parser.add_argument("--ci", nargs=2, metavar=("BASE_SHA", "HEAD_SHA"))
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--aura-path", default=None)
    parser.add_argument("--repo", default=None, help="override current repo name")
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()
    if args.pre_commit:
        return run_live("pre-commit", None, None, args.aura_path, args.repo)
    if args.ci:
        return run_live("ci", args.ci[0], args.ci[1], args.aura_path, args.repo)

    parser.error("one of --pre-commit, --ci BASE HEAD, or --selftest is required")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
