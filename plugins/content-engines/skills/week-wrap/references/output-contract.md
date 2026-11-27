# Week Wrap output contract

This is the reusable output shape, not a copy of business knowledge. Resolve facts, brand rules and operational identities live. Use a neutral teaching title that does not reveal a source instructor or training program.

## One-page advantage brief

After passing [prewrite completeness](completeness-gate.md), save a Google Doc named Week Wrap, {teaching title}, Advantage Brief in the resolved AGI Course Development folder.

Use these sections in order.

1. The lesson, the audience and the practical change
2. What we built, with the actual current status
3. What makes our implementation different and why it matters
4. The durable advantage, the mechanism that could endure and the evidence or hypothesis label
5. The competitor check, an observable test and what would disprove the advantage
6. What is not proved yet and the learner's next practical action

Keep the rendered document to one page without shrinking it below the live formatting standard. Use fewer words, not smaller type. Keep restricted provenance in the private run log and evidence map rather than copying it into the brief.

## Live-class run of show and talking points

Save a Google Doc named Week Wrap, {teaching title}, Live Class Run of Show in the same AGI Course Development folder.

Begin with the central lesson, audience, total duration, learner outcome, required setup and what is proposed rather than decided.

Then use a table with elapsed start and end, duration, segment, chapter slide identities, learning purpose, substantive talking points, demonstration or learner action, transition, and fallback if a live demonstration is unavailable. Include the opening, lesson context, explanation, practical example, exercise, debrief, questions and close. Sum all segment durations to the total. Keep fictional examples and proposed timings visibly labeled.

Close with likely learner questions and source-grounded answers, known limits and one practical next step. Talking points remain useful for rehearsal but never replace the full speaker-note scripts.

## Chapter in the existing Canva master teaching deck

Use the one existing master teaching collection resolved from the live owning record or assignment. Append one transformation-named chapter or revise the matching existing chapter in place. Put its source week only in the existing internal master Notes document. Do not create a second deck, kit or brand.

Map the chapter to the run of show. For each slide record its stable page identity, title, teaching purpose, concise on-slide copy, visual treatment and full speaker-note script. Put the script in Canva's actual speaker notes, not solely in a companion Doc or chat.

The script includes the exact spoken opening, explanation of terms, lesson origins in our own implementation and reasoning, concrete example, observed proof and limits, demonstration narration or complete fallback, exercise instructions and debrief where applicable, and the spoken transition. Stage cues are separate from spoken words. Include a full script even for title, exercise and closing slides.

Preserve the current deck's unrelated chapters and use its exact personal-brand kit. Record page identities as well as page numbers because numbers can shift when other chapters are added.

## Internal Hub video and dedicated chapter slide

Use the existing rendering and internal-publishing workflow with the stable package key. Resolve any prior render and slide before creating either. Save exactly one chapter video, up to 180 seconds, for Don, the team and future human and AI hires. The real Ember M2 recording shows the Hub, Drive brains and an AI department doing real work. Use the approved existing Allison avatar and professional voice in the before-and-after, working-screen and who-uses-it-and-how sequence. Capture only safe views. Inspect the actual frames, audio, captions, previews and destination access for the exclusions in the skill. Never upload unsafe raw capture or give external viewers access to the video.

Embed the same playable video on one dedicated slide of this chapter. Open and play the actual saved slide in authorized context, confirm it is the same video, and verify the external path excludes it and does not expose its underlying assets. The actual slide notes give the full script, what the clip shows and when to play it. Nothing in the external teaching depends on an avatar or access to the private clip.

## Private run log and evidence map

Use the existing Week Wrap Run Log in AGI Course Development, or create one there after confirming no existing record is pending migration. Keep one package record per input identity and separate timestamped attempts within it. Resolve folder, deck, kit and source IDs at runtime rather than copying them into this repository.

Each attempt records these fields.

