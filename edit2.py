def sub(path,a,b):
    s=open(path).read()
    assert a in s,(path,a[:50])
    open(path,'w').write(s.replace(a,b))
g='skills/gmail-assistant/SKILL.md'
sub(g,'> **Integration:** Gmail (optional). Drafts only. Without it','> **Integration:** Gmail (optional). Loads drafts, sends where the tool allows. Without it')
sub(g,'click. Drafts only: you can never send, and you say so up front, every run.','click. You load the drafts straight away, and send when the brief says to and the tool supports it.')
sub(g,'   below). NOT connected → skip the confirmation gate (nothing loads); deliver the\n   copy blocks immediately.\n6. CONNECTED → confirm before loading anything: "Loading [n] draft(s) to Gmail,\n   nothing sends until you hit send. Go?" Then WAIT for the agent\'s go. This gate\n   is mandatory: it always runs before any draft is created, even when "generate\n   immediately, zero questions" applies, and it does not count against the\n   one-question limit. More than 5 emails in? Say first: "That\'s [total] emails,\n   max is 5 per run. I\'ll load the first 5 now and the rest as a second run." Then\n   confirm with [n] = 5.',
'   below). NOT connected → deliver the copy blocks immediately.\n6. CONNECTED → load the draft(s) to Gmail right away and report what was loaded.\n   More than 5 emails in? Say: "That\'s [total] emails, max is 5 per run. I\'ll load\n   the first 5 now and the rest as a second run."')
sub(g,'Gmail now," then straight to the integration check and the confirmation gate.','Gmail now," then straight to the integration check and loading.')
sub(g,'review and send. 30 seconds','review and send. 30 seconds') if False else None
sub(g,'- IF CONNECTED: after the agent\'s go at the confirmation gate, create the email(s)\n  in the agent\'s Gmail as DRAFTS only, subject + body + recipient if given. Never\n  send, never publish, never schedule beyond a draft, never act unasked.',
'- IF CONNECTED: create the email(s) in the agent\'s Gmail as drafts, subject + body +\n  recipient if given. Send only where the tool supports it and the brief says send.\n  Report what was done.')
sub(g,'4. Reassure (this line matters most for email): "Connecting can never let me send\n   anything or read your inbox: drafts only, always."','4. One plain line: "Connecting lets me load your emails as drafts in Gmail, no copy-paste."')
sub(g,'- DRAFTS ONLY: this skill can never send. State that up front, every run: on the\n  connected path the confirmation line does it; on the standalone path, open the\n  delivery with one line saying nothing sends until they hit send. If asked to send\n  ("can you just send them?"): refuse, "No, drafts only. I load them, you hit\n  send."',
'- Load the drafts without asking. If asked to send ("can you just send them?"), send\n  through the tool where it supports sending and report what went out. Without that\n  support, say so and the drafts are ready for one click.')
sub(g,'Rewrites happen\n  BEFORE the confirmation: if the agent asks for changes at or after the "Go?"\n  gate, don\'t load: make the edit, then re-confirm with a fresh "Loading [n]\n  draft(s)..." line.','If the agent asks\n  for changes, make the edit and load the revised version.')
sub(g,'- You load DRAFTS the agent approves: the Integration behavior section above governs','- You load the drafts: the Integration behavior section above governs')
