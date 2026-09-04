#!/usr/bin/env bash
# Regression tests for tools/skill-deploy/deploy-skill.sh (aura issue #212, 2026-09-04).
# Builds a throwaway eps-shaped repo (the script under test copied into place) and a
# throwaway git repo standing in for aura, then exercises the deployed-copy contract:
# header + manifest on every deploy, --verify catching hand-edit drift and lying
# manifests, --repair-drift as the only way past them, --from for an external
# canonical, --mirror-mount deploying a whole mount with orphan and name-shadow
# detection, --verify-copies for a mixed mount, idempotent reruns across dates and
# locales, junk-file exclusion, loud write failures, and the mirror-of-mirror refusal.
#
# The last test is a CONTRACT test: it feeds a real pipeline-produced mount to the
# real extractor, which is the only place render()'s output meets the extractor's
# header regex and byte-fidelity check. Without it the two tools could drift apart
# with both suites green.
#
# Run: bash tools/skill-deploy/test/test-deploy-skill.sh   (needs python3 + PyYAML, rsync, shasum, git, node)
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT_REAL="$(cd "$HERE/../../.." && pwd)"
REAL_SCRIPT="$HERE/../deploy-skill.sh"
EXTRACTOR="$REPO_ROOT_REAL/tools/skill-map/extract-skills-graph.mjs"
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
git -C "$EPS" init -q && git -C "$EPS" add -A && git -C "$EPS" -c user.email=t@t -c user.name=t commit -qm init

# ---- fixture: aura-shaped git repo (external canonical home) ----
AURA="$TMP/Aura"
mkdir -p "$AURA/.claude/skills/beta"
git -C "$AURA" init -q
git -C "$AURA" remote add origin https://github.com/ExpertPartners/aura.git
printf '.DS_Store\n__pycache__/\n*.pyc\n' > "$AURA/.gitignore"
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
git -C "$AURA" add -A && git -C "$AURA" -c user.email=t@t -c user.name=t commit -qm init

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

# ---- T3 idempotent reruns, same day, later day, other locale ----
stamp_tree() { ( cd "$1" && find . -type f -print0 | LC_ALL=C sort -z | xargs -0 shasum -a 256 | shasum -a 256 ); }
before=$(stamp_tree "$MOUNT/alpha")
out=$("$D" alpha --to "$MOUNT" 2>&1)
printf '%s' "$out" | grep -q '^unchanged:'
check "T3 same-day rerun reports unchanged" $?
out=$(SKILL_DEPLOY_TODAY=2030-01-01 "$D" alpha --to "$MOUNT" 2>&1)
printf '%s' "$out" | grep -q '^unchanged:'
check "T3 later-day rerun reports unchanged (date is not drift)" $?
out=$(LC_ALL=en_US.UTF-8 "$D" alpha --to "$MOUNT" 2>&1)
printf '%s' "$out" | grep -q '^unchanged:'
check "T3 rerun under a different locale reports unchanged" $? "$out"
after=$(stamp_tree "$MOUNT/alpha")
[ "$before" = "$after" ]
check "T3 reruns leave every byte untouched" $?

# ---- T4 external canonical via --from ----
out=$("$D" beta --from "$AURA/.claude/skills/beta" --to "$MOUNT" 2>&1); rc=$?
check "T4 --from deploy exits 0" $rc "$out"
grep -qE '^# aura \.claude/skills/beta/SKILL\.md\. Deployed at tree sha256 [0-9a-f]{12}\.$' "$MOUNT/beta/SKILL.md"
check "T4 header names the aura canonical by remote repo name and carries a tree stamp" $?
out=$("$D" beta --from "$AURA/.claude/skills/beta" --to "$MOUNT" --verify 2>&1); rc=$?
check "T4 --verify passes for the external copy" $rc "$out"
diff <(grep -v '^# DEPLOYED COPY\|^# aura \.claude\|^# Edit the canonical' "$MOUNT/beta/SKILL.md") "$AURA/.claude/skills/beta/SKILL.md" >/dev/null
check "T4 body is byte-faithful to canonical (header aside)" $?

