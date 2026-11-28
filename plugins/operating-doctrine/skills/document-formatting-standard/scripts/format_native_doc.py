#!/usr/bin/env python3
"""Format an exact existing simple native Doc through its existing Google adapter."""

import argparse
import hashlib
import importlib.util
import io
import json
import math
from pathlib import Path
import re
import sys
import urllib.request

MARKER = "NATIVE_DOC_VERIFIED "


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def policy(text):
    section = re.search(r"Document formatting\.(.+?)(?:\r?\n|$)", text)
    require(section, "Live Rulebook Document formatting section missing")
    section = section[1]
    sizes = re.search(r"Title (\d+), Heading 1 (\d+), Heading 2 (\d+), and body (\d+)", section)
    line = re.search(r"Line spacing is (\d+(?:\.\d+)?)", section)
    body = re.search(r"(\d+) points after each body paragraph", section)
    heading = re.search(r"headings take (\d+) points above and (\d+) points below", section)
    bullet = re.search(
        r"items take (\d+) points after, and the last item in a list takes (\d+)", section
    )
    blue = re.search(r"Brand Blue (#[A-Fa-f0-9]{6})", section)
    require(
        all([sizes, line, body, heading, bullet, blue]) and "Poppins throughout" in section,
        "Live formatting policy is unsupported; update the parser, never guess values",
    )
    return {
        "sizes": dict(
            zip(["TITLE", "HEADING_1", "HEADING_2", "NORMAL_TEXT"], map(int, sizes.groups()))
        ),
        "line": float(line[1]) * 100,
        "body": int(body[1]),
        "above": int(heading[1]),
        "below": int(heading[2]),
        "bullet": int(bullet[1]),
        "last_bullet": int(bullet[2]),
        "blue": blue[1],
    }


def paragraphs(doc):
    tabs = doc.get("tabs", [])
    require(
        not tabs or (len(tabs) == 1 and not tabs[0].get("childTabs")),
        "Multi-tab documents need their owning layout procedure",
    )
    body = doc.get("body") or tabs[0]["documentTab"]["body"]
    require(
        all("paragraph" in x or "sectionBreak" in x for x in body["content"]),
        "Tables and special layouts need their owning layout procedure",
    )
    result = [x for x in body["content"] if "paragraph" in x]
    require(
        all("textRun" in e for x in result for e in x["paragraph"].get("elements", [])),
        "Non-text elements need their owning layout procedure",
    )
    require(
        all(not x["paragraph"].get("bullet") for x in result),
        "Generated list glyphs need their owning layout verification procedure",
    )
    return result


def text_of(element):
    return "".join(
        x.get("textRun", {}).get("content", "") for x in element["paragraph"].get("elements", [])
    )


def utf16(text):
    return len(text.encode("utf-16-le")) // 2


def source_projection_integrity(text):
    """Validate framing without reproducing the owning consumer's schema."""
    proof = []
    for name, version, many in [
        ("TODAY FAILURE TRACKER", 1, False),
        ("TODAY CHANGE LOG", 1, False),
        ("TODAY HEALTH RECEIPT", 1, False),
        ("HANDOFF REGISTER", 2, False),
        ("HANDOFF INSTANCE", 2, True),
    ]:
        candidates = list(re.finditer(r"^" + re.escape(name) + r" (?:BEGIN|END)[^\n]*", text, re.M))
        if not candidates:
            continue
        begin = name + " BEGIN v" + str(version)
        end = name + " END"
        require(
            all(m[0].strip(" \t\r") in (begin, end) for m in candidates),
            "Malformed source projection delimiter: " + name,
        )
        require(
            len(candidates) % 2 == 0 and (many or len(candidates) == 2),
            "Missing or duplicate source projection boundary: " + name,
        )
        payloads = []
        for left, right in zip(candidates[::2], candidates[1::2]):
            require(
                left[0].strip(" \t\r") == begin and right[0].strip(" \t\r") == end,
                "Unbalanced source projection boundaries: " + name,
            )
            def reject_constant(value):
                raise ValueError("Non-JSON constant in source projection: " + value)

            payload = text[left.end():right.start()]
            if name.startswith("TODAY "):
                json.loads(payload, parse_constant=reject_constant)
            # Existing Handoff registers are pipe rows and instances are
            # key=value lines. Preserve their grammar, not a second schema.
            payloads.append(hashlib.sha256(payload.encode()).hexdigest())
        proof.append({"name": name, "payload_sha256": payloads})
    return proof


