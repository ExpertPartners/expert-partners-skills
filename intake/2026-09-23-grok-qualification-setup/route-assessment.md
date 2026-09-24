---
classification: internal
classification_owner: allison
classification_date: 2026-09-23
date: 2026-09-23
source: Grok Repo Templates - Qualification Setup dispatch
project: expert-partners-skills
captured_at: 2026-09-23T20:44:20.264749+00:00
topic: qualification preparation evidence
---
# Grok Bot qualification route assessment

Status: DRAFT / NOT RELEASED. BLOCKED for qualification execution. Setup and evidence review only.
Retrieved: 2026-09-23.
Audience: NORTH and the qualification recorder/grader. Withhold this assessment, the grading rubric, prior answers, and grader feedback from the candidate.

## Finding

Current first-party documentation does not establish a non-duplicate route that can run the actual candidate Grok Bot twice per scenario/variant with clean independent context and a complete independently captured action/tool trace. This is an evidence gap, not a claim that such a route is impossible.

No candidate Bot turn, Bot change, duplicate, reset, browser automation, focus change, credential operation, or runtime demonstration was performed in this research. No endpoint was exercised against Grok Bot. Documentation cannot establish the live account's plan, enabled settings, or undocumented behavior.

The existing Estate Brain OAuth acceptance described by the parent verifier establishes that a connector worked. It does not establish clean-run isolation or complete candidate action capture. Its runbook says the door does not log tool names per client; token events and written content do not supply the missing full trace.

## Verified first-party documentation

| Requirement or route | Documented behavior | Qualification consequence |
| --- | --- | --- |
| Same Bot, successive runs | A Bot is durable and retains preferences, facts, and summaries. It has its own ongoing conversation. [S1] | A later message to the same Bot is not documented as a clean independent run. An instruction to ignore history does not prove history or learned memory is unavailable. |
| Separate conversations or separate Bots on one account | All Bots share one computer, files, browser cookies/sign-ins, and command-line credentials. Screens are not security boundaries. [S2] | Separate visible chats/screens do not establish lack of shared-state contamination. |
| Duplicate a Bot | The duplicate copies profile/settings/skills/routines/avatar, but omits learned memory, history, and attachments. [S1] | Duplicating has documented conversation/memory semantics, but is forbidden by this task and would still share the account computer. It is not the proposed route. |
| Reset/recovery | Cursor states that synced durable data remains and conversations survive a computer reset. [S3] | Reset is not documented as a clean candidate-context reset; it is not a qualification isolation mechanism. |
| Strong computer separation | Each user has a dedicated Firecracker microVM; vendor guidance assigns a separate Cursor user when a workload needs its own computer/credentials. [S4] | This documents the per-user boundary. It does not establish the permitted same-candidate, non-duplicate test route. No additional user/access or subscription change is proposed. |
| Visible transcript | Grok Bot's transcript shows tool activity, computer use, files, questions, and approvals. [S5] | Visibility alone does not document a complete independent, lossless, exportable transcript with every request/result or a trustworthy completeness marker. |
| Action Recording and export | Action Recording and OpenTelemetry Export are Enterprise-only. Recording is off by default. Audit Logs are a separate administrative/security pipeline. [S6] | An OAuth acceptance or audit log cannot stand in for candidate action recording. No account upgrade, spend, or setting change is proposed. |
| Export completeness | MCP arguments/results are never exported; shell command text is capped at 8 KiB; computer-use events contain counts/time, not typed text, coordinates, or screenshots. Bot turn identifiers are optional. [S7] | Even documented Action Recording plus OTel export does not, by itself, meet complete action/tool evidence requirements. |
| Response capture | Conversation export is a separate opt-in. Prompts/final responses are scrubbed, capped at 32 KiB, and not backfilled. [S8] | It must not be represented as an unmodified full transcript or used to infer missing intermediate actions. |
| Fixed inputs and runtime attribution | Cursor manages Bot model selection; there is no customer-facing model picker and serving models can change. [S6] | Pin and hash test inputs and configuration where possible, but do not claim the model/runtime itself was fixed. Record observed serving information if available. |
| Cursor CLI alternative | Cursor Agent CLI documents session IDs and stream-json tool start/completion records. [S9] | This is documentation for a coding-agent CLI, not proof it invokes the actual Grok Bot candidate. Substituting it, an SDK, Cloud Agent, or generic xAI API would change the evaluated system. |

## Required proof before execution

