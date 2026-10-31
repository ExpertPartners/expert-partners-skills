---
name: "code-block-routing"
description: "Routes complete messages between AIs under the current HQ Rulebook. Requires one copy box naming sender, receiver, model and effort or speed; isolated worktrees for spawning code sessions; job_status ownership checks; job_create or job_claim at receipt; and job_finish with a verified summary and result link at completion. Keeps pin timing, approval gates and evidence-based archive readiness."
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
tier: plugin
zone: routing
status: live
inherits: operating-doctrine
defers-to:
  - pin
brand-scope: null
subtitle: "paste block routing and the job list"
---

# Code Block Routing

<!-- RULED-BY: aura/decisions/0107-retire-routing-naming-ceremony.md date:2026-10-12 superseded naming text removed -->

Current authority: the HQ Rulebook section Handoffs between AIs and Decision Log 2026-10-31, The mail system is dissolved everywhere, and the job list stays as the one record. Every AI-to-AI message is one complete copy box with FROM, TO, MODEL and EFFORT/SPEED fields. Allison pastes it into the named chat. Include the whole assignment or reply, not a notice pointing to a separate message record.

Rule authored by Allison, 2026-07-27. Every time a block is handed to Allison to paste into a Claude Code session (intake block, implementation brief, fix instruction, verification request, anything), the block must be preceded by exactly one routing line, outside the code fence.

## The Routing Line Names The Surface, Not Just The Session

Amended 2026-07-28 at Allison's instruction. Naming the surface removes the ambiguity when the same workstream has both a Cowork conversation and a Claude Code session.

Required format:

PASTE INTO: Claude Code

Rules for the routing line:

1. Always name the destination surface.
2. Keep it one line and easy to spot.
3. Continue an existing worker when the actual task context and execution state show it is the same job. Otherwise start a new isolated worker.
4. Identify an existing worker by repo, worktree and branch, durable lane state, and exact scope.
5. An actual execution-scope collision blocks.


## Dispatch Dedupe: Check job_status For A Standing Owner First

Ruled by Allison 2026-08-07; born the night of 2026-08-06 when one ordered dispatch reached two lanes from two governing conversations and neither knew of the other. Door Tools Build and the Estate Brain Write Tools lane's Ledger Guard Build both built a working ledger tool. The second lane caught the collision at deploy pre-flight, when the live image and origin/main both already carried `update_lane_row`, and dropped its duplicate unmerged. Nothing was overwritten, and that was luck plus one careful pre-flight, not design. The duplicate was invisible until pre-flight because the second lane's worktree was cut from a stale remote ref.

Before dispatching ANY build, the dispatcher checks running work through job_status for a standing owner of that tool class. Not that exact tool, that tool CLASS: door tools, ledger writers, CI watchers, board publishers, brain readers, and so on. A lane already holding the class is its owner.

The three outcomes, and there is no fourth:

1. A standing owner exists and is active. Route the work to that lane as an existing session. Do not open a second lane on the same class.
2. A standing owner exists but is complete or archived. Say so on the routing line, name the prior job, and dispatch fresh. The prior lane's record is the new lane's inherited state.
3. No owner exists. Dispatch fresh. The receiving AI uses job_create or job_claim before work, which makes the next dispatcher's ownership check work. Do not create a duplicate job.

Two hard riders. Every dispatched build cuts its worktree from a freshly fetched remote ref, never from whatever the local clone happens to hold, because a stale base hides an existing implementation until pre-flight. And every build runs a pre-flight that checks the live artifact and origin/main for the thing it is about to build; finding it already there is a successful pre-flight, and the correct move is to drop the duplicate unmerged and report, exactly as the second lane did.

This rule is Rule 8 of the routing line extended from shared state to shared PURPOSE. Rule 8 stops two sessions from touching one file. This stops two sessions from building one tool.

## Worktree Isolation: Every Spawning Dispatch Names Its Worktree

First ruled by Allison 2026-08-07 as decision 9d of the Estate Brain Door Phase B record, after the 2026-08-04 incident where two sessions sharing one working tree reset each other's uncommitted edits mid-job. Uncommitted work has no undo, so this is data loss, not inconvenience.

