#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
RUNTIME_SOURCE="$ROOT/runtime/realsteamonmac_runtime.py"
DXMT_COMPAT_BUILDER="$ROOT/script/build_dxmt_winemac_compat.sh"
RUNTIME_ROOT="${REALSTEAMONMAC_RUNTIME_ROOT:-$HOME/Library/Application Support/RealSteamOnMac/runtimes}"
CACHE_DIR="${REALSTEAMONMAC_CACHE_DIR:-$HOME/Library/Caches/RealSteamOnMac/downloads}"
GPTK_DMG=""
GPTK_REDIST=""
STEAMWORKS_BRIDGE=""
DXMT_WINEMAC_COMPAT="$ROOT/artifacts/dxmt-winemac-compat"

PACKAGE_ID="gptk3.0-3-wine11.10-dxmt0.80-dxmtmac1-dxvkmacos1.10.3"
STEAMWORKS_PACKAGE_SUFFIX="-lsteamclient-proton11b5-macos2"
STEAMWORKS_PROTON_COMMIT="25880e88befb52c5aa7ff162c5b00b6b8825e494"
DXMT_WINE_COMMIT="2cac6ccf33c0807f374dc96f5a20e35a2da86157"
DXMT_WINE_STAGING_COMMIT="f45e84d7a01a52d379e4003f03800c13875c69e9"

GPTK_ARCHIVE="game-porting-toolkit-3.0-3.tar.xz"
GPTK_URL="https://github.com/Gcenx/game-porting-toolkit/releases/download/Game-Porting-Toolkit-3.0-3/game-porting-toolkit-3.0-3.tar.xz"
GPTK_SHA256="d377683937340f914823dbb2e1252b329cbf834ff58907d0293db8cebf0e392e"

WINE_ARCHIVE="wine-staging-11.10-osx64.tar.xz"
WINE_URL="https://github.com/Gcenx/macOS_Wine_builds/releases/download/11.10/wine-staging-11.10-osx64.tar.xz"
WINE_SHA256="940bdd1a177872020be01c5c33917cb8eecc1cc3193ad554914fb6efd90d7889"

DXMT_ARCHIVE="dxmt-v0.80-builtin.tar.gz"
DXMT_URL="https://github.com/3Shain/dxmt/releases/download/v0.80/dxmt-v0.80-builtin.tar.gz"
DXMT_SHA256="8f260e36b5739e68f3bad613381441385c4dc7b85b78ba8de653d5a6a264529d"

DXVK_ARCHIVE="dxvk-macOS-async-v1.10.3-20230507-repack-builtin.tar.gz"
DXVK_URL="https://github.com/Gcenx/DXVK-macOS/releases/download/v1.10.3-20230507-repack/dxvk-macOS-async-v1.10.3-20230507-repack-builtin.tar.gz"
DXVK_SHA256="810b1e5caf8ce975b784fae866a130ad23fa0ea233b0e5609cbc4a45f3ef6f00"

usage() {
    cat >&2 <<EOF
usage: $0 --gptk-dmg PATH [--dxmt-winemac-compat DIRECTORY] [--steamworks-bridge DIRECTORY] [--runtime-root DIRECTORY] [--cache-dir DIRECTORY]
       $0 --gptk-redist DIRECTORY [--dxmt-winemac-compat DIRECTORY] [--steamworks-bridge DIRECTORY] [--runtime-root DIRECTORY] [--cache-dir DIRECTORY]
EOF
    exit 2
}

while [ "$#" -gt 0 ]; do
    case "$1" in
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
        --steamworks-bridge)
            [ "$#" -ge 2 ] || usage
            STEAMWORKS_BRIDGE=$2
            shift 2
            ;;
        --dxmt-winemac-compat)
            [ "$#" -ge 2 ] || usage
            DXMT_WINEMAC_COMPAT=$2
            shift 2
            ;;
        --runtime-root)
            [ "$#" -ge 2 ] || usage
            RUNTIME_ROOT=$2
            shift 2
            ;;
        --cache-dir)
            [ "$#" -ge 2 ] || usage
            CACHE_DIR=$2
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
if [ -z "$GPTK_DMG" ] && [ -z "$GPTK_REDIST" ]; then
    usage
fi
test -f "$RUNTIME_SOURCE"
if [ -n "$GPTK_DMG" ]; then
    test -f "$GPTK_DMG"
fi
if [ -n "$GPTK_REDIST" ]; then
    test -d "$GPTK_REDIST/lib"
