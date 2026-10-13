#!/usr/bin/env python3
"""Read-only exact-rename verification; no metadata or authority inference."""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys


def git(repo: Path, *args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(repo), *args], stderr=subprocess.PIPE)


def verify(repo: Path, before: str, after: str) -> list[tuple[str, str]]:
    # Resolve first, so user-supplied refs cannot become diff options or paths.
    refs = [git(repo, "rev-parse", "--verify", "--end-of-options", f"{r}^{{commit}}").strip().decode()
            for r in (before, after)]
    raw = git(repo, "diff", "--raw", "-z", "--no-abbrev", "--no-ext-diff",
              "--no-textconv", "--find-renames=100%", *refs, "--")
    fields = raw.split(b"\0")
    moves = []
    i = 0
    while i < len(fields) - 1:
        header = fields[i].split()
        if len(header) != 5:
            raise ValueError("unrecognized Git diff record")
        old_mode, new_mode, old_blob, new_blob, status = header
        if (status != b"R100" or old_mode[1:] != new_mode or old_blob != new_blob
                or new_mode not in (b"100644", b"100755")):
            raise ValueError("not move-only: diff includes a non-exact rename, edit, addition, deletion, or mode/type change")
        if i + 2 >= len(fields) - 1:
            raise ValueError("incomplete Git rename record")
        moves.append((fields[i + 1].decode("utf-8", "surrogateescape"),
                      fields[i + 2].decode("utf-8", "surrogateescape")))
        i += 3
    if not moves:
        raise ValueError("no moves: empty diff is not relocation evidence")
    return moves


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("before")
    parser.add_argument("after")
    args = parser.parse_args()
    try:
        moves = verify(args.repo, args.before, args.after)
    except (ValueError, subprocess.CalledProcessError, OSError) as error:
        # Do not print file contents or subprocess buffers from an audited repo.
        detail = str(error) if isinstance(error, ValueError) else "cannot verify Git revisions or repository"
        print(f"FAIL: {detail}", file=sys.stderr)
        return 1
    print(f"PASS: {len(moves)} exact rename(s); bytes and modes unchanged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
