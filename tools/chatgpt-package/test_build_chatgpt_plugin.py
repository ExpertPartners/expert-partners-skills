#!/usr/bin/env python3
"""
test_build_chatgpt_plugin.py -- machine-checkable gate for the ChatGPT package.

Splits the acceptance work honestly into the half a machine can settle and the
half it cannot:

  MACHINE (this file, runs anywhere, no network, no ChatGPT account):
    - the canonical SKILL.md satisfies the Agent Skills specification OpenAI
      defers to
    - the generated package has the exact structure the upload path requires
    - the generated frontmatter is reduced to the spec's six keys
    - implicit invocation is switched on, since a skill that must fire without
      magic words is worthless if that flag is off
    - the --no-mcp-dependency rebuild path still produces a valid package
    - ACCEPTANCE TEST 5 in full: no positive prompt in the acceptance set
      contains a magic word. This one is fully mechanical, so it is settled
      here rather than left to a human reading prompts and vouching for them.

  HUMAN (acceptance/fresh-chat-acceptance.md):
    - whether ChatGPT actually fires the skill and retrieves in a fresh chat.
      No API reaches Allison's ChatGPT chat surface, so that half is run by
      hand against written rubrics. It is not asserted here and must never be
      reported as passing on this file's word.

Usage:  python3 tools/chatgpt-package/test_build_chatgpt_plugin.py
Exit:   0 all machine checks pass, 1 at least one failed.
"""

from __future__ import annotations

import json
import re
import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import importlib.util

_spec = importlib.util.spec_from_file_location(
    "build_chatgpt_plugin", Path(__file__).resolve().parent / "build-chatgpt-plugin.py")
bcp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bcp)

import yaml

ACCEPTANCE = Path(__file__).resolve().parent / "acceptance" / "prompts.json"

FAILURES: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  ok   {label}")
    else:
        print(f"  FAIL {label}{': ' + detail if detail else ''}", file=sys.stderr)
        FAILURES.append(label)


def test_canonical_sources_are_spec_clean() -> None:
    print("canonical sources")
    source = json.loads(bcp.SOURCE_MANIFEST.read_text())
    for name in source["skills"]:
        src = bcp.resolve_skill(name)
        fm, _ = bcp.parse_frontmatter((src / "SKILL.md").read_text(encoding="utf-8"), name)
        try:
            bcp.validate_spec(fm, src.name, name)
            ok = True
        except bcp.SpecError as exc:
            ok, detail = False, str(exc)
        check(f"{name} satisfies the Agent Skills spec", ok,
              detail if not ok else "")
        d = fm["description"]
        check(f"{name} description has headroom under the 1024 cap",
              len(d) <= 1024, f"{len(d)} chars")
        check(f"{name} description names concrete triggers, not a bare topic",
              len(d) >= 200, f"only {len(d)} chars")


