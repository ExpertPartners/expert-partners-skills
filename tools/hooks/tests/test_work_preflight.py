import importlib.util
import pathlib
import io
import json
import os
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "preflight", pathlib.Path(__file__).parents[1] / "work-preflight.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
context_spec = importlib.util.spec_from_file_location(
    "preflight_context", pathlib.Path(__file__).parents[1] / "work-preflight-context.py"
)
context_module = importlib.util.module_from_spec(context_spec)
context_spec.loader.exec_module(context_module)
client_module = context_module.load_client()


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

    def test_ordinary_closed_recovery_prompt_blocks_an_unscoped_native_drive_search(self):
        closed = context_module.closed_searches(
            self.policy, "Find the original capstone homework and build a replacement."
        )
        self.assertEqual(closed, ["lesson"])
        result = module.check(
            self.policy,
            {
                "tool_name": "mcp__drive__list_files",
                "tool_input": {"query": "name contains 'homework'"},
                "closedSearches": closed,
            },
        )
        self.assertEqual(result[0], "SOURCE_RECOVERY_CLOSED")
        self.assertIsNone(
            module.check(
                self.policy,
                {
                    "tool_name": "mcp__drive__list_files",
                    "tool_input": {"query": "'existing-folder' in parents"},
                    "closedSearches": closed,
                },
            )
        )

    def test_negative_receipt_does_not_turn_continuation_into_source_recovery(self):
        self.assertEqual(
            context_module.closed_searches(
                self.policy,
                "Do not search the original capstone homework. Continue existing approved implementation.",
            ),
            [],
        )

    def test_background_host_uses_existing_login_bootstrap_for_credential_reference(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.dict(os.environ, {"HOME": directory}),
        ):
            root = pathlib.Path(directory) / ".config/expert-partners"
            root.mkdir(parents=True)
            (root / "work-preflight-client.json").write_text(
                json.dumps(
                    {
                        "endpoint": "https://example.com/api/tools/work_preflight",
                        "credentialItem": "reference",
                        "vault": "vault-reference",
                    }
                )
            )
            policy = {
                "version": 1,
                "source": {"revision": "current"},
                "items": [{"id": "existing"}],
                "checks": [
                    {"stage": name}
                    for name in ["company_tool_builder", "skills_marketplace", "gap_build_list"]
                ],
            }
            with (
                patch.object(client_module.subprocess, "run") as process,
                patch.object(client_module.urllib.request, "urlopen") as request,
            ):
                process.return_value.stdout = json.dumps(
                    {"fields": [{"id": "credential", "value": "test-only-token"}]}
                )
                request.return_value = io.StringIO(json.dumps({"result": {"policy": policy}}))
                self.assertEqual(client_module.refresh(), policy)
                self.assertEqual(process.call_args.args[0][:3], ["/bin/zsh", "-lc", 'exec "$@"'])
                self.assertEqual(
                    json.loads((root / "work-preflight-policy.json").read_text()), policy
                )

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
