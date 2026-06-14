# Progress Log

## Session: 2026-06-11

### Phase 8: Field Regression Remediation And Verified Release

- **Status:** in progress
- **Started:** 2026-06-11 Asia/Shanghai
- Actions taken:
  - Read the complete field report and converted it into explicit subsystem and
    acceptance requirements.
  - Created a long-running goal for remediation, verification, packaging, and
    publication.
  - Loaded the brainstorming, codebase-learning, and file-based planning
    workflows.
  - Ran planning session recovery; no unsynchronized recovery output was
    reported.
  - Confirmed the active worktree is clean and aligned with its remote branch at
    commit `6ace14b`.
  - Inventoried repository source, tests, research, evidence, packages, and
    existing planning files.
  - Searched for out-of-band RTF instruction files; none were present.
  - Searched project memory; no RealSteamOnMac entry was available.
  - Decomposed the request into independently verifiable implementation and
    release phases without pausing for an approval loop, per the user's
    explicit instruction.
  - Audited commit `beee125` and proved the current UI hides Steam's native
    compatibility row before mounting a project-owned replacement panel.
  - Proved compatibility-row discovery is hard-coded to Chinese and English
    label text, explaining failure in other Steam UI languages.
  - Confirmed current tests explicitly preserve the incorrect hidden-native-row
    behavior and must be replaced with native-control integration coverage.
  - Read lines 1-1600 of `ui/realsteamonmac_ui.js` in full.
  - Confirmed the runtime already merges project tools into Steam's native
    `GetAvailableCompatTools` API, so a second hand-built selector is
    unnecessary.
  - Found one-time startup tool loading, indefinite per-AppID tool caching, and
    locale-dependent compatibility-page detection.
  - Read lines 1601-3027 of `ui/realsteamonmac_ui.js` in full, completing the
    UI source audit.
  - Confirmed all compatibility options and action dialogs are custom
    HTML/CSS overlays rather than Steam-owned controls.
  - Found an inert Create Log checkbox, split component/application install
    workflows, hard-coded Chinese copy, and aggressive one-second DOM/React
    polling.
  - Read `runtime/realsteamonmac_runtime.py` in full.
  - Found heuristic EXE guessing instead of Steam launch-config resolution,
    strict `steamapps` confinement that blocks non-Steam EXEs, and Run Command
    validation that rejects normal Win+R command names and external files.
  - Confirmed empty install directories are accepted as installed context and
    raw CrossOver-like runtime trees cannot be launched without project
    package metadata.
  - Read `runtime/compat_tool_catalog.py`, the compatibility-tool installer,
    the main installer, the injection installer, and the launcher in full.
  - Confirmed beta-manifest/build hard-coding, a fixed 30-second activation
    delay, and strict project-only tool metadata as direct causes of three
    field reports.
  - Read the SteamUI patcher, steamclient patcher, runtime package installer,
    and dependency catalog in full.
  - Confirmed fixed Steam resource hashes/anchors and Mach-O profiles prevent
    unprofiled stable/new builds from being patched safely.
  - Confirmed the current catalog has only three dependency entries and the
    runtime package duplicates full Wine trees per renderer.
  - Read `hook/compat_gate_hook.c` in full.
  - Confirmed spawn redirection cannot handle missing/wrong paths or `.app`
    targets, and that platform/install patches do not validate manifests or
    depots.
  - Identified overlapping 250 ms native polling, periodic full memory scans,
    and one-second JavaScript reconciliation as a performance concern.
  - Read the guard, DXMT bridge/shim, backup/restore/update/release paths,
    build helpers, compatibility wrapper files, and package scripts.
  - Confirmed wrapper `run` files are logging stubs, capabilities are static,
    and the updater reuses the install package rather than producing a tested
    `update.pkg`.
  - Read the shell test suite and native harnesses in source batches.
  - Found extensive source-grep tests that preserve the hidden custom UI and
    beta-only assumptions rather than validating user-visible behavior.
  - Confirmed native process-start tool discovery must remain disabled to avoid
    the proven Cloud regression; the native selector must be restored through
    Steam's UI/API layer instead.
  - Captured current native Steam process/build, installed state, launcher/hook
    logs, compatibility directory, runtime layout, Steam libraries, and
    CrossOver Preview engine roots.
  - Found a live 34-to-0-to-34 managed-registry transition that explains
    intermittent post-restart button and Windows-only state regressions.
  - Confirmed both stable and beta manifest files coexist while the running
    process identifies the active beta build.
  - Inspected the installed directories for Red Dead Redemption 2, Hogwarts
    Legacy, Black Myth: Wukong, Aim Lab, and People Playground.
  - Proved Hogwarts Legacy and Aim Lab retain valid Windows executables while
    their reported failing targets do not exist, separating launch-metadata
    corruption from depot loss.
  - Confirmed Black Myth: Wukong is an approximately 1.1 MB empty shell,
    matching the reported one-second pseudo-download/stale-installed-state
    failure class.
  - Confirmed RDR2 is fully present and reaches `PlayRDR2.exe` through the DXMT
    runtime; the remaining failure lies in Rockstar/prefix/runtime bootstrap
    handling after dispatch.
  - Read the explicit app manifests for RDR2, Hogwarts Legacy, Black Myth:
    Wukong, Aimlabs, and People Playground and separated installed depots from
    staged-only state.
  - Confirmed Black Myth: Wukong has no installed depots and zero recorded
    size, while a 149.8 GB depot remains staged; current normalization must not
    promote that state to installed.
  - Confirmed RDR2 has no per-AppID configuration and therefore inherits the
    runtime's DXMT default despite being a newer DX12 title.
  - Read the two failed Open C Drive job records and found that
    `/usr/bin/open` inherited the x86_64 DXMT visibility shim, causing an
    arm64e dyld abort. The job writer also incorrectly labeled exit `-6` as
    completed.
  - Read the full Python runtime/catalog/update tests and the full Node
    policy/runtime/CDP tests.
  - Confirmed the tests currently assert the handcrafted compatibility panel,
    explicitly hide Steam's native row, accept app discovery from only a
    manifest plus directory, and do not test environment scrubbing for native
    helper processes.
  - Read every Steam CDP probe and confirmed the acceptance tooling is
    People-Playground-specific, Chinese-text-dependent, and coupled to the
    project-owned compatibility panel.
  - Read the current README, interfaces, project history, release design,
    implementation plan, handoff, dependency research, action workflow, Steam
    beta validation, and cross-renderer acceptance documents.
  - Identified a documentation/implementation contradiction: the documents
    promise Steam's native selector while the deployed code hides it and
    mounts a replacement.
  - Audited CrossOver Preview's application-level engine roots, GPTK payload,
    DXMT/DXVK component roots, bottle templates, recipe database, running
    process tree, and installed bottle structure.
  - Confirmed CrossOver uses one shared Wine/component engine plus mutable
    bottles, while the current RealSteamOnMac package duplicates full Wine
    roots for each renderer.
  - Stopped an overly broad `/Volumes` filesystem scan and replaced it with
    explicit game, manifest, configuration, and log paths.
  - Discarded a malformed whitespace-splitting manifest loop and queued an
    explicit file list so AppIDs and paths cannot be lost.
  - Replaced a failed zsh command-substitution probe batch with an explicit
    `xargs` file list; zsh had preserved the newline-delimited list as one
    argument.
  - Completed implementation-plan Task 1 with test-first development.
  - Added RED coverage proving Open C Drive leaked Wine/Steam/DYLD variables
    and container exit `-6` was persisted as completed.
  - Added a native-helper environment allowlist and made dependency/container
    jobs fail on nonzero process exits.
  - Passed all 38 runtime-manager tests.
  - Passed a live Finder smoke test against the People Playground `drive_c`;
    `/usr/bin/open` returned zero with the fatal DXMT shim removed from its
    environment.
- Files modified:
  - `task_plan.md`
  - `findings.md`
  - `progress.md`

## Session: 2026-06-09

### Phase 1: Takeover Audit And Recovery

- **Status:** complete
- **Started:** 2026-06-09 09:00 Asia/Shanghai
- Actions taken:
  - Read the user's complete target behavior and safety constraints.
  - Created an explicit long-running goal for the whole project.
  - Loaded the planning, brainstorming, systematic-debugging, TDD, and
    implementation-planning workflows.
  - Inspected repository status, branches, recent commits, files, handoffs,
    README, and the two supplied screenshots.
  - Confirmed the local branch is exactly one commit behind the remote.
  - Confirmed the remote-only commit claims a completed People Playground
    Windows depot download.
  - Found and reviewed four additional uncommitted files in Claude's final
    linked worktree.
  - Ran the complete automated repository suite against that dirty worktree;
    all existing tests passed.
  - Identified an untested missing UI predicate and rejected the prototype's
    global install-gate NOP as too broad for production.
  - Verified the actual People Playground manifest, depot, content files, and
    Steam content-log completion evidence.
  - Verified no Proton-style prefix exists yet.
  - Inspected current Steam processes, signatures, support files, hook logs,
    config-store logs, CloudStorage logs, and cloud-related VDF state.
  - Confirmed live CDP is unavailable because the current long-running Steam
    process was not started with remote debugging.
  - Established a phased architecture and safety/commit gates.
  - Preserved Claude's uncommitted prototype as commit `fe6d20d` on pushed
    branch `codex/claude-recovery-20260609`.
  - Fast-forwarded the active branch to verified remote commit `be55b6a`.
  - Re-ran the complete active-head test suite; all tests passed.
  - Audited installer, rollback, launcher, compatibility tool, design, plan,
    research, and deployed-source hashes.
  - Confirmed the installed compatibility tool is a logging stub and no game
    launch implementation exists.
  - Found a rollback correctness bug: patched Steam UI resources are not
    restored before the support directory is removed.
  - Stopped Claude's orphaned twelve-hour log watcher without touching Steam.
  - Added the 2026-06-09 technical handoff.
  - Wrote a failing rollback regression that installed the real guarded Steam
    UI patch and proved the old rollback left injected resources behind.
  - Updated the rollback to restore Steam UI before moving any application,
    runtime, or support files.
  - Re-ran the focused rollback test and complete repository suite; all passed.
- Files created/modified:
  - `task_plan.md` (created)
  - `findings.md` (created)
  - `progress.md` (created)

### Phase 2: Live Steam Health And Cloud Root Cause

- **Status:** complete
- Actions taken:
  - Quit Steam normally and relaunched it through the installed launcher with
    `-cef-enable-debugging`.
  - Confirmed CDP became available on `127.0.0.1:8080`.
  - Reproduced the blank global Cloud page after the controlled restart.
  - Inspected the live settings DOM and confirmed the heading renders while the
    page body remains empty.
  - Reloaded while listening for runtime and console errors; no JavaScript
    exception explained the missing content.
  - Located Steam UI's native settings schema and confirmed it defines
    `cloud_enabled` and `show_screenshot_manager`.
  - Inspected the live settings store and confirmed the native backend omits
    both settings instead of returning `cloud_enabled: false`.
  - Traced the per-game warning to the same missing setting's disabled fallback.
  - Confirmed CloudStorage resumed normally and did not report remote-save
    corruption.
  - Searched the injected project UI and found no cloud-setting read or write.
  - Built isolated temporary Steam app wrappers that reuse the same runtime
    without modifying the installed `/Applications/Steam.app`.
  - Reproduced healthy Cloud settings with a minimal injected library that only
    clears inherited injection variables.
  - Proved that inherited `DYLD_INSERT_LIBRARIES` breaks the Steam Helper
    websocket/settings bridge.
  - Proved that constructor-time worker creation removes the Cloud settings
    even before the worker performs a patch.
  - Isolated `STEAM_EXTRA_COMPAT_TOOLS_PATHS` as a second trigger: an empty
    directory is healthy, while the real compatibility-tool manifest removes
    both Cloud fields.
  - Retested the full `arm64` engine with no worker and no valid tool path; the
    Cloud fields remained healthy, disproving the intermediate load-surface
    hypothesis.
  - Reduced the production fix to a minimal startup guard, dormant native
    engine, and project-owned compatibility-tool registry.
  - Added the split guard/engine build and installer contracts.
  - Removed valid native compatibility-tool registration from the launcher and
    added a regression that forbids reintroducing it.
  - Ran the complete Node, Python, and shell suite; all tests passed.
  - Backed up the prior deployed support and executables to
    `$HOME/RealSteamOnMac-Backups/cloud-fix-20260609T103853`.
  - Deployed the guarded startup to `/Applications/Steam.app` and verified deep
    code signing plus installed file hashes.
  - Verified the installed global Cloud page renders two setting groups.
  - Verified Garry's Mod retains its native Cloud checkbox and quota.
  - Verified People Playground exposes Cloud with a `953.67 MB` quota and its
    compatibility page.
  - Verified no new pending-platform-change or no-user sync failure appeared;
    roaming config reported all synced.
  - Attempted element-aware Computer Use twice; ScreenCaptureKit failed with
    `SCStreamErrorDomain -3811`, so no coordinate actions were used.
- Files created/modified:
  - `findings.md`
  - `progress.md`
  - `task_plan.md`

### Phase 3: Dynamic Windows-Only Library Enablement

