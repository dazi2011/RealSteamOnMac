#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
HOOK_BUILDER=${REALSTEAMONMAC_HOOK_BUILDER:-"$ROOT/script/build_compat_gate_hook.sh"}
LAUNCHER_BUILDER=${REALSTEAMONMAC_LAUNCHER_BUILDER:-"$ROOT/script/build_steam_launcher.sh"}
BRIDGE_BUILDER=${REALSTEAMONMAC_BRIDGE_BUILDER:-"$ROOT/script/build_lsteamclient_bridge.sh"}
GPTK_BRIDGE_BUILDER=${REALSTEAMONMAC_GPTK_BRIDGE_BUILDER:-"$ROOT/script/build_gptk_lsteamclient_bridge.sh"}
RUNTIME_INSTALLER=${REALSTEAMONMAC_RUNTIME_INSTALLER:-"$ROOT/script/install_runtime_package.sh"}
INJECTION_INSTALLER=${REALSTEAMONMAC_INJECTION_INSTALLER:-"$ROOT/script/install_steam_injection.sh"}
BACKUP_BUILDER=${REALSTEAMONMAC_BACKUP_BUILDER:-"$ROOT/script/backup_steam.sh"}
STEAM_STOPPER=${REALSTEAMONMAC_STEAM_STOPPER:-}

STEAM_APP="/Applications/Steam.app"
STEAM_RUNTIME="$HOME/Library/Application Support/Steam/Steam.AppBundle/Steam"
SUPPORT_ROOT="$HOME/Library/Application Support/RealSteamOnMac"
COMPAT_TOOLS_ROOT="$HOME/Library/Application Support/Steam/compatibilitytools.d"
RUNTIME_ROOT="$SUPPORT_ROOT/runtimes"
RUNTIME_ROOT_SET=false
CACHE_DIR="$HOME/Library/Caches/RealSteamOnMac/downloads"
BACKUP_ROOT="$HOME/RealSteamOnMac-Backups"
CLEAN_BACKUP=""
GPTK_DMG=""
GPTK_REDIST=""
WITHOUT_GPTK=false
QUIT_STEAM=false
STEAMWORKS_BRIDGE=""
GPTK_STEAMWORKS_BRIDGE=""

usage() {
    cat >&2 <<EOF
usage: $0 [--clean-backup DIRECTORY] [--gptk-dmg PATH | --gptk-redist DIRECTORY | --without-gptk] [options]

options:
  --quit-steam
  --backup-root DIRECTORY
  --steam-app PATH
  --runtime-app PATH
  --support-root DIRECTORY
  --compat-tools-root DIRECTORY
  --runtime-root DIRECTORY
  --cache-dir DIRECTORY
  --steamworks-bridge DIRECTORY
  --gptk-steamworks-bridge DIRECTORY

If no GPTK option is supplied, the installer uses
~/Downloads/Game_Porting_Toolkit_3.0.dmg when present and otherwise installs
the open Wine/DXMT/DXVK/WineD3D runtime.
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
        --without-gptk)
            WITHOUT_GPTK=true
            shift
            ;;
        --quit-steam)
            QUIT_STEAM=true
            shift
            ;;
        --backup-root)
            [ "$#" -ge 2 ] || usage
            BACKUP_ROOT=$2
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
        --compat-tools-root)
            [ "$#" -ge 2 ] || usage
            COMPAT_TOOLS_ROOT=$2
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
        --gptk-steamworks-bridge)
            [ "$#" -ge 2 ] || usage
            GPTK_STEAMWORKS_BRIDGE=$2
            shift 2
            ;;
        *)
            usage
            ;;
    esac
done

if [ -n "$GPTK_DMG" ] && [ -n "$GPTK_REDIST" ]; then
    usage
fi
if [ "$WITHOUT_GPTK" = true ] &&
    { [ -n "$GPTK_DMG" ] || [ -n "$GPTK_REDIST" ]; }; then
    usage
