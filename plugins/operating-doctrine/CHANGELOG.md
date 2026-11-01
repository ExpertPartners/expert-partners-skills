## 2.72.0 - 2026-10-31

Retire the AI mail system under Allison's October 31 ruling (Decision Log 2026-10-31, Mail
boxes and new Handoffs rows stop). Live handoff instructions point to the HQ Rulebook section
Handoffs between AIs. Complete copy boxes carry the sender, receiver, model and effort or speed.
Receiving AIs use the Chat to Code job list, job_create or job_claim, job_status, and job_finish
with a summary and result link; code work travels as a GitHub issue labeled job. Session Steward
checks job_inbox instead of message receipts, and Session Wrap files its job report. Dispatchers
verify the same pending job before a copy box leaves; receivers claim it. Partial wraps and future
obligations stay nonterminal in that job. Related skills, templates and references follow the same
path. Quick Update, systems-map and session-home now read in-flight work and ownership from the job list through job_status, with the Job Tracker kept for older work. Historical entries stay as history, and the three skill history lines that described the
Handoffs report row and mail box now say they are retired. Generated files remain untouched.

Session Wrap v1.22, the wrap and archive trigger, folded in from PR 104 in the same release. In a
Claude Code or Codex session, Allison's own message wrap and archive in any capitalization, or
only the letter W or w, is her full okay. The session runs its wrap duties, files this job's
job_finish summary and result link and verifies them with job_status, closes its tabs, says SAFE
TO ARCHIVE and archives itself with no second question. A W inside other words, such as Wait,
never triggers it. Quoted or pasted text and questions about the phrase never trigger it, and S
and Q keep their meanings. If anything is still owed, including unfinished, uncommitted or
unpushed work of its own, it says exactly what in one line and does not archive. The worker
retains unfinished duties; only an archive blocked after readiness and consent uses the steward
fallback. Finished project sessions end on Ready to archive and wait for Allison's Archive
instruction; W supplies that consent. Scheduled runs and completed Codex background records keep
their scoped exceptions. Native app tools are checked at use time. Section 5A readiness uses the
job list in place of the retired Handoffs report row. Adds reference/w-trigger-tests.md (Decision
Log 2026-10-30, Wrap and archive, or W, tells a code session to wrap and archive itself). PR 104
proposed this as 2.71.0; it ships here as 2.72.0 because 2.71.0 is Quick Update.

## 2.71.0 - 2026-10-31

Quick Update v1.0, a new skill. A message that is only quick update, simple update or short version
makes any AI check the live state, then answer in three short first grade lists, what's important,
what's still outstanding, and what I recommend, followed by the one closing status line for the
surface. Words like quick or update inside a normal sentence never fire it. CEO brief stays Teach
Me's own step opener and is not a trigger. Requested by Allison in the Google Workspace access
strategy audit session.
## 2.70.0 - 2026-10-31

