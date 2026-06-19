# Task Plan: RealSteamOnMac Independent Steam Play

## Goal

Turn native macOS Steam into a self-contained frontend that can discover,
download, configure, and launch owned Windows-only games through independently
managed GPTK, DXMT, DXVK, WineD3D, and Wine compatibility tools without
requiring CrossOver.

## Current Phase

Phase 8: 2026-06-11 field regression remediation and verified release

## Phases

### Phase 1: Takeover Audit And Recovery

- [x] Inspect repository history, branches, worktrees, and handoff documents.
- [x] Record the two supplied screenshots as durable findings.
- [x] Inspect Claude's final remote commit and all worktree-local changes.
- [x] Preserve Claude's uncommitted prototype on a separate recovery branch.
- [x] Fast-forward the active branch only after proving no work will be lost.
- [x] Run the complete repository test suite in Claude's final dirty worktree.
- [x] Run the complete repository test suite at the recovered active head.
- [x] Audit README, handoff, design, plans, installer, and rollback coverage.
- [x] Write and push a takeover handoff with verified and missing behavior.
- **Status:** complete

### Phase 2: Live Steam Health And Cloud Root Cause

- [x] Fix and test complete Steam UI resource restoration in rollback.
- [x] Capture Steam process, build, launcher, hook, config, and log state.
- [x] Reproduce the blank global Cloud page and per-game cloud-status behavior.
- [x] Trace console errors and configuration reads without changing cloud data.
- [x] Add a failing regression test and deterministic A/B diagnostic.
- [x] Split startup injection into a minimal environment guard and dormant
      native engine.
- [x] Deploy the guarded startup and verify native macOS games and People
      Playground.
- [x] Document, commit, and push the isolated cloud fix.
- **Status:** complete

### Phase 3: Dynamic Windows-Only Library Enablement

- [x] Specify an exact Windows-only eligibility rule and exclusions.
- [x] Add tests for dynamic discovery, additions, removals, and hot reload.
- [x] Replace the single-game fixture with a generated runtime registry.
- [x] Synchronize the browser registry into the delayed native engine through
      an authenticated loopback-only endpoint.
- [x] Keep native and dual-platform macOS titles on their original path in
      policy, browser, and native-registry tests.
- [x] Enable native blue download actions and compatibility pages dynamically.
- [x] Update the installer, README, and handoff for registry synchronization.
- [x] Install and verify against the current Steam library.
- [x] Commit and push the verified phase.
- **Status:** complete

### Phase 4: Independent Compatibility Runtime Foundation

- [x] Inventory locally available GPTK and installed Wine/CrossOver components.
- [x] Research current upstream DXMT, DXVK, Wine, GPTK requirements and licenses.
- [x] Define the independent package and Proton-compatible per-game layout.
- [x] Implement a runtime registry with versioned, transactional packages.
- [x] Create Proton-compatible `steamapps/compatdata/<appid>/pfx` prefixes.
- [x] Implement Steam-to-wrapper launch argument and environment propagation.
- [x] Build and validate a real Proton `lsteamclient` bridge for macOS Steam.
- [x] Pass DXVK Steamworks, normal-exit, and AutoCloud live acceptance.
- [x] Add smoke-test fixtures, structured logs, and failure diagnostics.
- [x] Document the independent package, GPTK window, and DXVK Steamworks
      milestones.
- **Status:** complete for the foundation and DXVK path

### Phase 5: Per-Game Compatibility Controls

- [x] Expose installed compatibility tools in Steam's per-game dropdown.
- [x] Add persistent per-AppID controls for MSync, high-resolution mode,
      Metal HUD, and supported MetalFX/DLSS translation settings.
- [x] Add a run-command workflow scoped to the selected game's prefix.
- [x] Add dependency search/install with manifests, checksums, and private receipts.
- [x] Ensure settings survive Steam and machine restarts.
- [x] Test renderer selection and control persistence against the actual
      generated DXVK and DXMT environments.
- [x] Document, commit, and push the renderer/control group.
- **Status:** renderer, runtime controls, run-command, and checksum-pinned
  dependency installation are accepted in live Steam

