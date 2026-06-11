#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
PROBE="$ROOT/probes/launch_options_readonly.js"

test -f "$PROBE"
grep -q 'GetLaunchOptionsForApp(appid)' "$PROBE"
grep -q 'JSON.stringify(option)' "$PROBE"
grep -q 'Object.getOwnPropertyNames(option)' "$PROBE"

if grep -Eq \
    'RunGame|PerformAppAction|OpenInstallWizard|ResumeAppUpdate|VerifyApp' \
    "$PROBE"; then
  echo "launch-options probe must remain read-only" >&2
  exit 1
fi

echo "launch options read-only probe: PASS"