# ---- T4b the tree stamp is locale-independent ----
sC=$(LC_ALL=C "$D" beta --from "$AURA/.claude/skills/beta" --to "$TMP/probeC" 2>/dev/null | grep -oE 'tree sha256 [0-9a-f]{12}')
sU=$(LC_ALL=en_US.UTF-8 "$D" beta --from "$AURA/.claude/skills/beta" --to "$TMP/probeU" 2>/dev/null | grep -oE 'tree sha256 [0-9a-f]{12}')
[ -n "$sC" ] && [ "$sC" = "$sU" ]
check "T4b tree stamp is identical under LC_ALL=C and en_US.UTF-8" $? "C=$sC U=$sU"

# ---- T5 --from refused when the skill has an eps canonical home ----
mkdir -p "$AURA/.claude/skills/alpha"; cp "$EPS/skills/alpha/SKILL.md" "$AURA/.claude/skills/alpha/SKILL.md"
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

# ---- T6b a canonical whose BODY documents the header format is still a valid source ----
mkdir -p "$AURA/.claude/skills/delta"
{ sed 's/^name: beta$/name: delta/' "$AURA/.claude/skills/beta/SKILL.md"
  echo; echo "Deployed copies carry a header shaped like this:"; echo
  echo "# DEPLOYED COPY (2026-09-04, skill-deploy pipeline): the canonical home is"
} > "$AURA/.claude/skills/delta/SKILL.md"
out=$("$D" delta --from "$AURA/.claude/skills/delta" --to "$MOUNT" 2>&1); rc=$?
check "T6b a canonical documenting the header in its BODY still deploys" $rc "$out"
rm -rf "$AURA/.claude/skills/delta" "$MOUNT/delta"

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

# ---- T9 lying manifest (file present that the manifest omits) ----
echo "stray" > "$MOUNT/beta/stray.md"
out=$("$D" beta --from "$AURA/.claude/skills/beta" --to "$MOUNT" --verify 2>&1); rc=$?
[ $rc -ne 0 ] && printf '%s' "$out" | grep -q 'extra file in deployed copy' && printf '%s' "$out" | grep -q 'not covered by the manifest'
check "T9 --verify catches a file the manifest does not cover" $? "$out"
rm "$MOUNT/beta/stray.md"

# ---- T9b git-ignored junk in the canonical never reaches the copy or the manifest ----
touch "$AURA/.claude/skills/beta/.DS_Store"
mkdir -p "$AURA/.claude/skills/beta/scripts/__pycache__"
echo x > "$AURA/.claude/skills/beta/scripts/__pycache__/run.cpython-312.pyc"
out=$("$D" beta --from "$AURA/.claude/skills/beta" --to "$MOUNT" --verify 2>&1); rc=$?
check "T9b --verify stays clean when git-ignored junk sits in the canonical" $rc "$out"
out=$("$D" beta --from "$AURA/.claude/skills/beta" --to "$MOUNT" 2>&1)
printf '%s' "$out" | grep -q '^unchanged:'
check "T9b redeploy with junk present is still a no-op" $?
! grep -q 'DS_Store\|__pycache__' "$MOUNT/beta/checksums.sha256"
check "T9b manifest lists no ignored junk" $?
rm -f "$AURA/.claude/skills/beta/.DS_Store"; rm -rf "$AURA/.claude/skills/beta/scripts"

# ---- T9c a write failure is FATAL, never reported as a deploy ----
mkdir -p "$TMP/blocked"; : > "$TMP/blocked/alpha"      # destination path is a regular file
out=$("$D" alpha --to "$TMP/blocked" 2>&1); rc=$?
[ $rc -ne 0 ] && printf '%s' "$out" | grep -qi 'FATAL' && ! printf '%s' "$out" | grep -q '^deployed:'
check "T9c deploy over a non-directory fails loudly and never prints 'deployed'" $? "$out"

