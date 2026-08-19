import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

DEVICE_CODE_ENDPOINT = "https://login.microsoftonline.com/common/oauth2/v2.0/devicecode"
TOKEN_ENDPOINT = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
SCOPE = "offline_access User.Read"


class DeviceCodeError(RuntimeError):
    pass


def post_form(url, data):
    body = urllib.parse.urlencode(data).encode()
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as error:
        payload = error.read().decode()
        try:
            return json.loads(payload)
        except json.JSONDecodeError as exc:
            raise DeviceCodeError(payload) from exc


def request_device_code(client_id, scope=SCOPE):
    response = post_form(
        DEVICE_CODE_ENDPOINT,
        {
            "client_id": client_id,
            "scope": scope,
        },
    )
    if "device_code" not in response:
        raise DeviceCodeError(response.get("error_description", str(response)))
    return response


def poll_token(client_id, device_code, interval, expires_in, sleep=time.sleep, scope=SCOPE):
    deadline = time.monotonic() + int(expires_in)
    wait = int(interval)

    while time.monotonic() < deadline:
        sleep(wait)
        response = post_form(
            TOKEN_ENDPOINT,
            {
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                "client_id": client_id,
                "device_code": device_code,
                "scope": scope,
            },
        )
        if "refresh_token" in response:
            return response

        error = response.get("error")
        if error == "authorization_pending":
            continue
        if error == "slow_down":
            wait += 5
            continue
        raise DeviceCodeError(response.get("error_description", str(response)))

    raise DeviceCodeError("Device code expired before authentication completed.")


def acquire_refresh_token(config_path, sleep=time.sleep, scope=SCOPE):
    path = Path(config_path)
    config = json.loads(path.read_text())
    client_id = config["client_id"]

    device = request_device_code(client_id, scope=scope)
    print("\nMicrosoft device login required for this registered app:", flush=True)
    print(device.get("message", ""), flush=True)
    print(f"Verification URL: {device.get('verification_uri')}", flush=True)
    print(f"User code: {device.get('user_code')}\n", flush=True)

    token = poll_token(
        client_id,
        device["device_code"],
        device.get("interval", 5),
        device.get("expires_in", 900),
        sleep=sleep,
        scope=scope,
    )
    config["refresh_token"] = token["refresh_token"]
    config["auth_flow"] = "device_code"
    path.write_text(json.dumps(config))


def main(argv):
    if len(argv) != 2:
        print("Usage: python device_code_token.py <config-file>", file=sys.stderr)
        return 2
    acquire_refresh_token(argv[1])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
