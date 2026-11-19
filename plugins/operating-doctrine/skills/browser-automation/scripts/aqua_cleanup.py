"""Invoke the signed Chrome helper in Ember's Aqua domain, without prompting."""

import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import stat
import subprocess
import tempfile
import time
import uuid

from relay_ownership import URL_CLASSES, valid_id


class AquaRefusal(RuntimeError):
    """Use a fixed diagnostic, not arbitrary output from Chrome or launchd."""


class AquaCleanup:
    def __init__(self, executable, digest, state):
        self.executable = Path(executable)
        if (
            not self.executable.is_absolute()
            or not isinstance(digest, str)
            or not re.fullmatch(r"[a-f0-9]{64}", digest)
        ):
            raise AquaRefusal("aqua_helper_config_invalid")
        self.digest = digest
        self.state = Path(state)
        self.domain = f"gui/{os.getuid()}"

    @staticmethod
    def _launchctl(*args):
        return subprocess.run(
            ["/bin/launchctl", *args], capture_output=True, text=True, timeout=4, check=False
        )

    def _verify(self):
        attrs = self.executable.lstat()
        directory = self.state.lstat()
        if (
            not stat.S_ISREG(attrs.st_mode)
            or attrs.st_uid != os.getuid()
            or attrs.st_mode & 0o022
            or not stat.S_ISDIR(directory.st_mode)
            or directory.st_uid != os.getuid()
            or directory.st_mode & 0o077
            or hashlib.sha256(self.executable.read_bytes()).hexdigest() != self.digest
        ):
            raise AquaRefusal("aqua_helper_identity_changed")

    def _invoke(self, *args):
        self._verify()
        label = "com.expertpartners.browser-exact-cleanup." + uuid.uuid4().hex
        service = self.domain + "/" + label
        with tempfile.TemporaryDirectory(dir=self.state, prefix="aqua-") as directory:
            root = Path(directory)
            plist, out = root / "job.plist", root / "result.json"
            out.touch(mode=0o600)
            plist.write_bytes(
                plistlib.dumps(
                    {
                        "Label": label,
                        "ProgramArguments": [str(self.executable), *args],
                        "LimitLoadToSessionType": "Aqua",
                        "RunAtLoad": True,
                        "StandardOutPath": str(out),
                        "StandardErrorPath": "/dev/null",
                    }
                )
            )
            if self._launchctl("bootstrap", self.domain, str(plist)).returncode:
                raise AquaRefusal("aqua_helper_bootstrap_failed")
            try:
                deadline = time.monotonic() + 12
                while time.monotonic() < deadline:
                    status = self._launchctl("print", service)
                    match = re.search(r"(?m)^\s*last exit code = (-?\d+)\s*$", status.stdout)
                    if match:
                        if status.returncode or match.group(1) != "0":
                            raise AquaRefusal("aqua_helper_refused")
                        if out.stat().st_size > 1_048_576:
                            raise AquaRefusal("aqua_helper_result_too_large")
                        return json.loads(out.read_bytes())
                    time.sleep(0.1)
                raise AquaRefusal("aqua_helper_outcome_unknown")
            finally:
                if self._launchctl("bootout", service).returncode:
                    raise AquaRefusal("aqua_helper_teardown_unverified")

    def inventory(self):
        value = self._invoke("list")
        rows = value.get("tabs") if isinstance(value, dict) else None
        if not isinstance(rows, list) or any(
            not isinstance(row, dict)
            or not valid_id(row.get("tabId"))
            or not valid_id(row.get("windowId"))
            or not isinstance(row.get("urlClass"), str)
            or row["urlClass"] not in URL_CLASSES
            for row in rows
        ):
            raise AquaRefusal("aqua_helper_inventory_invalid")
        return rows

    def close(self, window_id, tab_id, url_class):
        if (
            not valid_id(window_id)
            or not valid_id(tab_id)
            or not isinstance(url_class, str)
            or url_class not in URL_CLASSES
        ):
            raise AquaRefusal("aqua_helper_close_identity_invalid")
        value = self._invoke("close", str(window_id), str(tab_id), url_class)
        disposition = value.get("disposition") if isinstance(value, dict) else None
        if disposition not in (
            "closed",
            "window_missing",
            "tab_missing",
            "url_class_changed",
            "close_unverified",
        ):
            raise AquaRefusal("aqua_helper_close_result_invalid")
        return disposition
