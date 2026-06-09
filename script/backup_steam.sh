#!/bin/sh
set -eu

STEAM_APP=""
RUNTIME_APP=""
DESTINATION=""

usage() {
    echo "usage: $0 --steam-app PATH --runtime-app PATH --destination PATH" >&2
    exit 2
}

while [ "$#" -gt 0 ]; do
    case "$1" in
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
        --destination)
            [ "$#" -ge 2 ] || usage
            DESTINATION=$2
            shift 2
            ;;
        *)
            usage
            ;;
    esac
done

[ -d "$STEAM_APP" ] || {
    echo "Steam bootstrap app not found: $STEAM_APP" >&2
    exit 1
}
[ -d "$RUNTIME_APP" ] || {
    echo "Steam runtime app not found: $RUNTIME_APP" >&2
    exit 1
}
[ -n "$DESTINATION" ] || usage
[ ! -e "$DESTINATION" ] || {
    echo "backup destination already exists: $DESTINATION" >&2
    exit 1
}

RUNTIME_EXECUTABLE="$RUNTIME_APP/Contents/MacOS/steam_osx"
STEAM_EXECUTABLE_NAME=$(
    /usr/libexec/PlistBuddy -c 'Print :CFBundleExecutable' \
        "$STEAM_APP/Contents/Info.plist" 2>/dev/null || true
)
[ -n "$STEAM_EXECUTABLE_NAME" ] || {
    echo "Steam bootstrap executable name is unavailable" >&2
    exit 1
}
STEAM_EXECUTABLE="$STEAM_APP/Contents/MacOS/$STEAM_EXECUTABLE_NAME"
[ -f "$STEAM_EXECUTABLE" ] || {
    echo "Steam bootstrap executable not found: $STEAM_EXECUTABLE" >&2
    exit 1
}
if [ -x "$RUNTIME_EXECUTABLE" ] && pgrep -f "$RUNTIME_EXECUTABLE" >/dev/null 2>&1; then
    echo "Steam is still running; refusing to create a non-clean backup" >&2
    exit 1
fi

mkdir -p "$(dirname "$DESTINATION")"
mkdir "$DESTINATION"

/usr/bin/ditto --rsrc --extattr --acl "$STEAM_APP" "$DESTINATION/Steam.app"
/usr/bin/ditto --rsrc --extattr --acl "$RUNTIME_APP" "$DESTINATION/SteamRuntime.app"

verify_signature_if_source_is_strict() {
    source_bundle=$1
    copied_bundle=$2
    label=$3

    if codesign --verify --deep --strict "$source_bundle" >/dev/null 2>&1; then
        codesign --verify --deep --strict "$copied_bundle" >/dev/null
        printf '%s: OK\n' "$label"
    else
        printf '%s: SOURCE_NOT_STRICT\n' "$label"
    fi
}

{
    verify_signature_if_source_is_strict \
        "$STEAM_APP" "$DESTINATION/Steam.app" "Steam.app"
    verify_signature_if_source_is_strict \
        "$RUNTIME_APP" "$DESTINATION/SteamRuntime.app" "SteamRuntime.app"
} >"$DESTINATION/signature-status.txt"

{
    printf 'created_utc=%s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
    printf 'steam_app_source=%s\n' "$STEAM_APP"
    printf 'runtime_app_source=%s\n' "$RUNTIME_APP"
    printf 'steam_executable=%s\n' "$STEAM_EXECUTABLE_NAME"
    printf 'steam_app_bytes=%s\n' "$(du -sk "$STEAM_APP" | awk '{print $1 * 1024}')"
    printf 'runtime_app_bytes=%s\n' "$(du -sk "$RUNTIME_APP" | awk '{print $1 * 1024}')"
} >"$DESTINATION/backup-metadata.txt"

(
    cd "$DESTINATION"
    FILES="Steam.app/Contents/MacOS/$STEAM_EXECUTABLE_NAME SteamRuntime.app/Contents/MacOS/steam_osx"
    if [ -f "Steam.app/Contents/MacOS/steam_osx.original" ]; then
        FILES="$FILES Steam.app/Contents/MacOS/steam_osx.original"
    fi
    if [ -f "SteamRuntime.app/Contents/MacOS/steamclient.dylib" ]; then
        FILES="$FILES SteamRuntime.app/Contents/MacOS/steamclient.dylib"
    fi

    : >SHA256SUMS
    for file in $FILES; do
        /usr/bin/shasum -a 256 "$file" >>SHA256SUMS
    done
    /usr/bin/shasum -a 256 -c SHA256SUMS
)

echo "$DESTINATION"
