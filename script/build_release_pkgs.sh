#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
VERSION=$(tr -d '[:space:]' <"$ROOT/VERSION")
OUTPUT="$ROOT/dist"
BRIDGE=""
GPTK_BRIDGE=""
DXMT_WINEMAC_COMPAT=""
SIGNING_IDENTITY=${REALSTEAMONMAC_INSTALLER_IDENTITY:-}
RELEASE_PRIVATE_KEY=${REALSTEAMONMAC_RELEASE_PRIVATE_KEY:-"$HOME/.config/RealSteamOnMac/release-ed25519-private.pem"}
REPOSITORY=${REALSTEAMONMAC_REPOSITORY:-"dazi2011/RealSteamOnMac"}
STEAM_BUILDS=${REALSTEAMONMAC_STEAM_BUILDS:-${REALSTEAMONMAC_STEAM_BUILD:-"1780705203,1780965181"}}

usage() {
    cat >&2 <<EOF
usage: $0 [--output DIRECTORY] [--steamworks-bridge DIRECTORY] [--gptk-steamworks-bridge DIRECTORY] [--dxmt-winemac-compat DIRECTORY] [--signing-identity NAME] [--release-private-key PATH]
EOF
    exit 2
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --output)
            [ "$#" -ge 2 ] || usage
            OUTPUT=$2
            shift 2
            ;;
        --steamworks-bridge)
            [ "$#" -ge 2 ] || usage
            BRIDGE=$2
            shift 2
            ;;
        --gptk-steamworks-bridge)
            [ "$#" -ge 2 ] || usage
            GPTK_BRIDGE=$2
            shift 2
            ;;
        --dxmt-winemac-compat)
            [ "$#" -ge 2 ] || usage
            DXMT_WINEMAC_COMPAT=$2
            shift 2
            ;;
        --signing-identity)
            [ "$#" -ge 2 ] || usage
            SIGNING_IDENTITY=$2
            shift 2
            ;;
        --release-private-key)
            [ "$#" -ge 2 ] || usage
            RELEASE_PRIVATE_KEY=$2
            shift 2
            ;;
        *)
            usage
            ;;
    esac
done

case "$VERSION" in
    *[!0-9.]*|*.*.*.*|"") usage ;;
esac
if [ -z "$BRIDGE" ]; then
    ACTIVE_RUNTIME="$HOME/Library/Application Support/RealSteamOnMac/runtimes/current"
    BRIDGE="$ACTIVE_RUNTIME/steamworks/wine11"
fi
if [ -z "$GPTK_BRIDGE" ]; then
    ACTIVE_RUNTIME="$HOME/Library/Application Support/RealSteamOnMac/runtimes/current"
    GPTK_BRIDGE="$ACTIVE_RUNTIME/steamworks/gptk"
fi
[ -f "$BRIDGE/x86_64-windows/lsteamclient.dll" ] || {
    echo "Steamworks bridge is missing: $BRIDGE" >&2
    exit 1
}
[ -f "$BRIDGE/x86_64-unix/lsteamclient.so" ] || {
    echo "Steamworks bridge is missing: $BRIDGE" >&2
    exit 1
}
[ -f "$GPTK_BRIDGE/x86_64-windows/lsteamclient.dll" ] || {
    echo "GPTK Steamworks bridge is missing: $GPTK_BRIDGE" >&2
    exit 1
}
[ -f "$GPTK_BRIDGE/x86_64-unix/lsteamclient.dll.so" ] || {
    echo "GPTK Steamworks bridge is missing: $GPTK_BRIDGE" >&2
    exit 1
}
if [ -z "$DXMT_WINEMAC_COMPAT" ]; then
    DXMT_WINEMAC_COMPAT="$ROOT/artifacts/dxmt-winemac-compat"
fi
if [ ! -f "$DXMT_WINEMAC_COMPAT/winemac.so" ] ||
    [ ! -f "$DXMT_WINEMAC_COMPAT/librealsteamonmac_dxmt_macdrv_shim.dylib" ] ||
    [ ! -f "$DXMT_WINEMAC_COMPAT/build-info.json" ] ||
    [ ! -f "$DXMT_WINEMAC_COMPAT/SHA256SUMS" ]; then
    [ "$DXMT_WINEMAC_COMPAT" = "$ROOT/artifacts/dxmt-winemac-compat" ] || {
        echo "DXMT Wine compatibility package is incomplete: $DXMT_WINEMAC_COMPAT" >&2
        exit 1
    }
    "$ROOT/script/build_dxmt_winemac_compat.sh" \
        --output "$DXMT_WINEMAC_COMPAT"
