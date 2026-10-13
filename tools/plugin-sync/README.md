# plugin-sync

Two small daily jobs that keep Codex current and flag any surface that falls behind this repo. Both run on the M4 through launchd, and both live here, not loose on the Mac.

| File | What it does |
|---|---|
| `codex-sync.sh` | 7:30 AM. Runs `codex plugin marketplace upgrade expert-partners`, then installs every plugin in the repo that Codex does not have yet. Names in `codex-skip.txt` are skipped. Silent on success. |
| `drift-check.py` | 8:00 AM. Compares the repo head with what Claude Code and Codex have loaded, with the claude.ai copies once the head is a day old, and with ChatGPT if `~/.claude/plugin-sync/chatgpt-last-sync.json` exists. Silent when all match. When something is behind it adds or updates ONE row in the Job Tracker, and closes that row when everything matches again. `--dry-run` prints without writing. |
| `*.plist` | The two launchd jobs. Each one runs `git pull --ff-only` in `~/Claude/projects/ExpertPartnersSkills` first, so a merge reaches the job on its own. |
| `install.sh` | Copies the plists to `~/Library/LaunchAgents` and reloads them. Safe to run again. |

ChatGPT has no documented way to read which version a workspace imported (checked 2026-10-13), so its check only runs if that status file exists. The ChatGPT marketplace import syncs daily on its own.

Logs are in `~/Library/Logs/plugin-sync/`. Tests: `python3 -m unittest discover -s tools/plugin-sync/tests`.
