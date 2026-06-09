#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

LOG="$TMP/calls.log"
STEAM_APP="$TMP/Steam.app"
RUNTIME_APP="$TMP/SteamRuntime.app"
BACKUP="$TMP/backup"
SUPPORT="$TMP/support"
RUNTIME_ROOT="$SUPPORT/runtimes"
CACHE="$TMP/cache"
GPTK="$TMP/GPTK.dmg"

mkdir -p \
    "$STEAM_APP" \
    "$RUNTIME_APP/Contents/MacOS" \
    "$BACKUP" \
    "$TMP/bin"
: >"$RUNTIME_APP/Contents/MacOS/steam_osx"
: >"$GPTK"

make_recorder() {
    name=$1
    path="$TMP/bin/$name"
    sed \
        -e "s|@NAME@|$name|g" \
        -e "s|@LOG@|$LOG|g" \
        "$TMP/recorder.in" >"$path"
    chmod +x "$path"
}

cat >"$TMP/recorder.in" <<'EOF'
#!/bin/sh
printf '%s' '@NAME@' >>'@LOG@'
for argument in "$@"; do
    printf '\t%s' "$argument" >>'@LOG@'
done
printf '\n' >>'@LOG@'
if [ '@NAME@' = bridge ]; then
    while [ "$#" -gt 0 ]; do
        if [ "$1" = --output ]; then
            mkdir -p "$2/x86_64-windows" "$2/x86_64-unix"
            : >"$2/x86_64-windows/lsteamclient.dll"
            : >"$2/x86_64-unix/lsteamclient.so"
            break
        fi
        shift
    done
fi
EOF

for name in hook launcher bridge runtime injection; do
    make_recorder "$name"
done

env \
    REALSTEAMONMAC_HOOK_BUILDER="$TMP/bin/hook" \
    REALSTEAMONMAC_LAUNCHER_BUILDER="$TMP/bin/launcher" \
    REALSTEAMONMAC_BRIDGE_BUILDER="$TMP/bin/bridge" \
    REALSTEAMONMAC_RUNTIME_INSTALLER="$TMP/bin/runtime" \
    REALSTEAMONMAC_INJECTION_INSTALLER="$TMP/bin/injection" \
    "$ROOT/script/install_realsteamonmac.sh" \
        --clean-backup "$BACKUP" \
        --gptk-dmg "$GPTK" \
        --steam-app "$STEAM_APP" \
        --runtime-app "$RUNTIME_APP" \
        --support-root "$SUPPORT" \
        --runtime-root "$RUNTIME_ROOT" \
        --cache-dir "$CACHE"

test "$(cut -f1 "$LOG" | tr '\n' ' ')" = \
    "hook launcher bridge runtime injection "
grep -Fq "bridge	--output	$SUPPORT/build/lsteamclient-proton11b5-macos2" "$LOG"
grep -Fq "runtime	--gptk-dmg	$GPTK" "$LOG"
runtime_call=$(grep '^runtime	' "$LOG")
printf '%s\n' "$runtime_call" |
    grep -Fq "	--steamworks-bridge	$SUPPORT/build/lsteamclient-proton11b5-macos2"
printf '%s\n' "$runtime_call" |
    grep -Fq "	--runtime-root	$RUNTIME_ROOT"
grep -Fq "injection	--clean-backup	$BACKUP" "$LOG"
injection_call=$(grep '^injection	' "$LOG")
printf '%s\n' "$injection_call" |
    grep -Fq "	--steam-app	$STEAM_APP"

echo "one-click installer contract: PASS"
