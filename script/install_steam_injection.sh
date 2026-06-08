#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
STEAM_APP="/Applications/Steam.app"
RUNTIME_APP="$HOME/Library/Application Support/Steam/Steam.AppBundle/Steam"
HOOK_SOURCE="$ROOT/artifacts/compat-gate-hook/libRealSteamCompatGate.dylib"
LAUNCHER_SOURCE="$ROOT/artifacts/steam-launcher/realsteamonmac_launcher"
ENTITLEMENTS="$ROOT/config/steam-runtime-entitlements.plist"
COMPAT_SOURCE="$ROOT/compat-tool"
SUPPORT_ROOT="$HOME/Library/Application Support/RealSteamOnMac"
CLEAN_BACKUP=""

usage() {
    echo "usage: $0 --clean-backup DIRECTORY [--steam-app PATH] [--runtime-app PATH] [--support-root PATH]" >&2
    exit 2
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --clean-backup)
            [ "$#" -ge 2 ] || usage
            CLEAN_BACKUP=$2
            shift 2
            ;;
        --steam-app)
            [ "$#" -ge 2 ] || usage
            STEAM_APP=$2
            shift 2
            ;;
        --runtime-app)
            [ "$#" -ge 2 ] || usage
            RUNTIME_APP=$2
            shift 2
            ;;
        --support-root)
            [ "$#" -ge 2 ] || usage
            SUPPORT_ROOT=$2
            shift 2
            ;;
        *)
            usage
            ;;
    esac
done

[ -n "$CLEAN_BACKUP" ] || usage
[ -d "$STEAM_APP" ] || {
    echo "Steam app not found: $STEAM_APP" >&2
    exit 1
}
[ -d "$RUNTIME_APP" ] || {
    echo "Steam runtime app not found: $RUNTIME_APP" >&2
    exit 1
}
[ -d "$CLEAN_BACKUP/Steam.app" ] || {
    echo "clean Steam backup not found: $CLEAN_BACKUP/Steam.app" >&2
    exit 1
}
[ -d "$CLEAN_BACKUP/SteamRuntime.app" ] || {
    echo "clean Steam runtime backup not found: $CLEAN_BACKUP/SteamRuntime.app" >&2
    exit 1
}
[ -f "$HOOK_SOURCE" ] || {
    echo "hook is not built: $HOOK_SOURCE" >&2
    exit 1
}
[ -x "$LAUNCHER_SOURCE" ] || {
    echo "launcher is not built: $LAUNCHER_SOURCE" >&2
    exit 1
}
[ -f "$ENTITLEMENTS" ] || {
    echo "runtime entitlements are missing: $ENTITLEMENTS" >&2
    exit 1
}
[ -d "$COMPAT_SOURCE/realsteamonmac-experimental" ] || {
    echo "compatibility tool source is missing: $COMPAT_SOURCE" >&2
    exit 1
}

INFO_PLIST="$STEAM_APP/Contents/Info.plist"
EXECUTABLE="$STEAM_APP/Contents/MacOS/steam_osx"
ORIGINAL_BOOTSTRAP_TARGET="$STEAM_APP/Contents/MacOS/steam_osx.original"
LAUNCHER_TARGET="$STEAM_APP/Contents/MacOS/realsteamonmac_launcher"
RUNTIME_EXECUTABLE="$RUNTIME_APP/Contents/MacOS/steam_osx"
BACKUP_EXECUTABLE="$CLEAN_BACKUP/Steam.app/Contents/MacOS/steam_osx"
BACKUP_RUNTIME_EXECUTABLE="$CLEAN_BACKUP/SteamRuntime.app/Contents/MacOS/steam_osx"

for required in \
    "$INFO_PLIST" \
    "$RUNTIME_EXECUTABLE" \
    "$BACKUP_EXECUTABLE" \
    "$BACKUP_RUNTIME_EXECUTABLE"; do
    [ -f "$required" ] || {
        echo "required file is missing: $required" >&2
        exit 1
    }
done

CURRENT_BOOTSTRAP="$EXECUTABLE"
if [ -f "$ORIGINAL_BOOTSTRAP_TARGET" ]; then
    CURRENT_BOOTSTRAP="$ORIGINAL_BOOTSTRAP_TARGET"
fi
[ -f "$CURRENT_BOOTSTRAP" ] || {
    echo "Steam bootstrap executable is missing" >&2
    exit 1
}

if pgrep -f "^$RUNTIME_EXECUTABLE( |$)" >/dev/null 2>&1; then
    echo "Steam is running; refusing to modify its runtime executable" >&2
    exit 1
fi