def links_of(doc, drop_first=False):
    # Positions are relative to retained nonempty paragraphs, never run boundaries.
    items = [p for p in paragraphs(doc) if text_of(p).strip()]
    if drop_first:
        items = items[1:]
    result = []
    for index, p in enumerate(items):
        offset = 0
        for run in p["paragraph"].get("elements", []):
            text = run["textRun"]["content"]
            link = run["textRun"].get("textStyle", {}).get("link")
            if link:
                result.extend(
                    (index, offset + j, char, json.dumps(link, sort_keys=True))
                    for j, char in enumerate(text)
                )
            offset += len(text)
    return result


def supported_layout(doc):
    paragraphs(doc)
    containers = [doc] + [t.get("documentTab", {}) for t in doc.get("tabs", [])]
    require(
        not any(
            c.get(k)
            for c in containers
            for k in ("headers", "footers", "footnotes", "inlineObjects", "positionedObjects")
        ),
        "Headers, footers and objects need their owning layout procedure",
    )
    style = doc.get("documentStyle") or next(
        (c["documentStyle"] for c in containers if c.get("documentStyle")), {}
    )
    size = style.get("pageSize", {})
    width, height = size.get("width", {}), size.get("height", {})
    require(
        width.get("unit") == height.get("unit") == "PT"
        and any(
            abs(width.get("magnitude", 0) - w) < 1 and abs(height.get("magnitude", 0) - h) < 1
            for w, h in [(612, 792), (595.276, 841.89)]
        ),
        "Unknown or special page layout needs its owning procedure",
    )
    require(
        not any(
            style.get(k)
            for k in (
                "defaultHeaderId",
                "defaultFooterId",
                "firstPageHeaderId",
                "firstPageFooterId",
                "evenPageHeaderId",
                "evenPageFooterId",
            )
        ),
        "Header or footer layout needs its owning procedure",
    )
    for p in paragraphs(doc):
        require(
            not p["paragraph"].get("positionedObjectIds"),
            "Positioned objects need their owning layout procedure",
        )
    body = doc.get("body") or doc.get("tabs", [{}])[0].get("documentTab", {}).get("body", {})
    for element in body.get("content", []):
        columns = (
            element.get("sectionBreak", {}).get("sectionStyle", {}).get("columnProperties", [])
        )
        require(len(columns) <= 1, "Multi-column layout needs its owning procedure")


def read_native(api, document_id):
    doc = api.json(
        "https://docs.googleapis.com/v1/documents/" + document_id + "?includeTabsContent=true"
    )
    require(doc.get("documentId") == document_id, "Native Doc identity mismatch")
    supported_layout(doc)
    return doc


def title_subject(name):
    subject = re.sub(r"^(?:\[[^\]]+\])+\s*", "", name)
    require(subject.strip(), "Document subject missing")
    return subject


def preparation(doc, name):
    items = paragraphs(doc)
    require(
        not any(
            not text_of(p).strip()
            and any(
                e.get("textRun", {}).get("textStyle", {}).get("link")
                for e in p["paragraph"].get("elements", [])
            )
            for p in items
        ),
        "Linked spacer paragraphs must be preserved by their owning procedure",
    )
    nonempty = [x for x in items if text_of(x).strip()]
    require(nonempty, "Empty document has no saved content to verify")
    title = title_subject(name)
    requests = []
    # Delete spacer-only paragraphs backwards, never the mandatory final newline.
    for item in reversed(items[:-1]):
        if not text_of(item).strip():
            requests.append(
                {
                    "deleteContentRange": {
                        "range": {"startIndex": item["startIndex"], "endIndex": item["endIndex"]}
                    }
                }
            )
    has_title = nonempty[0]["paragraph"].get("paragraphStyle", {}).get("namedStyleType") == "TITLE"
    if not has_title and text_of(nonempty[0]).strip() != title:
        requests.append({"insertText": {"location": {"index": 1}, "text": title + "\n"}})
        requests.append(
            {
                "updateTextStyle": {
                    "range": {"startIndex": 1, "endIndex": 1 + utf16(title + "\n")},
                    "textStyle": {},
                    "fields": "link",
                }
            }
        )
    return requests


