#!/bin/sh
set -eu

STEAM_APP="/Applications/Steam.app"
RUNTIME_APP="$HOME/Library/Application Support/Steam/Steam.AppBundle/Steam"
SUPPORT_ROOT="$HOME/Library/Application Support/RealSteamOnMac"
CLEAN_BACKUP=""
HOLD_ROOT="$HOME/RealSteamOnMac-Rollback"

usage() {
    echo "usage: $0 --clean-backup DIRECTORY [--steam-app PATH] [--runtime-app PATH] [--support-root PATH] [--hold-root PATH]" >&2
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
        --hold-root)
            [ "$#" -ge 2 ] || usage
            HOLD_ROOT=$2
            shift 2
            ;;
        *)
            usage
            ;;
    esac
done

[ -n "$CLEAN_BACKUP" ] || usage
BACKUP_APP="$CLEAN_BACKUP/Steam.app"
BACKUP_RUNTIME="$CLEAN_BACKUP/SteamRuntime.app"
BACKUP_RUNTIME_EXECUTABLE="$BACKUP_RUNTIME/Contents/MacOS/steam_osx"
BACKUP_STEAMCLIENT="$BACKUP_RUNTIME/Contents/MacOS/steamclient.dylib"
RUNTIME_EXECUTABLE="$RUNTIME_APP/Contents/MacOS/steam_osx"
RUNTIME_STEAMCLIENT="$RUNTIME_APP/Contents/MacOS/steamclient.dylib"
STEAMUI_ROOT="$RUNTIME_APP/Contents/MacOS/steamui"
STEAMUI_PATCHER="$SUPPORT_ROOT/patch_steamui.py"
STEAMUI_INDEX_BACKUP="$STEAMUI_ROOT/index.html.realsteamonmac.original"
STEAMUI_COMPAT_BACKUP="$STEAMUI_ROOT/chunk~2dcc5aaf7.js.realsteamonmac.original"

[ -d "$BACKUP_APP" ] || {
    echo "backup Steam.app is missing: $BACKUP_APP" >&2
    exit 1
}
[ -f "$BACKUP_RUNTIME_EXECUTABLE" ] || {
    echo "backup runtime executable is missing" >&2
    exit 1
}
[ -d "$STEAM_APP" ] || {
    echo "installed Steam.app is missing: $STEAM_APP" >&2
    exit 1
}
[ -f "$RUNTIME_EXECUTABLE" ] || {
    echo "installed runtime executable is missing" >&2
    exit 1
}

if pgrep -f "^$RUNTIME_EXECUTABLE( |$)" >/dev/null 2>&1; then
    echo "Steam is running; refusing to restore live files" >&2
    exit 1
fi

if [ -e "$STEAMUI_INDEX_BACKUP" ] || [ -e "$STEAMUI_COMPAT_BACKUP" ]; then
    [ -f "$STEAMUI_INDEX_BACKUP" ] &&
        [ -f "$STEAMUI_COMPAT_BACKUP" ] || {
        echo "Steam UI patch backups are incomplete; refusing rollback" >&2
        exit 1
    }
    [ -x "$STEAMUI_PATCHER" ] || {
        echo "Steam UI patcher is unavailable; refusing rollback" >&2
        exit 1
    }
    "$STEAMUI_PATCHER" restore --steamui-root "$STEAMUI_ROOT"
fi

STAMP=$(date -u '+%Y%m%dT%H%M%SZ')
HOLD="$HOLD_ROOT/$STAMP"
mkdir -p "$HOLD"

APP_PARENT=$(dirname "$STEAM_APP")
APP_NAME=$(basename "$STEAM_APP")
STAGE="$APP_PARENT/.$APP_NAME.restore.$$"
trap 'rm -rf "$STAGE"' EXIT
ditto --rsrc --extattr --acl "$BACKUP_APP" "$STAGE"

mv "$STEAM_APP" "$HOLD/Steam.app.modified"
if ! mv "$STAGE" "$STEAM_APP"; then
    mv "$HOLD/Steam.app.modified" "$STEAM_APP"
    echo "failed to activate restored Steam.app" >&2
    exit 1
fi

mkdir -p "$HOLD/SteamRuntime.modified/Contents/MacOS"
cp -X "$RUNTIME_EXECUTABLE" \
    "$HOLD/SteamRuntime.modified/Contents/MacOS/steam_osx"
cp -X "$BACKUP_RUNTIME_EXECUTABLE" "$RUNTIME_EXECUTABLE"
chmod 0755 "$RUNTIME_EXECUTABLE"

if [ -f "$BACKUP_STEAMCLIENT" ] && [ -f "$RUNTIME_STEAMCLIENT" ]; then
    cp -X "$RUNTIME_STEAMCLIENT" \
        "$HOLD/SteamRuntime.modified/Contents/MacOS/steamclient.dylib"
    cp -X "$BACKUP_STEAMCLIENT" "$RUNTIME_STEAMCLIENT"
    chmod 0755 "$RUNTIME_STEAMCLIENT"
fi

if [ -e "$SUPPORT_ROOT" ]; then
    mv "$SUPPORT_ROOT" "$HOLD/RealSteamOnMac-support.disabled"
fi

printf 'restored_steam_app=%s\n' "$STEAM_APP"
printf 'restored_runtime=%s\n' "$RUNTIME_APP"
printf 'displaced_files=%s\n' "$HOLD"
printf '%s\n' \
    'note=CompatToolMapping for AppID 1118200 was intentionally not removed from config.vdf'
