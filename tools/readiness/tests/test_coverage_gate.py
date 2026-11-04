"""Offline checks for the coverage floors in .github/workflows/tooling-coverage.yml.

The scope tests read the workflow, pyproject.toml and each producer's package.json and
prove that every canonical source is measured, nothing is omitted, and every floor is
nontrivial. The fixture tests run the gate's exact commands (the workflow's coverage.py
lines and each producer's "coverage" script) in a throwaway tree whose sources are
synthetic. For each declared floor they find the fixture with the most uncovered code
that still passes, then add one more uncovered unit and require a nonzero exit with
coverage under that floor. They skip when coverage.py, node or npm is missing, unless
COVERAGE_REQUIRE_TOOLS=1 is set, as the workflow does.

Run from the repo root: python3 -m unittest tools/readiness/tests/test_coverage_gate.py -v
"""

import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest
from dataclasses import dataclass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
PYPROJECT = os.path.join(ROOT, "pyproject.toml")
WORKFLOW = os.path.join(ROOT, ".github", "workflows", "tooling-coverage.yml")
REQUIRE_TOOLS = os.environ.get("COVERAGE_REQUIRE_TOOLS") == "1"

# The canonical tooling whose existing suites the gate measures.
PY_SCOPES = {"auto-merge-gate": "tools/auto-merge-gate", "plugin-sync": "tools/plugin-sync"}
JS_PRODUCERS = ["tools/capability-feed", "tools/skill-map"]
JS_METRICS = {"lines": "line", "branches": "branch", "functions": "function"}

# A floor under this is not a gate worth having.
MIN_FLOOR = 60

# Settings that would hide source or lines from the measurement.
OMITTING_SETTINGS = {"omit", "exclude_lines", "exclude_also", "partial_branches", "partial_also"}
SUPPRESSIONS = [re.compile(r"pragma:\s*no\s*cover", re.I), re.compile(r"node:coverage\s+(?:ignore|disable)")]

RUN_RE = re.compile(r"^\s*(python -m coverage run .+)$", re.M)
REPORT_RE = re.compile(r"^\s*(python -m coverage report .+)$", re.M)
PY_TOTAL_RE = re.compile(r"^TOTAL\s.*?(\d+(?:\.\d+)?)%\s*$", re.M)
JS_ALL_FILES_RE = re.compile(r"all files\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)")
JS_THRESHOLD_RE = re.compile(r"([\d.]+)% (line|branch|function) coverage does not meet threshold of (\d+(?:\.\d+)?)%")


def glob_matches(path, pattern):
    """coverage.py and node --test glob semantics: * stays in one directory."""
    regex = re.escape(pattern).replace(r"\*\*/", "(?:.*/)?").replace(r"\*", "[^/]*")
    return re.fullmatch(regex, path) is not None


def rel(path, base=ROOT):
    return os.path.relpath(path, base).replace(os.sep, "/")


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def option(args, name):
    values = [a.split("=", 1)[1] for a in args if a.startswith(name + "=")]
    if len(values) != 1:
        raise AssertionError(f"expected one {name}= in {args}")
    return values[0]


@dataclass
class PythonGate:
    run: str
    report: str
    data_file: str
    source: str
    tests: str
    include: str
    floor: float


def python_gates():
    text = read(WORKFLOW)
    runs, reports = RUN_RE.findall(text), REPORT_RE.findall(text)
    by_data = {option(shlex.split(r), "--data-file"): r for r in reports}
    gates = {}
    for run in runs:
        args = shlex.split(run)
        data_file = option(args, "--data-file")
        report = by_data[data_file]
        report_args = shlex.split(report)
        source = option(args, "--source")
        gates[source] = PythonGate(
            run=run, report=report, data_file=data_file, source=source,
            tests=args[args.index("-s") + 1], include=option(report_args, "--include"),
            floor=float(option(report_args, "--fail-under")))
    return gates


def coverage_config():
    with open(PYPROJECT, "rb") as fh:
        return tomllib.load(fh)["tool"]["coverage"]


def python_sources(scope):
    folder = os.path.join(ROOT, scope)
    return sorted(f"{scope}/{name}" for name in os.listdir(folder) if name.endswith(".py"))


@dataclass
class NodeGate:
    script: str
    includes: list
    floors: dict


def node_gate(producer):
    with open(os.path.join(ROOT, producer, "package.json"), encoding="utf-8") as fh:
        scripts = json.load(fh)["scripts"]
    script = scripts["coverage"]
    args = shlex.split(script)
    floors = {}
    for metric in JS_METRICS:
        floors[metric] = float(option(args, f"--test-coverage-{metric}"))
    includes = [a.split("=", 1)[1] for a in args if a.startswith("--test-coverage-include=")]
    return NodeGate(script=script, includes=includes, floors=floors), scripts["test"]


