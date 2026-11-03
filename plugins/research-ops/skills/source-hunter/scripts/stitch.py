"""Stitch OCR lines from successive frames into continuous screens.

A scrolling screen shows overlapping windows of the same text. Each new frame
is aligned against the end of the current screen, and only the lines past the
overlap are added, so the scroll comes back as one text with no repeats.

A chat message that grows as it streams is joined the same way. Its frames
are the current screen plus added lines, with a small upward shift of the
pane, a cut off top or bottom line, and a short spinner or status line that
reads differently in every frame. That changing line stays one line and keeps
its other readings as variants.

Real OCR misreads a few steady lines in most frames. A frame that keeps most of
the screen in order still joins it, and every misread or missing reading is
kept, so noise never loses a line.
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
# A line this long or longer, digits left out, is long enough that OCR noise on it
# reads as noise rather than as a different line.
LONG_LINE_CHARS = 30
# A line longer than this, digits left out, is not a status word, so a lone digit
# that only one reading has, with every other word the same, is OCR noise.
MEDIUM_LINE_CHARS = VOLATILE_CHARS
# How closely a misread long line must read like its other reading.
NEAR_MISS = 0.5
# A changed word still counts as the same word misread at this likeness.
WORD_MISREAD = 0.6
# A word in a ticking header counts as misread, not rewritten, only at this likeness.
COUNTER_WORD_MISREAD = 0.75
# A number among this many first words of a top line numbers the slide (Week 1),
# rather than counting something on it.
TITLE_NUMBER_WORDS = 2
# A line cut at another place still shares at least this much of its words in the middle.
CUT_KEEP = 0.6
# More changed lines than GROW_MAX_CHANGED are noise, not a different screen, only
# when at least this share of the compared lines still match in order.
KEPT_SHARE = 2 / 3


@dataclass
class Line:
    text: str
    conf: float = 0.0
    frame: int = 0
    time: float = 0.0
    variants: list[str] = field(default_factory=list)
    # Set once the growth step sees this short line read as a different line in place,
    # as a spinner or status word does. OCR noise on a steady line never sets it.
    volatile: bool = False

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
            "lines": [{k: v for k, v in asdict(line).items() if k != "volatile"} for line in self.lines],
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
    if not _numbers_agree(na, nb, r"\b\d+\b"):
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
        following = new[j + k + 1] if j + k + 1 < len(new) else None
        if fresh.conf > old.conf or _wrapped(old, fresh, following):
            doc[i + k] = _reread(old, fresh)
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


def _reread(old: Line, fresh: Line) -> Line:
    """Old's line with fresh's reading as its text and every earlier reading kept."""
    kept = Line(fresh.text, fresh.conf, old.frame, old.time, list(old.variants), old.volatile)
    kept.add_variant(old.text)
    return kept


def _combine(old: Line, fresh: Line, keep: Line | None = None) -> Line:
    """One line holding both readings.

    The text is keep's reading when given. Otherwise the complete reading wins
    over one that was cut off or still being typed, and failing that the more
    confident one.
    """
    if keep is None:
        keep = _complete(old, fresh) or (fresh if fresh.conf > old.conf else old)
    if keep is fresh:
        kept = _reread(old, fresh)
    else:
        kept = Line(old.text, old.conf, old.frame, old.time, list(old.variants), old.volatile)
        kept.add_variant(fresh.text)
    for variant in fresh.variants:
        kept.add_variant(variant)
    kept.volatile = old.volatile or fresh.volatile
    return kept


def _align(doc: list[Line], new: list[Line]) -> list[tuple[int, int]]:
    """Longest in-order run of similar lines between doc and new, as index pairs.

    When two doc lines could take the same new line, the later one does, so new
    lines up against the end of doc as a scroll does.
    """
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
        if match[a][b] and longest[a + 1][b] < longest[a][b]:
            pairs.append((a, b))
            a, b = a + 1, b + 1
        elif longest[a + 1][b] >= longest[a][b + 1]:
            a += 1
        else:
            b += 1
    return pairs


def _numbers(normalized: str) -> list[str]:
    return re.findall(r"\d+", normalized)


def _letters(normalized: str) -> str:
    return " ".join(re.sub(r"\d+", "", normalized).split())


def _long(normalized: str) -> bool:
    return len(_letters(normalized)) >= LONG_LINE_CHARS


def _numbers_agree(na: str, nb: str, pattern: str = r"\d+") -> bool:
    """True unless the numbers in two normalized readings mark them as different lines.

    Numbers that differ mark different lines (Week 1, Week 2) when the line is
    otherwise short, or when one number reads as another. On a long line, a lone
    digit that only one reading has is OCR noise, as a stray 1 or 0 often is. On
    a medium line it is noise only when every other word reads the same.
    """
    a, b = re.findall(pattern, na), re.findall(pattern, nb)
    if a == b:
        return True
    if len(a) == len(b):
        return False
    if not (_long(na) and _long(nb)):
        return _stray_digit(na, nb)
    fewer, more = (a, nb) if len(a) < len(b) else (b, na)
    wanted = list(fewer)
    for token in more.split():
        found = re.findall(pattern, token)
        if not found:
            continue
        if wanted[: len(found)] == found:
            wanted = wanted[len(found) :]
        elif not (len(token) == 1 and token.isdigit()):
            return False
    return not wanted


def _stray_digit(na: str, nb: str) -> bool:
    """True when two medium readings differ only by one lone digit word."""
    if min(len(_letters(na)), len(_letters(nb))) <= MEDIUM_LINE_CHARS:
        return False
    fewer, more = sorted((na.split(), nb.split()), key=len)
    if len(more) != len(fewer) + 1:
        return False
    return any(
        len(word) == 1 and word.isdigit() and more[:k] + more[k + 1 :] == fewer
        for k, word in enumerate(more)
    )


def _counter_ticked(na: str, nb: str) -> bool:
    """True when two long readings differ in their numbers, as a running counter does.

    The words around the counter may also be misread a little from frame to
    frame, so the letters need only be alike at SIMILARITY, and every word that
    differs, end words included, must still read like its partner.
    """
    if na == nb or not (_long(na) and _long(nb)):
        return False
    la, lb = _letters(na), _letters(nb)
    if la == lb:
        return True
    if re.sub(r"\D", "", na) == re.sub(r"\D", "", nb):
        return False
    if SequenceMatcher(None, la, lb, autojunk=False).ratio() < SIMILARITY:
        return False
    # Every differing word, end words included, must read like its partner.
    wa, wb = la.split(), lb.split()
    for tag, i1, i2, j1, j2 in SequenceMatcher(None, wa, wb, autojunk=False).get_opcodes():
        if tag == "equal":
            continue
        if i2 - i1 != j2 - j1:
            return False
        for x, y in zip(wa[i1:i2], wb[j1:j2]):
            if not _misread_word(x, y):
                return False
    return True


def _counter_on_top(old: Line, fresh: Line) -> bool:
    """True when the top line of both frames reads the same apart from a running counter.

    The words must agree as _counter_ticked asks, so a rewritten header never
    passes. A changed number among the first TITLE_NUMBER_WORDS words numbers
    the slide (Week 1, Week 2) instead of counting, so it does not pass either.
    """
    na, nb = normalize(old.text), normalize(fresh.text)
    if not _counter_ticked(na, nb):
        return False
    lead_a, lead_b = (" ".join(n.split()[:TITLE_NUMBER_WORDS]) for n in (na, nb))
    return _numbers(lead_a) == _numbers(lead_b)


def _misread_word(x: str, y: str) -> bool:
    """True when y reads as x with a letter or two misread, not as another word."""
    if len(x) == len(y) and len(x) <= 4:
        return sum(a != b for a, b in zip(x, y)) <= 1
    return SequenceMatcher(None, x, y, autojunk=False).ratio() >= COUNTER_WORD_MISREAD


def _cut_off(old: Line, fresh: Line) -> bool:
    """True when fresh is a clean start of old, a line that is not a status word, read cut off."""
    na, nb = normalize(old.text), normalize(fresh.text)
    return not _short(old) and len(nb) < len(na) and _is_prefix(na, nb)


def _ocr_damage(na: str, nb: str) -> bool:
    """True when every word that differs looks misread, not rewritten.

    OCR damage swaps, drops or splits letters inside a word, or cuts the line at
    another place. An edit swaps a word for a different word. So words may only
    differ at either end around a long shared middle, each other changed
    stretch must keep about the same number of words, and each changed word
    must still read like its partner.
    """
    wa, wb = re.sub(r"\d+", "", na).split(), re.sub(r"\d+", "", nb).split()
    codes = SequenceMatcher(None, wa, wb, autojunk=False).get_opcodes()
    same = sum(i2 - i1 for tag, i1, i2, _, _ in codes if tag == "equal")
    cut = same >= CUT_KEEP * min(len(wa), len(wb))
    for tag, i1, i2, j1, j2 in codes:
        if tag == "equal":
            continue
        # Words that differ only at either end, around a long shared middle, are
        # the line cut at another place or a neighbor's words run into it.
        if cut and (i1 == 0 and j1 == 0 or i2 == len(wa) and j2 == len(wb)):
            continue
        a, b = wa[i1:i2], wb[j1:j2]
        if abs(len(a) - len(b)) > 1:
            return False
        if len(a) != len(b):
            # A word split or joined by the OCR reads the same once spaces go.
            if SequenceMatcher(None, "".join(a), "".join(b), autojunk=False).ratio() < WORD_MISREAD:
                return False
            continue
        for x, y in zip(a, b):
            if SequenceMatcher(None, x, y, autojunk=False).ratio() < WORD_MISREAD:
                return False
    return True


def _near_miss(old: Line, fresh: Line) -> bool:
    """True when two readings of a long line differ only as OCR noise does."""
    na, nb = normalize(old.text), normalize(fresh.text)
    return (_long(na) and _long(nb) and _numbers_agree(na, nb)
            and _resemblance(old.text, fresh.text) >= NEAR_MISS and _ocr_damage(na, nb))


def _keeps_most(steady: int, changed: int) -> bool:
    """True when most of the compared lines still match in order."""
    return steady >= GROW_MIN_ANCHORS and steady >= KEPT_SHARE * (steady + changed)


def _is_prefix(na: str, nb: str) -> bool:
    """True when one normalized reading is a long enough start of the other."""
    shorter, longer = sorted((na, nb), key=len)
    return shorter != longer and len(shorter) >= MIN_PREFIX_CHARS and longer.startswith(shorter)


def _continues(old: Line, fresh: Line) -> bool:
    """True when fresh is old with more text typed after it."""
    na, nb = normalize(old.text), normalize(fresh.text)
    return len(nb) > len(na) and _is_prefix(na, nb)


def _fragment_of(part: Line, whole: Line) -> bool:
    """True when part reads as a cut off piece of whole."""
    np_, nw = normalize(part.text), normalize(whole.text)
    if not np_ or len(np_) >= len(nw):
        return False
    if nw.startswith(np_):
        return True
    # A reading nearly as long as the line that still differs from it is another line.
    if len(np_) > SIMILARITY * len(nw):
        return False
    matcher = SequenceMatcher(None, np_, nw, autojunk=False)
    return sum(block.size for block in matcher.get_matching_blocks()) >= SIMILARITY * len(np_)


def _complete(old: Line, fresh: Line) -> Line | None:
    """The full reading when the other one is cut off or still being typed."""
    if _fragment_of(old, fresh):
        return fresh
    if _fragment_of(fresh, old):
        return old
    return None


def _wrapped(old: Line, fresh: Line, following: Line | None) -> bool:
    """True when old's end moved down to start the following line, as a word does when it wraps."""
    if following is None:
        return False
    no, nf, nn = normalize(old.text), normalize(fresh.text), normalize(following.text)
    if len(nf) < MIN_PREFIX_CHARS or not no.startswith(nf + " "):
        return False
    return nn.startswith(no[len(nf) + 1 :])


