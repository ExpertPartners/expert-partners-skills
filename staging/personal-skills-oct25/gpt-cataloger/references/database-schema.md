# Database schema: Expert Partners Custom GPT Library

This is the exact build spec. Property names are fixed (other parts of the skill
reference them). Select and multi-select options are the working set. When
cataloging, use the closest existing option rather than inventing one. Adding a
new select option is an exception, not a routine move: do it only when there is a
strong reason, and surface it to Allison rather than doing it silently. Route
secondary themes to Suggested Tags and the page body instead of new categories.

## Design decisions worth knowing

- The full 23-section documentation profile is the page body, not a property.
  Properties are the filterable summary; the body is the deep dive.
- `Internal Category` and `Primary Role` are single selects (one primary lane,
  for clean grouping). Cross-cutting labels live in `Suggested Tags`
  (multi-select). This stops two fields from fighting over the same job.
- `Ecosystem Role` is a separate field from `Priority`. Priority is urgency
  (High / Medium / Low). Ecosystem Role is the GPT's place in the system (Core
  Infrastructure, Department-Specific, etc.). Profiles often jam "Core
  Infrastructure" into Priority; move it to Ecosystem Role.
- `Capabilities / Tools` is multi-select for the ChatGPT platform tools only.
  Functional capabilities go in the body.
- `Created By / Doc Owner` and `Recommended Owner` are Select (type any name) so
  an owner can always be recorded even if that person is not a Notion member.
  Flip to People type later if every owner is a workspace member.
- `Related / Companion GPTs` is a self-relation so overlapping or complementary
  GPTs link to each other natively instead of being typed into a text box.

## Step 1: Create the database (DDL)

Call `notion-create-database` with `title` = "Expert Partners Custom GPT Library",
the chosen `parent` page, and this `schema`. (The self-relation is added in Step
2 because it needs the data source ID that only exists after creation.)

```sql
CREATE TABLE (
  "GPT Name" TITLE,
  "Direct GPT URL" URL,
  "Created By / Doc Owner" SELECT('Allison Gaddy':blue, 'Don Hobbs':orange, 'Other Leader':gray),
  "Owning Account / Workspace" SELECT('Expert Partners':blue, 'Free Agent Movement':green, 'Moxie Signature Group':purple, 'Personal':gray),
  "Visible Description" RICH_TEXT,
  "Internal Category" SELECT('Strategy':blue, 'Brand Strategy':purple, 'Marketing':pink, 'Marketing Operations & Execution':red, 'Content':yellow, 'Sales':green, 'Operations':brown, 'Leadership':orange, 'Real Estate':blue, 'Agent Attraction':green, 'Curriculum':purple, 'Brand Voice':pink, 'Coaching':orange, 'Research':gray, 'Admin':brown, 'Discovery':yellow, 'Funnel Architecture':red, 'Client Success':green, 'Other':default),
  "Primary Role" SELECT('Strategist':blue, 'Writer':pink, 'Coach':orange, 'Analyst':gray, 'Trainer':green, 'Architect':red, 'Interviewer':yellow, 'Implementation Partner':purple, 'Brand Voice Assistant':pink, 'Curriculum Builder':green, 'Research Assistant':gray, 'Operations Assistant':brown, 'Discovery Tool':yellow, 'Other':default),
  "Primary Audience" RICH_TEXT,
  "Primary Business Function" RICH_TEXT,
  "Best-Fit Team Users" MULTI_SELECT('Allison':blue, 'Don':orange, 'Leadership Team':red, 'Marketing Team':pink, 'Coaches':orange, 'Operations Team':brown, 'Sales Team':green, 'Admin Team':gray, 'Content Team':yellow, 'Real Estate Team':blue, 'Community Team':purple, 'Client Success':green, 'Brand Strategy Team':purple, 'Funnel Team':red, 'Full Company':default),
  "Best For" RICH_TEXT,
  "Not Best For" RICH_TEXT,
  "Core Knowledge Base" RICH_TEXT,
  "Knowledge Files" RICH_TEXT,
  "Key Frameworks" RICH_TEXT,
  "Capabilities / Tools" MULTI_SELECT('Web Browsing':blue, 'File Analysis':green, 'Image Generation':purple, 'Code Interpreter':red, 'Data Analysis':orange, 'Document Creation':yellow, 'Google Drive':blue, 'Gmail':pink, 'Calendar':green, 'Notion':gray, 'Actions':brown, 'Apps':purple, 'None Visible':default, 'Unknown':default),
  "Actions / Integrations" RICH_TEXT,
  "Conversation Starters" RICH_TEXT,
  "Example Prompts" RICH_TEXT,
  "Required Inputs" RICH_TEXT,
  "Typical Outputs" RICH_TEXT,
  "Voice / Tone" RICH_TEXT,
  "Limitations" RICH_TEXT,
  "Status" SELECT('Not Started':gray, 'Needs Documentation':red, 'Drafted':yellow, 'In Review':orange, 'Ready for Team Use':green, 'Needs Update':pink, 'Archived':brown),
  "Priority" SELECT('High':red, 'Medium':yellow, 'Low':gray),
  "Ecosystem Role" SELECT('Core Infrastructure':red, 'Department-Specific':blue, 'Experimental':yellow, 'Archived':gray, 'Needs Update':orange),
  "Last Reviewed" DATE,
  "Recommended Owner" SELECT('Allison Gaddy':blue, 'Don Hobbs':orange, 'Other Leader':gray),
  "Suggested Tags" MULTI_SELECT('Expert Partners':blue, 'Free Agent Movement':green, 'Don Hobbs':orange, 'Allison Gaddy':blue, 'Brand Strategy':purple, 'Marketing Architecture':pink, 'Agent Attraction':green, 'Real Estate':blue, 'eXp':red, 'Funnel Pilot':orange, 'Content':yellow, 'Voice':pink, 'Discovery':yellow, 'Coaching':orange, 'Operations':brown, 'Strategy':blue, 'Sales':green, 'Curriculum':purple, 'Community':purple, 'Leadership':red, 'Research':gray, 'Implementation':brown),
  "Plain-English Summary" RICH_TEXT,
  "Next Improvement Needed" RICH_TEXT
)
```

