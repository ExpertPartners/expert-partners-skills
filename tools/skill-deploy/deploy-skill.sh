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

# upload_preflight <SKILL.md path> -- enforce the constraints the claude.ai
# Skills upload actually rejects on, BEFORE anything is deployed or zipped.
# Added 2026-08-26 after a live upload rejected code-block-routing and lane-spawn
# with "field 'description' in SKILL.md must be at most 1024 characters" and
# "SKILL.md description cannot contain XML tags". Local plugin validation and
# blob verification both passed, so neither caught it; a package is not
# upload-ready until it satisfies the uploader's own frontmatter rules.
#
# The rule set is the UNION of the two official validators, because they
# disagree and either may be what the upload path runs:
#   skills-ref        github.com/agentskills/agentskills  (spec reference lib)
#   quick_validate.py github.com/anthropics/skills        (run by package_skill.py)
# Verified live 2026-08-26 against agentskills.io/specification,
# platform.claude.com/docs/en/build-with-claude/skills-guide and
# code.claude.com/docs/en/skills. Where docs conflict, the live rejection wins.
upload_preflight() {
  python3 - "$1" <<'PY'
import os, re, sys, unicodedata
try:
    import yaml
except ImportError:
    sys.exit("FATAL: upload_preflight needs PyYAML (pip3 install pyyaml)")

SPEC_KEYS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
path = sys.argv[1]
raw = open(path, "rb").read()
errs, warns = [], []

# --- file-level encoding gates -------------------------------------------
# Anthropic's shipped validator matches ^---\n(.*?)\n--- against the raw file,
# so a BOM or CRLF breaks frontmatter parsing with "Invalid frontmatter format".
if raw.startswith(b"\xef\xbb\xbf"):
    errs.append("file begins with a UTF-8 BOM; the validator gates on the literal '---' at byte 0")
if b"\r\n" in raw:
    errs.append("file uses CRLF line endings; the validator's frontmatter regex requires LF")
if os.path.basename(path) != "SKILL.md":
    errs.append(f"skill file must be named exactly 'SKILL.md', found {os.path.basename(path)!r}")
try:
    text = raw.decode("utf-8")
except UnicodeDecodeError as e:
    print(f"FATAL: {path} is not valid UTF-8: {e}", file=sys.stderr)
    sys.exit(1)

m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
if not m:
    errs.append("no parsable YAML frontmatter block delimited by '---' lines at the very start")
    block = ""
else:
    block = m.group(1)

fm = None
if block:
    try:
        fm = yaml.safe_load(block)
    except yaml.YAMLError as e:
        errs.append(f"frontmatter is not valid YAML: {e}")
    if fm is not None and not isinstance(fm, dict):
        errs.append("frontmatter must be a YAML mapping")
        fm = None
    # PyYAML silently keeps the last of duplicated keys; server behavior is
    # unknown, so a duplicate is treated as an authoring error.
    seen, dupes = set(), set()
    for line in block.split("\n"):
        km = re.match(r"^([A-Za-z0-9_.-]+):", line)
        if km:
            k = km.group(1)
            (dupes.add if k in seen else seen.add)(k)
    if dupes:
        errs.append("duplicate top-level frontmatter keys: " + ", ".join(sorted(dupes)))

def angle_check(field, value):
    # The uploader's error is "cannot contain XML tags" and Anthropic does not
    # publish the matching rule. Its own quick_validate.py rejects ANY '<' or
    # '>' anywhere, which is stricter than its prose and stricter than every
    # third-party tag-shaped regex. We enforce that strictest reading, so this
    # check can never let a real rejection through. Checked against the PARSED
    # scalar: backticks and quoting grant no exemption.
    if re.search(r"[<>]", value):
        bits = sorted(set(re.findall(r"\S*[<>]\S*", value)))[:6]
        errs.append(f"{field} contains angle brackets, which the uploader rejects as XML tags: "
                    + ", ".join(bits)
                    + " -- write the placeholder in prose (for example TABLE NAME) instead")

if isinstance(fm, dict):
    name = fm.get("name")
    if name is None or (isinstance(name, str) and not name.strip()):
        errs.append("frontmatter 'name' is missing or empty")
    elif not isinstance(name, str):
        errs.append(f"'name' must be a string; YAML coerced it to {type(name).__name__} "
                    f"({name!r}) -- quote it")
    else:
        n = name.strip()
        angle_check("name", n)
        if not 1 <= len(n) <= 64:
            errs.append(f"name is {len(n)} characters, must be 1 to 64")
        if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", n):
            errs.append(f"name {n!r} must match ^[a-z0-9]+(-[a-z0-9]+)*$ (lowercase ASCII, "
                        f"digits, single internal hyphens)")
        parent = os.path.basename(os.path.dirname(os.path.abspath(path)))
        if unicodedata.normalize("NFKC", n) != unicodedata.normalize("NFKC", parent):
            errs.append(f"name {n!r} must equal its parent directory name {parent!r} "
                        f"(NFKC-normalized)")
        for w in ("anthropic", "claude"):
            if w in n.lower():
                warns.append(f"name contains the reserved word {w!r}; the Skills API documents "
                             f"this as disallowed. Substring semantics are unspecified and "
                             f"Claude Code itself ships a 'claude-api' skill, so this is a "
                             f"warning rather than a failure")

    desc = fm.get("description")
    if desc is None or (isinstance(desc, str) and not desc.strip()):
        errs.append("frontmatter 'description' is missing or empty")
    elif not isinstance(desc, str):
        errs.append(f"'description' must be a string; YAML coerced it to {type(desc).__name__} "
                    f"({desc!r}) -- quote it")
    else:
        d = desc.strip()
        # Count in codepoints AND UTF-16 units: a non-BMP character counts 1 in
        # Python and 2 in JavaScript, and the server's counting unit is unknown.
        u16 = len(d.encode("utf-16-le")) // 2
        if len(d) > 1024 or u16 > 1024:
            errs.append(f"description is {len(d)} codepoints / {u16} UTF-16 units, the "
                        f"uploader's limit is 1024 (over by {max(len(d), u16) - 1024})")
        elif len(d) > 200:
            warns.append(f"description is {len(d)} characters. The live uploader enforced 1024 "
                         f"on 2026-08-26, but claude.com/docs/skills/how-to still states a "
                         f"200-character claude.ai limit; the 201-1024 band is untested")
        angle_check("description", d)

    compat = fm.get("compatibility")
    if compat is not None:
        if not isinstance(compat, str):
            errs.append("'compatibility' must be a string")
        elif not 1 <= len(compat) <= 500:
            errs.append(f"compatibility is {len(compat)} characters, must be 1 to 500")

    md = fm.get("metadata")
    if md is not None:
        if not isinstance(md, dict):
            errs.append("'metadata' must be a mapping")
        else:
            bad = [f"{k}={md[k]!r}" for k in md
                   if not isinstance(k, str) or not isinstance(md[k], str)]
            if bad:
                errs.append("'metadata' must map strings to strings; quote these: "
                            + ", ".join(bad[:6]))

    at = fm.get("allowed-tools")
    if at is not None:
        # The spec wants a single space-separated string; Claude Code also
        # accepts a YAML list and comma-separated values. Canonical files may
        # use either, because the packager normalizes to the spec shape when it
        # stages the upload copy, so this is a warning rather than a failure.
        if not isinstance(at, str):
            warns.append(f"'allowed-tools' is a {type(at).__name__}; the spec wants a "
                         f"space-separated string (normalized in the upload zip)")
        elif "," in at:
            warns.append("'allowed-tools' is comma-separated; the spec wants space-separated "
                         "(normalized in the upload zip)")

    lic = fm.get("license")
    if lic is not None and not isinstance(lic, str):
        errs.append("'license' must be a string")

    # The spec and both reference validators treat a key outside SPEC_KEYS as a
    # hard error, and code.claude.com/docs/en/skills names claude.ai uploads
    # explicitly. Canonical sources here intentionally carry skill-map keys
    # because Claude Code accepts every field, so this is a warning at source;
    # the upload zip is rewritten to the six keys and zip_preflight PROVES it.
    extra = sorted(set(fm) - SPEC_KEYS)
    if extra:
        warns.append("frontmatter keys outside the spec's six: " + ", ".join(extra)
                     + " (fine for Claude Code; stripped from the upload zip, where any "
                       "extra key is a hard error)")

for w in warns:
    print(f"warn: {os.path.basename(os.path.dirname(os.path.abspath(path)))}: {w}", file=sys.stderr)
if errs:
    print(f"FATAL: {path} is not claude.ai-upload-ready:", file=sys.stderr)
    for e in errs:
        print(f"  - {e}", file=sys.stderr)
    sys.exit(1)
PY
}

