# plugin-sync

Local jobs that keep Codex and Claude Code on each Mac carrying every plugin in this repo, plus a daily check that flags any surface that falls behind. They live here, not loose on a Mac. The GitHub repo stays the canonical source, and delivery uses only the native `codex plugin` and `claude plugin` commands. Cloud surfaces (claude.ai, Cowork, ChatGPT) sync on their own and never depend on either Mac.

| File | What it does |
|---|---|
| `codex-sync.sh` | Fast-forwards this checkout to `origin/main`, runs `codex plugin marketplace upgrade expert-partners`, reads only that marketplace with `codex plugin list --marketplace expert-partners --available --json`, adds every plugin that is missing or behind the repo, then reads the versions back. Names in `codex-skip.txt` are never added. |
| `claude-code-sync.sh` | Fast-forwards this checkout to `origin/main`, runs `claude plugin marketplace update expert-partners`, updates every enabled plugin that is behind, installs any that is missing, then reads the versions back with `claude plugin list --json`. |
| `drift-check.py` | 8:00 AM. Compares the repo head with what Claude Code and Codex have loaded, with the claude.ai copies once the head is a day old, and with ChatGPT if `~/.claude/plugin-sync/chatgpt-last-sync.json` exists. Silent when all match. When something is behind it adds or updates ONE row in the Job Tracker, and closes that row when everything matches again. `--dry-run` prints without writing. |
| `com.expertpartners.codex-plugin-sync.plist`, `com.expertpartners.claude-code-plugin-sync.plist` | Launch agent templates. Each runs its sync script at login and at every five-minute mark while the Mac is awake. `@HOME@` and `@CHECKOUT@` are filled in by `install.sh`. |
| `install.sh` | Renders the two templates for this user's home and the checkout it runs from, backs up any different installed copy as `<name>.plist.bak.<time>`, lints them, reloads both jobs, and prints which `codex` and `claude` binaries they will use. It refuses a checkout whose origin is not ExpertPartners/expert-partners-skills. Safe to run again. It does not touch the drift-check plist. |

## How a run behaves

- **When it runs.** At login, then at minutes 0, 5, 10 and so on. A slot missed while the Mac sleeps runs once on wake. A run that fails because the network is down is tried again at the next slot. Nothing wakes the Mac, and nothing depends on a chat staying open.
- **One run at a time.** Each surface holds its own lock, so a second run of the same job exits quietly while the first finishes. The lock is released by the system when its holder exits, so a crashed run never blocks the next one. The two jobs share a short wait for the checkout and otherwise run side by side.
- **Source first.** The checkout must be on `main`. The job fetches `origin/main` and fast-forwards only. If the fetch fails, the checkout is on another branch, local commits are not on GitHub, or a local edit is in the way, the run stops and reports a failure without running the CLIs. It never resets, stashes, or discards local work. After a fast-forward the updated script runs, not the old one.
- **Quiet when current.** When the last delivery matched the current commit, a run only fetches. A full check runs again after a new commit, after a failure, once a day, or with `PLUGIN_SYNC_FORCE=1`.
- **What it leaves alone.** Installed but disabled plugins, other marketplaces, and plugins that are no longer in this repo.
- **Binaries.** `CLAUDE_BIN` or `CODEX_BIN` win when set. Otherwise Codex is looked for in the ChatGPT app (`/Applications`, then `~/Applications`), then on `PATH`, in `~/.local/bin`, Homebrew, `/usr/local/bin`, Volta, and the newest nvm Node version. Claude Code is looked for on `PATH`, then in `~/.local/bin`, `~/.claude/local`, Homebrew, `/usr/local/bin`, Volta, and the newest nvm Node version. `<script> --locate` prints the one it picked.

## Receipts

Each run writes small JSON receipts to `~/Library/Application Support/plugin-sync/`:

- `source.json` is the source receipt: the checkout, its commit, the commit published on GitHub `main`, and whether the fast-forward worked.
- `codex-delivery.json` and `claude-code-delivery.json` are delivery receipts: the commit delivered, each plugin's repo version, installed version, enabled state, and result, and any failure.

A delivery receipt shows what is installed on this Mac. Runtime use stays unverified until a new or reloaded session actually loads the skill, and no local file proves delivery to a cloud surface.

## Install and test

Run `tools/plugin-sync/install.sh` from the checkout the jobs should keep current, on each Mac. ChatGPT has no documented way to read which version a workspace imported (checked 2026-10-13), so its drift check only runs if that status file exists. The ChatGPT marketplace import syncs daily on its own.

Logs are in `~/Library/Logs/plugin-sync/`. Tests: `python3 -m unittest discover -s tools/plugin-sync/tests`. `test_local_sync.py` runs both sync scripts and the installer against stub CLIs and local git remotes, so it needs no network and touches no real machine. Its tests name the stub CLIs through `CODEX_BIN` and `CLAUDE_BIN`, and point `PLUGIN_SYNC_SYSTEM_ROOT` at a fake root, so they never run the Mac's own `codex`, `claude` or `launchctl`.
