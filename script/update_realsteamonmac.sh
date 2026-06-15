#!/bin/sh
set -eu

PAYLOAD_ROOT=""
HOME_ROOT=${HOME:-}
ALLOW_TEST_PATHS=${REALSTEAMONMAC_UPDATE_ALLOW_TEST_PATHS:-0}
INSTALLER_OVERRIDE=${REALSTEAMONMAC_UPDATE_INSTALLER:-}

usage() {
    echo "usage: $0 --payload-root DIRECTORY --home DIRECTORY" >&2
    exit 2
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --payload-root)
            [ "$#" -ge 2 ] || usage
            PAYLOAD_ROOT=$2
            shift 2
            ;;
        --home)
            [ "$#" -ge 2 ] || usage
            HOME_ROOT=$2
            shift 2
            ;;
        *)
            usage
            ;;
    esac
done

[ -d "$PAYLOAD_ROOT" ] || usage
[ -d "$HOME_ROOT" ] || usage

STATE_FILE="$HOME_ROOT/Library/Application Support/RealSteamOnMac/install-state.json"
PAYLOAD_VERSION_FILE="$PAYLOAD_ROOT/VERSION"
INSTALLER=${INSTALLER_OVERRIDE:-"$PAYLOAD_ROOT/script/install_realsteamonmac.sh"}
BRIDGE="$PAYLOAD_ROOT/prebuilt/lsteamclient-proton11b5-macos2"
GPTK_BRIDGE="$PAYLOAD_ROOT/prebuilt/lsteamclient-proton7-gptk7.7-macos1"
VERIFIER="$PAYLOAD_ROOT/prebuilt/realsteamonmac-verify-signature"

[ -f "$STATE_FILE" ] || {
    echo "RealSteamOnMac is not installed: $STATE_FILE" >&2
    exit 1
}
[ -f "$PAYLOAD_VERSION_FILE" ] || {
    echo "update payload version is missing" >&2
    exit 1
}
[ -x "$INSTALLER" ] || {
    echo "update installer is missing: $INSTALLER" >&2
    exit 1
}
[ -f "$BRIDGE/x86_64-windows/lsteamclient.dll" ] || {
    echo "update Steamworks bridge is incomplete" >&2
    exit 1
}
[ -f "$BRIDGE/x86_64-unix/lsteamclient.so" ] || {
    echo "update Steamworks bridge is incomplete" >&2
    exit 1
}
[ -x "$VERIFIER" ] || {
    echo "update release verifier is missing" >&2
    exit 1
}

