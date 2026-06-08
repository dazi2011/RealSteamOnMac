#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
PROBE="$ROOT/probes/open_people_playground_install_wizard_experiment.js"

test -f "$PROBE"
grep -q 'const appid = 1118200;' "$PROBE"
grep -q 'OpenInstallWizard(\[appid\])' "$PROBE"
grep -q 'GetInstallManagerInfo()' "$PROBE"

if grep -Eq 'ContinueInstall|RunGame|ResumeAppUpdate' "$PROBE"; then
    echo "install wizard probe must not start an install, download, or game" >&2
    exit 1
fi

echo "People Playground install wizard safety contract: PASS"
