#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
TMP_ROOT=$(mktemp -d)
trap 'rm -rf "$TMP_ROOT"' EXIT

USER_NAME=$(id -un)
HOME_ROOT="$TMP_ROOT/home"
PAYLOAD="$TMP_ROOT/payload"
CALLS="$TMP_ROOT/calls.log"
mkdir -p \
    "$HOME_ROOT" \
    "$PAYLOAD/script" \
    "$PAYLOAD/config" \
    "$PAYLOAD/prebuilt/lsteamclient-proton11b5-macos2/x86_64-windows" \
    "$PAYLOAD/prebuilt/lsteamclient-proton11b5-macos2/x86_64-unix" \
    "$PAYLOAD/prebuilt/lsteamclient-proton7-gptk7.7-macos1/x86_64-windows" \
    "$PAYLOAD/prebuilt/lsteamclient-proton7-gptk7.7-macos1/x86_64-unix"

cp "$ROOT/script/check_for_updates.py" "$PAYLOAD/script/check_for_updates.py"
cp "$ROOT/config/release-public-key.hex" \
    "$PAYLOAD/config/release-public-key.hex"
cp "$ROOT/VERSION" "$PAYLOAD/VERSION"
printf 'bridge\n' \
    >"$PAYLOAD/prebuilt/lsteamclient-proton11b5-macos2/x86_64-windows/lsteamclient.dll"
printf 'bridge\n' \
    >"$PAYLOAD/prebuilt/lsteamclient-proton11b5-macos2/x86_64-unix/lsteamclient.so"
printf 'gptk bridge\n' \
    >"$PAYLOAD/prebuilt/lsteamclient-proton7-gptk7.7-macos1/x86_64-windows/lsteamclient.dll"
printf 'gptk bridge\n' \
    >"$PAYLOAD/prebuilt/lsteamclient-proton7-gptk7.7-macos1/x86_64-unix/lsteamclient.dll.so"
cp /usr/bin/true \
    "$PAYLOAD/prebuilt/realsteamonmac-verify-signature"

cat >"$PAYLOAD/script/install_realsteamonmac.sh" <<EOF
#!/bin/sh
printf '%s\\n' "\$*" >"$CALLS"
while [ "\$#" -gt 0 ]; do
    if [ "\$1" = --support-root ]; then
        mkdir -p "\$2"
        break
    fi
    shift
done
EOF
chmod +x "$PAYLOAD/script/install_realsteamonmac.sh"

cat >"$TMP_ROOT/runner" <<'EOF'
#!/bin/sh
exec "$@"
EOF
chmod +x "$TMP_ROOT/runner"

env \
    REALSTEAMONMAC_PACKAGE_PAYLOAD_ROOT="$PAYLOAD" \
    REALSTEAMONMAC_PACKAGE_USER="$USER_NAME" \
    REALSTEAMONMAC_PACKAGE_HOME="$HOME_ROOT" \
    REALSTEAMONMAC_PACKAGE_RUNNER="$TMP_ROOT/runner" \
    "$ROOT/packaging/install/scripts/postinstall"

grep -q -- '--quit-steam' "$CALLS"
grep -q -- '--without-gptk' "$CALLS"
grep -q -- "--steamworks-bridge $PAYLOAD/prebuilt/lsteamclient-proton11b5-macos2" \
    "$CALLS"
if grep -q -- '--gptk-steamworks-bridge' "$CALLS"; then
    echo "open runtime install must not receive the GPTK bridge" >&2
    exit 1
fi
SUPPORT="$HOME_ROOT/Library/Application Support/RealSteamOnMac"
test -x "$SUPPORT/bin/check-for-updates"
test -x "$SUPPORT/bin/verify-release-signature"
test -f "$SUPPORT/release-public-key.hex"

mkdir -p "$HOME_ROOT/Downloads"
: >"$HOME_ROOT/Downloads/Game_Porting_Toolkit_3.0.dmg"
env \
    REALSTEAMONMAC_PACKAGE_PAYLOAD_ROOT="$PAYLOAD" \
    REALSTEAMONMAC_PACKAGE_USER="$USER_NAME" \
    REALSTEAMONMAC_PACKAGE_HOME="$HOME_ROOT" \
    REALSTEAMONMAC_PACKAGE_RUNNER="$TMP_ROOT/runner" \
    "$ROOT/packaging/install/scripts/postinstall"
grep -q -- '--gptk-dmg' "$CALLS"
grep -q -- "--gptk-steamworks-bridge $PAYLOAD/prebuilt/lsteamclient-proton7-gptk7.7-macos1" \
    "$CALLS"

UPDATE_BACKUP="$HOME_ROOT/RealSteamOnMac-Backups/update-fixture"
mkdir -p \
    "$UPDATE_BACKUP/Steam.app" \
    "$UPDATE_BACKUP/SteamRuntime.app"
cat >"$SUPPORT/install-state.json" <<EOF
{
  "schema": 1,
  "version": "0.1.0",
  "clean_backup": "$UPDATE_BACKUP",
  "steam_build": "1781212412",
  "runtime_package": "fixture",
  "managed_compat_tools": []
}
EOF
cat >"$PAYLOAD/script/update_realsteamonmac.sh" <<EOF
#!/bin/sh
printf 'update\\t%s\\n' "\$*" >"$CALLS"
EOF
chmod +x "$PAYLOAD/script/update_realsteamonmac.sh"
env \
    REALSTEAMONMAC_PACKAGE_USER="$USER_NAME" \
    REALSTEAMONMAC_PACKAGE_HOME="$HOME_ROOT" \
    "$ROOT/packaging/update/scripts/preinstall"
