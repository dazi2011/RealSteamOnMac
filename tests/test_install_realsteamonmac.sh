#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

LOG="$TMP/calls.log"
STEAM_APP="$TMP/Steam.app"
RUNTIME_APP="$TMP/SteamRuntime.app"
BACKUP="$TMP/backup"
SUPPORT="$TMP/support"
RUNTIME_ROOT="$SUPPORT/runtimes"
CACHE="$TMP/cache"
COMPAT_TOOLS="$TMP/compatibilitytools.d"
GPTK="$TMP/GPTK.dmg"

mkdir -p \
    "$STEAM_APP" \
    "$RUNTIME_APP/Contents/MacOS/package" \
    "$BACKUP" \
    "$TMP/bin"
: >"$RUNTIME_APP/Contents/MacOS/steam_osx"
printf 'publicbeta\n' \
    >"$RUNTIME_APP/Contents/MacOS/package/beta"
cat >"$RUNTIME_APP/Contents/MacOS/package/steam_client_publicbeta_signed-2_osx.manifest" <<'EOF'
"osx"
{
    "version" "1780965181"
}
EOF
: >"$RUNTIME_APP/Contents/MacOS/package/steam_client_publicbeta_signed-2_osx.installed"
cat >"$RUNTIME_APP/Contents/MacOS/package/steam_client_publicbeta_signed_osx.manifest" <<'EOF'
"osx"
{
    "version" "1781139754"
}
EOF
: >"$RUNTIME_APP/Contents/MacOS/package/steam_client_publicbeta_signed_osx.installed"
: >"$GPTK"

make_recorder() {
    name=$1
    path="$TMP/bin/$name"
    sed \
        -e "s|@NAME@|$name|g" \
        -e "s|@LOG@|$LOG|g" \
        "$TMP/recorder.in" >"$path"
    chmod +x "$path"
}

cat >"$TMP/recorder.in" <<'EOF'
#!/bin/sh
printf '%s' '@NAME@' >>'@LOG@'
for argument in "$@"; do
    printf '\t%s' "$argument" >>'@LOG@'
done
printf '\n' >>'@LOG@'
if [ '@NAME@' = bridge ] || [ '@NAME@' = gptk_bridge ]; then
    while [ "$#" -gt 0 ]; do
        if [ "$1" = --output ]; then
            mkdir -p "$2/x86_64-windows" "$2/x86_64-unix"
            : >"$2/x86_64-windows/lsteamclient.dll"
            if [ '@NAME@' = gptk_bridge ]; then
                : >"$2/x86_64-unix/lsteamclient.dll.so"
            else
                : >"$2/x86_64-unix/lsteamclient.so"
            fi
            break
        fi
        shift
    done
fi
if [ '@NAME@' = runtime ]; then
    runtime_root=
    package_id=gptk-test-package
    renderers='"dxmt":{},"dxvk":{},"wined3d":{},"gptk":{}'
    while [ "$#" -gt 0 ]; do
        case "$1" in
            --runtime-root)
                runtime_root=$2
                shift 2
                ;;
            --without-gptk)
                package_id=open-test-package
                renderers='"dxmt":{},"dxvk":{},"wined3d":{}'
                shift
                ;;
            *)
                shift
                ;;
        esac
    done
    mkdir -p "$runtime_root/packages/$package_id"
    printf '{"schema":1,"package_id":"%s","renderers":{%s}}\n' \
        "$package_id" "$renderers" \
        >"$runtime_root/packages/$package_id/manifest.json"
    ln -s "packages/$package_id" "$runtime_root/current"
fi
if [ '@NAME@' = backup ]; then
    while [ "$#" -gt 0 ]; do
        if [ "$1" = --destination ]; then
            mkdir -p "$2/Steam.app" "$2/SteamRuntime.app"
            break
        fi
        shift
    done
fi
EOF

for name in hook launcher bridge gptk_bridge runtime injection backup; do
    make_recorder "$name"
done

