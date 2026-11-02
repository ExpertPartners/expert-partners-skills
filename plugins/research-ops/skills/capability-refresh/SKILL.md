---
name: capability-refresh
description: Use when a project runs its monthly self-update, or when I ask to refresh a specialist's knowledge of its own tools, software, and the latest Claude, Anthropic, or AI capabilities relevant to its specialty.
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
# Born dressed 2026-11-02 (Decision Log 2026-10-25, Which of the 19 personal
# skills move into the marketplace). Moved in from Allison's claude.ai skills.
tier: plugin
zone: hands
status: live
inherits: operating-doctrine
brand-scope: null
subtitle: "monthly specialist capability refresh"
---

# Capability Refresh

Run a monthly capability refresh for the project that calls you. Focus on that project's specialty, which it will name.

Use the Firecrawl MCP connector as the primary tool. It is connected and paid for, so use it to crawl and check for changes. Fall back to built-in web search and web fetch only if Firecrawl cannot reach a source.

Always check these core sources for Claude and Anthropic changes:
platform.claude.com docs release notes, support.claude.com release notes, code.claude.com docs changelog, anthropic.com news.

Then check the sources specific to this project's specialty: the docs, changelogs, and release notes of the actual software and tools that specialist leverages. The calling project names its tools.

Output:
- Summarize what changed in the last month.
- Update the project's reference file with anything new and relevant.
- Append a dated entry to the project's changelog file explaining what each change means for this specific specialty and my stack.
- Include the source URL for every claim so I can spot check.
- Flag any new capability or opportunity I should act on, and any change that affects how this specialist should work.

Format: no em dashes, no bold, no italics, no dividers, plain text. Voice memo tone. Lead with what matters.
