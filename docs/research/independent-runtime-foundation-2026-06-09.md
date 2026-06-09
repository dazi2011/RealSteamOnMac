# Independent Runtime Foundation Research

Date: 2026-06-09

## Objective

Build a CrossOver-independent compatibility runtime that native macOS Steam
can use for owned Windows-only games. The runtime must preserve the Linux
Steam Play layout:

```text
<steam-library>/steamapps/compatdata/<appid>/pfx
```

Runtime packages and per-game configuration are project-owned. Existing game
depots, prefixes, and Steam Cloud data must never be deleted by an installer or
upgrade.

## Verified Inputs

### Apple Game Porting Toolkit 3

User-supplied disk image:

```text
/Users/wudazi/Downloads/Game_Porting_Toolkit_3.0.dmg
```

The evaluation image contains Apple's D3DMetal redistributable libraries, not
a complete Wine runtime. Apple's readme requires a separately supplied custom
Wine and identifies Gcenx's game-porting-toolkit builds as one available
environment.

The project must not commit Apple binaries. The runtime installer may copy
them from a user-supplied official disk image and must retain Apple's license
files.

Documented environment controls:

- `D3DM_SUPPORT_DXR=1`: advertise supported DXR functionality.
- `ROSETTA_ADVERTISE_AVX=1`: advertise AVX through Rosetta where required.
- `D3DM_ENABLE_METALFX=1`: map supported DLSS calls to MetalFX on macOS 26.

MetalFX also requires the documented `nvngx` and `nvapi64` files in the
prefix's `drive_c/windows/system32`.

### Independent Wine Runtime

Verified upstream release:

```text
Gcenx game-porting-toolkit 3.0-3
SHA-256 d377683937340f914823dbb2e1252b329cbf834ff58907d0293db8cebf0e392e
```

The archive contains a complete custom Wine environment with `wine64`,
`wineserver`, WineD3D, `winevulkan`, and `libMoltenVK.dylib`. It is therefore
independent of the installed CrossOver applications.

### Renderer Payloads

Verified upstream releases:

```text
DXMT v0.80
SHA-256 8f260e36b5739e68f3bad613381441385c4dc7b85b78ba8de653d5a6a264529d

DXVK-macOS v1.10.3-20230507 repack builtin
SHA-256 810b1e5caf8ce975b784fae866a130ad23fa0ea233b0e5609cbc4a45f3ef6f00
```

The upstream DXVK v2.7.1 archive was also checksum-verified during research,
but it is not activated. Gcenx documents that current MoltenVK lacks Vulkan
extensions required by upstream DXVK and provides DXVK-macOS for this purpose.
Shipping upstream DXVK as selectable would create a known-broken option.

The active archives are downloaded and checksum-verified under:

```text
~/Library/Caches/RealSteamOnMac/downloads
```

WineD3D, DXMT, and DXVK-macOS use Gcenx Wine Staging 11.10:

```text
SHA-256 940bdd1a177872020be01c5c33917cb8eecc1cc3193ad554914fb6efd90d7889
```

That build includes the current macOS Wine driver exports, `winevulkan`, and
MoltenVK. DXVK-macOS has now passed a real Direct3D game launch and Steamworks
acceptance with People Playground.

## Package Layout

Use a transactional project-owned runtime root:

```text
~/Library/Application Support/RealSteamOnMac/runtimes/
  packages/<package-id>/
  current -> packages/<package-id>
```

Each immutable package contains four separate Wine roots:

```text
manifest.json
SHA256SUMS
wine/gptk/
wine/dxmt/
wine/dxvk/
wine/wined3d/
renderers/dxmt/
renderers/dxvk/
licenses/
```

Installation extracts to a sibling staging directory, verifies required files
and hashes, then atomically renames the completed package. The `current`
symlink is replaced atomically. Existing packages remain available for
rollback and multi-version selection.

## Per-Game Layout

For AppID `1118200` in the current library:

```text
/Volumes/990pro/games/mac/steamapps/compatdata/1118200/
  pfx/
  realsteamonmac/config.json
  realsteamonmac/logs/
  realsteamonmac/install-ledger.json
```

The runtime creates the prefix only when launching or explicitly preparing the
game. It never removes an existing prefix. Renderer DLL activation is
recorded so switching modes can restore or replace only project-owned files.

## Steam Launch Contract Finding

At 2026-06-09 12:16:46 local time, native Steam received:

```text
steam://rungameid/1118200
```

