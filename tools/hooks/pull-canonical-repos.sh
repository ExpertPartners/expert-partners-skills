#!/bin/bash
# Pull canonical Allison-domain repos. Safe to run any time — exits 0 even if offline.
# Used by Claude Code SessionStart hook on M4.
set -u

REPOS=(
    "$HOME/HQ-AI-Workspace-M4/Projects/Aura"
    "$HOME/HQ-AI-Workspace-M4/Projects/AGPersonalBrand"
    "$HOME/HQ-AI-Workspace-M4/Projects/AGVault"
    "$HOME/HQ-AI-Workspace-M4/Projects/AzulioPartnership"
    "$HOME/HQ-AI-Workspace-M4/Projects/EPIC"
    "$HOME/HQ-AI-Workspace-M4/Workbench"
    "$HOME/HQ-AI-Workspace-M4/Projects/FAM"
    "$HOME/HQ-AI-Workspace-M4/Projects/HeyGen"
    "$HOME/HQ-AI-Workspace-M4/Projects/MoxieSignatureGroup"
    "$HOME/HQ-AI-Workspace-M4/Projects/PartnerSync"
    "$HOME/HQ-AI-Workspace-M4/Projects/TheStrongOnes"
    "$HOME/HQ-AI-Workspace-M4/Projects/book"
    # ghl-automation removed 2026-09-08 (split into partnersync and partnersync-automation-backend, repo retired)
    # eXpExplained2 intentionally excluded (archival repo, no active sessions)
)

for repo in "${REPOS[@]}"; do
    if [ -d "$repo/.git" ]; then
        git -C "$repo" pull --quiet --ff-only 2>/dev/null || true
    fi
done

exit 0
