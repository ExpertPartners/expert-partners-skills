---
name: "video-transcript-relay"
description: "Fetch a video transcript, save it to Google Drive, and use it for the requested analysis, hooks, posts or training. Use for a YouTube, Vimeo, Loom or Instagram URL or video file with intent to use what is said, including pull the transcript, what does this video say, mine this for hooks, or analyze this reference film. On a local Mac run the bundled script directly. In ChatGPT, Claude chat, Cowork or cloud sandboxes dispatch through the existing Factory connection and read the result from Drive. Never ask the user to paste a transcript or relay a prompt. Inherits operating-doctrine."
tier: plugin
zone: content
status: live
inherits: operating-doctrine
brand-scope: null
subtitle: "video to transcript relay"
---

# Video Transcript Relay

One canonical skill, with execution chosen by the capabilities of the current surface.
The user supplies a video and intent, not a transcript or a prompt for another AI.
Run the work and return the result without paste blocks, pins or manual relays.

## Choose the execution lane

### Local Mac shell

Claude Code, Codex and local Factory Droid on either authorized Mac run
`scripts/fetch_transcript.sh` from this installed skill directly. A shell in a
cloud container is not this lane. Choose the available Mac by resources, not by
product name. M4 work is invisible background work only. All browser and visible
work belongs on Ember's M2.

1. Capture the video URL or file and the intent already present in the request.
   If intent is unknown, fetch anyway and retain that uncertainty.
2. Check for `yt-dlp`, installing it with `brew install yt-dlp` or
   `pipx install yt-dlp` if absent.
3. Run `bash scripts/fetch_transcript.sh "<URL>" "<output_dir>"` from the skill
   directory. It selects manual English, manual any-language, auto English,
   then auto any-language captions, and prints the cleaned text and JSON paths.
4. Read the cleaned text and sidecar. Check that speech is readable, nonempty
   and from the requested video. Use the recovery paths below when needed.
5. Upload to the existing Drive folder, verify the saved content, then return
   the Drive link and metadata. Local paths alone are not delivery.

For a supplied file, use its authorized accessible location. If no captions
exist, transcribe its audio locally with Whisper or faster-whisper and continue
with the same Drive delivery and provenance.

### Chat or cloud surface

ChatGPT, claude.ai chat, Cowork and cloud sandboxes do not fetch YouTube in their
sandbox. Use the existing Factory connection, following `factory-operator`.
Loading this skill does not itself install that connection.

1. Call `find_owner` first with the video and requested work. Reuse a matching
   existing assignment and read its result rather than starting a duplicate.
   Work owned by an existing mission goes through its orchestrator.
2. For a new bounded fetch, call `start_and_watch` once, with the first prompt
   line `Control Room - Video transcript`. Use Auto Model and High autonomy,
   and select an online authorized Mac by current resources. Do not select a
   cloud container for YouTube.
3. Give the session the complete URL or accessible file reference, downstream
   intent, this canonical skill path, and the local-lane steps above. Require
   it to run the bundled script, use the cookies fallback if needed, save and
   verify the transcript in the existing `Video Transcripts` Drive folder,
   and return its Drive file ID and link, title, channel, upload date,
   duration, word count and caption or transcription provenance. Never put
   credentials in a dispatch.
4. Read the completed result through the connection. A session ID or accepted
   dispatch is not completion. Read the actual transcript from Drive through
   the chat's Drive connection and perform the user's downstream request.
   Do not replace a failed fetch with a guessed summary.

If the Factory connection is absent, follow the existing `factory-operator`
Control Room direct line, including its completion receipt. Do not build a new
server or relay, create a platform-only skill, or ask the user to carry a prompt.
If neither the connection nor that existing writable route can be reached,
report the exact attempted route and unresolved execution gap honestly.

## YouTube network and cookies recovery

Verified 2026-11-13, cloud Claude Code containers hit YouTube's
`Sign in to confirm you're not a bot` response with yt-dlp. This supersedes
the 2026-07-31 finding that a cloud agent proxy could fetch successfully.
Chat sandbox host restrictions are a separate limitation. Neither is evidence
that captions do not exist. Route cloud work to the local Mac lane.

On a local Mac, if YouTube requires an authenticated session, retry the script
with yt-dlp's supported browser-cookie option on the authorized existing profile.
For example, on M2 with its existing signed-in Default Chrome profile

```sh
bash scripts/fetch_transcript.sh "<URL>" "<output_dir>" --cookies-from-browser "chrome:Default"
```

The flag reaches both metadata and subtitle requests. Do not export cookies to
a file, print them, copy a profile, send them to a cloud container, or open or
control M4's browser. A profile read is not a browser-control action. Do not
bypass a CAPTCHA or an account-access restriction. If local authentication still
fails, record the actual error and keep the dependent result unverified.

## Drive delivery

Search Drive for the exact folder title `Video Transcripts`, restricted to folders
and not trashed. Use the existing canonical folder, never create a second one.
If multiple results are ambiguous, resolve the owner and location from existing
records rather than picking by name alone.

Use a write-capable Drive connector or the existing service-account plus
domain-wide delegation route. Read-only access cannot upload. Resolve credentials
from 1Password at runtime and never expose them in a response, sidecar or dispatch.
Do not change sharing to public.

Name the plain-text working input

```text
YYYY-MM-DD <Channel> - <Video Title> transcript
```

Read the uploaded file back, check its parent and content against the local text,
and return the Drive file ID and link with title, channel, upload date, duration,
word count and manual, auto-generated or local-audio provenance. Raw text and
metadata are working input, not business knowledge for GitHub. Any analysis,
module or brief produced from it follows `document-formatting-standard`.

## Downstream intent

Use what the user already asked for. Fetching and saving are not completion of a
request for hooks, an analysis or training.

- Reference film or About Me adaptation, use `brand-film-reverse-engineering`.
- Website hero or listing film, use `hero-video-preproduction`.
- Training, SOP or onboarding, use `gemini-notebook-training-architect`.
- Hooks, posts, reels or scripts, use `rare-content-engine`.
- Positioning, funnel, offer or campaign strategy, use `master-marketer-free-agent-builder`.
- The user's own talk, use the matching current brand voice skill.

## Other failures

- No subtitles, exit 3. Attempt local bestaudio download and Whisper or
  faster-whisper transcription, then deliver with audio provenance. Do not
  silently treat an authentication or network failure as absent captions.
- Unreadable auto-captions. Use the local audio path and verify readable speech.
- Drive upload failure. Check the actual write route and matching 1Password
  credential, then the next existing supported route. Do not claim delivery.
- Playlist or multiple videos. Preserve the user's stated scope, process
  sequentially with one Drive file per video, and report the count and links.

## Adaptation boundary

Use another person's video as working input for analysis of structure, pacing,
hooks and narrative, not as a script to reproduce or lightly reword as original.
Build the requested output from the user's own story, proof and voice.
