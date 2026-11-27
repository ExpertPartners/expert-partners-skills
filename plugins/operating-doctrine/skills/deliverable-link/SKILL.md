---
name: "deliverable-link"
description: "Every deliverable Claude creates or updates for Allison lands with a markdown hyperlink whose link text is the exact document name. Fires on every create, update, or delivery of any document, file, design, page, board, base, record, or repo artifact in any system (Google Drive, Notion, GitHub, Canva, Miro, Airtable, ClickUp, Gamma, Lucid, or anywhere else that returns a URL), and on every later reference to a deliverable's location. Also use for Allison's explicit share this request for one Drive file; ordinary delivery never authorizes public sharing. Telling Allison where something is without handing her the clickable link is the failure condition this skill exists to remove. It inherits the operating-doctrine and never overrides it."
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
tier: plugin
zone: routing
status: live
inherits: operating-doctrine
brand-scope: null
subtitle: "deliverables land as named markdown links"
---

# Deliverable Link Standard

Ruled by Allison Gaddy, August 4, 2026, after a Session Close and Continuity Prompt v2 delivery landed as a title and a location description with no clickable link. Permanent, always on, every project, every session, every surface.

## The rule

When Claude builds, updates, or delivers anything that lives at a URL, the confirmation in chat carries a markdown hyperlink and the link text is the document's exact name. Like this, [2026-08-04 Session Close and Continuity Prompt v2](the Doc's URL). Never a raw URL. Never a location description standing in for a link ("it's in your Drive", "check the repo", "I pushed it to intake"). The link is the delivery. The name on the link matches the name on the file, including the YYYY-MM-DD prefix when the file carries one.

This standard extends to every automated sender on every rail. A robot's link text is always the exact document title, never a bare URL.

## What fires it

Every created or updated Google Doc, Sheet, Slide, or Drive file. Every Notion page or database record. Every GitHub file, commit, or pull request, linked to its github.com page. Every Canva design, Miro board, Airtable base or record, ClickUp task or doc, Gamma, Lucid document, or anything else in any system that returns a URL or an ID a canonical URL can be built from. It also fires on references. If Claude names a previously delivered document later in a conversation, or asks Allison to act on one, Claude links it again in that message.

## How to get the link

First, use the URL the tool result already returned (viewUrl, url, html_url, permalink, share link). Second, if no URL came back but a real ID did, construct the canonical URL from that ID only, never from a guessed or synthesized ID. Third, if neither a URL nor an ID exists, say plainly that no link is available and give the exact path or ID instead, stated as a fallback and named as one, not passed off as normal delivery.

## Format

One markdown hyperlink per deliverable. Multiple deliverables in one response each get their own named link. The link sits inside the two-line summary that the document formatting standard already requires, so chat stays a pointer and the document stays the deliverable.

## Share this, one file only

This is the existing delivery skill's sharing entrypoint, not a second sharing service. Brain folders stay restricted. Creating, updating, mentioning or delivering a link does not authorize public access.

When Allison explicitly asks to share a specific Drive file, do the settings work in that same request. Do not ask her to open sharing settings or confirm a file she already identified unambiguously.

1. Resolve the exact file from her link, file ID, or unambiguous conversation reference. Discover by exact title and owning home when needed, then fetch fresh metadata including `id`, `name`, `mimeType`, `parents`, `trashed` and `shortcutDetails`. A title match alone is not identity; never choose the first duplicate. If the reference is ambiguous, ask one short question identifying which file.
2. Reject a shared-drive root or `application/vnd.google-apps.folder` target. Do not apply this action to a folder, a list of files or a recursive selection. Resolve a shortcut to its actual target and fetch that target's metadata; continue only if it is the specific file Allison meant, not a folder. Stop if the target is missing, trashed, ambiguous or cannot be verified.
3. Read the file's current permissions, including `type`, `role`, `allowFileDiscovery` and inheritance details when available. Preserve named-user, group and domain roles and the file's parents. A file already verified as anyone-reader with discovery disabled needs no mutation.
4. Reuse the connected Drive action `make_public` for that exact file ID with `role: "reader"` and `allow_file_discovery: false`. If an anyone permission already exists but needs its role or discovery corrected, update only that file's existing anyone permission with those same settings instead of adding a duplicate. Never grant commenter or writer access.
5. Never widen a parent, brain folder, shared drive or another file. Never change inherited permissions, move or copy the file into a public home, or relax an organization policy to make sharing succeed. If the only available permission is inherited and cannot be changed on this file alone, report that exact gap without changing its source.
6. Read back permissions on the same resolved file ID. Confirm anyone-reader with discovery disabled, unchanged parents and unchanged named grants before saying the file can be viewed with the link. If an action errors or delivery is uncertain, inspect the actual state before any retry; do not claim success from the attempted call.
7. Return the resulting URL as a Markdown link whose text is the exact verified file name, with a short confirmation that anyone with that link can view this file only. Say precisely what failed if no verified share link could be delivered.

Use the equivalent supported Drive permission action if the surface names its tools differently, with the same exact-file checks and reader-only settings. If no write-capable route is available, report that route gap; do not ask Allison to change folder access. Other platforms keep their own explicit sharing actions and permissions.

## Failure condition

Any confirmation that a deliverable exists without its hyperlink in the same message. Any bare raw URL. Any sentence shaped like "I made it, it's in X". If a slip is noticed mid session, re-deliver the link at once.

## Where this standard lives

This file, in expert-partners-skills (plugins/operating-doctrine/skills/deliverable-link/), is the canonical copy. Surfaces receive it through the plugin marketplace.
