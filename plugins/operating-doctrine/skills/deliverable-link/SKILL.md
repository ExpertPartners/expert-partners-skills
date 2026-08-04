---
name: "deliverable-link"
description: "Every deliverable Claude creates or updates for Allison lands with a markdown hyperlink whose link text is the exact document name. Fires on every create, update, or delivery of any document, file, design, page, board, base, record, or repo artifact in any system (Google Drive, Notion, GitHub, Canva, Miro, Airtable, ClickUp, Gamma, Lucid, or anywhere else that returns a URL), and on every later reference to a deliverable's location. Telling Allison where something is without handing her the clickable link is the failure condition this skill exists to remove. It inherits the operating-doctrine and never overrides it."
---

# Deliverable Link Standard

Ruled by Allison Gaddy, August 4, 2026, after a Session Close and Continuity Prompt v2 delivery landed as a title and a location description with no clickable link. Permanent, always on, every project, every session, every surface.

## The rule

When Claude builds, updates, or delivers anything that lives at a URL, the confirmation in chat carries a markdown hyperlink and the link text is the document's exact name. Like this, [2026-08-04 Session Close and Continuity Prompt v2](https://docs.google.com/document/d/EXAMPLE). Never a raw URL. Never a location description standing in for a link ("it's in your Drive", "check the aura repo", "I pushed it to intake"). The link is the delivery. The name on the link matches the name on the file, including the YYYY-MM-DD prefix when the file carries one.

## What fires it

Every created or updated Google Doc, Sheet, Slide, or Drive file. Every Notion page or database record. Every GitHub file, commit, or pull request, linked to its github.com page. Every Canva design, Miro board, Airtable base or record, ClickUp task or doc, Gamma, Lucid document, or anything else in any system that returns a URL or an ID a canonical URL can be built from. It also fires on references. If Claude names a previously delivered document later in a conversation, or asks Allison to act on one, Claude links it again in that message.

## How to get the link

First, use the URL the tool result already returned (viewUrl, url, html_url, permalink, share link). Second, if no URL came back but a real ID did, construct the canonical URL from that ID only, never from a guessed or synthesized ID. Third, if neither a URL nor an ID exists, say plainly that no link is available and give the exact path or ID instead, stated as a fallback and named as one, not passed off as normal delivery.

## Format

One markdown hyperlink per deliverable. Multiple deliverables in one response each get their own named link. The link sits inside the two-line summary that the document formatting standard already requires, so chat stays a pointer and the document stays the deliverable.

## Failure condition

Any confirmation that a deliverable exists without its hyperlink in the same message. Any bare raw URL. Any sentence shaped like "I made it, it's in X". If a slip is noticed mid session, fix it immediately by re-delivering the link, do not wait to be asked.

## Where this standard lives

This file, in expert-partners-skills (plugins/operating-doctrine/skills/deliverable-link/), is the canonical copy. Cowork loads its saved operative copy of the same skill; Claude Code applies it via the user CLAUDE.md pointer and the expert-partners plugin marketplace mirror. If the standard changes, Allison rules it, and every copy updates together. The org-provisioned copy in Cowork does not auto-sync; after any change here, Allison re-uploads it per the skills sync ADR.
