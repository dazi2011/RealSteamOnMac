# RealSteamOnMac

Use the native macOS Steam client as the single frontend for selected
Windows-only games. The project is currently transitioning from the proven
single-game download prototype to a cloud-safe, independent compatibility
runtime.

## Verified State

- Steam Public Beta build: `1780705203`
- Test game: People Playground, AppID `1118200`
- Native macOS games remain outside the allowlist.
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
- People Playground exposes Steam's original `兼容性` properties page.
- A non-allowlisted game keeps the original macOS properties pages without a
  compatibility tab.
- The startup path intentionally does **not** register
  `STEAM_EXTRA_COMPAT_TOOLS_PATHS`. On macOS build `1780705203`, pointing that
  variable at a valid compatibility tool removes native Cloud settings from the
  settings bridge.
- The native install/data patch engine is built and installed but dormant. The
  earlier People Playground download is preserved, while new Windows-only
  enablement is being moved to a generated registry and post-initialization
  controller.
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
  only clears inherited injection variables before Steam creates Helper
  processes.
- `libRealSteamNativeEngine.dylib` contains the proven allowlist-gated app-data
  and `GetAppForInstallation` patches, but has no dyld constructor and is not
  loaded during Steam initialization.
- The launcher explicitly removes `STEAM_EXTRA_COMPAT_TOOLS_PATHS`. Runtime
  packages remain installed but dormant until the project-owned registry and
  post-initialization activation path are ready.
- A guarded Steam UI resource patch synchronizes only backend-ready allowlisted
  overview state.
- The same known-build patch extends Steam's native compatibility-page gate
  from Linux to explicit allowlisted AppIDs.
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
executable with the minimum DYLD entitlements, installs the minimal startup
guard plus dormant native engine, and installs a universal launcher in
`Steam.app`.

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
