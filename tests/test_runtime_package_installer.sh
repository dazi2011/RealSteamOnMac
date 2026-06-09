#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
INSTALLER="$ROOT/script/install_runtime_package.sh"
BRIDGE_BUILDER="$ROOT/script/build_lsteamclient_bridge.sh"
MAKEFILE_GENERATOR="$ROOT/script/generate_lsteamclient_makefile.py"
RUNTIME="$ROOT/runtime/realsteamonmac_runtime.py"

test -x "$INSTALLER"
test -f "$BRIDGE_BUILDER"
test -f "$MAKEFILE_GENERATOR"
test -f "$RUNTIME"

grep -q 'game-porting-toolkit-3.0-3.tar.xz' "$INSTALLER"
grep -q 'wine-staging-11.10-osx64.tar.xz' "$INSTALLER"
grep -q 'dxmt-v0.80-builtin.tar.gz' "$INSTALLER"
grep -q 'dxvk-macOS-async-v1.10.3-20230507-repack-builtin.tar.gz' "$INSTALLER"
grep -q 'checksum mismatch' "$INSTALLER"
grep -q 'shasum -a 256 -c SHA256SUMS' "$INSTALLER"
grep -q 'mv "$PACKAGE" "$DESTINATION"' "$INSTALLER"
grep -q 'mv -h "$CURRENT_TEMP" "$RUNTIME_ROOT/current"' "$INSTALLER"
grep -q 'packages/$PACKAGE_ID' "$INSTALLER"
grep -q 'Apple-GPTK-License.rtf' "$INSTALLER"
grep -q -- '--steamworks-bridge' "$INSTALLER"
grep -q 'lsteamclient-proton11b5-macos2' "$INSTALLER"
grep -q 'steamworks_bridge' "$INSTALLER"
grep -q 'x86_64-unix/lsteamclient.so' "$INSTALLER"
grep -q 'x86_64-windows/lsteamclient.dll' "$INSTALLER"
grep -q '25880e88befb52c5aa7ff162c5b00b6b8825e494' "$BRIDGE_BUILDER"
grep -q '2f70bfd4d0f4e67a8a599c4a09760579bc2a4fa4' "$BRIDGE_BUILDER"
grep -q 'proton-lsteamclient-macos.patch' "$BRIDGE_BUILDER"
grep -q 'generate_lsteamclient_makefile.py' "$BRIDGE_BUILDER"
grep -q 'macos_known_interfaces.inc' "$BRIDGE_BUILDER"
grep -q 'cmp -s "\$STAGING/SHA256SUMS" "\$OUTPUT/SHA256SUMS"' "$BRIDGE_BUILDER"
grep -q 'cmp -s "\$STAGING/build-info.json" "\$OUTPUT/build-info.json"' "$BRIDGE_BUILDER"

if grep -Eq 'rm -rf "\$DESTINATION"|rm -rf "\$RUNTIME_ROOT/packages"' "$INSTALLER"; then
    echo "installer must never delete an installed runtime package" >&2
    exit 1
fi

grep -q 'steamapps / "compatdata"' "$RUNTIME"
grep -q 'WINEMSYNC' "$RUNTIME"
grep -q 'MTL_HUD_ENABLED' "$RUNTIME"
grep -q 'D3DM_ENABLE_METALFX' "$RUNTIME"
grep -q 'MVK_CONFIG_RESUME_LOST_DEVICE' "$RUNTIME"
grep -q 'STEAM_COMPAT_CLIENT_INSTALL_PATH' "$RUNTIME"
grep -q 'winemenubuilder.exe=d' "$RUNTIME"
grep -q 'steamclient64=n,b' "$RUNTIME"
grep -q 'refusing to replace an unmanaged Steamworks file' "$RUNTIME"
grep -q 'POST_EXIT_PREFIX_KILL_APPIDS' "$RUNTIME"
grep -q 'wineserver.*\"-k\"' "$RUNTIME"

echo "runtime package installer contract: PASS"
