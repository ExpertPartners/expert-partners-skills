#!/usr/bin/env bash
# Regression tests for tools/skill-deploy/deploy-skill.sh (aura issue #212, 2026-09-04).
# Builds a throwaway eps-shaped repo (the script under test copied into place) and a
# throwaway git repo standing in for aura, then exercises the deployed-copy contract:
# header + manifest on every deploy, --verify catching hand-edit drift and lying
# manifests, --repair-drift as the only way past them, --from for an external canonical,
# --mirror-mount deploying a whole mount with orphan detection, idempotent reruns
# across dates, and the mirror-of-mirror refusal.
#
# Run: bash tools/skill-deploy/test/test-deploy-skill.sh   (needs python3 + PyYAML, rsync, shasum, git)
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
REAL_SCRIPT="$HERE/../deploy-skill.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

PASS=0 FAIL=0
ok()   { PASS=$((PASS + 1)); echo "PASS $1"; }
bad()  { FAIL=$((FAIL + 1)); echo "FAIL $1"; [ -n "${2:-}" ] && printf '%s\n' "$2" | sed 's/^/     /'; }
check() { # check <label> <condition-exit-code> [detail]
  if [ "$2" -eq 0 ]; then ok "$1"; else bad "$1" "${3:-}"; fi
}

# ---- fixture: eps-shaped repo with the script under test ----
EPS="$TMP/eps"
mkdir -p "$EPS/tools/skill-deploy" "$EPS/plugins" "$EPS/skills/alpha/references"
cp "$REAL_SCRIPT" "$EPS/tools/skill-deploy/deploy-skill.sh"
chmod +x "$EPS/tools/skill-deploy/deploy-skill.sh"
D="$EPS/tools/skill-deploy/deploy-skill.sh"
cat > "$EPS/skills/alpha/SKILL.md" <<'EOF'
---
name: alpha
description: Test skill alpha. Use when testing the deploy pipeline.
tier: organization
zone: hands
status: live
---

# Alpha -- v1.0 (2026-09-04)

Canonical instructions for alpha.
EOF
echo "alpha reference notes" > "$EPS/skills/alpha/references/notes.md"

# ---- fixture: aura-shaped git repo (external canonical home) ----
AURA="$TMP/Aura"
mkdir -p "$AURA/.claude/skills/beta" "$AURA/.claude/skills/alpha"
git -C "$AURA" init -q
git -C "$AURA" remote add origin https://github.com/ExpertPartners/aura.git
cat > "$AURA/.claude/skills/beta/SKILL.md" <<'EOF'
---
name: beta
description: Test skill beta, aura-native. Use when testing external canonical deploys.
allowed-tools: Read, Bash
tier: project
zone: routing
status: live
---

You are beta. No version line on purpose.
EOF
# alpha's presence in the aura mount stands for a deployed copy of an eps skill; its
# bytes are irrelevant because mirror-mount resolves alpha to the eps canonical.
cp "$EPS/skills/alpha/SKILL.md" "$AURA/.claude/skills/alpha/SKILL.md"

MOUNT="$AURA/.agents/skills"
export SKILL_DEPLOY_TODAY=2026-09-04

# ---- T1 deploy a single eps canonical skill ----
out=$("$D" alpha --to "$MOUNT" 2>&1); rc=$?
check "T1 single deploy exits 0" $rc "$out"
grep -q '^# expert-partners-skills skills/alpha/SKILL.md\. Deployed at v1\.0\.$' "$MOUNT/alpha/SKILL.md"
check "T1 header names canonical home and version" $?
grep -q '^# DEPLOYED COPY (2026-09-04, skill-deploy pipeline)' "$MOUNT/alpha/SKILL.md"
check "T1 header carries the deploy date" $?
[ -f "$MOUNT/alpha/checksums.sha256" ] && ( cd "$MOUNT/alpha" && shasum -a 256 -c checksums.sha256 --quiet )
check "T1 manifest present and verifies with shasum" $?
[ -f "$MOUNT/alpha/references/notes.md" ]
check "T1 reference files deployed alongside" $?

# ---- T2 verify passes on a clean copy ----
out=$("$D" alpha --to "$MOUNT" --verify 2>&1); rc=$?
check "T2 --verify exits 0 on a clean copy" $rc "$out"
printf '%s' "$out" | grep -q '^OK alpha:'
check "T2 --verify reports OK" $?

# ---- T3 idempotent reruns, same day and a later day ----
before=$(cd "$MOUNT/alpha" && find . -type f -print0 | sort -z | xargs -0 shasum -a 256 | shasum -a 256)
out=$("$D" alpha --to "$MOUNT" 2>&1); rc=$?
printf '%s' "$out" | grep -q '^unchanged:'
check "T3 same-day rerun reports unchanged" $?
out=$(SKILL_DEPLOY_TODAY=2030-01-01 "$D" alpha --to "$MOUNT" 2>&1); rc=$?
printf '%s' "$out" | grep -q '^unchanged:'
check "T3 later-day rerun reports unchanged (date is not drift)" $?
after=$(cd "$MOUNT/alpha" && find . -type f -print0 | sort -z | xargs -0 shasum -a 256 | shasum -a 256)
[ "$before" = "$after" ]
check "T3 rerun leaves every byte untouched" $?

