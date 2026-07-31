---
name: "video-transcript-relay"
description: "Relay any video to Claude Code for transcription and bring the transcript back to Cowork automatically via Google Drive, with zero clipboard courier work by Allison. Fires the moment a video URL or video file appears in a Cowork conversation with any intent to use what is said in it: transcribe this video, pull the transcript, what does this video say, take this YouTube video and, analyze this reference film, mine this for hooks, turn this training video into a module, or just a bare YouTube, Vimeo, Loom, or Instagram link pasted with an instruction attached. Fires even when Allison never says the word transcribe, because Cowork's network cannot reach video hosts and the fetch must route to Claude Code. Never ask Allison to paste a transcript by hand; that is the failure condition this skill exists to remove. It inherits the operating-doctrine and never overrides it."
---

# Video Transcript Relay

The verified constraint that created this skill, 2026-07-29. Cowork cannot reach video hosts. Two paths were tested live and both failed. The Anthropic web fetcher returns 429 on youtu.be, and a direct curl from the Cowork container returns 403 with header `x-deny-reason: host_not_allowed`, because youtube.com and googlevideo.com are not on the container allowlist. This is a real environment constraint, investigated and verified, not an unfamiliar path.

Claude Code on the M4 has unrestricted network access. So the fetch belongs there. The relay is the system that moves the video one way and the transcript back the other way without Allison carrying anything in a clipboard.

Verified addendum, 2026-07-31. Remote Claude Code sessions (Claude Code on the web, cloud containers) can also run the full relay. yt-dlp installs and fetches YouTube through the session's agent proxy, and Drive delivery works from there too via the write-capable Google Drive connector (see leg three). So the fetch lane is any Claude Code surface, not only the M4. The Cowork constraint is unchanged; Cowork still cannot fetch video hosts.

## The one rule of this skill

Allison never pastes a transcript. She pastes exactly one prompt block, once per video, and confirms. Everything else is machinery.

If a response written under this skill ever asks Allison to open a video, click Show transcript, copy, and paste it back, that response is a doctrine violation and gets rebuilt. The transcript is a file. Files move through Drive, not through her hands.

## The relay, end to end

Four legs. Cowork owns legs one and four, Code owns legs two and three.

Leg one, Cowork. Capture the video reference and the downstream intent. Ship one paste block routed to Claude Code per the code-block-routing skill. Never ship the block without knowing what the transcript is for, or at minimum flagging that the intent is still open.

Leg two, Code. Fetch and clean. Run `scripts/fetch_transcript.sh` with the URL. It resolves subtitles in this priority order, manual English, then manual any-language, then auto-generated English, then auto-generated any-language. It writes a clean plain-text transcript plus a JSON sidecar of the metadata, and it prints both paths.

Leg three, Code. Deliver to Drive. On the M4, upload the transcript to Google Drive using the SA plus DWD path impersonating allison@expertpartners.com, per the systems map. Never the read-only Google connectors. In a remote Claude Code session, where the SA JSON and 1Password CLI physically do not exist in the container, use the session's write-capable Google Drive connector (create_file) instead; verified live 2026-07-31, the file lands owned by allison@expertpartners.com. That connector is not one of the forbidden read-only connectors; the read-only ban exists because read-only connectors cannot write. Report back the Drive file ID, the shareable link, the title, the channel, the duration, the word count, and whether the captions were manual or auto-generated.

Leg four, Cowork. Read the transcript from Drive via the Google Drive connector, then run the downstream skill against it. This is the part that closes the loop with no paste. Cowork can read Drive natively, so once the file lands there the transcript is in context without Allison touching it.

## Where things land

Transcripts go to Google Workspace, in Drive, at `Video Transcripts/`. The canonical folder exists as of 2026-07-31: folder ID `1XARRZWCTC4BJoHxBAL006ObLte3Mvz8D`, at My Drive root, owned by allison@expertpartners.com. Search for it by ID or exact title before uploading; never create a second folder with the same job. Per the systems map, Workspace is delivery and reference, and transcripts are named there explicitly as belonging in Workspace. Transcripts are never canonical, so they never go to GitHub.

Filename, per the document formatting standard, date-prefixed and readable.

```
YYYY-MM-DD <Channel> - <Video Title> transcript
```

The raw transcript file stays plain text. It is working input, not a deliverable, so it does not get Poppins treatment. Anything Claude then writes from the transcript (an analysis, a module, a brief) is a deliverable and does get the full document formatting standard and the styled Google Doc delivery.

## The session lane

All video fetches route to one Claude Code session named "Video Ingest". One lane per workstream. It holds yt-dlp, the script, the Drive delivery path, and the accumulating library of what has already been pulled, so the second video costs a fraction of the first.

Register it in the code-block-routing known-sessions list on first use. Route to it as an existing session on every video after the first.

## The paste block template

Routing line above the fence, session name as the first line inside the fence, exactly as code-block-routing requires. One block per response. Substitute the real URL.

