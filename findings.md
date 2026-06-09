# Findings And Decisions

## Requirements

- Audit Claude's interrupted work and determine exactly what is complete.
- Audit and update all handoff, installation, rollback, and usage documentation.
- Enable all eligible owned Windows-only games dynamically, including newly
  acquired games, with Steam's native blue download action and compatibility
  page.
- Keep macOS Steam independent from CrossOver.
- Expose versioned GPTK, DXMT, DXVK, WineD3D, and Wine-based choices through
  Steam compatibility tooling.
- Create Proton-style prefixes at `steamapps/compatdata/<appid>/pfx`.
- Support per-game MSync, high-resolution mode, Metal HUD, and supported
  MetalFX/DLSS translation settings.
- Provide per-prefix dependency installation and a run-command workflow.
- Fix the blank global Steam Cloud settings page and indefinitely checking
  cloud status before relying on the launch path.
- Provide repeatable installation, update, rollback, documentation, real-machine
  installation, and end-to-end launch verification.
- Record every meaningful action and push each verified phase.

## Repository Findings

- Active repository: `/Users/wudazi/Documents/RealSteamOnMac`.
- Active branch: `codex/people-playground-experiment`.
- Local head before takeover: `a7e508f`.
- Remote head: `be55b6a`, one fast-forward commit ahead.
- Claude's remote-only commit is titled
  `feat: install Windows depots via steamclient install-gate redirect`.
- The remote commit reports that People Playground AppID `1118200` reached
  Fully Installed with depot `1118201` and about 456 MB on disk.
- Claude used two linked worktrees under `.claude/worktrees/`; their status and
  any uncommitted files still require direct inspection.
- The repository's only top-level untracked path is `.claude/`.
- Existing source has tests for the launcher, native hook, Steam UI patch,
  compatibility page, install action, runtime config, rollback, and CDP probes.
- Claude's final linked worktree contains four additional uncommitted files
  modified between 22:59 and 23:02 on 2026-06-08:
  `hook/compat_gate_hook.c`, `script/patch_steamui.py`,
  `tests/test_compat_gate_hook.sh`, and `tests/test_steamui_patch.py`.
- That prototype removes the allowlist by replacing the steamclient install
  platform branch with a global NOP and structurally scanning every
  `InvalidPlatform` `CAppOverview`.
- The prototype is not ready to merge:
  - `InvalidPlatform` does not prove a title is specifically Windows-only.
  - The install gate becomes unconditional for every owned AppID reaching it.
  - The patched compatibility page calls
    `globalThis.__REALSTEAMONMAC_IS_TARGET__`, but `ui.js` does not define it.
  - The tests pass despite the missing runtime predicate, exposing a test gap.
- The exact prototype will be preserved on a separate recovery branch before
  the active branch is advanced.

## Live Machine Findings

- `/Applications/Steam.app` currently launches through
  `realsteamonmac_launcher` and passes strict deep code-sign verification.
- Native Steam build is `1780705203`; the current process has been running for
  more than twelve hours.
- The deployed hook is still the committed allowlist-gated build, not Claude's
  uncommitted all-Windows prototype.
- The deployed compatibility tool is
  `~/Library/Application Support/Steam/compatibilitytools.d/realsteamonmac-experimental`.
- People Playground is genuinely installed at
  `/Volumes/990pro/games/mac/steamapps/common/People Playground`.
- Its manifest reports `StateFlags 4`, `UpdateResult 0`, Windows depot
  `1118201`, and `SizeOnDisk 455945761`.
- `content_log.txt` records the real download, commit, and Fully Installed
  transition on 2026-06-08 at 21:11 and again at 21:15.
- At takeover, no `compatdata/1118200/pfx` existed, confirming Claude had not
  implemented the launch/container phase. The later Phase 4 runtime now creates
  and uses that exact path.

## Dynamic Library Discovery Findings

- Steam's live SharedJSContext exposes `appStore.allApps` and
  `appDetailsStore.RequestAppDetails(appid)`. This is preferable to parsing the
  binary `appcache/appinfo.vdf` because it uses Steam's already-decoded owned
  library state and receives library updates in the running client.
