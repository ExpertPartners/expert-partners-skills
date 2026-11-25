# hooks

Claude Code and Codex hooks: the pre-tool-use enforcement hook, the routing check and the canonical repo pull hook, with their tests.

Moved here on November 8, 2026 from ExpertPartners/Development (archived) at commit 325fd884, under the HQ Repository Map. Full history stays in the archived Development repository.

Act by default (Decision Log 2026-11-08): the deletion approval notes, the SSH delete scanner, the Codex approved-delete wrapper and the M4 batch executor were retired. The enforcement hook now blocks one thing, an unscoped `git config user.name/user.email` that would rewrite the commit identity of every worktree, and allows everything else without a note.

It also runs `ai-copy-guard.py`, which blocks a `git clone`, a `git worktree add` or a heavy media or archive download whose destination is outside `~/HQ-AI-Workspace-M4/Scratch` or a temp folder, so AI copies stop piling up on the Macs. A deliberate new canonical clone in Projects passes with `EP_CANONICAL_CLONE=1`. Factory and Codex run the same guard directly; `tools/maintenance/install-m4-copy-prevention.py` adds it to their hook files, and `tools/maintenance/m4-scratch-janitor.py` expires what lands in Scratch.

The running copies on each Mac are installed locally. This folder is the source, not the runtime.

## Commands

```bash
bash tools/hooks/tests/test-routing-check.sh
bash tools/hooks/tests/test-git-identity-guard.sh
bash tools/hooks/tests/test-ai-copy-guard.sh
```
