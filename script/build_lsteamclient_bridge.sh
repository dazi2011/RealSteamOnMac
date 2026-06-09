#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
PROTON_COMMIT="25880e88befb52c5aa7ff162c5b00b6b8825e494"
WINE_COMMIT="2f70bfd4d0f4e67a8a599c4a09760579bc2a4fa4"
PROTON_URL="https://github.com/ValveSoftware/Proton.git"
WINE_URL="https://github.com/ValveSoftware/wine.git"
WORK_ROOT="${REALSTEAMONMAC_BUILD_ROOT:-$HOME/Library/Caches/RealSteamOnMac/build/lsteamclient-proton11b5-macos2}"
OUTPUT="${REALSTEAMONMAC_BRIDGE_OUTPUT:-$HOME/Library/Application Support/RealSteamOnMac/build/lsteamclient-proton11b5-macos2}"
WINE_ROOT="${REALSTEAMONMAC_WINE_ROOT:-$HOME/Library/Application Support/RealSteamOnMac/runtimes/current/wine/dxmt}"
PROTON_SOURCE=""
WINE_SOURCE=""
JOBS=$(sysctl -n hw.logicalcpu 2>/dev/null || printf '4')

usage() {
    cat >&2 <<EOF
usage: $0 [--wine-root DIRECTORY] [--output DIRECTORY] [--work-root DIRECTORY]
          [--proton-source DIRECTORY] [--wine-source DIRECTORY] [--jobs COUNT]
EOF
    exit 2
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --wine-root)
            [ "$#" -ge 2 ] || usage
            WINE_ROOT=$2
            shift 2
            ;;
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
        --proton-source)
            [ "$#" -ge 2 ] || usage
            PROTON_SOURCE=$2
            shift 2
            ;;
        --wine-source)
            [ "$#" -ge 2 ] || usage
            WINE_SOURCE=$2
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
    PATH="$BREW_PREFIX/opt/bison/bin:$BREW_PREFIX/opt/make/libexec/gnubin:$BREW_PREFIX/bin:$PATH"
    export PATH
fi

for command in autoconf bison clang clang++ git gmake \
    x86_64-w64-mingw32-gcc x86_64-w64-mingw32-g++ python3; do
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

NTDLL="$WINE_ROOT/lib/wine/x86_64-unix/ntdll.so"
test -f "$NTDLL"

mkdir -p "$WORK_ROOT"

