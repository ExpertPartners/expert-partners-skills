from stitch import Line, normalize, stitch


def _frame(index, texts):
    return (index, index / 10, index / 10, [Line(t, 90.0) for t in texts])


DOC = [f"{w} sentence about the {x}" for w, x in zip(
    ["first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth"],
    ["river", "mountain", "garden", "window", "harbor", "orchard", "meadow", "bridge"],
)]


def test_scroll_windows_join_without_repeats():
    frames = [_frame(n, DOC[n:n + 4]) for n in range(0, 5)]
    screens = stitch(frames)
    assert len(screens) == 1
    assert [l.text for l in screens[0].lines] == DOC


def test_window_already_seen_adds_nothing():
    frames = [_frame(0, DOC[:5]), _frame(1, DOC[1:4])]
    screens = stitch(frames)
    assert [l.text for l in screens[0].lines] == DOC[:5]


def test_unrelated_slide_starts_a_new_screen_and_return_is_not_repeated():
    other = ["a different slide entirely", "with its own closing words"]
    frames = [_frame(0, DOC[:4]), _frame(1, other), _frame(2, DOC[:4])]
    screens = stitch(frames)
    assert len(screens) == 2
    assert [l.text for l in screens[1].lines] == other


def test_small_ocr_misread_still_overlaps():
    noisy = [DOC[2].replace("garden", "gardcn"), DOC[3], DOC[4], DOC[5]]
    screens = stitch([_frame(0, DOC[:4]), _frame(1, noisy)])
    assert len(screens) == 1
    assert len(screens[0].lines) == 6


def test_numbered_lines_are_kept_apart():
    weeks = [f"Week {n} call recording link" for n in range(1, 9)]
    static = stitch([_frame(0, weeks[:3])])
    assert [l.text for l in static[0].lines] == weeks[:3]
    scrolled = stitch([_frame(n, weeks[n:n + 5]) for n in range(0, 4)])
    assert len(scrolled) == 1
    assert [l.text for l in scrolled[0].lines] == weeks


def test_non_latin_text_survives_normalizing():
    from stitch import normalize, similar

    assert normalize("Привет, мир") == "привет мир"
    assert normalize("Café naïve") == "cafe naive"
    assert similar("Привет мир", "привет, мир")


def test_slides_sharing_a_footer_stay_separate_and_keep_every_line():
    footer = ["Expert Partners brand footer", "Page footer with the date"]
    a = ["Title for slide A", "first point on slide A", "second point on slide A"] + footer
    b = ["How pricing works", "Charge for the outcome, not the hours"] + footer
    c = ["Scoring the board", "Each advisor gives one number"] + footer
    screens = stitch([_frame(0, a), _frame(1, b), _frame(2, c)])
    texts = [l.text for s in screens for l in s.lines]
    for line in a + b + c:
        assert line in texts
    assert len(screens) == 3


def test_slides_sharing_a_header_keep_the_earlier_last_line():
    a = ["Module one overview", "Shadow board advisor setup", "Ask three advisors for input"]
    b = ["Module one overview", "Shadow board advisor setup", "Score each answer out loud", "Pick the strongest answer"]
    screens = stitch([_frame(0, a), _frame(1, b)])
    texts = [l.text for s in screens for l in s.lines]
    for line in a + b:
        assert line in texts


def test_a_word_that_changes_between_frames_is_kept_as_a_variant():
    a = ["Building the board", "Pick three advisors you trust", "Write the charter today"]
    b = ["Building the board", "Pick two advisors you trust", "Write the charter tomorrow"]
    screens = stitch([_frame(0, a), _frame(1, b)])
    readings = {t for s in screens for l in s.lines for t in [l.text, *l.variants]}
    for line in a + b:
        assert line in readings


def test_a_short_line_is_not_swallowed_by_a_longer_one():
    a = ["Week zero plan", "Goals"]
    b = ["Week zero plan", "Goals and metrics for the first month", "Owner and due date"]
    screens = stitch([_frame(0, a), _frame(1, b)])
    texts = [l.text for s in screens for l in s.lines]
    assert "Goals" in texts
    assert "Goals and metrics for the first month" in texts


def test_a_slide_shown_again_keeps_a_changed_reading():
    first = ["Building the board", "Pick three advisors you trust", "Score each answer out loud"]
    other = ["A different slide entirely", "with its own closing words"]
    again = ["Building the board", "Pick two advisors you trust", "Score each answer out loud"]
    screens = stitch([_frame(0, first), _frame(1, other), _frame(2, again)])
    readings = {t for s in screens for l in s.lines for t in [l.text, *l.variants]}
    for line in first + other + again:
        assert line in readings