File to Knowledge Base Optimizer v1.0, a new skill built under the build standard from the approved
spec, [HQ][V1.0] Spec - File to Knowledge Base Optimizer, revision 4. It turns a transcript, a PDF, a
Word or Google Doc, a web page, a captions file or a recording into clean, structured Markdown for
Claude Project or Custom GPT knowledge in six steps, take in the source, one or two intake questions,
extract and clean without changing meaning, add a header, summary, takeaways and navigable sections,
split past about 50,000 tokens into numbered parts with a navigation page, then save by the company
file rules into the brain's Claude outputs folder and report. Nothing lost, nothing invented. Every
instruction carries its spec line. The engine, scripts/optimize.py, does the deterministic work and
the model does the judgment work (Decision Log 2026-10-27, The optimizer spec is approved at revision
4, and The optimizer's six open behaviors are decided). Assigned by HQ in Handoffs. Waits for
certification by Claude in HQ and Allison.

Amended during its test rounds (same release): Step 4 gained fidelity rules learned from the judges,
support quotes the engine verifies word for word, a self-check and a fresh eyes read, one point one
grouping, and a navigation summary drawn from the parts. The engine's validate step now also refuses
any name, number or term in the summary, takeaways, headings or actions that the source (or the intake)
does not carry spelled the same way, and a navigation summary that names the file or strays from the
parts' summaries and the source's headings. Captions without labels group into paragraphs that end at
sentence ends, PDF heading levels are normalized, and unmapped glyphs are restored from a second read
or marked unreadable. The navigation page's summary is built by the engine from the parts' summaries
in one or two paragraphs, and Step 4 names people, keeps unlabeled passages apart, keeps qualifiers
with their claims, places headings at topic changes and writes the shorter end of the spec's ranges.

## 2.69.0 - 2026-10-30

Build Standard v1.1. Four fixes. A tool's record starts in EP Notion HQ's AI Employee Vault the day
Allison approves its spec, and a missing record is reported while the chain check and release stay
blocked. Where a tool's most recent version is silent, the gap is filled from older versions.
Rule 7 lists Claude chat, Claude Code, Codex and ChatGPT, with Cowork now part of Claude. Every
build carries four cost and quality rules, with a $300 wait-for-yes line. AI-written parts get a
stated tolerance, judges run on the lowest model that can do the job, a cost estimate is posted
before any test run and over $300 waits for Allison's yes, and a failed test round stops the build
until it is reported (Decision Log 2026-10-30, Every build carries four cost and quality rules,
with a $300 wait-for-yes line). Assigned by HQ in Handoffs rows 1364 and 1424.

## 2.67.0 - 2026-10-26

Build Standard v1.0, a new HQ skill. Any builder on any surface follows one standard whenever it
starts, changes or retests a skill, AI employee, prompt or tool. Build only from a spec Allison
approved, trace every instruction to a spec line, replay every demonstration and test case three
times with saved evidence, never edit a test to pass it, test alone then with everything
upstream then one supervised run, draft the chain map update for HQ, report in one fixed
format, and never certify your own work. Claude in HQ and Allison certify. Every change reruns
the tool's tests and the tests of every downstream tool (Decision Log 2026-10-26, The HQ Build
Standard becomes permanent and goes in before any Week 0 build). Assigned by HQ in Handoffs.

## 2.66.0 - 2026-10-25

Ask Me Questions v1.0, a new HQ skill, and S narrowed to S only. A message that is only Q or q,
or ask me clarifying questions, makes any AI read what it has, then ask up to five clarifying
questions one at a time, most important first, never asking what it already knows, then say back
what it learned and do the work. A Q or the word question inside a sentence, like Q4, never fires
it. Only S or s alone now means sent, no other single letter does, and operating-doctrine v2.18,
code-block-routing, pin and the repo AGENTS.md follow the live Rulebook (Decision Log 2026-10-25,
Q means ask me clarifying questions, and S means sent, and no other single letter does). Assigned
by HQ in Handoffs.

## 2.65.0 - 2026-10-25

Teach Me v1.0, a new HQ skill. Every step of Cal's course opens with Next step, Teach Me and a
CEO brief under 200 words for someone who has never watched Cal's videos. Every finished step
gets a drafted HQ guide entry in four fixed parts, an SOP story when an SOP was written, and a
60 to 90 second explainer scene list that ends on Stuck, ask Allison. It drafts only and never
edits the Lovable app, Notion or Drive, and never renders video (Decision Log 2026-10-25,
Every step starts in teach-me mode and nothing gets skipped, and The skill is called Teach Me
and every step ends with a short AI video). Assigned by HQ in Handoffs.

## 2.64.1 - 2026-10-24

document-formatting-standard v4.1 follows the live HQ Rulebook. Every document an AI makes in
work with Allison uses Poppins throughout, for every brand and every room, AG Luxury included
(Decision Log 2026-10-24, Every document made in work with Allison uses Poppins). The skill no
longer tells AG Luxury documents to use Italiana and Manrope. Those are the allisongaddy.com
website fonts and belong only to public, client-facing design. Assigned by HQ.

## 2.64.0 - 2026-10-24

The archive gate and the orphan sweep (Decision Log 2026-10-24, Archiving is gated on the paper
trail, and an orphan sweep catches what slips). A Claude Code or Codex session archives itself
only after its report row is written in Handoffs and read back and its incoming row is marked
Done with a pointer to that report. The mail box in chat is only the bell, never the record, and
a session that cannot reach the tab stays open and says so. operating-doctrine v2.17 adds the
rule for every session, session-wrap v1.21 amends section 5A, code-block-routing and pin v4.8
make the Handoffs row the carry-back and the chat message the bell, and session-steward v1.6
adds section 10, the orphan sweep, for both the Claude Code and Codex stewards. It lists every
row still Sent or Read whose session is archived or missing and every pull request or commit
with no report row, in one row to HQ. Assigned by HQ in Handoffs row 725.

