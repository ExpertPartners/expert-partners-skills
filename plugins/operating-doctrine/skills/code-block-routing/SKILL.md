---
name: "code-block-routing"
description: "Fires on Claude Code paste blocks and implementation briefs for Allison. Requires a routing line naming the destination surface, WORKTREE and MODEL AND EFFORT lines on any block that spawns a Code session (missing either, the block bounces home), a waiting-on statement per hand-off, a Job Tracker row at dispatch and carry-back, one block per response, nothing fenced but terminal or Code, versions read from canonical, the pin only after Allison confirms the paste, and an earned archive verdict on every carry-back."
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
tier: plugin
zone: routing
status: live
inherits: operating-doctrine
defers-to:
  - pin
brand-scope: null
subtitle: "paste block routing and the Job Tracker"
---

# Code Block Routing

<!-- RULED-BY: aura/decisions/0107-retire-routing-naming-ceremony.md date:2026-10-12 superseded naming text removed -->

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


## Dispatch Dedupe: Read The Job Tracker For A Standing Owner First

Ruled by Allison 2026-08-07; born the night of 2026-08-06 when one ordered dispatch reached two lanes from two governing conversations and neither knew of the other. Door Tools Build and the Estate Brain Write Tools lane's Ledger Guard Build both built a working ledger tool. The second lane caught the collision at deploy pre-flight, when the live image and origin/main both already carried `update_lane_row`, and dropped its duplicate unmerged. Nothing was overwritten, and that was luck plus one careful pre-flight, not design. The duplicate was invisible until pre-flight because the second lane's worktree was cut from a stale remote ref.

Before dispatching ANY build, the dispatcher reads the running rows of the Job Tracker (Google Sheet `1FniEwCaZ89cViQxUcPkycxAmvvM47cnjRzQQyzpEk5c`) for a standing owner of that tool class. Not that exact tool, that tool CLASS: door tools, ledger writers, CI watchers, board publishers, brain readers, and so on. A lane already holding the class is its owner.

The three outcomes, and there is no fourth:

1. A standing owner exists and is active. Route the work to that lane as an existing session. Do not open a second lane on the same class.
2. A standing owner exists but is complete or archived. Say so on the routing line, name the row, and dispatch fresh. The prior lane's record is the new lane's inherited state.
3. No owner exists. Dispatch fresh and write the row at dispatch, which is what makes the next dispatcher's read work. A dispatch that skips its row is what causes the next collision.

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
4. Serializing is a legitimate answer when the work genuinely cannot split, and it is stated, never assumed: the dispatch replaces the `WORKTREE` line with an explicit serialization statement naming the order, and the second lane's row records that it waits on the first. Silence is never serialization.
5. The worktree is named in the job's Job Tracker row at dispatch, so the next dispatcher can see which trees are occupied.
6. This rule binds the dispatcher AND the dispatched session. The dispatcher ships the line; the session enforces it by bouncing a spawning block that lacks one, and confirms its tree's absolute path before touching anything else.
7. Continuation blocks routed to an EXISTING session inherit that session's established worktree and need not restate it. A pre-rule session with no isolated tree that receives new work isolates itself at that point and says so in its carry-back.

## The Model And Effort Line: Every Spawning Dispatch Names What To Click

Ruled by Allison 2026-08-10, same enforcement shape as Worktree Isolation above: a rule that exists but is not enforced at the dispatch chokepoint is a rule nobody can rely on.

**Every dispatch block that spawns a NEW Claude Code session carries a `MODEL AND EFFORT` line, naming exactly what to select in the Claude Code model and effort picker before the block below it is pasted.** Unconditional. **A dispatch block that spawns a Code session and arrives WITHOUT a `MODEL AND EFFORT` line is malformed and bounces home, same as a block missing its `WORKTREE` line.** The receiving session does not execute it; it replies naming what is missing so the dispatcher reships the block whole.

The line's content is not this skill's to derive. It comes from the session-model-advisor skill's existing Step 3 (fetch ADR 0057 live) and Step 4 (classify the task), run against the JOB THIS DISPATCH HANDS OFF rather than against the session drafting the dispatch. **This skill carries no copy of that logic and no copy of ADR 0057's decision matrix.** If either turns up duplicated here, that is a doctrine violation, delete it and re-point to session-model-advisor.