- The exact managed-game eligibility rule is:
  - `app_type === 1` (game);
  - `subscribed_to === true`;
  - `visible_in_game_list === true`;
  - `vecPlatforms` contains `windows`;
  - `vecPlatforms` does not contain `osx`.
- The rule deliberately excludes tools, DLC, unowned/hidden entries, native
  macOS games, and dual-platform games. Garry's Mod AppID `4000`, whose live
  platforms are `windows`, `osx`, and `linux`, is a confirmed exclusion.
- A live scan completed in about 0.7 seconds. It found 49 owned/visible game
  entries and 34 Windows-only candidates:
  `242050`, `304390`, `359550`, `517630`, `552500`, `578080`, `622590`,
  `623990`, `654310`, `674020`, `714010`, `729720`, `813000`, `892520`,
  `990080`, `1118200`, `1174180`, `1237970`, `1238810`, `1286560`,
  `1326470`, `1491000`, `1517290`, `1665460`, `1911390`, `2139460`,
  `2325290`, `2358720`, `2507950`, `2547140`, `2584990`, `2943650`,
  `2948190`, and `3983810`.
- At the initial registry scan all 34 candidates reported native display status
  `14` (`InvalidPlatform`). People Playground had local content but no prefix;
  the other installed/local candidates therefore required the same
  installed-state policy instead of being treated as ready-to-install.
- `SteamClient.Apps.GetAvailableCompatTools(1118200)` currently returns an
  empty list because the cloud-safe launcher no longer registers a valid
  `STEAM_EXTRA_COMPAT_TOOLS_PATHS`. The compatibility page and project-owned
  tool registry must therefore not depend on that native discovery path.
- Hot update can be implemented by periodically rescanning
  `appStore.allApps`, requesting details only for new or changed AppIDs, and
  replacing the managed registry atomically. Newly purchased games then become
  eligible without reinstalling or maintaining a static allowlist.
- A controlled LLDB experiment loaded `libRealSteamNativeEngine.dylib` into the
  already initialized Steam PID `97776` and explicitly called
  `realsteamonmac_start_native_worker()`. The process remained healthy and
  `cloud_enabled=true` plus `show_screenshot_manager=false` remained present.
- The late worker successfully installed the strict one-AppID install-gate
  trampoline and changed People Playground's backend details from status `14`
  to status `11`. Its already-cached overview remained status `14`.
- Live native titles confirm the actionable mapping:
  - no local content and backend status `9` means ready to install;
  - local content and backend status `11` means ready to launch.
- The UI bridge must therefore synchronize an invalid managed overview to the
  matching backend status `9` or `11`, while preserving download, update,
  running, and other active statuses.
- Steam's runtime startup has a forked/two-stage shape. Clearing the injection
  environment in the first constructor removes the guard from the final
  process; preserving it through the bootstrap stage keeps the guard mapped in
  the final `steam_osx`.
- The production activation handshake is:
  - launcher sets injection stage `bootstrap`, guard path, engine path, and a
    30-second delay;
  - bootstrap guard changes the stage to `runtime` without starting a worker;
  - the final runtime keeps the inherited one-shot dispatch timer;
  - every Helper exec loads the guard, clears all injection/activation
    variables, rejects engine activation because its process name is not
    `steam_osx`;
  - the final runtime timer loads the engine and starts its worker after normal
    Steam initialization.
- A live two-stage launch proved the timer survives Steam's startup fork. After
  30 seconds both guard and engine were mapped, the install gate and data worker
  were active, People Playground details were status `11`, Cloud remained
  enabled, and no Helper process retained a DYLD or RealSteamOnMac variable.

## Phase 3 Live Deployment Findings

- Steam's `appDetailsStore` was not an authoritative source by itself. All 34
  managed entries remained cached at status `14` because no active consumer had
  subscribed to their native detail stream.
- Direct
  `SteamClient.Apps.RegisterForAppDetails(appid, callback)` subscriptions
  returned the real states: 24 ready to install, locally installed games ready
  to launch, and the remaining games in their native update states.
