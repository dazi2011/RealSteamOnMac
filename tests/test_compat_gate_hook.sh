#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
SOURCE="$ROOT/hook/compat_gate_hook.c"
BUILD_SCRIPT="$ROOT/script/build_compat_gate_hook.sh"
OUTPUT="$ROOT/artifacts/compat-gate-hook/libRealSteamCompatGate.dylib"

test -f "$SOURCE"
test -x "$BUILD_SCRIPT"

grep -q 'REALSTEAMONMAC_FORCE_COMPAT' "$SOURCE"
grep -q '0x00A012D0' "$SOURCE"
grep -q '0x005EAC3C' "$SOURCE"
grep -q '0xB9401C00' "$SOURCE"
grep -q '0xD101C3FF' "$SOURCE"
grep -q '0xA9054FF4' "$SOURCE"
grep -q 'REALSTEAMONMAC_APPIDS' "$SOURCE"
grep -q 'allowlist.txt' "$SOURCE"
grep -q 'PLATFORM_INVALID_BIT' "$SOURCE"
grep -q 'realsteamonmac_platform_flags' "$SOURCE"
grep -q 'unsetenv("DYLD_INSERT_LIBRARIES")' "$SOURCE"
grep -q 'realsteamonmac_apply_data_overrides' "$SOURCE"
grep -q 'is_steam_runtime_process' "$SOURCE"
grep -q 'is_steam_bootstrap_process' "$SOURCE"
grep -q 'clear_injection_environment' "$SOURCE"
grep -q 'pthread_create' "$SOURCE"
grep -q 'data_override_worker' "$SOURCE"
if grep -Eq 'DATA_OVERRIDE_ATTEMPTS|DATA_OVERRIDE_RECONCILE_DELAY_US' "$SOURCE"; then
    echo "native reconciliation must use tracked objects, not repeated full scans" >&2
    exit 1
fi
grep -q 'TRACKED_OBJECT_REFRESH_DELAY_US' "$SOURCE"
grep -q 'FULL_RESCAN_INTERVAL_TICKS' "$SOURCE"
grep -q 'track_object' "$SOURCE"
grep -q 'refresh_tracked_objects' "$SOURCE"
grep -q 'while (is_steam_runtime_process())' "$SOURCE"
grep -q 'environment_cleared' "$SOURCE"
grep -q 'data override: initial reconciliation completed' "$SOURCE"
grep -q 'data override: reconciliation worker stopped' "$SOURCE"
grep -q 'mach_vm_region' "$SOURCE"
grep -q 'vtable + 0x68' "$SOURCE"
grep -q 'mach_vm_protect' "$SOURCE"
grep -q 'VM_PROT_COPY' "$SOURCE"
grep -q 'steam_osx' "$SOURCE"

"$BUILD_SCRIPT"

test -f "$OUTPUT"
file "$OUTPUT" | grep -q 'arm64'
file "$OUTPUT" | grep -q 'arm64e'
file "$OUTPUT" | grep -q 'x86_64'
codesign --verify --strict "$OUTPUT"

echo "compat gate hook contract: PASS"
