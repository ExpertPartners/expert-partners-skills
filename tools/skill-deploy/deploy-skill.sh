#!/usr/bin/env bash
# skill-deploy: the sole producer of deployed skill copies and upload zips,
# standalone or plugin-carried, single-skill or full-plugin bundle.
# ADR 0056 point 8 (deployed-copy drift control): every deployed copy carries
# a DEPLOYED COPY header naming the canonical home, a version stamp, and a
# SHA-256 checksum manifest committed alongside. Hand-editing a deployed copy
# is a violation; fixes flow through canonical source and this script.
#
# Usage:
#   deploy-skill.sh <skill-name> [--to <deploy-dir>] [--zip <zip-path>]
#   deploy-skill.sh <plugin-name> --bundle --zip <zip-path>
#
#   <skill-name>   directory under skills/ (standalone canonical), or, when
#                  no such directory exists, the single plugins/*/skills/<name>
#                  directory that carries it (a plugin-only skill with no
#                  other canonical home -- code-block-routing, pin, lane-spawn
#                  as of 2026-08-07).
#   <plugin-name>  (with --bundle) directory under plugins/ -- zips the whole
#                  plugin bundle instead of one skill.
#   --to           deployed-copy destination dir (e.g. aura .claude/skills).
#                  The copy lands at <deploy-dir>/<skill-name>/. Not valid
#                  with --bundle; bundles are zip-only archival artifacts.
#   --zip          build a claude.ai upload zip (skill) or an archival
#                  bundle zip (--bundle) at the given path.
#   --bundle       treat the positional argument as a plugin name and zip
#                  plugins/<plugin-name>/ in full, manifest included.
#
# Flags compose except --bundle excludes --to. The script never commits;
# the caller reviews and commits so the diff stays visible.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
NAME="${1:?usage: deploy-skill.sh <skill-name|plugin-name> [--to dir] [--zip path] [--bundle]}"
shift

DEPLOY_DIR="" ZIP_PATH="" BUNDLE=0
while [ $# -gt 0 ]; do
  case "$1" in
    --to)     DEPLOY_DIR="$2"; shift 2 ;;
    --zip)    ZIP_PATH="$2";  shift 2 ;;
    --bundle) BUNDLE=1; shift ;;
    *) echo "FATAL: unknown arg $1" >&2; exit 1 ;;
  esac
done

TODAY=$(date +%Y-%m-%d)

plugin_version() { # plugin_version <plugin-name> -- reads plugins/<name>/.claude-plugin/plugin.json
  python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['version'])" \
    "$REPO_ROOT/plugins/$1/.claude-plugin/plugin.json"
}

manifest() { # write checksums.sha256 over a dir (excluding the manifest itself)
  ( cd "$1" && find . -type f ! -name checksums.sha256 -print0 | sort -z \
    | xargs -0 shasum -a 256 > checksums.sha256 )
}

if [ "$BUNDLE" -eq 1 ]; then
  [ -z "$DEPLOY_DIR" ] || { echo "FATAL: --bundle does not support --to (bundles are zip-only archival artifacts)" >&2; exit 1; }
  [ -n "$ZIP_PATH" ] || { echo "FATAL: --bundle requires --zip" >&2; exit 1; }
  SRC="$REPO_ROOT/plugins/$NAME"
  [ -f "$SRC/.claude-plugin/plugin.json" ] || { echo "FATAL: $SRC/.claude-plugin/plugin.json not found -- $NAME is not a plugin" >&2; exit 1; }
  VERSION=$(plugin_version "$NAME")
  STAGE=$(mktemp -d)
  rsync -a "$SRC/" "$STAGE/$NAME/"
  manifest "$STAGE/$NAME"
  mkdir -p "$(dirname "$ZIP_PATH")"
  rm -f "$ZIP_PATH"
  ( cd "$STAGE" && zip -qr "$ZIP_PATH" "$NAME" )
  rm -rf "$STAGE"
  echo "bundle zip: $ZIP_PATH ($NAME $VERSION) sha256=$(shasum -a 256 "$ZIP_PATH" | cut -d' ' -f1)"
  exit 0
fi

SKILL_NAME="$NAME"
SRC="$REPO_ROOT/skills/$SKILL_NAME"
SOURCE_KIND="standalone"
PLUGIN_NAME=""

if [ ! -f "$SRC/SKILL.md" ]; then
  # Not homed under skills/ -- the only other legitimate canonical home is a
  # single plugins/*/skills/<name> directory (a plugin-only skill, no other
  # home to fall back to).
  MATCH_COUNT=0
  SRC_CANDIDATE=""
  for d in "$REPO_ROOT"/plugins/*/skills/"$SKILL_NAME"; do
    if [ -f "$d/SKILL.md" ]; then
      MATCH_COUNT=$((MATCH_COUNT + 1))
      SRC_CANDIDATE="$d"
    fi
  done
  if [ "$MATCH_COUNT" -eq 0 ]; then
    echo "FATAL: $SKILL_NAME has no SKILL.md under skills/ or plugins/*/skills/" >&2
    exit 1
  elif [ "$MATCH_COUNT" -gt 1 ]; then
    echo "FATAL: $SKILL_NAME exists under more than one plugin -- ambiguous, disambiguate manually" >&2
    exit 1
  fi
  SRC="$SRC_CANDIDATE"
  SOURCE_KIND="plugin"
  PLUGIN_NAME="$(basename "$(dirname "$(dirname "$SRC")")")"
fi

if [ "$SOURCE_KIND" = "standalone" ]; then
  # Version stamp: the "-- vX.Y (date)" line in the canonical SKILL.md title.
  VERSION=$(grep -m1 -oE 'v[0-9]+\.[0-9]+' "$SRC/SKILL.md" || true)
  [ -n "$VERSION" ] || { echo "FATAL: no vX.Y version line in $SRC/SKILL.md" >&2; exit 1; }
else
  # Plugin-carried skill with no standalone home: its release cadence IS the
  # plugin's, so the plugin's own semver is the version stamp.
  VERSION=$(plugin_version "$PLUGIN_NAME")
  echo "note: $SKILL_NAME has no skills/ home; sourcing from plugins/$PLUGIN_NAME/skills/$SKILL_NAME, versioned to plugin $VERSION" >&2
fi

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
  python3 - "$DEST/SKILL.md" "$SKILL_NAME" "$VERSION" "$TODAY" "$SOURCE_KIND" "$PLUGIN_NAME" <<'PY'
import sys
path, name, version, today, kind, plugin = sys.argv[1:7]
canonical = (f"expert-partners-skills plugins/{plugin}/skills/{name}/SKILL.md"
             if kind == "plugin" else
             f"expert-partners-skills skills/{name}/SKILL.md")
text = open(path).read()
header = (f"# DEPLOYED COPY ({today}, skill-deploy pipeline): the canonical home is\n"
          f"# {canonical}. Deployed at {version}.\n"
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
