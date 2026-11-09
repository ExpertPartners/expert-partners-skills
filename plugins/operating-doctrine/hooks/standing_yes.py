#!/usr/bin/env python3
"""Standing yes, a SessionStart hook that tells every session Allison's brief is the go.

Prints one SessionStart JSON object whose additionalContext carries the rule, so it
reaches every Claude Code session that has the operating-doctrine plugin, on every
machine, without waiting for a skill to load. Python 3.9 or later, standard library only.
"""

import json

RULE = (
    "Allison's standing yes. Her brief is the go. Do not ask her whether to continue, "
    "proceed, start a fresh session, restart, retry, file a job or do it now or later. "
    "Do the next step yourself, including starting a new session or a headless claude -p "
    "run when a fix only loads at startup. Stop and ask only at the Friction Floor in the "
    "operating-doctrine skill, which is spending money, permanent deletion, changing who "
    "holds access beyond what the HQ Rulebook or Decision Log already approve, publishing "
    "or sending outside the company, or a business decision only she can make. Then report "
    "what you did, with links."
)


def main() -> None:
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": RULE}}))


if __name__ == "__main__":
    main()
