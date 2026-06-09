#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
PAGE_PROBE="$ROOT/probes/verify_people_playground_compatibility_page.js"
STATE_PROBE="$ROOT/probes/verify_people_playground_compatibility_state.js"

test -f "$PAGE_PROBE"
test -f "$STATE_PROBE"
grep -q 'const appid = 1118200;' "$PAGE_PROBE"
grep -q 'RealSteamOnMac - DXMT 0.80' "$PAGE_PROBE"
grep -q 'input\[data-control\]' "$PAGE_PROBE"
grep -q 'realsteamonmac-controls' "$PAGE_PROBE"
grep -q 'role=combobox' "$PAGE_PROBE"
grep -q 'const appid = 1118200;' "$STATE_PROBE"
grep -q 'GetAvailableCompatTools(appid)' "$STATE_PROBE"
grep -q '__REALSTEAMONMAC_COMPAT_SELECTIONS_V1__' "$STATE_PROBE"
grep -q '__REALSTEAMONMAC_CONTROL_CONFIGS_V1__' "$STATE_PROBE"
grep -q 'realsteamonmac-wined3d' "$STATE_PROBE"
grep -q 'nCompatToolPriority' "$STATE_PROBE"

if grep -Eq \
    'SpecifyCompatTool|\.click\(|ContinueInstall|RunGame|OpenInstallWizard' \
    "$PAGE_PROBE" "$STATE_PROBE"; then
    echo "compatibility page verification probes must remain read-only" >&2
    exit 1
fi

echo "compatibility page probe contract: PASS"
