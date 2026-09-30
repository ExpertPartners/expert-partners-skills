---
name: canon-sync-protocol
description: "Fires automatically, 100 percent of the time, the moment any canon doc (Docs 00-13), doctrine rule, operating rule, Claude project rule, or rule-encoding skill is created, changed, approved, or promoted, even if nobody says sync. Claude initiates the full sync without being asked and drives every surface to the edge of what it can do itself. Canon docs route to Drive (source of truth, Allison-gated promotion), Claude project knowledge, and the partnersync repo via a Canon Doc Sync dispatch; the Team GPT surface is paused at Allison's direction. Rule-encoding SKILL changes route to the two skill shelves, the organization skills shelf and the operating-doctrine plugin shelf, through the deploy pipeline and the Both Shelves rule in code-block-routing. Noticing is the trigger, never being asked. Non-negotiable. It inherits the operating-doctrine and never overrides it."
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
# Adopted into canonical 2026-08-07 (Aura - Code Rule Fix - Both Shelves Rule lane).
# Ruling of record: aura intake/2026-08-08-ruling-canon-sync-protocol-repo-home-and-shelf-surfaces.md (2f70ea0).
# Before this adoption the skill existed ONLY as a claude.ai user-scope copy with no repo home,
# so no Code session could maintain it. That copy is a DEPLOYED COPY of this source from now on.
tier: organization
zone: routing
status: live
inherits: operating-doctrine
subtitle: "canon and rule changes reach every surface, automatically"
---

# Canon Sync Protocol -- v1.2 (2026-09-24, PROPOSED, unmerged until Allison rules it)

Rule authored by Allison, 2026-07-28. Her words: this is the Ten Commandments. Any time a canon doc or a rule changes anywhere, the sync happens automatically, 100 percent of the time, and Claude initiates it. Allison never has to ask, never has to remember, and never discovers a stale copy later.

v1.1 amendment 2026-08-07, ruled YES by Allison, both halves (ruling of record aura intake/2026-08-08-ruling-canon-sync-protocol-repo-home-and-shelf-surfaces.md, commit 2f70ea0). Half one, this skill gets a canonical home in the expert-partners-skills repo like every other rule-bearing skill, and the claude.ai user-scope copy becomes a deployed copy of it. Half two, the surface list gains the two skill shelves. The gap that forced both halves was found by the Both Shelves Rule lane and is worth stating plainly, because it is the exact failure this protocol exists to prevent: the trigger list below has always fired on a rule-encoding skill being created or overwritten, while the surface list named Drive, project knowledge, the partnersync repo, and the paused Team GPT. Not one of those is a skill shelf. The protocol caught skill changes and routed them nowhere.

v1.2 amendment 2026-09-24, PROPOSED by the Skill Lifecycle - Reconciliation Audit worker and not yet ruled. It becomes canon only when Allison rules it with Lock That under aura decisions 0060 and 0061; NORTH reviews and recommends, and a merge alone never rules it. Disclosure of record: expert-partners-skills intake/2026-09-24-disclosure-canon-sync-protocol-v1-2-skill-route-correction.md; evidence: aura intake/2026-09-24-skill-lifecycle-reconciliation/. It proposes to supersede the v1.1 skill route below on three points the live Estate showed on 2026-09-24. One, canonical sources sit in two repos: the skills graph on expert-partners-skills main lists 41 sources here and 16 `aura:` sources (9 live, 1 retired, 6 designed and not yet canonical), and v1.1 named only this repo although the graph already carried those `aura:` sources when v1.1 was committed. Two, the Estate loads skills through five clients (Claude Code, Codex, Claude Chat, Cowork, ChatGPT/NORTH) from thirteen distinct surface keys, and a delivery proven on one key is never evidence for another. Three, a rule-bearing change is complete only when its release receipt passes `tools/skill-deploy/deploy-skill.sh --receipt`. Until Allison rules, the v1.1 shelves remain the operative minimum; this amendment adds surfaces and a completion check and removes none.

## When this fires

The moment ANY of the following happens, this protocol runs, in the same response, without being asked:

- A canon doc (Docs 00 through 13 in the PartnerSync knowledge base) is drafted, amended, approved, or promoted
- A doctrine rule, operating rule, golden rule, or project instruction changes in any Claude project
- A skill that encodes a rule is created or overwritten
- Allison approves a draft that touches any of the above
- Claude notices any copy of canon is out of sync with another, even in passing

Do not wait for Allison to mention GitHub or syncing. Noticing is the trigger. If a change qualifies, the checklist below starts immediately.

