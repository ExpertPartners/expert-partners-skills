# hooks

Claude Code and Codex guard hooks: the pre-tool-use enforcement hook, the deletion approval note writer and its shared library, the Codex approved-delete wrapper, the routing check and the canonical repo pull hook, with their tests.

Moved here on November 8, 2026 from ExpertPartners/Development (archived) at commit 325fd884, under the HQ Repository Map. Full history stays in the archived Development repository.

The running copies on each Mac are installed locally (on the M4 under `~/HQ-AI-Workspace-M4/Workbench/scripts/`). This folder is the source, not the runtime. Several tests and the one-off September 23 M4 batch policy are tied to those local paths, so `test-approved-delete-codex.sh`, `test-deletion-approval-path.sh` and `test_m4_batch2.py` only pass on the M4 with the hooks installed. They failed the same way in Development before the move.

## Commands

```bash
bash tools/hooks/tests/test-routing-check.sh
bash tools/hooks/tests/test-git-identity-guard.sh
python3 tools/hooks/tests/test_ssh_deletion_approval.py
```
