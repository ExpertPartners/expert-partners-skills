#!/usr/bin/env bash
# skill-deploy: the sole producer of deployed skill copies and upload zips,
# standalone or plugin-carried, single-skill or full-plugin bundle, and of
# whole-mount mirrors (the Codex .agents/skills surface).
# ADR 0056 point 8 (deployed-copy drift control): every deployed copy carries
# a DEPLOYED COPY header naming the canonical home, a version stamp, and a
# SHA-256 checksum manifest committed alongside. Hand-editing a deployed copy
# is a violation; fixes flow through canonical source and this script.
#
# Usage:
#   deploy-skill.sh <skill-name> [--to <deploy-dir>] [--zip <zip-path>]
#   deploy-skill.sh <skill-name> --from <canonical-dir> --to <deploy-dir>
#   deploy-skill.sh <skill-name> [--from <canonical-dir>] --to <deploy-dir> --verify
#   deploy-skill.sh <plugin-name> --bundle --zip <zip-path>
#   deploy-skill.sh --mirror-mount <canonical-mount-dir> --to <deploy-dir> [--verify] [--repair-drift]
#   deploy-skill.sh --verify-copies <mount-dir>
#   deploy-skill.sh --check-all
#   deploy-skill.sh --audit-surfaces [--aura <aura-checkout>] [--json <out>] [--only a,b] [--quiet] [--report-only]
#   deploy-skill.sh --receipt <release-receipt.json> [--aura <aura-checkout>]
#   deploy-skill.sh --receipt-template <skill-name> [--aura <aura-checkout>]
#
#   --audit-surfaces  read-only lifecycle audit (tools/skill-deploy/skill-lifecycle.py):
#                  classify every local copy of every canonical skill on this
#                  machine, on every surface that can load one (Claude Code
#                  user and project mounts, plugin cache and claude.ai sync
#                  mirrors; Codex user and repo mounts, plugin caches and the
#                  unsourced .agents/skills/synced mirror; Cowork's account
#                  skills and org plugin stores), against canonical, and exit
#                  non-zero on STALE, HAND-EDITED, UNTRACKED, ORPHAN,
#                  RETIRED-LOADING, REWRITTEN or DUPLICATE-IDENTITY findings.
#                  --verify gates aura's repo mounts in CI; this gates the rest.
#   --receipt      validate a skill release receipt (schema
#                  skill-release-receipt/v1) against live canonical and a live
#                  audit, print the lifecycle state every surface reached
#                  (CANONICAL, PACKAGED, INSTALLED, DISCOVERED, BEHAVIOR TESTED,
#                  COMPLETE) and exit zero only when every intended surface is
#                  COMPLETE and every unintended copy carries a disposition.
#                  That exit is what "release complete" means for a skill.
#   --receipt-template
#                  print a receipt skeleton with every surface key present, so
#                  each surface (Claude Chat, Cowork, Claude Code, Codex,
#                  ChatGPT/NORTH are five surfaces, never one shelf) is decided.
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
#   --from         canonical source directory for a skill whose canonical home
#                  is NOT this repo (the aura-native project skills under aura
#                  .claude/skills, for example). The DEPLOYED COPY header names
#                  that home by its git remote repo name and repo-relative path.
#                  A skill that has a canonical home in this repo refuses --from
#                  (one canonical source, never two), and a source that already
#                  carries a DEPLOYED COPY header is refused: a deployed copy is
#                  never a source (no mirror of a mirror). Not valid with --zip.
#   --mirror-mount deploy EVERY skill directory under <canonical-mount-dir>
#                  into --to, one deployed copy per skill. Source resolution per
#                  skill: a canonical home in this repo (skills/<name> or
#                  plugins/*/skills/<name>) wins; otherwise the mount directory
#                  itself is the canonical home (--from <mount>/<name>). This is
#                  how aura .claude/skills (the Claude Code project mount)
#                  produces aura .agents/skills (the Codex repo-scope mount,
#                  learn.chatgpt.com/docs/build-skills, verified 2026-09-04).
#                  A skill directory present in --to but absent from the mount
#                  is an ORPHAN and fails the run; removing it is a deliberate
#                  git rm by a person, never an automatic delete.
#   --verify       write nothing. Regenerate each deployed copy into a scratch
#                  dir and compare it to what is deployed (the deploy DATE in
#                  the header is the only tolerated difference), and check the
#                  committed manifest against the deployed bytes, file for file.
#                  Any drift, missing copy, missing or lying manifest, or orphan
#                  exits non-zero naming it, with the diff. This is the CI
#                  drift gate of ADR 0056 points 3 and 8.
#   --repair-drift a deployed copy whose manifest fails, or that has no
#                  manifest at all, is hand-edit drift and the deploy REFUSES to
#                  overwrite it silently. Pass this flag to acknowledge the
#                  drift (it is printed) and replace the copy with pipeline
#                  output. Valid only with --to, never with --verify.
#   --verify-copies <mount-dir>
#                  write nothing. In a mount that MIXES canonical skills and
#                  deployed copies (aura .claude/skills: seven aura-native
#                  canonicals beside three copies of this repo's skills), verify
#                  every skill directory that carries a DEPLOYED COPY header
#                  against the canonical home in this repo, exactly as --verify
#                  does, and leave the header-less canonicals alone. Exits
#                  non-zero on drift, a lying manifest, or a header naming a
#                  canonical this repo does not hold.
#
# Idempotency: a redeploy that would change nothing but the header date leaves
# the deployed copy byte-for-byte untouched (the original deploy date stands),
# so a rerun is a no-op and a diff in a deployed tree always means canonical
# content moved. SKILL_DEPLOY_TODAY=YYYY-MM-DD overrides the header date (tests).
#
# Flags compose except --bundle excludes --to, --from, --mirror-mount, and
# --verify; --mirror-mount excludes a positional name, --zip, and --from. The
# script never commits; the caller reviews and commits so the diff stays visible.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

