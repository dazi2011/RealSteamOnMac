#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
TMP_ROOT=$(mktemp -d)
trap 'rm -rf "$TMP_ROOT"' EXIT
export REALSTEAMONMAC_ALLOW_TEST_FIXTURES=1

"$ROOT/script/build_compat_gate_hook.sh" >/dev/null
"$ROOT/script/build_steam_launcher.sh" >/dev/null

STEAM_APP="$TMP_ROOT/Steam.app"
RUNTIME_APP="$TMP_ROOT/SteamRuntime.app"
BACKUP="$TMP_ROOT/backup"
SUPPORT="$TMP_ROOT/support"
COMPAT_TOOLS="$TMP_ROOT/compatibilitytools.d"
mkdir -p \
    "$STEAM_APP/Contents/MacOS" \
    "$RUNTIME_APP/Contents/MacOS/steamui" \
    "$COMPAT_TOOLS/user-custom-tool" \
    "$COMPAT_TOOLS/realsteamonmac-experimental"
printf 'preserve\n' >"$COMPAT_TOOLS/user-custom-tool/marker"
printf '%s\n' \
    '"compatibilitytools"' \
    '{' \
    '  "compat_tools"' \
    '  {' \
    '    "realsteamonmac-experimental"' \
    '    {' \
    '      "install_path" "."' \
    '    }' \
    '  }' \
    '}' >"$COMPAT_TOOLS/realsteamonmac-experimental/compatibilitytool.vdf"

write_info_plist() {
    destination=$1
    identifier=$2
    printf '%s\n' \
        '<?xml version="1.0" encoding="UTF-8"?>' \
        '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">' \
        '<plist version="1.0"><dict>' \
        "<key>CFBundleIdentifier</key><string>$identifier</string>" \
        '<key>CFBundleExecutable</key><string>steam_osx</string>' \
        '<key>CFBundlePackageType</key><string>APPL</string>' \
        '<key>LSEnvironment</key><dict><key>LC_ALL</key><string>en_US.UTF-8</string></dict>' \
        '</dict></plist>' >"$destination"
}

write_info_plist "$STEAM_APP/Contents/Info.plist" \
    "test.realsteamonmac.steam"
write_info_plist "$RUNTIME_APP/Contents/Info.plist" \
    "test.realsteamonmac.runtime"
cp /usr/bin/true "$STEAM_APP/Contents/MacOS/steam_osx"
cp /usr/bin/true "$RUNTIME_APP/Contents/MacOS/steam_osx"
printf '%s' \
    '<!doctype html><html style="width: 100%; height: 100%"><head><title>SharedJSContext</title><meta charset="utf-8"><script defer="defer" src="/libraries/libraries~00299a408.js"></script><script defer="defer" src="/library.js"></script><link href="/css/library.css" rel="stylesheet"></head><body style="width: 100%; height: 100%; margin: 0; overflow: hidden;"><div id="root" style="height:100%; width: 100%"></div><div style="display:none"></div></body></html>' \
    >"$RUNTIME_APP/Contents/MacOS/steamui/index.html"
printf '%s' \
    'before(0,f.CI)()&&o.push({title:(0,A.we)("#AppProperties_CompatibilityPage")middle(0,f.CI)()&&o.push({title:(0,A.we)("#AppProperties_CompatibilityPage")after' \
    >"$RUNTIME_APP/Contents/MacOS/steamui/chunk~2dcc5aaf7.js"
ln -s steam_osx "$STEAM_APP/Contents/MacOS/steam.sh"
codesign --force --deep --sign - "$STEAM_APP"
codesign --force --deep --sign - "$RUNTIME_APP"

mkdir -p "$BACKUP"
ditto "$STEAM_APP" "$BACKUP/Steam.app"
ditto "$RUNTIME_APP" "$BACKUP/SteamRuntime.app"

"$ROOT/script/install_steam_injection.sh" \
    --clean-backup "$BACKUP" \
    --steam-app "$STEAM_APP" \
    --runtime-app "$RUNTIME_APP" \
    --support-root "$SUPPORT" \
    --compat-tools-root "$COMPAT_TOOLS"

"$ROOT/script/install_steam_injection.sh" \
    --clean-backup "$BACKUP" \
    --steam-app "$STEAM_APP" \
    --runtime-app "$RUNTIME_APP" \
    --support-root "$SUPPORT" \
    --compat-tools-root "$COMPAT_TOOLS" >/dev/null

test -f "$SUPPORT/libRealSteamCompatGate.dylib"
test -f "$SUPPORT/libRealSteamNativeEngine.dylib"
grep -q 'REALSTEAMONMAC_DELAYED_ENGINE_PATH' \
    "$STEAM_APP/Contents/MacOS/realsteamonmac_launcher"
for tool in gptk dxmt dxvk wined3d; do
    test -x "$COMPAT_TOOLS/realsteamonmac-$tool/run"
    test -f "$COMPAT_TOOLS/realsteamonmac-$tool/realsteamonmac.json"
