"""Writer tests against temporary Git remotes. Nothing touches the network or this checkout.

Each test builds a bare "remote" whose main plays the real main, a "dev" clone for other
approved writers, and a "ci" clone that stands in for the workflow's disposable checkout.
fake_producer.py replaces the real producers; advance_main.py, installed as the ci clone's
pre-push hook, moves main while the writer's push is in flight.

Run from the repo root: python3 -m unittest discover -s tools/skills-graph-ci/tests -v
"""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
WRITER = HERE.parent / "publish_generated.py"
PRODUCER = HERE / "fake_producer.py"
ADVANCE = HERE / "advance_main.py"
GRAPH = "tools/skill-map/skills-graph.json"
FEED = "tools/capability-feed/ai-workforce-feed.json"
MAIN_REF = "refs/heads/main"

# Isolate every git call from the machine's own config (signing, hooks, default branch).
GIT_ENV = {"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}


def base_env() -> dict[str, str]:
    """The caller's environment without anything from Actions or the writer's own settings,
    and without any token or secret, as a branch run triggered by Dependabot would have."""
    drop = ("GITHUB_", "SKILLS_GRAPH_", "ACTIONS_", "RUNNER_")
    env = {k: v for k, v in os.environ.items() if not k.startswith(drop) and not k.startswith("GIT_")}
    for name in list(env):
        if any(word in name.upper() for word in ("TOKEN", "SECRET", "PRIVATE_KEY", "PASSWORD")):
            del env[name]
    env.update(GIT_ENV)
    return env


def git(repo: Path, *args: str, check: bool = True) -> str:
    proc = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, env=base_env())
    if check and proc.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} failed: {proc.stdout}{proc.stderr}")
    return proc.stdout.strip()


def produce(repo: Path) -> None:
    subprocess.run([sys.executable, str(PRODUCER)], cwd=repo, check=True, env=base_env())


def expected_generated(tree_root: Path, head: str) -> tuple[str, str]:
    sys.path.insert(0, str(HERE))
    try:
        import fake_producer
    finally:
        sys.path.pop(0)
    return fake_producer.render(tree_root, head)


