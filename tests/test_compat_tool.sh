#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
TMP_ROOT=$(mktemp -d)
trap 'rm -rf "$TMP_ROOT"' EXIT

"$ROOT/script/install_compat_tool.sh" --target-root "$TMP_ROOT"

TOOL_DIR="$TMP_ROOT/realsteamonmac-experimental"
VDF="$TOOL_DIR/compatibilitytool.vdf"
MANIFEST="$TOOL_DIR/toolmanifest.vdf"
RUNNER="$TOOL_DIR/run"

test -f "$VDF"
test -f "$MANIFEST"
test -x "$RUNNER"

grep -q '"realsteamonmac-experimental"' "$VDF"
grep -q '"from_oslist"[[:space:]]*"windows"' "$VDF"
grep -q '"to_oslist"[[:space:]]*"macos"' "$VDF"
grep -q '"commandline"[[:space:]]*"/run %verb%"' "$MANIFEST"

if grep -Eqi 'global|platform_override|1118200' "$VDF" "$MANIFEST"; then
    echo "compat tool manifests must not contain global or per-AppID overrides" >&2
    exit 1
fi

LOG_ROOT="$TMP_ROOT/logs"
REALSTEAMONMAC_LOG_ROOT="$LOG_ROOT" \
    SteamAppId=1118200 \
    STEAM_COMPAT_APP_ID=1118200 \
    "$RUNNER" waitforexitandrun "/tmp/People Playground.exe" -test-flag

LOG_FILE="$LOG_ROOT/compat-tool.log"
test -f "$LOG_FILE"
grep -q 'SteamAppId=1118200' "$LOG_FILE"
grep -q 'STEAM_COMPAT_APP_ID=1118200' "$LOG_FILE"
grep -q 'verb=waitforexitandrun' "$LOG_FILE"

echo "compat tool contract: PASS"