### Phase 6: End-To-End Game Launch

- [x] Select DXVK-macOS as the current known-safe Steamworks runtime for People
      Playground.
- [x] Launch through Steam's original Play action.
- [x] Verify prefix creation, process tree, window creation, Steamworks, and
      normal exit.
- [x] Verify GPTK window creation and DXVK full runtime acceptance.
- [x] Diagnose and fix GPTK regression caused by an incompatible managed
      Steamworks bridge remaining in the shared PFX.
- [x] Verify cloud status no longer blocks launch and AutoCloud runs on exit.
- [x] Capture logs, screenshots, bridge hashes, and rollback evidence.
- [x] Verify live input initialization and CoreAudio backend startup from the
      game/runtime logs.
- [x] Verify DXMT with a compatible patched Wine build.
- [x] Deploy the DXMT package into the existing Steam installation and verify
      native launch, normal exit, process cleanup, and AutoCloud.
- [x] Update all handoff and installation documents.
- [x] Run the complete automated and live verification matrix.
- [x] Commit and push the final verified state.
- **Status:** complete

### Phase 7: Steam-Native Compatibility UX And Public Release

- [x] Remove the weak cross-window control mount that can cover library pages.
- [x] Use Steam's standard `compatibilitytools.d` directory as the canonical
      side-by-side compatibility tool repository.
- [x] Scan validated tool metadata without enabling the cloud-breaking native
      startup discovery path.
- [x] Persist the selected tool identity and immutable runtime package per game.
- [x] Replace the branded dashboard with compact Steam-style compatibility
      rows and secondary action dialogs.
- [x] Add capability-aware DXMT MetalFX support and version/runtime validation.
- [x] Default new PFX containers to Windows 10 and retain real MSync semantics.
- [x] Expand reviewed dependency metadata without copying proprietary
      CrossOver payloads.
- [x] Build transactional install, uninstall, and update PKG workflows.
- [x] Rewrite bilingual product documentation and move project history out of
      the README.
- [ ] Complete clean install, live Steam, uninstall, rollback, and release
      verification before publication.
- [ ] Publish a verified GitHub release and make the repository public.
- **Status:** in progress

### Phase 8: Field Regression Remediation And Verified Release

- [ ] Reproduce and map every 2026-06-11 field report to a concrete code path,
      Steam state transition, or external dependency.
- [x] Replace the simulated force-tool checkbox/dropdown with Steam-owned
      controls and populate Steam's existing selector without overlays.
- [x] Re-expose runtime options, Run Command, dependencies, and container
      actions through Steam-owned controls without reviving the legacy panel.
- [x] Discover side-by-side user-supplied GPTK, DXMT, DXVK, and Wine trees in
      standard CrossOver-like layouts under `compatibilitytools.d`.
- [x] Derive renderer capabilities from the discovered payload and disable
      unsupported DXR, MetalFX/DLSS, MSync, and related settings.
- [ ] Repair stable/beta Steam discovery, language-independent actions,
      restart readiness, Windows-only labeling, download reconciliation, and
      stale installed-manifest handling.
- [x] Drain a stale native `Steam.AppBundle/.../ipcserver` before restart
      without matching CrossOver's Windows Steam processes.
- [ ] Repair Windows executable resolution, Rockstar bootstrap recovery,
      Windows-only `.exe` launch, and avoid false `.app` target selection.
- [ ] Allow Steam's add-non-Steam-game flow to accept `.exe` files while
      preserving native `.app` behavior and applying compatibility only to PE
      executables.
  - [x] Extend Steam's existing guarded macOS picker filter to keep `.app` and
        add `.exe`, with migration and restore coverage.
  - [ ] Add typed shortcut discovery, canonical PE target binding, an external
        non-Steam prefix, and shortcut-only spawn redirection.
- [ ] Make Run Command behave like Windows Run, fix EXE selection persistence,
      and open the selected prefix drive in Finder.
