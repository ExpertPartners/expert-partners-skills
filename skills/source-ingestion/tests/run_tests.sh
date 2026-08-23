#!/usr/bin/env bash
# Real tests for the source-ingestion skill's deterministic machinery, run
# against synthetic fixtures only. Never touches a real corpus, a real repo,
# or network. Exercises scripts/scaffold_dossier.py directly (test matrix
# cases 1, 2, 3, 7, 8) and the deploy-skill.sh --chatgpt-zip extension
# (cross-surface packaging). Cases 4, 5, and 6 test the documented protocol
# text itself, since they are classification/routing judgment calls an LLM
# makes, not deterministic code; this proves the correct instruction is on
# the page rather than simulating a model's reasoning.
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
REPO_ROOT="$(cd "$SKILL_DIR/../.." && pwd)"
SCAFFOLD="$SKILL_DIR/scripts/scaffold_dossier.py"
DEPLOY="$REPO_ROOT/tools/skill-deploy/deploy-skill.sh"
FIXTURES="$SKILL_DIR/tests/fixtures"

TMPDIR_TEST=$(mktemp -d)
trap 'rm -rf "$TMPDIR_TEST"' EXIT

PASS=0
FAIL=0
check() {
  if [ "$1" = "true" ]; then
    echo "PASS: $2"; PASS=$((PASS + 1))
  else
    echo "FAIL: $2"; FAIL=$((FAIL + 1))
  fi
}

echo "== Case 1: third-party marketing source, ordinary =="
OUT1="$TMPDIR_TEST/case1"
python3 "$SCAFFOLD" \
  --title "The Offer Ladder (synthetic)" --creator "Fictional Author A" \
  --source-type pdf --domain marketing \
  --provenance "Synthetic fixture standing in for a purchased marketing book" \
  --original-location "$FIXTURES/marketing-pdf-synthetic.txt" \
  --date 2026-01-01 --ownership third-party --destination "PLANNED: ExpertPartners/external-methodologies (not yet created)" \
  --binary linked --binary-location "$FIXTURES/marketing-pdf-synthetic.txt" \
  --out "$OUT1" >/dev/null
D1="$OUT1/marketing/fictional-author-a/the-offer-ladder-synthetic"
[ -f "$D1/README.md" ] && [ -f "$D1/source-record.md" ] && FOUND1=true || FOUND1=false
check "$FOUND1" "case 1 produces README.md + source-record.md under domain/creator/source"
grep -q "^ownership: third-party$" "$D1/README.md" && check true "case 1 records third-party ownership" || check false "case 1 records third-party ownership"
grep -q "^core: false$" "$D1/README.md" && check true "case 1 defaults core to false (no silent elevation)" || check false "case 1 defaults core to false"

echo "== Case 2: same source, explicitly marked CORE =="
OUT2="$TMPDIR_TEST/case2"
python3 "$SCAFFOLD" \
  --title "The Offer Ladder (synthetic)" --creator "Fictional Author A" \
  --source-type pdf --domain marketing \
  --provenance "Synthetic fixture standing in for a purchased marketing book" \
  --original-location "$FIXTURES/marketing-pdf-synthetic-CORE.txt" \
  --date 2026-01-01 --ownership third-party --core \
  --core-basis "Allison: this is foundational, make sure the Estate knows this" \
  --destination "PLANNED: ExpertPartners/external-methodologies (not yet created)" \
  --binary linked --binary-location "$FIXTURES/marketing-pdf-synthetic-CORE.txt" \
  --out "$OUT2" >/dev/null
D2="$OUT2/marketing/fictional-author-a/the-offer-ladder-synthetic"
grep -q "^core: true$" "$D2/README.md" && check true "case 2 records core:true" || check false "case 2 records core:true"
grep -q "^core_basis: Allison: this is foundational" "$D2/README.md" && check true "case 2 core_basis is Allison's own words, not a guess" || check false "case 2 core_basis is Allison's own words"

echo "== Case 3: YouTube transcript, personal development =="
OUT3="$TMPDIR_TEST/case3"
python3 "$SCAFFOLD" \
  --title "Building Unshakeable Confidence (synthetic)" --creator "Fictional Creator B" \
  --source-type youtube-transcript --domain personal-development \
  --provenance "Synthetic fixture standing in for a YouTube transcript" \
  --original-location "https://youtube.com/watch?v=SYNTHETIC000" \
  --date 2026-02-01 --ownership third-party \
  --destination "PLANNED: ExpertPartners/external-methodologies (not yet created)" \
  --binary linked --binary-location "https://youtube.com/watch?v=SYNTHETIC000" \
  --out "$OUT3" >/dev/null
D3="$OUT3/personal-development/fictional-creator-b/building-unshakeable-confidence-synthetic"
grep -q "^domain: personal-development$" "$D3/README.md" && check true "case 3 routes to personal-development domain" || check false "case 3 routes to personal-development domain"
grep -q "Machine-readable transcript" "$D3/source-record.md" && check true "case 3 gets a timestamp-aware transcript section" || check false "case 3 gets a timestamp-aware transcript section"

