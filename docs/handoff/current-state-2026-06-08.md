# RealSteamOnMac Current State

Date: 2026-06-08

## Phase 1 Result

People Playground (`AppID 1118200`) now permanently exposes Steam's native
blue install action on macOS. The behavior survived:

- leaving the details page and returning;
- more than 30 seconds of runtime;
- a complete Steam quit and direct restart without rerunning the installer;
- Steam rebuilding the app overview and details objects.

A real click on the visible Steam button produced:

```text
eInstallState = 7
eAppError = 0
rgApps[0].nAppID = 1118200
lDiskSpaceRequiredBytes = 455945761
```

The verification called `CancelInstall()` and reached state `16`.
`ContinueInstall()` was not called.

## Phase 2 Result

People Playground now exposes Steam's original per-game `兼容性` page on
macOS. The page uses the unmodified native checkbox, dropdown, localization,
`GetAvailableCompatTools`, and `SpecifyCompatTool` flow.

Verified live behavior:

- the checkbox is selected;
- the dropdown shows `RealSteamOnMac Experimental`;
- the app details report tool priority `250`;
- disabling clears both native mapping and the displayed selection;
- enabling restores both;
- closing and reopening the properties window preserves the selection;
- a complete Steam quit and restart preserves the selection;
- No Man's Sky (`AppID 275850`), which is outside the allowlist, has no
  compatibility tab.

## Installed Architecture

```text
/Applications/Steam.app
  -> realsteamonmac_launcher
  -> verifies or reapplies the known Steam UI resource patch
  -> starts the official runtime with the native hook

Native hook
  -> loads the explicit AppID allowlist
  -> refreshes tracked app objects every 250 ms
  -> performs a full readable/writable-region scan every 15 s
  -> clears only the InvalidPlatform bit for validated allowlisted objects

Steam SharedJSContext UI patch
  -> waits for backend details status 9
  -> normalizes only allowlisted overview status 14 to status 9
  -> enumerates SteamUIStore.WindowStore.SteamUIWindows
  -> force-updates only matching native React action components
  -> wraps SpecifyCompatTool only for allowlisted AppIDs
  -> persists the selected tool in Steam UI local storage
  -> mirrors priority 250 into the macOS app-details object

Guarded Steam UI compatibility resource patch
  -> validates chunk~2dcc5aaf7.js by SHA-256
  -> changes only module 73291's two compatibility-page registration gates
  -> preserves the original Linux condition
  -> additionally accepts AppIDs from __REALSTEAMONMAC_CONFIG__
```

The UI patch status is:

```text
version = 4
mode = shared-app-store-native-actions-and-compatibility
lastError = null
```

No custom install button or replacement click handler is used.

## Current Machine State

- Steam build: `1780705203`
- Allowlist: `config/allowlist.txt`, currently only `1118200`
- Support directory:
  `~/Library/Application Support/RealSteamOnMac`
- Runtime:
  `~/Library/Application Support/Steam/Steam.AppBundle/Steam`
- Clean backup:
  `/Users/wudazi/RealSteamOnMac-Backups/steam-1780705203-20260607T083704Z`
- Guarded clean `steamui/index.html` SHA-256:
  `55ced284314dbc65bff38fb1333d4f4bd617635895e2c0e2197b05028c243282`
- Guarded clean `steamui/chunk~2dcc5aaf7.js` SHA-256:
  `6d28c06fafb32f99c695f4bc4d1b8a8b8fb5bc1efc425f2a78abb8697af81349`

## Verification

```sh
node --test tests/*.mjs
python3 -m unittest tests/test_steamui_patch.py
for test_file in tests/test_*.sh; do sh "$test_file"; done
```

Read-only live state:

```sh
node script/steam_cdp.mjs \
  --expression-file probes/shared_people_playground_state_readonly.js

node script/steam_cdp.mjs \
  --target-title Steam \
  --expression-file probes/verify_people_playground_persistent_ui.js

node script/steam_cdp.mjs \
  --target-title "People Playground" \
  --expression-file \
  probes/verify_people_playground_compatibility_page.js

node script/steam_cdp.mjs \
  --expression-file \
  probes/verify_people_playground_compatibility_state.js
```

The guarded real-button probe never confirms a download:

```sh
node script/steam_cdp.mjs \
  --target-title Steam \
  --expression-file \
  probes/click_people_playground_native_install_button_experiment.js

node script/steam_cdp.mjs \
  --expression-file probes/cancel_people_playground_install_experiment.js
```

## Rollback

Quit Steam, then run:

```sh
sh script/restore_steam_from_backup.sh \
  --clean-backup \
  /Users/wudazi/RealSteamOnMac-Backups/steam-1780705203-20260607T083704Z
```

Unknown Steam builds remain fail-closed. A Steam update requires revalidating
the native UUID/offset fingerprints and the UI index hash before enabling the
project again.

## Next Phase

1. Confirm a completed Windows depot download and Steam validation cycle.
2. Generalize the allowlist management UI beyond the People Playground
   fixture.
3. Implement CrossOver launch routing without opening a second Steam frontend.
4. Add runtime and renderer package management only after launch routing is
   stable.