Format, riding with the other envelope lines, above the fence:

RUN THIS SESSION AT: <model>, effort <level>

Name the level in ADR 0057's own vocabulary (`low`, `medium`, `high`, `xhigh`, `max`), verified fresh against current Claude Code documentation every time the line is written, never carried over from an earlier verification the same day. Which levels exist, and what each one means, is exactly the kind of vendor fact the doc-check standard exists to keep from going stale in a skill file.

**When a level has grown a same-looking UI sibling, name both and say which one to actually click.** Worked example, verified live 2026-08-10 against code.claude.com/docs/en/model-config: Claude Code's `/effort` picker grew an entry sitting at the strong end of the slider next to `max` for a Claude Code SETTING, not a separate or higher effort level. It sends `xhigh` plus gives Claude standing permission to orchestrate dynamic multi-agent workflows for substantive tasks, and it does not persist to `effortLevel` in settings.json the way `low`/`medium`/`high`/`xhigh` do. **Never spell that setting's name bare and contiguous in this file, in a dispatch block, or in any prose a session will read as a live prompt.** Live-confirmed 2026-08-10 (this lane's own incident, recorded in its ledger row): the bare word, typed anywhere in a message a Claude Code session receives, including inside a quoted worked example describing it, is read by the harness as the literal activation keyword and fires the real behavior, not merely describes it. Write it broken (`Ultra-code`) and point to code.claude.com/docs/en/workflows for the exact canonical spelling when someone actually needs to type it. A dispatch that means `xhigh` writes `xhigh`. A dispatch that means the orchestration behavior names it by its broken spelling, never lets the two get read as interchangeable just because they sit next to each other on the same picker, and never risks firing it by accident.

## The Hand-Off Choreography: Pin Fires AFTER the Paste Confirmation

Corrected 2026-07-28 after a live miss (the pin was fired alongside the block instead of after Allison's confirmation). This section now matches the operating-doctrine pin rule exactly; if they ever seem to disagree, the operating-doctrine pin rule wins.

The order, every hand-off, every session, every project:

1. The hand-off response carries: the routing line, the paste block, and one plain-prose sentence naming what we will be waiting for once she pastes. It does NOT solicit a paste confirmation (pin v4.2, ruled 2026-08-03: nothing ever asks her to say pasted). NO pin yet.
2. Allison pastes and, if she chooses, volunteers a confirmation (pasted, done, OK, or similar). If she says nothing, no pin fires and that is correct.
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
**SAFE TO ARCHIVE is a verified claim, never a phrase.** Issued only after all FOUR verify live in the same turn: `git status` clean and pushed on every repo the session touched; the session record, wrap, or closeout note written and pushed when doctrine requires one; every open wait re-lodged in the lane ledger's waiting-on column with its named condition and stale date, so nothing dies with the archive; and, added 2026-09-03 (ruling of record aura intake/2026-09-01-ruling-table-and-worker-lifecycle-terminality.md, delivered in session-steward v1.3 section 7A), **no monitor, check-in, subscription, scheduled wakeup, or background agent the session owns is still running**, each one released and confirmed released rather than assumed finished. The evidence rides in the line itself, and background activity is stated explicitly as NONE, never implied by omission. A worker that cannot stop something it owns names it and earns NOT safe to archive instead. Anything it does not own, an estate rail or another lane's work, is left running and said so.

**NOT safe means the session diagnoses AND prescribes.** It names exactly what is open and the single move that closes it: /session-wrap when chat-only decisions or flags are unrecorded, /session-closeout when shipped work has no handoff note on main, or the named open action otherwise. Never leave Allison to work out which close a session needs.

**What stays with the home conversation:** the archive click itself, and the Job Tracker flip. Home may still verify a verdict's claims against commits, and a hold still names its next block ("hold it open just in case" is not a call; it is a lane leaking). When home archives, it flips that job's row to `archived` in the Job Tracker BEFORE dispatching anything further, and no dispatch block is ever written against a session whose row reads `archived`; that lane is gone, spawn a new one.

**Default is archive.** Sessions are cheap, so spawn freely rather than hoarding a session because it might be useful later. A stale open lane is not free, and the verdict rule exists precisely so stale open lanes stop accumulating.

Sessions born before this re-ruling follow it from their next response. No cold sweep, no retroactive rewriting of past carry-backs.

Precedence: where this and any older SESSION STATUS wording disagree (the pin skill's carry-back template, the user-global close-of-turn rule, `behavior-defaults.md`), this re-ruling wins and the older wording is corrected to match. All three were corrected in the same pass on 2026-08-07 evening (pin v4.5, behavior-defaults, user-global CLAUDE.md, doctrine repo cf5d97e).

### The Earned Verdict Line

<!-- RULED-BY: aura/intake/2026-08-07-ruling-earned-verdict-line-on-carry-backs.md date:2026-08-07 -->

Amended by Allison 2026-08-07 (Aura / Code Rule Fix lane). This amends the archive-verdict re-ruling above; it does not replace it. **Every Code session carry-back ends with the standing SESSION STATUS line PLUS one earned verdict line, and the verdict line is the carry-back's last line.** Exactly two verdicts exist:

- `VERDICT: RECOMMEND ARCHIVE -- all pushed, nothing pending on Allison's side.` Permitted ONLY when the session verifies its checklist live in the same turn: every commit pushed, the whole brief executed, nothing gated or held open, no deliverable still owed. A bare safe-to-archive with no checklist behind it stays banned.
- `VERDICT: RECOMMEND HOLD OPEN, waiting on <the one named thing>.` The verdict every other state earns. One named thing, never a list; if several things are open, name the one that unblocks the rest.

Archive authority stays with the home conversation and home's GitHub grading remains the backstop, but Allison may archive on the spot on a RECOMMEND ARCHIVE without waiting for home. The verdict line is earned, never decorative: RECOMMEND ARCHIVE with an unverified checklist is the same failure the SAFE TO ARCHIVE evidence rule exists to prevent, stated at the moment Allison actually makes the call.

### BUILD BLOCKERS and OUTCOME BLOCKERS: Two Lines, Never One

Amended 2026-08-30, ruled by Allison; ruling of record: aura decisions/0083-sequencing-without-maximalism-amendment-to-decision-0075.md (an explicit amendment to decision 0075); advisory of record aura intake/2026-08-30-sequencing-without-maximalism-corrected-final-advisory-super.md.

Every carry-back reports BUILD BLOCKERS and OUTCOME BLOCKERS as two separate lines, riding immediately before the SESSION STATUS line. No surface ever reports a single BLOCKING line, and every disposition or completion list that would have carried one carries the BUILD and OUTCOME pair instead. "None" is a valid value and is stated explicitly, never implied by omission.

- BUILD BLOCKERS prevent the implementation from being built. They are owned by the active worker.
- OUTCOME BLOCKERS prevent Allison's stated result from functioning end to end, or prevent required acceptance proof, blocking mission completion even when the build is finished. Safe, bounded, reversible, clearly-owned fixes required for the current outcome are handled in place; fixes that materially change architecture, authority, security, cost, or system-of-record ownership go to Allison before implementation.

The worker's verdict speaks only to its own surface-specific job, never to the home table's objective. A worker closes when its job is finished and successor work is durably handed off; whether the home table's mission is achieved is judged only by the home table's own closeout (the session-wrap close-or-continue verdict), never imported from a worker's verdict. A worker carry-back that pronounces on the home objective is malformed on that line, exactly as a table verdict spoken in worker vocabulary is void under decision 0075.

## The Job Tracker: Row At Dispatch, Update At Carry-Back

The Job Tracker (Google Sheet `1FniEwCaZ89cViQxUcPkycxAmvvM47cnjRzQQyzpEk5c`) in Company Core [HQ-BB], HQ Business Brain, is the one place that answers "what Claude Code sessions exist, what does each belong to, and what is each waiting on" from any surface (Drive connector, Sheets connector). One row per running job; columns Job, Room or lane, Who is doing it, Status, Waiting on, Next step, Opened, Last updated. It replaces the aura lane ledger (Decision Log 2026-10-13). Where this skill says lane ledger or ledger, read Job Tracker.

The habit, every hand-off:

1. At dispatch, when a paste block is handed to Allison, the issuing block-writer adds or updates the job's row: a short label in Job, the return home (Claude project / conversation) in Room or lane, and in Who is doing it the worker, machine, stable session id when known, and the worktree named in the dispatch (per Worktree Isolation above, so the next dispatcher can see which trees are occupied), then Status, Waiting on, Next step, Opened, Last updated. The waiting-on statement this skill already requires with every hand-off is the same text that goes in the row, written once. A dispatch that creates a CLOUD worker records the owning room and available stable identifier in the row at creation time, unconditionally: cloud sessions are invisible to local Desktop session lists, so an unregistered cloud worker is unrecoverable later.
2. At carry-back receipt, the row updates to the new status (running / waiting-on-Allison / waiting-on-carry-back / archived / owned-elsewhere). `complete-safe-to-archive` is retired; only the home conversation writes `archived`, as one motion with its archive call.
3. Append and update rows, never delete. Finished jobs stay in the sheet with a terminal Status rather than vanishing, so the archive decision stays visible.
4. Rule 5 applies: rows are only as certain as their evidence. A lane whose home nobody has named stays needs-Allison; never invent a home for it.

A Code session that completes its carry-back updates its own row to `waiting-on-carry-back`, with the full report, in the same turn when it can write the sheet through the Google Sheets connector; otherwise the home updates it on receipt (root CLAUDE.md delivery protocol). It never writes `archived` into its own row: that is the home conversation's call and the home conversation's write.

<!-- RULED-BY: aura/intake/2026-09-01-ruling-table-and-worker-lifecycle-terminality.md date:2026-09-01 -->
**The archive and the flip are one motion, added 2026-09-03** (ruling of record aura intake/2026-09-01-ruling-table-and-worker-lifecycle-terminality.md, on live evidence that finished workers stayed machine-visible as `waiting-on-carry-back`, one of them after Allison had physically archived the session). Home does not archive and then flip the row later; the flip completes the same close. A carry-back recommending archive says plainly that its row still reads its pre-archive status and will be flipped with the click, so the owed write is visible rather than assumed. **A row that keeps advertising an active wait for a worker known to be finished is a lie the ledger is telling**, and it is reconciled on proven evidence at the next touch of that lane under session-steward v1.3 section 7, never by a sweeper and never by leaving it for Allison to spot.

Write mechanics: update only this job's row in place through the Google Sheets connector. Read the sheet immediately before writing, never clear or rewrite other rows, and re-read after to confirm no other row changed. If the write fails twice, stop and route the row verbatim in the carry-back for home to enter.

## One Block Per Response

Added 2026-07-27 at Allison's instruction: "I can't have you giving me two at a time."

Exactly one paste block per response. Never two, never a "then once that lands" second block, never a block plus a queued follow-up block. (The pin marker is a bookmark, not a block, and does not count.)

If the work needs several steps, ship step one only, wait for the result, then ship step two. Sequencing dependencies are the assistant's job to hold, not Allison's job to keep straight while scrolling.

Prose describing what comes later is fine and brief. A second fenced paste block is not.

One named exception, added 2026-08-07 with the staged-kickoff ruling: a session wrap's staged kickoff set (session-wrap skill v1.3, step 4). Those blocks are a menu Allison draws from at her own tempo, not a sequence of dependent steps, and the dependency-sequencing burden this rule protects her from does not exist among them. Every block in the set still carries its own destination label outside the fence. This is the only exception; it does not generalize to "several unrelated blocks are fine," and it never applies outside a wrap.

## What May Never Go Inside A Code Fence

Added 2026-07-27 after a live failure: a connector URL was placed in a code fence and Allison pasted it into a terminal, where zsh threw "no such file or directory."

In this workflow a code fence carries one meaning to Allison: paste this into Claude Code or a terminal. The only exception is the pin marker defined above. Nothing else may be fenced.

Never fence:

- URLs meant for a browser (connector endpoints, dashboards, sign-in links, docs)
- Values meant to be typed into a settings field or a web form
- Anything destined for 1Password, claude.ai settings, an admin panel, or any GUI

Write those inline in prose with the destination named first, for example: add it in claude.ai, Settings, Connectors, Add custom connector, using mcp.firecrawl.dev/v2/mcp-oauth

Fence only what a terminal or a Claude Code session will actually consume, plus the pin marker. If it is not going into a shell or a Code session and it is not a pin, it does not get a fence.

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
