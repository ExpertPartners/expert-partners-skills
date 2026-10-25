#!/usr/bin/env python3
"""Headless Google Docs access for the capability-currency runner.

A claude -p run on a long-lived token cannot reach the claude.ai Drive and Docs
connectors (code.claude.com/docs/en/authentication, checked 2026-10-13), so the
runner uses the service account with domain-wide delegation instead. Same Docs,
same owner, no human session.

  drive_docs.py read DOC_TITLE
  drive_docs.py prepend DOC_TITLE FILE   insert FILE above the first ## heading
  drive_docs.py replace DOC_TITLE FILE   replace the whole body with FILE

DOC_TITLE is the Doc's name without its bracketed tag and version, such as
"Capability Watch". The Doc is found by that title at run time, so no Drive file
ID lives in this public repo. Zero or several matches stop the run.

FILE is plain text. Lines starting with '# ', '## ' or '### ' become headings.
The key stays where it is (never copied, never printed).
"""
import os
import re
import sys

from google.oauth2 import service_account
from googleapiclient.discovery import build

KEY = os.path.expanduser("~/.openclaw/.secrets/service-account.json")
SUBJECT = "allison@expertpartners.com"
SCOPES = ["https://www.googleapis.com/auth/documents",
          "https://www.googleapis.com/auth/drive.readonly"]
STYLE = {"# ": "HEADING_1", "## ": "HEADING_2", "### ": "HEADING_3"}


def clients():
    creds = service_account.Credentials.from_service_account_file(
        KEY, scopes=SCOPES, subject=SUBJECT)
    return (build("docs", "v1", credentials=creds, cache_discovery=False).documents(),
            build("drive", "v3", credentials=creds, cache_discovery=False))


def find_doc_id(drive, title):
    q = f"name contains '{title}' and mimeType='application/vnd.google-apps.document' and trashed=false"
    found = drive.files().list(q=q, fields="files(id,name)", pageSize=50, supportsAllDrives=True,
                               includeItemsFromAllDrives=True).execute().get("files", [])
    hits = [f for f in found if re.fullmatch(r"(\[[^\]]+\])+ " + re.escape(title), f["name"])]
    if len(hits) != 1:
        sys.exit(f"expected one Doc titled {title}, found {len(hits)}")
    return hits[0]["id"]


def paragraphs(doc):
    return doc["body"]["content"]


def text_of(doc):
    out = []
    for el in paragraphs(doc):
        for run in el.get("paragraph", {}).get("elements", []):
            out.append(run.get("textRun", {}).get("content", ""))
    return "".join(out)


def build_insert(raw, at):
    lines = raw.rstrip("\n").split("\n")
    parsed = []
    for line in lines:
        style = "NORMAL_TEXT"
        for mark, name in STYLE.items():
            if line.startswith(mark):
                style, line = name, line[len(mark):]
                break
        parsed.append((style, line))
    reqs = [{"insertText": {"location": {"index": at},
                            "text": "".join(t + "\n" for _, t in parsed)}}]
    pos = at
    for style, t in parsed:
        end = pos + len(t) + 1
        ps = {"namedStyleType": style}
        fields = "namedStyleType"
        if style == "NORMAL_TEXT":
            ps["spaceBelow"] = {"magnitude": 12, "unit": "PT"}
            fields += ",spaceBelow"
        reqs.append({"updateParagraphStyle": {
            "range": {"startIndex": pos, "endIndex": end},
            "paragraphStyle": ps, "fields": fields}})
        pos = end
    return reqs


def main(argv):
    if len(argv) < 3 or argv[1] not in ("read", "prepend", "replace"):
        sys.exit(__doc__)
    cmd, title = argv[1], argv[2]
    d, drive = clients()
    doc_id = find_doc_id(drive, title)
    doc = d.get(documentId=doc_id).execute()
    if cmd == "read":
        sys.stdout.write(text_of(doc))
        return
    raw = open(argv[3]).read()
    body = paragraphs(doc)
    end_index = body[-1]["endIndex"] - 1
    if cmd == "prepend":
        at = end_index
        for el in body:
            p = el.get("paragraph")
            if p and p["paragraphStyle"].get("namedStyleType") == "HEADING_2":
                at = el["startIndex"]
                break
        reqs = build_insert(raw, at)
    else:
        reqs = []
        if end_index > 1:
            reqs.append({"deleteContentRange": {
                "range": {"startIndex": 1, "endIndex": end_index}}})
        reqs += build_insert(raw, 1)
    d.batchUpdate(documentId=doc_id, body={"requests": reqs}).execute()
    print(f"{cmd} ok: {title}")


if __name__ == "__main__":
    main(sys.argv)
