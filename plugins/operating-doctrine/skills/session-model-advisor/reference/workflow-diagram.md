# Session Model Advisor -- workflow diagram

```mermaid
flowchart TD
    A[Model question or new handoff] --> B{Existing dispatched Worker?}
    B -->|Yes| C{Dispatch line matches runtime?}
    C -->|Yes| D[Proceed under decision 0093]
    C -->|No| E[Read live ADR 0057]
    B -->|No| E
    E --> F[Classify job and surface under decisions 0057 and 0072]
    F --> G[Verify current model and exact effort options]
    G --> H{Options confirmed?}
    H -->|Yes| I[Recommend one task-fit combination]
    H -->|No| J[Retain approved current selection and name uncertainty]
    I --> K[Batch-First Execution validates complete handoff]
    J --> K
```

The current picker or supported API establishes account-specific options;
provider docs clarify their meaning. The companion Claude Code SessionStart
hook reports configuration only. It does not select a model or replace the
advisor. A matching dispatch does not repeat the full classification.