STATE_INFO=$(/usr/bin/python3 - \
    "$STATE_FILE" \
    "$PAYLOAD_VERSION_FILE" \
    "$HOME_ROOT" \
    "$ALLOW_TEST_PATHS" <<'PY'
import json
import os
import re
import sys
from pathlib import Path

state_path, version_path, home_raw, allow_test_raw = sys.argv[1:]
home = Path(home_raw).resolve()
allow_test = allow_test_raw == "1"
with open(state_path, encoding="utf-8") as stream:
    state = json.load(stream)
required = {
    "schema",
    "version",
    "clean_backup",
    "steam_app",
    "runtime_app",
    "support_root",
    "runtime_root",
    "compat_tools_root",
    "steam_build",
    "runtime_package",
    "managed_compat_tools",
}
if not isinstance(state, dict) or not required.issubset(state):
    raise SystemExit("installation state is incomplete")
if state["schema"] != 1:
    raise SystemExit("installation state schema is unsupported")
semver = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+")
if semver.fullmatch(state["version"]) is None:
    raise SystemExit("installed version is invalid")
new_version = Path(version_path).read_text(
    encoding="ascii"
).strip()
if semver.fullmatch(new_version) is None:
    raise SystemExit("update version is invalid")
old_parts = tuple(map(int, state["version"].split(".")))
new_parts = tuple(map(int, new_version.split(".")))
if new_parts <= old_parts:
    raise SystemExit(
        f"update version {new_version} is not newer than "
        f"installed version {state['version']}"
    )
if re.fullmatch(r"[0-9]{8,12}", state["steam_build"]) is None:
    raise SystemExit("installed Steam build is invalid")
state_channel = state.get("steam_channel")
if state_channel is not None and (
    not isinstance(state_channel, str)
    or re.fullmatch(
        r"stable|[a-z0-9][a-z0-9_-]{0,31}",
        state_channel,
    )
    is None
):
    raise SystemExit("installed Steam channel is invalid")
paths = {}
for key in (
    "clean_backup",
    "steam_app",
    "runtime_app",
    "support_root",
    "runtime_root",
    "compat_tools_root",
):
    value = state[key]
    if (
        not isinstance(value, str)
        or not os.path.isabs(value)
        or any(character in value for character in "\r\n\t")
    ):
        raise SystemExit(f"installation state path is invalid: {key}")
    paths[key] = Path(value).resolve()
if not allow_test:
    expected = {
        "steam_app": Path("/Applications/Steam.app"),
        "runtime_app": home
        / "Library/Application Support/Steam/Steam.AppBundle/Steam",
        "support_root": home
        / "Library/Application Support/RealSteamOnMac",
        "runtime_root": home
        / "Library/Application Support/RealSteamOnMac/runtimes",
        "compat_tools_root": home
        / "Library/Application Support/Steam/compatibilitytools.d",
    }
    for key, expected_path in expected.items():
        if paths[key] != expected_path:
            raise SystemExit(f"installation state path is unsafe: {key}")
    backup_root = home / "RealSteamOnMac-Backups"
    try:
        paths["clean_backup"].relative_to(backup_root)
    except ValueError:
        raise SystemExit("clean backup path is unsafe") from None
def read_steam_info(runtime_app, label):
    package = runtime_app / "Contents/MacOS/package"
    beta_path = package / "beta"
    channel = ""
    if beta_path.is_file():
        channel = beta_path.read_text(
            encoding="ascii", errors="strict"
        ).strip()
    if channel and re.fullmatch(
        r"[a-z0-9][a-z0-9_-]{0,31}", channel
    ) is None:
        raise SystemExit(f"{label} Steam beta channel is invalid")
    prefix = f"steam_client_{channel}_" if channel else "steam_client_"
    for variant in ("signed-2_", "signed_", ""):
        manifest = package / f"{prefix}{variant}osx.manifest"
        installed = package / f"{prefix}{variant}osx.installed"
        if not manifest.is_file() or not installed.is_file():
            continue
        content = manifest.read_text(
            encoding="utf-8", errors="strict"
        )[: 64 * 1024]
        match = re.search(
            r'"version"\s+"([0-9]{8,12})"', content
        )
        if match is not None:
            return match.group(1), channel or "stable"
    raise SystemExit(f"{label} Steam build manifest is unavailable")


current_build, current_channel = read_steam_info(
    paths["runtime_app"], "current"
)
backup_build, backup_channel = read_steam_info(
    paths["clean_backup"] / "SteamRuntime.app", "rollback"
)
if backup_build != state["steam_build"]:
    raise SystemExit(
        "rollback snapshot build does not match installation state"
    )
if current_build != state["steam_build"]:
    raise SystemExit(
        "current Steam build does not match the rollback snapshot"
    )
if current_channel != backup_channel:
    raise SystemExit(
        "current Steam channel does not match the rollback snapshot"
    )
if state_channel is not None and current_channel != state_channel:
    raise SystemExit(
        "current Steam channel does not match installation state"
    )
managed = state["managed_compat_tools"]
if not isinstance(managed, list):
    raise SystemExit("managed compatibility tools are invalid")
names = []
for entry in managed:
    if (
        not isinstance(entry, dict)
        or set(entry) != {"name", "metadata_sha256"}
        or re.fullmatch(r"realsteamonmac-[a-z0-9-]+", entry["name"])
        is None
    ):
        raise SystemExit("managed compatibility tool entry is invalid")
    names.append(entry["name"])
if len(names) != len(set(names)):
    raise SystemExit("managed compatibility tool list has duplicates")
for key in (
    "clean_backup",
    "steam_app",
    "runtime_app",
    "support_root",
    "runtime_root",
    "compat_tools_root",
):
    print(paths[key])
print(state["steam_build"])
print(current_channel)
print(state["version"])
print(new_version)
PY
)

CLEAN_BACKUP=$(printf '%s\n' "$STATE_INFO" | sed -n '1p')
STEAM_APP=$(printf '%s\n' "$STATE_INFO" | sed -n '2p')
RUNTIME_APP=$(printf '%s\n' "$STATE_INFO" | sed -n '3p')
SUPPORT_ROOT=$(printf '%s\n' "$STATE_INFO" | sed -n '4p')
RUNTIME_ROOT=$(printf '%s\n' "$STATE_INFO" | sed -n '5p')
COMPAT_TOOLS_ROOT=$(printf '%s\n' "$STATE_INFO" | sed -n '6p')
STEAM_BUILD=$(printf '%s\n' "$STATE_INFO" | sed -n '7p')
STEAM_CHANNEL=$(printf '%s\n' "$STATE_INFO" | sed -n '8p')
OLD_VERSION=$(printf '%s\n' "$STATE_INFO" | sed -n '9p')
NEW_VERSION=$(printf '%s\n' "$STATE_INFO" | sed -n '10p')

