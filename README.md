# RealSteamOnMac

Use the native macOS Steam client as the single frontend for owned
Windows-only games. The project is transitioning from the proven single-game
download prototype to a cloud-safe, independent compatibility runtime.

## Verified State

- Steam Public Beta build: `1780705203`
- Test game: People Playground, AppID `1118200`
- Steam's live owned-library data currently identifies 34 Windows-only games;
  native and dual-platform macOS games remain outside the managed registry.
- The earlier allowlisted prototype proved Steam's native blue `安装` action
  could survive page navigation/restarts and drive a real Windows-depot
  download without a project-owned click handler.
- People Playground reached **Fully Installed** on macOS through the native
  client: `appmanifest_1118200.acf` reports `StateFlags 4`, `UpdateResult 0`,
  `SizeOnDisk 455945761`, with depot `1118201` installed. The ~436 MB Windows
  build (`People Playground.exe`, `UnityPlayer.dll`, …) is on disk.
- Steam Cloud is restored in the deployed client: the global Cloud page renders
  both controls, native macOS games expose their normal cloud state, and People
  Playground no longer enters a new pending-platform-change loop.
- The repository's guarded UI patch now derives its managed registry from
  Steam's decoded app overview/details stores every five seconds. New purchases
  can enter the registry without reinstalling RealSteamOnMac.
- The browser registry is synchronized to the delayed native engine through an
  authenticated loopback-only endpoint. The installer creates a private token
  with mode `0600`; failed browser requests are retried on the next five-second
  scan.
- The repository patch exposes Steam's original `兼容性` properties page for
  managed Windows-only games while leaving native and dual-platform macOS games
  on their original page set. Live deployment of this dynamic revision is
  pending coordinated backend activation.
- The tested compatibility-page bridge provides a project-owned tool list
  without invoking Steam's cloud-breaking native tool discovery path.
- The startup path intentionally does **not** register
  `STEAM_EXTRA_COMPAT_TOOLS_PATHS`. On macOS build `1780705203`, pointing that
  variable at a valid compatibility tool removes native Cloud settings from the
  settings bridge.
- The repository's native install/data patch engine is loaded 30 seconds after
  the final Steam runtime starts. It accepts bounded AppID registry updates,
  rebuilds the allowlist-gated install trampoline, and restores the original
  instruction when the registry becomes empty.
- The currently installed persistent Steam files remain at the earlier
  cloud-safe baseline until the coordinated dynamic-registry deployment. The
  newer delayed activation and registry bridge have passed isolated and live
  A/B tests from the repository.
- In the current cloud-safe startup, People Playground remains installed but
  reports Steam display status `14`; restoring the blue/Play action is the
  active Phase 3 task.

Launching the installed Windows binary (CrossOver/Proton routing) and
renderer/package management remain future work. A download may briefly park as
`Disabled (Suspended)` — that is Steam's normal client-side download scheduler,
not a project limit; resuming it (or relaunching Steam) lets it finish, as it
did here.

## How It Works

- `libRealSteamCompatGate.dylib` is now a minimal startup guard. Its constructor
  preserves injection through Steam's bootstrap fork, then clears inherited
  variables in every Helper and schedules one engine activation in the final
  runtime.
- `libRealSteamNativeEngine.dylib` contains the proven allowlist-gated app-data
  and `GetAppForInstallation` patches, has no dyld constructor, and is loaded
  by the guard only after a 30-second initialization delay.
- The engine listens only on `127.0.0.1:57344` for authenticated `text/plain`
  AppID registry updates. Requests are capped at 16 KiB and 256 AppIDs; invalid
  tokens and malformed payloads leave the active registry unchanged.
- The launcher explicitly removes `STEAM_EXTRA_COMPAT_TOOLS_PATHS`. Runtime
  packages remain outside Steam's native discovery path; the project-owned
  browser bridge supplies their compatibility-page entries instead.
- A guarded Steam UI resource patch dynamically identifies owned, visible
  games whose platform list contains `windows` and not `osx`; it synchronizes
  only backend-ready managed overview state.
- The same known-build patch extends Steam's native compatibility-page gate
  from Linux to the dynamic managed-AppID predicate.
- The shared UI context refreshes Steam's own matching React action components
  through `SteamUIStore.WindowStore`; it does not create or restyle a custom
  button.
- The launcher reapplies the known-build UI patch before every Steam start and
  fails back to the original bootstrap on a signature mismatch.

## Build And Test

```sh
sh script/build_compat_gate_hook.sh
sh script/build_steam_launcher.sh
node --test tests/*.mjs
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
executable with the minimum DYLD entitlements, installs the minimal startup
guard plus delayed native engine, creates the private registry token, and
installs a universal launcher in `Steam.app`.

Verify the installed UI resources while Steam is stopped:

```sh
python3 script/patch_steamui.py verify \
  --steamui-root \
  "$HOME/Library/Application Support/Steam/Steam.AppBundle/Steam/Contents/MacOS/steamui"
```

With the People Playground properties window open:

```sh
node script/steam_cdp.mjs \
  --target-title "People Playground" \
  --expression-file \
  probes/verify_people_playground_compatibility_page.js

node script/steam_cdp.mjs \
  --expression-file probes/cloud_settings_state_readonly.js

node script/steam_cdp.mjs \
  --target-title "Steam 设置" \
  --expression-file probes/cloud_settings_page_readonly.js
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

See [current-state-2026-06-09.md](docs/handoff/current-state-2026-06-09.md)
for the technical handoff.