fi
if [ -n "$STEAMWORKS_BRIDGE" ]; then
    test -f "$STEAMWORKS_BRIDGE/x86_64-windows/lsteamclient.dll"
    test -f "$STEAMWORKS_BRIDGE/x86_64-unix/lsteamclient.so"
    PACKAGE_ID="${PACKAGE_ID}${STEAMWORKS_PACKAGE_SUFFIX}"
fi
if [ ! -f "$DXMT_WINEMAC_COMPAT/winemac.so" ] ||
    [ ! -f "$DXMT_WINEMAC_COMPAT/librealsteamonmac_dxmt_macdrv_shim.dylib" ] ||
    [ ! -f "$DXMT_WINEMAC_COMPAT/build-info.json" ] ||
    [ ! -f "$DXMT_WINEMAC_COMPAT/SHA256SUMS" ]; then
    test -x "$DXMT_COMPAT_BUILDER"
    "$DXMT_COMPAT_BUILDER" --output "$DXMT_WINEMAC_COMPAT"
fi
test -f "$DXMT_WINEMAC_COMPAT/winemac.so"
test -f "$DXMT_WINEMAC_COMPAT/librealsteamonmac_dxmt_macdrv_shim.dylib"
test -f "$DXMT_WINEMAC_COMPAT/build-info.json"
test -f "$DXMT_WINEMAC_COMPAT/SHA256SUMS"
(
    cd "$DXMT_WINEMAC_COMPAT"
    shasum -a 256 -c SHA256SUMS
)
file "$DXMT_WINEMAC_COMPAT/winemac.so" | grep -q 'x86_64'
file "$DXMT_WINEMAC_COMPAT/librealsteamonmac_dxmt_macdrv_shim.dylib" |
    grep -q 'x86_64'
nm -gU "$DXMT_WINEMAC_COMPAT/winemac.so" |
    grep -q ' _macdrv_functions$'
nm -gU "$DXMT_WINEMAC_COMPAT/librealsteamonmac_dxmt_macdrv_shim.dylib" |
    grep -q ' _macdrv_functions$'
codesign --verify "$DXMT_WINEMAC_COMPAT/winemac.so"
codesign --verify \
    "$DXMT_WINEMAC_COMPAT/librealsteamonmac_dxmt_macdrv_shim.dylib"
/usr/bin/python3 - \
    "$DXMT_WINEMAC_COMPAT/build-info.json" \
    "$DXMT_WINE_COMMIT" \
    "$DXMT_WINE_STAGING_COMMIT" <<'PY'
import json
import sys

path, wine_commit, staging_commit = sys.argv[1:]
with open(path, encoding="utf-8") as stream:
    value = json.load(stream)
expected = {
    "schema": 1,
    "name": "RealSteamOnMac DXMT Wine macdrv compatibility",
    "wine_commit": wine_commit,
    "wine_staging_commit": staging_commit,
    "minimum_macos": "10.15",
    "dxmt_version": "0.80",
}
if value != expected:
    raise SystemExit("DXMT Wine compatibility build metadata mismatch")
PY

mkdir -p "$CACHE_DIR" "$RUNTIME_ROOT/packages" "$RUNTIME_ROOT/bin"
STAGING=$(mktemp -d "$RUNTIME_ROOT/.staging.$PACKAGE_ID.XXXXXX")
OUTER_MOUNT=""
INNER_MOUNT=""

cleanup() {
    if [ -n "$INNER_MOUNT" ]; then
        hdiutil detach "$INNER_MOUNT" -quiet ||
            hdiutil detach "$INNER_MOUNT" -force -quiet ||
            true
        rmdir "$INNER_MOUNT" 2>/dev/null || true
    fi
    if [ -n "$OUTER_MOUNT" ]; then
        hdiutil detach "$OUTER_MOUNT" -quiet ||
            hdiutil detach "$OUTER_MOUNT" -force -quiet ||
            true
        rmdir "$OUTER_MOUNT" 2>/dev/null || true
    fi
    rm -rf "$STAGING"
}
trap cleanup EXIT INT TERM

fetch_and_verify() {
    name=$1
    url=$2
    expected=$3
    destination="$CACHE_DIR/$name"
    if [ ! -f "$destination" ]; then
        curl -fL --retry 3 --continue-at - -o "$destination" "$url"
    fi
    actual=$(shasum -a 256 "$destination" | awk '{print $1}')
    if [ "$actual" != "$expected" ]; then
        echo "checksum mismatch for $destination" >&2
        echo "expected $expected" >&2
        echo "actual   $actual" >&2
        exit 1
    fi
    printf '%s\n' "$destination"
}