fi
if [ "$WITHOUT_GPTK" = false ] &&
    [ -z "$GPTK_DMG" ] && [ -z "$GPTK_REDIST" ]; then
    AUTO_GPTK_DMG="$HOME/Downloads/Game_Porting_Toolkit_3.0.dmg"
    if [ -f "$AUTO_GPTK_DMG" ]; then
        GPTK_DMG="$AUTO_GPTK_DMG"
    else
        WITHOUT_GPTK=true
    fi
fi
if [ "$RUNTIME_ROOT_SET" = false ]; then
    RUNTIME_ROOT="$SUPPORT_ROOT/runtimes"
fi

RUNTIME_EXECUTABLE="$STEAM_RUNTIME/Contents/MacOS/steam_osx"
STEAM_PACKAGE="$STEAM_RUNTIME/Contents/MacOS/package"
STATE_FILE="$SUPPORT_ROOT/install-state.json"

read_steam_info() {
    STEAM_INFO=$(/usr/bin/python3 - "$STEAM_PACKAGE" <<'PY'
import re
import sys
from pathlib import Path

package = Path(sys.argv[1])
if not package.is_dir():
    raise SystemExit(f"installed Steam package directory is missing: {package}")
if "\n" in str(package) or "\r" in str(package):
    raise SystemExit("installed Steam package path is invalid")

beta_path = package / "beta"
channel = ""
if beta_path.is_file():
    channel = beta_path.read_text(
        encoding="ascii", errors="strict"
    ).strip()
if channel and re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,31}", channel) is None:
    raise SystemExit("installed Steam beta channel is invalid")

prefix = f"steam_client_{channel}_" if channel else "steam_client_"
manifest = None
for variant in ("signed-2_", "signed_", ""):
    candidate = package / f"{prefix}{variant}osx.manifest"
    installed = package / f"{prefix}{variant}osx.installed"
    if candidate.is_file() and installed.is_file():
        manifest = candidate
        break
if manifest is None:
    label = channel or "stable"
    raise SystemExit(
        f"installed Steam build manifest is missing for channel {label}"
    )

with manifest.open(encoding="utf-8") as stream:
    content = stream.read(64 * 1024)
match = re.search(r'"version"\s+"([0-9]{8,12})"', content)
if match is None:
    raise SystemExit("installed Steam build manifest has no valid version")
print(manifest)
print(channel or "stable")
print(match.group(1))
PY
    )
    STEAM_MANIFEST=$(printf '%s\n' "$STEAM_INFO" | sed -n '1p')
    STEAM_CHANNEL=$(printf '%s\n' "$STEAM_INFO" | sed -n '2p')
    STEAM_BUILD=$(printf '%s\n' "$STEAM_INFO" | sed -n '3p')
    case "$STEAM_BUILD" in
        1780705203|1780965181|1781212412) ;;
        *)
            echo "unsupported Steam build: $STEAM_BUILD" >&2
            exit 1
            ;;
    esac
}

read_steam_info

if [ -f "$STATE_FILE" ]; then
    STATE_STEAM_INFO=$(/usr/bin/python3 - "$STATE_FILE" <<'PY'
import json
import re
import sys

with open(sys.argv[1], encoding="utf-8") as stream:
    state = json.load(stream)
value = state.get("steam_build")
if not isinstance(value, str) or re.fullmatch(r"[0-9]{8,12}", value) is None:
    raise SystemExit("installation state has no valid Steam build")
print(value)
channel = state.get("steam_channel")
if channel is None:
    print("")
elif (
    not isinstance(channel, str)
    or re.fullmatch(r"stable|[a-z0-9][a-z0-9_-]{0,31}", channel) is None
):
    raise SystemExit("installation state has an invalid Steam channel")
else:
    print(channel)
PY
    )
    STATE_STEAM_BUILD=$(printf '%s\n' "$STATE_STEAM_INFO" | sed -n '1p')
    STATE_STEAM_CHANNEL=$(printf '%s\n' "$STATE_STEAM_INFO" | sed -n '2p')
    if [ "$STATE_STEAM_BUILD" != "$STEAM_BUILD" ]; then
        echo "Steam build changed from $STATE_STEAM_BUILD to $STEAM_BUILD; uninstall RealSteamOnMac before reinstalling so a new clean rollback backup can be created" >&2
        exit 1
    fi
    if [ -n "$STATE_STEAM_CHANNEL" ] &&
        [ "$STATE_STEAM_CHANNEL" != "$STEAM_CHANNEL" ]; then
        echo "Steam channel changed from $STATE_STEAM_CHANNEL to $STEAM_CHANNEL; uninstall RealSteamOnMac before reinstalling so a new clean rollback backup can be created" >&2
        exit 1
    fi
