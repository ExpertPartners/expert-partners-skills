#!/usr/bin/env python3
"""Structural checks only. Factual truth and voice require the current sources."""

import argparse
import json
import re
from pathlib import Path

HEADINGS = [
    "ROLE & MISSION",
    "ICP",
    "VOICE",
    "THINKING & STRATEGY PROTOCOL",
    "KNOWLEDGE BASE",
    "GROUND RULES",
    "FINAL CHECK BEFORE DELIVERING",
]


def word_count(text):
    return len(re.findall(r"\S+", text))


def validate(text, filename):
    errors = []
    if Path(filename).name != "marketing-workspace-custom-instructions.md":
        errors.append("Use marketing-workspace-custom-instructions.md")
    if re.search(r"^\s*```", text, re.M):
        errors.append("The saved file must contain Markdown, not a surrounding code fence")
    matches = list(re.finditer(r"^##[ \t]+(.+?)[ \t]*$", text, re.M))
    if [m.group(1) for m in matches] != HEADINGS:
        errors.append("Level-two section headings must match the required order exactly")
    words = word_count(text)
    if words > 1000:
        errors.append(f"Total length is {words} words, maximum 1000")
    sections = {
        m.group(1): text[m.end():matches[i + 1].start() if i + 1 < len(matches) else len(text)]
        for i, m in enumerate(matches)
    }
    voice_words = word_count(sections.get("VOICE", ""))
    if not 80 <= voice_words <= 120:
        errors.append(f"VOICE is {voice_words} words, expected 80 to 120")
    ground = sections.get("GROUND RULES", "")
    if re.findall(r"^###[ \t]+(.+?)[ \t]*$", ground, re.M) != ["Always Do", "Never Do"]:
        errors.append("GROUND RULES needs Always Do then Never Do subheadings")
    # This catches mechanical inventory leaks, not arbitrary document titles.
    if re.search(r"\b[\w.-]+\.(?:md|docx?|pdf|txt|csv|xlsx?)\b|https?://", text, re.I):
        errors.append("Remove file references and URLs from the paste-ready instructions")
    if re.search(r"\[(?:company(?: name)?|insert\b[^]]*|todo|tbd|missing\b[^]]*)\]|\b(?:TODO|TBD)\b", text, re.I):
        errors.append("Resolve placeholders before delivering finished instructions")
    return {"valid": not errors, "words": words, "voice_words": voice_words, "errors": errors}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path)
    args = parser.parse_args()
    try:
        result = validate(args.file.read_text(encoding="utf-8"), args.file.name)
    except (OSError, UnicodeError) as exc:
        result = {"valid": False, "errors": [str(exc)]}
    print(json.dumps(result, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