clone_tree() {
    source=$1
    destination=$2
    if cp -cR "$source" "$destination" 2>/dev/null; then
        return
    fi
    ditto "$source" "$destination"
}

first_directory() {
    base=$1
    pattern=$2
    result=$(find "$base" -type d -path "$pattern" -print -quit)
    [ -n "$result" ] || {
        echo "required directory was not found: $pattern" >&2
        exit 1
    }
    printf '%s\n' "$result"
}

GPTK_SOURCE=$(fetch_and_verify "$GPTK_ARCHIVE" "$GPTK_URL" "$GPTK_SHA256")
WINE_SOURCE=$(fetch_and_verify "$WINE_ARCHIVE" "$WINE_URL" "$WINE_SHA256")
DXMT_SOURCE=$(fetch_and_verify "$DXMT_ARCHIVE" "$DXMT_URL" "$DXMT_SHA256")
DXVK_SOURCE=$(fetch_and_verify "$DXVK_ARCHIVE" "$DXVK_URL" "$DXVK_SHA256")

if [ -z "$GPTK_REDIST" ]; then
    OUTER_MOUNT=$(mktemp -d "/tmp/realsteamonmac-gptk-outer.XXXXXX")
    INNER_MOUNT=$(mktemp -d "/tmp/realsteamonmac-gptk-inner.XXXXXX")
    hdiutil attach "$GPTK_DMG" -readonly -nobrowse -mountpoint "$OUTER_MOUNT" -quiet
    INNER_DMG=$(find "$OUTER_MOUNT" -maxdepth 2 -type f -name 'Evaluation environment for Windows games*.dmg' -print -quit)
    [ -n "$INNER_DMG" ] || {
        echo "GPTK evaluation environment image was not found" >&2
        exit 1
    }
    hdiutil attach "$INNER_DMG" -readonly -nobrowse -mountpoint "$INNER_MOUNT" -quiet
    GPTK_REDIST="$INNER_MOUNT/redist"
fi

test -d "$GPTK_REDIST/lib/external/D3DMetal.framework"
test -f "$GPTK_REDIST/lib/wine/x86_64-windows/d3d11.dll"
test -f "$GPTK_REDIST/lib/wine/x86_64-windows/nvngx-on-metalfx.dll"

PACKAGE="$STAGING/package"
mkdir -p "$PACKAGE/wine" "$PACKAGE/renderers" "$PACKAGE/licenses"

mkdir -p "$STAGING/gptk-source" "$STAGING/wine-source"
tar -xJf "$GPTK_SOURCE" -C "$STAGING/gptk-source"
tar -xJf "$WINE_SOURCE" -C "$STAGING/wine-source"
GPTK_WINE=$(first_directory "$STAGING/gptk-source" '*/Game Porting Toolkit.app/Contents/Resources/wine')
STAGING_WINE=$(first_directory "$STAGING/wine-source" '*/Wine Staging.app/Contents/Resources/wine')

clone_tree "$GPTK_WINE" "$PACKAGE/wine/gptk"
ditto "$GPTK_REDIST/lib" "$PACKAGE/wine/gptk/lib"
clone_tree "$STAGING_WINE" "$PACKAGE/wine/wined3d"
if [ ! -e "$PACKAGE/wine/wined3d/bin/wine64" ]; then
    test -x "$PACKAGE/wine/wined3d/bin/wine"
    ln -s wine "$PACKAGE/wine/wined3d/bin/wine64"
fi
clone_tree "$PACKAGE/wine/wined3d" "$PACKAGE/wine/dxmt"
clone_tree "$PACKAGE/wine/wined3d" "$PACKAGE/wine/dxvk"

cp "$DXMT_WINEMAC_COMPAT/winemac.so" \
    "$PACKAGE/wine/dxmt/lib/wine/x86_64-unix/winemac.so"
cp "$DXMT_WINEMAC_COMPAT/librealsteamonmac_dxmt_macdrv_shim.dylib" \
    "$PACKAGE/wine/dxmt/lib/librealsteamonmac_dxmt_macdrv_shim.dylib"
mkdir -p "$PACKAGE/dxmt-winemac-compat"
cp "$DXMT_WINEMAC_COMPAT/build-info.json" \
    "$PACKAGE/dxmt-winemac-compat/build-info.json"

