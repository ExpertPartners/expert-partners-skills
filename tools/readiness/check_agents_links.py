#!/usr/bin/env python3
"""Validate local Markdown links in the repository's root AGENTS.md."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

REPO_ROOT = Path(__file__).resolve().parents[2]
AGENTS_FILE = REPO_ROOT / "AGENTS.md"
FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
FENCE_CLOSE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})\s*$")
INLINE_CODE_RE = re.compile(r"(`+).*?\1")
LINK_RE = re.compile(
    r"(?<!!)\[(?:\\.|[^\]\n])+\]\("
    r"(?:<(?P<angle>[^>\n]+)>|(?P<plain>[^)\s]+))"
    r"(?:\s+(?:\"[^\"]*\"|'[^']*'|\([^)]+\)))?\)"
)
HEADING_RE = re.compile(r"^ {0,3}#{1,6}\s+(.+?)\s*#*\s*$")


def without_code(text: str) -> str:
    """Remove fenced code while preserving line numbers and link labels."""
    output: list[str] = []
    fence_char = ""
    fence_size = 0

    for line in text.splitlines():
        opening = FENCE_RE.match(line)
        if not fence_char and opening:
            marker = opening.group(1)
            fence_char = marker[0]
            fence_size = len(marker)
            output.append("")
            continue

        if fence_char:
            closing = FENCE_CLOSE_RE.match(line)
            if (
                closing
                and closing.group(1)[0] == fence_char
                and len(closing.group(1)) >= fence_size
            ):
                fence_char = ""
                fence_size = 0
            output.append("")
            continue

        output.append(line)

    return "\n".join(output)


def markdown_anchors(path: Path) -> set[str]:
    """Return GitHub-style anchors for Markdown headings in a local file."""
    anchors: set[str] = set()
    used: dict[str, int] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = HEADING_RE.match(line)
        if not match:
            continue
        heading = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", match.group(1))
        heading = re.sub(r"`([^`]*)`", r"\1", heading)
        slug = re.sub(r"[^\w\- ]", "", heading.lower())
        slug = re.sub(r"\s+", "-", slug.strip())
        occurrence = used.get(slug, 0)
        used[slug] = occurrence + 1
        anchors.add(slug if occurrence == 0 else f"{slug}-{occurrence}")
    return anchors


def validate_links(agents_file: Path) -> list[str]:
    """Return errors for broken or repository-escaping local Markdown links."""
    source = agents_file.resolve()
    repo_root = source.parent
    errors: list[str] = []

    for line_number, line in enumerate(
        without_code(source.read_text(encoding="utf-8")).splitlines(), 1
    ):
        for match in LINK_RE.finditer(line):
            if any(
                span.start() <= match.start() and match.end() <= span.end()
                for span in INLINE_CODE_RE.finditer(line)
            ):
                continue
            target = match.group("angle") or match.group("plain")
            parsed = urlsplit(target)
            if parsed.scheme or parsed.netloc:
                continue

            path_text = unquote(parsed.path)
            destination = (repo_root / path_text).resolve() if path_text else source
            if not destination.is_relative_to(repo_root):
                errors.append(
                    f"{source.name}:{line_number}: local link {target!r} escapes the repository"
                )
                continue
            if not destination.exists():
                errors.append(f"{source.name}:{line_number}: local link {target!r} does not exist")
                continue
            if (
                parsed.fragment
                and destination.is_file()
                and destination.suffix.lower()
                in {
                    ".md",
                    ".markdown",
                    ".mdx",
                }
            ):
                if unquote(parsed.fragment) not in markdown_anchors(destination):
                    errors.append(
                        f"{source.name}:{line_number}: local link {target!r} has no matching heading"
                    )

    return errors


def main() -> int:
    errors = validate_links(AGENTS_FILE)
    if errors:
        print("\n".join(f"FAIL {error}" for error in errors))
        return 1
    print("agents-links: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
