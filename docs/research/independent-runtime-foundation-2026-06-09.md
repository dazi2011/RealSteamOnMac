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
MoltenVK. A real Direct3D launch is still required before DXVK-macOS can be
declared working.

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
  and exits cleanly.
- At least one alternate renderer can be selected and reaches the executable.
