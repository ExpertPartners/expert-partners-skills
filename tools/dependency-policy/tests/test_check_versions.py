"""Offline fixture tests for tools/dependency-policy/check_versions.py.

Every test builds a synthetic repository in a temporary directory. Network sockets and
subprocesses are disabled for the whole module, so no package index, registry or other
provider can be reached and no resolver can run.
"""

from __future__ import annotations

import copy
import io
import json
import socket
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import check_versions  # noqa: E402

H1 = "--hash=sha256:" + "a" * 64
H2 = "--hash=sha256:" + "b" * 64
H3 = "--hash=sha256:" + "c" * 64


def _blocked(*_args, **_kwargs):
    raise AssertionError("dependency-policy tests must not open a network connection or run a process")


_patches = [
    mock.patch.object(socket.socket, "connect", _blocked),
    mock.patch.object(socket.socket, "connect_ex", _blocked),
    mock.patch.object(socket, "create_connection", _blocked),
    mock.patch.object(socket, "getaddrinfo", _blocked),
    mock.patch.object(subprocess, "Popen", _blocked),
]


def setUpModule() -> None:
    for patch in _patches:
        patch.start()


def tearDownModule() -> None:
    for patch in _patches:
        patch.stop()


def npm_entry(name: str, version: str, deps: dict | None = None) -> dict:
    entry = {
        "version": version,
        "resolved": f"https://registry.npmjs.org/{name}/-/{name}-{version}.tgz",
        "integrity": "sha512-" + (name + version).encode().hex()[:40] + "==",
        "license": "MIT",
    }
    if deps:
        entry["dependencies"] = deps
    return entry


def producer(name: str, deps: dict[str, str], resolved: dict[str, str]) -> tuple[dict, dict]:
    manifest = {"name": name, "private": True, "version": "1.0.0", "dependencies": deps}
    packages = {"": {"name": name, "version": "1.0.0", "dependencies": dict(deps)}}
    for pkg, version in resolved.items():
        extra = {"js-yaml": "^3.13.1"} if pkg == "gray-matter" else None
        packages[f"node_modules/{pkg}"] = npm_entry(pkg, version, extra)
    lock = {"name": name, "version": "1.0.0", "lockfileVersion": 3, "requires": True, "packages": packages}
    return manifest, lock


GOOD_FEED = producer("capability-feed", {"gray-matter": "^4.0.3", "zod": "^4.0.0"},
                     {"gray-matter": "4.0.3", "js-yaml": "3.15.2", "zod": "4.6.5"})
GOOD_MAP = producer("skill-map", {"elkjs": "^0.12.0", "gray-matter": "^4.0.3", "zod": "^4.0.0"},
                    {"elkjs": "0.12.0", "gray-matter": "4.0.3", "js-yaml": "3.15.2", "zod": "4.6.5"})

RUNTIME = f"""# Hash-locked runtime.
certifi==2026.10.23 \\
    {H1} \\
    {H2}
requests==2.34.2 \\
    {H1}
    # via -r requirements.in
colorama==0.4.6 ; sys_platform == 'win32' \\
    {H3}
"""
VERIFY = f"""-r requirements.txt
pillow==13.0.0 {H1} {H2}
"""
DEV = f"""-r requirements-verification.txt
pytest==9.2.0 \\
    {H1}
"""
SIBLING = f"""-r ../video/requirements.txt
pillow==13.0.0 \\
    {H3}
"""
TOOLING = f"""pyyaml==6.0.3 \\
    {H1}
"""
CI = """name: ci
jobs:
  lint:
    steps:
      - run: |
          set -euo pipefail
          python3 -m pip install --quiet --require-hashes -r requirements-tooling.txt
          python3 lint.py
      - run: >-
          python -m pip install --require-hashes \\
            -r skills/video/requirements-dev.txt
      - working-directory: tools/feed
        run: npm ci && npm test
"""