- **Status:** complete
- Actions taken:
  - Inspected Steam's live SharedJSContext application and details stores.
  - Selected `appStore.allApps` plus
    `appDetailsStore.RequestAppDetails(appid)` as the authoritative in-process
    library source.
  - Defined the strict eligibility rule: owned, visible game, Windows platform
    present, macOS platform absent.
  - Requested candidate details in bounded batches and completed the current
    library scan in about 0.7 seconds.
  - Found 49 owned/visible games and 34 Windows-only candidates.
  - Confirmed Garry's Mod and other native/dual-platform titles remain excluded.
  - Confirmed every candidate currently reports native
    `InvalidPlatform`, including locally installed People Playground.
  - Confirmed native compatibility-tool discovery is empty in the cloud-safe
    configuration, requiring a project-owned dynamic registry.
  - Added pure policy tests for Windows-only identification, native/dual
    exclusion, ownership/visibility filtering, registry additions, and
    removals.
  - Replaced the compatibility-page chunk's static AppID check with the runtime
    predicate `__REALSTEAMONMAC_IS_MANAGED_APP__`.
  - Added a tested migration from the previously installed static compatibility
    gate to the dynamic gate.
  - Implemented a five-second live registry refresh from Steam's app overview
    and details stores.
  - Added a project-owned compatibility-tool bridge so the page can enumerate
    RealSteamOnMac tools without setting `STEAM_EXTRA_COMPAT_TOOLS_PATHS`.
  - Added a browser-context integration test proving the predicate exists
    before property-page use, the bootstrap registry is atomically replaced,
    dual-platform games remain excluded, and project tool selection does not
    call Steam's native registration API.
  - Ran 43 Node tests, 8 Python tests, and every shell contract; all passed.
  - Captured a healthy Cloud baseline, then attached LLDB to the running Steam
    process, loaded the dormant native engine, called its explicit worker
    entrypoint, and detached successfully.
  - Verified the late-loaded engine remained mapped, Steam stayed alive, the
    install-gate trampoline was installed, and Cloud settings remained intact.
  - Observed People Playground backend details transition to status `11` while
    its cached overview stayed at status `14`.
  - Added policy and reconciliation coverage for mapping installed managed
    games to native ready-to-launch status `11`, while rejecting inconsistent
    local-content/status combinations.
  - Rejected external Mach injection as the shipping path because it would
    require debugger/task entitlements and weaken the installed runtime.
  - Added an environment-gated, one-shot dispatch timer to the minimal guard.
  - Added a fake-engine harness proving delayed `dlopen` and worker invocation,
    while preserving the original no-engine guard behavior.
  - Added launcher contracts for the engine path, 30-second delay, and explicit
    bootstrap/runtime injection stage.
  - Diagnosed Steam's startup fork and adjusted the stage handshake so the
    guard survives into the final runtime but every Helper clears the inherited
    environment and refuses activation.
  - Completed a live two-stage A/B launch: guard present before activation,
    engine automatically mapped after 30 seconds, worker/gate active, Cloud
    intact, People Playground backend status `11`, and all Helper environments
    clean.
  - Implemented an authenticated browser-to-native AppID registry bridge on
    `127.0.0.1:57344`.
  - Added installer-generated 32-character hexadecimal registry tokens with
    mode `0600`, and embedded the validated endpoint/token in generated local
    Steam UI configuration.
  - Restricted the generated token-bearing `config.js` to mode `0600` and made
    verification reject broader group/other permissions.
  - Added a bounded native HTTP parser accepting at most 16 KiB and 256 unique
    positive AppIDs.
  - Made native allowlist publication atomic and made the install gate rebuild
    on additions/removals, restoring the original Steam instruction when the
    registry becomes empty.
  - Added an allowlist generation counter so a registry update racing with
    trampoline replacement cannot be lost; the next worker tick rebuilds again.
  - Kept Steam memory reconciliation on its existing single worker instead of
    scanning concurrently from the registry server thread.
  - Added browser retry coverage proving an unavailable delayed engine does not
    cache the failed payload.
  - Added a native dynamic-load harness proving authorized add/remove, `403`
    rejection for a wrong token, and `400` rejection for malformed payloads.
  - Ran the modified native, installer, launcher, UI patch, and browser runtime
    tests sequentially; all passed.
  - Ran the complete repository matrix after implementation: 43 Node tests,
    10 Python tests, and every shell contract passed.
  - Traced the remaining 34 cached status-`14` entries to an inactive
    `appDetailsStore` subscription path rather than incorrect native install
    state.
  - Added allowlist-scoped direct native detail subscriptions after successful
    registry synchronization and published authoritative callbacks into
    Steam's shared details store.
  - Preserved native install, launch, download, and update display states rather
    than reducing every game to only status `9` or `11`.
  - Added bounded stale-cache refresh, removal/unregister handling, subscription
    metrics, and tests for dynamic add/remove behavior.
  - Removed repeated normalization of already-correct overview objects.
  - Fixed the backup script so a deployed RealSteamOnMac installation can be
    backed up and verified without assuming `steam_osx` is still the active
    bundle executable.
  - Removed the redundant SteamUI global platform-getter redirect after live
    evidence proved the data scan plus detail subscriptions cover all managed
    games. Added a source contract that fails if the redirect returns.
  - Ran the final complete matrix: 51 Node tests, 10 Python tests, and all 20
    shell contracts passed.
  - Quit Steam normally, installed the verified revision, matched source and
    deployed hashes, verified deep signing, and confirmed token mode `0600`.
  - Cold-started through the production launcher and verified the delayed
    engine, loopback registry, one-to-34 AppID install-gate rebuild, and 33
    additional data-object repairs.
  - Verified all 34 managed games match native detail and overview status, with
    no remaining invalid-platform state and Garry's Mod excluded.
  - Verified For Honor's real blue `安装` action and People Playground's green
    `开始游戏` action after the cold start.
  - Reconfirmed `cloud_enabled=true`, screenshot setting false, CloudStorage
    availability, and clean Helper activation environment.
  - Confirmed the new-run native log contains no SteamUI getter patch or
    allocation error.
  - Inventoried the user-supplied official GPTK 3 image, local renderer
    archives, and installed reference applications.
  - Verified current Gcenx GPTK Wine 3.0-3, DXMT v0.80, Wine Staging 11.10,
    DXVK-macOS v1.10.3, and upstream DXVK v2.7.1 release checksums.
  - Confirmed the independent Gcenx runtime contains `wine64`, `wineserver`,
    WineD3D, `winevulkan`, and MoltenVK.
  - Defined immutable runtime packages, atomic activation, and exact
    `steamapps/compatdata/<appid>/pfx` per-game layout.
  - Triggered native Steam Play for People Playground with the logging stub
    installed. Steam completed Cloud/stat/controller/license stages but failed
    at `CreatingProcess` with `AppError_46`; the stub was not invoked.
  - Confirmed Steam persists the AppID-to-tool mapping, isolating the remaining
    gap to native tool registration or launch dispatch.
  - Corrected the DXVK plan after current Gcenx documentation confirmed that
    upstream DXVK requires Vulkan extensions absent from MoltenVK.
  - Downloaded and checksum-verified Wine Staging 11.10 and the latest
    DXVK-macOS builtin release.
  - Implemented an immutable four-root package containing GPTK, DXMT,
    DXVK-macOS, and WineD3D modes.
  - Implemented a Python runtime manager with exact Proton path resolution,
    atomic private per-game configuration, MSync, Retina, Metal HUD, MetalFX,
    DXR, AVX, prefix preparation, structured logs, and `execve` launch.
  - Installed and activated package
    `gptk3.0-3-wine11.10-dxmt0.80-dxvkmacos1.10.3`.
  - Verified all package hashes and all four Wine entrypoints.
  - Verified a People Playground dry-run resolves the exact requested prefix
    without creating it.
  - Implemented a build-UUID-gated steamclient `posix_spawn` pointer redirect
    that accepts only managed PE targets and preserves native/unmanaged calls.
  - Added a dynamic engine harness proving the redirect decision boundary.
  - Ran the complete pre-deployment matrix: 51 Node tests, 18 Python tests,
    and all 22 shell contracts passed.

### Phase 4: Steamworks Bridge And DXVK Runtime Closure

- **Status:** complete for the DXVK milestone
- Actions taken:
  - Backed up and byte-count verified the complete People Playground PFX and
    active runtime state at
    `$HOME/RealSteamOnMac-Backups/pre-steamworks-bridge-20260609T051952Z`.
  - Pinned Proton commit
    `25880e88befb52c5aa7ff162c5b00b6b8825e494` and Valve Wine commit
    `2f70bfd4d0f4e67a8a599c4a09760579bc2a4fa4`.
  - Added a reproducible external `lsteamclient` build for Darwin x86_64 plus
    the matching PE x86_64 DLL.
  - Added macOS Steam Input keycode conversion.
  - Confirmed native `steamclient.dylib` lacks
    `Steam_IsKnownInterface` and `Steam_NotifyMissingInterface`.
  - Rejected the first `CreateInterface`-only fallback after it produced
    `VersionMismatch` for `STEAMAPPS_INTERFACE_VERSION008`.
  - Generated a table of all 208 interfaces implemented by the pinned bridge
    and used it for local interface validation.
  - Built the final bridge with SHA-256:
    `159798e1caab1102f5d51a5e15891f4d4f5cd901ed7fb54a9ae45d51bb1280ec`
    for `lsteamclient.so` and
    `b806f522a5e49b4b3ba9e0259e8bbf02787e7c287f4f10d880a660190c23c1ca`
    for `lsteamclient.dll`.
  - Extended the immutable runtime package installer with an optional,
    hash-verified `--steamworks-bridge` payload.
  - Installed package
    `gptk3.0-3-wine11.10-dxmt0.80-dxvkmacos1.10.3-lsteamclient-proton11b5-macos2`.
  - Added Steam AppID/data/client environment mapping, managed PFX DLL
    installation, private ledgering, unmanaged-DLL refusal, and Steam registry
    configuration.
  - Launched People Playground directly through DXVK and proved the bridge
    reached native macOS Steam, acquired Steam interfaces, and completed
    callbacks.
  - Launched again through native `steam://rungameid/1118200`.
  - Verified `Steamworks initialised`, `Steam login: True`, Workshop
    subscription retrieval, and subscribed content loading.
  - Captured
    `docs/evidence/people-playground-dxvk-steamworks-live-2026-06-09.png`.
  - Tested DXMT v0.80 and isolated its current blocker to missing
    DXMT-specific Wine exports, not the Steamworks bridge.
  - Found an old CrossOver `People Playground.app/Menu Helper` launched by
    Wine menu integration in the migrated PFX.
  - Disabled `winemenubuilder.exe` in all RealSteamOnMac runtime environments;
    repeat launch produced no CrossOver process.
  - Decompiled People Playground's .NET mod-compiler lifecycle and proved its
    default config is `127.0.0.1:32513`, so missing `config.json` is not the
    exit root cause.
  - Proved the actual root cause: the compiler monitors Wine PID `312`, while
    macOS PID `312` is persistent `/usr/libexec/searchpartyd`.
  - Added an AppID-scoped exit supervisor that terminates only People
    Playground's isolated Wine server after its main process exits.
  - Used the game's visible `quit` menu entry for final acceptance.
  - Verified game exit `0`, automatic runtime cleanup `0`, no remaining game,
    compiler, Wine, runtime, or CrossOver helper process within five seconds.
  - Verified Steam logged `Remove 1118200 from running list`.
  - Verified Steam Cloud logged `Starting sync (up,AC Exit,)`,
    `AutoCloud complete`, and `Upload complete in build list`.
  - Verified installed runtime-manager and source SHA-256 both equal
    `88f04910d46e1f87ab6f9e9a0c9fff83c3021951b4bc84278311401a9ac08a18`.
  - Ran 12 runtime-manager tests, the runtime installer contract, Python
    compilation, shell syntax checks, and `git diff --check`; all passed.

### Phase 4B: DXMT Wine 11 Compatibility

- **Status:** complete; formal package deployed and accepted through live Steam
- Actions taken:
  - Reproduced the DXMT v0.80 failure against stock Wine Staging 11.10 and
    isolated it to macdrv symbol visibility plus Wine 11's client-surface
    lifecycle.
  - Rejected the older Wine 8 path after Unity failed with a stack overflow.
  - Pinned Wine `2cac6ccf33c0807f374dc96f5a20e35a2da86157` and Wine Staging
    `f45e84d7a01a52d379e4003f03800c13875c69e9`.
  - Added an exported Wine 11 macdrv compatibility table that creates and
    retains a client surface for DXMT's legacy `client_cocoa_view` contract.
  - Added a narrow dyld visibility shim because Wine loads `winemac.so`
    locally while DXMT resolves through `RTLD_DEFAULT`.
  - Added a reproducible source builder with complete Staging patch application,
    Rosetta x86_64 configuration, macOS 10.15 deployment target, symbol checks,
    ad-hoc signing, hashes, and immutable metadata.
  - Extended the runtime package manifest and installer with fail-closed DXMT
    driver/shim validation and automatic artifact building.
  - Removed the temporary `wine64` wrapper design; the runtime now injects only
    the package-owned shim for DXMT.
  - Built accepted artifacts:
    `cc86bd9296688cbcceca146cdb9a88b9ac97859f96c4b05bf9c0e7c7496529c9`
    (`winemac.so`) and
    `afa8a47ddd73057bd014e1807bacaf7a91d7917ad1eb51b1d1afb7446b8349c0`
    (visibility shim).
  - Installed the complete candidate package into
    `/private/tmp/realsteamonmac-formal-dxmt-runtime`.
  - Launched People Playground without a wrapper or manual environment,
    rendered the main menu through DXMT, initialized Steamworks, logged in,
    and retrieved one Workshop subscription.
  - Sent `WM_CLOSE` inside the same Wine session and verified runtime exit `0`,
    no remaining managed processes, Steam running-list removal, and successful
    AutoCloud exit/upload.
  - Captured
    `docs/evidence/people-playground-dxmt-wine11-live-2026-06-09.png`.
  - Added three focused runtime tests; 15 runtime-manager tests and the package
    installer contract pass.
  - Ran the complete post-DXMT matrix: 51 Node tests, 25 Python tests, and all
    22 shell contracts passed.
  - Backed up the previous live runtime manager and active-package target at
    `$HOME/RealSteamOnMac-Backups/pre-dxmtmac1-live-20260609T075422Z`.
  - Atomically activated
    `gptk3.0-3-wine11.10-dxmt0.80-dxmtmac1-dxvkmacos1.10.3-`
    `lsteamclient-proton11b5-macos2` in the user's existing Steam environment.
  - Launched People Playground from native `steam://rungameid/1118200`; the
    deployed package reached the main menu in 31 seconds, initialized
    Steamworks, logged in, and retrieved one Workshop subscription.
  - Captured the deployed-runtime screenshot at
    `docs/evidence/people-playground-dxmt-live-deployed-2026-06-09.png`
    with SHA-256
    `3e2ed8f6ee30e060790dd30efa8750cf6d9c5521ef6659d9e75bb2523ac09978`.
  - Closed the game through `WM_CLOSE`; runtime exit was `0`, all managed
    processes cleared, and Steam completed `AC Exit`, AutoCloud, and upload at
    15:58:29 Asia/Shanghai.
  - Fixed the installer to detach its unique GPTK mount points directly and
    fall back to forced detach. A real idempotent reinstall left no mounted
    GPTK images.

### Phase 5A: Per-Game Renderer And Runtime Controls

- **Status:** complete; deployed and accepted in live Steam
- Actions taken:
  - Replaced the single experimental compatibility entry with four explicit
    project tools: GPTK 3, DXMT 0.80, DXVK-macOS 1.10.3, and WineD3D 11.10.
  - Kept native Steam tool discovery disabled at startup to preserve Cloud;
    the existing guarded UI bridge injects only project-owned tools for
    dynamically managed Windows-only games.
  - Added a token-authenticated `/config` endpoint to the native loopback
    server. It accepts only current managed AppIDs and a fixed seven-field
    configuration shape.
  - Added atomic per-AppID configuration at
    `~/Library/Application Support/RealSteamOnMac/apps/<appid>.json`, with
    directory mode `0700`, file mode `0600`, symlink refusal, and
    `fsync`/rename publication.
  - Updated the runtime to prefer the global configuration while retaining the
    existing PFX-local config as a migration fallback. CLI writes update both
    locations.
  - Changed the no-config default to the live-accepted DXMT renderer.
  - Added a Steam-native high-contrast controls panel below the project
    compatibility selector for MSync, Retina, Metal HUD, MetalFX, DXR, and AVX.
  - Enforced capability boundaries: MetalFX and DXR are GPTK-only; Metal HUD is
    disabled for WineD3D.
  - Added config load/save status, local persistence, legacy experimental-tool
    migration, and renderer-to-tool synchronization.
  - Expanded the complete matrix to 54 Node tests, 27 Python tests, and all 22
    shell contracts; all passed.
  - Discovered that Steam properties popups are tracked through
    `g_FriendsUIApp.m_IdleTracker.m_rgWindows`, not the main WindowStore, and
    added popup document enumeration with deduplication.
  - Fixed the control anchor to prioritize the compatibility combobox and skip
    root/oversized containers.
  - Removed recursive whole-library reconciliation from native detail
    callbacks and changed stale detail retries from one to five seconds.
  - Expanded focused Node coverage to 56 passing tests.
  - Deployed the controls to the current Steam client and verified all four
    tools are available for AppID `1118200`.
  - Selected DXVK and verified the canonical mode-`0600` config plus a dry-run
    using the package's DXVK Wine root.
  - Toggled Retina through the real checkbox and verified a second native save.
  - Restored DXMT/MSync, disabled Retina, verified the DXMT macdrv shim in the
    dry-run, closed/reopened properties, and confirmed the state persisted.
  - Captured
    `docs/evidence/people-playground-controls-live-2026-06-09.png`, SHA-256
    `daffe76b2d410377dfe5cf76897478a10f279a3ecdccf6b1311a23aa94042a10`.

### Phase 5B And Phase 6: Actions, Cross-Renderer Closure, And Release

- **Status:** complete; deployed and accepted in live Steam
- Actions taken:
  - Accepted token-authenticated run-command and pinned Visual C++ dependency
    installation with private jobs, logs, cache validation, and PFX receipts.
  - Added a Windows `WM_CLOSE` helper and guarded renderer-selection CLI for
    repeatable live acceptance.
  - Diagnosed GPTK exit code `3` to a Wine 11 Proton bridge DLL remaining in
    the shared PFX. Added hash-ledger reconciliation so GPTK deactivates only
    managed bridge files and supported renderers restore them atomically.
  - Deployed runtime SHA-256
    `5faa1e6bc7bcef72d8116c5218ae80c9ac4ca92c2d17aad9cb41b71575d7d1a1`.
  - Accepted GPTK D3DMetal/menu/normal-exit/Cloud behavior. Game-internal
    Steamworks remains unavailable under GPTK and is documented as a boundary.
  - Accepted WineD3D selection, bridge restoration, Steamworks, Workshop,
    normal exit, and Cloud. People Playground fell back to Unity
    Vulkan/MoltenVK after D3D11 creation failed.
  - Restored DXMT/MSync as the final default and reaccepted D3D11,
    Steamworks login, Workshop, process cleanup, and AutoCloud.
  - Added `script/install_realsteamonmac.sh`, which refuses a running Steam
    client and orchestrates native builds, bridge preparation, immutable
    runtime installation, and Steam integration as one fail-fast operation.
  - Final live registry: 34 Windows-only games managed, all four tools
    available for all 34, zero invalid-platform states, and Garry's Mod
    excluded.
  - Final Cloud state: `cloud_enabled=true`; CloudStorage available.
  - Final complete matrix: 64 Node tests, 40 Python tests, and all 25 shell
    contracts passed.

## Test Results

