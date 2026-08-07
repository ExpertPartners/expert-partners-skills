---
name: "code-block-routing"
description: "Fires on every Claude Code paste block, intake block, or implementation brief for Allison. Requires a routing line naming surface and exact session, the session name first inside the block, a WORKTREE line naming the isolated worktree on every block that spawns a Code session (a spawning block without one is malformed and bounces home), a waiting-on statement per hand-off, a lane ledger row at dispatch and carry-back, one block per response, nothing fenced but terminal or Code, versions from canonical only, the pin only AFTER Allison confirms the paste. Cowork and chat lane identity is the kickoff header line, not the title, so a chat kickoff leads with the conversation name plain and alone, envelope CONVERSATION never SESSION. Code sessions are named at launch via claude -n as Project short name - Conversation name - Job name, self-verified off disk at first contact; the session creates its named worktree from a freshly fetched remote ref and confirms the absolute path in the same first contact. /rename is a Code-only exception repair, never handed to a chat. Every carry-back ends with the archive verdict per the 2026-08-07 evening re-ruling: SAFE TO ARCHIVE with evidence or NOT safe with the one closing move named; awaiting-verification-at-home is retired. The archive click and the ledger flip to archived stay with the home conversation."
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
tier: plugin
zone: routing
status: live
inherits: operating-doctrine
defers-to:
  - pin
brand-scope: null
subtitle: "paste block routing and the lane ledger"
---

# Code Block Routing

Rule authored by Allison, 2026-07-27. Every time a block is handed to Allison to paste into a Claude Code session (intake block, implementation brief, fix instruction, verification request, anything), the block must be preceded by exactly one routing line, outside the code fence.

## The Routing Line Names The Surface, Not Just The Session

Amended 2026-07-28 at Allison's instruction: "always say paste into Claude Code Ember audit, even though it seems obvious, because sometimes the names get off." Naming the surface removes the ambiguity that appears when a session's window title has drifted from its authoritative name, or when the same workstream has both a Cowork conversation and a Claude Code session.

Required format, one of:

PASTE INTO: Claude Code, existing session "Session Name"

PASTE INTO: Claude Code, new session, name it "Short Name"

The surface always appears first and is always spelled Claude Code. Never ship a routing line that names only the session. Never shorten to "paste into Ember audit" or "Routing: ember-audit."

If a block is ever bound for a surface other than Claude Code, that surface is named the same way in the same position (for example, PASTE INTO: Terminal). Blocks bound for a browser, 1Password, or any GUI are not fenced at all; see the fencing rules below.

Rules for the routing line:

1. Always present. No paste block ships without it.
2. One line, first thing above the block, easy to spot.
3. Session names follow the three-segment format in the Session Naming section below (`<Project short name> - <Conversation name> - <Job name>`), readable words throughout. The assistant picks the name and bakes it into the dispatch's `claude -n` launch line; Allison never types it.
4. Route to an EXISTING session when the work continues a thread that session already holds context for (a pending brief, a prior fix, a repo it already has open). Name the session exactly as Allison named it.
5. Route to a NEW session when the work is a fresh workstream, a different repo, or would pollute an existing session's context.
6. Track known session names as they are created or mentioned, and reuse them consistently so both sides always know where a thread lives. Never invent a session name and register it as if it exists. If Allison reveals the real name, adopt her exact spelling immediately and correct the registry.
7. When it is unknown whether a coinciding session exists, say so on the routing line and default to a new session with a name: PASTE INTO: Claude Code, new session, name it "X" (or your existing session for this work if one is open).
8. Never route two concurrent sessions at the same shared state (the same repo, the same credential, the same config file). One lane per workstream. If a second session is already open on that state, say so and route everything to one of them.

## Dispatch Dedupe: Read The Ledger For A Standing Owner First