def style_requests(doc, spec, name):
    items = [x for x in paragraphs(doc) if text_of(x).strip()]
    result = []
    for index, item in enumerate(items):
        p = item["paragraph"]
        actual_named = p.get("paragraphStyle", {}).get("namedStyleType", "NORMAL_TEXT")
        require(actual_named in spec["sizes"], "Unsupported named heading or special layout")
        named = "TITLE" if index == 0 else actual_named
        require(named in spec["sizes"], "Unsupported named heading or special layout")
        span = {"startIndex": item["startIndex"], "endIndex": item["endIndex"] - 1}
        heading = named != "NORMAL_TEXT"
        after = spec["below"] if heading else spec["body"]
        if "bullet" in p:
            after = (
                spec["bullet"]
                if index + 1 < len(items) and "bullet" in items[index + 1]["paragraph"]
                else spec["last_bullet"]
            )
        ps = {
            "namedStyleType": named,
            "lineSpacing": spec["line"],
            "spaceAbove": {"magnitude": spec["above"] if heading else 0, "unit": "PT"},
            "spaceBelow": {"magnitude": after, "unit": "PT"},
        }
        color = (
            spec["blue"] if named == "HEADING_2" and name.startswith(("[HQ", "[EP")) else "#000000"
        )
        rgb = {
            k: int(color[1 + j * 2 : 3 + j * 2], 16) / 255
            for j, k in enumerate(["red", "green", "blue"])
        }
        ts = {
            "weightedFontFamily": {"fontFamily": "Poppins"},
            "fontSize": {"magnitude": spec["sizes"][named], "unit": "PT"},
            "bold": False,
            "italic": False,
            "foregroundColor": {"color": {"rgbColor": rgb}},
        }
        result.extend(
            [
                {
                    "updateParagraphStyle": {
                        "range": span,
                        "paragraphStyle": ps,
                        "fields": ",".join(ps),
                    }
                },
                {"updateTextStyle": {"range": span, "textStyle": ts, "fields": ",".join(ts)}},
            ]
        )
    return result


def verify_native(doc, spec, name):
    for request in style_requests(doc, spec, name):
        if "updateParagraphStyle" not in request:
            continue
        expected = request["updateParagraphStyle"]
        item = next(
            x for x in paragraphs(doc) if x["startIndex"] == expected["range"]["startIndex"]
        )
        actual = item["paragraph"].get("paragraphStyle", {})
        for key, value in expected["paragraphStyle"].items():
            got = actual.get(key)
            if key in ("spaceAbove", "spaceBelow"):
                # Google elides zero scalar magnitudes, not the unit or positive values.
                got = {
                    "unit": (got or {}).get("unit", "PT"),
                    "magnitude": (got or {}).get("magnitude", 0),
                }
            require(got == value, "Native paragraph style or spacing mismatch")
        named = item["paragraph"].get("paragraphStyle", {}).get("namedStyleType", "NORMAL_TEXT")
        styles = doc.get("namedStyles", {}).get("styles", [])
        if not styles and doc.get("tabs"):
            styles = doc["tabs"][0].get("documentTab", {}).get("namedStyles", {}).get("styles", [])
        base = {}
        for kind in ["NORMAL_TEXT", named]:
            base.update(
                next(
                    (x.get("textStyle", {}) for x in styles if x.get("namedStyleType") == kind), {}
                )
            )
        color = (
            spec["blue"] if named == "HEADING_2" and name.startswith(("[HQ", "[EP")) else "#000000"
        )
        wanted = [int(color[i : i + 2], 16) / 255 for i in (1, 3, 5)]
        for run in item["paragraph"].get("elements", []):
            if not run.get("textRun", {}).get("content", "").strip():
                continue
            effective = {**base, **run["textRun"].get("textStyle", {})}
            optional = effective.get("foregroundColor", {"color": {"rgbColor": {}}})
            rgb = optional.get("color", {}).get("rgbColor")
            require(
                isinstance(rgb, dict)
                and all(
                    abs(rgb.get(k, 0) - v) < 0.000001
                    for k, v in zip(("red", "green", "blue"), wanted)
                ),
                "Native effective text color mismatch",
            )