fi
(
    cd "$DXMT_WINEMAC_COMPAT"
    shasum -a 256 -c SHA256SUMS
)
/usr/bin/python3 - "$DXMT_WINEMAC_COMPAT/build-info.json" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as stream:
    value = json.load(stream)
expected = {
    "schema": 1,
    "name": "RealSteamOnMac DXMT Wine macdrv compatibility",
    "wine_commit": "2cac6ccf33c0807f374dc96f5a20e35a2da86157",
    "wine_staging_commit": "f45e84d7a01a52d379e4003f03800c13875c69e9",
    "minimum_macos": "10.15",
    "dxmt_version": "0.80",
}
if value != expected:
    raise SystemExit("DXMT Wine compatibility build metadata mismatch")
PY
if [ "${REALSTEAMONMAC_ALLOW_TEST_FIXTURES:-0}" != 1 ]; then
    file "$BRIDGE/x86_64-windows/lsteamclient.dll" |
        grep -q 'PE32+.*x86-64'
    file "$BRIDGE/x86_64-unix/lsteamclient.so" |
        grep -q 'Mach-O 64-bit.*x86_64'
    file "$GPTK_BRIDGE/x86_64-windows/lsteamclient.dll" |
        grep -q 'PE32+.*x86-64'
    file "$GPTK_BRIDGE/x86_64-unix/lsteamclient.dll.so" |
        grep -q 'Mach-O 64-bit.*x86_64'
    file "$DXMT_WINEMAC_COMPAT/winemac.so" |
        grep -q 'Mach-O 64-bit.*x86_64'
    file "$DXMT_WINEMAC_COMPAT/librealsteamonmac_dxmt_macdrv_shim.dylib" |
        grep -q 'Mach-O 64-bit.*x86_64'
    codesign --verify "$DXMT_WINEMAC_COMPAT/winemac.so"
    codesign --verify \
        "$DXMT_WINEMAC_COMPAT/librealsteamonmac_dxmt_macdrv_shim.dylib"
fi
[ -f "$RELEASE_PRIVATE_KEY" ] || {
    echo "release signing key is missing: $RELEASE_PRIVATE_KEY" >&2
    exit 1
}

"$ROOT/script/build_compat_gate_hook.sh"
"$ROOT/script/build_steam_launcher.sh"

WORK=$(mktemp -d "${TMPDIR:-/tmp}/realsteamonmac-release.XXXXXX")
trap 'rm -rf "$WORK"' EXIT INT TERM
PAYLOAD="$WORK/install-root/Library/Application Support/RealSteamOnMac/Installer"
mkdir -p "$PAYLOAD" "$PAYLOAD/prebuilt" "$OUTPUT"

for path in VERSION LICENSE THIRD_PARTY_NOTICES.md compat-tool config hook launcher patches runtime script third_party ui; do
    ditto "$ROOT/$path" "$PAYLOAD/$path"
done
find "$PAYLOAD" -name .DS_Store -delete
find "$PAYLOAD" -type d -name __pycache__ -prune -exec rm -rf {} +
find "$PAYLOAD" -type f -name '*.pyc' -delete
find "$PAYLOAD/compat-tool" -type d -empty -delete
mkdir -p \
    "$PAYLOAD/artifacts/compat-gate-hook" \
    "$PAYLOAD/artifacts/dxmt-winemac-compat" \
    "$PAYLOAD/artifacts/steam-launcher"
ditto "$ROOT/artifacts/compat-gate-hook" \
    "$PAYLOAD/artifacts/compat-gate-hook"
ditto "$DXMT_WINEMAC_COMPAT" \
    "$PAYLOAD/artifacts/dxmt-winemac-compat"
ditto "$ROOT/artifacts/steam-launcher" \
    "$PAYLOAD/artifacts/steam-launcher"
ditto "$BRIDGE" \
    "$PAYLOAD/prebuilt/lsteamclient-proton11b5-macos2"
ditto "$GPTK_BRIDGE" \
    "$PAYLOAD/prebuilt/lsteamclient-proton7-gptk7.7-macos1"

/usr/bin/swiftc -O \
    "$ROOT/script/verify_release_signature.swift" \
    -o "$PAYLOAD/prebuilt/realsteamonmac-verify-signature"

chmod 0755 \
    "$PAYLOAD/script/install_realsteamonmac.sh" \
    "$PAYLOAD/script/uninstall_realsteamonmac.sh" \
    "$PAYLOAD/script/check_for_updates.py" \
    "$PAYLOAD/prebuilt/realsteamonmac-verify-signature"