Ruled by Allison 2026-08-07; born the night of 2026-08-06 when one ordered dispatch reached two lanes from two governing conversations and neither knew of the other. Door Tools Build and the Estate Brain Write Tools lane's Ledger Guard Build both built a working ledger tool. The second lane caught the collision at deploy pre-flight, when the live image and origin/main both already carried `update_lane_row`, and dropped its duplicate unmerged. Nothing was overwritten, and that was luck plus one careful pre-flight, not design. The duplicate was invisible until pre-flight because the second lane's worktree was cut from a stale remote ref.

Before dispatching ANY build, the dispatcher reads the Active lanes table in aura `docs/estate/lanes.md` for a standing owner of that tool class. Not that exact tool, that tool CLASS: door tools, ledger writers, CI watchers, board publishers, brain readers, and so on. A lane already holding the class is its owner.

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
5. The worktree is named in the lane's ledger row at dispatch, so the next dispatcher can see which trees are occupied.
6. This rule binds the dispatcher AND the dispatched session. The dispatcher ships the line; the session enforces it by bouncing a spawning block that lacks one, and confirms its tree's absolute path before touching anything else.
7. Continuation blocks routed to an EXISTING session inherit that session's established worktree and need not restate it. A pre-rule session with no isolated tree that receives new work isolates itself at that point and says so in its carry-back.

## Session Naming: Three Segments, Set At Launch

Ruled by Allison 2026-08-04 ("yes adopt lane tag rule"), ruling of record at aura intake/2026-08-05-ruling-lane-tag-session-naming-rule.md. EXTENDED by Allison's ruling of 2026-08-07: the job-shaped name is extended, not replaced, and the job name is now the third segment.

Every Claude Code session name is three segments joined by space-hyphen-space:

```
<Project short name> - <Conversation name> - <Job name>
```

Project short names lock per project as they arise. `Aura` is the short name for the Claude project "Aura: Strategic Advisor". Readable words throughout, never bare initialisms. The point is unchanged from the 2026-08-04 ruling and now stronger: the Code sessions list identifies each session's lane AND its home on sight, with no ledger lookup.

Examples: `Aura - Code Rule Fix - Rule Rewrite`. `Aura - Repo Walk - Engine Build`. `EPIC - Funnel Audit - Nurture flow reconcile`.

Mechanics:

1. The name is set AT LAUNCH, never after. Every dispatch block for a new session ships the exact launch line with `-n "<full name>"` baked in. `-n, --name` is a real Claude Code flag, live-verified 2026-08-07 on 2.1.223, and it writes the exact string to the session's `custom-title` record on disk.
2. The dispatching lane owns name consistency, and its ledger row in aura docs/estate/lanes.md records the same canonical name.
3. Sessions self-verify at first contact by reading their own `custom-title` off disk and comparing it to the SESSION line in the briefing (recipe in the pin skill, section 5). The session reports the comparison in its first response. No human is in that loop.
4. Existing sessions are NOT cold-renamed. A pre-rule session gains its name the next time it is touched, via the `/rename` exception repair below. Never send Allison window hunting.
5. `/rename` is the exception repair only, fired when self-verification finds a mismatch or the session predates this rule. It is manual by necessity: a session cannot rename itself. Verified on Anthropic's public tracker 2026-08-07, all open: #33165, #83543, #84041, #84587. Hand Allison the exact `/rename` line once, then keep using the authoritative name regardless of what the window shows.

## Window Titles Drift; Session Names Do Not

Added 2026-07-28 after a live incident, and this is still why the parity rule exists. A Claude Code window displayed the title "Atlas bot token cleanup" while the session inside it was authoritatively "ember-audit," which it confirmed by its own envelope check. Allison nearly archived an active worker because of it. Drift is real, it is dangerous, and the cost is a live lane killed by mistake.

Amended 2026-08-07. The 2026-07-28 entry explained the drift by saying Claude Code cannot read or set its own window title. The READ half of that is superseded: a session CAN read its own name, off its own transcript's `custom-title` record (live-verified 2026-08-07 on Claude Code 2.1.223; recipe in the pin skill, section 5). The SET half stands, renaming is manual-only.

What that changes: drift is now DETECTABLE by the session itself, at first contact, with no human in the loop. The old rule waited for someone to notice a mismatch. The new rule catches it in the session's first response.