class Fixture:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.write("tools/capability-feed/package.json", GOOD_FEED[0])
        self.write("tools/capability-feed/package-lock.json", GOOD_FEED[1])
        self.write("tools/skill-map/package.json", GOOD_MAP[0])
        self.write("tools/skill-map/package-lock.json", GOOD_MAP[1])
        self.write("skills/video/requirements.txt", RUNTIME)
        self.write("skills/video/requirements-verification.txt", VERIFY)
        self.write("skills/video/requirements-dev.txt", DEV)
        self.write("skills/hunter/requirements.txt", SIBLING)
        self.write("requirements-tooling.txt", TOOLING)
        self.write(".github/workflows/ci.yml", CI)

    def write(self, path: str, content) -> None:
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        if not isinstance(content, str):
            content = json.dumps(content, indent=2) + "\n"
        target.write_text(content, encoding="utf-8")

    def read_json(self, path: str) -> dict:
        return json.loads((self.root / path).read_text(encoding="utf-8"))

    def edit_json(self, path: str, change) -> None:
        data = copy.deepcopy(self.read_json(path))
        change(data)
        self.write(path, data)


class PolicyTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo = Fixture(Path(self._tmp.name))

    def errors(self, pending: dict[str, str] | None = None) -> list[str]:
        return [str(f) for f in check_versions.check(self.repo.root, pending or {}).errors]

    def assertFails(self, *fragments: str) -> list[str]:
        errors = self.errors()
        self.assertTrue(errors, "expected the policy to fail")
        joined = "\n".join(errors)
        for fragment in fragments:
            self.assertIn(fragment, joined)
        return errors


class SandboxTest(unittest.TestCase):
    def test_network_and_processes_are_blocked(self) -> None:
        with self.assertRaises(AssertionError):
            socket.create_connection(("pypi.org", 443))
        with self.assertRaises(AssertionError):
            subprocess.run(["npm", "view", "zod", "version"])


class SharedJavaScriptVersionsTest(PolicyTestCase):
    def test_matching_shared_versions_pass(self) -> None:
        self.assertEqual(self.errors(), [])

    def test_changed_gray_matter_declaration_fails(self) -> None:
        for path in ("tools/skill-map/package.json", "tools/skill-map/package-lock.json"):
            self.repo.edit_json(path, lambda d: (d.get("packages", {}).get("", d))["dependencies"]
                                .__setitem__("gray-matter", "^4.0.2"))
        self.assertFails("tools/skill-map/package.json: declares gray-matter '^4.0.2'",
                         "tools/capability-feed/package.json declares '^4.0.3'")

    def test_changed_zod_declaration_fails(self) -> None:
        for path in ("tools/capability-feed/package.json", "tools/capability-feed/package-lock.json"):
            self.repo.edit_json(path, lambda d: (d.get("packages", {}).get("", d))["dependencies"]
                                .__setitem__("zod", "^3.23.8"))
        self.assertFails("declares zod '^4.0.0'", "declares '^3.23.8'")

    def test_shared_dependency_moved_to_another_section_still_compared(self) -> None:
        def move(d):
            section = d.get("packages", {}).get("", d)
            section["devDependencies"] = {"zod": "~4.6.0"}
            del section["dependencies"]["zod"]
        for path in ("tools/skill-map/package.json", "tools/skill-map/package-lock.json"):
            self.repo.edit_json(path, move)
        self.assertFails("declares zod '~4.6.0'")

    def test_incompatible_sibling_resolved_zod_fails(self) -> None:
        self.repo.edit_json("tools/skill-map/package-lock.json", lambda d: d["packages"].__setitem__(
            "node_modules/zod", npm_entry("zod", "4.4.3")))
        self.assertFails("tools/skill-map/package-lock.json: node_modules/zod resolves to 4.4.3",
                         "resolves it to 4.6.5")

    def test_incompatible_sibling_resolved_gray_matter_fails(self) -> None:
        self.repo.edit_json("tools/capability-feed/package-lock.json", lambda d: d["packages"].__setitem__(
            "node_modules/gray-matter", npm_entry("gray-matter", "4.0.2", {"js-yaml": "^3.13.1"})))
        self.assertFails("node_modules/gray-matter resolves to 4.0.3")

    def test_shared_transitive_resolution_drift_fails(self) -> None:
        self.repo.edit_json("tools/skill-map/package-lock.json", lambda d: d["packages"].__setitem__(
            "node_modules/js-yaml", npm_entry("js-yaml", "3.15.1")))
        self.assertFails("node_modules/js-yaml resolves to 3.15.1")

    def test_same_version_with_different_integrity_fails(self) -> None:
        self.repo.edit_json("tools/skill-map/package-lock.json", lambda d: d["packages"]["node_modules/zod"]
                            .__setitem__("integrity", "sha512-" + "Z" * 40 + "=="))
        self.assertFails("node_modules/zod@4.6.5 integrity differs")

    def test_producer_only_dependency_is_not_drift(self) -> None:
        self.repo.edit_json("tools/skill-map/package-lock.json", lambda d: d["packages"].__setitem__(
            "node_modules/elkjs", npm_entry("elkjs", "0.12.1")))
        self.assertEqual(self.errors(), [])

    def test_lock_out_of_sync_with_manifest_fails(self) -> None:
        self.repo.edit_json("tools/skill-map/package.json", lambda d: d["dependencies"]
                            .__setitem__("elkjs", "^0.13.0"))
        self.assertFails("tools/skill-map/package-lock.json: dependencies differ from package.json")

    def test_missing_lock_fails(self) -> None:
        (self.repo.root / "tools/skill-map/package-lock.json").unlink()
        self.assertFails("tools/skill-map: has package.json but no package-lock.json")

    def test_lock_entry_without_integrity_or_registry_fails(self) -> None:
        def strip(d):
            d["packages"]["node_modules/elkjs"].pop("integrity")
            d["packages"]["node_modules/elkjs"]["resolved"] = "git+https://example.invalid/elkjs.git"
        self.repo.edit_json("tools/skill-map/package-lock.json", strip)
        self.assertFails("node_modules/elkjs has no sha512 integrity",
                         "node_modules/elkjs does not resolve from https://registry.npmjs.org/")

    def test_old_lockfile_version_fails(self) -> None:
        self.repo.edit_json("tools/skill-map/package-lock.json", lambda d: d.__setitem__("lockfileVersion", 1))
        self.assertFails("lockfileVersion 1")