def _repeats_in_place(doc: list[Line], new: list[Line], anchors: list[tuple[int, int]]) -> bool:
    """True when new shows every line of a short doc at its place, give or take its last line.

    A short line may read differently at its place, as a status word does. The
    doc's last line may also be matched lower down, below lines new added above it.
    """
    body = anchors[:-1] if anchors[-1] == (len(doc) - 1, len(new) - 1) else anchors
    if any(a != b for a, b in body):
        return False
    held = {a for a, _ in body}
    return all(
        x in held or (x < len(new) and _short(doc[x]) and _short(new[x]))
        for x in range(len(doc) - 1)
    )


def _resemblance(old: str, fresh: str) -> float:
    """How much fresh reads as a later reading of old.

    A line still being typed starts with its earlier reading. Digits are left
    out because a running counter (12s, 13s) changes every frame.
    """
    na, nb = normalize(old), normalize(fresh)
    if not na or not nb:
        return 0.0
    if _is_prefix(na, nb):
        return 1.0
    da, db = re.sub(r"\d+", "", na).split(), re.sub(r"\d+", "", nb).split()
    return SequenceMatcher(None, " ".join(da), " ".join(db), autojunk=False).ratio()


def _short(line: Line) -> bool:
    return len(normalize(line.text)) <= VOLATILE_CHARS


