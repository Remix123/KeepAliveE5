#!/usr/bin/env python3
import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "register"))

from device_code_token import poll_token, request_device_code  # noqa: E402

DEFAULT_SCOPE = (
    "offline_access User.Read Mail.ReadWrite Calendars.ReadWrite "
    "Files.ReadWrite.All Sites.Read.All Contacts.ReadWrite"
)


def graph_me(access_token):
    request = urllib.request.Request(
        "https://graph.microsoft.com/v1.0/me?$select=userPrincipalName,mail",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError:
        return {}


def main():
    parser = argparse.ArgumentParser(
        description="Run Microsoft device-code login locally and save a Graph refresh token."
    )
    parser.add_argument("--client-id", required=True, help="Application (client) ID")
    parser.add_argument("--output", default="config/app0.json", help="Output config path")
    parser.add_argument(
        "--scope",
        default=DEFAULT_SCOPE,
        help="Space-separated delegated scopes. Include offline_access.",
    )
    parser.add_argument(
        "--username",
        default="",
        help="Optional username label to store if /me cannot be read.",
    )
    args = parser.parse_args()

    device = request_device_code(args.client_id, scope=args.scope)
    print(device.get("message", ""), flush=True)
    print(f"Verification URL: {device.get('verification_uri')}", flush=True)
    print(f"User code: {device.get('user_code')}", flush=True)

    token = poll_token(
        args.client_id,
        device["device_code"],
        device.get("interval", 5),
        device.get("expires_in", 900),
        scope=args.scope,
    )

    user = graph_me(token["access_token"])
    username = (
        user.get("userPrincipalName")
        or user.get("mail")
        or args.username
        or "device-code-user"
    )

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            {
                "username": username,
                "client_id": args.client_id,
                "refresh_token": token["refresh_token"],
                "auth_flow": "device_code",
                "scope": args.scope,
            },
            indent=2,
        )
    )
    print(f"Saved refresh token config to {output}", flush=True)


if __name__ == "__main__":
    main()
