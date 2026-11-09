"""Offline producer integrity checks in disposable source fixtures."""
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest


SOURCE = pathlib.Path(__file__).resolve().parents[1]


class RenderIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.temp.name)
        shutil.copytree(SOURCE, self.root / "generate", ignore=shutil.ignore_patterns("__pycache__", "tests"))
        self.run_render()

    def tearDown(self):
        self.temp.cleanup()

    def run_render(self, *args):
        return subprocess.run([sys.executable, str(self.root / "generate/render.py"), *args],
                              cwd=self.root, capture_output=True, text=True)

    def test_generated_manifest_is_repeatable_and_accepted(self):
        before = {str(p.relative_to(self.root)): p.read_bytes()
                  for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(self.run_render().returncode, 0)
        after = {str(p.relative_to(self.root)): p.read_bytes()
                 for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(before, after)
        self.assertEqual(self.run_render("--check").returncode, 0)

    def test_missing_manifest_is_rejected(self):
        (self.root / "generate/checksums.txt").unlink()
        result = self.run_render("--check")
        self.assertEqual(result.returncode, 1)
        self.assertIn("DRIFT generate/checksums.txt", result.stdout)

    def test_tampered_manifest_is_rejected(self):
        path = self.root / "generate/checksums.txt"
        path.write_text(path.read_text().replace("  CLAUDE.md", "  unexpected.md"))
        result = self.run_render("--check")
        self.assertEqual(result.returncode, 1)
        self.assertIn("DRIFT generate/checksums.txt", result.stdout)

    def test_target_drift_is_still_rejected(self):
        (self.root / "CLAUDE.md").write_text("corrupted target\n")
        result = self.run_render("--check")
        self.assertEqual(result.returncode, 1)
        self.assertIn("DRIFT CLAUDE.md", result.stdout)


if __name__ == "__main__":
    unittest.main()