class PythonLockTest(PolicyTestCase):
    def test_recognizes_hash_locked_format(self) -> None:
        report = check_versions.Report()
        pins, includes = check_versions.parse_lock(
            self.repo.root, self.repo.root / "skills/video/requirements.txt", report)
        self.assertEqual(report.errors, [])
        self.assertEqual([(p.name, p.version, p.marker) for p in pins], [
            ("certifi", "2026.10.23", ""),
            ("requests", "2.34.2", ""),
            ("colorama", "0.4.6", "sys_platform == 'win32'"),
        ])
        self.assertEqual(includes, [])
        _, includes = check_versions.parse_lock(
            self.repo.root, self.repo.root / "skills/hunter/requirements.txt", report)
        self.assertEqual(includes, [(self.repo.root / "skills/video/requirements.txt").resolve()])
        self.assertEqual(report.errors, [])

    def assertLineFails(self, line: str, fragment: str) -> None:
        self.repo.write("requirements-tooling.txt", TOOLING + line + "\n")
        self.assertFails(f"requirements-tooling.txt:3: {fragment}")

    def test_lower_bound_runtime_dependency_fails(self) -> None:
        self.assertLineFails("yt-dlp>=2026.10.21", "'yt-dlp>=2026.10.21' is open-ended or ranged")

    def test_bounded_range_fails(self) -> None:
        self.assertLineFails(f"pytest>=8,<10 {H1}", "'pytest>=8,<10' is open-ended or ranged")

    def test_compatible_release_fails(self) -> None:
        self.assertLineFails("protego~=0.5", "'protego~=0.5' is open-ended or ranged")

    def test_wildcard_pin_fails(self) -> None:
        self.assertLineFails(f"pillow==13.* {H1}", "'pillow==13.*' is open-ended or ranged")

    def test_bare_name_fails(self) -> None:
        self.assertLineFails("pyyaml", "'pyyaml' is open-ended or ranged")

    def test_exact_pin_without_hash_fails(self) -> None:
        self.assertLineFails("defusedxml==0.7.1", "'defusedxml==0.7.1' has no --hash=sha256 value")

    def test_url_requirement_fails(self) -> None:
        self.assertLineFails("tool @ https://example.invalid/tool.whl", "'tool @ https://example.invalid/tool.whl' installs from a URL or path")

    def test_editable_and_index_options_fail(self) -> None:
        self.assertLineFails("-e .", "option -e is not allowed")
        self.assertLineFails("--extra-index-url https://example.invalid/simple",
                             "option --extra-index-url is not allowed")

    def test_open_ended_test_dependency_in_included_layer_fails(self) -> None:
        self.repo.write("skills/video/requirements-dev.txt", "-r requirements-verification.txt\npytest>=8,<10\n")
        self.assertFails("skills/video/requirements-dev.txt:2: 'pytest>=8,<10' is open-ended or ranged")

    def test_missing_include_fails(self) -> None:
        self.repo.write("skills/hunter/requirements-dev.txt", f"-r requirements-test.txt\npytest==9.2.0 {H1}\n")
        self.assertFails("includes requirements-test.txt, which does not exist")

    def test_cross_file_version_drift_fails(self) -> None:
        self.repo.write("skills/hunter/requirements.txt", f"-r ../video/requirements.txt\npillow==12.0.0 {H3}\n")
        self.assertFails("drifts from", "pillow==12.0.0", "pillow==13.0.0")

    def test_duplicate_pin_inside_one_install_fails(self) -> None:
        self.repo.write("skills/video/requirements-dev.txt",
                        f"-r requirements-verification.txt\npytest==9.2.0 {H1}\nrequests==2.34.2 {H1}\n")
        self.assertFails("requests is pinned twice in one install")


