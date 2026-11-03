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
    assert texts == ["Assistant reply", statuses[19 % 4]] + MESSAGE[:22]
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


def test_a_numbered_slide_that_adds_a_bullet_starts_a_new_screen():
    shared = ["Course schedule overview", "Calls are recorded for replay", "Bring one question each time"]
    a = shared + ["Week 1 call recording link"]
    b = shared + ["Week 2 call recording link", "Office hours run on the side"]
    screens = stitch([_frame(0, a), _frame(1, b)])
    assert len(screens) == 2
    assert [l.text for l in screens[1].lines] == b
    for screen in screens:
        for line in screen.lines:
            assert not any("Week" in v for v in line.variants)


def test_a_static_numbered_slide_after_an_ocr_slip_starts_a_new_screen():
    shared = ["Course schedule overview", "Calls are recorded for replay", "Bring one question each time"]
    for week, slip, nxt in [
        ("Week 1 call recording link", "Week 1 call recordlng link", "Week 2 call recording link"),
        ("Week 1 recap", "Week 1 recaq", "Week 2 recap"),
    ]:
        screens = stitch([_frame(0, shared + [week]), _frame(1, shared + [slip]), _frame(2, shared + [nxt])])
        assert len(screens) == 2
        assert [l.text for l in screens[1].lines] == shared + [nxt]


def test_a_short_closing_line_that_replaces_the_spinner_stays_visible():
    frames, shown = _streaming_frames(MESSAGE, count=6)
    last = frames[-1]
    body = [Line(l.text, 90.0) for l in last[3][:-1]]
    spun = (last[0] + 1, last[1] + 0.1, last[2] + 0.1, body + [Line("Thinking 30s", 95.0)])
    done = (last[0] + 2, last[1] + 0.2, last[2] + 0.2, body + [Line("Let me know!", 80.0)])
    screens = stitch(frames + [spun, done])
    texts = [l.text for s in screens for l in s.lines]
    assert "Let me know!" in texts


def test_a_line_still_being_typed_keeps_its_full_reading():
    partial = "Delta is being typ"
    full = "Delta is being typed out in full now"
    first = [Line(t, 90.0) for t in MESSAGE[:4]] + [Line(partial, 95.0)]
    later = [Line(t, 90.0) for t in MESSAGE[:4]] + [Line(full, 80.0), Line(MESSAGE[4], 90.0)]
    screens = stitch([(0, 0.0, 0.0, first), (1, 0.1, 0.1, later)])
    assert len(screens) == 1
    lines = screens[0].lines
    assert [l.text for l in lines] == MESSAGE[:4] + [full, MESSAGE[4]]
    assert partial in lines[4].variants


def test_a_new_top_line_that_is_not_a_cut_off_piece_is_not_hidden():
    first = MESSAGE[:5] + ["Thinking 3s"]
    shifted = ["Unrelated top banner reads here"] + MESSAGE[2:7] + ["Thinking 4s"]
    screens = stitch([_frame(0, first), _frame(1, shifted)])
    texts = [l.text for s in screens for l in s.lines]
    assert "Unrelated top banner reads here" in texts


def test_the_first_frames_of_a_growing_message_join_one_screen():
    frames = [_frame(f, MESSAGE[:f + 1] + [f"Thinking {f + 3}s"]) for f in range(5)]
    screens = stitch(frames)
    assert len(screens) == 1
    lines = screens[0].lines
    assert [l.text for l in lines[:-1]] == MESSAGE[:5]
    assert {f"Thinking {f + 3}s" for f in range(5)} <= {lines[-1].text, *lines[-1].variants}


def test_a_short_slide_that_shares_only_its_title_starts_a_new_screen():
    a = ["Agenda for today", "Thanks"]
    b = ["Agenda for today", "Questions welcome", "Next steps"]
    screens = stitch([_frame(0, a), _frame(1, b)])
    assert len(screens) == 2
    assert [l.text for l in screens[1].lines] == b


def test_a_message_that_extends_its_last_line_stays_one_screen():
    words = "and the reply keeps running on past the edge of what was shown before".split()
    steps = [" ".join(words[:n]) for n in (4, 8, 12, len(words))]
    frames = [_frame(f, MESSAGE[:4] + [text]) for f, text in enumerate(steps)]
    screens = stitch(frames)
    assert len(screens) == 1
    assert [l.text for l in screens[0].lines] == MESSAGE[:4] + [steps[-1]]


