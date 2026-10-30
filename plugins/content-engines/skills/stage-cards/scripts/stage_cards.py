#!/usr/bin/env python3
"""
stage_cards.py -- lays card markup onto 4x6 stage cards in a Google Doc.

Format and markup are defined in references/format-spec.md. Layout only: the words in
the card file go into the Doc exactly as written.

Commands
  check FILE            parse the card file, pick each card's body size, flag any card
                        that will not fit. Offline, no credentials.
  requests FILE         print the Google Docs batchUpdate requests as JSON. Offline.
  create FILE --title T [--folder FOLDER_ID]
                        create the Doc, apply the cards, export a PDF and verify the page
                        count equals the card count and card N starts on page N.

Credentials (create only), read from the environment, never stored here
  GOOGLE_APPLICATION_CREDENTIALS   path to a service account key file
  STAGE_CARDS_SUBJECT              optional, a user to impersonate through domain-wide
                                   delegation so that user owns the Doc
Requires google-api-python-client and google-auth. pypdf is used for the page check when
installed, with a plain fallback otherwise.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

PAGE_W, PAGE_H = 432, 288
MARGIN_TB, MARGIN_LR = 19, 24
NAVY = {"red": 0x24 / 255, "green": 0x3B / 255, "blue": 0x57 / 255}
FONT = "Poppins"
HEADER_SIZE = 11
BODY_SIZES = (11, 10)
SEPARATOR = "---"

# Fit model, fitted so every approved Finish Strong card fits at the size Allison chose
# (cards up to about 770 characters held at 11 and about 920 at 10). Poppins text
# averages about 0.50 em per character and single spacing is 1.5 em per line. The
# estimate only picks a size. The PDF page check in create is the real test.
CHAR_EM = 0.50
LINE_EM = 1.5
USABLE_W = PAGE_W - 2 * MARGIN_LR
USABLE_H = PAGE_H - 2 * MARGIN_TB
FIT_SLACK = 0.97
HEADER_WARN_CHARS = 60
BULLET_INDENT = 36


class CardError(Exception):
    pass


def _runs(text: str) -> list[tuple[str, bool]]:
    """Split a line on **bold** spans into (text, bold) runs."""
    out, bold = [], False
    for i, part in enumerate(re.split(r"\*\*", text)):
        bold = i % 2 == 1
        if part:
            out.append((part, bold))
    return out


def parse(text: str) -> list[dict]:
    """Card markup to a list of cards. Each card is {paras, size, forced}."""
    blocks, cur = [], []
    for line in text.splitlines():
        if line.strip() == SEPARATOR:
            blocks.append(cur)
            cur = []
        else:
            cur.append(line)
    blocks.append(cur)
    cards = []
    for n, lines in enumerate(blocks, 1):
        paras, buf, forced = [], [], None

        def flush():
            if buf:
                paras.append({"kind": "body", "runs": _runs(" ".join(buf))})
                buf.clear()

        for raw in lines:
            line = raw.rstrip()
            if not line.strip():
                if buf:
                    flush()
                    paras.append({"kind": "blank", "runs": []})
                continue
            m = re.fullmatch(r"@(10|11)", line.strip())
            if m:
                forced = int(m.group(1))
            elif line.startswith("# "):
                flush()
                paras.append({"kind": "header", "runs": [(line[2:].strip(), True)]})
            elif line.startswith("- "):
                flush()
                paras.append({"kind": "bullet", "runs": _runs(line[2:].strip())})
            else:
                buf.append(line.strip())
        flush()
        while paras and paras[-1]["kind"] == "blank":
            paras.pop()
        if not paras:
            if n == len(blocks):
                continue
            raise CardError(f"card {n} is empty")
        cards.append({"paras": paras, "forced": forced, "size": None})
    if not cards:
        raise CardError("no cards found")
    return cards


def para_text(p: dict) -> str:
    return "".join(t for t, _ in p["runs"])


def estimate_height(card: dict, body_size: int) -> float:
    """Estimated height in points of a card with the given body size."""
    total = 0.0
    for p in card["paras"]:
        size = HEADER_SIZE if p["kind"] == "header" else body_size
        width = USABLE_W - (BULLET_INDENT if p["kind"] == "bullet" else 0)
        per_line = max(1, int(width / (size * CHAR_EM)))
        if p["kind"] == "blank":
            lines = 1
        else:
            lines, cur = 1, 0
            for word in para_text(p).split():
                need = len(word) + (1 if cur else 0)
                if cur + need > per_line and cur:
                    lines += 1
                    cur = len(word)
                else:
                    cur += need
        total += lines * size * LINE_EM
    return total


def choose_sizes(cards: list[dict]) -> list[str]:
    """Set each card's body size. Returns warnings for cards that will not fit."""
    warns = []
    for i, c in enumerate(cards, 1):
        for p in c["paras"]:
            if p["kind"] == "header" and len(para_text(p)) > HEADER_WARN_CHARS:
                warns.append(f"card {i}: header is {len(para_text(p))} characters, cut the topic short with an ellipsis")
        if c["forced"]:
            c["size"] = c["forced"]
            if estimate_height(c, c["size"]) > USABLE_H * FIT_SLACK:
                warns.append(f"card {i}: will not fit at {c['size']}, split at a sentence")
            continue
        for s in BODY_SIZES:
            if estimate_height(c, s) <= USABLE_H * FIT_SLACK:
                c["size"] = s
                break
        else:
            c["size"] = BODY_SIZES[-1]
            warns.append(f"card {i}: will not fit even at 10, split at a sentence (second card has no header)")
    return warns