## Step 2: Add the self-relation

Fetch the database to get its data source ID (the `collection://...` value).
Then call `notion-update-data-source` with that ID and:

```sql
ADD COLUMN "Related / Companion GPTs" RELATION('<DATA_SOURCE_ID>', DUAL 'Related / Companion GPTs' 'related___companion_gpts')
```

This makes a two-way relation pointing at the same data source, so linking GPT A
to GPT B shows the link on both.

## Step 3: The 10 views

Create each with `notion-create-view` using `database_id` + `data_source_id`.
Use the `configure` DSL shown.

1. **All GPTs** — type table, no filter. (Default landing view.)
2. **Ready for Team Use** — type table.
   `FILTER "Status" = "Ready for Team Use"`
3. **Needs Documentation** — type table.
   `FILTER "Status" = "Not Started" OR "Status" = "Needs Documentation"`
4. **Needs Update** — type table.
   `FILTER "Status" = "Needs Update"`
5. **By Category** — type board.
   `GROUP BY "Internal Category"`
6. **By Primary Role** — type board.
   `GROUP BY "Primary Role"`
7. **By Owner** — type board.
   `GROUP BY "Created By / Doc Owner"`
8. **High Priority GPTs** — type table.
   `FILTER "Priority" = "High"`
9. **Core Infrastructure GPTs** — type table.
   `FILTER "Ecosystem Role" = "Core Infrastructure"`
10. **Department-Specific GPTs** — type board.
    `GROUP BY "Best-Fit Team Users"`
    (Multi-select grouping repeats a GPT under each team it serves, which is the
    point. If Allison prefers one bucket per GPT, switch to
    `FILTER "Ecosystem Role" = "Department-Specific"` on a table instead.)

Optional team-decision view (Step 7 of the workflow): a table named "Which GPT
do I use" with `FILTER "Status" = "Ready for Team Use"` and
`SHOW "GPT Name", "Plain-English Summary", "Best For", "Not Best For", "Best-Fit Team Users"`.

## Profile-to-property mapping

When cataloging, pull these from the documentation profile:

| Property | Source in the profile | Notes |
| --- | --- | --- |
| GPT Name | Section 1 GPT name / Section 19 title | Title property. |
| Direct GPT URL | Section 1 / 19 Direct GPT URL | Must be clickable. |
| Created By / Doc Owner | Section 1 / 19 created by | Add option if new name. |
| Owning Account / Workspace | Section 1 owning account | Default Expert Partners. |
| Visible Description | Section 1 / 2 visible description | The public GPT blurb. |
| Internal Category | Section 1 internal category | One lead value; add option if needed. |
| Primary Role | Section 1 primary role | Lead role only; nuance to body. |
| Primary Audience | Section 1 primary audience | Short summary. |
| Primary Business Function | Section 1 business function | Short summary. |
| Best-Fit Team Users | Section 1 / 5 best-fit users | Multi-select; add options as needed. |
| Best For | Section 11 / 19 best for | Short summary; full list in body. |
| Not Best For | Section 13 / 19 not best for | Short summary. |
| Core Knowledge Base | Section 6 / 19 | One-line summary of the source set. |
| Knowledge Files | Section 2 / 6 knowledge files | The literal uploaded file list. |
| Key Frameworks | Section 9 / 19 frameworks | Named frameworks, comma-separated. |
| Capabilities / Tools | Section 2 capabilities | Platform tools only; else None Visible / Unknown. |
| Actions / Integrations | Section 2 actions | Text. |
| Conversation Starters | Section 2 starters | Text; "Not visible" is a valid value. |
| Example Prompts | Section 17 prompts | A few copy-ready prompts; full set in body. |
| Required Inputs | Section 14 | Short summary. |
| Typical Outputs | Section 15 | Short summary. |
| Voice / Tone | Section 16 | Short summary. |
| Limitations | Section 13 | Short summary. |
| Status | Section 2 status or judgment | Use the workflow status, not the GPT's live state. |
| Priority | Judgment | High / Medium / Low only. |
| Ecosystem Role | Section 21 routing | Core Infrastructure, Department-Specific, etc. |
| Last Reviewed | Section 19 last reviewed | Date. |
| Recommended Owner | Section 19 / 22 | Add option if new name. |
| Suggested Tags | Section 19 tags | Multi-select; add options freely. |
| Plain-English Summary | Section 23 | 2 to 3 sentence team-facing summary. |
| Next Improvement Needed | Section 18 | What to add or clean up next. |
| Related / Companion GPTs | Section 21 complements | Relation; link after both entries exist. |

Status values map to property options exactly: Not Started, Needs Documentation,
Drafted, In Review, Ready for Team Use, Needs Update, Archived.

## Hygiene checklist (Step 6)

Flag any entry that has:

- No Direct GPT URL, or a URL that does not open the GPT.
- No Created By / Doc Owner.
- No Visible Description.
- Empty Core Knowledge Base or Knowledge Files (means the deep dive is missing).
- No Status, or still Not Started / Needs Documentation.
- No Ecosystem Role (unclassified GPTs do not show up in the routing views).
- A near-empty page body (the 23-section profile was never filled in).
- Last Reviewed older than 6 months (Needs Update candidate).

Report gaps as a short list grouped by GPT. Offer to fill what can be filled
from material already provided. Never invent contents to close a gap.
