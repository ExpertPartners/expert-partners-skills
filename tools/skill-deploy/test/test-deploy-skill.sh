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
# T16-T19 exercise the read-only lifecycle half (skill-lifecycle.py) on fixture HOMEs:
# the surface audit (every surface, every copy state, loading precedence, canonical
# read from a git ref) and the release-receipt checker (the evidence ladder and
# every bypass a review proved possible). T16's pipeline-copy assertions are also a
# render-parity contract: a copy the producer just wrote must audit CURRENT.
#
# The T15 test is a CONTRACT test: it feeds a real pipeline-produced mount to the
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

# ---- T16 lifecycle audit: every surface classified against canonical at a git ref ----
# A fixture HOME carries every surface skill-lifecycle.py walks. Canonical skills of
# every source kind (versioned standalone with a reference file, tree-stamped
# standalone, plugin-carried, aura-native, retired, designed) are committed, and copies
# are planted in known states. Every assertion names the surface it expects.
LC="$EPS/tools/skill-deploy/skill-lifecycle.py"
cp "$HERE/../skill-lifecycle.py" "$LC"
LH="$TMP/lifehome"; mkdir -p "$LH"
ORG=org-active; ACCT=acct-1; ORG2=org-old
fail_setup() { bad "T16 fixture setup: $1" "${2:-}"; }
python3 - "$EPS" "$AURA" <<'PY' || fail_setup "canonical fixture"
import json, os, sys
eps, aura = sys.argv[1], sys.argv[2]
def w(p, s):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w").write(s)
with open(f"{eps}/skills/alpha/SKILL.md", "a") as f:
    f.write("\nRun it from Claude Code and read CLAUDE.md first.\n")
w(f"{eps}/skills/mu/SKILL.md", "---\nname: mu\ndescription: Fixture mu, tree-stamped. Use when testing stamps.\ntier: user\nzone: routing\nstatus: live\n---\n\nMu has no version line on purpose.\n")
w(f"{eps}/skills/mu/references/guide.md", "mu guide\n")
for plugin, ver, sid, body in (("doctrine-fixture", "1.2.0", "gamma", "# Gamma -- v2.0 (2026-09-24)\n\nGamma body.\n"),
                               ("voice-fixture", "1.0.0", "iota", "# Iota -- v1.0 (2026-09-24)\n\nIota body.\n"),
                               ("tools-fixture", "1.0.0", "lambda", "# Lambda -- v1.0 (2026-09-24)\n\nLambda body.\n")):
    w(f"{eps}/plugins/{plugin}/.claude-plugin/plugin.json", json.dumps({"name": plugin, "version": ver}) + "\n")
    w(f"{eps}/plugins/{plugin}/skills/{sid}/SKILL.md", f"---\nname: {sid}\ndescription: Fixture {sid}. Use when testing plugin surfaces.\ntier: plugin\nzone: routing\nstatus: live\n---\n\n{body}")
w(f"{eps}/plugins/doctrine-fixture/skills/gamma/references/ref.md", "gamma reference\n")
w(f"{aura}/.claude/skills/delta/SKILL.md", "---\nname: delta\ndescription: Retired fixture delta.\ntier: project\nzone: routing\nstatus: retired\n---\n\nDelta body.\n")
w(f"{aura}/.claude/skills/eta/SKILL.md", "---\nname: eta\ndescription: Fixture eta, aura-native. Use when testing precedence.\ntier: project\nzone: routing\nstatus: live\n---\n\nEta current body.\n")
w(f"{aura}/project-knowledge/staging/theta/SKILL.md", "---\nname: theta\ndescription: Designed fixture theta.\ntier: project\nzone: routing\nstatus: designed\n---\n\nTheta.\n")
nodes = [("alpha", "eps:skills/alpha/SKILL.md", "live"), ("mu", "eps:skills/mu/SKILL.md", "live"),
         ("gamma", "eps:plugins/doctrine-fixture/skills/gamma/SKILL.md", "live"),
         ("iota", "eps:plugins/voice-fixture/skills/iota/SKILL.md", "live"),
         ("lambda", "eps:plugins/tools-fixture/skills/lambda/SKILL.md", "live"),
         ("beta", "aura:.claude/skills/beta/SKILL.md", "live"), ("delta", "aura:.claude/skills/delta/SKILL.md", "retired"),
         ("eta", "aura:.claude/skills/eta/SKILL.md", "live"), ("theta", "aura:project-knowledge/staging/theta/SKILL.md", "designed")]
w(f"{eps}/tools/skill-map/skills-graph.json", json.dumps({"schema": "skill-map/v1", "edges": [],
  "nodes": [{"id": i, "source": s, "status": st} for i, s, st in nodes]}))