def build_requests(cards: list[dict]) -> list[dict]:
    """Google Docs batchUpdate requests that lay the cards onto the Doc."""
    lines, spans = [], []  # spans: (start, end, kind, size, runs)
    idx = 1
    card_last_end = []
    for c in cards:
        for p in c["paras"]:
            txt = para_text(p)
            start = idx
            pos = idx
            run_ranges = []
            for t, b in p["runs"]:
                run_ranges.append((pos, pos + len(t), b))
                pos += len(t)
            spans.append((start, start + len(txt), p["kind"], c["size"], run_ranges))
            lines.append(txt)
            idx = start + len(txt) + 1
        card_last_end.append(idx - 1)
    full = "\n".join(lines)
    end = 1 + len(full)

    def style(a, b, fields, **ts):
        return {"updateTextStyle": {"range": {"startIndex": a, "endIndex": b}, "textStyle": ts, "fields": fields}}

    reqs = [
        {"updateDocumentStyle": {"documentStyle": {
            "pageSize": {"width": {"magnitude": PAGE_W, "unit": "PT"}, "height": {"magnitude": PAGE_H, "unit": "PT"}},
            "marginTop": {"magnitude": MARGIN_TB, "unit": "PT"}, "marginBottom": {"magnitude": MARGIN_TB, "unit": "PT"},
            "marginLeft": {"magnitude": MARGIN_LR, "unit": "PT"}, "marginRight": {"magnitude": MARGIN_LR, "unit": "PT"}},
            "fields": "pageSize,marginTop,marginBottom,marginLeft,marginRight"}},
        {"insertText": {"location": {"index": 1}, "text": full}},
        style(1, end + 1, "weightedFontFamily,fontSize,bold",
              weightedFontFamily={"fontFamily": FONT}, fontSize={"magnitude": 11, "unit": "PT"}, bold=False),
        {"updateParagraphStyle": {"range": {"startIndex": 1, "endIndex": end + 1},
                                  "paragraphStyle": {"lineSpacing": 100, "spaceAbove": {"unit": "PT"}, "spaceBelow": {"unit": "PT"}},
                                  "fields": "lineSpacing,spaceAbove,spaceBelow"}},
    ]
    for start, stop, kind, size, run_ranges in spans:
        if stop == start:
            continue
        if kind == "header":
            reqs.append(style(start, stop, "bold,foregroundColor,fontSize",
                              bold=True, fontSize={"magnitude": HEADER_SIZE, "unit": "PT"},
                              foregroundColor={"color": {"rgbColor": NAVY}}))
            continue
        if size != 11:
            reqs.append(style(start, stop, "fontSize", fontSize={"magnitude": size, "unit": "PT"}))
        for a, b, bold in run_ranges:
            if bold:
                reqs.append(style(a, b, "bold", bold=True))
    # Bullets, one request per consecutive run of bullet paragraphs.
    run = None
    for start, stop, kind, *_ in spans + [(0, 0, "end")]:
        if kind == "bullet":
            run = (run[0], stop) if run else (start, stop)
        elif run:
            reqs.append({"createParagraphBullets": {"range": {"startIndex": run[0], "endIndex": run[1]},
                                                    "bulletPreset": "BULLET_DISC_CIRCLE_SQUARE"}})
            run = None
    # Page breaks go in last, from the end backwards so earlier indexes stay valid.
    for pos in reversed(card_last_end[:-1]):
        reqs.append({"insertPageBreak": {"location": {"index": pos}}})
    return reqs


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def verify_pdf(pdf: bytes, cards: list[dict]) -> list[str]:
    """Problems found in the exported PDF, empty when every card sits on its own page."""
    try:
        import io
        from pypdf import PdfReader
        pages = [pg.extract_text() or "" for pg in PdfReader(io.BytesIO(pdf)).pages]
    except ImportError:
        n = len(re.findall(rb"/Type\s*/Page\b", pdf))
        return [] if n == len(cards) else [f"PDF has {n} pages, expected {len(cards)}"]
    problems = []
    if len(pages) != len(cards):
        problems.append(f"PDF has {len(pages)} pages, expected {len(cards)} cards")
    for i, c in enumerate(cards):
        first = _norm(para_text(c["paras"][0]))[:24]
        if i < len(pages) and first and first not in _norm(pages[i]):
            problems.append(f"card {i + 1} does not start on page {i + 1}, an earlier card probably spilled over")
    return problems


