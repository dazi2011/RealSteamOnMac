# RealSteamOnMac Current State

> Historical snapshot. For the deployed cloud-safe state and current next
> steps, use `current-state-2026-06-09.md`.

Date: 2026-06-07

## Scope And Result

The current phase answers one question: can native macOS Steam use its own
license, depot, disk-space, and install-planning logic for a selected
Windows-only game without globally pretending to be Windows?

Yes, for People Playground AppID `1118200` on Steam Public Beta build
`1780705203`.

Verified result from the original Steam API:

```text
OpenInstallWizard([1118200])
eInstallState = 7 (ShowConfig)
eAppError = 0
lDiskSpaceRequiredBytes = 455945761
```

The install was immediately cancelled. `ContinueInstall` was never called and
no game content was downloaded.

## Current Machine State

- Modified entry app: `/Applications/Steam.app`
- Steam entry executable: `realsteamonmac_launcher`
- Original bootstrap fallback: `Contents/MacOS/steam_osx.original`
- Runtime:
  `~/Library/Application Support/Steam/Steam.AppBundle/Steam`
- Support:
  `~/Library/Application Support/RealSteamOnMac`
- Allowlist: only `1118200`
- Clean backup:
  `/Users/wudazi/RealSteamOnMac-Backups/steam-1780705203-20260607T083704Z`

`Steam.app` currently passes `codesign --verify --deep --strict`.

## Runtime Architecture

```text
LaunchServices opens /Applications/Steam.app
  -> realsteamonmac_launcher
  -> sets per-process hook and compatibility-tool environment
  -> execs the official Steam runtime with -skipinitialbootstrap
  -> Steam performs one early self-exec
  -> hook survives that exec
  -> a short-lived worker waits for steamui and app objects
  -> only allowlisted object flags are changed
  -> worker clears injection environment and exits
```

The hook does not patch the `steamui` text segment. It scans readable/writable
regions and accepts a candidate only when all conditions match:

- object `+0x08` is an allowlisted AppID;
- object `+0x1c` contains platform-invalid bit `0x10`;
- object vtable `+0x68` points to the verified platform-flags getter.

## Build Fingerprints

SteamUI:

- UUID: `BF95203F-385E-3AF0-82B6-AC509AE1224D`
- platform-flags getter offset: `0x005EAC3C`
- expected ARM64 instructions:
  `0xB9401C00`, `0xD65F03C0`

SteamClient compatibility enable gate:

- UUID: `B2950628-803A-3EFD-99EF-3AD6B7B65D1C`
- offset: `0x00A012D0`
- original ARM64 instructions:
  `0xD101C3FF`, `0xA9054FF4`
- current experimental runtime has the gate forced true on disk.
- AppID mapping remains per-game; there is no AppID `0` wildcard.

The clean backup restores the original `steamclient.dylib`.

## Rejected Paths

### Global Windows Platform

Rejected because it changes depot and update semantics for native and
dual-platform macOS games.

### Frontend-Only Button Styling

Rejected because InvalidPlatform maps to no action. A green button without a
backend state transition is cosmetic.

### Runtime SteamUI Text Patch

Rejected because modifying the getter code caused delayed Steam IPC failure
after debugger detach.

### Post-Startup LLDB Injection

Rejected because attaching stops the Steam main process long enough for
`ipcserver` to disconnect. SteamClient asynchronous calls then time out.

### Plain DYLD Environment On Valve-Signed Runtime

Rejected because macOS filters the injection. The installer ad-hoc signs only
the runtime main executable with:

```text
com.apple.security.cs.allow-dyld-environment-variables
com.apple.security.cs.disable-library-validation
```

## Important Files

- `hook/compat_gate_hook.c`: version-gated data-only platform override.
- `launcher/steam_launcher.c`: LaunchServices-safe runtime launcher.
- `script/install_steam_injection.sh`: guarded real-machine installer.
- `script/restore_steam_from_backup.sh`: non-destructive rollback.
- `script/steam_cdp.mjs`: CDP probe runner.
- `probes/open_people_playground_install_wizard_experiment.js`: original
  install-planner proof.
- `probes/cancel_people_playground_install_experiment.js`: safe cancellation.
- `config/allowlist.txt`: the only enabled AppIDs.

## Remaining Work

1. Verify a small, cancellable real depot download and inspect the selected
   Windows depot before keeping any files.
2. Add the native-style Compatibility properties page.
3. Implement provider and CrossOver Preview bottle scanning.
4. Route Play to CrossOver without showing a second Windows Steam window.
5. Add renderer/runtime package validation and transactional replacement.
6. Revalidate every UUID and offset after each Steam update.

Do not expand the allowlist or call `ContinueInstall` without a new bounded
test decision.
