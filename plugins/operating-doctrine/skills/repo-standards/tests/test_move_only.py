"""Synthetic Git fixtures exercise the real helper, including rejected changes."""
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest

HELPER = Path(__file__).resolve().parents[1] / "scripts" / "verify_move_only.py"
spec = importlib.util.spec_from_file_location("move_only", HELPER)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class MoveOnlyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        self.git("init", "-q")
        self.git("config", "user.email", "fixture@example.invalid")
        self.git("config", "user.name", "Fixture")
        (self.repo / "source.md").write_text("Approved source.\nQualifier remains.\n")
        (self.repo / "consumer.md").write_text("See source.md\n")
        self.before = self.commit()

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.repo), *args], stderr=subprocess.PIPE).decode().strip()

    def commit(self):
        self.git("add", "--all")
        self.git("-c", "core.hooksPath=/dev/null", "commit", "-qm", "synthetic fixture")
        return self.git("rev-parse", "HEAD")

    def move(self, destination="renamed.md"):
        (self.repo / "source.md").rename(self.repo / destination)

    def test_exact_move_and_repeat_are_read_only(self):
        self.move("space\tand\nnewline.md")
        after = self.commit()
        snapshot = self.git("status", "--porcelain", "--untracked-files=all")
        expected = [("source.md", "space\tand\nnewline.md")]
        self.assertEqual(module.verify(self.repo, self.before, after), expected)
        self.assertEqual(module.verify(self.repo, self.before, after), expected)
        self.assertEqual(self.git("status", "--porcelain", "--untracked-files=all"), snapshot)

    def test_move_with_rewrite_rejected(self):
        self.move()
        (self.repo / "renamed.md").write_text("Different meaning.\n")
        with self.assertRaises(ValueError):
            module.verify(self.repo, self.before, self.commit())

    def test_move_with_pointer_update_rejected(self):
        self.move()
        (self.repo / "consumer.md").write_text("See renamed.md\n")
        with self.assertRaises(ValueError):
            module.verify(self.repo, self.before, self.commit())

    def test_deletion_rejected(self):
        (self.repo / "source.md").unlink()
        with self.assertRaises(ValueError):
            module.verify(self.repo, self.before, self.commit())

    def test_copy_rejected(self):
        (self.repo / "copy.md").write_bytes((self.repo / "source.md").read_bytes())
        with self.assertRaises(ValueError):
            module.verify(self.repo, self.before, self.commit())

    def test_mode_change_rejected(self):
        self.move()
        (self.repo / "renamed.md").chmod(0o755)
        with self.assertRaises(ValueError):
            module.verify(self.repo, self.before, self.commit())

    def test_empty_diff_rejected(self):
        with self.assertRaises(ValueError):
            module.verify(self.repo, self.before, self.before)

    def test_bad_revision_fails_closed(self):
        result = subprocess.run(["python3", str(HELPER), "--repo", str(self.repo), "--", "--output=oops", "HEAD"], capture_output=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn(b"cannot verify", result.stderr)
        self.assertFalse((self.repo / "oops").exists())


if __name__ == "__main__":
    unittest.main()