if [ -n "$STEAMWORKS_BRIDGE" ]; then
    mkdir -p \
        "$PACKAGE/steamworks/x86_64-windows" \
        "$PACKAGE/steamworks/x86_64-unix"
    cp "$STEAMWORKS_BRIDGE/x86_64-windows/lsteamclient.dll" \
        "$PACKAGE/steamworks/x86_64-windows/lsteamclient.dll"
    cp "$STEAMWORKS_BRIDGE/x86_64-unix/lsteamclient.so" \
        "$PACKAGE/steamworks/x86_64-unix/lsteamclient.so"
    for renderer in dxmt dxvk wined3d; do
        cp "$STEAMWORKS_BRIDGE/x86_64-windows/lsteamclient.dll" \
            "$PACKAGE/wine/$renderer/lib/wine/x86_64-windows/lsteamclient.dll"
        cp "$STEAMWORKS_BRIDGE/x86_64-unix/lsteamclient.so" \
            "$PACKAGE/wine/$renderer/lib/wine/x86_64-unix/lsteamclient.so"
    done
fi

mkdir -p "$STAGING/dxmt" "$STAGING/dxvk"
tar -xzf "$DXMT_SOURCE" -C "$STAGING/dxmt"
tar -xzf "$DXVK_SOURCE" -C "$STAGING/dxvk"
DXMT_ROOT=$(first_directory "$STAGING/dxmt" '*/v0.80')
DXVK_ROOT=$(first_directory "$STAGING/dxvk" '*/dxvk-macOS-async-v1.10.3-20230507-repack-builtin')

ditto "$DXMT_ROOT" "$PACKAGE/renderers/dxmt"
ditto "$DXVK_ROOT" "$PACKAGE/renderers/dxvk"

cp "$DXMT_ROOT/x86_64-unix/winemetal.so" \
    "$PACKAGE/wine/dxmt/lib/wine/x86_64-unix/winemetal.so"
for file in "$DXMT_ROOT/x86_64-windows/"*.dll; do
    cp "$file" "$PACKAGE/wine/dxmt/lib/wine/x86_64-windows/"
done
for file in "$DXMT_ROOT/i386-windows/"*.dll; do
    cp "$file" "$PACKAGE/wine/dxmt/lib/wine/i386-windows/"
done

for file in "$DXVK_ROOT/x86_64-windows/"*.dll; do
    cp "$file" "$PACKAGE/wine/dxvk/lib/wine/x86_64-windows/"
done
for file in "$DXVK_ROOT/i386-windows/"*.dll; do
    cp "$file" "$PACKAGE/wine/dxvk/lib/wine/i386-windows/"
done

ditto "$GPTK_REDIST/License.rtf" "$PACKAGE/licenses/Apple-GPTK-License.rtf" 2>/dev/null || \
    ditto "$(dirname "$GPTK_REDIST")/License.rtf" "$PACKAGE/licenses/Apple-GPTK-License.rtf"
ditto "$(dirname "$GPTK_REDIST")/Acknowledgements.rtf" "$PACKAGE/licenses/Apple-GPTK-Acknowledgements.rtf"

for renderer in gptk dxmt dxvk wined3d; do
    test -x "$PACKAGE/wine/$renderer/bin/wine64"
    test -x "$PACKAGE/wine/$renderer/bin/wineserver"
done
test -f "$PACKAGE/wine/gptk/lib/external/D3DMetal.framework/Versions/A/D3DMetal"
test -f "$PACKAGE/wine/dxmt/lib/wine/x86_64-unix/winemetal.so"
test -f "$PACKAGE/wine/dxmt/lib/wine/x86_64-unix/winemac.so"
test -f "$PACKAGE/wine/dxmt/lib/librealsteamonmac_dxmt_macdrv_shim.dylib"
test -f "$PACKAGE/wine/dxvk/lib/wine/x86_64-windows/d3d11.dll"
test -f "$PACKAGE/wine/wined3d/lib/wine/x86_64-windows/wined3d.dll"
if [ -n "$STEAMWORKS_BRIDGE" ]; then
    for renderer in dxmt dxvk wined3d; do
        test -f "$PACKAGE/wine/$renderer/lib/wine/x86_64-windows/lsteamclient.dll"
        test -f "$PACKAGE/wine/$renderer/lib/wine/x86_64-unix/lsteamclient.so"
    done
fi

/usr/bin/python3 - \
    "$PACKAGE/manifest.json" \
    "$PACKAGE_ID" \
    "$STEAMWORKS_BRIDGE" \
    "$STEAMWORKS_PROTON_COMMIT" \
    "$PACKAGE/dxmt-winemac-compat/build-info.json" <<'PY'
import json
import sys

(
    path,
    package_id,
    steamworks_bridge,
    proton_commit,
    dxmt_build_info_path,
) = sys.argv[1:]
with open(dxmt_build_info_path, encoding="utf-8") as stream:
    dxmt_build_info = json.load(stream)
