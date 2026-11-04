"""Offline fixture tests for tools/dead-code/check_dead_code.py.

Each detector test writes a small synthetic repository to a temporary directory, with its
own pyproject.toml [tool.vulture] table and tools/dead-code/knip.json, plants one piece of
unused or reachable code, and runs the checker on it. No real file is changed and no
network request is made. The detector tests skip when vulture or knip is not installed,
unless DEADCODE_REQUIRE_TOOLS=1 is set, as .github/workflows/tooling-dead-code.yml does.

Run from the repo root: python3 -m unittest discover -s tools/dead-code/tests -v
"""

import contextlib
import importlib.util
import io
import json
import os
import re
import shutil
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
CHECKER = os.path.join(HERE, "..", "check_dead_code.py")
WORKFLOW = os.path.join(ROOT, ".github", "workflows", "tooling-dead-code.yml")
REQUIRE_TOOLS = os.environ.get("DEADCODE_REQUIRE_TOOLS") == "1"

spec = importlib.util.spec_from_file_location("check_dead_code", CHECKER)
dead = importlib.util.module_from_spec(spec)
sys.modules["check_dead_code"] = dead
spec.loader.exec_module(dead)

REQUIRED_PY_PATHS = [
    "tools",
    "plugins/research-ops/skills/source-hunter/scripts",
    "plugins/research-ops/skills/video-discovery/scripts",
]

PYPROJECT = """\
[tool.vulture]
paths = ["tools", "skill/scripts", "skill/tests"]
min_confidence = 60
exclude = ["*/node_modules/*"]
"""

PYTHON_FILES = {
    "tools/demo/cli.py": """\
import sys

import helper


def main() -> int:
    print(helper.used())
    return 0


if __name__ == "__main__":
    sys.exit(main())
""",
    "tools/demo/helper.py": """\
import io
import urllib.request
from typing import Protocol


def used() -> str:
    return "used"


class Reader(io.RawIOBase):
    def readable(self) -> bool:
        return True


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class Opener(Protocol):
    def __call__(self, url: str, /) -> bytes: ...

    def open_url(self, url: str) -> bytes: ...


REGISTERED = [Reader, NoRedirect, Opener]
""",
    "tools/demo/hyphen-tool.py": """\
def run() -> str:
    return "ran"
""",
    "tools/demo/tests/test_demo.py": """\
import importlib.util
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("hyphen_tool", os.path.join(HERE, "..", "hyphen-tool.py"))
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


def setUpModule():
    pass


class Base(unittest.TestCase):
    pass


class Runs(Base):
    def setUp(self):
        self.value = tool.run()

    def test_runs(self):
        self.assertEqual(self.value, "ran")
""",
    "skill/scripts/skill_cli.py": """\
from lib_mod import compute

if __name__ == "__main__":
    print(compute(2))
""",
    "skill/scripts/lib_mod.py": """\
def compute(value: int) -> int:
    return value * 2
""",
    "skill/tests/conftest.py": """\
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
""",
    "skill/tests/test_skill.py": """\
import pytest
from lib_mod import compute


@pytest.fixture
def number():
    return 2


@pytest.fixture
def offline():
    yield


def test_compute(number, offline):
    assert compute(number) == 4
""",
}

KNIP_JSON = {
    "ignoreExportsUsedInFile": True,
    "workspaces": {"tools/feed": {"entry": ["cli.mjs", "test/*.test.mjs"], "project": ["**/*.mjs"]}},
}

JS_FILES = {
    "tools/feed/package.json": json.dumps({
        "name": "feed", "private": True, "type": "module",
        "scripts": {"build": "node cli.mjs --write", "test": "node --test test/*.test.mjs"},
    }, indent=2) + "\n",
    "tools/feed/cli.mjs": """\
import { used } from './lib/used.mjs';

const plugin = await import('./lib/plugin.mjs');
console.log(used(), plugin.loaded());
""",
    "tools/feed/lib/used.mjs": """\
export const PREFIX = 'us';

export function used() {
  return `${PREFIX}ed`;
}
""",
    "tools/feed/lib/plugin.mjs": """\
export function loaded() {
  return 'loaded';
}
""",
    "tools/feed/test/cli.test.mjs": """\
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { used } from '../lib/used.mjs';
import { expected } from './expected.mjs';

test('used', () => {
  assert.equal(used(), expected());
});
""",
    "tools/feed/test/expected.mjs": """\
export function expected() {
  return 'used';
}
""",
}