It advanced through Cloud, stats, controller, license, and process-creation
tasks, then failed:

```text
CreatingProcess
Failed to spawn process
AppError_46, OS Error 0
```

The compatibility tool logging stub was not invoked.

Steam's configuration contains:

```text
CompatToolMapping/1118200/name = realsteamonmac-experimental
```

and `compat_log.txt` confirms the mapping. The missing link is native runtime
registration or launch dispatch: the project tool is visible in the patched UI
but the current Steam process did not load its executable entry from
`compatibilitytools.d`.

The prior startup experiment proved that presenting a valid compatibility tool
through `STEAM_EXTRA_COMPAT_TOOLS_PATHS` during startup removes Cloud settings
on this macOS Steam build. That variable must remain absent during startup.
The next implementation step is therefore either:

1. a post-initialization native tool-list refresh that preserves Cloud; or
2. an allowlist-scoped launch dispatch that invokes the project wrapper while
   leaving native macOS titles untouched.

Both paths must fail closed for unmanaged AppIDs and unknown Steam builds.

## Implemented Foundation

The first package is installed and activated:

```text
~/Library/Application Support/RealSteamOnMac/runtimes/packages/
  gptk3.0-3-wine11.10-dxmt0.80-dxvkmacos1.10.3
```

Verified:

- package `SHA256SUMS` passes;
- source and installed runtime-manager hashes match;
- GPTK Wine executes and reports its Gcenx Wine build;
- DXMT, DXVK-macOS, and WineD3D execute Wine Staging 11.10;
- the People Playground dry-run resolves exactly to
  `/Volumes/990pro/games/mac/steamapps/compatdata/1118200/pfx`;
- dry-run does not create the prefix.

The native engine now has a build-UUID-gated pointer replacement for
steamclient's resolved `posix_spawn` import. The replacement:

- checks `SteamAppId`, `SteamGameId`, or `STEAM_COMPAT_APP_ID`;
- requires the AppID to be in the authenticated live allowlist;
- requires an existing `.exe` with an `MZ` PE header;
- preserves Steam's file actions, spawn attributes, environment, and original
  game arguments;
- substitutes `/usr/bin/python3 <runtime> launch ...`;
- leaves unmanaged AppIDs and native executables on the original system
  `posix_spawn`.

This retains Steam's completed Cloud/license/controller launch pipeline and
lets Steam track the spawned PID while avoiding startup-time compatibility
tool discovery.

## Live GPTK Acceptance

At 2026-06-09 12:38 local time, Steam launched AppID `1118200` through the
new dispatcher. The complete observed chain was:

```text
Steam
  -> allowlist-scoped posix_spawn redirect
  -> realsteamonmac-runtime launch
  -> GPTK Wine
  -> People Playground.exe
```

The launch created the requested prefix at:

```text
/Volumes/990pro/games/mac/steamapps/compatdata/1118200/pfx
```

Steam tracked PID `3159`, advanced `LaunchApp` through
`WaitingGameWindow` to `Completed`, attached its native game overlay process,
and removed the process cleanly after the test. CoreGraphics independently
reported an on-screen 1920x1080 window titled `People Playground`.

Unity's `Player.log` confirms:

- Unity `2020.3.1f1` initialized;
- Direct3D 11 feature level 11.1 was created through GPTK;
- the game reached its menu initialization and registered all bundled maps;
- the prefix contains the expected game-local `Player.log`.

Visual evidence is stored at:

```text
docs/evidence/people-playground-gptk-live-2026-06-09.png
```

This passes the independent runtime, prefix, Direct3D, visible-window, Steam
PID tracking, and clean-exit gates. It does not yet pass the Steamworks gate.

## First Steamworks Boundary

The visible game menu reported `Steam is not initialised`, and `Player.log`
recorded:

```text
SteamApi_Init failed with FailedGeneric
Could not determine Steam client install directory.
```

This is not a renderer failure. The native macOS Steam client completed its
pre-launch Cloud, stats, controller, and license tasks, while the Windows game
could not initialize the in-process Steamworks API. Proton solves the
equivalent cross-ABI problem with `lsteamclient`; merely inventing registry
paths or copying a Windows Steam DLL would not establish a verified connection
to macOS Steam and could create false Cloud or entitlement behavior.

The next gate is therefore a real Darwin-to-Windows Steamworks bridge, or a
well-evidenced declaration of the APIs that cannot be bridged safely. No fake
success shim may be used.

