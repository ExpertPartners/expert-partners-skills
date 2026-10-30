---
name: file-to-knowledge-base-optimizer
description: "Turns a source file, a transcript, a PDF, a Word or Google Doc, a web page, captions or a recording, into clean, structured Markdown ready to load as Claude Project or Custom GPT knowledge. Fires as a slash command or on its own when someone asks to prepare, clean, format or optimize a file for project knowledge, or to combine related transcripts. Six steps. Take in the source, ask one or two intake questions, extract and clean without changing meaning, add a header, summary, takeaways and navigable sections, split anything past about 50,000 tokens into numbered parts with a navigation page, then save by the company file rules into the brain's Claude outputs folder and report the file name, place, parts and anything unreadable. Nothing lost, nothing invented. Speaker labels, timestamps, links and tables stay exactly as the source has them. Built from the approved File to Knowledge Base Optimizer spec, revision 4. Inherits operating-doctrine."
allowed-tools: []
# --- skill-map metadata (zone, tier, status required -- ruling 14) ---
# Born dressed 2026-10-29 (Optimizer Build, Decision Log 2026-10-27, The optimizer spec is approved at revision 4).
tier: plugin
zone: hands
status: live
inherits: operating-doctrine
brand-scope: null
subtitle: "turns any source file into clean, structured knowledge base Markdown"
---

# File to Knowledge Base Optimizer, v1.0 (2026-10-29)

Prepares source files for Claude Project or Custom GPT knowledge. Give it a transcript, a PDF, a Word or Google Doc, a web page, a captions file or a recording, and it returns structured Markdown an assistant can search and cite without wading through formatting debris (R04, R14). The output keeps every fact the source holds and adds none. Where the source showed its shape, the output matches that shape. The requirement IDs in parentheses are lines in the approved spec, [HQ][V1.0] Spec - File to Knowledge Base Optimizer, revision 4, in HQ Company Core. Every instruction here traces to one.

Rulings behind it, all in the live Decision Log. The optimizer spec is approved at revision 4. The optimizer's six open behaviors are decided. Cal's company-wide file rules govern everything every tool produces, always. The EP Business Brain gets a Claude Outputs folder. Read each entry live before relying on it, and never copy its text here. Where this skill differs from the live Rulebook or Decision Log, they win.

## When it fires (R01, R04, R24)

As the slash command, or on its own when someone asks to prepare, clean, format or optimize a file, a transcript, a Notion export or a document for a Claude Project, a Custom GPT or a knowledge base, or asks to combine related transcripts on one topic. Never change an original file. The original stays where it is and as it is.

## Check first

1. Read the live HQ Rulebook, How we build, for the file rules, and the Decision Log entries above (R31, G21).
2. Find where the source lives. Its own name may carry the company or department identity, and a source that sits in a brain's Private folder keeps its output in that Private folder (G13, R32, Decision Log 2026-10-28, The EP Business Brain gets a Claude Outputs folder).
3. Confirm a Python 3 runtime can run scripts/optimize.py in this session. The script has no required dependencies. pdfplumber gives better tables and page layout for PDFs when it is installed (R09, G18, G22).
4. Find the Drive route this session already holds, a connector or the service account the machine is set up with. Never ask for a credential before checking 1Password and the routes already set up (R13, R32).

## Step 1, take in the source (R05, R06, G22)

Accept pasted text, a PDF, a Word or Google Doc, a captions file (VTT or SRT), a Notion or web export, a web page by its address, or an audio or video recording. Save pasted text to a file first. For a Google Doc, fetch the document through the Docs API with every tab included and save that JSON, or export it as a Word file, so no tab is left behind. For a web page, fetch it and save the HTML. Several files are processed one at a time, each with its own run, unless the request asks to combine them (see Combining related files).

Pick the extraction route by source kind. The script does this when the kind is clear from the file. A recording goes through Whisper transcription when it is available in the session. If a file cannot be read at all, stop on that file, say exactly what failed, invent nothing, and continue with the remaining files (G22).

## Step 2, intake, one or two questions (R07, R08)

Ask at most two questions, and none the request already answers.

1. Where will this go, a Claude Project, a Custom GPT, or both, and which company or department file is it, if the file's own name does not already say (for example EP-Product or AG).
2. Is there a title, a date, or a list of who was there that I should use, where the file does not make them apparent.

Skip anything that is not apparent and not answered. Never fill it in. Write the answers to intake.json with these keys. destination, company_file, title, date, people, duration, type, change_size, request. Leave a key empty when nothing is known.

## Step 3, extract and clean (R09, R10, G18)

Run the extractor once per source. It writes the cleaned text, a metadata file, and the parts for Step 5.

```bash
python3 scripts/optimize.py extract --input "<source file>" --work "<run folder>/work" --original-name "<the file's name in Drive>"
```

