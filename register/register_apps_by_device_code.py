import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from device_code_token import acquire_refresh_token, poll_token, request_device_code

AZURE_CLI_CLIENT_ID = "04b07795-8ddb-461a-bbee-02f9e1bf7b46"
GRAPH = "https://graph.microsoft.com/v1.0"
GRAPH_MANAGEMENT_SCOPE = (
    "https://graph.microsoft.com/Application.ReadWrite.All "
    "https://graph.microsoft.com/Directory.ReadWrite.All "
    "https://graph.microsoft.com/User.Read"
)
APP_TOKEN_SCOPE = "https://graph.microsoft.com/.default offline_access"

CONFIG_PATH = Path("../config")
PERMISSIONS_FILE = Path("required-resource-accesses.json")
NAME_GENERATOR = Path("name_generator/bin/ng")


class GraphError(RuntimeError):
    pass


def graph_request(method, path, token, body=None):
    data = None
    headers = {"Authorization": f"Bearer {token}"}
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(
        f"{GRAPH}{path}",
        data=data,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            content = response.read().decode()
            return json.loads(content) if content else {}
    except urllib.error.HTTPError as error:
        payload = error.read().decode()
        raise GraphError(f"{method} {path} failed: {payload}") from error


def stable_id(value):
    output = subprocess.check_output(["cksum"], input=value.encode())
    return output.decode().split()[0]


def app_name_for(user_id):
    app_id = stable_id(user_id)
    return subprocess.check_output([str(NAME_GENERATOR), app_id]).decode().strip() + app_id


def get_management_token():
    device = request_device_code(AZURE_CLI_CLIENT_ID, scope=GRAPH_MANAGEMENT_SCOPE)
    print("\nMicrosoft Graph management login required:", flush=True)
    print(device.get("message", ""), flush=True)
    print(f"Verification URL: {device.get('verification_uri')}", flush=True)
    print(f"User code: {device.get('user_code')}\n", flush=True)
    token = poll_token(
        AZURE_CLI_CLIENT_ID,
        device["device_code"],
        device.get("interval", 5),
        device.get("expires_in", 900),
        scope=GRAPH_MANAGEMENT_SCOPE,
    )
    return token["access_token"]


def delete_existing_apps(token, names):
    for name in names:
        escaped = name.replace("'", "''")
        query = urllib.parse.urlencode({"$filter": f"displayName eq '{escaped}'"})
        while True:
            result = graph_request("GET", f"/applications?{query}", token)
            apps = result.get("value", [])
            if not apps:
                break
            for app in apps:
                graph_request("DELETE", f"/applications/{app['id']}", token)
            time.sleep(3)


def register_one(order):
    print(f"Preparing account {order + 1}.", flush=True)
    token = get_management_token()
    user = graph_request("GET", "/me?$select=id,userPrincipalName", token)
    user_id = user["id"]
    username = user.get("userPrincipalName", "")
    app_name = app_name_for(user_id)
    old_names = ["E5_ALIVE", app_name]
    delete_existing_apps(token, old_names)

    required_resource_access = json.loads(PERMISSIONS_FILE.read_text())
    app = graph_request(
        "POST",
        "/applications",
        token,
        {
            "displayName": app_name,
            "signInAudience": "AzureADMultipleOrgs",
            "isFallbackPublicClient": True,
            "requiredResourceAccess": required_resource_access,
        },
    )

    config_file = CONFIG_PATH / f"app{order}.json"
    config_file.write_text(
        json.dumps(
            {
                "username": username,
                "client_id": app["appId"],
                "auth_flow": "device_code",
                "old_app_name_prefixes": old_names,
            }
        )
    )

    print(f"Application created for {username}. Complete consent for the new app.", flush=True)
    acquire_refresh_token(config_file, scope=APP_TOKEN_SCOPE)


def main():
    count = int(os.environ.get("REGISTER_ACCOUNT_COUNT", "1"))
    if count < 1:
        raise SystemExit("REGISTER_ACCOUNT_COUNT must be a positive integer.")

    CONFIG_PATH.mkdir(exist_ok=True)
    for path in CONFIG_PATH.glob("*.json"):
        path.unlink()
    NAME_GENERATOR.chmod(0o755)

    for order in range(count):
        register_one(order)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(exc, file=sys.stderr, flush=True)
        raise
