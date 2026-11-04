#!/usr/bin/env python3
"""Find unused executable code in the canonical marketplace tooling.

Python: vulture lists unused functions, classes, methods, properties, imports and
unreachable statements across the [tool.vulture] paths in pyproject.toml. This runner adds
module reachability: every module must be reached from a source-based entrypoint (a
__main__ guard, a test module the unittest or pytest runner discovers, or a path that a
workflow, shell script, launchd plist or SKILL.md runs) through imports or a literal file
path that a loader opens. Definitions that Python, unittest, pytest or a standard library
base class calls by name are dispatched, not dead, and each one is reported with the
evidence found in the source.

JavaScript: knip lists unused files and exports in each producer that
tools/dead-code/knip.json names, starting from that producer's explicit entry files. The
runner checks those entries against what package.json scripts and workflows actually run.

Offline: it reads the tree and runs the installed detectors, and never makes a network
request. Exit 0 when nothing unused is found, 1 otherwise. tools/dead-code/README.md has
usage and the exception rules.
"""

from __future__ import annotations

import argparse
import ast
import builtins
import fnmatch
import importlib
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
import tomllib
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

REPO_ROOT = Path(__file__).resolve().parents[2]
PYPROJECT = "pyproject.toml"
KNIP_CONFIG = "tools/dead-code/knip.json"
WORKFLOWS_DIR = ".github/workflows"
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", ".mypy_cache", ".pytest_cache"}
LANGUAGES = ("python", "javascript")

# vulture kinds that are executable code. "variable" and "attribute" are data: dataclass
# fields read through asdict(), JSON-shaped records, protocol parameters such as the tb of
# __exit__, and attributes a library reads (Session.trust_env). A name alone cannot tell
# those from dead data, so they stay outside this gate.
PY_KINDS = ("function", "method", "class", "property", "import", "unreachable_code")

# knip issue types that are code. Dependency declarations belong to tools/dependency-policy.
KNIP_INCLUDE = ("files", "exports", "nsExports", "types", "nsTypes", "enumMembers",
                "namespaceMembers", "duplicates", "unresolved")

TESTCASE_BASES = {"TestCase", "IsolatedAsyncioTestCase"}
UNITTEST_MODULE_HOOKS = {"setUpModule", "tearDownModule", "load_tests"}
TEST_METHOD_HOOKS = {"setUp", "tearDown", "setUpClass", "tearDownClass", "asyncSetUp", "asyncTearDown"}
PATH_CALLS = {"join", "Path", "PurePath", "PurePosixPath"}
IMPORT_CALLS = {"import_module", "__import__"}
JS_SUFFIXES = (".mjs", ".cjs", ".js")
GLOB_CHARS = "*?["

# Findings that are not dead code. Each value names the dynamic use, with its source
# location, that the detector cannot see. Key: "<path>:<kind>:<name>". An entry fails once
# its finding is gone, so an exception cannot outlive the use it records.
EXCEPTIONS: dict[str, str] = {}

# Real findings in files that this gate's own change does not own. They print as WARN
# until the owner removes or uses the code. An entry fails once its finding is gone.
PENDING_FINDINGS: dict[str, str] = {
    "plugins/research-ops/skills/source-hunter/scripts/stitch.py:function:_numbers":
        "no caller in any scoped module or test; the source-hunter owner removes or uses it",
    "tools/plugin-sync/chatgpt-import-check.py:import:zipfile":
        "imported and never used; the plugin-sync owner removes the import",
}

DefNode = ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef


class ConfigError(Exception):
    """The detector configuration is missing or malformed."""


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    kind: str
    name: str
    message: str

    @property
    def key(self) -> str:
        return f"{self.path}:{self.kind}:{self.name}"

    def __str__(self) -> str:
        return f"{self.path}:{self.line}: {self.kind} {self.name!r}: {self.message}"


@dataclass(frozen=True)
class Entry:
    path: str
    kind: str
    evidence: str


