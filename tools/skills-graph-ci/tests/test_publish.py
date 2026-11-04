"""Offline proofs for tools/skills-graph-ci/publish.sh and the skills-graph workflow.

Every scenario runs against throwaway git repositories under a temporary directory: a
bare repository stands in for GitHub, one clone is the workflow's disposable checkout,
and another clone lands competing commits on main. The fixture producer is a
deterministic function of the committed sources, like the real extractor and feed
generator, and it can land a competing main commit while it runs, which is the moment a
real run loses the push race.

Run: python3 -m unittest discover -s tools/skills-graph-ci/tests -p 'test_*.py' -v
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOL = HERE.parent
REPO = TOOL.parent.parent
WORKFLOW = REPO / ".github" / "workflows" / "skills-graph.yml"
GRAPH = "tools/skill-map/skills-graph.json"
FEED = "tools/capability-feed/ai-workforce-feed.json"
MAIN_IF = "github.ref == 'refs/heads/main'"

PRODUCER = textwrap.dedent(
    """\
    import hashlib, json, os, subprocess, sys
    from pathlib import Path

    state = Path(os.environ["FIXTURE_STATE"])
    calls = state / "calls"
    n = int(calls.read_text()) + 1 if calls.exists() else 1
    calls.write_text(str(n))

    root = Path.cwd()
    sources = {p.relative_to(root).as_posix(): p.read_text() for p in sorted((root / "src").glob("*.txt"))}
    if any("INVALID" in text for text in sources.values()):
        print("fixture producer: invalid source", file=sys.stderr)
        sys.exit(2)
    head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    graph = {"generatedFrom": {"eps": head}, "nodes": sorted(sources)}
    feed = {"records": [{"id": k, "sha": hashlib.sha256(v.encode()).hexdigest()} for k, v in sorted(sources.items())]}
    (root / "tools/skill-map/skills-graph.json").write_text(json.dumps(graph, indent=2) + "\\n")
    (root / "tools/capability-feed/ai-workforce-feed.json").write_text(json.dumps(feed, indent=2) + "\\n")
    for extra in json.loads(os.environ.get("FIXTURE_TOUCH", "[]")):
        (root / extra).write_text("touched by producer\\n")

    race = state / f"race-{n}.json"
    if race.exists():
        subprocess.run([sys.executable, str(state / "land.py"), str(race)], check=True)
    """
)

LAND = textwrap.dedent(
    """\
    import json, subprocess, sys
    from pathlib import Path

    spec = json.loads(Path(sys.argv[1]).read_text())
    dev = Path(spec["dev"])
    def git(*a):
        subprocess.run(["git", "-C", str(dev), *a], check=True, capture_output=True)
    git("pull", "--quiet", "--ff-only", "origin", "main")
    for name, text in spec["files"].items():
        (dev / name).parent.mkdir(parents=True, exist_ok=True)
        (dev / name).write_text(text)
    git("add", "-A")
    git("commit", "--quiet", "-m", spec["message"])
    git("push", "--quiet", "origin", "HEAD:main")
    """
)


def expected_outputs(sources, head="seed"):
    """What the fixture producer writes; like the real extractor it stamps the commit."""
    graph = {"generatedFrom": {"eps": head}, "nodes": sorted(sources)}
    feed = {"records": [{"id": k, "sha": hashlib.sha256(v.encode()).hexdigest()} for k, v in sorted(sources.items())]}
    return json.dumps(graph, indent=2) + "\n", json.dumps(feed, indent=2) + "\n"


def run(*args, cwd=None, env=None, check=True):
    proc = subprocess.run(list(args), cwd=cwd, env=env, capture_output=True, text=True)
    if check and proc.returncode != 0:
        raise AssertionError(f"{args} failed ({proc.returncode}):\n{proc.stdout}\n{proc.stderr}")
    return proc


def git(repo, *args, check=True):
    return run("git", "-C", str(repo), *args, check=check)


class Fixture:
    """A bare origin, a dev clone for competing commits, and the disposable CI checkout."""

    def __init__(self, tmp: Path):
        self.tmp = tmp
        self.origin = tmp / "origin.git"
        self.dev = tmp / "dev"
        self.ci = tmp / "ci"
        self.state = tmp / "state"
        self.tool = tmp / "tool"
        self.state.mkdir()
        shutil.copytree(TOOL, self.tool, ignore=shutil.ignore_patterns("tests", "__pycache__"))
        (self.state / "land.py").write_text(LAND)
        self.producer = tmp / "producer.sh"
        (tmp / "producer.py").write_text(PRODUCER)
        self.producer.write_text(f'#!/usr/bin/env bash\nexec "{sys.executable}" "{tmp / "producer.py"}"\n')
        self.producer.chmod(0o755)

        run("git", "init", "--quiet", "--bare", "--initial-branch=main", str(self.origin))
        run("git", "clone", "--quiet", str(self.origin), str(self.dev))
        self.identify(self.dev)
        sources = {"src/a.txt": "alpha\n"}
        graph, feed = expected_outputs(sources)
        self.write(self.dev, {**sources, GRAPH: graph, FEED: feed, "README.md": "fixture\n"})
        git(self.dev, "add", "-A")
        git(self.dev, "commit", "--quiet", "-m", "seed")
        git(self.dev, "push", "--quiet", "origin", "HEAD:main")
        run("git", "clone", "--quiet", str(self.origin), str(self.ci))
        self.identify(self.ci)

    @staticmethod
    def identify(repo):
        # Scratch repositories only; a CI runner has no global git identity.
        git(repo, "config", "user.name", "fixture")
        git(repo, "config", "user.email", "fixture@example.invalid")

    @staticmethod
    def write(repo, files):
        for name, text in files.items():
            path = Path(repo) / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)

    def land(self, files, message):
        """Land a commit on main from the dev clone, as another approved writer would."""
        spec = self.state / "now.json"
        spec.write_text(json.dumps({"dev": str(self.dev), "files": files, "message": message}))
        run(sys.executable, str(self.state / "land.py"), str(spec))

    def race(self, call, files, message):
        """Land a commit on main while the producer runs for the call-th time."""
        spec = {"dev": str(self.dev), "files": files, "message": message}
        (self.state / f"race-{call}.json").write_text(json.dumps(spec))

    def env(self, **overrides):
        env = {k: v for k, v in os.environ.items() if not k.startswith(("SKILLS_GRAPH_", "GITHUB_"))}
        env.update(
            SKILLS_GRAPH_PUBLISH_REF="refs/heads/main",
            SKILLS_GRAPH_PUSH_TOKEN="fixture-token",
            SKILLS_GRAPH_CI_CHECKOUT=str(self.ci),
            FIXTURE_STATE=str(self.state),
        )
        for key, value in overrides.items():
            if value is None:
                env.pop(key, None)
            else:
                env[key] = value
        return env

    def publish(self, *extra, script=None, checkout=None, regenerate=None, **env):
        return run(
            "bash", str(script or self.tool / "publish.sh"),
            "--checkout", str(checkout or self.ci),
            "--regenerate", str(regenerate or self.producer),
            *extra, env=self.env(**env), check=False,
        )

    def producer_calls(self):
        calls = self.state / "calls"
        return int(calls.read_text()) if calls.exists() else 0

    def main_tip(self):
        return git(self.origin, "rev-parse", "main").stdout.strip()

    def main_file(self, name):
        return git(self.origin, "show", f"main:{name}").stdout

    def main_sources(self):
        names = git(self.origin, "ls-tree", "-r", "--name-only", "main", "src/").stdout.split()
        return {n: self.main_file(n) for n in names}


class Base(unittest.TestCase):
    def setUp(self):
        if shutil.which("git") is None:
            self.skipTest("needs git")
        self._tmp = tempfile.TemporaryDirectory()
        self.fx = Fixture(Path(self._tmp.name).resolve())

    def tearDown(self):
        self._tmp.cleanup()

    def assert_fresh_generated_commit(self, parent):
        """main is parent plus exactly one bot commit carrying freshly generated files."""
        fx = self.fx
        self.assertEqual(git(fx.origin, "rev-parse", "main~1").stdout.strip(), parent)
        changed = git(fx.origin, "diff", "--name-only", "main~1", "main").stdout.split()
        self.assertTrue(changed)
        self.assertLessEqual(set(changed), {GRAPH, FEED})
        graph, feed = expected_outputs(fx.main_sources(), head=parent)
        self.assertEqual(fx.main_file(GRAPH), graph)
        self.assertEqual(fx.main_file(FEED), feed)
        subject = git(fx.origin, "log", "-1", "--format=%s", "main").stdout.strip()
        self.assertTrue(subject.endswith("[skip ci]"), subject)
        for name in (GRAPH, FEED):
            self.assertNotIn("<<<<<<<", fx.main_file(name))


class MainMovement(Base):
    def stale_ci_commit(self):
        """The CI checkout's validation steps already rewrote the generated files from the
        sources it was triggered for, the state the old step committed and rebased."""
        fx = self.fx
        fx.write(fx.ci, {"src/c.txt": "from the triggering push\n"})
        git(fx.ci, "add", "-A")
        git(fx.ci, "commit", "--quiet", "-m", "triggering source change")
        git(fx.ci, "push", "--quiet", "origin", "HEAD:main")
        graph, feed = expected_outputs({"src/a.txt": "alpha\n", "src/c.txt": "from the triggering push\n"}, git(fx.ci, "rev-parse", "HEAD").stdout.strip())
        fx.write(fx.ci, {GRAPH: graph, FEED: feed})
        git(fx.dev, "pull", "--quiet", "--ff-only", "origin", "main")

    def land_competitor_with_generated_files(self):
        """Another approved writer lands a source change plus generated files it built from
        a tree without the triggering change, so both generated files differ from ours."""
        fx = self.fx
        graph, feed = expected_outputs({"src/a.txt": "alpha\n", "src/b.txt": "competitor\n"})
        fx.land({"src/b.txt": "competitor\n", GRAPH: graph, FEED: feed}, "competing source change")

    def test_old_rebase_replay_conflicts(self):
        """Root cause: replaying a generated-only commit onto a main whose generated files
        changed conflicts, the failure in run 41747143343."""
        fx = self.fx
        self.stale_ci_commit()
        git(fx.ci, "add", GRAPH, FEED)
        git(fx.ci, "commit", "--quiet", "-m", "generated")
        self.land_competitor_with_generated_files()
        self.assertNotEqual(git(fx.ci, "push", "--quiet", "origin", "HEAD:main", check=False).returncode, 0)
        rebase = git(fx.ci, "pull", "--rebase", "origin", "main", check=False)
        self.assertNotEqual(rebase.returncode, 0)
        self.assertIn("CONFLICT", rebase.stdout + rebase.stderr)

    def test_competing_commit_touching_generated_files(self):
        fx = self.fx
        self.stale_ci_commit()
        self.land_competitor_with_generated_files()
        competitor = fx.main_tip()
        result = fx.publish()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assert_fresh_generated_commit(competitor)
        self.assertEqual(fx.main_file("src/b.txt"), "competitor\n")
        self.assertEqual(fx.main_file("src/c.txt"), "from the triggering push\n")
        self.assertEqual(fx.producer_calls(), 1)

    def test_main_moves_again_during_retry(self):
        fx = self.fx
        self.stale_ci_commit()
        self.land_competitor_with_generated_files()
        sources_now = fx.main_sources()
        graph, feed = expected_outputs({**sources_now, "src/d.txt": "first race\n"})
        fx.race(1, {"src/d.txt": "first race\n", GRAPH: graph, FEED: feed}, "lands during attempt 1")
        fx.race(2, {"src/e.txt": "second race\n"}, "lands during attempt 2")
        result = fx.publish()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(fx.producer_calls(), 3)
        self.assertEqual(result.stdout.count("rebuilding the graph and feed"), 3)
        second_race = git(fx.dev, "rev-parse", "HEAD").stdout.strip()
        self.assert_fresh_generated_commit(second_race)
        for name, text in {"src/b.txt": "competitor\n", "src/d.txt": "first race\n", "src/e.txt": "second race\n"}.items():
            self.assertEqual(fx.main_file(name), text)
        self.assertEqual(git(fx.origin, "rev-list", "--count", "main").stdout.strip(), "6")

    def test_budget_exhausted_is_loud_and_bounded(self):
        fx = self.fx
        fx.land({"src/b.txt": "beta\n"}, "source change that needs publishing")
        for call in (1, 2, 3):
            fx.race(call, {f"src/r{call}.txt": f"race {call}\n"}, f"race {call}")
        result = fx.publish("--attempts", "3")
        self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
        self.assertEqual(fx.producer_calls(), 3)
        self.assertIn("hourly scheduled run", result.stderr)
        self.assertEqual(git(fx.origin, "log", "-1", "--format=%s", "main").stdout.strip(), "race 3")

    def test_push_run_keeps_committing_the_fresh_stamp(self):
        fx = self.fx
        before = fx.main_tip()
        result = fx.publish()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assert_fresh_generated_commit(before)
        self.assertEqual(git(fx.origin, "diff", "--name-only", "main~1", "main").stdout.split(), [GRAPH])

    def test_scheduled_reconcile_of_an_in_sync_main_commits_nothing(self):
        fx = self.fx
        self.assertEqual(fx.publish().returncode, 0)
        before = fx.main_tip()
        result = fx.publish("--reconcile")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("nothing to commit", result.stdout)
        self.assertEqual(fx.main_tip(), before)
        self.assertEqual(git(fx.ci, "status", "--porcelain").stdout, "")

    def test_scheduled_reconcile_repairs_a_stale_feed(self):
        fx = self.fx
        self.assertEqual(fx.publish().returncode, 0)
        fx.land({"src/missed.txt": "landed without a skills-graph run\n"}, "unwatched move")
        stale = fx.main_tip()
        result = fx.publish("--reconcile")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assert_fresh_generated_commit(stale)

    def test_move_while_already_current_is_rebuilt(self):
        fx = self.fx
        fx.race(1, {"src/late.txt": "lands while the first attempt finds nothing to do\n"}, "late source change")
        result = fx.publish()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(fx.producer_calls(), 2)
        self.assert_fresh_generated_commit(git(fx.dev, "rev-parse", "HEAD").stdout.strip())

    def test_rejection_without_movement_is_not_retried(self):
        fx = self.fx
        hook = fx.origin / "hooks" / "pre-receive"
        hook.write_text("#!/bin/sh\necho 'rejected by rule' >&2\nexit 1\n")
        hook.chmod(0o755)
        fx.write(fx.ci, {"src/z.txt": "needs a regenerate\n"})
        git(fx.ci, "add", "-A")
        git(fx.ci, "commit", "--quiet", "-m", "local only")
        hook.rename(fx.origin / "hooks" / "pre-receive.off")
        git(fx.ci, "push", "--quiet", "origin", "HEAD:main")
        (fx.origin / "hooks" / "pre-receive.off").rename(hook)
        before = fx.main_tip()
        result = fx.publish()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("not a race", result.stderr)
        self.assertEqual(fx.producer_calls(), 1)
        self.assertEqual(fx.main_tip(), before)


class GenuineFailure(Base):
    def test_invalid_sources_fail_without_retry_or_push(self):
        fx = self.fx
        fx.land({"src/bad.txt": "INVALID reference\n"}, "invalid source")
        before = fx.main_tip()
        result = fx.publish()
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("real validation failure", result.stderr)
        self.assertEqual(fx.producer_calls(), 1)
        self.assertEqual(fx.main_tip(), before)

    def test_producer_touching_other_files_is_refused(self):
        fx = self.fx
        fx.land({"src/b.txt": "beta\n"}, "source change")
        before = fx.main_tip()
        result = fx.publish(FIXTURE_TOUCH=json.dumps(["README.md"]))
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("other than", result.stderr)
        self.assertEqual(fx.main_tip(), before)


class WriterGate(Base):
    """Missing privileged secrets never fail validation and never enter the writer."""

    def assert_refused(self, result, before):
        self.assertEqual(result.returncode, 4, result.stdout + result.stderr)
        self.assertEqual(self.fx.producer_calls(), 0)
        self.assertEqual(self.fx.main_tip(), before)

    def setUp(self):
        super().setUp()
        self.fx.land({"src/b.txt": "beta\n"}, "source change that would need publishing")
        self.before = self.fx.main_tip()
        self.ci_head = git(self.fx.ci, "rev-parse", "HEAD").stdout.strip()

    def test_dependabot_branch_without_secret_is_refused(self):
        result = self.fx.publish(
            SKILLS_GRAPH_PUBLISH_REF="refs/heads/dependabot/npm_and_yarn/tools/skill-map/zod-4.1.0",
            SKILLS_GRAPH_PUSH_TOKEN="",
        )
        self.assert_refused(result, self.before)
        self.assertEqual(git(self.fx.ci, "rev-parse", "HEAD").stdout.strip(), self.ci_head)

    def test_branch_with_a_token_is_still_refused(self):
        self.assert_refused(self.fx.publish(SKILLS_GRAPH_PUBLISH_REF="refs/heads/job/1-x"), self.before)

    def test_main_without_token_is_refused(self):
        self.assert_refused(self.fx.publish(SKILLS_GRAPH_PUSH_TOKEN=""), self.before)
        self.assert_refused(self.fx.publish(SKILLS_GRAPH_PUSH_TOKEN=None), self.before)

    def test_undeclared_checkout_is_never_reset(self):
        fx = self.fx
        (fx.ci / "work-in-progress.txt").write_text("someone's uncommitted work\n")
        self.assert_refused(fx.publish(SKILLS_GRAPH_CI_CHECKOUT=str(fx.dev)), self.before)
        self.assert_refused(fx.publish(SKILLS_GRAPH_CI_CHECKOUT=None), self.before)
        self.assertTrue((fx.ci / "work-in-progress.txt").exists())

    def test_linked_worktree_is_never_reset(self):
        fx = self.fx
        wt = fx.tmp / "worker"
        git(fx.ci, "worktree", "add", "--quiet", "-b", "worker", str(wt))
        (wt / "work-in-progress.txt").write_text("another worker's state\n")
        self.assert_refused(fx.publish(checkout=wt, SKILLS_GRAPH_CI_CHECKOUT=str(wt)), self.before)
        self.assertTrue((wt / "work-in-progress.txt").exists())

    def test_scripts_inside_the_checkout_are_refused(self):
        fx = self.fx
        inside = fx.ci / "tools" / "skills-graph-ci"
        shutil.copytree(fx.tool, inside)
        self.assert_refused(fx.publish(script=inside / "publish.sh"), self.before)
        shutil.copy(fx.producer, fx.ci / "producer.sh")
        self.assert_refused(fx.publish(regenerate=fx.ci / "producer.sh"), self.before)

    def test_token_never_reaches_the_producers(self):
        fx = self.fx
        probe = fx.tmp / "probe.sh"
        probe.write_text(f'#!/usr/bin/env bash\nprintf %s "${{SKILLS_GRAPH_PUSH_TOKEN-unset}}" > "{fx.tmp}/seen"\nexec "{fx.producer}"\n')
        probe.chmod(0o755)
        result = fx.publish(regenerate=probe)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((fx.tmp / "seen").read_text(), "unset")


class WorkflowContract(unittest.TestCase):
    """The branch path of skills-graph.yml holds no privileged secret or writer token."""

    @classmethod
    def setUpClass(cls):
        try:
            import yaml
        except ImportError:  # pragma: no cover
            raise unittest.SkipTest("needs PyYAML")
        cls.raw = WORKFLOW.read_text()
        cls.doc = yaml.safe_load(cls.raw)
        cls.steps = cls.doc["jobs"]["regenerate"]["steps"]

    def step(self, name):
        return next(s for s in self.steps if s.get("name") == name)

    def test_privileged_steps_run_only_on_main(self):
        privileged = [s for s in self.steps if any(k in json.dumps(s) for k in ("secrets.", "steps.app-token", "create-github-app-token"))]
        self.assertEqual(
            sorted(s["name"] for s in privileged),
            ["Commit regenerated graph and AI Workforce feed (main only)", "Mint skills-graph app token"],
        )
        for s in privileged:
            self.assertEqual(s.get("if"), MAIN_IF, s["name"])
        self.assertIn("publish.sh", self.step("Commit regenerated graph and AI Workforce feed (main only)")["run"])

    def test_branch_path_has_no_secret_and_a_read_only_checkout(self):
        branch_steps = [s for s in self.steps if s.get("if") != MAIN_IF]
        for s in branch_steps:
            blob = json.dumps(s)
            self.assertNotIn("secrets.", blob, s.get("name"))
            self.assertNotIn("app-token", blob, s.get("name"))
        checkout = self.step("Checkout expert-partners-skills")
        self.assertNotIn("token", checkout["with"])
        self.assertIs(checkout["with"]["persist-credentials"], False)
        self.assertEqual(self.raw.count("secrets."), 1)

    def test_writer_gate_inputs_come_from_the_run(self):
        env = self.step("Commit regenerated graph and AI Workforce feed (main only)")["env"]
        self.assertEqual(env["SKILLS_GRAPH_PUBLISH_REF"], "${{ github.ref }}")
        self.assertEqual(env["SKILLS_GRAPH_PUSH_TOKEN"], "${{ steps.app-token.outputs.token }}")
        self.assertEqual(env["SKILLS_GRAPH_CI_CHECKOUT"], "${{ github.workspace }}/eps")

    def test_permissions_concurrency_and_durable_retry(self):
        self.assertEqual(self.doc["permissions"], {"contents": "read"})
        self.assertEqual(self.doc["concurrency"], {"group": "skills-graph-${{ github.ref }}", "cancel-in-progress": True})
        triggers = self.doc[True] if True in self.doc else self.doc["on"]
        self.assertTrue(triggers["schedule"])
        self.assertIn("**", triggers["push"]["branches"])
        self.assertIn("tools/skills-graph-ci/**", triggers["push"]["paths"])

    def test_every_job_inherits_a_read_only_github_token(self):
        # A job-level permissions key replaces the workflow-level one, so check what each
        # job effectively gets, not just the top of the file.
        for job_id, job in self.doc["jobs"].items():
            effective = job.get("permissions", self.doc["permissions"])
            self.assertEqual(effective, {"contents": "read"}, job_id)
        self.assertNotIn("write", json.dumps(self.doc.get("permissions")))
        self.assertNotRegex(self.raw, r"\$\{\{\s*(github\.token|secrets\.GITHUB_TOKEN)")

    def test_main_writer_authenticates_with_the_app_token_only(self):
        mint = self.step("Mint skills-graph app token")
        self.assertEqual(mint["uses"].split("@")[0], "actions/create-github-app-token")
        self.assertEqual(mint["with"]["private-key"], "${{ secrets.SKILLS_GRAPH_APP_PRIVATE_KEY }}")
        publish = self.step("Commit regenerated graph and AI Workforce feed (main only)")
        self.assertNotIn("GITHUB_TOKEN", json.dumps(publish))
        self.assertIn("x-access-token:%s", (TOOL / "publish.sh").read_text())

    def test_committed_feed_is_still_verified_after_publishing(self):
        names = [s.get("name") for s in self.steps]
        verify = "Verify the committed AI Workforce feed matches its sources (main only)"
        self.assertLess(names.index("Commit regenerated graph and AI Workforce feed (main only)"), names.index(verify))
        self.assertIn("--check", self.step(verify)["run"])


if __name__ == "__main__":
    unittest.main()
