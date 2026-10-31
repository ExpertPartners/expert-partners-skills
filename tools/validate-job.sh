#!/usr/bin/env bash
# One command that exits 0 on good work and non-zero otherwise.
# Used by Chat to Code Loop builders (AGENTS.md names it) and safe for people to run.
# Runs the same gates as .github/workflows/ci.yml on the files this branch changed.
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

BASE="${VALIDATE_BASE:-origin/main}"
if ! git rev-parse --verify --quiet "$BASE" >/dev/null; then
  BASE="$(git rev-parse --verify --quiet HEAD^ || git hash-object -t tree /dev/null)"
fi
MERGE_BASE="$(git merge-base "$BASE" HEAD 2>/dev/null || echo "$BASE")"

changed="$(git diff --name-only --diff-filter=ACMR "$MERGE_BASE" -- '*.md' '*.markdown' '*.mdx' '*.txt' '*.rst'; git ls-files --others --exclude-standard -- '*.md' '*.markdown' '*.mdx' '*.txt' '*.rst')"
changed="$(printf '%s\n' "$changed" | sort -u | grep . || true)"

echo "validate-job: base $MERGE_BASE"
if [ -n "$changed" ]; then
  echo "validate-job: changed text files"; printf '%s\n' "$changed"
  printf '%s\n' "$changed" | tr '\n' '\0' | xargs -0 python3 .ep/brand-lint.py
  md="$(printf '%s\n' "$changed" | grep -E '\.(md|markdown|mdx)$' || true)"
  if [ -n "$md" ]; then
    printf '%s\n' "$md" | tr '\n' '\0' | xargs -0 python3 .ep/frontmatter-lint.py --schema .ep/classification-schema.json
  fi
else
  echo "validate-job: no changed text files"
fi

python3 .ep/skill-description-lint.py --selftest

if command -v gitleaks >/dev/null 2>&1; then
  gitleaks git . --redact --config .gitleaks.toml
else
  echo "validate-job: gitleaks not installed here, CI runs it" >&2
fi

echo "validate-job: PASS"
