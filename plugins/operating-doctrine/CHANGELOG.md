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