done
test -f "$COMPAT_TOOLS/user-custom-tool/marker"
test ! -e "$COMPAT_TOOLS/realsteamonmac-experimental"
test -f \
    "$SUPPORT/migrations/legacy-compat-tools/realsteamonmac-experimental/compatibilitytool.vdf"
test -f "$SUPPORT/compat_tool_catalog.py"
test -f "$SUPPORT/allowlist.txt"
test -f "$SUPPORT/registry-token"
test "$(stat -f '%Lp' "$SUPPORT/registry-token")" = "600"
test -f "$SUPPORT/dependencies/catalog.json"
test "$(stat -f '%Lp' "$SUPPORT/dependencies")" = "700"
test "$(stat -f '%Lp' "$SUPPORT/dependencies/catalog.json")" = "600"
cmp "$ROOT/config/dependencies.json" \
    "$SUPPORT/dependencies/catalog.json"
test -x "$SUPPORT/patch_steamui.py"
test -f "$SUPPORT/ui/realsteamonmac_ui.js"
test -f \
    "$RUNTIME_APP/Contents/MacOS/steamui/index.html.realsteamonmac.original"
test -f \
    "$RUNTIME_APP/Contents/MacOS/steamui/chunk~2dcc5aaf7.js.realsteamonmac.original"
grep -q '/realsteamonmac/config.js' \
    "$RUNTIME_APP/Contents/MacOS/steamui/index.html"
grep -q '/realsteamonmac/ui.js' \
    "$RUNTIME_APP/Contents/MacOS/steamui/index.html"
grep -q '"appids":\[1118200\]' \
    "$RUNTIME_APP/Contents/MacOS/steamui/realsteamonmac/config.js"
grep -q '"id":"vcrun2022"' \
    "$RUNTIME_APP/Contents/MacOS/steamui/realsteamonmac/config.js"
grep -q '"strDisplayName":"DXMT 0.80"' \
    "$RUNTIME_APP/Contents/MacOS/steamui/realsteamonmac/config.js"
test "$(grep -o '__REALSTEAMONMAC_IS_MANAGED_APP__' \
    "$RUNTIME_APP/Contents/MacOS/steamui/chunk~2dcc5aaf7.js" |
    wc -l)" -eq 2
test -x "$STEAM_APP/Contents/MacOS/realsteamonmac_launcher"
test -x "$STEAM_APP/Contents/MacOS/steam_osx.original"
test ! -e "$STEAM_APP/Contents/MacOS/steam_osx"
test "$(readlink "$STEAM_APP/Contents/MacOS/steam.sh")" = \
    "realsteamonmac_launcher"
test "$(/usr/libexec/PlistBuddy -c \
    'Print :CFBundleExecutable' \
    "$STEAM_APP/Contents/Info.plist")" = "realsteamonmac_launcher"
test "$(/usr/libexec/PlistBuddy -c \
    'Print :LSEnvironment:LC_ALL' \
    "$STEAM_APP/Contents/Info.plist")" = "en_US.UTF-8"
if /usr/libexec/PlistBuddy -c \
    'Print :LSEnvironment:DYLD_INSERT_LIBRARIES' \
    "$STEAM_APP/Contents/Info.plist" >/dev/null 2>&1; then
    exit 1
fi
codesign --verify --deep --strict "$STEAM_APP"
codesign -d --entitlements :- \
    "$RUNTIME_APP/Contents/MacOS/steam_osx" 2>/dev/null |
    grep -q 'com.apple.security.cs.disable-library-validation'

OPEN_PACKAGE="open-runtime-test"
mkdir -p "$SUPPORT/runtimes/packages/$OPEN_PACKAGE"
printf '%s\n' \
    '{"schema":1,"package_id":"open-runtime-test","renderers":{"dxmt":{},"dxvk":{},"wined3d":{}}}' \
    >"$SUPPORT/runtimes/packages/$OPEN_PACKAGE/manifest.json"
ln -sfn "packages/$OPEN_PACKAGE" "$SUPPORT/runtimes/current"

"$ROOT/script/install_steam_injection.sh" \
    --clean-backup "$BACKUP" \
    --steam-app "$STEAM_APP" \
    --runtime-app "$RUNTIME_APP" \
    --support-root "$SUPPORT" \
    --compat-tools-root "$COMPAT_TOOLS" >/dev/null

test ! -e "$COMPAT_TOOLS/realsteamonmac-gptk"
for tool in dxmt dxvk wined3d; do
    grep -q '"runtime_package": "open-runtime-test"' \
        "$COMPAT_TOOLS/realsteamonmac-$tool/realsteamonmac.json"
done
test -f "$COMPAT_TOOLS/user-custom-tool/marker"
if grep -q '"strToolName":"realsteamonmac-gptk"' \
    "$RUNTIME_APP/Contents/MacOS/steamui/realsteamonmac/config.js"; then
    echo "GPTK must not be exposed by an open-only runtime" >&2
    exit 1
fi

echo "Steam injection installer contract: PASS"
