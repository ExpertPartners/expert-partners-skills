# Factory Inbox

This bridge belongs to Factory Operator. It connects an explicitly authorized shared Drive folder to the documented [Factory Sessions API](https://docs.factory.com/api-reference/sessions.md). It is an execution adapter, not the retired Chat to Code job system.

## Send work

Find Factory Inbox at the root of HQ Business Brain. Create one Google Doc or UTF-8 `.txt` file directly in that folder with this exact plain text. Use a unique file name and Request value for each new instruction.

```text
Request: north-20261109-001
Session: new
Mac: M4
Prompt:
Do the requested work and report the result with links.
```

To message an existing session, replace `new` with its session UUID from a receipt. An archived session accepts a follow-up and needs no reopening. `M2` is also supported when configured. An optional `Directory: /absolute/path` header before `Prompt:` selects the working directory for a new session. Everything after `Prompt:` is the prompt, including multiple paragraphs. Do not wrap the request in Markdown fences inside the file. The bridge uses Auto Model and High autonomy for new sessions, leaving existing session settings unchanged.

Read `<Request>.json` in Receipts for the session ID, session link, message ID and submission status. `accepted` means Factory received the prompt, not that Factory finished the work. Read `<Request>-completion.json` for the finished result, which the session publishes itself when the work is done. The original request moves to Done only after its acceptance receipt is published. Neither API keys nor prompts appear in receipts.

For a revision, write a new Request ID. Reusing an ID with identical content does not send twice. Reusing it with different content is deferred, never silently treated as new work. Invalid or partially written requests stay in the inbox so they can be corrected.

## North in one paragraph

North, use your writable Google Drive action to create one plain Google Doc or UTF-8 text file directly in HQ Business Brain → Factory Inbox, with a unique name and the exact five-line format above, replacing Request with a fresh unique ID, Session with `new` or the existing session UUID, Mac with `M4` or `M2`, and the last line with the full prompt. This is one file-creation action with content, not an empty-file action followed by an edit. Do not use Markdown fences or send credentials. Then read the matching `<Request>.json` in Receipts for the session link and submission status, and `<Request>-completion.json` for the finished result. A read-only Drive search connection cannot submit work; use the already authorized writable action instead. No paste or session-start step belongs to Allison.

## Close-out and archiving

Every prompt the bridge submits carries a standing close-out instruction naming that session's own ID. When the work is finished the session runs it, which publishes `<Request>-completion.json` to Receipts and then archives that session. The order is enforced in code, so an unarchived session means the bookkeeping is unfinished. Submission never archives anything: the acceptance receipt is written before the work starts.

Archive state is the owning machine's session settings file, `~/.factory/sessions/<working directory>/<session ID>.settings.json`, and the close-out sets `archivedAt` there, keeping the rest of the file intact. The documented `sessionSettings.archivedAt` field on `PATCH /api/v0/sessions/{id}` returns 200 with the timestamp but does not persist it for this account, and `/archive` sent through the messages endpoint arrives as plain text rather than a command, both verified on November 9, 2026. Verify archiving against the settings file, not an API response.

## Why this design

The Control Room can write connected files and read `~/.factory`, and other chats can write Drive. The existing Google Drive for Desktop mount supplies one common folder. One macOS LaunchAgent scans that folder on filesystem changes and every 30 seconds to catch coalesced sync events. There is no inbound port, web service, new credential store or separate dispatcher. Google Docs sync as `.gdoc` pointers, not text, so the worker reads their `doc_id` and exports them through the official Drive API. It also reads synced text files through that API to avoid stale local content. This follows the requested integration design, not a claim that Cal taught this transport.

The worker ignores files not directly in the configured Drive folder, symlinks, folders, unsupported formats and ambiguous text-file names. Drive upload must finish before a local file is dispatched. Native Docs must sync their pointer before dispatch. The Mac must be awake, signed in, with Drive Desktop mounted and Factory Remote Control connected. End-to-end latency includes Drive sync, the 30-second scan and Factory execution.

## Install on the M4

Use [Remote Control](https://docs.factory.com/remote-control.md) and its documented `droid computer ssh` command for invisible installation. Never start a browser on the M4.

The installer copies canonical code and this guide into `~/.factory/session-inbox`, then installs `com.expertpartners.factory-inbox` in `~/Library/LaunchAgents`. Two symlinks expose the same synced folder as `~/HQ-AI-Workspace-M4/Factory Inbox` and `~/.factory/Factory Inbox`. Local receipt mirrors and the durable journal live in `~/.factory/session-inbox`.

Use a Python with [google-auth](https://google-auth.readthedocs.io/en/latest/reference/google.oauth2.service_account.html) and requests, as listed in `requirements.txt`. Reuse the existing machine environment when those versions are already installed. The Google service identity needs authorized Drive access and domain-wide delegation for the configured subject. Reuse existing authorization, do not widen sharing.

Write a private machine config outside the repository with the following fields. Resolve IDs from the live Drive folder and `droid computer list`, never from a copied business document.

```json
{
  "inbox_path": "/absolute/GoogleDrive/Shared drives/HQ Business Brain/Factory Inbox",
  "inbox_id": "LIVE_INBOX_FOLDER_ID",
  "done_id": "LIVE_DONE_FOLDER_ID",
  "receipts_id": "LIVE_RECEIPTS_FOLDER_ID",
  "state_path": "~/.factory/session-inbox",
  "op": "/opt/homebrew/bin/op",
  "factory_key_ref": "op://VAULT/FACTORY_ITEM/credential",
  "google_key_ref": "op://VAULT/GOOGLE_SERVICE_ACCOUNT_ITEM/credential",
  "google_subject": "AUTHORIZED_WORKSPACE_USER",
  "machines": {
    "M4": {"computer_id": "LIVE_M4_COMPUTER_ID", "cwd": "/absolute/M4/workspace"},
    "M2": {"computer_id": "LIVE_M2_COMPUTER_ID", "cwd": "/absolute/M2/workspace"}
  }
}
```

```sh
python3 tools/factory-inbox/install.py --config /absolute/private/config.json --python /absolute/python3
```

The LaunchAgent uses the Mac's existing `~/.zshenv` 1Password service-account bootstrap. `op read` resolves the Factory key and Google service-account JSON into process memory on each scan. The key is not stored in the config, plist, receipts, logs or source. The installer never creates a new token store.

## Delivery and recovery

An exclusive file lock serializes scans. A private, fsynced journal records progress before every non-idempotent Factory POST. A known created session is reused if the process stops before message submission. If a crash or transport error leaves a create/message POST outcome unknown, the receipt says `uncertain`. The worker does not resend it automatically because the Sessions API documents no idempotency key. Inspect that session's messages through the API and reconcile before issuing a new Request ID. This is duplicate prevention, not a founder approval gate.

Receipt publication and moving to Done can retry without resending the prompt. Receipt uploads use a preallocated Drive file ID, making upload retries safe. Local receipt mirrors are available even during a Drive publication outage. Deferred files log only a file ID and generic status. Secrets and raw provider responses are withheld.

Run a scan or inspect the service without touching any desktop UI.

```sh
python3 ~/.factory/session-inbox/bridge.py --config ~/.factory/session-inbox/config.json
launchctl print gui/$(id -u)/com.expertpartners.factory-inbox
```

## Tests

```sh
python3 -m unittest discover -s tools/factory-inbox/tests -v
```

The contract for a new bridge is the request format and expected receipts above. Unit checks cover new sessions, same-session messages, local text and native Doc pointers, identical duplicates, conflicting revisions, partial writes, machine mismatch, interrupted POSTs and publication recovery. Live acceptance uses a local synced file, a Drive API text upload and a native Doc containing exactly the plain-text North format, plus a follow-up message into an archived session. Acceptance receipts demonstrate submission. Completion receipts, the `archivedAt` value in each session's settings file, API message reads and session-created proof files demonstrate execution, close-out and archiving separately.
