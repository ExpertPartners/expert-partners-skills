import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[3]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


hook = load("native_save", ROOT / "hooks/native_save.py")
fmt = load(
    "format_native_doc", Path(__file__).resolve().parents[1] / "scripts/format_native_doc.py"
)
NAME = "[HQ-Operations][V1.0] Synthetic Save"
URL = "https://docs.google.com/document/d/synthetic/edit"
POLICY = (
    "Document formatting. Line spacing is 1.5. 12 points after each body paragraph, "
    "headings take 18 points above and 6 points below. Bullet and numbered items take 6 "
    "points after, and the last item in a list takes 12 points. Poppins throughout, "
    "at Title 22, Heading 1 17, Heading 2 13, and body 11. Brand Blue #2757CF.\n"
)


def paragraph(text, start=1, style="NORMAL_TEXT"):
    return {
        "startIndex": start,
        "endIndex": start + fmt.utf16(text),
        "paragraph": {
            "paragraphStyle": {"namedStyleType": style},
            "elements": [{"textRun": {"content": text}}],
        },
    }


def doc(*items):
    return {"revisionId": "revision", "body": {"content": list(items)}}


def message(role, content, **extra):
    return {"role": role, "content": content, **extra}


def call(name, value, result='exit 0\n{"documentId":"synthetic"}\n', key="call"):
    return [
        message(
            "assistant",
            [{"type": "tool_use", "id": key, "name": name, "input": value}],
            visibility="user_only",
        ),
        message(
            "user",
            [{"type": "tool_result", "tool_use_id": key, "content": result}],
            visibility="user_only",
        ),
    ]


def skills():
    rows = []
    for name in hook.SKILLS:
        path = ROOT / "skills" / name / "SKILL.md"
        rows += call(
            "Skill", {"skill": name}, f'Skill "{name}" is now active. filePath="{path}"', name
        )
    return rows


def prose(text):
    return message("assistant", [{"type": "text", "text": text}])


WRITE = {
    "command": "u='https://docs.googleapis.com/v1/documents/synthetic'; call(u+':batchUpdate',method='POST')"
}
FORMAT = {
    "command": f"python3 {hook.FORMATTER} --document-id synthetic --name '{NAME}' --parent-id home --rulebook-id authority --subject authorized --adapter /existing/server.py"
}
RECEIPT = (
    "exit 0\n"
    + hook.MARKER
    + json.dumps(
        {
            "verified": True,
            "document_id": "synthetic",
            "name": NAME,
            "url": URL,
            "revision": "native-revision",
            "parents": ["home"],
            "native_sha256": "native-hash",
            "content_sha256": "text-hash",
        }
    )
    + "\n"
)


