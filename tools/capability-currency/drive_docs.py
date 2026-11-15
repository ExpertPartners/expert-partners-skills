#!/usr/bin/env python3
"""Headless Google Docs access for the capability-currency runner.

A claude -p run on a long-lived token cannot reach the claude.ai Drive and Docs
connectors (code.claude.com/docs/en/authentication, checked 2026-10-13), so the
runner uses the service account with domain-wide delegation instead. Same Docs,
same owner, no human session.

  drive_docs.py read DOC_TITLE
  drive_docs.py prepend DOC_TITLE FILE   insert FILE above the first ## heading
  drive_docs.py replace DOC_TITLE FILE   replace the whole body with FILE
  drive_docs.py create DOC_TITLE FILE FOLDER   new "[HQ][V1.0] DOC_TITLE" Doc in FOLDER, body FILE

DOC_TITLE is the Doc's name without its bracketed tag and version, such as
"Capability Watch". The Doc is found by that title at run time, so no Drive file
ID lives in this public repo. Zero or several matches stop the run. Shared
drives are searched too, since Company Core lives on one. FOLDER is a folder's
exact name, such as "🧠 Company Core [HQ-BB]", found the same way. create stops
if the Doc already exists.

FILE is plain text. Lines starting with '# ', '## ' or '### ' become headings,
and lines starting with '- ' become bullets.
The key stays where it is (never copied, never printed).
"""

import os
import re
import sys
from typing import Any

from google.oauth2 import service_account
from googleapiclient.discovery import build

KEY = os.path.expanduser("~/.openclaw/.secrets/service-account.json")
SUBJECT = "allison@expertpartners.com"
SCOPES = ["https://www.googleapis.com/auth/documents", "https://www.googleapis.com/auth/drive"]
STYLE = {"# ": "HEADING_1", "## ": "HEADING_2", "### ": "HEADING_3"}
BULLET = "- "
TAG = "[HQ][V1.0]"
DOC_MIME = "application/vnd.google-apps.document"

# googleapiclient is untyped, so its service objects and the JSON they return are Any.
JSONDict = dict[str, Any]
Service = Any


def clients() -> tuple[Service, Service]:
    creds = service_account.Credentials.from_service_account_file(
        KEY, scopes=SCOPES, subject=SUBJECT
    )
    return (
        build("docs", "v1", credentials=creds, cache_discovery=False).documents(),
        build("drive", "v3", credentials=creds, cache_discovery=False),
    )


def search(drive: Service, q: str) -> list[dict[str, str]]:
    found: list[dict[str, str]] = (
        drive.files()
        .list(
            q=q,
            fields="files(id,name)",
            pageSize=50,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            corpora="allDrives",
        )
        .execute()
        .get("files", [])
    )
    return found


def doc_hits(drive: Service, title: str) -> list[dict[str, str]]:
    found = search(drive, f"name contains '{title}' and mimeType='{DOC_MIME}' and trashed=false")
    return [f for f in found if re.fullmatch(r"(\[[^\]]+\])+ " + re.escape(title), f["name"])]


def find_doc_id(drive: Service, title: str) -> str:
    hits = doc_hits(drive, title)
    if len(hits) != 1:
        sys.exit(f"expected one Doc titled {title}, found {len(hits)}")
    return hits[0]["id"]


def create_doc(drive: Service, title: str, folder: str) -> str:
    if doc_hits(drive, title):
        sys.exit(f"a Doc titled {title} already exists")
    q = f"name = '{folder}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    folders = search(drive, q)
    if len(folders) != 1:
        sys.exit(f"expected one folder named {folder}, found {len(folders)}")
    made: dict[str, str] = (
        drive.files()
        .create(
            body={"name": f"{TAG} {title}", "mimeType": DOC_MIME, "parents": [folders[0]["id"]]},
            fields="id",
            supportsAllDrives=True,
        )
        .execute()
    )
    print(f"https://docs.google.com/document/d/{made['id']}/edit")
    return made["id"]


def paragraphs(doc: JSONDict) -> list[JSONDict]:
    content: list[JSONDict] = doc["body"]["content"]
    return content


def text_of(doc: JSONDict) -> str:
    out: list[str] = []
    for el in paragraphs(doc):
        for run in el.get("paragraph", {}).get("elements", []):
            out.append(run.get("textRun", {}).get("content", ""))
    return "".join(out)


def build_insert(raw: str, at: int) -> list[dict[str, object]]:
    lines = raw.rstrip("\n").split("\n")
    parsed = []
    for line in lines:
        style = "NORMAL_TEXT"
        for mark, name in STYLE.items():
            if line.startswith(mark):
                style, line = name, line[len(mark) :]
                break
        else:
            if line.startswith(BULLET):
                style, line = BULLET, line[len(BULLET) :]
        parsed.append((style, line))
    reqs: list[dict[str, object]] = [
        {"insertText": {"location": {"index": at}, "text": "".join(t + "\n" for _, t in parsed)}}
    ]
    total = sum(len(t) + 1 for _, t in parsed)
    # Inserted lines can inherit a bullet from the paragraph they land in, so clear first.
    reqs.append({"deleteParagraphBullets": {"range": {"startIndex": at, "endIndex": at + total}}})
    pos = at
    for style, t in parsed:
        end = pos + len(t) + 1
        named = "NORMAL_TEXT" if style == BULLET else style
        ps: dict[str, object] = {"namedStyleType": named}
        fields = "namedStyleType"
        if style == "NORMAL_TEXT":
            ps["spaceBelow"] = {"magnitude": 12, "unit": "PT"}
            fields += ",spaceBelow"
        reqs.append(
            {
                "updateParagraphStyle": {
                    "range": {"startIndex": pos, "endIndex": end},
                    "paragraphStyle": ps,
                    "fields": fields,
                }
            }
        )
        if style == BULLET:
            reqs.append(
                {
                    "createParagraphBullets": {
                        "range": {"startIndex": pos, "endIndex": end},
                        "bulletPreset": "BULLET_DISC_CIRCLE_SQUARE",
                    }
                }
            )
        pos = end
    return reqs


def main(argv: list[str]) -> None:
    if (
        len(argv) < 3
        or argv[1] not in ("read", "prepend", "replace", "create")
        or (argv[1] == "create" and len(argv) < 5)
    ):
        sys.exit(__doc__)
    cmd, title = argv[1], argv[2]
    d, drive = clients()
    doc_id = create_doc(drive, title, argv[4]) if cmd == "create" else find_doc_id(drive, title)
    doc: JSONDict = d.get(documentId=doc_id).execute()
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
            reqs.append({"deleteContentRange": {"range": {"startIndex": 1, "endIndex": end_index}}})
        reqs += build_insert(raw, 1)
    d.batchUpdate(documentId=doc_id, body={"requests": reqs}).execute()
    print(f"{cmd} ok: {title}")


if __name__ == "__main__":
    main(sys.argv)