## Route by what changed

A change is not done until every surface its ROUTE names is true. Two routes exist and a single change may travel both.

- **Canon docs and project rules** take the canon-doc route, surfaces 1 through 4 below.
- **Rule-encoding skills** take the skill route, surfaces 5 and 6 below.

A rule that lives in a canon doc AND in a skill travels both routes in the same pass. Naming one route and going quiet on the other is the drift this amendment closes.

## The canon-doc route, in order

Every canon doc lives in these places, and Claude drives each step to the edge of what it can do itself before handing Allison the smallest possible action.

1. Google Drive, the source of truth. Canon folder id 1N4bLj6BlDjdn_UCE7YWiUd-RTUAAgJqj. Promotion into Drive is Allison-gated: Claude produces the full replacement document (whole doc, never line-edit instructions), presents it as a file, and gives Allison the exact Drive doc link plus a one-paste instruction (including the doc retitle when the doc is renamed). Claude never asks her to hunt lines. Claude verifies the paste landed by reading the Drive doc live afterward.

2. Claude project knowledge. Check HOW the project holds the doc before instructing anything: if the knowledge file shows a Drive sync badge, the Drive paste already propagates and Allison does NOTHING here; say so explicitly. Only if the copy is a static upload does Allison get a remove-and-reupload step.

3. GitHub, the partnersync repo copy under project-knowledge/. Claude produces the Canon Doc Sync dispatch in the same response as the promotion, automatically, following the code-block-routing skill exactly: routing line above the fence, session name as the first line inside the fence, the WORKTREE line when the block spawns a session, one block per response, waiting-on sentence, and the pin only AFTER Allison confirms the paste. The block tells Claude Code to read the promoted file from the local project folder, replace the repo copy exactly (git mv for renames so history follows), diff, commit with a dated promotion message, push, and report the commit hash. Claude marks this surface green only when the hash comes back.

4. ChatGPT Team GPT: PAUSED at Allison's direction, 2026-07-28. The Team GPT is known-stale and she will refresh it in one batch on her own schedule. Do NOT flag UPDATE TEAM GPT per promotion, do not nag, do not track it as an open item. Reactivate this surface only when Allison says the Team GPT is being refreshed; at that moment, hand her the current canonical file set in one batch.

## The skill route, added 2026-08-07, corrected 2026-09-24 (proposed)

A rule-encoding skill has exactly one canonical source: in expert-partners-skills (`skills/<id>` or `plugins/<plugin>/skills/<id>`), or, for a skill the skills graph marks `aura:`, at exactly the path the graph gives as its `aura:` source. The canonical source is always the first write and it is never skipped, because a surface served from anything other than canonical is a hand-edit by another name. The two shelves below (5 and 6) are the v1.1 minimum and stay in force; the surface table after them is the proposed v1.2 correction, and every key in it is owed or explicitly declined in the release receipt.

5. **The organization skills shelf**, the claude.ai Skills upload. Served by an upload zip containing EXACTLY one top-level folder and EXACTLY one SKILL.md. The deploy pipeline `tools/skill-deploy/deploy-skill.sh <skill> --zip <path>` is the sole producer of that zip for any skill homed under `skills/`. The zip stages to `~/Desktop/Claude Skill Zips` per Rule 0 of the file-delivery rule, and the upload itself stays Allison's hands, because no API path exists for it. Name the exact filename and its Desktop path when reporting this surface.

6. **The plugin shelf**, the operating-doctrine bundle. NEVER an upload. Plugins load from the marketplace git repo `ExpertPartners/expert-partners-skills`, so this surface is served by pushing to `origin/main` and bumping the version in BOTH `plugins/<name>/.claude-plugin/plugin.json` AND the repo-root `.claude-plugin/marketplace.json` entry, then delivering with `claude plugin marketplace update <marketplace>` and `claude plugin update <plugin>@<marketplace>`. Nothing goes on the Desktop for it. Full mechanics, including the blob verification and the `claude plugin validate` check that the two version files agree, live in the code-block-routing skill, "Both Shelves: One Pass Serves Both Mount Surfaces." Where that section and this one ever disagree, that section wins and this one gets corrected to match.

A skill that mounts on only one shelf owes only that shelf, and the report says so plainly rather than leaving Allison waiting for a file that was never coming. A skill that mounts on both owes both in the same pass.

### The surface keys (v1.2, proposed)

