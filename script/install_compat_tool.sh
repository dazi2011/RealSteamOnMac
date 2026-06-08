#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
SOURCE="$ROOT/compat-tool/realsteamonmac-experimental"
TARGET_ROOT=""

usage() {
    echo "usage: $0 --target-root DIRECTORY" >&2
    exit 2
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --target-root)
            [ "$#" -ge 2 ] || usage
            TARGET_ROOT=$2
            shift 2
            ;;
        *)
            usage
            ;;
    esac
done

[ -n "$TARGET_ROOT" ] || usage
[ -d "$SOURCE" ] || {
    echo "missing source compat tool: $SOURCE" >&2
    exit 1
}

mkdir -p "$TARGET_ROOT"
DESTINATION="$TARGET_ROOT/realsteamonmac-experimental"
rm -rf "$DESTINATION"
cp -R "$SOURCE" "$DESTINATION"
chmod +x "$DESTINATION/run"

echo "$DESTINATION"