class HookTests(unittest.TestCase):
    def check(self, rows, kind="Stop", **extra):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "session.jsonl"
            path.write_text(
                "".join(json.dumps({"type": "message", "message": x}) + "\n" for x in rows)
            )
            event = {"hook_event_name": kind, "transcript_path": str(path), **extra}
            return hook.check(event, recheck=lambda receipt, args: None)

    def test_prompt_loads_existing_canonical_procedures(self):
        result = hook.check({"hook_event_name": "UserPromptSubmit", "prompt": "Save this note"})
        self.assertIn("document-formatting-standard", json.dumps(result))
        self.assertEqual(
            {}, hook.check({"hook_event_name": "UserPromptSubmit", "prompt": "Explain a function"})
        )

    def test_actual_first_failure_blocked_before_write(self):
        result = self.check([], "PreToolUse", tool_name="Execute", tool_input=WRITE)
        self.assertEqual("deny", result["hookSpecificOutput"]["permissionDecision"])
        self.assertIn("deliverable-link", json.dumps(result))

    def test_formatter_cannot_be_a_shell_echo_or_untrusted_copy(self):
        for command in [
            FORMAT["command"] + "; echo fake",
            FORMAT["command"].replace(hook.FORMATTER, "/tmp/format_native_doc.py"),
        ]:
            result = self.check(
                skills(), "PreToolUse", tool_name="Execute", tool_input={"command": command}
            )
            self.assertEqual("deny", result["hookSpecificOutput"]["permissionDecision"])

    def test_legacy_skill_name_is_not_canonical_load(self):
        rows = call(
            "Skill", {"skill": "document-formatting-standard"}, 'is now active /legacy/SKILL.md'
        )
        self.assertNotIn("document-formatting-standard", hook.evidence(rows)[0])

    def test_loaded_skills_without_announcement_blocked(self):
        result = self.check(skills(), "PreToolUse", tool_name="Execute", tool_input=WRITE)
        self.assertIn("Announce", json.dumps(result))

    def test_nested_execute_with_real_prewrite_announcement_allowed(self):
        rows = skills() + [prose(f"I’ll save {NAME} in HQ Operations.")]
        self.assertEqual({}, self.check(rows, "PreToolUse", tool_name="Execute", tool_input=WRITE))

    def test_reads_and_unrelated_commands_do_not_require_save(self):
        self.assertFalse(
            hook.is_write(
                "Execute", {"command": "call('https://docs.googleapis.com/v1/documents/synthetic')"}
            )
        )
        self.assertEqual({}, self.check([], "PreToolUse", tool_name="Read", tool_input={}))

    def test_missing_title_verification_blocks_stop(self):
        self.assertIn("no successful formatting", self.check(call("Execute", WRITE))["reason"])

    def test_actual_second_generic_caption_blocked(self):
        rows = (
            call("Execute", WRITE)
            + call("Execute", FORMAT, RECEIPT, "format")
            + [prose(f"Updated [existing TEST Doc]({URL}).")]
        )
        self.assertIn(f"[{NAME}]({URL})", self.check(rows)["reason"])

    def test_exact_caption_after_success_passes(self):
        rows = call("Execute", FORMAT, RECEIPT) + [prose(f"Saved [{NAME}]({URL}).")]
        self.assertEqual({}, self.check(rows))

    def test_later_content_write_invalidates_prior_receipt(self):
        rows = (
            call("Execute", FORMAT, RECEIPT)
            + call("Execute", WRITE, key="second")
            + [prose(f"Saved [{NAME}]({URL}).")]
        )
        self.assertIn("no successful formatting", self.check(rows)["reason"])

    def test_wrong_document_receipt_does_not_cover_actual_write(self):
        rows = call("Execute", WRITE, 'exit 0\n{"documentId":"different"}\n')
        rows += call("Execute", FORMAT, RECEIPT, "formatter") + [prose(f"[{NAME}]({URL})")]
        self.assertIn("no successful formatting", self.check(rows)["reason"])

    def test_final_native_revision_is_rechecked_not_just_a_timestamp(self):
        rows = call("Execute", FORMAT, RECEIPT) + [prose(f"[{NAME}]({URL})")]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "session.jsonl"
            path.write_text("".join(json.dumps({"message": m}) + "\n" for m in rows))

            def changed(receipt, args):
                raise ValueError("native revision changed")

            result = hook.check(
                {"hook_event_name": "Stop", "transcript_path": str(path)}, recheck=changed
            )
            self.assertIn("revision/content changed", result["reason"])

    def test_failed_or_forged_formatter_output_is_not_a_pass(self):
        rows = call("Execute", WRITE) + call(
            "Execute", FORMAT, RECEIPT.replace("exit 0", "exit 1"), "format"
        )
        self.assertTrue(self.check(rows))
        rows = call("Execute", WRITE) + [prose(RECEIPT)]
        self.assertTrue(self.check(rows))

    def test_new_user_turn_keeps_skills_not_old_announcement_or_receipt(self):
        rows = (
            skills()
            + [prose("I’ll save this in HQ Operations.")]
            + call("Execute", FORMAT, RECEIPT)
        )
        rows += [message("user", [{"type": "text", "text": "Update and save the same subject"}])]
        result = self.check(rows, "PreToolUse", tool_name="Execute", tool_input=WRITE)
        self.assertIn("Announce", json.dumps(result))
        self.assertEqual({}, self.check(rows))

    def test_repeat_stop_never_waives_missing_verification(self):
        self.assertEqual(
            "block", self.check(call("Execute", WRITE), stop_hook_active=True)["decision"]
        )

    def test_fixture_content_cannot_be_an_assistant_announcement(self):
        rows = skills() + [
            message("user", [{"type": "text", "text": "I will save this to HQ Operations"}])
        ]
        self.assertIn(
            "Announce",
            json.dumps(self.check(rows, "PreToolUse", tool_name="Execute", tool_input=WRITE)),
        )