- [x] Merge Windows component installation into Install Application To
      Container and provide a reviewed, checksum-pinned dependency catalog.
- [x] Correct Game Controllers to Wine `joy.cpl`, make it readable with a
      temporary prefix DPI override, and leave Steam Input unmodified.
- [x] Restore a clear bottom-of-page order for Install Windows Components,
      Container Actions, and Run Command while keeping every row implemented
      with Steam-owned controls and without reintroducing custom panels.
- [ ] Study CrossOver Preview statically and dynamically for container,
      command, registry, dependency, and launch behavior without making
      RealSteamOnMac depend on CrossOver at runtime.
- [ ] Verify update installation over an existing installation using
      `update.pkg`.
- [ ] Run the automated matrix, installed-library game matrix, representative
      DLSS tests, CrossOver control tests, performance sampling, rollback, and
      clean/update package acceptance.
- [ ] Update bilingual README and research/handoff evidence, build signed
      release artifacts, publish the release, and confirm remote hashes.
- **Status:** in progress
- **Run/Container checkpoint:** live jobs for uninstalled AppID `654310`
  proved that the action endpoint and hook were healthy but the original
  launch-context resolver rejected utility commands before dispatch. Actions
  now use a separate existing-container resolver: file selection and
  `inspect-state` remain read-only, installed games without a PFX keep their
  native action sections visible but disabled, and run/container/dependency
  jobs fail closed instead of creating a prefix. Automated coverage passes,
  but installed Steam acceptance is still required before this item can be
  checked again.
- **Native-controls checkpoint:** the compatibility page renders all project
  actions through Steam's existing React control constructors. The section
  order is complete, but the prior live-action acceptance claim was invalid:
  seven real jobs for AppID `654310` all failed before entering their command
  handlers. The corrected runtime and EXE picker remain pending installed
  acceptance; replacement UI is still prohibited.
- **Native-registration checkpoint:** current beta arm64 Steam constructs its
  local-tool loader only once during `CCompatManager` startup. Forcing the
  manager-wide Linux capability byte or supplying a valid local-tool path both
  reproducibly stall build `1780965181`; the experimental guard patch was
  removed. The active target is now the valid-manifest completion/dispatch
  path, and acceptance still requires Steam's own selector plus healthy Cloud.
- **Restart-readiness checkpoint:** the signed launcher was deployed over the
  existing Steam installation and removed live orphan PID `89863` in dry-run
  acceptance. The exact-path log reported a zero-millisecond drain while
  CrossOver Preview PIDs `19863`, `19885`, and `73736` remained alive. This
  closes the deterministic stale-IPC cause of delayed Play/Download controls;
  the other items in the combined restart/download task remain open.
- **Self-update restart checkpoint:** Steam beta `1781212412` exposed a second
  stale-IPC form: the updater renamed the running image to `ipcserver.old` and
  then deleted that vnode, causing `proc_pidpath` to return zero. The launcher
  now falls back to the exact canonical `KERN_PROCARGS2` executable only in
  that case. Live PID `32189` drained in zero milliseconds while the same
  CrossOver processes remained alive.
- **Build 1781212412 profile checkpoint:** the new beta is now represented by
  exact arm64 SteamClient and SteamUI UUID profiles. Static verification locks
  the compatibility gate at `0x00A03EF8`, install gate at `0x006279D8`,
  SteamUI getter at `0x005EDF44`, and `_posix_spawn` lazy pointer at
  `0x018FD500`. Patch, hook, spawn, installer, release-manifest, and injection
  contracts pass. Installed runtime and native-dropdown acceptance remain
  mandatory before this build is release-ready.
- **Update package checkpoint:** the repository still builds only Install and
  Uninstall PKGs. The design's `RealSteamOnMac-Update.pkg` is not implemented,
  and the current top-level installer intentionally rejects an existing state
  whose recorded Steam build differs after Valve self-update. This remains an
  explicit release blocker rather than being treated as covered by direct
  injection deployment.
