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
#   deploy-skill.sh --check-all
#
#   --check-all    repo-wide claude.ai upload-readiness sweep over every
#                  canonical SKILL.md, no deploy and no zip. Exits non-zero
#                  listing every skill whose frontmatter the upload UI would
#                  reject. Run this before any carry-back that claims a
#                  standalone shelf was delivered.
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
if [ "${1:-}" = "--check-all" ]; then
  NAME=""; CHECK_ALL=1; shift
else
  NAME="${1:?usage: deploy-skill.sh <skill-name|plugin-name> [--to dir] [--zip path] [--bundle] | deploy-skill.sh --check-all}"
  CHECK_ALL=0
  shift
fi

DEPLOY_DIR="" ZIP_PATH="" BUNDLE=0
while [ $# -gt 0 ]; do
  case "$1" in
    --to)        DEPLOY_DIR="$2"; shift 2 ;;
    --zip)       ZIP_PATH="$2";  shift 2 ;;
    --bundle)    BUNDLE=1; shift ;;
    --check-all) CHECK_ALL=1; shift ;;
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

# upload_preflight <SKILL.md path> -- enforce the constraints claude.ai's Skills
# upload UI actually rejects on, BEFORE anything is deployed or zipped.
# Added 2026-08-26 after a live upload rejected code-block-routing and lane-spawn
# with "field 'description' in SKILL.md must be at most 1024 characters" and
# "SKILL.md description cannot contain XML tags". Local plugin validation and
# blob verification both passed, so neither caught it; a package is not
# upload-ready until it satisfies the uploader's own frontmatter rules.
upload_preflight() {
  python3 - "$1" <<'PY'
import os, re, sys, unicodedata
try:
    import yaml
except ImportError:
    sys.exit("FATAL: upload_preflight needs PyYAML (pip3 install pyyaml)")

# Constraint set is the UNION of the two official validators, because they
# disagree and the upload path can enforce either:
#   skills-ref        github.com/agentskills/agentskills  (spec reference lib)
#   quick_validate.py github.com/anthropics/skills        (run by package_skill.py)
# Verified live 2026-08-26 against agentskills.io/specification,
# platform.claude.com/docs/en/api/skills-guide, and both validator sources.
# GROUND TRUTH outranks docs where they conflict: the 2026-08-26 upload
# rejection is authoritative, and Claude Code's own looser frontmatter rules
# are deliberately NOT the baseline (it makes every field optional and accepts
# ~20 extra keys, so validating against it would let a real rejection through).
SPEC_KEYS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
RESERVED_IN_NAME = ("anthropic", "claude")

path = sys.argv[1]
text = open(path).read()
if not text.startswith("---"):
    sys.exit(f"FATAL: {path} has no YAML frontmatter")
try:
    end = text.index("\n---", 3)
except ValueError:
    sys.exit(f"FATAL: {path} frontmatter is not terminated")
try:
    fm = yaml.safe_load(text[3:end])
except yaml.YAMLError as e:
    sys.exit(f"FATAL: {path} frontmatter is not valid YAML: {e}")
if not isinstance(fm, dict):
    sys.exit(f"FATAL: {path} frontmatter is not a mapping")

errs, warns = [], []

def angle_check(field, value):
    # The uploader's error is "cannot contain XML tags" and Anthropic does not
    # publish the matching rule. Independent reimplementations range from
    # </?[a-zA-Z][^>]*> to a blanket ban on any < or >. A confirmed live
    # rejection fired on a single angle-bracketed token buried mid-sentence
    # inside backticks, so formatting is no exemption. We enforce the strictest
    # reading (no angle bracket at all), which provably cannot be laxer than
    # the server, and which the whole shelf satisfies as of 2026-08-26.
    if re.search(r"[<>]", value):
        bits = sorted(set(re.findall(r"\S*[<>]\S*", value)))[:6]
        errs.append(
            f"{field} contains angle brackets, which the uploader rejects as XML tags: "
            + ", ".join(bits)
            + " -- write the placeholder in prose (for example TABLE NAME) instead")

name = fm.get("name")
if name is None or not str(name).strip():
    errs.append("frontmatter 'name' is missing or empty")
else:
    n = str(name).strip()
    angle_check("name", n)
    if len(n) > 64:
        errs.append(f"name is {len(n)} characters, the limit is 64")
    if not re.fullmatch(r"[a-z0-9-]+", n):
        errs.append(f"name {n!r} must match ^[a-z0-9-]+$ (lowercase ASCII letters, digits, hyphens)")
    if n.startswith("-") or n.endswith("-"):
        errs.append(f"name {n!r} must not start or end with a hyphen")
    if "--" in n:
        errs.append(f"name {n!r} must not contain consecutive hyphens")
    parent = os.path.basename(os.path.dirname(os.path.abspath(path)))
    if unicodedata.normalize("NFKC", n) != unicodedata.normalize("NFKC", parent):
        errs.append(f"name {n!r} must equal its parent directory name {parent!r}")
    for w in RESERVED_IN_NAME:
        if w in n.lower():
            warns.append(f"name contains the reserved word {w!r}; the Skills API documents "
                         f"this as disallowed and may reject it server-side")

desc = fm.get("description")
if desc is None or not str(desc).strip():
    errs.append("frontmatter 'description' is missing or empty")
else:
    d = str(desc).strip()
    if len(d) > 1024:
        errs.append(f"description is {len(d)} characters, the uploader's limit is 1024 "
                    f"(over by {len(d) - 1024})")
    angle_check("description", d)

compat = fm.get("compatibility")
if compat is not None and len(str(compat)) > 500:
    errs.append(f"compatibility is {len(str(compat))} characters, the limit is 500")

# The spec and both reference validators treat a key outside SPEC_KEYS as a hard
# error. The live claude.ai upload does NOT: on 2026-08-26 a skill carrying this
# estate's skill-map keys (tier, zone, status, subtitle, ...) uploaded
# successfully, and all 38 skills here carry them. Live behavior wins, so this
# is a warning that would tell us early if the upload path ever tightened.
extra = sorted(set(fm) - SPEC_KEYS)
if extra:
    warns.append("frontmatter keys outside the published spec set: " + ", ".join(extra)
                 + " (accepted by the live upload as of 2026-08-26; a hard error to the "
                   "spec's own reference validators)")

for w in warns:
    print(f"warn: {os.path.basename(os.path.dirname(path))}: {w}", file=sys.stderr)
if errs:
    print(f"FATAL: {path} is not claude.ai-upload-ready:", file=sys.stderr)
    for e in errs:
        print(f"  - {e}", file=sys.stderr)
    sys.exit(1)
PY
}