## Steamworks And DXVK Acceptance

The repository now builds a reproducible x86_64 bridge from pinned sources:

```text
Proton 25880e88befb52c5aa7ff162c5b00b6b8825e494
Valve Wine 2f70bfd4d0f4e67a8a599c4a09760579bc2a4fa4
```

The macOS patch supplies Steam Input keycode conversion and handles the two
interface helpers missing from native `steamclient.dylib` without changing the
Linux path. The generated bridge validates against all 208 interfaces exposed
by the pinned Proton generated source.

Validated hashes:

```text
159798e1caab1102f5d51a5e15891f4d4f5cd901ed7fb54a9ae45d51bb1280ec
  lsteamclient.so
b806f522a5e49b4b3ba9e0259e8bbf02787e7c287f4f10d880a660190c23c1ca
  lsteamclient.dll
```

The active package is:

```text
gptk3.0-3-wine11.10-dxmt0.80-dxvkmacos1.10.3-lsteamclient-proton11b5-macos2
```

The runtime records and verifies its managed bridge files, points the bridge at
the real native Steam client, and refuses to overwrite unmanaged Steam DLLs in
the PFX.

A native `steam://rungameid/1118200` DXVK launch produced:

```text
Steamworks initialised
Steam login: True
```

The bridge trace reached native `steamclient.dylib`, acquired the Steam pipe
and user, requested the generated Steam interfaces, and completed callbacks.
Workshop subscription retrieval also completed. The earlier
`SteamApi_Init failed`, `VersionMismatch`, and `FailedGeneric` markers were
absent.

The migrated PFX attempted to launch an old CrossOver menu helper through Wine
menu integration. The runtime now disables `winemenubuilder.exe`; the repeated
launch used only the RealSteamOnMac package and native Steam.

Normal exit exposed a game-specific Wine/.NET PID bug. People Playground's mod
compiler monitored Wine PID `312`, while macOS PID `312` was the persistent
`/usr/libexec/searchpartyd`. The runtime now supervises AppID `1118200` and
terminates only that AppID's isolated Wine server after the main game exits.
Other AppIDs retain normal Wine process behavior.

The final menu-exit test returned game exit code `0`, cleared all related
processes within five seconds, removed AppID `1118200` from Steam's running
list, and completed `AC Exit` AutoCloud upload.

Detailed evidence is recorded in:

```text
docs/research/steamworks-bridge-2026-06-09.md
docs/evidence/people-playground-dxvk-steamworks-live-2026-06-09.png
```

DXMT is not accepted. DXMT v0.80 reports that the current Wine build lacks its
required exported symbols. GPTK + Steamworks and WineD3D live acceptance also
remain open.

## Subsequent Closure

The earlier boundaries above are historical. A pinned Wine 11 macdrv
compatibility build later accepted DXMT as the default renderer. GPTK launches
after renderer-aware removal of the incompatible Wine 11 Steamworks bridge,
and WineD3D selection completed Steamworks/Workshop/exit/Cloud acceptance
while this game fell back to Unity Vulkan. See
`docs/research/cross-renderer-final-acceptance-2026-06-09.md`.

## Diagnostic Side Effect

One registry diagnostic command was initially run without the intended
`WINEPREFIX`. Wine updated the user's default `~/.wine` prefix at 12:42 local
time before the error was noticed. It did not modify the project PFX or Steam
files. The default prefix was not deleted or rolled back because its prior
state was unknown. All subsequent Wine diagnostics must set both
`WINEPREFIX` and the renderer's required synchronization environment.

## Acceptance Gates

- Package installer is idempotent and transactional.
- Source archive checksums are mandatory.
- Apple files come only from an explicit local official disk image.
- `wine64 --version` runs from the installed independent package.
- AppID resolves to the exact Steam library containing the game.
- Prefix path is exactly `steamapps/compatdata/<appid>/pfx`.
- A dry-run prints a lossless argument and environment plan.
- Cloud fields remain present after runtime installation and Steam restart.
- People Playground launches from Steam, creates its PFX, opens a real window,
  and exits cleanly. Passed for GPTK window creation and DXVK full closure.
- The Windows game initializes Steamworks against the running macOS Steam
  client without replacing ownership or Cloud behavior with a fake API.
  Passed with the pinned Proton bridge and DXVK-macOS.
- At least one alternate renderer can be selected and reaches the executable.
  Passed with DXVK-macOS. DXMT remains blocked by missing Wine exports.
