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
- The full Node, Python, and shell test suite passes with the cloud-safe startup
  and dynamic-registry changes.

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
- Startup guard:
  `~/Library/Application Support/RealSteamOnMac/libRealSteamCompatGate.dylib`
- Delayed native engine:
  `~/Library/Application Support/RealSteamOnMac/libRealSteamNativeEngine.dylib`
- Dormant compatibility-tool package:
  `~/Library/Application Support/RealSteamOnMac/compat-tool`
- Native engine bootstrap allowlist: one entry containing `1118200`
- Browser managed registry: generated from Steam's current owned library

The launcher does not set `STEAM_EXTRA_COMPAT_TOOLS_PATHS`. The valid tool
package remains on disk for later project-owned discovery, but native macOS
Steam is not asked to discover it during startup.

The installed startup guard, delayed engine, launcher, Python patcher, and
browser UI asset were rebuilt from the active working tree and cold-deployed on
2026-06-09 at 12:03 Asia/Shanghai. Source/deployed SHA-256 pairs matched, Steam
passed deep signature verification, and the registry token remained mode
`0600`.

## Dynamic Windows-Only Registry

Steam's SharedJSContext provides the authoritative decoded sources:

- `appStore.allApps` for owned/visible overview state;
- `appDetailsStore.RequestAppDetails(appid)` for platform details.

An entry is managed only when it is an owned, visible game, its platform list
contains `windows`, and its platform list does not contain `osx`. The current
library has 49 owned/visible games and 34 qualifying Windows-only entries.
Garry's Mod AppID `4000` is a confirmed dual-platform exclusion.

The browser asset now:

- installs `__REALSTEAMONMAC_IS_MANAGED_APP__` before property pages use it;
- refreshes the registry every five seconds;
- atomically adds newly purchased qualifying games and removes entries that no
  longer qualify;
- restores any project-normalized state before removing an AppID;
- supplies RealSteamOnMac compatibility tools from project configuration;
- persists per-AppID selection without calling Steam's native tool registration
  for project-owned tools;
- subscribes directly to each accepted AppID's native detail stream and
  publishes callbacks into the shared details store;
- retries only stale status-`14` details at a bounded one-second interval and
  unregisters removed games.

The known-build compatibility chunk migrates atomically from the previous
static AppID gate to the dynamic predicate. Unit, browser-context, migration,
installer, launcher, and rollback tests all pass.

### Authenticated Native Registry Bridge

The repository now also synchronizes that browser registry into the delayed
native engine:

- the installer creates
  `~/Library/Application Support/RealSteamOnMac/registry-token` with mode
  `0600`;
- the same validated token and fixed loopback endpoint are written into the
  generated local Steam UI configuration, also with mode `0600`;
- after delayed activation, the engine listens only on
  `127.0.0.1:57344`;
- the browser sends a sorted comma-separated AppID list with `text/plain`
  `POST` and retries unchanged lists after connection failures;
- the native endpoint accepts at most 16 KiB and 256 unique positive AppIDs;
- invalid tokens return `403`, malformed bodies return `400`, and neither can
  change the active registry;
- an accepted update atomically replaces the native allowlist and requests a
  live install-gate trampoline rebuild;
- an accepted empty registry restores Steam's original install-gate
  instruction.

The native HTTP harness dynamically loads the production engine and verifies
authorized add/remove behavior, unauthorized rejection, malformed-payload
rejection, and direct managed-AppID queries. The UI integration harness also
proves that an initial connection failure does not cache the payload and that
the next five-second scan retries it.

This bridge is installed persistently in `/Applications/Steam.app`. A cold
start synchronized all 34 current candidates with zero invalid-platform details
or overviews. Garry's Mod remained excluded at native status `31`.

### Live Phase 3 Acceptance

The final repository matrix passed with 51 Node tests, 10 Python tests, and all
20 shell contracts.

Live checks after the cold deployment proved:

- the delayed engine opened `127.0.0.1:57344`;
- the install gate rebuilt from the bootstrap AppID to all 34 managed AppIDs;
- the data scan patched the remaining 33 app objects;
- 24 uninstalled games expose Steam's native blue `安装` state;
- seven locally installed games expose the appropriate native launch state;
- active update states remain untouched;
- For Honor AppID `304390` visibly exposes an enabled native `安装` action at
  status `9/9`;
- People Playground visibly exposes the green native `开始游戏` action at
  status `11/11`;
- `cloud_enabled=true`, `show_screenshot_manager=false`, and CloudStorage
  remains available.