env \
    REALSTEAMONMAC_HOOK_BUILDER="$TMP/bin/hook" \
    REALSTEAMONMAC_LAUNCHER_BUILDER="$TMP/bin/launcher" \
    REALSTEAMONMAC_BRIDGE_BUILDER="$TMP/bin/bridge" \
    REALSTEAMONMAC_GPTK_BRIDGE_BUILDER="$TMP/bin/gptk_bridge" \
    REALSTEAMONMAC_RUNTIME_INSTALLER="$TMP/bin/runtime" \
    REALSTEAMONMAC_INJECTION_INSTALLER="$TMP/bin/injection" \
    REALSTEAMONMAC_BACKUP_BUILDER="$TMP/bin/backup" \
    "$ROOT/script/install_realsteamonmac.sh" \
        --clean-backup "$BACKUP" \
        --gptk-dmg "$GPTK" \
        --steam-app "$STEAM_APP" \
        --runtime-app "$RUNTIME_APP" \
        --support-root "$SUPPORT" \
        --compat-tools-root "$COMPAT_TOOLS" \
        --runtime-root "$RUNTIME_ROOT" \
        --cache-dir "$CACHE"

test "$(cut -f1 "$LOG" | tr '\n' ' ')" = \
    "hook launcher bridge gptk_bridge runtime injection "
grep -Fq "bridge	--output	$SUPPORT/build/lsteamclient-proton11b5-macos2" "$LOG"
grep -Fq "gptk_bridge	--output	$SUPPORT/build/lsteamclient-proton7-gptk7.7-macos1" "$LOG"
grep -Fq "runtime	--gptk-dmg	$GPTK" "$LOG"
runtime_call=$(grep '^runtime	' "$LOG")
printf '%s\n' "$runtime_call" |
    grep -Fq "	--steamworks-bridge	$SUPPORT/build/lsteamclient-proton11b5-macos2"
printf '%s\n' "$runtime_call" |
    grep -Fq "	--gptk-steamworks-bridge	$SUPPORT/build/lsteamclient-proton7-gptk7.7-macos1"
printf '%s\n' "$runtime_call" |
    grep -Fq "	--runtime-root	$RUNTIME_ROOT"
grep -Fq "injection	--clean-backup	$BACKUP" "$LOG"
injection_call=$(grep '^injection	' "$LOG")
printf '%s\n' "$injection_call" |
    grep -Fq "	--steam-app	$STEAM_APP"
test -f "$SUPPORT/install-state.json"
grep -q '"steam_build": "1780965181"' "$SUPPORT/install-state.json"
grep -q '"steam_channel": "publicbeta"' "$SUPPORT/install-state.json"

: >"$LOG"
STABLE_SUPPORT="$TMP/stable-support"
STABLE_RUNTIME_ROOT="$STABLE_SUPPORT/runtimes"
rm "$RUNTIME_APP/Contents/MacOS/package/beta"
mv \
    "$RUNTIME_APP/Contents/MacOS/package/steam_client_publicbeta_signed-2_osx.manifest" \
    "$RUNTIME_APP/Contents/MacOS/package/steam_client_signed-2_osx.manifest"
mv \
    "$RUNTIME_APP/Contents/MacOS/package/steam_client_publicbeta_signed-2_osx.installed" \
    "$RUNTIME_APP/Contents/MacOS/package/steam_client_signed-2_osx.installed"
env \
    REALSTEAMONMAC_HOOK_BUILDER="$TMP/bin/hook" \
    REALSTEAMONMAC_LAUNCHER_BUILDER="$TMP/bin/launcher" \
    REALSTEAMONMAC_BRIDGE_BUILDER="$TMP/bin/bridge" \
    REALSTEAMONMAC_RUNTIME_INSTALLER="$TMP/bin/runtime" \
    REALSTEAMONMAC_INJECTION_INSTALLER="$TMP/bin/injection" \
    REALSTEAMONMAC_BACKUP_BUILDER="$TMP/bin/backup" \
    "$ROOT/script/install_realsteamonmac.sh" \
        --clean-backup "$BACKUP" \
        --without-gptk \
        --steam-app "$STEAM_APP" \
        --runtime-app "$RUNTIME_APP" \
        --support-root "$STABLE_SUPPORT" \
        --compat-tools-root "$COMPAT_TOOLS" \
        --runtime-root "$STABLE_RUNTIME_ROOT" \
        --cache-dir "$CACHE"
