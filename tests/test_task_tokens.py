import importlib
import sys
import types
import unittest
from unittest.mock import patch

sys.modules.setdefault("requests", types.SimpleNamespace(post=None))
task = importlib.import_module("task")


class TaskTokenTests(unittest.TestCase):
    def test_device_code_refresh_omits_client_secret_and_redirect_uri(self):
        app = {
            "auth_flow": "device_code",
            "client_id": "client-id",
            "client_secret": "legacy-secret",
            "redirect_uri": "http://localhost:3000/",
            "refresh_token": "refresh-token",
            "scope": "offline_access User.Read Mail.Read",
        }

        with patch("task.requests.post") as post:
            post.return_value.json.return_value = {"access_token": "access"}
            task.get_access_token(app)

        sent = post.call_args.kwargs["data"]
        self.assertEqual(sent["client_id"], "client-id")
        self.assertEqual(sent["refresh_token"], "refresh-token")
        self.assertEqual(sent["scope"], "offline_access User.Read Mail.Read")
        self.assertNotIn("client_secret", sent)
        self.assertNotIn("redirect_uri", sent)


if __name__ == "__main__":
    unittest.main()
