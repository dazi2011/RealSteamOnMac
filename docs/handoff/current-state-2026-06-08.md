# RealSteamOnMac Current State

Date: 2026-06-08

> Historical snapshot. For the deployed cloud-safe state and current next
> steps, use `current-state-2026-06-09.md`.

## Phase 1 Result

People Playground (`AppID 1118200`, a Windows-only title) now installs on macOS
through the unmodified native Steam client: the blue `安装` action appears,
clicking it starts Steam's real Windows-depot download, and the download runs to
**Fully Installed**. No lldb, no manual patching, no project-owned button.

Authoritative end state from Steam's own
`appmanifest_1118200.acf` (on the active `/Volumes/990pro` library):

```text
StateFlags        4            (Fully Installed)
UpdateResult      0            (No Error)
SizeOnDisk        455945761    (full 456 MB)
BytesToDownload   61705504  == BytesDownloaded 61705504
BytesToStage      168049276 == BytesStaged 168049276
InstalledDepots { 1118201 -> manifest 9210503819883706733, size 455945761 }
```

On disk: `common/People Playground/` holds the real Windows build
(`People Playground.exe`, `UnityPlayer.dll`, `People Playground_Data/`,
`MonoBleedingEdge/`) at ~436 MB. Steam's content log recorded the genuine
download and commit:

```text
Downloading 796 chunks for depot 1118201
AppID 1118200 update started : download 0/61705504, stage 0/168049276
AppID 1118200 state changed : Fully Installed,
AppID 1118200 scheduler finished : removed from schedule (result No Error, state 0xc)
```

### Two-layer fix

The button and the download are two separate native gates:

1. **Button visibility** — the data-override worker clears only the
   `InvalidPlatform` bit (`0x10`) on validated allowlisted app objects, so Steam
   renders its own `安装` action (display status 9).
2. **Install gate** — `GetAppForInstallation` in `steamclient.dylib` (arm64 slice
   vmaddr `0x62505c`) runs `tbnz w8, #4, 0x62508c`: if the app's platform-flags
   word has bit 4 set it jumps to the "Invalid platform" branch and the click
   fails with **error 29**. Clearing the data bit was not enough on its own — the
   click still hit this text gate. The hook now redirects that single instruction
   through an allowlist-gated trampoline (`build_install_gate_trampoline`): for
   AppIDs in the allowlist (compared against `w21`, which carries the AppID
   through the function) it falls through to the real ownership/depot path
   (`0x625060`); everyone else keeps the original veto (`0x62508c`).

The redirect is applied by the **already-active** `data_override_worker` thread
(the `image_added` dyld callback is currently dormant — its only registrar,
`realsteamonmac_apply_text_hooks`, is never called at runtime). The worker
one-shots the patch as soon as `steamclient.dylib` is mapped, guarded by
`gSteamClientInstallGatePatched`, the steamclient UUID, the empty-allowlist
check, and a strict expected-bytes check (`0x37200188`); unexpected bytes are
refused, so an unknown Steam build stays fail-closed.

### Persistence (no lldb)

Verified by a full launcher restart (`open -a /Applications/Steam.app`):

```text
steamclient: install gate patched slide=0x0 target=0x129ed105c trampoline=0x12b290000 appids=1
```

The fresh process auto-installed the trampoline and a subsequent `安装` click
drove the download to Fully Installed — entirely from the deployed hook, with no
debugger attached. The deployed dylib is byte-identical to a fresh build of the
committed source.

### Download suspension (transient, not a blocker)

An earlier attempt showed Steam parking the download as `Disabled (Suspended)`
~3 s into the first burst (StateFlags `1026`), which looked like a hard limit.
It is not: on continuation Steam reused the staged partial and downloaded only
the remaining delta to reach Fully Installed. The suspend is a normal
client-side download-scheduler / auto-update-window behavior, independent of the
install gate, and it is not specific to RealSteamOnMac. If a download parks,
resuming it (or relaunching Steam) lets it finish.

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
  -> one-shot redirects the steamclient GetAppForInstallation gate (0x62505c)
     through an allowlist-gated trampoline so an allowlisted Install click
     reaches the real depot download instead of failing with error 29

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

Install-gate live confirmation (needs the patched runtime; no lldb):

```sh
# 1. The hook logs the redirect once steamclient.dylib is mapped:
grep "install gate patched" \
  "$HOME/Library/Logs/RealSteamOnMac/platform-hook.log"

# 2. Trigger Steam's own install planner, then click the native button:
open "steam://install/1118200"
node script/steam_cdp.mjs \
  --target-title Steam \
  --expression-file \
  probes/click_people_playground_native_install_button_experiment.js

# 3. Steam's authoritative state file reports a real, error-free install:
grep -E '"StateFlags"|"UpdateResult"|"InstalledDepots"' \
  "<library>/steamapps/appmanifest_1118200.acf"   # StateFlags 4, UpdateResult 0
```

The guarded cancel probe remains available to back out an in-progress install
without touching any other AppID:

```sh
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

1. Done — a completed Windows depot download and Steam validation cycle
   (People Playground reached Fully Installed, `UpdateResult 0`).
2. Launch the installed Windows binary via CrossOver/Proton routing without
   opening a second Steam frontend. The 436 MB Windows build is on disk; this is
   now the primary frontier.
3. Generalize the allowlist management UI beyond the People Playground fixture.
4. Add runtime and renderer package management only after launch routing is
   stable.
