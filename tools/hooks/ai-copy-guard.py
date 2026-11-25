#!/usr/bin/env python3
"""ai-copy-guard: PreToolUse hook that keeps AI copies inside the approved scratch roots.

Blocks, for a shell tool call:
  - `git clone` whose destination is outside an approved scratch root
  - `git worktree add` whose path is outside an approved scratch root
  - a media or archive download (curl, wget, yt-dlp, gdown, rclone, gsutil, aws s3)
    whose local destination is outside an approved scratch root

Approved scratch roots: ~/HQ-AI-Workspace-M4/Scratch, /tmp, /private/tmp, /var/folders
(the per-user TMPDIR). The scratch janitor expires what lands there.

A deliberate new canonical clone under ~/HQ-AI-Workspace-M4/Projects passes when the
command carries EP_CANONICAL_CLONE=1. Reuse the existing canonical clone first.

Reads hook JSON on stdin (tool_name, tool_input.command or .cmd, cwd). Exit 2 with the
reason on stderr blocks; anything else exits 0. Unparseable input exits 0, because the
sibling enforcement hook already fails closed on malformed input.

Kill-switch: touch ~/.claude/ai-copy-guard-off, or AI_COPY_GUARD_OFF=1.
"""

import json
import os
import re
import shlex
import sys

HOME = os.path.expanduser("~")
SHELL_TOOLS = {"Bash", "Execute", "shell", "exec_command", "local_shell", "container.exec"}
MEDIA_EXT = re.compile(
    r"\.(mp4|mov|m4v|mkv|webm|avi|mxf|prores|wav|aif|aiff|mp3|m4a|flac|aac|ogg|"
    r"zip|tar|tgz|gz|7z|dmg|iso|psd|braw|r3d)$",
    re.I,
)
OPTS_WITH_ARG_CLONE = {
    "-b",
    "--branch",
    "-o",
    "--origin",
    "-c",
    "--config",
    "--depth",
    "--reference",
    "--reference-if-able",
    "--separate-git-dir",
    "--filter",
    "-j",
    "--jobs",
    "--template",
    "-u",
    "--upload-pack",
    "--shallow-since",
    "--shallow-exclude",
    "--server-option",
    "--bundle-uri",
}
OPTS_WITH_ARG_WT = {"-b", "-B", "--reason"}


def approved_roots():
    roots = [
        os.path.join(HOME, "HQ-AI-Workspace-M4", "Scratch"),
        "/tmp",
        "/private/tmp",
        "/var/folders",
        "/private/var/folders",
    ]
    extra = os.environ.get("AI_COPY_GUARD_EXTRA_ROOTS", "")
    roots += [os.path.expanduser(p) for p in extra.split(":") if p]
    return [os.path.realpath(r) if os.path.exists(r) else r for r in roots]


def resolve(path, cwd):
    path = os.path.expanduser(os.path.expandvars(path))
    if not os.path.isabs(path):
        path = os.path.join(cwd or HOME, path)
    path = os.path.normpath(path)
    # Resolve the longest existing prefix so symlinked old paths map to their new home.
    head, tail = path, []
    while head and not os.path.exists(head) and head != "/":
        head, t = os.path.split(head)
        tail.insert(0, t)
    return os.path.join(os.path.realpath(head), *tail) if head else path


def inside(path, roots):
    return any(path == r or path.startswith(r.rstrip("/") + "/") for r in roots)


def canonical_projects_ok(path, cmd):
    projects = os.path.realpath(os.path.join(HOME, "HQ-AI-Workspace-M4", "Projects"))
    return "EP_CANONICAL_CLONE=1" in cmd and inside(path, [projects])


def segments(cmd):
    """Split a shell command into simple commands, tracking cd so paths resolve right."""
    parts = re.split(r"\|\||&&|;|\||\n", cmd)
    for p in parts:
        p = p.strip()
        if not p:
            continue
        try:
            yield shlex.split(p, comments=True)
        except ValueError:
            yield p.split()


def strip_env(tokens):
    i = 0
    while i < len(tokens) and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", tokens[i]):
        i += 1
    while i < len(tokens) and tokens[i] in (
        "nice",
        "nohup",
        "time",
        "command",
        "env",
        "sudo",
        "caffeinate",
    ):
        i += 1
        while i < len(tokens) and (
            tokens[i].startswith("-") or re.match(r"^[A-Za-z_]\w*=", tokens[i])
        ):
            i += 1
    return tokens[i:]


def git_dest(tokens, cwd):
    """Return (kind, destination) for git clone / git worktree add, else None."""
    i, gcwd = 1, cwd
    while i < len(tokens) and tokens[i].startswith("-"):
        if tokens[i] == "-C" and i + 1 < len(tokens):
            gcwd = resolve(tokens[i + 1], cwd)
            i += 2
        elif tokens[i] in ("-c", "--git-dir", "--work-tree", "--namespace") and i + 1 < len(tokens):
            i += 2
        else:
            i += 1
    if i >= len(tokens):
        return None
    sub, rest = tokens[i], tokens[i + 1 :]
    if sub == "clone":
        pos, j = [], 0
        while j < len(rest):
            t = rest[j]
            if t == "--":
                pos += rest[j + 1 :]
                break
            if t.startswith("-"):
                if t in OPTS_WITH_ARG_CLONE:
                    j += 1
                j += 1
                continue
            pos.append(t)
            j += 1
        if not pos:
            return None
        if len(pos) >= 2:
            return "git clone", resolve(pos[1], gcwd)
        name = re.sub(r"\.git$", "", pos[0].rstrip("/").split("/")[-1].split(":")[-1])
        return "git clone", resolve(name, gcwd)
    if sub == "worktree" and rest[:1] == ["add"]:
        j, args = 1, rest[1:]
        k = 0
        while k < len(args):
            t = args[k]
            if t.startswith("-"):
                k += 2 if t in OPTS_WITH_ARG_WT else 1
                continue
            return "git worktree add", resolve(t, gcwd)
        return None
    return None