Verified on AG-Mac-Mini-M4 on 2026-09-24 (evidence folder above) against code.claude.com/docs/en/skills, support.claude.com/en/articles/12512180-use-skills-in-claude, learn.chatgpt.com/docs/build-skills and learn.chatgpt.com/docs/enterprise/plugin-management, all read the same day. The keys are exactly the thirteen `deploy-skill.sh --receipt-template` prints, and a receipt missing any of them is refused.

| Surface key | Client | What loads there | Delivered by | Observable evidence |
| --- | --- | --- | --- | --- |
| claude-code-user-mount | Claude Code | personal skills at `~/.claude/skills` | `deploy-skill.sh <id> --to ~/.claude/skills` (`--from` for an `aura:` skill) | `--verify` for that copy; `--audit-surfaces` |
| claude-code-project-mount | Claude Code | project skills at `<aura>/.claude/skills`, the canonical home of some `aura:` skills | the canonical itself, or `deploy-skill.sh <id> --to <aura>/.claude/skills` | aura CI deployed-copy-drift; `--audit-surfaces`. A personal skill of the same name wins, so a shadowed project copy never counts as installed |
| claude-code-plugin-cache | Claude Code | `claude plugin` installs from the expert-partners marketplace | push to `origin/main` with the two-file version bump, then `claude plugin marketplace update expert-partners` and `claude plugin update <plugin>@expert-partners` | `claude plugin list`; `--audit-surfaces`. Only the installed, enabled version loads, and a stale local install also stops the org-synced copy of the same plugin from loading, so a local install is either current or removed |
| claudeai-org-plugin-sync | Claude Code | the claude.ai organization plugins downloaded into Claude Code | merged PR carrying a plugin version bump (GitHub sync, ruled 2026-08-07), automatic | `~/.claude/plugins/synced/<org_account>/`; `--audit-surfaces` |
| claudeai-account-skills-sync | Claude Code | the claude.ai account Skills shelf downloaded into Claude Code, namespaced `anthropic-skills:` | `deploy-skill.sh <id> --zip`, staged to `~/Desktop/Claude Skill Zips`, uploaded by Allison at claude.ai Customize > Skills | `~/.claude/skills/synced/<org_account>/manifest.json` and bodies; the ListSkills provider read (names only) |
| codex-user-mount, codex-repo-mount | Codex | user skills at `~/.agents/skills`, repo skills at `<aura>/.agents/skills` | the same producer commands; `--mirror-mount` for aura | Codex app-server `skills/list`; `--audit-surfaces`. Codex does not merge same-name skills, so every copy there loads, and an imported or rewritten copy is drift, never an adaptation |
| codex-plugin-cache | Codex | plugins enabled in `~/.codex/config.toml` | the expert-partners marketplace entry in `config.toml` | Codex app-server `skills/list`; `--audit-surfaces` |
| codex-synced-mirror | Codex | `~/.agents/skills/synced/<org_account>`, a copy of the claude.ai mirror that Codex Desktop's external-agent import sync produces. That sync is the producer, it copies external-agent skill content and rewrites its Claude wording to Codex wording, and as observed through 2026-09-30 it is additive, copying what is missing rather than reliably updating or deleting | nothing; never a release target | `--audit-surfaces`; the receipt records a disposition while any copy there loads |
| claude-chat | Claude Chat | the account Skills shelf and the org plugins | the account-shelf upload or the org plugin sync | no local read; a chat-side check filed as the receipt's evidence |
| cowork-account-skills | Cowork | the account Skills shelf as Cowork caches it for the signed-in org and account (Cowork never reads `~/.claude/skills`) | the account-shelf upload | `local-agent-mode-sessions/skills-plugin/<org>/<account>/`; a Cowork `/skills` read for discovery |
| cowork-org-plugins | Cowork | the org and library plugins as Cowork caches them | the org plugin sync | `local-agent-mode-sessions/<account>/<org>/rpm/`; a Cowork `/skills` read for discovery |
| chatgpt-north | ChatGPT/NORTH | a skill or plugin loaded in the Estate Control Tower chat | observed practice on 2026-09-24: a manual upload through the ChatGPT UI. ChatGPT also documents workspace plugin marketplaces imported from GitHub with daily sync, including a `.claude-plugin/marketplace.json`; whether that applies to the Estate's ChatGPT plan is unverified | NORTH's own reported loaded version, filed as the receipt's evidence |