PY
git -C "$EPS" add -A && git -C "$EPS" -c user.email=t@t -c user.name=t commit -qm "lifecycle fixture canonicals" || fail_setup "eps commit"
out=$("$D" alpha --to "$AURA/.claude/skills" --repair-drift 2>&1) || fail_setup "redeploy alpha into the aura project mount" "$out"
out=$("$D" --mirror-mount "$AURA/.claude/skills" --to "$AURA/.agents/skills" 2>&1) || fail_setup "mirror aura mounts" "$out"
git -C "$AURA" add -A && git -C "$AURA" -c user.email=t@t -c user.name=t commit -qm "lifecycle fixture aura" || fail_setup "aura commit"

# local surfaces, built through the producer where a pipeline copy is meant
for s in alpha mu gamma; do out=$("$D" "$s" --to "$LH/.claude/skills" 2>&1) || fail_setup "deploy $s to the Claude Code user mount" "$out"; done
out=$("$D" beta --from "$AURA/.claude/skills/beta" --to "$LH/.claude/skills" 2>&1) || fail_setup "deploy beta" "$out"
for s in alpha mu gamma; do out=$("$D" "$s" --to "$LH/.agents/skills" 2>&1) || fail_setup "deploy $s to the Codex user mount" "$out"; done
python3 - "$EPS" "$AURA" "$LH" "$ORG" "$ACCT" "$ORG2" <<'PY' || fail_setup "surface fixture"
import hashlib, json, os, shutil, sys
eps, aura, lh, org, acct, org2 = sys.argv[1:7]
def w(p, s):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w").write(s)
def remanifest(d):
    lines = []
    for dp, _, fn in os.walk(d):
        for f in fn:
            if f != "checksums.sha256":
                p = os.path.join(dp, f)
                lines.append((("./" + os.path.relpath(p, d)).encode(), hashlib.sha256(open(p, "rb").read()).hexdigest()))
    open(os.path.join(d, "checksums.sha256"), "w").write("".join(f"{h}  {r.decode()}\n" for r, h in sorted(lines)))
def rewrite(t):
    return t.replace("Claude Code", "Codex").replace("CLAUDE.md", "AGENTS.md").replace("Claude", "Codex")
def copytree(src, dst):
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(src, dst)
alpha = f"{eps}/skills/alpha"; gamma = f"{eps}/plugins/doctrine-fixture/skills/gamma"
# Claude Code user mount: eta is a header-less older copy that shadows the aura canonical
w(f"{lh}/.claude/skills/eta/SKILL.md", open(f"{aura}/.claude/skills/eta/SKILL.md").read().replace("Eta current body.", "Eta older body."))
# Codex user mount: alpha rewritten Claude->Codex (manifest now lies); zeta an orphan pipeline copy;
# mu a stale supporting file under a recomputed manifest; gamma a description-only drift under a recomputed manifest
p = f"{lh}/.agents/skills/alpha/SKILL.md"; w(p, rewrite(open(p).read()))
w(f"{lh}/.agents/skills/zeta/SKILL.md", "---\nname: zeta\ndescription: orphan\n# DEPLOYED COPY (2026-09-01, skill-deploy pipeline): the canonical home is\n# expert-partners-skills skills/zeta/SKILL.md. Deployed at v1.0.\n# Edit the canonical copy first, then redeploy via tools/skill-deploy.\n---\n\nZeta.\n")
w(f"{lh}/.agents/skills/mu/references/guide.md", "mu guide, an older revision\n"); remanifest(f"{lh}/.agents/skills/mu")
p = f"{lh}/.agents/skills/gamma/SKILL.md"; w(p, open(p).read().replace("description: Fixture gamma.", "description: Fixture gamma, an older trigger.")); remanifest(f"{lh}/.agents/skills/gamma")
# Claude Code plugin cache: gamma installed at stale 1.1.0 (loads), current 1.2.0 inert; iota installed but disabled
for ver, extra in (("1.1.0", "\nOld gamma paragraph.\n"), ("1.2.0", "")):
    d = f"{lh}/.claude/plugins/cache/expert-partners/doctrine-fixture/{ver}/skills/gamma"; copytree(gamma, d)
    if extra:
        open(f"{d}/SKILL.md", "a").write(extra)
copytree(f"{eps}/plugins/voice-fixture/skills/iota", f"{lh}/.claude/plugins/cache/expert-partners/voice-fixture/1.0.0/skills/iota")
w(f"{lh}/.claude/plugins/installed_plugins.json", json.dumps({"version": 2, "plugins": {
  "doctrine-fixture@expert-partners": [{"scope": "user", "version": "1.1.0"}],
  "voice-fixture@expert-partners": [{"scope": "user", "version": "1.0.0"}]}}))
