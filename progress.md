# Progress Log

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
    `/Users/wudazi/RealSteamOnMac-Backups/cloud-fix-20260609T103853`.
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

- **Status:** in progress
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

## 5-Question Reboot Check

| Question | Answer |
|----------|--------|
| Where am I? | Phase 3, repository implementation complete through browser-to-native hot registry; persistent live deployment is next. |
| Where am I going? | Rollback fix, cloud root cause, dynamic Windows-only enablement, independent runtimes, controls, and real launch. |
| What's the goal? | Native macOS Steam downloads and launches Windows-only games through independent selectable compatibility tools. |
| What have I learned? | Constructor threads and valid native compatibility-tool discovery break the macOS settings bridge; the engine load alone does not. |
| What have I done? | Recovered Claude's work, fixed rollback and Cloud, implemented dynamic eligibility, delayed native activation, and authenticated hot registry synchronization. |
