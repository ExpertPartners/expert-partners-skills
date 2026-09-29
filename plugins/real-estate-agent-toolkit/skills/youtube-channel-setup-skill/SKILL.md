---
name: youtube-channel-setup-skill
description: Set up or repair a real estate agent's YouTube channel so the profile is clear, searchable, conversion-ready, and easy to maintain. Use when the agent asks to set up a YouTube channel, fix an existing channel page, write the channel description, create channel keywords or playlists, plan banner copy, organize profile links, configure the Home tab, or choose upload defaults. Deliver a paste-by-paste YouTube Studio checklist for either a new channel or an existing one.
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
tier: plugin
zone: content
status: designed
inherits: []
brand-scope: null
subtitle: "YouTube channel setup checklist"
---
# YouTube Channel Setup

Set up a real estate agent's YouTube channel so a new visitor immediately understands who the agent helps, where they work, what the channel covers, and what to do next.

## Workflow

1. Determine the mode: `NEW` or `EXISTING`.
   - Infer `EXISTING` from language such as "fix my channel," a pasted current description, screenshots, or a channel URL.
   - Infer `NEW` from language such as "starting a channel" or "set up my channel."
   - If the user explicitly names the mode, use it.
2. Reuse known context before asking anything.
   - Use the agent profile (`agent-profile.md`, or the legacy name `claude-brain.md`) and any brand, voice, or offer documents the agent keeps, plus any other available context for market, niche, proof, CTA, links, and voice rules. The agent's own documents win over this skill's defaults.
   - Never re-ask for facts already available in the conversation or project.
3. Ask at most one batched question message when essential information is missing.
4. Build the setup in the exact output structure below.
5. For `EXISTING` mode, preserve accurate facts, valid links, and useful brand language. Rewrite only what needs improvement.
6. Deliver instructions for manual setup in YouTube Studio. Do not publish, change settings, or connect accounts unless the user separately asks for an available tool-assisted action.

## Minimum inputs

Use these when available:
- Channel mode: new or existing
- Agent name or brand/channel name
- Primary market or geographic focus
- Main audience or niche
- Primary CTA
- Website or lead-capture link
- Optional secondary links: booking page, Instagram, Facebook, LinkedIn, newsletter, relocation guide, buyer guide, seller guide
- Existing channel description or public channel URL for repair work

If information is missing, ask one compact message with only the missing items. Accept short, messy answers. If the user skips optional fields, finish with placeholders instead of stalling.

### Default question message

Use only when needed:

> I can build the whole channel setup in one pass. Give me whatever you have, messy is fine:
>
> 1. New channel or fixing an existing one? If existing, paste the current channel description or channel link.
> 2. Your market + the people you most want the channel to attract.
> 3. The one action you want viewers to take, plus the best link for it.
> 4. Any other links you want on the channel (optional).
>
> If you do not know an answer, skip it. I will use a clean placeholder instead of holding up the setup.

## Output structure

Use these exact section names and keep them in this order.

### CHANNEL POSITIONING
Provide:
- Recommended channel name, only if the user has not already locked one
- Recommended handle pattern, only if the handle is not already locked
- One-sentence positioning line in this form: `[WHO YOU HELP] + [WHAT YOU HELP THEM DO] + [WHERE]`
- 3 to 5 core content pillars that the rest of the channel should reinforce

Do not force a rename on an established personal brand. If the existing name is strong and clear, say to keep it.

### CHANNEL DESCRIPTION
Write one finished channel description, ready to paste into YouTube Studio under `Customization > Profile > Description`.

Requirements:
- Open with the market and viewer intent, not a résumé.
- State who the channel is for and what viewers will learn.
- Work the market and real estate search language in naturally. Do not keyword-stuff.
- Include the agent's differentiator or proof only when it is real and relevant.
- End with one primary CTA.
- Keep the copy scannable and human.
- Do not create a separate "About section" version. The current YouTube channel description is the profile description surfaced on the channel.

For `EXISTING` mode, start this section with one sentence: `What I changed: ...`

### 6-PLAYLIST STRUCTURE
Create exactly six playlists. Each playlist must include:
- Playlist title
- One-sentence purpose
- 3 to 5 starter video topics

Use this default architecture unless the user's niche calls for a better version:
1. Moving to [MARKET]
2. Living in [MARKET]
3. [MARKET] Neighborhoods & Communities
4. [MARKET] Real Estate Market & Money
5. Buying a Home in [MARKET]
6. Selling a Home in [MARKET]

Adapt the six categories for luxury, relocation, new construction, investing, condos, acreage, or another clearly stated focus. Never invent neighborhood names.

### BANNER TEXT BRIEF
Provide:
- Primary headline, ideally 3 to 7 words
- Supporting line, ideally 8 to 14 words
- Optional upload cadence line only when the user has a real cadence they intend to keep
- Primary visual direction in one sentence
- Placement note: keep all critical text and logos inside the safe area

Use current YouTube banner guidance from `references/youtube-studio-map.md` when dimensions are useful.

Do not cram contact information, multiple CTAs, or a paragraph into the banner.

