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
