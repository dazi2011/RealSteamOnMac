# Task Plan: RealSteamOnMac Independent Steam Play

## Goal

Turn native macOS Steam into a self-contained frontend that can discover,
download, configure, and launch owned Windows-only games through independently
managed GPTK, DXMT, DXVK, WineD3D, and Wine compatibility tools without
requiring CrossOver.

## Current Phase

Phase 4: independent compatibility runtime foundation

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

- [ ] Inventory locally available GPTK and installed Wine/CrossOver components.
- [ ] Research current upstream DXMT, DXVK, Wine, GPTK requirements and licenses.
- [ ] Define the package format under `compatibilitytools.d`.
- [ ] Implement a runtime registry with versioned, transactional packages.
- [ ] Create Proton-compatible `steamapps/compatdata/<appid>/pfx` prefixes.
- [ ] Implement Steam-to-wrapper launch argument and environment propagation.
- [ ] Add smoke-test executables and failure diagnostics.
- [ ] Document, commit, and push each independently testable runtime milestone.
- **Status:** pending

### Phase 5: Per-Game Compatibility Controls

- [ ] Expose installed compatibility tools in Steam's per-game dropdown.
- [ ] Add persistent per-AppID controls for MSync, high-resolution mode,
      Metal HUD, and supported MetalFX/DLSS translation settings.
- [ ] Add a run-command workflow scoped to the selected game's prefix.
- [ ] Add dependency search/install with manifests, checksums, and uninstall logs.
- [ ] Ensure settings survive Steam and machine restarts.
- [ ] Test each control against the actual generated environment.
- [ ] Document, commit, and push each control group.
- **Status:** pending

### Phase 6: End-To-End Game Launch

- [ ] Select a known-safe runtime for People Playground.
- [ ] Launch through Steam's original Play action.
- [ ] Verify prefix creation, process tree, window creation, input, audio, and exit.
- [ ] Verify at least one alternate renderer/runtime selection.
- [ ] Verify cloud status no longer blocks launch.
- [ ] Capture logs and rollback evidence.
- [ ] Update all handoff and installation documents.
- [ ] Run the complete automated and live verification matrix.
- [ ] Commit and push the final verified state.
- **Status:** pending

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

## Errors Encountered

| Error | Attempt | Resolution |
|-------|---------|------------|
| Memory registry search returned no RealSteamOnMac entry | 1 | Continue from repository evidence; no prior memory facts will be assumed. |
| SteamUI near-branch allocation failed and retried every worker tick | 2 | Removed the redundant global getter redirect; retained the getter address only as a vtable identity check for allowlist-scoped data objects. |
