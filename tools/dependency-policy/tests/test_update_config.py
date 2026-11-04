"""Offline tests for .github/dependabot.yml, the dependency update configuration.

The file is parsed here without PyYAML, a package index, a registry or GitHub. The tests
check that it covers every Python requirements directory and every JavaScript producer
that check_versions.py polices, and that it only asks for pull requests to review: no
merge instruction, credential, permission grant, pull request count hold or age rule.
Fixture cases prove that a removed ecosystem or directory is detected. Network sockets
and subprocesses are disabled for the whole module, so nothing is activated or fetched.
"""

from __future__ import annotations

import copy
import re
import socket
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import check_versions  # noqa: E402

try:
    import yaml
except ImportError:  # the offline policy job runs without PyYAML
    yaml = None

REPO_ROOT = check_versions.REPO_ROOT
CONFIG_PATH = ".github/dependabot.yml"
GATE_PATH = "tools/auto-merge-gate/gate.py"

PYTHON_DIRS = {
    "/",
    "/plugins/research-ops/skills/source-hunter",
    "/plugins/research-ops/skills/video-discovery",
}
NPM_DIRS = {"/tools/capability-feed", "/tools/skill-map"}
MANIFEST = {"pip": "requirements*.txt", "npm": "package.json"}


def _blocked(*_args, **_kwargs):
    raise AssertionError("update-config tests must not open a network connection or run a process")


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


# ---------------------------------------------------------------------------
# A strict parser for the block YAML subset the configuration uses. Anything outside the
# subset (flow collections, anchors, multi-line scalars, tabs, ambiguous booleans) is
# refused rather than guessed, so a value this parser returns is the value YAML means.
# ---------------------------------------------------------------------------


class YamlSubsetError(ValueError):
    pass


KEY_RE = re.compile(r'^(?P<key>[A-Za-z0-9][A-Za-z0-9_.-]*|"[^"\\]*"):(?:\s+(?P<rest>.*))?$')
INT_RE = re.compile(r"^(0|-?[1-9][0-9]*)$")
PLAIN_RE = re.compile(r"^[A-Za-z/][A-Za-z0-9/_.@+-]*$")
YAML11_WORDS = {"yes", "no", "on", "off", "y", "n", "true", "false", "null"}


def _strip_comment(line: str) -> str:
    quote = ""
    for i, char in enumerate(line):
        if quote:
            if char == quote:
                quote = ""
        elif char in "\"'":
            quote = char
        elif char == "#" and (i == 0 or line[i - 1] == " "):
            return line[:i]
    return line


def _is_item(content: str) -> bool:
    return content == "-" or content.startswith("- ")


def _scalar(text: str, number: int):
    if text.startswith('"'):
        match = re.fullmatch(r'"([^"\\]*)"', text)
        if not match:
            raise YamlSubsetError(f"line {number}: unsupported double-quoted scalar {text!r}")
        return match.group(1)
    if text.startswith("'"):
        match = re.fullmatch(r"'([^']*)'", text)
        if not match:
            raise YamlSubsetError(f"line {number}: unsupported single-quoted scalar {text!r}")
        return match.group(1)
    if INT_RE.fullmatch(text):
        return int(text)
    if text in ("true", "false"):
        return text == "true"
    if text == "null":
        return None
    if text.lower() in YAML11_WORDS or not PLAIN_RE.fullmatch(text):
        raise YamlSubsetError(f"line {number}: unsupported or ambiguous scalar {text!r}; quote it")
    return text


def _block(lines: list, pos: int, indent: int):
    return _seq(lines, pos, indent) if _is_item(lines[pos][2]) else _map(lines, pos, indent)


def _seq(lines: list, pos: int, indent: int):
    items = []
    while pos < len(lines) and lines[pos][1] == indent and _is_item(lines[pos][2]):
        number, _, content = lines[pos]
        rest = content[1:].lstrip(" ")
        if not rest:
            pos += 1
            if pos < len(lines) and lines[pos][1] > indent:
                value, pos = _block(lines, pos, lines[pos][1])
            else:
                value = None
        elif KEY_RE.match(rest):
            lines[pos] = [number, indent + len(content) - len(rest), rest]
            value, pos = _map(lines, pos, lines[pos][1])
        else:
            value, pos = _scalar(rest, number), pos + 1
        items.append(value)
    if pos < len(lines) and lines[pos][1] > indent:
        raise YamlSubsetError(f"line {lines[pos][0]}: unexpected indentation")
    return items, pos


