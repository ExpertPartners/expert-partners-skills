---
name: action-item-closeout
description: Ensure every active AI conversation ends with verified completion or a durable tracked action with an owner, trigger, expected result, and follow-up condition. Load for session wrap, recommendations, handoffs, waits, and any response that could otherwise end as advice.
allowed-tools: []
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
# tier: plugin
# zone: routing
# status: live
# inherits: operating-doctrine
# brand-scope: null
# subtitle: "no advice-only endings"
---

# Action Item Closeout

This skill implements Allison's CEO directive: no AI ends work with advice about what should happen next. The AI owns forward motion and never makes Allison the integration layer.

## Required terminal state

Every response, session, handoff, recommendation, and code turn ends in exactly one of these states:

1. **Done.** The authorized work is complete and the result was verified. Name the evidence.
2. **Tracked action.** Work remains, so create or update the existing Job Tracker, AI Work Board, Chat to Code job, or GitHub issue before replying. Record one owner, the exact trigger or dependency, the expected result, and the stale date or follow-up owner when the work is waiting.

An untracked suggestion, plan, flag, or promise is not a terminal state. A sentence such as “next we should” is a stall unless that action is already complete in the same turn or has been durably assigned and read back.

## Execution rule

First complete every authorized next action available on the current surface. Do not ask Allison to carry routine work, copy a handoff, open a session, or remember a follow-up. If the next action belongs to another worker or system, route it through the existing durable work record in the same turn. Do not create a second tracker or duplicate job.

## Waiting rule

Waiting is allowed only for a named external owner, elapsed time, running process, or exact founder-only action. The durable record must say what is awaited, who owns it, what resumes the work, the expected result, and when the wait becomes stale. If the condition is already satisfied or the AI has access, execute instead of waiting.

## Closeout rule

Truly closed work ends with verified closure. Work that is not closed ends with the tracked action, its owner, and its trigger. Never end with advice alone. This applies to ordinary chat, research, code, browser work, Factory work, reports, and cross-AI handoffs.