1. **Candidate identity and clean-run boundary.** A vendor-supported invocation route must identify the actual existing candidate Bot and explain how run A and run B are prevented from consuming earlier answers, learned memory, prior attachments, shared workspace residue, cross-Bot messages, and grader materials. No duplicate or destructive reset may be assumed. Identify an independently checkable pre-run state and run/session identifier.
2. **Complete independent recording.** The recorder must capture every candidate action/tool request and result, plus approvals, denials, delegated actions, failures, final response, and a terminal completeness signal. It must identify any redaction, truncation, gap, asynchronous work, or unjoined subagent. Candidate-authored summaries, OAuth events, OTel aggregates, and visible response text are insufficient substitutes.
3. **Fixed inputs and separation.** The recorder supplies the identical hashed scenario/variant input and permitted artifacts to each independent run. The candidate cannot read answers, rubric/grader notes, other runs, or recorder-only evidence. The grader evaluates sealed evidence after capture and cannot coach the candidate. A missing trace or unverifiable isolation produces an INVALID/NOT RUN record, not a candidate behavior score.
4. **Profile/mode match.** The parent's contract review identifies an ordinary/non-Grok-parent mode in the scenario matrix and a standing Scout/Auditor Grok profile. This potential mismatch must be resolved against the pinned canonical contract before any run. A standing Bot must not be silently treated as the ordinary candidate, and this assessment does not revise either profile or expected behavior.

The parent's scenario/variant matrix remains a plan requiring two independent runs per cell. The parent verifier owns its exact case/variant/run cardinality; this route research did not recount the matrix. Nothing here supplies candidate results.

## Smallest alternative for NORTH review

Recommend that NORTH authorize a narrowly scoped vendor-route clarification/proof request before any qualification run or harness build. Ask the vendor for one supported path addressing all three technical proofs:

- invoke the existing actual Grok Bot candidate in two independent clean contexts without duplication, with verifiable exclusion of persistent/shared contamination;
- export a recorder-owned complete request/result and action trail, including delegated work and evidence of completeness, beyond the explicitly limited OTel fields;
- identify the candidate profile/runtime and correlate immutable test inputs, each run, its transcript, tool evidence, and final response.

This is a proof request draft for NORTH's decision, not an external message or authorization to send one. Existing official documentation or a vendor-provided sample can be reviewed without creating a Bot or making an evaluation turn. If a supported path is documented, validate it against the contract and live account before execution. If the vendor cannot substantiate it, NORTH must explicitly decide whether to change the qualification contract or evaluated surface; the executor must not substitute a CLI/API or weaken evidence silently.

Do not build, buy, duplicate, alter access, enable telemetry, change the candidate, or issue Grok turns merely to investigate this gap.

## Sources and retrieval record

All successful sources below were fetched live through Firecrawl with maxAge: 0 on 2026-09-23. Scrape IDs identify retrievals; no source-content SHA-256 was captured. Documentation is evidence of vendor statements, not evidence of live account configuration or an executed run.

- **S1:** [xAI, Create and manage Bots](https://docs.x.ai/grok-bot/bots). Page last updated 2026-09-18. Scrape ID 01a0cffd-ff2a-73de-a43d-9572ddd16a51.
- **S2:** [xAI, Use the computer and apps](https://docs.x.ai/grok-bot/computer-and-apps). Page last updated 2026-09-14. Scrape ID 01a0cffe-5015-7603-bbc5-a73baa4c8c4f.
- **S3:** [Cursor, Work with Grok Bot](https://cursor.com/docs/grok-bot/work), “Update, recover, or reset” and Bot management sections. Retrieved 2026-09-23.
- **S4:** [xAI, Grok Bot security FAQ](https://docs.x.ai/grok-bot/security-faq), “How are users isolated from each other?” Page last updated 2026-09-17. Retrieved 2026-09-23.
- **S5:** [xAI, Message and collaborate](https://docs.x.ai/grok-bot/chat-and-collaboration), “Message a Bot.” Page last updated 2026-09-21. Retrieved 2026-09-23.
- **S6:** [xAI, Grok Bot security](https://docs.x.ai/grok-bot/security), “Logging and audit,” “Models and data,” and “Data retention and deletion.” Page last updated 2026-09-17. Scrape ID 01a0cffe-6240-768c-bfd7-567fe67f2f01.
- **S7:** [Cursor, OpenTelemetry Export wire reference](https://cursor.com/docs/enterprise/opentelemetry-export/wire), shared grok_bot attributes and the MCP, shell, browser, computer-use event schemas. Retrieved 2026-09-23.
- **S8:** [Cursor, OpenTelemetry Export](https://cursor.com/docs/enterprise/opentelemetry-export), conversation content, delivery, limitations, and joining sessions. Retrieved 2026-09-23.
- **S9:** [Cursor, CLI output format](https://cursor.com/docs/cli/reference/output-format), product scope and stream-json events. Retrieved 2026-09-23.

Searches also covered the xAI Grok Bot documentation index, FAQ, settings/recovery results, and the corresponding Cursor Grok Bot work page. No documented supported non-duplicate clean-run invocation API or complete Grok Bot tool request/result export was found in those reviewed sources. This bounded negative finding is not a claim that no private or future route exists.