def test_similar_lines_line_up_against_the_end_of_the_screen():
    first_review = "Review the first draft before noon"
    final_review = "Review the final draft before noon"
    doc = [first_review, final_review, MESSAGE[0], MESSAGE[1], "Thinking 3s"]
    new = [final_review, MESSAGE[0], MESSAGE[1], MESSAGE[2], "Pondering 4s"]
    screens = stitch([_frame(0, doc), _frame(1, new)])
    assert len(screens) == 1
    assert [l.text for l in screens[0].lines[:-1]] == [first_review, final_review] + MESSAGE[:3]


def test_a_status_above_the_first_lines_of_a_growing_message_stays_one_screen():
    statuses = ["Thinking", "Writing", "Reading sources"]
    frames = [_frame(f, ["Assistant reply", statuses[f]] + MESSAGE[:f + 1]) for f in range(3)]
    screens = stitch(frames)
    assert len(screens) == 1
    assert [l.text for l in screens[0].lines] == ["Assistant reply", statuses[-1]] + MESSAGE[:3]
    assert set(statuses) <= _readings(screens[0])


def test_a_slide_whose_title_changes_and_adds_a_bullet_starts_a_new_screen():
    shared = ["Calls are recorded for replay", "Bring one question each time", "Notes go in the shared folder"]
    for before, after in [
        ("Pricing plan overview", "Hiring plan review"),
        ("Pricing plan", "Hiring plan"),
        ("Pricing for the launch", "Hiring for the launch team"),
    ]:
        a = [before] + shared
        b = [after] + shared + ["Office hours run on the side"]
        screens = stitch([_frame(0, a), _frame(1, b)])
        assert len(screens) == 2
        assert [l.text for l in screens[1].lines] == b
        for screen in screens:
            for line in screen.lines:
                assert before not in line.variants and after not in line.variants


def test_a_typed_word_that_wraps_to_the_next_line_is_not_repeated():
    partial, start, wrapped = "The answer mentions collabor", "The answer mentions", "collaboration in detail"
    in_place = [_frame(0, MESSAGE[:4] + [partial]), _frame(1, MESSAGE[:4] + [start, wrapped])]
    shifted = [
        _frame(0, MESSAGE[:4] + [partial, "Thinking 3s"]),
        _frame(1, MESSAGE[1:4] + [start, wrapped, "Pondering 4s"]),
    ]
    for frames, spinner in [(in_place, 0), (shifted, 1)]:
        screens = stitch(frames)
        assert len(screens) == 1
        lines = screens[0].lines[:len(screens[0].lines) - spinner]
        assert [l.text for l in lines] == MESSAGE[:4] + [start, wrapped]
        assert partial in lines[4].variants


BASE = [
    "Gather the amber pebbles near the willow bank",
    "Carry the copper lantern past the quiet orchard gate",
    "Plant the silver turnips before the second frost arrives",
    "Fold the paper crane twice along the dotted edge",
    "Sing softly while the kettle hums on the stove",
]
ADDED = "Whistle once the lanterns are all lit"


def _noisy_frame(changes, missing=(), added=True):
    lines = [changes.get(n, line) for n, line in enumerate(BASE) if n not in missing]
    return lines + [ADDED] if added else lines


def _assert_one_screen_keeps_every_reading(second):
    screens = stitch([_frame(0, BASE), _frame(1, second)])
    assert len(screens) == 1
    readings = _readings(screens[0])
    for line in BASE + second:
        assert line in readings
    return screens[0]


def test_a_stray_digit_in_a_long_steady_line_still_grows_the_screen():
    second = _noisy_frame({1: "Carry the copper lantern 1 past the quiet orchard gate"})
    screen = _assert_one_screen_keeps_every_reading(second)
    assert [l.text for l in screen.lines] == BASE + [ADDED]


def test_heavy_ocr_noise_on_a_long_middle_line_still_grows_the_screen():
    second = _noisy_frame({2: "Plamt tne sliver tumlps bcfere tha secamd fncst anives"})
    screen = _assert_one_screen_keeps_every_reading(second)
    assert len(screen.lines) == len(BASE) + 1
    assert screen.lines[-1].text == ADDED


def test_a_steady_middle_line_missing_from_one_frame_is_kept():
    second = _noisy_frame({}, missing={2})
    screen = _assert_one_screen_keeps_every_reading(second)
    assert [l.text for l in screen.lines] == BASE + [ADDED]