def _pair_gap(
    old: list[Line], fresh: list[Line], bottom: bool, top: bool = False
) -> tuple[dict[int, int], set[int]]:
    """Pair lines that changed between two matched lines, in order.

    A line pairs with a later reading that resembles it, or with a misread
    reading of a long line that is a near miss. Failing that, a short
    line pairs with the short line at the same distance from the next matched
    line or the bottom of the frame, which is where a spinner or status word
    sits from frame to frame. Lines whose numbers differ are different lines
    (Week 1, Week 2), except a stray digit on a long line, and a short last
    line at the bottom of both frames, which is where a running counter sits.
    At the top of the screen, the first lines of both frames also pair when
    they are long and only their numbers differ, as a header with a running
    counter does. Only there, since a long line lower down whose number
    changes is a different line.

    Returns the pairs and the old indexes paired by place alone.
    """

    def allowed(di: int, ni: int) -> bool:
        na, nb = normalize(old[di].text), normalize(fresh[ni].text)
        if _numbers_agree(na, nb) or _is_prefix(na, nb):
            return True
        if top and di == 0 and ni == 0 and _counter_ticked(na, nb):
            return True
        return (
            bottom
            and di == len(old) - 1
            and ni == len(fresh) - 1
            and _short(old[di])
            and _short(fresh[ni])
        )

    pairs: dict[int, int] = {}
    by_place: set[int] = set()
    last = -1
    for di, line in enumerate(old):
        best = None
        for ni in range(last + 1, len(fresh)):
            if not allowed(di, ni):
                continue
            score = _resemblance(line.text, fresh[ni].text)
            enough = NEAR_MISS if _near_miss(line, fresh[ni]) else RESEMBLANCE
            if score >= enough and (best is None or score > best[0]):
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
        if not allowed(di, ni) or any((d < di) != (n < ni) for d, n in pairs.items()):
            break
        pairs[di] = ni
        by_place.add(di)
    return pairs, by_place


