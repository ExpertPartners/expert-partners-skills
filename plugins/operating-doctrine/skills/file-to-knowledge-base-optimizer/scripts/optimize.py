#!/usr/bin/env python3
"""
optimize.py, the engine for the File to Knowledge Base Optimizer skill.

It does the parts of the job that must come out the same every time. Extracting
text from a source, cleaning it without changing its meaning, estimating size,
splitting long material at section breaks, assembling the optimized Markdown with
its header and fixed sections, naming and saving the files by the company file
rules, archiving a superseded version, and writing the completion report.

The model does the judgment parts (summary, takeaways, topic sections for text
that has no headings, actions and decisions, conflicts between combined sources)
and hands them in as one small JSON file per part. The engine never writes a fact
the source does not hold.

Requirement IDs in comments (R01 to R34, G12 to G22) refer to the approved spec,
[HQ][V1.0] Spec - File to Knowledge Base Optimizer, revision 4.

Python 3.9 or later, standard library only. Optional helpers when installed:
pdfplumber (tables and layout in PDFs), pypdf (fallback PDF text), the pdftotext
and tesseract command line tools, and the Google API client (saving to Drive).

Commands
  extract   --input PATH --work DIR [--kind KIND] [--original-name NAME] [--source-date DATE]
  assemble  --work DIR [DIR ...] --intake FILE --derived DIR --out DIR [--version V1.0] [--combine]
  save      --out DIR --intake FILE --auth sa:PATH --impersonate EMAIL [--source-drive-id ID] [--dry-run]
  finish    (version check, assemble, save, report in one go)
  report    --out DIR
  validate  --derived FILE [--part PART.md ...] [--nav] [--combined]
"""
from __future__ import annotations

import argparse
import datetime as _dt
import difflib
import hashlib
import html as _html
import io
import json
import os
import re
import shutil
import subprocess
import sys
import unicodedata
import zipfile
from html.parser import HTMLParser
from pathlib import Path

TOKEN_CHARS = 4          # one token is estimated as four characters (R12, G16, approximate on purpose)
SPLIT_TOKENS = 50000     # past about 50,000 tokens the material is split (R12, G16)
SMALL_CHANGE_LIMIT = 0.34  # a revised source that changed under a third advances the decimal (R31, G14)
HEADER_ORDER = ["title", "type", "source", "date", "duration", "people", "optimized_for", "optimized_at"]  # R20, R22, G20


# ----------------------------------------------------------------------------
# small helpers
# ----------------------------------------------------------------------------

def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def est_tokens(text: str) -> int:
    return int(round(len(text) / TOKEN_CHARS))


LIGATURES = {"\ufb00": "ff", "\ufb01": "fi", "\ufb02": "fl", "\ufb03": "ffi", "\ufb04": "ffl", "\ufb06": "st"}


def clean_inline(text: str) -> str:
    """Whitespace and invisible-character cleanup only. Words are never changed (R10, G17)."""
    for lig, plain in LIGATURES.items():
        text = text.replace(lig, plain)
    text = unicodedata.normalize("NFC", text)
    text = text.replace(" ", " ").replace("​", "").replace("﻿", "").replace(" ", " ")
    text = text.replace("\x0b", " ").replace("\x0c", "")
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def norm_para(text: str) -> str:
    t = unicodedata.normalize("NFKC", text).lower()
    t = re.sub(r"\s+", " ", t).strip()
    return t


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def read_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def which(cmd: str):
    return shutil.which(cmd)


# ----------------------------------------------------------------------------
# blocks, the common shape of an extracted source
# ----------------------------------------------------------------------------
# heading  {level, text}            level 1 is the source's own top level
# para     {text}
# list     {items: [text]}
# table    {rows: [[cell]]}
# turn     {speaker, cues: [[ts, text]]}   labeled transcript turn (R11, G18)
# cues     {cues: [[ts, text]]}            unlabeled captions grouped by pause
# image    {path, note, ocr: [para]}       a scanned page or picture kept beside its text (G18)
# unreadable {note}                        marked, never guessed (G18, G22)
# code     {text}


def render_blocks(blocks, shift=1):
    """Render blocks to Markdown lines. Source headings shift down one level because the
    document title takes the first level (R17, R21)."""
    lines = []
    for b in blocks:
        t = b["type"]
        if t == "heading":
            level = min(6, max(2, b["level"] + shift))
            lines.append("#" * level + " " + b["text"])
            lines.append("")
        elif t == "para":
            lines.append(b["text"])
            lines.append("")
        elif t == "list":
            for it in b["items"]:
                lines.append("- " + it)
            lines.append("")
        elif t == "table":
            rows = b["rows"]
            if not rows:
                continue
            width = max(len(r) for r in rows)
            norm = [[(c or "").replace("|", "\\|") for c in r] + [""] * (width - len(r)) for r in rows]
            lines.append("| " + " | ".join(norm[0]) + " |")
            lines.append("|" + "|".join([" --- "] * width) + "|")
            for r in norm[1:]:
                lines.append("| " + " | ".join(r) + " |")
            lines.append("")
        elif t == "turn":
            parts = ["[" + ts + "] " + tx for ts, tx in b["cues"]]
            lines.append(b["speaker"] + ": " + " ".join(parts))
            lines.append("")
        elif t == "cues":
            parts = ["[" + ts + "] " + tx for ts, tx in b["cues"]]
            lines.append(" ".join(parts))
            lines.append("")
        elif t == "image":
            lines.append("![" + b.get("note", "image") + "](" + b["path"] + ")")
            lines.append("")
            for p in b.get("ocr", []):
                lines.append(p)
                lines.append("")
        elif t == "unreadable":
            lines.append("[unreadable: " + b["note"] + "]")
            lines.append("")
        elif t == "code":
            lines.append("```")
            lines.extend(b["text"].splitlines())
            lines.append("```")
            lines.append("")
    while lines and lines[-1] == "":
        lines.pop()
    return lines


def block_stats(blocks):
    stats = {"headings": 0, "paragraphs": 0, "tables": 0, "turns": 0, "cue_groups": 0, "timestamps": 0,
             "images": 0, "unreadable": 0, "links": 0, "speakers": []}
    speakers = []
    for b in blocks:
        t = b["type"]
        if t == "heading":
            stats["headings"] += 1
        elif t == "para":
            stats["paragraphs"] += 1
            stats["links"] += len(re.findall(r"https?://\S+", b["text"]))
        elif t == "table":
            stats["tables"] += 1
            for r in b["rows"]:
                for c in r:
                    stats["links"] += len(re.findall(r"https?://\S+", c or ""))
        elif t == "turn":
            stats["turns"] += 1
            stats["timestamps"] += len(b["cues"])
            if b["speaker"] not in speakers:
                speakers.append(b["speaker"])
        elif t == "cues":
            stats["cue_groups"] += 1
            stats["timestamps"] += len(b["cues"])
        elif t == "image":
            stats["images"] += 1
        elif t == "unreadable":
            stats["unreadable"] += 1
    stats["speakers"] = speakers
    return stats


# ----------------------------------------------------------------------------
# extraction routes (R05, R06, R09)
# ----------------------------------------------------------------------------

def detect_kind(path: Path, kind: str) -> str:
    if kind and kind != "auto":
        return kind
    ext = path.suffix.lower()
    if ext == ".json":
        try:
            d = read_json(path)
            if isinstance(d, dict) and ("tabs" in d or "body" in d) and "documentId" in d:
                return "gdoc-json"
        except Exception:
            pass
        return "txt"
    return {".pdf": "pdf", ".docx": "docx", ".vtt": "vtt", ".srt": "srt", ".md": "md", ".markdown": "md",
            ".txt": "txt", ".html": "html", ".htm": "html", ".mp3": "audio", ".m4a": "audio", ".wav": "audio",
            ".mp4": "video", ".mov": "video"}.get(ext, "txt")


# --- Google Doc, from the Docs API JSON with every tab (R05) ----------------

def _gdoc_elements_text(elements, notes):
    out = []
    for pe in elements:
        if "textRun" in pe:
            tr = pe["textRun"]
            t = tr.get("content", "")
            link = ((tr.get("textStyle") or {}).get("link") or {}).get("url")
            if link and t.strip():
                trail = "\n" if t.endswith("\n") else ""
                out.append("[" + t.strip() + "](" + link + ")" + trail)
            else:
                out.append(t)
        elif "footnoteReference" in pe:
            out.append("[" + str(pe["footnoteReference"].get("footnoteNumber", "?")) + "]")
        elif "inlineObjectElement" in pe:
            out.append("[image: " + pe["inlineObjectElement"].get("inlineObjectId", "object") + "]")
            notes.append("inline image " + pe["inlineObjectElement"].get("inlineObjectId", "") + " is kept as a placeholder, the picture itself was not exported")
        elif "richLink" in pe:
            rp = pe["richLink"].get("richLinkProperties", {})
            out.append("[" + rp.get("title", rp.get("uri", "link")) + "](" + rp.get("uri", "") + ")")
        elif "person" in pe:
            out.append(pe["person"].get("personProperties", {}).get("name", ""))
        elif "equation" in pe:
            out.append("[equation]")
            notes.append("an equation is kept as a placeholder")
    return "".join(out).replace("\x0b", " ")


def _gdoc_body(content, blocks, notes, footnotes):
    pending_list = None
    for e in content:
        if "paragraph" in e:
            p = e["paragraph"]
            text = clean_inline(_gdoc_elements_text(p.get("elements", []), notes))
            style = (p.get("paragraphStyle") or {}).get("namedStyleType", "NORMAL_TEXT")
            if not text:
                continue
            if "bullet" in p:
                lvl = p["bullet"].get("nestingLevel", 0)
                if pending_list is None:
                    pending_list = {"type": "list", "items": []}
                    blocks.append(pending_list)
                pending_list["items"].append(("  " * lvl) + text)
                continue
            pending_list = None
            if style.startswith("HEADING_"):
                blocks.append({"type": "heading", "level": int(style.split("_")[1]) + 1, "text": text})
            elif style in ("TITLE", "SUBTITLE"):
                blocks.append({"type": "heading", "level": 1, "text": text})
            else:
                blocks.append({"type": "para", "text": text})
        elif "table" in e:
            pending_list = None
            rows = []
            for r in e["table"].get("tableRows", []):
                row = []
                for c in r.get("tableCells", []):
                    cell_parts = []
                    for ce in c.get("content", []):
                        if "paragraph" in ce:
                            cell_parts.append(clean_inline(_gdoc_elements_text(ce["paragraph"].get("elements", []), notes)))
                    row.append(" ".join(x for x in cell_parts if x))
                rows.append(row)
            blocks.append({"type": "table", "rows": rows})
        elif "tableOfContents" in e:
            pending_list = None
            _gdoc_body(e["tableOfContents"].get("content", []), blocks, notes, footnotes)
        else:
            pending_list = None


