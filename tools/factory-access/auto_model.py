#!/usr/bin/env python3
"""PATH launcher for new headless sessions; vendor Droid stays untouched.

Install this file as ~/.factory/bin/droid, ahead of ~/.local/bin on PATH.
Existing sessions and non-exec commands pass through unchanged. This covers
ordinary exec launches, not Sessions API or JSON-RPC/ACP session settings.
"""

import os
from pathlib import Path
import sys


VALUE_OPTIONS = {
    "-o", "--output-format", "--input-format", "-f", "--file", "--auto",
    "-s", "--session-id", "--fork", "-m", "--model", "-r", "--reasoning-effort",
    "--spec-model", "--spec-reasoning-effort", "--only-tools", "--add-tools",
    "--remove-tools", "--cwd", "--settings", "--worktree-dir", "--tag",
    "--log-group-id", "--worker-model", "--worker-reasoning-effort",
    "--validator-model", "--validator-reasoning-effort",
    "--append-system-prompt", "--append-system-prompt-file",
}
AUTO_OPTIONS = {
    "-m": "auto", "--model": "auto", "-r": "none",
    "--reasoning-effort": "none", "--spec-model": "auto",
    "--spec-reasoning-effort": "none", "--worker-model": "auto",
    "--worker-reasoning-effort": "none", "--validator-model": "auto",
    "--validator-reasoning-effort": "none",
}
GLOBAL_VALUE_OPTIONS = {
    "--settings", "--cwd", "--auto", "--append-system-prompt",
    "--append-system-prompt-file", "--worktree-dir",
}


def auto_arguments(arguments):
    """Replace incoming pins, preserving option values, prompts and resumes."""
    command = 0
    while command < len(arguments) and arguments[command] != "exec":
        name, equals, _ = arguments[command].partition("=")
        if name in GLOBAL_VALUE_OPTIONS:
            command += 1 if equals else 2
        elif name in {"--use-spec", "--disable-builtin-skills"}:
            command += 1
        else:
            return arguments
    if command >= len(arguments):
        return arguments
    result = arguments[:command] + ["exec", "-m", "auto"]
    index = command + 1
    while index < len(arguments):
        token = arguments[index]
        if token == "--":
            result.extend(arguments[index:])
            break
        name, equals, value = token.partition("=")
        # Commander also accepts -mMODEL, -rEFFORT and -sSESSION.
        if token.startswith(("-m", "-r", "-s")) and not token.startswith("--") and len(token) > 2:
            name, equals, value = token[:2], "=", token[2:]
        if name in VALUE_OPTIONS:
            if not equals:
                if index + 1 == len(arguments):
                    # Keep malformed input malformed for the vendor parser.
                    return arguments
                index += 1
                value = arguments[index]
            if name in {"-s", "--session-id"}:
                return arguments
            if name == "--input-format" and value == "stream-jsonrpc":
                return arguments
            if name == "--output-format" and value in {"stream-jsonrpc", "acp"}:
                return arguments
            result.extend([name, AUTO_OPTIONS.get(name, value)])
        else:
            result.append(token)
        index += 1
    return result


def main():
    executable = Path.home() / ".local" / "bin" / "droid"
    os.execv(str(executable), [str(executable)] + auto_arguments(sys.argv[1:]))


if __name__ == "__main__":
    main()