HARDENED by Allison's ruling of 2026-08-07 afternoon (ruling of record: aura intake/2026-08-07-ruling-dispatch-blocks-must-name-worktrees.md). The rule existed but was not enforced at the dispatch chokepoint, and the Phase B session alone logged three collisions: a ledger edit that landed under a sibling's commit, a multi-branch git pull failure, and the Door Tools Build lane losing a full build to a sibling executing the same order. The requirement now lives where the violation is visible at paste time instead of discoverable at collision time.

**Every dispatch block that spawns a Claude Code session carries a `WORKTREE` line naming the isolated worktree the session works in.** Unconditional. Concurrency risk is assumed at dispatch, never assessed away with "they probably will not overlap."

Mechanics:

1. The `WORKTREE` line rides inside the block with the envelope, naming the tree and the branch (one name serves both when they match). The session's FIRST ACT is creating that worktree from a freshly fetched remote ref (`git worktree add ../worktrees/<name> -b <name>`, same fresh-ref rider as dispatch dedupe) and confirming the ABSOLUTE path in its first report. No work happens in the shared main tree.
2. **A dispatch block that spawns a Code session and arrives WITHOUT a `WORKTREE` line is malformed and bounces home, same as a block missing its routing line.** The receiving session does not execute it; it replies naming what is missing so the dispatcher reships the block whole.
3. A session NEVER writes in a repo's main working tree when another lane may hold uncommitted state in it. Check before writing: `git worktree list`, then `git status` in the main tree. Uncommitted changes belonging to someone else mean isolate, always.
4. Serializing is a legitimate answer when the work genuinely cannot split, and it is stated, never assumed: the dispatch replaces the `WORKTREE` line with an explicit serialization statement naming the order, and the second lane's existing job records that it waits on the first. Silence is never serialization.
5. The receiving AI records the worktree in the existing Chat to Code job, so the next dispatcher can see which trees are occupied.
6. This rule binds the dispatcher AND the dispatched session. The dispatcher ships the line; the session enforces it by bouncing a spawning block that lacks one, and confirms its tree's absolute path before touching anything else.
7. Continuation blocks routed to an EXISTING session inherit that session's established worktree and need not restate it. A pre-rule session with no isolated tree that receives new work isolates itself at that point and says so in its carry-back.

## The Model And Effort Line: Every Spawning Dispatch Names What To Click

Ruled by Allison 2026-08-10, same enforcement shape as Worktree Isolation above: a rule that exists but is not enforced at the dispatch chokepoint is a rule nobody can rely on.

**Every dispatch block that spawns a NEW Claude Code session carries a `MODEL AND EFFORT` line, naming exactly what to select in the Claude Code model and effort picker before the block below it is pasted.** Unconditional. **A dispatch block that spawns a Code session and arrives WITHOUT a `MODEL AND EFFORT` line is malformed and bounces home, same as a block missing its `WORKTREE` line.** The receiving session does not execute it; it replies naming what is missing so the dispatcher reships the block whole.

The line's content is not this skill's to derive. It comes from the session-model-advisor skill's existing Step 3 (fetch ADR 0057 live) and Step 4 (classify the task), run against the JOB THIS DISPATCH HANDS OFF rather than against the session drafting the dispatch. **This skill carries no copy of that logic and no copy of ADR 0057's decision matrix.** If either turns up duplicated here, that is a doctrine violation, delete it and re-point to session-model-advisor.

Format, riding inside the one copy box with FROM, TO and the other envelope lines:

RUN THIS SESSION AT: <model>, effort <level>

Name the level in ADR 0057's own vocabulary (`low`, `medium`, `high`, `xhigh`, `max`), verified fresh against current Claude Code documentation every time the line is written, never carried over from an earlier verification the same day. Which levels exist, and what each one means, is exactly the kind of vendor fact the doc-check standard exists to keep from going stale in a skill file.

