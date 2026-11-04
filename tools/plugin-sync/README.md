# plugin-sync

Local jobs that keep Codex and Claude Code on each Mac carrying every plugin in this repo, plus a daily check that flags any surface that falls behind. They live here, not loose on a Mac. The GitHub repo stays the canonical source, and delivery uses only the native `codex plugin` and `claude plugin` commands. Cloud surfaces (claude.ai, Cowork, ChatGPT) sync on their own and never depend on either Mac.

| File | What it does |
|---|---|
| `codex-sync.sh` | Fast-forwards this checkout to `origin/main`, runs `codex plugin marketplace upgrade expert-partners`, reads only that marketplace with `codex plugin list --marketplace expert-partners --available --json`, adds every plugin that is missing or behind the repo, then reads the versions back. Names in `codex-skip.txt` are never added. |
| `claude-code-sync.sh` | Fast-forwards this checkout to `origin/main`, runs `claude plugin marketplace update expert-partners`, updates every enabled plugin that is behind, installs any that is missing, then reads the versions back with `claude plugin list --json`. |
| `drift-check.py` | 8:00 AM. Reports per-plugin source publication, installed delivery, enabled state and runtime use separately as JSON. Missing cloud evidence stays unknown or unverified; local Claude caches are supporting evidence only. Judges installed content against the plugin folder fingerprint, not a moving repository HEAD. Exits 0 verified, 3 unverified, 2 behind, 1 failed. Only maintains an existing open legacy tracker row; never appends or reopens one, and never marks Done unless structured verification is verified. `--dry-run` writes nothing; `--offline` uses the local checkout without GitHub, Google or writes. |
| `com.expertpartners.codex-plugin-sync.plist`, `com.expertpartners.claude-code-plugin-sync.plist` | Launch agent templates. Each runs its sync script at login and at every five-minute mark while the Mac is awake. `@HOME@` and `@CHECKOUT@` are filled in by `install.sh`. |
| `install.sh` | Renders the two templates for this user's home and the checkout it runs from, backs up any different installed copy as `<name>.plist.bak.<time>`, lints them, reloads both jobs, and prints which `codex` and `claude` binaries they will use. It refuses a checkout whose origin is not ExpertPartners/expert-partners-skills. Safe to run again. It does not touch the drift-check plist. |
| `legacy-skills.py` | Called by both sync scripts after each full delivery run. Turns off the four old user-tier copies (`intake`, `new-project`, `session-home`, `verify-docs`) once the operating-doctrine plugin that replaces them is proven installed, enabled and byte-equal to the repo on that surface. See "Old user-tier copies" below. |
| `chatgpt-import-check.py` | Checks every plugin against OpenAI's published import rules, and checks source coverage: a live `SKILL.md` (front matter with `name` and `description`) outside a marketplace plugin's `skills/` folder, or a plugin missing from `.claude-plugin/marketplace.json`, fails. Retired pointers without front matter, deployed copies and git history pass. `tools/validate-job.sh` runs it. |

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

## Old user-tier copies

`intake`, `new-project`, `session-home` and `verify-docs` were once deployed by hand into `~/.claude/skills` and `~/.agents/skills`. They now ship in the operating-doctrine plugin (`verify-docs` as part of `research-before-guessing`). Plugin delivery cannot reach those old folders, so `legacy-skills.py` turns each old copy off through the surface's own per-skill setting during the normal five-minute catch-up:

- **Only known copies.** A copy is recognized only when its `SKILL.md`, minus any skill-deploy DEPLOYED COPY header naming `skills/<name>/SKILL.md`, equals a version of that file in this checkout's first-parent history. Anything else is left alone and reported in the receipt.
- **Replacement first.** The old copy stays on until the operating-doctrine plugin is installed and enabled on that surface and its skill folder holds the bytes committed at HEAD. A missing, disabled, skipped or different replacement is reported as waiting and checked again on the next full run.
- **Claude Code.** Sets `skillOverrides.<name>` to `"off"` in the user `settings.json` (plugin skills are not affected by that setting). It keeps every other field and any choice already set for that name, refuses a symlinked or unreadable file, writes atomically, and starts over if Claude Code changed the file meanwhile.
- **Codex.** Uses `codex app-server` `skills/config/write` with the exact old `SKILL.md` path and `enabled: false`, then reads the skill list back. Nothing runs when operating-doctrine is in `codex-skip.txt`.
- **Backups and safety.** Before any write, the original settings file is copied to a private backup (folder mode 0700, file mode 0600) under `legacy-skill-backups/` and read back. No skill folder is moved, edited or deleted, and no plugin cache is written.
- **Failures.** Each run writes `claude-code-legacy-skills.json` or `codex-legacy-skills.json` with the state of every old name, and the delivery receipt carries the same summary as `legacy_skills`. A failure fails the run, so the next slot retries it; a repeated run with nothing to do changes nothing.

Runtime use stays unverified until a new or reloaded session lists the skills.

## Install and test

Run `tools/plugin-sync/install.sh` from the checkout the jobs should keep current, on each Mac. The ChatGPT marketplace import uses ChatGPT's own native daily sync, and claude.ai syncs on its own, so neither depends on these jobs. Neither documents a way to read which version a workspace holds (checked 2026-10-13 for ChatGPT), so without a receipt in `~/.claude/plugin-sync/` the drift check reports that cloud delivery as unknown. Unknown is the expected answer when a platform exposes nothing, and nobody has to write receipts by hand. The copies in `~/.claude/plugins/synced` are supporting evidence only, and reading the source is never proof of installation. Installation and runtime use are separate states: runtime use stays unverified until a new or reloaded session loads the skill.

Logs are in `~/Library/Logs/plugin-sync/`. Tests: `python3 -m unittest discover -s tools/plugin-sync/tests`. `test_legacy_skills.py` runs both sync scripts against fake homes for the old-copy migration, including failure, retry and reconnect cases. `test_local_sync.py` runs both sync scripts and the installer against stub CLIs and local git remotes, so it needs no network and touches no real machine. Its tests name the stub CLIs through `CODEX_BIN` and `CLAUDE_BIN`, and point `PLUGIN_SYNC_SYSTEM_ROOT` at a fake root, so they never run the Mac's own `codex`, `claude` or `launchctl`.