def has_vulture():
    return importlib.util.find_spec("vulture") is not None


def has_knip():
    return any(Path(ROOT).glob("tools/*/node_modules/.bin/knip"))


def needs(available, what):
    if available:
        return lambda func: func
    if REQUIRE_TOOLS:
        def fail(self):
            self.fail(f"{what} is not installed and DEADCODE_REQUIRE_TOOLS=1")
        return lambda func: fail
    return unittest.skip(f"{what} is not installed")


class Fixture(unittest.TestCase):
    """A clean synthetic repository: every module and export is reached."""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="dead-code-fixture-"))
        self.addCleanup(shutil.rmtree, self.root, True)
        self.write("pyproject.toml", PYPROJECT)
        self.write("tools/dead-code/knip.json", json.dumps(KNIP_JSON, indent=2) + "\n")
        for path, text in {**PYTHON_FILES, **JS_FILES}.items():
            self.write(path, text)

    def write(self, path, text):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")

    def append(self, path, text):
        with open(self.root / path, "a", encoding="utf-8") as fh:
            fh.write(text)

    def check(self, language, exceptions=None, pending=None):
        return dead.check(self.root, exceptions=exceptions or {}, pending=pending or {}, languages=(language,))

    def run_cli(self, *args):
        """The command line on the fixture, with the repository's own tables emptied."""
        out = io.StringIO()
        with mock.patch.dict(dead.EXCEPTIONS, clear=True), mock.patch.dict(dead.PENDING_FINDINGS, clear=True), \
                contextlib.redirect_stdout(out):
            code = dead.main(["--root", str(self.root), *args])
        return code, out.getvalue()

    def keys(self, report):
        return {f.key for f in report.findings}

    def assert_clean(self, report):
        self.assertEqual([str(f) for f in report.findings], [])
        self.assertEqual(report.errors, [])