w(f"{lh}/.claude/settings.json", json.dumps({"enabledPlugins": {"voice-fixture@expert-partners": False, "tools-fixture@inline": False}}))
# claude.ai org plugin sync: doctrine-fixture shadowed by the local install; voice-fixture loads (local one disabled);
# tools-fixture disabled through enabledPlugins
for d, name, ver, sid, src in (("doctrine-fixture~g2", "doctrine-fixture", "1.2.0", "gamma", gamma),
                               ("voice-fixture~g2", "voice-fixture", "1.0.0", "iota", f"{eps}/plugins/voice-fixture/skills/iota"),
                               ("tools-fixture~g2", "tools-fixture", "1.0.0", "lambda", f"{eps}/plugins/tools-fixture/skills/lambda")):
    base = f"{lh}/.claude/plugins/synced/acct_sync/{d}"
    w(f"{base}/.claude-plugin/plugin.json", json.dumps({"name": name, "version": ver}))
    w(f"{base}.meta.json", json.dumps({"marketplace_name": "ExpertPartners/expert-partners-skills"}))
    copytree(src, f"{base}/skills/{sid}")
# claude.ai account shelf: alpha missing its reference file; beta with an older description
sy = f"{lh}/.claude/skills/synced/acct_sync"
w(f"{sy}/alpha/SKILL.md", open(f"{alpha}/SKILL.md").read())
w(f"{sy}/beta/SKILL.md", open(f"{aura}/.claude/skills/beta/SKILL.md").read().replace("description: Test skill beta", "description: Old beta trigger"))
w(f"{sy}/manifest.json", json.dumps({"lastUpdated": 0, "skills": [{"name": "alpha"}, {"name": "beta"}]}))
# Codex plugin caches: gamma current from expert-partners (plus an older inert version dir) and a stale claude-cowork import, both enabled
copytree(gamma, f"{lh}/.codex/plugins/cache/expert-partners/doctrine-fixture/1.2.0/skills/gamma")
copytree(gamma, f"{lh}/.codex/plugins/cache/expert-partners/doctrine-fixture/1.1.0/skills/gamma")
copytree(gamma, f"{lh}/.codex/plugins/cache/claude-cowork/doctrine-fixture/1.0.0/skills/gamma")
open(f"{lh}/.codex/plugins/cache/claude-cowork/doctrine-fixture/1.0.0/skills/gamma/SKILL.md", "a").write("\nImported old gamma.\n")
w(f"{lh}/.codex/config.toml", '[plugins."doctrine-fixture@expert-partners"]\nenabled = true\n\n[plugins."doctrine-fixture@claude-cowork"]\nenabled = true\n')
# Codex synced mirror: a Claude->Codex rewrite of alpha, reference file included
xd = f"{lh}/.agents/skills/synced/acct_sync/alpha"; copytree(alpha, xd); w(f"{xd}/SKILL.md", rewrite(open(f"{xd}/SKILL.md").read()))
# Cowork: the signed-in org/account loads; an older org's cache is inert
cw = f"{lh}/Library/Application Support/Claude/local-agent-mode-sessions"
old_alpha = open(f"{alpha}/SKILL.md").read().replace("Canonical instructions for alpha.", "Older alpha instructions.")
for o in (org, org2):
    w(f"{cw}/skills-plugin/{o}/{acct}/skills/alpha/SKILL.md", old_alpha)
for o, stale in ((org, False), (org2, True)):
    base = f"{cw}/{acct}/{o}/rpm/plugin_{o}"
    w(f"{base}/.claude-plugin/plugin.json", json.dumps({"name": "doctrine-fixture", "version": "1.2.0"}))
    copytree(gamma, f"{base}/skills/gamma")
    if stale:
        open(f"{base}/skills/gamma/SKILL.md", "a").write("\nOld org gamma.\n")
w(f"{lh}/.claude.json", json.dumps({"oauthAccount": {"organizationUuid": org, "accountUuid": acct}}))
PY

out=$(python3 "$LC" audit --eps "$EPS" --aura "$AURA" --home "$LH" --json "$LH/audit.json" 2>&1); rc=$?
[ $rc -eq 1 ] && printf '%s' "$out" | grep -q '^audit-surfaces: 9 of 9 canonical skill(s) audited, [1-9][0-9]* finding(s)' && ! printf '%s' "$out" | grep -q 'Traceback'
check "T16 audit exits 1 with its summary line and no traceback when findings exist" $? "$out"
python3 - "$LH/audit.json" <<'PY2'
import json, sys
a = json.load(open(sys.argv[1]))
def cp(sid, surface):
    return sorted((c["state"], c["loads"]) for c in a["skills"][sid]["copies"] if c["surface"] == surface)
