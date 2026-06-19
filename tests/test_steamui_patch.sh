#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
PATCHER="$ROOT/script/patch_steamui.py"
UI_SOURCE="$ROOT/ui/realsteamonmac_ui.js"
TMP_ROOT=$(mktemp -d)
trap 'rm -rf "$TMP_ROOT"' EXIT
export REALSTEAMONMAC_ALLOW_TEST_FIXTURES=1

test -x "$PATCHER"
test -f "$UI_SOURCE"

STEAMUI="$TMP_ROOT/steamui"
mkdir -p "$STEAMUI"
printf '%s' \
    '<!doctype html><html style="width: 100%; height: 100%"><head><title>SharedJSContext</title><meta charset="utf-8"><script defer="defer" src="/libraries/libraries~00299a408.js"></script><script defer="defer" src="/library.js"></script><link href="/css/library.css" rel="stylesheet"></head><body style="width: 100%; height: 100%; margin: 0; overflow: hidden;"><div id="root" style="height:100%; width: 100%"></div><div style="display:none"></div></body></html>' \
    >"$STEAMUI/index.html"
printf '%s' \
    'before(0,f.CI)()&&o.push({title:(0,A.we)("#AppProperties_CompatibilityPage")middle(0,f.CI)()&&o.push({title:(0,A.we)("#AppProperties_CompatibilityPage")controlsr=(0,s.q3)(()=>u.rV.settings.bCompatEnabled),a=vt(t.unAppID,r),o=r&&!!t.strCompatToolName&&t.nCompatToolPriority==h.JNdropdownselectedOption:t.strCompatToolName,onChange:native(0,i.jsx)(wt,{...e})]})});function vtpickercase"macos":return[{strFileTypeName:(0,a.we)("#AddNonSteam_Filter_Exe_MacOS"),rFilePatterns:["*.app"],bUseAsDefault:!0}after' \
    >"$STEAMUI/chunk~2dcc5aaf7.js"
printf '%s\n' 1118200 >"$TMP_ROOT/allowlist.txt"
printf '%s\n' 0123456789abcdef0123456789abcdef \
    >"$TMP_ROOT/registry-token"
mkdir -p "$TMP_ROOT/dependencies"
cp "$ROOT/config/dependencies.json" \
    "$TMP_ROOT/dependencies/catalog.json"
mkdir -p "$TMP_ROOT/compatibilitytools.d"
cp -R "$ROOT/compat-tool/"* "$TMP_ROOT/compatibilitytools.d/"

"$PATCHER" install \
    --steamui-root "$STEAMUI" \
    --ui-source "$UI_SOURCE" \
    --allowlist "$TMP_ROOT/allowlist.txt" \
    --dependencies "$TMP_ROOT/dependencies/catalog.json" \
    --compat-tools-root "$TMP_ROOT/compatibilitytools.d"
"$PATCHER" install \
    --steamui-root "$STEAMUI" \
    --ui-source "$UI_SOURCE" \
    --allowlist "$TMP_ROOT/allowlist.txt" \
    --dependencies "$TMP_ROOT/dependencies/catalog.json" \
    --compat-tools-root "$TMP_ROOT/compatibilitytools.d"
"$PATCHER" verify --steamui-root "$STEAMUI"

test "$(grep -o '/realsteamonmac/config.js' "$STEAMUI/index.html" | wc -l)" -eq 1
test "$(grep -o '/realsteamonmac/ui.js' "$STEAMUI/index.html" | wc -l)" -eq 1
grep -q '"appids":\[1118200\]' "$STEAMUI/realsteamonmac/config.js"
grep -q '"registryToken":"0123456789abcdef0123456789abcdef"' \
    "$STEAMUI/realsteamonmac/config.js"
grep -q '"defaultCompatTool":"realsteamonmac-dxmt"' \
    "$STEAMUI/realsteamonmac/config.js"
grep -q '"actionEndpoint":"http://127.0.0.1:57344/action"' \
    "$STEAMUI/realsteamonmac/config.js"
grep -q '"jobEndpoint":"http://127.0.0.1:57344/job"' \
    "$STEAMUI/realsteamonmac/config.js"
grep -q '"id":"vcrun2022"' \
    "$STEAMUI/realsteamonmac/config.js"
test "$(grep -o '\"renderer\":\"' \
    "$STEAMUI/realsteamonmac/config.js" | wc -l)" -eq 4
test "$(stat -f '%Lp' "$STEAMUI/realsteamonmac/config.js")" = "600"
test "$(grep -o '__REALSTEAMONMAC_IS_MANAGED_APP__' \
    "$STEAMUI/chunk~2dcc5aaf7.js" | wc -l)" -eq 3
grep -q 'bCompatEnabled)||globalThis.__REALSTEAMONMAC_IS_MANAGED_APP__?.(t.unAppID)' \
    "$STEAMUI/chunk~2dcc5aaf7.js"
test "$(grep -o '__REALSTEAMONMAC_SELECTED_COMPAT_TOOL__' \
    "$STEAMUI/chunk~2dcc5aaf7.js" | wc -l)" -eq 2
test "$(grep -o '__REALSTEAMONMAC_RENDER_NATIVE_COMPAT_CONTROLS__' \
    "$STEAMUI/chunk~2dcc5aaf7.js" | wc -l)" -eq 1

"$PATCHER" restore --steamui-root "$STEAMUI"
test ! -e "$STEAMUI/index.html.realsteamonmac.original"
test ! -e \
    "$STEAMUI/chunk~2dcc5aaf7.js.realsteamonmac.original"
test ! -e "$STEAMUI/realsteamonmac"
test "$(shasum -a 256 "$STEAMUI/index.html" | awk '{print $1}')" = \
    "55ced284314dbc65bff38fb1333d4f4bd617635895e2c0e2197b05028c243282"
test "$(shasum -a 256 "$STEAMUI/chunk~2dcc5aaf7.js" | awk '{print $1}')" = \
    "143e81017bebc619bc94cf7f7bab2d6945541c07c21df966d2aca24377b63b35"

echo "Steam UI resource patch contract: PASS"
