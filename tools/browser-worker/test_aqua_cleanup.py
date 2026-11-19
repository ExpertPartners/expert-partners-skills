import hashlib
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

SCRIPTS = (
    Path(__file__).resolve().parents[2]
    / "plugins/operating-doctrine/skills/browser-automation/scripts"
)
sys.path.insert(0, str(SCRIPTS))
try:
    from aqua_cleanup import AquaCleanup, AquaRefusal
finally:
    sys.path.pop(0)


class AquaCleanupTests(unittest.TestCase):
    def test_pins_helper_content(self):
        with TemporaryDirectory() as directory:
            executable = Path(directory) / "helper"
            executable.write_bytes(b"expected")
            executable.chmod(0o700)
            digest = hashlib.sha256(b"expected").hexdigest()
            client = AquaCleanup(executable, digest, directory)
            client._verify()
            executable.write_bytes(b"different")
            with self.assertRaisesRegex(AquaRefusal, "identity_changed"):
                client._verify()

    def test_exact_close_only(self):
        client = AquaCleanup("/test/helper", "0" * 64, "/test/private")
        with patch.object(client, "_invoke", return_value={"disposition": "closed"}) as run:
            self.assertEqual(client.close(14, 17, "blank"), "closed")
            run.assert_called_once_with("close", "14", "17", "blank")
        for invalid in ((True, 17, "blank"), (14, 0, "blank"), (14, 17, "https://example.com")):
            with self.assertRaisesRegex(AquaRefusal, "identity_invalid"):
                client.close(*invalid)

    def test_inventory_is_schema_checked(self):
        client = AquaCleanup("/test/helper", "0" * 64, "/test/private")
        valid = {"tabId": 17, "windowId": 14, "urlClass": "blank"}
        with patch.object(client, "_invoke", return_value={"tabs": [valid]}):
            self.assertEqual(client.inventory(), [valid])
        with patch.object(client, "_invoke", return_value={"tabs": [{**valid, "tabId": False}]}):
            with self.assertRaisesRegex(AquaRefusal, "inventory_invalid"):
                client.inventory()
