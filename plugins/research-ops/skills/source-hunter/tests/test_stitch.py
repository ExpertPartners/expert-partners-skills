from stitch import Line, stitch


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