def has(sid, kind, surface=None, client=None):
    return any(f["id"] == sid and f["kind"] == kind and (surface is None or f.get("surface") == surface)
               and (client is None or f.get("client") == client) for f in a["findings"])
checks = [
 ("pipeline copies of all four source kinds render CURRENT (versioned, tree-stamped, plugin, aura --from)",
  all(cp(s, "claude-code-user-mount") == [("CURRENT", True)] for s in ("alpha", "mu", "gamma", "beta"))),
 ("header-less older eta on the user mount is UNTRACKED-COPY-STALE", cp("eta", "claude-code-user-mount") == [("UNTRACKED-COPY-STALE", True)]),
 ("the aura canonical eta is shadowed by the personal copy, with a SHADOWED finding", cp("eta", "claude-code-project-mount") == [("CANONICAL", False)] and has("eta", "SHADOWED", "claude-code-project-mount")),
 ("an identical personal beta shadows the project canonical without a SHADOWED finding", cp("beta", "claude-code-project-mount") == [("CANONICAL", False)] and not has("beta", "SHADOWED")),
 ("the rewritten Codex alpha is HAND-EDITED and REWRITTEN on codex-user-mount", cp("alpha", "codex-user-mount") == [("HAND-EDITED", True)] and has("alpha", "REWRITTEN", "codex-user-mount")),
 ("a stale supporting file under a clean manifest is STALE on codex-user-mount", cp("mu", "codex-user-mount") == [("STALE", True)] and has("mu", "STALE", "codex-user-mount")),
 ("a description-only drift under a clean manifest is STALE on codex-user-mount", cp("gamma", "codex-user-mount") == [("STALE", True)]),
 ("an orphan pipeline copy is reported on codex-user-mount", has("zeta", "ORPHAN", "codex-user-mount")),
 ("the installed stale plugin version loads and the current one is inert", cp("gamma", "claude-code-plugin-cache") == [("CURRENT", False), ("STALE", True)] and has("gamma", "STALE", "claude-code-plugin-cache")),
 ("a disabled plugin is inert", cp("iota", "claude-code-plugin-cache") == [("CURRENT", False)]),
 ("an org-synced plugin shadowed by a local install is inert", cp("gamma", "claudeai-org-plugin-sync") == [("CURRENT", False)]),
 ("an org-synced plugin whose local twin is disabled loads", cp("iota", "claudeai-org-plugin-sync") == [("CURRENT", True)]),
 ("an org-synced plugin disabled in enabledPlugins is inert", cp("lambda", "claudeai-org-plugin-sync") == [("CURRENT", False)]),
 ("an account-shelf copy missing a supporting file is STALE", cp("alpha", "claudeai-account-skills-sync") == [("STALE", True)]),
 ("an account-shelf copy with an older description is STALE", cp("beta", "claudeai-account-skills-sync") == [("STALE", True)]),
 ("an older Codex cache version is inert, both enabled marketplaces load", cp("gamma", "codex-plugin-cache") == [("CURRENT", False), ("CURRENT", True), ("STALE", True)]),
 ("divergent Codex gamma copies raise DUPLICATE-IDENTITY for codex", has("gamma", "DUPLICATE-IDENTITY", client="codex")),
 ("the Codex synced mirror alpha is STALE and REWRITTEN", cp("alpha", "codex-synced-mirror") == [("STALE", True)] and has("alpha", "REWRITTEN", "codex-synced-mirror")),
 ("only the signed-in Cowork org loads: active alpha STALE, old org inert", cp("alpha", "cowork-account-skills") == [("STALE", False), ("STALE", True)]),
 ("Cowork org plugins: active gamma CURRENT, old org copy inert", cp("gamma", "cowork-org-plugins") == [("CURRENT", True), ("STALE", False)] and not has("gamma", "STALE", "cowork-org-plugins")),
 ("no DUPLICATE-IDENTITY for cowork gamma (the old org does not count)", not has("gamma", "DUPLICATE-IDENTITY", client="cowork")),
 ("the retired delta loads from the Codex repo mount", cp("delta", "codex-repo-mount") == [("CURRENT", True)] and has("delta", "RETIRED-LOADING", "codex-repo-mount")),
 ("the retired delta loads from its project canonical", cp("delta", "claude-code-project-mount") == [("CANONICAL", True)] and has("delta", "RETIRED-LOADING", "claude-code-project-mount")),
 ("beta is absent on the Codex user mount (a Claude Code copy never stands in for Codex)", cp("beta", "codex-user-mount") == []),
 ("no false REWRITTEN on any Claude-side copy", not any(f["kind"] == "REWRITTEN" and not f["surface"].startswith("codex") for f in a["findings"])),
 ("the canonical refs are recorded", a["canonicalRefs"]["eps"]["ref"] == "HEAD" and len(a["canonicalRefs"]["eps"]["commit"]) == 40),
]
bad = [m for m, ok in checks if not ok]
for m in bad:
    print("MISSING:", m)
