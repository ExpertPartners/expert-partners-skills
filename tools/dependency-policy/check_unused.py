#!/usr/bin/env python3
"""Flag declared dependencies nothing uses and imports nothing declares.

JavaScript: knip, the shared detector the dead-code job configured in
tools/dead-code/knip.json, already analyzes dependency usage from each producer's
entrypoints. This runner reuses that one configuration (no second knip config exists)
and reports the dependency issue types the dead-code gate leaves out: unused
dependencies, devDependencies and optional peer dependencies, unused binaries, and
unlisted imports (used but never declared in package.json).

Python: every requirements*.txt lock names its direct dependencies in a
``# Direct: ...`` header (check_versions.py owns the pinning rules). A direct
dependency must show usage evidence in the lock's scope, where a lock's scope is the
canonical tooling Python (the [tool.vulture] paths in pyproject.toml) governed by that
lock's directory:

- runtime: imported by a non-test module in scope
- test: imported only by test modules in scope
- CLI: run by a workflow, shell script or launchd plist (``python -m <name>`` or a
  ``node_modules/.bin/<name>`` path)
- optional integration: the import sits behind ``try: ... except ImportError``; it
  still counts as usage and still must be declared
- stub: a ``types-<pkg>`` pin is used when <pkg> itself is pinned or imported

An import in scope that no pin in the governing lock's closure provides fails as
undeclared, imports behind try/except included. EXCEPTIONS below waives only the
named lazy integrations, with evidence; each entry fails once its finding is gone.

Offline: the checker reads the tree and runs the installed knip binary. It never
contacts a registry, fetches a package, or edits a file. Exit 0 when clean, 1
otherwise. tools/dependency-policy/README.md has usage.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
import tempfile
import tomllib
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

REPO_ROOT = Path(__file__).resolve().parents[2]
PYPROJECT = "pyproject.toml"
KNIP_CONFIG = "tools/dead-code/knip.json"
WORKFLOWS_DIR = ".github/workflows"
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", ".mypy_cache", ".pytest_cache"}
LANGUAGES = ("python", "javascript")

# knip issue types about dependency declarations. The code issue types (unused files,
# exports, unresolved imports) are the dead-code gate's, not this one's. knip has no
# unused-optionalDependencies report: an optional dependency is a declared integration
# point, and this check never asks to remove one.
KNIP_INCLUDE = ("dependencies", "devDependencies", "optionalPeerDependencies", "unlisted", "binaries")

# Python distribution names whose importable top-level module is not the normalized
# name with dashes turned to underscores. types-* stubs install no module; the stub
# rule handles them.
IMPORT_NAMES: dict[str, tuple[str, ...]] = {
    "beautifulsoup4": ("bs4",),
    "pillow": ("PIL",),
    "pyyaml": ("yaml",),
    "yt-dlp": ("yt_dlp",),
}

DIRECT_RE = re.compile(r"^#\s*Direct:\s*([A-Za-z0-9._, -]+?)\s*\.")
PIN_NAME_RE = re.compile(r"^([A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?)\s*==")
INCLUDE_RE = re.compile(r"^(?:-r|--requirement)(?:\s+|=)(\S+)$")

# Imports nothing declares, waived per file and module with the evidence a detector
# cannot see. An entry fails once its import is gone, so a waiver cannot outlive the
# integration it records. There is no blanket ignore: a new undeclared import fails.
EXCEPTIONS: dict[str, str] = {
    "plugins/research-ops/skills/video-discovery/scripts/video_discovery.py:import:playwright":
        "lazy optional integration: the browser probe imports Playwright only when it runs, "
        "on a workstation that has it; no lock carries it and pyproject.toml [tool.mypy] "
        "lists playwright under ignore_missing_imports",
    "tools/capability-currency/drive_docs.py:import:google":
        "lazy optional integration: runs on the founder Mac with the Google client installed "
        "outside the repo locks; pyproject.toml [tool.mypy] lists google.oauth2 under "
        "ignore_missing_imports",
    "tools/capability-currency/drive_docs.py:import:googleapiclient":
        "lazy optional integration: runs on the founder Mac with the Google client installed "
        "outside the repo locks; pyproject.toml [tool.mypy] lists googleapiclient under "
        "ignore_missing_imports",
    "tools/plugin-sync/drift-check.py:import:google":
        "lazy optional integration: runs on the founder Mac with the Google client installed "
        "outside the repo locks; pyproject.toml [tool.mypy] lists google.oauth2 under "
        "ignore_missing_imports",
    "tools/plugin-sync/drift-check.py:import:googleapiclient":
        "lazy optional integration: runs on the founder Mac with the Google client installed "
        "outside the repo locks; pyproject.toml [tool.mypy] lists googleapiclient under "
        "ignore_missing_imports",
}


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
class Use:
    lock: str
    name: str
    kind: str
    evidence: str


@dataclass
class Report:
    uses: list[Use] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    excepted: list[tuple[Finding, str]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    locks: int = 0
    producers: int = 0
    imports: int = 0


def rel(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def walk(base: Path) -> list[Path]:
    found = []
    if base.is_file():
        return [base]
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for name in sorted(filenames):
            found.append(Path(dirpath) / name)
    return found


def normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def import_names(pin: str) -> tuple[str, ...]:
    if pin.startswith("types-"):
        return ()
    return IMPORT_NAMES.get(pin, (pin.replace("-", "_"),))


# ---------------------------------------------------------------------------
# Python: locks, the canonical source scope and import evidence
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Lock:
    path: str
    directory: str
    pins: frozenset[str]
    direct: tuple[str, ...]
    includes: tuple[str, ...]
    header_line: int


def logical_lines(text: str) -> list[tuple[int, str]]:
    """Requirement lines with comments stripped and backslash continuations joined."""
    lines: list[tuple[int, str]] = []
    buffer, start = "", 0
    for number, raw in enumerate(text.splitlines(), start=1):
        line = re.sub(r"(^|\s)#.*$", "", raw).rstrip()
        if not buffer:
            start = number
        if line.endswith("\\"):
            buffer += line[:-1] + " "
            continue
        buffer += line
        if buffer.strip():
            lines.append((start, buffer.strip()))
        buffer = ""
    if buffer.strip():
        lines.append((start, buffer.strip()))
    return lines


def parse_lock(root: Path, path: Path) -> Lock:
    where = rel(root, path)
    text = path.read_text(encoding="utf-8")
    direct: tuple[str, ...] = ()
    header_line = 1
    for number, raw in enumerate(text.splitlines(), start=1):
        match = DIRECT_RE.match(raw)
        if match:
            direct = tuple(normalize(name.strip()) for name in match.group(1).split(","))
            header_line = number
            break
    if not direct:
        raise ConfigError(f"{where} does not name its direct dependencies in a "
                          "'# Direct: ...' header line")
    pins: set[str] = set()
    includes: list[str] = []
    for _, line in logical_lines(text):
        include = INCLUDE_RE.match(line)
        if include:
            includes.append(rel(root, (path.parent / include.group(1)).resolve()))
            continue
        pin = PIN_NAME_RE.match(line)
        if pin:
            pins.add(normalize(pin.group(1)))
    directory = PurePosixPath(where).parent.as_posix()
    return Lock(where, "" if directory == "." else directory, frozenset(pins), direct,
                tuple(includes), header_line)


def python_locks(root: Path) -> dict[str, Lock]:
    locks: dict[str, Lock] = {}
    for path in walk(root):
        if path.name.startswith("requirements") and path.name.endswith(".txt"):
            lock = parse_lock(root, path)
            locks[lock.path] = lock
    return locks


def closure_pins(locks: dict[str, Lock], lock: Lock, seen: frozenset[str] = frozenset()) -> set[str]:
    if lock.path in seen:
        return set()
    pins = set(lock.pins)
    for include in lock.includes:
        target = locks.get(include)
        if target is not None:
            pins |= closure_pins(locks, target, seen | {lock.path})
    return pins


def python_scope(root: Path) -> list[str]:
    path = root / PYPROJECT
    if not path.is_file():
        raise ConfigError(f"{PYPROJECT} is missing")
    with open(path, "rb") as fh:
        table = tomllib.load(fh).get("tool", {}).get("vulture")
    if not isinstance(table, dict) or not isinstance(table.get("paths"), list) or not table["paths"]:
        raise ConfigError(f"{PYPROJECT} has no [tool.vulture] paths; the canonical Python "
                          "tooling scope lives there")
    return [str(p) for p in table["paths"]]


def scoped_files(root: Path, scope: list[str], report: Report) -> dict[str, ast.Module]:
    modules: dict[str, ast.Module] = {}
    for entry in scope:
        base = root / entry
        if not base.exists():
            report.errors.append(f"[tool.vulture] path {entry} does not exist")
            continue
        for path in walk(base):
            if path.suffix != ".py":
                continue
            where = rel(root, path)
            try:
                modules[where] = ast.parse(path.read_text(encoding="utf-8"), filename=where)
            except SyntaxError as exc:
                report.errors.append(f"{where}: cannot parse ({exc.msg})")
    return modules


def governing_dir(path: str, lock_dirs: list[str]) -> str:
    """The deepest lock directory that contains path; the root lock governs the rest."""
    for directory in sorted(lock_dirs, key=lambda d: len(PurePosixPath(d).parts), reverse=True):
        if directory and (path == directory or path.startswith(directory + "/")):
            return directory
    return ""


def is_test_module(path: str) -> bool:
    pure = PurePosixPath(path)
    in_tests = any(part in ("tests", "test") for part in pure.parts[:-1])
    named = pure.name.startswith("test_") or pure.name.endswith("_test.py")
    return in_tests and (named or pure.name == "conftest.py")


def optional_import_nodes(tree: ast.Module) -> set[int]:
    """id()s of imports inside a try whose handlers catch ImportError (or anything)."""
    found: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Try):
            continue
        catches = any(handler.type is None for handler in node.handlers) or any(
            "ImportError" in ast.dump(handler.type) for handler in node.handlers if handler.type)
        if catches:
            for sub in ast.walk(node):
                if isinstance(sub, (ast.Import, ast.ImportFrom)):
                    found.add(id(sub))
    return found


@dataclass(frozen=True)
class ImportUse:
    path: str
    line: int
    module: str
    test: bool
    optional: bool


def imports_of(path: str, tree: ast.Module) -> list[ImportUse]:
    optional = optional_import_nodes(tree)
    uses: list[ImportUse] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules = [alias.name.split(".")[0] for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            modules = [node.module.split(".")[0]]
        else:
            continue
        for module in modules:
            uses.append(ImportUse(path, node.lineno, module, is_test_module(path),
                                  id(node) in optional))
    return uses


def invocation_sources(root: Path) -> list[tuple[str, list[tuple[int, str]]]]:
    """Workflows, shell scripts and plists as (path, numbered lines); comments dropped."""
    sources = []
    for path in walk(root):
        where = rel(root, path)
        workflow = where.startswith(WORKFLOWS_DIR + "/") and path.suffix in (".yml", ".yaml")
        if not (workflow or path.suffix in (".sh", ".plist")):
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        if path.suffix in (".yml", ".yaml", ".sh"):
            lines = ["" if line.lstrip().startswith("#") else line for line in lines]
        sources.append((where, list(enumerate(lines, start=1))))
    return sources


def cli_evidence(root: Path, name: str) -> str | None:
    """Where a workflow or script runs the dependency's command, if one does."""
    variants = {name, name.replace("-", "_")}
    patterns = [re.compile(r"\bpython\d*(?:\.\d+)?\s+-m\s+" + re.escape(v) + r"\b") for v in variants]
    patterns += [re.compile(r"node_modules/\.bin/" + re.escape(v) + r"\b") for v in variants]
    for where, lines in invocation_sources(root):
        for number, line in lines:
            if any(pattern.search(line) for pattern in patterns):
                return f"{where}:{number} runs {name}"
    return None


