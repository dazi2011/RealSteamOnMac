# RealSteamOnMac

Use the native macOS Steam client as the single frontend for selected
Windows-only games. The current prototype enables Steam's original install
planner for allowlisted AppIDs without globally changing the client platform.

## Verified State

- Steam Public Beta build: `1780705203`
- Test game: People Playground, AppID `1118200`
- Native macOS games remain outside the allowlist.
- `SteamClient.Installs.OpenInstallWizard([1118200])` reaches state `7`
  (`ShowConfig`) with error `0`.
- Steam calculated `455945761` bytes through its original install planner.
- The experiment was cancelled before `ContinueInstall`; no download started.

The compatibility properties page, actual depot download, CrossOver launch,
and renderer/package management are not implemented yet.

## Build And Test

```sh
sh script/build_compat_gate_hook.sh
sh script/build_steam_launcher.sh
node --test tests/steam_cdp.test.mjs
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

See [current-state-2026-06-07.md](docs/handoff/current-state-2026-06-07.md)
for the technical handoff.
