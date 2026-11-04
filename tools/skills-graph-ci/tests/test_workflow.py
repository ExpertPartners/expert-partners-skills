"""Static proofs about .github/workflows/skills-graph.yml: a branch run, including one started
by Dependabot with no Actions secrets, validates with a read-only token and never reaches the
token mint or the writer; only the main path holds a secret; the concurrency contract stands.

Run from the repo root: python3 -m unittest discover -s tools/skills-graph-ci/tests -v
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = ROOT / ".github" / "workflows" / "skills-graph.yml"

BRANCH_RUNS = [
    {"github.ref": "refs/heads/dependabot/npm_and_yarn/tools/capability-feed/npm_and_yarn-b94f287d41",
     "github.event_name": "push", "github.actor": "dependabot[bot]"},
    {"github.ref": "refs/heads/job/237-skills-graph-reliable", "github.event_name": "push", "github.actor": "factory-droid[bot]"},
    {"github.ref": "refs/heads/feature", "github.event_name": "workflow_dispatch", "github.actor": "someone"},
]
MAIN_RUNS = [
    {"github.ref": "refs/heads/main", "github.event_name": "push", "github.actor": "AllisonGaddy"},
    {"github.ref": "refs/heads/main", "github.event_name": "schedule", "github.actor": "AllisonGaddy"},
    {"github.ref": "refs/heads/main", "github.event_name": "workflow_dispatch", "github.actor": "AllisonGaddy"},
]
COMPARISON = re.compile(r"^\s*(github\.[a-z_]+)\s*(==|!=)\s*'([^']*)'\s*$")


def evaluate(condition: str | None, context: dict[str, str]) -> bool:
    """Evaluate a job-level if: made of `github.x == 'v'` or `!=` terms joined by &&.
    Anything else raises, so a new condition shape must be proven here before it ships."""
    if condition is None:
        return True
    text = condition.strip()
    if text.startswith("${{") and text.endswith("}}"):
        text = text[3:-2]
    result = True
    for term in text.split("&&"):
        match = COMPARISON.match(term)
        if not match:
            raise AssertionError(f"unsupported job condition term: {term!r}")
        name, op, value = match.groups()
        equal = context[name] == value
        result = result and (equal if op == "==" else not equal)
    return result


def strings(node: Any) -> str:
    """Every key and value under node, one per line, unwrapped."""
    if isinstance(node, dict):
        return "\n".join(f"{k}\n{strings(v)}" for k, v in node.items())
    if isinstance(node, list):
        return "\n".join(strings(v) for v in node)
    return str(node)


def secret_refs(node: Any) -> list[str]:
    return re.findall(r"secrets\.[A-Za-z0-9_]+", strings(node))


class WorkflowTest(unittest.TestCase):
    text: str
    doc: dict[Any, Any]
    jobs: dict[str, Any]

    @classmethod
    def setUpClass(cls) -> None:
        cls.text = WORKFLOW.read_text()
        cls.doc = yaml.safe_load(cls.text)
        cls.jobs = cls.doc["jobs"]

    def jobs_for(self, context: dict[str, str]) -> set[str]:
        return {name for name, job in self.jobs.items() if evaluate(job.get("if"), context)}

    def test_branch_runs_reach_validation_only(self) -> None:
        for context in BRANCH_RUNS:
            with self.subTest(ref=context["github.ref"], event=context["github.event_name"]):
                running = self.jobs_for(context)
                self.assertIn("validate", running)
                for name in running:
                    job = self.jobs[name]
                    self.assertEqual(secret_refs(job), [], f"{name} runs on a branch and must need no secret")
                    self.assertNotIn("create-github-app-token", strings(job))
                    self.assertNotIn("publish_generated.py", strings(job))
                    self.assertEqual(job.get("permissions"), {"contents": "read"})

    def test_main_runs_reach_the_writer_after_validation(self) -> None:
        for context in MAIN_RUNS:
            with self.subTest(event=context["github.event_name"]):
                self.assertEqual(self.jobs_for(context), {"validate", "publish"})
        self.assertEqual(self.jobs["publish"].get("needs"), "validate")

    def test_validation_checkout_is_read_only(self) -> None:
        checkouts = [s for s in self.jobs["validate"]["steps"] if str(s.get("uses", "")).startswith("actions/checkout@")]
        self.assertEqual(len(checkouts), 1)
        with_ = checkouts[0].get("with", {})
        self.assertNotIn("token", with_)
        self.assertIs(with_.get("persist-credentials"), False)

    def test_secret_and_mint_live_only_in_the_main_writer(self) -> None:
        self.assertEqual(secret_refs(self.doc), ["secrets.SKILLS_GRAPH_APP_PRIVATE_KEY"])
        self.assertEqual(secret_refs(self.jobs["publish"]), ["secrets.SKILLS_GRAPH_APP_PRIVATE_KEY"])
        self.assertEqual(self.jobs["publish"].get("if"), "github.ref == 'refs/heads/main'")
        steps = self.jobs["publish"]["steps"]
        self.assertEqual(steps[0].get("uses"), "actions/create-github-app-token@v3")
        writer = next(s for s in steps if s.get("id") == "publish")
        self.assertIn("--expect-ref refs/heads/main", writer["run"])

    def test_existing_contract_is_kept(self) -> None:
        self.assertEqual(self.doc["permissions"], {"contents": "write"})
        self.assertEqual(self.doc["concurrency"], {"group": "skills-graph-${{ github.ref }}", "cancel-in-progress": True})
        # PyYAML reads the bare key on as the boolean True (YAML 1.1).
        triggers: dict[str, Any] = self.doc["on"] if "on" in self.doc else self.doc[True]
        self.assertIn("schedule", triggers)
        self.assertIn("workflow_dispatch", triggers)
        self.assertEqual(triggers["push"]["branches"], ["**"])
        validate = strings(self.jobs["validate"])
        for check in ("npm test", "test-deploy-skill.sh", "extract-skills-graph.mjs", "generate-feed.mjs --check",
                      "tools/skills-graph-ci/tests"):
            self.assertIn(check, validate)
        final = self.jobs["publish"]["steps"][-1]
        self.assertEqual(final["run"].strip(), "node tools/capability-feed/generate-feed.mjs --check")

    def test_evaluator_rejects_unknown_shapes(self) -> None:
        with self.assertRaises(AssertionError):
            evaluate("always()", MAIN_RUNS[0])


if __name__ == "__main__":
    unittest.main()
