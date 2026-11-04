#!/usr/bin/env python3
"""Commit the regenerated skill graph and AI Workforce feed to main without replaying stale output.

The skills-graph workflow's trusted main-only writer runs this in its own disposable CI checkout.
Every attempt starts from the newest fetched main, runs the existing producers on that exact
source tree, and commits only the two generated files. A local generated commit from an older
tree is never rebased or replayed, so a competing commit that also touched the generated files
on main cannot conflict with it.

Results (also written as result=<value> to $GITHUB_OUTPUT when it is set):
  published  exit 0   a fresh generated commit landed on main
  current    exit 0   main already carries what its sources produce; nothing pushed
  failed     exit 1   a producer or verification failed, or the push was refused while main
                      stayed put; never retried, because retrying cannot fix it
  refused    exit 3   the guards below stopped the writer before it touched anything
  deferred   exit 75  main kept moving through every attempt; the workflow's scheduled run
                      retries from the newest main

Guards: GITHUB_REF must equal --expect-ref, and SKILLS_GRAPH_CI_DISPOSABLE_CHECKOUT must name
--repo itself, a primary checkout rather than a linked worktree. The writer force-checks-out and
cleans that checkout, so it refuses to run anywhere else, such as a developer's worktree.

Usage: python3 publish_generated.py --repo DIR --expect-ref refs/heads/main
Tests replace the real producers with --regenerate-cmd and --verify-cmd.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable

GRAPH = "tools/skill-map/skills-graph.json"
FEED = "tools/capability-feed/ai-workforce-feed.json"
GENERATED = (GRAPH, FEED)
PRODUCER_DIRS = ("tools/skill-map", "tools/capability-feed")
DISPOSABLE_ENV = "SKILLS_GRAPH_CI_DISPOSABLE_CHECKOUT"
LOCK_STAMP = ".skills-graph-ci-lock-sha256"

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_REFUSED = 3
EXIT_DEFERRED = 75


class Failure(Exception):
    """A failure that retrying against a newer main cannot fix."""


def log(message: str) -> None:
    print(message, flush=True)


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if check and proc.returncode != 0:
        raise Failure(f"git {' '.join(args)} failed ({proc.returncode}): {proc.stderr.strip()}")
    return proc


def run(cmd: list[str], cwd: Path, what: str) -> None:
    log(f"$ {' '.join(cmd)}")
    proc = subprocess.run(cmd, cwd=str(cwd))
    if proc.returncode != 0:
        raise Failure(f"{what} failed with exit code {proc.returncode}")


def ensure_producer_deps(repo: Path) -> None:
    """npm ci in each producer whenever this tree's lockfile differs from the installed one."""
    for rel in PRODUCER_DIRS:
        lock = repo / rel / "package-lock.json"
        digest = hashlib.sha256(lock.read_bytes()).hexdigest()
        stamp = repo / rel / "node_modules" / LOCK_STAMP
        if stamp.is_file() and stamp.read_text().strip() == digest:
            continue
        run(["npm", "ci", "--no-audit", "--no-fund"], repo / rel, f"npm ci in {rel}")
        stamp.write_text(digest + "\n")


def default_regenerate(repo: Path) -> None:
    ensure_producer_deps(repo)
    run(
        ["node", "extract-skills-graph.mjs", "--eps", str(repo), "--out", str(repo / GRAPH)],
        repo / "tools/skill-map",
        "skill graph extractor",
    )
    run(["node", "tools/capability-feed/generate-feed.mjs", "--write"], repo, "AI Workforce feed generator")


def default_verify(repo: Path) -> None:
    run(["node", "tools/capability-feed/generate-feed.mjs", "--check"], repo, "AI Workforce feed --check")


def command_step(cmd: str, what: str) -> Callable[[Path], None]:
    argv = shlex.split(cmd)
    return lambda repo: run(argv, repo, what)


def guard(repo: Path, expect_ref: str) -> str | None:
    """Return why the writer must not run here, or None when it may."""
    ref = os.environ.get("GITHUB_REF", "")
    if ref != expect_ref:
        return f"the writer runs only on {expect_ref}; this run is on {ref or 'an unset GITHUB_REF'}"
    declared = os.environ.get(DISPOSABLE_ENV, "")
    if not declared or os.path.realpath(declared) != os.path.realpath(repo):
        return f"{DISPOSABLE_ENV} must name {repo}, the disposable CI checkout this writer may reset"
    top = git(repo, "rev-parse", "--show-toplevel", check=False)
    if top.returncode != 0 or os.path.realpath(top.stdout.strip()) != os.path.realpath(repo):
        return f"{repo} is not the top of a git checkout"
    git_dir = git(repo, "rev-parse", "--absolute-git-dir", check=False).stdout.strip()
    common = git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir", check=False).stdout.strip()
    if not git_dir or os.path.realpath(git_dir) != os.path.realpath(common):
        return f"{repo} is a linked worktree, which may belong to another worker"
    return None


def fetch_tip(repo: Path, remote: str, branch: str) -> str:
    tracking = f"refs/remotes/{remote}/{branch}"
    git(repo, "fetch", "--quiet", "--no-tags", remote, f"+refs/heads/{branch}:{tracking}")
    return git(repo, "rev-parse", "--verify", f"{tracking}^{{commit}}").stdout.strip()


def changed_paths(repo: Path) -> list[str]:
    out = git(repo, "status", "--porcelain=v1", "-z", "--untracked-files=all").stdout
    entries = [e for e in out.split("\0") if e]
    return [e[3:] for e in entries if len(e) > 3]