def verify_pdf(pdf, doc, spec):
    # Export is the independent effective-size evidence when native defaults are omitted.
    from pypdf import PdfReader

    actual = []
    for page in PdfReader(io.BytesIO(pdf)).pages:

        def visit(text, cm, tm, font, size):
            # Font size is in text space. Docs exports 4/3-sized glyphs under a 0.75 CTM.
            # Transform the text-space vertical vector into page points before comparing.
            scale = math.hypot(tm[2] * cm[0] + tm[3] * cm[2], tm[2] * cm[1] + tm[3] * cm[3])
            effective = size * scale * float(page.get("/UserUnit", 1))
            for char in text:
                if not char.isspace():
                    actual.append((char, str((font or {}).get("/BaseFont", "")), effective))

        page.extract_text(visitor_text=visit)
    expected = []
    for index, item in enumerate(x for x in paragraphs(doc) if text_of(x).strip()):
        named = item["paragraph"].get("paragraphStyle", {}).get("namedStyleType", "NORMAL_TEXT")
        require(
            (index != 0 or named == "TITLE") and named in spec["sizes"],
            "Native TITLE or named paragraph style missing",
        )
        expected.extend((c, spec["sizes"][named]) for c in text_of(item) if not c.isspace())
    require(
        "".join(c for c, _, _ in actual) == "".join(c for c, _ in expected),
        "Native PDF text does not exactly match saved title and body",
    )
    require(
        all(
            "Poppins" in font
            and not re.search("bold|italic|oblique", font, re.I)
            and abs(size - want[1]) < 0.005
            for (_, font, size), want in zip(actual, expected)
        ),
        "Native PDF effective font or size mismatch",
    )
    require(bool(expected), "No rendered text verified")