# ---- T4 external canonical via --from ----
out=$("$D" beta --from "$AURA/.claude/skills/beta" --to "$MOUNT" 2>&1); rc=$?
check "T4 --from deploy exits 0" $rc "$out"
grep -qE '^# aura \.claude/skills/beta/SKILL\.md\. Deployed at tree sha256 [0-9a-f]{12}\.$' "$MOUNT/beta/SKILL.md"
check "T4 header names the aura canonical by remote repo name and carries a tree stamp" $?
out=$("$D" beta --from "$AURA/.claude/skills/beta" --to "$MOUNT" --verify 2>&1); rc=$?
check "T4 --verify passes for the external copy" $rc "$out"
# the deployed copy is the canonical plus header, nothing else changed
diff <(grep -v '^# DEPLOYED COPY\|^# aura \.claude\|^# Edit the canonical' "$MOUNT/beta/SKILL.md") "$AURA/.claude/skills/beta/SKILL.md" >/dev/null
check "T4 body is byte-faithful to canonical (header aside)" $?

# ---- T5 --from refused when the skill has an eps canonical home ----
out=$("$D" alpha --from "$AURA/.claude/skills/alpha" --to "$MOUNT" 2>&1); rc=$?
[ $rc -ne 0 ] && printf '%s' "$out" | grep -q 'canonical home in this repo'
check "T5 --from on an eps-canonical skill is refused" $?

# ---- T6 mirror of a mirror refused ----
mkdir -p "$AURA/.claude/skills/gamma"
sed 's/^name: beta$/name: gamma/' "$MOUNT/beta/SKILL.md" > "$AURA/.claude/skills/gamma/SKILL.md"
out=$("$D" gamma --from "$AURA/.claude/skills/gamma" --to "$MOUNT" 2>&1); rc=$?
[ $rc -ne 0 ] && printf '%s' "$out" | grep -q 'is itself a DEPLOYED COPY'
check "T6 a source carrying a DEPLOYED COPY header is refused as a source" $?
rm -rf "$AURA/.claude/skills/gamma"

# ---- T7 hand-edit drift: verify catches it, deploy refuses, repair restores ----
printf '\nTampered by hand.\n' >> "$MOUNT/alpha/SKILL.md"
out=$("$D" alpha --to "$MOUNT" --verify 2>&1); rc=$?
[ $rc -ne 0 ] && printf '%s' "$out" | grep -q '^DRIFT alpha: deployed copy differs' && printf '%s' "$out" | grep -q 'manifest hash does not match'
check "T7 --verify fails on hand-edit drift, naming content and manifest" $? "$out"
out=$("$D" alpha --to "$MOUNT" 2>&1); rc=$?
[ $rc -ne 0 ] && printf '%s' "$out" | grep -q 'FATAL: existing deployed copy'
check "T7 deploy refuses to overwrite drift without --repair-drift" $?
out=$("$D" alpha --to "$MOUNT" --repair-drift 2>&1); rc=$?
[ $rc -eq 0 ] && printf '%s' "$out" | grep -q '^deployed:'
check "T7 --repair-drift replaces the drifted copy" $? "$out"
out=$("$D" alpha --to "$MOUNT" --verify 2>&1); rc=$?
check "T7 --verify passes after repair" $rc "$out"

# ---- T8 missing manifest is drift ----
rm "$MOUNT/beta/checksums.sha256"
out=$("$D" beta --from "$AURA/.claude/skills/beta" --to "$MOUNT" --verify 2>&1); rc=$?
[ $rc -ne 0 ] && printf '%s' "$out" | grep -q 'no checksums.sha256 present'
check "T8 --verify fails when the manifest is missing" $?
out=$("$D" beta --from "$AURA/.claude/skills/beta" --to "$MOUNT" 2>&1); rc=$?
[ $rc -ne 0 ]
check "T8 deploy refuses a manifest-less copy without --repair-drift" $?
out=$("$D" beta --from "$AURA/.claude/skills/beta" --to "$MOUNT" --repair-drift 2>&1); rc=$?
check "T8 --repair-drift restores the manifest" $rc "$out"

# ---- T9 lying manifest (file added that the manifest omits) ----
echo "stray" > "$MOUNT/beta/stray.md"
out=$("$D" beta --from "$AURA/.claude/skills/beta" --to "$MOUNT" --verify 2>&1); rc=$?
[ $rc -ne 0 ] && printf '%s' "$out" | grep -q 'extra file in deployed copy' && printf '%s' "$out" | grep -q 'not covered by the manifest'
check "T9 --verify catches a file the manifest does not cover" $? "$out"
rm "$MOUNT/beta/stray.md"