def check_python(root: Path, report: Report) -> list[Finding]:
    locks = python_locks(root)
    report.locks = len(locks)
    if not any(lock.directory == "" for lock in locks.values()):
        raise ConfigError("no requirements*.txt lock at the repository root to govern tools/")
    scope = python_scope(root)
    modules = scoped_files(root, scope, report)
    local_stems = {PurePosixPath(path).stem for path in modules}
    imports = [use for path, tree in modules.items() for use in imports_of(path, tree)]
    report.imports = len(imports)
    lock_dirs = sorted({lock.directory for lock in locks.values()})
    by_dir: dict[str, list[Lock]] = {}
    for lock in locks.values():
        by_dir.setdefault(lock.directory, []).append(lock)
    declared_by_dir = {
        directory: {name for lock in group for pin in closure_pins(locks, lock)
                    for name in import_names(pin)}
        for directory, group in by_dir.items()
    }

    findings: list[Finding] = []
    for use in imports:
        if use.module in sys.stdlib_module_names or use.module in local_stems:
            continue
        if use.module in declared_by_dir.get(governing_dir(use.path, lock_dirs), set()):
            continue
        findings.append(Finding(use.path, use.line, "import", use.module,
                                "imported but no pin in the governing lock's closure provides it"
                                + (" (optional import behind try/except; it still needs a "
                                   "declaration)" if use.optional else "")))

    all_pins = {pin for lock in locks.values() for pin in lock.pins}
    imported_modules = {use.module for use in imports}
    for lock in sorted(locks.values(), key=lambda l: l.path):
        scope_imports = [u for u in imports if governing_dir(u.path, lock_dirs) == lock.directory]
        for dep in lock.direct:
            if dep.startswith("types-"):
                base = dep[len("types-"):]
                base_names = IMPORT_NAMES.get(base, (base.replace("-", "_"),))
                if base in all_pins:
                    report.uses.append(Use(lock.path, dep, "stub",
                                           f"stubs {base}, which a repository lock pins"))
                elif any(name in imported_modules for name in base_names):
                    report.uses.append(Use(lock.path, dep, "stub",
                                           f"stubs {base}, which scoped sources import"))
                else:
                    findings.append(Finding(lock.path, lock.header_line, "dependency", dep,
                                            f"stub for {base}, which no lock pins and no scoped "
                                            "source imports"))
                continue
            names = set(import_names(dep))
            uses = [u for u in scope_imports if u.module in names]
            if uses:
                kind = "test" if all(u.test for u in uses) else "runtime"
                if all(u.optional for u in uses):
                    kind += ", optional"
                first = uses[0]
                report.uses.append(Use(lock.path, dep, kind,
                                       f"imported at {first.path}:{first.line}"))
                continue
            evidence = cli_evidence(root, dep)
            if evidence:
                report.uses.append(Use(lock.path, dep, "cli", evidence))
                continue
            scope_desc = f"the {lock.directory or 'repository tooling'} scope"
            findings.append(Finding(lock.path, lock.header_line, "dependency", dep,
                                    f"declared direct but nothing in {scope_desc} imports it and "
                                    "no workflow or script runs it"))
    return findings


