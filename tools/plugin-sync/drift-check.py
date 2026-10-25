#!/usr/bin/env python3
"""Daily drift check: is every surface on the same version of this repo?

Compares the repo head (GitHub, main) against what Claude Code, Codex, and
(claude.ai via the last terminal sync, ChatGPT once it reports) have loaded.
Silent when everything matches. When something is behind, adds or updates ONE
row in the Job Tracker. When it all matches again, closes that row quietly.

Surfaces:
  claude-code  the expert-partners marketplace clone and every plugin installed from it
  codex        the Codex marketplace snapshot and its installed plugins
  claude.ai    the synced plugin copies Claude Code downloads from claude.ai
               (what Cowork and chat carry); only judged once the repo head is
               over 24 hours old, so sync has had time to run
  chatgpt      no read API found (checked 2026-10-13), so it is judged only if
               ~/.claude/plugin-sync/chatgpt-last-sync.json exists with
               {"commit": "<sha>"}; nothing writes that file yet

Run: drift-check.py            (checks, writes the row if needed)
     drift-check.py --dry-run  (prints what it would do, writes nothing)
"""
import base64
import glob
import json
import os
import re
import subprocess
import sys
import time

REPO = "ExpertPartners/expert-partners-skills"
MARKETPLACE = "expert-partners"
HOME = os.path.expanduser("~")
CODEX = os.environ.get("CODEX_BIN", "/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex")
# The Sheet is found by its title at run time. This repo is public, so no Drive file ID lives here.
SHEET_TITLE = "Job Tracker"
TAB = "Untitled"
JOB = "Plugins are behind the skills repo"
KEY = os.path.join(HOME, ".openclaw/.secrets/service-account.json")
SUBJECT = "allison@expertpartners.com"
GRACE_SECONDS = 24 * 3600


def run(cmd, timeout=60):
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return r.returncode, r.stdout, r.stderr


def versions_from_marketplace(raw):
    d = json.loads(raw)
    return {p["name"]: p.get("version", "") for p in d.get("plugins", [])}


def repo_head():
    """(sha, committed_epoch, {plugin: version}) from GitHub."""
    rc, out, _ = run(["gh", "api", f"repos/{REPO}/commits/main", "--jq", '.sha + " " + .commit.committer.date'])
    if rc != 0:
        raise RuntimeError("cannot read the repo head from GitHub")
    sha, date = out.split()
    epoch = int(time.mktime(time.strptime(date, "%Y-%m-%dT%H:%M:%SZ"))) - time.timezone
    rc, out, _ = run(["gh", "api", "-H", "Accept: application/vnd.github.raw",
                      f"repos/{REPO}/contents/.claude-plugin/marketplace.json?ref={sha}"])
    if rc != 0:
        raise RuntimeError("cannot read marketplace.json at the repo head")
    return sha, epoch, versions_from_marketplace(out)


def git_head(path):
    rc, out, _ = run(["git", "-C", path, "rev-parse", "HEAD"])
    return out.strip() if rc == 0 else None


def claude_code_state():
    """(clone_sha, {plugin: installed_version}) for plugins installed from our marketplace."""
    clone = os.path.join(HOME, ".claude/plugins/marketplaces", MARKETPLACE)
    sha = git_head(clone)
    installed = {}
    f = os.path.join(HOME, ".claude/plugins/installed_plugins.json")
    if os.path.exists(f):
        d = json.load(open(f))
        for key, entries in d.get("plugins", {}).items():
            name, _, mk = key.partition("@")
            if mk == MARKETPLACE and entries:
                installed[name] = entries[0].get("version", "")
    return sha, installed


def parse_codex_list(text):
    """{plugin: version or None} for our marketplace block of `codex plugin list`."""
    out, inblock = {}, False
    for line in text.splitlines():
        if line.startswith("Marketplace `"):
            inblock = line.startswith(f"Marketplace `{MARKETPLACE}`")
            continue
        if inblock and "@" + MARKETPLACE in line:
            parts = line.split()
            name = parts[0].split("@")[0]
            if "not installed" in line:
                out[name] = None
            else:
                m = re.search(r"installed, (?:enabled|disabled)\s+(\S+)", line)
                out[name] = m.group(1) if m else ""
    return out


def codex_state():
    snap = os.path.join(HOME, ".codex/.tmp/marketplaces", MARKETPLACE)
    sha = git_head(snap)
    rc, out, _ = run([CODEX, "plugin", "list"], timeout=120)
    return sha, (parse_codex_list(out) if rc == 0 else None)


def claude_ai_state():
    """{plugin: synced_version} from the copies Claude Code syncs from claude.ai."""
    out = {}
    for d in glob.glob(os.path.join(HOME, ".claude/plugins/synced/*/")):
        for pj in glob.glob(os.path.join(d, "*/.claude-plugin/plugin.json")):
            try:
                j = json.load(open(pj))
                out[j["name"]] = j.get("version", "")
            except Exception:
                pass
    return out


def chatgpt_state():
    f = os.path.join(HOME, ".claude/plugin-sync/chatgpt-last-sync.json")
    if not os.path.exists(f):
        return None
    return json.load(open(f)).get("commit")


def short(sha):
    return (sha or "unknown")[:7]


def missing_in_claude_code(head_versions, installed):
    """Plugins in the repo that Claude Code has not installed from the marketplace."""
    return sorted(n for n in head_versions if n not in installed)