The earlier SteamUI platform-getter trampoline was removed. It was redundant
with the allowlist-scoped data scan and native detail subscriptions, failed
near-branch allocation under one ASLR layout, and retried every worker tick.
The new cold-run log begins at line `4774` and contains no `steamui:` patch or
allocation error.

## Post-Initialization Native Activation Experiment

LLDB was attached to the already initialized Steam PID `97776`. The dormant
engine was loaded with `process load`, its exported
`realsteamonmac_start_native_worker()` function was called, and LLDB detached.
This changed no persistent Steam file.

Verified afterward:

- Steam remained running;
- the engine was mapped in the process;
- the strict one-AppID install-gate trampoline was installed;
- global `cloud_enabled=true` and screenshot setting fields remained present;
- People Playground backend details transitioned to status `11`;
- its cached overview remained status `14`.

The result proves late native activation is cloud-safe on the current build.
It also proves the browser bridge must map backend-ready installed entries to
status `11`, just as uninstalled backend-ready entries map to status `9`.
Automated tests now cover both states and reject mismatched local-content/state
combinations. LLDB was diagnostic evidence only; the production delayed loader
described below has replaced it.

The production replacement for the debugger path has now also passed a live
A/B test. The launcher supplies a `bootstrap` stage, guard path, engine path,
and 30-second delay. Steam's first runtime stage forks the final process, so the
guard preserves injection through that stage. The final `steam_osx` retains a
one-shot dispatch timer; each Steam Helper exec loads the guard only long
enough to clear every injection/activation variable and refuses engine
activation because it is not the runtime process.

After 30 seconds the final runtime loaded the engine automatically and started
the worker. Verified at that point:

- both guard and engine were mapped;
- the install gate and data reconciliation worker were active;
- People Playground details were status `11` with local content;
- global Cloud fields remained present and enabled;
- no Helper process retained DYLD, compatibility-tool, or RealSteamOnMac
  activation variables.

The loader no longer requires LLDB, `task_for_pid`, `get-task-allow`, or an
administrator prompt. Browser-to-engine synchronization is now persistently
deployed and live-verified.

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
unimplemented. People Playground now reports display status `11` and exposes
Steam's native Play action, but the selected compatibility tool is still a
logging stub, so clicking Play cannot yet create a prefix or launch the Windows
executable.

## Cloud Root Cause And Fix

The blank global Cloud page and false “Steam Cloud is disabled globally”
message were client-side regressions, not an account restriction or damaged
remote saves.

Read-only CDP probes established:

- Steam UI still defines `cloud_enabled` and `show_screenshot_manager`;
- the broken startup omitted both fields from `m_ClientSettings`;
- the settings component renders nothing when those fields are absent;
- CloudStorage and roaming configuration remained available.

Controlled A/B testing found two independent startup hazards:

1. Inheriting `DYLD_INSERT_LIBRARIES` into Steam Helper breaks the
   websocket/settings bridge.
2. Setting `STEAM_EXTRA_COMPAT_TOOLS_PATHS` to a directory containing a valid
   compatibility tool makes macOS Steam omit the Cloud fields. The same
   variable pointing at an empty directory does not reproduce the failure.

The deployed correction is:

- inject only a minimal environment guard during startup;
- clear the injection variables before Helper creation;
- do not register native compatibility tools through
  `STEAM_EXTRA_COMPAT_TOOLS_PATHS`;
- keep the full patch engine constructor-free and dormant.

Verified after deployment:

- `cloud_enabled=true`;
- `show_screenshot_manager=false`;
- the global Cloud page has two rendered setting groups;
- Garry's Mod shows its normal Steam Cloud checkbox and quota;
- People Playground shows Steam Cloud with a `953.67 MB` quota and retains its
  `兼容性` page;
- the 10:39 startup produced no new `pending platform change` or
  `Sync Failed, no user set`;
- roaming config reported `PerformSyncCloud - all sync'd up` at 10:40:23.

Other Windows-only titles still report unresolved `WinAppDataLocal` cloud
roots. That is expected until the Proton-compatible PFX path exists.

## Installer And Rollback Audit

The installer is guarded against a running Steam process, unknown bootstrap
modifications, and unknown runtime signing state. It applies the known Steam UI
patch, installs the launcher/hook/tool, and signs the modified executables.

One gap remains before the runtime package manager is complete:

1. Compatibility-tool replacement uses `rm -rf` followed by `cp`, which is not
   transactional and cannot preserve multiple installed runtime versions.

