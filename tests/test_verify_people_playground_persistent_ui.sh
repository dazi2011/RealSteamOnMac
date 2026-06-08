#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
PROBE="$ROOT/probes/verify_people_playground_persistent_ui.js"
EXERCISE="$ROOT/probes/exercise_people_playground_store_reconciliation.js"
CLICK="$ROOT/probes/click_people_playground_native_install_button_experiment.js"

test -f "$PROBE"
test -f "$EXERCISE"
test -f "$CLICK"
grep -q 'const appid = 1118200;' "$PROBE"
grep -q '__REALSTEAMONMAC_UI_STATUS__' "$PROBE"
grep -q 'selected.display_status' "$PROBE"
grep -q 'details.eDisplayStatus' "$PROBE"
grep -q 'backgroundImage' "$PROBE"
grep -q 'pointerEvents' "$PROBE"
grep -q 'const appid = 1118200;' "$CLICK"
grep -q 'candidates.length !== 1' "$CLICK"
grep -q 'backgroundImage.includes("linear-gradient")' "$CLICK"
grep -q 'candidates\[0\].click()' "$CLICK"

if grep -Eq \
    'ContinueInstall|OpenInstallWizard|RunGame|ResumeAppUpdate|SpecifyCompatTool' \
    "$PROBE" "$EXERCISE" "$CLICK"; then
    echo "persistent UI verification must remain read-only" >&2
    exit 1
fi

echo "persistent People Playground UI probe contract: PASS"