| Test | Input | Expected | Actual | Status |
|------|-------|----------|--------|--------|
| Git divergence | `git rev-list --left-right --count HEAD...origin/codex/people-playground-experiment` | Identify interrupted remote work | `0 1` | PASS |
| Screenshot review | Two supplied PNG files | Capture cloud and run-command evidence | Findings recorded in `findings.md` | PASS |
| Claude dirty worktree suite | Node, Python, and all shell tests | Existing suite remains green | All tests passed | PASS |
| Installed game verification | Manifest, content tree, content log | Prove completed Windows depot | StateFlags 4, UpdateResult 0, depot 1118201, 436 MB content | PASS |
| Live CDP endpoint | `http://127.0.0.1:8080/json/list` | Enumerate Steam targets | Connection refused; process lacks debug flag | EXPECTED FAIL |
| Active recovered-head suite | Node, Python, and all shell tests | Clean recovered baseline | All tests passed | PASS |
| Rollback RED | Patched temporary Steam UI | Old rollback should fail exact-resource assertions | Failed because patched `index.html` remained | PASS |
| Rollback GREEN | Same fixture after minimal fix | Exact originals restored and assets removed | Focused and full suites passed | PASS |
| Debug Steam relaunch | Launcher plus `-cef-enable-debugging` | Obtain live settings state | CDP available on port 8080 | PASS |
| Global Cloud DOM | `steam://open/settings/cloud` | Reproduce supplied screenshot | Heading present; settings body empty | PASS |
| Cloud settings schema | webpack module `29788` | Determine whether client recognizes cloud fields | Fields 10000 and 10001 exist | PASS |
| Live native settings | webpack settings store | Distinguish disabled from unavailable | `cloud_enabled` and screenshot setting absent | PASS |
| Runtime/console capture | Reload global Cloud page | Find a render exception | No relevant exception emitted | PASS |
| Minimal injection A/B | Same Steam runtime with environment-only hook | Preserve native settings | `cloud_enabled=true`, screenshot setting false | PASS |
| Valid compatibility-tool path | Minimal healthy hook plus real tool manifest | Isolate native tool discovery | Cloud fields absent | PASS |
| Empty compatibility-tool path | Same variable pointed at empty directory | Distinguish variable from parsed tool | Cloud fields present | PASS |
| Full arm64 engine, no worker/tool path | Strict single-variable engine load | Test load-surface hypothesis | Cloud fields present; hypothesis rejected | PASS |
| Full repository suite | Node, Python, all shell tests | No regressions after split/launcher fix | All tests passed | PASS |
| Installed global Cloud page | Guarded `/Applications/Steam.app` | Two setting groups render | `DialogBody` child count 2 | PASS |
| Installed native title | Garry's Mod properties | Native Cloud remains intact | Checkbox text and 1,024 MB quota present | PASS |
| Installed Windows title | People Playground properties/logs | Cloud and compatibility page coexist | 953.67 MB quota, compatibility tab, normal eval | PASS |
| Computer Use UI session | Element-aware Steam session | Visual/accessibility tree | ScreenCaptureKit error `-3811`; CDP fallback used | BLOCKED |
| Live Windows-only discovery | Shared app overview plus requested details | Exclude native/dual-platform titles | 34 of 49 owned/visible games qualify; Garry's Mod excluded | PASS |
| Dynamic registry policy | Node unit tests | Add/remove candidates without broadening eligibility | 34 policy tests passed | PASS |
| Dynamic browser runtime | VM SharedJSContext fixture | Predicate, hot registry, project tools | Integration test passed | PASS |
| UI patch migration | Previous static compatibility gate | Upgrade atomically to dynamic predicate | Python and shell contracts passed | PASS |
| Post-init engine load | LLDB load plus explicit worker call | Install backend gate without breaking Cloud | Engine mapped, gate patched, Cloud fields preserved | PASS |
| Installed state mapping | People Playground plus native installed titles | Derive correct Play state | Backend `11` + local content maps overview to `11` | PASS |
| Delayed activation harness | Fake native engine and marker | Invoke only after configured delay | Marker written; inherited environment cleared | PASS |
| Live automatic activation | Two-stage guard launch | Load engine after initialization without Cloud regression | Engine/gate active; Cloud intact; Helpers clean | PASS |
| Native registry protocol | Production engine loaded by C harness | Authenticated hot add/remove with fail-closed rejection | `204` add/clear, `403` wrong token, `400` malformed body | PASS |
| Browser registry retry | First loopback request fails | Retry unchanged payload on next five-second scan | Second request succeeds and clears error state | PASS |
| Registry token install | Temporary Steam/support fixture | Private valid token shared by patcher and engine | 32 hex characters, mode `0600`, generated config verified | PASS |
| Native detail subscriptions | 34 managed AppIDs | Replace stale status `14` with current native state | 34/34 details and overview statuses synchronized | PASS |
| Full Phase 3 suite | 51 Node, 10 Python, 20 shell contracts | No regression across install/cloud/rollback/runtime | All passed | PASS |
| Installed source hashes | Built engine/UI versus deployed files | Exact tested artifacts installed | SHA-256 pairs matched | PASS |
| Cold native log | New run from log line `4774` | No global SteamUI getter retry | Zero `steamui:` entries; gate rebuilt 1 -> 34 | PASS |
| Cold dynamic registry | Current owned library | Every managed app native-synchronized | 34/34 synced, zero invalid details/overviews | PASS |
| For Honor visible action | AppID `304390` library page | Native enabled blue Install action | `安装`, pointer events auto, status `9/9` | PASS |
| People Playground visible action | AppID `1118200` library page | Native enabled Play action | `开始游戏`, green gradient, status `11/11` | PASS |
| Cloud after Phase 3 | Shared settings store | Dynamic registry must not regress Cloud | `cloud_enabled=true`; CloudStorage available | PASS |
| Independent Wine inventory | Gcenx GPTK Wine 3.0-3 archive | No CrossOver dependency; Wine and graphics loaders present | `wine64`, `wineserver`, WineD3D, winevulkan, MoltenVK present | PASS |
| Renderer release integrity | Cached GPTK Wine, DXMT, and DXVK archives | Exact upstream SHA-256 digests | All three matched published digests | PASS |
| Native Play dispatch probe | `steam://rungameid/1118200` with logging stub | Capture compatibility-tool invocation | Mapping present, but spawn failed before stub with `AppError_46` | BLOCKED |
| Runtime manager unit suite | PE/path/config/environment fixtures | Exact Proton paths and valid control mapping | 8 tests passed | PASS |
| Runtime package install | Verified local archives plus official GPTK redist | Atomic four-mode active package | Package installed; all recorded hashes passed | PASS |
| Independent Wine entrypoints | Four installed renderer roots | Each Wine launcher executes without CrossOver | GPTK Wine and three Wine Staging 11.10 roots executed | PASS |
| People Playground dry-run | Installed runtime plus AppID 1118200 | Exact prefix and no mutation | Exact `/compatdata/1118200/pfx`; prefix remained absent | PASS |
| Spawn redirect harness | Managed PE, unmanaged PE, native binary | Redirect only managed PE target | Decision boundary passed | PASS |
| Full Phase 4 post-DXMT suite | 51 Node, 25 Python, 22 shell contracts | No regression before live installation | All passed | PASS |
| Steamworks bridge build | Pinned Proton/Valve Wine plus macOS patch | Reproducible Mach-O and PE bridge | Both hashes verified | PASS |
| DXVK Steamworks direct trace | People Playground with bridge | Reach native Steam and initialize APIs | Pipe/user/interfaces/callbacks completed | PASS |
| Native Steam DXVK launch | `steam://rungameid/1118200` | Steam-tracked real game window | Menu rendered; Steamworks login true | PASS |
| CrossOver independence | Repeat launch with menu integration disabled | No CrossOver executable in process tree | No CrossOver Menu Helper appeared | PASS |
| Normal game exit | Visible in-game `quit` entry | Main process exits without force-quit | Exit code `0` | PASS |
| PPG compiler cleanup | Wine PID collides with macOS PID 312 | AppID-scoped PFX cleanup | All managed processes gone in five seconds | PASS |
| Steam running-list closure | Final supervised exit | Remove AppID after cleanup | `Remove 1118200 from running list` | PASS |
| Steam Cloud exit closure | Final supervised exit | Run AutoCloud upload | `AC Exit`, complete, upload complete | PASS |
| DXMT stock Wine launch | DXMT v0.80 plus unmodified Wine Staging 11.10 | Create Metal view | Required exports and legacy client view unavailable | EXPECTED FAIL |
| DXMT formal source build | Pinned Wine 11.10 + complete Staging v11.10 + project patch | x86_64, macOS 10.15, exported table, signed artifacts | All checks and hashes passed | PASS |
| DXMT isolated package install | Official GPTK image, verified archives, bridge, DXMT compatibility artifacts | Immutable package and complete SHA manifest | Package installed; every recorded hash passed | PASS |
| DXMT formal live launch | Manifest-driven shim, no wrapper, People Playground | Main menu plus Steamworks and Workshop | Menu rendered; login true; one subscription retrieved | PASS |
| DXMT normal exit and Cloud | Same formal run plus Windows `WM_CLOSE` | Exit 0, cleanup, Steam removal, AutoCloud | All conditions passed at 15:46:45 | PASS |
| Live DXMT deployment | Existing Steam plus active immutable `dxmtmac1` package | Native launch, real menu, Steamworks, Workshop | Main menu reached in 31 seconds; all conditions passed | PASS |
| Live DXMT exit and Cloud | Deployed package plus `WM_CLOSE` | Exit 0, process cleanup, AutoCloud upload | All conditions passed at 15:58:29 | PASS |
| Installer mount cleanup | Real GPTK DMG and existing immutable package | Idempotent install with no residual images | Reinstall passed; no project GPTK mounts remained | PASS |
| Runtime control API | Authorized/unauthorized AppIDs, valid/invalid settings, file permissions | Fixed schema, managed scope, atomic private persistence | Native socket harness passed every boundary | PASS |
| Four compatibility tools | Steam config, manifests, installer, runtime mapping | Unique GPTK/DXMT/DXVK/WineD3D selections | UI, patcher, compat-tool, and installer contracts passed | PASS |
| Full Phase 5A suite | 54 Node, 27 Python, 22 shell contracts | No regression before live control deployment | All passed | PASS |
| Properties popup discovery | Live shared Steam context | Find the independent People Playground popup | Located through idle-tracker window registry | PASS |
| Control panel live mount | People Playground compatibility page | One Steam-native panel below project tool | Six controls rendered; DXMT selected | PASS |
| DXVK control write | Select `realsteamonmac-dxvk` | Native private config and DXVK runtime | Save count incremented; mode `0600`; DXVK Wine selected | PASS |
| Retina UI write | Real checkbox `change` event | Persist per-AppID Retina setting | Saved true, then restored false | PASS |
| DXMT control restore | Select DXMT and reopen properties | Persist accepted default state | DXMT, MSync true, Retina false | PASS |
| Startup reconcile rate | Six-second settled counter delta | Fixed cadence without callback amplification | Seven scans, zero additional detail refreshes | PASS |
| GPTK managed bridge diagnosis | GPTK run-command plus private task log | Explain exit code 3 without guessing | Unity reached D3DMetal, then asserted in managed `lsteamclient` line 375 | PASS |
| GPTK bridge isolation experiment | Move only ledger-matched bridge DLLs out of the shared PFX | GPTK must launch without corrupting the prefix | Menu/map loading continued for 43 seconds; `WM_CLOSE` exit 0 | PASS |
| Steamworks renderer reconciliation | DXMT -> GPTK -> DXMT unit fixture | Remove incompatible managed bridge and restore it atomically | Two focused state-transition tests passed | PASS |
| GPTK native Steam launch | Renderer-aware bridge deactivation | D3DMetal/menu without bridge assertion | Menu reached; normal exit and AutoCloud completed at 18:11:28 | PASS |
| WineD3D native Steam launch | Bridge restoration plus WineD3D selection | Visible game, Steamworks, normal exit, Cloud | Unity used Vulkan fallback; Steamworks and Cloud passed at 18:13:20 | PASS |
| Final DXMT default | Restored DXMT/MSync configuration | D3D11, Steamworks, Workshop, clean exit | Accepted in 18 seconds; Cloud upload completed at 18:14:35 | PASS |
| Final complete matrix | All Node, Python, and shell tests | Release regression remains green | 64 Node, 40 Python, 25 shell contracts | PASS |
| Final live registry and Cloud | Read-only CDP probes | Dynamic eligibility and Cloud remain healthy | 34/34 managed, Garry's Mod excluded, Cloud enabled | PASS |
| One-click installer | Isolated component recorders | Build/install order and argument propagation | Hook -> launcher -> bridge -> runtime -> injection | PASS |
| One-click live preflight | Run top-level installer while Steam is active | Refuse before builds or file mutation | Exit 1 with explicit quit-Steam message | PASS |

## Error Log

| Timestamp | Error | Attempt | Resolution |
|-----------|-------|---------|------------|
| 2026-06-09 | Memory registry had no matching RealSteamOnMac entry | 1 | Continued from current repository and live-machine evidence. |
| 2026-06-09 | Steam CDP endpoint was unavailable | 1 | Confirmed current Steam lacks `-cef-enable-debugging`; plan a controlled debug relaunch after preserving repository state. |
| 2026-06-09 | Cloud page remained blank without a JS exception | 1 | Traced the shared settings store and found the native backend omitted `cloud_enabled`. |
| 2026-06-09 | Parallel tests raced while both built the same fat dylib | 1 | Re-ran build-writing tests sequentially; all passed. |
| 2026-06-09 | Computer Use could not start a capture stream | 2 | Recorded ScreenCaptureKit `-3811`; retained element-aware policy and used read-only CDP evidence. |
| 2026-06-09 | New native headers were accidentally appended after the final function | 1 | Strict `-Werror` build exposed undeclared atomic APIs; moved headers to the include block and rebuilt all three architectures. |
| 2026-06-09 | Rollback fixture lacked the new registry token | 1 | Added the same private token fixture required by UI installation, then reran the complete suite successfully. |
| 2026-06-09 | SteamUI getter near-branch allocator failed under the cold ASLR layout and logged every tick | 2 | Removed the redundant global getter hook; retained only allowlist-scoped data repair and native detail subscriptions. |
| 2026-06-09 | Shell matrix was first invoked by executable bit and stopped on a non-executable probe contract | 1 | Re-ran with the documented `sh "$test_file"` invocation; all 20 shell contracts passed. |
| 2026-06-09 | Native Play did not enter the compatibility-tool logging stub | 1 | Logs proved the request reached `CreatingProcess` and failed with `AppError_46`; mapping exists, so Phase 4 now targets post-init registration or scoped launch dispatch. |
| 2026-06-09 | First runtime package build stopped at Wine Staging `wine64` validation | 1 | Wine 11.10 uses unified `wine`; package now supplies a local `wine64 -> wine` compatibility symlink. |
| 2026-06-09 | First macOS bridge could not resolve `Steam_IsKnownInterface` | 1 | Added a macOS fallback instead of requiring the absent native export. |
| 2026-06-09 | `CreateInterface` fallback caused `VersionMismatch` | 1 | Generated and validated the 208 interfaces implemented by the pinned bridge. |
| 2026-06-09 | DXMT failed to create a Metal view | 1 | Recorded missing Wine exports; current Wine is not advertised as DXMT-capable. |
| 2026-06-09 | CrossOver Menu Helper appeared during independent launch | 1 | Disabled Wine menu integration; repeat launch contained no CrossOver process. |
| 2026-06-09 | PPG mod compiler survived normal game exit | 2 | Proved Wine PID 312 collided with macOS `searchpartyd`; added AppID-scoped PFX cleanup. |
| 2026-06-09 | Steam Cloud log rotated during final exit verification | 1 | Checked both `cloud_log.txt` and `cloud_log.previous.txt`; `AC Exit` and upload completion were present. |
| 2026-06-09 | Wine configure selected ARM64 despite x86_64 compiler flags | 1 | Ran `configure` itself under `arch -x86_64`; the host triplet and PE toolchain then resolved correctly. |
| 2026-06-09 | The first formal build used Apple's obsolete Bison | 1 | Put Homebrew Bison 3 first for both configure and make. |
| 2026-06-09 | A shared clone of a partial Wine cache could not fetch a promisor object | 1 | Reused the fully checked-out cache through APFS clone-copy instead of `git clone --shared`. |
| 2026-06-09 | GPTK installer could not attach an already-mounted image | 1 | Detached the inner read-only image before the outer image and reran the isolated install. |
| 2026-06-09 | Successful live installer run left its two GPTK images mounted | 1 | Removed the fragile mount-list condition, detach unique mount points directly with a force fallback, and passed a real idempotent reinstall cleanup check. |
| 2026-06-09 | Properties popup had no control panel despite four visible tools | 1 | Added the shared idle-tracker popup window registry and prioritized the compatibility combobox over the page root. |
| 2026-06-09 | Initial live startup accumulated over one thousand reconcile scans | 1 | Removed per-detail callback reconciliation and widened stale-detail retries to five seconds; settled cadence is now fixed. |
| 2026-06-09 | GPTK exited with code 3 after DXMT/DXVK Steamworks acceptance | 2 | Private game log proved the shared PFX loaded the Wine 11 Proton bridge under GPTK Wine 7.7. Temporarily disabling only ledger-matched bridge DLLs restored a normal GPTK launch and exit; runtime reconciliation now automates this boundary. |

