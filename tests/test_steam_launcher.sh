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
mkdir -p "$HOME_ROOT" "$SUPPORT/compat-tool"
touch "$SUPPORT/libRealSteamCompatGate.dylib"
printf '%s\n' '#!/bin/sh' 'exit 0' >"$RUNTIME"
chmod +x "$RUNTIME"

HOME="$HOME_ROOT" \
REALSTEAMONMAC_RUNTIME_EXECUTABLE="$RUNTIME" \
REALSTEAMONMAC_SUPPORT_ROOT="$SUPPORT" \
REALSTEAMONMAC_LAUNCHER_DRY_RUN=1 \
    "$LAUNCHER" -cef-enable-debugging >"$CAPTURE"

grep -Fq "dyld=$SUPPORT/libRealSteamCompatGate.dylib" "$CAPTURE"
grep -Fq "enabled=1" "$CAPTURE"
grep -Fq "tools=$SUPPORT/compat-tool" "$CAPTURE"
grep -Fq "args=-skipinitialbootstrap -cef-enable-debugging" "$CAPTURE"

echo "Steam launcher contract: PASS"
