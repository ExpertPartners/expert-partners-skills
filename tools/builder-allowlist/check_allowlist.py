#!/usr/bin/env python3
"""Fail when a Chat to Code builder workflow drops a required account from its allowlist.

A builder job gates on the issue author with contains(fromJSON('[...]'),
github.event.issue.user.login). Each of those allowlists must list every account in
REQUIRED, so a Job: issue opened by Allison or one of her own room accounts starts the
builder with no labeling by hand (Decision Log 2026-11-02).

The check reads each workflow as YAML, so comments are never counted. Any job whose if:
names the issue author must gate every event path in that if: with an allowlist: each
path joined by || is either the manual dispatch path or is joined by && to an allowlist.
An author gate in any other form counts as no gate and fails.

A caller that only hands off to the reusable builder in this repo needs no allowlist of
its own. Any other builder file with no gated job fails, and so does a set of builder
files with no gated job anywhere.

Run: check_allowlist.py              (checks every builder workflow in .github/workflows)
     check_allowlist.py FILE [FILE]  (checks only the named workflow files)
Needs PyYAML (python3 -m pip install pyyaml).
"""
import glob
import json
import os
import re
import sys

import yaml

REQUIRED = ("AllisonGaddy", "expertpartners", "expertpartners-ember", "expertpartners-aura")
WORKFLOWS = os.path.join(".github", "workflows")
BUILDER_NAMES = ("factory-chat-to-code-loop-builder*", "factory-builder*")
SUFFIXES = (".yml", ".yaml")
REUSABLE = "factory-builder-reusable.yml"
# Only the reusable builder in this repo counts as a handoff. It is the file this check
# reads from the working tree, and its main copy is the one this check guards on main.
HANDOFFS = (
    f"./.github/workflows/{REUSABLE}",
    f"ExpertPartners/expert-partners-skills/.github/workflows/{REUSABLE}@main",
)
AUTHOR = "github.event.issue.user.login"
# GitHub expression function and property names are case-insensitive.
AUTHOR_REF = re.compile(r"github\s*\.\s*event\s*\.\s*issue\s*\.\s*user\s*(\.\s*login\b|\[\s*'login'\s*\])", re.I)
ALLOWLIST = re.compile(
    r"contains\(\s*fromjson\(\s*'((?:[^']|'')*)'\s*\)\s*,\s*github\.event\.issue\.user\.login\s*\)", re.I
)
DISPATCH = re.compile(r"github\.event_name\s*==\s*'workflow_dispatch'", re.I)


def builder_paths(root):
    """Return every builder workflow under root, with either workflow suffix."""
    found = set()
    for name in BUILDER_NAMES:
        for suffix in SUFFIXES:
            found.update(glob.glob(os.path.join(root, WORKFLOWS, name + suffix)))
    return sorted(found)


def _scan(expr):
    """Yield (index, char, depth) for characters outside single-quoted strings."""
    depth = 0
    quoted = False
    i = 0
    while i < len(expr):
        c = expr[i]
        if quoted:
            if c == "'":
                if expr[i + 1 : i + 2] == "'":
                    i += 1
                else:
                    quoted = False
        elif c == "'":
            quoted = True
        else:
            if c == ")":
                depth -= 1
            yield i, c, depth
            if c == "(":
                depth += 1
        i += 1


def _strip_parens(expr):
    expr = expr.strip()
    while expr.startswith("(") and expr.endswith(")"):
        closes = [i for i, c, d in _scan(expr) if c == ")" and d == 0]
        if closes != [len(expr) - 1]:
            break
        expr = expr[1:-1].strip()
    return expr


def _split(expr, op):
    """Split expr on op where op sits outside every parenthesis and string."""
    parts, start = [], 0
    for i, c, depth in _scan(expr):
        if depth == 0 and c == op[0] and expr[i : i + len(op)] == op:
            parts.append(expr[start:i])
            start = i + len(op)
    parts.append(expr[start:])
    return parts


def gated(expr, found):
    """Return True when every path through expr needs dispatch or an allowlist.

    Appends the account text of every allowlist met to found.
    """
    expr = _strip_parens(expr)
    paths = _split(expr, "||")
    if len(paths) > 1:
        return all([gated(p, found) for p in paths])
    terms = _split(expr, "&&")
    if len(terms) > 1:
        return any([gated(t, found) for t in terms])
    if DISPATCH.fullmatch(expr):
        return True
    m = ALLOWLIST.fullmatch(expr)
    if m:
        found.append(m.group(1).replace("''", "'"))
        return True
    return False


def _expression(value):
    text = " ".join(str(value).split())
    m = re.fullmatch(r"\$\{\{(.*)\}\}", text)
    return m.group(1).strip() if m else text


def check(path, text):
    """Return (problems, number of gated jobs) for one workflow file."""
    try:
        doc = yaml.safe_load(text)
    except yaml.YAMLError as e:
        return [f"{path}: not valid YAML ({e.__class__.__name__})"], 0
    jobs = doc.get("jobs") if isinstance(doc, dict) else None
    if not isinstance(jobs, dict):
        return [f"{path}: no jobs found"], 0
    out = []
    gated_jobs = 0
    handoff = False
    for name, job in jobs.items():
        if not isinstance(job, dict):
            continue
        if str(job.get("uses", "")).strip() in HANDOFFS:
            handoff = True
        cond = job.get("if")
        if cond is None or not AUTHOR_REF.search(str(cond)):
            continue
        gated_jobs += 1
        found = []
        if not gated(_expression(cond), found):
            out.append(f"{path}: job {name}: an event path in its if: is not gated by "
                       f"contains(fromJSON('[...]'), {AUTHOR})")
        for n, raw in enumerate(found, 1):
            try:
                accounts = json.loads(raw)
            except json.JSONDecodeError:
                accounts = None
            if not isinstance(accounts, list) or not all(isinstance(a, str) for a in accounts):
                out.append(f"{path}: job {name}: allowlist {n} is not a JSON list of logins")
                continue
            have = {a.lower() for a in accounts}
            missing = [a for a in REQUIRED if a.lower() not in have]
            if missing:
                out.append(f"{path}: job {name}: allowlist {n} is missing {', '.join(missing)}")
    if not gated_jobs and not handoff:
        out.append(f"{path}: no job gates on {AUTHOR} with an allowlist, and no job hands off "
                   f"to {' or '.join(HANDOFFS)}")
    return out, gated_jobs


def problems(path, text):
    """Return one message per failure in this workflow file."""
    return check(path, text)[0]


def main(argv):
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    paths = argv or builder_paths(root)
    if not paths:
        print(f"builder-allowlist: FAIL no builder workflow matches {', '.join(BUILDER_NAMES)} in {WORKFLOWS}")
        return 1
    failures = []
    total = 0
    for path in paths:
        with open(path, encoding="utf-8") as f:
            found, count = check(path, f.read())
        failures += found
        total += count
        if not found:
            how = f"gated jobs: {count}" if count else f"hands off to {REUSABLE}"
            print(f"builder-allowlist: ok {path} ({how})")
    if not total:
        failures.append("no builder workflow has a job gated by an allowlist")
    for msg in failures:
        print(f"builder-allowlist: FAIL {msg}")
    if failures:
        print(f"builder-allowlist: every builder allowlist must list {', '.join(REQUIRED)}")
        return 1
    print("builder-allowlist: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
