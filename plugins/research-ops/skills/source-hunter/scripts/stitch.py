"""Stitch OCR lines from successive frames into continuous screens.

A scrolling screen shows overlapping windows of the same text. Each new frame
is aligned against the end of the current screen, and only the lines past the
overlap are added, so the scroll comes back as one text with no repeats.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from difflib import SequenceMatcher

SIMILARITY = 0.8


@dataclass
class Line:
    text: str
    conf: float = 0.0
    frame: int = 0
    time: float = 0.0


@dataclass
class Screen:
    lines: list[Line]
    frames: list[int] = field(default_factory=list)
    first_time: float = 0.0
    last_time: float = 0.0

    def to_dict(self) -> dict:
        return {
            "first_time": self.first_time,
            "last_time": self.last_time,
            "frames": self.frames,
            "lines": [asdict(line) for line in self.lines],
        }


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^0-9a-z]+", " ", text.lower())).strip()


def similar(a: str, b: str, threshold: float = SIMILARITY) -> bool:
    na, nb = normalize(a), normalize(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    return SequenceMatcher(None, na, nb, autojunk=False).ratio() >= threshold


def find_overlap(doc: list[Line], new: list[Line], max_head_skip: int = 2, max_tail_skip: int = 2):
    """Find where new continues doc.

    Returns (i, j, t, tail) where doc[i:i+t] matches new[j:j+t], or None.
    An alignment counts when the matched run reaches the end of doc (allowing
    max_tail_skip unmatched lines, which are usually a cut off line at the
    bottom of the previous frame) or when new is used up, meaning new is a
    window already inside doc.
    """
    best = None
    for j in range(min(max_head_skip, len(new) - 1) + 1):
        for i in range(len(doc)):
            t = 0
            while i + t < len(doc) and j + t < len(new) and similar(doc[i + t].text, new[j + t].text):
                t += 1
            if t == 0:
                continue
            tail = len(doc) - (i + t)
            consumed = j + t == len(new)
            if tail > max_tail_skip and not consumed:
                continue
            min_overlap = min(2, len(new) - j, len(doc))
            if t < min_overlap:
                continue
            key = (t, -j, -tail)
            if best is None or key > best[0]:
                best = (key, (i, j, t, tail))
    return None if best is None else best[1]


def _merge(screen: Screen, new: list[Line]) -> bool:
    doc = screen.lines
    found = find_overlap(doc, new)
    if found is None:
        return False
    i, j, t, tail = found
    for k in range(t):
        old, fresh = doc[i + k], new[j + k]
        if fresh.conf > old.conf:
            doc[i + k] = Line(fresh.text, fresh.conf, old.frame, old.time)
    if j + t < len(new):
        # The doc tail past the overlap was a partial line in the earlier frame.
        screen.lines = doc[: i + t] + new[j + t :]
    if i == 0 and j > 0:
        # Scrolled above the start of what we had, keep the lines revealed on top.
        screen.lines = new[:j] + screen.lines
    return True


def _contained(screen: Screen, new: list[Line]) -> bool:
    found = find_overlap(screen.lines, new)
    return found is not None and found[1] + found[2] == len(new)


def _drop_consecutive_repeats(lines: list[Line]) -> list[Line]:
    out: list[Line] = []
    for line in lines:
        if out and similar(out[-1].text, line.text, 0.95):
            if line.conf > out[-1].conf:
                out[-1] = Line(line.text, line.conf, out[-1].frame, out[-1].time)
            continue
        out.append(line)
    return out


def stitch(frames: list[tuple[int, float, float, list[Line]]]) -> list[Screen]:
    """Turn (frame index, first seen, last seen, lines) in time order into continuous screens."""
    screens: list[Screen] = []
    for index, time, until, lines in frames:
        lines = [Line(l.text, l.conf, index, time) for l in lines if normalize(l.text)]
        if not lines:
            continue
        if screens and _merge(screens[-1], lines):
            current = screens[-1]
        else:
            earlier = next((s for s in screens[:-1] if _contained(s, lines)), None)
            if earlier is not None:
                earlier.frames.append(index)
                earlier.last_time = max(earlier.last_time, until)
                continue
            current = Screen(lines=list(lines), first_time=time, last_time=time)
            screens.append(current)
        current.frames.append(index)
        current.last_time = until
    for screen in screens:
        screen.lines = _drop_consecutive_repeats(screen.lines)
    return screens
