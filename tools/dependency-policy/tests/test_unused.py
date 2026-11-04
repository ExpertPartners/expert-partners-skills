"""Offline fixture tests for tools/dependency-policy/check_unused.py.

Each test writes a small synthetic repository to a temporary directory, with its own
pyproject.toml [tool.vulture] scope, hash-locked requirements files and producer
manifests, plants one dependency problem (or a clean tree), and runs the checker on it.
No real file is changed and no network request is made: the Python analysis is pure
stdlib AST, and knip runs against the fixture tree with the binary installed in this
repository. The knip tests skip when knip is not installed, unless
UNUSED_REQUIRE_TOOLS=1 is set, as .github/workflows/tooling-unused-dependencies.yml does.

Run from the repo root: python3 -m unittest discover -s tools/dependency-policy/tests -v
"""

import contextlib
import fnmatch
import importlib.util
import io
import json
import os
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
CHECKER = os.path.join(HERE, "..", "check_unused.py")
WORKFLOW = os.path.join(ROOT, ".github", "workflows", "tooling-unused-dependencies.yml")
REQUIRE_TOOLS = os.environ.get("UNUSED_REQUIRE_TOOLS") == "1"

spec = importlib.util.spec_from_file_location("check_unused", CHECKER)
unused = importlib.util.module_from_spec(spec)
sys.modules["check_unused"] = unused
spec.loader.exec_module(unused)

HASH = "0" * 64

PYPROJECT = """\
[tool.vulture]
paths = ["tools", "skill/scripts", "skill/tests"]
min_confidence = 60
exclude = []
"""

WORKFLOW_YML = """\
name: check
jobs:
  typecheck:
    steps:
      - run: python -m mypy tools
"""

PYTHON_FILES = {
    "tools/demo/cli.py": '''\
"""Fixture CLI."""
import sys

import requests

try:
    import yaml
except ImportError:
    yaml = None


def main() -> int:
    print(requests.__name__, yaml)
    return 0


if __name__ == "__main__":
    sys.exit(main())
''',
    "skill/scripts/work.py": '''\
"""Fixture skill script."""
from PIL import Image


def size(path: str) -> tuple[int, int]:
    return Image.open(path).size
''',
    "skill/tests/test_work.py": '''\
import pytest
from PIL import Image


def test_image():
    assert Image is not None
    assert pytest is not None
''',
}

KNIP_JSON = {
    "ignoreExportsUsedInFile": True,
    "workspaces": {"tools/feed": {"entry": ["cli.mjs", "test/*.test.mjs"], "project": ["**/*.mjs"]}},
}

JS_FILES = {
    "tools/feed/package.json": json.dumps({
        "name": "feed", "private": True, "type": "module",
        "scripts": {"build": "node cli.mjs --write", "test": "node --test test/*.test.mjs"},
        "dependencies": {"gray-matter": "^4.0.3"},
        "devDependencies": {"mime": "^4.0.0"},
        "optionalDependencies": {"fsevents": "^2.3.3"},
    }, indent=2) + "\n",
    "tools/feed/cli.mjs": """\
import matter from 'gray-matter';
import fsevents from 'fsevents';

console.log(matter, typeof fsevents);
""",
    "tools/feed/test/cli.test.mjs": """\
import { test } from 'node:test';
import assert from 'node:assert/strict';
import mime from 'mime';

test('mime', () => {
  assert.equal(mime.getType('a.txt'), 'text/plain');
});
""",
}


def lock_text(direct, pins, includes=()):
    lines = ["# Hash-locked fixture lock.",
             f"# Direct: {', '.join(direct)}. Any other entry is a transitive dependency."]
    lines += [f"-r {include}" for include in includes]
    for pin in pins:
        lines += [f"{pin} \\", f"    --hash=sha256:{HASH}"]
    return "\n".join(lines) + "\n"


def tooling_lock(direct=("requests", "mypy", "pyyaml", "types-requests"),
                 pins=("requests==2.34.2", "mypy==1.19.0", "pyyaml==6.0.3",
                       "types-requests==2.33.0.20261030", "urllib3==2.8.0")):
    return lock_text(direct, pins)


def has_knip():
    return any(Path(ROOT).glob("tools/*/node_modules/.bin/knip"))


def needs(available, what):
    if available:
        return lambda func: func
    if REQUIRE_TOOLS:
        def fail(self):
            self.fail(f"{what} is not installed and UNUSED_REQUIRE_TOOLS=1")
        return lambda func: fail
    return unittest.skip(f"{what} is not installed")


