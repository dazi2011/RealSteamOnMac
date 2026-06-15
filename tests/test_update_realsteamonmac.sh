#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

make_fixture() {
    name=$1
    FIXTURE="$TMP/$name"
    HOME_ROOT="$FIXTURE/home"
    SUPPORT="$HOME_ROOT/Library/Application Support/RealSteamOnMac"
    RUNTIME_ROOT="$SUPPORT/runtimes"
    COMPAT_ROOT="$HOME_ROOT/Library/Application Support/Steam/compatibilitytools.d"
    STEAM_APP="$FIXTURE/Steam.app"
    RUNTIME_APP="$FIXTURE/SteamRuntime.app"
    BACKUP="$HOME_ROOT/RealSteamOnMac-Backups/clean"
    PAYLOAD="$FIXTURE/payload"
    mkdir -p \
        "$SUPPORT" \
        "$RUNTIME_ROOT/bin" \
        "$RUNTIME_ROOT/packages/old-runtime" \
        "$COMPAT_ROOT/realsteamonmac-dxmt" \
        "$COMPAT_ROOT/User-GPTK" \
        "$STEAM_APP" \
        "$RUNTIME_APP/Contents/MacOS/package" \
        "$BACKUP/Steam.app" \
        "$BACKUP/SteamRuntime.app/Contents/MacOS/package" \
        "$PAYLOAD/script" \
        "$PAYLOAD/config" \
        "$PAYLOAD/prebuilt/lsteamclient-proton11b5-macos2/x86_64-windows" \
        "$PAYLOAD/prebuilt/lsteamclient-proton11b5-macos2/x86_64-unix"
    ln -s packages/old-runtime "$RUNTIME_ROOT/current"
    printf '{"schema":1,"package_id":"old-runtime"}\n' \
        >"$RUNTIME_ROOT/packages/old-runtime/manifest.json"
    printf 'old steam\n' >"$STEAM_APP/version"
    printf 'old runtime\n' >"$RUNTIME_APP/version"
    printf 'publicbeta\n' \
        >"$RUNTIME_APP/Contents/MacOS/package/beta"
    cat >"$RUNTIME_APP/Contents/MacOS/package/steam_client_publicbeta_signed-2_osx.manifest" <<'EOF'
"osx"
{
    "version" "1781212412"
}
EOF
    : >"$RUNTIME_APP/Contents/MacOS/package/steam_client_publicbeta_signed-2_osx.installed"
    cp "$RUNTIME_APP/Contents/MacOS/package/beta" \
        "$BACKUP/SteamRuntime.app/Contents/MacOS/package/beta"
    cp \
        "$RUNTIME_APP/Contents/MacOS/package/steam_client_publicbeta_signed-2_osx.manifest" \
        "$BACKUP/SteamRuntime.app/Contents/MacOS/package/steam_client_publicbeta_signed-2_osx.manifest"
    cp \
        "$RUNTIME_APP/Contents/MacOS/package/steam_client_publicbeta_signed-2_osx.installed" \
        "$BACKUP/SteamRuntime.app/Contents/MacOS/package/steam_client_publicbeta_signed-2_osx.installed"
    printf 'old hook\n' >"$SUPPORT/libRealSteamCompatGate.dylib"
    printf 'old runtime executable\n' \
        >"$RUNTIME_ROOT/bin/realsteamonmac-runtime"
    printf 'managed old\n' \
        >"$COMPAT_ROOT/realsteamonmac-dxmt/marker"
    printf 'user tool\n' >"$COMPAT_ROOT/User-GPTK/marker"
    mkdir -p "$FIXTURE/steamapps/compatdata/1118200/pfx"
    printf 'prefix\n' \
        >"$FIXTURE/steamapps/compatdata/1118200/pfx/user.reg"
    printf '0.1.1\n' >"$PAYLOAD/VERSION"
    cp "$ROOT/script/check_for_updates.py" \
        "$PAYLOAD/script/check_for_updates.py"
    cp "$ROOT/config/release-public-key.hex" \
        "$PAYLOAD/config/release-public-key.hex"
    cp /usr/bin/true \
        "$PAYLOAD/prebuilt/realsteamonmac-verify-signature"
    printf 'bridge\n' \
        >"$PAYLOAD/prebuilt/lsteamclient-proton11b5-macos2/x86_64-windows/lsteamclient.dll"
    printf 'bridge\n' \
        >"$PAYLOAD/prebuilt/lsteamclient-proton11b5-macos2/x86_64-unix/lsteamclient.so"
    cat >"$SUPPORT/install-state.json" <<EOF
{
  "schema": 1,
  "version": "0.1.0",
  "clean_backup": "$BACKUP",
  "steam_app": "$STEAM_APP",
  "runtime_app": "$RUNTIME_APP",
  "support_root": "$SUPPORT",
  "runtime_root": "$RUNTIME_ROOT",
  "compat_tools_root": "$COMPAT_ROOT",
  "steam_build": "1781212412",
  "steam_channel": "publicbeta",
  "runtime_package": "old-runtime",
  "managed_compat_tools": [
    {"name": "realsteamonmac-dxmt", "metadata_sha256": "unused"}
  ]
}
EOF
}

