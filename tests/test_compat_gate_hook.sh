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

# GetAppForInstallation platform gate (the install-time counterpart to the data
# overrides): the single conditional veto at 0x62505c is overwritten with a NOP
# so EVERY owned Windows-only title — not just an allowlist — reaches the real
# depot download path instead of failing with error 29 ("Invalid platform").
# Removing the allowlist from this gate is what makes new purchases installable
# without a Steam restart.
grep -q 'STEAMCLIENT_INSTALL_GATE_OFFSET' "$SOURCE"
grep -q '0x0062505C' "$SOURCE"
grep -q '0x37200188' "$SOURCE"
grep -q '0xD503201F' "$SOURCE"
grep -q 'kSteamClientInstallGateNop' "$SOURCE"
grep -q 'patch_steamclient_install_gate' "$SOURCE"
grep -q 'gSteamClientInstallGatePatched' "$SOURCE"
grep -q 'steamclient: install gate cleared' "$SOURCE"
# The allowlist-gated trampoline is gone: the gate must be neutralized
# unconditionally, never rebuilt per-AppID.
if grep -q 'build_install_gate_trampoline' "$SOURCE"; then
    echo "install gate must be a NOP, not a per-AppID trampoline" >&2
    exit 1
fi
# The data scan must target Windows-only overviews structurally (InvalidPlatform
# bit + confirmed CAppOverview vtable), not an allowlist, so every Windows-only
# title in the library is covered and hot-update needs no restart.
grep -q 'APPID_PLAUSIBLE_MAX' "$SOURCE"
grep -q 'vtable_is_overview' "$SOURCE"
grep -q 'remember_overview_vtable' "$SOURCE"
# The gate patch must be driven by the proven-active data override worker, not
# only the (currently dormant) dyld image-added callback. The worker calls it
# with an explicit zero slide (resolved image), unlike the image_added path.
grep -q 'patch_steamclient_install_gate(steamclient, 0)' "$SOURCE"
grep -q 'patch_steamclient_install_gate(header, slide)' "$SOURCE"

"$BUILD_SCRIPT"

test -f "$OUTPUT"
file "$OUTPUT" | grep -q 'arm64'
file "$OUTPUT" | grep -q 'arm64e'
file "$OUTPUT" | grep -q 'x86_64'
codesign --verify --strict "$OUTPUT"

echo "compat gate hook contract: PASS"