sys.exit(1 if bad else 0)
PY2
check "T16 audit classifies every planted state on the surface it was planted on" $?
out=$(python3 "$LC" audit --eps "$EPS" --aura "$AURA" --home "$LH" --only beta --json "$LH/only.json" 2>&1); rc=$?
python3 -c "import json,sys; a=json.load(open('$LH/only.json')); sys.exit(0 if list(a['skills'])==['beta'] and a['findings'] and all(f['id']=='beta' for f in a['findings']) and a['auditedCount']==1 else 1)" && [ $rc -eq 1 ]
check "T16 --only narrows the walk, the findings and the count to the named skill" $? "$out"
out=$(python3 "$LC" audit --eps "$EPS" --aura "$AURA" --home "$LH" --only betaa 2>&1); rc=$?
[ $rc -ne 0 ] && printf '%s' "$out" | grep -q 'names no canonical skill: betaa'
check "T16 an unknown --only id is refused, never an empty pass" $? "$out"
python3 - "$EPS/tools/skill-map/skills-graph.json" "$LH" <<'PY2'
import copy, json, sys
source, out = sys.argv[1:]
base = json.load(open(source))
for name, node in (
    ("missing-eps", {"id": "missing-eps", "source": "eps:skills/missing-eps/SKILL.md", "status": "live"}),
    ("missing-aura", {"id": "missing-aura", "source": "aura:.claude/skills/missing-aura/SKILL.md", "status": "live"}),
):
    graph = copy.deepcopy(base)
    graph["nodes"].append(node)
    with open(f"{out}/{name}-graph.json", "w") as f:
        json.dump(graph, f)
graph = copy.deepcopy(base)
next(n for n in graph["nodes"] if n["id"] == "alpha")["source"] = "eps:skills/mu/SKILL.md"
with open(f"{out}/wrong-source-graph.json", "w") as f:
    json.dump(graph, f)
graph = copy.deepcopy(base)
graph["nodes"] = [n for n in graph["nodes"] if n["id"] != "alpha"]
with open(f"{out}/ungraphed-source-graph.json", "w") as f:
    json.dump(graph, f)
graph = copy.deepcopy(base)
graph["nodes"].append(copy.deepcopy(graph["nodes"][0]))
with open(f"{out}/duplicate-id-graph.json", "w") as f:
    json.dump(graph, f)
with open(f"{out}/empty-graph.json", "w") as f:
    json.dump({"nodes": []}, f)
PY2
for name in missing-eps missing-aura wrong-source ungraphed-source duplicate-id empty; do
  out=$(python3 "$LC" audit --eps "$EPS" --aura "$AURA" --home "$LH" --only alpha --graph "$LH/$name-graph.json" --report-only 2>&1); rc=$?
  [ $rc -ne 0 ] && printf '%s' "$out" | grep -Eq 'no canonical home|graph source mismatch|absent from the graph|duplicate canonical id|graph has no nodes'
  check "T16 graph $name fails even when the missing or mismapped node is outside --only" $? "$out"
done
printf '\nAn uncommitted edit in the working tree.\n' >> "$EPS/skills/alpha/SKILL.md"
out=$(python3 "$LC" audit --eps "$EPS" --home "$LH" --only alpha --json "$LH/ref.json" --report-only 2>&1)
python3 -c "import json,sys; a=json.load(open('$LH/ref.json')); s=[c['state'] for c in a['skills']['alpha']['copies'] if c['surface']=='claude-code-user-mount']; sys.exit(0 if s==['CURRENT'] else 1)"
check "T16 canonical comes from the committed ref, not the working tree" $? "$out"
out=$(python3 "$LC" audit --eps "$EPS" --home "$LH" --only alpha --canonical-ref WORKTREE --json "$LH/wt.json" --report-only 2>&1)
python3 -c "import json,sys; a=json.load(open('$LH/wt.json')); s=[c['state'] for c in a['skills']['alpha']['copies'] if c['surface']=='claude-code-user-mount']; sys.exit(0 if s==['STALE'] else 1)"
check "T16 --canonical-ref WORKTREE reads the working tree" $? "$out"
git -C "$EPS" checkout -q -- skills/alpha/SKILL.md

