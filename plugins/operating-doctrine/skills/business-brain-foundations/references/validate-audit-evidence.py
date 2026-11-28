#!/usr/bin/env python3
"""Check evidence integrity before an Auditor report is committed.

This checks identities and evidence, not the truth of an AI's content judgment.
Input is a JSON object with duplicateClaims and pieces arrays. Only confirmed
duplicate claims and verified content judgments require complete evidence.
"""

import json
import sys


def validate(evidence):
    errors = []
    for index, finding in enumerate(evidence.get("sharingFindings", [])):
        if finding.get("status") != "editor finding":
            continue
        if not any(
            p.get("type") in ("anyone", "domain")
            and p.get("role") in ("writer", "organizer", "fileOrganizer")
            for p in finding.get("permissions", [])
        ):
            errors.append(
                f"sharingFindings[{index}]: actual broad editor grant required; commenter is not editor"
            )
    for index, claim in enumerate(evidence.get("duplicateClaims", [])):
        if claim.get("status") != "confirmed":
            continue
        label = f"duplicateClaims[{index}]"
        a, b = claim.get("a", {}), claim.get("b", {})
        if not a.get("id") or not b.get("id") or a.get("id") == b.get("id"):
            errors.append(f"{label}: two distinct stable file IDs required")
        for side, item in (("a", a), ("b", b)):
            for field in ("version", "excerpt", "role", "scope"):
                if not str(item.get(field, "")).strip():
                    errors.append(f"{label}.{side}: {field} required")
        if not claim.get("sameRoleReason"):
            errors.append(f"{label}: same-role and scope reasoning required")
        if claim.get("basis") in ("name", "length", "similarity", "count"):
            errors.append(f"{label}: a heuristic is not confirmation")
    for index, piece in enumerate(evidence.get("pieces", [])):
        gaps = piece.get(
            "gaps", piece.get("missingFields", piece.get("missingOrUnresolvedFields", []))
        )
        if piece.get("contentStatus") == "thin" and not gaps:
            errors.append(f"pieces[{index}]: a thin judgment needs explicit field or evidence gaps")
        if gaps:
            rendered = evidence.get("renderedReportText")
            if not isinstance(rendered, str) or any(gap not in rendered for gap in gaps):
                errors.append(f"pieces[{index}]: rendered report omits declared gaps")
        if piece.get("contentStatus") not in ("healthy", "filled", "verified"):
            continue
        label = f"pieces[{index}]"
        if not piece.get("sourceId") or not piece.get("masterId"):
            errors.append(f"{label}: source and live master IDs required")
        checks = piece.get("fieldChecks", [])
        if not checks or any(
            not c.get("field") or not c.get("evidence") or not c.get("assessment") for c in checks
        ):
            errors.append(f"{label}: actual field assessments and evidence required")
        if piece.get("basis") in ("name", "length", "similarity", "count"):
            errors.append(f"{label}: a heuristic is not a content judgment")
    return errors


def main():
    with open(sys.argv[1], encoding="utf-8") as source:
        errors = validate(json.load(source))
    print(json.dumps({"valid": not errors, "errors": errors}))
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
