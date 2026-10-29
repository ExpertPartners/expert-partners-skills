# File rules for optimized files

The company wide file rules govern everything this tool produces (R31, R32, G13, G14, G23, and the live HQ Rulebook, How we build). Read the live Rulebook first. If it and this page ever differ, the Rulebook wins.

## Names (G13, R31)

[Company][Version] Descriptive Title.md for a company wide file, [Company-Department][Version] Descriptive Title.md for a department file, with the department as one whole word in title case. The identity comes from the source's own name when it carries one, otherwise from the intake. The descriptive title is the intake title, or the source's own title with any system characters replaced. Parts add , Part n of N. The navigation page adds , Navigation. The extension stays .md because that is the shown output type (R19).

Examples. [EP-Product][V1.0] DH IP Bible Interview, Answers Working Copy, Part 2 of 4.md. [EP-Product][V1.0] DH IP Bible Interview, Answers Working Copy, Navigation.md.

## Versions (R31, G14)

The first optimized version of a source is V1.0. When the same source is optimized again, the tool compares the new cleaned text with the version already saved. Unchanged source, nothing new is saved and the message says so. A small change advances the decimal, V1.0 to V1.1. A larger change advances the whole number, V1.0 to V2.0. Small means under about a third of the paragraphs changed, unless the intake says the change is small or large. The measured change is written in the completion message so a person can check the call.

## Save place (R13, R32, G23, Decision Log 2026-10-28, The EP Business Brain gets a Claude Outputs folder)

The optimized files land in the working folder first, then in the Claude outputs folder of the business brain the file belongs to, found by its name, for example Claude Outputs [EP-BB] for an Expert Partners file. Anything made from a file that sits in a brain's Private folder stays in that Private folder. The tool never creates a folder. If the folder cannot be found or reached, the files stay in the working folder and the message says the Drive save is pending and why.

## Archive, never delete (R31, G14)

When a new version replaces an old one, every file of the old version moves into the brain's Archives folder, for example 🗄 Archives [EP-BB], keeping its file ID and history. Nothing is deleted. The message names what moved.

## Copies elsewhere (R31)

A Claude Project or Custom GPT that holds an uploaded copy of the old version needs the new file. This tool does not reach those uploads, so the message names the refresh as the next step for whoever owns that project.
