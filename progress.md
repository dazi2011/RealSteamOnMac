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

## Error Log

| Timestamp | Error | Attempt | Resolution |
|-----------|-------|---------|------------|
| 2026-06-09 | Memory registry had no matching RealSteamOnMac entry | 1 | Continued from current repository and live-machine evidence. |
| 2026-06-09 | Steam CDP endpoint was unavailable | 1 | Confirmed current Steam lacks `-cef-enable-debugging`; plan a controlled debug relaunch after preserving repository state. |
| 2026-06-09 | Cloud page remained blank without a JS exception | 1 | Traced the shared settings store and found the native backend omitted `cloud_enabled`. |
| 2026-06-09 | Parallel tests raced while both built the same fat dylib | 1 | Re-ran build-writing tests sequentially; all passed. |
| 2026-06-09 | Computer Use could not start a capture stream | 2 | Recorded ScreenCaptureKit `-3811`; retained element-aware policy and used read-only CDP evidence. |

## 5-Question Reboot Check

| Question | Answer |
|----------|--------|
| Where am I? | Phase 3, replacing the one-game fixture with dynamic Windows-only discovery. |
| Where am I going? | Rollback fix, cloud root cause, dynamic Windows-only enablement, independent runtimes, controls, and real launch. |
| What's the goal? | Native macOS Steam downloads and launches Windows-only games through independent selectable compatibility tools. |
| What have I learned? | Constructor threads and valid native compatibility-tool discovery break the macOS settings bridge; the engine load alone does not. |
| What have I done? | Recovered Claude's work, fixed rollback, restored/deployed Cloud health, and established a safe startup boundary. |
