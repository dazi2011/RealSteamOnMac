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

write_snapshot_package() {
    package=$1
    channel=$2
    build=$3

    rm -rf "$package"
    mkdir -p "$package"
    if [ "$channel" = publicbeta ]; then
        printf 'publicbeta\n' >"$package/beta"
        manifest="$package/steam_client_publicbeta_signed-2_osx.manifest"
        installed="$package/steam_client_publicbeta_signed-2_osx.installed"
    else
        manifest="$package/steam_client_signed-2_osx.manifest"
        installed="$package/steam_client_signed-2_osx.installed"
    fi
    cat >"$manifest" <<EOF
"osx"
{
    "version" "$build"
}
EOF
    : >"$installed"
}

mkdir -p \
    "$STEAM_APP" \
    "$RUNTIME_APP/Contents/MacOS/package" \
    "$BACKUP/Steam.app" \
    "$TMP/bin"
: >"$RUNTIME_APP/Contents/MacOS/steam_osx"
printf 'publicbeta\n' \
    >"$RUNTIME_APP/Contents/MacOS/package/beta"
cat >"$RUNTIME_APP/Contents/MacOS/package/steam_client_publicbeta_signed-2_osx.manifest" <<'EOF'
"osx"
{
    "version" "1781212412"
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
write_snapshot_package \
    "$BACKUP/SteamRuntime.app/Contents/MacOS/package" \
    publicbeta \
    1781212412
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
    runtime_app=
    destination=
    while [ "$#" -gt 0 ]; do
        case "$1" in
            --runtime-app)
                runtime_app=$2
                shift 2
                ;;
            --destination)
                destination=$2
                shift 2
                ;;
            *)
                shift
                ;;
        esac
    done
    mkdir -p "$destination/Steam.app" \
        "$destination/SteamRuntime.app/Contents/MacOS"
    cp -R "$runtime_app/Contents/MacOS/package" \
        "$destination/SteamRuntime.app/Contents/MacOS/package"
fi
EOF

for name in hook launcher bridge gptk_bridge runtime injection backup; do
    make_recorder "$name"
done

run_first_install() {
    support=$1
    shift
    env \
        PATH="${INSTALLER_PATH:-$PATH}" \
        REALSTEAMONMAC_HOOK_BUILDER="$TMP/bin/hook" \
        REALSTEAMONMAC_LAUNCHER_BUILDER="$TMP/bin/launcher" \
        REALSTEAMONMAC_BRIDGE_BUILDER="$TMP/bin/bridge" \
        REALSTEAMONMAC_RUNTIME_INSTALLER="$TMP/bin/runtime" \
        REALSTEAMONMAC_INJECTION_INSTALLER="$TMP/bin/injection" \
        REALSTEAMONMAC_BACKUP_BUILDER="$TMP/bin/backup" \
        REALSTEAMONMAC_STEAM_STOPPER="${STEAM_STOPPER_FIXTURE:-}" \
        "$ROOT/script/install_realsteamonmac.sh" \
            --clean-backup "$BACKUP" \
            --without-gptk \
            --steam-app "$STEAM_APP" \
            --runtime-app "$RUNTIME_APP" \
            --support-root "$support" \
            --compat-tools-root "$support/compatibilitytools.d" \
            --runtime-root "$support/runtimes" \
            --cache-dir "$CACHE" \
            "$@"
}

MISMATCH_FAILURES=0
CHANNEL_MISMATCH_ERROR="$TMP/channel-mismatch.error"
write_snapshot_package \
    "$BACKUP/SteamRuntime.app/Contents/MacOS/package" \
    stable \
    1781212412
: >"$LOG"
if run_first_install "$TMP/channel-mismatch-support" \
    > /dev/null 2>"$CHANNEL_MISMATCH_ERROR"; then
    echo "installer must reject a rollback snapshot from another channel" >&2
    MISMATCH_FAILURES=$((MISMATCH_FAILURES + 1))
fi
if ! test "$(cat "$CHANNEL_MISMATCH_ERROR")" = \
    "current Steam channel does not match the rollback snapshot"; then
    echo "channel mismatch must report the exact rollback snapshot error" >&2
    MISMATCH_FAILURES=$((MISMATCH_FAILURES + 1))
fi
if [ -s "$LOG" ]; then
    echo "channel mismatch must fail before installer components run" >&2
    MISMATCH_FAILURES=$((MISMATCH_FAILURES + 1))
