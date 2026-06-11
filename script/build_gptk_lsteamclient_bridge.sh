#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
PROTON_COMMIT="c5ad95671cecaf03c4a92500de84b542add585d1"
PROTON_URL="https://github.com/ValveSoftware/Proton.git"
CROSSOVER_SOURCE_URL="https://media.codeweavers.com/pub/crossover/source/crossover-sources-22.1.1.tar.gz"
CROSSOVER_SOURCE_SHA256="cdfe282ce33788bd4f969c8bfb1d3e2de060eb6c296fa1c3cdf4e4690b8b1831"
APPLE_FORMULA_COMMIT="2bc44284e24d39ed64d6f492a0e1f4c47a5ced08"
APPLE_FORMULA_URL="https://raw.githubusercontent.com/apple/homebrew-apple/2bc44284e24d39ed64d6f492a0e1f4c47a5ced08/Formula/game-porting-toolkit.rb"
APPLE_FORMULA_SHA256="7a124b8e74edd3f453ef366e4e103608857801fbc5e085dc6fe885d57b6c9568"
WORK_ROOT="${REALSTEAMONMAC_BUILD_ROOT:-$HOME/Library/Caches/RealSteamOnMac/build/lsteamclient-proton7-gptk7.7-macos1}"
OUTPUT="${REALSTEAMONMAC_BRIDGE_OUTPUT:-$HOME/Library/Application Support/RealSteamOnMac/build/lsteamclient-proton7-gptk7.7-macos1}"
SOURCE_CACHE="${REALSTEAMONMAC_SOURCE_CACHE:-$HOME/Library/Caches/RealSteamOnMac/sources}"
TOOLCHAIN="${REALSTEAMONMAC_GPTK_TOOLCHAIN:-$HOME/Library/Application Support/RealSteamOnMac/toolchains/gptk-compiler-22.1.1}"
PROTON_SOURCE=""
CROSSOVER_SOURCE_ARCHIVE=""
APPLE_FORMULA=""
JOBS=$(sysctl -n hw.logicalcpu 2>/dev/null || printf '4')

usage() {
    cat >&2 <<EOF
usage: $0 [--output DIRECTORY] [--work-root DIRECTORY]
          [--source-cache DIRECTORY] [--proton-source DIRECTORY]
          [--crossover-source-archive FILE] [--toolchain DIRECTORY]
          [--apple-formula FILE] [--jobs COUNT]
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
        --work-root)
            [ "$#" -ge 2 ] || usage
            WORK_ROOT=$2
            shift 2
            ;;
        --source-cache)
            [ "$#" -ge 2 ] || usage
            SOURCE_CACHE=$2
            shift 2
            ;;
        --proton-source)
            [ "$#" -ge 2 ] || usage
            PROTON_SOURCE=$2
            shift 2
            ;;
        --crossover-source-archive)
            [ "$#" -ge 2 ] || usage
            CROSSOVER_SOURCE_ARCHIVE=$2
            shift 2
            ;;
        --toolchain)
            [ "$#" -ge 2 ] || usage
            TOOLCHAIN=$2
            shift 2
            ;;
        --apple-formula)
            [ "$#" -ge 2 ] || usage
            APPLE_FORMULA=$2
            shift 2
            ;;
        --jobs)
            [ "$#" -ge 2 ] || usage
            JOBS=$2
            shift 2
            ;;
        *)
            usage
            ;;
    esac
done

case "$JOBS" in
    *[!0-9]*|"") usage ;;
esac

BREW_PREFIX=$(brew --prefix 2>/dev/null || true)
if [ -n "$BREW_PREFIX" ]; then
    PATH="$BREW_PREFIX/opt/bison/bin:$BREW_PREFIX/bin:$PATH"
    export PATH
fi

for command in bison curl file git make nm otool patch perl python3 shasum tar xcrun; do
    command -v "$command" >/dev/null 2>&1 || {
        echo "required build command is unavailable: $command" >&2
        exit 1
    }
done
case "$(bison --version | sed -n '1s/.* //p')" in
    0.*|1.*|2.*)
        echo "GNU Bison 3 or newer is required" >&2
        exit 1
        ;;
esac

test -x "$TOOLCHAIN/bin/clang"
test -x "$TOOLCHAIN/bin/clang++"
file "$TOOLCHAIN/bin/clang" | grep -q 'Mach-O 64-bit.*x86_64'
"$TOOLCHAIN/bin/clang" --version | grep -q 'clang version 8\.0\.0'
xcrun --find clang++ >/dev/null

mkdir -p "$WORK_ROOT" "$SOURCE_CACHE"

verify_sha256() {
    path=$1
    expected=$2
    actual=$(shasum -a 256 "$path" | awk '{print $1}')
    if [ "$actual" != "$expected" ]; then
        echo "source checksum mismatch: $path" >&2
        echo "expected $expected" >&2
        echo "actual   $actual" >&2
        exit 1
    fi
}