class Google:
    def __init__(self, adapter, subject):
        path = Path(adapter).expanduser().resolve(strict=True)
        module = importlib.util.spec_from_file_location("existing_google_adapter", path)
        self.adapter = importlib.util.module_from_spec(module)
        module.loader.exec_module(self.adapter)
        self.subject = subject

    def request(self, url, method="GET", body=None):
        result = self.adapter.google_api(
            {
                "url": url,
                "method": method,
                "body": body,
                "subject": self.subject,
                "scopes": ["docs", "drive"],
            }
        )
        require(
            result.get("status") == 200 and not result.get("truncated"),
            "Existing Google route failed or returned incomplete content",
        )
        return result["response"]

    def json(self, url, method="GET", body=None):
        return json.loads(self.request(url, method, body))

    def pdf(self, document_id):
        token = self.adapter.mint_token(self.subject, self.adapter.SCOPES["drive"])
        request = urllib.request.Request(
            f"https://www.googleapis.com/drive/v3/files/{document_id}/export?mimeType=application%2Fpdf",
            headers={"Authorization": "Bearer " + token},
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.read()


def recheck_receipt(api, receipt):
    doc = read_native(api, receipt["document_id"])
    meta = api.json(
        "https://www.googleapis.com/drive/v3/files/"
        + receipt["document_id"]
        + "?fields=id,name,parents,mimeType,trashed&supportsAllDrives=true"
    )
    require(
        meta.get("id") == receipt["document_id"]
        and doc.get("revisionId") == receipt["revision"]
        and digest(doc) == receipt["native_sha256"]
        and digest([text_of(x) for x in paragraphs(doc)]) == receipt["content_sha256"]
        and meta["name"] == receipt["name"]
        and meta["parents"] == receipt["parents"]
        and not meta.get("trashed")
        and meta["mimeType"] == "application/vnd.google-apps.document",
        "Saved Doc changed after formatting or final readback is unavailable",
    )


def format_doc(api, document_id, rulebook_id, name, parent):
    require(
        re.fullmatch(r"[A-Za-z0-9_-]+", document_id)
        and re.fullmatch(r"[A-Za-z0-9_-]+", rulebook_id),
        "Invalid native file identity",
    )
    require(
        re.fullmatch(r"\[[A-Za-z][A-Za-z-]*\]\[V\d+\.\d+\] .+", name),
        "Resolve the current canonical document name before formatting",
    )
    require(document_id != rulebook_id, "The formatter never modifies its authority")
    base = "https://www.googleapis.com/drive/v3/files/"
    fields = "?fields=id,name,mimeType,parents,trashed,version&supportsAllDrives=true"
    meta = api.json(base + document_id + fields)
    require(
        meta["id"] == document_id
        and meta["name"] == name
        and parent in meta.get("parents", [])
        and not meta.get("trashed")
        and meta["mimeType"] == "application/vnd.google-apps.document",
        "Exact saved name, native type or owning parent mismatch",
    )
    authority = api.json(base + rulebook_id + fields)
    spec = policy(api.request(base + rulebook_id + "/export?mimeType=text%2Fplain"))
    require(
        authority["version"] == api.json(base + rulebook_id + fields)["version"],
        "Rulebook changed during read",
    )
    url = "https://docs.googleapis.com/v1/documents/" + document_id
    doc = read_native(api, document_id)
    projection_proof = source_projection_integrity("".join(text_of(x) for x in paragraphs(doc)))
    style_requests(doc, spec, name)  # Refuse unsupported layouts before any write.
    before_links = links_of(doc)
    before = [text_of(x) for x in paragraphs(doc) if text_of(x).strip()]
    requests = preparation(doc, name)
    inserted_title = any(
        request.get("insertText", {}).get("text") == title_subject(name) + "\n"
        and request["insertText"].get("location", {}).get("index") == 1
        for request in requests
    )
    if requests:
        api.json(
            url + ":batchUpdate",
            "POST",
            {"writeControl": {"requiredRevisionId": doc["revisionId"]}, "requests": requests},
        )
        doc = read_native(api, document_id)
    api.json(
        url + ":batchUpdate",
        "POST",
        {
            "writeControl": {"requiredRevisionId": doc["revisionId"]},
            "requests": style_requests(doc, spec, name),
        },
    )
    saved = read_native(api, document_id)
    require(
        source_projection_integrity("".join(text_of(x) for x in paragraphs(saved))) == projection_proof,
        "Formatting changed source projections",
    )
    after = [text_of(x) for x in paragraphs(saved) if text_of(x).strip()]
    require(
        after == ([title_subject(name) + "\n"] + before if inserted_title else before),
        "Formatting changed existing wording",
    )
    require(
        links_of(saved, drop_first=inserted_title) == before_links,
        "Formatting changed existing hyperlinks",
    )
    verify_native(saved, spec, name)
    verify_pdf(api.pdf(document_id), saved, spec)
    require(
        saved["revisionId"] == read_native(api, document_id)["revisionId"],
        "Document changed during PDF verification",
    )
    final = api.json(base + document_id + fields)
    require(
        final["id"] == document_id
        and final["name"] == name
        and final["parents"] == meta["parents"]
        and not final.get("trashed")
        and final["mimeType"] == "application/vnd.google-apps.document",
        "Saved identity or parent changed",
    )
    return {
        "verified": True,
        "document_id": document_id,
        "name": final["name"],
        "url": f"https://docs.google.com/document/d/{document_id}/edit",
        "revision": saved["revisionId"],
        "native_sha256": digest(saved),
        "content_sha256": digest([text_of(x) for x in paragraphs(saved)]),
        "parents": final["parents"],
        "rulebook_version": authority["version"],
        "rendered_font_sizes": True,
        "source_projections": projection_proof,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ["adapter", "document-id", "rulebook-id", "name", "parent-id", "subject"]:
        parser.add_argument("--" + flag, required=True)
    args = parser.parse_args()
    # Check verification dependency before any write.
    import pypdf  # noqa: F401

    try:
        receipt = format_doc(
            Google(args.adapter, args.subject),
            args.document_id,
            args.rulebook_id,
            args.name,
            args.parent_id,
        )
        print(MARKER + json.dumps(receipt))
        print(f"[{receipt['name']}]({receipt['url']})")
    except Exception:
        print(
            "Native formatting/readback failed; no verified save receipt. Inspect the exact document before retrying.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