TMP_ROOT=$(mktemp -d)
trap 'rm -rf "$TMP_ROOT"' EXIT

same_macho_content() {
    left=$1
    right=$2
    left_copy="$TMP_ROOT/left.$$.macho"
    right_copy="$TMP_ROOT/right.$$.macho"
    cp -X "$left" "$left_copy"
    cp -X "$right" "$right_copy"
    codesign --remove-signature "$left_copy" >/dev/null 2>&1 || true
    codesign --remove-signature "$right_copy" >/dev/null 2>&1 || true
    cmp -s "$left_copy" "$right_copy"
}

if ! same_macho_content "$CURRENT_BOOTSTRAP" "$BACKUP_EXECUTABLE"; then
    CURRENT_BOOTSTRAP_SIGNATURE=$(codesign -dvv \
        "$CURRENT_BOOTSTRAP" 2>&1 || true)
    CURRENT_APP_EXECUTABLE=$(/usr/libexec/PlistBuddy -c \
        'Print :CFBundleExecutable' "$INFO_PLIST" 2>/dev/null || true)
    PROJECT_BOOTSTRAP=false
    if [ "$CURRENT_APP_EXECUTABLE" = "realsteamonmac_launcher" ] &&
        printf '%s\n' "$CURRENT_BOOTSTRAP_SIGNATURE" |
            grep -Fq 'Identifier=com.valvesoftware.steam.bootstrap' &&
        printf '%s\n' "$CURRENT_BOOTSTRAP_SIGNATURE" |
            grep -Fq 'Signature=adhoc'; then
        PROJECT_BOOTSTRAP=true
    fi
    LEGACY_HOOK=$(/usr/libexec/PlistBuddy -c \
        'Print :LSEnvironment:DYLD_INSERT_LIBRARIES' \
        "$INFO_PLIST" 2>/dev/null || true)
    LEGACY_ENABLED=$(/usr/libexec/PlistBuddy -c \
        'Print :LSEnvironment:REALSTEAMONMAC_FORCE_COMPAT' \
        "$INFO_PLIST" 2>/dev/null || true)
    LEGACY_TOOLS=$(/usr/libexec/PlistBuddy -c \
        'Print :LSEnvironment:STEAM_EXTRA_COMPAT_TOOLS_PATHS' \
        "$INFO_PLIST" 2>/dev/null || true)
    if [ "$PROJECT_BOOTSTRAP" != true ] &&
        { [ "$LEGACY_HOOK" != "$SUPPORT_ROOT/libRealSteamCompatGate.dylib" ] ||
          [ "$LEGACY_ENABLED" != "1" ] ||
          [ "$LEGACY_TOOLS" != "$SUPPORT_ROOT/compat-tool" ]; }; then
        echo "Steam bootstrap executable differs from the clean backup" >&2
        exit 1
    fi
fi

if ! same_macho_content "$RUNTIME_EXECUTABLE" "$BACKUP_RUNTIME_EXECUTABLE"; then
    RUNTIME_SIGNATURE=$(codesign -dvv "$RUNTIME_EXECUTABLE" 2>&1 || true)
    RUNTIME_ENTITLEMENTS=$(codesign -d --entitlements :- \
        "$RUNTIME_EXECUTABLE" 2>/dev/null || true)
    VALVE_SIGNED=false
    PROJECT_SIGNED=false
    if printf '%s\n' "$RUNTIME_SIGNATURE" |
        grep -Fq 'Authority=Developer ID Application: Valve Corporation'; then
        VALVE_SIGNED=true
    fi
    if printf '%s\n' "$RUNTIME_SIGNATURE" |
        grep -Fq 'Identifier=com.valvesoftware.steam' &&
        printf '%s\n' "$RUNTIME_SIGNATURE" | grep -Fq 'Signature=adhoc' &&
        printf '%s\n' "$RUNTIME_ENTITLEMENTS" |
            grep -Fq 'com.apple.security.cs.allow-dyld-environment-variables' &&
        printf '%s\n' "$RUNTIME_ENTITLEMENTS" |
            grep -Fq 'com.apple.security.cs.disable-library-validation'; then
        PROJECT_SIGNED=true
    fi
    if [ "$VALVE_SIGNED" != true ] && [ "$PROJECT_SIGNED" != true ]; then
        echo "Steam runtime is neither the clean backup nor a Valve-signed update" >&2
        exit 1
    fi
fi

mkdir -p "$SUPPORT_ROOT"
HOOK_TARGET="$SUPPORT_ROOT/libRealSteamCompatGate.dylib"
COMPAT_TARGET="$SUPPORT_ROOT/compat-tool"