# spec_clean_frontmatter <SKILL.md path> -- rewrite frontmatter to the six keys
# the claude.ai upload / Skills API path allows, dropping every Claude Code and
# estate-local extension. Used ONLY when building an upload zip. Canonical
# source and Claude Code deployed copies keep their skill-map keys, because
# Claude Code accepts every field; it is the upload path that does not.
# code.claude.com/docs/en/skills, "Using skill frontmatter outside Claude Code"
# (verified live 2026-08-26): "If you include any field the spec doesn't allow,
# packaging or upload fails with a hard error instead of ignoring the field".
spec_clean_frontmatter() {
  python3 - "$1" <<'PY'
import sys, yaml
SPEC = ["name", "description", "license", "compatibility", "metadata", "allowed-tools"]
path = sys.argv[1]
text = open(path).read()
end = text.index("\n---", 3)
fm = yaml.safe_load(text[3:end])
body = text[end:]
kept = {k: fm[k] for k in SPEC if k in fm}
dropped = sorted(set(fm) - set(SPEC))
notes = []
at = kept.get("allowed-tools")
if at is not None:
    if isinstance(at, (list, tuple)):
        joined = " ".join(str(x).strip() for x in at if str(x).strip())
        notes.append("normalized allowed-tools from a list to a space-separated string")
    elif isinstance(at, str):
        joined = " ".join(x.strip() for x in at.replace(",", " ").split() if x.strip())
        if joined != at:
            notes.append("normalized allowed-tools to a space-separated string")
    else:
        joined = str(at).strip()
    # An empty allowed-tools (a bare [] in the source, meaning "no restriction
    # declared") must be DROPPED, not emitted as an empty string: the key is
    # optional, and an empty value could read as "no tools permitted".
    if joined:
        kept["allowed-tools"] = joined
    else:
        del kept["allowed-tools"]
        notes.append("dropped an empty allowed-tools from the upload copy (optional key)")
rendered = yaml.dump(kept, sort_keys=False, default_flow_style=False,
                     width=10**6, allow_unicode=True).rstrip("\n")
open(path, "w").write("---\n" + rendered + body)
if dropped:
    print("  spec-clean: dropped non-spec frontmatter keys from the upload copy: "
          + ", ".join(dropped), file=sys.stderr)
for note in notes:
    print("  spec-clean: " + note, file=sys.stderr)
PY
}