INSTALL_COMPONENT="$WORK/RealSteamOnMac-Install-component.pkg"
UNINSTALL_COMPONENT="$WORK/RealSteamOnMac-Uninstall-component.pkg"
pkgbuild \
    --root "$WORK/install-root" \
    --scripts "$ROOT/packaging/install/scripts" \
    --identifier io.github.dazi2011.realsteamonmac.install \
    --version "$VERSION" \
    "$INSTALL_COMPONENT"
pkgbuild \
    --nopayload \
    --scripts "$ROOT/packaging/uninstall/scripts" \
    --identifier io.github.dazi2011.realsteamonmac.uninstall \
    --version "$VERSION" \
    "$UNINSTALL_COMPONENT"

INSTALL_PKG="$OUTPUT/RealSteamOnMac-Install.pkg"
UNINSTALL_PKG="$OUTPUT/RealSteamOnMac-Uninstall.pkg"
if [ -n "$SIGNING_IDENTITY" ]; then
    productsign --sign "$SIGNING_IDENTITY" \
        "$INSTALL_COMPONENT" "$INSTALL_PKG"
    productsign --sign "$SIGNING_IDENTITY" \
        "$UNINSTALL_COMPONENT" "$UNINSTALL_PKG"
else
    cp "$INSTALL_COMPONENT" "$INSTALL_PKG"
    cp "$UNINSTALL_COMPONENT" "$UNINSTALL_PKG"
fi

(
    cd "$OUTPUT"
    shasum -a 256 \
        RealSteamOnMac-Install.pkg \
        RealSteamOnMac-Uninstall.pkg \
        >SHA256SUMS
)

TAG="v$VERSION"
INSTALL_SHA=$(shasum -a 256 "$INSTALL_PKG" | awk '{print $1}')
UNINSTALL_SHA=$(shasum -a 256 "$UNINSTALL_PKG" | awk '{print $1}')
INSTALL_SIZE=$(stat -f '%z' "$INSTALL_PKG")
UNINSTALL_SIZE=$(stat -f '%z' "$UNINSTALL_PKG")
MANIFEST="$OUTPUT/release-manifest.json"
/usr/bin/python3 - \
    "$MANIFEST" \
    "$VERSION" \
    "$REPOSITORY" \
    "$STEAM_BUILDS" \
    "$INSTALL_SHA" \
    "$INSTALL_SIZE" \
    "$UNINSTALL_SHA" \
    "$UNINSTALL_SIZE" <<'PY'
import datetime
import json
import sys

(
    output,
    version,
    repository,
    steam_builds_raw,
    install_sha,
    install_size,
    uninstall_sha,
    uninstall_size,
) = sys.argv[1:]
steam_builds = steam_builds_raw.split(",")
if (
    not steam_builds
    or len(steam_builds) != len(set(steam_builds))
    or any(
        not build.isdecimal() or not 8 <= len(build) <= 12
        for build in steam_builds
    )
):
    raise SystemExit("supported Steam build list is invalid")
tag = f"v{version}"
base = f"https://github.com/{repository}/releases/download/{tag}"
manifest = {
    "schema": 1,
    "version": version,
    "tag": tag,
    "repository": repository,
    "published_utc": datetime.datetime.now(
        datetime.timezone.utc
    ).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    "supported_steam_builds": steam_builds,
    "minimum_macos": "14.0",
    "architecture": "arm64",
    "installer": {
        "name": "RealSteamOnMac-Install.pkg",
        "sha256": install_sha,
        "size": int(install_size),
        "url": f"{base}/RealSteamOnMac-Install.pkg",
    },
    "uninstaller": {
        "name": "RealSteamOnMac-Uninstall.pkg",
        "sha256": uninstall_sha,
        "size": int(uninstall_size),
        "url": f"{base}/RealSteamOnMac-Uninstall.pkg",
    },
}
with open(output, "w", encoding="utf-8") as stream:
    json.dump(manifest, stream, indent=2, sort_keys=True)
    stream.write("\n")
PY

/opt/homebrew/bin/openssl pkeyutl \
    -sign \
    -rawin \
    -inkey "$RELEASE_PRIVATE_KEY" \
    -in "$MANIFEST" \
    -out "$OUTPUT/release-manifest.json.sig"

"$PAYLOAD/prebuilt/realsteamonmac-verify-signature" \
    "$(tr -d '[:space:]' <"$ROOT/config/release-public-key.hex")" \
    "$MANIFEST" \
    "$OUTPUT/release-manifest.json.sig"

echo "install=$INSTALL_PKG"
echo "uninstall=$UNINSTALL_PKG"
echo "checksums=$OUTPUT/SHA256SUMS"
echo "manifest=$MANIFEST"
if [ -z "$SIGNING_IDENTITY" ]; then
    echo "signature=unsigned-pkg (Developer ID Installer unavailable)"
else
    echo "signature=$SIGNING_IDENTITY"
fi
