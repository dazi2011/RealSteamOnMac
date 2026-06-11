# RDR2 Rockstar Recovery Evidence

## Scope

This note records a read-only snapshot of the installed Red Dead Redemption 2
Rockstar prerequisite state on 2026-06-11 at 19:17 +0800. No game, prefix,
registry, launcher, or Steam manifest file was changed while collecting it.

The inspected locations were:

- game: `/Volumes/990pro/games/steam/steamapps/common/Red Dead Redemption 2`;
- prefix:
  `/Volumes/990pro/games/steam/steamapps/compatdata/1174180/pfx`;
- runtime state:
  `/Volumes/990pro/games/steam/steamapps/compatdata/1174180/realsteamonmac`.

The prefix occupied 571 MB at the snapshot time.

## Depot Prerequisites

Steam's signed `installscript_sdk.vdf` defines two ordered Rockstar
prerequisites:

1. `Redistributables/Social-Club-Setup.exe /silent`, guarded by
   `HKLM\Software\Rockstar Games\Steam\SDK`;
2. `Redistributables/Rockstar-Games-Launcher.exe /s /t`, guarded by
   `HKLM\Software\Rockstar Games\Steam\Launcher`.

The depot installers were present and readable:

| File | Size | SHA-256 |
| --- | ---: | --- |
| `Rockstar-Games-Launcher.exe` | 112102008 | `51afae4b364112286fda8abeeda64867830792d6134ab6cf2d54bfbb8d21ece7` |
| `Social-Club-Setup.exe` | 127419512 | `8c057d4199ded0bd70e2f769548dd97bec9e0e89a27109d61026b286d79c7cb5` |

The separate signed `installscript.vdf` defines the Vulkan 1.1.108.0
installer and the RDR2 install-folder registry value. It is not a substitute
for either Rockstar SDK prerequisite.

## Prefix State

The following launcher files existed:

| File | Size | SHA-256 |
| --- | ---: | --- |
| `Launcher/Launcher.exe` | 30732408 | `c3095f3b4150583c72230bbcd97e34efb0c0c929f3181c84c5674ce3e93fddb2` |
| `Launcher/RockstarSteamHelper.exe` | 1374840 | `7754ce65446360441be38eefb69b0fb0396b1939656d6d13600f846532679936` |

The Launcher uninstall record, Launcher configuration key, and `Rockstar
Service` service key existed. The installed Launcher reported version
`1.0.106.2879`.

The following required completion evidence was absent:

- no `Social Club` installation directory or executable was found anywhere
  under `drive_c`;
- no `HKLM\Software\Rockstar Games\Steam\SDK` key was found;
- no `HKLM\Software\Rockstar Games\Steam\Launcher` key was found;
- no `HKLM\Software\Valve\Steam\Apps\1174180` prerequisite marker was found.

Registry snapshot hashes:

| File | Size | SHA-256 |
| --- | ---: | --- |
| `system.reg` | 4263641 | `6f41605f31bb75df54160d9426411df498268d57d5a4a2609e7dca3c5accb135` |
| `user.reg` | 119195 | `3f2b9e1bcc81f30e607223af399013a1f0341556236402f8d740028a94433cd0` |
| `userdef.reg` | 4078 | `6cded77fd461afd141fa5a9bfaf22e7ee92d61ca3881fc0a38d238af6e97bd18` |

## Log Evidence

`ProgramData/Rockstar Games/Launcher/installer_log.txt` records Launcher file
extraction, VC runtime installation, service installation, and registry
writes. The log stops immediately after writing `EstimatedSize`; it contains
no normal completion record.

`service_log.txt` shows an initial service start timeout (`1053`) followed by a
successful reinstall/start. On 2026-06-11 the service again reached
`SERVICE_RUNNING`. This proves the service can start, but it does not prove
that the Social Club SDK prerequisite or Steam completion markers exist.

The runtime log contains three direct `PlayRDR2.exe` attempts. The active
runtime path was a Wine 11.10 package and the recorded renderer was DXMT.

## Diagnosis

The prefix is a deterministic partial-install state:

- Launcher payload and service exist;
- Social Club payload is absent;
- both Steam prerequisite completion keys are absent;
- the installer log has no completion marker.

Therefore `Launcher.exe` existence alone must never classify this prefix as
healthy. Recovery must use the exact depot-provided prerequisite files in the
signed script order, preserve the game and prefix, and validate each
prerequisite after execution.

## CrossOver Control

The existing CrossOver `RDR2` bottle was inspected read-only as a known
working-state control. It contains:

- `Program Files/Rockstar Games/Social Club/SocialClubHelper.exe`;
- `Program Files/Rockstar Games/Social Club/socialclub.dll`;
- the Social Club uninstall record with display version `2.4.0.146`;
- `Software\Wow6432Node\Rockstar Games\Rockstar Games Social Club`;
- `Software\Wow6432Node\Rockstar Games\Launcher`;
- the Launcher and Social Club Steam prerequisite keys;
- `Rockstar Service`.

The control confirms that Social Club is a substantive installed prerequisite,
not merely an optional Launcher subdirectory. RealSteamOnMac therefore uses
the helper PE plus the Social Club product/uninstall registry keys as its SDK
postconditions. It uses the Launcher and Steam helper PEs plus Launcher
product/uninstall keys as the Launcher postconditions.

The CrossOver bottle is evidence only. No CrossOver binary or proprietary
runtime payload is copied into the project or required at runtime.

## Recovery Boundary

Before any repair mutation, the implementation must create a timestamped
snapshot containing:

- the three Wine registry files;
- Rockstar Launcher and Social Club directories if present;
- Rockstar ProgramData and per-user Rockstar state;
- relevant runtime and Rockstar logs;
- a JSON manifest containing paths, sizes, SHA-256 values, and missing paths.

Wine user folders can be symbolic links to host directories. Snapshot glob
matches are resolved again after expansion; matches outside the prefix are
listed in `external_skipped` and are never hashed or copied. Recovery does not
mutate those host paths.

Automatic recovery may run only the two verified depot installers with the
arguments from `installscript_sdk.vdf`. It must never delete the game
directory, replace the whole prefix, or infer an installer from an arbitrary
download.

The production recipe is stored in `config/dependencies.json`. The runtime
executes it after prefix preparation and before `PlayRDR2.exe`. A failed hash,
installer exit, PE check, or registry check blocks the game process and reports
the snapshot path.

Rollback restores files from the timestamped snapshot while Steam and all Wine
processes for AppID 1174180 are stopped. The mutation report must list every
installer command, exit code, postcondition, and snapshot path.
