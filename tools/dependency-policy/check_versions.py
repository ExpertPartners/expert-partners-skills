#!/usr/bin/env python3
"""Dependency policy for this repository's build and test tooling.

Two rules, checked offline from files in the tree (no package index, registry or other
network request is ever made):

1. Python requirement files are exact locks. Every requirement, direct and transitive,
   is pinned with ``==`` and carries at least one ``--hash=sha256:`` value, so pip runs in
   --require-hashes mode and refuses any package the lock does not list. A package pinned
   in more than one requirement file must carry the same version everywhere. Workflows
   install Python packages only through ``-r <lock file>``, never by naming a package.
2. The JavaScript producers under tools/ do not drift apart. Every producer has a
   lockfile in sync with its package.json, a dependency both producers declare carries
   the identical specifier in each, and a package both lockfiles resolve resolves to the
   identical version and integrity in each. Workflows install with ``npm ci``, never
   ``npm install``.

Exit 0 when the tree passes, 1 when any rule fails. tools/dependency-policy/README.md has
usage and the regeneration steps.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__"}
JS_PRODUCERS_DIR = "tools"
WORKFLOWS_DIR = ".github/workflows"

# Workflows outside the change that brought them under this policy, mapped to the one
# finding still waived there and the follow-up that removes it. Only a finding containing
# that text prints as a warning; any other finding in the workflow fails. The entry fails
# once the waived finding is gone, so the exception cannot outlive the gap it records.
PENDING_WORKFLOWS: dict[str, tuple[str, str]] = {
    "builder-allowlist.yml": ("installs 'pyyaml' by name",
                              "installs PyYAML by name; move it to -r requirements-tooling.txt"),
    "skills-graph.yml": ("installs 'pyyaml' by name",
                         "installs PyYAML by name; move it to -r requirements-tooling.txt"),
}

DEP_SECTIONS = ("dependencies", "devDependencies", "optionalDependencies", "peerDependencies")
HASH_RE = re.compile(r"--hash=sha256:[0-9a-f]{64}")
PIN_RE = re.compile(
    r"^(?P<name>[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?)"
    r"(?:\[[A-Za-z0-9._,\s-]+\])?"
    r"\s*==\s*(?P<version>[A-Za-z0-9][A-Za-z0-9.+!_-]*)"
    r"\s*(?:;\s*(?P<marker>[^-][^\n]*?))?"
    r"(?P<hashes>(?:\s+--hash=sha256:[0-9a-f]{64})+)\s*$"
)
RANGE_RE = re.compile(r"(>=|<=|~=|!=|===|>|<|\*)")
PIP_INSTALL_RE = re.compile(r"\bpip[\d.]*\s(?:[^\n;&|]*\s)?install\b")
PIP_RE = re.compile(r"pip[\d.]*")
SHELL_OPERATOR_CHARS = "();&|<>"
NPM_INSTALL_RE = re.compile(r"\bnpm\s+(?:install|i|add)\b")
NPM_INTEGRITY_RE = re.compile(r"^sha512-[A-Za-z0-9+/]+={0,2}$")
NPM_REGISTRY = "https://registry.npmjs.org/"


@dataclass
class Finding:
    path: str
    message: str

    def __str__(self) -> str:
        return f"{self.path}: {self.message}"


@dataclass
class Report:
    errors: list[Finding] = field(default_factory=list)
    warnings: list[Finding] = field(default_factory=list)

    def error(self, path: str, message: str) -> None:
        self.errors.append(Finding(path, message))


def rel(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def walk(root: Path, predicate) -> list[Path]:
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for name in sorted(filenames):
            if predicate(name):
                found.append(Path(dirpath) / name)
    return found


# ---------------------------------------------------------------------------
# Python requirement locks
# ---------------------------------------------------------------------------


def logical_lines(text: str) -> list[tuple[int, str]]:
    """Requirement-file lines with comments removed and backslash continuations joined."""
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


@dataclass
class Pin:
    name: str
    version: str
    marker: str
    path: str
    line: int


def parse_lock(root: Path, path: Path, report: Report) -> tuple[list[Pin], list[Path]]:
    """Pins and -r includes of one requirement file; every rule breach goes to report."""
    where = rel(root, path)
    pins: list[Pin] = []
    includes: list[Path] = []
    for number, line in logical_lines(path.read_text(encoding="utf-8")):
        at = f"{where}:{number}"
        include = re.match(r"^(?:-r|--requirement)(?:\s+|=)(\S+)$", line)
        if include:
            target = (path.parent / include.group(1)).resolve()
            if not target.is_file():
                report.error(at, f"includes {include.group(1)}, which does not exist")
            else:
                includes.append(target)
            continue
        if line.startswith("-"):
            report.error(at, f"option {line.split()[0]} is not allowed in a lock; only -r includes are")
            continue
        match = PIN_RE.match(line)
        if match:
            pins.append(Pin(normalize(match.group("name")), match.group("version"),
                            (match.group("marker") or "").strip(), where, number))
            continue
        requirement = line.split(" --hash", 1)[0].strip()
        if "://" in requirement or requirement.startswith((".", "/")):
            report.error(at, f"{requirement!r} installs from a URL or path; pin a released version")
        elif "==" not in requirement or RANGE_RE.search(requirement.split(";", 1)[0]):
            report.error(at, f"{requirement!r} is open-ended or ranged; pin it with == and --hash")
        elif not HASH_RE.search(line):
            report.error(at, f"{requirement!r} has no --hash=sha256 value; pip cannot verify it")
        else:
            report.error(at, f"{requirement!r} is not a recognized exact, hash-locked pin")
    return pins, includes


def check_python(root: Path, report: Report) -> list[str]:
    files = walk(root, lambda n: n.startswith("requirements") and n.endswith(".txt"))
    parsed: dict[Path, tuple[list[Pin], list[Path]]] = {}
    for path in files:
        parsed[path.resolve()] = parse_lock(root, path, report)

    def closure(path: Path, seen: set[Path]) -> list[Pin]:
        if path in seen:
            report.error(rel(root, path), "includes itself through -r")
            return []
        seen = seen | {path}
        if path not in parsed:
            parsed[path] = parse_lock(root, path, report)
        pins, includes = parsed[path]
        collected = list(pins)
        for include in includes:
            collected.extend(closure(include, seen))
        return collected

    for path in sorted(parsed):
        by_name: dict[tuple[str, str], Pin] = {}
        for pin in closure(path, set()):
            key = (pin.name, pin.marker)
            first = by_name.setdefault(key, pin)
            if first is not pin and (first.path, first.line) != (pin.path, pin.line):
                report.error(rel(root, path), f"{pin.name} is pinned twice in one install "
                             f"({first.path}:{first.line} and {pin.path}:{pin.line})")

    versions: dict[str, Pin] = {}
    for pins, _ in parsed.values():
        for pin in pins:
            first = versions.setdefault(pin.name, pin)
            if first.version != pin.version:
                report.error(f"{pin.path}:{pin.line}", f"{pin.name}=={pin.version} drifts from "
                             f"{pin.name}=={first.version} in {first.path}:{first.line}")
    return [rel(root, p) for p in files]


# ---------------------------------------------------------------------------
# JavaScript producers
# ---------------------------------------------------------------------------


def declared(manifest: dict) -> dict[str, str]:
    deps: dict[str, str] = {}
    for section in DEP_SECTIONS:
        deps.update(manifest.get(section) or {})
    return deps


def check_javascript(root: Path, report: Report) -> list[str]:
    base = root / JS_PRODUCERS_DIR
    manifests = sorted(base.glob("*/package.json")) if base.is_dir() else []
    producers: dict[str, tuple[dict, dict]] = {}
    for manifest_path in manifests:
        where = rel(root, manifest_path.parent)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        lock_path = manifest_path.parent / "package-lock.json"
        if not lock_path.is_file():
            report.error(where, "has package.json but no package-lock.json; npm ci needs the lock")
            continue
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
        lock_where = rel(root, lock_path)
        if lock.get("lockfileVersion") not in (2, 3):
            report.error(lock_where, f"lockfileVersion {lock.get('lockfileVersion')!r}; expected 2 or 3")
            continue
        lock_root = (lock.get("packages") or {}).get("") or {}
        for section in DEP_SECTIONS:
            if (manifest.get(section) or {}) != (lock_root.get(section) or {}):
                report.error(lock_where, f"{section} differ from package.json; the lock is out of sync")
        for key, entry in sorted((lock.get("packages") or {}).items()):
            if not key or entry.get("link"):
                continue
            if not entry.get("version"):
                report.error(lock_where, f"{key} has no resolved version")
            if not str(entry.get("resolved", "")).startswith(NPM_REGISTRY):
                report.error(lock_where, f"{key} does not resolve from {NPM_REGISTRY}")
            if not NPM_INTEGRITY_RE.match(str(entry.get("integrity", ""))):
                report.error(lock_where, f"{key} has no sha512 integrity")
        producers[where] = (manifest, lock.get("packages") or {})

    names = sorted(producers)
    for i, left in enumerate(names):
        for right in names[i + 1:]:
            left_deps, right_deps = declared(producers[left][0]), declared(producers[right][0])
            for dep in sorted(set(left_deps) & set(right_deps)):
                if left_deps[dep] != right_deps[dep]:
                    report.error(f"{right}/package.json", f"declares {dep} {right_deps[dep]!r} but "
                                 f"{left}/package.json declares {left_deps[dep]!r}")
            left_lock, right_lock = producers[left][1], producers[right][1]
            for key in sorted(set(left_lock) & set(right_lock) - {""}):
                a, b = left_lock[key], right_lock[key]
                if a.get("version") != b.get("version"):
                    report.error(f"{right}/package-lock.json", f"{key} resolves to {b.get('version')} but "
                                 f"{left}/package-lock.json resolves it to {a.get('version')}")
                elif a.get("integrity") != b.get("integrity"):
                    report.error(f"{right}/package-lock.json", f"{key}@{b.get('version')} integrity "
                                 f"differs from {left}/package-lock.json")
    return names


# ---------------------------------------------------------------------------
# Workflow installs
# ---------------------------------------------------------------------------


def shell_commands(line: str) -> list[list[str]]:
    """Tokens of each simple command on a shell line, split at ;, &&, ||, |, parens and redirects."""
    lexer = shlex.shlex(line, posix=True, punctuation_chars=SHELL_OPERATOR_CHARS)
    lexer.whitespace_split = True
    try:
        tokens = list(lexer)
    except ValueError:
        tokens = line.split()
    commands, current = [], []
    for token in tokens:
        if token and set(token) <= set(SHELL_OPERATOR_CHARS):
            if current:
                commands.append(current)
            current = []
        else:
            current.append(token)
    if current:
        commands.append(current)
    return commands


def pip_install_args(tokens: list[str]) -> list[str] | None:
    """Arguments after `install` when tokens run pip install, global options allowed between."""
    for i, token in enumerate(tokens):
        if PIP_RE.fullmatch(token) and "install" in tokens[i + 1:]:
            return tokens[tokens.index("install", i + 1) + 1:]
    return None


def check_pip_command(root: Path, command: str) -> list[str]:
    """Reasons a line's pip install commands bypass the locks (empty when all install from them)."""
    installs = [args for args in map(pip_install_args, shell_commands(command)) if args is not None]
    if not installs:
        return ["runs pip install in a form this check cannot read; call pip install -r directly"]
    problems: list[str] = []
    for args in installs:
        problems += check_pip_args(root, args)
    return problems


