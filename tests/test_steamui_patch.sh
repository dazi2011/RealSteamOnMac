#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
PATCHER="$ROOT/script/patch_steamui.py"
UI_SOURCE="$ROOT/ui/realsteamonmac_ui.js"
TMP_ROOT=$(mktemp -d)
trap 'rm -rf "$TMP_ROOT"' EXIT

test -x "$PATCHER"
test -f "$UI_SOURCE"

STEAMUI="$TMP_ROOT/steamui"
mkdir -p "$STEAMUI"
printf '%s' \
    '<!doctype html><html style="width: 100%; height: 100%"><head><title>SharedJSContext</title><meta charset="utf-8"><script defer="defer" src="/libraries/libraries~00299a408.js"></script><script defer="defer" src="/library.js"></script><link href="/css/library.css" rel="stylesheet"></head><body style="width: 100%; height: 100%; margin: 0; overflow: hidden;"><div id="root" style="height:100%; width: 100%"></div><div style="display:none"></div></body></html>' \
    >"$STEAMUI/index.html"
printf '%s\n' 1118200 >"$TMP_ROOT/allowlist.txt"

"$PATCHER" install \
    --steamui-root "$STEAMUI" \
    --ui-source "$UI_SOURCE" \
    --allowlist "$TMP_ROOT/allowlist.txt"
"$PATCHER" install \
    --steamui-root "$STEAMUI" \
    --ui-source "$UI_SOURCE" \
    --allowlist "$TMP_ROOT/allowlist.txt"
"$PATCHER" verify --steamui-root "$STEAMUI"

test "$(grep -o '/realsteamonmac/config.js' "$STEAMUI/index.html" | wc -l)" -eq 1
test "$(grep -o '/realsteamonmac/ui.js' "$STEAMUI/index.html" | wc -l)" -eq 1
grep -q '"appids":\[1118200\]' "$STEAMUI/realsteamonmac/config.js"

"$PATCHER" restore --steamui-root "$STEAMUI"
test ! -e "$STEAMUI/index.html.realsteamonmac.original"
test ! -e "$STEAMUI/realsteamonmac"
test "$(shasum -a 256 "$STEAMUI/index.html" | awk '{print $1}')" = \
    "55ced284314dbc65bff38fb1333d4f4bd617635895e2c0e2197b05028c243282"

echo "Steam UI resource patch contract: PASS"