The rollback correctness bug was fixed in the first 2026-06-09 implementation
step. The rollback now detects both guarded Steam UI backup files and requires
the installed patcher to restore `index.html`, the compatibility chunk, and
project assets before it moves the support directory or replaces application
files. Incomplete backups or a missing patcher make rollback fail closed.

The focused regression test installs the real UI patch in a temporary runtime,
runs the rollback, and verifies exact original resources and asset removal. The
complete repository suite passes with the fix.

Cloud-fix deployment snapshot:

```text
/Users/wudazi/RealSteamOnMac-Backups/cloud-fix-20260609T103853
```

Its `SHA256SUMS` covers the prior support directory, launcher, Info.plist,
bootstrap, and runtime executable. The full clean backup remains the
authoritative complete rollback source.

## Next Execution Order

1. Done: Steam UI restoration is covered by the rollback regression test.
2. Done: Cloud root cause isolated and the guarded startup deployed.
3. Done: generated browser registry from Steam ownership and platform details.
4. Done and deployed: authenticated hot synchronization into the delayed
   native backend.
5. Done: verified blue download/Play presentation for all current candidates,
   native-title exclusions, and Cloud health.
6. In progress: implement the independent versioned compatibility runtime and
   Proton-compatible prefix path.

## Phase 4 Runtime Foundation Update

The independent runtime inputs are now fixed and checksum-verified:

- Gcenx game-porting-toolkit Wine `3.0-3`;
- Apple GPTK 3 D3DMetal files copied only from the user's official local DMG;
- DXMT `v0.80`;
- Wine Staging `11.10`;
- DXVK-macOS `v1.10.3-20230507` builtin.

The Gcenx package includes `wine64`, `wineserver`, WineD3D, `winevulkan`, and
MoltenVK. CrossOver is not required by the planned runtime.

The runtime design uses immutable packages under
`~/Library/Application Support/RealSteamOnMac/runtimes/packages`, an atomic
`current` symlink, and exact Proton-compatible prefixes under each Steam
library's `steamapps/compatdata/<appid>/pfx`.

A live Play probe at 12:16 local time established the next implementation
boundary. Steam retained the mapping from AppID `1118200` to
`realsteamonmac-experimental` and advanced through Cloud, stats, controller,
license, and launch-delay tasks. It then failed at `CreatingProcess` with
`AppError_46` before invoking the compatibility tool's logging stub.

Therefore the current UI compatibility-tool bridge is presentation-only. The
remaining launch work must either refresh the native tool list after Steam has
initialized, or add an allowlist-scoped dispatcher that invokes the wrapper.
The startup environment variable path remains prohibited because prior A/B
testing proved that a valid `STEAM_EXTRA_COMPAT_TOOLS_PATHS` removes Cloud
settings on this Steam build.

Detailed evidence and package acceptance gates are recorded in
`docs/research/independent-runtime-foundation-2026-06-09.md`.

The runtime foundation is now implemented and installed. The active immutable
package is:

```text
~/Library/Application Support/RealSteamOnMac/runtimes/packages/
  gptk3.0-3-wine11.10-dxmt0.80-dxvkmacos1.10.3
```

It contains separate GPTK, DXMT, DXVK-macOS, and WineD3D roots. Upstream DXVK
2.7.1 is not exposed because current Gcenx documentation states that MoltenVK
lacks extensions it requires; the macOS-specific builtin release is used
instead.

All package hashes pass, all four Wine entrypoints execute independently of
CrossOver, and a People Playground dry-run resolves the exact
`steamapps/compatdata/1118200/pfx` path without creating it.

The native engine now implements the selected launch-dispatch solution. It
replaces only steamclient's resolved `posix_spawn` pointer for the exact known
build and redirects only live-allowlisted PE executables. It preserves Steam's
spawn actions, attributes, environment, and game arguments, then starts the
project runtime through `/usr/bin/python3`. Unmanaged AppIDs and native
executables retain the original system call. A dynamic engine harness verifies
that decision boundary. The complete pre-deployment matrix passes with 51 Node
tests, 18 Python tests, and all 22 shell contracts. Live Steam deployment is
the next acceptance step.

## Recovery And Rollback

Claude prototype recovery branch:

```sh
git show fe6d20d
```

Current clean Steam backup:

```text
/Users/wudazi/RealSteamOnMac-Backups/steam-1780705203-20260607T083704Z
```

The rollback is now automated-test verified, but still requires Steam to be
fully stopped and the clean backup path above to remain intact.

Computer Use was attempted for visual acceptance, but macOS ScreenCaptureKit
returned `SCStreamErrorDomain -3811` twice. No coordinate clicks were used.
CDP DOM/state probes supplied the exact UI evidence instead.