def find_behind(head_sha, head_epoch, head_versions, now=None):
    """Return a list of plain-words lines, empty when every surface matches."""
    now = now or time.time()
    behind = []

    cc_sha, cc_installed = claude_code_state()
    if cc_sha != head_sha:
        behind.append(f"Claude Code marketplace is at {short(cc_sha)}, repo is {short(head_sha)}")
    for name, v in sorted(cc_installed.items()):
        want = head_versions.get(name)
        if want and v != want:
            behind.append(f"Claude Code has {name} {v}, repo has {want}")
    for name in missing_in_claude_code(head_versions, cc_installed):
        behind.append(f"Claude Code does not have {name} {head_versions[name]}")

    cx_sha, cx_list = codex_state()
    if cx_sha != head_sha:
        behind.append(f"Codex marketplace is at {short(cx_sha)}, repo is {short(head_sha)}")
    if cx_list is None:
        behind.append("Codex plugin list could not be read")
    else:
        skip = set()
        sf = os.path.join(os.path.dirname(os.path.abspath(__file__)), "codex-skip.txt")
        if os.path.exists(sf):
            skip = {l.strip() for l in open(sf) if l.strip() and not l.startswith("#")}
        for name, want in sorted(head_versions.items()):
            if name in skip:
                continue
            have = cx_list.get(name)
            if have is None:
                behind.append(f"Codex does not have {name} {want}")
            elif have != want:
                behind.append(f"Codex has {name} {have}, repo has {want}")

    if now - head_epoch > GRACE_SECONDS:
        synced = claude_ai_state()
        for name, want in sorted(head_versions.items()):
            have = synced.get(name)
            if have is not None and have != want:
                behind.append(f"claude.ai (Cowork and chat) copy of {name} is {have}, repo has {want}")
            elif have is None and name in cc_installed:
                behind.append(f"claude.ai (Cowork and chat) has no copy of {name}, repo has {want}")

    gpt = chatgpt_state()
    if gpt is not None and gpt != head_sha and now - head_epoch > GRACE_SECONDS:
        behind.append(f"ChatGPT last synced {short(gpt)}, repo is {short(head_sha)}")
    return behind


def find_sheet_id(drive, title):
    """Find the one Sheet whose name is title behind its bracketed tag and version, such as
    [HQ][V1.0] Job Tracker. Zero or several matches stop the check, it never guesses."""
    q = f"name contains '{title}' and mimeType='application/vnd.google-apps.spreadsheet' and trashed=false"
    found = drive.files().list(q=q, fields="files(id,name)", pageSize=50, supportsAllDrives=True,
                               includeItemsFromAllDrives=True).execute().get("files", [])
    hits = [f for f in found if re.fullmatch(r"(\[[^\]]+\])+ " + re.escape(title), f["name"])]
    if len(hits) != 1:
        raise RuntimeError(f"expected one Sheet titled {title}, found {len(hits)}")
    return hits[0]["id"]


def sheets():
    """Returns the Sheets values API and the id of the Sheet found by title."""
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    creds = service_account.Credentials.from_service_account_file(
        KEY, scopes=["https://www.googleapis.com/auth/spreadsheets",
                     "https://www.googleapis.com/auth/drive.readonly"], subject=SUBJECT)
    drive = build("drive", "v3", credentials=creds, cache_discovery=False)
    values = build("sheets", "v4", credentials=creds, cache_discovery=False).spreadsheets().values()
    return values, find_sheet_id(drive, SHEET_TITLE)


def plan_row(rows, behind, head_sha, today):
    """Pure: decide the sheet write. Returns (action, row_number_or_None, values_or_None)."""
    idx = next((i for i, r in enumerate(rows) if r and r[0] == JOB), None)
    is_open = idx is not None and (len(rows[idx]) < 4 or rows[idx][3] != "Done")
    if behind:
        waiting = f"RETURN WHEN: the daily check finds every surface at {short(head_sha)} or newer"
        nxt = "; ".join(behind)[:900]
        if idx is None:
            return ("append", None, [JOB, "HQ / Chief HR Officer", "launchd drift check", "Not started",
                                      waiting, nxt, today, today])
        row = rows[idx] + [""] * (8 - len(rows[idx]))
        return ("update", idx + 1, [row[0], row[1], row[2], "Not started", waiting, nxt, row[6], today])
    if is_open:
        row = rows[idx] + [""] * (8 - len(rows[idx]))
        return ("update", idx + 1, [row[0], row[1], row[2], "Done", "None",
                                    f"Every surface matched {short(head_sha)} on {today}", row[6], today])
    return ("none", None, None)


def main(argv):
    dry = "--dry-run" in argv
    today = time.strftime("%Y-%m-%d")
    head_sha, head_epoch, head_versions = repo_head()
    behind = find_behind(head_sha, head_epoch, head_versions)
    if dry:
        print("repo head:", short(head_sha), "plugins:", head_versions)
        print("behind:", behind or "nothing")
    vals, sheet_id = sheets()
    got = vals.get(spreadsheetId=sheet_id, range=f"{TAB}!A:H").execute().get("values", [])
    action, rownum, values = plan_row(got, behind, head_sha, today)
    if dry:
        print("sheet action:", action, rownum, values)
        return 0
    if action == "append":
        vals.append(spreadsheetId=sheet_id, range=f"{TAB}!A1", valueInputOption="USER_ENTERED",
                    body={"values": [values]}).execute()
    elif action == "update":
        vals.update(spreadsheetId=sheet_id, range=f"{TAB}!A{rownum}:H{rownum}", valueInputOption="USER_ENTERED",
                    body={"values": [values]}).execute()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except Exception as e:  # a broken check must be visible, so it is not swallowed
        print(f"drift-check failed: {e}", file=sys.stderr)
        sys.exit(1)