## 5-Question Reboot Check

| Question | Answer |
|----------|--------|
| Where am I? | The Steam-native UI, multi-version tool catalog, reversible installer, updater, and release documentation are implemented and under final acceptance. |
| Where am I going? | Complete full regression, live PKG install/uninstall/reinstall, screenshots, and public release verification. |
| What's the goal? | Native macOS Steam downloads and launches Windows-only games through independent selectable compatibility tools. |
| What have I learned? | A shared PFX needs renderer-aware ABI reconciliation: GPTK Wine 7.7 must not inherit the Wine 11 Proton bridge. |
| What have I done? | Completed dynamic downloads, controls, actions, dependencies, transactional packaging, signed update manifests, and prior live GPTK/WineD3D/DXMT acceptance with Cloud intact. |

## 2026-06-10 Phase 7 Start

- Received eight screenshots and a release-focused redesign request.
- Confirmed the persistent right-side panel is caused by
  `mountControlPanels()` scanning every Steam document and accepting an anchor
  based on project-name text. The insertion target is not positively proven to
  be a properties compatibility page.
- Confirmed the current compatibility catalog is hard-coded in
  `script/patch_steamui.py`, while the installed standard Steam directory still
  contains only the legacy `realsteamonmac-experimental` tool.
- Confirmed the repository is private, has no GitHub release, and uses
  `codex/people-playground-experiment` as its default branch.
- Preserved the verified Cloud constraint: valid startup-time native
  compatibility-tool discovery is not re-enabled on Steam build `1780705203`.
- Selected a validated standard-directory scanner plus Steam API bridge so
  multiple versions can coexist without the known Cloud regression.
- Inspected CrossOver Preview's readable application resources. Its setup
  libraries and localized UI assets are available for behavioral research, but
  proprietary runtime binaries and unreviewed recipes will not be copied into
  the public project.
- Added the Phase 7 design and implementation plan:
  - `docs/superpowers/specs/2026-06-10-steam-native-release-design.md`
  - `docs/superpowers/plans/2026-06-10-steam-native-release.md`
- Replaced the hard-coded compatibility-tool installation location with
  `~/Library/Application Support/Steam/compatibilitytools.d/`.
- Added validated, deterministic discovery for side-by-side compatibility-tool
  versions while preserving unrelated user directories in the same root.
- Updated the UI patcher, launcher, installer, and rollback fixtures to use the
  standard Steam directory.
- Verified 19 Python catalog/patcher tests and all focused Steam UI patch,
  rollback, launcher, and injection installer shell contracts.
- Persisted the exact compatibility-tool ID through Steam UI, the authenticated
  native config service, and the per-AppID runtime configuration.
- Runtime package selection now follows each tool's immutable
  `runtime_package` metadata instead of collapsing all DXMT/GPTK versions to
  one renderer-wide `current` symlink.
- Added capability-aware control gating. DXMT 0.80 now enables its official
  NVEXT DLSS-SR-to-MetalFX path with `DXMT_ENABLE_NVEXT=1`; unsupported tools
  cannot save those controls.
- Verified 61 focused Node tests, 49 focused Python tests, and the native
  registry server, runtime installer, Steam injection installer, and launcher
  contracts after the tool-identity change.
- New prefixes now run `winecfg -v win10` immediately after `wineboot --init`.
- Connected Finder-backed executable selection and eight container operations
  to the authenticated background-job channel.
- Container removal is recoverable: the PFX is stopped and moved under the
  AppID state recovery directory rather than deleted.
- Added a managed MetalFX DLL ledger so GPTK and DXMT can replace each other's
  known files safely and remove them when the feature is disabled.
- Full checkpoint regression: 67 Node tests, 52 Python tests, and 25 shell
  contracts pass.
- Added an open-runtime installation mode that does not require or redistribute
  Apple GPTK/D3DMetal. When the user's official
  `~/Downloads/Game_Porting_Toolkit_3.0.dmg` is present, GPTK is imported
  locally; otherwise only DXMT, DXVK macOS, and WineD3D are exposed.
- The top-level installer now stops Steam on explicit request, reuses a prior
  clean rollback snapshot during updates, creates a new clean backup on first
  install, and writes a private `install-state.json`.
- Added a reversible uninstaller that restores Steam before moving only
  metadata-hash-matched first-party tools. User tools, game depots, and PFX
  directories remain in place.
- Added an Ed25519-signed release manifest, a CryptoKit verifier, a strict
  updater, and install/uninstall PKG build scripts. The release private key is
  stored outside the repository; only the public key is committed.
- Isolated packaging contracts passed package expansion, SHA-256 verification,
  release-manifest validation, signature verification, open-runtime filtering,
  and recoverable uninstall tests.
- Replaced the progress-style README with bilingual product documentation and
  added project history, public interface, third-party notice, and license
  files.
- Updated the dependency catalog with current checksum-pinned Microsoft Visual
  C++ x64 and x86 installers. DirectX and font recipes remain excluded until
  their multi-stage installation and licensing can be represented safely.
- Replaced the remaining compact compatibility header with a visible
  Steam-style "Force the use of a specific Steam Play compatibility tool"
  checkbox and selector. Live acceptance showed DXMT 0.80, DXVK macOS 1.10.3,
  GPTK 3.0, and WineD3D 11.10 in one native dropdown.
- Added hash-restricted adoption for MetalFX DLLs written by older project
  versions before the managed ledger existed. Unknown DLLs are still rejected.
- Reinstalled against the preserved clean Steam build 1780705203 backup and
  confirmed the People Playground library page no longer mounts a persistent
  right-side panel.
- Live compatibility-page acceptance passed:
  - DXMT -> GPTK -> DXMT switching persisted the exact compatibility-tool ID.
  - Run Command opens a Steam-style command/arguments/environment/log dialog.
  - Install Windows Components opens a searchable dependency dialog.
  - Container Operations exposes Finder-backed, Wine, controller, restart,
    task-manager, stop, and recoverable removal actions.
- Live DXMT 0.80 MetalFX acceptance passed. Enabling installed the package
  `nvngx.dll` and `nvapi64.dll` with a SHA-256 ledger; disabling removed only
  those ledger-matched files and the ledger itself.
- The full direct uninstall/reinstall cycle passed on the live machine:
  - Steam was restored to its original `steam_osx` bootstrap.
  - All four managed compatibility tools moved into the recoverable uninstall
    directory.
  - The People Playground executable and PFX `user.reg` retained identical
    pre/post-uninstall SHA-256 hashes.
  - The validated 3.0 GB immutable runtime cache was APFS-cloned from the
    uninstall recovery directory and the one-click installer completed again.
- Final Phase 7 source regression passed:
  - 67 Node tests.
  - 60 Python tests.
  - 27 shell contract files, including packaging, install, uninstall,
    injection, runtime, launcher, backup, and restore paths.
- Cropped the live Steam acceptance captures into `docs/images/` and added
  tool-selection, command-runner, and dependency-installation previews to both
  product READMEs. The public crops exclude the Codex window and desktop.
- Built the final `v0.1.0` release into an isolated directory before replacing
  `dist/`. Verification passed:
  - Both PKG payload SHA-256 values match `SHA256SUMS`.
  - The Ed25519 release-manifest signature verifies with the committed public
    key.
  - The manifest targets repository `dazi2011/RealSteamOnMac`, tag `v0.1.0`,
    macOS 14+, arm64, and Steam build `1780705203`.
  - Package expansion contains the current UI, runtime manager, compatibility
    tool metadata, license notices, installer scripts, and prebuilt Steamworks
    bridge.
  - `pkgutil --check-signature` reports no Apple installer signature because no
    Developer ID Installer identity is available; this is disclosed in both
    READMEs and will be repeated in the release notes.
- Public-repository audit found that release packaging previously depended on
  an ignored local DXMT macdrv artifact. `build_release_pkgs.sh` now accepts an
  explicit validated package, rebuilds the pinned package when its default is
  absent, verifies its checksums and source-commit metadata, and enforces
  Mach-O/signature checks outside test-fixture mode.
- Removed personal absolute paths from tracked tests and engineering documents.
  The untracked user-owned RTF remains untouched and will not be staged.
- Final post-audit regression passed again: 67 Node tests, 60 Python tests, and
  all 27 shell contract files.
- Rebuilt `dist/` after the packaging fix. Final release hashes:
  - `RealSteamOnMac-Install.pkg`:
    `56602a98e37498eea8daf5cd9dc2f9ca6634e4a006f7bbff0b02ff2683a14d46`
  - `RealSteamOnMac-Uninstall.pkg`:
    `e153808464657b710ed80016dc41c9543338d4a8745eb564ce8a7017b77150b7`

## 2026-06-10 Steam Public Beta 1780965181 Support

- Detected a cached pending Steam Public Beta manifest for build
  `1780965181` while the live installed runtime remained on `1780705203`.
- Built the upstream `valvevz` v1.0 decompressor in a temporary directory and
  verified each cached VZip archive against Valve's manifest before offline
  extraction. No live Steam files were changed during this analysis.
- Recorded the new arm64 identities:
  - `steamclient.dylib` UUID
    `04B50ECB-07FF-30DF-A03B-1EB9292B856B`, SHA-256
    `d0945fc67880d048d163cf071ec9cc264cb3618c56cfb73520da36de0188f13e`.
  - `steamui.dylib` UUID
    `87B914EC-F267-3559-8063-F21D85D896DE`.
- Verified the new build-specific patch offsets:
  - compatibility gate `0x00A00874`;
  - installation gate `0x00624600`, fall-through `0x00624604`, invalid target
    `0x00624630`;
  - SteamUI platform getter `0x005EAC24`;
  - arm64 `posix_spawn` pointer slot remains `0x018F9500`.
- Confirmed the install-gate instruction remains `tbnz w8, #4` with the
  expected decoded branch target, and confirmed the SteamUI getter signature
  is unique in the arm64 slice.
- Added strict build profiles for both `1780705203` and `1780965181` to the
  native hook and offline steamclient patcher. Rosetta profiles remain absent,
  preserving the native-arm64 fail-closed policy.
- Added the new compatibility-chunk SHA-256
  `f77316131cbed91865a800103bbda855a43395eecfb2bc866bc58c33fdea4c69`.
  The chunk still contains exactly two supported page anchors and patches to
  `f53e16c4066cecb367c12d9a9f4e93843467d5cbe298929bedda3e3c43581515`.
- Updated release manifests and installer state to advertise and record both
  supported builds.
- Added a rollback safety rule: an installation state from one Steam build
  cannot reuse its clean backup on another build. Users must uninstall, let
  Steam update, and reinstall so the new runtime receives a matching clean
  snapshot.
- Focused validation passed for both real steamclient binaries, both SteamUI
  resource profiles, install-state build detection, unsupported-build
  rejection, and the native dual-architecture hook build.
- Full evidence is preserved in
  `docs/research/steam-public-beta-1780965181-validation-2026-06-10.md`.
- Final `0.1.1` source regression passed:
  - 67 Node tests.
  - 61 Python tests.
  - 27 shell contract files.
- Built the release PKGs and independently verified:
  - release-manifest Ed25519 signature: valid;
  - package metadata and bundled `VERSION`: `0.1.1`;
  - supported Steam builds: `1780705203`, `1780965181`;
  - `RealSteamOnMac-Install.pkg` SHA-256:
    `68a3e79e20a10dee8e9e0b627b97dd2330a6a9304bfd0aadafc6b3df16ef6eaf`;
  - `RealSteamOnMac-Uninstall.pkg` SHA-256:
    `175ec95099fcdc70a3c4531a2723ab9310843634bbacd9c31101f7711a441b6f`.
- `pkgutil --check-signature` confirms both PKGs remain unsigned because a
  Developer ID Installer identity is unavailable. The limitation remains
  disclosed in the bilingual README and release notes.
- Completed the live transition from the clean `1780705203` backup to official
  Steam Public Beta `1780965181`, then installed the packaged `0.1.1`
  postinstall payload. The new clean rollback snapshot is
  `/Users/wudazi/RealSteamOnMac-Backups/steam-20260610T054049Z`.
- Verified the live Valve files and UUIDs exactly match the offline profile,
  and the cold-start hook log reports the build-specific
  `build=1780965181` installation gate before expanding from the bootstrap
  AppID to all 34 managed Windows-only games.
- Preserved People Playground across the full uninstall, Steam update, and
  reinstall cycle. Its executable and PFX `user.reg` SHA-256 values were
  identical before and after the transition.
- Fixed a live-only compatibility-page mount failure. On macOS, Steam omits
  the compatibility dropdown while its native row is disabled; the UI bridge
  previously required exactly one dropdown and therefore never mounted.
  The bridge now falls back to the exact native force-tool row, ignores its
  own selector during later scans, and temporarily hides the unusable Steam
  row while the replacement is active.
- Added regression coverage for:
  - a compatibility page with no native dropdown;
  - repeated scans after the project selector is mounted;
  - hiding and restoring Steam's disabled native compatibility row.
- Final live UI acceptance on build `1780965181` passed:
  - only one enabled Steam-style force-tool row is visible;
  - DXMT 0.80, DXVK macOS 1.10.3, GPTK 3.0, and WineD3D 11.10 appear in the
    native dropdown;
  - DXMT -> GPTK -> DXMT switching updates the authenticated per-AppID config;
  - DXMT 0.80 MetalFX can be enabled and disabled through the UI;
  - the properties page scrolls to Run Command, Install Windows Components,
    and Container Operations;
  - all three secondary dialogs render inside the Steam properties window and
    close with Escape;
  - closing properties returns to the normal People Playground library page
    with a green Start Game action and no persistent right-side panel.
- Post-fix release regression passed:
  - 70 Node tests.
  - 61 Python tests.
  - 27 shell contract files.
  - `git diff --check`, shell syntax checks, Python bytecode compilation, and
    JavaScript syntax checks.
- Rebuilt the final `0.1.1` release after the compatibility-page fix:
  - install PKG SHA-256:
    `68a3e79e20a10dee8e9e0b627b97dd2330a6a9304bfd0aadafc6b3df16ef6eaf`;
  - uninstall PKG SHA-256:
    `175ec95099fcdc70a3c4531a2723ab9310843634bbacd9c31101f7711a441b6f`;
  - release manifest SHA-256:
    `1f836796b117cdaa8b402313129bb15c87f8cebcb33db9a14886e2f86be6d334`;
  - manifest signature SHA-256:
    `c0cdd74340b1b0e6262dc52427e2511a9bb0f48fb6cccf69e5d848cf17f2775d`;
  - publication timestamp:
    `2026-06-10T06:28:32Z`.
- Expanded the final PKGs independently and confirmed:
  - both `PackageInfo` versions and the bundled `VERSION` are `0.1.1`;
  - the bundled UI SHA-256 matches the committed source;
  - both Steam build profiles and exact arm64 UUIDs are present;
  - the packaged postinstall script matches the repository source;
  - the Ed25519 release-manifest signature and every declared size/hash verify.
- Executed the final install PKG's packaged postinstall payload on the live
  `1780965181` installation. The installed source, packaged source, support
  copy, and active SteamUI copy all have SHA-256
  `6621eb7e36dc456aae84b305fce1d0a9c19c40b79c95fa84dde4b80cc90607fe`.
- Final packaged cold-start acceptance preserved the People Playground
  executable and PFX hashes, rebuilt the 34-AppID native registry, and rendered
  the corrected single-selector compatibility page.
- Published public GitHub Release `v0.1.1` from commit
  `e0fd2601c4e531fd85f74e97d1eb8d5758e0c577`.
- Re-downloaded all five public release assets and verified they are byte-for-
  byte identical to `dist/`; GitHub's reported SHA-256 digests also match.
