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
grep -q 'unsetenv("STEAM_EXTRA_COMPAT_TOOLS_PATHS")' "$SOURCE"
if grep -Eq \
    '(^|[^[:alnum:]_])setenv\("STEAM_EXTRA_COMPAT_TOOLS_PATHS"' \
    "$SOURCE"; then
    echo "launcher must not activate Steam's macOS compatibility-tool path" >&2
    exit 1
fi
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
touch "$SUPPORT/libRealSteamNativeEngine.dylib"
cp "$ROOT/script/patch_steamui.py" "$SUPPORT/patch_steamui.py"
cp "$ROOT/ui/realsteamonmac_ui.js" "$SUPPORT/ui/realsteamonmac_ui.js"
printf '%s\n' 1118200 >"$SUPPORT/allowlist.txt"
printf '%s\n' '#!/bin/sh' 'exit 0' >"$RUNTIME"
chmod +x "$RUNTIME"
printf '%s' \
    '<!doctype html><html style="width: 100%; height: 100%"><head><title>SharedJSContext</title><meta charset="utf-8"><script defer="defer" src="/libraries/libraries~00299a408.js"></script><script defer="defer" src="/library.js"></script><link href="/css/library.css" rel="stylesheet"></head><body style="width: 100%; height: 100%; margin: 0; overflow: hidden;"><div id="root" style="height:100%; width: 100%"></div><div style="display:none"></div></body></html>' \
    >"$STEAMUI/index.html"
printf '%s' \
    'before(0,f.CI)()&&o.push({title:(0,A.we)("#AppProperties_CompatibilityPage")middle(0,f.CI)()&&o.push({title:(0,A.we)("#AppProperties_CompatibilityPage")after' \
    >"$STEAMUI/chunk~2dcc5aaf7.js"

HOME="$HOME_ROOT" \
REALSTEAMONMAC_ALLOW_TEST_FIXTURES=1 \
REALSTEAMONMAC_RUNTIME_EXECUTABLE="$RUNTIME" \
REALSTEAMONMAC_SUPPORT_ROOT="$SUPPORT" \
REALSTEAMONMAC_LAUNCHER_DRY_RUN=1 \
    "$LAUNCHER" -cef-enable-debugging >"$CAPTURE"

grep -Fq "dyld=$SUPPORT/libRealSteamCompatGate.dylib" "$CAPTURE"
grep -Fq "engine=$SUPPORT/libRealSteamNativeEngine.dylib" "$CAPTURE"
grep -Fq "activation_delay_ms=30000" "$CAPTURE"
grep -Fq "injection_stage=bootstrap" "$CAPTURE"
grep -Fq "enabled=1" "$CAPTURE"
grep -Fq "tools=disabled" "$CAPTURE"
grep -Fq "args=-skipinitialbootstrap -cef-enable-debugging" "$CAPTURE"
grep -Fq "steamui=verified" "$CAPTURE"
grep -Fq '/realsteamonmac/ui.js' "$STEAMUI/index.html"
test -f "$STEAMUI/index.html.realsteamonmac.original"
test -f \
    "$STEAMUI/chunk~2dcc5aaf7.js.realsteamonmac.original"
test "$(grep -o '__REALSTEAMONMAC_IS_MANAGED_APP__' \
    "$STEAMUI/chunk~2dcc5aaf7.js" | wc -l)" -eq 2

echo "Steam launcher contract: PASS"
