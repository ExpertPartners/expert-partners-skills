#!/usr/bin/env python3
"""Deterministic source-dossier scaffolder for the source-ingestion skill.

Builds the two-file dossier shape documented in
../reference/dossier-schema.md at <out>/<domain>/<creator-slug>/<source-slug>/.
Never touches network, git, or any real corpus; it only writes local files
under the --out path the caller gives it. Classification (title, creator,
domain, ownership, CORE) is the assistant's job per reference/protocol.md;
this script only turns an already-made decision into a correctly shaped
package, deterministically, every time.
"""
import argparse
import json
import re
import sys
from pathlib import Path

SOURCE_TYPES = [
    "pdf", "docx", "deck", "youtube-video", "youtube-transcript",
    "podcast-transcript", "course", "drive-file", "pasted-text",
    "research-report", "web-page", "interview", "original",
]
OWNERSHIP = ["allison-ep", "third-party", "unclear"]
BINARY = ["stored", "linked", "both", "not-applicable"]


def slugify(text):
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return re.sub(r"-+", "-", text).strip("-")


def yaml_list(items):
    if not items:
        return "[]"
    return "[" + ", ".join(items) + "]"


def build_readme(a):
    core_basis = a.core_basis or ("recommended, not yet ruled" if a.core else "not core")
    lines = [
        "---",
        f"title: {a.title}",
        f"creator: {a.creator}",
        f"source_type: {a.source_type}",
        f"domain: {a.domain}",
        f"methodology: {a.methodology or 'null'}",
        f"provenance: {a.provenance}",
        f"original_location: {a.original_location}",
        f"date: {a.date}",
        f"ownership: {a.ownership}",
        f"core: {'true' if a.core else 'false'}",
        f"core_basis: {core_basis}",
        f"downstream: {yaml_list(a.downstream)}",
        f"destination: {a.destination}",
        f"binary: {a.binary}",
        f"binary_location: {a.binary_location or 'null'}",
        "---",
        "",
        f"# {a.title}",
        "",
        "## Why this source matters",
        "",
        a.why or "(fill in: one paragraph on why this source matters)",
        "",
        "## What it is",
        "",
        a.what or "(fill in: one paragraph plainly describing the source)",
        "",
        "## Related sources",
        "",
        "\n".join(f"- {r}" for r in a.related) if a.related else "(none recorded yet)",
        "",
    ]
    return "\n".join(lines)


def build_source_record(a):
    sections = [
        f"# {a.title} -- source record",
        "",
        "## Concepts, frameworks, and principles",
        "",
        "(fill in from the actual source)",
        "",
        "## Terminology",
        "",
        "(fill in if the source coins or specially uses terms)",
        "",
        "## Examples",
        "",
        "(fill in concrete examples or case studies from the source)",
        "",
        "## References",
        "",
        "(page numbers, timestamps, section headings, or slide numbers, "
        "only when the source format actually supports them)",
        "",
        "## Allison / Expert Partners observations",
        "",
        "(commentary ABOUT the source, kept separate from the source's own "
        "claims; graduates to a downstream repo if it becomes doctrine)",
        "",
    ]
    if a.source_type in ("youtube-video", "youtube-transcript", "podcast-transcript"):
        sections += [
            "## Machine-readable transcript",
            "",
            "(timestamped transcript appendix, if not already covered above)",
            "",
        ]
    return "\n".join(sections)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--title", required=True)
    p.add_argument("--creator", required=True)
    p.add_argument("--source-type", required=True, choices=SOURCE_TYPES)
    p.add_argument("--domain", required=True)
    p.add_argument("--methodology", default="")
    p.add_argument("--provenance", required=True)
    p.add_argument("--original-location", required=True)
    p.add_argument("--date", required=True)
    p.add_argument("--ownership", required=True, choices=OWNERSHIP)
    p.add_argument("--core", action="store_true")
    p.add_argument("--core-basis", default="")
    p.add_argument("--downstream", default="", help="comma-separated list")
    p.add_argument("--destination", required=True)
    p.add_argument("--binary", required=True, choices=BINARY)
    p.add_argument("--binary-location", default="")
    p.add_argument("--why", default="")
    p.add_argument("--what", default="")
    p.add_argument("--related", default="", help="comma-separated list")
    p.add_argument("--creator-slug", default="")
    p.add_argument("--source-slug", default="")
    p.add_argument("--out", required=True)
    p.add_argument("--dry-run", action="store_true",
                    help="print the planned path and files, write nothing")
    a = p.parse_args()

    a.downstream = [d.strip() for d in a.downstream.split(",") if d.strip()]
    a.related = [r.strip() for r in a.related.split(",") if r.strip()]
    if a.core and not a.core_basis:
        print("FATAL: --core requires --core-basis (Allison's own words, "
              "or 'recommended, not yet ruled')", file=sys.stderr)
        return 2

    creator_slug = a.creator_slug or slugify(a.creator)
    source_slug = a.source_slug or slugify(a.title)
    domain_slug = slugify(a.domain)
    target = Path(a.out) / domain_slug / creator_slug / source_slug

    if a.dry_run:
        print(json.dumps({
            "target": str(target),
            "files": ["README.md", "source-record.md"],
            "core": a.core,
            "destination": a.destination,
        }, indent=2))
        return 0

    target.mkdir(parents=True, exist_ok=True)
    (target / "README.md").write_text(build_readme(a) + "\n", encoding="utf-8")
    (target / "source-record.md").write_text(build_source_record(a) + "\n", encoding="utf-8")
    print(f"dossier scaffolded: {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