manifest = {
    "schema": 1,
    "package_id": package_id,
    "renderers": {
        "gptk": {
            "wine": "game-porting-toolkit-3.0-3",
            "graphics": "Apple Game Porting Toolkit 3.0",
        },
        "dxmt": {
            "wine": "wine-staging-11.10",
            "graphics": "DXMT v0.80 builtin",
        },
        "dxvk": {
            "wine": "wine-staging-11.10",
            "graphics": "DXVK-macOS v1.10.3 builtin",
        },
        "wined3d": {
            "wine": "wine-staging-11.10",
            "graphics": "WineD3D",
        },
    },
    "dxmt_winemac_compat": {
        "name": dxmt_build_info["name"],
        "wine_commit": dxmt_build_info["wine_commit"],
        "wine_staging_commit": dxmt_build_info[
            "wine_staging_commit"
        ],
        "minimum_macos": dxmt_build_info["minimum_macos"],
        "winemac_driver": (
            "wine/dxmt/lib/wine/x86_64-unix/winemac.so"
        ),
        "visibility_shim": (
            "wine/dxmt/lib/"
            "librealsteamonmac_dxmt_macdrv_shim.dylib"
        ),
    },
}
if steamworks_bridge:
    manifest["steamworks_bridge"] = {
        "name": (
            "Valve Proton lsteamclient 11.0-1-beta5 "
            "+ RealSteamOnMac macOS compatibility 2"
        ),
        "proton_commit": proton_commit,
        "renderers": ["dxmt", "dxvk", "wined3d"],
        "unix_library": "steamworks/x86_64-unix/lsteamclient.so",
        "windows_dll": "steamworks/x86_64-windows/lsteamclient.dll",
    }
with open(path, "w", encoding="utf-8") as stream:
    json.dump(manifest, stream, indent=2, sort_keys=True)
    stream.write("\n")
PY

(
    cd "$PACKAGE"
    shasum -a 256 \
        manifest.json \
        wine/gptk/bin/wine64 \
        wine/gptk/lib/external/D3DMetal.framework/Versions/A/D3DMetal \
        wine/dxmt/bin/wine64 \
        wine/dxmt/lib/wine/x86_64-unix/winemac.so \
        wine/dxmt/lib/wine/x86_64-unix/winemetal.so \
        wine/dxmt/lib/librealsteamonmac_dxmt_macdrv_shim.dylib \
        dxmt-winemac-compat/build-info.json \
        wine/dxvk/bin/wine64 \
        wine/dxvk/lib/wine/x86_64-windows/d3d11.dll \
        wine/wined3d/bin/wine64 \
        wine/wined3d/lib/wine/x86_64-windows/wined3d.dll \
        >SHA256SUMS
    if [ -n "$STEAMWORKS_BRIDGE" ]; then
        shasum -a 256 \
            steamworks/x86_64-windows/lsteamclient.dll \
            steamworks/x86_64-unix/lsteamclient.so \
            wine/dxmt/lib/wine/x86_64-windows/lsteamclient.dll \
            wine/dxmt/lib/wine/x86_64-unix/lsteamclient.so \
            wine/dxvk/lib/wine/x86_64-windows/lsteamclient.dll \
            wine/dxvk/lib/wine/x86_64-unix/lsteamclient.so \
            wine/wined3d/lib/wine/x86_64-windows/lsteamclient.dll \
            wine/wined3d/lib/wine/x86_64-unix/lsteamclient.so \
            >>SHA256SUMS
    fi
    shasum -a 256 -c SHA256SUMS
)

DESTINATION="$RUNTIME_ROOT/packages/$PACKAGE_ID"
if [ -e "$DESTINATION" ]; then
    (
        cd "$DESTINATION"
        shasum -a 256 -c SHA256SUMS
    )
else
    mv "$PACKAGE" "$DESTINATION"
fi

RUNTIME_TEMP="$RUNTIME_ROOT/bin/.realsteamonmac-runtime.$$"
cp "$RUNTIME_SOURCE" "$RUNTIME_TEMP"
chmod 0755 "$RUNTIME_TEMP"
mv "$RUNTIME_TEMP" "$RUNTIME_ROOT/bin/realsteamonmac-runtime"

CURRENT_TEMP="$RUNTIME_ROOT/.current.$$"
ln -s "packages/$PACKAGE_ID" "$CURRENT_TEMP"
mv -h "$CURRENT_TEMP" "$RUNTIME_ROOT/current"

echo "package=$DESTINATION"
echo "current=$RUNTIME_ROOT/current"
echo "runtime=$RUNTIME_ROOT/bin/realsteamonmac-runtime"
