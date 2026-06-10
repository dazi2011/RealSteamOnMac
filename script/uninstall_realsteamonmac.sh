#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
RESTORE_SCRIPT=${REALSTEAMONMAC_RESTORE_SCRIPT:-"$ROOT/script/restore_steam_from_backup.sh"}
STEAM_STOPPER=${REALSTEAMONMAC_STEAM_STOPPER:-}

SUPPORT_ROOT="$HOME/Library/Application Support/RealSteamOnMac"
STATE_FILE=""
HOLD_ROOT="$HOME/RealSteamOnMac-Rollback"
QUIT_STEAM=false

usage() {
    cat >&2 <<EOF
usage: $0 [--state PATH] [--support-root DIRECTORY] [--hold-root DIRECTORY] [--quit-steam]
EOF
    exit 2
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --state)
            [ "$#" -ge 2 ] || usage
            STATE_FILE=$2
            shift 2
            ;;
        --support-root)
            [ "$#" -ge 2 ] || usage
            SUPPORT_ROOT=$2
            shift 2
            ;;
        --hold-root)
            [ "$#" -ge 2 ] || usage
            HOLD_ROOT=$2
            shift 2
            ;;
        --quit-steam)
            QUIT_STEAM=true
            shift
            ;;
        *)
            usage
            ;;
    esac
done

if [ -z "$STATE_FILE" ]; then
    STATE_FILE="$SUPPORT_ROOT/install-state.json"
fi
[ -f "$STATE_FILE" ] || {
    echo "installation state is missing: $STATE_FILE" >&2
    exit 1
}
[ -x "$RESTORE_SCRIPT" ] || {
    echo "restore script is unavailable: $RESTORE_SCRIPT" >&2
    exit 1
}

read_state_field() {
    /usr/bin/python3 - "$STATE_FILE" "$1" <<'PY'
import json
import os
import sys

path, key = sys.argv[1:]
with open(path, encoding="utf-8") as stream:
    state = json.load(stream)
if state.get("schema") != 1:
    raise SystemExit("unsupported installation state schema")
value = state.get(key)
if not isinstance(value, str) or not os.path.isabs(value):
    raise SystemExit(f"invalid installation state field: {key}")
if any(character in value for character in "\r\n\0"):
    raise SystemExit(f"unsafe installation state field: {key}")
print(value)
PY
}

CLEAN_BACKUP=$(read_state_field clean_backup)
STEAM_APP=$(read_state_field steam_app)
RUNTIME_APP=$(read_state_field runtime_app)
STATE_SUPPORT_ROOT=$(read_state_field support_root)
COMPAT_TOOLS_ROOT=$(read_state_field compat_tools_root)

[ "$STATE_SUPPORT_ROOT" = "$SUPPORT_ROOT" ] || {
    echo "installation state support root does not match --support-root" >&2
    exit 1
}
[ -d "$CLEAN_BACKUP/Steam.app" ] || {
    echo "clean Steam backup is missing: $CLEAN_BACKUP" >&2
    exit 1
}
[ -d "$CLEAN_BACKUP/SteamRuntime.app" ] || {
    echo "clean Steam runtime backup is missing: $CLEAN_BACKUP" >&2
    exit 1
}

RUNTIME_EXECUTABLE="$RUNTIME_APP/Contents/MacOS/steam_osx"
steam_is_running() {
    pgrep -f "^$RUNTIME_EXECUTABLE( |$)" >/dev/null 2>&1
}

stop_steam() {
    if [ -n "$STEAM_STOPPER" ]; then
        "$STEAM_STOPPER" "$RUNTIME_EXECUTABLE"
        return
    fi
    /usr/bin/osascript -e 'tell application "Steam" to quit' \
        >/dev/null 2>&1 || true
    remaining=20
    while steam_is_running && [ "$remaining" -gt 0 ]; do
        sleep 1
        remaining=$((remaining - 1))
    done
    if steam_is_running; then
        pkill -TERM -f "^$RUNTIME_EXECUTABLE( |$)" || true
        sleep 3
    fi
    if steam_is_running; then
        pkill -KILL -f "^$RUNTIME_EXECUTABLE( |$)" || true
        sleep 1
    fi
}

if steam_is_running; then
    if [ "$QUIT_STEAM" != true ]; then
        echo "Steam is running; pass --quit-steam or quit it first" >&2
        exit 1
    fi
    stop_steam
    if steam_is_running; then
        echo "Steam could not be stopped safely" >&2
        exit 1
    fi
fi

STAMP=$(date -u '+%Y%m%dT%H%M%SZ')
SESSION_HOLD="$HOLD_ROOT/uninstall-$STAMP"
mkdir -p "$SESSION_HOLD"
STATE_COPY="$SESSION_HOLD/install-state.json"
cp "$STATE_FILE" "$STATE_COPY"
chmod 0600 "$STATE_COPY"

"$RESTORE_SCRIPT" \
    --clean-backup "$CLEAN_BACKUP" \
    --steam-app "$STEAM_APP" \
    --runtime-app "$RUNTIME_APP" \
    --support-root "$SUPPORT_ROOT" \
    --hold-root "$SESSION_HOLD/steam-restore"

/usr/bin/python3 - \
    "$STATE_COPY" \
    "$COMPAT_TOOLS_ROOT" \
    "$SESSION_HOLD/compatibility-tools-disabled" \
    "$SESSION_HOLD/uninstall-report.txt" <<'PY'
import hashlib
import json
import os
import re
import shutil
import sys
from pathlib import Path

state_path, tools_root, hold_root, report_path = sys.argv[1:]
with open(state_path, encoding="utf-8") as stream:
    state = json.load(stream)
entries = state.get("managed_compat_tools")
if not isinstance(entries, list):
    raise SystemExit("installation state has no managed tool list")
tools = Path(tools_root)
hold = Path(hold_root)
removed = []
skipped = []
pattern = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{1,127}")
for entry in entries:
    if not isinstance(entry, dict):
        raise SystemExit("managed tool entry is invalid")
    name = entry.get("name")
    expected = entry.get("metadata_sha256")
    if (
        not isinstance(name, str)
        or pattern.fullmatch(name) is None
        or not isinstance(expected, str)
        or re.fullmatch(r"[0-9a-f]{64}", expected) is None
    ):
        raise SystemExit("managed tool entry is unsafe")
    directory = tools / name
    metadata = directory / "realsteamonmac.json"
    if not directory.exists():
        skipped.append(f"{name}: already absent")
        continue
    if directory.is_symlink() or not metadata.is_file():
        skipped.append(f"{name}: changed after installation")
        continue
    actual = hashlib.sha256(metadata.read_bytes()).hexdigest()
    if actual != expected:
        skipped.append(f"{name}: metadata changed after installation")
        continue
    hold.mkdir(parents=True, exist_ok=True)
    destination = hold / name
    if destination.exists():
        raise SystemExit(f"rollback destination already exists: {destination}")
    shutil.move(str(directory), str(destination))
    removed.append(name)
with open(report_path, "w", encoding="utf-8") as stream:
    stream.write("RealSteamOnMac uninstall completed\n")
    stream.write(f"clean_backup={state['clean_backup']}\n")
    stream.write("prefixes_preserved=true\n")
    for name in removed:
        stream.write(f"compat_tool_moved={name}\n")
    for message in skipped:
        stream.write(f"compat_tool_preserved={message}\n")
PY

echo "RealSteamOnMac uninstall completed"
echo "rollback=$SESSION_HOLD"
echo "report=$SESSION_HOLD/uninstall-report.txt"