fi

if [ -z "$CLEAN_BACKUP" ] && [ -f "$STATE_FILE" ]; then
    CLEAN_BACKUP=$(/usr/bin/python3 - "$STATE_FILE" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as stream:
    state = json.load(stream)
value = state.get("clean_backup")
if isinstance(value, str):
    print(value)
PY
    )
    if [ ! -d "$CLEAN_BACKUP/Steam.app" ] ||
        [ ! -d "$CLEAN_BACKUP/SteamRuntime.app" ]; then
        CLEAN_BACKUP=""
    fi
fi

CURRENT_BOOTSTRAP=$(
    /usr/libexec/PlistBuddy -c 'Print :CFBundleExecutable' \
        "$STEAM_APP/Contents/Info.plist" 2>/dev/null || true
)
if [ -z "$CLEAN_BACKUP" ] &&
    [ "$CURRENT_BOOTSTRAP" = "realsteamonmac_launcher" ]; then
    CLEAN_BACKUP=$(/usr/bin/python3 - "$BACKUP_ROOT" <<'PY'
import os
import sys
from pathlib import Path

root = Path(sys.argv[1])
if not root.is_dir():
    raise SystemExit(0)
for candidate in sorted(root.iterdir(), reverse=True):
    if (
        candidate.is_dir()
        and (candidate / "Steam.app").is_dir()
        and (candidate / "SteamRuntime.app").is_dir()
        and "\n" not in str(candidate)
        and "\r" not in str(candidate)
    ):
        print(candidate.resolve())
        break
PY
    )
    [ -n "$CLEAN_BACKUP" ] || {
        echo "an existing installation was detected but no clean backup is available" >&2
        exit 1
    }
fi

validate_clean_backup() {
    /usr/bin/python3 - \
        "$CLEAN_BACKUP/SteamRuntime.app/Contents/MacOS/package" \
        "$STEAM_CHANNEL" \
        "$STEAM_BUILD" <<'PY'
import re
import sys
from pathlib import Path

package = Path(sys.argv[1])
current_channel = sys.argv[2]
current_build = sys.argv[3]
if not package.is_dir():
    raise SystemExit("rollback snapshot Steam package directory is missing")
if "\n" in str(package) or "\r" in str(package):
    raise SystemExit("rollback snapshot Steam package path is invalid")

beta_path = package / "beta"
channel = ""
try:
    if beta_path.is_file():
        channel = beta_path.read_text(
            encoding="ascii", errors="strict"
        ).strip()
except (OSError, UnicodeError):
    raise SystemExit(
        "rollback snapshot Steam beta channel could not be read"
    ) from None
if channel and re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,31}", channel) is None:
    raise SystemExit("rollback snapshot Steam beta channel is invalid")

prefix = f"steam_client_{channel}_" if channel else "steam_client_"
manifest = None
try:
    for variant in ("signed-2_", "signed_", ""):
        candidate = package / f"{prefix}{variant}osx.manifest"
        installed = package / f"{prefix}{variant}osx.installed"
        if candidate.is_file() and installed.is_file():
            manifest = candidate
            break
except OSError:
    raise SystemExit(
        "rollback snapshot Steam build manifest could not be read"
    ) from None
if manifest is None:
    label = channel or "stable"
    raise SystemExit(
        f"rollback snapshot Steam build manifest is missing for channel {label}"
    )

try:
    with manifest.open(encoding="utf-8") as stream:
        content = stream.read(64 * 1024)
except (OSError, UnicodeError):
    raise SystemExit(
        "rollback snapshot Steam build manifest could not be read"
    ) from None
