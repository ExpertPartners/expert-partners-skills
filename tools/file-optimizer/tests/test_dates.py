"""Synthetic date-provenance regressions, never private source material."""

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = (
    Path(__file__).resolve().parents[3]
    / "plugins/operating-doctrine/skills/file-to-knowledge-base-optimizer/scripts/optimize.py"
)
SPEC = importlib.util.spec_from_file_location("optimizer", SCRIPT)
OPT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(OPT)

QUOTES = [
    "The garden grows in spring.",
    "The gate stays open today.",
    "The path leads to the garden.",
]


class DateProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def command(self, *args):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), *map(str, args)],
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def extract(self, name="2026-10-02__sample.vtt", source_date=""):
        source = self.root / name
        source.write_text(
            "WEBVTT\n\n"
            + "\n\n".join(
                f"{i}\n00:00:0{i}.000 --> 00:00:0{i + 1}.000\nSample: {quote}"
                for i, quote in enumerate(QUOTES, 1)
            )
            + "\n"
        )
        work = self.root / source.stem
        self.command(
            "extract",
            "--input",
            source,
            "--work",
            work,
            "--source-date",
            source_date,
        )
        return work

    def finish(self, works, intake=None, combine=False):
        intake = {"company_file": "EP", "title": "Garden", **(intake or {})}
        intake_path = self.root / "intake.json"
        intake_path.write_text(json.dumps(intake))
        derived = self.root / "derived"
        derived.mkdir(exist_ok=True)
        data = {
            "summary": [QUOTES[0]],
            "takeaways": [{"point": q, "support": [q]} for q in QUOTES],
            "sections": [],
        }
        if combine:
            data["sections"] = [
                {"heading": "garden", "source": chr(65 + i), "start_line": 1, "end_line": 99}
                for i in range(len(works))
            ]
        draft = derived / ("combined.json" if combine else "derived.json")
        draft.write_text(json.dumps(data))
        parts = []
        for work in works:
            parts += ["--part", work / "parts/part-1.md"]
        self.command(
            "validate",
            "--derived",
            draft,
            "--intake",
            intake_path,
            *parts,
            *(["--combined"] if combine else []),
        )
        out = self.root / "out"
        self.command(
            "finish",
            "--work",
            *works,
            "--intake",
            intake_path,
            "--derived",
            derived,
            "--out",
            out,
            *(["--combine"] if combine else []),
        )
        manifest = json.loads((out / "manifest.json").read_text())
        return (out / manifest["files"][0]["name"]).read_text()

    def test_filename_candidate_is_unknown_through_native_finish(self):
        work = self.extract()
        output = self.finish([work], {"date": ""})
        self.assertIn("\ndate: unknown\n", output)
        self.assertIn("file name shows 2026-10-02, not confirmed as the meeting date", output)
        self.assertNotIn("date_status:", output)
        for i, quote in enumerate(QUOTES, 1):
            self.assertIn(f"[00:00:0{i}.000] {quote}", output)

    def test_unconfirmed_file_metadata_is_not_a_source_date(self):
        work = self.extract("sample.vtt")
        path = work / "source.meta.json"
        meta = json.loads(path.read_text())
        meta["date_from_file"] = "2026-09-01"
        path.write_text(json.dumps(meta))
        output = self.finish([work])
        self.assertIn("\ndate: unknown\n", output)
        self.assertIn(
            "file metadata shows 2026-09-01, not confirmed as the meeting date",
            output,
        )

    def test_explicit_intake_date_is_preserved(self):
        output = self.finish([self.extract()], {"date": "2026-08-03"})
        self.assertIn("\ndate: 2026-08-03\n", output)
        self.assertIn("from the intake", output)

    def test_explicit_source_date_is_preserved(self):
        output = self.finish([self.extract(source_date="2026-08-04")])
        self.assertIn("\ndate: 2026-08-04\n", output)
        self.assertIn("source date supplied at extraction", output)

    def test_embedded_date_fact_stays_in_content(self):
        work = self.extract()
        source = work / "source.md"
        text = source.read_text() + "\nMeeting date: 2026-08-05.\n"
        source.write_text(text)
        (work / "parts/part-1.md").write_text(text)
        output = self.finish([work], {"date": "2026-08-05"})
        self.assertIn("Meeting date: 2026-08-05.", output)
        self.assertIn("\ndate: 2026-08-05\n", output)

    def test_combine_does_not_promote_filename_or_metadata(self):
        work = self.extract()
        second = self.extract("other.vtt")
        path = second / "source.meta.json"
        meta = json.loads(path.read_text())
        meta["date_from_file"] = "2026-09-01"
        path.write_text(json.dumps(meta))
        output = self.finish([work, second], combine=True)
        self.assertIn('\ndate: "unknown, unknown"\n', output)
        self.assertIn("2026-10-02__sample.vtt, unknown.", output)
        self.assertIn("file name shows 2026-10-02, not confirmed as the meeting date", output)
        self.assertIn(
            "file metadata shows 2026-09-01, not confirmed as the meeting date",
            output,
        )

    def test_combine_explicit_source_dates_are_preserved(self):
        output = self.finish(
            [self.extract(), self.extract("other.vtt", "2026-08-04")],
            {"source_dates": {"2026-10-02__sample.vtt": "2026-08-03"}},
            combine=True,
        )
        self.assertIn('\ndate: "2026-08-03, 2026-08-04"\n', output)
        self.assertIn("2026-10-02__sample.vtt, 2026-08-03.", output)
        self.assertIn("dated 2026-08-03 (from the intake)", output)
        self.assertIn(
            "other.vtt, captions (VTT), dated 2026-08-04 (source date supplied at extraction)",
            output,
        )


if __name__ == "__main__":
    unittest.main()
