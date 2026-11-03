#!/usr/bin/env python3
"""Fail when a Chat to Code builder workflow drops a required account from its allowlist.

Every contains(fromJSON('[...]'), <...>.login) expression in a builder workflow is an
author allowlist. Each one must list every account in REQUIRED, so a Job: issue opened by
Allison or one of her own room accounts starts the builder with no labeling by hand
(Decision Log 2026-11-02). The allowlists live in the reusable builder. A caller that only
hands off to it (uses: ...factory-builder-reusable.yml) needs none of its own. Any other
builder file with no allowlist fails, and so does a set of builder files with no
allowlist anywhere, so a rewrite of the trigger cannot pass the check by accident.

Run: check_allowlist.py              (checks every builder workflow in .github/workflows)
     check_allowlist.py FILE [FILE]  (checks only the named workflow files)
"""
import glob
import json
import os
import re
import sys

REQUIRED = ("AllisonGaddy", "expertpartners", "expertpartners-ember", "expertpartners-aura")
BUILDER_GLOBS = (
    os.path.join(".github", "workflows", "factory-chat-to-code-loop-builder*.yml"),
    os.path.join(".github", "workflows", "factory-builder*.yml"),
)
ALLOWLIST = re.compile(r"contains\(\s*fromJSON\(\s*'(\[[^']*\])'\s*\)\s*,\s*([\w.\[\]*-]+\.login)\s*\)")
HANDOFF = re.compile(r"^\s*uses:\s*['\"]?\S*factory-builder-reusable\.yml(@\S+)?['\"]?\s*$", re.MULTILINE)


def allowlists(text):
    """Return (line number, accounts, login expression) for each allowlist in text."""
    found = []
    for m in ALLOWLIST.finditer(text):
        line = text.count("\n", 0, m.start()) + 1
        try:
            accounts = json.loads(m.group(1))
        except json.JSONDecodeError:
            accounts = None
        found.append((line, accounts, m.group(2)))
    return found


def problems(path, text):
    """Return one message per failure in this workflow file."""
    lists = allowlists(text)
    if not lists:
        if HANDOFF.search(text):
            return []
        return [f"{path}: no contains(fromJSON('[...]'), ....login) allowlist found"]
    out = []
    for line, accounts, login in lists:
        if not isinstance(accounts, list):
            out.append(f"{path}:{line}: allowlist for {login} is not a JSON list of logins")
            continue
        missing = [a for a in REQUIRED if a not in accounts]
        if missing:
            out.append(f"{path}:{line}: allowlist for {login} is missing {', '.join(missing)}")
    return out


def main(argv):
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    paths = argv or sorted({p for g in BUILDER_GLOBS for p in glob.glob(os.path.join(root, g))})
    if not paths:
        print(f"builder-allowlist: FAIL no builder workflow matches {' or '.join(BUILDER_GLOBS)}")
        return 1
    failures = []
    total = 0
    for path in paths:
        with open(path, encoding="utf-8") as f:
            text = f.read()
        found = problems(path, text)
        failures += found
        count = len(allowlists(text))
        total += count
        if not found:
            how = f"{count} allowlists" if count else "hands off to factory-builder-reusable.yml"
            print(f"builder-allowlist: ok {path} ({how})")
    if not total:
        failures.append("no builder workflow has an allowlist")
    for msg in failures:
        print(f"builder-allowlist: FAIL {msg}")
    if failures:
        print(f"builder-allowlist: every builder allowlist must list {', '.join(REQUIRED)}")
        return 1
    print("builder-allowlist: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
