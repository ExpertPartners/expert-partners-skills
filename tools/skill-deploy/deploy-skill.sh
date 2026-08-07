#!/usr/bin/env bash
# skill-deploy: the sole producer of deployed skill copies and upload zips.
# ADR 0056 point 8 (deployed-copy drift control): every deployed copy carries
# a DEPLOYED COPY header naming the canonical home, a version stamp, and a
# SHA-256 checksum manifest committed alongside. Hand-editing a deployed copy
# is a violation; fixes flow through canonical source and this script.
#
# Usage:
#   deploy-skill.sh <skill-name> [--to <deploy-dir>] [--zip <zip-path>]
#
#   <skill-name>   directory under skills/ in this repo (canonical source)
#   --to           deployed-copy destination dir (e.g. aura .claude/skills).
#                  The copy lands at <deploy-dir>/<skill-name>/.
#   --zip          build a claude.ai upload zip at the given path.
#
# Both flags are optional and composable. The script never commits; the
# caller reviews and commits so the diff stays visible.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SKILL_NAME="${1:?usage: deploy-skill.sh <skill-name> [--to dir] [--zip path]}"
shift
SRC="$REPO_ROOT/skills/$SKILL_NAME"
[ -f "$SRC/SKILL.md" ] || { echo "FATAL: $SRC/SKILL.md not found" >&2; exit 1; }

DEPLOY_DIR="" ZIP_PATH=""
while [ $# -gt 0 ]; do
  case "$1" in
    --to)  DEPLOY_DIR="$2"; shift 2 ;;
    --zip) ZIP_PATH="$2";  shift 2 ;;
    *) echo "FATAL: unknown arg $1" >&2; exit 1 ;;
  esac
done

# Version stamp: the "-- vX.Y (date)" line in the canonical SKILL.md title.
VERSION=$(grep -m1 -oE 'v[0-9]+\.[0-9]+' "$SRC/SKILL.md" || true)
[ -n "$VERSION" ] || { echo "FATAL: no vX.Y version line in $SRC/SKILL.md" >&2; exit 1; }
TODAY=$(date +%Y-%m-%d)

manifest() { # write checksums.sha256 over a skill dir (excluding the manifest itself)
  ( cd "$1" && find . -type f ! -name checksums.sha256 -print0 | sort -z \
    | xargs -0 shasum -a 256 > checksums.sha256 )
}

if [ -n "$DEPLOY_DIR" ]; then
  DEST="$DEPLOY_DIR/$SKILL_NAME"
  mkdir -p "$DEST"
  # Refuse to clobber a hand-edited deployed copy silently: if a manifest
  # exists and fails verification, stop and surface it.
  if [ -f "$DEST/checksums.sha256" ]; then
    ( cd "$DEST" && shasum -a 256 -c checksums.sha256 --quiet ) \
      || { echo "FATAL: existing deployed copy at $DEST fails its manifest (hand-edit drift). Resolve before redeploying." >&2; exit 1; }
  fi
  rsync -a --delete --exclude checksums.sha256 "$SRC/" "$DEST/"
  # Inject the DEPLOYED COPY header into the frontmatter, after description.
  python3 - "$DEST/SKILL.md" "$SKILL_NAME" "$VERSION" "$TODAY" <<'PY'
import sys
path, name, version, today = sys.argv[1:5]
text = open(path).read()
header = (f"# DEPLOYED COPY ({today}, skill-deploy pipeline): the canonical home is\n"
          f"# expert-partners-skills skills/{name}/SKILL.md. Deployed at {version}.\n"
          f"# Edit the canonical copy first, then redeploy via tools/skill-deploy.\n")
lines = text.split("\n")
# insert before the closing '---' of the frontmatter block
end = next(i for i, l in enumerate(lines[1:], 1) if l.strip() == "---")
lines[end:end] = header.rstrip("\n").split("\n")
open(path, "w").write("\n".join(lines))
PY
  manifest "$DEST"
  echo "deployed: $DEST ($VERSION), manifest: $DEST/checksums.sha256"
fi

if [ -n "$ZIP_PATH" ]; then
  STAGE=$(mktemp -d)
  rsync -a "$SRC/" "$STAGE/$SKILL_NAME/"
  manifest "$STAGE/$SKILL_NAME"
  mkdir -p "$(dirname "$ZIP_PATH")"
  rm -f "$ZIP_PATH"
  ( cd "$STAGE" && zip -qr "$ZIP_PATH" "$SKILL_NAME" )
  rm -rf "$STAGE"
  echo "zip: $ZIP_PATH ($VERSION) sha256=$(shasum -a 256 "$ZIP_PATH" | cut -d' ' -f1)"
fi