- **Concurrent restart checkpoint:** a second launcher can start a new native
  `ipcserver` while the first launcher is still draining the stale one. The
  drain now follows only the originally matched PID and treats its zombie state
  as exited, so the replacement process is neither terminated nor mistaken for
  the stale target. The delayed replacement fixture passes while the fake
  CrossOver process remains alive.
- **Native section-order checkpoint:** the project controls now use Valve's
  `DialogSettingsSection` export directly, without nesting another
  `DialogBody`. Their exact order is Compatibility Options, Install Windows
  Components, Container Actions, Run Command, and Recent Activity. The first
  three requested action areas therefore remain Steam-owned controls and
  appear in the requested bottom-of-page order.
- **Compatibility preference checkpoint:** disabling Steam's force-tool
  control no longer clears MSync, Retina, Metal HUD, MetalFX, DXR, or AVX
  preferences. Backend configuration loads cannot silently re-enable the
  force-tool control, and temporary registry removal preserves per-AppID
  snapshots for later rediscovery. The first section label is now exactly
  `兼容性选项`.
- **Component-recipe checkpoint:** the runtime now accepts only three bounded
  installer strategies (`exe`, `msi`, and the fixed DirectX redistributable
  flow), validates prerequisite graphs, prefix-relative files, and restricted
  Wine registry-key or exact file-hash postconditions, and writes receipts
  only after every required check passes. The production catalog now contains
  14 pinned official recipes spanning current and legacy Visual C++, .NET 4.8,
  DirectX June 2010, XNA 4.0 Refresh, and PhysX Legacy. All 67 runtime-manager
  tests pass. Live acceptance covers EXE, MSI, DirectX extraction, prerequisite
  ordering, registry verification, exact file hashes, and private receipts;
  the active game prefix was used for low-risk VC/PhysX/DirectX tests and an
  APFS-cloned prefix isolated the .NET/XNA test.
- **Native dependency UI checkpoint:** the deployed SteamUI config and native
  properties subtree now expose all 14 reviewed recipes through Steam's
  existing `DialogDropDown`. Live People Playground inspection found three
  native dropdowns, seven native checkboxes, zero legacy project panels, zero
  project modal layers, and no native render error. The read-only acceptance
  probe now derives dropdown options from Steam's React props instead of
  looking for the removed handcrafted panel.
- **Steam channel checkpoint:** the one-click installer no longer assumes a
  public-beta manifest name. It reads Steam's bounded `package/beta` channel,
  selects the active `signed-2` manifest only when its matching `.installed`
  marker exists, records `stable` or the beta channel in installation state,
  and refuses a channel change against a clean backup. Stable and public-beta
  fixtures pass, including a newer downloaded but inactive manifest.
- **Download/repair diagnostics checkpoint:** native repair dispatch now
  fetches the backend `inspect-state` job before choosing Steam's install,
  resume, or verify APIs. Missing manifests, missing install directories,
  empty content shells, zero installed depots, invalid manifests, and blocked
  states cannot remain normalized as ReadyToLaunch; only the verified
  files-missing repair state remains launchable as a warning. Automated
  coverage passes, but Black Myth's fresh native install/download path still
  needs live acceptance.
- **Startup allowlist seed checkpoint:** the native hook now persists each
  successful authenticated dynamic registry to a private
  `managed-appids-cache.txt` seed and merges it with the static bootstrap
  allowlist on the next Steam start. This should let early Aimlabs/Hogwarts
  Play clicks reach the missing-target spawn redirect before the browser
  registry scan completes. Automated hook and spawn contracts pass; live
  launch acceptance remains required.
- **Restart/language checkpoint:** after authenticated native registry sync,
  the browser policy now derives Steam's native ready-to-launch or
  ready-to-install state from installed, local-content, and positive-size
  fields when the details cache remains platform-invalid. Live acceptance
  normalized all 34 managed Windows-only games, removed every invalid-platform
  overview, and produced clickable native actions in Simplified Chinese and
  English. Steam was restored to Simplified Chinese and retained it across a
  later launch without a language override. Stale depot-manifest repair remains
  open and is not covered by this checkpoint.
