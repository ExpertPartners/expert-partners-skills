# Session Model Advisor -- workflow diagram

Technical/internal track (Mermaid), per the four-artifact rule's own split -- Excalidraw for customer-facing skills, Mermaid for technical/internal ones. This skill has no customer-facing audience, so Mermaid is the correct choice, not a substitute for one.

```mermaid
flowchart TD
    A[First user message of a new conversation] --> B{Which surface?}

    B -->|Claude Code| C1[Read this session's own\ntranscript JSONL]
    B -->|Claude Project| C2[Check for a stated\nmodel/effort in context]
    B -->|Claude Chat| C2

    C1 --> D1{Last assistant record\nexists?}
    D1 -->|Yes| E1[Read message.model +\ntop-level effort field\n= LIVE, authoritative]
    D1 -->|No, first-ever turn| E2[Fall back to settings.json\nhierarchy + env vars\n= configured default, not yet live]

    C2 --> E3["No introspection path exists.\nAsk, or say plainly --\n'can't read this here.'"]

    E1 --> F[Fetch ADR 0057 live]
    E2 --> F
    E3 --> F

    F --> G1{estate-brain fetch\ntool available?}
    G1 -->|Yes| H1[fetch repo=aura,\npath=decisions/0057...md]
    G1 -->|No, Claude Code only| G2{Local aura clone\non disk?}
    G2 -->|Yes| H2[Read local canonical clone\nkept fresh by pull-canonical-repos.sh]
    G2 -->|No| G3{gh CLI available?}
    G3 -->|Yes| H3[gh api ...contents/decisions/0057...]
    G3 -->|No| H4[Declare unknown.\nNever fabricate the matrix.]

    H1 --> I[Classify the task against\nADR 0057's categories,\nas fetched THIS run]
    H2 --> I
    H3 --> I
    H4 --> J["State -- can't reach ADR 0057\nfrom this surface right now"]

    I --> K{Current model/effort\nmatches ADR 0057's call\nfor this task category?}
    K -->|Yes| L["STATE -- staying on\ncurrent model/effort + why"]
    K -->|No| M["STATE -- recommend switching\nto X + why, before continuing"]

    L --> N[Proceed with the actual response]
    M --> N
    J --> N

    style H4 fill:#7a1f1f,color:#fff
    style E3 fill:#7a5a1f,color:#fff
    style N fill:#1f4d2b,color:#fff
```

## Reading the diagram

- The two amber/red boxes are the honesty points -- "can't see this on Chat/Projects" and "can't fabricate the matrix if every fetch path fails." Both are intended dead ends that still produce a truthful Step 5 line, not a crash and not a guess.
- Every path converges on the same Step 5 statement before the real response starts (green box). That convergence is the whole point of the skill -- no branch skips the fit-check, it only changes what the fit-check is allowed to claim.
- The companion SessionStart hook (see `session-model-effort-banner.sh`) is not on this diagram. It runs earlier, at session start, and only prints a banner -- it feeds nothing into this flow except, optionally, a shortcut so Step 2 on Claude Code can read the hook's already-printed line instead of re-deriving it.