## 2.61.0 - 2026-10-22

Five skills follow the live HQ Rulebook. document-formatting-standard v4 points to the
Rulebook's Document formatting section for every number (1.5 line spacing as of 2026-10-22,
no blank lines between paragraphs, short paragraphs, AG Luxury fonts kept) and keeps only
how to apply it with tools. browser-automation and ember-browser-routing adopt Browser tabs
stay clean, one working tab per task reused in place, every opened tab closed before
reporting, never another AI's or Allison's. session-wrap v1.19 adds section 5A and
session-steward v1.4 follows it, finished Claude Code and Codex sessions archive themselves
where the app allows and never ask Allison, otherwise they end on WRAP, safe to archive for
the steward's archive pass. Disclosure intake/2026-10-22-disclosure-rulebook-sync-formatting-tabs-session-wrap.md.
Assigned by HQ, confirmed by Allison in the session that made it.

## 2.60.4 - 2026-10-21

browser-automation adds Rule 2a, follow the trail before you ask. Sessions must try the API,
then the signed-in Ember browser through playwright, then a 1Password login, before asking
Allison anything about access, and must not use the Claude in Chrome extension for this work
because it is also connected on the M4. Added after a session stalled asking Allison to
identify browsers for a site that was already signed in. Allison's direction 2026-10-21.

## 2.60.3 - 2026-10-20

browser-automation records the Chrome settings that keep Ember's M2 clean. Chrome starts with
--silent-debugger-extension-api through a login item, so the extension debugging bar never
shows, and both profiles stop pinning and showing tab groups on the bookmarks bar. Done with
Allison on 2026-10-20 after the bar and the pinned AI tab groups were getting in the way.

## 2.60.2 - 2026-10-20

browser-automation replaces Gemini CLI with Antigravity CLI, Google's replacement (Gemini CLI
is retired 2026-12-18). Antigravity CLI on Ember's M2 has the playwright and playwright-atlas
browser tools, signs in with the Gemini API key from 1Password through agy-launch.sh, and was
verified on GoHighLevel with its tab closed afterward. Set up at Allison's direction 2026-10-20.

## 2.60.1 - 2026-10-20

browser-automation documents the Atlas browser. Every AI client on Ember's M2 now has a
`playwright-atlas` MCP server (Profile 3, atlas@ token) beside `playwright` (Default,
ember@), approved by Allison 2026-10-20. Adds when to pick each browser, that several AIs
can share one browser in separate tab groups, and that the two token items are read by ID.

## 2.60.0 - 2026-10-20

browser-automation now reaches the signed-in Chrome through the Playwright Extension
instead of Chrome's remote-debugging port. The port route made Chrome ask "Allow remote
debugging?" on every new connection, which stopped unattended work. A shared connector
(~/maintenance/chrome-signed-in-mcp.sh, token from 1Password) now backs a `playwright`
MCP server in Claude Code, Claude desktop, Codex and Gemini CLI, and a job runner
(~/maintenance/pw-run.py) runs scripted jobs and closes every tab from the run. Adds tab
group cleanup rules, per-profile lanes, token rotation, and the missing-tool rule from
Allison's 2026-10-20 direction. Verified live on Ember's M2, GHL signed in with no prompt.

## 2.59.0 - 2026-10-20

Adds browser-automation to operating-doctrine and updates ember-browser-routing,
per Allison's 2026-10-20 Decision Log entry "Browser automation runs only in the
signed-in Chrome on Ember's M2". Browser work always attaches to the signed-in
Chrome on Ember's M2 and never opens a fresh or signed-out browser. It assumes
Chrome and 1Password access until a real failure, picks the most durable and
fastest path rather than the easiest, and closes every tab it opens.
browser-automation covers scripted and unattended jobs, GoHighLevel first
(workflows, contact merges, UI-only settings), using Playwright 1.56.0 in
~/.venvs/playwright attached over Chrome's existing debugging connection.
ember-browser-routing now carries the same ruling and points scripted jobs to
browser-automation, while interactive work keeps the cua_ember route. Shipping
in this plugin is what delivers it to Claude Code, Claude surfaces and Codex.

## 2.58.0 - 2026-10-19