Consequences:

- The authoritative name is the one in the SESSION line of the block that briefed the session, never the window title.
- Every session self-verifies its own name at first contact and reports the comparison. A mismatch is surfaced immediately, not discovered later.
- When self-verification finds a mismatch, hand Allison the exact `/rename` line once, and keep using the authoritative name regardless of what the window shows.
- Naming at launch (`claude -n "<full name>"`) is the actual fix. Self-verification is the safety net under it, not the primary mechanism. A dispatch that ships the launch line correctly produces a session that never drifts in the first place.
- Never advise archiving or closing a session based on its window title alone. Confirm what work that session still holds first.

## Lane Identity By Surface: Kickoff Header Is Canonical In Cowork

Ruled by Allison 2026-08-03. Cowork and Claude.ai chat titles are auto-generated from conversation content and cannot be set by any session, tool, or API; live-verified 2026-08-03 when the auto-namer paraphrased a first message that opened with the exact intended lane name. Manually renaming Cowork chats to match a convention is retired as of this ruling. Manual renaming was a failure condition; the identity rule moves instead.

The rule by surface:

- Cowork and Claude.ai chat lanes. Canonical identity is the kickoff header line, the first line of the lane's first message. As of Allison's ruling of 2026-08-07 that line is the conversation name, plain and alone, with no label in front of it, no date suffix, and no "kickoff" word (the old "Lane name - YYYY-MM-DD kickoff" format is retired; see Chat Blocks Lead With The Conversation Name below). The block-writer controls that line fully at dispatch, and the lane ledger records the lane name from it. The displayed chat title is cosmetic; it may be logged parenthetically when someone needs to find the window, but it is never flagged for rename and never treated as identity. Chat lanes never get PARITY MISMATCH flags, and Claude never hands Allison a rename instruction for a chat.
- Claude Code sessions. Exact-name parity stays enforced, because this surface supports it, and as of the 2026-08-07 ruling it is enforced at LAUNCH rather than by repair. A dispatch spawning a new session ships the `claude -n "<full name>"` launch line, so the session is born correctly named. The session then self-verifies its own name off disk at first contact and reports the comparison. A PARITY MISMATCH flag on a Code lane means self-verification failed or the lane predates the rule; it resolves by the in-session `/rename` request the next time the session is used (live-verified 2026-07-28 and reconfirmed 2026-08-07, only Allison can type `/rename` into a Code session), never by Allison hunting windows to rename them cold.

## Session Name Goes First Inside The Block

Added 2026-07-28 at Allison's instruction, rewritten 2026-08-07 under the launch-line ruling. This section governs blocks bound for Claude Code. Blocks bound for a chat conversation lead with the conversation name instead and never carry a SESSION line at all; see Chat Blocks Lead With The Conversation Name below.

The first line INSIDE every Claude Code paste block is still the session name, so the pasted prompt identifies its own lane in the transcript. What changed is how the session ends up correctly named: the launch line does it, and the in-block line verifies it.

**For a NEW session, the dispatch ships the launch line above the fence.** Allison runs it, and the session is born named:

```
claude -n "Aura - Code Rule Fix - Rule Rewrite"
```

**Inside the fence, the first line is the SESSION header plus the self-verify instruction.** Exact format:

SESSION: Aura - Code Rule Fix - Rule Rewrite -- self-verify this name against your own custom-title record before executing (pin skill section 5). If it does not match, hand Allison the exact /rename line in your first output, then execute the brief below.

Substitute the actual session name for each block. The routing line above the fence still ships too. Outside the fence Allison reads where to paste; inside the fence the session learns what it is called and proves it.

**For a NEW session the envelope also carries the `WORKTREE` line** (Worktree Isolation above): the isolated tree the session creates from a freshly fetched remote ref and works in, confirmed by absolute path in its first report. A spawning block without one is malformed and bounces home.