# ---- T17 receipt: the ladder is computed from evidence, never claimed ----
LH2="$TMP/lifehome2"; mkdir -p "$LH2"
out=$("$D" alpha --to "$LH2/.claude/skills" 2>&1) || fail_setup "deploy alpha to the clean home" "$out"
EPS_HEAD=$(git -C "$EPS" rev-parse HEAD)
python3 "$LC" receipt-template alpha --eps "$EPS" > "$LH2/tmpl.json" 2>"$LH2/tmpl.err"
python3 - "$LH2/tmpl.json" "$EPS_HEAD" <<'PY2'
import json, sys
t = json.load(open(sys.argv[1]))
ok = (len(t["surfaces"]) == 13 and t["canonical"]["commit"] == sys.argv[2]
      and all(v[k] is None for v in t["surfaces"].values() for k in ("intended", "installed", "discovered", "behaviorTested"))
      and t["packaged"] == [])
sys.exit(0 if ok else 1)
PY2
check "T17 receipt-template names every surface key, fills canonical from the ref, and leaves every slot null" $?
cat > "$TMP/rx.py" <<'PY2'
import json, sys
src, dst, code = sys.argv[1], sys.argv[2], sys.argv[3]
r = json.load(open(src))
for k in r["surfaces"]:
    r["surfaces"][k] = {"intended": False, "reason": "not owed in this fixture", "installed": None,
                        "discovered": None, "behaviorTested": None, "disposition": "fixture copy noted"}
SLOT = {"verifiedAt": "2026-09-24", "method": "fixture method", "evidence": "fixture log"}
BEH = {"verifiedAt": "2026-09-24", "fixture": "alpha-A", "result": "pass", "evidence": "fixture log"}
ZIP = {"kind": "upload-zip", "artifact": "alpha-v1.0.zip", "sha256": "ab" * 32, "builtFrom": r["canonical"]["commit"]}
def full(k, beh=True):
    r["surfaces"][k].update({"intended": True, "reason": "owed", "installed": dict(SLOT), "discovered": dict(SLOT),
                             "behaviorTested": dict(BEH) if beh else None, "disposition": None})
