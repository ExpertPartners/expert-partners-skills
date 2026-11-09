# hooks

Claude Code and Codex hooks: the pre-tool-use enforcement hook, the routing check and the canonical repo pull hook, with their tests.

Moved here on November 8, 2026 from ExpertPartners/Development (archived) at commit 325fd884, under the HQ Repository Map. Full history stays in the archived Development repository.

Act by default (Decision Log 2026-11-08): the deletion approval notes, the SSH delete scanner, the Codex approved-delete wrapper and the M4 batch executor were retired. The enforcement hook now blocks one thing, an unscoped `git config user.name/user.email` that would rewrite the commit identity of every worktree, and allows everything else without a note.

The running copies on each Mac are installed locally. This folder is the source, not the runtime.

## Commands

```bash
bash tools/hooks/tests/test-routing-check.sh
bash tools/hooks/tests/test-git-identity-guard.sh
```
