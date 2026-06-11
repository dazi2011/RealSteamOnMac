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
- [ ] Re-expose runtime options, Run Command, dependencies, and container
      actions through Steam-owned controls without reviving the legacy panel.
- [ ] Discover side-by-side user-supplied GPTK, DXMT, DXVK, and Wine trees in
      standard CrossOver-like layouts under `compatibilitytools.d`.
- [ ] Derive renderer capabilities from the discovered payload and disable
      unsupported DXR, MetalFX/DLSS, MSync, and related settings.
- [ ] Repair stable/beta Steam discovery, language-independent actions,
      restart readiness, Windows-only labeling, download reconciliation, and
      stale installed-manifest handling.
- [ ] Repair Windows executable resolution, Rockstar bootstrap recovery,
      Windows-only `.exe` launch, and avoid false `.app` target selection.
- [ ] Allow Steam's add-non-Steam-game flow to accept `.exe` files while
      preserving native `.app` behavior and applying compatibility only to PE
      executables.
- [ ] Make Run Command behave like Windows Run, fix EXE selection persistence,
      and open the selected prefix drive in Finder.
- [ ] Merge Windows component installation into Install Application To
      Container and provide a reviewed, checksum-pinned dependency catalog.
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
| Do not set `STEAM_EXTRA_COMPAT_TOOLS_PATHS` to a valid tool on macOS | A/B testing proves valid native tool discovery removes the Cloud settings fields on build `1780705203`. |
| Synchronize AppIDs over an authenticated loopback endpoint | Steam's browser context can reach loopback with `no-cors`; a private token and strict parser avoid a global unauthenticated patch-control surface. |
| Subscribe directly to native app details after registry sync | Steam's shared details cache remained at status `14` without active subscriptions; `RegisterForAppDetails` provides the authoritative install, launch, and update state. |
| Keep the SteamUI platform getter unmodified | Data-object reconciliation plus native detail subscriptions passed 34/34 live; redirecting the global getter was redundant, version-sensitive, and contrary to the narrow production design. |
| Build on Gcenx custom Wine and user-supplied official GPTK files | The independent archive contains Wine, WineD3D, winevulkan, and MoltenVK; Apple supplies D3DMetal but not Wine, and its binaries must not be committed. |
| Keep runtimes immutable and activate them transactionally | Side-by-side package IDs support rollback and multi-version selection without deleting a working runtime or prefix. |
| Build the Steamworks bridge from pinned Proton and Valve Wine commits | It preserves real ownership, callbacks, Workshop, and Cloud behavior and is reproducible; fake Steam API shims are rejected. |
| Disable `winemenubuilder.exe` in the independent runtime | Migrated CrossOver prefixes otherwise recreate or launch old CrossOver menu applications. |
| Scope forced Wine cleanup to People Playground | Its .NET helper confuses Wine PID 312 with persistent macOS PID 312; a global cleanup policy could break launcher-style games. |
| Treat raw GPTK/DXMT/DXVK/Wine directories as validated catalog inputs | Users can install standard vendor layouts directly; the runtime manager will compose them with an immutable base package instead of requiring project-private wrapper files or mutating the source tree. |

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