def _join_changed(old: Line, fresh: Line, following: Line | None = None) -> Line:
    """One line for a line that reads differently in the new frame.

    A complete reading wins over a cut off or partly typed one, unless the
    rest of the longer reading wrapped onto the following line. A short line
    that changed in place, such as a spinner, shows its newest reading, so a
    short closing line that replaced it stays visible. Otherwise the more
    confident reading wins.
    """
    complete = _complete(old, fresh)
    in_place = _short(old) and _short(fresh) and not similar(old.text, fresh.text)
    if _wrapped(old, fresh, following):
        joined = _combine(old, fresh, keep=fresh)
    elif complete is not None:
        joined = _combine(old, fresh, keep=complete)
    elif in_place:
        joined = _combine(old, fresh, keep=fresh)
    else:
        joined = _combine(old, fresh)
    if in_place and not _continues(old, fresh):
        joined.volatile = True
    return joined


def _grow(doc: list[Line], new: list[Line]) -> list[Line] | None:
    """The joined lines when new is the end of doc plus added lines, else None.

    Lines above the first match scrolled off and are kept. Every line of doc
    from the first match down must reappear, or be one of a few short changing
    lines, or be a short last line of doc, which is kept. New may show one cut
    off piece of the line above its first match on top. A changed line that
    is not short, or that sits above the first match, must be a cut off,
    partly typed or wrapped reading of the same line, so a slide whose title
    changed starts a new screen even when it adds a bullet. New must add a
    line, or extend one, unless every changed line was already seen changing
    or reads as a clean cut off start of a line that is not a status word, so a
    static slide whose title or number changed still starts a new screen.

    Real OCR misreads a few steady lines in every frame, so the frame is also
    judged by how much of the screen it keeps in order. When most compared
    lines match in order, a long line that is a near miss of its earlier
    reading joins it, and a line missing from new between matched lines, with
    nothing in its place, is kept. So does the top line of the screen when only
    its numbers changed, as a header with a running counter does. None of these
    counts as a change new must add to, except a changed number in the first
    words of the top line, which may be the next numbered slide.

    A screen too short to hold GROW_MIN_ANCHORS steady lines, as at the start
    of a message, joins only when new repeats every line of it in place, apart
    from short lines such as a status word that read differently in place,
    its last line reappears as new's last line or changes into a line that
    resembles it or was already seen changing, and new adds a line.
    """
    start = max(0, len(doc) - len(new) - GROW_MAX_CHANGED)
    window = doc[start:]
    anchors = _align(window, new)
    early = start == 0 and 0 < len(anchors) < GROW_MIN_ANCHORS and _repeats_in_place(doc, new, anchors)
    if len(anchors) < GROW_MIN_ANCHORS and not early:
        return None
    bounds = [(-1, -1), *anchors, (len(window), len(new))]
    out = list(doc[:start])
    changed = added = grown = unseen = tolerated = cut = 0
    for k in range(len(bounds) - 1):
        (a0, b0), (a1, b1) = bounds[k], bounds[k + 1]
        old, fresh = window[a0 + 1 : a1], new[b0 + 1 : b1]
        head, tail = k == 0, k == len(bounds) - 2
        pairs, by_place = _pair_gap(old, fresh, bottom=tail, top=head and start == 0)
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
            allowed = [len(old) - 1] if tail and old and _short(old[-1]) else []
            missing = [di for di in lone_old if di not in allowed]
            if missing and lone_new:
                # A line replaced by a different line, not a line the OCR dropped.
                return None
            if early and tail and old:
                last = len(old) - 1
                if last not in pairs or (last in by_place and not old[last].volatile):
                    return None
            tolerated += len(missing)
            unseen += len(lone_old) - len(missing)
            added += len(lone_new)
        for di, ni in pairs.items():
            if _continues(old[di], fresh[ni]):
                grown += 1
            elif not old[di].volatile:
                status_like = not head and _short(old[di]) and _short(fresh[ni])
                if head and start == 0 and di == 0 and ni == 0 and _counter_ticked(
                    normalize(old[di].text), normalize(fresh[ni].text)
                ):
                    tolerated += 1
                    if not _counter_on_top(old[di], fresh[ni]):
                        # A title number change alone could be the next numbered
                        # slide, so it never lets a frame that adds nothing join.
                        unseen += 1
                elif status_like or _complete(old[di], fresh[ni]) is not None:
                    unseen += 1
                    cut += _cut_off(old[di], fresh[ni])
                elif _near_miss(old[di], fresh[ni]):
                    tolerated += 1
                else:
                    return None
        dpos = npos = 0
        for di, ni in [*sorted(pairs.items()), (len(old), len(fresh))]:
            out += old[dpos:di]
            for n in range(npos, ni):
                if n == cut_top:
                    if not out or not _fragment_of(fresh[n], out[-1]):
                        return None
                    out[-1] = _combine(out[-1], fresh[n], keep=out[-1])
                else:
                    out.append(fresh[n])
            if di < len(old):
                following = new[b0 + 2 + ni] if b0 + 2 + ni < len(new) else None
                out.append(_join_changed(old[di], fresh[ni], following))
            dpos, npos = di + 1, ni + 1
        if k < len(anchors):
            following = new[b1 + 1] if b1 + 1 < len(new) else None
            keep = new[b1] if _wrapped(window[a1], new[b1], following) else None
            out.append(_combine(window[a1], new[b1], keep=keep))
    if (changed > GROW_MAX_CHANGED or tolerated) and not _keeps_most(len(anchors), changed):
        return None
    if early and added < 1:
        return None
    if added + grown < 1 and (changed == 0 or unseen > cut):
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
                out[-1] = _reread(out[-1], line)
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