grep -q '"steam_build": "1780965181"' \
    "$STABLE_SUPPORT/install-state.json"
grep -q '"steam_channel": "stable"' \
    "$STABLE_SUPPORT/install-state.json"
mv \
    "$RUNTIME_APP/Contents/MacOS/package/steam_client_signed-2_osx.manifest" \
    "$RUNTIME_APP/Contents/MacOS/package/steam_client_publicbeta_signed-2_osx.manifest"
mv \
    "$RUNTIME_APP/Contents/MacOS/package/steam_client_signed-2_osx.installed" \
    "$RUNTIME_APP/Contents/MacOS/package/steam_client_publicbeta_signed-2_osx.installed"
printf 'publicbeta\n' \
    >"$RUNTIME_APP/Contents/MacOS/package/beta"

: >"$LOG"
sed -i '' 's/1780965181/1780705203/' \
    "$RUNTIME_APP/Contents/MacOS/package/steam_client_publicbeta_signed-2_osx.manifest"
if env \
    REALSTEAMONMAC_HOOK_BUILDER="$TMP/bin/hook" \
    REALSTEAMONMAC_LAUNCHER_BUILDER="$TMP/bin/launcher" \
    REALSTEAMONMAC_BRIDGE_BUILDER="$TMP/bin/bridge" \
    REALSTEAMONMAC_RUNTIME_INSTALLER="$TMP/bin/runtime" \
    REALSTEAMONMAC_INJECTION_INSTALLER="$TMP/bin/injection" \
    REALSTEAMONMAC_BACKUP_BUILDER="$TMP/bin/backup" \
    "$ROOT/script/install_realsteamonmac.sh" \
        --clean-backup "$BACKUP" \
        --without-gptk \
        --steam-app "$STEAM_APP" \
        --runtime-app "$RUNTIME_APP" \
        --support-root "$SUPPORT" \
        --compat-tools-root "$COMPAT_TOOLS" \
        --runtime-root "$RUNTIME_ROOT" \
        --cache-dir "$CACHE" >/dev/null 2>&1; then
    echo "installer must reject a stale clean backup after a Steam build change" >&2
    exit 1
fi
test ! -s "$LOG"
sed -i '' 's/1780705203/1780965181/' \
    "$RUNTIME_APP/Contents/MacOS/package/steam_client_publicbeta_signed-2_osx.manifest"

: >"$LOG"
rm -rf "$SUPPORT" "$RUNTIME_ROOT"
AUTO_BACKUPS="$TMP/automatic-backups"
env \
    HOME="$TMP/home" \
    REALSTEAMONMAC_HOOK_BUILDER="$TMP/bin/hook" \
    REALSTEAMONMAC_LAUNCHER_BUILDER="$TMP/bin/launcher" \
    REALSTEAMONMAC_BRIDGE_BUILDER="$TMP/bin/bridge" \
    REALSTEAMONMAC_RUNTIME_INSTALLER="$TMP/bin/runtime" \
    REALSTEAMONMAC_INJECTION_INSTALLER="$TMP/bin/injection" \
    REALSTEAMONMAC_BACKUP_BUILDER="$TMP/bin/backup" \
    "$ROOT/script/install_realsteamonmac.sh" \
        --without-gptk \
        --steam-app "$STEAM_APP" \
        --runtime-app "$RUNTIME_APP" \
        --support-root "$SUPPORT" \
        --compat-tools-root "$COMPAT_TOOLS" \
        --runtime-root "$RUNTIME_ROOT" \
        --cache-dir "$CACHE" \
        --backup-root "$AUTO_BACKUPS"

test "$(cut -f1 "$LOG" | tr '\n' ' ')" = \
    "backup hook launcher bridge runtime injection "
