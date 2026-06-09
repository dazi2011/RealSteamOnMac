#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
TMP_ROOT=$(mktemp -d)
trap 'rm -rf "$TMP_ROOT"' EXIT

STEAM_APP="$TMP_ROOT/Steam.app"
RUNTIME_APP="$TMP_ROOT/SteamRuntime.app"
SUPPORT="$TMP_ROOT/support"
BACKUP="$TMP_ROOT/backup"
HOLD="$TMP_ROOT/hold"

mkdir -p \
    "$STEAM_APP/Contents/MacOS" \
    "$RUNTIME_APP/Contents/MacOS" \
    "$RUNTIME_APP/Contents/MacOS/steamui" \
    "$SUPPORT/ui" \
    "$SUPPORT/dependencies" \
    "$BACKUP/Steam.app/Contents/MacOS" \
    "$BACKUP/SteamRuntime.app/Contents/MacOS"

STEAMUI="$RUNTIME_APP/Contents/MacOS/steamui"
ORIGINAL_INDEX='<!doctype html><html style="width: 100%; height: 100%"><head><title>SharedJSContext</title><meta charset="utf-8"><script defer="defer" src="/libraries/libraries~00299a408.js"></script><script defer="defer" src="/library.js"></script><link href="/css/library.css" rel="stylesheet"></head><body style="width: 100%; height: 100%; margin: 0; overflow: hidden;"><div id="root" style="height:100%; width: 100%"></div><div style="display:none"></div></body></html>'
ORIGINAL_COMPAT='before(0,f.CI)()&&o.push({title:(0,A.we)("#AppProperties_CompatibilityPage")middle(0,f.CI)()&&o.push({title:(0,A.we)("#AppProperties_CompatibilityPage")after'

printf 'modified app\n' >"$STEAM_APP/Contents/MacOS/marker"
printf 'modified runtime\n' >"$RUNTIME_APP/Contents/MacOS/steam_osx"
printf 'modified steamclient\n' >"$RUNTIME_APP/Contents/MacOS/steamclient.dylib"
printf 'support\n' >"$SUPPORT/marker"
printf '%s' "$ORIGINAL_INDEX" >"$STEAMUI/index.html"
printf '%s' "$ORIGINAL_COMPAT" >"$STEAMUI/chunk~2dcc5aaf7.js"
cp "$ROOT/script/patch_steamui.py" "$SUPPORT/patch_steamui.py"
cp "$ROOT/ui/realsteamonmac_ui.js" "$SUPPORT/ui/realsteamonmac_ui.js"
printf '1118200\n' >"$SUPPORT/allowlist.txt"
printf '0123456789abcdef0123456789abcdef\n' \
    >"$SUPPORT/registry-token"
cp "$ROOT/config/dependencies.json" \
    "$SUPPORT/dependencies/catalog.json"
chmod 0600 "$SUPPORT/registry-token"
chmod +x "$SUPPORT/patch_steamui.py"
printf 'clean app\n' >"$BACKUP/Steam.app/Contents/MacOS/marker"
printf 'clean runtime\n' >"$BACKUP/SteamRuntime.app/Contents/MacOS/steam_osx"
printf 'clean steamclient\n' \
    >"$BACKUP/SteamRuntime.app/Contents/MacOS/steamclient.dylib"
chmod +x \
    "$RUNTIME_APP/Contents/MacOS/steam_osx" \
    "$BACKUP/SteamRuntime.app/Contents/MacOS/steam_osx"

export REALSTEAMONMAC_ALLOW_TEST_FIXTURES=1
"$SUPPORT/patch_steamui.py" install \
    --steamui-root "$STEAMUI" \
    --ui-source "$SUPPORT/ui/realsteamonmac_ui.js" \
    --allowlist "$SUPPORT/allowlist.txt" \
    --dependencies "$SUPPORT/dependencies/catalog.json" >/dev/null
grep -q '/realsteamonmac/ui.js' "$STEAMUI/index.html"
test -e "$STEAMUI/index.html.realsteamonmac.original"
test -e "$STEAMUI/chunk~2dcc5aaf7.js.realsteamonmac.original"

"$ROOT/script/restore_steam_from_backup.sh" \
    --clean-backup "$BACKUP" \
    --steam-app "$STEAM_APP" \
    --runtime-app "$RUNTIME_APP" \
    --support-root "$SUPPORT" \
    --hold-root "$HOLD" >/dev/null

grep -q 'clean app' "$STEAM_APP/Contents/MacOS/marker"
grep -q 'clean runtime' "$RUNTIME_APP/Contents/MacOS/steam_osx"
grep -q 'clean steamclient' "$RUNTIME_APP/Contents/MacOS/steamclient.dylib"
test "$(cat "$STEAMUI/index.html")" = "$ORIGINAL_INDEX"
test "$(cat "$STEAMUI/chunk~2dcc5aaf7.js")" = "$ORIGINAL_COMPAT"
test ! -e "$STEAMUI/index.html.realsteamonmac.original"
test ! -e "$STEAMUI/chunk~2dcc5aaf7.js.realsteamonmac.original"
test ! -e "$STEAMUI/realsteamonmac"
test ! -e "$SUPPORT"
test "$(find "$HOLD" -name 'Steam.app.modified' -type d | wc -l)" -eq 1
test "$(find "$HOLD" -name 'RealSteamOnMac-support.disabled' -type d | wc -l)" -eq 1

echo "Steam restore contract: PASS"
