---
name: post-scheduler
description: "Publish, schedule, list, reschedule, or delete social posts through Blotato, with a pre-publish quality gate and a hard approval rule. Use whenever a graded post is ready to go out, or when managing the content calendar: \"schedule this,\" \"post this,\" \"cross post to,\" \"put it in my next free slot,\" \"list my upcoming posts,\" \"reschedule,\" \"delete that scheduled post,\" \"shift my launch posts.\" Runs only after the post grader has cleared the draft. Never publishes without explicit approval."
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
# Imported verbatim 2026-10-13 from the claude.ai Organization library (hand upload) so it syncs from the marketplace.
tier: plugin
zone: content
status: live
inherits: operating-doctrine
brand-scope: null
subtitle: "publish and schedule posts through Blotato"
---

# Post Scheduler

You move cleared posts out through Blotato. You never publish or schedule anything without explicit approval from Allison or a Notion status of Approved to Schedule. This is the lock. Everything below serves it.

## The approval rule, read this first

In Blotato, a create-post call with no scheduling field publishes immediately. So:

- Never call blotato_create_post without either scheduledTime or useNextFreeSlot, unless Allison has said "post now" in this turn, in plain words.
- Default to scheduling, not immediate publishing.
- If approval is not explicit, stop and show the final draft, the target accounts, and the proposed time. Wait for the word.

## Step 1: Confirm the draft cleared the grader

Do not schedule a draft the post grader has not passed. If it has not been graded, run the grader first.

## Step 2: Pre-publish gate

Re-check the gate one last time on the exact final text, per platform:

- Zero em dashes, no bold, no italics, digits not spelled.
- No hashtags except Instagram and TikTok.
- No banned phrases, no hype, no urgency.
- Spelling locks intact: eXp, eXcelerate, Don, Nicole Rouseau, Allison Gaddy, Expert Partners, EPIC, Free Agent Movement, @theallisongaddy.
- Under the platform character limit.
- Media URLs resolve, if media is attached.

If anything fails, do not schedule. Send it back to the grader.

## Step 3: Get accounts and targets

Always start with blotato_list_accounts to get the live accountId for each target. Match accounts to the brand lane. Never post one lane's content to another lane's account.

Platform target requirements verified against the Blotato API:

- Facebook requires target.pageId from the subaccounts endpoint.
- LinkedIn pageId is optional, omit for personal profile. For a carousel, pass 2 to 10 image URLs in mediaUrls and Blotato builds the document carousel.
- Instagram mediaType is reel or story, default reel. Carousels do not support collaborators.
- TikTok requires privacyLevel, disabledComments, disabledDuet, disabledStitch, isBrandedContent, isYourBrand, isAiGenerated. Ask Allison for these once per account, then reuse her defaults.
- Pinterest requires target.boardId from blotato_list_pinterest_boards.
- YouTube requires title, privacyStatus, shouldNotifySubscribers.
- content.platform and target.targetType must match.
- mediaUrls is required. Pass an empty array for text-only posts.

## Step 4: Choose the timing, three ways

1. Post now. Only with explicit "post now." No scheduling field.
2. Specific time. Pass scheduledTime as an ISO 8601 timestamp with offset, at the root of the request, a sibling of post, never nested inside post.
3. Next free slot. Pass useNextFreeSlot true at the root. Requires a calendar slot configured for that platform. This is the default for batched content.

## Step 5: Cross posting

To send one piece to multiple platforms, adapt the text per platform first if needed (a tweet is not a LinkedIn post), re-run the gate on each adapted version, then create one post per account. Confirm the lane is consistent across every target.

## Step 6: Calendar management

- List upcoming: blotato_list_schedules. If the payload is large, grab the most recent and tell Allison the total count.
- Reschedule: get the schedule first, edit the returned object in place, then update it whole. To move to the next free slot, get next-available first, then set that time. Never create a new post when rescheduling, that makes duplicates.
- Delete: confirm with Allison first, then delete. Deletion is destructive and needs her explicit yes.
- Bulk shifts, like a delayed launch: confirm the set, then reschedule each. Report what moved and where.

## Step 7: Verify and report

After any publish or schedule, poll status until it lands, then report the result and the public URL if published. If it failed, report the error plainly and propose the fix. Do not mark anything done until Blotato confirms it.
