#!/bin/sh
set -eu

PROBE="probes/refresh_people_playground_compat_mapping.js"

test -f "$PROBE"
grep -q 'const appid = 1118200;' "$PROBE"
grep -q 'SpecifyCompatTool(appid, "")' "$PROBE"
grep -q 'SpecifyCompatTool(appid, toolName)' "$PROBE"

if grep -Eq 'OpenInstallWizard|ContinueInstall|RunGame|ResumeInstall' "$PROBE"; then
  echo "compat refresh probe contains a forbidden action" >&2
  exit 1
fi

echo "compat refresh probe guard checks passed"
