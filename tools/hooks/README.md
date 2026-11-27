# hooks

Claude Code and Codex hooks: the pre-tool-use enforcement hook, the routing check and the canonical repo pull hook, with their tests.

Moved here on November 8, 2026 from ExpertPartners/Development (archived) at commit 325fd884, under the HQ Repository Map. Full history stays in the archived Development repository.

Act by default (Decision Log 2026-11-08): the deletion approval notes, the SSH delete scanner, the Codex approved-delete wrapper and the M4 batch executor were retired. The enforcement hook now blocks one thing, an unscoped `git config user.name/user.email` that would rewrite the commit identity of every worktree, and allows everything else without a note.

It also runs `ai-copy-guard.py`, which blocks a `git clone`, a `git worktree add` or a heavy media or archive download whose destination is outside `~/HQ-AI-Workspace-M4/Scratch` or a temp folder, so AI copies stop piling up on the Macs. A deliberate new canonical clone in Projects passes with `EP_CANONICAL_CLONE=1`. Factory and Codex run the same guard directly; `tools/maintenance/install-m4-copy-prevention.py` adds it to their hook files, and `tools/maintenance/m4-scratch-janitor.py` expires what lands in Scratch.

The running copies on each Mac are installed locally. This folder is the source, not the runtime.

Work preflight uses `work-preflight.py` and the shared Factory connector before source searches or replacement builds. `install-work-preflight.py --policy <private-projection>` adds the canonical hook to Factory, Claude Code and Codex without replacing unrelated hooks. The projection comes from existing owning Ledger dispositions and contains no independent work queue. Keep it private and update it when the owning dispositions or implementation owners change. Never put business record IDs or policy data in this public repository. Source closure never means implementation passed. Vendor tools that do not execute these hooks are not covered by a host installation, and an existing session is not proven refreshed by a settings write.

## Commands

```bash
bash tools/hooks/tests/test-routing-check.sh
bash tools/hooks/tests/test-git-identity-guard.sh
bash tools/hooks/tests/test-ai-copy-guard.sh
```