def check_pip_args(root: Path, args: list[str]) -> list[str]:
    problems, locks, i = [], [], 0
    while i < len(args):
        token = args[i]
        if token in ("-r", "--requirement"):
            if i + 1 < len(args):
                locks.append(args[i + 1])
            i += 2
            continue
        if token.startswith("--requirement="):
            locks.append(token.split("=", 1)[1])
        elif token in ("-e", "--editable") or token.startswith("--editable="):
            problems.append("installs an editable package; install from a lock with -r")
        elif not token.startswith("-"):
            problems.append(f"installs {token!r} by name; install it from a lock with -r")
        i += 1
    if not locks and not problems:
        problems.append("installs nothing from a lock; use -r <requirements file>")
    for lock in locks:
        if not re.fullmatch(r"requirements[^/]*\.txt", Path(lock).name):
            problems.append(f"names {lock}; only requirements*.txt files are checked as locks")
        elif not (root / lock).is_file():
            problems.append(f"names {lock}, which is not a requirements file from the repo root")
    return problems


def check_workflows(root: Path, report: Report, pending: dict[str, tuple[str, str]]) -> list[str]:
    base = root / WORKFLOWS_DIR
    paths = sorted(p for p in base.glob("*") if p.suffix in (".yml", ".yaml")) if base.is_dir() else []
    for path in paths:
        where = rel(root, path)
        findings: list[Finding] = []
        for number, line in logical_lines(path.read_text(encoding="utf-8")):
            if PIP_INSTALL_RE.search(line):
                findings += [Finding(f"{where}:{number}", p) for p in check_pip_command(root, line)]
            if NPM_INSTALL_RE.search(line):
                findings.append(Finding(f"{where}:{number}", "runs npm install; use npm ci so the lock is honored"))
        waived_text = pending[path.name][0] if path.name in pending else None
        waived = [f for f in findings if waived_text and waived_text in f.message]
        report.warnings += waived
        report.errors += [f for f in findings if f not in waived]
        if waived_text and not waived:
            report.error(where, "is listed in PENDING_WORKFLOWS but no longer has its waived finding; "
                         "remove the entry")
    return [rel(root, p) for p in paths]


def check(root: Path, pending: dict[str, tuple[str, str]] | None = None) -> Report:
    report = Report()
    check_python(root, report)
    check_javascript(root, report)
    check_workflows(root, report, PENDING_WORKFLOWS if pending is None else pending)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="repository root to check")
    args = parser.parse_args(argv)
    report = check(args.root)
    for warning in report.warnings:
        reason = PENDING_WORKFLOWS.get(Path(warning.path.split(":")[0]).name, ("", ""))[1]
        print(f"WARN {warning} (pending: {reason})")
    for error in report.errors:
        print(f"FAIL {error}")
    if report.errors:
        print(f"dependency-policy: FAIL ({len(report.errors)} problem(s))")
        return 1
    print("dependency-policy: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
