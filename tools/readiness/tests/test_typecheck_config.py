"""Offline checks for the source type-check configuration: pyproject.toml ([tool.mypy])
for the Python tooling and jsconfig.json for the JavaScript producers.

The scope tests read the configuration and the tree only. The checker tests run mypy and
tsc against throwaway copies of the scoped sources, so an intentional type error never
touches a real file. They skip when a checker is not installed, unless
TYPECHECK_REQUIRE_TOOLS=1 is set, as .github/workflows/tooling-typecheck.yml does.

Run from the repo root: python3 -m unittest discover -s tools/readiness/tests -v
"""

import fnmatch
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
PYPROJECT = os.path.join(ROOT, "pyproject.toml")
JSCONFIG = os.path.join(ROOT, "jsconfig.json")
WORKFLOW = os.path.join(ROOT, ".github", "workflows", "tooling-typecheck.yml")
REQUIRE_TOOLS = os.environ.get("TYPECHECK_REQUIRE_TOOLS") == "1"

# Every executable Python source the type check must cover. Tests directories are not
# listed: they are not in this check's scope.
PY_SCOPE_GLOBS = [
    "tools/auto-merge-gate/gate.py",
    "tools/plugin-sync/*.py",
    "tools/capability-currency/drive_docs.py",
    "plugins/research-ops/skills/source-hunter/scripts/*.py",
    "plugins/research-ops/skills/video-discovery/scripts/*.py",
]

# Every JavaScript producer, source and tests alike. Only installed packages are left out.
JS_PRODUCERS = ["tools/capability-feed", "tools/skill-map"]
JS_VENDOR_DIRS = {"node_modules"}

# The only third-party relaxations allowed. yt-dlp ships no py.typed marker, so mypy reads
# its source and exempts its unannotated functions from the untyped-call rule. The others
# are imported lazily, live in no lock, and are not installed where the check runs.
UNTYPED_FOLLOWED = {"yt_dlp", "yt_dlp.*"}
NOT_INSTALLED = {"googleapiclient.*", "google.oauth2.*", "playwright.*"}
THIRD_PARTY = UNTYPED_FOLLOWED | NOT_INSTALLED
ALLOWED_OVERRIDES = [
    ({"follow_untyped_imports": True}, UNTYPED_FOLLOWED),
    ({"ignore_missing_imports": True}, NOT_INSTALLED),
]

SUPPRESSIONS = [
    re.compile(r"#\s*type:\s*ignore"),
    re.compile(r"#\s*mypy:"),
    re.compile(r"#\s*pyright:"),
    re.compile(r"@ts-(?:ignore|nocheck|expect-error)"),
]

PY_STATIC_ERROR = '\n_typecheck_probe: int = "not an int"\n'
PY_STRICT_ONLY_ERROR = "\n\ndef _typecheck_probe(value):\n    return value\n"
JS_STATIC_ERROR = "\n/** @type {number} */\nconst typecheckProbe = 'not a number';\nvoid typecheckProbe;\n"
JS_STRICT_ONLY_ERROR = "\nexport function typecheckProbe(value) {\n  return value;\n}\n"


def include_matches(path, pattern):
    """tsconfig include semantics: ** spans zero or more directories, * stays in one."""
    regex = re.escape(pattern).replace(r"\*\*/", "(?:.*/)?").replace(r"\*", "[^/]*")
    return re.fullmatch(regex, path) is not None


def rel(path):
    return os.path.relpath(path, ROOT).replace(os.sep, "/")


def expected_python_files():
    found = set()
    for pattern in PY_SCOPE_GLOBS:
        found.update(rel(p) for p in glob.glob(os.path.join(ROOT, pattern)))
    return found


def mypy_config():
    with open(PYPROJECT, "rb") as fh:
        return tomllib.load(fh)["tool"]["mypy"]


def configured_python_files():
    found = set()
    for entry in mypy_config()["files"]:
        path = os.path.join(ROOT, entry)
        if os.path.isdir(path):
            for dirpath, dirnames, filenames in os.walk(path):
                dirnames[:] = [d for d in dirnames if d != "__pycache__"]
                found.update(rel(os.path.join(dirpath, f)) for f in filenames if f.endswith(".py"))
        else:
            found.add(entry)
    return found


def javascript_files():
    found = set()
    for producer in JS_PRODUCERS:
        for dirpath, dirnames, filenames in os.walk(os.path.join(ROOT, producer)):
            dirnames[:] = [d for d in dirnames if d not in JS_VENDOR_DIRS]
            found.update(rel(os.path.join(dirpath, f)) for f in filenames if f.endswith((".js", ".mjs", ".cjs")))
    return found


def jsconfig():
    with open(JSCONFIG, encoding="utf-8") as fh:
        return json.load(fh)


def has_mypy():
    return subprocess.run([sys.executable, "-m", "mypy", "--version"], capture_output=True).returncode == 0


def tsc_path():
    for producer in JS_PRODUCERS:
        candidate = os.path.join(ROOT, producer, "node_modules", ".bin", "tsc")
        if os.path.exists(candidate):
            return candidate
    return None


