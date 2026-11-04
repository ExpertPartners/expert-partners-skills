---
classification: internal
classification_owner: allison
classification_date: 2026-11-04
date: 2026-11-04
source: HQ Rulebook Check first and Project ownership, AI Implementation SOP Pick the right tool, build-standard skill, Skills Distribution Audit 2026-11-03, historical AI Capability Routing export
topic: placement comparison and launch phases for ai-capability-routing
---
# Placement and transition

Use with the ai-capability-routing skill when the home is not obvious or a capability is being launched somewhere new. The Rulebook and Decision Log govern. Nothing here adds a rule.

## Comparing candidate homes

Compare only the homes a real owner check left standing, and only on the dimensions that change the answer.

| Dimension | What to establish |
| --- | --- |
| Required access | Can it reach the sources, connectors and accounts the job needs, through the access order the AI Implementation SOP sets? |
| Unattended operation | Only when asked for. Can it run on its own, and has it passed the proving runs the Decision Log requires? |
| Persistence | Where its state and working context live between runs, and whether that state stays out of a second truth store. |
| Collaboration | Who can use it, share it and see its results. |
| Deployment and updates | How a change reaches it, how fast the current vendor docs say that happens, and what a running session keeps. |
| Observable results | How a person or AI can see that it worked, with real output. |
| Reversibility | How cleanly it can be undone or moved later. |
| Team usability | Whether the people who need it can find and use it without help. |

Read the vendor's current first-party documentation for any fact in this table that can change, and record the source and date. Observations from a live system are evidence about that system only.

When one outcome needs more than one system, each gets exactly one job. For a skill, that usually reads as GitHub holds the source, the marketplace delivers it, each destination runs it, and the Skills Vault holds its human side. That is one design, not four owners.

## The six phases

1. Discover. Name the outcome, run the owner checks and gather current capability evidence. Build nothing while the owner is unclear.
2. Place. Choose the home and say why. Name the canonical source, operating owner, execution surface, human view and delivery surface.
3. Launch. Coordinate the smallest build that establishes the capability in its home, through the existing Chat to Code route and the build-standard skill. Write the acceptance criteria and approval boundaries first.
4. Prove. Verify in the destination itself. Keep the five kinds of evidence apart.
5. Reconcile. Bring the existing records up to date and make sure the human view points to the source. A destination's settings screen never becomes a second truth.
6. Transition. Hand day-to-day work to the owner. The room keeps only what still belongs to it, such as open cross-system issues. If nothing remains, recommend closing it.

## Five kinds of evidence

| Evidence | What it proves | What it does not prove |
| --- | --- | --- |
| Configuration | A setting was saved and read back. | That anything uses it. |
| Upload | Bytes reached a place. | That the place serves them. |
| Source publication | The release is on GitHub main with its manifests. | That any destination imported it. |
| Destination delivery | A destination's import or installed files match the release. | That a running conversation loaded them. |
| Runtime behavior | A fresh session loaded the instructions and behaved as expected. | That every older session did the same. |

When a platform does not expose the exact release it loaded, keep that uncertainty in the report rather than filling it with a source read.

## Acceptance for a persistent specialist

Before building an AI employee, bot or agent, write down its owned outcome, what is in and out of scope, its sources of truth, its tool and connector access, its approval boundaries, its state model, its output standard, its tests and failure tests, its first supervised assignment, and the proving runs that would let it run unattended. The build-standard skill and its test plan carry these forward.

## The failure to prevent

The room that discovered a need does not become its owner for that reason. A good end state reads, this room designed and launched the capability, it now lives in its proper home, and the room no longer runs it.
