# Analysis Method Notes (hard-won details)

## Shot detection accuracy
- Two-pass scene detection is mandatory: hard threshold (~0.25) for the skeleton, soft (~0.12) for dissolves. Every disagreement gets visual verification via start/end frames. Common false positives: whip pans, handheld drift, subject crossing frame, sun flares.
- Fades: a fade-from-black leader registers as its own tiny "shot". Merge into the first real shot and renumber. Check the tail for fade-outs into logo cards.
- Long "single takes" flagged by the soft pass are often continuous handheld shots, not cuts. Confirm by extracting 4–6 frames across the span and checking continuity of background.
- Record shot observations in batches while viewing review grids (~12 shots per grid) into a running notes file immediately, because multimodal observations are lost after context compression.

## Transcript and cadence
- Run STT even when an SRT is provided; diff them. SRT files are often auto-generated with different line timings, dropped fillers ("that that", "not, not"), or corrected grammar. The *imperfections* are analytically important (interview-vs-teleprompter evidence).
- Word-level timing JSON from STT enables per-segment WPM. Slowest segments usually mark the emotional core; note where the edit pairs them with the longest-held shots.

## Interview-film pattern recognition
Signals that the reference is an interview edit (the dominant luxury-agent format): two fixed seated angles (A frontal / B profile) in one wardrobe; B-angle cuts hiding mid-sentence edits; conversational run-ons; audio continuing as VO over b-roll. Quantify the interview share of screen time. It is usually the headline finding (Ramey: 55%).

## Asset audit discipline
- **Never classify from filenames.** Download samples, extract frames, view them. In practice: "C1253.MP4" turned out to be a realtor-association classroom, not property footage; a "lifestyle photos" folder was an AI-generated pack unusable on screen.
- Flag AI-generated headshot/lifestyle packs as do-not-use in film: identity drift and synthetic texture destroy the authenticity that the interview format depends on. They may serve as *supplementary* identity references only, always subordinate to real photographs.
- Check video metadata early (`videoMediaMetadata` via gws, or ffprobe after download): orientation surprises are common (a "cinematic reel" may be vertical 1080×1920 → needs outpainting for 16:9 use).
- Rights triage: stock packs found in client folders need license-scope confirmation (image license ≠ video use); third-party skyline photos and footage inside other producers' edits are do-not-use.
- Privacy triage: personal iPhone videos and event recordings with non-consenting attendees require explicit client sign-off (put in questionnaire).
- Shared-drive folders need `supportsAllDrives: true, includeItemsFromAllDrives: true, corpora: "allDrives"` in gws params; a plain `files get` 404 on a valid ID usually means it lives on a shared drive.
- Upload deliverables back with rclone using `root_folder_id` remotes: `rclone copy <file> "manus_google_drive,root_folder_id=<FOLDER_ID>:"`.

## Strategic-analysis anchors
- The origin story is the differentiator to hunt for: an unusual, uncopyable institution/experience convertible to a client benefit in one sentence (funeral home → "hold their hands"; film school + trading floor → "produced like a film, priced like an asset").
- The conversion law: every personal fact must become a client benefit within one breath. Audit both the reference and the substitution framework against it.
- Restraint inventory: no CTA, no logo walls, no credential graphics, stillness at the close. These absences are usually what makes the reference feel expensive. Name them explicitly.
- Agent-presence budget: count agent-in-frame b-roll share; luxury references keep the agent as "guide, not star" (~20–25% of b-roll). Carry the number into production plans.
- AI usage rule for the adaptation: AI only for invisible work on owned pixels (upscale, outpaint/reframe, still-to-video push-ins, restoration). Never synthesize the client's face, body, or on-camera speech; never let AI b-roll carry architecture that can warp.