- The browser bridge now creates subscriptions only after the authenticated
  native registry update succeeds. It feeds each callback into
  `appDetailsStore.AppDetailsChanged`, retries stale status `14` at a bounded
  one-second interval, and unregisters games removed from the dynamic registry.
- A cold deployment on 2026-06-09 synchronized all 34 managed games:
  - `nativeStatusSyncedCount=34`;
  - `invalidPlatformDetailsCount=0`;
  - `invalidPlatformOverviewCount=0`;
  - `projectToolAvailableCount=34`;
  - Garry's Mod AppID `4000` remained excluded at native status `31`.
- The visible Steam library UI matched the backend:
  - For Honor AppID `304390` showed the original enabled blue `安装` action at
    status `9/9`;
  - People Playground AppID `1118200` showed the original green `开始游戏`
    action at status `11/11`, with local content and
    `realsteamonmac-experimental` selected.
- A controlled click on For Honor's real React action reached Steam's native
  install manager with AppID `304390`, install state `7`, app error `0`, and
  the expected disk requirement. The experiment immediately called
  `CancelInstall` before `ContinueInstall`; no game payload was downloaded.
- Cloud remained healthy after the dynamic deployment:
  `cloud_enabled=true`, `show_screenshot_manager=false`, and CloudStorage was
  available.
- The attempted hot-rebuild of SteamUI's platform getter was unnecessary. It
  failed near-branch allocation under the live ASLR layout and retried every
  worker tick, while all 34 games still reached correct states through data
  reconciliation and native detail subscriptions.
- The global getter redirect was removed. The cold run beginning at platform
  log line `4774` contains no `steamui:` patch/error entries; the install gate
  rebuilt from one bootstrap AppID to all 34 and the data scan patched the
  remaining 33 objects.
- The backup script now recognizes an already-installed RealSteamOnMac
  bootstrap, records the active `CFBundleExecutable`, and hashes the launcher,
  original bootstrap, runtime executable, and steamclient library.

## Documentation Audit Findings

- `docs/handoff/current-state-2026-06-07.md` is intentionally historical and
  says no content was downloaded.
- Local `docs/handoff/current-state-2026-06-08.md` and `README.md` stop before
  the remote final commit and still say completed download is future work.
- The remote final commit updates both files, but a full consistency audit has
  not yet been completed.
- Existing plans/specs are scoped only to People Playground's download flow.
  The independent runtime and dynamic library work needs a new decomposed spec.
- The current compatibility `run` script only logs its inputs and exits `0`;
  it does not create a prefix or launch a Windows process.
- The original rollback script did not restore patched Steam UI resources before
  removing the support directory. A TDD regression now requires restoration of
  `index.html`, the compatibility chunk, backups, and project assets before
  support removal.
- Current compatibility-tool installation deletes and recopies a single fixed
  directory. The multi-version runtime manager must replace this with staged,
  validated, atomic activation.

## Visual Findings

### Screenshot 2026-06-09 09:23:21

- Steam Settings is open on the global `云` page.
- The entire content pane is blank/dark while the navigation sidebar renders.
- This is a page-render or data-loading failure, not merely a disabled toggle.
- The failure is global and therefore must be diagnosed before game-specific
  cloud or launch conclusions are made.
- Live logs at the same time repeatedly say
  `waiting for roaming storage to initialize`.
- `sharedconfig.vdf` is a small, syntactically valid VDF file and was loaded
  successfully by Steam after 20:59 on 2026-06-08.
- CloudStorage itself resumed namespaces successfully in earlier sessions.
  Current evidence does not support the theory that RealSteamOnMac caused a
  server-side account sanction or intentionally disabled cloud synchronization.
- The active Steam process was not launched with `-cef-enable-debugging`, so a
  controlled restart is required to capture the settings page's live JS and
  backend state through CDP.
- A controlled restart with `-cef-enable-debugging` exposed the settings page
  and shared Steam UI context on `127.0.0.1:8080`.
- The cloud settings DOM renders the sidebar and `云` heading, but its
  `DialogBody` is empty. Reloading the page produced no JavaScript exception.
- Steam UI's protobuf schema still defines `cloud_enabled` as boolean field
  `10000` and `show_screenshot_manager` as field `10001`.