class FormattingTests(unittest.TestCase):
    def test_reads_policy_values_not_remembered_numbers(self):
        spec = fmt.policy(POLICY.replace("Title 22", "Title 24").replace("1.5", "1.6"))
        self.assertEqual(24, spec["sizes"]["TITLE"])
        self.assertEqual(160, spec["line"])
        with self.assertRaises(ValueError):
            fmt.policy("No supported current formatting policy")

    def test_missing_title_inserts_subject_without_overwriting_text(self):
        original = doc(paragraph("Count is 17.\n"))
        before = copy.deepcopy(original)
        result = fmt.preparation(original, NAME)
        self.assertEqual("Synthetic Save\n", result[0]["insertText"]["text"])
        self.assertEqual(before, original)

    def test_existing_title_text_is_retained(self):
        original = doc(
            paragraph("A deliberate title\n", style="TITLE"), paragraph("Count is 23.\n", 20)
        )
        self.assertEqual([], fmt.preparation(original, NAME))
        requests = fmt.style_requests(original, fmt.policy(POLICY), NAME)
        self.assertEqual(22, requests[1]["updateTextStyle"]["textStyle"]["fontSize"]["magnitude"])
        self.assertEqual(11, requests[3]["updateTextStyle"]["textStyle"]["fontSize"]["magnitude"])

    def test_plain_subject_is_promoted_without_duplicate(self):
        self.assertEqual([], fmt.preparation(doc(paragraph("Synthetic Save\n")), NAME))

    def test_empty_spacers_removed_backwards_but_final_newline_kept(self):
        original = doc(
            paragraph("Synthetic Save\n"),
            paragraph("\n", 16),
            paragraph("Body\n", 17),
            paragraph("\n", 22),
        )
        result = fmt.preparation(original, NAME)
        self.assertEqual(
            [{"deleteContentRange": {"range": {"startIndex": 16, "endIndex": 17}}}], result
        )

    def test_unicode_range_uses_utf16(self):
        self.assertEqual(3, fmt.utf16("A😀"))

    def test_special_layouts_refuse_before_flattening(self):
        with self.assertRaises(ValueError):
            fmt.paragraphs({"body": {"content": [{"table": {}}]}})
        with self.assertRaises(ValueError):
            fmt.paragraphs({"tabs": [{}, {}]})
        bulleted = doc(paragraph("Bullet\n"))
        bulleted["body"]["content"][0]["paragraph"]["bullet"] = {"listId": "list"}
        with self.assertRaises(ValueError):
            fmt.paragraphs(bulleted)

    def test_native_spacing_mismatch_fails(self):
        with self.assertRaisesRegex(ValueError, "spacing"):
            fmt.verify_native(
                doc(paragraph("Synthetic Save\n", style="TITLE")), fmt.policy(POLICY), NAME
            )

    def test_native_zero_dimension_omission_is_not_a_mismatch(self):
        document = doc(paragraph("Synthetic Save\n", style="TITLE"), paragraph("Body\n", 16))
        for request in fmt.style_requests(document, fmt.policy(POLICY), NAME):
            if "updateParagraphStyle" in request:
                update = request["updateParagraphStyle"]
                item = next(
                    x
                    for x in fmt.paragraphs(document)
                    if x["startIndex"] == update["range"]["startIndex"]
                )
                item["paragraph"]["paragraphStyle"] = copy.deepcopy(update["paragraphStyle"])
        document["body"]["content"][1]["paragraph"]["paragraphStyle"]["spaceAbove"] = {"unit": "PT"}
        fmt.verify_native(document, fmt.policy(POLICY), NAME)

    def test_hyperlinks_survive_native_run_splitting(self):
        original = doc(paragraph("Linked text\n"))
        original["body"]["content"][0]["paragraph"]["elements"][0]["textRun"]["textStyle"] = {
            "link": {"url": "https://example.test/"}
        }
        before = fmt.links_of(original)
        changed = copy.deepcopy(original)
        changed["body"]["content"][0]["paragraph"]["elements"] = [
            {"textRun": {"content": text, "textStyle": {"link": {"url": "https://example.test/"}}}}
            for text in ["Linked ", "text\n"]
        ]
        self.assertEqual(before, fmt.links_of(changed))
        self.assertTrue(
            all(
                "link" not in request.get("updateTextStyle", {}).get("fields", "")
                for request in fmt.style_requests(original, fmt.policy(POLICY), NAME)
            )
        )

    def pdf(self, spans, document, matrix=None):
        class Page:
            def get(self, key, default):
                return default

            def extract_text(self, visitor_text):
                for text, font, size in spans:
                    visitor_text(
                        text,
                        matrix or [1, 0, 0, 1, 0, 0],
                        [1, 0, 0, -1, 0, 0],
                        {"/BaseFont": font},
                        size,
                    )

        fake = types.SimpleNamespace(PdfReader=lambda _: types.SimpleNamespace(pages=[Page()]))
        with patch.dict(sys.modules, {"pypdf": fake}):
            fmt.verify_pdf(b"native export", document, fmt.policy(POLICY))

    def test_native_pdf_text_space_size_is_transformed_to_points(self):
        document = doc(paragraph("Synthetic Save\n", style="TITLE"), paragraph("Count 23\n", 16))
        self.pdf(
            [
                ("Synthetic Save", "Poppins-Regular", 29.333334),
                ("Count 23", "Poppins-Regular", 14.666667),
            ],
            document,
            [0.75, 0, 0, -0.75, 72, 720],
        )

    def test_omitted_native_body_size_needs_rendered_evidence(self):
        document = doc(paragraph("Synthetic Save\n", style="TITLE"), paragraph("Count 23\n", 16))
        self.pdf(
            [("Synthetic Save", "Poppins-Regular", 22), ("Count 23", "Poppins-Regular", 11)],
            document,
        )
        for font, size in [("Arial", 11), ("Poppins-Regular", 12), ("Poppins-Bold", 11)]:
            with self.assertRaises(ValueError):
                self.pdf(
                    [("Synthetic Save", "Poppins-Regular", 22), ("Count 23", font, size)], document
                )

    def test_missing_rendered_title_or_wrong_text_fails(self):
        document = doc(paragraph("Synthetic Save\n", style="TITLE"), paragraph("Count 23\n", 16))
        with self.assertRaises(ValueError):
            self.pdf([("Count 23", "Poppins-Regular", 11)], document)
        with self.assertRaises(ValueError):
            self.pdf([("Synthetic SaveCount 17", "Poppins-Regular", 11)], document)