# ---- T9d empty or comment-only frontmatter is refused ----
mkdir -p "$AURA/.claude/skills/empty"
printf -- '---\n\n---\n\nNo name or description here.\n' > "$AURA/.claude/skills/empty/SKILL.md"
out=$("$D" empty --from "$AURA/.claude/skills/empty" --to "$MOUNT" 2>&1); rc=$?
[ $rc -ne 0 ] && printf '%s' "$out" | grep -q 'frontmatter block is empty'
check "T9d a canonical with empty frontmatter is refused" $? "$out"
rm -rf "$AURA/.claude/skills/empty" "$MOUNT/empty"

# ---- T10 mirror-mount deploys a whole mount, resolving each source correctly ----
# The mount's own copy of an eps-canonical skill must itself be a deployed copy;
# deploy it into the mount first, exactly as the real estate does.
"$D" alpha --to "$AURA/.claude/skills" --repair-drift >/dev/null 2>&1
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

# ---- T10b a mount entry that shadows an eps canonical name is refused ----
cp "$AURA/.claude/skills/alpha/SKILL.md" "$TMP/alpha-copy-backup"
sed '/^# DEPLOYED COPY/,+2d' "$TMP/alpha-copy-backup" > "$AURA/.claude/skills/alpha/SKILL.md"  # a second canonical wearing a taken name
out=$("$D" --mirror-mount "$AURA/.claude/skills" --to "$MOUNT2" 2>&1); rc=$?
[ $rc -ne 0 ] && printf '%s' "$out" | grep -q 'shares its name with the canonical skill at expert-partners-skills skills/alpha/SKILL.md but is not a pipeline-produced copy of it'
check "T10b a mount entry shadowing an eps canonical name is refused, not silently overwritten" $? "$out"
cp "$TMP/alpha-copy-backup" "$AURA/.claude/skills/alpha/SKILL.md"

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
[ $rc -ne 0 ] && printf '%s' "$out" | grep -q 'DRIFT alpha'
check "T12 --verify flags a copy that is stale against canonical" $? "$out"
# refresh the Claude Code mount copy first (it is a deployed copy of the same canonical)
"$D" alpha --to "$AURA/.claude/skills" --repair-drift >/dev/null 2>&1
out=$("$D" --mirror-mount "$AURA/.claude/skills" --to "$MOUNT2" 2>&1); rc=$?
[ $rc -eq 0 ] && printf '%s' "$out" | grep -q '^deployed: .*alpha' && printf '%s' "$out" | grep -q '^unchanged: .*beta'
check "T12 redeploy refreshes only the stale copy" $? "$out"
out=$("$D" --mirror-mount "$AURA/.claude/skills" --to "$MOUNT2" --verify 2>&1); rc=$?
check "T12 --verify passes after redeploy" $rc "$out"

# ---- T12b --verify-copies gates a MIXED mount without touching its canonicals ----
out=$("$D" --verify-copies "$AURA/.claude/skills" 2>&1); rc=$?
[ $rc -eq 0 ] && printf '%s' "$out" | grep -q 'all 1 deployed cop(ies)' && printf '%s' "$out" | grep -q '1 canonical skill(s) left alone'
check "T12b --verify-copies checks the copies and leaves the canonicals alone" $? "$out"
printf '\nHand edit in the Claude Code mount.\n' >> "$AURA/.claude/skills/alpha/SKILL.md"
out=$("$D" --verify-copies "$AURA/.claude/skills" 2>&1); rc=$?
[ $rc -ne 0 ] && printf '%s' "$out" | grep -q '^DRIFT alpha'
check "T12b --verify-copies catches a hand edit in a mixed mount" $? "$out"
"$D" alpha --to "$AURA/.claude/skills" --repair-drift >/dev/null 2>&1

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
out=$("$D" --verify-copies "$AURA/.claude/skills" --to "$MOUNT2" 2>&1); rc=$?
[ $rc -ne 0 ] && printf '%s' "$out" | grep -q 'stands alone'
check "T14 --verify-copies refuses to combine with other flags" $?