- **Restart race checkpoint:** `StartShutdown(true)` proved that the main
  process can exit before its old CEF helpers and SharedJSContext disappear.
  Relaunching in that interval produces a false-ready UI followed by broken
  IPC and process exit. The bootstrap now waits up to 15 seconds for orphaned
  `Steam Helper` processes when no `steam_osx` remains, while preserving
  normal forwarding to an already-running Steam instance.
- **Native mapping checkpoint:** compatibility selections are now committed
  through Steam's original `SpecifyCompatTool` only after the authenticated
  native registry accepts the managed AppID set. Successful writes are cached
  to prevent one-second rewrites; rejected writes leave the prior selection
  and runtime config untouched. Live `config.vdf` contains all 34 mappings,
  but Steam has not yet registered the four project tools in
  `CCompatManager`, so mapping persistence and native tool availability remain
  separate acceptance gates.
- **Zero-depot recovery checkpoint:** Black Myth: Wukong has two stale
  `StateFlags=4` manifests with `SizeOnDisk=0`, no `InstalledDepots`, and no
  install directory. Native install-wizard inspection and two guarded
  verify-then-pause runs produced no depot target and mounted zero depots.
  The Windows-library record has now been removed through Steam's native
  uninstall lifecycle after backing up and hash-verifying the four save files
  that occupied its install directory. Steam preserved those saves and logged
  a clean uninstall. After restart, the duplicate macOS-library record was
  removed through the same guarded native lifecycle. Both manifests are now
  absent and save hashes remain unchanged. A fresh install no longer
  false-completes, but fails explicitly with native app error 29
  (`InvalidPlatform`); native compatibility-tool registration is now the
  remaining download gate.
- **Same-build refresh checkpoint:** Valve replaced `steamclient.dylib` and
  `steamui.dylib` on June 11 while retaining build `1780965181`. The current
  hook rejected both refreshed UUIDs, so the current process never installed
  the native compatibility, install, data-object, or launch redirections.
  Structurally verified refreshed profiles have been added; deployment and a
  repeated native install-plan test are the next gate before attributing any
  remaining error 29 to compatibility-tool registration.
- **Same-build refresh acceptance:** the tested engine was deployed with a
  rollback copy, and the current Steam session installed the refreshed
  allowlist-scoped gate, data reconciliation, and spawn redirect. Black Myth
  moved from error 29 to install state `7` with error `0`. The bounded probe
  cancelled without a manifest or download, but the plan still contains zero
  bytes; post-initialization native tool registration and Windows-depot
  selection are now the next implementation target.
- **Native compatibility interface checkpoint:** the exact current
  `steamclient.dylib` factory exposes
  `CLIENTENGINE_INTERFACE_VERSION005`, and RTTI proves engine slot 72 returns
  `IClientCompatMap`. The 19-entry serialized map is now version-resolved.
  SharedJSContext tool queries do not traverse its local stub, so the next
  gate is the server-side `CCompatManager` cache/manifest refresh path rather
  than another browser-layer list merge.
- **Current checkpoint:** verified Steam launch descriptors, managed
  missing-target redirection, and guarded Rockstar recovery have passed live
  acceptance. RDR2 now reaches Rockstar Steam min-mode but not `RDR2.exe`.
  A GPTK/Wine 7.7-specific Proton 7 `lsteamclient` bridge has now passed a
  real `SteamClient020` interface smoke test against native macOS Steam. Its
  pinned cold-build script, renderer-specific runtime schema, immutable
  package installer, top-level installer, and release-PKG propagation now
  pass. The new live package was built and activated, and its activation
  exposed and then corrected a missing Python-module deployment fault. Live
  GPTK bridge installation passes, but RDR2 still stops at Rockstar's Steam
  min-mode handoff; the remaining Windows-Steam ownership path is unresolved.

## Architecture Decision

Use a hybrid native-frontend architecture:

1. Keep native macOS Steam as the only library/download/properties frontend.
2. Keep Steam patches narrowly version-gated and limited to eligibility,
   compatibility-page registration, and launch dispatch.
