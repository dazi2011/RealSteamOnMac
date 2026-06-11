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

## Live Recovery Acceptance

The guarded recovery was executed against the live AppID 1174180 prefix on
2026-06-11. Before the installers ran, the runtime published a valid selective
snapshot at:

`/Volumes/990pro/games/steam/steamapps/compatdata/1174180/realsteamonmac/recovery/snapshots/20260611T113340Z`

The snapshot occupied 103 MB. Its manifest was mode `0600`, the snapshot
directories were mode `0700`, and the manifest SHA-256 was
`343e3c97c48f37707f2c31f42cd402370a1b34e71c7e1df436b76599e0a2589a`.
The external host Documents match was recorded in `external_skipped` and was
not copied.

Both signed depot installers returned exit code `0` in the required order:

1. Social Club with `/silent`;
2. Rockstar Games Launcher with `/s /t`.

The private mutation report is:

`/Volumes/990pro/games/steam/steamapps/compatdata/1174180/realsteamonmac/recovery/reports/20260611T113340Z.json`

All seven substantive PE and registry postconditions passed. After recovery,
the prefix occupied 944 MB and contained:

| File | Size | SHA-256 |
| --- | ---: | --- |
| `Social Club/SocialClubHelper.exe` | 2417272 | `b2d3d10ce51dcd8aa1d1777a750a535df01e21a52917893ce86331c0b568a758` |
| `Social Club/socialclub.dll` | 4829816 | `be163741daf029bdf271530dc0a2840e9e10c695c53def767048dc93ece7c2c6` |

The Social Club product and uninstall keys, Launcher product and uninstall
keys, and Steam prerequisite keys were present. A second recovery invocation
returned `state: complete` with no snapshot, report, or installer process,
proving idempotence.

The game payload remained unchanged:

| File | SHA-256 |
| --- | --- |
| `PlayRDR2.exe` | `028db16cbd90c7ab07358a7d6dfc981800b6fd4f1583d9b39fe5ea0441d9483d` |
| `RDR2.exe` | `b56c9548f670654a9b73bf25def3cd73af12e269f6e47dba28a34079adaf465e` |

## Post-Recovery Launch Boundary

The live game launch was then tested with the AppID renderer changed from DXMT
to GPTK. Recovery correctly classified the prefix as complete and did not run
an installer.

`PlayRDR2.exe` remained alive for more than four minutes, but `RDR2.exe` was
never created. The current Launcher log ended immediately after:

```text
Creating Steam min mode launch
Steam App Id 1174180
Steam Location Z:\Volumes\990pro\games\steam\steamapps\common\Red Dead Redemption 2
```

The Launcher process exited, while `PlayRDR2.exe` remained idle in the macOS
application event loop with no game or Launcher window and no network socket.
The AppID-scoped GPTK wineserver was stopped cleanly after evidence collection;
the unrelated CrossOver wineserver and Steam process remained running.

This is a separate defect from the interrupted installer. Recovery is accepted;
end-to-end game launch is not. The evidence points to the Rockstar Steam
min-mode handoff: GPTK intentionally cannot load the package's Wine 11
`lsteamclient` bridge, while the Launcher expects a Windows Steam context.
That hypothesis requires implementation and regression proof before it can be
treated as the final root cause.

## CrossOver Launch Control

The CrossOver RDR2 bottle's Steam `gameprocess_log.txt` contains repeated
complete historical launch chains from 2026-01-15 through 2026-01-19:

`PlayRDR2.exe` -> `Launcher.exe` -> `RockstarService.exe` ->
`SocialClubHelper.exe` -> `RDR2.exe`.

Several recorded `RDR2.exe` sessions remained tracked for minutes, including a
session from 18:03:37 to 18:19:46 on 2026-01-19. The command included
`-useSteam -steamAppId=1174180 -scCommerceProvider=4` and D3D12 selection.
This proves that the installed game payload has previously crossed the
Rockstar/Steam boundary in CrossOver.

A fresh CrossOver control was attempted on 2026-06-11 with the RDR2 bottle's
own Windows Steam. It stopped at `WaitingForCredentials` with `steamid=0`, so
no current game process was created. No login tokens or credentials were copied
from another bottle. Therefore the historical process log is valid positive
control evidence, while the 2026-06-11 attempt is recorded only as an
account-state-blocked control, not as a current successful launch.
