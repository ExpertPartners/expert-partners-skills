#!/usr/bin/env bash
# install.sh -- put both plugin-sync jobs on this Mac's launchd, idempotently.
#
# Renders the two plist templates in this folder for this user's home and this
# checkout, backs up any different installed copy, lints the result, and reloads
# each job. Run it from the checkout the jobs should keep current; it refuses a
# checkout whose origin is not ExpertPartners/expert-partners-skills. Safe to run
# again. drift-check.py keeps its own plist and is not touched here.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
CHECKOUT="$(git -C "$HERE" rev-parse --show-toplevel)"
ORIGIN="$(git -C "$CHECKOUT" remote get-url origin 2>/dev/null || true)"
authorized='[/:]ExpertPartners/expert-partners-skills(\.git)?/?$'
if ! [[ "$ORIGIN" =~ $authorized ]]; then
  echo "install.sh: $CHECKOUT is not a checkout of ExpertPartners/expert-partners-skills (origin: ${ORIGIN:-none})" >&2
  exit 1
fi
for tool in python3 plutil launchctl; do
  command -v "$tool" >/dev/null 2>&1 || { echo "install.sh: $tool not found" >&2; exit 1; }
done

DEST="$HOME/Library/LaunchAgents"
mkdir -p "$DEST" "$HOME/Library/Logs/plugin-sync"
DOMAIN="gui/$(id -u)"

for label in com.expertpartners.codex-plugin-sync com.expertpartners.claude-code-plugin-sync; do
  src="$HERE/$label.plist" dst="$DEST/$label.plist"
  python3 - "$src" "$dst" "$HOME" "$CHECKOUT" <<'PY'
import os, plistlib, shutil, sys, time

src, dst, home, checkout = sys.argv[1:5]


def fill(v):
    if isinstance(v, str):
        return v.replace("@HOME@", home).replace("@CHECKOUT@", checkout)
    if isinstance(v, list):
        return [fill(x) for x in v]
    if isinstance(v, dict):
        return {k: fill(x) for k, x in v.items()}
    return v


with open(src, "rb") as f:
    rendered = plistlib.dumps(fill(plistlib.load(f)))
if os.path.exists(dst):
    with open(dst, "rb") as f:
        if f.read() == rendered:
            sys.exit(0)
    backup = f"{dst}.bak.{time.strftime('%Y%m%d-%H%M%S')}"
    n = 1
    while os.path.exists(backup):
        backup = f"{dst}.bak.{time.strftime('%Y%m%d-%H%M%S')}.{n}"
        n += 1
    shutil.copy2(dst, backup)
    print(f"backed up {dst} to {backup}")
tmp = f"{dst}.{os.getpid()}.tmp"
with open(tmp, "wb") as f:
    f.write(rendered)
os.replace(tmp, dst)
PY
  plutil -lint "$dst" >/dev/null
  launchctl bootout "$DOMAIN/$label" 2>/dev/null || true
  # bootout returns before the job is fully gone, so a quick bootstrap can be refused.
  loaded=""
  for _ in 1 2 3 4 5; do
    if launchctl bootstrap "$DOMAIN" "$dst" 2>/dev/null; then loaded=1; break; fi
    sleep 1
  done
  [[ -n "$loaded" ]] || { echo "install.sh: launchctl bootstrap $DOMAIN $dst failed" >&2; exit 1; }
  echo "loaded $label"
done

for surface in codex claude-code; do
  if bin="$(/bin/bash "$HERE/$surface-sync.sh" --locate)"; then
    echo "$surface binary: $bin"
  else
    echo "$surface binary: not found yet; the job reports a failure and retries every five minutes"
  fi
done