checkout_commit() {
    url=$1
    commit=$2
    destination=$3
    if [ ! -d "$destination/.git" ]; then
        git init -q "$destination"
        git -C "$destination" remote add origin "$url"
        git -C "$destination" sparse-checkout init --cone
        git -C "$destination" sparse-checkout set lsteamclient
        git -C "$destination" fetch --depth 1 origin "$commit"
        git -C "$destination" checkout -q --detach FETCH_HEAD
    fi
    actual=$(git -C "$destination" rev-parse HEAD)
    if [ "$actual" != "$commit" ]; then
        echo "source checkout has unexpected commit: $destination" >&2
        echo "expected $commit" >&2
        echo "actual   $actual" >&2
        exit 1
    fi
}

if [ -z "$PROTON_SOURCE" ]; then
    PROTON_SOURCE="$SOURCE_CACHE/proton-7.0-6-lsteamclient"
    checkout_commit "$PROTON_URL" "$PROTON_COMMIT" "$PROTON_SOURCE"
else
    test "$(git -C "$PROTON_SOURCE" rev-parse HEAD)" = "$PROTON_COMMIT"
fi

if [ -z "$CROSSOVER_SOURCE_ARCHIVE" ]; then
    CROSSOVER_SOURCE_ARCHIVE="$SOURCE_CACHE/crossover-sources-22.1.1.tar.gz"
    if [ ! -f "$CROSSOVER_SOURCE_ARCHIVE" ]; then
        temporary="$CROSSOVER_SOURCE_ARCHIVE.download.$$"
        trap 'rm -f "$temporary"' EXIT INT TERM
        curl --fail --location --retry 3 \
            --output "$temporary" "$CROSSOVER_SOURCE_URL"
        verify_sha256 "$temporary" "$CROSSOVER_SOURCE_SHA256"
        mv "$temporary" "$CROSSOVER_SOURCE_ARCHIVE"
        trap - EXIT INT TERM
    fi
fi
verify_sha256 "$CROSSOVER_SOURCE_ARCHIVE" "$CROSSOVER_SOURCE_SHA256"

if [ -z "$APPLE_FORMULA" ]; then
    APPLE_FORMULA="$SOURCE_CACHE/game-porting-toolkit-$APPLE_FORMULA_COMMIT.rb"
    if [ ! -f "$APPLE_FORMULA" ]; then
        temporary="$APPLE_FORMULA.download.$$"
        trap 'rm -f "$temporary"' EXIT INT TERM
        curl --fail --location --retry 3 \
            --output "$temporary" "$APPLE_FORMULA_URL"
        verify_sha256 "$temporary" "$APPLE_FORMULA_SHA256"
        mv "$temporary" "$APPLE_FORMULA"
        trap - EXIT INT TERM
    fi
fi
verify_sha256 "$APPLE_FORMULA" "$APPLE_FORMULA_SHA256"

CROSSOVER_SOURCE="$WORK_ROOT/crossover-22.1.1-apple-gptk-1.1"
WINE_SOURCE="$CROSSOVER_SOURCE/sources/wine"
if [ ! -f "$WINE_SOURCE/configure" ]; then
    mkdir -p "$CROSSOVER_SOURCE"
    tar -xzf "$CROSSOVER_SOURCE_ARCHIVE" \
        -C "$CROSSOVER_SOURCE" sources/wine
fi
test "$(sed -n 's/^Wine version //p' "$WINE_SOURCE/VERSION")" = "7.7"
APPLE_WINE_PATCH="$WORK_ROOT/apple-gptk-wine.patch"
python3 - "$APPLE_FORMULA" "$APPLE_WINE_PATCH" <<'PY'
import pathlib
import sys

source = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
marker = "\n__END__\n"
if marker not in source:
    raise SystemExit("Apple GPTK formula has no DATA patch")
path = pathlib.Path(sys.argv[2])
path.write_text(source.split(marker, 1)[1], encoding="utf-8")
PY
APPLE_PATCH_MARKER="$WINE_SOURCE/.realsteamonmac-apple-gptk-patched"
if [ ! -f "$APPLE_PATCH_MARKER" ]; then
    if [ -f "$WINE_SOURCE/include/distversion.h" ]; then
        echo "incomplete Apple-patched Wine source cache: $WINE_SOURCE" >&2
        echo "choose a new --work-root after preserving diagnostic logs" >&2
        exit 1
    fi
    patch -d "$CROSSOVER_SOURCE/sources" -p0 -f <"$APPLE_WINE_PATCH"
    : >"$APPLE_PATCH_MARKER"
fi