def needs(available, what):
    if available:
        return lambda func: func
    if REQUIRE_TOOLS:
        def fail(self):
            self.fail(f"{what} is not installed and TYPECHECK_REQUIRE_TOOLS=1")
        return lambda func: fail
    return unittest.skip(f"{what} is not installed")


class PythonScopeTest(unittest.TestCase):
    def test_strict_mode_is_on_for_python_3_12(self):
        config = mypy_config()
        self.assertIs(config.get("strict"), True)
        self.assertEqual(config.get("python_version"), "3.12")

    def test_files_cover_every_executable_module_and_nothing_else(self):
        expected = expected_python_files()
        self.assertTrue(expected)
        self.assertEqual(configured_python_files(), expected)

    def test_every_listed_directory_has_covered_modules(self):
        configured = configured_python_files()
        for pattern in PY_SCOPE_GLOBS:
            with self.subTest(pattern=pattern):
                self.assertTrue(any(fnmatch.fnmatch(path, pattern) for path in configured))

    def test_nothing_is_excluded_and_no_override_relaxes_checking(self):
        config = mypy_config()
        self.assertNotIn("exclude", config)
        self.assertNotIn("follow_imports", config)
        self.assertNotIn("disable_error_code", config)
        self.assertEqual(config.get("untyped_calls_exclude"), ["yt_dlp"])
        for override in config.get("overrides", []):
            with self.subTest(override=override):
                modules = override["module"] if isinstance(override["module"], list) else [override["module"]]
                settings = {k: v for k, v in override.items() if k != "module"}
                self.assertIn((settings, set(modules)), ALLOWED_OVERRIDES)

    def test_third_party_names_are_not_repository_modules(self):
        local = {os.path.splitext(os.path.basename(p))[0] for p in configured_python_files()}
        for name in THIRD_PARTY:
            with self.subTest(module=name):
                self.assertNotIn(name.split(".")[0], local)


