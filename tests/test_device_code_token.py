import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from register import device_code_token


class DeviceCodeTokenTests(unittest.TestCase):
    def test_writes_refresh_token_and_marks_device_code_flow(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "app0.json"
            config_path.write_text(json.dumps({"client_id": "client-id"}))

            with patch.object(
                device_code_token,
                "request_device_code",
                return_value={
                    "device_code": "device-code",
                    "user_code": "ABCD-EFGH",
                    "verification_uri": "https://microsoft.com/devicelogin",
                    "message": "Use this code",
                    "interval": 1,
                    "expires_in": 900,
                },
            ), patch.object(
                device_code_token,
                "poll_token",
                return_value={"refresh_token": "refresh-token"},
            ):
                device_code_token.acquire_refresh_token(config_path, sleep=lambda _: None)

            saved = json.loads(config_path.read_text())
            self.assertEqual(saved["refresh_token"], "refresh-token")
            self.assertEqual(saved["auth_flow"], "device_code")


if __name__ == "__main__":
    unittest.main()
