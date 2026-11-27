# Week Wrap prewrite completeness gate

Before drafting or writing any package output, assemble a private linked preflight from the current owning records. Read the independent inventories in full first, then reconcile evidence against them. Do not build an expected list from the rows that happen to have receipts. A truncated, missing, stale or not independently established inventory is a gap, never an empty pass.

## Implementation-week route

| Check | Independent inventory | Required evidence per item |
| --- | --- | --- |
| `readiness` | Every teaching point in the exact week's current readiness list and source coverage, expanded to one key per point and company, `HQ:point-id`, `EP:point-id`, `AG:point-id` | One explicit decision from `Covered`, `Test`, `Finish`, `Upgrade`, `Build`, `Skip`, a reason and a record link. A decision is not proof of execution; preserve open work in its own check. |
| `decisions` | Every entry dated in the inclusive week window, across the full live Decision Log, including multiple decisions on the same day | Decision link and either `implemented` with a Change Log receipt link, or `routed` with a named owner and link to the actual routing record. List all unsupported and unrouted decisions as gaps. |
| `close` | Every non-package criterion in the owning week's Standard and newer applicable decisions | `passed` with linked evidence for each criterion. For Week 10 include `engine`, `wheels`, `steering`, `gas`, `transmission`, `dashboard`, `maintenance`, each checked against Allison's confirmed plain-business definition, and `brain-walkthrough`, with evidence that Allison and HQ Chief HR Officer walked the filled templates department by department across all brains. Do not use a template file or planned walkthrough as evidence it happened. |
| `tools` | Every tool or skill surfaced by the week's evidence and decisions | `owned`, the assigned owner, and the actual assignment link in the week's tool-builds Workstream. No requirement that nonblocking builds finish before the package. |
| `sources` | Every missing source piece from the week's ledger, coverage and gap records | One linked disposition, `search`, `have it`, or `create our own`, with the reason. A search disposition does not prove recovery; if required source coverage or a separate close criterion is still unmet, report that as a gap. |

For Week 10 use the standard's canonical number `10` and the eight close keys above, even if the Standard uses other labels. Do not invent a universal set of close criteria for other weeks; resolve their actual governing Standard and decisions.

## Attended-session route

Require a source identity and evidence for both Allison's intent to teach this session and review of the full supplied source, with basis and limits. Use `session` keys `intent` and `source-review`, status `verified`. Do not require weekly readiness or imply the session was a curriculum close. If a request is actually for a week close, use the implementation-week route.

## Both routes: package feasibility, then completion

Require the following `package` keys, each status `ready` with its `url`. Verify those routes on current evidence; a check is not a request to pre-create a deliverable. Use a known working route receipt or an authorized practice asset, never the production teaching package itself to check whether writes are possible.

| Key | Required linked evidence and binding |
| --- | --- |
| `advantage-brief`, `run-of-show` | Verified writable AGI Course Development parent and the applicable output checks. |
| `canva-chapter` | Verified `owner` and `owner_url`; exact `brand_book_id`, `kit_id`, `deck_id`, `master_notes_id`; `brand_url`, `append_route_url`, `master_notes_route_url`. No duplicate assets. |
| `presenter-notes` | `notes_write_url` and `notes_read_url` for actual Canva Notes, not a sidecar or a slide-face editor. |
| `internal-video` | Existing `avatar_id` and `voice_id` with `voice_kind: professional` and `avatar_voice_url`; `capture_machine: ember-m2`, `capture_route_url`, `sanitization_route_url`, `renderer_route_url`, `internal_hub_route_url`. Read the video workflow's verified private capability receipt; authenticated inventory alone is not render evidence. |
| `canva-video-slide` | `embed_route_url`, `playback_route_url`, `external_exclusion_route_url` for playable media in one dedicated slide in the existing deck, and a route that excludes it from external teaching. |

Never report a week closed from a feasibility pass. Missing or unverified ownership, brand, capture, privacy, save, playback or exclusion is a linked HR gap, not a deferred section that can be marked ready.

## Run the gate and handle its result

Pass the private preflight JSON to `python3 scripts/check_completeness.py` via stdin from the skill directory. Keep real inputs and stdout out of the public repo and avoid logging private data. The script checks reconciliation and the evidence fields, not what the linked documents say. Open and verify the links when assembling preflight. If the runner is unavailable or refuses the input, no output writes are allowed.

- Top-level `route` is `week` or `session`. For `week`, provide a nonnegative integer `week`. `checks` maps each required check name to `{inventory_url, expected, evidence}`. `expected` is the independently inventoried list of item keys. `evidence` is an object keyed by those same keys; each row has `status` and `url`. For `readiness` and `sources` add `reason`; for `tools` and routed `decisions` add `owner`; for `decisions` add `receipt_url` pointing to the Change Log receipt or actual owner route. Use `url` to identify the decision itself.
- To report an inaccessible inventory or incomplete retrieval, do not submit it as read: omit that check and attach its real attempted source link to the private gap report. An empty tools, decision or source inventory is valid only when an exhaustive read confirms no items, with the inventory link retained.
- Exit `1` or `2`: stop. Send HQ Chief HR Officer a plain private report with the exact week/cohort or session, each missing item or inaccessible source, its inventory/item link and the owner or next recovery action. Report known Week 10 gaps without invoking or writing the Week 10 package. Do not create, update or append package artifacts on a failed preflight.
- Exit `0`: retain the linked preflight in the private run record and proceed to the whole package, including the internal video and embedded slide. If the source, identity or evidence changes before saving, reconcile the affected preflight evidence and rerun the gate. A pass never substitutes for post-save verification.
