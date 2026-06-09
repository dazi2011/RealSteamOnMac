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
- Dormant native engine:
  `~/Library/Application Support/RealSteamOnMac/libRealSteamNativeEngine.dylib`
- Dormant compatibility-tool package:
  `~/Library/Application Support/RealSteamOnMac/compat-tool`
- Native engine bootstrap allowlist: one entry containing `1118200`
- Browser managed registry: generated from Steam's current owned library

The launcher does not set `STEAM_EXTRA_COMPAT_TOOLS_PATHS`. The valid tool
package remains on disk for later project-owned discovery, but native macOS
Steam is not asked to discover it during startup.

The installed startup guard, dormant engine, launcher, Python patcher, and
browser UI asset were rebuilt from the active working tree and deployed on
2026-06-09 at 10:39 Asia/Shanghai.

The dynamic browser registry implementation is tested in the repository but
has not yet been deployed to the live Steam runtime. The installed browser
assets therefore remain at the preceding cloud-safe baseline until the
post-initialization backend design is ready for a coordinated live test.

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
  for project-owned tools.

The known-build compatibility chunk migrates atomically from the previous
static AppID gate to the dynamic predicate. Unit, browser-context, migration,
installer, launcher, and rollback tests all pass.

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
combinations. A production post-initialization loader is still required; LLDB
is diagnostic evidence, not the shipping mechanism.

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
unimplemented. In the current cloud-safe startup, People Playground remains
installed but reports display status `14`; the compatibility page exists, while
the native tool list is intentionally empty and the Play action is not forced.

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
4. Restore blue download/Play presentation through the cloud-safe registry and
   a post-initialization backend path.
5. Implement the independent versioned compatibility runtime and
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

The rollback is now automated-test verified, but still requires Steam to be
fully stopped and the clean backup path above to remain intact.

Computer Use was attempted for visual acceptance, but macOS ScreenCaptureKit
returned `SCStreamErrorDomain -3811` twice. No coordinate clicks were used.
CDP DOM/state probes supplied the exact UI evidence instead.