def test_build_structure() -> None:
    print("generated package structure")
    with tempfile.TemporaryDirectory() as td:
        out, zp = Path(td) / "out", Path(td) / "pkg.zip"
        result = bcp.build(out, zp, with_mcp=True)
        plugin = result["plugin"]

        with zipfile.ZipFile(zp) as zf:
            names = zf.namelist()
            tops = {n.split("/")[0] for n in names}
            check("archive has exactly one top-level folder", len(tops) == 1, str(sorted(tops)))
            check("top-level folder is the plugin name", tops == {plugin})
            check("manifest is at .codex-plugin/plugin.json",
                  f"{plugin}/.codex-plugin/plugin.json" in names)
            check("no macOS metadata in the archive",
                  not [n for n in names if "__MACOSX" in n or n.endswith(".DS_Store")])
            check("no checksums manifest leaked into the package",
                  not [n for n in names if n.endswith("checksums.sha256")])

            manifest = json.loads(zf.read(f"{plugin}/.codex-plugin/plugin.json"))
            check("manifest skills field is exactly './skills/'",
                  manifest.get("skills") == "./skills/", repr(manifest.get("skills")))
            for key in ("name", "version", "description"):
                check(f"manifest carries {key}", bool(manifest.get(key)))

            for skill in result["skills"]:
                sk = f"{plugin}/skills/{skill}/SKILL.md"
                check(f"{skill}: SKILL.md present at the skill root", sk in names)
                fm, body = bcp.parse_frontmatter(zf.read(sk).decode("utf-8"), sk)
                extra = sorted(set(fm) - set(bcp.SPEC_KEYS))
                check(f"{skill}: packaged frontmatter is spec-clean", not extra, str(extra))
                check(f"{skill}: packaged name matches its folder", fm.get("name") == skill)
                check(f"{skill}: body survived packaging intact", len(body) > 500)
                # REGRESSION, acceptance T1 failure of 2026-09-04. In a fresh
                # ChatGPT conversation the model demanded the chat be retitled
                # and confirmed before it would retrieve anything, so no Estate
                # read happened at all. The canonical source never carried that
                # vocabulary (grep-proven clean); the gate was injected from
                # elsewhere in the account. The skill now refuses the ceremony
                # explicitly, and that refusal must survive packaging.
                body_l = body.lower()
                for phrase in ("retrieval is never gated",
                               "rename the conversation",
                               "never identity"):
                    check(f"{skill}: no-ceremony guard survives packaging ({phrase!r})",
                          phrase in body_l)
                for banned in ("chair", "table birth", "title parity"):
                    check(f"{skill}: packaged skill stays free of governance vocabulary "
                          f"({banned!r})", banned not in body_l)

                skmd = [n for n in names
                        if n.lower().startswith(f"{plugin}/skills/{skill}/".lower())
                        and n.lower().endswith("/skill.md")]
                check(f"{skill}: exactly one SKILL.md in the bundle", len(skmd) == 1, str(skmd))

                y = yaml.safe_load(
                    zf.read(f"{plugin}/skills/{skill}/agents/openai.yaml").decode("utf-8"))
                check(f"{skill}: implicit invocation is enabled",
                      y.get("policy", {}).get("allow_implicit_invocation") is True,
                      "a skill that must fire without magic words needs this true")
                short = y.get("interface", {}).get("short_description", "")
                check(f"{skill}: short_description is within OpenAI's 25-64 range",
                      25 <= len(short) <= 64, f"{len(short)} chars")
                check(f"{skill}: MCP dependency declared when requested",
                      y.get("dependencies", {}).get("tools"))

        check("no .mcp.json is bundled (avoids the Desktop-only label)",
              not (out / result["plugin"] / ".mcp.json").exists())


def test_no_mcp_dependency_rebuild_path() -> None:
    print("rebuild path without the MCP dependency block")
    with tempfile.TemporaryDirectory() as td:
        out, zp = Path(td) / "out", Path(td) / "pkg.zip"
        result = bcp.build(out, zp, with_mcp=False)
        check("build succeeds and preflights", zp.exists())
        check("result records the dependency as absent",
              result["mcp_dependency_declared"] is False)
        with zipfile.ZipFile(zp) as zf:
            for skill in result["skills"]:
                y = yaml.safe_load(
                    zf.read(
                        f"{result['plugin']}/skills/{skill}/agents/openai.yaml").decode("utf-8"))
                check(f"{skill}: no dependencies block emitted", "dependencies" not in y)
                check(f"{skill}: implicit invocation still enabled",
                      y.get("policy", {}).get("allow_implicit_invocation") is True)


def test_acceptance_set_has_no_magic_words() -> None:
    """ACCEPTANCE TEST 5, settled mechanically.

    No positive-polarity prompt may contain a word that tells ChatGPT to look
    anything up internally. If a prompt needs a hint to pass, the skill has not
    been proven.
    """
    print("acceptance test 5, no magic words in any positive prompt")
    data = json.loads(ACCEPTANCE.read_text())
    forbidden = [w.lower() for w in data["magic_words_forbidden"]]
    positives = [t for t in data["tests"] if t["polarity"] == "positive"]
    check("the acceptance set actually contains positive prompts", len(positives) >= 3)
    for t in positives:
        low = t["prompt"].lower()
        hits = [w for w in forbidden if re.search(r"\b" + re.escape(w) + r"\b", low)]
        check(f"{t['id']} prompt is free of magic words", not hits, str(hits))
    for t in data["tests"]:
        check(f"{t['id']} declares a pass criterion", bool(t.get("pass_criteria")))
        if t["polarity"] == "positive":
            check(f"{t['id']} names at least one expected target",
                  bool(t.get("expected_targets")))


def main() -> int:
    for fn in (test_canonical_sources_are_spec_clean,
               test_build_structure,
               test_no_mcp_dependency_rebuild_path,
               test_acceptance_set_has_no_magic_words):
        fn()
        print()
    if FAILURES:
        print(f"FAILED: {len(FAILURES)} check(s): " + ", ".join(FAILURES), file=sys.stderr)
        return 1
    print("all machine checks passed. The fresh-chat behavioral half is NOT covered here; "
          "run tools/chatgpt-package/acceptance/fresh-chat-acceptance.md by hand.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
