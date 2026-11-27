"""Create or fill Google Docs from simple text markup.

Lines starting with "# " become HEADING_1, "## " HEADING_2, "### " HEADING_3,
everything else NORMAL_TEXT. Blank lines are dropped (paragraph spacing comes
from the styles).
"""

import gws


def parse(text):
    out = []
    for line in text.splitlines():
        s = line.rstrip()
        if not s.strip():
            continue
        if s.startswith("### "):
            out.append(("HEADING_3", s[4:]))
        elif s.startswith("## "):
            out.append(("HEADING_2", s[3:]))
        elif s.startswith("# "):
            out.append(("HEADING_1", s[2:]))
        else:
            out.append(("NORMAL_TEXT", s))
    return out


def insert_requests(paras, index=1):
    """Requests that insert paras at index, styled. Returns (requests, total_len)."""
    body = "".join(p + "\n" for _, p in paras)
    reqs = [{"insertText": {"location": {"index": index}, "text": body}}]
    pos = index
    for style, p in paras:
        end = pos + len(p) + 1
        reqs.append(
            {
                "updateParagraphStyle": {
                    "range": {"startIndex": pos, "endIndex": end},
                    "paragraphStyle": {"namedStyleType": style},
                    "fields": "namedStyleType",
                }
            }
        )
        reqs.append(
            {
                "updateTextStyle": {
                    "range": {"startIndex": pos, "endIndex": end},
                    "textStyle": {"bold": False, "italic": False},
                    "fields": "bold,italic",
                }
            }
        )
        pos = end
    return reqs, len(body)


def create_doc(name, parent, text):
    f = gws.api(
        "https://www.googleapis.com/drive/v3/files?supportsAllDrives=true&fields=id,name,webViewLink",
        method="POST",
        body={
            "name": name,
            "mimeType": "application/vnd.google-apps.document",
            "parents": [parent],
        },
    )
    reqs, _ = insert_requests(parse(text))
    gws.batch_update(f["id"], reqs)
    return f


def create_folder(name, parent):
    return gws.api(
        "https://www.googleapis.com/drive/v3/files?supportsAllDrives=true&fields=id,name,webViewLink",
        method="POST",
        body={"name": name, "mimeType": "application/vnd.google-apps.folder", "parents": [parent]},
    )


def doc_end(doc_id):
    d = gws.get_doc(doc_id)
    return d["body"]["content"][-1]["endIndex"], d
