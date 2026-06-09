# DXMT v0.80 And Wine 11.10 macdrv Compatibility

Date: 2026-06-09

## Result

People Playground AppID `1118200` renders its main menu through DXMT v0.80
using Wine Staging 11.10. Steamworks initializes against native macOS Steam,
Workshop subscriptions load, the game exits normally, and Steam completes its
AutoCloud exit workflow.

The accepted isolated package is:

```text
/private/tmp/realsteamonmac-formal-dxmt-runtime/packages/
  gptk3.0-3-wine11.10-dxmt0.80-dxmtmac1-dxvkmacos1.10.3-
  lsteamclient-proton11b5-macos2
```

The user's active `~/Library/Application Support/RealSteamOnMac/runtimes/current`
was not changed during this isolated acceptance.

## Root Cause

DXMT v0.80 resolves an optional `macdrv_functions` table through
`dlsym(RTLD_DEFAULT, "macdrv_functions")`. Its window structure expects the
pre-Wine-11 `client_cocoa_view` field.

Wine 11.10 changed this boundary in two ways:

1. winemac is loaded locally, so its private exports are not visible through
   `RTLD_DEFAULT`;
2. the current window data stores `client_view`, which can remain null until a
   `macdrv_client_surface` is created and presented.

The earlier Wine 8 experiment was rejected because Unity failed with a stack
overflow. Replacing DXMT or bypassing its Metal-view checks was also rejected.

## Implemented Compatibility Layer

`runtime/dxmt_winemac_compat.c` is compiled into Wine's `winemac.so`. It:

- exports the exact function-table ABI expected by DXMT v0.80;
- creates a Wine 11 client surface when a window lacks `client_view`;
- returns a legacy-shaped, short-lived window-data proxy;
- retains the client surface until DXMT releases its Metal view;
- preserves Wine's native lock and reference-count boundaries.

`hook/dxmt_macdrv_visibility_shim.c` is injected only into DXMT Wine processes.
It exports a globally visible table, finds the locally loaded `winemac.so`
through dyld, and forwards only the functions DXMT uses.

The runtime removes inherited `DYLD_INSERT_LIBRARIES` and sets the package-owned
shim path only when `renderer == "dxmt"`. Missing manifest metadata, driver, or
shim fails closed before Wine starts.

## Reproducible Build

Run:

```sh
script/build_dxmt_winemac_compat.sh
```

Pinned sources:

```text
Wine 11.10
2cac6ccf33c0807f374dc96f5a20e35a2da86157

Wine Staging v11.10
f45e84d7a01a52d379e4003f03800c13875c69e9
```

The builder applies the complete Wine Staging patch set, applies
`patches/wine-11.10-dxmt-macdrv-compat.patch`, builds every linked winemac
object with `MACOSX_DEPLOYMENT_TARGET=10.15`, compiles the visibility shim,
ad-hoc signs both outputs, and verifies architecture, exported symbols, minimum
OS, hashes, and immutable output metadata.

Accepted hashes:

```text
cc86bd9296688cbcceca146cdb9a88b9ac97859f96c4b05bf9c0e7c7496529c9
  winemac.so

afa8a47ddd73057bd014e1807bacaf7a91d7917ad1eb51b1d1afb7446b8349c0
  librealsteamonmac_dxmt_macdrv_shim.dylib
```

The runtime installer builds these artifacts automatically when they are not
already present, installs them only into the DXMT Wine root, records their
source metadata in `manifest.json`, and includes both files in package
`SHA256SUMS`.

## Live Acceptance

The formal runtime dry-run showed:

```text
renderer = dxmt
dxmt_winemac_compat =
  RealSteamOnMac DXMT Wine macdrv compatibility
DYLD_INSERT_LIBRARIES =
  <package>/wine/dxmt/lib/librealsteamonmac_dxmt_macdrv_shim.dylib
```

The installed `wine64` remained the original Mach-O launcher and symlinked to
`wine`; no wrapper script was used.

`Player.log` recorded:

```text
Steamworks initialised
Steam login: True
Initialising control scheme menu
Steam Workshop Retrieving list
Retrieved 1 subscriptions
```

Visual evidence:

```text
docs/evidence/people-playground-dxmt-wine11-live-2026-06-09.png
SHA-256 4be624af3074df33dc948011197853f2cc347f75ff0f64f02413ac3824f421af
```

A helper in the same Wine session sent the game window `WM_CLOSE`. The game
and runtime exited `0`; no game, compiler, crash handler, Wine server, or
runtime process remained. Steam logged:

```text
Remove 1118200 from running list
Starting sync (up,AC Exit,)
AutoCloud complete
Upload complete in build list
```

## Remaining Issue

People Playground's separate mod compiler still reports a transient
`127.0.0.1:32513` connection refusal while recompiling the installed Chinese
translation mod. It does not prevent menu rendering, Steamworks login,
Workshop subscription retrieval, normal exit, or AutoCloud. It remains a
game-specific dependency/process test, not a DXMT rendering blocker.