- Verified the downloaded manifest signature again with the committed public
  key. GitHub's latest-release API returns `v0.1.1`, and the installed updater
  reports `{"status":"current","version":"0.1.1"}` on Steam build
  `1780965181`.
- Added a startup-race integration scenario that first synchronizes two managed
  AppIDs, exposes a transient empty `appStore.allApps`, then restores the
  initialized store. The test failed before the fix because the managed
  predicate became false and native subscriptions were removed.
- The browser now rejects a transient empty overview store when a nonempty
  managed registry is already active. It preserves the accepted registry and
  subscriptions, while a later authoritative nonempty scan can still remove an
  actually unmanaged game.
- Focused SteamUI regression after the fix: 64 Node tests passed across
  `test_steamui_runtime.mjs` and `test_steamui_policy.mjs`.
- Added real-shape Steam ACF fixtures for fully installed, files-missing,
  staged-only, empty-directory, and missing-`InstalledDepots` states.
- The focused installation-state suite failed RED with `FileNotFoundError` for
  the intentionally absent `runtime/steam_app_state.py`.
- Added a bounded structured VDF document API and a read-only Steam app-state
  inspector. Launch context now requires `FullyInstalled`, nonzero manifest and
  depot sizes, at least one valid installed depot, nonempty local content, and
  no blocking Steam state.
- Staged-only, files-missing/corrupt, empty-directory, missing-depot, and
  unknown-state cases fail closed with a diagnostic directing callers back to
  Steam install or repair actions. No ACF file is rewritten.
- Verification passed:
  - 5 installation-state tests;
  - 39 runtime-manager tests;
  - 8 compatibility-tool catalog tests;
  - Python bytecode compilation and `git diff --check`.
- Read-only live classification matched the reported field state for RDR2,
  Hogwarts Legacy, Black Myth: Wukong, and Aimlabs.
- Recovered the current Steam `EDisplayStatus` enum directly from the installed
  `steamui` module: statuses span `0..39`, `14` is InvalidPlatform, `15` is
  undefined, and `38/39` are download/update failures.
- Added RED policy coverage for a staged-only Black Myth shell reported as
  backend status `11`, exact preservation of validation/download/update/error
  states, and rejection of undefined or out-of-range display statuses.
- The focused policy run failed in exactly three places: staged-only target
  selection, undefined status `15`, and full staged-shell reconciliation.
- Restricted browser normalization to the current Steam display-status enum,
  excluding InvalidPlatform and undefined value `15`.
- Added a narrow consistency rule: an explicit zero-byte or `installed=false`
  ReadyToLaunch detail is normalized to Steam's ReadyToInstall state instead.
  All valid active, queued, paused, repair, Cloud, download-failure, and
  update-failure states remain unchanged.
- SteamUI policy/runtime regression passed 76 tests plus JavaScript syntax and
  whitespace validation.
- Added RED contracts for a managed-only native repair dispatcher that selects
  exactly one of `VerifyApp`, `ResumeAppUpdate`, or `OpenInstallWizard`, while
  treating active install/download/validation states as no-ops.
- The focused suite failed only because `chooseNativeRepairAction` and
  `requestNativeRepair` do not exist yet; the other 72 policy tests passed.
- Implemented a managed-only repair dispatcher and exposed it to the injected
  Steam context as `__REALSTEAMONMAC_REQUEST_REPAIR__`. It accepts only an
  AppID, reads current Steam state, and calls one fixed Valve API without
  arbitrary arguments or filesystem mutation.
- Full VM coverage proved install and verify dispatch, active-state no-op
  behavior, transient-empty-store refusal, and rejection of unmanaged AppIDs.
- Final Task 4 verification passed 78 Node tests, JavaScript syntax,
  `git diff --check`, and the native authenticated registry-server harness.
- A real Black Myth resume was intentionally deferred to the controlled game
  matrix because it would immediately mutate the 149.8 GB download queue.
- Started Task 5 with six launch-descriptor contracts covering Hogwarts
  Legacy's stale development target, Aimlabs' erroneous macOS `.app` target,
  RDR2's explicit launcher, multiple legitimate Windows options, complete
  failure, AppID mismatch, and path traversal.
- Corrected the implementation plan to use the repository's real
  `tests/test_spawn_redirect.sh` harness path.
- Task 5 RED verification failed at import with `FileNotFoundError` for the
  intentionally absent `runtime/steam_launch_descriptor.py`; none of the new
  cases can pass through the old executable-directory heuristic.
- Added a bounded, duplicate-key-rejecting launch-descriptor parser. It
  validates schema, AppID, entry IDs, OS, relative executable and working
  directory paths, arguments, defaults, PE headers, and installation-root
  containment.
- Task 5 descriptor verification passed all 6 fixtures plus Python bytecode
  compilation and whitespace validation.
- Static inspection of the installed SteamUI launch workflow found the native
  decoded-data API `SteamClient.Apps.GetLaunchOptionsForApp(appid)`. Added a
  read-only probe that records JSON fields plus own/prototype property names
  for RDR2, Hogwarts Legacy, Aimlabs, and People Playground.
- Relaunched native Steam normally through the installed launcher with
  `-cef-enable-debugging`; CDP became ready. The first launch-options probe
  reached the API but all four calls returned opaque bridge error objects, so
  the probe now preserves enumerable and own error fields for diagnosis.
- A second live probe showed `GetLaunchOptionsForApp` exposes only UI metadata:
  Aimlabs returned index, description, name, type, and VR flags; RDR2,
  Hogwarts Legacy, and People Playground returned empty arrays. It does not
  expose executable paths, working directories, or arguments.
- A read-only v41 appinfo prototype decoded all four target records and matched
  each binary VDF SHA-1. Added RED contracts for verified v41 decoding,
  case-insensitive requested-target matching, and hash-corruption rejection.
- The corrected v41 fixture reached the intended RED boundary: the existing
  six JSON descriptor tests passed, while exactly three appinfo tests failed
  because `build_launch_descriptor_from_appinfo` is not implemented.
- Implemented bounded Steam appinfo v40/v41 decoding with universe, record
  length, string-table, KeyValues type/depth/node, duplicate-key, and binary
  SHA-1 validation. Generated launch records pass through the same descriptor
  validator as JSON inputs.
- All 9 descriptor tests passed. Read-only validation against the live v41
  cache resolved:
  - Aimlabs requested entry `1` to Windows entry `0` / `AimLab_tb.exe`;
  - Hogwarts requested entry `0` to default entry `13` /
    `HogwartsLegacy.exe`;
  - People Playground and RDR2 remained on entry `0`.
- Added runtime integration RED coverage with a verified v41 fixture. The old
  runtime failed exactly at the intended boundaries: no working directory or
  launch-entry metadata, no requested-target input, and directory-wide EXE
  guessing when the appinfo target was missing.
- Runtime launch, action, and recovery context now use only the verified Steam
  launch descriptor. Directory-wide EXE discovery remains diagnostic-only.
  The selected working directory and arguments flow into dry-run plans and the
  game process cwd.
- Focused verification passed 51 Python tests. Live read-only dry runs:
  - Aimlabs' requested `AimLab.app` resolved to `AimLab_tb.exe` with its
    existing GPTK configuration;
  - RDR2 retained `PlayRDR2.exe` with DXMT;
  - Hogwarts Legacy failed closed at its existing `repair-required` install
    state before launch resolution.
- Added native spawn-decision RED cases for managed missing `.exe`, managed
  `.app`, unmanaged missing targets, and an existing non-PE `.exe`.
- Native RED verification stopped at
  `managed missing EXE target was not redirected`; source contracts also
  failed because the recovery predicates do not exist yet.
- The allowlist-scoped spawn bridge now redirects existing PE targets,
  recoverable missing `.exe`/`.app` targets, and `.app` selections for managed
  Windows-only games. Existing non-PE `.exe` files, native executables, and
  unmanaged AppIDs remain on Steam's original spawn path.
- Task 5 final verification passed 51 Python tests, the spawn redirect native
  harness, compatibility-gate contract, hook environment-isolation contract,
  JavaScript probe syntax/contract, Python compilation, and whitespace checks.
- Added `docs/research/steam-launch-descriptor-2026-06-11.md` with pinned
  reference commits, live launch records, validation limits, and rollback.
- Captured a read-only RDR2 prefix snapshot before Rockstar recovery work.
  The Launcher payload, uninstall record, and service exist, but Social Club
  files and both Steam prerequisite completion keys are absent.
- The Rockstar installer log stops after registry writes without a normal
  completion record. The service later reaches `SERVICE_RUNNING`, proving
  that service health alone cannot classify the prerequisite chain as
  complete.
- Recorded depot installer, Launcher executable, and Wine registry sizes and
  SHA-256 values in
  `docs/research/rdr2-rockstar-recovery-2026-06-11.md`. No prefix, game,
  manifest, or registry file was mutated during collection.
- Added six Rockstar recovery contracts for ordered partial-state repair,
  complete-state no-op behavior, tampered installer rejection, malformed PE
  rejection, selective snapshot hashing, exact argv execution, data
  preservation, and private mutation reports.
- Task 6 RED verification failed at import with `FileNotFoundError` for the
  intentionally absent `runtime/launcher_recovery.py`. The test fixtures and
  runner did not reach any unrelated failure.
- Implemented the bounded launcher recovery engine. It validates AppID,
  depot-relative paths, exact installer size/SHA-256, PE headers, fixed argv,
  success codes, and substantive PE/registry postconditions.
- Recovery snapshots are selective, size/file-count bounded, atomically
  published, and include hashes for registry, Rockstar, user, and runtime-log
  evidence. Unknown or contradictory state fails closed with the snapshot
  path instead of deleting or replacing the prefix.
- The focused recovery suite now passes all 6 tests plus Python bytecode and
  whitespace validation.
- Added integration RED coverage for the repository RDR2 recipe, recovery
  ordering before the game process, and launch blocking on recovery failure.
  RED failed only because AppID `1174180` is absent from the catalog and the
  runtime has no `execute_configured_launcher_recovery` entry point yet.
- Added the pinned RDR2 recipe to `config/dependencies.json`: Social Club
  `/silent` precedes Launcher `/s /t`, using the exact live depot sizes and
  SHA-256 values.
- CrossOver's existing RDR2 bottle confirmed the substantive postconditions:
  Social Club helper/product/uninstall state and Launcher/Steam-helper/product/
  uninstall state. CrossOver remains a read-only control and runtime
  dependency is still forbidden.
- Runtime launch now executes configured launcher recovery after prefix
  preparation and before the game process. A recovery error blocks launch and
  retains the snapshot/report path; games without a recipe are unchanged.
- Added an explicit `recover-launcher` CLI for controlled acceptance and
  support use.
- Automated verification passed 7 launcher-recovery tests, 44 runtime-manager
  tests, and 22 launch-descriptor/app-state/tool-catalog tests, plus JSON,
  Python bytecode, and whitespace checks.
- The first live snapshot exposed a Wine path-boundary bug: the prefix
  `Documents` link points at host `~/Documents`, so a snapshot glob began
  reading host Rockstar cache data. The process was interrupted before any
  installer ran, and its single incomplete temporary snapshot was removed.
- Added RED coverage requiring glob matches whose resolved path escapes the
  prefix to be skipped and recorded as `external_skipped`. RED failed because
  the manifest and containment guard do not exist yet.
- Added the post-expansion containment guard. Parent-symlink escapes are now
  recorded as `external_skipped` and never opened; the incomplete 103 MB
  temporary snapshot from the failed attempt was the only deleted artifact.
- Verification passed all 8 recovery tests and all 44 runtime-manager tests,
  plus Python bytecode and whitespace checks.
- Executed the guarded RDR2 recovery on the live prefix. The private 103 MB
  snapshot and mutation report were published with restrictive permissions;
  Social Club and Launcher installers both returned `0`, and all seven PE and
  registry postconditions passed.
- A second live recovery returned `state: complete` without creating a
  snapshot, report, or installer process. Both game executable hashes remained
  unchanged.
- Post-recovery GPTK launch no longer reports an incomplete Rockstar install,
  but it does not reach `RDR2.exe`. `PlayRDR2.exe` remained idle for more than
  four minutes and the Launcher log stopped at `Creating Steam min mode
  launch`; the AppID-scoped GPTK wineserver was then stopped cleanly.
- CrossOver's RDR2 Steam logs contain repeated historical complete process
  chains through `RDR2.exe`, including multi-minute D3D12 sessions. A fresh
  2026-06-11 control could not proceed because that bottle's Windows Steam was
  at `WaitingForCredentials`; no account tokens were copied.
- Task 6 recovery acceptance is complete. End-to-end RDR2 launch remains open
  at the GPTK/Steam min-mode handoff and must not be reported as fixed.
- Built an isolated Proton 7 `lsteamclient` candidate for GPTK/Wine 7.7 from
  pinned Proton commit `c5ad95671cecaf03c4a92500de84b542add585d1` and the
  locally cached CodeWeavers 22.1.1 Wine 7.7 source.
- Replaced Proton 7's unsupported macOS input compile guard with the newer
  pure Carbon key-code map and used a dedicated x86_64 system-clang C++
  `wineg++` wrapper to avoid clang 8/current-libc++ incompatibility.
- Diagnosed the first DLL-load failure (`symbol not found in flat namespace
  '_CloseHandle'`) as missing Wine import libraries caused by
  `winegcc --wine-objdir`. Relinking with explicit `advapi32`, `user32`,
  `winecrt0`, `kernel32`, and `ntdll` removed every unresolved Win32 API
  symbol from the Mach-O bundle.
- Added a cache-only diagnostic export and invoked it through GPTK's own
  `rundll32.exe` in an independent prefix. The bridge successfully loaded the
  native `steamclient.dylib` and returned `SteamClient020` with
  `iface=0x373b70` and `return_code=0`; no Wine assertion occurred.
- The cache-only diagnostic export is not a release artifact. The next build
  step removes it, regenerates the clean PE/Mach-O pair, and packages the
  result as a GPTK-specific renderer variant using `lsteamclient.dll.so`.
- Extended the runtime manifest reader with renderer-specific Steamworks
  bridge variants while preserving the existing single-bridge schema.
  Legacy manifests still remove the Wine 11 bridge for GPTK exactly as before.
- New variants declare their package-local Windows DLL, Unix companion, and
  fixed Unix install name. Only `lsteamclient.so` and
  `lsteamclient.dll.so` are accepted, and resolved payload paths must remain
  inside the immutable runtime package even through symlinks.
- The shared-prefix ledger safely replaced the Wine 11 bridge with the GPTK
  bridge during a DXMT-to-GPTK test and retained the existing unmanaged-file
  and modified-managed-file refusal behavior.
- Full runtime-manager verification passed 47 tests plus Python bytecode and
  whitespace checks.
- Added `patches/proton7-lsteamclient-macos.patch` with the macOS Carbon
  key-code conversion and a dedicated
  `script/build_gptk_lsteamclient_bridge.sh`.
- The builder pins Proton
  `c5ad95671cecaf03c4a92500de84b542add585d1`, CodeWeavers source SHA-256
  `cdfe282ce33788bd4f969c8bfb1d3e2de060eb6c296fa1c3cdf4e4690b8b1831`,
  and Apple formula commit
  `2bc44284e24d39ed64d6f492a0e1f4c47a5ced08` plus formula SHA-256
  `7a124b8e74edd3f453ef366e4e103608857801fbc5e085dc6fe885d57b6c9568`.
- A clean build exposed and resolved four reproducibility faults: macOS Bison
  was too old, BSD patch could reverse an already applied patch, the Apple
  DATA stream cannot be globally dry-run, and Wine's generated `-DCXX` macro
  can wrap across lines for long paths.
- The cold build and an identical second invocation both passed. The formal
  output is a minimum-macOS 10.14 x86_64 Mach-O
  `lsteamclient.dll.so` plus a PE32+ Wine placeholder and complete build
  metadata/SHA256SUMS.
- A separate cache-only probe DLL loaded the formal output through GPTK's own
  `rundll32.exe`. Native Steam returned `SteamClient020` with
  `module=0x74940000`, `iface=0x373b80`, and `return_code=0`; the formal bridge
  exports no `BridgeSmoke` symbol.
- Static builder contract, shell syntax, patch applicability, artifact format,
  symbol, linkage, minimum-version, checksum, idempotence, and formal live
  interface smoke checks all passed.
- Extended the runtime package installer with a separate
  `--gptk-steamworks-bridge` input and a new immutable package suffix. Wine 11
  bridge files are installed only into DXMT, DXVK, and WineD3D; the Wine 7.7
  bridge is installed only into GPTK with its required
  `lsteamclient.dll.so` Unix companion name.