def extract_gdoc_json(path: Path, notes):
    d = read_json(path)
    blocks = []
    footnotes = d.get("footnotes", {})

    def walk(tabs, depth):
        for t in tabs:
            title = (t.get("tabProperties") or {}).get("title", "Tab")
            blocks.append({"type": "heading", "level": 1 + depth, "text": title})
            body = (t.get("documentTab") or {}).get("body", {}).get("content", [])
            _gdoc_body(body, blocks, notes, footnotes)
            walk(t.get("childTabs", []), depth + 1)

    if d.get("tabs"):
        walk(d["tabs"], 0)
    else:
        _gdoc_body(d.get("body", {}).get("content", []), blocks, notes, footnotes)
    if footnotes:
        blocks.append({"type": "heading", "level": 1, "text": "Footnotes"})
        for fid, fn in footnotes.items():
            parts = []
            for ce in fn.get("content", []):
                if "paragraph" in ce:
                    parts.append(clean_inline(_gdoc_elements_text(ce["paragraph"].get("elements", []), notes)))
            blocks.append({"type": "para", "text": "[" + fid + "] " + " ".join(x for x in parts if x)})
    return blocks, {"kind": "Google Doc", "tabs": len(d.get("tabs", [])) or 1, "title": d.get("title", "")}


# --- Word document (R06) ----------------------------------------------------

def extract_docx(path: Path, notes):
    import xml.etree.ElementTree as ET
    W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
    blocks = []
    with zipfile.ZipFile(path) as z:
        rels = {}
        try:
            rx = ET.fromstring(z.read("word/_rels/document.xml.rels"))
            for rel in rx:
                rels[rel.get("Id")] = rel.get("Target")
        except KeyError:
            pass
        root = ET.fromstring(z.read("word/document.xml"))
    body = root.find(W + "body")

    def run_text(el):
        out = []
        for node in el.iter():
            if node.tag == W + "t":
                out.append(node.text or "")
            elif node.tag == W + "tab":
                out.append(" ")
            elif node.tag == W + "br":
                out.append(" ")
            elif node.tag == W + "drawing":
                out.append("[image]")
                notes.append("an embedded picture is kept as a placeholder")
        return "".join(out)

    def para_text(p):
        out = []
        for child in p:
            if child.tag == W + "hyperlink":
                target = rels.get(child.get(R + "id"), "")
                txt = run_text(child)
                out.append("[" + txt + "](" + target + ")" if target else txt)
            else:
                out.append(run_text(child))
        return clean_inline("".join(out))

    pending_list = None
    for el in body:
        if el.tag == W + "p":
            text = para_text(el)
            if not text:
                continue
            ppr = el.find(W + "pPr")
            style = ""
            is_list = False
            if ppr is not None:
                ps = ppr.find(W + "pStyle")
                if ps is not None:
                    style = ps.get(W + "val", "")
                if ppr.find(W + "numPr") is not None:
                    is_list = True
            if is_list:
                if pending_list is None:
                    pending_list = {"type": "list", "items": []}
                    blocks.append(pending_list)
                pending_list["items"].append(text)
                continue
            pending_list = None
            m = re.match(r"(?i)heading\s*(\d)", style)
            if m:
                blocks.append({"type": "heading", "level": int(m.group(1)), "text": text})
            elif style.lower() in ("title", "subtitle"):
                blocks.append({"type": "heading", "level": 1, "text": text})
            else:
                blocks.append({"type": "para", "text": text})
        elif el.tag == W + "tbl":
            pending_list = None
            rows = []
            for tr in el.findall(W + "tr"):
                row = []
                for tc in tr.findall(W + "tc"):
                    row.append(" ".join(x for x in (para_text(p) for p in tc.findall(W + "p")) if x))
                rows.append(row)
            blocks.append({"type": "table", "rows": rows})
    return blocks, {"kind": "Word document"}


# --- PDF (R09, R10, G18) ----------------------------------------------------

PAGE_NUMBER_RE = re.compile(r"^\s*(page\s*)?\d{1,4}(\s*(of|/)\s*\d{1,4})?\s*$", re.I)


def _lines_to_paras(lines, cleanup):
    """lines: list of dicts with text, top, bottom, size. Join lines into paragraphs by
    vertical gap, repair hyphenation and broken line endings (R10)."""
    paras = []
    cur = None
    for ln in lines:
        text = clean_inline(ln["text"])
        if not text:
            continue
        if cur is None:
            cur = {"text": text, "size": ln["size"], "lines": 1, "top": ln["top"], "bottom": ln["bottom"]}
            continue
        gap = ln["top"] - cur["bottom"]
        height = max(1.0, ln["bottom"] - ln["top"])
        size_jump = abs(ln["size"] - cur["size"]) > 1.0
        if gap > 0.55 * height or size_jump:
            paras.append(cur)
            cur = {"text": text, "size": ln["size"], "lines": 1, "top": ln["top"], "bottom": ln["bottom"]}
        else:
            prev = cur["text"]
            if prev.endswith("-") and text[:1].islower():
                cur["text"] = prev[:-1] + text
                cleanup.add("hyphenation at line breaks repaired")
            else:
                cur["text"] = prev + " " + text
                cleanup.add("broken line endings joined")
            cur["lines"] += 1
            cur["bottom"] = ln["bottom"]
    if cur is not None:
        paras.append(cur)
    return paras


def _repair_glyphs(text: str, ref: str, notes, cleanup, page: int) -> str:
    """A glyph the PDF font does not map (it arrives as a null character, often a ligature) is
    restored from a second, independent read of the same page when exactly one reading fits the
    letters around it. Otherwise it is marked unreadable, never guessed (G18, R10)."""
    if "\x00" not in text:
        return text
    out = text
    guard = 0
    while "\x00" in out and guard < 200:
        guard += 1
        i = out.index("\x00")
        j = i
        while j < len(out) and out[j] == "\x00":
            j += 1
        pre = out[max(0, i - 8):i]
        suf = out[j:j + 8]
        found = set()
        if ref and (pre.strip() or suf.strip()):
            pat = re.escape(pre) + r"(\S{1,4})" + re.escape(suf)
            found = {m.group(1) for m in re.finditer(pat, ref)}
        if len(found) == 1:
            out = out[:i] + found.pop() + out[j:]
            cleanup.add("unmapped glyphs restored from a second read of the same page")
        else:
            out = out[:i] + "[unreadable character]" + out[j:]
            notes.append("page %d holds a glyph the font does not map, it is marked unreadable" % page)
    return out


def _page_reference_text(path: Path, pno: int) -> str:
    if not which("pdftotext"):
        return ""
    try:
        res = subprocess.run(["pdftotext", "-f", str(pno), "-l", str(pno), str(path), "-"], capture_output=True, text=True, timeout=60)
        return re.sub(r"\s+", " ", res.stdout)
    except Exception:
        return ""


def _continues(prev: str, nxt: str) -> bool:
    """True when a page's first paragraph is the tail of the previous page's last one."""
    if not prev or not nxt:
        return False
    if prev.endswith("-") and nxt[:1].islower():
        return True
    ends_sentence = bool(re.search(r"[.!?:;\"\u201d\u2019)\]]$", prev))
    return (not ends_sentence) and (nxt[:1].islower() or nxt[:1] in ",;)")


