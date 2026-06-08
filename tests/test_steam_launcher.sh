#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
BUILD_SCRIPT="$ROOT/script/build_steam_launcher.sh"
LAUNCHER="$ROOT/artifacts/steam-launcher/realsteamonmac_launcher"
SOURCE="$ROOT/launcher/steam_launcher.c"
TMP_ROOT=$(mktemp -d)
trap 'rm -rf "$TMP_ROOT"' EXIT

test -x "$BUILD_SCRIPT"
test -f "$SOURCE"
grep -q 'DYLD_INSERT_LIBRARIES' "$SOURCE"
grep -q 'REALSTEAMONMAC_FORCE_COMPAT' "$SOURCE"
grep -q 'STEAM_EXTRA_COMPAT_TOOLS_PATHS' "$SOURCE"
grep -q 'exec_original_bootstrap' "$SOURCE"

"$BUILD_SCRIPT"
file "$LAUNCHER" | grep -q 'arm64'
file "$LAUNCHER" | grep -q 'x86_64'
codesign --verify --strict "$LAUNCHER"

HOME_ROOT="$TMP_ROOT/home"
SUPPORT="$TMP_ROOT/support"
RUNTIME="$TMP_ROOT/fake-runtime"
CAPTURE="$TMP_ROOT/capture.txt"
STEAMUI="$TMP_ROOT/steamui"
mkdir -p "$HOME_ROOT" "$SUPPORT/compat-tool" "$SUPPORT/ui" "$STEAMUI"
touch "$SUPPORT/libRealSteamCompatGate.dylib"
cp "$ROOT/script/patch_steamui.py" "$SUPPORT/patch_steamui.py"
cp "$ROOT/ui/realsteamonmac_ui.js" "$SUPPORT/ui/realsteamonmac_ui.js"
printf '%s\n' 1118200 >"$SUPPORT/allowlist.txt"
printf '%s\n' '#!/bin/sh' 'exit 0' >"$RUNTIME"
chmod +x "$RUNTIME"
printf '%s' \
    '<!doctype html><html style="width: 100%; height: 100%"><head><title>SharedJSContext</title><meta charset="utf-8"><script defer="defer" src="/libraries/libraries~00299a408.js"></script><script defer="defer" src="/library.js"></script><link href="/css/library.css" rel="stylesheet"></head><body style="width: 100%; height: 100%; margin: 0; overflow: hidden;"><div id="root" style="height:100%; width: 100%"></div><div style="display:none"></div></body></html>' \
    >"$STEAMUI/index.html"

HOME="$HOME_ROOT" \
REALSTEAMONMAC_RUNTIME_EXECUTABLE="$RUNTIME" \
REALSTEAMONMAC_SUPPORT_ROOT="$SUPPORT" \
REALSTEAMONMAC_LAUNCHER_DRY_RUN=1 \
    "$LAUNCHER" -cef-enable-debugging >"$CAPTURE"

grep -Fq "dyld=$SUPPORT/libRealSteamCompatGate.dylib" "$CAPTURE"
grep -Fq "enabled=1" "$CAPTURE"
grep -Fq "tools=$SUPPORT/compat-tool" "$CAPTURE"
grep -Fq "args=-skipinitialbootstrap -cef-enable-debugging" "$CAPTURE"
grep -Fq "steamui=verified" "$CAPTURE"
grep -Fq '/realsteamonmac/ui.js' "$STEAMUI/index.html"
test -f "$STEAMUI/index.html.realsteamonmac.original"

echo "Steam launcher contract: PASS"
