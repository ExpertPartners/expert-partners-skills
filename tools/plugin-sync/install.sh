#!/usr/bin/env bash
# install.sh -- put both plugin-sync jobs on this Mac's launchd, idempotently.
# Copies the plists from this folder to ~/Library/LaunchAgents (backing up any
# different existing file), lints them, and reloads each job.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
DEST="$HOME/Library/LaunchAgents"
mkdir -p "$DEST" "$HOME/Library/Logs/plugin-sync"
for src in "$HERE"/com.expertpartners.*.plist; do
  name="$(basename "$src")"; label="${name%.plist}"; dst="$DEST/$name"
  plutil -lint "$src" >/dev/null
  if [[ -f "$dst" ]] && ! cmp -s "$src" "$dst"; then cp "$dst" "$dst.bak.$(date '+%Y%m%d-%H%M%S')"; fi
  cp "$src" "$dst"
  launchctl bootout "gui/$(id -u)/$label" 2>/dev/null || true
  launchctl bootstrap "gui/$(id -u)" "$dst"
  echo "loaded $label"
done