def js_sources(producer):
    base = os.path.join(ROOT, producer)
    found = []
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d not in ("node_modules", "test")]
        found += [rel(os.path.join(dirpath, f), base) for f in filenames if f.endswith((".mjs", ".js", ".cjs"))]
    return sorted(found)


def has_coverage():
    return subprocess.run([sys.executable, "-m", "coverage", "--version"], capture_output=True).returncode == 0


def needs(available, what):
    if available:
        return lambda func: func
    if REQUIRE_TOOLS:
        def fail(self):
            self.fail(f"{what} is not installed and COVERAGE_REQUIRE_TOOLS=1")
        return lambda func: fail
    return unittest.skip(f"{what} is not installed")


class PythonScopeTest(unittest.TestCase):
    def test_workflow_declares_one_gate_per_python_scope(self):
        self.assertEqual(sorted(python_gates()), sorted(PY_SCOPES.values()))

    def test_each_gate_measures_its_suite_and_every_source(self):
        for scope, gate in python_gates().items():
            with self.subTest(scope=scope):
                self.assertEqual(gate.tests, f"{scope}/tests")
                self.assertEqual(gate.include, f"{scope}/*.py")
                self.assertIn("-m unittest discover", gate.run)
                sources = python_sources(scope)
                self.assertTrue(sources)
                for path in sources:
                    self.assertTrue(glob_matches(path, gate.include), path)
                self.assertFalse(glob_matches(f"{scope}/tests/test_x.py", gate.include))

    def test_floors_are_nontrivial(self):
        for scope, gate in python_gates().items():
            with self.subTest(scope=scope):
                self.assertGreaterEqual(gate.floor, MIN_FLOOR)
                self.assertLessEqual(gate.floor, 100)

    def test_branches_and_child_processes_count_and_nothing_is_omitted(self):
        config = coverage_config()
        self.assertIs(config["run"].get("branch"), True)
        self.assertEqual(config["run"].get("patch"), ["subprocess"])
        for section in config.values():
            self.assertFalse(OMITTING_SETTINGS & set(section), section)
        for gate in python_gates().values():
            for command in (gate.run, gate.report):
                with self.subTest(command=command):
                    self.assertNotRegex(command, r"--omit|--skip-covered|--skip-empty")


class JavaScriptScopeTest(unittest.TestCase):
    def test_coverage_script_runs_the_same_suite_as_test(self):
        for producer in JS_PRODUCERS:
            with self.subTest(producer=producer):
                gate, test_script = node_gate(producer)
                self.assertTrue(test_script.startswith("node --test "), test_script)
                self.assertTrue(gate.script.startswith("node --test --experimental-test-coverage "), gate.script)
                self.assertEqual(shlex.split(gate.script)[-1], shlex.split(test_script)[-1])

    def test_includes_name_every_source_and_no_test(self):
        for producer in JS_PRODUCERS:
            gate, _ = node_gate(producer)
            self.assertTrue(gate.includes, producer)
            for path in js_sources(producer):
                with self.subTest(producer=producer, path=path):
                    self.assertTrue(any(glob_matches(path, p) for p in gate.includes), path)
            for path in os.listdir(os.path.join(ROOT, producer, "test")):
                with self.subTest(producer=producer, test=path):
                    self.assertFalse(any(glob_matches(f"test/{path}", p) for p in gate.includes))

    def test_every_metric_has_a_nontrivial_floor_and_nothing_is_excluded(self):
        for producer in JS_PRODUCERS:
            gate, _ = node_gate(producer)
            self.assertNotIn("--test-coverage-exclude", gate.script)
            for metric, floor in gate.floors.items():
                with self.subTest(producer=producer, metric=metric):
                    self.assertGreaterEqual(floor, MIN_FLOOR)
                    self.assertLessEqual(floor, 100)


class SuppressionTest(unittest.TestCase):
    def test_no_measured_source_excludes_itself(self):
        paths = [os.path.join(ROOT, p) for scope in PY_SCOPES.values() for p in python_sources(scope)]
        paths += [os.path.join(ROOT, producer, p) for producer in JS_PRODUCERS for p in js_sources(producer)]
        for path in paths:
            text = read(path)
            for pattern in SUPPRESSIONS:
                with self.subTest(path=rel(path), pattern=pattern.pattern):
                    self.assertIsNone(pattern.search(text))


