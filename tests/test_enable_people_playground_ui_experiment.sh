#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
PROBE="$ROOT/probes/enable_people_playground_ui_experiment.js"
RESTORE="$ROOT/probes/restore_people_playground_ui_experiment.js"

test -f "$PROBE"
test -f "$RESTORE"

grep -q 'const appid = 1118200;' "$PROBE"
grep -q 'const invalidPlatformStatus = 14;' "$PROBE"
grep -q 'const readyToInstallStatus = 9;' "$PROBE"
grep -q 'overview.appid !== appid' "$PROBE"
grep -q 'selected.display_status !== invalidPlatformStatus' "$PROBE"
grep -q '__realSteamOnMacPeoplePlaygroundUIExperiment' "$PROBE"
grep -q '__realSteamOnMacPeoplePlaygroundUIExperiment' "$RESTORE"

if grep -Eq 'OpenInstallWizard|RunGame|ResumeAppUpdate' "$PROBE"; then
    echo "UI experiment must not start an install, download, or game" >&2
    exit 1
fi

echo "People Playground UI experiment safety contract: PASS"