Why the self-verify line still ships even though the launch line exists: the harness auto-titles sessions from their first message, so a session launched WITHOUT `-n` (an existing session receiving a dispatch, or a launch line Allison did not use) will carry a generated name. The in-block line is what catches that case. Only Allison can type `/rename` into a Code session, verified 2026-07-28 and reconfirmed against Anthropic's tracker 2026-08-07 (#33165, #83543, #84041, #84587 all open).

## Chat Blocks Lead With The Conversation Name

Ruled by Allison 2026-08-07, same lane as the naming and archive rulings. The section above governs blocks bound for Claude Code. This one governs blocks bound for a chat conversation in the Claude app or Cowork, and the two rules do not overlap at any point.

The live failure that forced it: a lane-spawn block buried the conversation name mid-block and opened with mission text, so the app auto-titled the chat off the mission and the lane was born carrying two names, the one in the ledger and the one Allison could see in her sidebar.

Chat conversation titles cannot be set programmatically. The app auto-titles from the first message and no session, tool, or API can override it (live-verified 2026-08-03, reconfirmed 2026-08-07). The only lever the block-writer has is what the first message says first.

**The first line inside a chat block is the conversation name, plain and alone.** No label, no date suffix, no "kickoff" word, no envelope line above it, no mission text above it. The envelope follows on the next lines. Full block anatomy lives in the lane-spawn skill, "The spawn pair."

**Vocabulary lock.** A chat block heads its envelope `CONVERSATION:`. A Code block heads its envelope `SESSION:`. A chat block carrying a `SESSION:` line is malformed and gets rewritten before it ships. `WORKER SESSION:` inside a chat kickoff is a pointer to the Code lane that will carry back, not the block's own header, and is correct. `CLAUDE HOME:` inside a Code block is the same kind of pointer, and is unchanged.

**Near-match titles are accepted and left alone.** Chat lane identity is the kickoff header line, not the displayed title, so leading with the name is a courtesy to Allison's eyes and not a correctness requirement. A chat titled "Ember Rail Repair Plan" for a lane named "Ember Rail Repair" is fine.

**No rename instruction ever reaches Allison for a chat.** Not `/rename`, not "please retitle this," not a parenthetical suggestion. Manual chat renaming was retired as a failure condition by the 2026-08-03 identity ruling and this rule does not revive it. `/rename` remains a Claude Code repair only. If Allison retitles a conversation herself, her name wins from that point on and the ledger follows her; she is simply never asked to.

Routing line for a chat destination follows the same shape as the Code one, surface first:

PASTE INTO: Claude app, new conversation named "Ember Rail Repair"

PASTE INTO: Cowork, existing conversation "Ember Rail Repair"

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

Re-ruled by Allison 2026-08-07 evening in the Estate Brain Door Phase B Code session, superseding the same-date "Archive Authority Belongs To The Home Conversation" ruling. Her reason, recorded: the session must tell her whether it is okay to archive, determine whether something is open, and say whether a closeout or a wrap is needed, because sessions that cannot say whether they are done pile up, and too many open sessions is the real failure.

**`SESSION STATUS: carry-back delivered, awaiting verification at home.` is RETIRED and never written again.** Every carry-back ends with one of the four verdict lines from `behavior-defaults.md`: Waiting on you, Still working, SAFE TO ARCHIVE with evidence, or NOT safe to archive with the one closing move named.

**SAFE TO ARCHIVE is a verified claim, never a phrase.** Issued only after all three verify live in the same turn: `git status` clean and pushed on every repo the session touched; the session record, wrap, or closeout note written and pushed when doctrine requires one; and every open wait re-lodged in the lane ledger's waiting-on column with its named condition and stale date, so nothing dies with the archive. The evidence rides in the line itself.

**NOT safe means the session diagnoses AND prescribes.** It names exactly what is open and the single move that closes it: /session-wrap when chat-only decisions or flags are unrecorded, /session-closeout when shipped work has no handoff note on main, or the named open action otherwise. Never leave Allison to work out which close a session needs.