match = re.search(r'"version"\s+"([0-9]{8,12})"', content)
if match is None:
    raise SystemExit("rollback snapshot Steam build manifest has no valid version")

snapshot_channel = channel or "stable"
if snapshot_channel != current_channel:
    raise SystemExit(
        "current Steam channel does not match the rollback snapshot"
    )
if match.group(1) != current_build:
    raise SystemExit(
        "current Steam build does not match the rollback snapshot"
    )
PY
}

if [ -n "$CLEAN_BACKUP" ]; then
    validate_clean_backup
fi

steam_is_running() {
    pgrep -f "^$RUNTIME_EXECUTABLE( |$)" >/dev/null 2>&1
}

stop_steam() {
    if [ -n "$STEAM_STOPPER" ]; then
        "$STEAM_STOPPER" "$RUNTIME_EXECUTABLE"
        return
    fi
    /usr/bin/osascript -e 'tell application "Steam" to quit' \
        >/dev/null 2>&1 || true
    remaining=20
    while steam_is_running && [ "$remaining" -gt 0 ]; do
        sleep 1
        remaining=$((remaining - 1))
    done
    if steam_is_running; then
        pkill -TERM -f "^$RUNTIME_EXECUTABLE( |$)" || true
        sleep 3
    fi
    if steam_is_running; then
        pkill -KILL -f "^$RUNTIME_EXECUTABLE( |$)" || true
        sleep 1
    fi
}

if steam_is_running; then
    if [ "$QUIT_STEAM" != true ]; then
        echo "Steam is running; pass --quit-steam or quit it first" >&2
        exit 1
    fi
    stop_steam
    if steam_is_running; then
        echo "Steam could not be stopped safely" >&2
        exit 1
    fi
fi

read_steam_info
if [ -n "$CLEAN_BACKUP" ]; then
    validate_clean_backup
fi

for executable in \
    "$HOOK_BUILDER" \
    "$LAUNCHER_BUILDER" \
    "$BRIDGE_BUILDER" \
    "$RUNTIME_INSTALLER" \
    "$INJECTION_INSTALLER" \
    "$BACKUP_BUILDER"; do
    [ -x "$executable" ] || {
        echo "required installer component is not executable: $executable" >&2
        exit 1
    }
done
if [ "$WITHOUT_GPTK" = false ] &&
    [ -z "$GPTK_STEAMWORKS_BRIDGE" ] &&
    [ ! -x "$GPTK_BRIDGE_BUILDER" ]; then
    echo "required GPTK bridge builder is not executable: $GPTK_BRIDGE_BUILDER" >&2
    exit 1
fi

if [ -z "$CLEAN_BACKUP" ]; then
    STAMP=$(date -u '+%Y%m%dT%H%M%SZ')
    CLEAN_BACKUP="$BACKUP_ROOT/steam-$STAMP"
    "$BACKUP_BUILDER" \
        --steam-app "$STEAM_APP" \
        --runtime-app "$STEAM_RUNTIME" \
        --destination "$CLEAN_BACKUP"
    validate_clean_backup
fi

"$HOOK_BUILDER"
"$LAUNCHER_BUILDER"

if [ -z "$STEAMWORKS_BRIDGE" ]; then
    STEAMWORKS_BRIDGE="$SUPPORT_ROOT/build/lsteamclient-proton11b5-macos2"
    "$BRIDGE_BUILDER" --output "$STEAMWORKS_BRIDGE"
fi
if [ "$WITHOUT_GPTK" = false ] &&
    [ -z "$GPTK_STEAMWORKS_BRIDGE" ]; then
    GPTK_STEAMWORKS_BRIDGE="$SUPPORT_ROOT/build/lsteamclient-proton7-gptk7.7-macos1"
    "$GPTK_BRIDGE_BUILDER" --output "$GPTK_STEAMWORKS_BRIDGE"
fi

if [ "$WITHOUT_GPTK" = true ]; then
    "$RUNTIME_INSTALLER" \
        --without-gptk \
        --steamworks-bridge "$STEAMWORKS_BRIDGE" \
        --runtime-root "$RUNTIME_ROOT" \
        --support-root "$SUPPORT_ROOT" \
        --cache-dir "$CACHE_DIR"