# Lifecycle modes are read-only and live in skill-lifecycle.py beside this
# script; the producer stays the one entry point. Arguments after the mode
# flag pass through untouched (--aura, --json, --home, --only, ...).
case "${1:-}" in
  --audit-surfaces)   shift; exec python3 "$REPO_ROOT/tools/skill-deploy/skill-lifecycle.py" audit --eps "$REPO_ROOT" "$@" ;;
  --receipt)          shift; [ -n "${1:-}" ] || { echo "FATAL: --receipt needs a receipt file" >&2; exit 1; }
                      exec python3 "$REPO_ROOT/tools/skill-deploy/skill-lifecycle.py" receipt-check --eps "$REPO_ROOT" "$@" ;;
  --receipt-template) shift; [ -n "${1:-}" ] || { echo "FATAL: --receipt-template needs a skill name" >&2; exit 1; }
                      exec python3 "$REPO_ROOT/tools/skill-deploy/skill-lifecycle.py" receipt-template --eps "$REPO_ROOT" "$@" ;;
esac

NAME="" CHECK_ALL=0 DEPLOY_DIR="" ZIP_PATH="" BUNDLE=0
FROM_DIR="" MIRROR_MOUNT="" VERIFY=0 REPAIR_DRIFT=0 VERIFY_COPIES=""
USAGE="usage: deploy-skill.sh <skill-name|plugin-name> [--from dir] [--to dir] [--zip path] [--bundle] [--verify] | deploy-skill.sh --mirror-mount <dir> --to <dir> [--verify] [--repair-drift] | deploy-skill.sh --verify-copies <dir> | deploy-skill.sh --check-all | deploy-skill.sh --audit-surfaces [...] | deploy-skill.sh --receipt <file> | deploy-skill.sh --receipt-template <skill>"
while [ $# -gt 0 ]; do
  case "$1" in
    --to)            DEPLOY_DIR="${2:?--to needs a directory}"; shift 2 ;;
    --zip)           ZIP_PATH="${2:?--zip needs a path}";  shift 2 ;;
    --from)          FROM_DIR="${2:?--from needs a directory}"; shift 2 ;;
    --mirror-mount)  MIRROR_MOUNT="${2:?--mirror-mount needs a directory}"; shift 2 ;;
    --verify-copies) VERIFY_COPIES="${2:?--verify-copies needs a directory}"; shift 2 ;;
    --bundle)        BUNDLE=1; shift ;;
    --check-all)     CHECK_ALL=1; shift ;;
    --verify)        VERIFY=1; shift ;;
    --repair-drift)  REPAIR_DRIFT=1; shift ;;
    --*)             echo "FATAL: unknown arg $1" >&2; echo "$USAGE" >&2; exit 1 ;;
    *) if [ -z "$NAME" ]; then NAME="$1"; shift; else echo "FATAL: unexpected positional argument $1" >&2; echo "$USAGE" >&2; exit 1; fi ;;
  esac
done

if [ "$CHECK_ALL" -eq 0 ] && [ -z "$MIRROR_MOUNT" ] && [ -z "$VERIFY_COPIES" ] && [ -z "$NAME" ]; then
  echo "FATAL: $USAGE" >&2; exit 1
fi
if [ -n "$VERIFY_COPIES" ]; then
  if [ -n "$NAME" ] || [ -n "$DEPLOY_DIR" ] || [ -n "$ZIP_PATH" ] || [ -n "$FROM_DIR" ] || [ -n "$MIRROR_MOUNT" ] || [ "$BUNDLE" -eq 1 ] || [ "$REPAIR_DRIFT" -eq 1 ]; then
    echo "FATAL: --verify-copies <dir> stands alone (it is read-only and names its own mount)" >&2; exit 1
  fi
  VERIFY=1
fi
if [ -n "$MIRROR_MOUNT" ]; then
  [ -z "$NAME" ]     || { echo "FATAL: --mirror-mount takes no positional skill name (it deploys every skill in the mount)" >&2; exit 1; }
  [ -z "$ZIP_PATH" ] || { echo "FATAL: --mirror-mount does not build zips" >&2; exit 1; }
  [ -z "$FROM_DIR" ] || { echo "FATAL: --mirror-mount resolves sources itself; drop --from" >&2; exit 1; }
  [ "$BUNDLE" -eq 0 ] || { echo "FATAL: --mirror-mount excludes --bundle" >&2; exit 1; }
  [ -n "$DEPLOY_DIR" ] || { echo "FATAL: --mirror-mount requires --to <deploy-dir>" >&2; exit 1; }