Extraction is source appropriate. PDF text with tables read as tables, Word and Google Doc structure with headings, lists, tables and links, caption parsing for VTT and SRT, web pages with navigation, menus, scripts and advertising containers removed, and Whisper for recordings (R09). Cleanup removes page numbers, running headers and footers, broken line endings, hyphenation at line breaks and OCR debris, and nothing else. No word is corrected and no meaning changes (R10, G17). Tables stay tables. A scanned page gets readable text with the page image kept beside it. Anything unreadable is marked unreadable and never guessed. Timestamps and links stay exactly as they were (G18). Existing speaker labels are kept exactly, and no speaker identity is ever invented (R11).

Read the extractor's printed summary. It shows the size estimate, the parts, the speaker labels found, the cleanup applied, and anything it could not read.

## Step 4, structure, one part at a time (R11, R15, R16, R17, R18, G19, G20, R33, R34)

For each part in <run folder>/work/parts, read that part's text and write one JSON file in <run folder>/derived, named part-1.json, part-2.json and so on (derived.json when there is one part). Read one part at a time, and use a fresh context per part when the parts are large, so every part gets full attention.

```json
{
  "type": "interview",
  "summary": ["One or two paragraphs that say what this part holds."],
  "takeaways": [{"point": "One substantive point about a claim, decision, method or number.", "support": ["the exact words from the part that say it"]}],
  "sections": [{"heading": "The origin story", "start_line": 1}],
  "actions_decisions": [{"item": "What was decided or must be done", "owner": "", "due": "", "source_line": 12, "support": ["the exact words that state it"]}],
  "people_note": "how the people in the header were identified",
  "could_not_read": [],
  "notes": ""
}
```

Rules for what you write.

- The summary is one or two paragraphs and the takeaways are three to seven points, each supported by the text of that part (R16). Nothing is stated that the source does not say (G19).
- Every takeaway and every action carries the words behind it. Copy at least one passage from the part, word for word, into its support list. The engine checks each quote against the text and refuses a point that has none. Write the point from the quote, not from memory, and attribute it only to the speaker whose labeled words the quote comes from. Both say or they agree is written only when each speaker's own words are quoted (R16, G17, G19).
- Join two facts with because, since or so only when the text gives that cause. Say nothing about the file itself, such as that it is complete or the full transcript, unless the source says so. Keep the source's category words, a guy stays a guy and never becomes an agent. Carry names, numbers and their punctuation exactly as written (G17, G19).
- Sections. The body is divided with second level headings named for their topics (R17). When the source has its own headings, the extractor already carries them, so leave sections empty or add headings only inside long stretches that have none. When the source has no headings, such as a transcript, choose topic sections and give the line number in the part file where each begins. A heading sits on the first paragraph it describes, never on the paragraph before it, and goes where the topic changes, never inside a continuing exchange. When in doubt, fewer headings. Headings are the only thing inserted. The text itself is never retyped, trimmed or reordered. A name or term in a heading is spelled as the source spells it.
- Actions and Decisions. Only for decision oriented material such as meetings. List each item with an owner and a due date only when the source gives them (R18).
- People and speakers. The header's people field means everyone who was there, from the intake and from the labels the source carries. Name a speaker only when the source itself says who said what (G20, R33). Labels inside passages a document quotes name the speakers of what is quoted, not the people of this file, so they stay in the Content and do not enter the header. Say in people_note how the people were identified.
- Type is one or two plain words for the kind of source, such as transcript, interview, meeting, document, report or article (R15).
- When the material has more than one part, the engine builds the navigation page's summary from each part's first summary paragraph, in order, so nothing is written for it and nothing new is claimed there (G16, G19).
- Spell every name, brand and term exactly as the source spells it, even when it looks wrong. The source's spelling is a fact (G17, R10).
- When a speaker corrects or takes back something, or gives up a label for something, report what they settled on, never the words they took back (G17, G19).
- Keep the strength of every claim as the source has it. A hedge such as sometimes, maybe, almost or I think stays in. Never raise a sometimes to an often or a guess to a fact (G17, G19).
- One point, one grouping. When the source counts or groups things, carry its count and its grouping. Items from different groups, dates or events are never folded into one statement, and a statement about a set, such as all, each, most or the later ones, stands only when it holds for every member (G17, G19, R16).
- Name who. When a statement is about people, name them as the text does. Never let they, the two, both or the speakers stand in for names (G17, G19).
- In material with no speaker labels, every statement stands alone as what a speaker says. Never tie two passages to one voice, such as that speaker also or the other speaker, since the text does not say they share a speaker (G20, R33, G19).
- A qualifier such as I don't mean that as a brag, honestly or I think stays with the exact claim it followed in the text, never a neighboring one (G17, G19).
- Write the shorter end of every range unless the material needs more, one summary paragraph and three to five takeaways. Every added sentence is a claim to defend (R16, G19).
- An action or decision is something the source states as a commitment, a decision or a request still to be done. Something the source already treats as settled is not an action (R18, G19).
- The intake's title, date and people may appear in the summary and takeaways. Nothing else from outside the source may (R07, G19).
- Keep interpretation in the summary and takeaways. The Content section is the source itself (G17).
- Check your own work before handing it in. Read every summary sentence and every takeaway again next to the passage it comes from. Count anything you counted, and state the count the text gives. Keep the source's own groupings, so two statements the source makes separately stay separate. Use words like first, last, closes with or opens with only when the text's order bears them out. Fix or remove anything the text does not say exactly (G17, G19, R16).
- Then check it with fresh eyes. Where the session can start a fresh context, such as Claude Code or Codex, hand the part text and the draft file to a fresh reader whose only job is to find every statement the text does not support, every attribution the labeled words do not carry, every hedge dropped and every word the source does not use, and fix what it finds. Elsewhere, read the part again from the top and run the same hunt yourself. Nothing is handed in until that read finds nothing (G17, G19).
- Check each file's shape, quotes and words before moving on, with python3 scripts/optimize.py validate --derived <file> --part <the part file> (add --combined and one --part per source for combined.json). Besides the shape and the quotes, it checks that every name, number and term in the summary, takeaways, headings and actions appears in the part text, or in the run folder's intake.json, spelled the same way. It prints OK or says what to fix (R16, R17, G17, G19).