### LINKS & CONTACT
List links in recommended display order.

Rules:
- Put the single highest-value CTA first because the first profile link receives the most prominent placement.
- Prefer a direct lead-capture, relocation guide, home search, home valuation, or booking link over a generic social profile when that link exists.
- Then list the website and strongest supporting social/profile links.
- Provide a short display label for each link.
- Include the business contact email only if the user provides or confirms it.
- Never invent a URL, email address, phone number, or social handle.

### CHANNEL KEYWORDS
Provide 12 to 20 channel keywords, comma-separated, ready to paste under `Settings > Channel > Basic info > Keywords`.

Mix:
- Market terms
- Real estate intent terms
- Niche terms
- Relocation terms when relevant
- Agent or brand name

Avoid repetitive keyword stuffing, irrelevant cities, brokerage recruiting terms unless that is genuinely part of the channel, and claims the user does not make.

### HOME TAB LAYOUT
Recommend the channel Home tab order under `Customization > Home tab`.

Use this default order when enough content exists:
1. Channel trailer for non-subscribers
2. Featured video for returning subscribers
3. Start Here / Moving to [MARKET]
4. Neighborhoods & Communities
5. Buying in [MARKET]
6. Selling in [MARKET]
7. Market & Money
8. Recent uploads

For a brand-new channel with few videos, explain which sections should wait until videos exist. Do not create empty-looking rows just to fill the page.

### UPLOAD DEFAULTS
Provide a conservative, practical default setup for `Settings > Upload defaults`.

Always cover:
- Default description footer: short evergreen bio + primary CTA + contact/link placeholders
- Default visibility: recommend `Private` unless the user has a deliberate reason to use another default, so videos are reviewed before publishing
- Default language: use the channel's actual primary language
- Default category: recommend the best fit for the user's content and explain it in one phrase
- Default tags: only evergreen brand/market tags, never video-specific tags
- Comments/moderation: recommend a sensible review setting without pretending one moderation level fits every channel
- License: standard YouTube license unless the user explicitly needs Creative Commons
- Audience: instruct the user to answer the made-for-kids setting accurately for their content; never choose it based on guesswork

Add this note: `Upload defaults apply to browser uploads. Videos uploaded through mobile or some editors may not inherit them.`

### PASTE-BY-PASTE CHECKLIST
Finish with a short numbered implementation checklist in the order the user should do it inside YouTube Studio:
1. `Customization > Profile`: name/handle if needed, description, links, contact info
2. `Customization > Profile`: profile image and banner
3. `Settings > Channel > Basic info`: channel keywords
4. `Content > Playlists`: create the six playlists
5. `Customization > Home tab`: trailer, featured video, and sections
6. `Settings > Upload defaults`: basic info and advanced settings
7. Final QA: desktop + mobile visual check, test every link, confirm CTA, confirm banner text is not cropped

Then add:

`Why this works:` 2 to 3 sentences explaining the strategy specific to this agent and market, plus the single most useful next action.

End with one tailored follow-up offer, such as:
- `Want me to build the first 20 YouTube video ideas for these playlists?`
- `Want me to turn the banner brief into a design-ready Canva/Adobe brief?`

## Current YouTube Studio rules

Read `references/youtube-studio-map.md` when giving UI paths, banner dimensions, link limits, or upload-default behavior.

If the user reports that YouTube Studio looks different from the reference, verify the current YouTube Help flow before giving click-by-click instructions. Platform navigation changes; do not bluff.

## Quality rules

- Make the channel about the viewer's questions, not the agent's résumé.
- Use natural search language: `moving to Frisco Texas`, not a pile of near-duplicate keywords.
- Localize with real markets and communities only. Never invent a neighborhood, development, school district fact, market statistic, ranking, or award.
- Attribute any researched market number with source and date.
- Do not claim guaranteed ranking, leads, subscribers, or income.
- Keep one primary CTA across description, first profile link, and upload-default footer whenever possible.
- Preserve the user's established brand language when it is already clear and effective.
- If the channel serves multiple business lanes, choose one primary viewer promise and organize secondary lanes underneath it instead of making the channel sound like several unrelated businesses.
- Fair housing: describe properties, amenities, location, housing stock, and observable lifestyle features. Do not describe protected classes, imply who belongs in an area, or steer viewers toward or away from communities based on demographics.
- Avoid legal, tax, lending, or investment guarantees. Refer viewers to the appropriate licensed professional when needed.
- Match the user's actual voice. Without a voice profile, use warm, direct, plain-language copy.
- Avoid generic AI filler such as `unlock`, `supercharge`, `game-changer`, `revolutionary`, `secret weapon`, and `leverage` as a verb.
- Prefer concise copy over marketing fog.

## Existing-channel audit rule

When repairing an existing channel, classify each current element as one of:
- `KEEP`: already clear and useful
- `TIGHTEN`: factually sound but weak or vague
- `REPLACE`: confusing, duplicated, stale, off-brand, or not aligned with the channel's audience
- `ADD`: missing but materially useful

Use the classification internally. In the final output, summarize the changes in plain language rather than dumping a long audit table unless the user asks for one.
