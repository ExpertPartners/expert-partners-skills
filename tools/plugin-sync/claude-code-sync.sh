#!/usr/bin/env bash
# claude-code-sync.sh -- keep Claude Code on this Mac current with the canonical repo.
#
# Fired by the launch agent com.expertpartners.claude-code-plugin-sync at login and
# every five minutes while the Mac is awake (install.sh renders it for this user's
# home and checkout). Each run:
#   1. takes this surface's lock, so overlapping runs never stack up,
#   2. fast-forwards this checkout to origin/main and runs the updated script,
#      or stops with a failure, so stale code never reports success,
#   3. refreshes the expert-partners marketplace, updates enabled plugins that are
#      behind the repo, installs missing ones, and reads the versions back.
# Installed but disabled plugins are left alone, and so is every other marketplace.
# Receipts go to ~/Library/Application Support/plugin-sync/. They show what is
# installed on this Mac, not what a session has loaded, and nothing about cloud
# surfaces. Running sessions pick up changes after a restart or /reload-plugins.
#
#   claude-code-sync.sh            one run; quiet when the last delivery already matches
#   claude-code-sync.sh --locate   print the claude binary a run would use
# PLUGIN_SYNC_FORCE=1 re-checks even when the last delivery matches this commit.
# Commands: code.claude.com/docs/en/plugins/cli-reference (read 2026-11-04).

set -uo pipefail

SURFACE="claude-code"
HERE="$(cd "$(dirname "$0")" && pwd)"
SELF="$HERE/$(basename "$0")"
REPO="$(cd "$HERE/../.." && pwd)"
STATE_DIR="$HOME/Library/Application Support/plugin-sync"
LOG_DIR="$HOME/Library/Logs/plugin-sync"
CMD_TIMEOUT="${PLUGIN_SYNC_CMD_TIMEOUT:-600}"