Plugin-carried skills that still have a standalone copy on the account shelf ride that shelf today and owe it under Both Shelves in code-block-routing. The 2026-08-07 GitHub-sync ruling (aura intake/2026-08-07-ruling-github-sync-adopted-for-skill-deployment.md) retires those standalone copies once the sync is proven live, with Allison's per-item approval; the sync is proven, so their retirement is the proposed disposition, not yet an executed one.

A release receipt (`deploy-skill.sh --receipt-template <id>`, checked by `--receipt <file>`, stored beside the release's checkpoint in the owning repo's intake) records, for each key, whether the surface is intended and why. For an intended key it records the installed, discovered and behavior-tested evidence separately, and the checker climbs CANONICAL, PACKAGED, INSTALLED, DISCOVERED and BEHAVIOR TESTED from that evidence plus a live audit of the local surfaces. The receipt verdict is RELEASE COMPLETE only when every intended key reached BEHAVIOR TESTED. A key not intended where a copy still loads needs a disposition; an inert copy (one that does not load, such as an old cached plugin version) is reported and needs none.

## Sequencing and tracking

- One tiny step at a time, per Allison's delivery protocol. Claude holds the sequence; Allison only ever sees the current step.
- Claude keeps a live checklist of the surfaces for every doc or skill in flight (per Doc 00 Checklist Discipline) and states plainly which surfaces are done and which are open. No canon or rule change is reported as finished while any active surface is stale.
- If a session ends mid-sync, the open surfaces go into the session record and continuity prompt so the next session picks the sync up first.

## The canon-doc dispatch, exact shape

Per the code-block-routing skill: routing line outside the fence, session name first inside the fence, pin after paste confirmation. Canon promotions always route to the session named "Canon Doc Sync" (as an existing session; if Allison reports it does not exist, route as new session with that exact name, which means the block also ships the `claude -n` launch line and a `WORKTREE` line).

PASTE INTO: Claude Code, existing session "Canon Doc Sync"

(fenced block begins)
SESSION: Canon Doc Sync -- self-verify this name against your own custom-title record before executing (pin skill section 5).

Update [Doc XX - Name] in the partnersync repo to match the newly promoted Drive version.
Source file: [local path]
Steps: locate the repo copy under project-knowledge/, verify branch (canon lives on main, stop and report if not on main), replace content exactly, rename with git mv if the doc was retitled, diff and summarize, commit "[Doc XX]: [summary] (promoted from Drive [date])", push, report the commit hash.
(fenced block ends)

Corrected 2026-08-07 in the same pass that adopted this skill into canonical. The skeleton previously carried the retired self-rename instruction, which told the session to ask Allison to paste `/rename Canon Doc Sync`. Sessions are named AT LAUNCH via `claude -n` and self-verify off disk at first contact; `/rename` survives only as the exception repair when self-verification finds a mismatch. Keeping the old skeleton would have shipped a superseded block format out of canonical every time this protocol fired.

## Canonical home and deployed copies

This skill practices ADR 0056 point 8 on itself. The canonical home is `expert-partners-skills skills/canon-sync-protocol/SKILL.md`. The claude.ai user-scope copy is a DEPLOYED COPY of that source as of Allison's ruling of 2026-08-07, and every deployed copy carries the DEPLOYED COPY header naming the canonical home, a version stamp matching the canonical version line, and a SHA-256 checksum manifest. The deploy pipeline `tools/skill-deploy/deploy-skill.sh` is the sole producer of deployed copies and upload zips for skills homed under `skills/`. Hand-editing a deployed copy is a violation; fixes flow through canonical source and redeploy.

## Never

- Never let Allison discover a stale copy. Claude surfaces the gap first.
- Never mark a canon or rule change complete with any active surface unsynced.
- Never produce a canon draft without this protocol attached to its approval.
- Never edit the repo copy first; Drive promotes first, always, on the canon-doc route.
- Never revive the Team GPT flag until Allison reactivates that surface.
- Never route a rule-encoding skill change through the canon-doc surfaces alone. That was the gap this amendment closed, and it is the one failure mode this protocol had built into itself.
- Never hand Allison a plugin bundle zip to upload. That door does not open, and the trip is wasted.
- Never report a rule-bearing skill change complete without a release receipt the checker calls RELEASE COMPLETE, and never let evidence for one surface key stand in for another (proposed v1.2).
- Never produce a surface copy by rewriting canonical text (the Claude-to-Codex substitution found in `~/.agents/skills` on 2026-09-24 is drift, not adaptation); every copy comes from the producer, and a surface that genuinely needs different wording gets a declared adaptation born in canon first (proposed v1.2).