exec(code)
json.dump(r, open(dst, "w"), indent=1)
PY2
rx() { python3 "$TMP/rx.py" "$1" "$LH2/r.json" "$2"; }
chk() { python3 "$LC" receipt-check "$LH2/r.json" --eps "$EPS" --home "$LH2" "$@" 2>&1; }
out=$(python3 "$LC" receipt-check "$LH2/tmpl.json" --eps "$EPS" --home "$LH2" 2>&1); rc=$?
[ $rc -ne 0 ] && printf '%s' "$out" | grep -q 'intended must be true or false'
check "T17 the unedited template is NOT COMPLETE" $? "$out"
rx "$LH2/tmpl.json" 'r["surfaces"]["codex-user-mount"] = None'; out=$(chk); rc=$?
[ $rc -ne 0 ] && printf '%s' "$out" | grep -q 'codex-user-mount: entry must be an object'
check "T17 a null surface entry fails" $? "$out"
rx "$LH2/tmpl.json" 'full("claude-code-user-mount"); del r["surfaces"]["chatgpt-north"]'; out=$(chk); rc=$?
[ $rc -ne 0 ] && printf '%s' "$out" | grep -q 'missing chatgpt-north'
check "T17 a receipt that omits ChatGPT/NORTH is refused" $? "$out"
ladder() { # ladder <label> <python edits> <expected state> <expected note>
  rx "$LH2/tmpl.json" "$2"; out=$(chk); rc=$?
  [ $rc -ne 0 ] && printf '%s' "$out" | grep -q "claude-code-user-mount  *$3  *.*$4"
  check "T17 $1" $? "$out"
}
ladder "no installed slot stops at PACKAGED" 'full("claude-code-user-mount"); r["surfaces"]["claude-code-user-mount"]["installed"] = None' PACKAGED 'installed: slot missing'
ladder "a placeholder verifiedAt is not evidence" 'full("claude-code-user-mount"); r["surfaces"]["claude-code-user-mount"]["installed"]["verifiedAt"] = "YYYY-MM-DD"' PACKAGED 'verifiedAt must be'
ladder "installed without discovery stops at INSTALLED" 'full("claude-code-user-mount"); r["surfaces"]["claude-code-user-mount"]["discovered"] = None' INSTALLED 'discovered: slot missing'
ladder "discovered without a fixture stops at DISCOVERED" 'full("claude-code-user-mount", beh=False)' DISCOVERED 'behaviorTested: slot missing'
ladder "a failed fixture stays at DISCOVERED" 'full("claude-code-user-mount"); r["surfaces"]["claude-code-user-mount"]["behaviorTested"]["result"] = "FAIL"' DISCOVERED 'behavior fixture failed'
rx "$LH2/tmpl.json" 'full("claude-code-user-mount")'; out=$(chk); rc=$?
[ $rc -eq 0 ] && printf '%s' "$out" | grep -q 'claude-code-user-mount  *BEHAVIOR TESTED' && printf '%s' "$out" | grep -q 'RELEASE COMPLETE'
check "T17 installed, discovered and a passed fixture reach BEHAVIOR TESTED and RELEASE COMPLETE" $? "$out"
out=$(python3 "$LC" receipt-check - --eps "$EPS" --home "$LH2" < "$LH2/r.json" 2>&1); rc=$?
[ $rc -eq 0 ] && printf '%s' "$out" | grep -q 'RELEASE COMPLETE' && [ -z "$(find "$LH2" -name '.*audit*' -print)" ]
check "T17 a receipt read from stdin checks the same way and leaves no temp file" $? "$out"
rx "$LH2/tmpl.json" 'full("chatgpt-north")'; out=$(chk); rc=$?
[ $rc -ne 0 ] && printf '%s' "$out" | grep -q 'chatgpt-north  *CANONICAL  *no valid'
check "T17 a hosted surface with no package stops at CANONICAL" $? "$out"
rx "$LH2/tmpl.json" 'full("chatgpt-north"); r["packaged"] = [{"kind": "plugin-version", "artifact": "x@1", "builtFrom": r["canonical"]["commit"]}]'; out=$(chk); rc=$?
[ $rc -ne 0 ] && printf '%s' "$out" | grep -q 'which no plugin carries'
check "T17 a plugin-version package for a standalone skill is refused" $? "$out"
rx "$LH2/tmpl.json" 'full("chatgpt-north"); r["packaged"] = [dict(ZIP, sha256="<zip sha256>")]'; out=$(chk); rc=$?
[ $rc -ne 0 ] && printf '%s' "$out" | grep -q 'upload-zip needs a real artifact name and a 64-hex sha256'
check "T17 a placeholder package hash is refused" $? "$out"
rx "$LH2/tmpl.json" 'full("chatgpt-north"); r["packaged"] = [ZIP]'; out=$(chk); rc=$?
[ $rc -eq 0 ] && printf '%s' "$out" | grep -q 'chatgpt-north  *BEHAVIOR TESTED'
check "T17 a hosted surface with a valid package and full evidence reaches BEHAVIOR TESTED" $? "$out"
rx "$LH2/tmpl.json" 'full("claude-code-user-mount"); del r["canonical"]["skillmdSha256"]'; out=$(chk); rc=$?
[ $rc -ne 0 ] && printf '%s' "$out" | grep -q 'skillmdSha256 is required'
check "T17 a receipt without the canonical hash is refused" $? "$out"
rx "$LH2/tmpl.json" 'full("claude-code-user-mount"); r["canonical"]["version"] = "v0.1"'; out=$(chk); rc=$?
[ $rc -ne 0 ] && printf '%s' "$out" | grep -q 'does not match the live version line'
check "T17 a receipt for another version is refused" $? "$out"
rx "$LH2/tmpl.json" 'full("chatgpt-north"); r["packaged"] = [dict(ZIP, builtFrom="0123456")]'; out=$(chk); rc=$?
[ $rc -ne 0 ] && printf '%s' "$out" | grep -q 'builtFrom .* must equal canonical.commit'
check "T17 a package built from another commit is refused" $? "$out"
rx "$LH2/tmpl.json" 'full("claude-code-user-mount"); r["canonical"]["skillmdSha256"] = "00" * 32'; out=$(chk); rc=$?
[ $rc -ne 0 ] && printf '%s' "$out" | grep -q 'stale receipt'
check "T17 a receipt whose canonical hash no longer matches canonical is refused as stale" $? "$out"
printf '{"schema":"skill-release-receipt/v1","skill":"nope","canonical":{},"packaged":[],"surfaces":{}}\n' > "$LH2/r.json"
out=$(chk); rc=$?
[ $rc -ne 0 ] && printf '%s' "$out" | grep -q 'missing canonical home'
check "T17 a receipt for a skill with no canonical home is refused" $? "$out"
printf '{"schema":"skill-release-receipt/v1","skill":"beta","canonical":{},"packaged":[],"surfaces":{}}\n' > "$LH2/r.json"
out=$(chk); rc=$?
[ $rc -ne 0 ] && printf '%s' "$out" | grep -q 'beta is aura-native; pass --aura'
check "T17 an aura-native receipt checked without --aura says so" $? "$out"
for s in theta delta; do
  printf '{"schema":"skill-release-receipt/v1","skill":"%s","canonical":{},"packaged":[],"surfaces":{}}\n' "$s" > "$LH2/r.json"
  out=$(chk --aura "$AURA"); rc=$?
  case $s in theta) want='not yet canonical' ;; delta) want='retired' ;; esac
  [ $rc -ne 0 ] && printf '%s' "$out" | grep -q "$s is $want"
  check "T17 a $s receipt is refused ($want)" $? "$out"
