"""Stitch OCR lines from successive frames into continuous screens.

A scrolling screen shows overlapping windows of the same text. Each new frame
is aligned against the end of the current screen, and only the lines past the
overlap are added, so the scroll comes back as one text with no repeats.

A chat message that grows as it streams is joined the same way. Its frames
are the current screen plus added lines, with a small upward shift of the
pane, a cut off top or bottom line, and a short spinner or status line that
reads differently in every frame. That changing line stays one line and keeps
its other readings as variants.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass, field
from difflib import SequenceMatcher

SIMILARITY = 0.8
# A spinner glyph or a status word reads this short or shorter once normalized.
VOLATILE_CHARS = 20
# How closely a changed line must read like its earlier reading, digits ignored.
RESEMBLANCE = 0.6
# A prefix shorter than this is too weak to call a line still being typed.
MIN_PREFIX_CHARS = 10
GROW_MIN_ANCHORS = 3
GROW_MAX_CHANGED = 3


@dataclass
class Line:
    text: str
    conf: float = 0.0
    frame: int = 0
    time: float = 0.0
    variants: list[str] = field(default_factory=list)

    def add_variant(self, text: str) -> None:
        """Keep another reading of this line when it differs after normalizing."""
        seen = {normalize(self.text), *(normalize(v) for v in self.variants)}
        if normalize(text) not in seen:
            self.variants.append(text)


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
    decomposed = unicodedata.normalize("NFKD", text).casefold()
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return re.sub(r"[\W_]+", " ", stripped).strip()


def similar(a: str, b: str, threshold: float = SIMILARITY) -> bool:
    return _similar_normalized(normalize(a), normalize(b), threshold)


def _similar_normalized(na: str, nb: str, threshold: float = SIMILARITY) -> bool:
    if not na or not nb:
        return False
    if na == nb:
        return True
    # Numbered lines (Week 1, Week 2) score as near matches but are different lines.
    if re.findall(r"\b\d+\b", na) != re.findall(r"\b\d+\b", nb):
        return False
    matcher = SequenceMatcher(None, na, nb, autojunk=False)
    # The quick ratios are upper bounds on ratio, so they only skip sure misses.
    return (
        matcher.real_quick_ratio() >= threshold
        and matcher.quick_ratio() >= threshold
        and matcher.ratio() >= threshold
    )


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


def _resembles_any(line: Line, others: list[Line]) -> bool:
    """True when line reads as the same line as one of others.

    Kept strict on purpose. When in doubt the stitcher starts a new screen, which
    can repeat a line but never loses one.
    """
    if not normalize(line.text):
        return True
    return any(similar(line.text, other.text) for other in others)


def _merge(screen: Screen, new: list[Line]) -> bool:
    doc = screen.lines
    found = find_overlap(doc, new)
    if found is None:
        return False
    i, j, t, tail = found
    if i > 0 and j > 0:
        # The lines before the match in the new frame would be thrown away. That is a
        # different slide sharing a header or footer, not a scroll.
        return False
    if j + t < len(new) and tail > 0 and not all(_resembles_any(l, new) for l in doc[i + t :]):
        # Cutting the doc tail would lose real lines that never show up again.
        return False
    for k in range(t):
        old, fresh = doc[i + k], new[j + k]
        if fresh.conf > old.conf:
            kept = Line(fresh.text, fresh.conf, old.frame, old.time, list(old.variants))
            kept.add_variant(old.text)
            doc[i + k] = kept
        else:
            old.add_variant(fresh.text)
    if j + t < len(new):
        # The doc tail past the overlap was a partial line in the earlier frame.
        for line in doc[i + t :]:
            later = next((l for l in new[j + t :] if similar(l.text, line.text)), None)
            if later is not None:
                for reading in [line.text, *line.variants]:
                    later.add_variant(reading)
        screen.lines = doc[: i + t] + new[j + t :]
    if i == 0 and j > 0:
        # Scrolled above the start of what we had, keep the lines revealed on top.
        screen.lines = new[:j] + screen.lines
    return True


def _contained(screen: Screen, new: list[Line]) -> bool:
    found = find_overlap(screen.lines, new)
    if found is None:
        return False
    i, j, t, tail = found
    # The whole new frame must sit inside the screen from its first line, so a
    # shared header or footer alone never swallows a different slide.
    return j == 0 and t == len(new)


def _combine(old: Line, fresh: Line) -> Line:
    """One line holding both readings, the more confident one as its text."""
    if fresh.conf > old.conf:
        kept = Line(fresh.text, fresh.conf, old.frame, old.time, list(old.variants))
        kept.add_variant(old.text)
    else:
        kept = Line(old.text, old.conf, old.frame, old.time, list(old.variants))
        kept.add_variant(fresh.text)
    for variant in fresh.variants:
        kept.add_variant(variant)
    return kept


def _align(doc: list[Line], new: list[Line]) -> list[tuple[int, int]]:
    """Longest in-order run of similar lines between doc and new, as index pairs."""
    n, m = len(doc), len(new)
    doc_norm = [normalize(d.text) for d in doc]
    new_norm = [normalize(x.text) for x in new]
    match = [[_similar_normalized(d, x) for x in new_norm] for d in doc_norm]
    longest = [[0] * (m + 1) for _ in range(n + 1)]
    for a in range(n - 1, -1, -1):
        for b in range(m - 1, -1, -1):
            if match[a][b]:
                longest[a][b] = longest[a + 1][b + 1] + 1
            else:
                longest[a][b] = max(longest[a + 1][b], longest[a][b + 1])
    pairs, a, b = [], 0, 0
    while a < n and b < m:
        if match[a][b]:
            pairs.append((a, b))
            a, b = a + 1, b + 1
        elif longest[a + 1][b] >= longest[a][b + 1]:
            a += 1
        else:
            b += 1
    return pairs


def _resemblance(old: str, fresh: str) -> float:
    """How much fresh reads as a later reading of old.

    A line still being typed starts with its earlier reading. Digits are left
    out because a running counter (12s, 13s) changes every frame.
    """
    na, nb = normalize(old), normalize(fresh)
    if not na or not nb:
        return 0.0
    shorter, longer = sorted((na, nb), key=len)
    if len(shorter) >= MIN_PREFIX_CHARS and longer.startswith(shorter):
        return 1.0
    da, db = re.sub(r"\d+", "", na).split(), re.sub(r"\d+", "", nb).split()
    return SequenceMatcher(None, " ".join(da), " ".join(db), autojunk=False).ratio()


def _short(line: Line) -> bool:
    return len(normalize(line.text)) <= VOLATILE_CHARS


def _pair_gap(old: list[Line], fresh: list[Line]) -> dict[int, int]:
    """Pair lines that changed between two matched lines, in order.

    A line pairs with a later reading that resembles it. Failing that, a short
    line pairs with the short line at the same distance from the next matched
    line or the bottom of the frame, which is where a spinner or status word
    sits from frame to frame.
    """
    pairs: dict[int, int] = {}
    last = -1
    for di, line in enumerate(old):
        best = None
        for ni in range(last + 1, len(fresh)):
            score = _resemblance(line.text, fresh[ni].text)
            if score >= RESEMBLANCE and (best is None or score > best[0]):
                best = (score, ni)
        if best is not None:
            pairs[di] = best[1]
            last = best[1]
    for r in range(min(len(old), len(fresh))):
        di, ni = len(old) - 1 - r, len(fresh) - 1 - r
        if di in pairs and pairs[di] == ni:
            continue
        if di in pairs or ni in pairs.values() or not (_short(old[di]) and _short(fresh[ni])):
            break
        if any((d < di) != (n < ni) for d, n in pairs.items()):
            break
        pairs[di] = ni
    return pairs


def _grow(doc: list[Line], new: list[Line]) -> list[Line] | None:
    """The joined lines when new is the end of doc plus added lines, else None.

    Lines above the first match scrolled off and are kept. Every line of doc
    from the first match down must reappear, or be one of a few short changing
    lines, or be the last line of doc, which may have been cut off. New may
    show one cut off line on top. New must add at least one line unless every
    changed line was already seen changing, so a static slide whose title or
    number changed still starts a new screen.
    """
    start = max(0, len(doc) - len(new) - GROW_MAX_CHANGED)
    window = doc[start:]
    anchors = _align(window, new)
    if len(anchors) < GROW_MIN_ANCHORS:
        return None
    bounds = [(-1, -1), *anchors, (len(window), len(new))]
    out = list(doc[:start])
    changed = added = unseen = 0
    for k in range(len(bounds) - 1):
        (a0, b0), (a1, b1) = bounds[k], bounds[k + 1]
        old, fresh = window[a0 + 1 : a1], new[b0 + 1 : b1]
        head, tail = k == 0, k == len(bounds) - 2
        pairs = _pair_gap(old, fresh)
        paired_new = set(pairs.values())
        lone_old = [di for di in range(len(old)) if di not in pairs]
        lone_new = [ni for ni in range(len(fresh)) if ni not in paired_new]
        cut_top = None
        if head:
            changed += len(pairs)
            if lone_new and start + len(old) > 0:
                if lone_new != [0]:
                    return None
                cut_top = 0
            else:
                added += len(lone_new)
        else:
            changed += len(old)
            allowed = [len(old) - 1] if tail else []
            if any(di not in allowed for di in lone_old):
                return None
            unseen += len(lone_old)
            added += len(lone_new)
        unseen += sum(1 for di in pairs if not old[di].variants)
        dpos = npos = 0
        for di, ni in [*sorted(pairs.items()), (len(old), len(fresh))]:
            out += old[dpos:di]
            for n in range(npos, ni):
                if n == cut_top:
                    if not out:
                        return None
                    out[-1] = _combine(out[-1], fresh[n])
                else:
                    out.append(fresh[n])
            if di < len(old):
                out.append(_combine(old[di], fresh[ni]))
            dpos, npos = di + 1, ni + 1
        if k < len(anchors):
            out.append(_combine(window[a1], new[b1]))
    if changed > GROW_MAX_CHANGED:
        return None
    if added < 1 and (changed == 0 or unseen):
        return None
    return out


def _grow_into(screen: Screen, new: list[Line]) -> bool:
    joined = _grow(screen.lines, new)
    if joined is None:
        return False
    screen.lines = joined
    return True


def _drop_consecutive_repeats(lines: list[Line]) -> list[Line]:
    out: list[Line] = []
    for line in lines:
        if out and normalize(out[-1].text) == normalize(line.text):
            if line.conf > out[-1].conf:
                kept = Line(line.text, line.conf, out[-1].frame, out[-1].time, list(out[-1].variants))
                kept.add_variant(out[-1].text)
                out[-1] = kept
            for variant in line.variants:
                out[-1].add_variant(variant)
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
        if screens and (_merge(screens[-1], lines) or _grow_into(screens[-1], lines)):
            current = screens[-1]
        else:
            earlier = next((s for s in screens[:-1] if _contained(s, lines)), None)
            if earlier is not None:
                found = find_overlap(earlier.lines, lines)
                if found is not None:
                    i, j, t, _ = found
                    for k in range(t):
                        earlier.lines[i + k].add_variant(lines[j + k].text)
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
