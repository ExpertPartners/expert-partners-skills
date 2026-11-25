# maintenance

Keeps AI copies from piling up on Allison's Macs.

The rule: AI scratch work, temporary clones, worktrees and local media copies go only in `~/HQ-AI-Workspace-M4/Scratch/<date>-<task>`. Heavy media lives on the M2 or in Drive. Reuse the one canonical clone in `~/HQ-AI-Workspace-M4/Projects` instead of cloning again. A session removes what it created when it ends; the janitor catches anything left behind.

- `m4-scratch-janitor.py` runs every 6 hours at background priority from launchd. In Scratch it removes rebuildable caches idle for 2 days and whole entries idle for 7 days (3 days when less than 15 GiB is free), but only when every git repository inside is clean, has no stash and has every commit on a remote. It also removes leftover linked worktrees in Projects and `~/.codex/worktrees` under the same test. Anything open by a running process is skipped. Entries that were in Scratch before the janitor was installed only lose safe repositories and caches, never other files. Every removal and every item kept for a person is logged in `~/Library/Logs/m4-scratch-janitor/`.
- `--sweep PATH ...` applies the same safe-repository and cache rules to any folder, for a one-time cleanup. Use `--dry-run` first to see what would go.
- `install-m4-copy-prevention.py` loads the launchd job and adds `tools/hooks/ai-copy-guard.py` to the Factory and Codex PreToolUse hooks. Claude Code runs the guard through `tools/hooks/pre-tool-use-enforcement.sh`. Everything runs from the synced marketplace clone, so there is no hand copy to drift.
- The free-space warning itself is the existing `m4-storage-watch` launchd job.

Removal is permanent because the Trash is on the same disk and would free nothing. Only verified pushed clones and rebuildable caches qualify.

## Commands

```bash
bash tools/maintenance/tests/test-m4-scratch-janitor.sh
bash tools/hooks/tests/test-ai-copy-guard.sh
python3 tools/maintenance/m4-scratch-janitor.py --dry-run
python3 tools/maintenance/install-m4-copy-prevention.py
```
