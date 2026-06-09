#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
PATCH="$ROOT/patches/wine-11.10-dxmt-macdrv-compat.patch"
DXMT_COMPAT_SOURCE="$ROOT/runtime/dxmt_winemac_compat.c"
SHIM_SOURCE="$ROOT/hook/dxmt_macdrv_visibility_shim.c"
CACHE_DIR="${REALSTEAMONMAC_SOURCE_CACHE:-$HOME/Library/Caches/RealSteamOnMac/sources}"
OUTPUT="$ROOT/artifacts/dxmt-winemac-compat"
WORK_DIR=""

WINE_COMMIT="2cac6ccf33c0807f374dc96f5a20e35a2da86157"
WINE_TAG="wine-11.10"
WINE_REPOSITORY="https://github.com/wine-mirror/wine.git"
STAGING_COMMIT="f45e84d7a01a52d379e4003f03800c13875c69e9"
STAGING_TAG="v11.10"
STAGING_REPOSITORY="https://github.com/wine-staging/wine-staging.git"
MINIMUM_MACOS="10.15"

usage() {
    cat >&2 <<EOF
usage: $0 [--output DIRECTORY] [--cache-dir DIRECTORY] [--work-dir DIRECTORY]
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
        --cache-dir)
            [ "$#" -ge 2 ] || usage
            CACHE_DIR=$2
            shift 2
            ;;
        --work-dir)
            [ "$#" -ge 2 ] || usage
            WORK_DIR=$2
            shift 2
            ;;
        *)
            usage
            ;;
    esac
done

for command in arch brew clang codesign git install_name_tool make nm otool python3 shasum x86_64-w64-mingw32-gcc; do
    command -v "$command" >/dev/null 2>&1 || {
        echo "required build command is unavailable: $command" >&2
        exit 1
    }
done
arch -x86_64 /usr/bin/true
BISON_DIR="$(brew --prefix bison)/bin"
test -x "$BISON_DIR/bison"
"$BISON_DIR/bison" --version |
    awk 'NR == 1 { split($4, version, "."); exit !(version[1] >= 3) }'
test -f "$PATCH"
test -f "$DXMT_COMPAT_SOURCE"
test -f "$SHIM_SOURCE"

mkdir -p "$CACHE_DIR"
WINE_CACHE="$CACHE_DIR/wine-$WINE_TAG"
STAGING_CACHE="$CACHE_DIR/wine-staging-$STAGING_TAG"

ensure_checkout() {
    repository=$1
    tag=$2
    commit=$3
    destination=$4

    if [ ! -d "$destination/.git" ]; then
        git clone --filter=blob:none --no-checkout "$repository" "$destination"
    fi
    git -C "$destination" fetch --depth 1 origin "refs/tags/$tag"
    actual=$(git -C "$destination" rev-parse "FETCH_HEAD^{}")
    if [ "$actual" != "$commit" ]; then
        echo "source tag mismatch for $repository $tag" >&2
        echo "expected $commit" >&2
        echo "actual   $actual" >&2
        exit 1
    fi
    git -C "$destination" checkout --detach --force "$commit"
    git -C "$destination" clean -ffd
}

ensure_checkout \
    "$WINE_REPOSITORY" "$WINE_TAG" "$WINE_COMMIT" "$WINE_CACHE"
ensure_checkout \
    "$STAGING_REPOSITORY" "$STAGING_TAG" "$STAGING_COMMIT" "$STAGING_CACHE"

if [ -n "$WORK_DIR" ]; then
    mkdir -p "$WORK_DIR"
    STAGING="$WORK_DIR/build"
    rm -rf "$STAGING"
    mkdir -p "$STAGING"
    CLEANUP_STAGING=0
else
    STAGING=$(mktemp -d "${TMPDIR:-/tmp}/realsteamonmac-dxmt-winemac.XXXXXX")
    CLEANUP_STAGING=1
fi

cleanup() {
    if [ "$CLEANUP_STAGING" -eq 1 ]; then
        rm -rf "$STAGING"
    fi
}
trap cleanup EXIT INT TERM

SOURCE="$STAGING/wine"
BUILD="$STAGING/build"
ARTIFACTS="$STAGING/artifacts"
if ! cp -cR "$WINE_CACHE" "$SOURCE" 2>/dev/null; then
    ditto "$WINE_CACHE" "$SOURCE"
fi
git -C "$SOURCE" checkout --detach --force "$WINE_COMMIT"
git -C "$SOURCE" clean -ffd
"$STAGING_CACHE/staging/patchinstall.py" \
    DESTDIR="$SOURCE" --all --no-autoconf
git -C "$SOURCE" apply "$PATCH"
cp "$DXMT_COMPAT_SOURCE" "$SOURCE/dlls/winemac.drv/dxmt_compat.c"

