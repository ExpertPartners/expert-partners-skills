#!/usr/bin/env python3
"""Drive Desktop inbox -> documented Factory Sessions API. No stored API keys."""

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import time
from urllib.parse import quote

MAX_BYTES = 128_000
DOC = "application/vnd.google-apps.document"
FACTORY = "https://api.factory.ai/api/v0"
DRIVE = "https://www.googleapis.com/drive/v3"


class BridgeError(Exception):
    """Safe to record, unlike raw HTTP responses or credential errors."""


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    with os.fdopen(os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w") as handle:
        json.dump(value, handle, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def parse_request(text, machines):
    """One format for a text file, a Google Doc, or a ChatGPT Drive action."""
    header, separator, prompt = text.replace("\r\n", "\n").partition("\nPrompt:\n")
    if not separator or not prompt.strip():
        raise BridgeError("Expected headers then a line containing Prompt: and a nonempty prompt.")
    fields = {}
    for line in header.splitlines():
        key, colon, value = line.partition(":")
        if not colon or key not in ("Request", "Session", "Mac", "Directory") or key in fields:
            raise BridgeError("Unknown, duplicate, or malformed request header.")
        fields[key] = value.strip()
    if not all(fields.get(key) for key in ("Request", "Session", "Mac")):
        raise BridgeError("Request, Session, and Mac are required.")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,99}", fields["Request"]):
        raise BridgeError("Request must be a unique filename-safe ID, at most 100 characters.")
    if fields["Mac"] not in machines:
        raise BridgeError("Mac must name a configured machine.")
    if fields["Session"] != "new" and not re.fullmatch(
        r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", fields["Session"]
    ):
        raise BridgeError("Session must be new or a session UUID.")
    if "Directory" in fields and not fields["Directory"].startswith("/"):
        raise BridgeError("Directory must be an absolute path on the selected Mac.")
    if fields["Session"] != "new" and "Directory" in fields:
        raise BridgeError("Directory applies only to new sessions.")
    return {**fields, "Prompt": prompt.strip()}


def read_secret(reference, op):
    if not reference.startswith("op://"):
        raise BridgeError("Credentials must be 1Password references.")
    try:
        result = subprocess.run(
            [op, "read", reference], capture_output=True, timeout=25, check=True
        )
        secret = result.stdout.decode().strip()
        if not secret:
            raise ValueError()
        return secret
    except (OSError, ValueError, subprocess.SubprocessError):
        raise BridgeError("1Password runtime read failed; no credential output recorded.") from None


def close_out(request_id, session_id, python, bridge, config):
    """Standing close-out: completion receipt first, then the session archives itself."""
    command = " ".join(
        shlex.quote(part)
        for part in [
            python,
            bridge,
            "--config",
            config,
            "--finish",
            request_id,
            "--session",
            session_id,
            "--note",
            "<one line result>",
        ]
    )
    return (
        "\n\n---\nFactory Inbox close-out. When the requested work is finished, replace "
        "<one line result> with one line naming the result, run this command, and stop.\n"
        f"{command}\n"
        "It publishes your completion receipt to the Factory Inbox Receipts folder and then "
        "archives this session. Archive only after the work itself is done."
    )


def settings_path(session_id, cwd=None):
    root = Path.home() / ".factory/sessions"
    found = sorted(root.glob(f"*/{session_id}.settings.json"))
    if found:
        return found[0]
    return root / str(Path(cwd or Path.cwd())).replace("/", "-") / f"{session_id}.settings.json"


def archive_session(session_id, cwd=None):
    """Archive state is the owning machine's session settings file. The documented
    sessionSettings.archivedAt PATCH returns 200 for this account but never persists,
    so the local store is the only durable archive switch."""
    path = settings_path(session_id, cwd)
    settings = {}
    if path.exists():
        try:
            settings = json.loads(path.read_text())
        except ValueError:
            settings = {}
    if settings.get("archivedAt"):
        return settings["archivedAt"]
    settings["archivedAt"] = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
    save(path, settings)
    return settings["archivedAt"]


class Http:
    def __init__(self, config):
        import requests
        from google.oauth2 import service_account

        self.http = requests.Session()
        self.key = read_secret(config["factory_key_ref"], config["op"])
        info = json.loads(read_secret(config["google_key_ref"], config["op"]))
        if info.get("token_uri") != "https://oauth2.googleapis.com/token":
            raise BridgeError("Unexpected Google token endpoint.")
        self.google = service_account.Credentials.from_service_account_info(
            info, scopes=["https://www.googleapis.com/auth/drive"]
        ).with_subject(config["google_subject"])

    def call(self, method, url, *, google=False, **kwargs):
        from google.auth.transport.requests import Request
        import requests

        if google:
            if not self.google.valid:
                self.google.refresh(Request())
            token = self.google.token
        else:
            token = self.key
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = "Bearer " + token
        try:
            response = self.http.request(
                method, url, headers=headers, timeout=(10, 90), allow_redirects=False, **kwargs
            )
        except requests.RequestException:
            raise BridgeError(
                "HTTP transport failed; a submitted POST may have been accepted."
            ) from None
        if not 200 <= response.status_code < 300:
            raise BridgeError(f"HTTP {response.status_code}; response body withheld.")
        return response

    def factory(self, method, path, body=None):
        return self.call(method, FACTORY + path, json=body).json()

    def drive(self, method, path, **kwargs):
        params = {"supportsAllDrives": "true", **kwargs.pop("params", {})}
        return self.call(method, DRIVE + path, google=True, params=params, **kwargs)

    def files(self, folder):
        files, cursor = [], None
        while True:
            params = {
                "q": f"'{folder}' in parents and trashed=false",
                "fields": "files(id,name,mimeType),nextPageToken",
                "pageSize": 100,
                "includeItemsFromAllDrives": "true",
            }
            if cursor:
                params["pageToken"] = cursor
            data = self.drive("GET", "/files", params=params).json()
            files.extend(data["files"])
            cursor = data.get("nextPageToken")
            if not cursor:
                return files

    def text(self, file):
        if file["mimeType"] == DOC:
            response = self.drive(
                "GET", f"/files/{file['id']}/export", params={"mimeType": "text/plain"}
            )
        else:
            response = self.drive("GET", f"/files/{file['id']}", params={"alt": "media"})
        if len(response.content) > MAX_BYTES:
            raise BridgeError("Request exceeds 128 KB.")
        return response.content.decode("utf-8-sig")

    def publish(self, receipt, folder, file_id, name):
        # Caller saves a generated Drive ID before upload. Reusing that ID is safe
        # after an uncertain upload; Factory POSTs have no such documented contract.
        metadata = {"id": file_id, "name": name, "parents": [folder]}
        boundary = "factory-inbox-receipt"
        body = (
            f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n"
            + json.dumps(metadata)
            + f"\r\n--{boundary}\r\nContent-Type: text/plain; charset=UTF-8\r\n\r\n"
            + json.dumps(receipt, indent=2)
            + f"\r\n--{boundary}--\r\n"
        )
        try:
            self.call(
                "POST",
                "https://www.googleapis.com/upload/drive/v3/files",
                google=True,
                params={"uploadType": "multipart", "supportsAllDrives": "true"},
                headers={"Content-Type": "multipart/related; boundary=" + boundary},
                data=body.encode(),
            )
        except BridgeError:
            # Only suppress a failed create when this exact preallocated file exists.
            existing = self.drive(
                "GET", "/files/" + file_id, params={"fields": "id,parents"}
            ).json()
            if folder not in existing.get("parents", []):
                raise BridgeError(
                    "Receipt ID exists outside the configured Receipts folder."
                ) from None

    def receipt_id(self):
        return self.drive(
            "GET", "/files/generateIds", params={"count": 1, "space": "drive"}
        ).json()["ids"][0]

    def move_done(self, file_id, config):
        self.drive(
            "PATCH",
            "/files/" + file_id,
            params={"addParents": config["done_id"], "removeParents": config["inbox_id"]},
            json={},
        )


class Worker:
    def __init__(self, config, api, config_path):
        self.config, self.api = config, api
        self.state = Path(config["state_path"]).expanduser()
        # The LaunchAgent runs the interpreter that owns this worker's dependencies,
        # so a session told to close out reuses it rather than guessing a python3.
        self.close_out = (sys.executable, str(Path(__file__).resolve()), str(config_path))

    def process(self, file, text):
        request = parse_request(text, self.config["machines"])
        rid = request["Request"]
        digest = hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest()
        journal = self.state / "journal" / (rid + ".json")
        state = json.loads(journal.read_text()) if journal.exists() else {}
        if state and state["digest"] != digest:
            raise BridgeError(
                "Request ID already used with different content. Use a new Request ID for a revision."
            )
        if not state:
            state = {"digest": digest, "phase": "ready", "request_id": rid}
        machine = self.config["machines"][request["Mac"]]
        if state["phase"] == "ready":
            try:
                if request["Session"] == "new":
                    state["phase"] = "creating"
                    save(journal, state)
                    result = self.api.factory(
                        "POST",
                        "/sessions",
                        {
                            "computerId": machine["computer_id"],
                            "cwd": request.get("Directory", machine["cwd"]),
                            "sessionSettings": {
                                "model": "auto",
                                "interactionMode": "auto",
                                "autonomyLevel": "high",
                            },
                        },
                    )
                    state["session_id"] = result["sessionId"]
                else:
                    sid = request["Session"]
                    result = self.api.factory(
                        "GET", f"/sessions/{sid}?computerId={quote(machine['computer_id'])}"
                    )
                    if result.get("computerId") != machine["computer_id"]:
                        raise BridgeError("Existing session is not on the requested Mac.")
                    state["session_id"] = sid
                state["phase"] = "created"
                save(journal, state)
            except BridgeError:
                if state["phase"] == "ready":
                    raise
                state["phase"] = "uncertain"
                save(journal, state)
        if state["phase"] == "created":
            state["phase"] = "sending"
            save(journal, state)
            try:
                result = self.api.factory(
                    "POST",
                    f"/sessions/{state['session_id']}/messages",
                    {
                        "text": request["Prompt"]
                        + close_out(rid, state["session_id"], *self.close_out),
                        "computerId": machine["computer_id"],
                    },
                )
                state.update(
                    phase="accepted", message_id=result["messageId"], agent_status=result["status"]
                )
            except BridgeError:
                state["phase"] = "uncertain"
            save(journal, state)
        if state["phase"] in ("creating", "sending"):
            # A previous process stopped across a non-idempotent Factory POST.
            state["phase"] = "uncertain"
            save(journal, state)
        receipt = {
            "request_id": rid,
            "status": state["phase"],
            "mac": request["Mac"],
            "computer_id": machine["computer_id"],
            "session_id": state.get("session_id"),
            "session_link": (
                "https://app.factory.ai/sessions/" + state["session_id"]
                if state.get("session_id")
                else None
            ),
            "message_id": state.get("message_id"),
            "agent_status": state.get("agent_status"),
            "meaning": (
                "Factory accepted the prompt, not proof the requested work is complete. The"
                " session publishes its completion receipt and archives itself once the work is"
                " done."
                if state["phase"] == "accepted"
                else "A Factory POST outcome is unknown. Reconcile the session/message before resubmitting. No automatic resend."
            ),
        }
        # Local receipts remain readable even if Drive publication is temporarily down.
        save(self.state / "receipts" / (rid + ".json"), receipt)
        if not state.get("receipt_id"):
            state["receipt_id"] = self.api.receipt_id()
            save(journal, state)
        receipt["receipt_link"] = "https://drive.google.com/file/d/" + state["receipt_id"] + "/view"
        save(self.state / "receipts" / (rid + ".json"), receipt)
        if not state.get("published"):
            self.api.publish(
                receipt, self.config["receipts_id"], state["receipt_id"], rid + ".json"
            )
            state["published"] = True
            save(journal, state)
        # Also move duplicate copies of the exact request without resending it.
        self.api.move_done(file["id"], self.config)
        return receipt

    def finish(self, request_id, session_id, note):
        """Run by the session itself when its work is done. Publishes the completion
        receipt, then archives the session. An unarchived session means unfinished
        bookkeeping, so the archive step never runs before the receipt is published."""
        journal = self.state / "journal" / (request_id + ".json")
        if not journal.exists():
            raise BridgeError("No inbox request with that Request ID on this machine.")
        state = json.loads(journal.read_text())
        if state.get("session_id") != session_id:
            raise BridgeError("That session does not belong to that Request ID.")
        receipt = {
            "request_id": request_id,
            "status": "completed",
            "session_id": session_id,
            "session_link": "https://app.factory.ai/sessions/" + session_id,
            "note": note,
            "completed_at": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()),
            "meaning": (
                "The session reported the requested work finished, published this completion"
                " receipt, and archived itself."
            ),
        }
        if not state.get("completion_receipt_id"):
            state["completion_receipt_id"] = self.api.receipt_id()
            save(journal, state)
        receipt["receipt_link"] = (
            "https://drive.google.com/file/d/" + state["completion_receipt_id"] + "/view"
        )
        save(self.state / "receipts" / (request_id + "-completion.json"), receipt)
        self.api.publish(
            receipt,
            self.config["receipts_id"],
            state["completion_receipt_id"],
            request_id + "-completion.json",
        )
        state["phase"] = "completed"
        save(journal, state)
        state["archived_at"] = archive_session(session_id)
        save(journal, state)
        return receipt

    def scan(self):
        root = Path(self.config["inbox_path"]).expanduser()
        if not root.is_dir():
            raise BridgeError("Drive Desktop inbox is not mounted.")
        files = self.api.files(self.config["inbox_id"])
        by_name = {}
        by_id = {file["id"]: file for file in files}
        for file in files:
            by_name.setdefault(file["name"], []).append(file)
        for path in sorted(root.iterdir()):
            if path.is_symlink() or not path.is_file() or path.suffix not in (".txt", ".gdoc"):
                continue
            if time.time() - path.stat().st_mtime < 3:
                continue
            try:
                if path.suffix == ".gdoc":
                    pointer = json.loads(path.read_text())
                    file = by_id.get(pointer.get("doc_id"))
                    if not file or file["mimeType"] != DOC:
                        continue
                else:
                    matches = by_name.get(path.name, [])
                    if len(matches) != 1 or matches[0]["mimeType"] != "text/plain":
                        continue  # Wait for Drive upload or an unambiguous name.
                    file = matches[0]
                # Read the authoritative content, not a stale hydrated text copy.
                text = self.api.text(file)
                receipt = self.process(file, text)
                print(
                    json.dumps({"request_id": receipt["request_id"], "status": receipt["status"]})
                )
            except (BridgeError, ValueError, OSError):
                # Keep partial Docs and revised files eligible on the next scan.
                # No prompts, credentials, or raw provider responses enter logs.
                print(
                    json.dumps(
                        {
                            "file_id": file["id"] if "file" in locals() else None,
                            "status": "deferred",
                            "reason": "Invalid, conflicting, or temporarily unavailable request. Inspect privately.",
                        }
                    )
                )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--finish")
    parser.add_argument("--session")
    parser.add_argument("--note", default="")
    args = parser.parse_args()
    if bool(args.finish) != bool(args.session):
        raise SystemExit("--finish needs --session, and --session needs --finish.")
    os.umask(0o077)
    config = json.loads(args.config.read_text())
    state = Path(config["state_path"]).expanduser()
    state.mkdir(parents=True, exist_ok=True)
    with (state / "worker.lock").open("a") as lock:
        if args.finish:
            # A close-out waits for an in-flight scan instead of skipping its receipt.
            fcntl.flock(lock, fcntl.LOCK_EX)
            worker = Worker(config, Http(config), args.config)
            receipt = worker.finish(args.finish, args.session, args.note)
            print(json.dumps({"request_id": receipt["request_id"], "status": receipt["status"]}))
            return
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        Worker(config, Http(config), args.config).scan()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Credential/library exceptions may include secret material. Never echo them.
        print(
            "Factory inbox scan failed. Check mount, runtime vault access, and API availability privately."
        )
        raise SystemExit(1) from None