@dataclass
class Report:
    entries: list[Entry] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    dispatched: list[tuple[Finding, str]] = field(default_factory=list)
    excepted: list[tuple[Finding, str]] = field(default_factory=list)
    pending: list[tuple[Finding, str]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    modules: dict[str, int] = field(default_factory=dict)


def rel(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def walk(base: Path) -> Iterator[Path]:
    if base.is_file():
        yield base
        return
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for name in sorted(filenames):
            yield Path(dirpath) / name


def excluded(path: Path, patterns: list[str]) -> bool:
    """vulture's exclude rule: a pattern with no glob character matches as a substring."""
    text = str(path).lower()
    for pattern in patterns:
        if not any(char in pattern for char in GLOB_CHARS):
            pattern = f"*{pattern}*"
        if fnmatch.fnmatchcase(text, pattern.lower()):
            return True
    return False


def has_glob(text: str) -> bool:
    return any(char in text for char in GLOB_CHARS)


# ---------------------------------------------------------------------------
# Python: configuration, entrypoint inventory and module reachability
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PythonConfig:
    paths: list[str]
    min_confidence: int
    exclude: list[str]


def python_config(root: Path) -> PythonConfig:
    path = root / PYPROJECT
    if not path.is_file():
        raise ConfigError(f"{PYPROJECT} is missing")
    with open(path, "rb") as fh:
        table = tomllib.load(fh).get("tool", {}).get("vulture")
    if not isinstance(table, dict):
        raise ConfigError(f"{PYPROJECT} has no [tool.vulture] table")
    paths, confidence = table.get("paths"), table.get("min_confidence")
    if not isinstance(paths, list) or not paths or not all(isinstance(p, str) for p in paths):
        raise ConfigError("[tool.vulture] paths must be a non-empty list of paths")
    if not isinstance(confidence, int):
        raise ConfigError("[tool.vulture] min_confidence must be an integer")
    exclude = table.get("exclude", [])
    if not isinstance(exclude, list) or not all(isinstance(p, str) for p in exclude):
        raise ConfigError("[tool.vulture] exclude must be a list of patterns")
    return PythonConfig(paths, confidence, exclude)


def python_modules(root: Path, config: PythonConfig, report: Report) -> dict[str, ast.Module]:
    modules: dict[str, ast.Module] = {}
    for entry in config.paths:
        base = root / entry
        if not base.exists():
            report.errors.append(f"[tool.vulture] path {entry} does not exist")
            continue
        for path in walk(base):
            if path.suffix != ".py" or excluded(path, config.exclude):
                continue
            where = rel(root, path)
            try:
                modules[where] = ast.parse(path.read_text(encoding="utf-8"), filename=where)
            except SyntaxError as exc:
                report.errors.append(f"{where}: cannot parse ({exc.msg})")
    return modules


def main_guard_line(tree: ast.Module) -> int | None:
    for node in tree.body:
        if not (isinstance(node, ast.If) and isinstance(node.test, ast.Compare)):
            continue
        test = node.test
        if len(test.ops) != 1 or not isinstance(test.ops[0], ast.Eq):
            continue
        sides = [test.left, *test.comparators]
        names = {s.id for s in sides if isinstance(s, ast.Name)}
        values = {s.value for s in sides if isinstance(s, ast.Constant)}
        if names == {"__name__"} and values == {"__main__"}:
            return node.lineno
    return None


def is_test_module(path: str) -> bool:
    pure = PurePosixPath(path)
    in_tests = any(part in ("tests", "test") for part in pure.parts[:-1])
    named = fnmatch.fnmatchcase(pure.name, "test_*.py") or fnmatch.fnmatchcase(pure.name, "*_test.py")
    return in_tests and (named or pure.name == "conftest.py")


def invocation_sources(root: Path) -> list[Path]:
    """Files that run tooling by path: workflows, shell scripts, launchd plists, SKILL.md."""
    found = []
    for path in walk(root):
        top = rel(root, path)
        if top.startswith(WORKFLOWS_DIR + "/") and path.suffix in (".yml", ".yaml"):
            found.append(path)
        elif path.suffix in (".sh", ".plist") or path.name == "SKILL.md":
            found.append(path)
    return found


def path_pattern(text: str) -> re.Pattern[str]:
    return re.compile(r"(?<![\w.-])" + re.escape(text) + r"(?![\w-])")


def python_invocations(root: Path, modules: dict[str, ast.Module]) -> list[Entry]:
    entries = []
    for source in invocation_sources(root):
        source_rel = rel(root, source)
        try:
            lines = source.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        if source.suffix != ".plist" and source.name != "SKILL.md":
            lines = ["" if line.lstrip().startswith("#") else line for line in lines]
        source_dir = PurePosixPath(source_rel).parent
        for module in modules:
            spellings = [module]
            if source_dir != PurePosixPath(".") and PurePosixPath(module).is_relative_to(source_dir):
                spellings.append(PurePosixPath(module).relative_to(source_dir).as_posix())
            patterns = [path_pattern(s) for s in spellings]
            for number, line in enumerate(lines, start=1):
                if any(p.search(line) for p in patterns):
                    entries.append(Entry(module, "run", f"{source_rel}:{number}"))
                    break
    return entries


def python_entries(root: Path, modules: dict[str, ast.Module]) -> list[Entry]:
    entries = []
    for path, tree in sorted(modules.items()):
        guard = main_guard_line(tree)
        if guard is not None:
            entries.append(Entry(path, "cli", f"__main__ guard at line {guard}"))
        if is_test_module(path):
            entries.append(Entry(path, "test", "discovered by unittest or pytest"))
    return entries + python_invocations(root, modules)


def dotted_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = dotted_name(node.value)
        return f"{base}.{node.attr}" if base else None
    if isinstance(node, ast.Subscript):
        return dotted_name(node.value)
    if isinstance(node, ast.Call):
        return dotted_name(node.func)
    return None


def literal_parts(node: ast.AST) -> list[str]:
    """String pieces of a path expression: a literal, os.path.join(...), Path(...) or a / b."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value]
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        return literal_parts(node.left) + literal_parts(node.right)
    if isinstance(node, ast.Call):
        name = dotted_name(node.func) or ""
        if name.split(".")[-1] in PATH_CALLS:
            return [part for arg in node.args for part in literal_parts(arg)]
    return []


def nearest(candidates: list[str], origin: str) -> list[str]:
    """The candidates sharing the longest leading directory path with origin."""
    origin_parts = PurePosixPath(origin).parent.parts

    def shared(candidate: str) -> int:
        count = 0
        for a, b in zip(PurePosixPath(candidate).parent.parts, origin_parts):
            if a != b:
                break
            count += 1
        return count

    best = max(shared(c) for c in candidates)
    return sorted(c for c in candidates if shared(c) == best)


def module_references(path: str, tree: ast.Module, modules: dict[str, ast.Module]) -> list[tuple[str, int]]:
    """Scoped modules that path imports or opens by a literal file path, with the line."""
    by_stem: dict[str, list[str]] = {}
    for module in modules:
        by_stem.setdefault(PurePosixPath(module).stem, []).append(module)
    here = PurePosixPath(path).parent
    refs: list[tuple[str, int]] = []

    def by_name(name: str, line: int, directory: PurePosixPath | None = None) -> None:
        local = (directory or here) / f"{name}.py"
        if local.as_posix() in modules:
            refs.append((local.as_posix(), line))
        elif directory is None and name not in sys.stdlib_module_names and name in by_stem:
            refs.extend((target, line) for target in nearest(by_stem[name], path))

    for node in ast.walk(tree):
        line = getattr(node, "lineno", 1)
        if isinstance(node, ast.Import):
            for alias in node.names:
                by_name(alias.name.split(".")[0], line)
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                by_name(node.module.split(".")[0], line)
            elif node.level:
                base = here
                for _ in range(node.level - 1):
                    base = base.parent
                names = [node.module.split(".")[0]] if node.module else [a.name for a in node.names]
                for name in names:
                    by_name(name, line, base)
        if isinstance(node, ast.Call):
            func = (dotted_name(node.func) or "").split(".")[-1]
            if func in IMPORT_CALLS and node.args:
                first = node.args[0]
                if isinstance(first, ast.Constant) and isinstance(first.value, str):
                    by_name(first.value.split(".")[0], line)
        if isinstance(node, (ast.Constant, ast.Call, ast.BinOp)):
            parts = literal_parts(node)
            if parts and parts[-1].endswith(".py"):
                segments = [s for p in parts for s in p.replace("\\", "/").split("/") if s not in ("", ".", "..")]
                suffix = "/".join(segments)
                matches = [m for m in modules if m == suffix or m.endswith("/" + suffix)]
                if matches:
                    refs.extend((target, line) for target in nearest(matches, path))
    return [(target, line) for target, line in refs if target != path]


def unreachable_modules(modules: dict[str, ast.Module], entries: list[Entry]) -> list[Finding]:
    reached = {e.path for e in entries}
    queue = sorted(reached)
    while queue:
        current = queue.pop()
        for target, _ in module_references(current, modules[current], modules):
            if target not in reached:
                reached.add(target)
                queue.append(target)
    return [Finding(path, 1, "module", PurePosixPath(path).stem,
                    "no entrypoint reaches this module through an import or a loaded path")
            for path in sorted(set(modules) - reached)]


# ---------------------------------------------------------------------------
# Python: symbols the runtime dispatches by name
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Definition:
    node: DefNode
    owner: ast.ClassDef | None
    module_level: bool


def definitions(tree: ast.Module) -> dict[int, Definition]:
    """Definitions by the line of their def or class statement and of each decorator."""
    index: dict[int, Definition] = {}
    stack: list[ast.AST] = [tree]
    while stack:
        parent = stack.pop()
        for child in ast.iter_child_nodes(parent):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                owner = parent if isinstance(parent, ast.ClassDef) else None
                found = Definition(child, owner, parent is tree)
                for line in (child.lineno, *(d.lineno for d in child.decorator_list)):
                    index.setdefault(line, found)
            stack.append(child)
    return index


def import_aliases(tree: ast.Module) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.asname:
                    aliases[alias.asname] = alias.name
                else:
                    top = alias.name.split(".")[0]
                    aliases[top] = top
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            for alias in node.names:
                aliases[alias.asname or alias.name] = f"{node.module}.{alias.name}"
    return aliases


def stdlib_object(dotted: str, aliases: dict[str, str]) -> object | None:
    """The standard library object a dotted base-class name refers to, if it is one."""
    head, _, rest = dotted.partition(".")
    if head in aliases:
        qualified = aliases[head] + (f".{rest}" if rest else "")
    elif hasattr(builtins, head):
        qualified = f"builtins.{dotted}"
    else:
        return None
    parts = qualified.split(".")
    if parts[0] not in sys.stdlib_module_names:
        return None
    for cut in range(len(parts), 0, -1):
        try:
            found: object = importlib.import_module(".".join(parts[:cut]))
        except ImportError:
            continue
        for attr in parts[cut:]:
            found = getattr(found, attr, None)
        return found
    return None


def class_defines(obj: object, name: str) -> bool:
    return isinstance(obj, type) and any(name in vars(k) for k in obj.__mro__ if k is not object)


def overridden_base(owner: ast.ClassDef, name: str, classes: dict[str, ast.ClassDef],
                    aliases: dict[str, str], seen: frozenset[str] = frozenset()) -> str | None:
    """The base class whose own method this one overrides, so the base calls it by name."""
    for base in owner.bases:
        dotted = dotted_name(base)
        if not dotted:
            continue
        local = classes.get(dotted)
        if local is not None and local is not owner and local.name not in seen:
            if any(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name for n in local.body):
                return dotted
            deeper = overridden_base(local, name, classes, aliases, seen | {owner.name})
            if deeper:
                return deeper
            continue
        obj = stdlib_object(dotted, aliases)
        if class_defines(obj, name):
            return f"{getattr(obj, '__module__', '')}.{getattr(obj, '__qualname__', dotted)}"
    return None


def has_base(owner: ast.ClassDef, names: set[str], classes: dict[str, ast.ClassDef],
             seen: frozenset[str] = frozenset()) -> bool:
    for base in owner.bases:
        dotted = dotted_name(base) or ""
        if dotted.split(".")[-1] in names:
            return True
        local = classes.get(dotted)
        if local is not None and local.name not in seen and has_base(local, names, classes, seen | {owner.name}):
            return True
    return False


def requested_fixtures(modules: dict[str, ast.Module]) -> dict[str, str]:
    """Parameter names of test functions and usefixtures() names, with where they appear."""
    requested: dict[str, str] = {}
    for path, tree in modules.items():
        if not is_test_module(path):
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                args = node.args
                for arg in (*args.posonlyargs, *args.args, *args.kwonlyargs):
                    requested.setdefault(arg.arg, f"{path}:{node.lineno}")
            elif isinstance(node, ast.Call) and (dotted_name(node.func) or "").endswith("usefixtures"):
                for arg in node.args:
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                        requested.setdefault(arg.value, f"{path}:{node.lineno}")
    return requested


def fixture_decorator(node: DefNode) -> ast.expr | None:
    for decorator in node.decorator_list:
        if (dotted_name(decorator) or "").split(".")[-1] == "fixture":
            return decorator
    return None


def autouse(decorator: ast.expr) -> bool:
    return isinstance(decorator, ast.Call) and any(
        k.arg == "autouse" and isinstance(k.value, ast.Constant) and k.value.value is True
        for k in decorator.keywords)


@dataclass
class ModuleFacts:
    index: dict[int, Definition]
    classes: dict[str, ast.ClassDef]
    aliases: dict[str, str]


def module_facts(tree: ast.Module) -> ModuleFacts:
    classes = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)}
    return ModuleFacts(definitions(tree), classes, import_aliases(tree))


def dispatch_rule(path: str, facts: ModuleFacts, line: int, fixtures: dict[str, str]) -> str | None:
    """Why the runtime calls this definition by name, or None when nothing does."""
    found = facts.index.get(line)
    if found is None:
        return None
    node, owner, name = found.node, found.owner, found.node.name
    if name.startswith("__") and name.endswith("__"):
        return f"Python calls special method {name} implicitly"
    if is_test_module(path):
        if isinstance(node, ast.ClassDef) and has_base(node, TESTCASE_BASES, facts.classes):
            return "unittest loads every TestCase subclass in a test module"
        if found.module_level and name in UNITTEST_MODULE_HOOKS:
            return f"unittest calls the module hook {name}"
        if owner is not None and has_base(owner, TESTCASE_BASES, facts.classes) and (
                name in TEST_METHOD_HOOKS or name.startswith("test")):
            return f"unittest calls {name} on a TestCase"
        if not isinstance(node, ast.ClassDef) and name.startswith("test") and (found.module_level or owner is not None):
            return f"pytest collects {name}"
        if isinstance(node, ast.ClassDef) and name.startswith("Test") and found.module_level:
            return f"pytest collects {name}"
        if PurePosixPath(path).name == "conftest.py" and name.startswith("pytest_"):
            return f"pytest calls the hook {name}"
    decorator = fixture_decorator(node)
    if decorator is not None:
        if autouse(decorator):
            return f"pytest runs the autouse fixture {name}"
        if name in fixtures:
            return f"pytest injects fixture {name}, requested at {fixtures[name]}"
        return None
    if owner is not None:
        if has_base(owner, {"Protocol"}, facts.classes):
            return f"{name} declares the interface of Protocol {owner.name}"
        base = overridden_base(owner, name, facts.classes, facts.aliases)
        if base:
            return f"overrides {base}.{name}, which the base class calls"
    return None


def vulture_findings(root: Path, config: PythonConfig, modules: dict[str, ast.Module],
                     report: Report) -> list[Finding]:
    try:
        import vulture
    except ImportError:
        report.errors.append("vulture is not installed; run "
                             "python3 -m pip install --require-hashes -r requirements-tooling.txt")
        return []
    detector = vulture.Vulture()
    detector.scavenge([str(root / path) for path in sorted(modules)])
    facts = {path: module_facts(tree) for path, tree in modules.items()}
    fixtures = requested_fixtures(modules)
    findings = []
    for item in detector.get_unused_code(min_confidence=config.min_confidence):
        if item.typ not in PY_KINDS:
            continue
        path = rel(root, Path(item.filename))
        finding = Finding(path, item.first_lineno, item.typ, item.name,
                          f"{item.message} ({item.confidence}% confidence, vulture)")
        rule = dispatch_rule(path, facts[path], item.first_lineno, fixtures) if path in facts else None
        if rule and item.typ != "import" and item.typ != "unreachable_code":
            report.dispatched.append((finding, rule))
        else:
            findings.append(finding)
    return findings


def check_python(root: Path, report: Report) -> list[Finding]:
    config = python_config(root)
    modules = python_modules(root, config, report)
    report.modules["python"] = len(modules)
    entries = python_entries(root, modules)
    report.entries += entries
    return unreachable_modules(modules, entries) + vulture_findings(root, config, modules, report)


# ---------------------------------------------------------------------------
# JavaScript: knip per producer, with the entries checked against what runs them
# ---------------------------------------------------------------------------


def knip_config(root: Path) -> tuple[dict[str, object], dict[str, dict[str, object]]]:
    path = root / KNIP_CONFIG
    if not path.is_file():
        raise ConfigError(f"{KNIP_CONFIG} is missing")
    data = json.loads(path.read_text(encoding="utf-8"))
    workspaces = data.get("workspaces") if isinstance(data, dict) else None
    if not isinstance(workspaces, dict) or not workspaces:
        raise ConfigError(f"{KNIP_CONFIG} names no producer under workspaces")
    for producer, options in workspaces.items():
        entry = options.get("entry") if isinstance(options, dict) else None
        if not isinstance(entry, list) or not entry or not all(isinstance(e, str) for e in entry):
            raise ConfigError(f"{KNIP_CONFIG} workspace {producer} needs an explicit entry list")
    shared = {k: v for k, v in data.items() if k not in ("workspaces", "$schema")}
    return shared, workspaces


def producer_files(root: Path, producer: str, pattern: str) -> list[str]:
    base = root / producer
    found = [p for p in base.glob(pattern) if p.is_file() and "node_modules" not in p.relative_to(base).parts]
    return sorted(rel(root, p) for p in found)


def node_targets(command: str) -> list[tuple[str, bool]]:
    """Files each `node` command on a line runs, and whether it runs them as tests."""
    lexer = shlex.shlex(command, posix=True, punctuation_chars="();&|<>")
    lexer.whitespace_split = True
    try:
        tokens = list(lexer)
    except ValueError:
        tokens = command.split()
    targets = []
    for i, token in enumerate(tokens):
        if token != "node" and not token.endswith("/node"):
            continue
        as_test = False
        for arg in tokens[i + 1:]:
            if arg.startswith("-"):
                as_test = as_test or arg == "--test"
                continue
            if arg.endswith(JS_SUFFIXES) or (has_glob(arg) and any(s in arg for s in JS_SUFFIXES)):
                targets.append((arg, as_test))
            break
    return targets


def resolve_target(root: Path, producer: str, target: str) -> list[str]:
    if has_glob(target):
        prefix = f"{producer}/"
        in_root = [p for p in producer_files(root, ".", target) if p.startswith(prefix)]
        return in_root or producer_files(root, producer, target)
    for candidate in (root / target, root / producer / target):
        if candidate.is_file():
            where = rel(root, candidate)
            if where.startswith(f"{producer}/"):
                return [where]
    return []


def javascript_invocations(root: Path, producer: str) -> list[Entry]:
    entries = []
    manifest = json.loads((root / producer / "package.json").read_text(encoding="utf-8"))
    for script, command in sorted((manifest.get("scripts") or {}).items()):
        for target, as_test in node_targets(str(command)):
            for path in resolve_target(root, producer, target):
                entries.append(Entry(path, "test" if as_test else "cli",
                                     f"{producer}/package.json scripts.{script}"))
    workflows = root / WORKFLOWS_DIR
    for workflow in sorted(workflows.glob("*.y*ml")) if workflows.is_dir() else []:
        for number, line in enumerate(workflow.read_text(encoding="utf-8").splitlines(), start=1):
            if "node" not in line or line.lstrip().startswith("#"):
                continue
            for target, as_test in node_targets(line):
                for path in resolve_target(root, producer, target):
                    entries.append(Entry(path, "test" if as_test else "cli", f"{rel(root, workflow)}:{number}"))
    return entries


def knip_binary(root: Path, producer: str) -> Path | None:
    candidates = [root / producer / "node_modules" / ".bin" / "knip"]
    candidates += sorted(REPO_ROOT.glob("tools/*/node_modules/.bin/knip"))
    return next((c for c in candidates if c.exists()), None)


def knip_issue_findings(producer: str, issues: list[dict[str, object]]) -> list[Finding]:
    findings = []
    for issue in issues:
        file = str(issue.get("file", ""))
        for kind in KNIP_INCLUDE:
            values = issue.get(kind)
            if not isinstance(values, list):
                continue
            for item in values:
                group = item if isinstance(item, list) else [item]
                names = [str(i.get("name", "")) for i in group if isinstance(i, dict)]
                first = next((i for i in group if isinstance(i, dict)), {})
                line = first.get("line") if isinstance(first.get("line"), int) else 1
                name = file if kind == "files" else " = ".join(names)
                label = "file" if kind == "files" else kind
                findings.append(Finding(f"{producer}/{file}", int(str(line)), label, name,
                                        f"unused {label} (knip)" if kind != "unresolved"
                                        else "import resolves to no file (knip)"))
    return findings


def run_knip(root: Path, producer: str, options: dict[str, object], report: Report) -> list[Finding]:
    binary = knip_binary(root, producer)
    if binary is None:
        report.errors.append(f"knip is not installed; run npm ci in {producer}")
        return []
    with tempfile.TemporaryDirectory(prefix="dead-code-knip-") as tmp:
        config = Path(tmp) / "knip.json"
        config.write_text(json.dumps(options), encoding="utf-8")
        result = subprocess.run(
            [str(binary), "--directory", str(root / producer), "--config", str(config),
             "--reporter", "json", "--no-progress", "--no-config-hints", "--no-exit-code",
             "--include", ",".join(KNIP_INCLUDE)],
            capture_output=True, text=True, timeout=600)
    try:
        issues = json.loads(result.stdout)["issues"]
    except (ValueError, KeyError, TypeError):
        report.errors.append(f"knip failed in {producer} (exit {result.returncode}): "
                             f"{(result.stderr or result.stdout).strip()[:500]}")
        return []
    return knip_issue_findings(producer, issues)


def check_javascript(root: Path, report: Report) -> list[Finding]:
    shared, workspaces = knip_config(root)
    findings: list[Finding] = []
    modules = 0
    for producer, options in sorted(workspaces.items()):
        if not (root / producer / "package.json").is_file():
            report.errors.append(f"{KNIP_CONFIG} workspace {producer} has no package.json")
            continue
        entry_files: dict[str, str] = {}
        patterns = options.get("entry")
        for pattern in patterns if isinstance(patterns, list) else []:
            matched = producer_files(root, producer, str(pattern))
            if not matched:
                report.errors.append(f"{KNIP_CONFIG} {producer} entry {pattern!r} matches no file")
            for path in matched:
                entry_files.setdefault(path, str(pattern))
        invoked = javascript_invocations(root, producer)
        run_paths = {e.path for e in invoked}
        for path in sorted(set(entry_files) - run_paths):
            report.errors.append(f"{KNIP_CONFIG} {producer} lists entry {path} but no package.json "
                                 "script or workflow runs it")
        for entry in invoked:
            if entry.path not in entry_files:
                report.errors.append(f"{entry.path} is run by {entry.evidence} but is not a "
                                     f"{KNIP_CONFIG} entry for {producer}")
        report.entries += invoked
        modules += sum(len(producer_files(root, producer, f"**/*{suffix}")) for suffix in JS_SUFFIXES)
        findings += run_knip(root, producer, {**shared, **options}, report)
    report.modules["javascript"] = modules
    return findings


# ---------------------------------------------------------------------------
# Exceptions, pending findings and the report
# ---------------------------------------------------------------------------


def language_of(key: str) -> str:
    return "python" if key.split(":", 1)[0].endswith(".py") else "javascript"


def check(root: Path, exceptions: dict[str, str] | None = None, pending: dict[str, str] | None = None,
          languages: tuple[str, ...] = LANGUAGES) -> Report:
    exceptions = EXCEPTIONS if exceptions is None else exceptions
    pending = PENDING_FINDINGS if pending is None else pending
    report = Report()
    raw: list[Finding] = []
    for language, runner in (("python", check_python), ("javascript", check_javascript)):
        if language not in languages:
            continue
        try:
            raw += runner(root, report)
        except ConfigError as exc:
            report.errors.append(str(exc))
    for key, evidence in exceptions.items():
        if not evidence.strip():
            report.errors.append(f"exception {key} names no evidence of dynamic use")
    matched: set[str] = set()
    for finding in raw:
        if finding.key in exceptions:
            report.excepted.append((finding, exceptions[finding.key]))
        elif finding.key in pending:
            report.pending.append((finding, pending[finding.key]))
        else:
            report.findings.append(finding)
            continue
        matched.add(finding.key)
    for table, entries in (("EXCEPTIONS", exceptions), ("PENDING_FINDINGS", pending)):
        for key in sorted(entries):
            if key not in matched and language_of(key) in languages:
                report.errors.append(f"{table} lists {key} but no detector reports it; remove the entry")
    return report


def print_report(report: Report, verbose: bool) -> None:
    by_path: dict[str, list[Entry]] = {}
    for entry in report.entries:
        by_path.setdefault(entry.path, []).append(entry)
    for path in sorted(by_path):
        kinds = sorted({e.kind for e in by_path[path]})
        evidence = "; ".join(sorted({e.evidence for e in by_path[path]}))
        print(f"ENTRY {path} [{', '.join(kinds)}] {evidence}")
    if verbose:
        for finding, rule in report.dispatched:
            print(f"DISPATCHED {finding.path}:{finding.line}: {finding.kind} {finding.name!r}: {rule}")
    for finding, why in report.excepted:
        print(f"EXCEPTION {finding}: {why}")
    for finding, why in report.pending:
        print(f"WARN {finding} (pending: {why})")
    for finding in report.findings:
        print(f"FAIL {finding}")
    for error in report.errors:
        print(f"FAIL {error}")
    counts = ", ".join(f"{language} {count} modules" for language, count in sorted(report.modules.items()))
    summary = (f"{counts}; {len(by_path)} entrypoints; {len(report.dispatched)} dispatched by name; "
               f"{len(report.excepted)} exceptions; {len(report.pending)} pending")
    problems = len(report.findings) + len(report.errors)
    if problems:
        print(f"dead-code: FAIL ({problems} problem(s); {summary})")
    else:
        print(f"dead-code: PASS ({summary})")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="repository root to check")
    parser.add_argument("--only", choices=LANGUAGES, help="check one language")
    parser.add_argument("--verbose", action="store_true", help="also list each definition dispatched by name")
    args = parser.parse_args(argv)
    languages = (args.only,) if args.only else LANGUAGES
    report = check(args.root, languages=languages)
    print_report(report, args.verbose)
    return 1 if report.findings or report.errors else 0


if __name__ == "__main__":
    sys.exit(main())