elif [ -n "$GPTK_DMG" ]; then
    "$RUNTIME_INSTALLER" \
        --gptk-dmg "$GPTK_DMG" \
        --steamworks-bridge "$STEAMWORKS_BRIDGE" \
        --gptk-steamworks-bridge "$GPTK_STEAMWORKS_BRIDGE" \
        --runtime-root "$RUNTIME_ROOT" \
        --support-root "$SUPPORT_ROOT" \
        --cache-dir "$CACHE_DIR"
else
    "$RUNTIME_INSTALLER" \
        --gptk-redist "$GPTK_REDIST" \
        --steamworks-bridge "$STEAMWORKS_BRIDGE" \
        --gptk-steamworks-bridge "$GPTK_STEAMWORKS_BRIDGE" \
        --runtime-root "$RUNTIME_ROOT" \
        --support-root "$SUPPORT_ROOT" \
        --cache-dir "$CACHE_DIR"
fi

"$INJECTION_INSTALLER" \
    --clean-backup "$CLEAN_BACKUP" \
    --steam-app "$STEAM_APP" \
    --runtime-app "$STEAM_RUNTIME" \
    --support-root "$SUPPORT_ROOT" \
    --compat-tools-root "$COMPAT_TOOLS_ROOT"

mkdir -p "$SUPPORT_ROOT"
STATE_TEMP="$SUPPORT_ROOT/.install-state.json.$$"
/usr/bin/python3 - \
    "$STATE_TEMP" \
    "$CLEAN_BACKUP" \
    "$STEAM_APP" \
    "$STEAM_RUNTIME" \
    "$SUPPORT_ROOT" \
    "$RUNTIME_ROOT" \
    "$COMPAT_TOOLS_ROOT" \
    "$ROOT/compat-tool" \
    "$ROOT/VERSION" \
    "$STEAM_BUILD" \
    "$STEAM_CHANNEL" <<'PY'
import datetime
import hashlib
import json
import os
import sys

(
    output,
    clean_backup,
    steam_app,
    runtime_app,
    support_root,
    runtime_root,
    compat_tools_root,
    source_tools_root,
    version_path,
    steam_build,
    steam_channel,
) = sys.argv[1:]
with open(
    os.path.join(runtime_root, "current", "manifest.json"),
    encoding="utf-8",
) as stream:
    manifest = json.load(stream)
managed_tools = []
for name in sorted(os.listdir(source_tools_root)):
    installed_metadata = os.path.join(
        compat_tools_root, name, "realsteamonmac.json"
    )
    if not os.path.isfile(installed_metadata):
        continue
    with open(installed_metadata, "rb") as stream:
        digest = hashlib.sha256(stream.read()).hexdigest()
    managed_tools.append(
        {"name": name, "metadata_sha256": digest}
    )
state = {
    "schema": 1,
    "version": open(
        version_path, encoding="ascii"
    ).read().strip(),
    "installed_utc": datetime.datetime.now(
        datetime.timezone.utc
    ).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    "clean_backup": os.path.abspath(clean_backup),
    "steam_app": os.path.abspath(steam_app),
    "runtime_app": os.path.abspath(runtime_app),
    "support_root": os.path.abspath(support_root),
    "runtime_root": os.path.abspath(runtime_root),
    "compat_tools_root": os.path.abspath(compat_tools_root),
    "steam_build": steam_build,
    "steam_channel": steam_channel,
    "runtime_package": manifest["package_id"],
    "managed_compat_tools": managed_tools,
}
with open(output, "w", encoding="utf-8") as stream:
    json.dump(state, stream, indent=2, sort_keys=True)
    stream.write("\n")
PY
chmod 0600 "$STATE_TEMP"
mv "$STATE_TEMP" "$STATE_FILE"

echo "RealSteamOnMac one-click installation completed"
echo "runtime=$RUNTIME_ROOT/current"
echo "support=$SUPPORT_ROOT"
echo "backup=$CLEAN_BACKUP"
echo "state=$STATE_FILE"
