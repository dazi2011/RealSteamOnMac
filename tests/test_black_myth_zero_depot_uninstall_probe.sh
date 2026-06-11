#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PROBE="$ROOT/probes/uninstall_black_myth_zero_depot_experiment.js"

node --check "$PROBE"
grep -q 'const appid = 2358720;' "$PROBE"
grep -q 'String(overview.size_on_disk) !== "0"' "$PROBE"
grep -q 'localClient?.installed' "$PROBE"
grep -q 'GetInstallManagerInfo()' "$PROBE"
grep -q 'GetGameActionForApp(appid)' "$PROBE"
grep -q 'OpenUninstallWizard(\[appid\], true)' "$PROBE"

if grep -Eq \
  'ContinueInstall|OpenInstallWizard|ResumeAppUpdate|RunGame|VerifyApp' \
  "$PROBE"; then
  printf '%s\n' "zero-depot probe must only uninstall" >&2
  exit 1
fi