# ---- T15 CONTRACT: a real pipeline-produced mount satisfies the real extractor ----
# This is the only place render()'s bytes meet the extractor's header regex AND its
# byte-fidelity check. If the two tools' idea of the header ever diverges, this fails.
if [ -f "$EXTRACTOR" ] && command -v node >/dev/null 2>&1 && [ -d "$REPO_ROOT_REAL/tools/skill-map/node_modules" ]; then
  CEPS="$TMP/contract/eps"; CAURA="$TMP/contract/aura"
  mkdir -p "$CEPS/tools/skill-deploy" "$CEPS/plugins/operating-doctrine/skills/operating-doctrine" "$CEPS/skills/alpha"
  mkdir -p "$CAURA/.claude/skills/beta"
  cp "$REAL_SCRIPT" "$CEPS/tools/skill-deploy/deploy-skill.sh"; chmod +x "$CEPS/tools/skill-deploy/deploy-skill.sh"
  cat > "$CEPS/plugins/operating-doctrine/skills/operating-doctrine/SKILL.md" <<'EOF'
---
name: operating-doctrine
description: The contract-test stand-in for the doctrine root skill.
tier: plugin
zone: brain
status: live
inherits: []
---

Doctrine body.
EOF
  cat > "$CEPS/skills/alpha/SKILL.md" <<'EOF'
---
name: alpha
description: Contract-test canonical alpha. Use when testing the deploy-to-extractor contract.
tier: organization
zone: hands
status: live
---

# Alpha -- v2.0 (2026-09-04)

Contract body.
EOF
  cat > "$CAURA/.claude/skills/beta/SKILL.md" <<'EOF'
---
name: beta
description: Contract-test aura-native beta. Use when testing the deploy-to-extractor contract.
tier: project
zone: routing
status: live
---

Beta body, no version line.
EOF
  git -C "$CAURA" init -q
  git -C "$CAURA" remote add origin https://github.com/ExpertPartners/aura.git
  git -C "$CAURA" add -A && git -C "$CAURA" -c user.email=t@t -c user.name=t commit -qm init
  # Shape the fixture like the real estate: the Claude Code mount carries a
  # deployed copy of an eps canonical (alpha) beside an aura-native canonical
  # (beta), and the Codex mount mirrors both.
  "$CEPS/tools/skill-deploy/deploy-skill.sh" alpha --to "$CAURA/.claude/skills" >/dev/null 2>&1
  "$CEPS/tools/skill-deploy/deploy-skill.sh" --mirror-mount "$CAURA/.claude/skills" --to "$CAURA/.agents/skills" >/dev/null 2>&1
  cp -R "$REPO_ROOT_REAL/tools/skill-map" "$CEPS/tools/skill-map"
  out=$(node "$CEPS/tools/skill-map/extract-skills-graph.mjs" --eps "$CEPS" --aura "$CAURA" --out "$TMP/contract/graph.json" 2>&1); rc=$?
  [ $rc -eq 0 ]
  check "T15 the extractor accepts a real pipeline-produced mount" $? "$out"
  n=$(python3 -c "import json;print(len(json.load(open('$TMP/contract/graph.json'))['flags']['deployedMounts']))" 2>/dev/null)
  [ "$n" = "3" ]
  check "T15 all three deployed copies are recorded as mounts, not as nodes" $? "deployedMounts=$n (expected alpha in both mounts, beta in the Codex mount)"
  ids=$(python3 -c "import json;print(','.join(sorted(n['id'] for n in json.load(open('$TMP/contract/graph.json'))['nodes'])))" 2>/dev/null)
  [ "$ids" = "alpha,beta,operating-doctrine" ]
  check "T15 exactly the three canonical skills are nodes" $? "nodes=$ids"
else
  echo "SKIP T15 contract test (extractor or node_modules unavailable)"
fi

echo
echo "deploy-skill tests: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
