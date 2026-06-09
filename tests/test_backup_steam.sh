#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
TMP_ROOT=$(mktemp -d)
trap 'rm -rf "$TMP_ROOT"' EXIT

STEAM_APP="$TMP_ROOT/source/Steam.app"
RUNTIME_APP="$TMP_ROOT/source/SteamRuntime.app"
DESTINATION="$TMP_ROOT/backups/steam-test"
INSTALLED_DESTINATION="$TMP_ROOT/backups/steam-installed-test"

mkdir -p "$STEAM_APP/Contents/MacOS" "$RUNTIME_APP/Contents/MacOS"
printf '%s\n' \
    '<?xml version="1.0" encoding="UTF-8"?>' \
    '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">' \
    '<plist version="1.0"><dict>' \
    '<key>CFBundleIdentifier</key><string>test.realsteamonmac.bootstrap</string>' \
    '<key>CFBundleExecutable</key><string>steam_osx</string>' \
    '<key>CFBundlePackageType</key><string>APPL</string>' \
    '</dict></plist>' >"$STEAM_APP/Contents/Info.plist"
printf '%s\n' \
    '<?xml version="1.0" encoding="UTF-8"?>' \
    '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">' \
    '<plist version="1.0"><dict>' \
    '<key>CFBundleIdentifier</key><string>test.realsteamonmac.runtime</string>' \
    '<key>CFBundleExecutable</key><string>steam_osx</string>' \
    '<key>CFBundlePackageType</key><string>APPL</string>' \
    '</dict></plist>' >"$RUNTIME_APP/Contents/Info.plist"
cp /usr/bin/true "$STEAM_APP/Contents/MacOS/steam_osx"
cp /usr/bin/true "$RUNTIME_APP/Contents/MacOS/steam_osx"
printf 'client\n' >"$RUNTIME_APP/Contents/MacOS/steamclient.dylib"
codesign --force --deep --sign - "$STEAM_APP"
codesign --force --deep --sign - "$RUNTIME_APP"

"$ROOT/script/backup_steam.sh" \
    --steam-app "$STEAM_APP" \
    --runtime-app "$RUNTIME_APP" \
    --destination "$DESTINATION"

test -f "$DESTINATION/Steam.app/Contents/MacOS/steam_osx"
test -f "$DESTINATION/SteamRuntime.app/Contents/MacOS/steam_osx"
test -f "$DESTINATION/SteamRuntime.app/Contents/MacOS/steamclient.dylib"
test -f "$DESTINATION/SHA256SUMS"
test -f "$DESTINATION/backup-metadata.txt"
test -f "$DESTINATION/signature-status.txt"
grep -q '^Steam.app: OK$' "$DESTINATION/signature-status.txt"
grep -q '^SteamRuntime.app: OK$' "$DESTINATION/signature-status.txt"

(cd "$DESTINATION" && /usr/bin/shasum -a 256 -c SHA256SUMS)

cp /usr/bin/true "$STEAM_APP/Contents/MacOS/realsteamonmac_launcher"
mv \
    "$STEAM_APP/Contents/MacOS/steam_osx" \
    "$STEAM_APP/Contents/MacOS/steam_osx.original"
/usr/libexec/PlistBuddy -c \
    'Set :CFBundleExecutable realsteamonmac_launcher' \
    "$STEAM_APP/Contents/Info.plist"
codesign --force --deep --sign - "$STEAM_APP"

"$ROOT/script/backup_steam.sh" \
    --steam-app "$STEAM_APP" \
    --runtime-app "$RUNTIME_APP" \
    --destination "$INSTALLED_DESTINATION"

test -f \
    "$INSTALLED_DESTINATION/Steam.app/Contents/MacOS/realsteamonmac_launcher"
test -f \
    "$INSTALLED_DESTINATION/Steam.app/Contents/MacOS/steam_osx.original"
grep -q \
    'Steam.app/Contents/MacOS/realsteamonmac_launcher' \
    "$INSTALLED_DESTINATION/SHA256SUMS"
grep -q \
    'Steam.app/Contents/MacOS/steam_osx.original' \
    "$INSTALLED_DESTINATION/SHA256SUMS"
(cd "$INSTALLED_DESTINATION" && /usr/bin/shasum -a 256 -c SHA256SUMS)

if "$ROOT/script/backup_steam.sh" \
    --steam-app "$STEAM_APP" \
    --runtime-app "$RUNTIME_APP" \
    --destination "$DESTINATION" >/dev/null 2>&1; then
    echo "backup script must refuse to overwrite an existing backup" >&2
    exit 1
fi

echo "steam backup contract: PASS"
