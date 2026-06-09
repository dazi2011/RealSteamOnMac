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
  on their original page set. This dynamic revision is installed in the current
  Steam client.
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
- The installed shared UI subscribes directly to Steam's native app-detail
  stream after the authenticated registry sync. On the current library all 34
  managed games match their authoritative native status: 24 show the original
  blue `安装` action, seven locally installed games are ready to launch, and
  active update states remain unchanged.
- Live cold-start verification shows For Honor with an enabled native blue
  `安装` button and People Playground with the original green `开始游戏`
  button at status `11/11`. Garry's Mod remains excluded at native status `31`.
- The native engine does not redirect SteamUI's global platform getter. It uses
  that getter address only to identify real app objects before applying
  allowlist-scoped data changes, avoiding a redundant version-sensitive hook.
- The independent runtime package is installed under
  `~/Library/Application Support/RealSteamOnMac/runtimes`. It contains separate
  GPTK, DXMT, DXVK-macOS, and WineD3D roots and does not use either installed
  CrossOver application.
- Runtime configuration resolves prefixes to the Proton-compatible
  `steamapps/compatdata/<appid>/pfx` layout. MSync, Retina mode, Metal HUD,
  MetalFX, DXR, and AVX environment/registry mappings have automated coverage.
- The pre-deployment native launch bridge redirects only managed PE
  executables through the project runtime while preserving Steam's spawn
  attributes, environment, and arguments.
- The reproducible Proton `lsteamclient` bridge connects Windows Steamworks
  calls to native macOS Steam without a fake API. People Playground now reports
  `Steamworks initialised` and `Steam login: True`, retrieves Workshop state,
  and renders through DXVK-macOS.
- A real `steam://rungameid/1118200` launch now creates/uses the Proton-layout
  PFX, opens the game, exits from the game's own menu, clears the isolated Wine
  session, and completes Steam's AutoCloud exit upload.
- DXMT now passes the same real-game boundary through its pinned Wine 11
  macdrv compatibility build: menu, Steamworks login, Workshop state, normal
  exit, and AutoCloud all completed. It is the installed default.
- GPTK now safely deactivates the Wine 11-only Steamworks bridge before
  launch. People Playground reaches D3DMetal and its menu and exits normally;
  in-game Steamworks remains unavailable in GPTK mode instead of crashing.
- WineD3D selection restores the bridge and completes Steamworks, Workshop,
  normal exit, and AutoCloud. For this title Unity falls back from failed
  D3D11 creation to Vulkan/MoltenVK, so this is not a WineD3D rendering claim.
- The compatibility panel now includes a bounded `运行命令` workflow and a
  searchable fixed dependency catalog. Jobs are token-authenticated, scoped
  to one managed AppID, serialized per PFX, and reported through private
  status/log files. The live People Playground panel completed a guarded
  `reg.exe query` and installed the pinned Microsoft Visual C++ 2015-2022 x64
  package with exact size/SHA-256 validation and a per-PFX receipt.

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
- The same loopback service accepts only two fixed action schemas:
  `run-command` and `install-dependency`. It creates a random 128-bit job ID,
  starts the Python runtime without a shell, and serves only the corresponding
  private JSON status file.
- The launcher explicitly removes `STEAM_EXTRA_COMPAT_TOOLS_PATHS`. Runtime
  packages remain outside Steam's native discovery path; the project-owned
  browser bridge supplies their compatibility-page entries instead.
- A guarded Steam UI resource patch dynamically identifies owned, visible
  games whose platform list contains `windows` and not `osx`; it synchronizes
  each managed overview to the authoritative status delivered by Steam's
  native detail subscription.
- The same known-build patch extends Steam's native compatibility-page gate
  from Linux to the dynamic managed-AppID predicate.
- The shared UI context refreshes Steam's own matching React action components
  through `SteamUIStore.WindowStore`; it does not create or restyle a custom
  button.
- The launcher reapplies the known-build UI patch before every Steam start and
  fails back to the original bootstrap on a signature mismatch.
- The runtime installer verifies every upstream archive, copies Apple's
  D3DMetal files only from a user-supplied official GPTK disk image, builds an
  immutable package in a staging directory, and atomically switches `current`.
- The delayed native engine replaces the known steamclient build's resolved
  `posix_spawn` pointer. It invokes the runtime only when the live allowlist
  contains the AppID and the target is an existing PE `.exe`; native programs
  and unmanaged games keep the original system implementation.
- The runtime installs only hash-recorded Steamworks bridge files into a
  game's isolated PFX, rejects unmanaged DLL replacement, removes the managed
  Wine 11 bridge while GPTK is selected, restores it for supported renderers,
  and disables Wine menu integration so migrated CrossOver prefixes cannot
  launch old CrossOver helper applications.
- Run-command targets must be PE files below the game installation or its
  Proton-layout PFX. Reserved Steam, Wine, project, and DYLD environment
  variables cannot be overridden. Dependency installers come only from the
  versioned catalog, must remain on allowlisted Microsoft HTTPS hosts, and
  must match their exact byte size and SHA-256 before Wine starts them.

## Build And Test

```sh
sh script/build_compat_gate_hook.sh
sh script/build_steam_launcher.sh
node --test tests/*.mjs
python3 -m unittest discover -s tests -p 'test_*.py'
for test_file in tests/test_*.sh; do
  sh "$test_file"
done
```

## Install

Quit Steam, then run the repeatable top-level installer:

```sh
sh script/install_realsteamonmac.sh \
  --clean-backup \
  /Users/wudazi/RealSteamOnMac-Backups/steam-1780705203-20260607T083704Z \
  --gptk-dmg \
  "$HOME/Downloads/Game_Porting_Toolkit_3.0.dmg"
```

The top-level installer builds the native components and Steamworks bridge,
installs the immutable runtime package, then installs the Steam integration.
It refuses a running Steam client and stops on the first failed phase.

The lower-level commands remain available for development or partial updates:

```sh
sh script/build_lsteamclient_bridge.sh

sh script/install_runtime_package.sh \
  --gptk-dmg \
  "$HOME/Downloads/Game_Porting_Toolkit_3.0.dmg" \
  --steamworks-bridge \
  "$HOME/Library/Application Support/RealSteamOnMac/build/lsteamclient-proton11b5-macos2"

sh script/install_steam_injection.sh \
  --clean-backup \
  /Users/wudazi/RealSteamOnMac-Backups/steam-1780705203-20260607T083704Z
```

Apple binaries are never committed to this repository. Runtime versions are
kept side by side; the installer verifies checksums and changes only the
`current` symlink after a package passes validation.

The dependency catalog is installed at:

```text
~/Library/Application Support/RealSteamOnMac/dependencies/catalog.json
```

It currently pins the official Microsoft Visual C++ 2015-2022 x64
redistributable and .NET Framework 4.8 offline installer. Downloaded installers
are private cached artifacts and are never committed.

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
for the technical handoff and
[steamworks-bridge-2026-06-09.md](docs/research/steamworks-bridge-2026-06-09.md)
for the bridge build and live acceptance evidence, and
[run-command-dependency-workflow-2026-06-09.md](docs/research/run-command-dependency-workflow-2026-06-09.md)
for the fixed action protocol and dependency security model, and
[cross-renderer-final-acceptance-2026-06-09.md](docs/research/cross-renderer-final-acceptance-2026-06-09.md)
for the final GPTK, WineD3D, DXMT, Cloud, and test boundaries.