class ReviewRegressionTests(unittest.TestCase):
    check = HookTests.check

    def test_file_metadata_and_json_artifacts_are_not_native_document_content(self):
        for command in [
            "api.call('PATCH','https://www.googleapis.com/drive/v3/files/synthetic',json={'trashed':True})",
            "api.call('PATCH','https://www.googleapis.com/drive/v3/files/synthetic',json={'name':'Existing name'})",
            "api.call('PATCH','https://www.googleapis.com/upload/drive/v3/files/proof?uploadType=media',headers={'Content-Type':'application/json'},data='{}')",
        ]:
            for name in ["Execute", "Bash"]:
                self.assertFalse(hook.is_write(name, {"command": command}))
                self.assertEqual(
                    {},
                    self.check([], "PreToolUse", tool_name=name, tool_input={"command": command}),
                )
        html = "api.call('PATCH','https://www.googleapis.com/upload/drive/v3/files/synthetic?uploadType=media',headers={'Content-Type':'text/html'},data='<p>Count</p>')"
        self.assertTrue(hook.is_write("Execute", {"command": html}))
        self.assertTrue(hook.is_write("Execute", WRITE))

    def test_docs_create_query_and_json_proof_content_have_distinct_transports(self):
        url = "https://docs.googleapis.com/v1/documents?fields=documentId,title"
        for name in ["Execute", "Bash"]:
            self.assertTrue(
                hook.is_write(
                    name, {"command": f"api.call('POST','{url}',json={{'title':'Native'}})"}
                )
            )
        self.assertTrue(
            hook.is_write(
                "mcp__google_workspace__google_api",
                {"method": "POST", "url": url, "body": {"title": "Native"}},
            )
        )
        proof = {
            "documentId": "synthetic",
            "source": {"mimeType": "application/vnd.google-apps.document"},
        }
        for name in ["app.google_drive.upload_file", "app.google_drive.update_file_content"]:
            self.assertFalse(
                hook.is_write(
                    name,
                    {
                        "input": {
                            "file_id": "proof",
                            "content_mime_type": "application/json",
                            "content": json.dumps(proof),
                        }
                    },
                )
            )
        command = (
            "api.call('PATCH','https://www.googleapis.com/upload/drive/v3/files/proof?uploadType=media',headers={'Content-Type':'application/json'},json="
            + repr(proof)
            + ")"
        )
        self.assertFalse(hook.is_write("Execute", {"command": command}))
        self.assertTrue(hook.is_write("Execute", {"command": WRITE["command"] + "; " + command}))
        self.assertTrue(hook.is_write("Execute", {"command": command + "; " + FORMAT["command"]}))
        html = "api.call('PATCH','https://www.googleapis.com/upload/drive/v3/files/synthetic?uploadType=media',headers={'Content-Type':'text/html'},data='<p>Count</p>')"
        self.assertTrue(hook.is_write("Execute", {"command": command + "; " + html}))

    def test_real_native_google_write_shapes_are_detected(self):
        shapes = [
            (
                "app.google_drive.update_file_content",
                {
                    "input": {
                        "file_id": "synthetic",
                        "content_mime_type": "text/html",
                        "content": "<p>Count 17</p>",
                    }
                },
            ),
            (
                "app.google_drive.upload_file",
                {"input": {"content_mime_type": "text/html", "content": "<p>Count 17</p>"}},
            ),
            (
                "mcp__google_workspace__google_api",
                {
                    "method": "POST",
                    "url": "https://docs.googleapis.com/v1/documents/synthetic:batchUpdate",
                    "body": {"requests": []},
                },
            ),
        ]
        for name, value in shapes:
            with self.subTest(name=name):
                self.assertTrue(hook.is_write(name, value))
                result = self.check([], "PreToolUse", tool_name=name, tool_input=value)
                self.assertEqual("deny", result["hookSpecificOutput"]["permissionDecision"])

    def test_drive_id_response_and_bash_formatter_can_finish(self):
        value = {
            "input": {
                "file_id": "synthetic",
                "content_mime_type": "text/html",
                "content": "<p>Count</p>",
            }
        }
        rows = call("app.google_drive.update_file_content", value, json.dumps({"id": "synthetic"}))
        self.assertEqual({"synthetic"}, hook.evidence(rows)[1][0][1])
        rows += call("Bash", FORMAT, RECEIPT, "formatter") + [prose(f"Saved [{NAME}]({URL}).")]
        self.assertEqual({}, self.check(rows))

    def test_escaped_delegated_api_response_binds_actual_document(self):
        value = {
            "method": "POST",
            "url": "https://docs.googleapis.com/v1/documents/synthetic:batchUpdate",
            "body": {"requests": []},
        }
        result = json.dumps(
            {"status": 200, "response": json.dumps({"documentId": "synthetic", "replies": []})}
        )
        rows = call("mcp__google_workspace__google_api", value, result)
        self.assertEqual({"synthetic"}, hook.evidence(rows)[1][0][1])
        rows += call("Execute", FORMAT, RECEIPT, "formatter") + [prose(f"Saved [{NAME}]({URL}).")]
        self.assertEqual({}, self.check(rows))

    def test_negative_prose_is_not_a_destination_announcement(self):
        for text in [
            "I am not saving this to HQ Operations.",
            "I will not save this in HQ Operations.",
            "I won't save this to HQ Operations.",
        ]:
            result = self.check(
                skills() + [prose(text)], "PreToolUse", tool_name="Execute", tool_input=WRITE
            )
            self.assertIn("Announce", json.dumps(result))

    def test_repeated_invalid_stop_is_not_a_delivery_pass(self):
        rows = call("Execute", FORMAT, RECEIPT) + [prose(f"Updated [existing TEST Doc]({URL}).")]
        self.assertEqual("block", self.check(rows, stop_hook_active=True)["decision"])
        rows += [prose(f"Saved [{NAME}]({URL}).")]
        self.assertEqual({}, self.check(rows, stop_hook_active=True))

    def test_first_unsupported_named_style_refuses_before_preparation(self):
        for named in ["HEADING_3", "SUBTITLE"]:
            with self.assertRaises(ValueError):
                fmt.style_requests(
                    doc(paragraph("Existing wording\n", style=named)), fmt.policy(POLICY), NAME
                )

    def test_identical_words_do_not_hide_moved_hyperlinks(self):
        original = doc(paragraph("X X\n"))
        original["body"]["content"][0]["paragraph"]["elements"] = [
            {
                "textRun": {
                    "content": "X",
                    "textStyle": {"link": {"url": "https://example.test/first"}},
                }
            },
            {"textRun": {"content": " X\n", "textStyle": {}}},
        ]
        changed = copy.deepcopy(original)
        changed["body"]["content"][0]["paragraph"]["elements"] = [
            {"textRun": {"content": "X ", "textStyle": {}}},
            {
                "textRun": {
                    "content": "X",
                    "textStyle": {"link": {"url": "https://example.test/first"}},
                }
            },
            {"textRun": {"content": "\n", "textStyle": {}}},
        ]
        self.assertNotEqual(fmt.links_of(original), fmt.links_of(changed))

    class API:
        def __init__(self, layout=None, flip=None):
            self.layout = layout
            self.flip = flip
            self.writes = []
            self.reads = []
            self.meta_reads = 0

        def request(self, url, *args):
            return POLICY

        def json(self, url, method="GET", body=None):
            self.reads.append(url)
            if method == "POST":
                self.writes.append(body)
                return {"documentId": "synthetic"}
            if urlsplit(url).hostname == "docs.googleapis.com":
                base = doc(paragraph("Synthetic Save\n", style="TITLE"), paragraph("Body\n", 16))
                base["documentId"] = "synthetic"
                base["documentStyle"] = {
                    "pageSize": {
                        "width": {"magnitude": 612, "unit": "PT"},
                        "height": {"magnitude": 792, "unit": "PT"},
                    }
                }
                if self.layout == "tabs" and "includeTabsContent=true" in url:
                    base["tabs"] = [
                        {"documentTab": {"body": copy.deepcopy(base["body"])}},
                        {"documentTab": {"body": copy.deepcopy(base["body"])}},
                    ]
                if self.layout == "header":
                    base["headers"] = {"h": {"content": [paragraph("Header\n")]}}
                if self.layout == "card":
                    base["documentStyle"]["pageSize"] = {
                        "width": {"magnitude": 288, "unit": "PT"},
                        "height": {"magnitude": 432, "unit": "PT"},
                    }
                return base
            meta = {
                "id": "synthetic",
                "name": NAME,
                "parents": ["home"],
                "mimeType": "application/vnd.google-apps.document",
                "trashed": False,
                "version": "1",
            }
            if "/authority" not in url:
                self.meta_reads += 1
                if self.meta_reads > 1 and self.flip:
                    meta.update(self.flip)
            return meta

        def pdf(self, document_id):
            return b"unsupported fixture pdf"

    def test_real_complete_layout_refusals_precede_every_write(self):
        for layout in ["tabs", "header", "card"]:
            api = self.API(layout=layout)
            with self.subTest(layout=layout):
                with self.assertRaises(ValueError):
                    fmt.format_doc(api, "synthetic", "authority", NAME, "home")
                self.assertEqual([], api.writes)

    def test_final_identity_is_rechecked_before_verified_receipt(self):
        for change in [{"trashed": True}, {"id": "different"}, {"mimeType": "application/pdf"}]:
            api = self.API(flip=change)
            with patch.object(fmt, "verify_native"), patch.object(fmt, "verify_pdf"):
                with self.subTest(change=change), self.assertRaises(ValueError):
                    fmt.format_doc(api, "synthetic", "authority", NAME, "home")

    def test_external_title_insertion_cannot_be_attributed_to_the_formatter(self):
        class Changed(self.API):
            def json(self, url, method="GET", body=None):
                result = super().json(url, method, body)
                if (
                    method == "GET"
                    and urlsplit(url).hostname == "docs.googleapis.com"
                    and self.writes
                ):
                    result["body"]["content"] = [
                        paragraph("Synthetic Save\n", 1, "TITLE"),
                        paragraph("Synthetic Save\n", 16, "TITLE"),
                        paragraph("Body\n", 31),
                    ]
                return result

        api = Changed()
        with patch.object(fmt, "verify_native"), patch.object(fmt, "verify_pdf"):
            with self.assertRaisesRegex(ValueError, "wording"):
                fmt.format_doc(api, "synthetic", "authority", NAME, "home")
        self.assertFalse(any("insertText" in r for write in api.writes for r in write["requests"]))

    def test_malformed_receipt_returns_a_structured_block(self):
        raw = json.loads(RECEIPT.split(hook.MARKER)[1])
        for receipt in [{k: v for k, v in raw.items() if k != "url"}, [], {**raw, "parents": None}]:
            body = "exit 0\n" + hook.MARKER + json.dumps(receipt) + "\n"
            rows = call("Execute", FORMAT, body) + [prose(f"Saved [{NAME}]({URL}).")]
            self.assertEqual("block", self.check(rows)["decision"])

    def test_actual_api_failure_does_not_poison_a_later_same_doc_recovery(self):
        value = {
            "method": "POST",
            "url": "https://docs.googleapis.com/v1/documents/synthetic:batchUpdate",
            "body": {"requests": []},
        }
        rows = call(
            "mcp__google_workspace__google_api",
            value,
            json.dumps({"status": 400, "response": "invalid request"}),
            "failed",
        )
        self.assertEqual([], hook.evidence(rows)[1])
        rows += call(
            "mcp__google_workspace__google_api",
            value,
            json.dumps({"status": 200, "response": json.dumps({"documentId": "synthetic"})}),
            "retried",
        )
        rows += call("Execute", FORMAT, RECEIPT, "formatter") + [prose(f"Saved [{NAME}]({URL}).")]
        self.assertEqual({}, self.check(rows))
        unknown = call(
            "mcp__google_workspace__google_api",
            value,
            json.dumps({"status": 502, "response": "outcome uncertain"}),
            "uncertain",
        )
        self.assertEqual({"synthetic"}, hook.evidence(unknown)[1][0][1])
        self.assertEqual("block", self.check(unknown)["decision"])
        unknown += call("Execute", FORMAT, RECEIPT, "formatter") + [
            prose(f"Saved [{NAME}]({URL}).")
        ]
        self.assertEqual({}, self.check(unknown))

    def test_h2_effective_color_is_checked_after_native_readback(self):
        document = doc(
            paragraph("Synthetic Save\n", style="TITLE"), paragraph("Heading\n", 16, "HEADING_2")
        )
        for request in fmt.style_requests(document, fmt.policy(POLICY), NAME):
            if "updateParagraphStyle" in request:
                u = request["updateParagraphStyle"]
                p = next(
                    x
                    for x in fmt.paragraphs(document)
                    if x["startIndex"] == u["range"]["startIndex"]
                )
                p["paragraph"]["paragraphStyle"] = copy.deepcopy(u["paragraphStyle"])
        with self.assertRaisesRegex(ValueError, "color"):
            fmt.verify_native(document, fmt.policy(POLICY), NAME)