def create(cards: list[dict], title: str, folder: str | None) -> dict:
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except ImportError as e:
        raise CardError(f"missing Google client libraries ({e}). Install google-api-python-client and google-auth.")
    key = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if not key:
        raise CardError("GOOGLE_APPLICATION_CREDENTIALS is not set")
    creds = service_account.Credentials.from_service_account_file(
        key, scopes=["https://www.googleapis.com/auth/documents", "https://www.googleapis.com/auth/drive"])
    subject = os.environ.get("STAGE_CARDS_SUBJECT")
    if subject:
        creds = creds.with_subject(subject)
    docs = build("docs", "v1", credentials=creds, cache_discovery=False)
    drive = build("drive", "v3", credentials=creds, cache_discovery=False)
    doc_id = docs.documents().create(body={"title": title}).execute()["documentId"]
    docs.documents().batchUpdate(documentId=doc_id, body={"requests": build_requests(cards)}).execute()
    if folder:
        parents = drive.files().get(fileId=doc_id, fields="parents").execute().get("parents", [])
        drive.files().update(fileId=doc_id, addParents=folder, removeParents=",".join(parents), fields="id").execute()
    pdf = drive.files().export(fileId=doc_id, mimeType="application/pdf").execute()
    problems = verify_pdf(pdf, cards)
    return {"docId": doc_id, "url": f"https://docs.google.com/document/d/{doc_id}/edit",
            "cards": len(cards), "pdfProblems": problems}


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("check", "requests", "create"):
        sp = sub.add_parser(name)
        sp.add_argument("file")
        if name == "create":
            sp.add_argument("--title", required=True)
            sp.add_argument("--folder")
    a = ap.parse_args(argv)
    try:
        with open(a.file, encoding="utf-8") as f:
            cards = parse(f.read())
        warns = choose_sizes(cards)
        if a.cmd == "check":
            for i, c in enumerate(cards, 1):
                first = para_text(c["paras"][0])[:48]
                print(f"card {i:>2}  size {c['size']}  est {estimate_height(c, c['size']):5.0f}/{USABLE_H} pt  {first}")
            print(f"{len(cards)} cards")
            for w in warns:
                print("WARN", w)
            return 1 if any("will not fit" in w for w in warns) else 0
        if a.cmd == "requests":
            json.dump(build_requests(cards), sys.stdout, indent=1)
            return 0
        res = create(cards, a.title, a.folder)
        print(json.dumps({**res, "warnings": warns}, indent=1))
        return 1 if res["pdfProblems"] else 0
    except CardError as e:
        print(f"ERROR {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