class JavaScriptScopeTest(unittest.TestCase):
    def test_checking_is_strict_and_emits_nothing(self):
        options = jsconfig()["compilerOptions"]
        for key in ("allowJs", "checkJs", "strict", "noEmit"):
            with self.subTest(option=key):
                self.assertIs(options.get(key), True)

    def test_include_covers_every_producer_source_and_test(self):
        includes = jsconfig()["include"]
        for path in javascript_files():
            with self.subTest(path=path):
                self.assertTrue(any(include_matches(path, pattern) for pattern in includes), path)

    def test_only_installed_packages_are_excluded(self):
        self.assertEqual(jsconfig().get("exclude"), ["**/node_modules"])

    def test_generated_data_is_not_in_scope(self):
        for pattern in jsconfig()["include"]:
            with self.subTest(pattern=pattern):
                self.assertTrue(pattern.endswith(".mjs"), pattern)

    def test_both_producers_pin_the_same_checker(self):
        specs = []
        for producer in JS_PRODUCERS:
            with open(os.path.join(ROOT, producer, "package.json"), encoding="utf-8") as fh:
                dev = json.load(fh).get("devDependencies", {})
            self.assertRegex(dev.get("typescript", ""), r"^\d+\.\d+\.\d+$", producer)
            self.assertRegex(dev.get("@types/node", ""), r"^\d+\.\d+\.\d+$", producer)
            specs.append((dev["typescript"], dev["@types/node"]))
        self.assertEqual(len(set(specs)), 1, specs)

    @needs(tsc_path(), "tsc")
    def test_compiler_lists_exactly_the_producer_files(self):
        result = subprocess.run([tsc_path(), "-p", JSCONFIG, "--listFilesOnly"],
                                capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        listed = {rel(line.strip()) for line in result.stdout.splitlines()
                  if line.strip() and "/node_modules/" not in line}
        self.assertEqual(listed, javascript_files())


class SuppressionTest(unittest.TestCase):
    def test_no_scoped_source_silences_the_checker(self):
        for path in sorted(configured_python_files() | javascript_files()):
            with open(os.path.join(ROOT, path), encoding="utf-8") as fh:
                text = fh.read()
            for pattern in SUPPRESSIONS:
                with self.subTest(path=path, pattern=pattern.pattern):
                    self.assertIsNone(pattern.search(text))


class WorkflowTest(unittest.TestCase):
    def test_workflow_runs_both_checkers_and_requires_them_in_these_tests(self):
        with open(WORKFLOW, encoding="utf-8") as fh:
            text = fh.read()
        self.assertIn("python -m mypy", text)
        self.assertRegex(text, r"node_modules/\.bin/tsc -p jsconfig\.json")
        self.assertIn("TYPECHECK_REQUIRE_TOOLS: \"1\"", text)
        self.assertIn("--require-hashes -r requirements-tooling.txt", text)


def copy_into(tmp, paths):
    for path in paths:
        target = os.path.join(tmp, path)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.copyfile(os.path.join(ROOT, path), target)


def append(tmp, path, text):
    with open(os.path.join(tmp, path), "a", encoding="utf-8") as fh:
        fh.write(text)


def first_per_scope(paths, patterns):
    picks = []
    for pattern in patterns:
        picks.append(sorted(p for p in paths if fnmatch.fnmatch(p, pattern))[0])
    return picks


class PythonCheckerTest(unittest.TestCase):
    """Runs mypy on copies of every scoped module, once strict and once with the same
    configuration minus strict mode (the ordinary static check)."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="typecheck-py-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.files = sorted(configured_python_files())
        copy_into(self.tmp, self.files)
        with open(PYPROJECT, encoding="utf-8") as fh:
            canonical = fh.read()
        self.assertEqual(canonical.count("\nstrict = true\n"), 1)
        with open(os.path.join(self.tmp, "pyproject.toml"), "w", encoding="utf-8") as fh:
            fh.write(canonical)
        with open(os.path.join(self.tmp, "ordinary.toml"), "w", encoding="utf-8") as fh:
            fh.write(canonical.replace("\nstrict = true\n", "\n"))
        self.probes = first_per_scope(self.files, PY_SCOPE_GLOBS)

    def mypy(self, config):
        return subprocess.run(
            [sys.executable, "-m", "mypy", "--config-file", config, "--cache-dir", os.path.join(self.tmp, ".cache")],
            capture_output=True, text=True, cwd=self.tmp)

    def assert_flags_every_probe(self, result):
        self.assertNotEqual(result.returncode, 0, result.stdout)
        for path in self.probes:
            with self.subTest(path=path):
                self.assertRegex(result.stdout, re.escape(path) + r":\d+: error:")

    @needs(has_mypy(), "mypy")
    def test_clean_copies_pass_strict_and_ordinary(self):
        for config in ("pyproject.toml", "ordinary.toml"):
            with self.subTest(config=config):
                result = self.mypy(config)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @needs(has_mypy(), "mypy")
    def test_static_error_fails_ordinary_and_strict_in_every_scope(self):
        for path in self.probes:
            append(self.tmp, path, PY_STATIC_ERROR)
        for config in ("ordinary.toml", "pyproject.toml"):
            with self.subTest(config=config):
                result = self.mypy(config)
                self.assert_flags_every_probe(result)
                self.assertIn("[assignment]", result.stdout)

    @needs(has_mypy(), "mypy")
    def test_untyped_function_fails_strict_only(self):
        for path in self.probes:
            append(self.tmp, path, PY_STRICT_ONLY_ERROR)
        strict = self.mypy("pyproject.toml")
        self.assert_flags_every_probe(strict)
        self.assertIn("[no-untyped-def]", strict.stdout)
        ordinary = self.mypy("ordinary.toml")
        self.assertEqual(ordinary.returncode, 0, ordinary.stdout + ordinary.stderr)


class JavaScriptCheckerTest(unittest.TestCase):
    """Runs tsc on copies of every producer source and test, strict and with strict off."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="typecheck-js-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.files = sorted(javascript_files())
        copy_into(self.tmp, self.files + ["jsconfig.json"] + [f"{p}/package.json" for p in JS_PRODUCERS])
        for producer in JS_PRODUCERS:
            modules = os.path.join(ROOT, producer, "node_modules")
            if os.path.isdir(modules):
                os.symlink(modules, os.path.join(self.tmp, producer, "node_modules"))
        self.probes = first_per_scope(self.files, [f"{p}/*" for p in JS_PRODUCERS])

    def tsc(self, *extra):
        return subprocess.run([tsc_path(), "-p", os.path.join(self.tmp, "jsconfig.json"), "--pretty", "false", *extra],
                              capture_output=True, text=True, cwd=self.tmp)

    def assert_flags_every_probe(self, result, code):
        self.assertNotEqual(result.returncode, 0, result.stdout)
        for path in self.probes:
            with self.subTest(path=path):
                self.assertRegex(result.stdout, re.escape(path) + r"\(\d+,\d+\): error " + code)

    @needs(tsc_path(), "tsc")
    def test_clean_copies_pass_strict_and_ordinary(self):
        for extra in ((), ("--strict", "false")):
            with self.subTest(flags=extra):
                result = self.tsc(*extra)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @needs(tsc_path(), "tsc")
    def test_static_error_fails_ordinary_and_strict_in_every_producer(self):
        for path in self.probes:
            append(self.tmp, path, JS_STATIC_ERROR)
        for extra in (("--strict", "false"), ()):
            with self.subTest(flags=extra):
                self.assert_flags_every_probe(self.tsc(*extra), "TS2322")

    @needs(tsc_path(), "tsc")
    def test_implicit_any_fails_strict_only(self):
        for path in self.probes:
            append(self.tmp, path, JS_STRICT_ONLY_ERROR)
        self.assert_flags_every_probe(self.tsc(), "TS7006")
        ordinary = self.tsc("--strict", "false")
        self.assertEqual(ordinary.returncode, 0, ordinary.stdout + ordinary.stderr)


if __name__ == "__main__":
    unittest.main()