3. Put each selectable compatibility implementation in a versioned wrapper
   package under `compatibilitytools.d`.
4. Store per-game state and a Proton-compatible prefix under
   `steamapps/compatdata/<appid>/`.
5. Let an independent runtime manager own package validation, prefix lifecycle,
   dependency installation, settings, logs, and hot reload.

This preserves the requested Steam UX while avoiding a hard dependency on
CrossOver and reducing the amount of Steam binary/UI code that must be patched.

## Safety And Commit Gates

- Never modify cloud saves or remote storage while diagnosing cloud UI/state.
- Never delete an existing prefix, game depot, Steam backup, or runtime package.
- Back up every real-machine file before replacement and record its hash.
- Fail closed on unknown Steam UUIDs, instruction bytes, resource hashes, or
  compatibility package manifests.
- Each phase must have automated tests, a live verification note, rollback
  instructions, a focused commit, and a confirmed remote push.
- Treat each coherent file-edit batch as a small step: test it, commit it, and
  push it before starting the next batch.
- Never report a game, DLSS path, package update, or CrossOver comparison as
  verified unless direct logs/process/window/output evidence was captured.

## Key Questions

1. Did Claude's final commit fully download the Windows depot and update every
   handoff/install document?
2. Which post-initialization activation mechanism can expose native install
   behavior without constructor threads or native macOS tool discovery?
3. Which Steam-owned data source can identify owned Windows-only games without
   globally changing platform semantics?
4. Which current macOS-compatible Wine/GPTK combinations can launch 32-bit and
   64-bit Windows games on this machine?
5. What minimal launch-dispatch patch is needed for Steam to invoke wrappers
   with the same AppID and command contract used by Steam Play on Linux?
6. Which native observable is changing once per second and causing the
   compatibility checkbox to oscillate between enabled and disabled?