Repoints skills from the retired aura repo and the Estate Brain connector to
the Google Drive business brains. This implements Aura Retirement Plan step 2
and the Decision Log entries "Repointing the skills starts now" and "No skill
exceptions" (2026-10-19). Only where a skill reads or writes changed. Each
skill's job and triggers stay the same. Live reads of aura rules, ADRs and
the lane ledger now point to the HQ Rulebook, the Decision Log and the Job
Tracker (Handoffs tab for messages). Deployed-copy and upload-shelf wording
in estate-memory-router, remember-this and repo-standards now says skills
reach every surface only through the GitHub skills marketplace. session-home,
new-project, session-model-advisor, grok-auditor, grok-fixer, pin,
connection-first-implementation and operating-doctrine are repointed in the
same way. Mentions of aura as history, including RULED-BY citations, are
kept. brand-voice 0.6.1, research-ops 0.1.1 and systems-map 0.6.2 carry
matching edits. Merge and per-surface verification remain separate steps.

## 2.57.0 - 2026-10-16

Adds wordpress-implementation-routing to operating-doctrine. WordPress work now
classifies the owning live-state layer before choosing a tool, prefers native
WordPress abilities or APIs and REST for routine reversible content/state
changes, uses repository code only when the requested outcome is genuinely
code-owned, reserves WP-CLI/server tools for operational and bulk work, and
keeps browser automation last. The skill adds an explicit anti-overcoding
check so link, copy, metadata, media, menu, and ordinary setting changes do not
turn into unnecessary release-engineering projects. Live-state inspection,
rollback, visitor-facing verification, 1Password-first access, existing-owner
reuse, and normal HQ approval gates remain required.

## 2.56.3 - 2026-10-14

Live Job 2 tests found that "sixth grade" did not reliably load the skill,
and some replies bundled several physical actions into one named step.
The same skill now leads its shorter discovery description with the three
triggers and makes the one-physical-action boundary explicit with an example.
No safety, approval, direct-tool, name, or location change. Five-surface
behavior verification remains open.

## 2.56.2 - 2026-10-14

kindergartner-mode adds "sixth grade", "kindergarten", and "hand-holding mode"
to discovery and instructions, preserving its existing name, location, and
triggers. Replies use a sixth-grade reading level and give one step, then wait
for Allison's result. A hands-only step contains one physical action. Safe
direct tool use, safety rules, and approval requirements remain in force.
This implements Allison's October 14 decision in the HQ Decision Log. Release
and live behavior on each supported surface require separate verification.

## 2.56.1 - 2026-10-13

ChatGPT import fix. batch-first-execution carried an agents/openai.yaml that
listed policy.products as chatgpt, codex, api and atlas. OpenAI's plugin
validation allows only CHAT, CODEX or both in that field, so ChatGPT rejected
the whole operating-doctrine plugin while the other seven imported. The products
line is removed (every product still sees the skill), the icon paths now start
with ./ and the icon is 48 by 48. Claude Code and Codex read the same files and
are unaffected.

## 2.56.0 - 2026-10-13

Standalone skills move into marketplace plugins so every surface gets them by sync and none depends on a hand upload. operating-doctrine now carries session-wrap, remember-this, estate-memory-router, batch-first-execution, canon-sync-protocol and repo-standards. canon-sync-protocol is rewritten for the Drive brain (v2.0): one Drive home, the Decision Log, and the marketplace as the only road for skills, no zips. content-engines 0.6.0 adds content-coach, hook-engine, post-grader, post-scheduler, post-value-filter and social-analyzer, imported verbatim from the claude.ai Organization library. research-ops 0.1.0 is new and carries capability-currency, research-intake and the three TUB analysts, also imported verbatim. business-plan-builder and video-transcript-relay already live in plugins, so no second copy was added. ai-brain-builder duplicates agent-brain-builder in real-estate-agent-toolkit and is preserved in archive/ rather than loaded.

## 2.55.0 - 2026-10-13

Corrections to the batch 1 cutover. Decision Log entries drop numbered IDs and
read as date, what was decided, why, and a Replaces note. Reminders become one
Job Tracker row with the come-back condition in Waiting on (remember-this,
estate-memory-router, capability-currency). repo-standards reads the new Repo
rules section of the HQ Rulebook and registers repos in the GitHub Archive
Index sheet. session-model-advisor reads the new Model chart section of the HQ
Rulebook. capability-currency writes the Capability Watch and Capability
Refresh Changelog Docs in Company Core, and its runner script and launchd plist
now live in tools/capability-currency/. systems-map 0.6.1 adds two plain
definitions (business brain, repo).