class Fixture:
    def __init__(self, tmp: Path) -> None:
        self.tmp = tmp
        self.remote = tmp / "remote.git"
        self.dev = tmp / "dev"
        self.ci = tmp / "ci"
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(self.remote)], check=True, env=base_env())
        self.clone(self.dev, "Fixture Dev", "dev@example.invalid")
        self.write(self.dev, {"src/a.txt": "alpha\n"})
        self.commit(self.dev, "seed sources")
        produce(self.dev)
        self.commit(self.dev, "seed generated files")
        git(self.dev, "push", "-q", "origin", "HEAD:main")

    def clone(self, path: Path, name: str, email: str) -> None:
        subprocess.run(["git", "clone", "-q", str(self.remote), str(path)], check=True, env=base_env(), capture_output=True)
        git(path, "config", "user.name", name)
        git(path, "config", "user.email", email)

    def clone_ci(self) -> None:
        self.clone(self.ci, "skills-graph-bot", "actions@users.noreply.github.com")

    @staticmethod
    def write(repo: Path, files: dict[str, str]) -> None:
        for rel, text in files.items():
            (repo / rel).parent.mkdir(parents=True, exist_ok=True)
            (repo / rel).write_text(text)

    @staticmethod
    def commit(repo: Path, message: str) -> str:
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "-m", message)
        return git(repo, "rev-parse", "HEAD")

    def dev_push(self, files: dict[str, str], message: str, regenerate: bool = False) -> str:
        git(self.dev, "fetch", "-q", "origin", "main")
        git(self.dev, "reset", "-q", "--hard", "origin/main")
        self.write(self.dev, files)
        self.commit(self.dev, message)
        if regenerate:
            produce(self.dev)
            self.commit(self.dev, message + " (generated)")
        git(self.dev, "push", "-q", "origin", "HEAD:main")
        return git(self.dev, "rev-parse", "HEAD")

    def remote_tip(self) -> str:
        return git(self.remote, "rev-parse", "refs/heads/main")

    def install_race(self, plan: list[dict[str, object]], forever: bool = False) -> Path:
        racer = self.tmp / "racer"
        self.clone(racer, "Other Writer", "other@example.invalid")
        state = self.tmp / "race-state.json"
        state.write_text(json.dumps({"dev": str(racer), "producer": str(PRODUCER), "count": 0, "plan": plan, "forever": forever}))
        hooks = self.tmp / "hooks"
        hooks.mkdir(exist_ok=True)
        hook = hooks / "pre-push"
        hook.write_text(f"#!/bin/sh\nexec {shlex.quote(sys.executable)} {shlex.quote(str(ADVANCE))} {shlex.quote(str(state))}\n")
        hook.chmod(0o755)
        git(self.ci, "config", "core.hooksPath", str(hooks))
        return state

    def run_writer(self, *extra: str, ref: str = MAIN_REF, disposable: Path | None = None,
                   attempts: int = 5) -> tuple[int, str, dict[str, str]]:
        out_file = self.tmp / "github-output"
        out_file.write_text("")
        env = base_env()
        env["GITHUB_REF"] = ref
        env["GITHUB_OUTPUT"] = str(out_file)
        env["SKILLS_GRAPH_CI_DISPOSABLE_CHECKOUT"] = str(disposable if disposable is not None else self.ci)
        cmd = [
            sys.executable, str(WRITER), "--repo", str(self.ci), "--expect-ref", MAIN_REF,
            "--attempts", str(attempts), "--backoff", "0",
            "--regenerate-cmd", f"{shlex.quote(sys.executable)} {shlex.quote(str(PRODUCER))}",
            "--verify-cmd", f"{shlex.quote(sys.executable)} {shlex.quote(str(PRODUCER))} --check",
            *extra,
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, env=env)
        outputs = dict(line.split("=", 1) for line in out_file.read_text().splitlines() if "=" in line)
        return proc.returncode, proc.stdout + proc.stderr, outputs

    def assert_tip_is_fresh_generation(self, case: unittest.TestCase) -> str:
        """The tip is one bot commit that changes only the generated files, and they are exactly
        what the producer makes from its parent's source tree."""
        tip = self.remote_tip()
        parent = git(self.remote, "rev-parse", f"{tip}^")
        changed = git(self.remote, "diff", "--name-only", parent, tip).splitlines()
        case.assertEqual(sorted(changed), sorted([GRAPH, FEED]))
        case.assertEqual(git(self.remote, "log", "-1", "--format=%an", tip), "skills-graph-bot")
        scratch = self.tmp / f"scratch-{parent[:8]}"
        subprocess.run(["git", "clone", "-q", str(self.remote), str(scratch)], check=True, env=base_env(), capture_output=True)
        git(scratch, "checkout", "-q", "--detach", parent)
        graph, feed = expected_generated(scratch, parent)
        case.assertEqual(git(self.remote, "show", f"{tip}:{GRAPH}") + "\n", graph)
        case.assertEqual(git(self.remote, "show", f"{tip}:{FEED}") + "\n", feed)
        for rel in (GRAPH, FEED):
            case.assertNotIn("<<<<<<<", git(self.remote, "show", f"{tip}:{rel}"))
        return tip


class WriterTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="skills-graph-ci-")
        self.addCleanup(self._tmp.cleanup)
        self.fx = Fixture(Path(self._tmp.name))

    def test_competing_generated_commit_and_main_moving_during_retry(self) -> None:
        fx = self.fx
        # The run's trigger: a source change merged to main without its generated files.
        fx.dev_push({"src/b.txt": "bravo\n"}, "merge: add b")
        fx.clone_ci()
        # The old writer's obsolete state: a generated commit built from the trigger tree.
        produce(fx.ci)
        fx.commit(fx.ci, "skills-graph: obsolete generated commit [skip ci]")
        # Meanwhile another approved writer lands a commit touching the generated files,
        # then an unrelated source change.
        fx.dev_push({"src/b.txt": "bravo, revised\n"}, "merge: revise b", regenerate=True)
        fx.dev_push({"src/c.txt": "charlie\n"}, "merge: add c")

        # The old pull --rebase recovery really conflicts on this history.
        old = fx.tmp / "old-writer"
        shutil.copytree(fx.ci, old, symlinks=True)
        proc = subprocess.run(["git", "-C", str(old), "pull", "--rebase", "origin", "main"],
                              capture_output=True, text=True, env=base_env())
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("CONFLICT", proc.stdout + proc.stderr)

        # Main moves during the first push (another generated commit, then a source change)
        # and again during the retry's push.
        state = fx.install_race([
            {"files": {"src/d.txt": "delta\n"}, "regenerate": True, "after": {"src/a.txt": "alpha, revised\n"}},
            {"files": {"src/e.txt": "echo\n"}, "regenerate": False},
        ])
        rc, out, outputs = fx.run_writer()
        self.assertEqual(rc, 0, out)
        self.assertEqual(outputs.get("result"), "published", out)
        self.assertEqual(json.loads(state.read_text())["count"], 3, out)
        self.assertEqual(out.count("rebuilding from the new tip"), 2, out)

        tip = fx.assert_tip_is_fresh_generation(self)
        self.assertEqual(outputs.get("commit"), tip)
        tree = {name: git(fx.remote, "show", f"{tip}:src/{name}") for name in ("a.txt", "b.txt", "c.txt", "d.txt", "e.txt")}
        self.assertEqual(tree, {"a.txt": "alpha, revised", "b.txt": "bravo, revised", "c.txt": "charlie", "d.txt": "delta", "e.txt": "echo"})
        # The obsolete local generated commit never reached main.
        self.assertNotIn("obsolete generated commit", git(fx.remote, "log", "--format=%s", "main"))
        self.assertEqual(git(fx.ci, "rev-parse", "HEAD"), tip)
        self.assertEqual(git(fx.ci, "status", "--porcelain"), "")

    def test_genuine_validation_failure_stays_a_failure(self) -> None:
        fx = self.fx
        bad = fx.dev_push({"src/bad.txt": "INVALID reference\n"}, "merge: broken source")
        fx.clone_ci()
        state = fx.install_race([], forever=True)
        rc, out, outputs = fx.run_writer()
        self.assertEqual(rc, 1, out)
        self.assertEqual(outputs.get("result"), "failed", out)
        self.assertIn("regenerate command failed with exit code 2", out)
        self.assertEqual(fx.remote_tip(), bad)
        self.assertEqual(json.loads(state.read_text())["count"], 0, "a failed validation must never push")

    def test_failed_verification_is_not_pushed(self) -> None:
        fx = self.fx
        before = fx.dev_push({"src/b.txt": "bravo\n"}, "merge: add b")
        fx.clone_ci()
        rc, out, outputs = fx.run_writer("--verify-cmd", "false")
        self.assertEqual(rc, 1, out)
        self.assertEqual(outputs.get("result"), "failed")
        self.assertEqual(fx.remote_tip(), before)

    def test_refused_push_while_main_stays_put_is_a_failure_not_a_retry(self) -> None:
        fx = self.fx
        before = fx.dev_push({"src/b.txt": "bravo\n"}, "merge: add b")
        hook = fx.remote / "hooks" / "pre-receive"
        hook.write_text("#!/bin/sh\necho 'rule violation' >&2\nexit 1\n")
        hook.chmod(0o755)
        fx.clone_ci()
        rc, out, outputs = fx.run_writer()
        self.assertEqual(rc, 1, out)
        self.assertEqual(outputs.get("result"), "failed")
        self.assertIn("was refused while main stayed at", out)
        self.assertEqual(out.count("Attempt "), 1, out)
        self.assertEqual(fx.remote_tip(), before)

    def test_exhausted_budget_defers_then_a_later_run_publishes(self) -> None:
        fx = self.fx
        fx.dev_push({"src/b.txt": "bravo\n"}, "merge: add b")
        fx.clone_ci()
        state = fx.install_race([], forever=True)
        rc, out, outputs = fx.run_writer(attempts=3)
        self.assertEqual(rc, 75, out)
        self.assertEqual(outputs.get("result"), "deferred")
        self.assertIn("::warning title=skills-graph update deferred::", out)
        self.assertEqual(json.loads(state.read_text())["count"], 3, "bounded: one push per attempt, then stop")
        self.assertNotEqual(git(fx.remote, "log", "-1", "--format=%an", "main"), "skills-graph-bot")

        # The scheduled run: main has stopped moving, so the next attempt lands.
        git(fx.ci, "config", "--unset", "core.hooksPath")
        rc, out, outputs = fx.run_writer()
        self.assertEqual(rc, 0, out)
        self.assertEqual(outputs.get("result"), "published")
        fx.assert_tip_is_fresh_generation(self)

    def test_current_main_commits_nothing(self) -> None:
        fx = self.fx
        fx.dev_push({"src/b.txt": "bravo\n"}, "merge: add b")
        fx.clone_ci()
        rc, out, _ = fx.run_writer()
        self.assertEqual(rc, 0, out)
        published = fx.remote_tip()
        # A later run (scheduled, or dispatched) on the bot's own commit: only generatedFrom
        # would change, and the sources it names are identical, so nothing is committed.
        rc, out, outputs = fx.run_writer()
        self.assertEqual(rc, 0, out)
        self.assertEqual(outputs.get("result"), "current", out)
        self.assertEqual(fx.remote_tip(), published)
        # A source change after that is stale again and publishes.
        fx.dev_push({"src/c.txt": "charlie\n"}, "merge: add c")
        rc, out, outputs = fx.run_writer()
        self.assertEqual(outputs.get("result"), "published", out)
        fx.assert_tip_is_fresh_generation(self)

    def test_producer_touching_other_files_fails(self) -> None:
        fx = self.fx
        before = fx.dev_push({"src/b.txt": "bravo\n"}, "merge: add b")
        fx.clone_ci()
        script = fx.tmp / "stray.py"
        script.write_text("open('src/a.txt', 'a').write('tampered\\n')\n")
        rc, out, outputs = fx.run_writer("--regenerate-cmd", f"{shlex.quote(sys.executable)} {shlex.quote(str(script))}")
        self.assertEqual(rc, 1, out)
        self.assertIn("src/a.txt", out)
        self.assertEqual(fx.remote_tip(), before)


