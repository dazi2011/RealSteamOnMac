#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
SOURCE="$ROOT/config/allowlist.txt"
TARGET_ROOT="${REALSTEAMONMAC_CONFIG_ROOT:-$HOME/Library/Application Support/RealSteamOnMac}"

test -f "$SOURCE"
mkdir -p "$TARGET_ROOT"
cp "$SOURCE" "$TARGET_ROOT/allowlist.txt"
chmod 0600 "$TARGET_ROOT/allowlist.txt"

echo "$TARGET_ROOT/allowlist.txt"
