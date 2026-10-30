#!/usr/bin/env python3
"""Offline tests for stage_cards.py. Run: python3 scripts/test_stage_cards.py"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
import stage_cards as sc

SAMPLE = os.path.join(os.path.dirname(__file__), "..", "references", "sample-cards.txt")


def load():
    with open(SAMPLE, encoding="utf-8") as f:
        return sc.parse(f.read())


class ParseTests(unittest.TestCase):
    def test_card_count_and_kinds(self):
        cards = load()
        self.assertEqual(len(cards), 5)
        self.assertEqual(cards[1]["paras"][0]["kind"], "header")
        self.assertEqual([p["kind"] for p in cards[3]["paras"]].count("bullet"), 3)

    def test_bold_runs(self):
        cards = load()
        self.assertEqual(cards[0]["paras"][0]["runs"][0], ("Host intro Sam", True))

    def test_words_kept_exactly(self):
        cards = load()
        self.assertIn("Please welcome Pat Morgan!", sc.para_text(cards[1]["paras"][-1]))

    def test_empty_card_rejected(self):
        with self.assertRaises(sc.CardError):
            sc.parse("hello\n---\n\n---\nworld")


class FitTests(unittest.TestCase):
    def test_sample_fits(self):
        cards = load()
        warns = sc.choose_sizes(cards)
        self.assertEqual([w for w in warns if "will not fit" in w], [])
        self.assertEqual(cards[2]["size"], 10)  # forced

    def test_long_text_drops_to_10_then_flags_split(self):
        word = "word " * 150
        card = sc.parse("# 9:00 AM. A - B\n" + word)[0]
        self.assertTrue(sc.estimate_height(card, 11) > sc.estimate_height(card, 10))
        huge = sc.parse("# 9:00 AM. A - B\n" + "word " * 400)
        self.assertTrue(any("will not fit" in w for w in sc.choose_sizes(huge)))

    def test_long_header_warned(self):
        cards = sc.parse("# 9:00 AM. Somebody Long - " + "topic " * 20 + "\nbody")
        self.assertTrue(any("header" in w for w in sc.choose_sizes(cards)))


class RequestTests(unittest.TestCase):
    def setUp(self):
        self.cards = load()
        sc.choose_sizes(self.cards)
        self.reqs = sc.build_requests(self.cards)

    def test_page_setup(self):
        ds = self.reqs[0]["updateDocumentStyle"]["documentStyle"]
        self.assertEqual(ds["pageSize"]["width"]["magnitude"], 432)
        self.assertEqual(ds["pageSize"]["height"]["magnitude"], 288)
        self.assertEqual(ds["marginTop"]["magnitude"], 19)   # 380 twips
        self.assertEqual(ds["marginLeft"]["magnitude"], 24)  # 480 twips

    def test_one_page_break_between_cards(self):
        pbs = [r for r in self.reqs if "insertPageBreak" in r]
        self.assertEqual(len(pbs), len(self.cards) - 1)
        idxs = [r["insertPageBreak"]["location"]["index"] for r in pbs]
        self.assertEqual(idxs, sorted(idxs, reverse=True))

    def test_headers_navy_bold(self):
        navy = [r for r in self.reqs if "updateTextStyle" in r
                and "foregroundColor" in r["updateTextStyle"]["textStyle"]]
        self.assertEqual(len(navy), 4)
        c = navy[0]["updateTextStyle"]["textStyle"]["foregroundColor"]["color"]["rgbColor"]
        self.assertAlmostEqual(c["red"], 0x24 / 255)

    def test_text_inserted_matches_cards(self):
        text = [r for r in self.reqs if "insertText" in r][0]["insertText"]["text"]
        self.assertIn("Alpha Title with Casey Lin.", text)
        self.assertNotIn("**", text)

    def test_bullet_range_covers_three_paragraphs(self):
        b = [r for r in self.reqs if "createParagraphBullets" in r]
        self.assertEqual(len(b), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
