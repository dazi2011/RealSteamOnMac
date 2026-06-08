#!/bin/sh
set -eu

PROBE="probes/cancel_people_playground_install_experiment.js"

test -f "$PROBE"
grep -q 'const appid = 1118200;' "$PROBE"
grep -q 'before.currentAppID !== appid' "$PROBE"
grep -q 'SteamClient.Installs.CancelInstall()' "$PROBE"

if grep -Eq 'ContinueInstall|RunGame|ResumeInstall' "$PROBE"; then
  echo "cancel probe contains a forbidden action" >&2
  exit 1
fi

echo "cancel probe guard checks passed"
