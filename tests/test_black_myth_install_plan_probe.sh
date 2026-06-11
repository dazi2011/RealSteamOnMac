#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PROBE="$ROOT/probes/inspect_black_myth_install_plan_experiment.js"

node --check "$PROBE"
grep -q 'const appid = 2358720;' "$PROBE"
grep -q 'OpenInstallWizard(\[appid\])' "$PROBE"
grep -q 'GetInstallManagerInfo()' "$PROBE"
grep -q 'CancelInstall()' "$PROBE"

if grep -Eq 'ContinueInstall|RunGame|ResumeAppUpdate' "$PROBE"; then
  printf '%s\n' "install-plan probe must not start a download or game" >&2
  exit 1
fi