class PythonDetectorTest(Fixture):
    @needs(has_vulture(), "vulture")
    def test_clean_fixture_passes_through_the_command_line(self):
        code, out = self.run_cli("--only", "python")
        self.assertEqual(code, 0, out)
        self.assertIn("dead-code: PASS", out)
        self.assertIn("ENTRY tools/demo/cli.py [cli] __main__ guard at line 11", out)

    @needs(has_vulture(), "vulture")
    def test_inventory_comes_from_the_source(self):
        report = self.check("python")
        kinds = {(e.path, e.kind) for e in report.entries}
        self.assertIn(("tools/demo/cli.py", "cli"), kinds)
        self.assertIn(("skill/scripts/skill_cli.py", "cli"), kinds)
        self.assertIn(("tools/demo/tests/test_demo.py", "test"), kinds)
        self.assertIn(("skill/tests/test_skill.py", "test"), kinds)
        self.assertNotIn("tools/demo/helper.py", {e.path for e in report.entries})

    @needs(has_vulture(), "vulture")
    def test_reachable_cli_test_and_dynamically_loaded_modules_pass(self):
        report = self.check("python")
        self.assert_clean(report)
        rules = {f.name: rule for f, rule in report.dispatched}
        self.assertIn("io.RawIOBase.readable", rules["readable"])
        self.assertIn("HTTPRedirectHandler.redirect_request", rules["redirect_request"])
        self.assertIn("Protocol Opener", rules["open_url"])
        self.assertIn("special method", rules["__call__"])
        self.assertIn("TestCase", rules["Runs"])
        self.assertIn("setUpModule", rules["setUpModule"])
        self.assertIn("requested at skill/tests/test_skill.py", rules["offline"])

    @needs(has_vulture(), "vulture")
    def test_script_run_by_a_workflow_is_an_entrypoint(self):
        self.write("tools/demo/standalone.py", "print('ran by CI')\n")
        self.write(".github/workflows/run.yml", "jobs:\n  x:\n    steps:\n      - run: python3 tools/demo/standalone.py\n")
        report = self.check("python")
        self.assert_clean(report)
        self.assertIn(dead.Entry("tools/demo/standalone.py", "run", ".github/workflows/run.yml:4"), report.entries)

    @needs(has_vulture(), "vulture")
    def test_commented_reference_is_not_an_entrypoint(self):
        self.write("tools/demo/standalone.py", "print('nobody runs me')\n")
        self.write(".github/workflows/run.yml", "# python3 tools/demo/standalone.py\njobs: {}\n")
        self.assertIn("tools/demo/standalone.py:module:standalone", self.keys(self.check("python")))

    @needs(has_vulture(), "vulture")
    def test_unused_production_function_fails(self):
        self.append("tools/demo/helper.py", "\n\ndef orphan_helper() -> str:\n    return 'never called'\n")
        report = self.check("python")
        self.assertEqual(self.keys(report), {"tools/demo/helper.py:function:orphan_helper"})
        code, out = self.run_cli("--only", "python")
        self.assertEqual(code, 1, out)
        self.assertRegex(out, r"FAIL tools/demo/helper\.py:\d+: function 'orphan_helper'")
        self.assertIn("dead-code: FAIL", out)

    @needs(has_vulture(), "vulture")
    def test_unused_import_fails(self):
        self.append("tools/demo/helper.py", "\nimport json\n")
        self.assertEqual(self.keys(self.check("python")), {"tools/demo/helper.py:import:json"})

    @needs(has_vulture(), "vulture")
    def test_unreachable_module_fails(self):
        self.write("tools/demo/orphan_module.py", "VALUE = 1\n")
        self.assertEqual(self.keys(self.check("python")), {"tools/demo/orphan_module.py:module:orphan_module"})

    @needs(has_vulture(), "vulture")
    def test_unrequested_fixture_fails(self):
        self.append("skill/tests/test_skill.py", "\n\n@pytest.fixture\ndef never_requested():\n    return 1\n")
        self.assertEqual(self.keys(self.check("python")), {"skill/tests/test_skill.py:function:never_requested"})

    @needs(has_vulture(), "vulture")
    def test_method_the_base_class_does_not_define_fails(self):
        self.append("tools/demo/helper.py", "\n\nclass Wrapper(io.RawIOBase):\n    def frobnicate(self) -> int:\n"
                                            "        return 1\n\n\nWRAPPERS = [Wrapper]\n")
        self.assertEqual(self.keys(self.check("python")), {"tools/demo/helper.py:method:frobnicate"})

    @needs(has_vulture(), "vulture")
    def test_test_named_function_outside_tests_fails(self):
        self.append("tools/demo/helper.py", "\n\ndef test_looking_helper() -> None:\n    pass\n")
        self.assertEqual(self.keys(self.check("python")), {"tools/demo/helper.py:function:test_looking_helper"})

    @needs(has_vulture(), "vulture")
    def test_variables_and_attributes_are_out_of_scope(self):
        self.append("tools/demo/helper.py", "\n\nclass Record:\n    def __init__(self) -> None:\n"
                                            "        self.never_read = 1\n\n\nRECORDS = [Record]\n")
        self.assert_clean(self.check("python"))


class ExceptionTest(Fixture):
    ORPHAN = "\n\ndef orphan_helper() -> str:\n    return 'never called'\n"
    KEY = "tools/demo/helper.py:function:orphan_helper"

    @needs(has_vulture(), "vulture")
    def test_evidenced_exception_clears_only_its_finding(self):
        self.append("tools/demo/helper.py", self.ORPHAN + "\n\ndef second_orphan() -> None:\n    pass\n")
        report = self.check("python", exceptions={self.KEY: "called by name through getattr in tools/demo/cli.py:7"})
        self.assertEqual([f.key for f, _ in report.excepted], [self.KEY])
        self.assertEqual(self.keys(report), {"tools/demo/helper.py:function:second_orphan"})

    @needs(has_vulture(), "vulture")
    def test_exception_without_evidence_fails(self):
        self.append("tools/demo/helper.py", self.ORPHAN)
        report = self.check("python", exceptions={self.KEY: "  "})
        self.assertTrue(any("names no evidence" in e for e in report.errors), report.errors)

    @needs(has_vulture(), "vulture")
    def test_stale_exception_fails(self):
        report = self.check("python", exceptions={self.KEY: "called by name somewhere"})
        self.assertTrue(any("EXCEPTIONS lists" in e for e in report.errors), report.errors)

    @needs(has_vulture(), "vulture")
    def test_pending_finding_warns_and_fails_once_gone(self):
        self.append("tools/demo/helper.py", self.ORPHAN)
        report = self.check("python", pending={self.KEY: "owner removes it"})
        self.assertEqual([f.key for f, _ in report.pending], [self.KEY])
        self.assert_clean(report)
        self.write("tools/demo/helper.py", PYTHON_FILES["tools/demo/helper.py"])
        report = self.check("python", pending={self.KEY: "owner removes it"})
        self.assertTrue(any("PENDING_FINDINGS lists" in e for e in report.errors), report.errors)