def _map(lines: list, pos: int, indent: int):
    result: dict = {}
    while pos < len(lines) and lines[pos][1] == indent:
        number, _, content = lines[pos]
        match = KEY_RE.match(content)
        if not match:
            raise YamlSubsetError(f"line {number}: expected 'key: value', got {content!r}")
        key = match.group("key").strip('"')
        if key in result:
            raise YamlSubsetError(f"line {number}: duplicate key {key!r}")
        rest = match.group("rest")
        pos += 1
        if rest:
            value = _scalar(rest, number)
        elif pos < len(lines) and lines[pos][1] > indent:
            value, pos = _block(lines, pos, lines[pos][1])
        elif pos < len(lines) and lines[pos][1] == indent and _is_item(lines[pos][2]):
            value, pos = _seq(lines, pos, indent)
        else:
            value = None
        result[key] = value
    if pos < len(lines) and lines[pos][1] > indent:
        raise YamlSubsetError(f"line {lines[pos][0]}: unexpected indentation")
    return result, pos


def parse_yaml_subset(text: str):
    lines = []
    for number, raw in enumerate(text.splitlines(), 1):
        if "\t" in raw:
            raise YamlSubsetError(f"line {number}: tab character")
        body = _strip_comment(raw).rstrip()
        if body.strip():
            lines.append([number, len(body) - len(body.lstrip(" ")), body.strip()])
    if not lines:
        raise YamlSubsetError("empty document")
    if lines[0][1] != 0:
        raise YamlSubsetError(f"line {lines[0][0]}: the document must start at column 1")
    value, pos = _block(lines, 0, 0)
    if pos != len(lines):
        raise YamlSubsetError(f"line {lines[pos][0]}: unexpected indentation")
    return value


# ---------------------------------------------------------------------------
# Rules for the configuration.
# ---------------------------------------------------------------------------

TOP_LEVEL_KEYS = {"version", "updates"}
ENTRY_KEYS = {"package-ecosystem", "directories", "schedule", "groups", "labels",
              "commit-message", "ignore", "allow"}
SCHEDULE_KEYS = {"interval", "day", "time", "timezone", "cronjob"}
INTERVALS = {"daily", "weekly", "monthly", "quarterly", "semiannually", "yearly", "cron"}
GROUP_KEYS = {"group-by", "patterns", "exclude-patterns", "applies-to", "update-types",
              "dependency-type"}
REFUSED = {
    "open-pull-requests-limit": "holds update pull requests at a fixed count",
    "cooldown": "is a dependency-age rule, which this repository has not decided",
    "registries": "configures registry credentials",
    "insecure-external-code-execution": "lets an update run code from a manifest",
    "directory": "is the single-path form; use directories so coverage is one list",
}
SENSITIVE_KEY_RE = re.compile(r"token|password|secret|credential|auth|username|permission|merge", re.I)
SENSITIVE_VALUE_RE = re.compile(r"\$\{\{|secrets\.|auto-?merge", re.I)
MERGE_STEP_RE = re.compile(
    r"gh\s+pr\s+(merge|review)|--auto\b|enablePullRequestAutoMerge|/merge\b|approve", re.I)


def _walk(value, where: str):
    if isinstance(value, dict):
        for key, child in value.items():
            yield f"{where}.{key}", key, child
            yield from _walk(child, f"{where}.{key}")
    elif isinstance(value, list):
        for i, child in enumerate(value):
            yield f"{where}[{i}]", None, child
            yield from _walk(child, f"{where}[{i}]")