**What stays with the home conversation:** the archive click itself, and the ledger flip. Home may still verify a verdict's claims against commits, and a hold still names its next block ("hold it open just in case" is not a call; it is a lane leaking). When home archives, it flips that lane's row to `archived` in aura `docs/estate/lanes.md` BEFORE dispatching anything further, and no dispatch block is ever written against a session whose row reads `archived`; that lane is gone, spawn a new one.

**Default is archive.** Sessions are cheap and deterministically named, so spawn freely rather than hoarding a session because it might be useful later. A correctly named session is trivially reproducible; a stale open lane is not free, and the verdict rule exists precisely so stale open lanes stop accumulating.

Sessions born before this re-ruling follow it from their next response. No cold sweep, no retroactive rewriting of past carry-backs.

Precedence: where this and any older SESSION STATUS wording disagree (the pin skill's carry-back template, the user-global close-of-turn rule, `behavior-defaults.md`), this re-ruling wins and the older wording is corrected to match. All three were corrected in the same pass on 2026-08-07 evening (pin v4.5, behavior-defaults, user-global CLAUDE.md, doctrine repo cf5d97e).

## The Lane Ledger: Row At Dispatch, Update At Carry-Back

Added 2026-08-03. The estate-wide lane ledger lives at `docs/estate/lanes.md` in the aura repo. It is the single file that answers "what Claude Code sessions exist, what does each belong to, and what is each waiting on" from any surface; any project reads it through its aura connection.

The habit, every hand-off:

1. At dispatch, when a paste block is handed to Allison, the issuing Cowork chat's block-writer appends or updates the lane's row in the ledger: canonical session name (three segments per the naming rule, and the same string the dispatch's `claude -n` launch line carries), window title as shown in the Code sessions list (flag PARITY MISMATCH with the rename when they differ; Code sessions only, per the lane identity ruling of 2026-08-03; a lane launched with `-n` should read parity-clean on the session's own first-contact self-verify), Cowork home (Claude project / conversation, identified by its kickoff header line, not its displayed title), machine, the worktree named in the dispatch (per Worktree Isolation above, so the next dispatcher can see which trees are occupied), status, waiting-on, last-updated date. The waiting-on statement this skill already requires with every hand-off is the same text that goes in the row -- write it once, use it in both places.
2. At carry-back receipt, the row updates to the new status (running / waiting-on-Allison / waiting-on-carry-back / archived / owned-elsewhere). `complete-safe-to-archive` is retired as of 2026-08-07; only the home conversation writes `archived`, as one motion with its archive call.
3. Append and update rows, never delete. Completed lanes move to the ledger's Completed section rather than vanishing, so the archive decision stays visible.
4. Rule 5 applies: rows are only as certain as their evidence. A lane whose home nobody has named stays needs-Allison; never invent a home for it.

A Code session that completes its carry-back updates its own row to `waiting-on-carry-back`, with the full report, in the same push when it already has aura write access; otherwise the home updates it on receipt (root CLAUDE.md delivery protocol). It never writes `archived` into its own row: that is the home conversation's call and the home conversation's write.

Write mechanics for the ledger file itself, added 2026-08-05 per Allison's ruling of 2026-08-04 after the second ledger regression (a stale-base full-file write erased three rows of newer state before the owning lanes healed it): every write to `docs/estate/lanes.md` obeys the shared-canonical-file-writes directive, canonical at aura `docs/directives/shared-canonical-file-writes.md`. In one breath, fresh read immediately before the write, blob-SHA compare-and-swap on any contents-API write, post-write diff check that no other lane's rows changed, git-based writers (Claude Code) preferred for this hot file, and a chat-surface writer that bounces twice on the SHA guard stops racing and routes the row verbatim through an intake handoff note for the next git-based writer to fold in. The directive also carries Allison's ordered build of the Estate Brain ledger-row tool, which retires whole-file writes once it ships.

## One Block Per Response

Added 2026-07-27 at Allison's instruction: "I can't have you giving me two at a time."

Exactly one paste block per response. Never two, never a "then once that lands" second block, never a block plus a queued follow-up block. (The pin marker is a bookmark, not a block, and does not count.)

If the work needs several steps, ship step one only, wait for the result, then ship step two. Sequencing dependencies are the assistant's job to hold, not Allison's job to keep straight while scrolling.

Prose describing what comes later is fine and brief. A second fenced paste block is not.

One named exception, added 2026-08-07 with the staged-kickoff ruling: a session wrap's staged kickoff set (session-wrap skill v1.3, step 4). Those blocks are a menu Allison draws from at her own tempo, not a sequence of dependent steps, and the dependency-sequencing burden this rule protects her from does not exist among them. Every block in the set still carries its own destination label and conversation name outside the fence. This is the only exception; it does not generalize to "several unrelated blocks are fine," and it never applies outside a wrap.

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

Known session names (update this list via skill overwrite as new ones appear):

- "Ember audit": the Ember estate audit and rebuild lane, running Claude Code locally on the M2 Mac mini (Ember's Mac mini, Embers-Mac-mini.local, Mac14,12 Apple M2 Pro, login account allison). Authoritative session name is ember-audit even when the window title has drifted. Created 2026-07-28. Holds the Ember source capture that closed ADR 0031 (commit eebd88a99, 65 previously unversioned production files), the Telegram rotation to bot @Ember_HQBot 8234710582, the Slack rotation on app A0AG008U1V5, the ADR 0029 correction (OpenCLAW is NOT decommissioned; gateway 2026.5.12 runs alongside Claude Agent SDK 0.2.87 and serves Ember's Slack surface), the credential blast-radius reduction across ember_agent.py and gateway.env, and the 1Password-versus-production reconciliation. Route all Ember host, rail, credential-reconciliation, and observability work here.
- "Canon Doc Sync": the canonical lane for pushing promoted canon docs and rule changes into the partnersync repo (created 2026-07-28, first promotion commit 25126c3, Doc 00). Canon markdown lives at project-knowledge/ top level in ExpertPartners/partnersync; Doc 00 is project-knowledge/00-How-to-Use-This-Project.md. ALL future canon promotions route here as an existing session. Works together with the canon-sync-protocol skill.
- "n8n Notion Wiring": the Layer 2 build lane on the partnersync-automation-backend repo (registered 2026-07-28 from Allison's carry-back). Holds the certified error logger PS-ErrorLog-Notify-v1 (live, version 6754f1de, renaming to CORE-Error-Logger-Notify-v1), the S6-Instant gated draft PS-S6Instant-EPICActive-v1 (ARlSztdu5a5DrxqP), the local repo clone at ~/Claude/projects/partnersync-automation-backend/, and the open gates (instance-wide error-workflow designation APPROVED ON by Allison 2026-07-28, fires next session; EP location PIT plus Google Sheets OAuth for S6 certification). Route all n8n workflow build and certification work here.
- "Email Setup Handoff": the email deliverability workstream (sender config, DNS fixes, EPIC and Expert Partners email setup). Also referred to earlier as the Legacy500 Pivot to GHL Kickoff thread.
- "Firecrawl onboarding": the live Firecrawl and doctrine session on the aura repo. Holds the key rotation record (rotated 2026-07-27 to the fc-344c3 prefix key), the headersHelper fix routing op through /bin/zsh -c, the config backups, the two-lane doctrine (Claude Code uses the Bearer lane, OAuth is the CoWork and app lane), the operating-doctrine State Check amendment shipped as v2.3, and the credential-helper class audit. This is the single lane for all Firecrawl and doctrine work.
- "Firecrawl MCP OAuth": a second Firecrawl session opened 2026-07-27, read-only and idle. Superseded by "Firecrawl onboarding" and should be closed rather than reused, since its context predates the doctrine edits.

Archived lanes, do not route to these:

- "Credential Rotation" and its Cowork conversation: archived by Allison 2026-07-28 after she completed all rotations herself. Its output files survive on disk at ~/Claude/projects/PartnerSync Operations Engineer/2026-07-28-github-repo-audit-secret-scan.md and 2026-07-28-session-summary-github-audit-and-credential-consolidation.md. Credential reconciliation ownership moved to "Ember audit."