class Fixture(unittest.TestCase):
    """A clean synthetic repository: every direct dependency is used, every import declared."""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="unused-deps-fixture-"))
        self.addCleanup(shutil.rmtree, self.root, True)
        self.write("pyproject.toml", PYPROJECT)
        self.write("requirements-tooling.txt", tooling_lock())
        self.write("skill/requirements.txt", lock_text(["pillow"], ["pillow==13.0.0"]))
        self.write("skill/requirements-dev.txt",
                   lock_text(["pytest"], ["pytest==9.2.0"], includes=["requirements.txt"]))
        self.write(".github/workflows/check.yml", WORKFLOW_YML)
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

    def check(self, language, exceptions=None):
        return unused.check(self.root, exceptions=exceptions or {}, languages=(language,))

    def run_cli(self, *args):
        """The command line on the fixture, with the repository's own exceptions emptied."""
        out = io.StringIO()
        with mock.patch.dict(unused.EXCEPTIONS, clear=True), contextlib.redirect_stdout(out):
            code = unused.main(["--root", str(self.root), *args])
        return code, out.getvalue()

    def keys(self, report):
        return {f.key for f in report.findings}

    def assert_clean(self, report):
        self.assertEqual([str(f) for f in report.findings], [])
        self.assertEqual(report.errors, [])

    def use_kinds(self, report):
        return {(u.lock, u.name): u.kind for u in report.uses}


class PythonDetectorTest(Fixture):
    def test_clean_fixture_passes_through_the_command_line(self):
        code, out = self.run_cli("--only", "python")
        self.assertEqual(code, 0, out)
        self.assertIn("unused-dependencies: PASS", out)

    def test_runtime_test_cli_optional_and_stub_usage_are_distinguished(self):
        report = self.check("python")
        self.assert_clean(report)
        kinds = self.use_kinds(report)
        self.assertEqual(kinds[("requirements-tooling.txt", "requests")], "runtime")
        self.assertEqual(kinds[("requirements-tooling.txt", "pyyaml")], "runtime, optional")
        self.assertEqual(kinds[("requirements-tooling.txt", "mypy")], "cli")
        self.assertEqual(kinds[("requirements-tooling.txt", "types-requests")], "stub")
        self.assertEqual(kinds[("skill/requirements.txt", "pillow")], "runtime")
        self.assertEqual(kinds[("skill/requirements-dev.txt", "pytest")], "test")

    def test_declared_dependency_nothing_uses_fails(self):
        self.write("requirements-tooling.txt",
                   tooling_lock(direct=("requests", "mypy", "pyyaml", "types-requests", "click"),
                                pins=("requests==2.34.2", "mypy==1.19.0", "pyyaml==6.0.3",
                                      "types-requests==2.33.0.20261030", "urllib3==2.8.0",
                                      "click==8.3.0")))
        report = self.check("python")
        self.assertEqual(self.keys(report), {"requirements-tooling.txt:dependency:click"})
        code, out = self.run_cli("--only", "python")
        self.assertEqual(code, 1, out)
        self.assertRegex(out, r"FAIL requirements-tooling\.txt:\d+: dependency 'click'")
        self.assertIn("unused-dependencies: FAIL", out)

    def test_import_nothing_declares_fails(self):
        self.append("tools/demo/cli.py", "\nimport boto3\n")
        report = self.check("python")
        self.assertEqual(self.keys(report), {"tools/demo/cli.py:import:boto3"})

    def test_optional_import_is_not_silenced_and_still_needs_a_declaration(self):
        self.append("tools/demo/cli.py",
                    "\ntry:\n    import boto3\nexcept ImportError:\n    boto3 = None\n")
        report = self.check("python")
        self.assertEqual(self.keys(report), {"tools/demo/cli.py:import:boto3"})
        finding = report.findings[0]
        self.assertIn("try/except", finding.message)

    def test_cli_evidence_is_required(self):
        self.write(".github/workflows/check.yml", "name: check\njobs: {}\n")
        report = self.check("python")
        self.assertIn("requirements-tooling.txt:dependency:mypy", self.keys(report))

    def test_stub_without_the_stubbed_package_fails(self):
        self.write("requirements-tooling.txt",
                   tooling_lock(direct=("mypy", "pyyaml", "types-requests"),
                                pins=("mypy==1.19.0", "pyyaml==6.0.3",
                                      "types-requests==2.33.0.20261030")))
        self.write("tools/demo/cli.py", PYTHON_FILES["tools/demo/cli.py"].replace(
            "import requests\n", ""))
        report = self.check("python")
        self.assertIn("requirements-tooling.txt:dependency:types-requests", self.keys(report))

    def test_transitive_pin_is_not_expected_to_be_imported(self):
        # urllib3 is pinned but not in the Direct header: a transitive pin never fails.
        report = self.check("python")
        self.assertNotIn("urllib3", {u.name for u in report.uses})
        self.assert_clean(report)

    def test_import_of_a_transitive_pin_needs_a_direct_declaration(self):
        self.append("tools/demo/cli.py", "\nimport urllib3\n")
        report = self.check("python")
        self.assertEqual(self.keys(report), {"tools/demo/cli.py:import:urllib3"})
        code, out = self.run_cli("--only", "python")
        self.assertEqual(code, 1, out)
        self.assertIn("urllib3", out)
        self.assertIn("unused-dependencies: FAIL", out)

    def test_optional_import_of_a_transitive_pin_needs_a_direct_declaration(self):
        self.append("tools/demo/cli.py",
                    "\ntry:\n    import urllib3\nexcept ImportError:\n    urllib3 = None\n")
        report = self.check("python")
        self.assertEqual(self.keys(report), {"tools/demo/cli.py:import:urllib3"})
        self.assertIn("try/except", report.findings[0].message)

    def test_included_transitive_pin_is_not_a_declaration_until_promoted_to_direct(self):
        pins = ["pillow==13.0.0", "urllib3==2.8.0"]
        self.write("skill/requirements.txt", lock_text(["pillow"], pins))
        self.append("skill/tests/test_work.py", "\nimport urllib3\n")
        report = self.check("python")
        self.assertEqual(self.keys(report), {"skill/tests/test_work.py:import:urllib3"})
        # The included runtime layer can declare it directly without changing pins.
        self.write("skill/requirements.txt", lock_text(["pillow", "urllib3"], pins))
        self.assert_clean(self.check("python"))

    def test_direct_declaration_in_an_unrelated_scope_does_not_cover_an_import(self):
        self.append("skill/scripts/work.py", "\nimport yaml\n")
        report = self.check("python")
        self.assertEqual(self.keys(report), {"skill/scripts/work.py:import:yaml"})

    def test_lock_without_a_direct_header_is_refused(self):
        self.write("requirements-tooling.txt",
                   "# Hash-locked fixture lock.\nrequests==2.34.2 \\\n"
                   f"    --hash=sha256:{HASH}\n")
        report = self.check("python")
        self.assertTrue(any("'# Direct: ...' header" in e for e in report.errors), report.errors)

    def test_missing_scope_config_is_refused(self):
        self.write("pyproject.toml", "[tool.vulture]\npaths = []\n")
        report = self.check("python")
        self.assertTrue(any("[tool.vulture] paths" in e for e in report.errors), report.errors)