class ConnectorEvidenceTests(unittest.TestCase):
    check = HookTests.check

    def test_actual_formatter_file_inspection_is_not_a_native_write(self):
        for command in [
            "ls /tmp/format_native_doc.py",
            "test -f /tmp/format_native_doc.py",
            "cat /tmp/format_native_doc.py",
            f"ls -l '{hook.FORMATTER}'",
        ]:
            for name in ["Bash", "Execute"]:
                with self.subTest(command=command, name=name):
                    self.assertFalse(hook.is_write(name, {"command": command}))
                    self.assertEqual(
                        {},
                        hook.check(
                            {
                                "hook_event_name": "PreToolUse",
                                "tool_name": name,
                                "tool_input": {"command": command},
                            }
                        ),
                    )

    def test_formatter_execution_and_compound_writes_still_require_the_guard(self):
        for command in [
            FORMAT["command"],
            FORMAT["command"].replace(hook.FORMATTER, "/tmp/format_native_doc.py"),
            "ls /tmp/format_native_doc.py && " + FORMAT["command"],
            "test -f /tmp/format_native_doc.py; " + WRITE["command"],
            'cat "$(python3 /tmp/format_native_doc.py)"',
            "python3 /tmp/format_native_doc.py --help; python3 /tmp/format_native_doc.py --document-id x",
        ]:
            with self.subTest(command=command):
                self.assertTrue(hook.is_write("Bash", {"command": command}))

    def test_metadata_only_and_malformed_conversation_never_establish_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "session.jsonl"
            for row in [
                {},
                {"type": "system", "subtype": "init"},
                {"type": "message", "message": {"role": "assistant", "content": [None]}},
                {"type": "message", "message": {"role": "assistant", "content": []}},
                {
                    "type": "message",
                    "message": {"role": "assistant", "content": [{"type": "tool_use"}]},
                },
            ]:
                with self.subTest(row=row):
                    path.write_text(json.dumps(row) + "\n")
                    result = hook.check({"hook_event_name": "Stop", "transcript_path": str(path)})
                    self.assertEqual("block", result["decision"])
                    self.assertIn("unverified", result["reason"].lower())

    def test_real_messages_preserve_harmless_metadata_and_normalize_string_content(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "session.jsonl"
            rows = [
                {"type": "system", "subtype": "init"},
                {"type": "message", "message": {"role": "user", "content": "Explain this."}},
                {
                    "type": "message",
                    "message": {"role": "assistant", "content": "Here is the explanation."},
                },
            ]
            path.write_text("".join(json.dumps(row) + "\n" for row in rows))
            messages = hook.records(path)
            self.assertEqual(2, len(messages))
            self.assertEqual([{"type": "text", "text": "Explain this."}], messages[0]["content"])
            self.assertEqual(
                {}, hook.check({"hook_event_name": "Stop", "transcript_path": str(path)})
            )

    def test_actual_connector_writes_require_procedures_and_bind_native_targets(self):
        cases = [
            (
                "mcp__Google_Docs__update_doc",
                {
                    "documentId": "synthetic",
                    "requests": [{"insertText": {"location": {"index": 1}, "text": "TEST"}}],
                },
                '{"replies":[{"errors":[],"api_replies":[{}]}],"writeControl":{"requiredRevisionId":"saved"}}',
            ),
            (
                "mcp__Google_Drive__create_file",
                {
                    "contentMimeType": "application/vnd.google-apps.document",
                    "parentId": "home",
                    "title": NAME,
                },
                '{"id":"synthetic","mimeType":"application/vnd.google-apps.document","parentId":"home"}',
            ),
        ]
        for name, value, response in cases:
            with self.subTest(name=name):
                self.assertTrue(hook.is_write(name, value))
                denied = self.check([], "PreToolUse", tool_name=name, tool_input=value)
                self.assertEqual("deny", denied["hookSpecificOutput"]["permissionDecision"])
                rows = skills() + [prose("I will save this in the existing company home.")]
                rows += call(name, value, response)
                self.assertEqual({"synthetic"}, hook.evidence(rows)[1][-1][1])
                self.assertEqual("block", self.check(rows)["decision"])
                rows += call("Execute", FORMAT, RECEIPT, "format")
                rows += [prose(f"[{NAME}]({URL})")]
                self.assertEqual({}, self.check(rows))

    def test_native_connector_inspection_metadata_and_json_proofs_stay_usable(self):
        for name, value in [
            ("mcp__Google_Docs__read_doc", {"documentId": "synthetic"}),
            ("mcp__Google_Drive__update_file", {"fileId": "synthetic", "title": "Existing"}),
            (
                "mcp__Google_Drive__create_file",
                {
                    "contentMimeType": "application/json",
                    "content": '{"documentId":"synthetic","mimeType":"application/vnd.google-apps.document"}',
                },
            ),
        ]:
            with self.subTest(name=name):
                self.assertFalse(hook.is_write(name, value))
                self.assertEqual(
                    {},
                    hook.check(
                        {"hook_event_name": "PreToolUse", "tool_name": name, "tool_input": value}
                    ),
                )

    def test_missing_or_unreadable_transcript_has_explicit_unverified_denial(self):
        with tempfile.TemporaryDirectory() as folder:
            broken = Path(folder) / "broken.jsonl"
            broken.write_text("not valid JSON\n")
            empty = Path(folder) / "empty.jsonl"
            empty.write_text("")
            for value in [
                None,
                "",
                str(Path(folder) / "missing.jsonl"),
                folder,
                str(broken),
                str(empty),
            ]:
                for repeated in [False, True]:
                    with self.subTest(path=value, repeated=repeated):
                        event = {"hook_event_name": "Stop", "stop_hook_active": repeated}
                        if value is not None:
                            event["transcript_path"] = value
                        result = hook.check(event)
                        self.assertEqual("block", result["decision"])
                        self.assertIn("unverified", result["reason"].lower())
                        self.assertIn("runtime", result["reason"].lower())
            result = hook.check(
                {
                    "hook_event_name": "PreToolUse",
                    "tool_name": "mcp__Google_Docs__update_doc",
                    "tool_input": {"documentId": "synthetic", "requests": []},
                }
            )
            self.assertEqual("deny", result["hookSpecificOutput"]["permissionDecision"])
            self.assertIn(
                "unverified", result["hookSpecificOutput"]["permissionDecisionReason"].lower()
            )


class SourceProjectionTests(unittest.TestCase):
    def test_actual_corrupt_closer_refuses_before_any_native_write(self):
        malformed = (
            'TODAY FAILURE TRACKER BEGIN v1\n{"schemaVersion":1,"rows":[]}\n'
            'TODAY FAILURE TRACKER ENDer handoff runner\n{"rows":[]}\n'
            'TODAY FAILURE TRACKER END\n'
        )

        class Broken(ReviewRegressionTests.API):
            def json(self, url, method="GET", body=None):
                value = super().json(url, method, body)
                if method == "GET" and urlsplit(url).hostname == "docs.googleapis.com":
                    value["body"]["content"][1] = paragraph(malformed, 16)
                return value

        api = Broken()
        with self.assertRaisesRegex(ValueError, "Malformed source projection"):
            fmt.format_doc(api, "synthetic", "authority", NAME, "home")
        self.assertEqual([], api.writes)

    def test_full_payload_and_both_exact_boundaries_are_required(self):
        good = 'TODAY FAILURE TRACKER BEGIN v1\n{"rows":[]}\nTODAY FAILURE TRACKER END\n'
        for text in [
            good + good,
            good.replace('END\n', 'END appended history\n'),
            good.replace('{"rows":[]}', '{"rows":[]}\n{"old":true}'),
            good.replace('BEGIN v1', 'BEGIN v2'),
            good.replace('{"rows":[]}', '{"value":NaN}'),
            good.replace('TODAY FAILURE TRACKER END\n', ''),
            'TODAY FAILURE TRACKER END\n',
        ]:
            with self.subTest(text=text), self.assertRaises(ValueError):
                fmt.source_projection_integrity(text)

    def test_valid_payloads_and_multiple_handoff_instances_remain_usable(self):
        text = 'Retained ordinary history.\nTODAY CHANGE LOG BEGIN v1\n{"rows":[]}\nTODAY CHANGE LOG END\n'
        text += 'HANDOFF REGISTER BEGIN v2\nroute_id | sender | receiver\nTEST | Sender | Receiver\nHANDOFF REGISTER END\n'
        text += 'HANDOFF INSTANCE BEGIN v2\nroute_id=TEST\ninstance_id=one\nHANDOFF INSTANCE END\n'
        text += 'HANDOFF INSTANCE BEGIN v2\nroute_id=TEST\ninstance_id=two\nHANDOFF INSTANCE END\n'
        proof = fmt.source_projection_integrity(text)
        self.assertEqual([1, 1, 2], [len(x["payload_sha256"]) for x in proof])
        self.assertEqual([], fmt.source_projection_integrity('Ordinary working note.\n'))


if __name__ == "__main__":
    unittest.main()
