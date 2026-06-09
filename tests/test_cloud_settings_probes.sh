#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
STATE_PROBE="$ROOT/probes/cloud_settings_state_readonly.js"
PAGE_PROBE="$ROOT/probes/cloud_settings_page_readonly.js"

test -f "$STATE_PROBE"
test -f "$PAGE_PROBE"

grep -q 'const cloudSetting = "cloud_enabled";' "$STATE_PROBE"
grep -q 'const screenshotSetting = "show_screenshot_manager";' "$STATE_PROBE"
grep -q 'webpackRequire(29788)' "$STATE_PROBE"
grep -q 'webpackRequire(33867)' "$STATE_PROBE"
grep -q 'm_ClientSettings' "$STATE_PROBE"
grep -q 'CloudStorage' "$STATE_PROBE"

grep -q 'DialogContent_InnerWidth' "$PAGE_PROBE"
grep -q 'DialogBody' "$PAGE_PROBE"
grep -q 'document.body' "$PAGE_PROBE"

for forbidden in \
  SetSetting \
  Delete \
  Upload \
  Download \
  Resolve \
  '.click(' \
  dispatchEvent \
  'localStorage.setItem'
do
  if grep -Fq "$forbidden" "$STATE_PROBE" "$PAGE_PROBE"; then
    echo "cloud settings probes must remain read-only" >&2
    exit 1
  fi
done

echo "cloud settings probe contract: PASS"
