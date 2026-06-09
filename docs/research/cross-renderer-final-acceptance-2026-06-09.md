# Cross-Renderer Final Acceptance

Date: 2026-06-09

Steam build: `1780705203`

AppID: `1118200` (People Playground)

## Accepted Default

The installed default is DXMT with MSync enabled and all other optional
switches disabled. Native Steam launched the game through the project runtime,
created Direct3D 11 feature level 11.1 on Apple M2 Max, initialized
Steamworks, logged in, retrieved Workshop state, and reached the menu in 18
seconds. `WM_CLOSE` returned the game to Steam's fully installed state, removed
all managed Wine processes, and completed AutoCloud plus upload at 18:14:35
Asia/Shanghai.

## GPTK Boundary And Fix

GPTK initially returned exit code `3` after the shared PFX had been used by
the Wine 11 renderers. A private run-command job proved that GPTK Wine 7.7
could still use the prefix and execute `reg.exe`, so this was not a general
prefix-version failure.

The GPTK `Player.log` reached D3DMetal and then asserted in the project Proton
bridge at `steamclient_main.c:375`. The Wine 11 bridge DLLs were present in
the shared PFX, while GPTK has no compatible Unix bridge in its Wine root.

The runtime now reconciles those files by renderer:

- DXMT, DXVK, and WineD3D atomically install the hash-recorded bridge;
- GPTK removes only bridge files whose current hashes match the private ledger;
- modified or unmanaged files make the transition fail closed.

After deployment, native Steam selected GPTK, the ledger changed to
`active:false`, and the game reached D3DMetal plus menu/map initialization.
Normal `WM_CLOSE` exited at 18:11:28 and completed AutoCloud/upload. GPTK does
not provide in-game Steamworks in this package; the game logs a handled
`Failed to load module ... steamclient64.dll` error instead of crashing.

## WineD3D Acceptance

Selecting WineD3D changed the canonical mode-`0600` AppID config and restored
both managed bridge DLLs with SHA-256:

```text
b806f522a5e49b4b3ba9e0259e8bbf02787e7c287f4f10d880a660190c23c1ca
```

People Playground's D3D11 device creation failed in this mode, after which
Unity selected its Vulkan renderer through MoltenVK. The visible game window,
Steamworks initialization, login, Workshop retrieval, normal exit, process
cleanup, and AutoCloud upload all passed. This is a successful launch path,
but it is not evidence that this title rendered through WineD3D.

Visual evidence:

```text
docs/evidence/people-playground-wined3d-live-2026-06-09.png
SHA-256 9ec179adc4974c525b5497b9013f60e9c85cbc8220390031e8773df886f7f6c2
```

## Final Regression

Read-only live verification after restoring DXMT:

- 34 managed owned Windows-only games;
- 34/34 managed predicates true;
- 34/34 expose all four project tools;
- 34/34 native statuses synchronized;
- 0 invalid-platform detail or overview states;
- Garry's Mod remains excluded at native status `31/31`;
- People Playground remains installed and ready at `11/11`;
- `cloud_enabled=true`;
- native `CloudStorage` remains available.

Automated matrix:

```text
64 Node tests passed
40 Python tests passed
25 shell contracts passed
```

The shell total includes the one-click installer orchestration contract.

## Installation

`script/install_realsteamonmac.sh` is the repeatable top-level installer. It
fails early if Steam is running, then builds the guarded native components,
builds or reuses the pinned Steamworks bridge, installs the immutable runtime
package, and finally installs the Steam integration. Each lower-level
installer retains its existing checksum, signature, atomic publication, and
rollback checks.

The live runtime script deployed for this acceptance has SHA-256:

```text
5faa1e6bc7bcef72d8116c5218ae80c9ac4ca92c2d17aad9cb41b71575d7d1a1
```

Its pre-deployment backup is:

```text
~/Library/Application Support/RealSteamOnMac/runtimes/bin/
  realsteamonmac-runtime.pre-76ec1e5-20260609T101032Z
```

The two bridge DLLs temporarily moved during GPTK diagnosis were preserved
outside the PFX at:

```text
/Users/wudazi/RealSteamOnMac-Backups/
  gptk-bridge-isolation-20260609T100600Z
```