7. Which Steam-owned controller dialog sizing and typography rules can be
   adjusted without mounting a replacement or overlay UI?

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Use a generated registry instead of a global platform wildcard | A wildcard can select wrong depots for native/dual-platform games and broadens binary-hook risk. |
| Preserve `steamapps/compatdata/<appid>/pfx` | It matches the user's requested Proton layout and enables predictable per-game tooling. |
| Use thin compatibility wrappers | Multiple runtime versions can coexist and wrappers can translate Steam arguments into backend-specific commands. |
| Diagnose cloud before expanding patches | Cloud behavior affects native titles too and may indicate a global UI or configuration regression. |
| Treat visible UI and backend behavior as separate acceptance criteria | A blue button or dropdown is not proof that install or launch paths work. |
| Never start the native worker from a dyld constructor | A delayed no-op worker still removes Cloud settings before patching anything. |
| Do not set `STEAM_EXTRA_COMPAT_TOOLS_PATHS` to a valid tool on macOS | Build `1780705203` removed Cloud fields; build `1780965181` reproducibly stalls the Steam main loop before UI initialization. |
| Synchronize AppIDs over an authenticated loopback endpoint | Steam's browser context can reach loopback with `no-cors`; a private token and strict parser avoid a global unauthenticated patch-control surface. |
| Subscribe directly to native app details after registry sync | Steam's shared details cache remained at status `14` without active subscriptions; `RegisterForAppDetails` provides the authoritative install, launch, and update state. |
| Keep the SteamUI platform getter unmodified | Data-object reconciliation plus native detail subscriptions passed 34/34 live; redirecting the global getter was redundant, version-sensitive, and contrary to the narrow production design. |
| Build on Gcenx custom Wine and user-supplied official GPTK files | The independent archive contains Wine, WineD3D, winevulkan, and MoltenVK; Apple supplies D3DMetal but not Wine, and its binaries must not be committed. |
| Keep runtimes immutable and activate them transactionally | Side-by-side package IDs support rollback and multi-version selection without deleting a working runtime or prefix. |
| Build the Steamworks bridge from pinned Proton and Valve Wine commits | It preserves real ownership, callbacks, Workshop, and Cloud behavior and is reproducible; fake Steam API shims are rejected. |
| Disable `winemenubuilder.exe` in the independent runtime | Migrated CrossOver prefixes otherwise recreate or launch old CrossOver menu applications. |
| Scope forced Wine cleanup to People Playground | Its .NET helper confuses Wine PID 312 with persistent macOS PID 312; a global cleanup policy could break launcher-style games. |
| Treat raw GPTK/DXMT/DXVK/Wine directories as validated catalog inputs | Users can install standard vendor layouts directly; the runtime manager will compose them with an immutable base package instead of requiring project-private wrapper files or mutating the source tree. |
| Compose raw tools into content-addressed runtime views | Hardlink the immutable selected base Wine, clone or copy user component files into an isolated overlay, and key the cache by base package plus source-tree fingerprint so source edits create a new view without changing old launches. |
| Reuse a Steamworks bridge for raw Wine only across the same Wine major | A matching Wine 11 bridge retains Steam ownership integration for Wine 11.x; an unknown ABI combination must launch without that bridge instead of injecting an incompatible helper. |
| Commit compatibility selections only after authenticated native registry sync | Steam remains the control owner; the data-only fallback stabilizes checkbox/dropdown state, while delayed original-API writes persist mappings without racing startup. Successful writes are cached and failures leave project state unchanged; native tool registration is still a separate unresolved gate. |
| Scale Wine's game-controller panel without touching Steam Input | The requested controller interface is `wine64 control.exe joy.cpl`. Temporarily raise that prefix's `LogPixels` to at least 192 while the panel runs, restore the exact prior value on every normal or failed exit, and keep Steam's native controller configurator completely untouched. |
| Reject the constructor-wide `CCompatManager +0x798` force-enable patch | It makes the startup-only local-tool job active but also enables unrelated Linux-only manager paths and reproducibly triggers `CSteamEngine::BMainLoop` stalls on build `1780965181`. |
| Never create a prefix from compatibility-page utility actions | A complete Steam installation controls section visibility; an existing non-symlink `compatdata/<appid>/pfx` controls whether component installation, container management, Run Command, browse, and run controls are enabled. Uninstalled games expose only compatibility selection/options. |
| Model Run Command as a Steam-native secondary section | The compatibility page shows one native `运行命令...` button and expands Valve-owned input/button controls in place. No overlay, custom modal, or replacement UI is introduced. |
| Let recovery escape long-running interactive actions | Run Command, Wine configuration, and Task Manager return after successful process creation; `quit-all` bypasses the per-prefix action lock so it can stop a still-open Wine controller panel or application. |
| Let only the newest native action own visible status | A recovery action may intentionally terminate an older Wine process. Preserve both job records, but ignore stale completion when updating Steam's current action status. |
| Ship update as a distinct transactional package | Existing installations need rollback ownership and preservation of user tools/PFX; the online updater must never substitute the full install package for an in-place update. |
| Infer a missing legacy Steam channel from two manifests | `0.1.1` did not persist `steam_channel`. Accept migration only when the current runtime and clean backup agree and both match the recorded build. |

## Update Package Checkpoint

- [x] Build separate Install, Update, and Uninstall packages.
- [x] Add transactional snapshot and rollback around the existing installer.
- [x] Preserve user compatibility tools, PFX directories, and old runtime
  packages.
- [x] Migrate legacy `0.1.1` state without `steam_channel`.
- [x] Make the online updater select and verify the distinct Update artifact.
- [x] Verify checksums, detached release signature, package scripts, package
  metadata, rollback fixtures, and live fail-closed preflight.
- [ ] Obtain a Developer ID Installer identity and sign/notarize the three
  Apple installer packages.
- [ ] Perform a successful live Update.pkg run only after a current-build clean
  rollback snapshot is available; do not destroy the current installation
  without explicit approval.

## Native Controls And Actions Checkpoint

- [x] Prevent missing manifests and empty install shells from being treated as
  completed downloads.
- [x] Seed dynamically managed AppIDs before the first browser registry sync
  so Aimlabs/Hogwarts launch redirection is available on early Play clicks.