echo "== Case 4 (protocol text): deep research routes to research-intake, not brand canon =="
grep -qi "hand off to the .research-intake. skill" "$SKILL_DIR/reference/protocol.md" && check true "case 4 protocol instructs handoff to research-intake for unruled research" || check false "case 4 protocol instructs handoff to research-intake"
grep -qi "do not build a source dossier for it here" "$SKILL_DIR/reference/protocol.md" && check true "case 4 protocol explicitly avoids duplicating research-intake's job" || check false "case 4 protocol avoids duplicate filing"

echo "== Case 5 (protocol text): ruled doctrine routes downstream with lineage =="
grep -qi "Authority Engine doctrine" "$SKILL_DIR/reference/protocol.md" && check true "case 5 protocol names the ruled-into-doctrine example" || check false "case 5 protocol names the ruled-into-doctrine example"
grep -qi "carrying lineage back to the original report" "$SKILL_DIR/reference/protocol.md" && check true "case 5 protocol requires lineage back to the source" || check false "case 5 protocol requires lineage back to source"

echo "== Case 6 (protocol text): bare 'add this to GitHub' is an encoded trigger =="
grep -q '"add this to GitHub"' "$SKILL_DIR/SKILL.md" && check true "case 6 'add this to GitHub' is a literal encoded trigger" || check false "case 6 trigger phrase encoded"

echo "== Case 7: advisory surface, dry-run never writes =="
OUT7="$TMPDIR_TEST/case7"
python3 "$SCAFFOLD" \
  --title "Dry Run Source" --creator "Nobody" --source-type pasted-text \
  --domain marketing --provenance "test" --original-location "test" \
  --date 2026-01-01 --ownership unclear --destination "test" --binary not-applicable \
  --out "$OUT7" --dry-run >/tmp/case7-dryrun-stdout.txt
[ ! -d "$OUT7" ] && check true "case 7 dry-run creates no directory (advisory mode never fakes a write)" || check false "case 7 dry-run creates no directory"
grep -q '"target"' /tmp/case7-dryrun-stdout.txt && check true "case 7 dry-run still reports the planned target" || check false "case 7 dry-run reports planned target"

echo "== Case 8: write-capable surface builds a validated package in a synthetic location =="
[ -f "$D1/README.md" ] && [ -f "$D3/README.md" ] && check true "case 8 write-capable mode proven by cases 1 and 3 landing real files under a synthetic TMPDIR, never a production path" || check false "case 8 write path proof"

echo "== Cross-surface: ChatGPT package generation (real script, real zip) =="
CHATGPT_ZIP="$TMPDIR_TEST/source-ingestion-chatgpt.zip"
"$DEPLOY" source-ingestion --chatgpt-zip "$CHATGPT_ZIP" >/tmp/chatgpt-deploy-stdout.txt 2>&1 || cat /tmp/chatgpt-deploy-stdout.txt
[ -f "$CHATGPT_ZIP" ] && check true "chatgpt-zip artifact created" || check false "chatgpt-zip artifact created"
UNZIP_DIR="$TMPDIR_TEST/chatgpt-unzipped"
mkdir -p "$UNZIP_DIR"
unzip -q "$CHATGPT_ZIP" -d "$UNZIP_DIR"
[ -f "$UNZIP_DIR/source-ingestion/SKILL.md" ] && check true "chatgpt package has SKILL.md at its root" || check false "chatgpt package has SKILL.md"
[ -f "$UNZIP_DIR/source-ingestion/agents/openai.yaml" ] && check true "chatgpt package has agents/openai.yaml" || check false "chatgpt package has agents/openai.yaml"
KEYCOUNT=$(python3 -c "
import re
text = open('$UNZIP_DIR/source-ingestion/SKILL.md', encoding='utf-8').read()
front = re.match(r'^---\n(.*?\n)---\n', text, re.S).group(1)
keys = [l.split(':',1)[0] for l in front.split(chr(10)) if l and not l.startswith(' ')]
print(len(keys))
")
[ "$KEYCOUNT" = "2" ] && check true "chatgpt SKILL.md frontmatter has exactly 2 top-level keys (name, description)" || check false "chatgpt SKILL.md frontmatter key count is 2 (got $KEYCOUNT)"
[ -f "$UNZIP_DIR/source-ingestion/reference/protocol.md" ] && check true "chatgpt package carries the same canonical reference/protocol.md through unchanged" || check false "chatgpt package carries reference/ through"
diff -q "$UNZIP_DIR/source-ingestion/reference/protocol.md" "$SKILL_DIR/reference/protocol.md" >/dev/null && check true "chatgpt package's protocol.md is byte-identical to canonical (never re-authored per surface)" || check false "chatgpt protocol.md byte-identical to canonical"

echo ""
echo "== Results: $PASS passed, $FAIL failed =="
[ "$FAIL" -eq 0 ]
