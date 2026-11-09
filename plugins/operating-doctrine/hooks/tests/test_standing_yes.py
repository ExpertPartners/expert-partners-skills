import json
import subprocess
import sys
import unittest
from pathlib import Path

HOOK = Path(__file__).resolve().parents[1] / "standing_yes.py"


class StandingYes(unittest.TestCase):
    def test_prints_session_start_context_with_the_floor(self):
        out = subprocess.run([sys.executable, str(HOOK)], capture_output=True, text=True, check=True).stdout
        specific = json.loads(out)["hookSpecificOutput"]
        self.assertEqual(specific["hookEventName"], "SessionStart")
        self.assertIn("Her brief is the go", specific["additionalContext"])
        self.assertIn("Friction Floor", specific["additionalContext"])

    def test_hooks_json_registers_it(self):
        hooks = json.loads((HOOK.parent / "hooks.json").read_text())
        commands = [h["command"] for entry in hooks["hooks"]["SessionStart"] for h in entry["hooks"]]
        self.assertTrue(any("standing_yes.py" in c for c in commands))


if __name__ == "__main__":
    unittest.main()