mkdir -p "$BUILD" "$ARTIFACTS"
(
    cd "$BUILD"
    env \
        PATH="$BISON_DIR:$PATH" \
        MACOSX_DEPLOYMENT_TARGET="$MINIMUM_MACOS" \
        CC='clang -arch x86_64' \
        CXX='clang++ -arch x86_64' \
        CFLAGS="-O2 -mmacosx-version-min=$MINIMUM_MACOS" \
        CXXFLAGS="-O2 -mmacosx-version-min=$MINIMUM_MACOS" \
        LDFLAGS="-arch x86_64 -mmacosx-version-min=$MINIMUM_MACOS" \
        arch -x86_64 /bin/bash "$SOURCE/configure" \
            --enable-win64 --disable-tests \
            --without-alsa --without-capi --without-cups --without-dbus \
            --without-ffmpeg --without-fontconfig --without-freetype \
            --without-gettext --without-gphoto --without-gnutls \
            --without-gssapi --without-gstreamer --without-krb5 \
            --without-netapi --without-opencl --without-oss --without-pcap \
            --without-pcsclite --without-pulse --without-sane --without-sdl \
            --without-udev --without-usb --without-v4l2 --without-vulkan \
            --without-wayland
    env \
        PATH="$BISON_DIR:$PATH" \
        MACOSX_DEPLOYMENT_TARGET="$MINIMUM_MACOS" \
        make -j"$(sysctl -n hw.logicalcpu)" \
            dlls/winemac.drv/winemac.so
)

cp "$BUILD/dlls/winemac.drv/winemac.so" "$ARTIFACTS/winemac.so"
install_name_tool -id winemac.so "$ARTIFACTS/winemac.so"
clang \
    -arch x86_64 \
    -dynamiclib \
    -O2 \
    -Wall \
    -Wextra \
    -fvisibility=hidden \
    -mmacosx-version-min="$MINIMUM_MACOS" \
    -install_name @rpath/librealsteamonmac_dxmt_macdrv_shim.dylib \
    -o "$ARTIFACTS/librealsteamonmac_dxmt_macdrv_shim.dylib" \
    "$SHIM_SOURCE"
codesign --force --sign - "$ARTIFACTS/winemac.so"
codesign --force --sign - \
    "$ARTIFACTS/librealsteamonmac_dxmt_macdrv_shim.dylib"

file "$ARTIFACTS/winemac.so" | grep -q 'x86_64'
file "$ARTIFACTS/librealsteamonmac_dxmt_macdrv_shim.dylib" |
    grep -q 'x86_64'
nm -gU "$ARTIFACTS/winemac.so" | grep -q ' _macdrv_functions$'
nm -gU "$ARTIFACTS/librealsteamonmac_dxmt_macdrv_shim.dylib" |
    grep -q ' _macdrv_functions$'
otool -l "$ARTIFACTS/winemac.so" |
    grep -A5 LC_BUILD_VERSION |
    grep -q "minos $MINIMUM_MACOS"
otool -l "$ARTIFACTS/librealsteamonmac_dxmt_macdrv_shim.dylib" |
    grep -A5 LC_BUILD_VERSION |
    grep -q "minos $MINIMUM_MACOS"

(
    cd "$ARTIFACTS"
    shasum -a 256 \
        winemac.so \
        librealsteamonmac_dxmt_macdrv_shim.dylib \
        >SHA256SUMS
)

python3 - \
    "$ARTIFACTS/build-info.json" \
    "$WINE_COMMIT" \
    "$STAGING_COMMIT" \
    "$MINIMUM_MACOS" <<'PY'
import json
import sys

path, wine_commit, staging_commit, minimum_macos = sys.argv[1:]
payload = {
    "schema": 1,
    "name": "RealSteamOnMac DXMT Wine macdrv compatibility",
    "wine_commit": wine_commit,
    "wine_staging_commit": staging_commit,
    "minimum_macos": minimum_macos,
    "dxmt_version": "0.80",
}
with open(path, "w", encoding="utf-8") as stream:
    json.dump(payload, stream, indent=2, sort_keys=True)
    stream.write("\n")
PY

mkdir -p "$(dirname "$OUTPUT")"
OUTPUT_TEMP="${OUTPUT}.tmp.$$"
rm -rf "$OUTPUT_TEMP"
mkdir -p "$OUTPUT_TEMP"
cp "$ARTIFACTS/"* "$OUTPUT_TEMP/"
if [ -d "$OUTPUT" ]; then
    (
        cd "$OUTPUT"
        shasum -a 256 -c SHA256SUMS
    )
    cmp -s "$OUTPUT/SHA256SUMS" "$OUTPUT_TEMP/SHA256SUMS"
    cmp -s "$OUTPUT/build-info.json" "$OUTPUT_TEMP/build-info.json"
    rm -rf "$OUTPUT_TEMP"
else
    mv "$OUTPUT_TEMP" "$OUTPUT"
fi

echo "output=$OUTPUT"