- The live native settings store omits both fields from `m_ClientSettings`;
  `cloud_enabled` is absent rather than present with the value `false`.
- The per-game cloud component reads the same `cloud_enabled` setting. Its
  missing value follows the disabled fallback, which explains the misleading
  “Steam 云已在 Steam 全局设置中被禁用” message.
- CloudStorage namespaces resumed and no remote-storage failure was observed.
  The evidence therefore points to missing native capability/settings data,
  not damaged cloud saves or an account sanction.
- RealSteamOnMac's injected UI code does not read or write Steam cloud settings.
  Controlled clean-versus-injected A/B testing proved that the native startup
  injection was the indirect cause.
- A clean runtime and a minimal hook that only clears
  `DYLD_INSERT_LIBRARIES`/`REALSTEAMONMAC_FORCE_COMPAT` both return
  `cloud_enabled=true`, `show_screenshot_manager=false`, and render the Cloud
  controls.
- Leaving the injection environment inherited by Steam Helper breaks the
  websocket/settings bridge.
- Starting a pthread from the injected dylib constructor omits both settings
  even when that worker initially sleeps and performs no patch.
- Early tests that appeared to blame the full engine's import/load surface were
  confounded by the launcher's valid compatibility-tool path. A strict
  single-variable retest loaded the full `arm64` engine with an environment-only
  constructor and no valid tool path; both Cloud fields remained healthy.
- The full engine's presence is therefore not independently causal. Constructor
  thread creation and valid native compatibility-tool discovery are the proven
  triggers.
- `STEAM_EXTRA_COMPAT_TOOLS_PATHS` pointing to an empty directory preserves the
  Cloud fields. Pointing the same variable to the real
  `compatibilitytool.vdf` directory removes both fields.
- The production architecture must split startup injection into a minimal
  environment guard and keep the full native patch engine out of the process
  until an explicit post-initialization activation path exists.
- Historical People Playground logs contain
  `Inhibiting sync requests for pending platform change` and
  `Sync Failed, no user set`, but the guarded 10:39 startup produced neither.
  It completed a normal People Playground cloud evaluation and roaming config
  later reported `PerformSyncCloud - all sync'd up`.

### Screenshot 2026-06-09 09:26:10

- CrossOver's `运行命令` dialog provides a useful reference UX:
  container selection, executable/command selection, environment variables,
  optional logging, log path, and Run.
- RealSteamOnMac should reproduce the capability per game/prefix, not depend on
  CrossOver or copy its bottle model.

## Steamworks And DXVK Findings

- The native macOS Steam client exposes a real `steamclient.dylib` that Proton
  `lsteamclient` can load when the runtime supplies the native client path and
  the expected AppID/PFX environment.
- Native `steamclient.dylib` does not export `Steam_IsKnownInterface` or
  `Steam_NotifyMissingInterface`.
- Treating every `CreateInterface` success as equivalent to
  `Steam_IsKnownInterface` is wrong. The first fallback passed an unsupported
  interface far enough to produce `VersionMismatch` for
  `STEAMAPPS_INTERFACE_VERSION008`.
- The pinned Proton generated source contains 208 bridge-supported interface
  names. Using that generated set for local validation restored correct
  behavior without changing the Linux code path.
- Final bridge hashes:
  - Unix Mach-O:
    `159798e1caab1102f5d51a5e15891f4d4f5cd901ed7fb54a9ae45d51bb1280ec`;
  - Windows PE:
    `b806f522a5e49b4b3ba9e0259e8bbf02787e7c287f4f10d880a660190c23c1ca`.
- DXVK-macOS reached native Steam, acquired the Steam pipe/user/interfaces,
  completed callbacks, and produced `Steamworks initialised` plus
  `Steam login: True`.
- Workshop subscription retrieval completed in the same run. No fake API or
  ownership bypass was used.
- Stock DXMT v0.80 initially failed before rendering because Wine Staging
  11.10 did not expose the legacy macdrv contract it needs. The project-owned
  compatibility build described below resolves that boundary.