class GuardTest(unittest.TestCase):
    """The writer touches nothing unless it is on main and in its own disposable checkout."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="skills-graph-ci-guard-")
        self.addCleanup(self._tmp.cleanup)
        self.fx = Fixture(Path(self._tmp.name))
        self.fx.dev_push({"src/b.txt": "bravo\n"}, "merge: add b")
        self.fx.clone_ci()
        # Uncommitted work that a reset would destroy.
        (self.fx.ci / "src" / "a.txt").write_text("someone's unsaved edit\n")
        self.before = self.fx.remote_tip()

    def assert_untouched(self, rc: int, out: str, outputs: dict[str, str]) -> None:
        self.assertEqual(rc, 3, out)
        self.assertEqual(outputs.get("result"), "refused")
        self.assertEqual((self.fx.ci / "src" / "a.txt").read_text(), "someone's unsaved edit\n")
        self.assertEqual(self.fx.remote_tip(), self.before)
        self.assertFalse((self.fx.ci / GRAPH).read_text().count("bravo"), "the producers never ran")

    def test_secret_free_branch_run_cannot_enter_the_writer(self) -> None:
        for ref in ("refs/heads/dependabot/npm_and_yarn/tools/capability-feed/zod-4", "refs/heads/job/1-x", ""):
            with self.subTest(ref=ref):
                rc, out, outputs = self.fx.run_writer(ref=ref)
                self.assert_untouched(rc, out, outputs)
                self.assertIn("the writer runs only on refs/heads/main", out)

    def test_other_checkout_is_never_reset(self) -> None:
        rc, out, outputs = self.fx.run_writer(disposable=self.fx.tmp / "somewhere-else")
        self.assert_untouched(rc, out, outputs)
        self.assertIn("SKILLS_GRAPH_CI_DISPOSABLE_CHECKOUT must name", out)

    def test_linked_worktree_is_never_reset(self) -> None:
        fx = self.fx
        linked = fx.tmp / "linked"
        git(fx.ci, "worktree", "add", "-q", "--detach", str(linked))
        (linked / "src" / "a.txt").write_text("another worker's edit\n")
        original_ci = fx.ci
        fx.ci = linked
        try:
            rc, out, outputs = fx.run_writer()
        finally:
            fx.ci = original_ci
        self.assertEqual(rc, 3, out)
        self.assertIn("linked worktree", out)
        self.assertEqual((linked / "src" / "a.txt").read_text(), "another worker's edit\n")
        self.assertEqual(fx.remote_tip(), self.before)


if __name__ == "__main__":
    unittest.main()
