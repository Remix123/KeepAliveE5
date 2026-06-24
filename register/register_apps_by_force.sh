#!/usr/bin/env bash

set -eu

REGISTER_ACCOUNT_COUNT="${REGISTER_ACCOUNT_COUNT:-1}"

[[ "$REGISTER_ACCOUNT_COUNT" =~ ^[1-9][0-9]*$ ]] || {
    echo "REGISTER_ACCOUNT_COUNT must be a positive integer."
    exit 1
}

python3 register_apps_by_device_code.py