BRIDGE_SOURCE="$WORK_ROOT/lsteamclient.dll"
if [ ! -f "$BRIDGE_SOURCE/steamclient_main.c" ]; then
    cp -R "$PROTON_SOURCE/lsteamclient" "$BRIDGE_SOURCE"
fi
PATCH="$ROOT/patches/proton7-lsteamclient-macos.patch"
if ! grep -q 'Carbon virtual key codes used by the native Steam Input client' \
    "$BRIDGE_SOURCE/steamclient_main.c"; then
    if ! patch -d "$BRIDGE_SOURCE" -p1 -f --dry-run \
        <"$PATCH" >/dev/null 2>&1; then
        echo "Proton 7 lsteamclient source does not match the pinned patch" >&2
        exit 1
    fi
    patch -d "$BRIDGE_SOURCE" -p1 -f <"$PATCH"
fi
if grep -q 'BridgeSmoke' "$BRIDGE_SOURCE/steamclient_main.c" \
    "$BRIDGE_SOURCE/lsteamclient.spec"; then
    echo "diagnostic Steamworks exports are forbidden in release builds" >&2
    exit 1
fi

TOOLCHAIN_LINK="$WORK_ROOT/gptk-toolchain"
ln -sfn "$TOOLCHAIN" "$TOOLCHAIN_LINK"
WINE_BUILD="$WORK_ROOT/wine-build-x86_64-apple-gptk-1.1"
if [ ! -f "$WINE_BUILD/Makefile" ]; then
    mkdir -p "$WINE_BUILD"
    (
        cd "$WINE_BUILD"
        MACOSX_DEPLOYMENT_TARGET=10.14 \
        CC="$TOOLCHAIN_LINK/bin/clang" \
        CXX="$TOOLCHAIN_LINK/bin/clang++" \
        CFLAGS="-O3 -Wno-implicit-function-declaration -Wno-format -Wno-deprecated-declarations -Wno-incompatible-pointer-types" \
        LDFLAGS="-lSystem" \
        "$WINE_SOURCE/configure" \
            --build=x86_64-apple-darwin \
            --enable-win64 \
            --disable-win16 \
            --disable-tests \
            --without-alsa \
            --without-capi \
            --without-dbus \
            --without-fontconfig \
            --without-freetype \
            --without-gphoto \
            --without-gnutls \
            --without-gssapi \
            --without-gstreamer \
            --without-inotify \
            --without-krb5 \
            --without-netapi \
            --without-openal \
            --without-opencl \
            --without-opengl \
            --without-oss \
            --without-pcap \
            --without-pulse \
            --without-sane \
            --without-sdl \
            --without-udev \
            --without-unwind \
            --without-usb \
            --without-v4l2 \
            --without-vulkan \
            --without-x
    )
fi

MACOSX_DEPLOYMENT_TARGET=10.14 make -C "$WINE_BUILD" -j"$JOBS" \
    tools/winebuild/winebuild \
    tools/winegcc/winegcc \
    tools/wrc/wrc \
    dlls/advapi32/libadvapi32.a \
    dlls/user32/libuser32.a \
    dlls/winecrt0/libwinecrt0.a \
    dlls/kernel32/libkernel32.a \
    dlls/ntdll/libntdll.a

WRAPPERS="$WORK_ROOT/winegcc-wrappers"
mkdir -p "$WRAPPERS"
cp "$WINE_BUILD/tools/winegcc/winegcc" "$WRAPPERS/winegcc"
python3 - "$WINE_BUILD/Makefile" <<'PY'
import pathlib
import re
import sys

path = pathlib.Path(sys.argv[1])
content = path.read_text(encoding="utf-8")
pattern = re.compile(r'-DCXX="\\".*?\\""', re.DOTALL)
replacement = r'-DCXX="\"xcrun clang++ -arch x86_64\""'
updated, count = pattern.subn(lambda _match: replacement, content, count=1)
if count != 1:
    raise SystemExit("could not replace Wine C++ compiler definition")
path.write_text(updated, encoding="utf-8")
PY
rm -f \
    "$WINE_BUILD/tools/winegcc/winegcc.o" \
    "$WINE_BUILD/tools/winegcc/winegcc"
MACOSX_DEPLOYMENT_TARGET=10.14 make -C "$WINE_BUILD" -j"$JOBS" \
    tools/winegcc/winegcc
cp "$WINE_BUILD/tools/winegcc/winegcc" "$WRAPPERS/wineg++"

if [ ! -f "$BRIDGE_SOURCE/Makefile" ]; then
    (
        cd "$BRIDGE_SOURCE"
        perl "$WINE_SOURCE/tools/winemaker/winemaker" \
            --nosource-fix \
            --nolower-include \
            --nodlls \
            --nomsvcrt \
            -I"$WINE_SOURCE/include" \
            -I"$WINE_SOURCE/include/wine" \
            -I"$WINE_BUILD/include" \
            --dll \
            -DSTEAM_API_EXPORTS \
            .
    )