for required in \
    "$CLEAN_BACKUP/Steam.app" \
    "$CLEAN_BACKUP/SteamRuntime.app" \
    "$STEAM_APP" \
    "$RUNTIME_APP" \
    "$SUPPORT_ROOT" \
    "$RUNTIME_ROOT/packages" \
    "$COMPAT_TOOLS_ROOT"; do
    [ -e "$required" ] || {
        echo "required update state is missing: $required" >&2
        exit 1
    }
done

TRANSACTION_ROOT="$HOME_ROOT/Library/Caches/RealSteamOnMac/update-transactions"
STAMP=$(date -u '+%Y%m%dT%H%M%SZ')
TRANSACTION="$TRANSACTION_ROOT/$STAMP-$$"
SNAPSHOT="$TRANSACTION/snapshot"
ROLLBACK_ROOT="$HOME_ROOT/RealSteamOnMac-Rollback/update-$STAMP-$$"
MANAGED_NAMES="$TRANSACTION/managed-tools"
PACKAGE_NAMES="$TRANSACTION/runtime-packages"
MUTABLE_PATHS="$TRANSACTION/mutable-paths"
LOG_FILE="$TRANSACTION/update.log"

copy_path() {
    source=$1
    destination=$2
    mkdir -p "$(dirname "$destination")"
    if [ -L "$source" ]; then
        cp -P "$source" "$destination"
    elif [ -d "$source" ]; then
        ditto "$source" "$destination"
    elif [ -f "$source" ]; then
        cp -p "$source" "$destination"
    fi
}

restore_path() {
    snapshot=$1
    destination=$2
    rm -rf "$destination"
    if [ -L "$snapshot" ] || [ -e "$snapshot" ]; then
        copy_path "$snapshot" "$destination"
    fi
}

SNAPSHOT_READY=false
UPDATE_SUCCEEDED=false

