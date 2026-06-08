# RealSteamOnMac

Use the native macOS Steam client as the single frontend for selected
Windows-only games. The current prototype enables Steam's original install
planner for allowlisted AppIDs without globally changing the client platform.

## Verified State

- Steam Public Beta build: `1780705203`
- Test game: People Playground, AppID `1118200`
- Native macOS games remain outside the allowlist.
- People Playground permanently renders Steam's native blue `安装` action
  after page navigation and full Steam restarts.
- Clicking that visible button reaches install state `7` (`ShowConfig`) with
  error `0`; the click is not replaced by a project-owned handler.
- Steam calculated `455945761` bytes through its original install planner.
- The verification cancelled at state `16` before `ContinueInstall`; no
  download started.

The compatibility properties page, completed depot download, CrossOver launch,
and renderer/package management are Phase 2 work.

## How It Works

- A process-lifetime native worker keeps only allowlisted app objects eligible.
  It refreshes known objects every `250 ms` and performs a bounded full rescan
  every `15 s`.
- A guarded Steam UI resource patch synchronizes only backend-ready allowlisted
  overview state.
- The shared UI context refreshes Steam's own matching React action components
  through `SteamUIStore.WindowStore`; it does not create or restyle a custom
  button.
- The launcher reapplies the known-build UI patch before every Steam start and
  fails back to the original bootstrap on a signature mismatch.

## Build And Test

```sh
sh script/build_compat_gate_hook.sh
sh script/build_steam_launcher.sh
node --test tests/steam_cdp.test.mjs
node --test tests/test_steamui_policy.mjs
python3 -m unittest tests/test_steamui_patch.py
for test_file in tests/test_*.sh; do
  sh "$test_file"
done
```

## Install

```sh
sh script/install_steam_injection.sh \
  --clean-backup \
  /Users/wudazi/RealSteamOnMac-Backups/steam-1780705203-20260607T083704Z
```

The installer refuses unknown Steam modifications, signs only the runtime main
executable with the minimum DYLD entitlements, and installs a universal
launcher in `Steam.app`.

Verify the installed UI resources while Steam is stopped:

```sh
python3 script/patch_steamui.py verify \
  --steamui-root \
  "$HOME/Library/Application Support/Steam/Steam.AppBundle/Steam/Contents/MacOS/steamui"
```

## Roll Back

Quit Steam first, then run:

```sh
sh script/restore_steam_from_backup.sh \
  --clean-backup \
  /Users/wudazi/RealSteamOnMac-Backups/steam-1780705203-20260607T083704Z
```

The rollback keeps displaced modified files under
`~/RealSteamOnMac-Rollback/`. A Steam update can invalidate the verified UUIDs,
offsets, and runtime signature; unknown builds must remain disabled.

See [current-state-2026-06-08.md](docs/handoff/current-state-2026-06-08.md)
for the technical handoff.