class WorkflowTest(unittest.TestCase):
    def test_workflow_installs_from_locks_and_runs_every_gate(self):
        text = read(WORKFLOW)
        self.assertIn("--require-hashes -r requirements-tooling.txt", text)
        self.assertIn("npm ci --ignore-scripts", text)
        for producer in JS_PRODUCERS:
            with self.subTest(producer=producer):
                self.assertRegex(text, rf"working-directory: {re.escape(producer)}\n\s+run: npm run coverage\n")
        self.assertIn('COVERAGE_REQUIRE_TOOLS: "1"', text)
        self.assertIn("python -m unittest tools/readiness/tests/test_coverage_gate.py", text)

    def test_coverage_is_a_hash_locked_direct_dependency(self):
        text = read(os.path.join(ROOT, "requirements-tooling.txt"))
        self.assertRegex(text, r"(?m)^# Direct: .*\bcoverage\b")
        self.assertRegex(text, r"(?m)^coverage==\d+\.\d+\.\d+ \\\n\s+--hash=sha256:")


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def find_boundary(probe, metric, limit=1 << 14):
    """The largest count of uncovered units that still passes, given probe(n) -> (ok, output).
    Coverage only falls as uncovered units are added, so the boundary is unique."""
    ok, output = probe(0)
    if not ok:
        raise AssertionError(f"fully covered {metric} fixture failed:\n{output}")
    passing, failing = 0, 1
    while True:
        ok, output = probe(failing)
        if not ok:
            break
        passing, failing = failing, failing * 2
        if failing > limit:
            raise AssertionError(f"{metric}: {limit} uncovered units never fell under the floor")
    while failing - passing > 1:
        middle = (passing + failing) // 2
        if probe(middle)[0]:
            passing = middle
        else:
            failing = middle
    return passing


PY_BODY = "".join(f"    v{j} = {j}\n" for j in range(3)) + "    return v0\n"


def python_fixture_module(covered, uncovered):
    lines = [f"def c{i}():\n{PY_BODY}" for i in range(covered)]
    lines += [f"def u{i}():\n    return {i}\n" for i in range(uncovered)]
    return "\n".join(lines) or "VALUE = 0\n"


def python_fixture_test(paths, scope):
    depth = scope.count("/") + 2
    return (
        "import importlib.util\nimport os\nimport unittest\n\n"
        f"ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), *['..'] * {depth}))\n"
        f"PATHS = {paths!r}\n\n\n"
        "class Fixture(unittest.TestCase):\n"
        "    def test_calls_every_covered_function(self):\n"
        "        for i, path in enumerate(PATHS):\n"
        "            spec = importlib.util.spec_from_file_location(f'fixture_{i}', os.path.join(ROOT, path))\n"
        "            module = importlib.util.module_from_spec(spec)\n"
        "            spec.loader.exec_module(module)\n"
        "            for name in dir(module):\n"
        "                if name.startswith('c'):\n"
        "                    getattr(module, name)()\n"
    )


class PythonFloorFixtureTest(unittest.TestCase):
    """Runs the workflow's own coverage.py lines against synthetic sources at the real paths."""

    COVERED_FUNCTIONS = 60

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="coverage-py-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        shutil.copyfile(PYPROJECT, os.path.join(self.tmp, "pyproject.toml"))
        shim = os.path.join(self.tmp, ".bin")
        # A wrapper rather than a symlink, so a virtual environment's interpreter keeps its packages.
        write(os.path.join(shim, "python"), f'#!/bin/sh\nexec {shlex.quote(sys.executable)} "$@"\n')
        os.chmod(os.path.join(shim, "python"), 0o755)
        self.env = dict(os.environ, PATH=shim + os.pathsep + os.environ.get("PATH", ""))

    def gate(self, gate, sources, uncovered):
        shutil.rmtree(os.path.join(self.tmp, gate.source), ignore_errors=True)
        for i, path in enumerate(sources):
            covered = self.COVERED_FUNCTIONS if i == 0 else 1
            write(os.path.join(self.tmp, path), python_fixture_module(covered, uncovered if i == 0 else 0))
        write(os.path.join(self.tmp, gate.tests, "test_fixture.py"), python_fixture_test(sources, gate.source))
        result = subprocess.run(["bash", "-c", f"set -e\n{gate.run}\n{gate.report}\n"],
                                cwd=self.tmp, env=self.env, capture_output=True, text=True)
        return result.returncode == 0, result.stdout + result.stderr

    @needs(has_coverage(), "coverage.py")
    def test_one_statement_under_each_floor_fails_and_the_floor_passes(self):
        for scope, gate in python_gates().items():
            with self.subTest(scope=scope, floor=gate.floor):
                sources = python_sources(scope)
                probe = lambda n: self.gate(gate, sources, n)
                boundary = find_boundary(probe, scope)
                ok, output = probe(boundary)
                self.assertTrue(ok, output)
                self.assertGreaterEqual(float(PY_TOTAL_RE.search(output).group(1)), gate.floor, output)
                ok, output = probe(boundary + 1)
                self.assertFalse(ok, output)
                self.assertLess(float(PY_TOTAL_RE.search(output).group(1)), gate.floor, output)
                self.assertRegex(output, rf"Coverage failure: total of [\d.]+ is less than fail-under={gate.floor:g}\b")
                for path in sources:
                    self.assertIn(path, output)