checkout_commit() {
    url=$1
    commit=$2
    destination=$3
    sparse=$4
    if [ ! -d "$destination/.git" ]; then
        git init -q "$destination"
        git -C "$destination" remote add origin "$url"
        if [ -n "$sparse" ]; then
            git -C "$destination" sparse-checkout init --cone
            git -C "$destination" sparse-checkout set "$sparse"
        fi
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
    PROTON_SOURCE="$WORK_ROOT/proton"
    checkout_commit "$PROTON_URL" "$PROTON_COMMIT" "$PROTON_SOURCE" lsteamclient
else
    test "$(git -C "$PROTON_SOURCE" rev-parse HEAD)" = "$PROTON_COMMIT"
fi

if [ -z "$WINE_SOURCE" ]; then
    WINE_SOURCE="$WORK_ROOT/wine"
    checkout_commit "$WINE_URL" "$WINE_COMMIT" "$WINE_SOURCE" ""
else
    test "$(git -C "$WINE_SOURCE" rev-parse HEAD)" = "$WINE_COMMIT"
fi

PATCH="$ROOT/patches/proton-lsteamclient-macos.patch"
if git -C "$PROTON_SOURCE" apply --unidiff-zero --check "$PATCH" 2>/dev/null; then
    git -C "$PROTON_SOURCE" apply --unidiff-zero "$PATCH"
elif ! git -C "$PROTON_SOURCE" apply --unidiff-zero --reverse --check "$PATCH" 2>/dev/null; then
    echo "Proton lsteamclient source does not match the pinned patch" >&2
    exit 1
fi

python3 - \
    "$PROTON_SOURCE/lsteamclient/steamclient_generated.c" \
    "$PROTON_SOURCE/lsteamclient/macos_known_interfaces.inc" <<'PY'
import pathlib
import re
import sys

source, output = map(pathlib.Path, sys.argv[1:])
pattern = re.compile(
    r'^\s*\{"([^"]+)",\s*&create_win[^}]+\},\s*$'
)
interfaces = []
for line in source.read_text(encoding="utf-8").splitlines():
    match = pattern.match(line)
    if match:
        interfaces.append(match.group(1))
if not interfaces:
    raise SystemExit("no generated Steam interfaces were found")
output.write_text(
    "".join(f'        "{name}",\n' for name in sorted(set(interfaces))),
    encoding="utf-8",
)
PY

if [ ! -x "$WINE_SOURCE/configure" ]; then
    (
        cd "$WINE_SOURCE"
        autoconf
    )
fi

WINE_BUILD="$WORK_ROOT/wine-build-x86_64"
if [ ! -f "$WINE_BUILD/Makefile" ]; then
    mkdir -p "$WINE_BUILD"
    (
        cd "$WINE_BUILD"
        CC="clang -arch x86_64" \
        CXX="clang++ -arch x86_64" \
        "$WINE_SOURCE/configure" \
            --build=x86_64-apple-darwin \
            --enable-archs=x86_64 \
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
            --without-krb5 \
            --without-netapi \
            --without-opencl \
            --without-opengl \
            --without-oss \
            --without-pcap \
            --without-pulse \
            --without-sane \
            --without-sdl \
            --without-udev \
            --without-usb \
            --without-v4l2 \
            --without-vulkan \
            --without-wayland \
            --without-x
    )
fi

gmake -C "$WINE_BUILD" -j"$JOBS" \
    tools/makedep \
    tools/winebuild/winebuild \
    tools/winegcc/winegcc \
    tools/widl/widl \
    tools/wrc/wrc \
    dlls/winecrt0/x86_64-windows/libwinecrt0.a \
    dlls/ucrtbase/x86_64-windows/libucrtbase.a \
    dlls/kernel32/x86_64-windows/libkernel32.a \
    dlls/ntdll/x86_64-windows/libntdll.a

ln -sf winegcc "$WINE_BUILD/tools/winegcc/wineg++"
ln -sf winegcc "$WINE_BUILD/tools/winegcc/winecpp"

PRELUDE="$WORK_ROOT/lsteamclient-macos-prelude.hpp"
cat >"$PRELUDE" <<'EOF'
#pragma once

#include <array>
#include <type_traits>
#include <unordered_map>
#include <vector>
EOF

NTDLL_LINK="$WORK_ROOT/dxmt-ntdll.so"
ln -sf "$NTDLL" "$NTDLL_LINK"

BRIDGE_BUILD="$WORK_ROOT/lsteamclient-build-x86_64"
BRIDGE_PREFIX="$WORK_ROOT/lsteamclient-dist"
mkdir -p "$BRIDGE_BUILD"
python3 "$ROOT/script/generate_lsteamclient_makefile.py" \
    --wine-makefile "$WINE_BUILD/Makefile" \
    --wine-source "$WINE_SOURCE" \
    --wine-build "$WINE_BUILD" \
    --lsteamclient-source "$PROTON_SOURCE/lsteamclient" \
    --ntdll "$NTDLL_LINK" \
    --prelude "$PRELUDE" \
    --prefix "$BRIDGE_PREFIX" \
    --output "$BRIDGE_BUILD/Makefile"

(
    cd "$BRIDGE_BUILD"
    "$WINE_BUILD/tools/makedep" -fMakefile
)

gmake -C "$BRIDGE_BUILD" -j"$JOBS" \
    dlls/lsteamclient/lsteamclient.so \
    dlls/lsteamclient/x86_64-windows/lsteamclient.dll

STAGING=$(mktemp -d "$WORK_ROOT/.bridge-output.XXXXXX")
trap 'rm -rf "$STAGING"' EXIT INT TERM
mkdir -p "$STAGING/x86_64-unix" "$STAGING/x86_64-windows"
cp "$BRIDGE_BUILD/dlls/lsteamclient/lsteamclient.so" \
    "$STAGING/x86_64-unix/lsteamclient.so"
cp "$BRIDGE_BUILD/dlls/lsteamclient/x86_64-windows/lsteamclient.dll" \
    "$STAGING/x86_64-windows/lsteamclient.dll"

file "$STAGING/x86_64-unix/lsteamclient.so" | grep -q 'Mach-O 64-bit.*x86_64'
file "$STAGING/x86_64-windows/lsteamclient.dll" | grep -q 'PE32+.*x86-64'
otool -L "$STAGING/x86_64-unix/lsteamclient.so" | grep -q 'ntdll.so'

(
    cd "$STAGING"
    shasum -a 256 \
        x86_64-unix/lsteamclient.so \
        x86_64-windows/lsteamclient.dll \
        >SHA256SUMS
    shasum -a 256 -c SHA256SUMS
)

python3 - "$STAGING/build-info.json" "$PROTON_COMMIT" "$WINE_COMMIT" <<'PY'
import json
import sys

path, proton_commit, wine_commit = sys.argv[1:]
with open(path, "w", encoding="utf-8") as stream:
    json.dump(
        {
            "schema": 1,
            "name": (
                "Valve Proton lsteamclient 11.0-1-beta5 "
                "+ RealSteamOnMac macOS compatibility 2"
            ),
            "proton_commit": proton_commit,
            "wine_commit": wine_commit,
            "architecture": "x86_64",
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
        echo "existing bridge output differs from the reproducible build: $OUTPUT" >&2
        echo "choose a new --output path or remove the stale project-owned output after backup" >&2
        exit 1
    fi
else
    mkdir -p "$(dirname "$OUTPUT")"
    mv "$STAGING" "$OUTPUT"
fi

echo "$OUTPUT"
