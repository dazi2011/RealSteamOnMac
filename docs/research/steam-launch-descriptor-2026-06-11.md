# Steam Launch Descriptor Evidence

Date: 2026-06-11

## Problem

Native Steam can select a launch record whose target is absent or belongs to
the wrong platform. The previous spawn bridge only intercepted an existing PE
file, so these cases failed before the independent runtime could recover:

- Hogwarts Legacy selected `Phoenix-Win64-Test.exe`;
- Aimlabs selected `AimLab.app` despite the installed Windows executable;
- directory-wide EXE guessing could select an unrelated helper.

## Steam Data Sources

`SteamClient.Apps.GetLaunchOptionsForApp(appid)` was inspected in the live
SharedJSContext. It returns UI option metadata such as `nIndex`,
`strDescription`, `eType`, and VR flags. It does not expose executable paths,
working directories, or arguments, so it cannot safely define a launch
command by itself.

The authoritative local executable records are in:

```text
~/Library/Application Support/Steam/appcache/appinfo.vdf
```

The installed file uses magic `0x07564429`, format v41. The implementation was
cross-checked against:

- `ValveResourceFormat/SteamAppInfo`
  commit `ae3bdb44da41c8a05f4ca248d433bd482a0b3bc9`;
- `ValveResourceFormat/ValveKeyValue`
  commit `39db3975a39f017a8de68bbea55ef18a04d816bb`.

Reference URLs:

- https://github.com/ValveResourceFormat/SteamAppInfo
- https://github.com/ValveResourceFormat/ValveKeyValue

## Validation Boundary

The runtime reads appinfo without modifying it and fails closed on:

- unknown magic/version or non-public universe;
- oversized file, record, string table, string, node count, or nesting;
- truncated fields or invalid string-table indexes;
- duplicate KeyValues keys or unsupported node types;
- a per-record binary VDF SHA-1 mismatch;
- AppID mismatch, unsafe paths, missing targets, or non-PE Windows targets.

Only Steam's selected launch entry or a Steam-marked default Windows entry may
be used. Directory-wide executable discovery remains diagnostic-only.

## Live Records

Read-only decoding and binary SHA-1 verification produced:

| AppID | Steam requested | Verified result |
|---|---|---|
| `714010` | entry `1`, `AimLab.app` | entry `0`, `AimLab_tb.exe` |
| `990080` | entry `0`, `Phoenix-Win64-Test.exe` | entry `13`, `HogwartsLegacy.exe` |
| `1118200` | entry `0` | `People Playground.exe` |
| `1174180` | entry `0` | `PlayRDR2.exe` |

Hogwarts entry `13` is the unbranched default. The missing Phoenix entries are
scoped to named beta/playtest branches. The current Hogwarts installation is
still classified `repair-required`, so the runtime correctly stops before
launch until Steam repairs the installation state.

## Spawn Scope

The native hook redirects only allowlisted Windows-only AppIDs when the Steam
target is:

- an existing PE executable;
- a missing `.exe` or `.app` launch target; or
- an `.app` target selected for a managed Windows-only title.

Existing non-PE `.exe` files, native executables, and unmanaged AppIDs keep the
original Steam `posix_spawn` path.

## Verification

```sh
/usr/bin/python3 -m unittest \
  tests.test_steam_launch_descriptor tests.test_runtime_manager -v
sh tests/test_spawn_redirect.sh
sh tests/test_compat_gate_hook.sh
sh tests/test_hook_environment_isolation.sh
sh tests/test_launch_options_probe.sh
```

Result: 51 Python tests and all focused native/shell contracts passed.

Live dry-run plans resolved Aimlabs to `AimLab_tb.exe`, retained RDR2
`PlayRDR2.exe`, and rejected Hogwarts at its incomplete installation-state
gate. Dry runs did not create prefixes or launch games.

## Rollback

The change is code-only until installed. Reinstalling the previous package or
running the repository restore workflow restores the prior native hook and
runtime. The appinfo cache and game directories are never rewritten by this
feature.
