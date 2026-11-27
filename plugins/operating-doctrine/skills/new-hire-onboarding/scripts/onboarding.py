"""Check onboarding observations without credentials, network, or implicit grants."""

import json
import re
import sys


READER_OR_HIGHER = {"reader", "commenter", "writer", "fileOrganizer", "organizer", "owner"}


def person(request, mode):
    email = request.get("principal", "").strip().lower()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise ValueError("A named user email is required")
    folders = request["folders"]
    if len(folders) != 2 or any(not folder["id"] for folder in folders):
        raise ValueError("Provide the verified Core and department folder")
    unique = {}
    for folder in folders:
        if unique.setdefault(folder["id"], folder) != folder:
            raise ValueError("Conflicting observations for the same Drive folder")
    rows = []
    for folder_id, folder in unique.items():
        matches = [
            p
            for p in folder["permissions"]
            if p.get("type") == "user"
            and p.get("email", "").strip().lower() == email
            and p.get("deleted") is False
        ]
        if not (folder.get("verified") is True and folder.get("complete") is True):
            status = "unverified_folder_or_acl"
        elif folder.get("effective_access_verified") is True or any(
            p.get("id") and p.get("role") in READER_OR_HIGHER and not p.get("expires")
            for p in matches
        ):
            status = "present"
        elif matches or any(
            p.get("type") == "user"
            and p.get("email", "").strip().lower() == email
            and p.get("deleted") is not True
            for p in folder["permissions"]
        ):
            status = "ambiguous_permission"
        elif folder.get("can_share") is not True:
            status = "cannot_share"
        else:
            status = "would_create" if mode == "plan" else "create"
        rows.append({"folder": folder_id, "status": status})

    states = {row["status"] for row in rows}
    if states - {"present", "create", "would_create"}:
        for row in rows:
            if row["status"] in {"create", "would_create"}:
                row["status"] = "not_attempted"
        state = "blocked"
    elif mode == "plan" or "create" in states:
        state = "planned"
    else:
        state = "complete" if request.get("first_use") is True else "access_verified"
    return {"state": state, "folders": rows}


def ai(request, mode):
    own, dept = request["own_core"], request["department"]
    cores, extras = dict(request["cores"]), dict(request["extras"])
    if own not in cores or len(cores) < 2:
        raise ValueError("Provide own Core and all currently approved other Cores")
    required = dict(cores)
    department_folder = request["department_folder"]
    if dept in required and required[dept] != department_folder:
        raise ValueError("Department scope conflicts with Core")
    required[dept] = department_folder
    if any(key in required and required[key] != value for key, value in extras.items()):
        raise ValueError("An extra conflicts with approved Core or department")
    expected = required | extras
    if any(not key or not value for key, value in expected.items()):
        raise ValueError("Expected scopes and folder IDs must not be empty")
    observed = request["observed"]
    missing = sorted(expected.keys() - observed.keys())
    unexpected = sorted(observed.keys() - expected.keys())
    misrouted = sorted(
        key for key in expected.keys() & observed.keys() if expected[key] != observed[key]
    )
    complete_checks = ("instructions_verified", "first_use", "recovery_verified")
    access_checks = ("principal_verified", "roots_verified")
    outstanding = [key for key in access_checks + complete_checks if request.get(key) is not True]
    if mode == "plan":
        state = "planned"
    elif missing or unexpected or misrouted or any(key in outstanding for key in access_checks):
        state = "blocked"
    else:
        state = "access_verified" if outstanding else "complete"
    return {
        "state": state,
        "missing": missing,
        "unexpected": unexpected,
        "misrouted": misrouted,
        "outstanding": outstanding,
    }


def main():
    try:
        request = json.load(sys.stdin)
        mode = request["mode"]
        if mode not in {"plan", "apply"}:
            raise ValueError("Unknown mode")
        result = {"person": person, "ai": ai}[request["kind"]](request, mode)
    except (ValueError, AttributeError, KeyError, TypeError):
        print(json.dumps({"state": "blocked", "error": "invalid_onboarding_input"}))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 1 if result["state"] == "blocked" else 0


if __name__ == "__main__":
    sys.exit(main())