def graph_provenance_only(repo: Path, tip: str) -> bool:
    """True when the only fresh difference is the graph's generatedFrom commit and that recorded
    commit has the same sources as tip, so the committed graph and feed are already current.

    The extractor records the HEAD it read, so every new commit, including this writer's own,
    changes generatedFrom. Without this check a scheduled run on a tip whose sources did not
    change would add a commit that only bumps that sha, every time it runs.
    """
    if git(repo, "diff", "--quiet", "HEAD", "--", FEED, check=False).returncode != 0:
        return False
    shown = git(repo, "show", f"HEAD:{GRAPH}", check=False)
    if shown.returncode != 0:
        return False
    try:
        committed = json.loads(shown.stdout)
        fresh = json.loads((repo / GRAPH).read_text())
    except (OSError, ValueError):
        return False
    if not isinstance(committed, dict) or not isinstance(fresh, dict):
        return False
    recorded = committed.get("generatedFrom")
    source = recorded.get("eps") if isinstance(recorded, dict) else None
    committed.pop("generatedFrom", None)
    fresh.pop("generatedFrom", None)
    if committed != fresh or not isinstance(source, str):
        return False
    if git(repo, "cat-file", "-e", f"{source}^{{commit}}", check=False).returncode != 0:
        return False
    excludes = [f":(exclude){p}" for p in GENERATED]
    return git(repo, "diff", "--quiet", source, tip, "--", ".", *excludes, check=False).returncode == 0


def commit_message(repo: Path) -> str:
    if git(repo, "diff", "--cached", "--quiet", "--", FEED, check=False).returncode == 0:
        return "skills-graph: regenerate from SKILL.md sources [skip ci]"
    return "skills-graph: regenerate graph and AI Workforce feed from canonical sources [skip ci]"


def publish(
    repo: Path,
    remote: str,
    branch: str,
    attempts: int,
    backoff: float,
    regenerate: Callable[[Path], None],
    verify: Callable[[Path], None],
) -> tuple[str, str]:
    """Return (result, commit). Raises Failure for anything a retry cannot fix."""
    for attempt in range(1, attempts + 1):
        tip = fetch_tip(repo, remote, branch)
        log(f"Attempt {attempt} of {attempts}: rebuilding from {branch} at {tip}.")
        # Discard any older generated state; this checkout is disposable (see guard()).
        git(repo, "checkout", "--quiet", "--force", "--detach", tip)
        git(repo, "clean", "-fdq")

        regenerate(repo)
        stray = sorted(p for p in changed_paths(repo) if p not in GENERATED)
        if stray:
            raise Failure("the producers changed files other than the generated graph and feed: " + ", ".join(stray))
        if not changed_paths(repo) or graph_provenance_only(repo, tip):
            git(repo, "checkout", "--quiet", "--force", "--detach", tip)
            log(f"{GRAPH} and {FEED} already match the sources at {tip}; nothing to commit.")
            return "current", tip

        git(repo, "add", "--", *GENERATED)
        git(repo, "commit", "--quiet", "-m", commit_message(repo))
        commit = git(repo, "rev-parse", "HEAD").stdout.strip()
        verify(repo)

        pushed = git(repo, "push", "--quiet", remote, f"HEAD:refs/heads/{branch}", check=False)
        if pushed.returncode == 0:
            log(f"Published {commit} on {branch}.")
            return "published", commit
        now = fetch_tip(repo, remote, branch)
        if now == commit:
            log(f"Published {commit} on {branch} (the push reported an error after it landed).")
            return "published", commit
        if now == tip:
            raise Failure(f"push to {branch} was refused while {branch} stayed at {tip}: {pushed.stderr.strip()}")
        log(f"{branch} moved from {tip} to {now} during attempt {attempt}; rebuilding from the new tip.")
        if attempt < attempts and backoff > 0:
            time.sleep(min(backoff * 2 ** (attempt - 1), 30.0))
    return "deferred", ""


def report(result: str, commit: str, detail: str) -> None:
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as fh:
            fh.write(f"result={result}\ncommit={commit}\n")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(f"### skills-graph writer: {result}\n\n{detail}\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", required=True, help="the disposable CI checkout")
    parser.add_argument("--expect-ref", required=True, help="the only GITHUB_REF the writer runs on")
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--branch", default="main")
    parser.add_argument("--attempts", type=int, default=5)
    parser.add_argument("--backoff", type=float, default=2.0, help="seconds before the second attempt, doubling")
    parser.add_argument("--regenerate-cmd", help="replace the real producers (tests)")
    parser.add_argument("--verify-cmd", help="replace generate-feed.mjs --check (tests)")
    args = parser.parse_args(argv)
    if args.attempts < 1:
        parser.error("--attempts must be at least 1")

    repo = Path(args.repo).resolve()
    refusal = guard(repo, args.expect_ref)
    if refusal:
        print(f"::error title=skills-graph writer refused::{refusal}", flush=True)
        report("refused", "", refusal)
        return EXIT_REFUSED

    regenerate = command_step(args.regenerate_cmd, "regenerate command") if args.regenerate_cmd else default_regenerate
    verify = command_step(args.verify_cmd, "verify command") if args.verify_cmd else default_verify
    try:
        result, commit = publish(repo, args.remote, args.branch, args.attempts, args.backoff, regenerate, verify)
    except Failure as exc:
        print(f"::error title=skills-graph writer failed::{exc}", flush=True)
        report("failed", "", str(exc))
        return EXIT_FAILED

    if result == "deferred":
        detail = (
            f"{args.branch} moved during all {args.attempts} attempts, so nothing was pushed. The scheduled "
            f"skills-graph run rebuilds from the newest {args.branch}, and any later push to {args.branch} "
            "that touches a graph or feed source starts a fresh run."
        )
        print(f"::warning title=skills-graph update deferred::{detail}", flush=True)
        report(result, commit, detail)
        return EXIT_DEFERRED
    report(result, commit, f"{result} at {commit}.")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