fi

MACOSX_DEPLOYMENT_TARGET=10.14 make -C "$BRIDGE_SOURCE" -j"$JOBS" \
    CC="$WRAPPERS/winegcc --wine-objdir=$WINE_BUILD" \
    CXX="$WRAPPERS/wineg++ --wine-objdir=$WINE_BUILD" \
    CFLAGS="-O2 -m64" \
    CXXFLAGS="-O2 -m64" \
    lsteamclient_dll_LDFLAGS="-shared lsteamclient.spec -Wl,-undefined,dynamic_lookup" \
    lsteamclient_dll_LIBRARIES="advapi32 user32 winecrt0 kernel32 ntdll" \
    lsteamclient.dll.so

STAGING=$(mktemp -d "$WORK_ROOT/.bridge-output.XXXXXX")
trap 'rm -rf "$STAGING"' EXIT INT TERM
mkdir -p "$STAGING/x86_64-windows" "$STAGING/x86_64-unix"
cp "$BRIDGE_SOURCE/lsteamclient.dll.so" \
    "$STAGING/x86_64-unix/lsteamclient.dll.so"
MACOSX_DEPLOYMENT_TARGET=10.14 \
    "$WRAPPERS/winegcc" --wine-objdir="$WINE_BUILD" \
    -shared "$BRIDGE_SOURCE/lsteamclient.spec" \
    -o "$STAGING/x86_64-windows/lsteamclient.dll.fake"
mv "$STAGING/x86_64-windows/lsteamclient.dll.fake" \
    "$STAGING/x86_64-windows/lsteamclient.dll"

file "$STAGING/x86_64-unix/lsteamclient.dll.so" |
    grep -q 'Mach-O 64-bit.*x86_64'
file "$STAGING/x86_64-windows/lsteamclient.dll" |
    grep -q 'PE32+.*x86-64'
if nm -u "$STAGING/x86_64-unix/lsteamclient.dll.so" |
    grep -Eq '^_(CloseHandle|CreateEventA|CreateThread|GetModuleHandleW|HeapAlloc|keybd_event)$'; then
    echo "GPTK bridge contains unresolved Win32 API symbols" >&2
    exit 1
fi
if nm -gU "$STAGING/x86_64-unix/lsteamclient.dll.so" |
    grep -q ' _BridgeSmoke$'; then
    echo "diagnostic Steamworks export leaked into release output" >&2
    exit 1
fi

(
    cd "$STAGING"
    shasum -a 256 \
        x86_64-unix/lsteamclient.dll.so \
        x86_64-windows/lsteamclient.dll \
        >SHA256SUMS
    shasum -a 256 -c SHA256SUMS
)

python3 - \
    "$STAGING/build-info.json" \
    "$PROTON_COMMIT" \
    "$CROSSOVER_SOURCE_URL" \
    "$CROSSOVER_SOURCE_SHA256" \
    "$APPLE_FORMULA_COMMIT" \
    "$APPLE_FORMULA_SHA256" <<'PY'
import json
import sys

(
    path,
    proton_commit,
    crossover_source_url,
    crossover_source_sha256,
    apple_formula_commit,
    apple_formula_sha256,
) = sys.argv[1:]
with open(path, "w", encoding="utf-8") as stream:
    json.dump(
        {
            "schema": 1,
            "name": (
                "Valve Proton 7 lsteamclient + GPTK Wine 7.7 "
                "macOS compatibility 1"
            ),
            "proton_commit": proton_commit,
            "wine_version": "7.7",
            "crossover_source_url": crossover_source_url,
            "crossover_source_sha256": crossover_source_sha256,
            "apple_formula_commit": apple_formula_commit,
            "apple_formula_sha256": apple_formula_sha256,
            "architecture": "x86_64",
            "unix_install_name": "lsteamclient.dll.so",
        },
        stream,
        indent=2,
        sort_keys=True,
    )
    stream.write("\n")
PY

if [ -e "$OUTPUT" ]; then
    (
        cd "$OUTPUT"
        shasum -a 256 -c SHA256SUMS
    )
    if ! cmp -s "$STAGING/SHA256SUMS" "$OUTPUT/SHA256SUMS" ||
        ! cmp -s "$STAGING/build-info.json" "$OUTPUT/build-info.json"; then
        echo "existing GPTK bridge output differs from this build: $OUTPUT" >&2
        echo "choose a new --output path after preserving the existing output" >&2
        exit 1
    fi
else
    mkdir -p "$(dirname "$OUTPUT")"
    mv "$STAGING" "$OUTPUT"
fi

echo "$OUTPUT"
