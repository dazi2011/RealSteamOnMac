#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
SOURCE="$ROOT/hook/compat_gate_hook.c"
BUILD_SCRIPT="$ROOT/script/build_compat_gate_hook.sh"
GUARD="$ROOT/artifacts/compat-gate-hook/libRealSteamCompatGate.dylib"
OUTPUT="$ROOT/artifacts/compat-gate-hook/libRealSteamNativeEngine.dylib"

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
grep -q 'clear_injection_environment' "$SOURCE"
grep -q 'realsteamonmac_start_native_worker' "$SOURCE"
grep -q 'pthread_create' "$SOURCE"
grep -q 'data_override_worker' "$SOURCE"
if grep -q '__attribute__((constructor))' "$SOURCE"; then
    echo "native engine must be loaded explicitly after Steam initialization" >&2
    exit 1
fi
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

# GetAppForInstallation platform gate redirect (the install-time counterpart to
# the data overrides): allowlist-gated trampoline at 0x62505c that lets an
# allowlisted Install click reach the real depot download path instead of
# failing with error 29 ("Invalid platform").
grep -q 'STEAMCLIENT_INSTALL_GATE_OFFSET' "$SOURCE"
grep -q '0x0062505C' "$SOURCE"
grep -q '0x00625060' "$SOURCE"
grep -q '0x0062508C' "$SOURCE"
grep -q '0x37200188' "$SOURCE"
grep -q '0x6B0A02BF' "$SOURCE"
grep -q 'build_install_gate_trampoline' "$SOURCE"
grep -q 'patch_steamclient_install_gate' "$SOURCE"
grep -q 'gSteamClientInstallGatePatched' "$SOURCE"
grep -q 'steamclient: install gate patched' "$SOURCE"
# The gate redirect must be driven by the proven-active data override worker,
# not only the (currently dormant) dyld image-added callback. The worker calls
# it with an explicit zero slide (resolved image), unlike the image_added path.
grep -q 'patch_steamclient_install_gate(steamclient, 0)' "$SOURCE"
grep -q 'patch_steamclient_install_gate(header, slide)' "$SOURCE"

# The browser registry is authenticated, loopback-only, bounded, and can
# request a live install-gate rebuild without broadening the initial allowlist.
grep -q 'realsteamonmac_start_registry_server' "$SOURCE"
grep -q 'realsteamonmac_is_managed_app' "$SOURCE"
grep -q 'INADDR_LOOPBACK' "$SOURCE"
grep -q 'registry-token' "$SOURCE"
grep -q 'REGISTRY_REQUEST_CAPACITY' "$SOURCE"
grep -q 'gInstallGateRefreshRequested' "$SOURCE"
grep -q 'gAllowlistGeneration' "$SOURCE"
grep -q 'finish_install_gate_update' "$SOURCE"
grep -q 'memory_order_release' "$SOURCE"
grep -q 'registry: accepted %zu managed AppID(s)' "$SOURCE"

"$BUILD_SCRIPT"

test -f "$OUTPUT"
test -f "$GUARD"
file "$OUTPUT" | grep -q 'arm64'
file "$OUTPUT" | grep -q 'arm64e'
file "$OUTPUT" | grep -q 'x86_64'
codesign --verify --strict "$OUTPUT"
codesign --verify --strict "$GUARD"

echo "compat gate hook contract: PASS"
