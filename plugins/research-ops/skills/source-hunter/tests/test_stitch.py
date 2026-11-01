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
