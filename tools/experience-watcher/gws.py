"""Google Workspace helper for the HQ Experience Director watcher.

Mints a delegated token from the Ember workspace service account key held in
1Password. The key is read with op at run time and never printed or stored.
Acts as the AI worker mailbox named in GWS_SUBJECT (default the ember worker).
"""

import json
import os
import subprocess
import urllib.request

from google.oauth2 import service_account
import google.auth.transport.requests

SA_REF = "op://Ember/6d2p2sastgo5yktlde4gfr5z5i/credential"
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/documents",
]
DEFAULT_SUBJECT = os.environ.get("GWS_SUBJECT", "ember" + "@" + "expertpartners.com")
_tok = {}


def _op_env():
    env = dict(os.environ)
    p = os.path.expanduser("~/.ember/op-sa-token-main")
    if "OP_SERVICE_ACCOUNT_TOKEN" not in env and os.path.exists(p):
        env["OP_SERVICE_ACCOUNT_TOKEN"] = open(p).read().strip()
    return env


def op_read(ref):
    return subprocess.run(
        ["/opt/homebrew/bin/op", "read", ref],
        capture_output=True,
        text=True,
        check=True,
        env=_op_env(),
    ).stdout.strip()


def token(subject=None):
    subject = subject or DEFAULT_SUBJECT
    if subject not in _tok:
        info = json.loads(op_read(SA_REF))
        c = service_account.Credentials.from_service_account_info(
            info, scopes=SCOPES, subject=subject
        )
        c.refresh(google.auth.transport.requests.Request())
        _tok[subject] = c.token
    return _tok[subject]


def api(url, method="GET", body=None, subject=None, raw=False):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": "Bearer " + token(subject),
            "Content-Type": "application/json",
            "User-Agent": "hq-experience-director/1.0",
        },
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        b = r.read()
    return b.decode("utf-8") if raw else (json.loads(b) if b else {})


def export_text(doc_id, subject=None):
    return api(
        f"https://www.googleapis.com/drive/v3/files/{doc_id}/export?mimeType=text/plain",
        raw=True,
        subject=subject,
    )


def get_doc(doc_id, subject=None):
    return api(f"https://docs.googleapis.com/v1/documents/{doc_id}", subject=subject)


def batch_update(doc_id, requests, subject=None):
    return api(
        f"https://docs.googleapis.com/v1/documents/{doc_id}:batchUpdate",
        method="POST",
        body={"requests": requests},
        subject=subject,
    )
