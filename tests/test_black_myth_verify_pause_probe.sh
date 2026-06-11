#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PROBE="$ROOT/probes/verify_black_myth_and_pause_experiment.js"

node --check "$PROBE"
grep -q 'const appid = 2358720;' "$PROBE"
grep -q 'SteamClient.Apps.VerifyApp(appid)' "$PROBE"
grep -q 'SteamClient.Apps.GetActiveGameActions()' "$PROBE"
grep -q 'SteamClient.Downloads.PauseAppUpdate' "$PROBE"

if grep -Eq 'ContinueInstall|ResumeAppUpdate|RunGame|Uninstall' "$PROBE"; then
  printf '%s\n' "verify probe must pause without installing or uninstalling" >&2
  exit 1
fi
