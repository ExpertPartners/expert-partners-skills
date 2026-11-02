# Deliverable Specifications

The full package is 15 documents plus a README index. Scale down for smaller briefs (a hero-loop-only analysis may need only 1, 3, 10, 12, 13, 14), but never skip 1, 3, 10, or 14. Number files `NN_name.md` in one `deliverables/` folder.

## 01 Master source analysis
Verify before analyzing: exact duration, resolution, frame rate (ffprobe); audio-layer structure (music vs. voice segments, use volumedetect/astats per segment); transcript-vs-audio discrepancy log (run STT with `manus-speech-to-text`, diff against any provided transcript, list every mismatch, never silently correct); platform context from the public URL (title, caption, channel). State what is evidence vs. inference.

## 02 Transcript map
One row or block per narrative beat (sentence/phrase/meaningful pause): start–end time, exact words, speaker position (on-camera / VO / off-camera), tone, pace (compute WPM per segment from word-level STT timings), emphasis words, pauses, sentence length, narrative function, viewer question answered, paired visual + visual type (literal / symbolic / atmospheric / archival / lifestyle / credibility), transition out. Preserve original wording exactly.

## 03 Shot list
One row per shot: number, timecodes, duration, words spoken during shot, location, subject, agent-in-frame?, wardrobe code (W1/W2/W3...), props, framing, angle, lens impression, camera movement, subject movement, lighting/time of day, palette/grade, speed treatment, transitions in/out, audio sync, narrative purpose, emotional purpose, luxury/credibility signal, and an **essential / replaceable / decorative** verdict. Group into acts. End with an analytics table: total shots, average shot length, shortest/longest, interview vs. b-roll screen-time split, aerial count, location count, wardrobe count, transition inventory.

## 04 Narrative chapter map
Only chapters actually present (do not force a template). Per chapter: what is revealed, why it sits there, what the viewer feels after, trust mechanism, personal:professional ratio, bridge to next chapter. Include a chapter mechanics table (time, share %, core reveal, trust mechanism, ratio) and a section on what is **deliberately absent** and why. Close with a one-page emotional arc summary.

## 05 Sentence-function analysis
Every major line classified by strategic purpose (identity, curiosity, vulnerability, credibility, place, roots, values→service conversion, local authority, lifestyle, trust, aspiration, emotional close, invitation). Flag: most natural lines, most scripted-sounding, heaviest emotional weight, removable lines, multi-function lines, visually supported vs. delivery-carried lines.

## 06 Cadence and performance analysis
Average WPM, fastest/slowest sections, sentence-length stats, fragments, conversational markers (run-ons, repeats like "that that" are evidence of interview not teleprompter), pauses, energy shifts, confidence vs. vulnerability moments, humor. Conclude with a production judgment: memorized / interviewed / improvised / assembled. Provide a reusable **cadence template** (pattern only, no words).

## 07 Word-visual relationship map
Per beat: direct illustration / emotional reinforcement / contrast / symbolic / location establishment / archival proof / lifestyle proof / credibility proof / personal texture / transitional atmosphere. Identify where the film deliberately avoids literalism and explain why that prevents promotional flatness.

## 08 Production-method analysis
Narration recorded before or after filming; interview-edit vs. scripted VO; staged vs. documentary scenes; location count; wardrobe count; estimated shoot days; participants; drone use; licensed footage; archival material; location audio; music-driven editing; crew estimate; which elements create the perceived production value. Separate visual evidence from inference explicitly.

## 09 Story substitution framework
Chapter-by-chapter table mapping reference function → client's equivalent. Columns: original function, original beat, what viewer must learn, emotional purpose, personal story type, professional proof type, suggested interview questions (reference #11), visuals from client's life, local-market visuals, career material, on-camera vs. VO, target duration. **Ground every candidate fact in located documents; mark unknowns REQUIRES YOUR INPUT. Never invent biography.** End with the structural rules that must survive translation.

## 10 Existing asset audit
Every located asset: exact filename, folder path, contents (verified by viewing, not filename), date, quality/resolution, which beat it supports, classification, required work, rights/privacy concerns. Use the 8-category classification: (1) use as-is, (2) normal edit/color, (3) AI enhancement, (4) AI background/location replacement, (5) motion reference for AI shot, (6) identity/character reference, (7) do not use, (8) missing. Close with a shape-of-the-library summary (what's covered vs. empty).

## 11 Missing-story questionnaire
Chapter-grouped interview questions engineered for vivid, filmable answers (sensory moments, named people, specific scenes), never "tell me about your journey." Include a production-and-permissions section (participants, consent, locations, licenses, wardrobe, off-limits topics). Recommend voice-memo answers (client cadence feeds the script).

## 12 Missing-asset inventory
Every missing visual grouped by footage family (interview / agent-in-environment / aerials / lifestyle / craft inserts / archival / brand close), each classified FILM / LICENSE / AI-FROM-OWNED / PICKUP / OPTIONAL. End with a 3-item priority list ("if only three acquisitions happen").

## 13 Production pathways
Three options: A = existing-assets/archive only, B = minimal-shoot hybrid (usually the recommendation floor), C = premium full production. Per option: assets used, missing assets, AI tools, pickup shots, editing requirements, strengths, realism/continuity risks, which reference chapters it can reproduce structurally, what should intentionally differ, complexity in shoot days. Comparison table + recommendation logic. No vendor pricing without evidence.

## 14 Storyboard contact sheet
Numbered grid, one representative frame per shot with exact timecodes and durations (`scripts/build_contact_sheet.py`). Shot numbers must match #03 exactly.

## 15 Creative summary
One page of prose: why the source works (structural devices, persuasion engine, visual grammar, restraint) and what must carry into the client's version vs. what must be natively theirs.

## 00 README index
Table of all deliverables + the 3–5 findings that matter most + exactly what is needed from the client to proceed. This is the entry document; write it last.