- Run key and package key
- Started at, finished at and time zone
- Input route and stable input key; keep the chapter's source week only in the existing internal master Notes document and reference that document from the log
- Input basis, recording review, transcript or notes, with coverage limits
- Linked prewrite evidence, preflight outcome and separate post-save package outcome
- Source keys, private source links, versions or modification times and unresolved conflicts
- Evidence map linking each substantive claim to source key, implementation status, observed proof and limitation
- Exact destination folder, master deck and kit identities
- Existing output identities reused and newly created output identities
- Advantage brief title and link
- Live-class run of show title and link
- Existing master-deck link, chapter title, stable page identities and current range
- Actual Canva Notes readback for every page, including the video slide
- Private internal Hub video and media links, render ID, duration, avatar/voice IDs and actual redaction, capture and playback proof
- Dedicated slide identity, in-deck playback, notes cue and external-exclusion proof
- Verification result for each output, timing total and one-page rendering
- Prior chapter preservation and actual browser closure result, if a browser was used
- Status, complete, partial or blocked
- Exact remaining gap and the next action, or none

Private provenance may identify authorized source records, but never copy lead, client or attendee personal information or credentials into the log. Keep the log out of teaching exports and audience links. Do not change access or expose a source to make a citation work.

Use the package key to resume a partial attempt or revise a changed input. Preserve earlier attempts and source versions. The final receipt covers prewrite gate, brief, run of show, chapter with full Notes, internal video, and playable slide. The checker represents the gate as the retained preflight and separates the Notes into its own saved readback row so no page is missed.

### Saved receipt check

Pass the same private input to `python3 scripts/check_completeness.py --saved`, adding a `completion` object with `run_log_url`, `preflight_receipt_url` and `evidence` keyed by the six `package` keys. Each row has the saved artifact `url` and independent `readback_url`. A readback URL must lead to actual private evidence and not a draft, proposed tool action or fixture. Read back the assets once before recording the following fields:

| Key | Additional observed fields |
| --- | --- |
| `advantage-brief` | `rendered_pages: 1` |
| `run-of-show` | `timing_reconciled: true` |
| `canva-chapter` | Transformation `title`, exact `brand_book_id`, `kit_id`, `deck_id`, `master_notes_id`, `master_notes_url`, distinct `page_ids`, `prior_chapters_preserved: true`, `source_week_visible: false`, and for an implementation week `source_week_in_master_notes: true`. |
| `presenter-notes` | `pages` object keyed by exactly those page IDs. Each has `readback_url`, `full_read_as_is_script: true` and `actual_canva_notes_match: true`. |
| `internal-video` | `video_id`, `provider: heygen`, `intent: production` (never promote practice), numeric `duration_seconds`, matching `avatar_id` and `voice_id`, `capture_machine: ember-m2`, `working_recording: true`, `internal_only: true`, `chapter_video_count: 1`, `screens: [hub, drive-brains, ai-department-real-work]`, `redactions_verified: [client-names, deal-prices, private-ag-personal, passwords, don-private-files]`, `audience: [don, team, future-human-hires, future-ai-hires]`, `sequence: [before-after, working-screen, who-uses-it-and-how]`, `hub_url`, `capture_receipt_url`, `redaction_receipt_url`, `media_playback_url` and `internal_access_receipt_url`. Redaction proof includes captions and previews. Count the chapter's saved media from destination readback, not renderer jobs. |
| `canva-video-slide` | Matching `deck_id` and `video_id`, a `page_id` from this chapter, `dedicated_slide: true`, `playback_verified: true`, `external_exclusion_verified: true`, `notes_what_and_when: true`, `playback_url`, and `external_exclusion_url`. |

The checker verifies the shape and cross-references, not the authenticity of evidence or the underlying service operations. Do not translate missing receipts into `true`. Exit 1 or 2 leaves the package incomplete: log actual artifacts and route the linked gap. Only exit 0 with independently observed proof permits a complete receipt.