- [x] Verify the native force-tool checkbox does not flicker on the deployed
  build and that disable/re-enable preserves the selected tool.
- [x] Verify all compatibility options and lower sections use Steam-native
  controls without an overlay or replacement page.
- [x] Live-test Run Command, EXE resolution, environment variables, Open C
  Drive, Wine configuration, Task Manager, Wine Game Controllers, and
  `quit-all` against an existing prefix.
- [x] Raise Wine Game Controllers to readable 192 DPI with bounded,
  best-effort registry restoration.
- [ ] Run a destructive live `delete-container` acceptance only after explicit
  approval. Automated recoverable-move and confirmation tests remain the
  current evidence.
- [x] Implement and live-verify standard raw `compatibilitytools.d` GPTK,
  DXMT, DXVK, Wine, and CrossOver-style directory discovery with multi-version
  coexistence and capability detection.
- [x] Distinguish an installed game with a real pending update from a
  zero-byte files-missing warning. Aimlabs now routes to Steam's native resume
  action while Hogwarts retains verified stale-target recovery.

## Errors Encountered

| Error | Attempt | Resolution |
|-------|---------|------------|
| Memory registry search returned no RealSteamOnMac entry | 1 | Continue from repository evidence; no prior memory facts will be assumed. |
| SteamUI near-branch allocation failed and retried every worker tick | 2 | Removed the redundant global getter redirect; retained the getter address only as a vtable identity check for allowlist-scoped data objects. |
| Native Play reached `CreatingProcess` but did not invoke the tool stub | 1 | Confirmed AppID mapping exists; investigate post-init native tool refresh or an allowlist-scoped launch dispatcher. |
| Wine Staging 11.10 had no separate `wine64` executable | 1 | Added a package-local `wine64 -> wine` compatibility symlink for its unified WoW64 launcher. |
| Upstream DXVK 2.7.1 is incompatible with current MoltenVK extensions | 1 | Replaced the active mode with Gcenx DXVK-macOS builtin; retained upstream DXVK only as research evidence. |
| Native macOS Steam lacks two Linux `steamclient` helper exports | 2 | Added generated local interface validation and local missing-interface logging while preserving the Linux path. |
| DXMT v0.80 cannot create its Metal view with stock Wine Staging 11.10 | 1 | Added a Wine 11 client-surface bridge plus a narrow dyld visibility shim; the formal isolated package renders the People Playground menu and exits cleanly. |
| People Playground's compiler kept Steam running after normal exit | 2 | Proved Wine PID `312` collided with `/usr/libexec/searchpartyd`; added an AppID-only post-exit Wine cleanup. |
| Runtime installer left official GPTK images mounted after success | 1 | Detach the installer-owned mount points directly, use force only as fallback, and verify a real idempotent reinstall leaves no mounts. |
| A broad game-evidence scan under `/Volumes` did not terminate promptly | 1 | Terminated the scan without modifying data and switched to explicit known library, manifest, configuration, and log paths. |
| A shell loop split AppID/path pairs on whitespace and queried `appmanifest_.acf` | 1 | Discarded the invalid output and replaced the loop with an explicit manifest file list. |
| zsh preserved a newline-delimited probe list as one `awk` filename | 1 | Re-ran the read-only batch through `xargs`, which passed each probe path as a distinct argument. |
| The first native-helper patch used an inexact constant-block context | 1 | `apply_patch` changed no file; re-read the exact neighboring lines and applied smaller targeted hunks. |
| The field-regression plan named two launcher/guard tests that do not exist | 1 | Corrected the plan to use `tests/test_steam_launcher.sh` and `tests/test_hook_environment_isolation.sh`. |
| The repair integration assertion ran while the fixture intentionally exposed an empty overview store | 1 | Moved repair calls before the transient-empty registry phase; production correctly refused unavailable app state. |
| Task 5 named `tests/test_spawn_redirect_harness.sh`, but the repository uses `tests/test_spawn_redirect.sh` | 1 | Corrected both verification and commit paths before editing the spawn redirect implementation. |