def policy_problems(config) -> list[str]:
    if not isinstance(config, dict):
        return ["the configuration is not a mapping"]
    problems = []
    for path, key, child in _walk(config, "config"):
        if key is not None and SENSITIVE_KEY_RE.search(str(key)):
            problems.append(f"{path}: key {key!r} could carry a credential, permission or merge rule")
        if isinstance(child, str) and SENSITIVE_VALUE_RE.search(child):
            problems.append(f"{path}: value {child!r} references a secret or merge rule")
    for key in sorted(set(config) - TOP_LEVEL_KEYS):
        problems.append(f"config.{key}: {REFUSED.get(key, 'is not a reviewed top-level option')}")
    if config.get("version") != 2:
        problems.append(f"config.version: is {config.get('version')!r}, not 2")
    updates = config.get("updates")
    if not isinstance(updates, list) or not updates:
        return problems + ["config.updates: is not a non-empty list"]
    for i, entry in enumerate(updates):
        where = f"config.updates[{i}]"
        if not isinstance(entry, dict):
            problems.append(f"{where}: is not a mapping")
            continue
        for key in sorted(set(entry) - ENTRY_KEYS):
            problems.append(f"{where}.{key}: {REFUSED.get(key, 'is not a reviewed update option')}")
        ecosystem = entry.get("package-ecosystem")
        if ecosystem not in MANIFEST:
            problems.append(f"{where}.package-ecosystem: {ecosystem!r} is not pip or npm")
        directories = entry.get("directories")
        if not isinstance(directories, list) or not directories:
            problems.append(f"{where}.directories: is not a non-empty list")
            directories = []
        for directory in directories:
            if not isinstance(directory, str) or not directory.startswith("/"):
                problems.append(f"{where}.directories: {directory!r} is not a path from the repository root")
            elif "*" in directory:
                problems.append(f"{where}.directories: {directory!r} is a wildcard the coverage check cannot verify")
        if len(set(map(str, directories))) != len(directories):
            problems.append(f"{where}.directories: lists a directory twice")
        schedule = entry.get("schedule")
        if not isinstance(schedule, dict):
            problems.append(f"{where}.schedule: is not a mapping")
        else:
            for key in sorted(set(schedule) - SCHEDULE_KEYS):
                problems.append(f"{where}.schedule.{key}: is not a schedule option")
            if schedule.get("interval") not in INTERVALS:
                problems.append(f"{where}.schedule.interval: {schedule.get('interval')!r} is not a Dependabot interval")
        groups = entry.get("groups") or {}
        if not isinstance(groups, dict):
            problems.append(f"{where}.groups: is not a mapping")
            groups = {}
        for name, group in groups.items():
            if not isinstance(group, dict):
                problems.append(f"{where}.groups.{name}: is not a mapping")
                continue
            for key in sorted(set(group) - GROUP_KEYS):
                problems.append(f"{where}.groups.{name}.{key}: is not a group option")
        shared = [g for g in groups.values() if isinstance(g, dict) and g.get("group-by") == "dependency-name"
                  and "*" in (g.get("patterns") or ["*"]) and not g.get("exclude-patterns")
                  and not g.get("update-types") and not g.get("dependency-type")]
        if len(directories) > 1 and not shared:
            problems.append(f"{where}.groups: no group with group-by: dependency-name covers every dependency, "
                            "so a dependency two directories share could move in one of them only")
    return problems


def _as_dir(root: Path, manifest: Path) -> str:
    where = check_versions.rel(root, manifest.parent)
    return "/" if where in ("", ".") else "/" + where


def expected_directories(root: Path) -> dict[str, set[str]]:
    locks = check_versions.walk(root, lambda n: n.startswith("requirements") and n.endswith(".txt"))
    base = root / check_versions.JS_PRODUCERS_DIR
    producers = sorted(base.glob("*/package.json")) if base.is_dir() else []
    return {"pip": {_as_dir(root, p) for p in locks}, "npm": {_as_dir(root, p) for p in producers}}


def coverage_problems(config, root: Path) -> list[str]:
    expected = expected_directories(root)
    configured: dict[str, set[str]] = {ecosystem: set() for ecosystem in expected}
    present: set[str] = set()
    updates = config.get("updates") if isinstance(config, dict) else None
    for entry in updates if isinstance(updates, list) else []:
        if isinstance(entry, dict) and entry.get("package-ecosystem") in configured:
            ecosystem = entry["package-ecosystem"]
            present.add(ecosystem)
            directories = entry.get("directories")
            configured[ecosystem].update(d for d in directories or [] if isinstance(d, str))
    problems = []
    for ecosystem, directories in expected.items():
        if directories and ecosystem not in present:
            problems.append(f"no {ecosystem} entry; {MANIFEST[ecosystem]} lives in {', '.join(sorted(directories))}")
        for directory in sorted(directories - configured[ecosystem]):
            problems.append(f"{ecosystem} does not cover {directory}")
        for directory in sorted(configured[ecosystem] - directories):
            problems.append(f"{ecosystem} lists {directory}, which has no {MANIFEST[ecosystem]}")
    return problems


