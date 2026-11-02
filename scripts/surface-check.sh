#!/usr/bin/env bash
# surface-check.sh -- is one skill live on every surface the build standard names?
#
# Usage: scripts/surface-check.sh <skill-name>
#
# Prints one line per surface, VERIFIED, GAP or MANUAL with the reason. Exits 1 when any
# local surface is a GAP, 2 on a usage error, 0 otherwise. MANUAL lines never change the
# exit code. Read only, it changes nothing.
#
#   main         plugins/*/skills/<skill>/SKILL.md in this checkout, its frontmatter name
#                line, and its plugin's version in plugin.json and marketplace.json
#   Claude Code  a copy of the skill in the Claude Code plugin cache at main's version
#   Codex        the same in the Codex plugin cache, and the codex command on the PATH
#   claude.ai chat and Cowork  MANUAL, a browser check on Ember's M2
#
# Overrides, so tests can point at fixture folders:
#   SURFACE_CHECK_REPO          repo root (default: the checkout holding this script)
#   SURFACE_CHECK_CLAUDE_CACHE  default ~/.claude/plugins/cache
#   SURFACE_CHECK_CODEX_CACHE   default ~/.codex/plugins/cache
#
# Runs on the macOS system bash (3.2), so no mapfile or associative arrays.

set -uo pipefail

usage() { echo "usage: $0 <skill-name>" >&2; exit 2; }
[ $# -eq 1 ] || usage
SKILL="$1"
case "$SKILL" in
  "" | */* | .*) usage ;;
esac

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="${SURFACE_CHECK_REPO:-$(cd "$HERE/.." && pwd)}"
CLAUDE_CACHE="${SURFACE_CHECK_CLAUDE_CACHE:-$HOME/.claude/plugins/cache}"
CODEX_CACHE="${SURFACE_CHECK_CODEX_CACHE:-$HOME/.codex/plugins/cache}"
MANUAL_REASON="browser check on Ember's M2"

command -v python3 >/dev/null 2>&1 || { echo "surface-check: python3 is required to read plugin JSON" >&2; exit 2; }

GAPS=0
report() { # report <surface> <VERIFIED|GAP|MANUAL> <reason>
  printf '%s: %s %s\n' "$1" "$2" "$3"
  if [ "$2" = "GAP" ]; then GAPS=$((GAPS + 1)); fi
}

# json_get <file> <key> -- top-level string value, empty when missing or unreadable.
json_get() {
  python3 - "$1" "$2" <<'PY' 2>/dev/null
import json, sys
try:
    v = json.load(open(sys.argv[1])).get(sys.argv[2], "")
except Exception:
    v = ""
print(v if isinstance(v, str) else "")
PY
}

# marketplace_version <marketplace.json> <plugin> -- that plugin's version, empty when absent.
marketplace_version() {
  python3 - "$1" "$2" <<'PY' 2>/dev/null
import json, sys
try:
    plugins = json.load(open(sys.argv[1])).get("plugins", [])
except Exception:
    plugins = []
print(next((p.get("version", "") for p in plugins if p.get("name") == sys.argv[2]), ""))
PY
}

# frontmatter_name <SKILL.md> -- the name line inside the leading --- block, unquoted.
frontmatter_name() {
  awk -v q="'" 'NR == 1 && $0 != "---" { exit }
       NR > 1 && $0 == "---" { exit }
       NR > 1 && /^name:/ { sub(/^name:[ \t]*/, ""); sub(/[ \t]+$/, ""); gsub("^[\"" q "]|[\"" q "]$", ""); print; exit }' "$1"
}