# ---------------------------------------------------------------------------
# JavaScript: the shared knip configuration, read for its dependency issue types
# ---------------------------------------------------------------------------


def knip_config(root: Path) -> tuple[dict[str, object], dict[str, dict[str, object]]]:
    path = root / KNIP_CONFIG
    if not path.is_file():
        raise ConfigError(f"{KNIP_CONFIG} is missing; the dead-code job owns the one shared "
                          "knip configuration and this check reuses it")
    data = json.loads(path.read_text(encoding="utf-8"))
    workspaces = data.get("workspaces") if isinstance(data, dict) else None
    if not isinstance(workspaces, dict) or not workspaces:
        raise ConfigError(f"{KNIP_CONFIG} names no producer under workspaces")
    shared = {k: v for k, v in data.items() if k not in ("workspaces", "$schema")}
    return shared, workspaces


def knip_binary(root: Path, producer: str) -> Path | None:
    candidates = [root / producer / "node_modules" / ".bin" / "knip"]
    candidates += sorted(REPO_ROOT.glob("tools/*/node_modules/.bin/knip"))
    return next((c for c in candidates if c.exists()), None)


def knip_issue_findings(producer: str, issues: list[dict[str, object]]) -> list[Finding]:
    findings = []
    sections = (("dependencies", "dependency", "declared in dependencies but nothing imports it"),
                ("devDependencies", "devDependency",
                 "declared in devDependencies but no source, test or script uses it"),
                ("optionalPeerDependencies", "optional peer dependency",
                 "declared as an optional peer dependency but nothing imports it"),
                ("binaries", "binary", "dependency binary nothing runs"))
    for issue in issues:
        file = str(issue.get("file", ""))
        where = f"{producer}/{file}"
        for section, kind, message in sections:
            values = issue.get(section)
            if not isinstance(values, list):
                continue
            for item in values:
                name = str(item.get("name", "")) if isinstance(item, dict) else str(item)
                findings.append(Finding(where, 1, kind, name, f"{message} (knip)"))
        unlisted = issue.get("unlisted")
        if isinstance(unlisted, list):
            for item in unlisted:
                name = str(item.get("name", "")) if isinstance(item, dict) else str(item)
                line = item.get("line") if isinstance(item, dict) and isinstance(item.get("line"), int) else 1
                findings.append(Finding(where, int(str(line)), "import", name,
                                        "imported but not declared in package.json (knip)"))
    return findings