rollback_update() {
    status=$1
    trap - EXIT INT TERM
    if [ "$SNAPSHOT_READY" = true ] &&
        [ "$UPDATE_SUCCEEDED" != true ]; then
        mkdir -p "$ROLLBACK_ROOT"
        restore_path "$SNAPSHOT/Steam.app" "$STEAM_APP"
        restore_path "$SNAPSHOT/SteamRuntime.app" "$RUNTIME_APP"
        while IFS= read -r relative; do
            [ -n "$relative" ] || continue
            restore_path "$SNAPSHOT/support/$relative" \
                "$SUPPORT_ROOT/$relative"
        done <"$MUTABLE_PATHS"
        while IFS= read -r name; do
            [ -n "$name" ] || continue
            restore_path "$SNAPSHOT/compat-tools/$name" \
                "$COMPAT_TOOLS_ROOT/$name"
        done <"$MANAGED_NAMES"
        for package in "$RUNTIME_ROOT/packages"/*; do
            [ -d "$package" ] || continue
            name=$(basename "$package")
            if ! grep -Fqx "$name" "$PACKAGE_NAMES"; then
                mkdir -p "$ROLLBACK_ROOT/runtime-packages"
                mv "$package" \
                    "$ROLLBACK_ROOT/runtime-packages/$name"
            fi
        done
        mv "$TRANSACTION" "$ROLLBACK_ROOT/transaction"
        echo "update failed; previous installation restored" >&2
        echo "rollback=$ROLLBACK_ROOT" >&2
    elif [ -d "$TRANSACTION" ]; then
        rm -rf "$TRANSACTION"
    fi
    exit "$status"
}
trap 'rollback_update $?' EXIT
trap 'rollback_update 130' INT
trap 'rollback_update 143' TERM

required_kb=$(
    du -sk "$STEAM_APP" "$RUNTIME_APP" |
        awk '{total += $1} END {print total + 262144}'
)
available_kb=$(df -Pk "$HOME_ROOT" | awk 'NR == 2 {print $4}')
if [ -z "$available_kb" ] || [ "$available_kb" -lt "$required_kb" ]; then
    echo "insufficient free space for transactional update snapshot" >&2
    exit 1
fi

mkdir -p "$SNAPSHOT/support" "$SNAPSHOT/compat-tools"

/usr/bin/python3 - "$STATE_FILE" "$MANAGED_NAMES" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as stream:
    state = json.load(stream)
with open(sys.argv[2], "w", encoding="utf-8") as stream:
    for entry in state["managed_compat_tools"]:
        stream.write(entry["name"] + "\n")
PY
find "$RUNTIME_ROOT/packages" -mindepth 1 -maxdepth 1 -type d \
    -exec basename {} \; | LC_ALL=C sort >"$PACKAGE_NAMES"
cat >"$MUTABLE_PATHS" <<'EOF'
install-state.json
libRealSteamCompatGate.dylib
libRealSteamNativeEngine.dylib
patch_steamui.py
compat_tool_catalog.py
allowlist.txt
registry-token
ui
dependencies
bin
release-public-key.hex
VERSION
runtimes/bin
runtimes/current
EOF

copy_path "$STEAM_APP" "$SNAPSHOT/Steam.app"
copy_path "$RUNTIME_APP" "$SNAPSHOT/SteamRuntime.app"
while IFS= read -r relative; do
    [ -n "$relative" ] || continue
    copy_path "$SUPPORT_ROOT/$relative" \
        "$SNAPSHOT/support/$relative"
done <"$MUTABLE_PATHS"
while IFS= read -r name; do
    [ -n "$name" ] || continue
    copy_path "$COMPAT_TOOLS_ROOT/$name" \
        "$SNAPSHOT/compat-tools/$name"
done <"$MANAGED_NAMES"

SNAPSHOT_READY=true

set -- \
    "$INSTALLER" \
    --quit-steam \
    --clean-backup "$CLEAN_BACKUP" \
    --steam-app "$STEAM_APP" \
    --runtime-app "$RUNTIME_APP" \
    --support-root "$SUPPORT_ROOT" \
    --compat-tools-root "$COMPAT_TOOLS_ROOT" \
    --runtime-root "$RUNTIME_ROOT" \
    --cache-dir "$HOME_ROOT/Library/Caches/RealSteamOnMac/downloads" \
    --steamworks-bridge "$BRIDGE"

GPTK_DMG="$HOME_ROOT/Downloads/Game_Porting_Toolkit_3.0.dmg"
if [ -f "$GPTK_DMG" ] &&
    [ -f "$GPTK_BRIDGE/x86_64-windows/lsteamclient.dll" ] &&
    [ -f "$GPTK_BRIDGE/x86_64-unix/lsteamclient.dll.so" ]; then
    set -- \
        "$@" \
        --gptk-dmg "$GPTK_DMG" \
        --gptk-steamworks-bridge "$GPTK_BRIDGE"
else
    set -- "$@" --without-gptk
fi

"$@" >>"$LOG_FILE" 2>&1

mkdir -p "$SUPPORT_ROOT/bin"
cp "$PAYLOAD_ROOT/script/check_for_updates.py" \
    "$SUPPORT_ROOT/bin/check-for-updates"
cp "$VERIFIER" "$SUPPORT_ROOT/bin/verify-release-signature"
cp "$PAYLOAD_ROOT/config/release-public-key.hex" \
    "$SUPPORT_ROOT/release-public-key.hex"
cp "$PAYLOAD_VERSION_FILE" "$SUPPORT_ROOT/VERSION"
chmod 0755 \
    "$SUPPORT_ROOT/bin/check-for-updates" \
    "$SUPPORT_ROOT/bin/verify-release-signature"
chmod 0644 \
    "$SUPPORT_ROOT/release-public-key.hex" \
    "$SUPPORT_ROOT/VERSION"

/usr/bin/python3 - \
    "$STATE_FILE" \
    "$NEW_VERSION" \
    "$STEAM_BUILD" \
    "$STEAM_CHANNEL" \
    "$CLEAN_BACKUP" \
    "$RUNTIME_ROOT" <<'PY'
import json
import os
import sys

(
    state_path,
    expected_version,
    expected_build,
    expected_channel,
    expected_backup,
    runtime_root,
) = sys.argv[1:]
with open(state_path, encoding="utf-8") as stream:
    state = json.load(stream)
checks = {
    "version": expected_version,
    "steam_build": expected_build,
    "steam_channel": expected_channel,
}
for key, expected in checks.items():
    if state.get(key) != expected:
        raise SystemExit(f"updated installation state mismatch: {key}")
if os.path.realpath(state.get("clean_backup", "")) != os.path.realpath(
    expected_backup
):
    raise SystemExit("updated installation state mismatch: clean_backup")
current = os.path.join(runtime_root, "current")
if not os.path.islink(current):
    raise SystemExit("updated runtime current link is missing")
manifest = os.path.join(current, "manifest.json")
if not os.path.isfile(manifest):
    raise SystemExit("updated runtime manifest is missing")
with open(manifest, encoding="utf-8") as stream:
    runtime = json.load(stream)
if runtime.get("package_id") != state.get("runtime_package"):
    raise SystemExit("updated runtime package is inconsistent")
PY

UPDATE_SUCCEEDED=true
rm -rf "$TRANSACTION"
trap - EXIT INT TERM
echo "RealSteamOnMac update completed"
echo "version=$OLD_VERSION->$NEW_VERSION"
echo "state=$STATE_FILE"