- Runtime manifests now emit renderer-specific bridge variants for all four
  renderers. The existing runtime reader retains legacy-manifest support.
- The one-click installer builds both pinned bridges for GPTK installs and
  only the Wine 11 bridge for open installs. Release PKGs embed both formal
  payloads, while `postinstall` forwards the GPTK payload only when the user
  has supplied the GPTK DMG.
- Installer, runtime-package, and release-packaging contract tests passed.
  The release test built and inspected temporary install/uninstall PKGs,
  verified both package hashes, and validated the signed release manifest.
  All 47 runtime-manager tests and whitespace/shell syntax checks also passed.
- Built and activated the full immutable dual-bridge runtime package. Every
  staged and installed checksum passed twice, all four manifest variants
  resolved to the expected ABI-specific payloads, no staging directory
  remained, and the previous package was retained for one-link rollback.
- Post-activation CLI acceptance found that the installer had not deployed
  `launcher_recovery.py`, `steam_app_state.py`, or
  `steam_launch_descriptor.py`. The package and bridge payloads were valid,
  but the runtime entry point failed before argument parsing; module
  deployment is now part of the activation transaction.
- A real temporary `activate_package` run deployed all four imported modules
  and the resulting CLI completed `--help`. Verification also passed 69
  related Python tests, the one-click installer contract, and a fresh pair of
  temporary release PKGs with signed-manifest validation.
- Re-activated the live dual-bridge package idempotently and verified the
  installed runtime import closure. `prepare-prefix` atomically replaced both
  managed Steam DLLs in AppID 1174180 with the formal GPTK bridge hash
  `264b3fcb0624f6e9fb04642cd0433033a3c8479878f27e5798f84c9228309228`;
  the ledger records the new package and bridge as active.
- A bounded RDR2 launch reached the current Rockstar Launcher with the correct
  `-steamAppId=1174180` and game path, but the log again ended at
  `Creating Steam min mode launch`; no `RDR2.exe` process appeared after
  88 seconds. The AppID-specific GPTK wineserver was stopped cleanly, and the
  running CrossOver Steam control PIDs were unchanged.

## 2026-06-11 Steam-Native Compatibility Control Acceptance

- Added a third guarded SteamUI patch anchor for the native compatibility
  component. For managed AppIDs only, Steam's effective `bCompatEnabled`
  predicate now evaluates true; the existing Steam checkbox, dropdown,
  `GetAvailableCompatTools`, and `SpecifyCompatTool` paths remain intact.
- Disabled the runtime call that hid Steam's native row and mounted the
  project replacement panel. The legacy panel helpers are no longer exported
  and are unreachable while their actions await migration to Steam-owned
  controls.
- Added migration coverage for the previous static gate, the previous
  dynamic-page-only gate, and clean Steam build changes with stale backups.
  Unknown resource hashes and altered anchor counts still fail closed.
- During live restart testing, Steam updated the compatibility chunk to
  build `1781139754`, SHA-256
  `387e1b1aacdcbddd5b1fbf65b64c9f5222cfe60d917568999c2c7ddedfdf6b0a`.
  The new source retained exactly two page anchors and one control anchor, so
  it was added as a separately verified profile and its clean file replaced
  the old-build rollback backup.
- The installed support patcher and UI source were atomically refreshed.
  Launcher startup then logged `Steam UI patch verified`; installed resource
  verification reported two managed page gates, one managed native-control
  gate, and one index injection.
- Live Steam properties acceptance for People Playground passed:
  the native checkbox was visible with `disabled=false`, `checked=true`, and
  a React `onChange` function; the native `DialogDropDown` rendered DXMT 0.80,
  DXVK macOS 1.10.3, GPTK 3.0, and WineD3D 11.10 as four `role=option` items.
  The page contained zero `.realsteamonmac-controls`, zero project modal
  layers, and zero hidden native rows.
- CrossOver Preview control PIDs `19863`, `19885`, `20242`, `20269`, and
  `73736` were unchanged across both Steam restarts.
- Automated verification passed 14 Python patcher tests, the shell install /
  verify / restore contract, 77 JavaScript runtime/policy tests, JavaScript
  syntax, Python bytecode, and whitespace checks.

## 2026-06-11 Raw Compatibility Payload Discovery

- Read the user-authored `codex LOOKLOOK ITTTTT!!!!!!!.rtf`. It adds two
  mandatory live acceptance defects: the native compatibility checkbox must
  stop toggling about once per second, and Steam's native controller page must
  be made readable without replacing it with a project-owned fake page.
- Extended `runtime/compat_tool_catalog.py` without changing the existing
  managed-wrapper contract. A child containing any managed file still requires
  `run`, both VDF files, and `realsteamonmac.json`.
- A user can now place a complete raw GPTK, DXMT, DXVK, or Wine directory
  directly below Steam's `compatibilitytools.d`. The scanner derives a stable
  tool id, display name, renderer, version, current base package reference, and
  conservative capability map from the payload itself.
- GPTK validation reads the bounded D3DMetal `Info.plist` and requires the
  shared D3D library plus matching D3D11/DXGI Unix and Windows modules. DXR is
  enabled only when both D3D12 modules exist; MetalFX requires NVAPI plus an
  NVNGX-to-MetalFX module.
- DXMT requires `winemetal.so`, D3D11, and DXGI. DXVK requires D3D9 and D3D11.
  A full raw Wine requires executable Wine and wineserver launchers plus both
  NTDLL architecture modules, and starts with conservative optional
  capabilities disabled.
- Required raw files may use internal symlinks, matching official GPTK and
  CrossOver layouts, but every resolved target must remain within the same
  compatibility-tool directory. Suspected but incomplete payloads fail closed
  instead of disappearing from the catalog.
- Fourteen catalog tests and fourteen SteamUI patch tests passed, including
  raw-tree discovery, incomplete-tree refusal, symlink-escape refusal, and
  capability gating. A read-only scan of the live directory retained the
  current four managed entries unchanged.
- The full Python discovery suite passed 102 tests. It exposed stale
  native-control fixtures in the install and launcher shell contracts; both
  fixtures now contain the real control anchor and expect all three managed
  gates.

## 2026-06-11 Native Compatibility Selection Stability

- Reproduced the RTF-reported checkbox flicker in the live People Playground
  properties window. A 15-second, 250 ms CDP trace captured the native React
  checkbox switching true/false repeatedly while local storage continuously
  selected `realsteamonmac-dxmt`.
- Confirmed the conflict source: Steam's native detail refresh clears the
  macOS compatibility fields, then the one-second project reconcile restores
  them. The persistent native mapping was also stale at
  `realsteamonmac-experimental`.
- Added a stable selected-tool accessor for Steam's existing compatibility
  component. The guarded chunk patch now uses it only when native detail
  fields are empty, both for the native checkbox and the native dropdown's
  selected option.
- A first live attempt restored Steam's original `SpecifyCompatTool` call for
  project tools. It returned without persisting the unknown tool, left the
  legacy mapping unchanged, and raced Steam startup before the global
  navigator context existed. The main window then failed to initialize.
- Removed that unsafe project-tool native call while retaining the stable
  checkbox/dropdown data fallback. Native persistence remains blocked on a
  genuine macOS backend registration mechanism that does not reactivate
  `STEAM_EXTRA_COMPAT_TOOLS_PATHS` and its proven Cloud regression.
- Added migration from the currently installed native-control patch. Unknown
  hashes and unexpected checkbox/dropdown anchor counts still fail closed.
- Pre-deployment verification passed 15 patcher tests, 77 JavaScript
  runtime/policy tests, SteamUI install/verify/restore, Steam injection,
  launcher, JavaScript syntax, Python bytecode, and whitespace checks.

## 2026-06-11 Native Selection Corrective Live Acceptance

- Committed and pushed `d625a16` after 103 Python tests, 83 JavaScript tests,
  every shell contract test, JavaScript syntax, and whitespace checks passed.
  The shell pass also corrected the restore fixture to use the current native
  checkbox and selector anchors.
- Backed up the installed UI source and compatibility chunk at
  `~/Library/Application Support/RealSteamOnMac/backups/`
  `native-write-deferral-20260611T140708Z`, atomically installed UI version 12,
  and verified the installed SteamUI patch.
- A controlled native Steam restart restored the full library window. The
  current helper session emitted no new global-navigator error, chunk
  TypeError, or browser-frame disconnect; CrossOver Preview control PIDs
  `19863`, `19885`, and `73736` remained unchanged.
- The People Playground properties window used Steam's native compatibility
  checkbox and `DialogDropDown`. A 10-second trace sampled the page 50 times
  and found one state only: checked `true`, checkbox enabled, selected
  `DXMT 0.80`, dropdown enabled, zero project panels, and zero project modals.
- Opening the native dropdown produced exactly four `role=option` entries:
  DXMT 0.80, DXVK macOS 1.10.3, GPTK 3.0, and WineD3D 11.10.
- A persistent Playwright CDP attachment again made Steam's debug endpoint
  unresponsive. Repeating the same navigation with the project's one-shot
  WebSocket evaluator completed successfully and left CDP healthy. Continue
  live Steam UI verification with short, immediately closed CDP sessions.

## 2026-06-12 Wine Game Controller Readability Correction

- Re-read the user's clarification and corrected the target: the requested
  interface is Wine's Game Controllers panel from `control.exe joy.cpl`, not
  Steam's native Steam Input configurator. The 2026-06-11 interpretation was
  wrong.
- Removed the SteamUI code that searched every second for
  `SP Controller Configurator_*`, resized that native window, and applied
  document zoom. Steam Input is again completely owned and rendered by Steam.
- Measured the actual Wine panel in the People Playground prefix. At the
  existing 96 DPI it was `250x311` points; 144 DPI yielded `373x436`; 192 DPI
  yielded a readable `496x562` panel with complete controls and no clipping.
- Added a controller-only runtime path that reads
  `HKCU\Control Panel\Desktop\LogPixels`, temporarily raises it to at least
  192, launches `wine64 control.exe joy.cpl`, and restores the exact previous
  value on success, nonzero exit, or exception. Existing values above 192 are
  never lowered.
- Closed the live 192 DPI probe and queried the same prefix through the active
  DXMT Wine runtime. `LogPixels` was restored to `REG_DWORD 0x60` (96).
  CrossOver Preview was not stopped or modified.

## 2026-06-11 Standard Tool Runtime Composition

- Extended the runtime manager so raw GPTK, DXMT, DXVK, and complete Wine
  directories are executable selections rather than catalog-only entries.
- Each raw selection creates a content-addressed package below the runtime
  composition cache. The selected immutable base Wine and Steamworks payload
  are hardlinked; user graphics files are APFS-cloned or copied into their
  expected Wine module paths, so neither the base package nor the user's
  source directory is modified.
- GPTK maps `external` and `wine` into the base GPTK `lib` tree while
  preserving internal framework and `../../external` symlinks. DXMT and DXVK
  map their Unix and Windows architecture directories into Wine's builtin
  module directories.
- A complete raw Wine directory becomes the entire renderer Wine root. Unified
  WoW64 layouts receive a local `wine64 -> wine` alias. A base Steamworks
  bridge is retained only when its Wine major matches the raw Wine major.
- Added six end-to-end runtime tests covering all four source kinds, base
  hardlink reuse, user-source inode isolation, cache reuse, cache invalidation,
  source changes during construction, relative and absolute GPTK symlink
  rebasing, complete-Wine replacement, and matching Wine 11 Steamworks
  injection. The complete runtime manager suite passed 53 tests;
  the companion catalog, patcher, app-state, launch-descriptor, and recovery
  suites passed 51 tests.
- Performed an isolated real-payload acceptance using CrossOver Preview's
  `lib64/apple_gptk`, `lib/dxmt`, and `lib/dxvk`. All three produced executable
  composed packages in 5.4 seconds. Each probed component matched its source
  hash with a distinct inode, and each package reused the selected base
  `wine64` inode. The temporary acceptance tree was removed automatically and
  the running CrossOver Preview instance was not touched.
- Final repository verification passed 109 Python tests, 84 JavaScript tests,
  all 24 shell contract tests, JavaScript syntax, Python bytecode compilation,
  and whitespace checks.

## 2026-06-11 Run Command And Container Semantics

- Replaced POSIX argument parsing with bounded Windows command-line parsing,
  preserving backslashes and double-quoted arguments without invoking a host
  shell.
- Added typed Wine launch plans for `cmd`, `regedit`, `control`, `winecfg`,
  `explorer`, PE files, batch files, control-panel applets, associated
  documents, URLs, and inline Windows Run commands.
- External selected EXE files are now accepted after their PE signature is
  verified. Steam's native `OpenFileDialog` supplies EXE/BAT/CMD filters and
  returns the chosen absolute path directly to the command field.
- Changed Open C Drive to invoke `/usr/bin/open -a Finder` with the exact
  prefix path and a scrubbed native environment.
- Removed the separate Windows Components button from the dormant legacy
  markup. Install Application To Container now routes to the reviewed catalog,
  while a direct obsolete backend request fails closed without opening a file
  chooser.
- Live AppID `1118200` acceptance ran `cmd.exe /c echo
  REALSTEAMONMAC_RUN_OK` through the installed DXMT runtime. Job
  `a14c9e7f4b9d4b4a8b807d3c11e95001` completed with exit code 0, emitted the
  expected marker, and stored its JSON and log at mode `0600`.
- Live Open C Drive job `a14c9e7f4b9d4b4a8b807d3c11e95002` completed with
  exit code 0 and logged Finder opening
  `/Volumes/990pro/games/mac/steamapps/compatdata/1118200/pfx/drive_c`.
  A separate read-only Finder AppleScript probe waited on macOS automation
  permission and was terminated; no Steam, Finder, prefix, or CrossOver
  process was terminated.
- The focused runtime suite passed 57 tests and the focused Steam UI
  policy/runtime suites passed 79 tests. Final repository verification passed
  113 Python tests, 85 JavaScript tests, all 28 shell contract tests, Python
  bytecode compilation, JavaScript syntax checks, and whitespace checks.

## 2026-06-11 Steam-Owned Action Controls

- Replaced the dormant handcrafted compatibility panel with a guarded child of
  Steam's existing compatibility React subtree. The injected call passes
  Steam's own React, JSX, component, stylesheet, and app-detail objects; it
  does not scan translated text or mount a separate DOM root.
- Removed the old route/document detection, copied CSS, fake switches,
  replacement selectors, panel markup, and modal layer. Source and live DOM
  checks found zero `.realsteamonmac-controls`, zero
  `.realsteamonmac-modal-layer`, no handcrafted `<select>`, no project
  `role="switch"`, and no `innerHTML` mount.
- Added Steam-native MSync, Retina, Metal HUD, MetalFX, DXR, and AVX toggles;
  native text fields and file picker for Run Command; native dependency and
  container dropdowns; native action buttons; and a disabled native status
  field.
- Live component inspection showed Steam mixes function components with
  `forwardRef` component objects. The validator now accepts only those two
  valid React forms and still fails closed on missing or malformed
  constructors.
- A controlled restart triggered the public-beta update from client build
  `1780965181` to `1781139754`. Steam removed the project asset directory and
  left the previous selected-tool chunk patch. The refreshed support patcher
  migrated that exact guarded structure to chunk SHA-256
  `10deb9010054af847d3b1ae8f226b34b3281d54a04cdc767a81abaab96d42fb4`.
- Live People Playground acceptance reported UI version 15,
  `nativeCompatRenders > 0`, `nativeCompatLastError=null`, and
  `controlLastError=null`. The native dropdown listed DXMT 0.80, DXVK macOS
  1.10.3, GPTK 3.0, and WineD3D 11.10.
- The native MSync toggle saved and restored the backend value; the
  `controlNativeSaves` counter advanced twice with no error. Under DXMT, the
  unsupported DXR toggle ignored clicks and did not advance the save counter.
  Selecting GPTK through Steam's native dropdown unlocked DXR and changed the
  native details to `realsteamonmac-gptk`; selecting DXMT restored both the
  tool and disabled state.
- Steam's native file chooser selected
  `/Volumes/990pro/games/mac/steamapps/common/People Playground/People Playground.exe`;
  the command field retained the full absolute path after the panel closed.
- The first native Run-button attempt exposed a stale installed runtime CLI.
  Its old code treated `cmd` as a game-relative file. After backing it up and
  atomically installing the already tested repository runtime, job
  `3f43ea69fffb21284dd675c3a7645cf5` completed with exit code 0 and emitted
  `REALSTEAMONMAC_NATIVE_UI_OK`.
