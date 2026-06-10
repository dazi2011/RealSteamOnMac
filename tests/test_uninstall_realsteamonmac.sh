#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
TMP_ROOT=$(mktemp -d)
trap 'rm -rf "$TMP_ROOT"' EXIT

STEAM_APP="$TMP_ROOT/Steam.app"
RUNTIME_APP="$TMP_ROOT/SteamRuntime.app"
SUPPORT="$TMP_ROOT/support"
BACKUP="$TMP_ROOT/backup"
COMPAT_TOOLS="$TMP_ROOT/compatibilitytools.d"
HOLD="$TMP_ROOT/rollback"
PFX="$TMP_ROOT/steamapps/compatdata/1118200/pfx"

mkdir -p \
    "$STEAM_APP/Contents/MacOS" \
    "$RUNTIME_APP/Contents/MacOS/steamui" \
    "$SUPPORT" \
    "$BACKUP/Steam.app/Contents/MacOS" \
    "$BACKUP/SteamRuntime.app/Contents/MacOS" \
    "$COMPAT_TOOLS/realsteamonmac-dxmt" \
    "$COMPAT_TOOLS/realsteamonmac-dxvk" \
    "$COMPAT_TOOLS/user-tool" \
    "$PFX"

printf 'modified app\n' >"$STEAM_APP/Contents/MacOS/marker"
printf 'modified runtime\n' >"$RUNTIME_APP/Contents/MacOS/steam_osx"
printf 'clean app\n' >"$BACKUP/Steam.app/Contents/MacOS/marker"
printf 'clean runtime\n' >"$BACKUP/SteamRuntime.app/Contents/MacOS/steam_osx"
printf 'support\n' >"$SUPPORT/marker"
printf '{"tool":"realsteamonmac-dxmt"}\n' \
    >"$COMPAT_TOOLS/realsteamonmac-dxmt/realsteamonmac.json"
printf '{"tool":"realsteamonmac-dxvk","changed":true}\n' \
    >"$COMPAT_TOOLS/realsteamonmac-dxvk/realsteamonmac.json"
printf 'user\n' >"$COMPAT_TOOLS/user-tool/marker"
printf 'prefix\n' >"$PFX/marker"
chmod +x \
    "$RUNTIME_APP/Contents/MacOS/steam_osx" \
    "$BACKUP/SteamRuntime.app/Contents/MacOS/steam_osx"

DXMT_SHA=$(shasum -a 256 \
    "$COMPAT_TOOLS/realsteamonmac-dxmt/realsteamonmac.json" |
    awk '{print $1}')
DXVK_OLD_SHA=$(printf '{"tool":"realsteamonmac-dxvk"}\n' |
    shasum -a 256 | awk '{print $1}')

/usr/bin/python3 - \
    "$SUPPORT/install-state.json" \
    "$BACKUP" \
    "$STEAM_APP" \
    "$RUNTIME_APP" \
    "$SUPPORT" \
    "$COMPAT_TOOLS" \
    "$DXMT_SHA" \
    "$DXVK_OLD_SHA" <<'PY'
import json
import sys

(
    output,
    backup,
    steam_app,
    runtime_app,
    support,
    tools,
    dxmt_sha,
    dxvk_sha,
) = sys.argv[1:]
state = {
    "schema": 1,
    "clean_backup": backup,
    "steam_app": steam_app,
    "runtime_app": runtime_app,
    "support_root": support,
    "runtime_root": support + "/runtimes",
    "compat_tools_root": tools,
    "runtime_package": "fixture",
    "managed_compat_tools": [
        {
            "name": "realsteamonmac-dxmt",
            "metadata_sha256": dxmt_sha,
        },
        {
            "name": "realsteamonmac-dxvk",
            "metadata_sha256": dxvk_sha,
        },
    ],
}
with open(output, "w", encoding="utf-8") as stream:
    json.dump(state, stream)
PY

"$ROOT/script/uninstall_realsteamonmac.sh" \
    --support-root "$SUPPORT" \
    --hold-root "$HOLD" >/dev/null

grep -q 'clean app' "$STEAM_APP/Contents/MacOS/marker"
grep -q 'clean runtime' "$RUNTIME_APP/Contents/MacOS/steam_osx"
test ! -e "$SUPPORT"
test ! -e "$COMPAT_TOOLS/realsteamonmac-dxmt"
test -f "$COMPAT_TOOLS/realsteamonmac-dxvk/realsteamonmac.json"
test -f "$COMPAT_TOOLS/user-tool/marker"
test -f "$PFX/marker"
test "$(find "$HOLD" -path '*/compatibility-tools-disabled/realsteamonmac-dxmt' -type d | wc -l)" -eq 1
REPORT=$(find "$HOLD" -name uninstall-report.txt -type f -print -quit)
grep -q '^prefixes_preserved=true$' "$REPORT"
grep -q '^compat_tool_moved=realsteamonmac-dxmt$' "$REPORT"
grep -q '^compat_tool_preserved=realsteamonmac-dxvk: metadata changed after installation$' "$REPORT"

echo "uninstaller contract: PASS"
