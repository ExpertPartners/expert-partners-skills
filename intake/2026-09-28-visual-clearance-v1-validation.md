---
classification: internal
classification_owner: allison
classification_date: 2026-09-28
date: 2026-09-28
captured_at: 2026-09-28
project: NORTH'S ESTATE CONTROL TOWER / Luxury Photo Sourcing
source: local executions of this repo's gates and the skill's tests at d10c59b, plus cold-reader behavioral runs
topic: visual-clearance v1 validation receipt and delivery handoff
---
# Visual Clearance v1 validation receipt

SESSION: Luxury Photo Sourcing - Visual Clearance Build
Branch: `claude/visual-clearance-v1-j2w5cq`, fresh base `94c2add`. Implementation commits `c503090` and `d10c59b`.
Skill tree `skills/visual-clearance` at `d10c59b`: git tree `db67592997999856fdf24cda7ac3f8e1e67ce947`, SKILL.md SHA-256 `d869d2abca4f6e7eae9ca466e39729ba728159a465104fd2c5e1a547d0b334e1`.

## Authority read before writing

Live Estate Manifest v1.21 (aura `6a24c50`), ADR 0056 with its 2026-09-22 clarification, ADR 0078, canonical repo-standards v1.6, this repo's README, AGENTS.md, CI and pre-commit gates, `tools/skill-deploy/deploy-skill.sh` and `tools/skill-map/`. Open PRs #6, #9, #18, #39 and #40 were checked by file list; none touches `skills/visual-clearance/` or the new workflow. PR #39 (HOLD) carries an unmerged lifecycle audit tool, so the lifecycle used here is main's. Doc-check: code.claude.com skills page read 2026-09-28 (SKILL.md under 500 lines, supporting files by progressive disclosure); this repo's 1024-character description cap is stricter and governs.

The 2026-09-28 research report (Drive `12GWlfoG8Q_jBclTfaBSFTm_KncAhkO_N`) is used as design evidence only.

## Gates

| Check | Result |
| --- | --- |
| Skill tests (`python3 -m unittest discover -s skills/visual-clearance/tests -p 'test_*.py'`) | PASS, 29 tests |
| Brand lint, changed Markdown | PASS |
| Classification frontmatter lint, changed Markdown | PASS |
| Description cap and fallback selftest | PASS, 42/42 fixtures, visual-clearance 973 characters |
| Ruling provenance, `--ci origin/main HEAD` with local aura | PASS, 24 files, 0 breaches |
| Extractor and layout suite (`npm test`) | PASS, 47/47, after installing the missing `rsync` in this container |
| Deploy contract suite | PASS, 53/53 |
| Graph extraction against aura `6a24c50` | PASS, 58 nodes, 89 edges, strict zone/tier/status, 17 mounts verified; node `visual-clearance` hands / organization / designed |
| Upload preflight `--check-all` | PASS, all 42 skills |
| Upload package build to scratch | PASS, zip sha256 `e1ba0e0a...` at `c503090`, built only as a packaging proof and never uploaded |
| gitleaks 8.30.1, full history | PASS, no leaks |
| Diff whitespace and end-of-file | PASS |

The generated `tools/skill-map/skills-graph.json` was not edited; the skills-graph workflow regenerates it on main after merge.

## Pilots and guards (deterministic)

| Pilot or guard | Observed |
| --- | --- |
| Newman Village | apartments result REJECT on recorded contradiction, stock gate UNVERIFIED and REJECT, zero defensible, route COMMISSION |
| Light Farms | real CC BY-SA 4.0 and source metadata, PROBABLE only; entrance and fitness center fail hero resolution; BY-SA, monument trademark and currency flags; water tower REQUEST PERMISSION; no USE |
| Generic lifestyle | generic stock USE (after recorded review) and LICENSE cards; flipping the request to a named place leaves zero defensible and routes COMMISSION |
| Generated named place | REJECT, grade violation flagged on the claimed VERIFIED |
| Cleared-asset reuse | reusable only for recorded scope; print, other brand, other place, overdue review and failing fit each refuse reuse |
| UNVERIFIED cannot become VERIFIED | claimed grades never exceed recorded evidence; validator refuses weak VERIFIED and relabeled records |
| Attribution never cures | NC, editorial-only and visible-online stay NOT CLEARED with attribution present |
| Insufficient resolution | surfaced as its own flag, reason and card text |
| Zero results | renderer exits 0 with "No defensible candidate found." and a route |
| Sends and spend gated | every decision `auto_executable: false`, draft-only and spending gates present, no network or mail imports in scripts |

## Behavioral runs

Two independent cold readers (one allowed to run the scripts, one instructions-only) answered the ten cases with the rubric withheld. An independent grader scored both 10/10 against `tests/behavioral-rubric.md`. The grader named three contained instruction gaps where prose was looser than the scripts (NEXT precedence for UNVERIFIED with a reachable creator, the empty-route default, borrowing a mismatched fit profile). `d10c59b` closed them and added a guard test; a fresh instructions-only reader of the four affected cases then applied rule 2, the COMMISSION default and a request-scoped profile correctly. A fourth observation, ShareAlike on a cropped website hero, matches the research's stated tolerance and stays flagged on every card. Full responses and grades: `intake/2026-09-28-visual-clearance-v1-behavior-responses.md`.

These are simulated-fixture instruction tests, not live sourcing, clearance or filing.

## Delivery state

Not deployed. No claude.ai organization upload, no Aura deployed copy, no Codex mirror, no marketplace change (standalone skills are not marketplace entries). `status: designed` until a separately authorized delivery pass runs `tools/skill-deploy/deploy-skill.sh` for its named shelves and flips it to `live`. The `ExpertPartners/visual-assets` register this skill reads and files into was not created in this pass; its birth packet is aura `intake/2026-09-28-visual-assets-birth-packet.md`. Until it exists the skill reports the register unreachable and files nothing.