fi
if [ "$VERIFY" -eq 1 ] && [ -z "$VERIFY_COPIES" ]; then
  [ -n "$DEPLOY_DIR" ] || { echo "FATAL: --verify checks a deployed copy, so it requires --to <deploy-dir>" >&2; exit 1; }
  [ -z "$ZIP_PATH" ] || { echo "FATAL: --verify writes nothing; drop --zip" >&2; exit 1; }
  [ "$BUNDLE" -eq 0 ] || { echo "FATAL: --verify excludes --bundle" >&2; exit 1; }
  [ "$REPAIR_DRIFT" -eq 0 ] || { echo "FATAL: --verify never writes; --repair-drift belongs to a deploy run" >&2; exit 1; }
fi
if [ -n "$FROM_DIR" ]; then
  [ "$BUNDLE" -eq 0 ] || { echo "FATAL: --from excludes --bundle" >&2; exit 1; }
  [ -z "$ZIP_PATH" ] || { echo "FATAL: --from sources are deployed copies, never claude.ai upload zips; drop --zip" >&2; exit 1; }
  [ -n "$DEPLOY_DIR" ] || { echo "FATAL: --from requires --to <deploy-dir>" >&2; exit 1; }
fi
if [ "$REPAIR_DRIFT" -eq 1 ] && [ -z "$DEPLOY_DIR" ]; then
  echo "FATAL: --repair-drift only applies to a deploy (--to)" >&2; exit 1
fi

TODAY="${SKILL_DEPLOY_TODAY:-$(date +%Y-%m-%d)}"
case "$TODAY" in
  [0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]) ;;
  *) echo "FATAL: SKILL_DEPLOY_TODAY must be YYYY-MM-DD, got $TODAY" >&2; exit 1 ;;
esac

plugin_version() { # plugin_version <plugin-name> -- reads plugins/<name>/.claude-plugin/plugin.json
  python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['version'])" \
    "$REPO_ROOT/plugins/$1/.claude-plugin/plugin.json"
}

manifest() { # write checksums.sha256 over a dir (excluding the manifest itself)
  # LC_ALL=C pins the sort: `sort` honors LC_COLLATE, so an en_US.UTF-8 caller
  # would otherwise order "./reference/x" before "./SKILL.md" and write a
  # manifest whose line order differs from the committed one for no content
  # reason (found 2026-09-04, aura issue #212 review).
  ( cd "$1" && find . -type f ! -name checksums.sha256 -print0 | LC_ALL=C sort -z \
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

# ---------------------------------------------------------------------------
# Deployed-copy machinery (added 2026-09-04, aura issue #212). One render path
# produces every deployed copy, whatever its canonical home, so a copy can
# always be regenerated and diffed. The DEPLOYED COPY header format below is a
# contract read by tools/skill-map/extract-skills-graph.mjs, which classifies a
# SKILL.md carrying it as a deployed copy of the named canonical home, never as
# a second canonical skill identity. Change the format in both places or not at all.
# ---------------------------------------------------------------------------

# frontmatter_of <SKILL.md> -- print the frontmatter lines only (nothing from the
# body), so a body that documents the header format is never mistaken for one.
frontmatter_of() {
  awk 'NR==1 { if ($0 != "---") exit 1; next } /^---[[:space:]]*$/ { exit } { print }' "$1"
}
has_deployed_header() { frontmatter_of "$1" | grep -q '^# DEPLOYED COPY ('; }
# header_names_canonical <SKILL.md> <label> -- the header names exactly this home
header_names_canonical() { frontmatter_of "$1" | grep -qF -- "# $2. Deployed at "; }

# canonical_label_external <dir> -> "<repo> <repo-relative-path>/SKILL.md"
# The repo name comes from the origin remote (aura, not the local folder name
# Aura), so the label is stable across clones and worktrees.
canonical_label_external() {
  local dir="$1" top url repo prefix
  top=$(git -C "$dir" rev-parse --show-toplevel 2>/dev/null) \
    || { echo "FATAL: --from $dir is not inside a git repository; a canonical home must be git-tracked" >&2; return 1; }
  url=$(git -C "$dir" remote get-url origin 2>/dev/null || true)
  if [ -n "$url" ]; then repo="$(basename "${url%.git}")"; else repo="$(basename "$top")"; fi
  repo="$(printf '%s' "$repo" | tr '[:upper:]' '[:lower:]')"
  prefix="$(git -C "$dir" rev-parse --show-prefix)"; prefix="${prefix%/}"
  [ -n "$prefix" ] || { echo "FATAL: --from $dir is a repository root, not a skill directory" >&2; return 1; }
  echo "$repo $prefix/SKILL.md"
}

# list_source_files <dir> -- NUL-separated, bytewise-sorted, <dir>-relative list of
# the files a deployed copy carries: what git tracks or would track (tracked plus
# untracked-but-not-ignored, i.e. what `git add -A` would take), minus the manifest
# and the junk set the --zip path already excludes (.DS_Store, ._*, __pycache__,
# *.pyc). A directory outside git (never a canonical home) falls back to a walk
# with the same exclusions. Bytewise order is locale-independent on purpose:
# stamps and manifests must not change with LC_COLLATE.
list_source_files() {
  python3 - "$1" <<'PY'
import os, subprocess, sys
root = sys.argv[1]
JUNK_NAMES = {"checksums.sha256", ".DS_Store"}
def junk(rel):
    parts = rel.split("/")
    base = parts[-1]
    return (base in JUNK_NAMES or base.startswith("._") or base.endswith(".pyc")
            or "__pycache__" in parts[:-1])
files = None
try:
    out = subprocess.run(["git", "-C", root, "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", "."],
                         capture_output=True, check=True).stdout
    files = [f.decode("utf-8", "surrogateescape") for f in out.split(b"\0") if f]
    # a path git still indexes but the working tree no longer has is not deployable
    files = [f for f in files if os.path.isfile(os.path.join(root, f))]
except (subprocess.CalledProcessError, FileNotFoundError):
    files = []
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in (".git",)]
        for f in fn:
            files.append(os.path.relpath(os.path.join(dp, f), root))
files = sorted({f for f in files if not junk(f)}, key=lambda s: s.encode("utf-8", "surrogateescape"))
sys.stdout.buffer.write(b"".join(f.encode("utf-8", "surrogateescape") + b"\0" for f in files))
PY
}

# tree_stamp <dir> -- deterministic 12-hex content stamp over a canonical skill
# directory's deployable files. The version stamp for a canonical skill that
# carries no vX.Y line: it changes exactly when canonical content changes.
# The hashed text is exactly what `shasum -a 256` prints for those files, in
# bytewise path order, with the "./<path>" names `find .` yields: so the stamp
# equals the one an LC_ALL=C `find | sort | xargs shasum | shasum` run produced,
# and every stamp committed before 2026-09-04 stays valid. Computed in python
# rather than a shell pipeline because BSD sed has no -z and a broken pipe here
# would silently hash the empty string instead of failing.
tree_stamp() {
  python3 - "$1" <<'PYSTAMP'
import hashlib, os, subprocess, sys
root = sys.argv[1]
JUNK_NAMES = {"checksums.sha256", ".DS_Store"}
def junk(rel):
    parts = rel.split("/"); base = parts[-1]
    return (base in JUNK_NAMES or base.startswith("._") or base.endswith(".pyc")
            or "__pycache__" in parts[:-1])
try:
    out = subprocess.run(["git", "-C", root, "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", "."],
                         capture_output=True, check=True).stdout
    files = [f.decode("utf-8", "surrogateescape") for f in out.split(b"\0") if f]
    files = [f for f in files if os.path.isfile(os.path.join(root, f))]
except (subprocess.CalledProcessError, FileNotFoundError):
    files = []
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d != ".git"]
        for f in fn:
            files.append(os.path.relpath(os.path.join(dp, f), root))
files = sorted({f for f in files if not junk(f)},
               key=lambda s: ("./" + s).encode("utf-8", "surrogateescape"))
if not files:
    sys.exit(f"FATAL: {root} carries no deployable files to stamp")
lines = b"".join(
    hashlib.sha256(open(os.path.join(root, rel), "rb").read()).hexdigest().encode()
    + b"  ./" + rel.encode("utf-8", "surrogateescape") + b"\n"
    for rel in files)
print(hashlib.sha256(lines).hexdigest()[:12])
PYSTAMP
}