version_gt() {
  local i x y
  local -a a b
  IFS=. read -r -a a <<<"${1//[^0-9.]/}"
  IFS=. read -r -a b <<<"${2//[^0-9.]/}"
  for ((i = 0; i < 4; i++)); do
    x="${a[i]:-0}" y="${b[i]:-0}"
    ((10#${x:-0} > 10#${y:-0})) && return 0
    ((10#${x:-0} < 10#${y:-0})) && return 1
  done
  return 1
}

newest_nvm() {
  local f v best="" best_v=""
  for f in "$HOME"/.nvm/versions/node/v*/bin/"$1"; do
    [[ -x "$f" ]] || continue
    v="${f#"$HOME/.nvm/versions/node/v"}"
    v="${v%%/*}"
    if [[ -z "$best" ]] || version_gt "$v" "$best_v"; then best="$f" best_v="$v"; fi
  done
  printf '%s' "$best"
}

find_claude() {
  if [[ -n "${CLAUDE_BIN:-}" ]]; then
    [[ -x "$CLAUDE_BIN" ]] && { printf '%s\n' "$CLAUDE_BIN"; return 0; }
    return 1
  fi
  # Tests point PLUGIN_SYNC_SYSTEM_ROOT at a fake root so discovery never reaches this
  # machine's own Homebrew or /usr/local.
  local c sys="${PLUGIN_SYNC_SYSTEM_ROOT:-}"
  for c in "$(command -v claude 2>/dev/null)" "$HOME/.local/bin/claude" "$HOME/.claude/local/claude" \
    "$sys/opt/homebrew/bin/claude" "$sys/usr/local/bin/claude" "$HOME/.volta/bin/claude" "$(newest_nvm claude)"; do
    [[ -n "$c" && -f "$c" && -x "$c" ]] && { printf '%s\n' "$c"; return 0; }
  done
  return 1
}

if [[ "${1:-}" == "--locate" ]]; then find_claude; exit $?; fi

mkdir -p "$STATE_DIR" "$LOG_DIR"
LOG="$LOG_DIR/$SURFACE-sync-$(date '+%Y-%m-%d').log"
log() { printf '%s %s\n' "$(date '+%H:%M:%S')" "$*" >>"$LOG"; }

PY="$(command -v python3 2>/dev/null || true)"
[[ -n "$PY" ]] || { log "FAILED: python3 not found"; exit 1; }

# macOS has no timeout(1). A pending alarm survives exec, so perl caps a hung git call.
limited() {
  if command -v perl >/dev/null 2>&1; then
    perl -e '$t = shift; alarm $t; exec @ARGV or exit 127' "$CMD_TIMEOUT" "$@"
  else
    "$@"
  fi
}

# Git never inherits the lock descriptors, so a detached git helper cannot hold a lock.
git_() { (exec 8>&- 9>&-; GIT_TERMINAL_PROMPT=0 limited git -C "$REPO" "$@"); }

# flock(2) locks belong to the open file, so the kernel drops one when its holder
# dies. A lock left by a dead run never blocks the next run, and no run deletes a
# live run's lock file.
take_lock() {
  "$PY" - "$1" "$2" <<'PY'
import fcntl, sys, time
fd, deadline = int(sys.argv[1]), time.time() + float(sys.argv[2])
while True:
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        sys.exit(0)
    except BlockingIOError:
        if time.time() >= deadline:
            sys.exit(1)
        time.sleep(0.5)
PY
}

write_source() {
  "$PY" - "$STATE_DIR/source.json" "$1" "$2" "$REPO" "$SURFACE" \
    "$(git_ rev-parse HEAD 2>/dev/null)" "$(git_ rev-parse --verify --quiet refs/remotes/origin/main 2>/dev/null)" <<'PY'
import json, os, sys, time
path, status, reason, repo, surface, head, published = sys.argv[1:8]
receipt = {
    "status": status,
    "reason": reason or None,
    "checkout": repo,
    "checkout_commit": head or None,
    "published_commit": published or None,
    "checked_by": surface,
    "checked_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
}
tmp = f"{path}.{os.getpid()}.tmp"
with open(tmp, "w") as f:
    json.dump(receipt, f, indent=2)
    f.write("\n")
os.replace(tmp, path)
PY
}

source_failed() { log "FAILED: source update: $1"; write_source failed "$1"; return 1; }

update_source() {
  local branch head published
  branch="$(git_ symbolic-ref --quiet --short HEAD)" || { source_failed "checkout is not on a branch"; return; }
  [[ "$branch" == main ]] || { source_failed "checkout is on $branch, not main"; return; }
  git_ fetch --quiet origin +refs/heads/main:refs/remotes/origin/main >>"$LOG" 2>&1 \
    || { source_failed "git fetch origin main failed"; return; }
  head="$(git_ rev-parse HEAD)" published="$(git_ rev-parse refs/remotes/origin/main)"
  if [[ "$head" != "$published" ]]; then
    git_ merge-base --is-ancestor HEAD refs/remotes/origin/main \
      || { source_failed "local main has commits that are not on origin/main"; return; }
    git_ merge --ff-only --quiet refs/remotes/origin/main >>"$LOG" 2>&1 \
      || { source_failed "fast-forward refused, local changes are in the way"; return; }
    head="$(git_ rev-parse HEAD)"
  fi
  [[ "$head" == "$published" ]] || { source_failed "checkout did not reach origin/main"; return; }
  SOURCE_SHA="$head"
  write_source ok ""
}

if [[ -n "${PLUGIN_SYNC_REEXEC:-}" ]] && { : >&9; } 2>/dev/null; then
  : # still holding the lock taken before the updated script was started
else
  exec 9>>"$STATE_DIR/$SURFACE.lock"
  take_lock 9 0 || { log "another $SURFACE run is active, leaving it to finish"; exit 0; }
fi

if [[ -z "${PLUGIN_SYNC_REEXEC:-}" ]]; then
  before="$(git_ rev-parse HEAD 2>/dev/null || true)"
  exec 8>>"$STATE_DIR/source.lock"
  take_lock 8 120 || { log "FAILED: source update: another run held the checkout for 2 minutes"; exit 1; }
  update_source
  source_rc=$?
  exec 8>&-
  [[ $source_rc -eq 0 ]] || exit 1
  if [[ "$SOURCE_SHA" != "$before" ]]; then
    log "checkout moved ${before:0:7} -> ${SOURCE_SHA:0:7}, running the updated script"
    PLUGIN_SYNC_REEXEC="$SOURCE_SHA" exec "$BASH" "$SELF" "$@"
  fi
else
  SOURCE_SHA="$(git_ rev-parse HEAD)"
  [[ "$SOURCE_SHA" == "$PLUGIN_SYNC_REEXEC" ]] || { log "FAILED: checkout moved during the run"; exit 1; }
fi

CLAUDE="$(find_claude || true)"
# An nvm install is a node script, so its own bin directory has to be on PATH.
if [[ -n "$CLAUDE" ]]; then
  PATH="$(dirname "$CLAUDE"):$PATH"
  export PATH
fi

exec "$PY" - "$CLAUDE" "$REPO" "$STATE_DIR" "$LOG" "$SOURCE_SHA" "$CMD_TIMEOUT" "${PLUGIN_SYNC_FORCE:-0}" "$HERE/legacy-skills.py" <<'PY'
import importlib.util, json, os, subprocess, sys, time

claude, repo, state_dir, log_path, head, timeout, force, legacy_helper = sys.argv[1:9]
MK = "expert-partners"
RECEIPT = os.path.join(state_dir, "claude-code-delivery.json")
RECHECK_SECONDS = 24 * 3600
NOTE = ("Installed on this Mac only. Runtime use is unverified until a new or reloaded "
        "session loads the skill. This receipt says nothing about cloud surfaces.")


def log(msg):
    with open(log_path, "a") as f:
        f.write(time.strftime("%H:%M:%S ") + msg + "\n")


def run(*args, quiet=False):
    """Return code of `claude args`, or None when it could not finish, and its stdout."""
    log("claude " + " ".join(args))
    try:
        r = subprocess.run([claude, *args], stdin=subprocess.DEVNULL, capture_output=True,
                           text=True, timeout=float(timeout))
    except (OSError, subprocess.TimeoutExpired) as e:
        log(f"FAILED: claude {' '.join(args)}: {e}")
        return None, ""
    with open(log_path, "a") as f:
        f.write(r.stderr if quiet else r.stdout + r.stderr)
    return r.returncode, r.stdout


def inventory():
    """{name: (version, enabled)} for plugins installed from our marketplace, or None."""
    rc, out = run("plugin", "list", "--json", "--available", quiet=True)
    if rc != 0:
        return None
    try:
        data = json.loads(out)
    except ValueError:
        return None
    rows = data.get("installed") if isinstance(data, dict) else data
    if not isinstance(rows, list):
        return None
    got = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        name, _, mk = str(row.get("id", "")).rpartition("@")
        if mk != MK or not name:
            continue
        version, enabled = got.get(name, (None, False))
        if version is None or row.get("scope") == "user":
            version = str(row.get("version", ""))
        got[name] = (version, enabled or row.get("enabled") is True)
    return got


def retire_legacy():
    """Turn off the old user-tier copies the operating-doctrine plugin replaced."""
    try:
        spec = importlib.util.spec_from_file_location("legacy_skills", legacy_helper)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.MIGRATIONS["claude-code"](repo, state_dir, head, log, claude, float(timeout))
    except Exception as e:  # a broken helper must fail the run visibly, never hide delivery
        log(f"FAILED: legacy skill migration: {e!r}")
        return {"status": "failed", "failures": [f"legacy skill migration crashed: {e!r}"]}


def finish(failures, have, legacy=None):
    plugins = {}
    for name, v in sorted(want.items()):
        version, enabled = (None, None) if have is None else have.get(name, (None, None))
        if have is None:
            state = "unknown"
        elif version is None:
            state = "missing"
        elif not enabled:
            state = "disabled, left alone"
        elif version == v:
            state = "current"
        else:
            state = "behind"
        if state in ("missing", "behind"):
            failures.append(f"{name} is {state}")
        plugins[name] = {"repo": v, "installed": version, "enabled": enabled, "state": state}
    ok = not failures
    receipt = {"surface": "claude-code", "marketplace": MK, "commit": head,
               "status": "ok" if ok else "failed", "failures": failures, "plugins": plugins,
               "checked_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "checked_epoch": int(time.time()),
               "note": NOTE}
    if legacy is not None:
        receipt["legacy_skills"] = legacy
    tmp = f"{RECEIPT}.{os.getpid()}.tmp"
    with open(tmp, "w") as f:
        json.dump(receipt, f, indent=2)
        f.write("\n")
    os.replace(tmp, RECEIPT)
    log(f"delivered {head[:7]}" if ok else f"FAILED: not delivered at {head[:7]}: " + "; ".join(failures))
    sys.exit(0 if ok and (legacy or {}).get("status") != "failed" else 1)


try:
    with open(RECEIPT) as f:
        prev = json.load(f)
except (OSError, ValueError):
    prev = {}
if (force != "1" and prev.get("status") == "ok" and prev.get("commit") == head
        and (prev.get("legacy_skills") or {}).get("status") not in ("failed", "waiting")
        and time.time() - prev.get("checked_epoch", 0) < RECHECK_SECONDS):
    sys.exit(0)

want = {}
try:
    with open(os.path.join(repo, ".claude-plugin", "marketplace.json")) as f:
        want = {p["name"]: str(p.get("version", "")) for p in json.load(f)["plugins"]}
except (OSError, ValueError, KeyError, TypeError) as e:
    finish([f"cannot read the repo marketplace.json: {e}"], None)
if not claude:
    finish(["claude binary not found"], None)
rc, _ = run("plugin", "marketplace", "update", MK)
if rc != 0:
    finish([f"claude plugin marketplace update {MK} failed"], None)
have = inventory()
if have is None:
    finish(["claude plugin list --json failed"], None)

failures = []
for name in sorted(want):
    version, enabled = have.get(name, (None, False))
    if version is None:
        verb = "install"
    elif not enabled:
        log(f"leave {name} alone, it is disabled")
        continue
    elif version != want[name]:
        verb = "update"
    else:
        continue
    rc, _ = run("plugin", verb, f"{name}@{MK}")
    if rc != 0:
        failures.append(f"claude plugin {verb} {name}@{MK} failed")

after = inventory()
if after is None:
    failures.append("claude plugin list --json readback failed")
finish(failures, after, retire_legacy())
PY
