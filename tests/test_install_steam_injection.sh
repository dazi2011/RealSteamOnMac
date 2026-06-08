#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
TMP_ROOT=$(mktemp -d)
trap 'rm -rf "$TMP_ROOT"' EXIT

"$ROOT/script/build_compat_gate_hook.sh" >/dev/null
"$ROOT/script/build_steam_launcher.sh" >/dev/null

STEAM_APP="$TMP_ROOT/Steam.app"
RUNTIME_APP="$TMP_ROOT/SteamRuntime.app"
BACKUP="$TMP_ROOT/backup"
SUPPORT="$TMP_ROOT/support"
mkdir -p "$STEAM_APP/Contents/MacOS" "$RUNTIME_APP/Contents/MacOS"

write_info_plist() {
    destination=$1
    identifier=$2
    printf '%s\n' \
        '<?xml version="1.0" encoding="UTF-8"?>' \
        '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">' \
        '<plist version="1.0"><dict>' \
        "<key>CFBundleIdentifier</key><string>$identifier</string>" \
        '<key>CFBundleExecutable</key><string>steam_osx</string>' \
        '<key>CFBundlePackageType</key><string>APPL</string>' \
        '<key>LSEnvironment</key><dict><key>LC_ALL</key><string>en_US.UTF-8</string></dict>' \
        '</dict></plist>' >"$destination"
}

write_info_plist "$STEAM_APP/Contents/Info.plist" \
    "test.realsteamonmac.steam"
write_info_plist "$RUNTIME_APP/Contents/Info.plist" \
    "test.realsteamonmac.runtime"
cp /usr/bin/true "$STEAM_APP/Contents/MacOS/steam_osx"
cp /usr/bin/true "$RUNTIME_APP/Contents/MacOS/steam_osx"
ln -s steam_osx "$STEAM_APP/Contents/MacOS/steam.sh"
codesign --force --deep --sign - "$STEAM_APP"
codesign --force --deep --sign - "$RUNTIME_APP"

mkdir -p "$BACKUP"
ditto "$STEAM_APP" "$BACKUP/Steam.app"
ditto "$RUNTIME_APP" "$BACKUP/SteamRuntime.app"

"$ROOT/script/install_steam_injection.sh" \
    --clean-backup "$BACKUP" \
    --steam-app "$STEAM_APP" \
    --runtime-app "$RUNTIME_APP" \
    --support-root "$SUPPORT"

"$ROOT/script/install_steam_injection.sh" \
    --clean-backup "$BACKUP" \
    --steam-app "$STEAM_APP" \
    --runtime-app "$RUNTIME_APP" \
    --support-root "$SUPPORT" >/dev/null

test -f "$SUPPORT/libRealSteamCompatGate.dylib"
test -x "$SUPPORT/compat-tool/realsteamonmac-experimental/run"
test -f "$SUPPORT/allowlist.txt"
test -x "$STEAM_APP/Contents/MacOS/realsteamonmac_launcher"
test -x "$STEAM_APP/Contents/MacOS/steam_osx.original"
test ! -e "$STEAM_APP/Contents/MacOS/steam_osx"
test "$(readlink "$STEAM_APP/Contents/MacOS/steam.sh")" = \
    "realsteamonmac_launcher"
test "$(/usr/libexec/PlistBuddy -c \
    'Print :CFBundleExecutable' \
    "$STEAM_APP/Contents/Info.plist")" = "realsteamonmac_launcher"
test "$(/usr/libexec/PlistBuddy -c \
    'Print :LSEnvironment:LC_ALL' \
    "$STEAM_APP/Contents/Info.plist")" = "en_US.UTF-8"
if /usr/libexec/PlistBuddy -c \
    'Print :LSEnvironment:DYLD_INSERT_LIBRARIES' \
    "$STEAM_APP/Contents/Info.plist" >/dev/null 2>&1; then
    exit 1
fi
codesign --verify --deep --strict "$STEAM_APP"
codesign -d --entitlements :- \
    "$RUNTIME_APP/Contents/MacOS/steam_osx" 2>/dev/null |
    grep -q 'com.apple.security.cs.disable-library-validation'

echo "Steam injection installer contract: PASS"