class WorkflowInstallTest(PolicyTestCase):
    def add_step(self, run: str) -> None:
        self.repo.write(".github/workflows/ci.yml", CI + f"      - run: {run}\n")

    def test_unpinned_ci_pyyaml_install_fails(self) -> None:
        self.add_step("python3 -m pip install --quiet pyyaml")
        self.assertFails(".github/workflows/ci.yml:14: installs 'pyyaml' by name")

    def test_exact_but_unhashed_ci_pyyaml_install_fails(self) -> None:
        self.add_step("pip install pyyaml==6.0.3")
        self.assertFails("installs 'pyyaml==6.0.3' by name")

    def test_install_from_unchecked_file_fails(self) -> None:
        self.repo.write("deps.txt", "pyyaml\n")
        self.add_step("pip install -r deps.txt")
        self.assertFails("names deps.txt; only requirements*.txt files are checked as locks")

    def test_install_from_missing_lock_fails(self) -> None:
        self.add_step("pip install -r requirements-missing.txt")
        self.assertFails("names requirements-missing.txt, which is not a requirements file")

    def test_continued_command_with_package_fails(self) -> None:
        self.add_step("pip install -r requirements-tooling.txt \\\n          mypy")
        self.assertFails("installs 'mypy' by name")

    def test_npm_install_fails(self) -> None:
        self.add_step("npm install")
        self.assertFails("runs npm install; use npm ci")

    def test_pending_workflow_warns_and_stale_entry_fails(self) -> None:
        self.repo.write(".github/workflows/graph.yml", "jobs:\n  a:\n    steps:\n      - run: pip install pyyaml\n")
        report = check_versions.check(self.repo.root, {"graph.yml": "follow-up"})
        self.assertEqual(report.errors, [])
        self.assertEqual([str(w) for w in report.warnings],
                         [".github/workflows/graph.yml:4: installs 'pyyaml' by name; install it from a lock with -r"])
        self.assertIn("graph.yml", "\n".join(self.errors()))
        self.repo.write(".github/workflows/graph.yml", "jobs: {}\n")
        report = check_versions.check(self.repo.root, {"graph.yml": "follow-up"})
        self.assertEqual([str(e) for e in report.errors],
                         [".github/workflows/graph.yml: is listed in PENDING_WORKFLOWS but now passes; remove the entry"])


class RepositoryTest(unittest.TestCase):
    def test_this_repository_passes(self) -> None:
        out = io.StringIO()
        with redirect_stdout(out):
            code = check_versions.main([])
        self.assertEqual(code, 0, out.getvalue())
        self.assertIn("dependency-policy: PASS", out.getvalue())

    def test_cli_reports_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            Fixture(Path(tmp)).write("requirements.txt", "requests>=2.32,<3\n")
            out = io.StringIO()
            with redirect_stdout(out):
                code = check_versions.main(["--root", tmp])
        self.assertEqual(code, 1)
        self.assertIn("FAIL requirements.txt:1: 'requests>=2.32,<3' is open-ended or ranged", out.getvalue())
        self.assertIn("dependency-policy: FAIL", out.getvalue())


if __name__ == "__main__":
    unittest.main()
