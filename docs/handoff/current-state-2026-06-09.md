# RealSteamOnMac Current State

Date: 2026-06-09

## Takeover Result

Claude's interrupted work was recovered without losing committed or uncommitted
changes.

- The active branch was fast-forwarded from `a7e508f` to the remote verified
  download commit `be55b6a`.
- Four later uncommitted prototype files were preserved exactly in commit
  `fe6d20d` on branch `codex/claude-recovery-20260609`.
- The recovery prototype is intentionally not merged into the active branch.
  It globally NOPs the install platform veto, treats every `InvalidPlatform`
  app overview as a target, and references an unimplemented browser predicate.
- The full Node, Python, and shell test suite passes at active head `be55b6a`.

Persistent working context is maintained in:

- `task_plan.md`
- `findings.md`
- `progress.md`

## Verified Download State

People Playground AppID `1118200` is genuinely installed through native macOS
Steam at:

```text
/Volumes/990pro/games/mac/steamapps/common/People Playground
```

The authoritative manifest reports:

```text
StateFlags      4
UpdateResult    0
SizeOnDisk      455945761
InstalledDepot  1118201
Manifest        9210503819883706733
```

`content_log.txt` records the Windows depot download, commit, and
`Fully Installed` transition. This is not a cosmetic button-only result.

## Current Installed Architecture

- Steam entry executable:
  `/Applications/Steam.app/Contents/MacOS/realsteamonmac_launcher`
- Steam runtime build: `1780705203`
- Support root:
  `~/Library/Application Support/RealSteamOnMac`
- Compatibility tool:
  `~/Library/Application Support/Steam/compatibilitytools.d/realsteamonmac-experimental`
- Current target registry: one-entry allowlist containing `1118200`

The installed Python patcher and browser UI asset are byte-identical to the
active repository source. The deployed native hook logs successful
allowlist-gated installation-gate redirection.

## What Is Not Implemented

The installed compatibility tool's `run` script only logs Steam's verb,
arguments, AppID, install path, and compatibility-data path, then exits `0`.
It does not:

- create `steamapps/compatdata/<appid>/pfx`;
- invoke Wine, GPTK, DXMT, DXVK, or WineD3D;
- start the game executable;
- preserve a Steamworks process relationship;
- expose MSync, high-resolution, Metal HUD, MetalFX, dependency installation,
  or run-command controls.

No `compatdata/1118200/pfx` exists. The independent launch path is therefore
unimplemented, even though Steam's Play button is visible.

## Cloud Investigation State

The global Steam Cloud settings page renders a blank content pane. Per-game UI
reports that Steam Cloud is disabled globally, and People Playground can remain
at checking cloud status.

Current evidence:

- Steam's `CloudStorage` resumed successfully in earlier sessions.
- `sharedconfig.vdf` is present, readable, and syntactically valid.
- Steam loaded that roaming write-aside store successfully after 20:59 on
  2026-06-08.
- At the time of the blank-page screenshot, `webhelper_js.txt` repeatedly
  logged `waiting for roaming storage to initialize`.
- The active Steam process was not launched with `-cef-enable-debugging`, so
  live settings-page JS/backend inspection has not yet been captured.

There is no evidence yet that RealSteamOnMac triggered a server-side account
restriction or intentionally disabled cloud sync. Do not change cloud saves or
remote storage until the client-side initialization failure is isolated.

## Installer And Rollback Audit

The installer is guarded against a running Steam process, unknown bootstrap
modifications, and unknown runtime signing state. It applies the known Steam UI
patch, installs the launcher/hook/tool, and signs the modified executables.

Two gaps must be fixed before the next real-machine installer run:

1. The rollback script restores `Steam.app`, the runtime executable, and
   `steamclient.dylib`, but does not restore patched Steam UI resources. Moving
   the support directory away can leave `index.html` referencing missing
   project scripts.
2. Compatibility-tool replacement uses `rm -rf` followed by `cp`, which is not
   transactional and cannot preserve multiple installed runtime versions.

The first gap is a rollback correctness bug. The second will be replaced by the
versioned runtime package manager.

## Next Execution Order

1. Add a failing rollback test for Steam UI restoration and fix the rollback.
2. Relaunch Steam through the existing launcher with CEF debugging enabled.
3. Reproduce the Cloud page failure and capture page exceptions, account
   settings, roaming-store state, and per-game cloud state through read-only
   CDP probes.
4. Fix and verify Cloud behavior before broadening the native patch.
5. Implement a generated Windows-only AppID registry from Steam platform,
   launch, and depot metadata; do not use `InvalidPlatform` alone.
6. Implement the independent versioned compatibility runtime and
   Proton-compatible prefix path.

## Recovery And Rollback

Claude prototype recovery branch:

```sh
git show fe6d20d
```

Current clean Steam backup:

```text
/Users/wudazi/RealSteamOnMac-Backups/steam-1780705203-20260607T083704Z
```

Do not run the current rollback script on the real installation until the
Steam UI restoration gap above is fixed and tested.
