# Gamma Integration Routing

Use this reference only when Gamma tools are available or when deciding whether a requested Gamma action is supported.

## Create a new presentation

Use the Gamma `generate` action for a new presentation created from the conversation, an outline, or fully written slide content.

When the deck structure is already fully written:

- send the complete relevant deck content, not a summary
- use presentation format
- prefer preserve mode when the slide copy is already final and should not be rewritten
- use explicit input breaks when the integration supports honoring card boundaries and the deck has already been divided slide by slide
- specify the card count only when the user requested an exact count or the prebuilt structure requires it
- request 16:9 only when presentation dimensions matter to the request

Do not add optional generation settings just because they exist. Let Gamma use defaults unless the user asked for or clearly implied a preference.

## Use a Gamma template

If the user identifies an existing Gamma template as the starting point, use `generate_from_template`, not ordinary generation.

- Use only a real accessible template ID returned by Gamma or explicitly supplied by the user.
- Do not invent or guess a template ID.
- If discovery is needed, list accessible Gamma templates and choose only from returned results.
- Preserve the user's supplied source content verbatim when the integration instructs you to do so.

## Themes

Use Gamma theme discovery when the user explicitly asks for or describes a visual style that requires theme selection.

- choose from returned theme IDs only
- match the theme to the requested tone and subject
- do not invent a theme ID
- if the user gave no visual preference, let Gamma use its default unless known brand requirements make a theme lookup necessary

## Folders

Use Gamma folder discovery only when the user asks to organize the new presentation into a folder. Do not guess folder IDs.

## Exports

Request an export only when the user explicitly asks for PowerPoint, PDF, or PNG output.

- return the export URL when confirmed
- note that generated export URLs may expire
- do not imply an export exists until the integration confirms it

## Sharing and publishing

Do not change workspace access, external access, email sharing, or publishing settings unless the user explicitly requests them.

Creating a Gamma is not the same as publishing it.

## Existing Gamma limitations

The available generation actions create new Gamma content. Do not promise to revise or refine an existing generated Gamma in place when no editing action is available.

After creating a deck:

- share the returned editable Gamma URL
- tell the user to use Gamma's editor for layout, theme, or copy refinements that require editing the existing asset
- do not offer an integration-based "tweak" unless a future tool explicitly supports editing

## Speaker notes

The current generation schema does not expose a dedicated presenter-notes field.

Therefore:

- always keep the speaker-note script in the chat output
- include notes in source text only as clearly labeled material when useful
- never claim Gamma inserted them into a dedicated notes panel unless a tool result explicitly confirms that capability