fi

BUILD_MISMATCH_ERROR="$TMP/build-mismatch.error"
write_snapshot_package \
    "$BACKUP/SteamRuntime.app/Contents/MacOS/package" \
    publicbeta \
    1780705203
: >"$LOG"
if run_first_install "$TMP/build-mismatch-support" \
    > /dev/null 2>"$BUILD_MISMATCH_ERROR"; then
    echo "installer must reject a rollback snapshot from another build" >&2
    MISMATCH_FAILURES=$((MISMATCH_FAILURES + 1))
fi
if ! test "$(cat "$BUILD_MISMATCH_ERROR")" = \
    "current Steam build does not match the rollback snapshot"; then
    echo "build mismatch must report the exact rollback snapshot error" >&2
    MISMATCH_FAILURES=$((MISMATCH_FAILURES + 1))
fi
if [ -s "$LOG" ]; then
    echo "build mismatch must fail before installer components run" >&2
    MISMATCH_FAILURES=$((MISMATCH_FAILURES + 1))
fi

INVALID_BETA_ERROR="$TMP/invalid-beta.error"
write_snapshot_package \
    "$BACKUP/SteamRuntime.app/Contents/MacOS/package" \
    publicbeta \
    1781212412
printf '\377\n' \
    >"$BACKUP/SteamRuntime.app/Contents/MacOS/package/beta"
: >"$LOG"
if run_first_install "$TMP/invalid-beta-support" \
    > /dev/null 2>"$INVALID_BETA_ERROR"; then
    echo "installer must reject an unreadable rollback beta channel" >&2
    MISMATCH_FAILURES=$((MISMATCH_FAILURES + 1))
fi
if ! test "$(cat "$INVALID_BETA_ERROR")" = \
    "rollback snapshot Steam beta channel could not be read"; then
    echo "invalid rollback beta encoding must report a stable error" >&2
    MISMATCH_FAILURES=$((MISMATCH_FAILURES + 1))
fi
if grep -Fq "Traceback" "$INVALID_BETA_ERROR"; then
    echo "invalid rollback beta encoding must not emit a traceback" >&2
    MISMATCH_FAILURES=$((MISMATCH_FAILURES + 1))
fi
if [ -s "$LOG" ]; then
    echo "invalid rollback beta encoding must fail before components run" >&2
    MISMATCH_FAILURES=$((MISMATCH_FAILURES + 1))
fi

INVALID_MANIFEST_ERROR="$TMP/invalid-manifest.error"
write_snapshot_package \
    "$BACKUP/SteamRuntime.app/Contents/MacOS/package" \
    publicbeta \
    1781212412
printf '\377\n' \
    >"$BACKUP/SteamRuntime.app/Contents/MacOS/package/steam_client_publicbeta_signed-2_osx.manifest"
: >"$LOG"
if run_first_install "$TMP/invalid-manifest-support" \
    > /dev/null 2>"$INVALID_MANIFEST_ERROR"; then
    echo "installer must reject an unreadable rollback manifest" >&2
    MISMATCH_FAILURES=$((MISMATCH_FAILURES + 1))
fi
if ! test "$(cat "$INVALID_MANIFEST_ERROR")" = \
    "rollback snapshot Steam build manifest could not be read"; then
    echo "invalid rollback manifest encoding must report a stable error" >&2
    MISMATCH_FAILURES=$((MISMATCH_FAILURES + 1))
fi
if grep -Fq "Traceback" "$INVALID_MANIFEST_ERROR"; then
    echo "invalid rollback manifest encoding must not emit a traceback" >&2
    MISMATCH_FAILURES=$((MISMATCH_FAILURES + 1))
fi
if [ -s "$LOG" ]; then
    echo "invalid rollback manifest encoding must fail before components run" >&2
    MISMATCH_FAILURES=$((MISMATCH_FAILURES + 1))
fi

STOP_RUNNING_MARKER="$TMP/steam-running"
cat >"$TMP/bin/pgrep" <<EOF
#!/bin/sh
test -f "$STOP_RUNNING_MARKER"
EOF
chmod +x "$TMP/bin/pgrep"
cat >"$TMP/bin/stopper" <<EOF
#!/bin/sh
set -eu
package="$RUNTIME_APP/Contents/MacOS/package"
rm "\$package/beta"
mv "\$package/steam_client_publicbeta_signed-2_osx.manifest" \
    "\$package/steam_client_signed-2_osx.manifest"