- A migrated CrossOver PFX may contain menu-integration artifacts even when all
  actual Wine binaries come from RealSteamOnMac. Disabling
  `winemenubuilder.exe` prevents those artifacts from launching old CrossOver
  `.app` helpers.
- People Playground's missing `ppgModCompiler/config.json` is non-fatal:
  `CompilerConfig` defaults to host `127.0.0.1`, port `32513`, and
  `ShutdownWhenGameNotFound=true`.
- The compiler's exit monitor receives Wine PID `312`. On this machine macOS
  PID `312` is persistent `/usr/libexec/searchpartyd`, so .NET's process lookup
  never reports the game as gone.
- AppID-scoped Wine-server termination after the main process exits resolves
  the collision without imposing a global policy that could break games whose
  launchers intentionally spawn another executable.
- The final normal-menu exit cleared all managed processes in five seconds,
  removed AppID `1118200` from Steam's running list, and triggered a successful
  `AC Exit` AutoCloud upload.

## DXMT Wine 11 Findings

- DXMT v0.80 does not merely need a public function symbol. Its
  `macdrv_win_data` layout predates Wine 11 and reads `client_cocoa_view`.
- Wine 11's `client_view` can remain null until a `macdrv_client_surface` is
  created and presented. Returning the current struct without creating that
  surface still fails Metal-view creation.
- Wine loads winemac locally, so exporting `macdrv_functions` from
  `winemac.so` alone is insufficient for DXMT's `RTLD_DEFAULT` lookup.
- The accepted design combines:
  - a Wine-side function table and legacy proxy with explicit client-surface
    lifetime management;
  - a globally injected, DXMT-only visibility shim that forwards into the
    locally loaded winemac table.
- The complete Wine Staging v11.10 patch set is based on the exact Wine 11.10
  commit used by the project. The formal artifact is no longer a vanilla-Wine
  driver mixed silently into a Staging package.
- Building every linked object with deployment target 10.15 matters. Relinking
  only the final dylib does not lower object-level availability assumptions.
- The formal runtime launches with the original Mach-O `wine64` entrypoint.
  Runtime-managed `DYLD_INSERT_LIBRARIES` replaces the temporary shell wrapper.
- People Playground's Chinese translation mod compiler connection refusal is
  reproducible under both DXVK and DXMT. It is non-fatal to rendering,
  Steamworks, Workshop retrieval, exit, and Cloud.
- The exact `dxmtmac1` package is now active in the user's existing Steam. A
  native URL launch reached the main menu in 31 seconds; normal close returned
  `0` and Steam completed AutoCloud plus upload.
- Successful installation initially left both official GPTK images mounted.
  Detaching installer-owned unique mount points directly is reliable; a
  mount-list precondition was unnecessary and failed in the live path.

## Technical Decisions