cp "$HOOK_SOURCE" "$HOOK_TARGET"
rm -rf "$COMPAT_TARGET"
cp -R "$COMPAT_SOURCE" "$COMPAT_TARGET"
chmod +x "$COMPAT_TARGET/realsteamonmac-experimental/run"
codesign --force --sign - "$HOOK_TARGET"

if [ ! -f "$SUPPORT_ROOT/allowlist.txt" ]; then
    cp "$ROOT/config/allowlist.txt" "$SUPPORT_ROOT/allowlist.txt"
    chmod 0600 "$SUPPORT_ROOT/allowlist.txt"
fi

# Preserve the clean Valve bootstrap as a standalone fallback executable.
SIGNED_BOOTSTRAP="$TMP_ROOT/steam_osx.original"
cp -X "$BACKUP_EXECUTABLE" "$SIGNED_BOOTSTRAP"
chmod 0755 "$SIGNED_BOOTSTRAP"
codesign --force --sign - \
    --identifier com.valvesoftware.steam.bootstrap \
    "$SIGNED_BOOTSTRAP"
mv "$SIGNED_BOOTSTRAP" "$ORIGINAL_BOOTSTRAP_TARGET"
rm -f "$EXECUTABLE"

cp "$LAUNCHER_SOURCE" "$LAUNCHER_TARGET"
chmod 0755 "$LAUNCHER_TARGET"
codesign --force --sign - "$LAUNCHER_TARGET"
if [ -L "$STEAM_APP/Contents/MacOS/steam.sh" ]; then
    ln -sfn realsteamonmac_launcher "$STEAM_APP/Contents/MacOS/steam.sh"
fi

SIGNED_RUNTIME="$TMP_ROOT/steam_osx.signed"
cp -X "$RUNTIME_EXECUTABLE" "$SIGNED_RUNTIME"
chmod 0755 "$SIGNED_RUNTIME"
codesign --force --sign - \
    --identifier com.valvesoftware.steam \
    --entitlements "$ENTITLEMENTS" \
    "$SIGNED_RUNTIME"
codesign --verify --strict "$SIGNED_RUNTIME"
mv "$SIGNED_RUNTIME" "$RUNTIME_EXECUTABLE"

if /usr/libexec/PlistBuddy -c 'Print :CFBundleExecutable' \
    "$INFO_PLIST" >/dev/null 2>&1; then
    /usr/libexec/PlistBuddy -c \
        'Set :CFBundleExecutable realsteamonmac_launcher' "$INFO_PLIST"
else
    /usr/libexec/PlistBuddy -c \
        'Add :CFBundleExecutable string realsteamonmac_launcher' "$INFO_PLIST"
fi

for key in \
    DYLD_INSERT_LIBRARIES \
    REALSTEAMONMAC_FORCE_COMPAT \
    STEAM_EXTRA_COMPAT_TOOLS_PATHS; do
    /usr/libexec/PlistBuddy -c "Delete :LSEnvironment:$key" \
        "$INFO_PLIST" >/dev/null 2>&1 || true
done

plutil -lint "$INFO_PLIST" >/dev/null
codesign --force --sign - "$STEAM_APP"
codesign --verify --deep --strict "$STEAM_APP"
touch "$STEAM_APP"

test "$(/usr/libexec/PlistBuddy -c \
    'Print :CFBundleExecutable' "$INFO_PLIST")" = \
    "realsteamonmac_launcher"
for key in \
    DYLD_INSERT_LIBRARIES \
    REALSTEAMONMAC_FORCE_COMPAT \
    STEAM_EXTRA_COMPAT_TOOLS_PATHS; do
    if /usr/libexec/PlistBuddy -c "Print :LSEnvironment:$key" \
        "$INFO_PLIST" >/dev/null 2>&1; then
        echo "unexpected legacy LSEnvironment key remains: $key" >&2
        exit 1
    fi
done
codesign -d --entitlements :- "$RUNTIME_EXECUTABLE" 2>/dev/null |
    grep -q 'com.apple.security.cs.allow-dyld-environment-variables'

printf 'steam_app=%s\n' "$STEAM_APP"
printf 'runtime_app=%s\n' "$RUNTIME_APP"
printf 'launcher=%s\n' "$LAUNCHER_TARGET"
printf 'hook=%s\n' "$HOOK_TARGET"
printf 'compat_tools=%s\n' "$COMPAT_TARGET"
printf 'allowlist=%s\n' "$SUPPORT_ROOT/allowlist.txt"
printf 'rollback_source=%s\n' "$CLEAN_BACKUP"