# zip_preflight <zip path> <expected skill name> -- assert every structural rule
# the upload UI enforces, on the artifact Allison actually uploads. The
# one-top-level-folder rule is ground truth from a live rejection 2026-08-07.
zip_preflight() {
  python3 - "$1" "$2" <<'PY'
import os, posixpath, sys, unicodedata, zipfile
try:
    import yaml
except ImportError:
    sys.exit("FATAL: zip_preflight needs PyYAML")

SPEC = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
zp, expected = sys.argv[1], sys.argv[2]
errs, warns = [], []

try:
    zf = zipfile.ZipFile(zp)
except zipfile.BadZipFile as e:
    sys.exit(f"FATAL: {zp} is not a readable zip: {e}")

infos = zf.infolist()
names = [i.filename for i in infos]
if not names:
    errs.append("archive is empty")

# Path hygiene. A Finder- or ditto-built archive carries a sibling __MACOSX/
# directory, which is a SECOND top-level entry and trips the one-folder rule.
# This is the most likely real-world cause of the 2026-08-07 rejection on a
# Mac, so it is detected rather than filtered out.
junk = sorted({n for n in names
               if n.split("/")[0] == "__MACOSX" or posixpath.basename(n.rstrip("/")).startswith("._")
               or posixpath.basename(n.rstrip("/")) == ".DS_Store"})
if junk:
    errs.append("archive contains macOS metadata entries (build with python zipfile or "
                "'zip -r -X', never Finder Compress): " + ", ".join(junk[:6]))
for i in infos:
    n = i.filename
    if n.startswith("/") or ".." in n.split("/") or "\\" in n:
        errs.append(f"unsafe entry path: {n!r}")
    if (i.external_attr >> 16) & 0o170000 == 0o120000:
        errs.append(f"archive contains a symlink: {n!r}")

tops = sorted({n.split("/")[0] for n in names if n.strip()})
if len(tops) != 1:
    errs.append(f"archive must contain exactly one top-level folder and nothing else at its "
                f"root; found {len(tops)}: {tops[:6]}")
elif unicodedata.normalize("NFKC", tops[0]) != unicodedata.normalize("NFKC", expected):
    errs.append(f"top-level folder is {tops[0]!r}, expected {expected!r}")

root_skill = [n for n in names if n.count("/") == 1 and posixpath.basename(n) == "SKILL.md"]
deeper = [n for n in names if n.count("/") > 1 and posixpath.basename(n) == "SKILL.md"]
if len(root_skill) != 1:
    errs.append(f"archive must contain exactly one SKILL.md at the top folder's root; "
                f"found {len(root_skill)}: {root_skill[:4]}")
if deeper:
    warns.append("additional SKILL.md files nested deeper: " + ", ".join(deeper[:4]))

# Documented Skills API ceiling, borrowed: no claude.ai UI number is published.
total = sum(i.file_size for i in infos)
if total > 30 * 1024 * 1024:
    errs.append(f"uncompressed contents total {total/1048576:.1f} MB, over the documented "
                f"30 MB Skills API ceiling (no claude.ai UI figure is published)")

# Prove the packaged frontmatter is spec-clean on the artifact itself, rather
# than trusting the source it was built from.
if len(root_skill) == 1:
    t = zf.read(root_skill[0]).decode("utf-8", "replace")
    if t.startswith("---"):
        try:
            fm = yaml.safe_load(t[3:t.index("\n---", 3)])
            extra = sorted(set(fm) - SPEC)
            if extra:
                errs.append("packaged SKILL.md still carries non-spec frontmatter keys, which "
                            "the upload rejects as a hard error: " + ", ".join(extra))
            pat = fm.get("allowed-tools")
            if pat is not None and (not isinstance(pat, str) or "," in pat):
                errs.append(f"packaged 'allowed-tools' is not a space-separated string: {pat!r}")
            if unicodedata.normalize("NFKC", str(fm.get("name", ""))) != \
               unicodedata.normalize("NFKC", tops[0] if tops else ""):
                errs.append(f"packaged name {fm.get('name')!r} does not match the top-level "
                            f"folder {tops[0] if tops else None!r}")
        except Exception as e:
            errs.append(f"packaged SKILL.md frontmatter unreadable: {e}")

for w in warns:
    print(f"warn: {os.path.basename(zp)}: {w}", file=sys.stderr)
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
  # Exclusions mirror Anthropic's own package_skill.py, and keep macOS junk out
  # of the archive: a __MACOSX/ sibling is a second top-level entry and trips
  # the one-folder rule the uploader enforces.
  rsync -a \
    --exclude '.DS_Store' --exclude '._*' \
    --exclude '__pycache__/' --exclude '*.pyc' \
    --exclude 'node_modules/' --exclude '/evals/' \
    "$SRC/" "$STAGE/$SKILL_NAME/"
  # The upload path allows only the six spec keys and hard-errors on any other,
  # so the zip copy is stripped to them. Canonical source is untouched.
  spec_clean_frontmatter "$STAGE/$SKILL_NAME/SKILL.md"
  upload_preflight "$STAGE/$SKILL_NAME/SKILL.md"
  manifest "$STAGE/$SKILL_NAME"
  mkdir -p "$(dirname "$ZIP_PATH")"
  rm -f "$ZIP_PATH"
  ( cd "$STAGE" && zip -qrX "$ZIP_PATH" "$SKILL_NAME" )
  rm -rf "$STAGE"
  # The zip is the thing Allison actually uploads, so assert its structure too.
  zip_preflight "$ZIP_PATH" "$SKILL_NAME"
  echo "zip: $ZIP_PATH ($VERSION) sha256=$(shasum -a 256 "$ZIP_PATH" | cut -d' ' -f1) upload-preflight=PASS"
fi