**When a level has grown a same-looking UI sibling, name both and say which one to actually click.** Worked example, verified live 2026-08-10 against code.claude.com/docs/en/model-config: Claude Code's `/effort` picker grew an entry sitting at the strong end of the slider next to `max` for a Claude Code SETTING, not a separate or higher effort level. It sends `xhigh` plus gives Claude standing permission to orchestrate dynamic multi-agent workflows for substantive tasks, and it does not persist to `effortLevel` in settings.json the way `low`/`medium`/`high`/`xhigh` do. **Never spell that setting's name bare and contiguous in this file, in a dispatch block, or in any prose a session will read as a live prompt.** Live-confirmed 2026-08-10 (this lane's own incident, recorded in its ledger row): the bare word, typed anywhere in a message a Claude Code session receives, including inside a quoted worked example describing it, is read by the harness as the literal activation keyword and fires the real behavior, not merely describes it. Write it broken (`Ultra-code`) and point to code.claude.com/docs/en/workflows for the exact canonical spelling when someone actually needs to type it. A dispatch that means `xhigh` writes `xhigh`. A dispatch that means the orchestration behavior names it by its broken spelling, never lets the two get read as interchangeable just because they sit next to each other on the same picker, and never risks firing it by accident.

## The Hand-Off Choreography: Pin Fires AFTER the Paste Confirmation

Corrected 2026-07-28 after a live miss (the pin was fired alongside the block instead of after Allison's confirmation). This section now matches the operating-doctrine pin rule exactly; if they ever seem to disagree, the operating-doctrine pin rule wins.

For delivery confirmations, follow the current HQ Rulebook section Handoffs between AIs. Confirmation that Allison pasted a message is not a receiving AI's claim or completion receipt.

The order, every hand-off, every session, every project:

1. The hand-off response carries: the routing line, the paste block, and one plain-prose sentence naming what we will be waiting for once she pastes. It does NOT solicit a paste confirmation (pin v4.2, ruled 2026-08-03: nothing ever asks her to say pasted). NO pin yet.
2. Allison pastes and, if she chooses, volunteers a confirmation (the delivery confirmation recognized by the current HQ Rulebook). If she says nothing, no pin fires and that is correct.
3. ONLY THEN the pin fires: the pin marker (pin skill format, fresh real timestamp from TZ=America/Chicago date "+%Y-%m-%d %H:%M %Z", never guessed or reused) plus one sentence restating what we are waiting for and what happens next.

The pin is the bookmark of the moment the baton actually left her hands, which is why it cannot exist before her confirmation.

Precedence notes so the rules do not fight each other:

- The pin marker is a bookmark, not a paste block. It does NOT count against the one-block-per-response rule, and it is exempt from the nothing-fenced-but-Code rule. It is the only other thing that may ever be fenced.
- The pin skill's rule that the marker is the entire response applies only when Allison manually invokes /pin. Confirmation-triggered pins may ride in a response that also continues other work.

## The Session Gives The Archive Verdict

<!-- RULED-BY: aura/intake/2026-08-07-ruling-archive-verdict-returns-to-code-sessions.md date:2026-08-07 -->
<!-- Restores and generalizes a rule Allison first ruled 2026-07-27, struck without disclosure 2026-08-07 morning, and re-ruled the same afternoon: aura/intake/2026-07-27-ruling-code-session-close-includes-safe-to-archive.md date:2026-07-27 status:superseded-and-restored -->

Re-ruled by Allison 2026-08-07 evening in the Estate Brain Door Phase B Code session, superseding the same-date "Archive Authority Belongs To The Home Conversation" ruling. Her reason, recorded: the session must tell her whether it is okay to archive, determine whether something is open, and say whether a closeout or a wrap is needed, because sessions that cannot say whether they are done pile up, and too many open sessions is the real failure.

**`SESSION STATUS: carry-back delivered, awaiting verification at home.` is RETIRED and never written again.** Every carry-back ends with one of the four verdict lines from `behavior-defaults.md`: Waiting on you, Still working, SAFE TO ARCHIVE with evidence, or NOT safe to archive with the one closing move named.

<!-- RULED-BY: aura/intake/2026-09-01-ruling-table-and-worker-lifecycle-terminality.md date:2026-09-01 -->
**SAFE TO ARCHIVE is a verified claim, never a phrase.** Issued only after all FIVE verify live in the same turn: `git status` clean and pushed on every repo the session touched; the session record, wrap, or closeout note written and pushed when doctrine requires one; every open wait preserved in its existing Chat to Code job with its named condition and stale date, so nothing dies with the archive; **the job report is saved through job_finish with a summary and result link and verified through job_status (section The Job Report below)**; and, added 2026-09-03 (ruling of record aura intake/2026-09-01-ruling-table-and-worker-lifecycle-terminality.md, delivered in session-steward v1.3 section 7A), **no monitor, check-in, subscription, scheduled wakeup, or background agent the session owns is still running**, each one released and confirmed released rather than assumed finished. The evidence rides in the line itself, and background activity is stated explicitly as NONE, never implied by omission. A worker that cannot stop something it owns names it and earns NOT safe to archive instead. Anything it does not own, an estate rail or another lane's work, is left running and said so.

**NOT safe means the session diagnoses AND prescribes.** It names exactly what is open and the single move that closes it: /session-wrap when chat-only decisions or flags are unrecorded, /session-closeout when shipped work has no handoff note on main, or the named open action otherwise. Never leave Allison to work out which close a session needs.

**What stays with the home conversation:** acceptance of the returned evidence against its mission. The worker files its own job_finish summary and result link; job_status is the ownership and status view. Follow the current HQ Rulebook section Session lifecycle for archive consent. Do not dispatch more work to an archived session.

**Default is archive.** Sessions are cheap, so spawn freely rather than hoarding a session because it might be useful later. A stale open lane is not free, and the verdict rule exists precisely so stale open lanes stop accumulating.

Sessions born before this re-ruling follow it from their next response. No cold sweep, no retroactive rewriting of past carry-backs.

Precedence: where this and any older SESSION STATUS wording disagree (the pin skill's carry-back template, the user-global close-of-turn rule, `behavior-defaults.md`), this re-ruling wins and the older wording is corrected to match. All three were corrected in the same pass on 2026-08-07 evening (pin v4.5, behavior-defaults, user-global CLAUDE.md, doctrine repo cf5d97e).

### The Earned Verdict Line

<!-- RULED-BY: aura/intake/2026-08-07-ruling-earned-verdict-line-on-carry-backs.md date:2026-08-07 -->

Amended by Allison 2026-08-07 (Aura / Code Rule Fix lane). This amends the archive-verdict re-ruling above; it does not replace it. **Every Code session carry-back ends with the standing SESSION STATUS line PLUS one earned verdict line, and the verdict line is the carry-back's last line.** Exactly two verdicts exist:

- `VERDICT: RECOMMEND ARCHIVE -- all pushed, nothing pending on Allison's side.` Permitted ONLY when the session verifies its checklist live in the same turn: every commit pushed, the whole brief executed, nothing gated or held open, no deliverable still owed. A bare safe-to-archive with no checklist behind it stays banned.
- `VERDICT: RECOMMEND HOLD OPEN, waiting on <the one named thing>.` The verdict every other state earns. One named thing, never a list; if several things are open, name the one that unblocks the rest.

Archive consent follows the current HQ Rulebook section Session lifecycle. Home's GitHub grading remains the backstop, and Allison may still archive on the spot on a RECOMMEND ARCHIVE. The verdict line is earned, never decorative: RECOMMEND ARCHIVE with an unverified checklist is the same failure the SAFE TO ARCHIVE evidence rule exists to prevent, stated at the moment Allison actually makes the call.

### BUILD BLOCKERS and OUTCOME BLOCKERS: Two Lines, Never One

Amended 2026-08-30, ruled by Allison; ruling of record: aura decisions/0083-sequencing-without-maximalism-amendment-to-decision-0075.md (an explicit amendment to decision 0075); advisory of record aura intake/2026-08-30-sequencing-without-maximalism-corrected-final-advisory-super.md.

Every carry-back reports BUILD BLOCKERS and OUTCOME BLOCKERS as two separate lines, riding immediately before the SESSION STATUS line. No surface ever reports a single BLOCKING line, and every disposition or completion list that would have carried one carries the BUILD and OUTCOME pair instead. "None" is a valid value and is stated explicitly, never implied by omission.

- BUILD BLOCKERS prevent the implementation from being built. They are owned by the active worker.
- OUTCOME BLOCKERS prevent Allison's stated result from functioning end to end, or prevent required acceptance proof, blocking mission completion even when the build is finished. Safe, bounded, reversible, clearly-owned fixes required for the current outcome are handled in place; fixes that materially change architecture, authority, security, cost, or system-of-record ownership go to Allison before implementation.

The worker's verdict speaks only to its own surface-specific job, never to the home table's objective. A worker closes when its job is finished and successor work is durably handed off; whether the home table's mission is achieved is judged only by the home table's own closeout (the session-wrap close-or-continue verdict), never imported from a worker's verdict. A worker carry-back that pronounces on the home objective is malformed on that line, exactly as a table verdict spoken in worker vocabulary is void under decision 0075.

## The Job Report: One Work Record

The current rule lives in the HQ Rulebook section Handoffs between AIs. The receiving AI uses job_create or job_claim before starting, retains the existing job identity on continuation, and uses job_finish with the full outcome summary and result link when finished. Code jobs travel as a GitHub issue labeled job. Check job_status before dispatch to avoid duplicate ownership and after completion to verify the saved report.

Record the actual worker, repository/worktree/branch, return destination, evidence, and any named wait in the existing job. Never create a second spreadsheet record. The return message follows the same complete copy-box envelope as the assignment. A copy box alone is not a saved job report.

If a job write fails, inspect job_status before retrying an uncertain write. If the report remains unverified, keep the reporting obligation open and name the failed action. Follow the current HQ Rulebook section Session lifecycle for archive readiness and consent. Session-steward checks job_inbox for work awaiting an owner and reports gaps from job evidence, not message receipts.

## One Block Per Response

Added 2026-07-27 at Allison's instruction: "I can't have you giving me two at a time."

Exactly one paste block per response. Never two, never a "then once that lands" second block, never a block plus a queued follow-up block. (The pin marker is a bookmark, not a block, and does not count.)

If the work needs several steps, ship step one only, wait for the result, then ship step two. Sequencing dependencies are the assistant's job to hold, not Allison's job to keep straight while scrolling.

Prose describing what comes later is fine and brief. A second fenced paste block is not.

One named exception, added 2026-08-07 with the staged-kickoff ruling: a session wrap's staged kickoff set (session-wrap skill v1.3, step 4). Those blocks are a menu Allison draws from at her own tempo, not a sequence of dependent steps, and the dependency-sequencing burden this rule protects her from does not exist among them. Every block in the set still carries its own destination label outside the fence. This is the only exception; it does not generalize to "several unrelated blocks are fine," and it never applies outside a wrap.

## What May Never Go Inside A Code Fence

Added 2026-07-27 after a live failure: a connector URL was placed in a code fence and Allison pasted it into a terminal, where zsh threw "no such file or directory."

In this workflow a code fence carries terminal input or a complete message for the AI chat named by the routing line. The pin marker defined above remains a bookmark, not a work message.

Never fence:

- URLs meant for a browser (connector endpoints, dashboards, sign-in links, docs)
- Values meant to be typed into a settings field or a web form
- Anything destined for 1Password, claude.ai settings, an admin panel, or any GUI

Write those inline in prose with the destination named first, for example: add it in claude.ai, Settings, Connectors, Add custom connector, using mcp.firecrawl.dev/v2/mcp-oauth

Fence only what a terminal or the named AI chat will actually consume, plus the pin marker. If it is not going into a shell or an AI chat and it is not a pin, it does not get a fence.

## Reading Versions From The Right Place

Added 2026-07-27 after a live failure: a doctrine version bump was specified as v2.1 based on a plugin cache mirror reading v2.0, when canonical was already at v2.2 and the correct bump was v2.3.

Never state or prescribe a version number from a plugin cache, a loaded skill copy, or any mirror. Those lag canonical. Read canonical in the repo, or have Claude Code read it and report back. If only a mirror was read, say which copy was read and that it may lag.

## Both Shelves: One Pass Serves Both Mount Surfaces

Ruled by Allison 2026-08-07. Several skills ride two mount surfaces at once, a standalone claude.ai skill copy and a copy inside the operating-doctrine plugin bundle. pin, code-block-routing, and lane-spawn all sit on both shelves today. The Deployed Copy Content Check of 2026-08-07 verified the two surfaces byte-identical, and that check is the reason the gap was visible: nothing in canon forced a future pass to serve both, so one single-shelf delivery would have opened silent drift between two copies Allison believes are the same rule.

**Any pass that touches a skill carried by the operating-doctrine plugin serves BOTH mount surfaces in that same pass.** A pass that serves one and mentions the other is not finished; it is a drift event with a note attached.

**The two shelves do not load the same way, and treating them as one delivery is the mistake this section was born correcting.** Corrected the same evening it was written, after the first delivery under it failed live: a plugin bundle zip was handed to Allison for the claude.ai Skills upload and was rejected with "Zip must contain exactly one top-level folder. Currently there are 2" and "Zip must contain exactly one SKILL.md file. Currently there are 8." The rejection was correct product behavior, not a build defect. Verified live 2026-08-07 against support.claude.com (how to create custom skills) and code.claude.com/docs/en/plugins plus /docs/en/discover-plugins.

**Shelf one, the standalone claude.ai skill. This one IS a zip upload.** The upload requires EXACTLY one top-level folder and EXACTLY one SKILL.md inside it. Build `<skill-name>/SKILL.md` and nothing else at the top level. It lands in `~/Desktop/Claude Skill Zips` per Rule 0 of `rules/file-delivery.md`, and Allison uploads it by hand because no API path exists for it.

**Shelf two, the plugin bundle. This one is NEVER a zip upload.** Plugins load from a marketplace git repository, not from an upload dialog; there is no claude.ai screen that accepts a plugin bundle zip, and a bundle can never satisfy the one-folder one-SKILL.md rule the Skills upload enforces. The estate's marketplace is the `expert-partners` entry pointing at the GitHub repo `ExpertPartners/expert-partners-skills`. Delivering this shelf means pushing to `origin/main` and bumping the version so the marketplace serves the update. Nothing goes on the Desktop for it, and handing Allison a bundle zip to upload is a category error that costs her a failed trip.

Mechanics:

1. **The plugin version bump is TWO files, not one.** `plugins/<plugin-name>/.claude-plugin/plugin.json` AND the matching entry in the repo-root `.claude-plugin/marketplace.json`. Bumping only the manifest leaves the marketplace advertising the old version, so installed copies never see the update and the shelf silently stays stale. Both numbers are read from canonical per Reading Versions From The Right Place above, never from a cache mirror, and they must agree.
2. **Content is blob-verified against `origin/main` before anything is called delivered.** Every SKILL.md hashes with `git hash-object` to the same blob SHA that `git rev-parse origin/main:<path>` reports. Build the standalone zip from `git archive origin/main`, never from a working tree, because a zip of unpushed work is a zip of something that does not exist yet.
3. **The carry-back names what each shelf actually got.** For the standalone shelf, the exact zip filename with its archive SHA and its Desktop path. For the plugin shelf, the commit on `origin/main`, both version numbers, and the fact that no upload is owed. Going quiet on either shelf is the failure this rule exists to remove.
4. The rule keys on the plugin's carrying, not on how the pass started. A pass that set out to touch only the standalone copy still owes the plugin shelf, because the plugin copy is the one that governs (skill-map standing flag, plugin copy wins).
5. Skills carried by the plugin with no standalone claude.ai copy owe only the plugin shelf, and the carry-back says so plainly rather than leaving Allison hunting for a second file that was never coming.
6. A plugin bundle zip is built ONLY when something actually consumes one: `claude --plugin-dir ./bundle.zip` for local testing, or `--plugin-url` for a hosted archive. Those are development paths. Such a zip never goes to `~/Desktop/Claude Skill Zips`, because that folder means "Allison uploads this" and she cannot.
7. **The two-file bump is VERIFIED, not remembered.** `claude plugin validate <marketplace-repo-root>` checks that every plugin manifest agrees with its enclosing marketplace entry, and `claude plugin tag` validates the same agreement before cutting a release tag. Run the validate before calling the plugin shelf delivered; a mechanical check is what turns mechanic 1 from a thing a pass can forget into a thing a pass cannot ship without.
8. **The plugin shelf is delivered by CLI, never by a hand step.** After the push, `claude plugin marketplace update <marketplace>` refreshes the catalog and `claude plugin update <plugin>@<marketplace>` moves the installed copy to the new version, reporting the exact old-to-new transition. Third-party marketplaces have auto-update OFF by default, so without these two commands an installed copy sits on the old version indefinitely while canonical moves on. Both were live-verified 2026-08-07 on Claude Code 2.1.223, taking operating-doctrine from 2.33.0 to 2.35.0 with no upload and no action from Allison. A session that pushes and stops has updated the catalog, not the shelf.

Precedence: this section is the delivery half of Reading Versions From The Right Place. That rule stops a wrong version from being SPOKEN; this one stops a right version from reaching only one shelf, and stops a right artifact from being sent to a door that does not open.

## Links Are Evidence: Never Construct A URL

Added 2026-08-04 after a live recurrence (Marketing Canon lane: a Code session emitted constructed claude.ai links in its carry-backs, was corrected at gate one, saved the rule to its own session memory, and still emitted constructed links at closeout; session memory is a notebook, this skill is the rulebook, so the rule lives here).

Every carry-back, report, or block that points at a file cites the repo path plus the commit hash, or a URL actually verified to resolve. Never construct a URL by gluing a path onto a guessed address. A session that cannot verify a URL gives the path and hash instead. This rule governs both directions of the hand-off, blocks handed to Allison and carry-backs handed home. The deliverable-link skill's every-deliverable-gets-a-link rule is satisfied by a verified link or by path plus hash, never by an invented one.

Scope widened 2026-08-07 (decision 9c of the Estate Brain Door Phase B record, wording checked against the ruling in the same pass). The rule covers EVERY URL a carry-back carries, not only the ones that point at files. The 2026-08-05 carry-back that forced the check shipped two broken claude.ai links, which were not file pointers at all. A conversation link, a dashboard link, a board link, a doc link, and a file link are all held to the same test: it resolved when you tried it, or it does not ship. Links are evidence, and evidence is the thing you actually looked at.

## The Hand-Step URL Rule: Give Her The Address, Not Directions

Ruled by Allison 2026-08-07; decision 9a of the Estate Brain Door Phase B record (aura intake/2026-08-05-session-record-estate-brain-door-phase-b-lane.md). The live proof: a manifest page a session needed Allison's eyes on sat inside a browser pane for hours, because the session handed over a navigation path instead of an address.

When a session needs Allison's hands on a web page, it hands her the full URL, complete and clickable, for her own browser. Never a navigation path. Never "go to Settings, then Connectors, then scroll to." Never a page left waiting in a Browser pane on the assumption she will find it there. The Browser pane is optional garnish, useful to the session for its own verification, never the delivery mechanism for a step that is hers.

Mechanics:

1. The URL is written inline in prose with the destination named first, never fenced (see What May Never Go Inside A Code Fence). Naming the destination and giving the full address are one act, not alternatives.
2. The URL is verified to resolve before it ships, per Links Are Evidence above. A hand step pointed at a guessed address costs her the trip.
3. Directions may ride ALONGSIDE the URL when the target is a control inside a long page ("open this, then the grant is the third row"). They never ride instead of it.
4. One hand step, one URL, named once. The Ruling Cadence in the operating-doctrine already requires hands-only actions to be named explicitly with the direct URL; this section is that requirement's mechanics.