# ---- main ----
MAIN_PLUGIN="" MAIN_VERSION=""
check_main() {
  local hits n skill_md plugin_dir name pj_version mk_version where
  hits="$(find "$REPO/plugins" -mindepth 4 -maxdepth 4 -path "*/skills/$SKILL/SKILL.md" -type f 2>/dev/null | LC_ALL=C sort)"
  n="$(printf '%s' "$hits" | grep -c . || true)"
  if [ "$n" -eq 0 ]; then
    report main GAP "no plugins/*/skills/$SKILL/SKILL.md in $REPO"; return
  fi
  if [ "$n" -gt 1 ]; then
    report main GAP "$SKILL is in more than one plugin: $(printf '%s' "$hits" | sed "s|^$REPO/||" | tr '\n' ' ')"; return
  fi
  skill_md="$hits"
  plugin_dir="$(dirname "$(dirname "$(dirname "$skill_md")")")"
  MAIN_PLUGIN="$(basename "$plugin_dir")"
  where="${skill_md#"$REPO"/}"

  name="$(frontmatter_name "$skill_md")"
  if [ "$name" != "$SKILL" ]; then
    report main GAP "$where name line is '${name:-missing}', expected '$SKILL'"; return
  fi
  pj_version="$(json_get "$plugin_dir/.claude-plugin/plugin.json" version)"
  mk_version="$(marketplace_version "$REPO/.claude-plugin/marketplace.json" "$MAIN_PLUGIN")"
  if [ -z "$pj_version" ]; then
    report main GAP "$MAIN_PLUGIN has no version in plugins/$MAIN_PLUGIN/.claude-plugin/plugin.json"; return
  fi
  if [ -z "$mk_version" ]; then
    report main GAP "$MAIN_PLUGIN has no version in .claude-plugin/marketplace.json"; return
  fi
  if [ "$pj_version" != "$mk_version" ]; then
    report main GAP "$MAIN_PLUGIN is $pj_version in plugin.json but $mk_version in marketplace.json"; return
  fi
  MAIN_VERSION="$pj_version"

  local ref note=""
  ref="$(git -C "$REPO" rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
  if [ -n "$ref" ] && [ "$ref" != "main" ]; then note=" (read from the $ref checkout, not main)"; fi
  report main VERIFIED "$where, name matches, $MAIN_PLUGIN $MAIN_VERSION in plugin.json and marketplace.json$note"
}

# ---- plugin caches (Claude Code and Codex share one layout: <marketplace>/<plugin>/<version>/) ----
# check_cache <surface> <cache root> -- sets CACHE_STATUS and CACHE_REASON, prints nothing.
CACHE_STATUS="" CACHE_REASON=""
check_cache() {
  local surface="$1" root="$2" skill_md plugin_root name version found="" match=""
  if [ -z "$MAIN_VERSION" ]; then
    CACHE_STATUS=GAP CACHE_REASON="cannot compare, main is a GAP"; return
  fi
  if [ ! -d "$root" ]; then
    CACHE_STATUS=GAP CACHE_REASON="no $surface plugin cache at $root"; return
  fi
  while IFS= read -r skill_md; do
    [ -n "$skill_md" ] || continue
    plugin_root="$(dirname "$(dirname "$(dirname "$skill_md")")")"
    name="" version=""
    for pj in "$plugin_root/.claude-plugin/plugin.json" "$plugin_root/.codex-plugin/plugin.json"; do
      if [ -f "$pj" ]; then
        name="$(json_get "$pj" name)"
        version="$(json_get "$pj" version)"
        break
      fi
    done
    [ -n "$name" ] || name="$(basename "$(dirname "$plugin_root")")"
    [ -n "$version" ] || version="$(basename "$plugin_root")"
    [ "$name" = "$MAIN_PLUGIN" ] || continue
    case " $found " in *" $version "*) ;; *) found="${found:+$found }$version" ;; esac
    if [ "$version" = "$MAIN_VERSION" ] && [ -z "$match" ]; then match="$plugin_root"; fi
  done <<EOF_FIND
$(find "$root" -path "*/skills/$SKILL/SKILL.md" -type f 2>/dev/null | LC_ALL=C sort)
EOF_FIND

  if [ -n "$match" ]; then
    CACHE_STATUS=VERIFIED CACHE_REASON="$MAIN_PLUGIN $MAIN_VERSION holds $SKILL at $match, matches main"
  elif [ -n "$found" ]; then
    CACHE_STATUS=GAP CACHE_REASON="cache has $MAIN_PLUGIN $found, main has $MAIN_VERSION"
  else
    CACHE_STATUS=GAP CACHE_REASON="no copy of $SKILL from $MAIN_PLUGIN in $root"
  fi
}

check_main

check_cache "Claude Code" "$CLAUDE_CACHE"
report "Claude Code" "$CACHE_STATUS" "$CACHE_REASON"

check_cache Codex "$CODEX_CACHE"
if command -v codex >/dev/null 2>&1; then
  report Codex "$CACHE_STATUS" "$CACHE_REASON, codex command at $(command -v codex)"
elif [ "$CACHE_STATUS" = VERIFIED ]; then
  report Codex GAP "$CACHE_REASON, but the codex command is not on the PATH"
else
  report Codex GAP "$CACHE_REASON, and the codex command is not on the PATH"
fi

report "claude.ai chat" MANUAL "$MANUAL_REASON"
report Cowork MANUAL "$MANUAL_REASON"

[ "$GAPS" -eq 0 ]