def workflow_problems(root: Path) -> list[str]:
    base = root / check_versions.WORKFLOWS_DIR
    problems = []
    for path in sorted(base.glob("*.y*ml")) if base.is_dir() else []:
        text = path.read_text(encoding="utf-8")
        if re.search(r"dependabot", text, re.I) and MERGE_STEP_RE.search(text):
            problems.append(f"{check_versions.rel(root, path)}: acts on Dependabot pull requests "
                            "with a merge or approval step")
    return problems


def all_problems(config, root: Path) -> list[str]:
    return policy_problems(config) + coverage_problems(config, root) + workflow_problems(root)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

CONFIG_TEXT = (REPO_ROOT / CONFIG_PATH).read_text(encoding="utf-8")
LOCK = "pyyaml==6.0.3 --hash=sha256:" + "a" * 64 + "\n"


class SandboxTest(unittest.TestCase):
    def test_network_and_processes_are_blocked(self) -> None:
        with self.assertRaises(AssertionError):
            socket.create_connection(("api.github.com", 443))
        with self.assertRaises(AssertionError):
            subprocess.run(["gh", "api", "repos/{owner}/{repo}/dependabot/alerts"])


class RepositoryConfigTest(unittest.TestCase):
    def setUp(self) -> None:
        self.config = parse_yaml_subset(CONFIG_TEXT)

    @unittest.skipIf(yaml is None, "PyYAML is not installed here; the subset parser still ran")
    def test_subset_parser_agrees_with_pyyaml(self) -> None:
        self.assertEqual(yaml.safe_load(CONFIG_TEXT), self.config)

    def test_discovers_the_actual_lock_and_producer_directories(self) -> None:
        self.assertEqual(expected_directories(REPO_ROOT), {"pip": PYTHON_DIRS, "npm": NPM_DIRS})

    def test_covers_both_npm_producers_and_every_python_requirements_directory(self) -> None:
        self.assertEqual(coverage_problems(self.config, REPO_ROOT), [])
        listed = {e["package-ecosystem"]: set(e["directories"]) for e in self.config["updates"]}
        self.assertEqual(listed, {"pip": PYTHON_DIRS, "npm": NPM_DIRS})

    def test_only_asks_for_reviewable_pull_requests(self) -> None:
        self.assertEqual(policy_problems(self.config), [])
        for entry in self.config["updates"]:
            self.assertNotIn("open-pull-requests-limit", entry)
            self.assertNotIn("cooldown", entry)
        self.assertNotIn("registries", self.config)

    def test_no_workflow_merges_or_approves_dependabot_pull_requests(self) -> None:
        self.assertEqual(workflow_problems(REPO_ROOT), [])

    def test_auto_merge_gate_considers_factory_pull_requests_only(self) -> None:
        gate = (REPO_ROOT / GATE_PATH).read_text(encoding="utf-8")
        self.assertRegex(gate, re.compile(r'^FACTORY_LOGIN = "factory-droid\[bot\]"$', re.M))
        self.assertNotIn("dependabot", gate.lower())