def test_a_line_cut_at_a_different_place_still_grows_the_screen():
    second = _noisy_frame({3: "Saved Notes Search the paper crane twice along the"})
    screen = _assert_one_screen_keeps_every_reading(second)
    assert len(screen.lines) == len(BASE) + 1
    assert screen.lines[-1].text == ADDED


def test_a_long_line_really_rewritten_still_starts_a_new_screen():
    # Review on PR 197. A real edit is not OCR noise, even when the two lines look alike.
    second = _noisy_frame({3: "Fold the paper swan thrice along the painted rim"})
    screens = stitch([_frame(0, BASE), _frame(1, second)])
    assert len(screens) == 2


def test_a_repeat_frame_whose_top_line_has_a_stray_digit_adds_nothing():
    second = _noisy_frame({0: "Gather the amber 1 pebbles near the willow bank"}, added=False)
    screen = _assert_one_screen_keeps_every_reading(second)
    assert [l.text for l in screen.lines] == BASE


def test_a_noisy_top_line_and_a_stray_digit_still_grow_the_screen():
    second = _noisy_frame({
        0: "Gathor tho ambar pebblcs ncar tne wlllow bamk",
        1: "Carry the copper 1 lantern past the quiet orchard gate",
    })
    screen = _assert_one_screen_keeps_every_reading(second)
    assert len(screen.lines) == len(BASE) + 1
    assert screen.lines[-1].text == ADDED


def test_a_long_numbered_line_whose_number_changes_still_starts_a_new_screen():
    shared = [
        "Calls are recorded for replay each week",
        "Bring one question each time you join us",
        "Notes go in the shared folder after class",
    ]
    a = shared + ["Week 1 call recording link for the spring cohort"]
    for b in (
        shared + ["Week 2 call recording link for the spring cohort"],
        shared + ["Week 2 call recording link for the spring cohort", "Office hours run on the side"],
    ):
        screens = stitch([_frame(0, a), _frame(1, b)])
        assert len(screens) == 2
        assert [l.text for l in screens[1].lines] == b


def test_a_top_line_with_a_running_counter_stays_one_screen():
    # Cause A: the top line reads the same every frame apart from a number that ticks.
    headers = [f"Replay chat for the juniper cohort {n} viewers {2 * n + 1}" for n in range(4)]
    frames = [_frame(f, [headers[f]] + MESSAGE[:4 + f]) for f in range(4)]
    screens = stitch(frames)
    assert len(screens) == 1
    assert [l.text for l in screens[0].lines[1:]] == MESSAGE[:7]
    assert set(headers) <= _readings(screens[0])


def test_a_misread_top_line_with_a_running_counter_stays_one_screen():
    # Live recheck after PR 199: the real header is also misread a little each frame.
    spellings = ["juniper", "junlper", "juniper", "jun1per"]
    headers = [f"Replay chat for the {spellings[n]} cohort {n} viewers {2 * n + 1}" for n in range(4)]
    frames = [_frame(f, [headers[f]] + MESSAGE[:4 + f]) for f in range(4)]
    screens = stitch(frames)
    assert len(screens) == 1
    assert [l.text for l in screens[0].lines[1:]] == MESSAGE[:7]


def test_a_top_line_rewritten_while_its_counter_ticks_still_starts_a_new_screen():
    a = ["Replay chat for the juniper cohort 1 viewers 3"] + MESSAGE[:4]
    b = ["Office hours for the maple circle 2 viewers 5"] + MESSAGE[:5]
    screens = stitch([_frame(0, a), _frame(1, b)])
    assert len(screens) == 2


def test_a_top_line_whose_end_word_is_rewritten_as_its_counter_ticks_starts_a_new_screen():
    # Review on PR 200: "viewers" to "listeners" is an edit, not a misreading.
    a = ["Replay chat for the juniper cohort 1 viewers 3"] + MESSAGE[:4]
    b = ["Replay chat for the juniper cohort 2 listeners 5"] + MESSAGE[:5]
    screens = stitch([_frame(0, a), _frame(1, b)])
    assert len(screens) == 2


