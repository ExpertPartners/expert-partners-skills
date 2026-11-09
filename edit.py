import re
files=[l.strip() for l in open('../../files.txt')]
old='- You WRITE and PREPARE. Never send, publish, schedule, or act on your own. If asked\n  to automate: "I\'ll write it, you send it."'
new='- You WRITE and PREPARE, then act. Where a connected tool can send, publish or\n  schedule, do it when the brief calls for it and report what you did with links.\n  Without a tool, deliver it ready to paste.'
n=0
def sub(path,a,b,cnt=1):
    s=open(path).read()
    assert a in s,(path,a[:40])
    s=s.replace(a,b); open(path,'w').write(s)
for f in files:
    s=open(f).read()
    if old in s:
        open(f,'w').write(s.replace(old,new)); n+=1
print(n)
# canva
c='skills/canva-assistant/SKILL.md'
sub(c,'> **Integration:** Canva (optional). Drafts only. Without it','> **Integration:** Canva (optional). Creates the design in Canva. Without it')
sub(c,'  platform, as a DRAFT they approve, then return the link. Never send, never\n  publish, never schedule beyond a draft, never act unasked.','  platform, then return the link. Publish or schedule only where the tool supports\n  it and the brief calls for it, and report what was done with links.')
sub(c,'4. One reassurance line: "I can only create drafts you approve; connecting never\n   lets anything send or publish on its own."','4. One plain line: "Connecting lets me build the design in your account and hand you the link."')
sub(c,'- Drafts only, never published. The agent opens, adjusts, and posts it themselves.','- Build the design and return the link. Post or publish through the tool where it supports it, otherwise the agent opens and posts it.')
sub(c,'- You WRITE and PREPARE. The only thing you ever push is the Integration behavior\n  above: a draft in the agent\'s own Canva, when asked. If asked to automate:\n  "I\'ll write it, you send it."','- You WRITE and PREPARE, then act. Push the design into the agent\'s own Canva\n  through the Integration behavior above and report the link.')
