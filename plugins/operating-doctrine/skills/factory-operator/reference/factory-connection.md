---
classification: public
---

# Factory connection

One service, three users. The Factory connection is a Cloudflare Worker that wraps the Factory Public API. Claude and ChatGPT reach it as a remote MCP connector at `https://factory-connection.expert-partners.workers.dev/mcp`, signing in through Cloudflare Access with Allison's Expert Partners account only. The Expert Partners Hub reaches the same tools at `https://factory-connection.expert-partners.workers.dev/api` with a bearer token. Code lives in `tools/factory-connection`.

## Routing every request

Decide what the message is before calling anything.

| The message is | Do this |
| --- | --- |
| A status question ("where is X", "what is running") | `whats_running`, or `find_owner` then `read_messages` on the owner. Start nothing. |
| A correction to work already assigned | `find_owner`, then `post_message` to the session that owns it. Start nothing new. |
| A duplicate (the owner's recent assignments already cover it) | Say who owns it and what it is doing. Start nothing. |
| A new assignment for a continuing program that has a Workstream | `post_message` to that Workstream's orchestrator. Never start a parallel session. |
| A new continuing program with no Workstream | Write a Workstream brief for Allison to start (below). |
| A bounded job | `start_and_watch` (or `create_session` with `firstMessage`), first line `Section - Mission`. |
| A job whose architecture is unclear | Start it with `interactionMode: "spec"` first. |

Always call `find_owner` before starting anything. A match with kind `workstream-or-mission` is a Workstream orchestrator or mission that owns continuing work. Its `recentAssignments` show the latest instructions it received, newest first, so you can tell new work from repeated work.

## Workstream brief for Allison

Workstreams start in the Factory app, so a new continuing program gets a brief Allison starts herself. Give it these parts.

1. Outcome, the finished state in one or two sentences.
2. Constraints, including machines (Ember M2 for browser and visible work, Allison M4 for invisible background work), brand and repository.
3. How Factory tests it, the checks and evidence that prove each piece done.
4. Decisions reserved for Allison.
5. Where deliverables land, Drive for documents, GitHub for code.

## Defaults

Auto Model (`model: "auto"`) and High autonomy (`autonomyLevel: "high"`). Change them only for a task reason.

## Deliverables

Documents land in the owning Drive brain. Code lands in GitHub through a pull request. A Factory Workstream shared folder is working space, never the only home of a deliverable.

## Machines

The Workstream Defaults machine descriptions tell orchestrators where to route.

- Ember M2, signed-in Chrome, all browser and visible work, always on.
- Allison M4, invisible background work only, never touch the screen or browser.

Name either one as `M2` or `M4` in any tool.

## What the live tests showed (2026-11-09)

- A Workstream orchestrator can be found through the API, messaged, and its history read for duplicate checks. The Week 2-10 Document Creation orchestrator answered a status question through the API with its open assignment.
- Session Contents Sync is on for the organization, so messages stay readable when a Mac is offline. Reads of a session whose computer no longer exists succeeded.
- Posting to a session whose Mac is offline or asleep returns 503 "Failed to connect to session daemon" and nothing is queued. `start_and_watch` refuses an offline Mac up front.
- `archivedAt` set through the API is stored by Factory but the session stays in the app's active sidebar. Archive from the app until Factory changes this.
- The API has no title field. Factory names a session from its first message and may retitle it, so put `Section - Mission` on the first line.
- Mission mode started through the API ran a one-step task directly, with no plan approval pause and no agents.
- A brand new session can answer 404 to its first message for a second or two. The tools retry.

## Tool list

Sessions API: `list_sessions`, `create_session`, `get_session`, `update_session` (settings, tags, archivedAt), `delete_session`, `list_children` (attention, usage), `interrupt_session`, `read_messages`, `post_message` (images and files), `get_message`.

Helpers: `start_and_watch`, `watch_session`, `whats_running`, `find_owner`.

Computers: `list_computers`, `get_computer`, `computer_providers`, `computer_metrics`, `create_computer`, `update_computer`, `delete_computer`, `refresh_computer`, `restart_computer`, `retry_install_deps`.

CI Automations: `ci_scan`, `ci_list_jobs`, `ci_list_repositories`, `ci_list_repository_owners`, `ci_list_runs`, `ci_open_workflow_pr`.

Webhook automations: `list_automation_webhooks`, `trigger_automation_webhook`.

Agent Readiness: `list_readiness_reports`.

AutoWiki: `wiki_list`, `wiki_create`, `wiki_get`, `wiki_history`, `wiki_page`, `wiki_search`, `wiki_privacy`, `wiki_delete`.