def test_a_long_line_below_the_top_whose_number_ticks_still_starts_a_new_screen():
    rows = [f"Replay chat for the juniper cohort {n} viewers {2 * n + 1}" for n in range(2)]
    a = MESSAGE[:4] + [rows[0]] + MESSAGE[4:6]
    b = MESSAGE[:4] + [rows[1]] + MESSAGE[4:7]
    screens = stitch([_frame(0, a), _frame(1, b)])
    assert len(screens) == 2


MEDIUM = [
    "Carry the copper lantern home",
    "Sweep the cedar porch at dusk",
    "Stack the walnut crates high",
    "Mend the linen sail by noon",
    "Trim the hazel hedge neatly",
]


def test_a_stray_digit_on_a_medium_line_still_grows_the_screen():
    # Cause B: these lines are just under LONG_LINE_CHARS once digits go.
    from stitch import LONG_LINE_CHARS, VOLATILE_CHARS, _letters

    assert all(VOLATILE_CHARS < len(_letters(normalize(t))) < LONG_LINE_CHARS for t in MEDIUM)
    for slip in ("Sweep the cedar 1 porch at dusk", "Sweep the cedar porch at dusk 7"):
        second = [MEDIUM[0], slip, *MEDIUM[2:], ADDED]
        screens = stitch([_frame(0, MEDIUM), _frame(1, second)])
        assert len(screens) == 1
        assert [l.text for l in screens[0].lines] == MEDIUM + [ADDED]
        assert slip in _readings(screens[0])


def test_a_medium_line_whose_number_really_changes_still_starts_a_new_screen():
    a = MEDIUM[:4] + ["Week 1 of the hazel hedge plan"]
    for last in ("Week 2 of the hazel hedge plan", "Week 12 of the hazel hedge plan"):
        screens = stitch([_frame(0, a), _frame(1, MEDIUM[:4] + [last, ADDED])])
        assert len(screens) == 2


def test_a_repeat_frame_with_one_cut_off_line_adds_nothing():
    # Cause C: the frame repeats the screen and one line reads cut off.
    for n, cut in [(4, "Sing softly while the kettle"), (2, "Plant the silver turnips before")]:
        second = [cut if k == n else line for k, line in enumerate(BASE)]
        screen = _assert_one_screen_keeps_every_reading(second)
        assert [l.text for l in screen.lines] == BASE
        assert cut in screen.lines[n].variants


def test_a_short_status_line_changing_in_place_still_starts_a_new_screen():
    for before, after in [("Upload pending", "Upload complete"), ("Draft saved locally", "Draft saved")]:
        screens = stitch([_frame(0, BASE[:4] + [before]), _frame(1, BASE[:4] + [after])])
        assert len(screens) == 2
        assert [l.text for l in screens[1].lines] == BASE[:4] + [after]


def test_a_numbered_top_title_on_static_slides_still_starts_a_new_screen():
    # Review on PR 199. "Week 1" then "Week 2" over the same body is two slides,
    # not a ticking counter, when the second frame adds nothing.
    body = [
        "Bring the lantern list to every evening walk",
        "Keep the garden gate latched after the second bell",
        "Leave muddy boots beside the cedar bench outside",
    ]
    a = ["Week 1 call recording link for the willow cohort"] + body
    b = ["Week 2 call recording link for the willow cohort"] + body
    screens = stitch([_frame(0, a), _frame(1, b)])
    assert len(screens) == 2

def test_a_top_line_whose_only_change_is_a_running_counter_stays_one_screen():
    # Case R11, the protoA2 rule: a long top line whose only change is a running
    # counter joins even when the frame adds nothing, since every other line is the same.
    body = [
        "Sort the cobalt tickets by the harbor door",
        "Hang the linen maps along the quarry wall",
        "Count the walnut drawers before the late bell",
    ]
    headers = [f"Lantern keepers posted {n} notes in the cedar hall today" for n in (10, 11, 12)]
    screens = stitch([_frame(f, [header] + body) for f, header in enumerate(headers)])
    assert len(screens) == 1
    assert [l.text for l in screens[0].lines[1:]] == body
    assert set(headers) <= _readings(screens[0])
    # A top line whose letters change as its counter ticks is a different line.
    for changed in (
        "Lantern keepers burned 11 notes in the cedar hall today",
        "Lantern keepers posted 11 notes in the cedar barn today",
    ):
        screens = stitch([_frame(0, [headers[0]] + body), _frame(1, [changed] + body)])
        assert len(screens) == 2
        assert [l.text for l in screens[1].lines] == [changed] + body
