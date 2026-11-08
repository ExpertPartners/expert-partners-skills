"""Deterministic preflight routing and instruction contract, no model calls."""

import ast
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


HOOKS = Path(__file__).resolve().parents[1]
PLUGIN = HOOKS.parent
REPO = PLUGIN.parents[1]
SCRIPT = HOOKS / "factory_preflight.py"
spec = importlib.util.spec_from_file_location("factory_preflight", SCRIPT)
hook = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hook)


class PreflightHookTests(unittest.TestCase):
    def test_session_start_sources(self):
        for source in ("startup", "resume", "clear", "compact"):
            text = hook.context_for({"hook_event_name": "SessionStart", "source": source})
            self.assertIn("Skill(factory-operator)", text)
            self.assertIn("Auto", text)
            self.assertLess(len(text), 500)

    def test_trivial_prompts_are_silent(self):
        for prompt in ("", "   ", "Hi!", "thanks", "Yes.", "approved", "s", "q",
                       "continue", "quick update", "where are we?", "status"):
            with self.subTest(prompt=prompt):
                self.assertEqual("", hook.context_for(
                    {"hook_event_name": "UserPromptSubmit", "prompt": prompt}))

    def test_short_new_tasks_not_skipped(self):
        for prompt in ("fix tests", "build it", "review PR", "implement", "ship skill",
                       "Yes, implement the new module", "Explain Factory limits"):
            with self.subTest(prompt=prompt):
                text = hook.context_for(
                    {"hook_event_name": "UserPromptSubmit", "prompt": prompt})
                self.assertIn("Skill(factory-operator)", text)
                self.assertIn("Reuse", text)
                self.assertLess(len(text), 500)

    def test_read_only_assignment_gets_lightweight_skill_route(self):
        for prompt in ("Review these two files", "Read README.md", "Explain this function"):
            text = hook.context_for({"hook_event_name": "UserPromptSubmit", "prompt": prompt})
            self.assertIn("Skill(factory-operator)", text)
            self.assertIn("read/review/explain included", text)
            self.assertIn("one-line", text)
            self.assertIn("Await its result", text)
            self.assertIn("never in parallel", text)

    def test_no_prompt_echo(self):
        prompt = "Implement customer-specific private text, never echo this input"
        output = hook.context_for({"hook_event_name": "UserPromptSubmit", "prompt": prompt})
        self.assertNotIn(prompt, output)
        self.assertNotIn("customer-specific", output)
        self.assertEqual(output, hook.TASK_CONTEXT)

    def test_image_without_text(self):
        for prompt in (None, "", "thanks"):
            self.assertEqual(hook.TASK_CONTEXT, hook.context_for({
                "hook_event_name": "UserPromptSubmit", "prompt": prompt, "has_images": True}))

    def test_wrong_shapes_and_events(self):
        for payload in (None, [], "text", 123, {}, {"hook_event_name": "PreToolUse"},
                        {"hook_event_name": "Stop"}, {"prompt": "build it"},
                        {"hook_event_name": "UserPromptSubmit", "prompt": {}}):
            self.assertEqual("", hook.context_for(payload))

    def test_process_malformed_and_oversize(self):
        for raw in ("", "{", "null", "[]", '{"prompt": "new task"}',
                    "[" * 2000 + "]" * 2000, "x" * 1_048_577):
            result = subprocess.run([sys.executable, str(SCRIPT)], input=raw, text=True,
                                    capture_output=True, timeout=3, check=False)
            self.assertEqual(0, result.returncode)
            self.assertEqual("", result.stdout)
            self.assertEqual("", result.stderr)

    def test_process_stdout_context_no_files(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [sys.executable, str(SCRIPT)], cwd=directory,
                input=json.dumps({"hook_event_name": "UserPromptSubmit", "prompt": "fix tests"}),
                text=True, capture_output=True, timeout=3, check=False)
            self.assertEqual(0, result.returncode)
            self.assertEqual(hook.TASK_CONTEXT + "\n", result.stdout)
            self.assertEqual("", result.stderr)
            self.assertEqual([], list(Path(directory).iterdir()))

    def test_no_network_settings_or_process_imports(self):
        tree = ast.parse(SCRIPT.read_text())
        imported = {node.names[0].name for node in ast.walk(tree)
                    if isinstance(node, ast.Import)}
        self.assertEqual({"json", "re", "sys"}, imported)
        self.assertFalse(any(isinstance(node, ast.ImportFrom) for node in ast.walk(tree)))
        self.assertNotIn("open(", SCRIPT.read_text())

    def test_manifest_events_preserve_browser_hook(self):
        config = json.loads((HOOKS / "hooks.json").read_text())
        for event in ("SessionStart", "UserPromptSubmit"):
            commands = config["hooks"][event]
            self.assertEqual(1, len(commands))
            self.assertEqual("python3 \"${CLAUDE_PLUGIN_ROOT}/hooks/factory_preflight.py\"",
                             commands[0]["hooks"][0]["command"])
            self.assertEqual("command", commands[0]["hooks"][0]["type"])
        browser = config["hooks"]["PreToolUse"]
        self.assertEqual(1, len(browser))
        self.assertEqual(
            "^mcp__.*__(browser_navigate|navigate|tabs_create_mcp|browser_tabs|"
            "browser_run_code_unsafe|browser_run_code|browser_evaluate)$", browser[0]["matcher"])
        self.assertEqual('python3 "${CLAUDE_PLUGIN_ROOT}/hooks/headless_route_check.py"',
                         browser[0]["hooks"][0]["command"])
        self.assertNotIn("Stop", config["hooks"])


class PreflightInstructionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skill = (PLUGIN / "skills/factory-operator/SKILL.md").read_text()
        cls.refs = PLUGIN / "skills/factory-operator/reference"

    def test_preflight_receipt_fields(self):
        for field in ("Complexity", "reasoning", "Duration", "resources", "Parallelism",
                      "zero additional workers", "one active worker", "autonomy",
                      "unknown", "work record"):
            self.assertIn(field, self.skill)

    def test_preserves_selection_and_no_byok_gate(self):
        self.assertIn("Preserve Auto", self.skill)
        self.assertIn("BYOK optional", self.skill)
        self.assertIn("BYOK never blocks", self.skill)
        for stale in ("Default two agents", "one agent max", "Otherwise pin",
                      "Auto only when", "5-hour at or above 90%"):
            self.assertNotIn(stale, self.skill)

    def test_control_scope_and_visibility(self):
        for phrase in ("Workstream agents", "Task subagents", "Mission workers",
                       "creation-time", "future", "backend unknown",
                       "not proof", "instruction/context only"):
            self.assertIn(phrase, self.skill)
        settings = (self.refs / "settings-map.md").read_text()
        self.assertIn("not documented fields", settings)
        self.assertIn("maxAgents", settings)

    def test_reference_examples_cover_unknown_conflict_and_revision(self):
        examples = (self.refs / "decision-ladder.md").read_text()
        for phrase in ("allowance unknown", "Revised scope", "Explicit model choice",
                       "BYOK empty", "Short acknowledgement"):
            self.assertIn(phrase, examples)

    def test_repo_route_is_pointer_not_duplicate(self):
        text = (REPO / "AGENTS.md").read_text()
        self.assertIn("invoke `factory-operator`", text)
        self.assertIn("context only", text)


if __name__ == "__main__":
    unittest.main()