```
Video Ingest: this is the session name. If this session is not already named "Video Ingest", make your very first output a request that Allison paste /rename Video Ingest into this session's input box, then execute the brief below.

Fetch and deliver a video transcript.

URL: <URL>

1. Ensure yt-dlp is present. If missing, install it (pipx install yt-dlp, or brew install yt-dlp).
2. Run the relay script from this skill's scripts directory:
   ./fetch_transcript.sh "<URL>"
   If the script is not on this machine, replicate its behavior: pull the best available subtitle track in the priority order manual-en, manual-any, auto-en, auto-any; strip VTT timestamps, cue numbers, positioning tags, and the duplicate rolling lines that auto-captions produce; collapse to clean paragraphs.
3. Report inline: title, channel, upload date, duration, caption type (manual or auto), and word count.
4. Upload the cleaned transcript to Google Drive using the SA plus DWD path impersonating allison@expertpartners.com. Folder: Video Transcripts. Filename: YYYY-MM-DD <Channel> - <Video Title> transcript
5. Return the Drive file ID and the shareable link.
6. If no subtitle track of any kind exists, say so explicitly, then fall back to audio: download bestaudio, transcribe locally with whisper (or faster-whisper), and continue from step 3. Name which path you used.

Do not paste the transcript body into your reply. The Drive file is the handoff. Report the metadata and the link only.
```

That last line matters. A transcript pasted into Code's output just moves the courier problem one surface over. The file is the handoff.

## Downstream routing, what the transcript is for

The transcript is never the deliverable. Something gets built from it. Ask once, up front, before shipping the block, because the answer changes what gets captured in leg four.

Route by intent:

- A reference film, competitor brand video, or About Me video to be adapted, go to brand-film-reverse-engineering. That skill wants structure, cadence, and narrative beats, not just words.
- A hero video or website film for a listing or a market, go to hero-video-preproduction.
- A training video, SOP walkthrough, or onboarding session, go to gemini-notebook-training-architect.
- Raw material to be mined for hooks, posts, reels, or scripts, go to rare-content-engine.
- Positioning, funnel, offer, or campaign strategy from a talk or interview, go to master-marketer-free-agent-builder.
- A recording of Allison's own talk, keynote, or panel, go to the matching brand voice skill, ag-personal-brand for her own platform, fam-epic-brand for coaching and EPIC, moxie-signature-group-brand for Moxie.

If the intent is genuinely unknown, say so on the routing line and fetch anyway. The fetch is cheap and the transcript is reusable. Do not stall the relay waiting on a decision that can be made once the words are in hand.

## Use boundary on other people's video

A transcript of someone else's video is their copyrighted material. It is working input for analysis and adaptation, and it is never output.

What this skill supports: analyzing structure, pacing, hook architecture, narrative sequence, and rhetorical moves, then rebuilding those patterns with Allison's own story, market, proof, and voice. That is the whole premise of brand-film-reverse-engineering and it is legitimate.

What this skill never supports: reproducing a transcript or substantial passages of it as Allison's content, or lightly rewording someone else's script and shipping it as original. If a downstream request drifts toward reproduction rather than adaptation, name the line and redirect to structural adaptation.

Allison's own recordings carry no such limit. Her words are hers.

## Failure modes and what to do

Subtitles disabled entirely on the video. The script says so and exits nonzero. Fall back to the whisper audio path in step 6 of the block. Do not report the video as untranscribable until the audio path has actually been attempted.

Age-gated, members-only, or private video. yt-dlp needs cookies. Have Code export cookies from the browser profile on the M4 and retry with `--cookies-from-browser`. Only if that fails is there a real blocker to name.

Auto-captions come back as unreadable mush. Auto-captions on heavy-accent or music-heavy audio degrade badly. If the cleaned text reads as noise, skip it and go straight to the whisper path, which is materially better on the same audio.

Drive upload fails. Test the SA plus DWD path live before concluding the credential is missing, per the verify-first protocol. Check 1Password across all vaults for the service account JSON. Four verified failures before Allison's hands enter the picture.

Playlist or multi-video URL. Confirm the scope with Allison first, because a fifty video playlist is a different job than one video. Then fetch sequentially with the same script, one Drive file each.

## The hand-off choreography

Per code-block-routing and the pin rule, in this order and no other.

One, the response carries the routing line, the single paste block, and one plain sentence naming what comes back once she pastes. It ends by telling her to say pasted when she has. No pin yet.

Two, Allison pastes and confirms.

Three, only then the pin fires, with a real timestamp from `TZ=America/Chicago date "+%Y-%m-%d %H:%M %Z"`, In flight naming the specific video, Awaiting naming the Drive link and metadata.

Then Cowork reads the file from Drive and the downstream skill runs.

## Version

v1.1, 2026-07-31. First live run (youtu.be/N4Q4iM05PPc, remote Claude Code session) surfaced and fixed three loose ends: the cleaning script now decodes HTML entities (speaker markers arrived as `&gt;&gt;`) and strips non-speech noise tags like `[music]`; leg three gained the verified remote-session Drive delivery path via the write-capable Drive connector; the canonical Video Transcripts folder now exists and its ID is recorded above so no duplicate is ever created. Also moved into the canonical skills repo (plugins/content-engines), which v1.0 never reached.

v1.0, 2026-07-29. Authored for Allison Gaddy. Created after a live verified network block on youtu.be from Cowork, both via the Anthropic fetcher (429) and via direct container curl (403 host_not_allowed). Inherits operating-doctrine, code-block-routing, expert-partners-systems-map, and document-formatting-standard. Overrides none of them.
