#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
PAGE_PROBE="$ROOT/probes/verify_people_playground_compatibility_page.js"
STATE_PROBE="$ROOT/probes/verify_people_playground_compatibility_state.js"

test -f "$PAGE_PROBE"
test -f "$STATE_PROBE"
grep -q 'const appid = 1118200;' "$PAGE_PROBE"
grep -q '强制使用特定 Steam Play 兼容性工具' "$PAGE_PROBE"
grep -q '兼容性选项' "$PAGE_PROBE"
grep -q '安装 Windows 组件' "$PAGE_PROBE"
grep -q '容器操作' "$PAGE_PROBE"
grep -q '运行命令' "$PAGE_PROBE"
grep -q '最近操作状态' "$PAGE_PROBE"
grep -q 'nativeControlSectionOrder' "$PAGE_PROBE"
grep -q 'role=combobox' "$PAGE_PROBE"
grep -q 'DialogDropDown' "$PAGE_PROBE"
grep -q 'realsteamonmac-controls' "$PAGE_PROBE"
grep -q 'realsteamonmac-modal-layer' "$PAGE_PROBE"
grep -q 'const appid = 1118200;' "$STATE_PROBE"
grep -q 'GetAvailableCompatTools(appid)' "$STATE_PROBE"
grep -q 'realsteamonmac-wined3d' "$STATE_PROBE"
grep -q 'physx-legacy' "$STATE_PROBE"
grep -q 'props?.rgOptions' "$STATE_PROBE"
grep -q 'nCompatToolPriority' "$STATE_PROBE"
grep -q 'DialogDropDown' "$STATE_PROBE"

if grep -Eq \
    'SpecifyCompatTool|\.click\(|ContinueInstall|RunGame|OpenInstallWizard' \
    "$PAGE_PROBE" "$STATE_PROBE"; then
    echo "compatibility page verification probes must remain read-only" >&2
    exit 1
fi

echo "Steam-native compatibility page probe contract: PASS"