class JavaScriptDetectorTest(Fixture):
    @needs(has_knip(), "knip")
    def test_clean_fixture_passes_through_the_command_line(self):
        code, out = self.run_cli("--only", "javascript")
        self.assertEqual(code, 0, out)
        self.assertIn("dead-code: PASS", out)

    @needs(has_knip(), "knip")
    def test_clean_fixture_passes_with_test_and_dynamic_entries(self):
        report = self.check("javascript")
        self.assert_clean(report)
        kinds = {(e.path, e.kind) for e in report.entries}
        self.assertIn(("tools/feed/cli.mjs", "cli"), kinds)
        self.assertIn(("tools/feed/test/cli.test.mjs", "test"), kinds)

    @needs(has_knip(), "knip")
    def test_unused_production_export_fails(self):
        self.append("tools/feed/lib/used.mjs", "\nexport function orphanExport() {\n  return 1;\n}\n")
        report = self.check("javascript")
        self.assertEqual(self.keys(report), {"tools/feed/lib/used.mjs:exports:orphanExport"})
        self.assertEqual(report.errors, [])

    @needs(has_knip(), "knip")
    def test_unused_file_fails(self):
        self.write("tools/feed/lib/orphan.mjs", "export const lonely = 1;\n")
        self.assertEqual(self.keys(self.check("javascript")), {"tools/feed/lib/orphan.mjs:file:lib/orphan.mjs"})

    @needs(has_knip(), "knip")
    def test_entry_nothing_runs_fails(self):
        self.write("tools/feed/extra.mjs", "console.log('extra');\n")
        config = json.loads(json.dumps(KNIP_JSON))
        config["workspaces"]["tools/feed"]["entry"].append("extra.mjs")
        self.write("tools/dead-code/knip.json", json.dumps(config))
        report = self.check("javascript")
        self.assertTrue(any("lists entry tools/feed/extra.mjs" in e for e in report.errors), report.errors)

    @needs(has_knip(), "knip")
    def test_file_a_workflow_runs_must_be_an_entry(self):
        self.write("tools/feed/tool.mjs", "console.log('tool');\n")
        self.write(".github/workflows/run.yml", "jobs:\n  x:\n    steps:\n      - run: node tools/feed/tool.mjs\n")
        report = self.check("javascript")
        self.assertTrue(any(e.startswith("tools/feed/tool.mjs is run by .github/workflows/run.yml:4")
                            for e in report.errors), report.errors)

    def test_entry_pattern_matching_nothing_fails(self):
        config = json.loads(json.dumps(KNIP_JSON))
        config["workspaces"]["tools/feed"]["entry"].append("missing.mjs")
        self.write("tools/dead-code/knip.json", json.dumps(config))
        report = self.check("javascript")
        self.assertTrue(any("'missing.mjs' matches no file" in e for e in report.errors), report.errors)

    def test_workspace_without_explicit_entries_is_refused(self):
        self.write("tools/dead-code/knip.json", json.dumps({"workspaces": {"tools/feed": {"project": ["**/*.mjs"]}}}))
        report = self.check("javascript")
        self.assertTrue(any("needs an explicit entry list" in e for e in report.errors), report.errors)