## 2.54.0 - 2026-10-13

Step 1 of the clean-slate cutover, batch 1. code-block-routing, session-steward
and session-model-advisor now use the Job Tracker (Drive sheet), the Decision
Log and the HQ Rulebook in place of aura lanes.md, update_lane_row and Estate
Brain reads. Worktree, model and effort, closeout and verdict rules are
unchanged. Companion changes in the standalone skills (session-wrap,
estate-memory-router, intake, research-intake, capability-currency,
remember-this, new-project, repo-standards, batch-first-execution) and the
systems-map plugin 0.6.0 ship in the same pull request.

## 2.53.0 - 2026-10-12

Removes the remaining routing naming text from pin, code-block-routing,
lane-spawn, session-steward, cowork-direct-execution and session-model-advisor,
with matching removals in session-wrap v1.18, canon-sync-protocol and
batch-first-execution, per Allison's 2026-10-12 amendment to decision 0107
(delete, never restate). Worktree, model and effort, ledger and closeout rules
are unchanged.

## 2.52.0 - 2026-10-12

Completes the decision 0107 propagation sweep after 2.51.0. Removes remaining
live naming-only gates from pin, lane-spawn and session-steward; replaces the
canon-sync dispatch skeleton's title self-verification with durable destination
metadata; updates session-wrap to v1.17 so live terminality and successor
obligations use durable mission and destination state instead of naming ceremony;
and preserves worktree, model/effort, scope-collision, wrong-repo,
wrong-host, production, credential, destructive-action and lifecycle controls.
Historical version prose remains marked as provenance and is not governing.

Review addendum (same release, independent Claude Code review of this PR):
code-block-routing's operative lane-ledger rule no longer requires a two-word
worker title, a Table Birth home, or parity-mismatch renames; the first ledger
cell is any short label or stable session id. canon-sync-protocol's dispatch
recipe no longer puts an exact session name first or describes launch-naming
and off-disk self-verification as current.

## 2.51.0 - 2026-10-12

Decision 0107 retires mandatory Room/Table/Chair/Worker naming ceremony and visible-title gates. code-block-routing no longer requires exact session/table names or naming-only bounces; lane-spawn drops Table Birth/title ceremony; session-steward drops birth self-title and drift repair; pin and session-wrap no longer enforce title parity; batch-first-execution validates substantive execution fields instead of naming metadata. Worktree isolation, model/effort, real scope collision, wrong-repo/host, production, credential, and lifecycle safeguards remain.

# operating-doctrine changelog

## 2.49.0 -- 2026-09-23

`session-model-advisor` v1.1 retains conversation-start and explicit
model/effort-question invocation, preserves decision 0093's matching-Worker
fast path, and adds current surface capability checks for technical handoffs.
The separate Batch-First Execution v1.1 skill composes with the advisor for
model selection and with `code-block-routing` for sending-side envelope
completeness. It does not change code-block-routing's one-block-per-response
rule. No model matrix is copied into the plugin.

## 2.48.0 -- 2026-09-08