def extract_pdf(path: Path, work: Path, notes, cleanup):
    try:
        import pdfplumber  # type: ignore
    except ImportError:
        return extract_pdf_fallback(path, work, notes, cleanup)
    blocks = []
    pages_meta = []
    tops, bottoms = {}, {}
    page_items = []
    with pdfplumber.open(str(path)) as pdf:
        meta = pdf.metadata or {}
        for pno, page in enumerate(pdf.pages, 1):
            text_all = page.extract_text() or ""
            items = []
            if len(text_all.strip()) < 25:
                # a scanned page, keep the picture beside readable text (G18)
                img_dir = work / "images"
                img_dir.mkdir(parents=True, exist_ok=True)
                img_path = img_dir / ("page-%d.png" % pno)
                ocr_paras = []
                try:
                    page.to_image(resolution=200).save(str(img_path))
                    if which("tesseract"):
                        res = subprocess.run(["tesseract", str(img_path), "stdout"], capture_output=True, text=True)
                        for chunk in re.split(r"\n\s*\n", res.stdout):
                            c = clean_inline(chunk.replace("\n", " "))
                            if c:
                                ocr_paras.append(c)
                    else:
                        notes.append("page %d is a scan and no OCR tool is installed, marked unreadable" % pno)
                except Exception as exc:  # pragma: no cover
                    notes.append("page %d could not be rendered: %s" % (pno, exc))
                blk = {"type": "image", "path": "images/page-%d.png" % pno, "note": "scanned page %d" % pno, "ocr": ocr_paras}
                items.append(("image", blk))
                if not ocr_paras:
                    items.append(("unreadable", {"type": "unreadable", "note": "scanned page %d, no readable text could be recovered" % pno}))
                page_items.append(items)
                pages_meta.append({"page": pno, "scanned": True})
                continue
            tables = page.find_tables()
            tables = sorted(tables, key=lambda t: t.bbox[1])
            y = 0.0

            def band_lines(y0, y1):
                if y1 - y0 < 2:
                    return []
                region = page.crop((0, max(0, y0), page.width, min(page.height, y1)), strict=False)
                out = []
                try:
                    for ln in region.extract_text_lines(layout=False, strip=True, return_chars=True):
                        sizes = [c.get("size", 0) for c in ln.get("chars", []) if c.get("size")]
                        size = sorted(sizes)[len(sizes) // 2] if sizes else 0
                        out.append({"text": ln["text"], "top": ln["top"], "bottom": ln["bottom"], "size": size})
                except Exception:
                    for t in (region.extract_text() or "").splitlines():
                        out.append({"text": t, "top": 0, "bottom": 0, "size": 0})
                return out

            for t in tables:
                x0, top, x1, bottom = t.bbox
                items.append(("lines", band_lines(y, top)))
                rows = [[clean_inline((c or "").replace("\n", " ")) for c in r] for r in t.extract()]
                # drop columns that are empty in every row
                if rows:
                    width = max(len(r) for r in rows)
                    keep = [j for j in range(width) if any(j < len(r) and r[j] for r in rows)]
                    rows = [[r[j] if j < len(r) else "" for j in keep] for r in rows]
                items.append(("table", {"type": "table", "rows": rows}))
                y = bottom
            items.append(("lines", band_lines(y, page.height)))
            page_items.append(items)
            # candidates for running headers and footers and page numbers
            all_lines = [ln for kind, payload in items if kind == "lines" for ln in payload]
            if all_lines:
                first = clean_inline(all_lines[0]["text"])
                last = clean_inline(all_lines[-1]["text"])
                tops[first] = tops.get(first, 0) + 1
                bottoms[last] = bottoms.get(last, 0) + 1
            pages_meta.append({"page": pno, "scanned": False, "tables": len(tables)})
        page_count = len(pdf.pages)
    running = {t for t, n in tops.items() if n >= 3} | {t for t, n in bottoms.items() if n >= 3}
    running = {t for t in running if len(t) < 120}
    # body font size for heading detection
    sizes = []
    for items in page_items:
        for kind, payload in items:
            if kind == "lines":
                sizes.extend(ln["size"] for ln in payload if ln["size"])
    body_size = sorted(sizes)[len(sizes) // 2] if sizes else 0
    for page_index, items in enumerate(page_items):
        fresh_page = True
        pno = page_index + 1
        ref = None
        for kind, payload in items:
            if kind == "lines":
                kept = []
                for i, ln in enumerate(payload):
                    txt = clean_inline(ln["text"])
                    edge = i == 0 or i == len(payload) - 1
                    if edge and PAGE_NUMBER_RE.match(txt):
                        cleanup.add("page numbers removed")
                        continue
                    if edge and txt in running:
                        cleanup.add("running headers and footers removed")
                        continue
                    kept.append(ln)
                for p in _lines_to_paras(kept, cleanup):
                    if "\x00" in p["text"]:
                        if ref is None:
                            ref = _page_reference_text(path, pno)
                        p["text"] = _repair_glyphs(p["text"], ref, notes, cleanup, pno)
                    is_heading = (p["lines"] == 1 and len(p["text"]) <= 90 and body_size and p["size"] >= body_size * 1.12
                                  and not p["text"].endswith((".", ",", ";")))
                    if is_heading:
                        blocks.append({"type": "heading", "level": 2, "text": p["text"], "_size": round(p["size"], 1)})
                    elif fresh_page and blocks and blocks[-1]["type"] == "para" and _continues(blocks[-1]["text"], p["text"]):
                        # a paragraph that crosses the page break is one paragraph (R10)
                        prev = blocks[-1]["text"]
                        blocks[-1]["text"] = (prev[:-1] + p["text"]) if prev.endswith("-") else (prev + " " + p["text"])
                        cleanup.add("paragraphs rejoined across page breaks")
                    else:
                        blocks.append({"type": "para", "text": p["text"]})
                    fresh_page = False
            else:
                if payload.get("type") == "table":
                    for row in payload["rows"]:
                        for ci, cell in enumerate(row):
                            if cell and "\x00" in cell:
                                if ref is None:
                                    ref = _page_reference_text(path, pno)
                                row[ci] = _repair_glyphs(cell, ref, notes, cleanup, pno)
                blocks.append(payload)
                fresh_page = False
    # heading levels follow the distinct heading sizes, the largest is the top level (R17)
    sizes = sorted({b["_size"] for b in blocks if b["type"] == "heading" and "_size" in b}, reverse=True)
    for b in blocks:
        if b["type"] == "heading" and "_size" in b:
            b["level"] = min(3, sizes.index(b.pop("_size")) + 1)
    created = ""
    raw = (meta.get("CreationDate") or "") if isinstance(meta, dict) else ""
    m = re.search(r"D:(\d{4})(\d{2})(\d{2})", str(raw))
    if m:
        created = "%s-%s-%s" % m.groups()
    return blocks, {"kind": "PDF", "pages": page_count, "pdf_created": created, "route": "pdfplumber"}


def extract_pdf_fallback(path: Path, work: Path, notes, cleanup):
    text = ""
    route = ""
    if which("pdftotext"):
        res = subprocess.run(["pdftotext", "-layout", str(path), "-"], capture_output=True, text=True)
        text = res.stdout
        route = "pdftotext"
    else:
        try:
            from pypdf import PdfReader  # type: ignore
            reader = PdfReader(str(path))
            text = "\n\x0c".join((p.extract_text() or "") for p in reader.pages)
            route = "pypdf"
        except ImportError:
            raise RuntimeError("no PDF reader is available (install pdfplumber, pypdf or pdftotext)")
    notes.append("tables could not be detected on this route (" + route + "), their layout text is kept as it was")
    blocks = []
    for page in text.split("\x0c"):
        lines = [l.rstrip() for l in page.splitlines()]
        para = []
        for i, l in enumerate(lines):
            s = clean_inline(l)
            if not s:
                if para:
                    blocks.append({"type": "para", "text": " ".join(para)})
                    cleanup.add("broken line endings joined")
                    para = []
                continue
            if (i == 0 or i == len(lines) - 1) and PAGE_NUMBER_RE.match(s):
                cleanup.add("page numbers removed")
                continue
            if para and para[-1].endswith("-") and s[:1].islower():
                para[-1] = para[-1][:-1] + s
                cleanup.add("hyphenation at line breaks repaired")
            else:
                para.append(s)
        if para:
            blocks.append({"type": "para", "text": " ".join(para)})
    return blocks, {"kind": "PDF", "route": route}


# --- captions, WebVTT and SRT (R05, R11, G18) -------------------------------

TIMING_RE = re.compile(r"^(\d{1,2}:\d{2}:\d{2}[.,]\d{3}|\d{1,2}:\d{2}[.,]\d{3})\s*-->\s*(\d{1,2}:\d{2}:\d{2}[.,]\d{3}|\d{1,2}:\d{2}[.,]\d{3})")
VOICE_RE = re.compile(r"<v\s+([^>]+)>(.*?)(</v>|$)", re.S)
LABEL_RE = re.compile(r"^([^:\n]{1,40}?):\s+(.*)$", re.S)


def _ts_seconds(ts: str) -> float:
    ts = ts.replace(",", ".")
    parts = ts.split(":")
    parts = [float(p) for p in parts]
    while len(parts) < 3:
        parts.insert(0, 0.0)
    return parts[0] * 3600 + parts[1] * 60 + parts[2]


def _duration_words(seconds: float) -> str:
    s = int(round(seconds))
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    out = []
    if h:
        out.append("%d hour%s" % (h, "" if h == 1 else "s"))
    if m:
        out.append("%d minute%s" % (m, "" if m == 1 else "s"))
    out.append("%d second%s" % (sec, "" if sec == 1 else "s"))
    return " ".join(out)


def extract_captions(path: Path, notes, cleanup):
    raw = path.read_text(encoding="utf-8", errors="replace")
    raw = raw.replace("\r\n", "\n").replace("\r", "\n")
    cues = []
    block = []
    for line in raw.split("\n") + [""]:
        if line.strip() == "":
            if block:
                timing_idx = None
                for i, l in enumerate(block):
                    if TIMING_RE.match(l.strip()):
                        timing_idx = i
                        break
                if timing_idx is not None:
                    m = TIMING_RE.match(block[timing_idx].strip())
                    text = " ".join(clean_inline(x) for x in block[timing_idx + 1:] if clean_inline(x))
                    text = re.sub(r"</?[biu]>", "", text)
                    speaker = ""
                    vm = VOICE_RE.search(text)
                    if vm:
                        speaker = clean_inline(vm.group(1))
                        text = clean_inline(VOICE_RE.sub(lambda mm: mm.group(2), text))
                    cues.append({"start": m.group(1), "end": m.group(2), "text": text, "speaker": speaker})
                block = []
        else:
            block.append(line)
    if not cues:
        raise RuntimeError("no caption cues were found in the file")
    # labels written as Name: text count as speaker labels when they repeat (R11)
    counts = {}
    for c in cues:
        if not c["speaker"]:
            m = LABEL_RE.match(c["text"])
            if m and not re.search(r"\d", m.group(1).split("(")[0]):
                counts[m.group(1)] = counts.get(m.group(1), 0) + 1
    labels = {k for k, n in counts.items() if n >= 2}
    for c in cues:
        if not c["speaker"]:
            m = LABEL_RE.match(c["text"])
            if m and m.group(1) in labels:
                c["speaker"] = m.group(1)
                c["text"] = clean_inline(m.group(2))
    blocks = []
    cur = None
    for c in cues:
        if c["speaker"]:
            if cur and cur["type"] == "turn" and cur["speaker"] == c["speaker"]:
                cur["cues"].append([c["start"], c["text"]])
            else:
                cur = {"type": "turn", "speaker": c["speaker"], "cues": [[c["start"], c["text"]]]}
                blocks.append(cur)
            cleanup.add("caption fragments joined into speaker turns")
        else:
            keep = False
            if cur and cur["type"] == "cues":
                gap = _ts_seconds(c["start"]) - _ts_seconds(cur["cues"][-1][0])
                ends_sentence = bool(re.search(r"[.!?\u2026]['\")\]]?$", cur["cues"][-1][1]))
                # a paragraph ends at a sentence end, never mid sentence (R10)
                keep = (not ends_sentence and len(cur["cues"]) < 40) or (gap <= 8.0 and len(cur["cues"]) < 12)
            if keep:
                cur["cues"].append([c["start"], c["text"]])
            else:
                cur = {"type": "cues", "cues": [[c["start"], c["text"]]]}
                blocks.append(cur)
            cleanup.add("caption fragments grouped into paragraphs at pauses")
    duration = _duration_words(_ts_seconds(cues[-1]["end"]))
    return blocks, {"kind": "captions (" + path.suffix.lstrip(".").upper() + ")", "cues": len(cues), "duration": duration,
                    "duration_basis": "from the last caption end time " + cues[-1]["end"],
                    "speaker_labels": sorted(labels) if labels else [], "route": "caption parser"}


# --- plain text and Markdown (R05) ------------------------------------------

def extract_text(path: Path, notes, cleanup):
    raw = path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")
    blocks = []
    lines = raw.split("\n")
    i = 0
    para = []

    def flush():
        if para:
            blocks.append({"type": "para", "text": clean_inline(" ".join(para))})
            para.clear()

    while i < len(lines):
        l = lines[i]
        s = l.strip()
        if s.startswith("```"):
            flush()
            code = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code.append(lines[i])
                i += 1
            blocks.append({"type": "code", "text": "\n".join(code)})
            i += 1
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", s)
        if m:
            flush()
            blocks.append({"type": "heading", "level": len(m.group(1)), "text": clean_inline(m.group(2))})
            i += 1
            continue
        if s.startswith("|") and i + 1 < len(lines) and re.match(r"^\|?\s*:?-{3,}", lines[i + 1].strip()):
            flush()
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                row_s = lines[i].strip()
                if not re.match(r"^\|?\s*:?-{3,}", row_s):
                    cells = [clean_inline(c) for c in row_s.strip("|").split("|")]
                    rows.append(cells)
                i += 1
            blocks.append({"type": "table", "rows": rows})
            continue
        if re.match(r"^[-*+]\s+", s) or re.match(r"^\d+[.)]\s+", s):
            flush()
            items = []
            while i < len(lines) and (re.match(r"^[-*+]\s+", lines[i].strip()) or re.match(r"^\d+[.)]\s+", lines[i].strip())):
                items.append(clean_inline(re.sub(r"^([-*+]|\d+[.)])\s+", "", lines[i].strip())))
                i += 1
            blocks.append({"type": "list", "items": items})
            continue
        if s == "":
            flush()
        else:
            if para and para[-1].endswith("-") and s[:1].islower():
                para[-1] = para[-1][:-1] + s
                cleanup.add("hyphenation at line breaks repaired")
            else:
                if para:
                    cleanup.add("broken line endings joined")
                para.append(s)
        i += 1
    flush()
    return blocks, {"kind": "text", "route": "text parser"}


# --- web page, navigation and advertising removed (R09) --------------------

class _HtmlToBlocks(HTMLParser):
    SKIP = {"script", "style", "nav", "header", "footer", "aside", "noscript", "iframe", "form", "svg"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.blocks = []
        self.skip_depth = 0
        self.buf = []
        self.in_heading = 0
        self.in_table = False
        self.rows = []
        self.row = None
        self.cell = None
        self.list_items = None
        self.href = None
        self.saw_main = False
        self.in_main = False

    def _flush(self):
        text = clean_inline("".join(self.buf))
        self.buf = []
        if not text:
            return
        if self.in_heading:
            self.blocks.append({"type": "heading", "level": self.in_heading, "text": text})
        elif self.list_items is not None:
            self.list_items.append(text)
        else:
            self.blocks.append({"type": "para", "text": text})

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skip_depth += 1
            return
        if self.skip_depth:
            return
        if tag in ("main", "article"):
            self.saw_main = True
            self.in_main = True
        if tag in ("p", "div", "br", "section"):
            self._flush()
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self._flush()
            self.in_heading = int(tag[1])
        elif tag in ("ul", "ol"):
            self._flush()
            self.list_items = []
        elif tag == "li":
            self._flush()
        elif tag == "table":
            self._flush()
            self.in_table = True
            self.rows = []
        elif tag == "tr":
            self.row = []
        elif tag in ("td", "th"):
            self.cell = []
        elif tag == "a":
            for k, v in attrs:
                if k == "href":
                    self.href = v

    def handle_endtag(self, tag):
        if tag in self.SKIP:
            self.skip_depth = max(0, self.skip_depth - 1)
            return
        if self.skip_depth:
            return
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self._flush()
            self.in_heading = 0
        elif tag in ("p", "div", "section", "li"):
            self._flush()
        elif tag in ("ul", "ol"):
            self._flush()
            if self.list_items:
                self.blocks.append({"type": "list", "items": self.list_items})
            self.list_items = None
        elif tag in ("td", "th"):
            if self.row is not None and self.cell is not None:
                self.row.append(clean_inline("".join(self.cell)))
            self.cell = None
        elif tag == "tr":
            if self.row:
                self.rows.append(self.row)
            self.row = None
        elif tag == "table":
            if self.rows:
                self.blocks.append({"type": "table", "rows": self.rows})
            self.in_table = False
        elif tag == "a":
            self.href = None
        elif tag in ("main", "article"):
            self.in_main = False

    def handle_data(self, data):
        if self.skip_depth:
            return
        if self.cell is not None:
            self.cell.append(data)
            return
        if self.href and data.strip():
            self.buf.append("[" + data.strip() + "](" + self.href + ")")
        else:
            self.buf.append(data)


def extract_html(path: Path, notes, cleanup):
    raw = path.read_text(encoding="utf-8", errors="replace")
    p = _HtmlToBlocks()
    p.feed(raw)
    p._flush()
    cleanup.add("navigation, menus, scripts and advertising containers removed")
    return p.blocks, {"kind": "web page", "route": "html parser"}


# --- audio and video, transcription with Whisper when available (R09) ------

def extract_media(path: Path, work: Path, notes, cleanup):
    if which("whisper"):
        out_dir = work / "transcription"
        out_dir.mkdir(parents=True, exist_ok=True)
        subprocess.run(["whisper", str(path), "--output_format", "vtt", "--output_dir", str(out_dir)], capture_output=True, text=True)
        vtts = list(out_dir.glob("*.vtt"))
        if vtts:
            blocks, info = extract_captions(vtts[0], notes, cleanup)
            info["kind"] = "recording transcribed with Whisper"
            return blocks, info
    raise RuntimeError("the recording could not be transcribed, no Whisper transcription is available in this session")


# --- the extract command ----------------------------------------------------

def propose_parts(lines):
    """Split rendered Markdown lines into parts at section breaks when the whole is past
    about 50,000 tokens (R12, G16). Returns list of parts, each {start, end, tokens, headings}."""
    total = est_tokens("\n".join(lines))
    if total <= SPLIT_TOKENS:
        return [{"start": 1, "end": len(lines), "tokens": total, "headings": _headings_in(lines, 0, len(lines)), "break": "whole file"}]
    # sections at the top heading level present
    levels = [len(re.match(r"^(#+)\s", l).group(1)) for l in lines if re.match(r"^(#+)\s", l)]
    if not levels:
        return _split_paragraphs(lines)
    top = min(levels)
    parts = []
    bounds = [i for i, l in enumerate(lines) if re.match(r"^#{%d}\s" % top, l)]
    if bounds and bounds[0] != 0:
        bounds.insert(0, 0)
    bounds.append(len(lines))
    sections = [(bounds[i], bounds[i + 1]) for i in range(len(bounds) - 1)]
    cur_start, cur_tokens = None, 0
    for s, e in sections:
        sec_tokens = est_tokens("\n".join(lines[s:e]))
        if sec_tokens > SPLIT_TOKENS:
            if cur_start is not None:
                parts.append({"start": cur_start + 1, "end": s, "tokens": cur_tokens, "break": "section break"})
                cur_start, cur_tokens = None, 0
            for sub in propose_parts_sub(lines, s, e, top):
                parts.append(sub)
            continue
        if cur_start is None:
            cur_start, cur_tokens = s, sec_tokens
        elif cur_tokens + sec_tokens > SPLIT_TOKENS:
            parts.append({"start": cur_start + 1, "end": s, "tokens": cur_tokens, "break": "section break"})
            cur_start, cur_tokens = s, sec_tokens
        else:
            cur_tokens += sec_tokens
    if cur_start is not None:
        parts.append({"start": cur_start + 1, "end": len(lines), "tokens": cur_tokens, "break": "section break"})
    for p in parts:
        p["headings"] = _headings_in(lines, p["start"] - 1, p["end"])
    return parts


def propose_parts_sub(lines, s, e, top):
    sub_levels = [len(re.match(r"^(#+)\s", l).group(1)) for l in lines[s + 1:e] if re.match(r"^(#+)\s", l)]
    deeper = [lv for lv in sub_levels if lv > top]
    if not deeper:
        return _split_paragraphs(lines[s:e], offset=s)
    nxt = min(deeper)
    bounds = [s] + [s + 1 + i for i, l in enumerate(lines[s + 1:e]) if re.match(r"^#{%d}\s" % nxt, l)] + [e]
    out = []
    cur_start, cur_tokens = None, 0
    for i in range(len(bounds) - 1):
        a, b = bounds[i], bounds[i + 1]
        t = est_tokens("\n".join(lines[a:b]))
        if t > SPLIT_TOKENS:
            if cur_start is not None:
                out.append({"start": cur_start + 1, "end": a, "tokens": cur_tokens, "break": "section break"})
                cur_start, cur_tokens = None, 0
            out.extend(_split_paragraphs(lines[a:b], offset=a))
            continue
        if cur_start is None:
            cur_start, cur_tokens = a, t
        elif cur_tokens + t > SPLIT_TOKENS:
            out.append({"start": cur_start + 1, "end": a, "tokens": cur_tokens, "break": "section break"})
            cur_start, cur_tokens = a, t
        else:
            cur_tokens += t
    if cur_start is not None:
        out.append({"start": cur_start + 1, "end": e, "tokens": cur_tokens, "break": "section break"})
    return out


def _split_paragraphs(lines, offset=0):
    """A stretch with no smaller section breaks is split at paragraph breaks, and the
    navigation page says so (G16 keeps the threshold approximate)."""
    out = []
    cur_start, cur_tokens = 0, 0
    i = 0
    while i < len(lines):
        j = i
        while j < len(lines) and lines[j] != "":
            j += 1
        t = est_tokens("\n".join(lines[i:j]))
        if cur_tokens + t > SPLIT_TOKENS and j > cur_start:
            out.append({"start": offset + cur_start + 1, "end": offset + i, "tokens": cur_tokens, "break": "paragraph break, this stretch has no section breaks"})
            cur_start, cur_tokens = i, 0
        cur_tokens += t
        i = j + 1
    out.append({"start": offset + cur_start + 1, "end": offset + len(lines), "tokens": cur_tokens, "break": "paragraph break, this stretch has no section breaks"})
    return out


def _headings_in(lines, a, b):
    return [re.sub(r"^#+\s+", "", l) for l in lines[a:b] if re.match(r"^#+\s", l)]


def cmd_extract(args):
    path = Path(args.input)
    work = Path(args.work)
    work.mkdir(parents=True, exist_ok=True)
    kind = detect_kind(path, args.kind)
    notes = []
    cleanup = set()
    info = {}
    try:
        if kind == "gdoc-json":
            blocks, info = extract_gdoc_json(path, notes)
        elif kind == "docx":
            blocks, info = extract_docx(path, notes)
        elif kind == "pdf":
            blocks, info = extract_pdf(path, work, notes, cleanup)
        elif kind in ("vtt", "srt"):
            blocks, info = extract_captions(path, notes, cleanup)
        elif kind == "html":
            blocks, info = extract_html(path, notes, cleanup)
        elif kind in ("audio", "video"):
            blocks, info = extract_media(path, work, notes, cleanup)
        else:
            blocks, info = extract_text(path, notes, cleanup)
    except Exception as exc:
        # G22, stop on this file, say exactly what failed, invent nothing
        failure = {"status": "failed", "input": str(path), "kind": kind, "error": str(exc)}
        write_json(work / "source.meta.json", failure)
        print(json.dumps(failure, indent=1))
        return 2
    lines = render_blocks(blocks)
    text = "\n".join(lines) + "\n"
    (work / "source.md").write_text(text, encoding="utf-8")
    write_json(work / "source.blocks.json", blocks)
    stats = block_stats(blocks)
    original_name = args.original_name or path.name
    date_from_name = ""
    m = re.search(r"(20\d{2})[-_.](\d{2})[-_.](\d{2})", original_name)
    if m:
        date_from_name = "%s-%s-%s" % m.groups()
    meta = {
        "status": "ok",
        "input": str(path),
        "original_name": original_name,
        "kind": kind,
        "kind_label": info.get("kind", kind),
        "route": info.get("route", kind),
        "info": info,
        "chars": len(text),
        "tokens_estimate": est_tokens(text),
        "stats": stats,
        "cleanup": sorted(cleanup),
        "notes": notes,
        "date_from_name": date_from_name,
        "date_from_file": args.source_date or info.get("pdf_created", ""),
        "duration": info.get("duration", ""),
        "duration_basis": info.get("duration_basis", ""),
        "speaker_labels": info.get("speaker_labels", stats["speakers"]),
        "fingerprint": sha256_text(text),
        "lines": len(lines),
    }
    parts = propose_parts(lines)
    parts_dir = work / "parts"
    if parts_dir.exists():
        shutil.rmtree(parts_dir)
    parts_dir.mkdir()
    for n, p in enumerate(parts, 1):
        (parts_dir / ("part-%d.md" % n)).write_text("\n".join(lines[p["start"] - 1:p["end"]]) + "\n", encoding="utf-8")
        p["number"] = n
    meta["parts"] = parts
    write_json(work / "source.meta.json", meta)
    summary = {k: meta[k] for k in ("original_name", "kind_label", "route", "chars", "tokens_estimate", "cleanup", "notes", "date_from_name", "date_from_file", "duration", "speaker_labels", "lines")}
    summary["stats"] = stats
    summary["parts"] = [{"number": p["number"], "lines": "%d-%d" % (p["start"], p["end"]), "tokens": p["tokens"], "break": p["break"], "headings": p["headings"][:12]} for p in parts]
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return 0


# ----------------------------------------------------------------------------
# assembly (R14 to R18, R21, G12, G16, G20, R33, R34)
# ----------------------------------------------------------------------------

def yaml_scalar(v) -> str:
    s = str(v)
    if s == "" or re.search(r"[:#\[\]{}&*!|>'\"%@`,]", s) or s.strip() != s or s.lower() in ("yes", "no", "true", "false", "null"):
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return s


def build_header(fields: dict) -> list:
    lines = ["---"]
    for k in HEADER_ORDER:
        v = fields.get(k)
        if k == "duration" and not v:
            continue  # duration only when the source establishes one (R15, R20, R22, R08)
        if v is None or v == "":
            v = "unknown"  # the key is carried, the value is never invented (G19, G20)
        if isinstance(v, list):
            if not v:
                v = "unknown"
                lines.append(k + ": " + v)
            else:
                lines.append(k + ": [" + ", ".join(yaml_scalar(x) for x in v) + "]")
        else:
            lines.append(k + ": " + yaml_scalar(v))
    lines.append("---")
    return lines


def friendly_title(name: str) -> str:
    """A friendly file name, never a system code (G13). Strips an existing company tag,
    the extension, and replaces characters file systems reject."""
    t = name
    t = re.sub(r"^\s*(\[[^\]]+\]\s*)+", "", t)
    t = re.sub(r"\.(pdf|docx?|vtt|srt|md|txt|html?|json)$", "", t, flags=re.I)
    t = t.replace("—", ",").replace("–", ",").replace(":", ",").replace("/", "-").replace("\\", "-").replace("__", " ").replace("_", " ")
    t = re.sub(r"\s*,\s*", ", ", t)
    t = re.sub(r"\s+", " ", t).strip(" ,.")
    return t


def file_name(identity: str, version: str, title: str, suffix: str = "") -> str:
    return "[" + identity + "][" + version + "] " + title + suffix + ".md"


def load_derived(derived_dir: Path, name: str):
    p = derived_dir / name
    if not p.exists():
        raise RuntimeError("missing derived file " + str(p))
    return read_json(p)


def _norm_quote(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    s = s.replace("\u2019", "'").replace("\u2018", "'").replace("\u201c", '"').replace("\u201d", '"')
    return re.sub(r"\s+", " ", s).strip().lower()


def takeaway_point(x) -> str:
    return x["point"] if isinstance(x, dict) else str(x)


NAME_STOP = set("""a an the and or of to in on at for from by with without under over after before between into through
during about against among per via as is are was were be been being has have had do does did not no nor so yet but if
then than that this these those it its he she they we you i his her their our your my me him them us one two three four
five six seven eight nine ten first second third fourth fifth last next later earlier early late also only even still just
both each every all any some several many most few more less much other another same such which what who whom whose when
where why how here there now today part parts tab tabs section sections page pages chapter chapters summary content key
takeaways source sources notes note actions decisions line lines paragraph paragraphs speaker speakers question questions
answer answers step steps record records entry entries item items table tables list lists figure figures opening closing
greetings introduction background overview discussion conclusion context wrap setup update updates""".split())
_BOUND = ".,;:!?()[]{}\"'«»…*`_"
_SENTENCE_END = ".!?:"


def _nraw(t: str) -> str:
    t = unicodedata.normalize("NFKC", t).replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    return re.sub(r"[‐-―−]", "-", t)


def _ntok(t: str) -> str:
    return _nraw(t).strip(_BOUND)


def names_hay(text: str) -> str:
    """The words of a text one space apart, lower case, boundary punctuation and lone punctuation marks removed,
    for the names check. The pieces of a slash joined token and the owner in a possessive are listed as well,
    apart from each other, so a term inside a/b/c or before an 's counts as present while a slash dropped from
    a name does not."""
    toks = [_ntok(t).lower() for t in str(text).split()]
    words = [t for t in toks if t and re.search(r"[0-9A-Za-zÀ-ɏ]", t)]
    pieces = []
    for t in words:
        if "/" in t:
            pieces += [x.strip(_BOUND) for x in t.split("/") if x.strip(_BOUND)]
        if t.endswith("'s") and len(t) > 2:
            pieces.append(t[:-2])
    return " " + " ".join(words) + " | " + " | ".join(pieces) + " "


def _digits_only(tok: str) -> bool:
    return re.fullmatch(r"[\d.,%$€£]+", tok) is not None and any(ch.isdigit() for ch in tok)


def _exempt(tok: str) -> bool:
    low = tok.lower()
    if low in NAME_STOP:
        return True
    if re.fullmatch(r"\d{1,3}(st|nd|rd|th)", low):
        return True
    return _digits_only(tok) and sum(ch.isdigit() for ch in tok) <= 3


def _marked(tok: str) -> bool:
    return bool(tok) and (tok[0].isupper() or any(ch.isdigit() for ch in tok))


def unsourced_names(text: str, hay: str) -> list:
    """Runs of names, numbers and terms (capitalized words and tokens carrying digits) in model written text
    that the hay does not carry word for word (G17, G19). A run ends at punctuation or after a possessive, a bare
    number stands alone, and a lone capitalized word that opens a sentence or heading passes as ordinary English
    unless it looks like a name or a term."""
    runs, cur = [], []
    at_start = True

    def close():
        nonlocal cur
        if cur:
            runs.append(cur)
        cur = []

    for raw in str(text).split():
        nraw = _nraw(raw)
        if nraw[:1] in "([{\"'":
            close()
        tok = nraw.strip(_BOUND)
        if not tok or not re.search(r"[0-9A-Za-zÀ-ɏ]", tok):
            close()
            at_start = True
            continue
        if _digits_only(tok):
            close()
            if not _exempt(tok):
                runs.append([(tok, False)])
        elif _marked(tok) and not _exempt(tok):
            cur.append((tok, at_start and tok[0].isupper()))
            if tok.lower().endswith("'s"):
                close()
        else:
            close()
        if nraw[-1:] in _BOUND:
            close()
        at_start = nraw[-1:] in _SENTENCE_END
    close()
    bad = []
    for run in runs:
        words = [t for t, _ in run]
        phrase = " ".join(w.lower() for w in words)
        cands = {phrase, re.sub(r"'s\b", "", phrase)}
        if any((" " + c.strip() + " ") in hay for c in cands if c.strip()):
            continue
        if len(run) == 1 and run[0][1] and not _looks_like_term(words[0]):
            continue
        bad.append(" ".join(words))
    return bad


def _looks_like_term(tok: str) -> bool:
    """A lone capitalized word opening a sentence is ordinary English unless it carries a digit, a slash or a
    hyphen, is written in capitals, or has a capital inside it, the marks of a name or a term."""
    core = re.sub(r"'s$", "", tok)
    if any(ch.isdigit() for ch in core) or "/" in core or "-" in core:
        return True
    letters = [ch for ch in core if ch.isalpha()]
    if len(letters) >= 2 and all(ch.isupper() for ch in letters):
        return True
    return any(ch.isupper() for ch in core[1:])


def intake_words(intake: dict) -> str:
    """The intake values the summary and takeaways may carry, the title, date, duration, people and source dates (R07)."""
    vals = [intake.get("title") or "", intake.get("date") or "", intake.get("duration") or ""] + list(intake.get("people") or [])
    sd = intake.get("source_dates") or {}
    vals += [str(v) for v in (sd.values() if isinstance(sd, dict) else sd)]
    return "\n".join(str(v) for v in vals if v)


def validate_derived(d: dict, label: str, part_text: str = "", extra_text: str = ""):
    """The shape of a derived file, and the words behind every point (R16, G17, G19). Every takeaway
    and every action carries at least one support quote, the speaker's or the author's exact words,
    and when the part text is given each quote must appear in it word for word."""
    summary = d.get("summary")
    if not isinstance(summary, list) or not (1 <= len(summary) <= 2) or not all(isinstance(x, str) and x.strip() for x in summary):
        raise RuntimeError(label + ": summary must be a list of one or two paragraphs (R16)")
    tk = d.get("takeaways")
    if not isinstance(tk, list) or not (3 <= len(tk) <= 7):
        raise RuntimeError(label + ": takeaways must be three to seven points (R16)")
    hay = _norm_quote(part_text) if part_text else ""
    for i, x in enumerate(tk, 1):
        if not isinstance(x, dict) or not str(x.get("point", "")).strip() or not isinstance(x.get("support"), list) or not x["support"]:
            raise RuntimeError(label + ": takeaway %d must be {point, support} with at least one exact quote from the text (G17, G19)" % i)
        for q in x["support"]:
            if not isinstance(q, str) or len(q.strip()) < 8:
                raise RuntimeError(label + ": takeaway %d has a support quote that is empty or too short to check" % i)
            if hay and _norm_quote(q) not in hay:
                raise RuntimeError(label + ": takeaway %d support quote is not in the text word for word: %r" % (i, q[:90]))
    for s in d.get("sections", []) or []:
        if not isinstance(s, dict) or not s.get("heading") or not isinstance(s.get("start_line"), int):
            raise RuntimeError(label + ": each section needs a heading and an integer start_line")
    for i, a in enumerate(d.get("actions_decisions", []) or [], 1):
        if not isinstance(a, dict) or not a.get("item"):
            raise RuntimeError(label + ": each action or decision needs an item")
        sup = a.get("support")
        if not isinstance(sup, list) or not sup:
            raise RuntimeError(label + ": action %d needs at least one exact support quote from the text (R18, G19)" % i)
        for q in sup:
            if hay and _norm_quote(str(q)) not in hay:
                raise RuntimeError(label + ": action %d support quote is not in the text word for word: %r" % (i, str(q)[:90]))
    if part_text:
        # Every name, number and term the model wrote must be in the text, or the intake, spelled the same way (G17, G19).
        names = names_hay(part_text + "\n" + (extra_text or ""))
        fields = [("summary paragraph %d" % i, x) for i, x in enumerate(summary, 1)]
        fields += [("takeaway %d" % i, takeaway_point(x)) for i, x in enumerate(tk, 1)]
        fields += [("heading at line %s" % x.get("start_line"), x.get("heading", "")) for x in (d.get("sections") or [])]
        fields += [("action %d" % i, a.get("item", "")) for i, a in enumerate(d.get("actions_decisions") or [], 1)]
        problems = []
        for where, text in fields:
            bad = unsourced_names(text, names)
            if bad:
                problems.append("%s: %s" % (where, ", ".join(repr(b) for b in bad[:6])))
        if problems:
            raise RuntimeError(label + ": words the source does not carry, spell them as the text does or drop them. " + "; ".join(problems[:12]) + " (G17, G19)")


def insert_sections(part_lines: list, sections: list, notes: list) -> list:
    """Insert second level headings the model chose for text that has no headings of its own (R17, R11).
    Only headings are inserted, never text changes. A heading lands at the start of a paragraph."""
    if not sections:
        return list(part_lines)
    out = list(part_lines)
    inserts = []
    for s in sorted(sections, key=lambda x: x["start_line"]):
        idx = max(1, min(len(out), s["start_line"])) - 1
        # move back to the paragraph start
        while idx > 0 and out[idx - 1] != "":
            idx -= 1
        if idx < len(out) and re.match(r"^#+\s", out[idx]):
            notes.append("section heading '%s' was not inserted, the source already has a heading there" % s["heading"])
            continue
        inserts.append((idx, "## " + clean_inline(s["heading"])))
    for idx, h in sorted(inserts, key=lambda x: x[0], reverse=True):
        out[idx:idx] = [h, ""]
    return out


def source_notes_lines(meta: dict, intake: dict, header: dict, extra: dict) -> list:
    stats = meta["stats"]
    lines = []
    lines.append("- Origin: " + meta["kind_label"] + (", " + meta["route"] if meta.get("route") else "") + extra.get("origin_extra", ""))
    lines.append("- Original file: " + meta["original_name"])
    lines.append("- Date: " + str(header.get("date") or "unknown") + " (" + extra.get("date_basis", "unknown, the source carries no date") + ")")
    lines.append("- People: " + extra.get("people_note", "unknown"))
    if meta.get("speaker_labels"):
        lines.append("- Speaker labels: kept exactly as the source writes them, " + ", ".join(meta["speaker_labels"]))
    elif stats.get("timestamps"):
        lines.append("- Speaker labels: the source does not label who said what, so no line is attributed to a speaker")
    if stats.get("timestamps"):
        lines.append("- Timestamps: %d caption start times kept inline exactly as the source gives them, caption numbers and end times are not carried" % stats["timestamps"])
    lines.append("- Tables: %d kept as tables" % stats.get("tables", 0))
    lines.append("- Links: %d kept exactly" % stats.get("links", 0))
    if stats.get("images"):
        lines.append("- Pictures and scans: %d kept beside their readable text" % stats["images"])
    lines.append("- Cleanup: " + (", ".join(meta.get("cleanup", [])) if meta.get("cleanup") else "nothing needed removing"))
    cnr = list(meta.get("notes", [])) + list(extra.get("could_not_read", []))
    lines.append("- Could not read: " + ("none" if not cnr else "; ".join(cnr)))
    lines.append("- Parts: " + extra.get("parts_note", "single file"))
    lines.append("- Source fingerprint: sha256 " + meta["fingerprint"] + " of the cleaned source text")
    for n in extra.get("more", []):
        lines.append("- " + n)
    return lines


def resolve_header(meta: dict, intake: dict, derived: dict, title: str):
    date = intake.get("date") or meta.get("date_from_name") or meta.get("date_from_file") or ""
    if intake.get("date"):
        basis = "from the intake"
    elif meta.get("date_from_name"):
        basis = "from the file name"
    elif meta.get("date_from_file"):
        basis = "from the file's own metadata"
    else:
        basis = "unknown, the source carries no date"
    people = list(intake.get("people") or [])
    for s in meta.get("speaker_labels") or []:
        if s not in people:
            people.append(s)
    if intake.get("people") and meta.get("speaker_labels"):
        people_note = "from the intake, with the speaker labels the source carries"
    elif intake.get("people"):
        people_note = "from the intake, the source itself does not name who was there"
    elif meta.get("speaker_labels"):
        people_note = "the speakers the source labels"
    else:
        people_note = "unknown, neither the source nor the intake names who was there"
    if derived.get("people_note"):
        people_note = derived["people_note"]
    header = {
        "title": title,
        "type": intake.get("type") or derived.get("type") or ("transcript" if meta["stats"].get("timestamps") else "document"),
        "source": meta["original_name"],
        "date": date or "unknown",
        "duration": intake.get("duration") or meta.get("duration") or "",
        "people": people if people else "unknown",
        "optimized_for": intake.get("destination") or "unknown",
        "optimized_at": _dt.date.today().isoformat(),
    }
    return header, {"date_basis": basis, "people_note": people_note}


def assemble_single(work: Path, intake: dict, derived_dir: Path, out: Path, version: str, identity: str, title: str):
    meta = read_json(work / "source.meta.json")
    if meta.get("status") != "ok":
        raise RuntimeError("the source was not extracted: " + str(meta.get("error")))
    parts = meta["parts"]
    total_parts = len(parts)
    files = []
    nav_sections = []
    first_header = None
    part_firsts = []
    first_people_note = None
    for p in parts:
        n = p["number"]
        label = "part-%d.json" % n if total_parts > 1 else None
        d = load_derived(derived_dir, label) if label else (load_derived(derived_dir, "part-1.json") if (derived_dir / "part-1.json").exists() else load_derived(derived_dir, "derived.json"))
        part_text = (work / "parts" / ("part-%d.md" % n)).read_text(encoding="utf-8")
        validate_derived(d, "part %d" % n, part_text, intake_words(intake))
        part_firsts.append((n, str(d["summary"][0]).strip()))
        if first_people_note is None:
            first_people_note = d.get("people_note") or ""
        part_lines = part_text.splitlines()
        notes = []
        body = insert_sections(part_lines, d.get("sections") or [], notes)
        header, extra = resolve_header(meta, intake, d, title + (", Part %d of %d" % (n, total_parts) if total_parts > 1 else ""))
        if first_header is None:
            first_header = header
        extra["could_not_read"] = list(d.get("could_not_read") or [])
        extra["parts_note"] = ("Part %d of %d, the navigation page is %s" % (n, total_parts, file_name(identity, version, title, ", Navigation"))) if total_parts > 1 else "single file"
        extra["more"] = ["Split: " + p["break"]] if total_parts > 1 else []
        if d.get("notes"):
            extra["more"].append("Note: " + clean_inline(d["notes"]))
        lines = []
        lines += build_header(header)
        lines += ["", "# " + header["title"], "", "## Summary", ""]
        for para in d["summary"]:
            lines += [clean_inline(para), ""]
        lines += ["## Key Takeaways", ""]
        for t in d["takeaways"]:
            lines.append("- " + clean_inline(takeaway_point(t)))
        lines += ["", "## Content", ""]
        lines += body
        acts = d.get("actions_decisions") or []
        if acts:
            lines += ["", "## Actions and Decisions", ""]
            for a in acts:
                item = clean_inline(a["item"])
                tail = []
                if a.get("owner"):
                    tail.append("owner " + clean_inline(a["owner"]))
                if a.get("due"):
                    tail.append("due " + clean_inline(a["due"]))
                lines.append("- " + item + (" (" + ", ".join(tail) + ")" if tail else ""))
        lines += ["", "## Source Notes", ""]
        lines += source_notes_lines(meta, intake, header, extra)
        text = "\n".join(lines).rstrip() + "\n"
        name = file_name(identity, version, title, ", Part %d of %d" % (n, total_parts) if total_parts > 1 else "")
        (out / name).write_text(text, encoding="utf-8")
        files.append({"name": name, "part": n, "tokens_estimate": est_tokens(text), "sha256": sha256_text(text), "headings": _headings_in(body, 0, len(body))})
        nav_sections.append((n, name, est_tokens(text), _headings_in(body, 0, len(body))))
    if total_parts > 1:
        # The navigation summary is built here from each part's first summary paragraph, in order, so the
        # navigation page claims nothing the parts do not (G16, G19), in one or two paragraphs (R16).
        # One paragraph for up to two parts, two paragraphs past that, so the page keeps the spec's one or two (R16).
        pieces = ["Part %d of %d. %s" % (n, total_parts, first) for n, first in part_firsts]
        if len(pieces) <= 2:
            nav_paras = [" ".join(pieces)]
        else:
            half = (len(pieces) + 1) // 2
            nav_paras = [" ".join(pieces[:half]), " ".join(pieces[half:])]
        nav = {"summary": nav_paras, "people_note": first_people_note}
        header, extra = resolve_header(meta, intake, nav, title + ", Navigation")
        extra["parts_note"] = "navigation page for %d parts, its summary built from each part's first summary paragraph" % total_parts
        lines = build_header(header) + ["", "# " + header["title"], "", "## Summary", ""]
        for para in nav["summary"]:
            lines += [clean_inline(para), ""]
        lines += ["## Parts", ""]
        for n, name, tokens, heads in nav_sections:
            desc = ", ".join(h for h in heads if not h.startswith("Content"))
            lines.append("- " + name + ", about " + "{:,}".format(tokens) + " tokens. Contains " + (desc if desc else "the text in order") + ".")
        lines += ["", "## Source Notes", ""] + source_notes_lines(meta, intake, header, extra)
        text = "\n".join(lines).rstrip() + "\n"
        name = file_name(identity, version, title, ", Navigation")
        (out / name).write_text(text, encoding="utf-8")
        files.append({"name": name, "part": 0, "tokens_estimate": est_tokens(text), "sha256": sha256_text(text), "headings": []})
    return files, meta


def assemble_combined(works: list, intake: dict, derived_dir: Path, out: Path, version: str, identity: str, title: str):
    """Combine related files on the same topic, only when asked (G15, R24). Every section
    keeps its source, exact repeats appear once, disagreements keep both claims with dates."""
    d = load_derived(derived_dir, "combined.json")
    validate_derived(d, "combined", "\n".join((w / "source.md").read_text(encoding="utf-8") for w in works), intake_words(intake))
    metas = [read_json(w / "source.meta.json") for w in works]
    for m in metas:
        if m.get("status") != "ok":
            raise RuntimeError("a source was not extracted: " + str(m.get("error")))
    labels = [chr(ord("A") + i) for i in range(len(works))]
    src_lines = [(w / "source.md").read_text(encoding="utf-8").splitlines() for w in works]
    src_dates = []
    for m in metas:
        src_dates.append((intake.get("source_dates") or {}).get(m["original_name"]) or m.get("date_from_name") or m.get("date_from_file") or "unknown")
    seen = {}
    repeats = []
    folded = []
    body = ["## Content", ""]
    for s in d.get("sections") or []:
        si = labels.index(s["source"]) if s.get("source") in labels else int(s.get("source_index", 0))
        a = max(1, s["start_line"]) - 1
        b = min(len(src_lines[si]), s.get("end_line") or len(src_lines[si]))
        sec = []
        kept_any = False
        para = []
        chunk = src_lines[si][a:b] + [""]
        for l in chunk:
            if l == "":
                if para:
                    text = "\n".join(para)
                    key = norm_para(text)
                    if key in seen and not re.match(r"^#+\s", para[0]):
                        repeats.append("A passage beginning '%s' appears in Source %s and Source %s and is kept once, under %s." % (text[:60], seen[key][0], labels[si], seen[key][1]))
                    else:
                        seen.setdefault(key, (labels[si], s["heading"]))
                        sec.extend(para)
                        sec.append("")
                        if not re.match(r"^#+\s", para[0]):
                            kept_any = True
                    para = []
            else:
                para.append(l)
        if not kept_any:
            folded.append("The section '%s' from Source %s held only passages already kept elsewhere, so it was folded into the earlier copy." % (clean_inline(s["heading"]), labels[si]))
            continue
        body.append("## " + clean_inline(s["heading"]))
        body.append("")
        body.append("Source " + labels[si] + ", " + metas[si]["original_name"] + ", " + src_dates[si] + ".")
        body.append("")
        body.extend(sec)
    conflicts = d.get("conflicts") or []
    if conflicts:
        body += ["## Conflicts between sources", ""]
        for c in conflicts:
            body.append("- About " + clean_inline(c.get("about", "")) + ".")
            for cl in c.get("claims", []):
                body.append("  - Source " + str(cl.get("source", "")) + " (" + str(cl.get("date", "unknown")) + "): " + clean_inline(cl.get("text", "")))
            body.append("  - Both are kept as written. No winner is chosen.")
        body.append("")
    header = {
        "title": title,
        "type": intake.get("type") or d.get("type") or "combined document",
        "source": "; ".join(m["original_name"] for m in metas),
        "date": ", ".join(src_dates),
        "duration": "",
        "people": intake.get("people") or sorted({sp for m in metas for sp in (m.get("speaker_labels") or [])}) or "unknown",
        "optimized_for": intake.get("destination") or "unknown",
        "optimized_at": _dt.date.today().isoformat(),
    }
    lines = build_header(header) + ["", "# " + title, "", "## Summary", ""]
    for para in d["summary"]:
        lines += [clean_inline(para), ""]
    lines += ["## Key Takeaways", ""]
    for t in d["takeaways"]:
        lines.append("- " + clean_inline(takeaway_point(t)))
    lines += [""] + body
    lines += ["## Source Notes", ""]
    for i, m in enumerate(metas):
        lines.append("- Source " + labels[i] + ": " + m["original_name"] + ", " + m["kind_label"] + ", dated " + src_dates[i] + ", fingerprint sha256 " + m["fingerprint"])
    lines.append("- Combined because the request asked for it, the sources are on the same topic")
    lines.append("- Repeated passages: " + ("none" if not repeats else " ".join(repeats + folded)))
    lines.append("- Conflicts: " + ("none found" if not conflicts else "%d flagged above, both claims kept with their dates" % len(conflicts)))
    lines.append("- People: " + (d.get("people_note") or "as the sources and the intake give them"))
    lines.append("- Could not read: " + ("none" if not any(m.get("notes") for m in metas) else "; ".join(n for m in metas for n in m.get("notes", []))))
    lines.append("- Parts: single file")
    text = "\n".join(lines).rstrip() + "\n"
    name = file_name(identity, version, title)
    (out / name).write_text(text, encoding="utf-8")
    return [{"name": name, "part": 1, "tokens_estimate": est_tokens(text), "sha256": sha256_text(text), "headings": _headings_in(body, 0, len(body))}], metas[0]


def identity_and_title(intake: dict, meta: dict):
    identity = intake.get("company_file") or ""
    m = re.match(r"^\s*\[([^\]]+)\]", meta.get("original_name", ""))
    if not identity and m:
        identity = m.group(1)
    if not identity:
        raise RuntimeError("the company or department file identity is unknown, ask for it in the intake (G13, R31)")
    identity = identity.strip("[] ")
    title = intake.get("title") or friendly_title(meta.get("original_name", "")) or "Untitled"
    return identity, title


def cmd_assemble(args):
    works = [Path(w) for w in args.work]
    intake = read_json(Path(args.intake))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    version = args.version or "V1.0"
    meta0 = read_json(works[0] / "source.meta.json")
    identity, title = identity_and_title(intake, meta0)
    if args.combine or len(works) > 1:
        files, meta = assemble_combined(works, intake, Path(args.derived), out, version, identity, title)
    else:
        files, meta = assemble_single(works[0], intake, Path(args.derived), out, version, identity, title)
    manifest = {"identity": identity, "title": title, "version": version, "files": files,
                "parts": len([f for f in files if f["part"] > 0]), "fingerprint": meta["fingerprint"],
                "could_not_read": meta.get("notes", []), "original_name": meta["original_name"],
                "destination": intake.get("destination", ""), "works": [str(w) for w in works]}
    write_json(out / "manifest.json", manifest)
    print(json.dumps({"files": [f["name"] for f in files], "parts": manifest["parts"], "version": version}, ensure_ascii=False, indent=1))
    return 0


# ----------------------------------------------------------------------------
# saving to Drive by the company file rules (R13, R31, R32, G12, G14, G23)
# ----------------------------------------------------------------------------

def drive_client(auth: str, impersonate: str):
    if not auth or auth == "none":
        return None
    if auth.startswith("sa:"):
        from google.oauth2 import service_account  # type: ignore
        from googleapiclient.discovery import build  # type: ignore
        creds = service_account.Credentials.from_service_account_file(auth[3:], scopes=["https://www.googleapis.com/auth/drive"])
        if impersonate:
            creds = creds.with_subject(impersonate)
        return build("drive", "v3", credentials=creds, cache_discovery=False)
    if auth.startswith("token:"):
        from google.oauth2.credentials import Credentials  # type: ignore
        from googleapiclient.discovery import build  # type: ignore
        token = os.environ.get(auth[6:], "")
        if not token:
            raise RuntimeError("the token environment variable is empty")
        return build("drive", "v3", credentials=Credentials(token=token), cache_discovery=False)
    raise RuntimeError("unknown auth route " + auth)


def brain_tag(identity: str) -> str:
    return identity.split("-")[0].strip().upper()


def find_folder(drive, tag: str, which_folder: str):
    """Find the brain's outputs or archive folder by name, never create one (G23)."""
    q = "mimeType='application/vnd.google-apps.folder' and trashed=false and name contains '[%s-BB]'" % tag
    res = drive.files().list(q=q, fields="files(id,name,driveId,parents)", supportsAllDrives=True, includeItemsFromAllDrives=True, pageSize=100, corpora="allDrives").execute()
    for f in res.get("files", []):
        n = f["name"].lower()
        if which_folder == "outputs" and n.endswith("claude outputs [%s-bb]" % tag.lower()):
            return f
        if which_folder == "archives" and n.endswith("archives [%s-bb]" % tag.lower()):
            return f
    return None


def private_ancestor(drive, file_id: str):
    """If the source sits under a Private folder of its brain, outputs stay in that Private folder."""
    seen = 0
    cur = file_id
    while cur and seen < 12:
        f = drive.files().get(fileId=cur, fields="id,name,parents", supportsAllDrives=True).execute()
        if f["name"].lower().startswith("private [") or f["name"].lower().startswith("private["):
            return f
        parents = f.get("parents") or []
        cur = parents[0] if parents else None
        seen += 1
    return None


VERSION_RE = r"\[V(\d+)\.(\d+)\]"


def list_prior(drive, folder_id: str, identity: str, title: str):
    q = "'%s' in parents and trashed=false and name contains '%s'" % (folder_id, title.replace("'", "\\'"))
    res = drive.files().list(q=q, fields="files(id,name,md5Checksum,modifiedTime)", supportsAllDrives=True, includeItemsFromAllDrives=True, pageSize=200).execute()
    pat = re.compile(r"^\[" + re.escape(identity) + r"\]" + VERSION_RE + r" " + re.escape(title) + r"(, Part \d+ of \d+|, Navigation)?\.md$")
    out = {}
    for f in res.get("files", []):
        m = pat.match(f["name"])
        if m:
            ver = (int(m.group(1)), int(m.group(2)))
            out.setdefault(ver, []).append(f)
    return out


def download_text(drive, file_id: str) -> str:
    data = drive.files().get_media(fileId=file_id, supportsAllDrives=True).execute()
    return data.decode("utf-8", errors="replace") if isinstance(data, bytes) else str(data)


def content_paragraphs(text: str) -> list:
    m = re.search(r"^## Content\s*$", text, re.M)
    start = m.end() if m else 0
    end = len(text)
    for marker in ("\n## Source Notes", "\n## Actions and Decisions", "\n## Conflicts between sources"):
        i = text.find(marker, start)
        if i != -1:
            end = min(end, i)
    body = text[start:end]
    return [norm_para(p) for p in re.split(r"\n\s*\n", body) if p.strip() and not re.match(r"^#+\s", p.strip())]


def bump(ver, small: bool) -> str:
    major, minor = ver
    return "V%d.%d" % ((major, minor + 1) if small else (major + 1, 0))


def plan_version(drive, folder, manifest_like: dict, new_paras: list, intake: dict):
    """Decide the version against what already sits in the destination (R31, G14)."""
    priors = list_prior(drive, folder["id"], manifest_like["identity"], manifest_like["title"])
    if not priors:
        return {"version": "V1.0", "state": "new", "prior": None}
    top = max(priors)
    files = priors[top]
    first = sorted(files, key=lambda f: f["name"])
    texts = [download_text(drive, f["id"]) for f in first]
    fp = ""
    for t in texts:
        m = re.search(r"Source fingerprint: sha256 ([0-9a-f]{64})", t)
        if m:
            fp = m.group(1)
            break
    prior_label = "V%d.%d" % top
    if fp and fp == manifest_like["fingerprint"]:
        return {"version": prior_label, "state": "unchanged", "prior": {"version": prior_label, "files": files}}
    prev_paras = []
    for t in texts:
        if ", Navigation.md" in t[:0]:
            continue
        prev_paras.extend(content_paragraphs(t))
    ratio = difflib.SequenceMatcher(None, prev_paras, new_paras).ratio() if prev_paras and new_paras else 0.0
    change = round(1.0 - ratio, 3)
    size = intake.get("change_size") or ("small" if change < SMALL_CHANGE_LIMIT else "large")
    return {"version": bump(top, size == "small"), "state": "revised", "change_fraction": change, "change_size": size,
            "prior": {"version": prior_label, "files": files}}


def upload_file(drive, folder_id: str, path: Path):
    from googleapiclient.http import MediaInMemoryUpload  # type: ignore
    data = path.read_bytes()
    media = MediaInMemoryUpload(data, mimetype="text/markdown", resumable=False)
    f = drive.files().create(body={"name": path.name, "parents": [folder_id]}, media_body=media, supportsAllDrives=True,
                             fields="id,name,md5Checksum,webViewLink,parents").execute()
    back = drive.files().get_media(fileId=f["id"], supportsAllDrives=True).execute()
    ok = sha256_bytes(back) == sha256_bytes(data)
    return {"id": f["id"], "name": f["name"], "link": f.get("webViewLink", ""), "verified": ok, "sha256": sha256_bytes(data)}


def move_file(drive, file_id: str, to_folder: str):
    f = drive.files().get(fileId=file_id, fields="id,name,parents", supportsAllDrives=True).execute()
    prev = ",".join(f.get("parents") or [])
    moved = drive.files().update(fileId=file_id, addParents=to_folder, removeParents=prev, supportsAllDrives=True, fields="id,name,parents").execute()
    return moved


def completion_report(manifest: dict, save: dict) -> str:
    """The completion message (G12): file name, where it saved, how many parts, anything unreadable."""
    lines = ["Optimized " + manifest["original_name"] + "."]
    if save.get("state") == "unchanged":
        lines.append("The source is unchanged since " + save["prior"]["version"] + ", which already sits in " + save.get("folder_name", "the destination") + ". Nothing new was saved.")
    else:
        where = save.get("folder_name") or "the working folder (Drive save pending, " + save.get("pending_reason", "no Drive route in this session") + ")"
        lines.append("Saved %d file%s in %s." % (len(manifest["files"]), "" if len(manifest["files"]) == 1 else "s", where))
        for f in manifest["files"]:
            link = ""
            for u in save.get("uploaded", []):
                if u["name"] == f["name"]:
                    link = " " + u["link"] if u.get("link") else ""
            lines.append("  " + f["name"] + " (about {:,} tokens)".format(f["tokens_estimate"]) + link)
    parts = manifest["parts"]
    lines.append("Parts: " + ("one file, no split needed" if parts <= 1 else "%d numbered parts plus a navigation page, split past about 50,000 tokens" % parts))
    if save.get("state") == "revised":
        lines.append("Version: " + manifest["version"] + " replaces " + save["prior"]["version"] + " (" + save.get("change_size", "") + " change, about %d percent of the text changed)" % int(round(100 * save.get("change_fraction", 0))) + ". The " + save["prior"]["version"] + " file%s moved to %s, nothing was deleted." % ("s" if len(save["prior"]["files"]) > 1 else "", save.get("archive_name", "the archive")))
        lines.append("Copies to refresh: any Claude Project or Custom GPT that holds the " + save["prior"]["version"] + " upload needs the " + manifest["version"] + " file" + ("s" if parts > 1 else "") + ". This tool does not reach those uploads.")
    elif save.get("state") == "new":
        lines.append("Version: " + manifest["version"] + ", first optimized version.")
    cnr = manifest.get("could_not_read") or []
    lines.append("Could not read: " + ("none" if not cnr else "; ".join(cnr)))
    return "\n".join(lines)


def cmd_save(args):
    out = Path(args.out)
    manifest = read_json(out / "manifest.json")
    intake = read_json(Path(args.intake))
    drive = drive_client(args.auth, args.impersonate)
    save = {"state": "new", "uploaded": []}
    if drive is None:
        save["state"] = "pending"
        save["pending_reason"] = "no Drive route in this session"
        write_json(out / "save-report.json", save)
        text = completion_report(manifest, save)
        (out / "completion-report.md").write_text(text + "\n", encoding="utf-8")
        print(text)
        return 0
    tag = brain_tag(manifest["identity"])
    folder = None
    if args.source_drive_id:
        folder = private_ancestor(drive, args.source_drive_id)
    if folder is None:
        folder = find_folder(drive, tag, "outputs")
    if folder is None:
        raise RuntimeError("no Claude outputs folder was found for the %s brain, and this tool never creates folders (G23)" % tag)
    archive = find_folder(drive, tag, "archives")
    new_paras = []
    for f in manifest["files"]:
        if f["part"] > 0:
            new_paras.extend(content_paragraphs((out / f["name"]).read_text(encoding="utf-8")))
    plan = plan_version(drive, folder, manifest, new_paras, intake)
    save.update(plan)
    save["folder_name"] = folder["name"]
    save["folder_id"] = folder["id"]
    if plan["state"] == "unchanged":
        write_json(out / "save-report.json", save)
        text = completion_report(manifest, save)
        (out / "completion-report.md").write_text(text + "\n", encoding="utf-8")
        print(text)
        return 0
    if plan["version"] != manifest["version"]:
        raise RuntimeError("the destination already holds %s, assemble again with --version %s" % (plan["prior"]["version"], plan["version"]))
    if args.dry_run:
        save["dry_run"] = True
        write_json(out / "save-report.json", save)
        print(json.dumps(save, indent=1))
        return 0
    if plan["state"] == "revised":
        if archive is None:
            raise RuntimeError("no Archives folder was found for the %s brain, the superseded version cannot be archived and nothing is deleted (R31, G23)" % tag)
        save["archive_name"] = archive["name"]
        save["archived"] = []
        for f in plan["prior"]["files"]:
            moved = move_file(drive, f["id"], archive["id"])
            save["archived"].append({"id": moved["id"], "name": moved["name"], "parents": moved.get("parents")})
    for f in manifest["files"]:
        save["uploaded"].append(upload_file(drive, folder["id"], out / f["name"]))
    save["all_verified"] = all(u["verified"] for u in save["uploaded"])
    write_json(out / "save-report.json", save)
    text = completion_report(manifest, save)
    (out / "completion-report.md").write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if save["all_verified"] else 3


def cmd_finish(args):
    """Version check first, then assemble with the right version, then save and report."""
    works = [Path(w) for w in args.work]
    intake = read_json(Path(args.intake))
    meta0 = read_json(works[0] / "source.meta.json")
    identity, title = identity_and_title(intake, meta0)
    version = args.version or "V1.0"
    drive = drive_client(args.auth, args.impersonate)
    if drive is not None and not args.version:
        tag = brain_tag(identity)
        folder = None
        if args.source_drive_id:
            folder = private_ancestor(drive, args.source_drive_id)
        if folder is None:
            folder = find_folder(drive, tag, "outputs")
        if folder is None:
            raise RuntimeError("no Claude outputs folder was found for the %s brain, and this tool never creates folders (G23)" % tag)
        lines = (works[0] / "source.md").read_text(encoding="utf-8")
        probe = {"identity": identity, "title": title, "fingerprint": meta0["fingerprint"]}
        plan = plan_version(drive, folder, probe, [norm_para(p) for p in re.split(r"\n\s*\n", lines) if p.strip() and not re.match(r"^#+\s", p.strip())], intake)
        version = plan["version"]
    args.version = version
    rc = cmd_assemble(args)
    if rc != 0:
        return rc
    return cmd_save(args)


def cmd_validate(args):
    """Check the shape, the quotes and the words of a derived JSON file before assembly (R16, R17, G17, G19).
    The run folder's intake.json supplies the title, date and people the summary may carry (R07)."""
    derived_path = Path(args.derived)
    d = read_json(derived_path)
    run_dir = derived_path.parent.parent
    intake_path = Path(args.intake) if args.intake else run_dir / "intake.json"
    intake = read_json(intake_path) if intake_path.exists() else {}
    part_text = "\n".join(Path(pp).read_text(encoding="utf-8") for pp in (args.part or []))
    validate_derived(d, derived_path.name, part_text, intake_words(intake))
    if args.combined:
        for s in d.get("sections") or []:
            if s.get("source") not in [chr(ord("A") + i) for i in range(26)] or not isinstance(s.get("end_line"), int):
                raise RuntimeError("each combined section needs source (A, B, ...) and an integer end_line")
        for c in d.get("conflicts") or []:
            if not c.get("about") or len(c.get("claims") or []) < 2:
                raise RuntimeError("each conflict needs about and at least two claims")
    print("OK " + str(args.derived))
    return 0


def cmd_report(args):
    out = Path(args.out)
    manifest = read_json(out / "manifest.json")
    save = read_json(out / "save-report.json") if (out / "save-report.json").exists() else {"state": "pending", "pending_reason": "not saved yet"}
    print(completion_report(manifest, save))
    return 0


# ----------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(description="File to Knowledge Base Optimizer engine")
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("extract")
    e.add_argument("--input", required=True)
    e.add_argument("--work", required=True)
    e.add_argument("--kind", default="auto")
    e.add_argument("--original-name", default="")
    e.add_argument("--source-date", default="")
    for name in ("assemble", "finish"):
        a = sub.add_parser(name)
        a.add_argument("--work", nargs="+", required=True)
        a.add_argument("--intake", required=True)
        a.add_argument("--derived", required=True)
        a.add_argument("--out", required=True)
        a.add_argument("--version", default="")
        a.add_argument("--combine", action="store_true")
        a.add_argument("--auth", default="none")
        a.add_argument("--impersonate", default="")
        a.add_argument("--source-drive-id", default="")
        a.add_argument("--dry-run", action="store_true")
    s = sub.add_parser("save")
    s.add_argument("--out", required=True)
    s.add_argument("--intake", required=True)
    s.add_argument("--auth", default="none")
    s.add_argument("--impersonate", default="")
    s.add_argument("--source-drive-id", default="")
    s.add_argument("--dry-run", action="store_true")
    r = sub.add_parser("report")
    r.add_argument("--out", required=True)
    v = sub.add_parser("validate")
    v.add_argument("--derived", required=True)
    v.add_argument("--part", action="append", default=[], help="the part text the quotes must appear in, repeat for several sources")
    v.add_argument("--combined", action="store_true")
    v.add_argument("--intake", default="", help="the intake file, found in the run folder when not given")
    args = ap.parse_args(argv)
    try:
        return {"extract": cmd_extract, "assemble": cmd_assemble, "save": cmd_save, "finish": cmd_finish, "report": cmd_report, "validate": cmd_validate}[args.cmd](args)
    except Exception as exc:
        print("STOPPED: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