# ---- T10 mirror-mount deploys a whole mount, resolving each source correctly ----
MOUNT2="$AURA/.agents2/skills"
out=$("$D" --mirror-mount "$AURA/.claude/skills" --to "$MOUNT2" 2>&1); rc=$?
check "T10 --mirror-mount deploy exits 0" $rc "$out"
grep -q '^# expert-partners-skills skills/alpha/SKILL.md\. Deployed at v1\.0\.$' "$MOUNT2/alpha/SKILL.md"
check "T10 eps-canonical skill in the mount is sourced from eps, not from the mount copy" $?
grep -qE '^# aura \.claude/skills/beta/SKILL\.md\. Deployed at tree sha256 [0-9a-f]{12}\.$' "$MOUNT2/beta/SKILL.md"
check "T10 aura-native skill in the mount is sourced from the mount" $?
out=$("$D" --mirror-mount "$AURA/.claude/skills" --to "$MOUNT2" --verify 2>&1); rc=$?
[ $rc -eq 0 ] && printf '%s' "$out" | grep -q 'all 2 skill(s) clean'
check "T10 --mirror-mount --verify passes on a fresh mirror" $? "$out"
out=$("$D" --mirror-mount "$AURA/.claude/skills" --to "$MOUNT2" 2>&1); rc=$?
[ $rc -eq 0 ] && [ "$(printf '%s\n' "$out" | grep -c '^unchanged:')" -eq 2 ]
check "T10 --mirror-mount rerun is a no-op (2 unchanged)" $? "$out"

# ---- T11 orphan in the destination fails verify and deploy ----
mkdir -p "$MOUNT2/zeta"; echo "---" > "$MOUNT2/zeta/SKILL.md"
out=$("$D" --mirror-mount "$AURA/.claude/skills" --to "$MOUNT2" --verify 2>&1); rc=$?
[ $rc -ne 0 ] && printf '%s' "$out" | grep -q '^ORPHAN zeta:'
check "T11 orphan skill directory in the destination is named and fails" $? "$out"
[ -d "$MOUNT2/zeta" ]
check "T11 orphan is never deleted automatically" $?
rm -rf "$MOUNT2/zeta"

# ---- T12 canonical change propagates: verify flags stale, deploy refreshes ----
printf '\nA new canonical paragraph.\n' >> "$EPS/skills/alpha/SKILL.md"
out=$("$D" --mirror-mount "$AURA/.claude/skills" --to "$MOUNT2" --verify 2>&1); rc=$?
[ $rc -ne 0 ] && printf '%s' "$out" | grep -q '^DRIFT alpha: deployed copy differs'
check "T12 --verify flags a copy that is stale against canonical" $? "$out"
out=$("$D" --mirror-mount "$AURA/.claude/skills" --to "$MOUNT2" 2>&1); rc=$?
[ $rc -eq 0 ] && printf '%s' "$out" | grep -q '^deployed: .*alpha' && printf '%s' "$out" | grep -q '^unchanged: .*beta'
check "T12 redeploy refreshes only the stale copy" $? "$out"
out=$("$D" --mirror-mount "$AURA/.claude/skills" --to "$MOUNT2" --verify 2>&1); rc=$?
check "T12 --verify passes after redeploy" $rc "$out"

# ---- T13 the portable frontmatter contract gates the mount ----
mkdir -p "$AURA/.claude/skills/Bad-Name"
printf -- '---\nname: Bad-Name\ndescription: bad\ntier: project\nzone: routing\nstatus: live\n---\nx\n' > "$AURA/.claude/skills/Bad-Name/SKILL.md"
out=$("$D" --mirror-mount "$AURA/.claude/skills" --to "$MOUNT2" 2>&1); rc=$?
[ $rc -ne 0 ] && printf '%s' "$out" | grep -q 'Agent Skills frontmatter contract'
check "T13 a mount skill violating the Agent Skills name rule fails the deploy" $? "$out"
rm -rf "$AURA/.claude/skills/Bad-Name" "$MOUNT2/Bad-Name"

# ---- T14 flag hygiene ----
out=$("$D" --mirror-mount "$AURA/.claude/skills" --to "$MOUNT2" --verify --repair-drift 2>&1); rc=$?
[ $rc -ne 0 ] && printf '%s' "$out" | grep -q 'never writes'
check "T14 --verify with --repair-drift is refused" $?
out=$("$D" alpha --verify 2>&1); rc=$?
[ $rc -ne 0 ] && printf '%s' "$out" | grep -q 'requires --to'
check "T14 --verify without --to is refused" $?
out=$("$D" --mirror-mount "$AURA/.claude/skills" --to "$AURA/.claude/skills" 2>&1); rc=$?
[ $rc -ne 0 ] && printf '%s' "$out" | grep -q 'same directory'
check "T14 mount and destination must differ" $?

echo
echo "deploy-skill tests: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