- Native Open C Drive job `aebaad8f1342925edbd87801c42b85ca`
  completed with exit code 0 and invoked Finder with the exact path
  `/Volumes/990pro/games/mac/steamapps/compatdata/1118200/pfx/drive_c`.
- The installed runtime hash now matches the repository runtime:
  `527db7ae05429dc5bf974d9b9b41fe46a22e6e702789201f2cafed0e84ad024b`.
  CrossOver Preview PIDs `19863`, `19885`, and `73736` remained alive through
  all native Steam restarts.
- Final repository verification passed 114 Python tests, 79 JavaScript tests,
  all 28 shell contract tests, Python bytecode compilation, JavaScript syntax,
  and whitespace checks. The shell fixtures now contain and assert the guarded
  native-controls anchor instead of silently exercising the previous chunk
  shape.

## 2026-06-11 Bounded Component Recipe Executor

- Studied CrossOver Preview's `crossover.tie` component records as an
  implementation reference. They confirm that reliable component installation
  requires dependency ordering, installer-specific invocation, and
  post-install detection rather than a large flat URL list.
- Extended the runtime catalog with optional, backward-compatible recipe
  metadata. Only direct EXE, MSI through Wine `msiexec`, and the fixed
  DirectX redistributable extraction flow are accepted.
- Added prerequisite existence and cycle validation, safe prefix-relative
  file postconditions, ordered prerequisite installation, per-component
  receipts, and fail-closed DirectX `DXSETUP.exe` extraction checks.
- A live prefix inventory showed that Wine's builtins already satisfy many
  DLL-name checks. Added a restricted registry-key postcondition that invokes
  Wine `reg query`; catalog keys are bounded to `HKLM` or `HKCU` and control
  characters are rejected.
- Added NVIDIA's official download host to the allowlist in preparation for
  checksum-pinned PhysX entries; no NVIDIA payload is in the catalog yet.
- Ten focused recipe/download/action tests and all 64 runtime-manager tests
  passed. The current three-entry production catalog still loads unchanged.
- CrossOver Preview's wineserver, Windows Steam wrapper, and app process, plus
  native Steam, remained alive throughout this batch. Real catalog expansion
  and live component installation acceptance remain the next step.

## 2026-06-11 Reviewed Component Catalog Expansion

- Expanded the production catalog from 3 to 14 checksum-pinned recipes:
  current Visual C++ v14 x86/x64, Visual C++ 2013/2012/2010/2008 x86/x64,
  .NET Framework 4.8, DirectX June 2010, XNA 4.0 Refresh, and NVIDIA PhysX
  Legacy 9.12.1031.
- All payloads use official Microsoft or NVIDIA hosts with exact sizes and
  SHA-256 digests. x64 Visual C++ recipes install their matching x86 runtime
  first; XNA installs .NET Framework 4.8 first.
- Added exact file-SHA-256 postconditions. DirectX acceptance now requires the
  native x86 and x64 `d3dx9_43.dll` bytes from Microsoft's package, preventing
  Wine builtin DLLs from producing false success.
- Visual C++, .NET, XNA, and PhysX continue to use bounded registry-key
  postconditions through Wine `reg query`. Receipts remain blocked until all
  postconditions pass.
- JSON validation, all 66 runtime-manager tests, the full 123-test Python
  suite, 79 JavaScript tests, five installer/patch/launcher shell contracts,
  syntax checks, and whitespace checks passed. Live installation into the
  preserved People Playground prefix is the next acceptance step.

## 2026-06-11 VC++ 2013 Live Recipe Correction

- Backed up the People Playground prefix registries and existing dependency
  receipts before the first representative live installation.
- VC++ 2013 x86 installed successfully, passed its registry postcondition, and
  wrote a receipt. VC++ 2013 x64 installed its native DLLs, but the action
  correctly failed before writing a receipt because the catalog queried the
  native x64 uninstall view.
- Direct inspection and Wine `reg query` proved that the 32-bit Burn
  bootstrapper writes the x64 bundle key below `Wow6432Node`. Corrected the
  matching VC++ 2012 and 2013 x64 postconditions and added production-catalog
  regression assertions.
- Rollback snapshot:
  `~/Library/Application Support/RealSteamOnMac/backups/people-playground-dependencies-20260611T160058Z`.

## 2026-06-11 .NET 4.8 Download Pin Correction

- Created an APFS-cloned acceptance prefix at
  `/Volumes/990pro/games/mac/steamapps/compatdata/rsom-acceptance-xna-20260611T160614Z`
  so .NET/XNA testing does not modify the active People Playground prefix.
- The first isolated XNA attempt failed before installation because the
  `.NET 4.8` recipe used a `go.microsoft.com` redirect and Homebrew Python's
  TLS trust store rejected the redirected certificate chain.
- Resolved Microsoft's current final URL, downloaded it independently, and
  confirmed it is byte-identical to the existing manifest pin:
  121,346,568 bytes and SHA-256
  `0a3a390c47e639d0f7fc65b21195fee6b7f65b066f80f70c60fab191d14b7e40`.
- Replaced the redirect URL with the fixed official `download.microsoft.com`
  URL and added a production-catalog regression assertion.
- A direct retry proved the fixed URL alone was insufficient because Homebrew
  Python still used its own CA bundle. Replaced Python `urllib` transport with
  fixed `/usr/bin/curl` using SecureTransport, HTTPS-only protocols, bounded
  redirects, and a maximum file size. Final-host, exact-size, and SHA-256
  verification remain mandatory; no certificate bypass is permitted.
- The isolated retry installed .NET 4.8 successfully and wrote its verified
  receipt. XNA installed its files but failed the historical uninstall-GUID
  postcondition. Direct registry inspection showed the official MSI's actual
  Wine product key at
  `HKLM\Software\Wow6432Node\Microsoft\XNA\Framework\v4.0`; the catalog and
  production regression test now use that key.

## 2026-06-11 Component Installer Live Acceptance

- People Playground's preserved prefix passed production actions for Visual
  C++ 2012 x86/x64, Visual C++ 2013 x86/x64, PhysX Legacy, and DirectX June
  2010. Every item has a private receipt with exit code 0.
- The DirectX two-stage flow downloaded the pinned outer package, extracted to
  a private temporary directory, ran `DXSETUP.exe`, cleaned the extraction
  directory, and installed x64/x86 `d3dx9_43.dll` with exact expected
  SHA-256 hashes.
- PhysX exercised the MSI strategy and verified
  `HKLM\Software\Wow6432Node\AGEIA Technologies`. VC++ 2012 and 2013 exercised
  prerequisite ordering and Wine registry-view correction.
- The APFS-cloned acceptance prefix passed the complete XNA action: .NET
  Framework 4.8 installed first, both product keys passed Wine `reg query`,
  and both receipts were written. The active game prefix did not receive
  .NET/XNA changes.
- The final runtime-manager suite contains 67 passing tests. CrossOver Preview
  PIDs `19863`, `19885`, and `73736`, plus native Steam PID `75369`, remained
  alive throughout the live component tests.

## 2026-06-11 Native Dependency Dropdown Acceptance

- Backed up the deployed SteamUI assets to
  `~/Library/Application Support/RealSteamOnMac/backups/dependency-ui-catalog-20260611T161551Z`
  and refreshed the guarded config through the installed patcher. Verification
  passed and the live shared context loaded all 14 reviewed dependency entries.
- Restarted only native Steam with `-cef-enable-debugging`; CrossOver Preview
  PIDs `19863`, `19885`, and `73736` remained alive. Native Steam resumed as
  PID `95029`.
- Opened People Playground's compatibility page through Steam's own
  `OpenAppSettingsDialog(1118200, "compatibility")`. The page rendered three
  Steam `DialogDropDown` controls, seven native checkboxes, and the native
  Run, dependency, and container actions.
- Read-only React-fiber inspection proved the component dropdown contains the
  exact ordered 14-entry catalog. UI status reported
  `nativeCompatRenders > 0`, `nativeCompatLastError=null`, and all four project
  compatibility tools available.
- Live DOM inspection found zero `.realsteamonmac-controls` and zero
  `.realsteamonmac-modal-layer` elements. The acceptance probes now inspect
  Steam-native controls and no longer encode the removed replacement-panel
  contract.
- Verification passed the probe shell contract, both probe syntax checks,
  `git diff --check`, and 79 focused SteamUI/CDP JavaScript tests.

## 2026-06-11 Stable And Beta Steam Manifest Discovery

- Reproduced the regular-Steam installer failure in the contract fixture: the
  one-click installer required
  `steam_client_publicbeta_signed-2_osx.manifest` even when no beta channel was
  selected.
- Replaced the hardcoded public-beta name with bounded discovery from Steam's
  own `package/beta` file. The installer accepts only a short lowercase channel
  identifier and checks `signed-2`, `signed`, then base variants in that order.
- A candidate manifest is active only when the matching `.installed` marker
  exists. This prevents a newer downloaded manifest from being mistaken for
  the currently running build.
- Installation state now records `steam_channel`; existing state without that
  field remains readable, while a later stable/beta channel change requires a
  new clean rollback backup.
- Public-beta and stable fixtures both selected build `1780965181`. The beta
  fixture also contained an inactive `1781139754` manifest and correctly
  ignored it.
- Read-only validation against the live package selected channel `publicbeta`,
  manifest `steam_client_publicbeta_signed-2_osx.manifest`, and running build
  `1780965181`. Shell syntax, whitespace validation, and the full one-click
  installer contract passed.

## 2026-06-11 Language-Independent Native Action Readiness

- Reproduced the post-restart failure across all 34 dynamically managed
  Windows-only games. The authenticated native registry synchronized
  successfully, but Steam details remained at platform-invalid status `14`,
  so the previous browser policy refused to update any native action.
- Added a fail-closed readiness derivation that activates only after native
  registry synchronization. Installed games with local content and positive
  `size_on_disk` become native status `11`; missing, never-installed, and
  zero-byte staged games become native status `9`.
- Added policy tests for installed, uninstalled, and zero-byte states and
  retained exact restoration when an AppID leaves the synchronized registry.
  All 81 focused SteamUI, runtime, and CDP tests pass.
- Backed up the deployed UI to
  `~/Library/Application Support/RealSteamOnMac/backups/readiness-fallback-20260611T163357Z`,
  refreshed it through the guarded patcher, and restarted only native Steam.
  CrossOver Preview PIDs `19863`, `19885`, and `73736` remained alive.
- Live registry acceptance normalized 34/34 managed overviews, with zero
  remaining platform-invalid overviews. People Playground, Hogwarts Legacy,
  Aimlabs, and Red Dead Redemption 2 resolved to status `11`; FOR HONOR and
  Black Myth: Wukong's zero-byte staged directory resolved to status `9`.
- Added a read-only native-window action probe. Simplified Chinese acceptance
  found clickable `开始游戏` and `安装` buttons. A temporary English launch
  found clickable `PLAY` and `INSTALL` buttons for the same states, proving
  the implementation does not depend on translated labels.
- Restored Steam to Simplified Chinese and verified that a subsequent launch
  without a language override still reported `LANGUAGE=schinese`. Native
  Steam resumed as PID `50579`; CrossOver Preview remained untouched.

## 2026-06-12 Native Compatibility Mapping And Zero-Depot Diagnosis

- Changed the compatibility bridge to call Steam's original
  `SpecifyCompatTool` for project, third-party, and empty selections only
  after authenticated native registry synchronization. Successful native
  writes are cached; a rejected write cannot change the selected project tool
  or post a runtime-control update.
- Expanded the runtime contract to cover initial and dynamic native mappings,
  manual project-tool changes, failure rollback, and clearing a selection.
  All 81 focused JavaScript tests pass.
- Backed up the deployed UI, SteamUI assets, `config.vdf`, and both Black
  Myth manifests at
  `~/Library/Application Support/RealSteamOnMac/backups/native-compat-mapping-20260611T164718Z`.
- Deployed the mapping bridge and restarted only native Steam. UI status
  reported `compatNativeSyncs=34`, `registryNativeSyncs=1`, and no error.
  Live `config.vdf` contains 34 mappings; sampled entries are People Playground
  to DXMT, Black Myth to GPTK, FOR HONOR to DXMT, and Hogwarts Legacy to GPTK.
- Native `compat_log.txt` confirms the mappings but contains no registration or
  manifest-load lines for the four current tools. Startup discovery remains
  deliberately disabled because the valid-path A/B test removed Steam Cloud
  settings.
- Added two fixed-AppID experimental probes. The install-plan probe opens
  Steam's native wizard and cancels any plan it creates. The verification probe
  invokes only `VerifyApp`, polls the native action, and always attempts
  `PauseAppUpdate` in `finally`; it never resumes, installs, launches, or
  uninstalls.
- Both Black Myth manifests remain fully-installed zero-content records:
  `SizeOnDisk=0`, empty `InstalledDepots`, and no install directory. The native
  wizard produced no plan, and two verify-then-pause runs produced no target
  depots and mounted zero depots. No 130 GB download began.
- CrossOver Preview PIDs `19863`, `19885`, and `73736` remained alive throughout
  the mapping deployment and Black Myth diagnostics.
- Found that the remaining 1.1 MB under the Windows Black Myth install path is
  four save files rather than game content. Backed them up under the existing
  native-mapping backup and verified all four SHA-256 hashes.
- Added and tested a fixed-AppID zero-depot uninstall probe. Its host preflight
  required both manifests to remain fully installed with size zero and an
  empty `InstalledDepots`, required the game directory to contain only the
  four backed-up saves, and required CrossOver Preview to remain alive.
- Steam's native uninstall removed the Windows-library manifest successfully
  and preserved every save file. `content_log.txt` records `Uninstalled` and
  `finished uninstall (No Error)` at 2026-06-12 01:04:25. The duplicate
  macOS-library manifest remains for a second native lifecycle pass.
- Corrected the experimental probes after live console evidence showed that
  `GetGameActionForApp` is callback-based and rejects one argument. The probes
  now use `GetActiveGameActions()` for Promise-based safety checks and
  observation.
- A shutdown timing attempt also exposed a signature issue:
  `StartShutdown()` without an argument is rejected. Steam's production UI
  consistently calls `StartShutdown(true)`; the next restart test will use the
  same native signature.
- Repeated the shutdown through `StartShutdown(true)`: the main process exited
  in three seconds, but an immediate relaunch falsely observed the old
  SharedJSContext and then died with disconnected/broken IPC pipes. Seven
  seconds later no native Steam process remained, reproducing the reported
  restart race.
- Updated the C bootstrap launcher to inspect the macOS process table before
  patching or executing the runtime. If no `steam_osx` remains but a
  `Steam Helper` does, it waits in 250 ms intervals for up to 15 seconds.
  If a main Steam process is still alive, launch forwarding is unchanged.
- Added a process-level launcher contract using a real executable whose kernel
  accounting name is `Steam Helper`. The launcher waited for the fixture to
  exit, logged the completed drain, rebuilt as universal arm64/x86_64, passed
  strict code-signature verification, and passed `-Wall -Wextra -Werror`.
- Deployed only the launcher after backing up the prior binary; the tested
  source and installed launcher match after removing their code signatures,
  and Steam.app passes deep/strict verification. The hook, native engine, and
  runtime package were deliberately left unchanged.
- LaunchServices acceptance repeated the two-second stale-helper condition,
  reached SharedJSContext in four seconds, and remained alive across a second
  command 15 seconds later. A prior direct `nohup` run ended exactly with its
  terminal execution session and was rejected as a product-lifetime test.
- The restart caused Steam to load the remaining macOS-library Black Myth
  manifest. A second hash-guarded native uninstall removed it cleanly while
  preserving the four Windows-library save files byte-for-byte. Both AppID
  2358720 manifests are now absent.
- Reopened the native install wizard and cancelled it without starting a
  download. Steam now enters a real installer failure state instead of the
  one-second false completion: `eInstallState=15`, `eAppError=29`,
  `currentAppID=2358720`, zero required bytes, and an empty depot plan.
  Steam localizes error 29 as `平台无效`.
- Reconciled the active Valve libraries after discovering a same-build binary
  refresh. The current arm64 UUIDs and source hashes differ from the original
  `1780965181` profile even though Steam still reports the same build number.
- Used exact sequence matching, Capstone disassembly, Mach-O lazy-bind metadata,
  and bounded read-only LLDB memory checks to recover all five refreshed
  runtime locations. No live process memory was modified during diagnosis.
