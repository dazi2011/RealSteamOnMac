#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
STEAM_APP="/Applications/Steam.app"
RUNTIME_APP="$HOME/Library/Application Support/Steam/Steam.AppBundle/Steam"
HOOK_SOURCE="$ROOT/artifacts/compat-gate-hook/libRealSteamCompatGate.dylib"
ENGINE_SOURCE="$ROOT/artifacts/compat-gate-hook/libRealSteamNativeEngine.dylib"
LAUNCHER_SOURCE="$ROOT/artifacts/steam-launcher/realsteamonmac_launcher"
ENTITLEMENTS="$ROOT/config/steam-runtime-entitlements.plist"
COMPAT_SOURCE="$ROOT/compat-tool"
COMPAT_CATALOG_SOURCE="$ROOT/runtime/compat_tool_catalog.py"
PATCHER_SOURCE="$ROOT/script/patch_steamui.py"
UI_SOURCE="$ROOT/ui/realsteamonmac_ui.js"
DEPENDENCY_SOURCE="$ROOT/config/dependencies.json"
SUPPORT_ROOT="$HOME/Library/Application Support/RealSteamOnMac"
COMPAT_TOOLS_ROOT="$HOME/Library/Application Support/Steam/compatibilitytools.d"
CLEAN_BACKUP=""