VERBS = (
    "gather sort label check sketch measure polish water fold count tune pack "
    "read seal paint carry sweep stack mend trim wrap brush clean lift plant "
    "print scan file bind press mark hang fill test"
).split()
NOUNS = (
    "maple copper velvet harbor lantern granite silver jasmine crimson walnut "
    "brass cedar coral amber willow cobalt ivory saffron onyx pewter linen "
    "marble ember juniper basil quartz garnet hazel indigo olive opal russet slate topaz"
).split()
PLACES = (
    "attic barn cellar dock garage hall kitchen loft market office pantry porch "
    "quarry studio tower vault yard bakery chapel depot forge garden inn kiosk "
    "library mill nursery orchard parlor ranch school temple wharf workshop"
).split()
MESSAGE = [f"{v} each {n} box at the {p}" for v, n, p in zip(VERBS, NOUNS, PLACES)]
STATUS_WORDS = ["Thinking", "Pondering", "Brewing", "Musing"]


def _spinner(f):
    return f"{STATUS_WORDS[f % len(STATUS_WORDS)]} {f + 3}s"


def _streaming_frames(message, count=20, visible=8, start=4):
    """A message growing one or two lines a frame, the pane shifting up, a spinner below."""
    frames, shown = [], start
    for f in range(count):
        frames.append(_frame(f, message[max(0, shown - visible):shown] + [_spinner(f)]))
        shown += 1 + f % 2
    return frames, shown - 1 - (count - 1) % 2


def _readings(screen):
    return {t for l in screen.lines for t in [l.text, *l.variants]}


def test_synthetic_stream_lines_read_as_different_lines():
    from stitch import similar

    assert len(MESSAGE) >= 32
    for n, a in enumerate(MESSAGE):
        for b in MESSAGE[n + 1:]:
            assert not similar(a, b)


def test_growing_message_with_a_spinner_stitches_into_one_screen():
    frames, shown = _streaming_frames(MESSAGE)
    screens = stitch(frames)
    assert len(screens) == 1
    lines = screens[0].lines
    texts = [l.text for l in lines]
    assert texts[:-1] == MESSAGE[:shown]
    assert len({normalize(t) for t in texts}) == len(texts)
    assert sorted(screens[0].frames) == list(range(20))
    spinner = {lines[-1].text, *lines[-1].variants}
    assert spinner == {_spinner(f) for f in range(20)}


def test_status_word_beside_a_streaming_message_stays_one_line():
    statuses = ["Thinking", "Searching", "Writing", "Reading sources"]
    frames = [
        _frame(f, ["Assistant reply", statuses[f % 4]] + MESSAGE[:3 + f])
        for f in range(20)
    ]
    screens = stitch(frames)
    assert len(screens) == 1
    texts = [l.text for l in screens[0].lines]
    assert texts == ["Assistant reply", "Thinking"] + MESSAGE[:22]
    assert set(statuses) <= _readings(screens[0])


def test_a_stream_frame_that_only_moves_the_spinner_stays_in_the_screen():
    frames, shown = _streaming_frames(MESSAGE, count=6)
    last = frames[-1]
    paused = (last[0] + 1, last[1] + 0.1, last[2] + 0.1, last[3][:-1] + [Line("Musing 40s", 90.0)])
    resumed = _frame(last[0] + 2, [l.text for l in last[3][2:-1]] + MESSAGE[shown:shown + 2] + ["Brewing 41s"])
    screens = stitch(frames + [paused, resumed])
    assert len(screens) == 1
    lines = screens[0].lines
    assert [l.text for l in lines[:-1]] == MESSAGE[:shown + 2]
    assert {"Musing 40s", "Brewing 41s"} <= {lines[-1].text, *lines[-1].variants}


def test_a_real_screen_change_after_a_stream_starts_a_new_screen():
    frames, shown = _streaming_frames(MESSAGE, count=6)
    other = ["A different slide entirely", "with its own closing words", "and a third unrelated line"]
    frames += [_frame(6 + n, other) for n in range(3)]
    screens = stitch(frames)
    assert len(screens) == 2
    assert [l.text for l in screens[0].lines[:-1]] == MESSAGE[:shown]
    assert [l.text for l in screens[1].lines] == other


def test_numbered_lines_in_a_growing_stream_are_kept_apart():
    weeks = [f"Week {n} call recording link" for n in range(1, 41)]
    frames, shown = _streaming_frames(weeks)
    screens = stitch(frames)
    assert len(screens) == 1
    texts = [l.text for l in screens[0].lines]
    assert texts[:-1] == weeks[:shown]
    for line in screens[0].lines[:-1]:
        assert line.variants == []


def test_a_static_slide_whose_week_number_changes_keeps_both_lines():
    shared = ["Course schedule overview", "Calls are recorded for replay", "Bring one question each time"]
    a = shared + ["Week 1 call recording link"]
    b = shared + ["Week 2 call recording link"]
    screens = stitch([_frame(0, a), _frame(1, b)])
    texts = [l.text for s in screens for l in s.lines]
    assert "Week 1 call recording link" in texts
    assert "Week 2 call recording link" in texts


def test_growing_message_with_a_cut_off_top_line_stays_one_screen():
    first = MESSAGE[:5] + ["Thinking 3s"]
    shifted = ["ach copp bx a th"] + MESSAGE[2:7] + ["Musing 4s"]
    screens = stitch([_frame(0, first), _frame(1, shifted)])
    assert len(screens) == 1
    assert [l.text for l in screens[0].lines[:-1]] == MESSAGE[:7]
    assert "ach copp bx a th" in _readings(screens[0])
