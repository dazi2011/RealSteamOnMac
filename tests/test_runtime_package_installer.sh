#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
INSTALLER="$ROOT/script/install_runtime_package.sh"
RUNTIME="$ROOT/runtime/realsteamonmac_runtime.py"

test -x "$INSTALLER"
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

if grep -Eq 'rm -rf "\$DESTINATION"|rm -rf "\$RUNTIME_ROOT/packages"' "$INSTALLER"; then
    echo "installer must never delete an installed runtime package" >&2
    exit 1
fi

grep -q 'steamapps / "compatdata"' "$RUNTIME"
grep -q 'WINEMSYNC' "$RUNTIME"
grep -q 'MTL_HUD_ENABLED' "$RUNTIME"
grep -q 'D3DM_ENABLE_METALFX' "$RUNTIME"
grep -q 'MVK_CONFIG_RESUME_LOST_DEVICE' "$RUNTIME"
grep -q 'os.execve' "$RUNTIME"

echo "runtime package installer contract: PASS"
