#!/usr/bin/env python3
"""Compile the existing Ledger K:T disposition export into a private runtime view.

No work is created. Original evidence and implementation/test status remain in
the owning Ledger. Publish the same output to the connector KV and host installer.
"""

import argparse
import json
import re
import sys


def compile_policy(values, source_url, revision):
    items = []
    seen = set()
    for row in values[1:]:
        if not row or not row[0]:
            continue
        if len(row) != 10:
            raise ValueError("Every active disposition needs all ten K:T fields")
        (
            recovery,
            decision,
            implementation,
            owner,
            key,
            tests,
            aliases,
            installed,
            approved,
            evidence,
        ) = row
        if recovery not in ("closed", "open") or key in seen:
            raise ValueError("Invalid recovery state or duplicate capability key")
        if (
            not decision.startswith("https://")
            or installed not in (True, False)
            or approved not in (True, False)
        ):
            raise ValueError("Decision evidence and explicit booleans are required")
        if not isinstance(installed, bool) or not isinstance(approved, bool):
            raise ValueError("Use typed booleans, never inferred build status")
        match = re.fullmatch(r"https://app\.factory\.ai/sessions/([a-zA-Z0-9-]+)", owner)
        if not match:
            raise ValueError("Use the existing owner session link")
        names, proof = json.loads(aliases), json.loads(evidence)
        if not isinstance(names, list) or not isinstance(proof, list) or not tests:
            raise ValueError("Aliases, evidence and independent-test status are required")
        seen.add(key)
        items.append(
            {
                "id": key,
                "aliases": names,
                "sourceRecovery": recovery,
                "decisionUrl": decision,
                "ownerSession": match[1],
                "implementation": implementation,
                "installed": installed,
                "replacementApproved": approved,
                "evidence": proof,
            }
        )
    if not items or not source_url.startswith("https://") or not revision:
        raise ValueError("A complete owning-record export and revision are required")
    return {"version": 1, "source": {"url": source_url, "revision": revision}, "items": items}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--revision", required=True)
    args = parser.parse_args()
    data = json.load(sys.stdin)
    print(json.dumps(compile_policy(data["values"], args.source_url, args.revision), indent=2))


if __name__ == "__main__":
    main()
