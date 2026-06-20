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
grep -q '0x00A00874' "$SOURCE"
grep -q '0x00A03DA4' "$SOURCE"
grep -q '0x00A03EF8' "$SOURCE"
grep -q '0x005EAC3C' "$SOURCE"
grep -q '0x005EAC24' "$SOURCE"
grep -q '0x005EDF44' "$SOURCE"
grep -q '1780705203' "$SOURCE"
grep -q '1780965181' "$SOURCE"
grep -q '1781212412' "$SOURCE"
grep -q 'steamclient_profile_for_header' "$SOURCE"
grep -q 'find_steamui_image' "$SOURCE"
grep -q '0xD101C3FF' "$SOURCE"
grep -q '0xA9054FF4' "$SOURCE"
grep -q 'REALSTEAMONMAC_APPIDS' "$SOURCE"
grep -q 'allowlist.txt' "$SOURCE"
grep -q 'managed-appids-cache.txt' "$SOURCE"
grep -q 'managed-registry-v1.txt' "$SOURCE"
grep -q 'PLATFORM_INVALID_BIT' "$SOURCE"
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
grep -q 'install_gate_offset' "$SOURCE"
grep -q 'install_gate_fallthrough_offset' "$SOURCE"
grep -q 'install_gate_invalid_offset' "$SOURCE"
grep -q '0x0062505C' "$SOURCE"
grep -q '0x00625060' "$SOURCE"
grep -q '0x0062508C' "$SOURCE"
grep -q '0x00624600' "$SOURCE"
grep -q '0x00624604' "$SOURCE"
grep -q '0x00624630' "$SOURCE"
grep -q '0x00627884' "$SOURCE"
grep -q '0x00627888' "$SOURCE"
grep -q '0x006278B4' "$SOURCE"
grep -q '0x006279D8' "$SOURCE"
grep -q '0x006279DC' "$SOURCE"
grep -q '0x00627A08' "$SOURCE"
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
grep -q 'distance += page_size' "$SOURCE"
grep -q 'gAllowlistGeneration' "$SOURCE"
grep -q 'finish_install_gate_update' "$SOURCE"
grep -q 'memory_order_release' "$SOURCE"
grep -q 'RSMREG\\t1\\n' "$SOURCE"
grep -q 'managed_registry' "$SOURCE"
grep -q 'persist_managed_registry' "$SOURCE"
grep -q 'shortcut-binding-%u.txt' "$SOURCE"
grep -q 'O_NOFOLLOW' "$SOURCE"
grep -q 'fsync(directory)' "$SOURCE"

# The launch bridge replaces only the resolved steamclient posix_spawn pointer.
# It redirects verified PE targets plus recoverable missing/.app launch targets
# only for allowlisted Windows apps. Native executables and unmanaged AppIDs
# keep the original system implementation.
grep -q 'STEAMCLIENT_POSIX_SPAWN_POINTER_OFFSET' "$SOURCE"
grep -q 'STEAMCLIENT_POSIX_SPAWN_POINTER_OFFSET_REFRESH' "$SOURCE"
grep -q '0x018FD500' "$SOURCE"
grep -q 'realsteamonmac_should_redirect_spawn' "$SOURCE"
grep -q 'patch_steamclient_spawn_redirect' "$SOURCE"
grep -q 'gOriginalPosixSpawn' "$SOURCE"
grep -q 'lookup_managed_shortcut' "$SOURCE"
grep -q 'shortcut_file_identity_matches' "$SOURCE"
grep -q 'is_store_managed(appid)' "$SOURCE"
grep -q 'build_redirect_environment' "$SOURCE"
grep -q 'validate_runtime_script' "$SOURCE"
grep -q 'is_pe_executable(path)' "$SOURCE"
grep -q 'is_missing_launch_target(path)' "$SOURCE"
grep -q 'has_app_suffix(path)' "$SOURCE"
grep -q -- '--shortcut-id' "$SOURCE"
grep -q 'patch_steamclient_spawn_redirect(steamclient)' "$SOURCE"

# Keep SteamUI's getter intact. The native engine uses its vtable address only
# to identify real app objects before applying allowlist-scoped data changes.
if grep -q 'build_platform_filter_trampoline' "$SOURCE" ||
    grep -Fq 'patch_steamui(' "$SOURCE"; then
    echo "native engine must not globally redirect the SteamUI platform getter" >&2
    exit 1
fi

"$BUILD_SCRIPT"

test -f "$OUTPUT"
test -f "$GUARD"
file "$OUTPUT" | grep -q 'arm64'
file "$OUTPUT" | grep -q 'arm64e'
file "$OUTPUT" | grep -q 'x86_64'
codesign --verify --strict "$OUTPUT"
codesign --verify --strict "$GUARD"

echo "compat gate hook contract: PASS"