env \
    REALSTEAMONMAC_PACKAGE_PAYLOAD_ROOT="$PAYLOAD" \
    REALSTEAMONMAC_PACKAGE_USER="$USER_NAME" \
    REALSTEAMONMAC_PACKAGE_HOME="$HOME_ROOT" \
    REALSTEAMONMAC_PACKAGE_RUNNER="$TMP_ROOT/runner" \
    "$ROOT/packaging/update/scripts/postinstall"
grep -Fq "update	--payload-root $PAYLOAD --home $HOME_ROOT" "$CALLS"

rm -rf "$PAYLOAD"
mkdir -p "$PAYLOAD/script"
cat >"$PAYLOAD/script/uninstall_realsteamonmac.sh" <<EOF
#!/bin/sh
printf '%s\\n' "\$*" >"$CALLS"
EOF
chmod +x "$PAYLOAD/script/uninstall_realsteamonmac.sh"

env \
    REALSTEAMONMAC_PACKAGE_PAYLOAD_ROOT="$PAYLOAD" \
    REALSTEAMONMAC_PACKAGE_USER="$USER_NAME" \
    REALSTEAMONMAC_PACKAGE_HOME="$HOME_ROOT" \
    REALSTEAMONMAC_PACKAGE_RUNNER="$TMP_ROOT/runner" \
    "$ROOT/packaging/uninstall/scripts/postinstall"

grep -q -- '--quit-steam' "$CALLS"
grep -q -- "--support-root $SUPPORT" "$CALLS"
test ! -e "$PAYLOAD"

FAKE_BRIDGE="$TMP_ROOT/bridge"
mkdir -p "$FAKE_BRIDGE/x86_64-windows" "$FAKE_BRIDGE/x86_64-unix"
printf 'fixture\n' >"$FAKE_BRIDGE/x86_64-windows/lsteamclient.dll"
printf 'fixture\n' >"$FAKE_BRIDGE/x86_64-unix/lsteamclient.so"
FAKE_GPTK_BRIDGE="$TMP_ROOT/gptk-bridge"
mkdir -p \
    "$FAKE_GPTK_BRIDGE/x86_64-windows" \
    "$FAKE_GPTK_BRIDGE/x86_64-unix"
printf 'fixture\n' \
    >"$FAKE_GPTK_BRIDGE/x86_64-windows/lsteamclient.dll"
printf 'fixture\n' \
    >"$FAKE_GPTK_BRIDGE/x86_64-unix/lsteamclient.dll.so"
FAKE_DXMT_COMPAT="$TMP_ROOT/dxmt-winemac-compat"
mkdir -p "$FAKE_DXMT_COMPAT"
printf 'fixture winemac\n' >"$FAKE_DXMT_COMPAT/winemac.so"
printf 'fixture shim\n' \
    >"$FAKE_DXMT_COMPAT/librealsteamonmac_dxmt_macdrv_shim.dylib"
cat >"$FAKE_DXMT_COMPAT/build-info.json" <<'EOF'
{
  "dxmt_version": "0.80",
  "minimum_macos": "10.15",
  "name": "RealSteamOnMac DXMT Wine macdrv compatibility",
  "schema": 1,
  "wine_commit": "2cac6ccf33c0807f374dc96f5a20e35a2da86157",
  "wine_staging_commit": "f45e84d7a01a52d379e4003f03800c13875c69e9"
}
EOF
(
    cd "$FAKE_DXMT_COMPAT"
    shasum -a 256 \
        winemac.so \
        librealsteamonmac_dxmt_macdrv_shim.dylib \
        >SHA256SUMS
)
DIST="$TMP_ROOT/dist"
env REALSTEAMONMAC_ALLOW_TEST_FIXTURES=1 \
    "$ROOT/script/build_release_pkgs.sh" \
        --output "$DIST" \
        --steamworks-bridge "$FAKE_BRIDGE" \
        --gptk-steamworks-bridge "$FAKE_GPTK_BRIDGE" \
        --dxmt-winemac-compat "$FAKE_DXMT_COMPAT" >/dev/null

for package in \
    RealSteamOnMac-Install.pkg \
    RealSteamOnMac-Update.pkg \
    RealSteamOnMac-Uninstall.pkg; do
    test -f "$DIST/$package"
    pkgutil --payload-files "$DIST/$package" >/dev/null
done
(cd "$DIST" && shasum -a 256 -c SHA256SUMS)
/usr/bin/python3 - "$ROOT" "$DIST/release-manifest.json" <<'PY'
import importlib.util
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
spec = importlib.util.spec_from_file_location(
    "updates", root / "script/check_for_updates.py"
)
updates = importlib.util.module_from_spec(spec)
spec.loader.exec_module(updates)
with open(sys.argv[2], encoding="utf-8") as stream:
    value = json.load(stream)
updates.validate_manifest(value, "dazi2011/RealSteamOnMac")
if value["supported_steam_builds"] != [
    "1780705203",
    "1780965181",
    "1781212412",
]:
    raise SystemExit("release manifest Steam build list is incomplete")
if value["updater"]["name"] != "RealSteamOnMac-Update.pkg":
    raise SystemExit("release manifest updater is missing")
PY
/opt/homebrew/bin/openssl pkeyutl \
    -verify \
    -rawin \
    -pubin \
    -inkey "$HOME/.config/RealSteamOnMac/release-ed25519-public.pem" \
    -in "$DIST/release-manifest.json" \
    -sigfile "$DIST/release-manifest.json.sig"

echo "release packaging contract: PASS"
