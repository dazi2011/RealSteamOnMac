#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
HOOK_BUILDER=${REALSTEAMONMAC_HOOK_BUILDER:-"$ROOT/script/build_compat_gate_hook.sh"}
LAUNCHER_BUILDER=${REALSTEAMONMAC_LAUNCHER_BUILDER:-"$ROOT/script/build_steam_launcher.sh"}
BRIDGE_BUILDER=${REALSTEAMONMAC_BRIDGE_BUILDER:-"$ROOT/script/build_lsteamclient_bridge.sh"}
RUNTIME_INSTALLER=${REALSTEAMONMAC_RUNTIME_INSTALLER:-"$ROOT/script/install_runtime_package.sh"}
INJECTION_INSTALLER=${REALSTEAMONMAC_INJECTION_INSTALLER:-"$ROOT/script/install_steam_injection.sh"}

STEAM_APP="/Applications/Steam.app"
STEAM_RUNTIME="$HOME/Library/Application Support/Steam/Steam.AppBundle/Steam"
SUPPORT_ROOT="$HOME/Library/Application Support/RealSteamOnMac"
RUNTIME_ROOT="$SUPPORT_ROOT/runtimes"
RUNTIME_ROOT_SET=false
CACHE_DIR="$HOME/Library/Caches/RealSteamOnMac/downloads"
CLEAN_BACKUP=""
GPTK_DMG=""
GPTK_REDIST=""
STEAMWORKS_BRIDGE=""

usage() {
    cat >&2 <<EOF
usage: $0 --clean-backup DIRECTORY --gptk-dmg PATH [options]
       $0 --clean-backup DIRECTORY --gptk-redist DIRECTORY [options]

options:
  --steam-app PATH
  --runtime-app PATH
  --support-root DIRECTORY
  --runtime-root DIRECTORY
  --cache-dir DIRECTORY
  --steamworks-bridge DIRECTORY
EOF
    exit 2
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --clean-backup)
            [ "$#" -ge 2 ] || usage
            CLEAN_BACKUP=$2
            shift 2
            ;;
        --gptk-dmg)
            [ "$#" -ge 2 ] || usage
            GPTK_DMG=$2
            shift 2
            ;;
        --gptk-redist)
            [ "$#" -ge 2 ] || usage
            GPTK_REDIST=$2
            shift 2
            ;;
        --steam-app)
            [ "$#" -ge 2 ] || usage
            STEAM_APP=$2
            shift 2
            ;;
        --runtime-app)
            [ "$#" -ge 2 ] || usage
            STEAM_RUNTIME=$2
            shift 2
            ;;
        --support-root)
            [ "$#" -ge 2 ] || usage
            SUPPORT_ROOT=$2
            shift 2
            ;;
        --runtime-root)
            [ "$#" -ge 2 ] || usage
            RUNTIME_ROOT=$2
            RUNTIME_ROOT_SET=true
            shift 2
            ;;
        --cache-dir)
            [ "$#" -ge 2 ] || usage
            CACHE_DIR=$2
            shift 2
            ;;
        --steamworks-bridge)
            [ "$#" -ge 2 ] || usage
            STEAMWORKS_BRIDGE=$2
            shift 2
            ;;
        *)
            usage
            ;;
    esac
done

[ -n "$CLEAN_BACKUP" ] || usage
if [ -n "$GPTK_DMG" ] && [ -n "$GPTK_REDIST" ]; then
    usage
fi
if [ -z "$GPTK_DMG" ] && [ -z "$GPTK_REDIST" ]; then
    usage
fi
if [ "$RUNTIME_ROOT_SET" = false ]; then
    RUNTIME_ROOT="$SUPPORT_ROOT/runtimes"
fi

RUNTIME_EXECUTABLE="$STEAM_RUNTIME/Contents/MacOS/steam_osx"
if pgrep -f "^$RUNTIME_EXECUTABLE( |$)" >/dev/null 2>&1; then
    echo "Steam is running; quit it before the one-click install" >&2
    exit 1
fi

for executable in \
    "$HOOK_BUILDER" \
    "$LAUNCHER_BUILDER" \
    "$BRIDGE_BUILDER" \
    "$RUNTIME_INSTALLER" \
    "$INJECTION_INSTALLER"; do
    [ -x "$executable" ] || {
        echo "required installer component is not executable: $executable" >&2
        exit 1
    }
done

"$HOOK_BUILDER"
"$LAUNCHER_BUILDER"

if [ -z "$STEAMWORKS_BRIDGE" ]; then
    STEAMWORKS_BRIDGE="$SUPPORT_ROOT/build/lsteamclient-proton11b5-macos2"
    "$BRIDGE_BUILDER" --output "$STEAMWORKS_BRIDGE"
fi

if [ -n "$GPTK_DMG" ]; then
    "$RUNTIME_INSTALLER" \
        --gptk-dmg "$GPTK_DMG" \
        --steamworks-bridge "$STEAMWORKS_BRIDGE" \
        --runtime-root "$RUNTIME_ROOT" \
        --support-root "$SUPPORT_ROOT" \
        --cache-dir "$CACHE_DIR"
else
    "$RUNTIME_INSTALLER" \
        --gptk-redist "$GPTK_REDIST" \
        --steamworks-bridge "$STEAMWORKS_BRIDGE" \
        --runtime-root "$RUNTIME_ROOT" \
        --support-root "$SUPPORT_ROOT" \
        --cache-dir "$CACHE_DIR"
fi

"$INJECTION_INSTALLER" \
    --clean-backup "$CLEAN_BACKUP" \
    --steam-app "$STEAM_APP" \
    --runtime-app "$STEAM_RUNTIME" \
    --support-root "$SUPPORT_ROOT"

echo "RealSteamOnMac one-click installation completed"
echo "runtime=$RUNTIME_ROOT/current"
echo "support=$SUPPORT_ROOT"