class ExceptionTest(Fixture):
    KEY = "tools/demo/cli.py:import:boto3"

    def plant(self):
        self.append("tools/demo/cli.py", "\nimport boto3\n")

    def test_evidenced_exception_clears_only_its_finding(self):
        self.plant()
        self.append("tools/demo/cli.py", "\nimport botocore\n")
        report = self.check("python", exceptions={self.KEY: "lazy integration, installed on the runner"})
        self.assertEqual([f.key for f, _ in report.excepted], [self.KEY])
        self.assertEqual(self.keys(report), {"tools/demo/cli.py:import:botocore"})

    def test_exception_without_evidence_fails(self):
        self.plant()
        report = self.check("python", exceptions={self.KEY: "  "})
        self.assertTrue(any("names no evidence" in e for e in report.errors), report.errors)

    def test_stale_exception_fails(self):
        report = self.check("python", exceptions={self.KEY: "lazy integration"})
        self.assertTrue(any("EXCEPTIONS lists" in e for e in report.errors), report.errors)


class JavaScriptDetectorTest(Fixture):
    @needs(has_knip(), "knip")
    def test_clean_fixture_passes_runtime_test_and_optional_declared_usage(self):
        code, out = self.run_cli("--only", "javascript")
        self.assertEqual(code, 0, out)
        self.assertIn("unused-dependencies: PASS", out)

    @needs(has_knip(), "knip")
    def test_unused_dependency_fails(self):
        manifest = json.loads(JS_FILES["tools/feed/package.json"])
        manifest["dependencies"]["left-pad"] = "^1.3.0"
        self.write("tools/feed/package.json", json.dumps(manifest, indent=2) + "\n")
        report = self.check("javascript")
        self.assertEqual(self.keys(report), {"tools/feed/package.json:dependency:left-pad"})
        self.assertEqual(report.errors, [])

    @needs(has_knip(), "knip")
    def test_unused_dev_dependency_fails(self):
        manifest = json.loads(JS_FILES["tools/feed/package.json"])
        manifest["devDependencies"]["prettier"] = "^3.0.0"
        self.write("tools/feed/package.json", json.dumps(manifest, indent=2) + "\n")
        report = self.check("javascript")
        self.assertEqual(self.keys(report), {"tools/feed/package.json:devDependency:prettier"})

    @needs(has_knip(), "knip")
    def test_import_nothing_declares_fails(self):
        self.append("tools/feed/cli.mjs", "import _ from 'lodash';\nconsole.log(_);\n")
        report = self.check("javascript")
        self.assertEqual(self.keys(report), {"tools/feed/cli.mjs:import:lodash"})

    def test_workspace_without_a_manifest_is_an_error(self):
        config = {"workspaces": {"tools/ghost": {"entry": ["cli.mjs"], "project": ["**/*.mjs"]}}}
        self.write("tools/dead-code/knip.json", json.dumps(config))
        report = self.check("javascript")
        self.assertTrue(any("tools/ghost has no package.json" in e for e in report.errors), report.errors)