mv "\$package/steam_client_publicbeta_signed-2_osx.installed" \
    "\$package/steam_client_signed-2_osx.installed"
sed -i '' 's/1781212412/1780705203/' \
    "\$package/steam_client_signed-2_osx.manifest"
rm "$STOP_RUNNING_MARKER"
EOF
chmod +x "$TMP/bin/stopper"
write_snapshot_package \
    "$BACKUP/SteamRuntime.app/Contents/MacOS/package" \
    publicbeta \
    1781212412
: >"$STOP_RUNNING_MARKER"
: >"$LOG"
STOP_REVALIDATION_ERROR="$TMP/stop-revalidation.error"
if INSTALLER_PATH="$TMP/bin:$PATH" \
    STEAM_STOPPER_FIXTURE="$TMP/bin/stopper" \
    run_first_install "$TMP/stop-revalidation-support" --quit-steam \
    > /dev/null 2>"$STOP_REVALIDATION_ERROR"; then
    echo "installer must revalidate the rollback snapshot after stopping Steam" >&2
    MISMATCH_FAILURES=$((MISMATCH_FAILURES + 1))
fi
if ! test "$(cat "$STOP_REVALIDATION_ERROR")" = \
    "current Steam channel does not match the rollback snapshot"; then
    echo "post-stop channel mismatch must report the exact snapshot error" >&2
    MISMATCH_FAILURES=$((MISMATCH_FAILURES + 1))
fi
if grep -Fq "Traceback" "$STOP_REVALIDATION_ERROR"; then
    echo "post-stop snapshot validation must not emit a traceback" >&2
    MISMATCH_FAILURES=$((MISMATCH_FAILURES + 1))
fi
if [ -s "$LOG" ]; then
    echo "post-stop snapshot mismatch must fail before components run" >&2
    MISMATCH_FAILURES=$((MISMATCH_FAILURES + 1))
fi
sed -i '' 's/1780705203/1781212412/' \
    "$RUNTIME_APP/Contents/MacOS/package/steam_client_signed-2_osx.manifest"
mv \
    "$RUNTIME_APP/Contents/MacOS/package/steam_client_signed-2_osx.manifest" \
    "$RUNTIME_APP/Contents/MacOS/package/steam_client_publicbeta_signed-2_osx.manifest"
mv \
    "$RUNTIME_APP/Contents/MacOS/package/steam_client_signed-2_osx.installed" \
    "$RUNTIME_APP/Contents/MacOS/package/steam_client_publicbeta_signed-2_osx.installed"
printf 'publicbeta\n' \
    >"$RUNTIME_APP/Contents/MacOS/package/beta"

if [ "$MISMATCH_FAILURES" -ne 0 ]; then
    exit 1
fi

write_snapshot_package \
    "$BACKUP/SteamRuntime.app/Contents/MacOS/package" \
    publicbeta \
    1781212412
: >"$LOG"
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
grep -q '"steam_build": "1781212412"' "$SUPPORT/install-state.json"
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
write_snapshot_package \
    "$BACKUP/SteamRuntime.app/Contents/MacOS/package" \
    stable \
    1781212412
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
grep -q '"steam_build": "1781212412"' \
    "$STABLE_SUPPORT/install-state.json"
grep -q '"steam_channel": "stable"' \
    "$STABLE_SUPPORT/install-state.json"
write_snapshot_package \
    "$BACKUP/SteamRuntime.app/Contents/MacOS/package" \
    publicbeta \
    1781212412
mv \
    "$RUNTIME_APP/Contents/MacOS/package/steam_client_signed-2_osx.manifest" \
    "$RUNTIME_APP/Contents/MacOS/package/steam_client_publicbeta_signed-2_osx.manifest"
mv \
    "$RUNTIME_APP/Contents/MacOS/package/steam_client_signed-2_osx.installed" \
    "$RUNTIME_APP/Contents/MacOS/package/steam_client_publicbeta_signed-2_osx.installed"
printf 'publicbeta\n' \
    >"$RUNTIME_APP/Contents/MacOS/package/beta"

: >"$LOG"
sed -i '' 's/1781212412/1780705203/' \
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
sed -i '' 's/1780705203/1781212412/' \
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
write_snapshot_package \
    "$LEGACY_BACKUP/SteamRuntime.app/Contents/MacOS/package" \
    publicbeta \
    1781212412
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
sed -i '' 's/1781212412/1999999999/' \
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
