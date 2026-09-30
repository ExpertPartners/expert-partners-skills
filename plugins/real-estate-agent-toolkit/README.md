# Real Estate Agent Toolkit

Forty portable AI skills for real estate agents. They work with any AI assistant that can
load skills or read a text file. Every skill shares one profile file, `agent-profile.md`,
written by the Agent Brain Builder. The contract is in
[agent-profile-contract.md](skills/agent-brain-builder/references/agent-profile-contract.md).

## Ground rules every skill follows

- The agent's own brand, voice, offer, content, or business documents always win over the
  profile and over any default in a skill. A skill may help create a missing capability but
  never silently replaces an existing authoritative source.
- Skills read `agent-profile.md` (or the legacy name `claude-brain.md`) and never edit it.
  Only the Agent Brain Builder writes it.
- Skills write and prepare. They never send, publish, or schedule on their own.
- When an integration is unavailable, or an action fails, the skill says what is unavailable,
  delivers a manual fallback, and never claims an action happened unless the tool confirms it.

## Skills by function

Setup and positioning
- agent-brain-builder: interviews the agent and writes `agent-profile.md`
- brand-direction-builder, offer-usp-skill, agent-bio-writer
- business-plan-builder, daily-planner
- market-research-skill, competitor-analysis-skill

Social and short-form content
- content-multiplier, hook-generator, reel-script-writer, carousel-writer
- instagram-story-skill, this-week-in-city-writer

YouTube and video
- youtube-channel-setup-skill, youtube-video-ideas-skill, long-form-script-writer
- youtube-seo-skill, video-repurposer-skill, market-video-scripter

Lead generation, follow-up, and proof
- lead-magnet-builder, lead-magnet-delivery-scripts, lead-follow-up-email-writer
- client-follow-up-writer, objection-response-writer
- newsletter-writer, real-estate-postcard-writer
- review-referral-writer, client-case-study-writer

Listing and client lifecycle
- listing-marketing-skill, open-house-kit-writer, pre-listing-package-writer
- client-welcome-pack-writer, google-business-profile-skill, listing-ad-copy-skill

Named-app skills
- notion-content-board-builder, gamma-presentation-builder, canva-assistant
- gmail-assistant, metricool-post-scheduler

## Named-app dependencies

| Skill | App | Kind | Without the app |
|---|---|---|---|
| gmail-assistant | Gmail | optional integration, drafts only | emails as copy blocks |
| canva-assistant | Canva | optional integration, drafts only | full layout spec |
| notion-content-board-builder | Notion | optional integration | board as a visual page and document |
| metricool-post-scheduler | Metricool | optional integration, drafts only | platform-formatted pack |
| gamma-presentation-builder | Gamma | optional integration | deck plan and one paste-ready Gamma prompt |
| google-business-profile-skill | Google Business Profile | target app, paste-by-paste | the same package, always manual |
| youtube-channel-setup-skill | YouTube Studio | target app, checklist | the same checklist, always manual |

Other skills use web search when the tool has it (market-research-skill, competitor-analysis-skill,
this-week-in-city-writer, market-video-scripter, agent-brain-builder) and say so plainly when it does not.

## Status

Every skill is `designed`, not deployed.