class RepositoryConfigTest(unittest.TestCase):
    def test_every_lock_names_its_direct_dependencies(self):
        locks = unused.python_locks(Path(ROOT))
        self.assertGreaterEqual(len(locks), 2)
        for lock in locks.values():
            with self.subTest(lock=lock.path):
                self.assertTrue(lock.direct, lock.path)

    def test_tooling_lock_declares_the_detectors(self):
        locks = unused.python_locks(Path(ROOT))
        tooling = locks["requirements-tooling.txt"]
        self.assertLessEqual({"pyyaml", "mypy", "vulture"}, set(tooling.direct))

    def test_one_shared_knip_configuration_covers_every_producer(self):
        configs = [p.relative_to(ROOT).as_posix() for p in Path(ROOT).glob("tools/**/knip.json")
                   if "node_modules" not in p.parts]
        self.assertEqual(configs, ["tools/dead-code/knip.json"])
        with open(os.path.join(ROOT, "tools", "dead-code", "knip.json"), encoding="utf-8") as fh:
            config = json.load(fh)
        producers = {p.parent.relative_to(ROOT).as_posix() for p in Path(ROOT).glob("tools/*/package.json")}
        self.assertEqual(set(config["workspaces"]), producers)

    def test_repository_exceptions_name_an_existing_file_and_a_reason(self):
        for key, reason in unused.EXCEPTIONS.items():
            with self.subTest(key=key):
                self.assertTrue(os.path.isfile(os.path.join(ROOT, key.split(":", 1)[0])))
                self.assertTrue(reason.strip())

    def test_workflow_runs_the_checker_and_requires_knip(self):
        with open(WORKFLOW, encoding="utf-8") as fh:
            text = fh.read()
        self.assertIn("python tools/dependency-policy/check_unused.py", text)
        self.assertIn("python -m unittest discover -s tools/dependency-policy/tests -v", text)
        self.assertIn('UNUSED_REQUIRE_TOOLS: "1"', text)
        self.assertIn("npm ci --ignore-scripts", text)
        self.assertNotRegex(text, r"\bnpm\s+install\b")
        self.assertNotRegex(text, r"\bpip[\d.]*\s+install\b(?!.*-r )")

    def test_workflow_runs_when_inspected_python_or_javascript_sources_change(self):
        text = Path(WORKFLOW).read_text(encoding="utf-8")
        changed_paths = ("tools/capability-currency/drive_docs.py",
                         "tools/plugin-sync/drift-check.py", "tools/demo/new.py",
                         "tools/capability-feed/generate-feed.mjs",
                         "tools/capability-feed/test/new.test.mjs",
                         "tools/skill-map/extract-skills-graph.mjs")
        for event in ("pull_request", "push"):
            section = re.search(r"(?ms)^  " + event + r":\n(.*?)(?=^  \w|\Z)", text)
            self.assertIsNotNone(section, event)
            patterns = re.findall(r"^      - '([^']+)'$", section.group(1), re.M)
            for path in changed_paths:
                with self.subTest(event=event, path=path):
                    self.assertTrue(any(fnmatch.fnmatchcase(path, pattern) for pattern in patterns),
                                    f"{event} does not run for {path}")

    def test_repository_python_dependencies_are_used_and_declared(self):
        report = unused.check(Path(ROOT), languages=("python",))
        self.assertEqual([str(f) for f in report.findings], [])
        self.assertEqual(report.errors, [])
        kinds = {u.kind for u in report.uses}
        self.assertLessEqual({"runtime", "test", "cli"}, {k.split(",")[0] for k in kinds})
        self.assertTrue(any(u.name == "vulture" and "optional" in u.kind for u in report.uses))

    @needs(has_knip(), "knip")
    def test_repository_has_no_unused_or_undeclared_dependencies(self):
        report = unused.check(Path(ROOT))
        self.assertEqual([str(f) for f in report.findings], [])
        self.assertEqual(report.errors, [])
        self.assertEqual(report.producers, 2)


if __name__ == "__main__":
    unittest.main()