- Added the refreshed UUID-gated profiles to the native engine and offline
  compatibility-gate patcher, extended the hook contract, and made the live
  patcher test prefer the refreshed Valve binary when its exact hash matches.
- Re-ran hook, offline patcher, spawn redirect, native registry, environment
  isolation, launcher, and injection-installer contracts. One initial
  injection test failure was a shared-artifact race caused by running multiple
  rebuilding tests concurrently; the same test passed when run serially.
- Backed up the deployed native engine under
  `~/Library/Application Support/RealSteamOnMac/backups/steam-refresh-profile-20260611T172909Z`
  and atomically installed the tested engine hash
  `bdc80bde7ea80130681d85a0bd65db7ac11912414d6bd4959ad83b7d26e3acaf`.
- Restarted only native Steam through `StartShutdown(true)` and LaunchServices.
  CrossOver Preview PIDs `19863`, `19885`, and `73736` remained alive.
- Current-session logs prove the refreshed profile is live: the install gate
  rebuilt from one to 34 AppIDs, data reconciliation patched 34 objects, and
  the spawn redirect installed. LLDB confirmed the install instruction is now
  a branch, the SteamUI getter remains original, and the spawn slot points into
  the deployed native engine.
- Repeated the bounded Black Myth install-plan probe. Error 29 is gone:
  `eInstallState=7`, `eAppError=0`, and the probe cancelled successfully.
  Required bytes remain zero, no AppID manifest was created, and no download
  began, isolating native tool registration/depot selection as the next gate.
- Corrected the private-interface investigation after LLDB proved the global
  `CreateInterface` symbol belonged to `crashhandler.dylib`. The exact current
  `steamclient.dylib` factory returned all `SteamClient016` through
  `SteamClient023` wrappers and `CLIENTENGINE_INTERFACE_VERSION005`.
- Created and released a temporary engine pipe/global-user connection, then
  identified current `GetIClientCompat` by returned RTTI. Engine slot 72
  returned `16IClientCompatMap`; slot 75 returned null.
- Recorded the current 19-entry compatibility-map vtable and disassembled its
  first five serialized IPC stubs. A WebUI `GetAvailableCompatTools` call did
  not hit the native map breakpoint, confirming the JavaScript bridge is not a
  native tool-registration mechanism.
- Added
  `docs/research/native-compat-interface-2026-06-12.md` with exact addresses,
  cross-version slot evidence, RTTI validation, cleanup behavior, and the
  narrowed server-side `CCompatManager` refresh target.
- Corrected the game-controller target after the user's clarification. Removed
  all Steam Input popup resizing and implemented temporary 192 DPI scaling for
  Wine `control.exe joy.cpl`, with exact prior-value restoration.
- The corrected batch passed `git diff --check`, Python compilation, JavaScript
  syntax checking, 80 Node tests, 131 Python tests, and the runtime-package
  installer contract. CrossOver Preview PIDs `19863`, `19885`, and `73736`
  remained alive.
- Committed and pushed the correction as `c97b1f6`, then backed up the installed
  runtime and UI under
  `~/Library/Application Support/RealSteamOnMac/backups/`
  `wine-controller-readability-20260612T104827Z`. Source and installed hashes
  matched after atomic deployment.
- Direct installed-runtime acceptance opened Wine Game Controllers at
  `496x562` points with `LogPixels=0xc0`. Closing it completed action job
  `ee32137ad707451d88377dd487fb0c46` with exit code zero and restored
  `LogPixels=0x60`.
- Restarted only native Steam through `StartShutdown(true)` and LaunchServices.
  The refreshed shared context no longer exposes either old controller-popup
  status field. Native registry synchronization recovered to one successful
  sync and 34 app-detail subscriptions with no error.
- Reopened People Playground compatibility through Steam's own
  `OpenAppSettingsDialog`. The page contained three Steam `DialogDropDown`
  controls, seven native checkboxes, all 14 reviewed dependencies, zero legacy
  panels, and zero legacy modal layers.
- A 15-second, 60-sample compatibility trace observed one state and zero
  transitions: checkbox checked and enabled, DXMT selected, and no replacement
  UI. This reconfirms the RTF-reported compatibility-checkbox flicker remains
  fixed after removing the mistaken controller scanner.
- Selected `Game Controllers` through the real container `DialogDropDown` and
  clicked Steam's native Execute button. UI status reached
  `started=1`, `completed=1`, `failed=0`; the Wine panel again measured
  `496x562`, and the prefix returned from `0xc0` to `0x60` after close. The
  dropdown was restored to Open C: Drive.
- A visible `rundll32.exe` Program Error belongs to PID `63690`, started on
  2026-06-11 at 22:51, before this acceptance run. It was neither caused nor
  closed by the controller test. Native Steam PID `8939` and CrossOver Preview
  PIDs `19863`, `19885`, and `73736` remained alive afterward.
- Resumed the interrupted 2026-06-12 session after the usage-limit stop and
  terminated the abandoned broad-search process without touching Steam,
  CrossOver Preview, a Wine prefix, or game data.
- Re-read both untracked user RTF files. The original retains SHA-256
  `35667f4f766c527196729f534b499fe0e9fefeac18686ea93760cb2e567d68b3`;
  the new `_副本` file has SHA-256
  `fc2aa3152cb51f73660d254dae380e925463ff550baf544f5a2616cd1bc3a466`.
  An initial combined command misleadingly printed the original text/hash
  twice, but independent `shasum`, `stat`, `cmp`, and extracted-text `diff`
  disproved that result.
- The second RTF adds a real layout requirement: preserve the Steam-native
  implementation while placing Install Windows Components, Container Actions,
  and Run Command as three clearly ordered areas at the bottom of the
  compatibility page. This is now an explicit open Phase 8 item.
- The first RTF's two requirements remain covered by the accepted 60-sample
  native checkbox trace and the twice-verified Wine `joy.cpl` DPI/window test.
- Confirmed the resumed live baseline before native compatibility-manager
  work: native Steam PID `8939` still owns the debug session, CrossOver Preview
  PIDs `19863`, `19885`, and `73736` remain alive, and the independent runtime
  wineserver remains separate. The next blocker is still post-start
  `CCompatManager` tool registration, not the Wine controller implementation.
- Extracted and hashed the current arm64 `steamclient.dylib` slice, mapped its
  cstring and text virtual addresses, and recovered the current ASLR slide
  through a read-only LLDB attach.
- Located `InternalSpecifyCompatTool`, `RunCacheOffJob`, `YldRegisterTool`, the
  local-tool worker, and the cache job's all-list processing call through exact
  string cross-references.
- Backed up `config.vdf` under
  `~/Library/Application Support/RealSteamOnMac/backups/`
  `native-compat-runtime-trace-20260612T110305Z`, then cleared and restored
  People Playground's DXMT mapping through Steam's original native API.
- The `InternalSpecifyCompatTool` breakpoint fired twice and exposed the real
  current `CCompatManager` object plus its AppID/tool/experiment/priority ABI.
  The final mapping remains DXMT and the native registry probe still reports
  one successful sync, 34 managed AppIDs, and no invalid-platform records.
- Proved the native-registration root cause in the constructor: Steam enables
  `CCompatManager + 0x798` only when the platform string equals `linux`.
  Current macOS stores zero at both the platform-enabled byte and post-logon
  byte, so `RunCacheOffJob` and local manifest processing cannot start.
- Detached LLDB cleanly. Native Steam PID `8939` and CrossOver Preview PIDs
  `19863`, `19885`, and `73736` remained alive. An attempted address-bounded
  `llvm-objdump --macho` command ignored its bounds and emitted the whole text
  section; it was terminated and will not be repeated.
- Corrected the tentative interpretation of backtrace address `0x7356b8`:
  bounded static disassembly shows it belongs to an internal callback object
  constructor, not a stable return site after `InternalSpecifyCompatTool`.
- Verified the current method's first word as `0xd10243ff`
  (`sub sp, sp, #0x90`) and selected it as the fail-closed bridge site. The
  bridge will preserve the five method inputs, invoke a one-shot helper on
  Steam's `IPC:CSteamEngine` thread, replay the displaced instruction, and
  resume at `0x728eb4`.
- Disassembled `LaunchLogOnCompatProcessingJob`: it owns the post-logon flag
  transition at manager byte `+0x799`, checks app-state readiness, and
  tail-calls `RunCacheOffJob`. The resulting cache job starts Steam's own
  threaded local-manifest scan. Calling it from the project's reconciliation
  pthread is therefore excluded from the implementation.
- Captured a pre-experiment Cloud/config baseline and attached LLDB to native
  Steam PID `8939`. The verified `InternalSpecifyCompatTool` breakpoint fired
  on `IPC:CSteamEngine` for AppID `1118200`; entry bytes and manager state
  matched the static profile.
- Changed only manager byte `+0x798` to one and invoked the current
  `LaunchLogOnCompatProcessingJob`. Byte `+0x799` changed to one and
  `compat_log.txt` recorded a complete normal cache job. Cloud settings,
  `CloudStorage.WriteKey`, and `loginusers.vdf` remained intact.
- The job processed only Steam's built-in AppID `891390` list, rejected its
  Linux-targeted tools, and never logged a project local manifest.
- The incomplete refresh temporarily made native details report no selected
  compatibility tool and removed People Playground from the dynamic registry.
  Its persistent mapping was restored to `realsteamonmac-dxmt`, LLDB detached
  cleanly, and native Steam plus all CrossOver Preview processes remained
  alive.
- Located all four local-root string references. Bounded disassembly proves
  `CLoadLocalToolListJob` always constructs system roots, optional environment
  roots, and a Steam base path plus `/compatibilitytools.d`; the earlier
  constructor-omission hypothesis was wrong. The next inspection target is
  the actual macOS base path or child-manifest filtering.
- A second LLDB experiment incorrectly re-invoked the completed post-login Job
  from the stopped main thread. Its callback lacked valid Steam Job context,
  dereferenced address zero, and Steam aborted. No game files, prefix, Cloud
  data, or CrossOver process was touched. This establishes a strict one-shot
  engine-thread rule for the implementation and future dynamic tests.
- Restarted native Steam through the installed launcher. Launcher/UI patching
  and delayed engine injection completed, but that first process later exited
  without a new macOS crash report. CrossOver Preview and Windows Steam
  remained alive; the next restart will be launched with captured stdout and
  process lifetime rather than through an opaque `open` call.
- Launched native Steam in a real terminal session and held PID `11968`
  stable beyond the delayed-injection window. The dynamic registry recovered
  all 34 AppIDs, all four project tools were visible again, People Playground
  returned to the registry, and Cloud state remained healthy. CrossOver
  Preview stayed untouched.
- On this clean process, installed breakpoints at the local user-root insertion
  and threaded-enumerator return before the first one-shot manager enable.
  `CCacheOffSteamPlayStateJob` completed, but neither breakpoint fired. The
  local-tool Job is therefore not scheduled on macOS; the fault precedes path
  construction and manifest enumeration.
- Disassembled `RunCacheOffJob`: after the `+0x798` and `+0x799` checks it only
  creates `CCacheOffSteamPlayStateJob`. The next reverse-engineering target is
  that cache job's condition for creating `CLoadLocalToolListJob`.
- Resolved the remaining scheduling question through RTTI and Mach-O chained
  fixups. `CLoadLocalToolListJob` is allocated and queued once in the
  `CCompatManager` constructor, not by `CCacheOffSteamPlayStateJob`; therefore
  no late cache refresh can trigger its path builder.
- Tested the exact startup instruction controlling manager byte `+0x798`:
  forcing it true before `steamclient` initialization produced a repeatable
  `CSteamEngine::BMainLoop` stall and no project-manifest registration. The
  installed guard and engine were atomically restored from
  `early-steamplay-20260612T113603Z`; the experimental source and contracts
  were removed before commit.
- Reproduced the same stall without any binary patch by setting
  `STEAM_EXTRA_COMPAT_TOOLS_PATHS` to the valid four-tool directory on current
  beta build `1780965181`. This distinguishes valid-manifest completion from
  path construction: empty discovery is healthy, at least one valid manifest
  enters a broken macOS startup completion path.
- Captured a read-only all-thread LLDB trace. The main thread waited in the
  Steam startup event chain, `IPC:CSteamEngine` was sleeping normally, and a
  short-lived thread had a null program counter. This is evidence for, but not
  yet proof of, an uninitialized local-tool completion callback.
- Confirmed the restart-delay field report has a separate deterministic cause:
  failed/manual native Steam shutdown leaves the exact
  `Steam.AppBundle/Steam/Contents/MacOS/ipcserver` process parented by launchd.
  It blocks a subsequent native Steam instance until removed. CrossOver
  Preview remained alive throughout every experiment.
- Added a launcher regression fixture with two live processes named
  `ipcserver`: one at the exact native Steam AppBundle path and one under a
  fake CrossOver tree. The pre-fix test failed because both remained alive.
- The launcher now canonicalizes the expected executable path, matches only
  the current user's exact native Steam `ipcserver`, sends `SIGTERM`, and waits
  at most five seconds. The native fixture exits while the CrossOver fixture
  remains alive. No basename-only process kill is used.
- Deployed the current launcher with
  `script/install_steam_injection.sh --clean-backup` using the recorded
  `steam-1780705203-20260607T083704Z` rollback source. Steam passed
  `codesign --verify --deep --strict`, and the installed guard and engine
  hashes exactly match their repository artifacts.
- Ran installed-launcher dry-run acceptance against live orphan native
  `ipcserver` PID `89863`. It exited immediately, the launcher returned zero,
  and the log recorded an exact-path zero-millisecond drain. CrossOver Preview
  PIDs `19863`, `19885`, and `73736` remained alive. No game, prefix,
  container, or Wine `joy.cpl` state was modified.
- Steam installed beta manifest `1781212412` during a read-only LLDB launch.
  Its arm64 `steamclient.dylib` UUID is
  `BAF0A603-23F9-3F14-A019-73825732E82F`; all prior address profiles were
  treated as invalid immediately.
- Reproduced the updater's deleted-executable IPC state in the launcher test:
  start `ipcserver`, rename it to `.old`, install a replacement, then delete
  the old vnode. The pre-fix launcher missed it because `proc_pidpath`
  returned zero.
- Added a bounded `KERN_PROCARGS2` fallback used only when the primary
  executable path is unavailable. It canonicalizes the preserved executable
  or its parent directory and accepts only the exact native path or exact
  `.old` sibling.
- The upgraded fixture passes and leaves the fake CrossOver `ipcserver`
  running. Live artifact acceptance also drained real deleted-image PID
  `32189` in zero milliseconds while CrossOver Preview PIDs `19863`, `19885`,
  and `73736` remained alive.
- Added exact UUID-gated SteamClient and SteamUI profiles for beta build
  `1781212412`, preserving fail-closed behavior for every unknown binary.
- Verified the live universal files, expected gate instructions, error-29
  branch, SteamUI getter, and unique `_posix_spawn` lazy binding before adding
  the profile.
- Updated the standalone compatibility-gate patcher, top-level build
  allowlist, release-manifest build list, and their regression fixtures.
- Passed the serial profile matrix: compatibility patcher, hook contract,
  spawn redirect, one-click installer, hook environment isolation, Steam
  injection, update-manifest validation, and release packaging.
- Recorded the new build analysis and bounded LLDB trace points under
  `docs/research/`. Dynamic installed-runtime and native compatibility-tool
  registration acceptance are the next gates.
- Confirmed that the requested `RealSteamOnMac-Update.pkg` is still absent:
  current release output contains only Install and Uninstall packages, while
  an existing `install-state.json` still records build `1780965181`. This is a
  tracked release blocker, not a completed feature.
- Deployed the `1781212412` engine and launcher into the live Steam
  installation. Repository and installed hook hashes match, both Steam app
  signatures verify, and the new session remained alive beyond the delayed
  injection window.
- Live logs prove the exact new profile is active: the installation gate
  patched with `build=1781212412`, the allowlist-scoped spawn redirect
  installed, 34 managed AppIDs registered, and the data reconciliation worker
  patched the remaining tracked objects. Steam Cloud restore jobs completed
  normally for the observed platform changes.
- The same launch exposed a double-launch IPC race: a replacement native
  `ipcserver` appeared while the first launcher was waiting for the stale PID
  it had terminated. Added a delayed-exit/replacement fixture and changed the
  drain loop to track only the original PID using BSD process status.
- `tests/test_steam_launcher.sh` now proves the old updater-deleted PID exits,
  the replacement native `ipcserver` remains alive, the fake CrossOver
  `ipcserver` remains alive, and no false five-second timeout is logged.