# zip_preflight <zip path> <expected skill name> -- assert the two structural
# rules the upload UI enforces (proven by live rejection 2026-08-07):
# exactly one top-level folder, exactly one SKILL.md.
zip_preflight() {
  python3 - "$1" "$2" <<'PY'
import sys, zipfile
zp, expected = sys.argv[1], sys.argv[2]
names = [n for n in zipfile.ZipFile(zp).namelist() if not n.startswith("__MACOSX")]
tops = {n.split("/")[0] for n in names if n.strip()}
skills = [n for n in names if n.endswith("SKILL.md")]
errs = []
if len(tops) != 1:
    errs.append(f"zip must contain exactly one top-level folder, found {len(tops)}: {sorted(tops)}")
elif tops != {expected}:
    errs.append(f"top-level folder is {sorted(tops)[0]!r}, expected {expected!r}")
if len(skills) != 1:
    errs.append(f"zip must contain exactly one SKILL.md, found {len(skills)}: {skills}")
if errs:
    print(f"FATAL: {zp} would be rejected by the claude.ai Skills upload:", file=sys.stderr)
    for e in errs:
        print(f"  - {e}", file=sys.stderr)
    sys.exit(1)
PY
}

if [ "$CHECK_ALL" -eq 1 ]; then
  # Repo-wide upload readiness sweep. Checks every canonical SKILL.md so a
  # violation surfaces in one call instead of one failed upload at a time.
  FAILED=0 CHECKED=0
  for f in "$REPO_ROOT"/skills/*/SKILL.md "$REPO_ROOT"/plugins/*/skills/*/SKILL.md; do
    [ -f "$f" ] || continue
    CHECKED=$((CHECKED + 1))
    if ! upload_preflight "$f"; then FAILED=$((FAILED + 1)); fi
  done
  if [ "$FAILED" -gt 0 ]; then
    echo "upload-preflight: $FAILED of $CHECKED skills are NOT claude.ai-upload-ready" >&2
    exit 1
  fi
  echo "upload-preflight: all $CHECKED skills pass (name and description rules: description 1-1024 chars, no angle brackets in name or description, name matches ^[a-z0-9-]+$ and its parent directory, compatibility <= 500)"
  exit 0
fi

if [ "$BUNDLE" -eq 1 ]; then
  [ -z "$DEPLOY_DIR" ] || { echo "FATAL: --bundle does not support --to (bundles are zip-only archival artifacts)" >&2; exit 1; }
  [ -n "$ZIP_PATH" ] || { echo "FATAL: --bundle requires --zip" >&2; exit 1; }
  SRC="$REPO_ROOT/plugins/$NAME"
  [ -f "$SRC/.claude-plugin/plugin.json" ] || { echo "FATAL: $SRC/.claude-plugin/plugin.json not found -- $NAME is not a plugin" >&2; exit 1; }
  VERSION=$(plugin_version "$NAME")
  # Bundles are never uploaded to claude.ai, but every skill they carry is a
  # future standalone package, so gate their frontmatter here too.
  for f in "$SRC"/skills/*/SKILL.md; do
    [ -f "$f" ] || continue
    upload_preflight "$f"
  done
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

# Gate every single-skill deploy and zip on the claude.ai upload constraints,
# against the CANONICAL source, before anything is written or packaged.
upload_preflight "$SRC/SKILL.md"

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
  # The zip is the thing Allison actually uploads, so assert its structure too.
  zip_preflight "$ZIP_PATH" "$SKILL_NAME"
  echo "zip: $ZIP_PATH ($VERSION) sha256=$(shasum -a 256 "$ZIP_PATH" | cut -d' ' -f1) upload-preflight=PASS"
fi
