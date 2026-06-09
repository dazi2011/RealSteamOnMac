# macOS Steamworks Bridge And DXVK Acceptance

Date: 2026-06-09

## Result

People Playground AppID `1118200` now launches from native macOS Steam through
the independent RealSteamOnMac runtime, initializes the real Steamworks client,
renders through DXVK-macOS, exits from the game's own `quit` action, and
completes Steam's AutoCloud exit workflow.

This is a real host-client bridge. It does not replace ownership checks,
Steamworks APIs, achievements, Workshop, or Cloud with a fake implementation.

## Reproducible Bridge Build

The bridge builder pins:

```text
ValveSoftware/Proton
25880e88befb52c5aa7ff162c5b00b6b8825e494

ValveSoftware/wine
2f70bfd4d0f4e67a8a599c4a09760579bc2a4fa4
```

Build:

```sh
sh script/build_lsteamclient_bridge.sh
```

The builder:

1. verifies the exact Proton and Wine commits;
2. applies `patches/proton-lsteamclient-macos.patch`;
3. generates a list of the 208 interfaces implemented by the pinned
   `steamclient_generated.c`;
4. builds the Darwin x86_64 Unix half and PE x86_64 Windows half;
5. verifies Mach-O/PE formats, the `ntdll.so` dependency, and SHA-256 hashes;
6. publishes an immutable output only after validation;
7. refuses an existing output unless its hash manifest and build metadata
   exactly match the newly built staging result.

Validated bridge hashes:

```text
159798e1caab1102f5d51a5e15891f4d4f5cd901ed7fb54a9ae45d51bb1280ec
  x86_64-unix/lsteamclient.so

b806f522a5e49b4b3ba9e0259e8bbf02787e7c287f4f10d880a660190c23c1ca
  x86_64-windows/lsteamclient.dll
```

The macOS patch has two narrow compatibility changes:

- Steam Input key conversion uses macOS Carbon virtual key codes.
- The native `steamclient.dylib` does not export
  `Steam_IsKnownInterface` or `Steam_NotifyMissingInterface`. The bridge
  validates interface names against its generated interface table and logs
  missing-interface notification locally. Linux behavior remains unchanged.

## Installed Runtime

The accepted immutable package is:

```text
~/Library/Application Support/RealSteamOnMac/runtimes/packages/
  gptk3.0-3-wine11.10-dxmt0.80-dxvkmacos1.10.3-lsteamclient-proton11b5-macos2
```

Install or rebuild it with:

```sh
sh script/install_runtime_package.sh \
  --gptk-dmg "$HOME/Downloads/Game_Porting_Toolkit_3.0.dmg" \
  --steamworks-bridge \
  "$HOME/Library/Application Support/RealSteamOnMac/build/lsteamclient-proton11b5-macos2"
```

The package records the bridge in `manifest.json`, installs it only into the
DXMT, DXVK, and WineD3D Wine roots, checks every copied bridge file, and changes
`current` atomically. Existing packages and prefixes are not deleted.

For each prepared prefix the runtime:

- sets `SteamAppId`, `SteamGameId`, `STEAM_COMPAT_APP_ID`, and the exact
  `STEAM_COMPAT_DATA_PATH`;
- points `STEAM_COMPAT_CLIENT_INSTALL_PATH` at native Steam's real
  `steamclient.dylib`;
- installs managed `lsteamclient.dll` and `steamclient64.dll` files under
  `drive_c/Program Files (x86)/Steam`;
- refuses to replace an unmanaged DLL;
- records the package and file hashes in
  `realsteamonmac/steamworks-bridge.json`;
- writes the required Wine Steam registry values;
- disables `winemenubuilder.exe` so a migrated CrossOver prefix cannot launch
  an old CrossOver `.app/Menu Helper`.

## Live Acceptance

Native launch command:

```text
steam://rungameid/1118200
```

The accepted path was:

```text
native macOS Steam
  -> allowlist-scoped posix_spawn redirect
  -> realsteamonmac-runtime
  -> Wine Staging 11.10
  -> DXVK-macOS 1.10.3 / MoltenVK
  -> Proton lsteamclient bridge
  -> native macOS steamclient.dylib
  -> People Playground.exe
```

`Player.log` contains:

```text
Steamworks initialised
Steam login: True
```

The same run retrieved Workshop subscriptions and loaded subscribed content.
It contains none of the previous `SteamApi_Init failed`, `VersionMismatch`, or
`FailedGeneric` markers.

Steam's process log tracked the runtime, Wine processes, game, crash handler,
and mod compiler under AppID `1118200`. Screenshot evidence:

```text
docs/evidence/people-playground-dxvk-steamworks-live-2026-06-09.png
SHA-256 7954debe6bc0137244f3629561582170dd6fc021e792490016a8b73e67ee406c
```

## Exit And Cloud Closure

People Playground passes its Wine PID to its .NET 10 mod compiler. The game PID
was `312`, while macOS PID `312` was the unrelated persistent process:

```text
/usr/libexec/searchpartyd
```

`Process.GetProcessById(312)` therefore never reported exit in this Wine/.NET
combination. `PPGModCompiler.exe` survived the game and kept Steam's AppID
active.

The runtime now supervises the launched process. Only AppID `1118200` receives
the compatibility fix: after the main game exits, the runtime terminates that
AppID's isolated Wine server. Other AppIDs are not force-cleaned.

The final live test used the game's own `quit` menu entry:

- game exit code: `0`;
- runtime cleanup event:
  `post-exit-prefix-cleanup`, wineserver exit code `0`;
- all game, compiler, Wine, and runtime processes were gone within five
  seconds;
- Steam logged `Remove 1118200 from running list`;
- Steam Cloud logged `Starting sync (up,AC Exit,)`, `AutoCloud complete`, and
  `Upload complete in build list`.

The old CrossOver `People Playground.app/Menu Helper` did not appear.

## Backups

Full pre-bridge PFX/runtime snapshot:

```text
/Users/wudazi/RealSteamOnMac-Backups/pre-steamworks-bridge-20260609T051952Z
```

Installed runtime-manager rollback copies:

```text
~/Library/Application Support/RealSteamOnMac/runtimes/bin/
  realsteamonmac-runtime.pre-winemenubuilder-20260609T054455Z
  realsteamonmac-runtime.pre-exit-supervisor-20260609T055241Z
```

## Remaining Boundaries

- DXVK-macOS is the currently verified Steamworks renderer.
- DXMT v0.80 reaches Wine but fails with:

  ```text
  Failed to create metal view, it seems like your Wine has no exported
  symbols needed by DXMT.
  ```

  A DXMT-patched Wine build is still required.
- The GPTK Wine root opens the game with D3DMetal, but the current
  `lsteamclient` package is not installed into that different Wine root.
  GPTK + Steamworks is not yet accepted.
- WineD3D has bridge payloads but has not completed a live game acceptance.
- People Playground still emits a non-fatal initial mod-compiler connection
  warning. The game reaches its menu and Steamworks succeeds, but mod
  compilation itself needs a separate functional test.
- Per-game Steam UI controls, run-command, and dependency installation remain
  future phases.