def run_knip(root: Path, producer: str, options: dict[str, object], report: Report) -> list[Finding]:
    binary = knip_binary(root, producer)
    if binary is None:
        report.errors.append(f"knip is not installed; run npm ci in {producer}")
        return []
    with tempfile.TemporaryDirectory(prefix="unused-deps-knip-") as tmp:
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
    for producer, options in sorted(workspaces.items()):
        if not (root / producer / "package.json").is_file():
            report.errors.append(f"{KNIP_CONFIG} workspace {producer} has no package.json")
            continue
        report.producers += 1
        findings += run_knip(root, producer, {**shared, **options}, report)
    return findings


# ---------------------------------------------------------------------------
# Exceptions and the report
# ---------------------------------------------------------------------------


def check(root: Path, exceptions: dict[str, str] | None = None,
          languages: tuple[str, ...] = LANGUAGES) -> Report:
    exceptions = EXCEPTIONS if exceptions is None else exceptions
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
            report.errors.append(f"exception {key} names no evidence of the integration")
    matched: set[str] = set()
    for finding in raw:
        if finding.key in exceptions:
            report.excepted.append((finding, exceptions[finding.key]))
            matched.add(finding.key)
        else:
            report.findings.append(finding)
    for key in sorted(exceptions):
        if key not in matched and key.split(":", 1)[0].endswith(".py") and "python" in languages:
            report.errors.append(f"EXCEPTIONS lists {key} but no check reports it; remove the entry")
    return report


def print_report(report: Report) -> None:
    for use in sorted(report.uses, key=lambda u: (u.lock, u.name)):
        print(f"USED {use.lock}: {use.name} [{use.kind}] {use.evidence}")
    for finding, why in report.excepted:
        print(f"EXCEPTION {finding}: {why}")
    for finding in report.findings:
        print(f"FAIL {finding}")
    for error in report.errors:
        print(f"FAIL {error}")
    summary = (f"{report.locks} Python locks, {report.imports} imports read, "
               f"{report.producers} JavaScript producers, {len(report.excepted)} exceptions")
    problems = len(report.findings) + len(report.errors)
    if problems:
        print(f"unused-dependencies: FAIL ({problems} problem(s); {summary})")
    else:
        print(f"unused-dependencies: PASS ({summary})")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="repository root to check")
    parser.add_argument("--only", choices=LANGUAGES, help="check one language")
    args = parser.parse_args(argv)
    languages = (args.only,) if args.only else LANGUAGES
    report = check(args.root, languages=languages)
    print_report(report)
    return 1 if report.findings or report.errors else 0


if __name__ == "__main__":
    sys.exit(main())