class RepositoryConfigTest(unittest.TestCase):
    def test_python_scope_covers_the_canonical_tooling(self):
        with open(os.path.join(ROOT, "pyproject.toml"), "rb") as fh:
            config = tomllib.load(fh)["tool"]["vulture"]
        for path in REQUIRED_PY_PATHS:
            with self.subTest(path=path):
                self.assertIn(path, config["paths"])
                self.assertTrue(os.path.isdir(os.path.join(ROOT, path)))
        self.assertEqual(config["exclude"], ["*/node_modules/*"])
        self.assertLessEqual(config["min_confidence"], 60)

    def test_knip_covers_every_javascript_producer_with_explicit_entries(self):
        with open(os.path.join(ROOT, "tools", "dead-code", "knip.json"), encoding="utf-8") as fh:
            config = json.load(fh)
        producers = {p.parent.relative_to(ROOT).as_posix() for p in Path(ROOT).glob("tools/*/package.json")}
        self.assertEqual(set(config["workspaces"]), producers)
        for producer, options in config["workspaces"].items():
            with self.subTest(producer=producer):
                self.assertTrue(options["entry"])
                self.assertNotIn("ignore", options)
        self.assertNotIn("ignore", config)

    def test_executable_kinds_only_leave_out_data_names(self):
        self.assertEqual(set(dead.PY_KINDS), {"function", "method", "class", "property", "import", "unreachable_code"})
        self.assertNotIn("exports", {"dependencies", "devDependencies"} & set(dead.KNIP_INCLUDE))
        self.assertIn("files", dead.KNIP_INCLUDE)
        self.assertIn("exports", dead.KNIP_INCLUDE)

    def test_every_exception_and_pending_entry_names_an_existing_file_and_a_reason(self):
        for table in (dead.EXCEPTIONS, dead.PENDING_FINDINGS):
            for key, reason in table.items():
                with self.subTest(key=key):
                    self.assertTrue(os.path.isfile(os.path.join(ROOT, key.split(":", 1)[0])))
                    self.assertTrue(reason.strip())

    def test_both_producers_pin_the_same_knip(self):
        specs = set()
        for manifest in Path(ROOT).glob("tools/*/package.json"):
            dev = json.loads(manifest.read_text(encoding="utf-8")).get("devDependencies", {})
            self.assertRegex(dev.get("knip", ""), r"^\d+\.\d+\.\d+$", manifest)
            specs.add(dev["knip"])
        self.assertEqual(len(specs), 1, specs)

    def test_vulture_is_hash_locked(self):
        with open(os.path.join(ROOT, "requirements-tooling.txt"), encoding="utf-8") as fh:
            text = fh.read()
        found = re.search(r"(?m)^vulture==\d+\.\d+ \\\n    --hash=sha256:[0-9a-f]{64}", text)
        self.assertIsNotNone(found, "requirements-tooling.txt has no hash-locked vulture pin")
        self.assertRegex(text.splitlines()[3], r"^# Direct: .*\bvulture\b")

    def test_workflow_runs_the_checker_and_requires_the_detectors(self):
        with open(WORKFLOW, encoding="utf-8") as fh:
            text = fh.read()
        self.assertIn("--require-hashes -r requirements-tooling.txt", text)
        self.assertIn("npm ci --ignore-scripts", text)
        self.assertIn("python tools/dead-code/check_dead_code.py", text)
        self.assertIn('DEADCODE_REQUIRE_TOOLS: "1"', text)
        self.assertNotRegex(text, r"\bnpm\s+install\b")

    @needs(has_vulture() and has_knip(), "vulture and knip")
    def test_repository_has_no_unlisted_unused_code(self):
        report = dead.check(Path(ROOT))
        self.assertEqual([str(f) for f in report.findings], [])
        self.assertEqual(report.errors, [])
        entries = {e.path for e in report.entries}
        for producer in ("tools/capability-feed", "tools/skill-map"):
            self.assertTrue(any(p.startswith(producer + "/") for p in entries), producer)
        for scripts in REQUIRED_PY_PATHS[1:]:
            self.assertTrue(any(p.startswith(scripts + "/") for p in entries), scripts)
        self.assertTrue(re.search(r"^tools/", "\n".join(entries), re.M))


if __name__ == "__main__":
    unittest.main()