usage() {
    echo "usage: $0 --clean-backup DIRECTORY [--steam-app PATH] [--runtime-app PATH] [--support-root PATH] [--compat-tools-root PATH]" >&2
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
        --compat-tools-root)
            [ "$#" -ge 2 ] || usage
            COMPAT_TOOLS_ROOT=$2
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
[ -f "$ENGINE_SOURCE" ] || {
    echo "native engine is not built: $ENGINE_SOURCE" >&2
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
[ -d "$COMPAT_SOURCE/realsteamonmac-dxmt" ] || {
    echo "compatibility tool source is missing: $COMPAT_SOURCE" >&2
    exit 1
}
[ -f "$COMPAT_CATALOG_SOURCE" ] || {
    echo "compatibility tool catalog scanner is missing: $COMPAT_CATALOG_SOURCE" >&2
    exit 1
}
[ -x "$PATCHER_SOURCE" ] || {
    echo "Steam UI patcher is missing: $PATCHER_SOURCE" >&2
    exit 1
}
[ -f "$UI_SOURCE" ] || {
    echo "Steam UI source is missing: $UI_SOURCE" >&2
    exit 1
}
[ -f "$DEPENDENCY_SOURCE" ] || {
    echo "dependency catalog is missing: $DEPENDENCY_SOURCE" >&2
    exit 1
}

INFO_PLIST="$STEAM_APP/Contents/Info.plist"
EXECUTABLE="$STEAM_APP/Contents/MacOS/steam_osx"
ORIGINAL_BOOTSTRAP_TARGET="$STEAM_APP/Contents/MacOS/steam_osx.original"
LAUNCHER_TARGET="$STEAM_APP/Contents/MacOS/realsteamonmac_launcher"
RUNTIME_EXECUTABLE="$RUNTIME_APP/Contents/MacOS/steam_osx"
STEAMUI_ROOT="$RUNTIME_APP/Contents/MacOS/steamui"
BACKUP_EXECUTABLE="$CLEAN_BACKUP/Steam.app/Contents/MacOS/steam_osx"
BACKUP_RUNTIME_EXECUTABLE="$CLEAN_BACKUP/SteamRuntime.app/Contents/MacOS/steam_osx"

for required in \
    "$INFO_PLIST" \
    "$RUNTIME_EXECUTABLE" \
    "$STEAMUI_ROOT/index.html" \
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
ENGINE_TARGET="$SUPPORT_ROOT/libRealSteamNativeEngine.dylib"
PATCHER_TARGET="$SUPPORT_ROOT/patch_steamui.py"
COMPAT_CATALOG_TARGET="$SUPPORT_ROOT/compat_tool_catalog.py"
UI_TARGET="$SUPPORT_ROOT/ui/realsteamonmac_ui.js"
DEPENDENCY_TARGET="$SUPPORT_ROOT/dependencies/catalog.json"

cp "$HOOK_SOURCE" "$HOOK_TARGET"
cp "$ENGINE_SOURCE" "$ENGINE_TARGET"
mkdir -p "$COMPAT_TOOLS_ROOT"
LEGACY_COMPAT_TOOL="$COMPAT_TOOLS_ROOT/realsteamonmac-experimental"
if [ -e "$LEGACY_COMPAT_TOOL" ]; then
    [ ! -L "$LEGACY_COMPAT_TOOL" ] || {
        echo "legacy compatibility tool is an unsafe symlink" >&2
        exit 1
    }
    [ -f "$LEGACY_COMPAT_TOOL/compatibilitytool.vdf" ] &&
        grep -Fq '"realsteamonmac-experimental"' \
            "$LEGACY_COMPAT_TOOL/compatibilitytool.vdf" || {
        echo "legacy compatibility tool directory is not project-owned" >&2
        exit 1
    }
    LEGACY_HOLD="$SUPPORT_ROOT/migrations/legacy-compat-tools"
    mkdir -p "$LEGACY_HOLD"
    LEGACY_DESTINATION="$LEGACY_HOLD/realsteamonmac-experimental"
    if [ -e "$LEGACY_DESTINATION" ]; then
        LEGACY_DESTINATION="$LEGACY_DESTINATION.$(date -u '+%Y%m%dT%H%M%SZ')"
    fi
    mv "$LEGACY_COMPAT_TOOL" "$LEGACY_DESTINATION"
fi
ACTIVE_RUNTIME_MANIFEST="$SUPPORT_ROOT/runtimes/current/manifest.json"
for tool in "$COMPAT_SOURCE"/*; do
    [ -f "$tool/run" ] || continue
    name=$(basename "$tool")
    rm -rf "$COMPAT_TOOLS_ROOT/$name"
done
for tool in "$COMPAT_SOURCE"/*; do
    [ -f "$tool/run" ] || continue
    name=$(basename "$tool")
    target="$COMPAT_TOOLS_ROOT/$name"
    if [ -f "$ACTIVE_RUNTIME_MANIFEST" ]; then
        supported=$(/usr/bin/python3 - \
            "$tool/realsteamonmac.json" \
            "$ACTIVE_RUNTIME_MANIFEST" <<'PY'
import json
import sys

metadata_path, manifest_path = sys.argv[1:]
with open(metadata_path, encoding="utf-8") as stream:
    metadata = json.load(stream)
with open(manifest_path, encoding="utf-8") as stream:
    manifest = json.load(stream)
renderers = manifest.get("renderers")
if not isinstance(renderers, dict):
    raise SystemExit("active runtime manifest has no renderer map")
print("true" if metadata.get("renderer") in renderers else "false")
PY
        )
        [ "$supported" = true ] || continue
    fi
    cp -R "$tool" "$target"
    if [ -f "$ACTIVE_RUNTIME_MANIFEST" ]; then
        /usr/bin/python3 - \
            "$target/realsteamonmac.json" \
            "$ACTIVE_RUNTIME_MANIFEST" <<'PY'
import json
import os
import sys
import tempfile

metadata_path, manifest_path = sys.argv[1:]
with open(metadata_path, encoding="utf-8") as stream:
    metadata = json.load(stream)
with open(manifest_path, encoding="utf-8") as stream:
    manifest = json.load(stream)
package_id = manifest.get("package_id")
if not isinstance(package_id, str) or not package_id:
    raise SystemExit("active runtime package identifier is invalid")
metadata["runtime_package"] = package_id
directory = os.path.dirname(metadata_path)
descriptor, temporary = tempfile.mkstemp(
    prefix=".realsteamonmac.json.",
    dir=directory,
)
try:
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump(metadata, stream, indent=2, sort_keys=True)
        stream.write("\n")
    os.chmod(temporary, 0o644)
    os.replace(temporary, metadata_path)
finally:
    if os.path.exists(temporary):
        os.unlink(temporary)
PY
    fi
    chmod +x "$target/run"
done
codesign --force --sign - "$HOOK_TARGET"
codesign --force --sign - "$ENGINE_TARGET"
mkdir -p "$SUPPORT_ROOT/ui"
cp "$PATCHER_SOURCE" "$PATCHER_TARGET"
cp "$COMPAT_CATALOG_SOURCE" "$COMPAT_CATALOG_TARGET"
cp "$UI_SOURCE" "$UI_TARGET"
chmod 0755 "$PATCHER_TARGET"
mkdir -p "$SUPPORT_ROOT/dependencies"
chmod 0700 "$SUPPORT_ROOT/dependencies"
DEPENDENCY_TEMP="$SUPPORT_ROOT/dependencies/.catalog.json.$$"
cp "$DEPENDENCY_SOURCE" "$DEPENDENCY_TEMP"
chmod 0600 "$DEPENDENCY_TEMP"
mv "$DEPENDENCY_TEMP" "$DEPENDENCY_TARGET"

if [ ! -f "$SUPPORT_ROOT/allowlist.txt" ]; then
    cp "$ROOT/config/allowlist.txt" "$SUPPORT_ROOT/allowlist.txt"
    chmod 0600 "$SUPPORT_ROOT/allowlist.txt"
fi

REGISTRY_TOKEN="$SUPPORT_ROOT/registry-token"
if [ ! -f "$REGISTRY_TOKEN" ]; then
    TOKEN=$(/usr/bin/uuidgen | tr -d '-')
    (umask 077 && printf '%s\n' "$TOKEN" >"$REGISTRY_TOKEN")
fi
chmod 0600 "$REGISTRY_TOKEN"
if ! grep -Eq '^[0-9A-Fa-f]{32,64}$' "$REGISTRY_TOKEN"; then
    echo "RealSteamOnMac registry token is invalid" >&2
    exit 1
fi

"$PATCHER_TARGET" install \
    --steamui-root "$STEAMUI_ROOT" \
    --ui-source "$UI_TARGET" \
    --allowlist "$SUPPORT_ROOT/allowlist.txt" \
    --dependencies "$DEPENDENCY_TARGET" \
    --compat-tools-root "$COMPAT_TOOLS_ROOT"

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
printf 'native_engine=%s\n' "$ENGINE_TARGET"
printf 'compat_tools=%s\n' "$COMPAT_TOOLS_ROOT"
printf 'allowlist=%s\n' "$SUPPORT_ROOT/allowlist.txt"
printf 'registry_token=%s\n' "$REGISTRY_TOKEN"
printf 'dependencies=%s\n' "$DEPENDENCY_TARGET"
printf 'steamui=%s\n' "$STEAMUI_ROOT"
printf 'rollback_source=%s\n' "$CLEAN_BACKUP"