done

# ---- T18 receipt: live state decides, and one surface never stands in for another ----
python3 "$LC" receipt-template alpha --eps "$EPS" --aura "$AURA" > "$LH/tmpl-alpha.json" 2>/dev/null
python3 "$LC" receipt-template eta --eps "$EPS" --aura "$AURA" > "$LH/tmpl-eta.json" 2>/dev/null
python3 "$LC" receipt-template gamma --eps "$EPS" --aura "$AURA" > "$LH/tmpl-gamma.json" 2>/dev/null
rchk() { python3 "$LC" receipt-check "$LH2/r.json" --eps "$EPS" --aura "$AURA" --home "$LH" 2>&1; }
rx "$LH/tmpl-alpha.json" 'full("codex-user-mount")'; out=$(rchk); rc=$?
[ $rc -ne 0 ] && printf '%s' "$out" | grep -q 'codex-user-mount .*a loading copy is HAND-EDITED' && printf '%s' "$out" | grep -q 'Claude-to-Codex rewrite'
check "T18 an installed claim on Codex is refused while the live copy is a hand-edited rewrite" $? "$out"
rx "$LH/tmpl-alpha.json" 'full("claude-code-user-mount")'; out=$(rchk); rc=$?
[ $rc -ne 0 ] && printf '%s' "$out" | grep -q 'divergent duplicate identity in claude-code'
check "T18 a current copy does not install while a divergent copy of the same skill loads in the same client" $? "$out"
rx "$LH/tmpl-alpha.json" 'full("claude-code-user-mount"); r["surfaces"]["codex-user-mount"]["intended"] = True; r["surfaces"]["codex-user-mount"]["reason"] = "owed"'; out=$(rchk); rc=$?
[ $rc -ne 0 ] && printf '%s' "$out" | grep -q 'codex-user-mount  *PACKAGED  *installed: slot missing'
check "T18 Claude Code evidence never covers the Codex surface" $? "$out"
rx "$LH/tmpl-eta.json" 'full("claude-code-project-mount")'; out=$(rchk); rc=$?
[ $rc -ne 0 ] && printf '%s' "$out" | grep -q 'claude-code-project-mount .*no loading copy on this surface (shadowed by the personal skill'
check "T18 a canonical shadowed by a personal copy never counts as installed" $? "$out"
rx "$LH/tmpl-gamma.json" 'full("claude-code-plugin-cache"); r["packaged"] = [{"kind": "plugin-version", "artifact": "doctrine-fixture@1.2.0", "builtFrom": r["canonical"]["commit"]}]'; out=$(rchk); rc=$?
[ $rc -ne 0 ] && printf '%s' "$out" | grep -q 'claude-code-plugin-cache .*a loading copy is STALE'
check "T18 the installed stale plugin version blocks INSTALLED even though a current version sits in the cache" $? "$out"
rx "$LH/tmpl-gamma.json" 'full("claude-code-plugin-cache"); r["packaged"] = [{"kind": "plugin-version", "artifact": "doctrine-fixture@1.2.0", "builtFrom": r["canonical"]["commit"]}]; r["surfaces"]["codex-plugin-cache"]["disposition"] = None'; out=$(rchk); rc=$?
[ $rc -ne 0 ] && printf '%s' "$out" | grep -q 'codex-plugin-cache: not intended, yet a copy loads there'
check "T18 a loading copy on an unintended surface needs a disposition" $? "$out"
printf '%s' "$out" | grep -q 'claudeai-org-plugin-sync  *NOT INTENDED  *no loading copy; inert copy present: CURRENT'
check "T18 an inert copy on an unintended surface is reported, never 'no copy present'" $? "$out"

# ---- T19 the producer is the entry point ----
out=$("$D" --audit-surfaces --aura "$AURA" --home "$LH" --only alpha --report-only 2>&1); rc=$?
[ $rc -eq 0 ] && printf '%s' "$out" | grep -q '^alpha \['
check "T19 deploy-skill.sh --audit-surfaces passes through to the audit" $? "$out"
out=$("$D" --receipt-template alpha --aura "$AURA" 2>&1); rc=$?
[ $rc -eq 0 ] && printf '%s' "$out" | grep -q '"skill-release-receipt/v1"'
check "T19 deploy-skill.sh --receipt-template passes through" $? "$out"
out=$("$D" --receipt 2>&1); rc=$?
[ $rc -ne 0 ] && printf '%s' "$out" | grep -q 'needs a receipt file'
check "T19 deploy-skill.sh --receipt without a file is refused" $? "$out"

echo
echo "deploy-skill tests: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