make_installer() {
    path=$1
    result=$2
    cat >"$path" <<'EOF'
#!/bin/sh
set -eu
support=
runtime_root=
compat_root=
steam_app=
runtime_app=
while [ "$#" -gt 0 ]; do
    case "$1" in
        --support-root) support=$2; shift 2 ;;
        --runtime-root) runtime_root=$2; shift 2 ;;
        --compat-tools-root) compat_root=$2; shift 2 ;;
        --steam-app) steam_app=$2; shift 2 ;;
        --runtime-app) runtime_app=$2; shift 2 ;;
        *) shift ;;
    esac
done
printf 'new steam\n' >"$steam_app/version"
printf 'new runtime\n' >"$runtime_app/version"
printf 'new hook\n' >"$support/libRealSteamCompatGate.dylib"
printf 'managed new\n' >"$compat_root/realsteamonmac-dxmt/marker"
mkdir -p "$runtime_root/packages/new-runtime"
printf '{"schema":1,"package_id":"new-runtime"}\n' \
    >"$runtime_root/packages/new-runtime/manifest.json"
rm "$runtime_root/current"
ln -s packages/new-runtime "$runtime_root/current"
python3 - "$support/install-state.json" <<'PY'
import json
import sys
path = sys.argv[1]
with open(path, encoding="utf-8") as stream:
    value = json.load(stream)
value["version"] = "0.1.1"
value["runtime_package"] = "new-runtime"
value["steam_channel"] = "publicbeta"
with open(path, "w", encoding="utf-8") as stream:
    json.dump(value, stream, indent=2, sort_keys=True)
    stream.write("\n")
PY
EOF
    printf 'exit %s\n' "$result" >>"$path"
    chmod +x "$path"
}

make_fixture success
SUCCESS_INSTALLER="$FIXTURE/installer"
make_installer "$SUCCESS_INSTALLER" 0
env \
    REALSTEAMONMAC_UPDATE_ALLOW_TEST_PATHS=1 \
    REALSTEAMONMAC_UPDATE_INSTALLER="$SUCCESS_INSTALLER" \
    "$ROOT/script/update_realsteamonmac.sh" \
        --payload-root "$PAYLOAD" \
        --home "$HOME_ROOT"
grep -q 'new steam' "$STEAM_APP/version"
grep -q 'new runtime' "$RUNTIME_APP/version"
grep -q 'managed new' \
    "$COMPAT_ROOT/realsteamonmac-dxmt/marker"
grep -q 'user tool' "$COMPAT_ROOT/User-GPTK/marker"
grep -q 'prefix' \
    "$FIXTURE/steamapps/compatdata/1118200/pfx/user.reg"
grep -q '"version": "0.1.1"' "$SUPPORT/install-state.json"
test "$(readlink "$RUNTIME_ROOT/current")" = packages/new-runtime
test -x "$SUPPORT/bin/check-for-updates"

make_fixture legacy-state
LEGACY_INSTALLER="$FIXTURE/installer"
make_installer "$LEGACY_INSTALLER" 0
python3 - "$SUPPORT/install-state.json" <<'PY'
import json
import sys