def download_dests(tokens, cwd):
    prog = os.path.basename(tokens[0])
    out = []

    def opt_values(names):
        vals = []
        for k, t in enumerate(tokens):
            for n in names:
                if t == n and k + 1 < len(tokens):
                    vals.append(tokens[k + 1])
                elif n.startswith("--") and t.startswith(n + "="):
                    vals.append(t.split("=", 1)[1])
        return vals

    if prog == "curl":
        for v in opt_values(["-o", "--output"]):
            out.append(v)
        # Bundled short flags such as -sLo FILE or -sLO.
        for k, t in enumerate(tokens[1:], 1):
            if re.match(r"^-[A-Za-z]+$", t) and len(t) > 2:
                if t.endswith("o") and k + 1 < len(tokens):
                    out.append(tokens[k + 1])
        remote_name = any(re.match(r"^-[A-Za-z]*O[A-Za-z]*$", t) for t in tokens[1:])
        if remote_name or "--remote-name" in tokens:
            urls = [t for t in tokens if re.match(r"^https?://", t)]
            out += [u.split("?")[0].rstrip("/").split("/")[-1] for u in urls]
        if "--output-dir" in tokens:
            d = opt_values(["--output-dir"])
            out = [os.path.join(d[0], os.path.basename(o)) for o in out] if d else out
    elif prog == "wget":
        out += opt_values(["-O", "--output-document"])
        d = opt_values(["-P", "--directory-prefix"])
        urls = [t for t in tokens if re.match(r"^https?://", t)]
        if not out:
            base = d[0] if d else "."
            out += [os.path.join(base, u.split("?")[0].rstrip("/").split("/")[-1]) for u in urls]
    elif prog in ("yt-dlp", "youtube-dl"):
        p = opt_values(["-P", "--paths"])
        o = opt_values(["-o", "--output"])
        base = p[0] if p else "."
        # yt-dlp always writes media, so the folder alone decides.
        return [resolve(os.path.join(base, (o[0] if o else "x.mp4")), cwd)], True
    elif prog == "gdown":
        out += opt_values(["-O", "--output"]) or ["."]
        return [resolve(x, cwd) for x in out], True
    elif prog in ("rclone", "gsutil", "aws", "gcloud") and len(tokens) >= 3:
        if prog == "aws" and tokens[1:3] != ["s3", "cp"] and tokens[1:3] != ["s3", "sync"]:
            return [], False
        if prog == "gcloud" and "cp" not in tokens:
            return [], False
        if prog == "rclone" and tokens[1] not in ("copy", "sync", "copyto", "move", "moveto"):
            return [], False
        if prog == "gsutil" and not any(t in ("cp", "rsync", "mv") for t in tokens[1:3]):
            return [], False
        dest = [t for t in tokens[2:] if not t.startswith("-")][-1:]
        if dest and ":" not in dest[0]:
            return [resolve(dest[0], cwd)], True
        return [], False
    return [resolve(x, cwd) for x in out if x and x != "-" and MEDIA_EXT.search(x)], False


def check(cmd, cwd):
    roots = approved_roots()
    cur = cwd or HOME
    for tokens in segments(cmd):
        tokens = strip_env(tokens)
        if not tokens:
            continue
        if tokens[0] == "cd" and len(tokens) > 1:
            cur = resolve(tokens[1], cur)
            continue
        if os.path.basename(tokens[0]) == "git":
            r = git_dest(tokens, cur)
            if r and not inside(r[1], roots) and not canonical_projects_ok(r[1], cmd):
                return (
                    f"{r[0]} into {r[1]} would leave a copy outside the approved scratch root. "
                    f"Put temporary clones and worktrees under ~/HQ-AI-Workspace-M4/Scratch/<date>-<task> "
                    f"(the janitor expires them once they are pushed and idle), or reuse the canonical clone "
                    f"in ~/HQ-AI-Workspace-M4/Projects. A deliberate new canonical clone in Projects passes "
                    f"with EP_CANONICAL_CLONE=1 in the command."
                )
            continue
        dests, _ = download_dests(tokens, cur)
        for d in dests:
            if not inside(d, roots):
                return (
                    f"downloading media or an archive to {d} would leave a heavy copy on this Mac. "
                    f"Heavy media lives on the M2 or in Drive. For a temporary local copy, write it under "
                    f"~/HQ-AI-Workspace-M4/Scratch/<date>-<task> so the janitor expires it."
                )
    return None


def main():
    if (
        os.path.exists(os.path.join(HOME, ".claude", "ai-copy-guard-off"))
        or os.environ.get("AI_COPY_GUARD_OFF") == "1"
    ):
        return 0
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return 0
    if not isinstance(data, dict) or data.get("tool_name") not in SHELL_TOOLS:
        return 0
    ti = data.get("tool_input") or {}
    cmd = ti.get("command") or ti.get("cmd") or ""
    if isinstance(cmd, list):
        cmd = " ".join(shlex.quote(c) for c in cmd)
    if not isinstance(cmd, str) or not cmd:
        return 0
    reason = check(cmd, data.get("cwd") or ti.get("workdir") or os.getcwd())
    if reason:
        print("ai-copy-guard: " + reason, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