| Decision | Rationale |
|----------|-----------|
| Separate compatibility selection from runtime implementation | Steam UI can select stable wrappers while GPTK/Wine/DXMT packages update independently. |
| Generate an AppID registry from owned-library metadata | Supports new purchases and avoids a permanent single-game allowlist. |
| Keep global wildcard disabled | It risks changing native/dual-platform depot and update behavior. |
| Scope every setting to AppID and tool version | Prevents one game's experimental option from contaminating another prefix. |
| Use manifests and checksums for dependencies | Arbitrary remote installers are a supply-chain and reproducibility risk. |
| Diagnose cloud with read-only probes first | Remote saves and account state must not be changed during root-cause collection. |
| Split the injected guard from the native engine | The split makes it structurally impossible to start the patch worker during dyld construction and preserves a clean post-initialization activation boundary. |
| Reject Claude's global NOP as the production design | It broadens the backend gate beyond proven Windows-only games and is not paired with a complete UI predicate. |
| Preserve Claude's prototype on a recovery branch | It protects interrupted work while keeping incomplete behavior out of the verified mainline. |
| Identify targets from Steam app/depot metadata | A title must have a Windows launch/depot path and no usable macOS launch/depot path; `InvalidPlatform` alone is insufficient. |
| Use the live app store plus requested details as the authoritative registry | It is already decoded by Steam, reflects ownership and visibility, and supports in-process hot updates without parsing binary cache files. |
| Activate the native engine only after Steam initialization | Live LLDB loading proved the install gate can be installed without removing Cloud settings; startup-time worker creation remains forbidden. |
| Use a two-stage guard plus one-shot dispatch timer | It survives Steam's startup fork, avoids debugger entitlements, activates after Cloud initialization, and sanitizes every Helper exec. |
| Use an authenticated loopback registry bridge | It lets the decoded Steam library update the delayed native allowlist without restart, native tool discovery, debugger entitlements, or a global wildcard. |
| Subscribe to native details only after native registry acceptance | The browser must fail closed until the backend install gate owns the same AppID set; direct subscriptions then provide current install/launch/update states. |
| Do not redirect SteamUI's platform getter | The data scan and detail stream are sufficient and allowlist-scoped; a global code hook adds ASLR allocation failure, log spam, and a wider crash surface without improving live behavior. |
| Restore Steam UI before any other rollback mutation | A failed UI restore now aborts before Steam.app, runtime binaries, or support files are moved. |
| Treat missing `cloud_enabled` as the primary cloud symptom | The blank page and false “globally disabled” state share this backend omission; changing account/cloud data would hide evidence without proving a cause. |
| Build a real bridge rather than fake Steam API success | The pinned Proton bridge preserves native ownership, callbacks, Workshop, and Cloud behavior. |
| Validate interfaces from generated bridge code | Native macOS Steam lacks Linux helper exports; generated local validation is narrower than blindly accepting `CreateInterface`. |
| Keep People Playground cleanup AppID-scoped | Its PID collision is proven, while global post-exit kills could terminate legitimate launcher-spawned games. |
| Inject the DXMT shim only from the per-renderer runtime environment | Steam and non-DXMT Wine processes must never inherit the visibility shim. |
| Build the DXMT driver from exact Wine plus complete Wine-Staging sources | A live-compatible but source-mixed driver is not a maintainable release boundary. |
| Detach installer-owned GPTK mount points unconditionally during cleanup | The paths are unique to the installer, detach is idempotent, and cleanup must not depend on a separate mount-list probe. |

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| The requested scope spans several independent subsystems | Decomposed into audit/cloud, dynamic eligibility, runtime foundation, controls, and end-to-end launch phases. |
| The user requested uninterrupted autonomous execution while the brainstorming skill normally asks for approval | Treat the user's detailed architecture and explicit delegation of decisions as authorization; document decisions and proceed without pausing for approval. |
| The full test suite passed while the UI target predicate was missing | Add an integration contract that loads `config.js` and `ui.js` together and proves the compatibility-page predicate exists before accepting dynamic enablement. |
| Rollback tests did not cover Steam UI resource restoration | Resolved with a real patch-install/restore fixture in `tests/test_restore_steam_from_backup.sh`. |
| Steam cloud UI showed no console exception | Traced the rendered DOM, protobuf schema, settings store, and CloudStorage state; the deterministic failure is an omitted native setting field. |
| Computer Use could not start ScreenCaptureKit | Earlier Cloud work used CDP. The later game-exit test used local screenshots, process-scoped foreground activation, and a CoreGraphics click on the visibly confirmed in-game `quit` entry. |
| Shared app details stayed at status `14` after native data changes | Registered direct native detail subscriptions and published callbacks into the shared details store. |
| SteamUI getter trampoline retried continuously | Removed the redundant global getter patch and added a contract that rejects its reintroduction. |
| Native Steamworks bridge failed on missing helper exports | Added macOS-only interface validation and local notification fallback. |
| People Playground stayed “running” after menu exit | Proved the Wine/macOS PID collision and added an AppID-scoped PFX cleanup. |

## Resources

- Repository handoff: `docs/handoff/current-state-2026-06-08.md`
- Existing download design:
  `docs/superpowers/specs/2026-06-08-people-playground-native-download-design.md`
- Existing implementation plan:
  `docs/superpowers/plans/2026-06-08-people-playground-native-download.md`
- Steam backup recorded by the handoff:
  `/Users/wudazi/RealSteamOnMac-Backups/steam-1780705203-20260607T083704Z`