class FixtureRepo:
    """A synthetic tree with the same lock and producer directories as this repository."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.write("requirements-tooling.txt", LOCK)
        self.write("plugins/research-ops/skills/video-discovery/requirements.txt", LOCK)
        self.write("plugins/research-ops/skills/video-discovery/requirements-dev.txt", "-r requirements.txt\n")
        self.write("plugins/research-ops/skills/source-hunter/requirements.txt", LOCK)
        self.write("tools/capability-feed/package.json", "{}\n")
        self.write("tools/skill-map/package.json", "{}\n")
        self.write(".github/workflows/ci.yml", "name: ci\njobs: {}\n")

    def write(self, path: str, content: str) -> None:
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


class FixtureTestCase(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.repo = FixtureRepo(Path(tmp.name))
        self.config = parse_yaml_subset(CONFIG_TEXT)

    def entry(self, ecosystem: str) -> dict:
        return next(e for e in self.config["updates"] if e["package-ecosystem"] == ecosystem)

    def assertDetected(self, *fragments: str, config=None) -> None:
        problems = all_problems(self.config if config is None else config, self.repo.root)
        self.assertTrue(problems, "expected the configuration to be refused")
        joined = "\n".join(problems)
        for fragment in fragments:
            self.assertIn(fragment, joined)


class RemovedCoverageTest(FixtureTestCase):
    def test_baseline_fixture_passes(self) -> None:
        self.assertEqual(all_problems(self.config, self.repo.root), [])

    def test_removed_pip_ecosystem_is_detected(self) -> None:
        self.config["updates"].remove(self.entry("pip"))
        self.assertDetected("no pip entry", "pip does not cover /plugins/research-ops/skills/source-hunter")

    def test_removed_npm_ecosystem_is_detected(self) -> None:
        self.config["updates"].remove(self.entry("npm"))
        self.assertDetected("no npm entry", "npm does not cover /tools/capability-feed",
                            "npm does not cover /tools/skill-map")

    def test_each_removed_npm_directory_is_detected(self) -> None:
        for directory in sorted(NPM_DIRS):
            with self.subTest(directory=directory):
                config = copy.deepcopy(self.config)
                next(e for e in config["updates"] if e["package-ecosystem"] == "npm")["directories"].remove(directory)
                self.assertDetected(f"npm does not cover {directory}", config=config)

    def test_each_removed_python_directory_is_detected(self) -> None:
        for directory in sorted(PYTHON_DIRS):
            with self.subTest(directory=directory):
                config = copy.deepcopy(self.config)
                next(e for e in config["updates"] if e["package-ecosystem"] == "pip")["directories"].remove(directory)
                self.assertDetected(f"pip does not cover {directory}", config=config)

    def test_directory_removed_from_the_file_text_is_detected(self) -> None:
        line = '      - "/tools/skill-map"\n'
        self.assertIn(line, CONFIG_TEXT)
        self.assertDetected("npm does not cover /tools/skill-map",
                            config=parse_yaml_subset(CONFIG_TEXT.replace(line, "")))

    def test_ecosystem_swapped_to_wrong_directory_is_detected(self) -> None:
        self.entry("npm")["package-ecosystem"] = "pip"
        self.assertDetected("no npm entry", "pip lists /tools/skill-map, which has no requirements*.txt")

    def test_new_lock_directory_without_coverage_is_detected(self) -> None:
        self.repo.write("plugins/new-plugin/skills/new-skill/requirements.txt", LOCK)
        self.assertDetected("pip does not cover /plugins/new-plugin/skills/new-skill")

    def test_new_producer_without_coverage_is_detected(self) -> None:
        self.repo.write("tools/new-producer/package.json", "{}\n")
        self.assertDetected("npm does not cover /tools/new-producer")

    def test_stale_directory_is_detected(self) -> None:
        (self.repo.root / "plugins/research-ops/skills/source-hunter/requirements.txt").unlink()
        self.assertDetected("pip lists /plugins/research-ops/skills/source-hunter, which has no requirements*.txt")

    def test_vendored_lock_is_not_coverage(self) -> None:
        self.repo.write("tools/skill-map/node_modules/pkg/requirements.txt", LOCK)
        self.assertEqual(all_problems(self.config, self.repo.root), [])


class PolicyTest(FixtureTestCase):
    def test_pull_request_count_hold_is_refused(self) -> None:
        for limit in (0, 2):
            with self.subTest(limit=limit):
                config = copy.deepcopy(self.config)
                config["updates"][0]["open-pull-requests-limit"] = limit
                self.assertDetected("open-pull-requests-limit: holds update pull requests at a fixed count",
                                    config=config)

    def test_dependency_age_rule_is_refused(self) -> None:
        self.entry("npm")["cooldown"] = {"default-days": 7}
        self.assertDetected("cooldown: is a dependency-age rule")

    def test_registry_credentials_are_refused(self) -> None:
        self.config["registries"] = {"npm-private": {"type": "npm-registry", "url": "https://example.invalid",
                                                     "token": "${{secrets.NPM_TOKEN}}"}}
        self.assertDetected("config.registries: configures registry credentials",
                            "key 'token' could carry a credential", "references a secret")

    def test_secret_reference_in_any_value_is_refused(self) -> None:
        self.entry("pip")["commit-message"] = {"prefix": "${{ secrets.PREFIX }}"}
        self.assertDetected("references a secret or merge rule")

    def test_merge_instruction_is_refused(self) -> None:
        self.entry("pip")["labels"] = ["automerge"]
        self.assertDetected("value 'automerge' references a secret or merge rule")
        config = copy.deepcopy(self.config)
        config["updates"][0]["auto-merge"] = True
        self.assertDetected("key 'auto-merge' could carry a credential, permission or merge rule", config=config)

    def test_permission_grant_is_refused(self) -> None:
        self.config["permissions"] = {"contents": "write"}
        self.assertDetected("key 'permissions' could carry a credential, permission or merge rule")

    def test_code_execution_is_refused(self) -> None:
        self.entry("pip")["insecure-external-code-execution"] = "allow"
        self.assertDetected("lets an update run code from a manifest")

    def test_unknown_option_is_refused(self) -> None:
        self.entry("npm")["target-branch"] = "release"
        self.assertDetected("target-branch: is not a reviewed update option")

    def test_shared_dependencies_must_move_together(self) -> None:
        del self.entry("npm")["groups"]
        self.assertDetected("config.updates[1].groups: no group with group-by: dependency-name")
        config = parse_yaml_subset(CONFIG_TEXT)
        config["updates"][0]["groups"]["python-locks"]["patterns"] = ["pillow"]
        self.assertDetected("config.updates[0].groups: no group", config=config)

    def test_single_directory_form_and_wildcards_are_refused(self) -> None:
        npm = self.entry("npm")
        npm["directory"] = npm.pop("directories")[0]
        self.assertDetected("directory: is the single-path form", "directories: is not a non-empty list")
        config = parse_yaml_subset(CONFIG_TEXT)
        config["updates"][1]["directories"] = ["/tools/*"]
        self.assertDetected("is a wildcard the coverage check cannot verify", config=config)

    def test_wrong_version_and_interval_are_refused(self) -> None:
        self.config["version"] = 1
        self.entry("pip")["schedule"]["interval"] = "hourly"
        self.assertDetected("config.version: is 1, not 2", "'hourly' is not a Dependabot interval")

    def test_workflow_that_merges_dependabot_pull_requests_is_refused(self) -> None:
        self.repo.write(".github/workflows/dependabot-merge.yml",
                        "on: pull_request\njobs:\n  merge:\n    if: github.actor == 'dependabot[bot]'\n"
                        "    steps:\n      - uses: dependabot/fetch-metadata@v2\n"
                        "      - run: gh pr merge --auto --squash \"$PR_URL\"\n")
        self.assertDetected(".github/workflows/dependabot-merge.yml: acts on Dependabot pull requests")


class SubsetParserTest(unittest.TestCase):
    def test_parses_nested_mappings_and_sequences(self) -> None:
        text = ('version: 2  # comment\nupdates:\n  - package-ecosystem: "npm"\n    directories:\n'
                '      - "/a#b"\n      - /c\n    schedule:\n      interval: weekly\nlist:\n- 1\n- \'x\'\n')
        self.assertEqual(parse_yaml_subset(text), {
            "version": 2,
            "updates": [{"package-ecosystem": "npm", "directories": ["/a#b", "/c"],
                         "schedule": {"interval": "weekly"}}],
            "list": [1, "x"],
        })

    def test_refuses_what_it_cannot_read_exactly(self) -> None:
        cases = {
            "flow sequence": "patterns: [\"*\"]\n",
            "flow mapping": "schedule: {interval: weekly}\n",
            "tab": "version:\t2\n",
            "duplicate key": "version: 2\nversion: 2\n",
            "bad indentation": "updates:\n  - a\n   - b\n",
            "ambiguous boolean": "enabled: yes\n",
            "anchor": "base: &anchor x\n",
            "block scalar": "text: |\n  x\n",
            "octal-looking number": "mode: 0755\n",
            "indented document": "  version: 2\n",
        }
        for name, text in cases.items():
            with self.subTest(case=name):
                with self.assertRaises(YamlSubsetError):
                    parse_yaml_subset(text)

    @unittest.skipIf(yaml is None, "PyYAML is not installed here")
    def test_agrees_with_pyyaml_on_its_own_examples(self) -> None:
        text = "a: 1\nb:\n  - x\n  - c: 'd'\n    e: null\nf: true\n"
        self.assertEqual(yaml.safe_load(text), parse_yaml_subset(text))


if __name__ == "__main__":
    unittest.main()
