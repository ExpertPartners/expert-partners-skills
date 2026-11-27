import importlib.util
import pathlib
import unittest

spec = importlib.util.spec_from_file_location(
    "preflight", pathlib.Path(__file__).parents[1] / "work-preflight.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class WorkPreflightTests(unittest.TestCase):
    def setUp(self):
        self.policy = {
            "items": [
                {
                    "id": "lesson",
                    "aliases": ["Build 101", "capstone homework"],
                    "sourceRecovery": "closed",
                    "installed": True,
                    "replacementApproved": True,
                    "ownerSession": "owner",
                }
            ]
        }

    def test_source_tools_and_shell_reopen_are_blocked(self):
        for tool, args in [
            ("web__run", {"query": "capstone homework original"}),
            ("Execute", {"command": "search 'Build 101 original videos'"}),
        ]:
            self.assertEqual(
                module.check(self.policy, {"tool_name": tool, "tool_input": args})[0],
                "SOURCE_RECOVERY_CLOSED",
            )

    def test_duplicate_dispatch_is_blocked(self):
        result = module.check(
            self.policy,
            {
                "tool_name": "post_message",
                "tool_input": {"text": "Commission Build 101 lesson"},
            },
        )
        self.assertEqual(result[0], "CAPABILITY_EXISTS")

    def test_inspection_and_existing_work_are_usable(self):
        self.assertIsNone(
            module.check(
                self.policy,
                {
                    "tool_name": "post_message",
                    "tool_input": {
                        "text": "Controlled live results passed for capstone homework and Build 101; duplicate Auditor commission routed to owner"
                    },
                },
            )
        )
        self.assertIsNone(
            module.check(
                self.policy,
                {
                    "tool_name": "Execute",
                    "tool_input": {"command": "rg 'Build 101' existing-records"},
                },
            )
        )
        self.assertIsNone(
            module.check(
                self.policy,
                {
                    "tool_name": "post_message",
                    "tool_input": {
                        "text": "No Build 101 search. Continue the existing replacement."
                    },
                },
            )
        )
        self.assertIsNone(
            module.check(
                self.policy,
                {
                    "tool_name": "post_message",
                    "tool_input": {
                        "sessionId": "owner",
                        "workIntent": {"action": "continue", "capabilityId": "lesson"},
                    },
                },
            )
        )


if __name__ == "__main__":
    unittest.main()