path = sys.argv[1]
with open(path, encoding="utf-8") as stream:
    value = json.load(stream)
value.pop("steam_channel")
with open(path, "w", encoding="utf-8") as stream:
    json.dump(value, stream, indent=2, sort_keys=True)
    stream.write("\n")
PY
env \
    REALSTEAMONMAC_UPDATE_ALLOW_TEST_PATHS=1 \
    REALSTEAMONMAC_UPDATE_INSTALLER="$LEGACY_INSTALLER" \
    "$ROOT/script/update_realsteamonmac.sh" \
        --payload-root "$PAYLOAD" \
        --home "$HOME_ROOT"
grep -q '"steam_channel": "publicbeta"' \
    "$SUPPORT/install-state.json"

make_fixture failure
FAIL_INSTALLER="$FIXTURE/installer"
make_installer "$FAIL_INSTALLER" 1
if env \
    REALSTEAMONMAC_UPDATE_ALLOW_TEST_PATHS=1 \
    REALSTEAMONMAC_UPDATE_INSTALLER="$FAIL_INSTALLER" \
    "$ROOT/script/update_realsteamonmac.sh" \
        --payload-root "$PAYLOAD" \
        --home "$HOME_ROOT"; then
    echo "failed update must return nonzero" >&2
    exit 1
fi
grep -q 'old steam' "$STEAM_APP/version"
grep -q 'old runtime' "$RUNTIME_APP/version"
grep -q 'old hook' "$SUPPORT/libRealSteamCompatGate.dylib"
grep -q 'managed old' \
    "$COMPAT_ROOT/realsteamonmac-dxmt/marker"
grep -q 'user tool' "$COMPAT_ROOT/User-GPTK/marker"
grep -q 'prefix' \
    "$FIXTURE/steamapps/compatdata/1118200/pfx/user.reg"
grep -q '"version": "0.1.0"' "$SUPPORT/install-state.json"
test "$(readlink "$RUNTIME_ROOT/current")" = packages/old-runtime

make_fixture mismatch
MISMATCH_INSTALLER="$FIXTURE/installer"
make_installer "$MISMATCH_INSTALLER" 0
sed -i '' 's/1781212412/1780965181/' \
    "$RUNTIME_APP/Contents/MacOS/package/steam_client_publicbeta_signed-2_osx.manifest"
if env \
    REALSTEAMONMAC_UPDATE_ALLOW_TEST_PATHS=1 \
    REALSTEAMONMAC_UPDATE_INSTALLER="$MISMATCH_INSTALLER" \
    "$ROOT/script/update_realsteamonmac.sh" \
        --payload-root "$PAYLOAD" \
        --home "$HOME_ROOT" >/dev/null 2>&1; then
    echo "update must reject a Steam build that does not match backup state" >&2
    exit 1
fi
grep -q 'old steam' "$STEAM_APP/version"
grep -q '"version": "0.1.0"' "$SUPPORT/install-state.json"
test ! -e \
    "$HOME_ROOT/Library/Caches/RealSteamOnMac/update-transactions"

make_fixture backup-mismatch
BACKUP_MISMATCH_INSTALLER="$FIXTURE/installer"
make_installer "$BACKUP_MISMATCH_INSTALLER" 0
sed -i '' 's/1781212412/1780965181/' \
    "$BACKUP/SteamRuntime.app/Contents/MacOS/package/steam_client_publicbeta_signed-2_osx.manifest"
if env \
    REALSTEAMONMAC_UPDATE_ALLOW_TEST_PATHS=1 \
    REALSTEAMONMAC_UPDATE_INSTALLER="$BACKUP_MISMATCH_INSTALLER" \
    "$ROOT/script/update_realsteamonmac.sh" \
        --payload-root "$PAYLOAD" \
        --home "$HOME_ROOT" >/dev/null 2>&1; then
    echo "update must reject a rollback snapshot with the wrong build" >&2
    exit 1
fi
grep -q 'old steam' "$STEAM_APP/version"
grep -q '"version": "0.1.0"' "$SUPPORT/install-state.json"
test ! -e \
    "$HOME_ROOT/Library/Caches/RealSteamOnMac/update-transactions"

echo "transactional update contract: PASS"