grep -q '^runtime	--without-gptk	' "$LOG"
grep -q "^backup	--steam-app	$STEAM_APP	--runtime-app	$RUNTIME_APP	--destination	$AUTO_BACKUPS/steam-" "$LOG"
grep -q '"runtime_package": "open-test-package"' \
    "$SUPPORT/install-state.json"

: >"$LOG"
rm -rf "$SUPPORT" "$RUNTIME_ROOT"
LEGACY_BACKUP_ROOT="$TMP/legacy-backups"
LEGACY_BACKUP="$LEGACY_BACKUP_ROOT/steam-20260607T000000Z"
mkdir -p "$LEGACY_BACKUP/Steam.app" "$LEGACY_BACKUP/SteamRuntime.app"
LEGACY_BACKUP_REAL=$(CDPATH= cd -- "$LEGACY_BACKUP" && pwd -P)
mkdir -p "$STEAM_APP/Contents"
printf '%s\n' \
    '<?xml version="1.0" encoding="UTF-8"?>' \
    '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">' \
    '<plist version="1.0"><dict>' \
    '<key>CFBundleExecutable</key><string>realsteamonmac_launcher</string>' \
    '</dict></plist>' >"$STEAM_APP/Contents/Info.plist"
env \
    HOME="$TMP/home" \
    REALSTEAMONMAC_HOOK_BUILDER="$TMP/bin/hook" \
    REALSTEAMONMAC_LAUNCHER_BUILDER="$TMP/bin/launcher" \
    REALSTEAMONMAC_BRIDGE_BUILDER="$TMP/bin/bridge" \
    REALSTEAMONMAC_RUNTIME_INSTALLER="$TMP/bin/runtime" \
    REALSTEAMONMAC_INJECTION_INSTALLER="$TMP/bin/injection" \
    REALSTEAMONMAC_BACKUP_BUILDER="$TMP/bin/backup" \
    "$ROOT/script/install_realsteamonmac.sh" \
        --without-gptk \
        --steam-app "$STEAM_APP" \
        --runtime-app "$RUNTIME_APP" \
        --support-root "$SUPPORT" \
        --compat-tools-root "$COMPAT_TOOLS" \
        --runtime-root "$RUNTIME_ROOT" \
        --cache-dir "$CACHE" \
        --backup-root "$LEGACY_BACKUP_ROOT"

test "$(cut -f1 "$LOG" | tr '\n' ' ')" = \
    "hook launcher bridge runtime injection "
grep -Fq "injection	--clean-backup	$LEGACY_BACKUP_REAL" "$LOG"

: >"$LOG"
sed -i '' 's/1780965181/1999999999/' \
    "$RUNTIME_APP/Contents/MacOS/package/steam_client_publicbeta_signed-2_osx.manifest"
if env \
    REALSTEAMONMAC_HOOK_BUILDER="$TMP/bin/hook" \
    REALSTEAMONMAC_LAUNCHER_BUILDER="$TMP/bin/launcher" \
    REALSTEAMONMAC_BRIDGE_BUILDER="$TMP/bin/bridge" \
    REALSTEAMONMAC_RUNTIME_INSTALLER="$TMP/bin/runtime" \
    REALSTEAMONMAC_INJECTION_INSTALLER="$TMP/bin/injection" \
    REALSTEAMONMAC_BACKUP_BUILDER="$TMP/bin/backup" \
    "$ROOT/script/install_realsteamonmac.sh" \
        --clean-backup "$BACKUP" \
        --without-gptk \
        --steam-app "$STEAM_APP" \
        --runtime-app "$RUNTIME_APP" \
        --support-root "$SUPPORT" \
        --compat-tools-root "$COMPAT_TOOLS" \
        --runtime-root "$RUNTIME_ROOT" \
        --cache-dir "$CACHE" >/dev/null 2>&1; then
    echo "installer must reject an unsupported Steam build" >&2
    exit 1
fi
test ! -s "$LOG"

echo "one-click installer contract: PASS"