def js_fixture_module(metric, uncovered):
    """A synthetic source that is fully covered at uncovered=0. Each added unit leaves one
    line, one branch or one function unrun, and only that metric falls."""
    out = ["export function base(x) {", "  let y = 0;"]
    out += [f"  if (x === 0) y += {i};" for i in range(100)]
    if metric == "lines" and uncovered:
        out += ["  if (x === -1) {"] + [f"    y += {i};" for i in range(uncovered)] + ["  }"]
    if metric == "branches":
        out += [f"  if (x === -1) y -= {i};" for i in range(uncovered)]
    out += ["  return y;", "}"]
    out += [f"export function c{i}() {{ return {i}; }}" for i in range(100)]
    if metric == "functions":
        out += [f"const a{i} = {i}; export function u{i}() {{ return a{i}; }}" for i in range(uncovered)]
    return "\n".join(out) + "\n"


def js_fixture_test(paths):
    imports = "".join(f"import * as m{i} from '../{p}';\n" for i, p in enumerate(paths))
    modules = ", ".join(f"m{i}" for i in range(len(paths)))
    return (
        "import { test } from 'node:test';\n" + imports +
        "test('fixture', () => {\n"
        f"  for (const m of [{modules}]) {{\n"
        "    m.base(0);\n    m.base(1);\n"
        "    for (const [name, fn] of Object.entries(m)) if (name.startsWith('c')) fn();\n"
        "  }\n});\n"
    )


class JavaScriptFloorFixtureTest(unittest.TestCase):
    """Runs each producer's own "coverage" script against synthetic sources at the real paths."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="coverage-js-")
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def gate(self, producer, metric, uncovered):
        work = os.path.join(self.tmp, producer)
        shutil.rmtree(work, ignore_errors=True)
        os.makedirs(work)
        shutil.copyfile(os.path.join(ROOT, producer, "package.json"), os.path.join(work, "package.json"))
        sources = js_sources(producer)
        for i, path in enumerate(sources):
            write(os.path.join(work, path), js_fixture_module(metric, uncovered if i == 0 else 0))
        write(os.path.join(work, "test", "fixture.test.mjs"), js_fixture_test(sources))
        result = subprocess.run(["npm", "run", "--silent", "coverage"], cwd=work, capture_output=True, text=True)
        return result.returncode == 0, result.stdout + result.stderr

    @needs(shutil.which("node") and shutil.which("npm"), "node and npm")
    def test_one_unit_under_each_floor_fails_and_the_floor_passes(self):
        for producer in JS_PRODUCERS:
            gate, _ = node_gate(producer)
            for index, (metric, word) in enumerate(JS_METRICS.items()):
                floor = gate.floors[metric]
                with self.subTest(producer=producer, metric=metric, floor=floor):
                    probe = lambda n: self.gate(producer, metric, n)
                    boundary = find_boundary(probe, f"{producer} {metric}")
                    ok, output = probe(boundary)
                    self.assertTrue(ok, output)
                    self.assertNotIn("does not meet threshold", output)
                    self.assertGreaterEqual(float(JS_ALL_FILES_RE.search(output).group(index + 1)), floor, output)
                    ok, output = probe(boundary + 1)
                    self.assertFalse(ok, output)
                    failures = {m[1]: (float(m[0]), float(m[2])) for m in JS_THRESHOLD_RE.findall(output)}
                    self.assertEqual(set(failures), {word}, output)
                    measured, threshold = failures[word]
                    self.assertEqual(threshold, floor)
                    self.assertLess(measured, floor)
                    for path in js_sources(producer):
                        self.assertIn(os.path.basename(path), output)


if __name__ == "__main__":
    unittest.main()