## Step 5, size and split (R12, G16)

The extractor estimates the size as characters divided by four and treats about 50,000 tokens as the limit. Material under the limit stays one file. Past it, the extractor splits at section breaks into numbered parts, each about 50,000 tokens or fewer, and the assembly step adds a navigation page listing each part and what it contains. Where a stretch has no section breaks the split lands on a paragraph break and the navigation page says so. No tokenizer, no exact rule, no fixed part size.

## Step 6, name, save, archive and report (R13, R19, G12, G13, G14, G23, R31, R32)

Assemble the files, decide the version, save, and report, in one command. Pass the Drive route this session holds. With no route, the files stay in the working folder and the message says the save is pending.

```bash
python3 scripts/optimize.py finish --work "<run folder>/work" --intake "<run folder>/intake.json" --derived "<run folder>/derived" --out "<run folder>/out" --auth "sa:<service account file>" --impersonate "<the account the session acts as>" --source-drive-id "<the source's Drive file ID when known>"
```

What happens, from references/file-rules.md.

- Names follow the company file rule, [Company][Version] Title.md or [Company-Department][Version] Title.md, with the version near the front and a friendly title. Parts add , Part n of N and the navigation page adds , Navigation (G13, R31).
- The files land in the working folder, then in the Claude outputs folder of the brain the file belongs to, found by its name, for example Claude Outputs [EP-BB]. A source that sits in a Private folder keeps its output there. The tool never creates a folder (R13, R32, G23).
- A source optimized for the first time is V1.0. A source already optimized is compared with the saved version. Unchanged, nothing new is saved. A small change advances the decimal and a larger change the whole number. The superseded files move to the brain's Archives folder, keeping their IDs, and nothing is deleted (R31, G14).
- Then the message, printed and saved as completion-report.md. The file name or names, where they were saved, how many parts, the version and what it replaced, which uploaded copies now need refreshing, and anything that could not be read (G12). Give that message to the person who asked, with each saved file as a clickable name.

Read references/output-contract.md for the exact shape of every file.

## Combining related files (G15, R24, R25)

Combine only when the request asks for it, and only files on the same topic. Run the extractor once per file into its own work folder. Then write one combined.json with the summary, takeaways, a sections list where each section names its source (A, B, and so on in the order given) and the line range in that source's part file, and a conflicts list for every point where the sources disagree, each claim with its source and date. Then assemble with --combine and every work folder. Every section keeps its source. A section is a passage of body text, so a source's own title and date lines belong to that source's first section, never to a section of their own. A passage that appears word for word in two sources appears once, a section that held only repeats is folded into the earlier copy, and Source Notes say so. Disagreements keep both claims with their dates in a Conflicts between sources section, and no winner is chosen. The optimizer stays a single file tool otherwise. Collection wide knowledge base design is other work (R25, R26).

## What this tool never does

- Invents a date, a name, an owner, a deadline, a number or a fact the source does not hold (G19).
- Corrects, trims, reorders or paraphrases the source text in Content, or respells a name or brand anywhere (G17, R10).
- Assigns words to a speaker the source does not label (R11, G20, R33).
- Guesses at a table, a scan or an unreadable region (G18).
- Picks a winner between sources that disagree (G15).
- Creates a folder, deletes a file, or changes an original (G23, R31).
- Certifies its own output. Claude in HQ and Allison certify under the build standard (G21).

## Files in this skill

- scripts/optimize.py, the engine. Extraction, cleanup, size estimate, splitting, assembly, naming, saving, archiving and the completion message. Standard library only, with pdfplumber, pypdf, pdftotext, tesseract, Whisper and the Google API client used when present.
- references/output-contract.md, the exact shape of every optimized file.
- references/file-rules.md, names, versions, save place and archive, from the company file rules.