eps_canonical_exists() { # eps_canonical_exists <name>
  [ -f "$REPO_ROOT/skills/$1/SKILL.md" ] && return 0
  local d
  for d in "$REPO_ROOT"/plugins/*/skills/"$1"; do [ -f "$d/SKILL.md" ] && return 0; done
  return 1
}

# resolve_source <name> <external-dir-or-empty>
# Sets SRC, SOURCE_KIND (standalone|plugin|external), PLUGIN_NAME, CANONICAL
# (the header label), VERSION (the header stamp).
resolve_source() {
  local name="$1" external="${2:-}"
  SRC="" SOURCE_KIND="" PLUGIN_NAME="" CANONICAL="" VERSION=""
  if [ -n "$external" ]; then
    if eps_canonical_exists "$name"; then
      echo "FATAL: $name has a canonical home in this repo; --from would make a second canonical source. Drop --from." >&2
      return 1
    fi
    [ -f "$external/SKILL.md" ] || { echo "FATAL: $external/SKILL.md not found" >&2; return 1; }
    [ "$(basename "$external")" = "$name" ] \
      || { echo "FATAL: --from directory $(basename "$external") does not match skill name $name" >&2; return 1; }
    if has_deployed_header "$external/SKILL.md"; then
      echo "FATAL: $external/SKILL.md is itself a DEPLOYED COPY; point --from at the canonical home it names, never at a mirror" >&2
      return 1
    fi
    SRC="$(cd "$external" && pwd)"
    SOURCE_KIND="external"
    CANONICAL="$(canonical_label_external "$SRC")" || return 1
    VERSION=$(grep -m1 -oE 'v[0-9]+\.[0-9]+' "$SRC/SKILL.md" || true)
    [ -n "$VERSION" ] || VERSION="tree sha256 $(tree_stamp "$SRC")"
    return 0
  fi
  if [ -f "$REPO_ROOT/skills/$name/SKILL.md" ]; then
    SRC="$REPO_ROOT/skills/$name"
    SOURCE_KIND="standalone"
    CANONICAL="expert-partners-skills skills/$name/SKILL.md"
    # Version stamp: the "-- vX.Y (date)" line in the canonical SKILL.md title.
    # A canonical skill that carries no such line (research-intake as of 2026-09-04)
    # gets the deterministic tree stamp instead, the same rule as an external
    # canonical: it changes exactly when canonical content changes, which is what
    # drift control needs. The note asks the author for a version line; it never
    # blocks the pipeline from being the sole producer of the copy.
    VERSION=$(grep -m1 -oE 'v[0-9]+\.[0-9]+' "$SRC/SKILL.md" || true)
    if [ -z "$VERSION" ]; then
      VERSION="tree sha256 $(tree_stamp "$SRC")"
      echo "note: $name carries no vX.Y version line in $SRC/SKILL.md; stamping the deployed copy with its content tree hash ($VERSION). Consider adding a version line to the canonical title." >&2
    fi
    return 0
  fi
  # Not homed under skills/ -- the only other legitimate canonical home is a
  # single plugins/*/skills/<name> directory (a plugin-only skill, no other
  # home to fall back to).
  local count=0 cand="" d
  for d in "$REPO_ROOT"/plugins/*/skills/"$name"; do
    if [ -f "$d/SKILL.md" ]; then count=$((count + 1)); cand="$d"; fi
  done
  if [ "$count" -eq 0 ]; then
    echo "FATAL: $name has no SKILL.md under skills/ or plugins/*/skills/ (pass --from <canonical-dir> for a skill whose canonical home is another repo)" >&2
    return 1
  elif [ "$count" -gt 1 ]; then
    echo "FATAL: $name exists under more than one plugin -- ambiguous, disambiguate manually" >&2
    return 1
  fi
  SRC="$cand"
  SOURCE_KIND="plugin"
  PLUGIN_NAME="$(basename "$(dirname "$(dirname "$SRC")")")"
  CANONICAL="expert-partners-skills plugins/$PLUGIN_NAME/skills/$name/SKILL.md"
  # Plugin-carried skill with no standalone home: its release cadence IS the
  # plugin's, so the plugin's own semver is the version stamp.
  VERSION=$(plugin_version "$PLUGIN_NAME")
  echo "note: $name has no skills/ home; sourcing from plugins/$PLUGIN_NAME/skills/$name, versioned to plugin $VERSION" >&2
}

# mount_preflight <SKILL.md> -- the portable Agent Skills frontmatter contract
# every deployed copy must satisfy regardless of surface (agentskills.io
# /specification and learn.chatgpt.com/docs/build-skills, verified 2026-09-04):
# parsable, non-empty frontmatter, name 1-64 lowercase-hyphen equal to the parent
# folder, description 1-1024 and non-empty. Codex tolerates extra keys and YAML
# comments (openai/codex codex-rs/skills/src/parser.rs, read 2026-09-04), so
# skill-map keys and the DEPLOYED COPY header pass through untouched.
mount_preflight() {
  python3 - "$1" <<'PY'
import os, re, sys, unicodedata
try:
    import yaml
except ImportError:
    sys.exit("FATAL: mount_preflight needs PyYAML (pip3 install pyyaml)")
path = sys.argv[1]
text = open(path, encoding="utf-8").read()
m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
errs = []
fm = None
if not m:
    errs.append("no YAML frontmatter block delimited by '---' at the very start")
else:
    try:
        fm = yaml.safe_load(m.group(1))
    except yaml.YAMLError as e:
        errs.append(f"frontmatter is not valid YAML: {e}")
    if fm is None and not errs:
        errs.append("frontmatter block is empty (or comments only); name and description are required")
if fm is not None and not isinstance(fm, dict):
    errs.append("frontmatter must be a YAML mapping"); fm = None
if isinstance(fm, dict):
    name = fm.get("name"); desc = fm.get("description")
    parent = os.path.basename(os.path.dirname(os.path.abspath(path)))
    if not isinstance(name, str) or not name.strip():
        errs.append("frontmatter 'name' is missing or empty")
    else:
        n = name.strip()
        if not 1 <= len(n) <= 64: errs.append(f"name is {len(n)} characters, must be 1 to 64")
        if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", n):
            errs.append(f"name {n!r} must be lowercase letters, digits, and single internal hyphens")
        if unicodedata.normalize("NFKC", n) != unicodedata.normalize("NFKC", parent):
            errs.append(f"name {n!r} must equal its parent directory name {parent!r}")
    if not isinstance(desc, str) or not desc.strip():
        errs.append("frontmatter 'description' is missing or empty")
    elif len(desc.strip()) > 1024:
        errs.append(f"description is {len(desc.strip())} characters, the spec limit is 1024")
if errs:
    print(f"FATAL: {path} does not satisfy the Agent Skills frontmatter contract:", file=sys.stderr)
    for e in errs: print(f"  - {e}", file=sys.stderr)
    sys.exit(1)
PY
}

# render <stage-dir> -- produce the deployed copy of the resolved source into an
# empty scratch dir: the canonical's deployable files (list_source_files), the
# DEPLOYED COPY header injected into the frontmatter after the canonical keys,
# and a fresh manifest. Every step fails loudly; a partial render is never
# reported as a copy.
render() {
  local stage="$1"
  python3 - "$SRC" "$stage" <<'PY' || return 1
import os, shutil, subprocess, sys
src, stage = sys.argv[1], sys.argv[2]
JUNK_NAMES = {"checksums.sha256", ".DS_Store"}
def junk(rel):
    parts = rel.split("/"); base = parts[-1]
    return (base in JUNK_NAMES or base.startswith("._") or base.endswith(".pyc")
            or "__pycache__" in parts[:-1])
try:
    out = subprocess.run(["git", "-C", src, "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", "."],
                         capture_output=True, check=True).stdout
    files = [f.decode("utf-8", "surrogateescape") for f in out.split(b"\0") if f]
    files = [f for f in files if os.path.isfile(os.path.join(src, f))]
except (subprocess.CalledProcessError, FileNotFoundError):
    files = []
    for dp, dn, fn in os.walk(src):
        dn[:] = [d for d in dn if d != ".git"]
        for f in fn:
            files.append(os.path.relpath(os.path.join(dp, f), src))
files = sorted({f for f in files if not junk(f)})
if "SKILL.md" not in files:
    sys.exit(f"FATAL: {src} has no deployable SKILL.md")
for rel in files:
    dst = os.path.join(stage, rel)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(os.path.join(src, rel), dst)
PY
  python3 - "$stage/SKILL.md" "$CANONICAL" "$VERSION" "$TODAY" <<'PY' || return 1
import sys
path, canonical, version, today = sys.argv[1:5]
text = open(path, encoding="utf-8").read()
header = (f"# DEPLOYED COPY ({today}, skill-deploy pipeline): the canonical home is\n"
          f"# {canonical}. Deployed at {version}.\n"
          f"# Edit the canonical copy first, then redeploy via tools/skill-deploy.\n")
lines = text.split("\n")
if not lines or lines[0].strip() != "---":
    sys.exit(f"FATAL: {path} does not start with a frontmatter block; cannot inject the DEPLOYED COPY header")
# insert before the closing '---' of the frontmatter block
try:
    end = next(i for i, l in enumerate(lines[1:], 1) if l.strip() == "---")
except StopIteration:
    sys.exit(f"FATAL: {path} frontmatter block never closes")
lines[end:end] = header.rstrip("\n").split("\n")
open(path, "w", encoding="utf-8").write("\n".join(lines))
PY
  manifest "$stage" || return 1
}

# compare_deployed <regenerated-dir> <deployed-dir> -- byte compare, manifest
# excluded, the header DATE in SKILL.md being the only tolerated difference.
# Prints every difference; exit 0 when identical.
compare_deployed() {
  python3 - "$1" "$2" <<'PY'
import difflib, os, re, sys
fresh, deployed = sys.argv[1], sys.argv[2]
DATE = re.compile(rb"^(# DEPLOYED COPY \()\d{4}-\d{2}-\d{2}(, skill-deploy pipeline\))", re.M)
def files(root):
    out = {}
    for dp, _, fn in os.walk(root):
        for f in fn:
            if f == "checksums.sha256": continue
            p = os.path.join(dp, f)
            out[os.path.relpath(p, root)] = open(p, "rb").read()
    return out
def norm(rel, data):
    return DATE.sub(rb"\1DATE\2", data) if rel == "SKILL.md" else data
A, B = files(fresh), files(deployed)
drift = []
for rel in sorted(set(A) | set(B)):
    if rel not in B:
        drift.append(f"missing in deployed copy: {rel}")
    elif rel not in A:
        drift.append(f"extra file in deployed copy, absent from canonical: {rel}")
    elif norm(rel, A[rel]) != norm(rel, B[rel]):
        drift.append(f"content differs from a fresh render of canonical: {rel}")
        try:
            a = norm(rel, A[rel]).decode("utf-8").splitlines()
            b = norm(rel, B[rel]).decode("utf-8").splitlines()
            for line in list(difflib.unified_diff(b, a, "deployed/" + rel, "canonical-render/" + rel, lineterm="", n=1))[:60]:
                drift.append("    " + line)
        except UnicodeDecodeError:
            drift.append("    (binary)")
if drift:
    print("\n".join(drift)); sys.exit(1)
PY
}

# manifest_check <deployed-dir> -- the committed checksums.sha256 must exist and
# describe exactly the deployed files: every listed file present with that hash,
# no file present that the manifest omits. Prints every violation; exit 0 clean.
manifest_check() {
  python3 - "$1" <<'PY'
import hashlib, os, sys
dest = sys.argv[1]
mf = os.path.join(dest, "checksums.sha256")
if not os.path.isfile(mf):
    print("no checksums.sha256 present (not pipeline-produced)"); sys.exit(1)
listed = {}
for line in open(mf, encoding="utf-8"):
    line = line.rstrip("\n")
    if not line.strip(): continue
    h, _, p = line.partition("  ")
    listed[os.path.normpath(p)] = h.strip()
actual = {}
for dp, _, fn in os.walk(dest):
    for f in fn:
        if f == "checksums.sha256": continue
        p = os.path.join(dp, f)
        actual[os.path.normpath(os.path.relpath(p, dest))] = hashlib.sha256(open(p, "rb").read()).hexdigest()
bad = []
for p in sorted(set(listed) | set(actual)):
    if p not in actual: bad.append(f"manifest lists a file that is not deployed: {p}")
    elif p not in listed: bad.append(f"deployed file not covered by the manifest: {p}")
    elif listed[p] != actual[p]: bad.append(f"manifest hash does not match the deployed bytes: {p} (manifest {listed[p][:12]}, actual {actual[p][:12]})")
if bad:
    print("\n".join(bad)); sys.exit(1)
PY
}

# deploy_one <name> -- deploy the resolved source to $DEPLOY_DIR/<name>.
# Unchanged (modulo header date) and manifest-clean: leave every byte alone.
# Manifest failing or absent: refuse unless --repair-drift acknowledged it.
# Any write failure is FATAL and never reported as a deploy.
deploy_one() {
  local name="$1" dest="$DEPLOY_DIR/$1" stage_root stage
  # The render lands under <scratch>/<name>/ so the copy's parent folder is its
  # skill name, exactly as it will sit in the mount; the frontmatter contract
  # (name equals parent directory) is then checked on the real shape.
  stage_root="$(mktemp -d)"; stage="$stage_root/$name"; mkdir -p "$stage"
  render "$stage" || { echo "FATAL: could not render $name from $SRC" >&2; rm -rf "$stage_root"; return 1; }
  mount_preflight "$stage/SKILL.md" || { rm -rf "$stage_root"; return 1; }
  if [ -e "$dest" ] && [ ! -d "$dest" ]; then
    echo "FATAL: $dest exists and is not a directory; refusing to deploy over it" >&2
    rm -rf "$stage_root"; return 1
  fi
  if [ -d "$dest" ]; then
    if compare_deployed "$stage" "$dest" >/dev/null && manifest_check "$dest" >/dev/null; then
      echo "unchanged: $dest already matches $CANONICAL ($VERSION); not rewritten"
      rm -rf "$stage_root"; return 0
    fi
    if ! manifest_check "$dest" >/dev/null; then
      if [ "$REPAIR_DRIFT" -eq 1 ]; then
        echo "repair-drift: $dest is not pipeline-clean; replacing it with pipeline output. What was there:" >&2
        manifest_check "$dest" 2>&1 | sed 's/^/    /' >&2 || true
        compare_deployed "$stage" "$dest" 2>&1 | sed 's/^/    /' >&2 || true
      else
        echo "FATAL: existing deployed copy at $dest fails its manifest (hand-edit drift, or no manifest at all). Inspect with --verify; pass --repair-drift to replace it with pipeline output." >&2
        rm -rf "$stage_root"; return 1
      fi
    fi
  fi
  if ! mkdir -p "$dest" || ! rsync -a --delete "$stage/" "$dest/"; then
    echo "FATAL: could not write the deployed copy to $dest" >&2
    rm -rf "$stage_root"; return 1
  fi
  rm -rf "$stage_root"
  if ! manifest_check "$dest" >/dev/null; then
    echo "FATAL: $dest was written but does not verify against its own manifest; the destination is not a faithful filesystem" >&2
    return 1
  fi
  echo "deployed: $dest ($VERSION), manifest: $dest/checksums.sha256"
}

# verify_one <name> -- no writes. OK when the deployed copy equals a fresh render
# (header date aside) and its manifest describes it exactly.
verify_one() {
  local name="$1" dest="$DEPLOY_DIR/$1" stage_root stage rc=0 out
  if [ ! -d "$dest" ]; then
    echo "DRIFT $name: no deployed copy at $dest (canonical $CANONICAL, $VERSION)"; return 1
  fi
  stage_root="$(mktemp -d)"; stage="$stage_root/$name"; mkdir -p "$stage"
  render "$stage" || { echo "DRIFT $name: could not render canonical $CANONICAL for comparison"; rm -rf "$stage_root"; return 1; }
  if ! out="$(compare_deployed "$stage" "$dest")"; then
    echo "DRIFT $name: deployed copy differs from a fresh render of $CANONICAL ($VERSION)"
    printf '%s\n' "$out" | sed 's/^/  /'; rc=1
  fi
  if ! out="$(manifest_check "$dest")"; then
    echo "DRIFT $name: checksums.sha256 does not describe the deployed bytes"
    printf '%s\n' "$out" | sed 's/^/  /'; rc=1
  fi
  [ "$rc" -eq 0 ] && echo "OK $name: deployed copy matches $CANONICAL ($VERSION); manifest verifies"
  rm -rf "$stage_root"
  return "$rc"
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

if [ -n "$VERIFY_COPIES" ]; then
  [ -d "$VERIFY_COPIES" ] || { echo "FATAL: --verify-copies $VERIFY_COPIES is not a directory" >&2; exit 1; }
  DEPLOY_DIR="$(cd "$VERIFY_COPIES" && pwd)"
  FAILS=0 COUNT=0 SKIPPED=0
  for d in "$DEPLOY_DIR"/*/; do
    [ -d "$d" ] && [ -f "$d/SKILL.md" ] || continue
    n="$(basename "$d")"
    if ! has_deployed_header "$d/SKILL.md"; then SKIPPED=$((SKIPPED + 1)); continue; fi   # a canonical skill living in this mount
    COUNT=$((COUNT + 1))
    if ! resolve_source "$n" "" 2>/dev/null; then
      echo "DRIFT $n: carries a DEPLOYED COPY header but this repo holds no canonical skill named $n"
      FAILS=$((FAILS + 1)); continue
    fi
    if ! header_names_canonical "$d/SKILL.md" "$CANONICAL"; then
      echo "DRIFT $n: DEPLOYED COPY header names a canonical home other than $CANONICAL"
      frontmatter_of "$d/SKILL.md" | grep '^# ' | sed 's/^/  /'
      FAILS=$((FAILS + 1)); continue
    fi
    verify_one "$n" || FAILS=$((FAILS + 1))
  done
  if [ "$FAILS" -gt 0 ]; then
    echo "verify-copies: $FAILS problem(s) across $COUNT deployed cop(ies) in $DEPLOY_DIR ($SKIPPED canonical skill(s) left alone)" >&2
    exit 1
  fi
  echo "verify-copies: all $COUNT deployed cop(ies) in $DEPLOY_DIR clean ($SKIPPED canonical skill(s) left alone)"
  exit 0
fi

if [ -n "$MIRROR_MOUNT" ]; then
  [ -d "$MIRROR_MOUNT" ] || { echo "FATAL: --mirror-mount $MIRROR_MOUNT is not a directory" >&2; exit 1; }
  MOUNT_ABS="$(cd "$MIRROR_MOUNT" && pwd)"
  if [ -d "$DEPLOY_DIR" ] && [ "$(cd "$DEPLOY_DIR" && pwd)" = "$MOUNT_ABS" ]; then
    echo "FATAL: --mirror-mount and --to name the same directory" >&2; exit 1
  fi
  MODE="deploy"; [ "$VERIFY" -eq 1 ] && MODE="verify"
  FAILS=0 COUNT=0 NAMES=""
  for d in "$MOUNT_ABS"/*/; do
    [ -d "$d" ] || continue
    n="$(basename "$d")"
    if [ ! -f "$d/SKILL.md" ]; then
      echo "FATAL: mount entry $MOUNT_ABS/$n has no SKILL.md; every directory in a skills mount is a skill" >&2
      FAILS=$((FAILS + 1)); continue
    fi
    COUNT=$((COUNT + 1)); NAMES="$NAMES $n "
    if eps_canonical_exists "$n"; then EXT=""; else EXT="$MOUNT_ABS/$n"; fi
    if ! resolve_source "$n" "$EXT"; then FAILS=$((FAILS + 1)); continue; fi
    if [ -z "$EXT" ]; then
      # The mount entry shares its name with a canonical skill of this repo, so it
      # must BE a deployed copy of that canonical. Anything else is a second
      # canonical wearing a taken name, and it would be silently shadowed here.
      if ! header_names_canonical "$d/SKILL.md" "$CANONICAL"; then
        echo "FATAL: mount entry $MOUNT_ABS/$n shares its name with the canonical skill at $CANONICAL but is not a pipeline-produced copy of it (no DEPLOYED COPY header naming that home). Two canonical homes for one skill id are never allowed: redeploy it from canonical (deploy-skill.sh $n --to $MOUNT_ABS --repair-drift) or give the mount skill its own name." >&2
        FAILS=$((FAILS + 1)); continue
      fi
      upload_preflight "$SRC/SKILL.md" || { FAILS=$((FAILS + 1)); continue; }
    fi
    if [ "$VERIFY" -eq 1 ]; then
      verify_one "$n" || FAILS=$((FAILS + 1))
    else
      deploy_one "$n" || FAILS=$((FAILS + 1))
    fi
  done
  [ "$COUNT" -gt 0 ] || { echo "FATAL: no skill directories found under $MOUNT_ABS" >&2; exit 1; }
  # Orphans: anything in the destination that the mount does not carry. Never
  # deleted here; a person removes it deliberately (git rm) or restores canonical.
  if [ -d "$DEPLOY_DIR" ]; then
    for d in "$DEPLOY_DIR"/*/; do
      [ -d "$d" ] || continue
      n="$(basename "$d")"
      case "$NAMES" in *" $n "*) ;; *)
        echo "ORPHAN $n: $DEPLOY_DIR/$n has no canonical skill in $MOUNT_ABS; remove it deliberately (git rm) or restore its canonical"
        FAILS=$((FAILS + 1)) ;;
      esac
    done
  fi
  if [ "$FAILS" -gt 0 ]; then
    echo "mirror-mount $MODE: $FAILS problem(s) across $COUNT skill(s) ($MOUNT_ABS -> $DEPLOY_DIR)" >&2
    exit 1
  fi
  echo "mirror-mount $MODE: all $COUNT skill(s) clean ($MOUNT_ABS -> $DEPLOY_DIR)"
  exit 0
fi

SKILL_NAME="$NAME"
resolve_source "$SKILL_NAME" "$FROM_DIR" || exit 1

# Gate every single-skill deploy and zip on the claude.ai upload constraints,
# against the CANONICAL source, before anything is written or packaged. An
# external canonical (another repo's project skill) is never a claude.ai upload
# candidate, so it is gated by the portable contract in deploy_one instead.
if [ "$SOURCE_KIND" != "external" ]; then upload_preflight "$SRC/SKILL.md"; fi

if [ "$VERIFY" -eq 1 ]; then
  verify_one "$SKILL_NAME"
  exit $?
fi

if [ -n "$DEPLOY_DIR" ]; then
  deploy_one "$SKILL_NAME" || exit 1
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
