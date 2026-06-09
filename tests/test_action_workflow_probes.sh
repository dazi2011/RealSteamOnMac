#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
VERIFY="$ROOT/probes/verify_people_playground_action_panel.js"
RUN="$ROOT/probes/run_people_playground_registry_query_experiment.js"
INSTALL="$ROOT/probes/install_people_playground_vcrun2022_experiment.js"
FOCUS="$ROOT/probes/focus_people_playground_action_status_readonly.js"

for probe in "$VERIFY" "$RUN" "$INSTALL" "$FOCUS"; do
    grep -q 'const appid = 1118200;' "$probe"
    grep -q 'Number(panel.*dataset.appid) !== appid' "$probe"
done

if grep -Fq '.click(' "$VERIFY" || grep -Fq 'fetch(' "$VERIFY"; then
    echo "action panel verification probe must remain read-only" >&2
    exit 1
fi

if grep -Fq '.click(' "$FOCUS" || grep -Fq 'fetch(' "$FOCUS"; then
    echo "action status focus probe must remain read-only" >&2
    exit 1
fi
grep -q 'scrollIntoView' "$FOCUS"

test "$(grep -c 'button.click();' "$RUN")" -eq 1
grep -q 'refusing mismatched action panel AppID' "$RUN"
grep -q 'C:\\windows\\system32\\reg.exe' "$RUN"

test "$(grep -c 'button.click();' "$INSTALL")" -eq 1
grep -q 'const dependency = "vcrun2022";' "$INSTALL"
grep -q 'refusing mismatched action panel AppID' "$INSTALL"

echo "action workflow probe contract: PASS"
