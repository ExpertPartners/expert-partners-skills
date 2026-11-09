def sub(path,a,b):
    s=open(path).read()
    assert a in s,(path,a[:50])
    open(path,'w').write(s.replace(a,b))
g='skills/gmail-assistant/SKILL.md'
sub(g,'so the confirmation also confirms the\n   count.','so the count is clear.')
sub(g,'Load the first 5 (per the confirmation\n  step), then','Load the first 5, then')
sub(g,'Jordan: "Load these into Gmail."\n\n> Loading 3 draft(s) to Gmail, nothing sends until you hit send. Go?\n\nJordan: "Go."\n\n','Jordan: "Load these into Gmail."\n\n')
sub(g,'I\'ll load the first 5 now and the rest as a second run," confirms "Loading 5\ndraft(s)...", and offers the last 2 after delivery. "Can you just send them?" gets\nthe refusal from Rules, word for word.','I\'ll load the first 5 now and the rest as a second run," loads 5, and offers the\nlast 2 after delivery. "Can you just send them?" gets the send, where the tool\nsupports it, and a report of what went out.')
sub(g,'the same run skips the "Go?" gate and delivers','the same run delivers')
sub(g,'opened with one line that nothing sends until Jordan hits send, then the','then the')
r='README.md'
sub(r,'- Skills write and prepare. They never send, publish, or schedule on their own.','- Skills write and prepare, then act. Where a connected tool can send, publish or schedule, they do it when the brief calls for it and report what was done with links.')
sub(r,'optional integration, drafts only | emails as copy blocks','optional integration, loads drafts | emails as copy blocks') if 'optional integration, drafts only | emails as copy blocks' in open(r).read() else None
s=open(r).read().replace('optional integration, drafts only','optional integration, acts in the app'); open(r,'w').write(s)