Two-word worker titles per decision 0091 (ruled by Allison 2026-09-07 via Lock
that, ruling of record aura decisions/0091-allison-controlled-two-word-routing-names.md).
`code-block-routing` (dated amendment, description frontmatter updated),
`lane-spawn` v1.9, `session-steward` v1.5, and `pin` v4.10 retire the
`<Table Name> - <Specific Job>` worker form and the room-token exception that
rode on it. Every new WORKER visible title is exactly two clear words
identifying the job, every new or Allison-renamed TABLE NAME is exactly two
clear words, worker ownership and return identity ride in the lane ledger row
and the CLAUDE HOME line rather than in the title, Allison may rename a Table
by explicit direction with prior names kept as historical aliases, workers
active before 2026-09-07 finish under their admitted titles, and legacy names
are never mass-renamed by AI. Superseded lines are marked SUPERSEDED IN PART
in place. Pin section 5 also gains the decision 0082 amendment pointer on its
one-table-one-active-worker sentence, which the sibling skills already
carried. Disclosure filed at
intake/2026-09-08-disclosure-worker-title-form-superseded-by-decision-0091.md.
Same pass, implementation detail with no rule change: the search for the native
session-management tool is made once per session and a successful
set_session_title result is the birth verification (transcript reread reserved
for tool errors and drift checks), in session-steward section 1, pin section 5,
and code-block-routing's absent-tools paragraph.
NORTH review correction, same day: the sweep reached every ACTIVE line. Table
names are no longer described as permanent or set once (Allison may rename a
Table by explicit direction, decision 0091), the code-block-routing heading
reads Two-Word Job Title, the SESSION NAME template no longer commands an
independent reread, and every routine reread in code-block-routing, pin, and
session-steward is rewritten as the exception path. Version-history paragraphs
keep their original wording, marked SUPERSEDED IN PART.
Inked by the Startup Efficiency - Routing Simplification Code session
(table Startup Efficiency, room NORTH'S ESTATE CONTROL TOWER), a conformance
pass only; no new rule, registry, or routing-state write.

## 2.47.0 -- 2026-09-07

`connection-first-implementation` amended: access first, browser last, and
rung five gains its execution home. Ruled by Allison 2026-09-07 as a standing
direction (ruling of record:
aura intake/2026-09-07-ruling-browser-last-ember-browser-execution-home.md).
The ladder now names the access roads that live on rungs one through four
(surface-native tools and connectors, Claude and ChatGPT plugins and
connectors, Estate and official MCP servers, existing org integrations,
official APIs, OAuth, service accounts and delegated identities, 1Password
credentials, official CLIs and SDKs, approved SSH and remote-host roads,
Firecrawl and existing web-data roads, native web search and fetch), states
that "try all methods" means continue through roads until one succeeds and
never repeat a write through several channels, keeps every stronger
system-specific rule in force, and inherits the systems map as the access
inventory rather than copying it. New section "Rung five has a home:
Embers-Mac-mini": browser automation that genuinely survives the ladder runs
on Embers-Mac-mini (M2 Pro), Google Chrome, existing saved profile and
session state only, the existing Claude-connected Chrome window, the existing
1Password integration; never by default on AG-Mac-Mini-M4, never a fresh or
Guest profile, never the foreground window, never Allison's focus; Ember path
unavailable means re-check non-browser roads, diagnose, report the blocker,
never fall back silently to the M4; Allison may override per task. The M4
keeps every non-browser job it already owns. Companion edit in the same pass:
aura docs/directives/host-machine.md retires its "any machine with a browser"
sentence and carries the machine half of the same ruling. No new skill was
created and no per-project copy was made; the plugin distributes the rule.
Inked by the Ember Browser Routing - Deploy Access Routing Rule Code session.

## 2.38.0 -- 2026-08-08

New skill, `session-model-advisor`. Fires on the first user message of any
new conversation, on Claude Chat, Claude Projects, and Claude Code. Reads
the current model and effort, fetches ADR 0057 (Model and Effort Operating
Standard, aura repo `decisions/0057-model-and-effort-operating-standard.md`)
live, classifies the incoming task against the ADR's decision matrix, and
states plainly -- before anything else -- whether to stay or switch. Carries
no copy of the matrix, a changed default in the ADR never requires editing
this skill. Full four-artifact treatment (SKILL.md, README.md, Mermaid
workflow diagram, training-walkthrough script) per skill build session
System Hardening / Session Model Advisor / Skill Build, authorized under
ADR 0057 (accepted 2026-08-08). Cowork's introspection gap (no documented
way for a claude.ai Chat or Project conversation to read back its own
model/effort selection) is named explicitly in SKILL.md Step 2 rather than
assumed away -- verified live against `support.claude.com` the same day,
not carried forward from the source research untested.

Companion SessionStart hook, `session-model-effort-banner.sh` (Claude Code
only, lives in `~/scripts/` plus `~/.claude/settings.json`, shipped as
reference material inside the skill package). Prints the configured model
and effort as a banner line at session start. Print-only, no classification,
installed and wired live on the M4 this same session.

## 2.34.1 -- 2026-08-07

GitHub sync acceptance test. No doctrine change, no skill body change. This
version bump exists to prove the claude.ai org marketplace pipe end to end,
per Allison's ruling of record (aura
intake/2026-08-07-ruling-github-sync-adopted-for-skill-deployment.md).
The pipe is proven when the deployed plugin reports 2.34.1 without any zip
touching any page.

Originally staged as 2.33.0 -> 2.33.1. Rebased past a same-day direct push
to main (8aab6bc) that bumped plugin.json to 2.34.0 without updating
marketplace.json, which still read 2.33.0 for operating-doctrine, a live
manifest drift. Resolved by carrying the bump to 2.34.1 in both files.
