# Findings And Decisions

## 2026-06-11 Field Requirements

- Rockstar Launcher installation interruption can leave Red Dead Redemption 2
  in a persistent `Unable to launch game, please try reinstalling the game`
  state; recovery must not require deleting the whole game.
- After a user quits Steam, the next start may take too long to restore Install
  or Play actions and may temporarily show a Windows-only marker beside Play.
- Steam UI languages other than Chinese currently break Install and Play
  actions, which proves action binding depends on localized text or a
  locale-specific DOM shape.
- Installed Windows games can resolve to missing or incorrect targets, including
  `Phoenix-Win64-Test.exe` for Hogwarts Legacy and `AimLab.app` for the
  Windows-only Aimlabs title.
- Verification can fail to repair stale executable/install state, and deleting
  a previously downloaded game can lead Steam to complete a new download in
  one second after creating only an empty directory.
- Run Command does not persist an EXE selected from the file picker.
- Open C Drive does not open the prefix in Finder.
- Install Application To Container must become the single entry point for
  Windows dependencies/components; the separate components panel must be
  removed.
- Compatibility settings must use Steam's actual compatibility page controls,
  selector, rows, and switches. Overlay UI and hand-built lookalike controls
  are explicitly rejected.
- The canonical user contract is direct side-by-side folders under
  `~/Library/Application Support/Steam/compatibilitytools.d`, including
  CrossOver-like GPTK, Wine, DXMT, and DXVK layouts without requiring users to
  author project-specific `run` scripts or manifests.
- Stable Steam and Steam beta installations must both be detected and patched
  by one installer.
- Steam's Add a Non-Steam Game flow must accept `.exe`; `.app` remains native,
  while PE executables use the selected compatibility tool.
- Runtime options must be capability-aware. Unsupported DXR, MetalFX/DLSS,
  MSync, and renderer features must not remain actionable.
- CrossOver Preview is an allowed research and licensed component source on
  this machine, but the shipped product must remain operational without
  depending on CrossOver at runtime.
- Acceptance includes downloaded-library launch tests, newer DX12 titles with
  GPTK, older DX10/DX11 titles with DXMT, representative DLSS conversion tests,
  CrossOver controls for failures, performance comparison, common dependency
  installation tests, update.pkg upgrade acceptance, README updates, PKG
  publication, and remote verification.

## 2026-06-11 Initial Audit

- The active branch is `codex/people-playground-experiment`, clean and aligned
  with `origin/codex/people-playground-experiment` at `6ace14b`.
- `origin/main` points to the same commit.
- No RTF or `codex LOOKLOOK ITTTTT!!!!!!!` instruction file is present.
- Existing Phase 7 claims native release acceptance, but commit
  `beee125` is titled `mount compatibility controls without native dropdown`;
  that wording directly conflicts with the newly restated native-selector
  requirement and must be re-audited rather than trusted.
- No matching prior RealSteamOnMac memory entry was found, so repository and
  live-machine evidence are the only accepted sources for this run.
- Commit `beee125` confirms the current compatibility UI deliberately hides
  Steam's native compatibility row with `style.display = "none"` and mounts a
  project-owned `realsteamonmac-controls` panel in its place. This is not a
  native Steam implementation and directly violates the field requirement.
- The same code locates the native row by exact Chinese or English text:
  `强制使用特定 Steam Play 兼容性工具` or
  `Force the use of a specific Steam Play compatibility tool`. Other Steam
  locales cannot match this predicate, providing a concrete root cause for
  language-dependent compatibility UI/action failure.
- Tests for that behavior encode Chinese text fixtures and explicitly assert
  that the native row is hidden, so the test suite currently protects the
  incorrect design instead of detecting it.
- The browser runtime already wraps Steam's own
  `SteamClient.Apps.GetAvailableCompatTools` and merges project tool records
  into that API. Therefore the native dropdown can consume project entries;
  the separate DOM-built selector is an avoidable second implementation, not a
  technical necessity.
- For project tools, the current `SpecifyCompatTool` wrapper intentionally does
  not call Steam's original API. It persists project-local state and mutates
  cached app details instead. This must be reconciled with the native selector
  so Steam's control remains authoritative and visibly selected without
  introducing the macOS cloud regression previously caused by process-start
  compatibility-tool discovery.
- `projectCompatTools` is loaded once from generated startup configuration and
  `getAvailableCompatTools` caches the merged result indefinitely per AppID.
  A folder added to `compatibilitytools.d` after startup cannot appear without
  regenerating configuration and invalidating these caches.
- Compatibility-page detection itself is locale-dependent: it requires a page
  heading matching only Chinese `兼容性` or English `Compatibility` and the
  force-tool label in one of those two languages. This is a wider failure than
  the hidden-row selector alone.
- The remainder of `ui/realsteamonmac_ui.js` confirms every visible project
  control is handcrafted HTML/CSS: the force-tool checkbox and `<select>`,
  capability switches, action buttons, run-command dialog, dependency dialog,
  and container-operation dialog. Steam styling is imitated, but Steam-owned
  React controls are not used.
- All project control labels, status messages, dialog copy, and most error
  fallback text are hard-coded Chinese. The feature cannot follow Steam's
  active locale and cannot be considered language-independent.
- The Run Command dialog exposes a `创建日志文件` checkbox but
  `buildRunCommandPayload` sends only target, arguments, and environment. The
  checkbox has no behavioral effect.
- The file-picker action is implemented as an asynchronous native job that
  triggers panel re-renders before writing the selected path back into the
  modal input. The backend response contract and modal lifetime must be tested;
  the current code alone does not prove a selected EXE can survive that cycle.
- Dependency installation and Install Application To Container are separate
  actions and separate dialogs. This directly contradicts the required single
  install entry point.
- A full-screen `realsteamonmac-modal-layer` with `z-index: 100000` is used for
  every secondary action. It is an overlay and conflicts with the explicit
  no-overlay/native-control requirement.
- Reconciliation runs every second across every managed AppID and repeatedly
  walks Steam documents/React fibers. Registry discovery runs every five
  seconds across all owned visible games. This polling design is a plausible
  contributor to slow post-restart action readiness and requires profiling or
  event-driven replacement.
- `runtime/realsteamonmac_runtime.py` does not read Steam's per-game launch
  configuration. `discover_default_executable` scans up to 5000 `.exe` files
  and ranks them by folder-name similarity, depth, and lexical path. This can
  select test, shipping, launcher, or helper executables incorrectly and is a
  concrete explanation for paths such as
  `Hogwarts Legacy/Phoenix-Win64-Test.exe`.
- The runtime accepts only a PE file as the game context and requires that file
  to be inside a directory named `steamapps`. A newly added non-Steam `.exe`
  outside a Steam library cannot use the current launch path.
- Run Command is narrower than Windows Run: it resolves only an existing PE
  file under the game install directory or PFX. It rejects command names such
  as `cmd`, `regedit`, `control`, or `winecfg`, rejects documents and shell
  associations, and rejects arbitrary selected installers outside those two
  roots.
- The file picker accepts `.exe`, `.bat`, and `.cmd`, but
  `execute_choose_file_action` then rejects any selection outside the game or
  PFX and the actual Run Command resolver rejects non-PE files. Selecting a
  normal external EXE can therefore complete the macOS picker and still return
  no target to the UI because the native job fails validation.
- `find_app_installation` treats a manifest plus an existing directory as an
  installation even when the directory is empty. It does not validate depot
  files, install size, state flags, or Steam's launch executable before
  presenting the app to action workflows.
- Open C Drive invokes `/usr/bin/open <prefix>/drive_c`, which should normally
  reach Finder. Its reported failure is not explained by command construction
  alone and requires job-log/live LaunchServices evidence.
- Install Application To Container already runs an arbitrary selected Windows
  installer in the prefix, while dependency installation uses a separate
  checksum-pinned catalog. The two backends can be unified behind one native
  Steam action surface.
- Runtime selection requires project-specific `realsteamonmac.json` metadata
  and a `runtimePackage` pointing into the RealSteamOnMac immutable package
  store. A raw CrossOver-like GPTK/Wine directory cannot currently be launched
  directly even if its payload is otherwise valid.
- `script/install_realsteamonmac.sh` hard-codes the beta manifest filename
  `steam_client_publicbeta_signed-2_osx.manifest` and accepts only builds
  `1780705203` and `1780965181`. Stable Steam, a differently named manifest,
  and every newer build are rejected before installation.
- The installer and launcher otherwise use the normal shared macOS paths
  `/Applications/Steam.app` and
  `~/Library/Application Support/Steam/Steam.AppBundle/Steam`; the primary
  stable/beta incompatibility is manifest/build detection, not a separate
  application bundle path.
- `launcher/steam_launcher.c` sets
  `REALSTEAMONMAC_ACTIVATION_DELAY_MS=30000`. Managed-game native state cannot
  become active for at least 30 seconds after a cold Steam start, directly
  explaining the reported long delay before Install/Play becomes available.
- Every Steam launch synchronously reruns the SteamUI patcher before starting
  Steam. Patch verification plus the fixed 30-second engine delay compounds
  perceived startup latency.
- `scan_compat_tools` requires exactly four project-defined regular files in
  every recognized tool folder: executable `run`, `compatibilitytool.vdf`,
  `toolmanifest.vdf`, and `realsteamonmac.json`. Raw GPTK, Wine, DXMT, and DXVK
  payload directories are ignored because none of those marker files exist.
- The metadata schema also requires a renderer enum, complete project
  capability map, and immutable `runtime_package` identifier. This is the
  non-standard user-facing format explicitly rejected in the field report.
- A viable replacement is to recognize payload signatures in-place and
  synthesize Steam API records plus a launch adapter outside the user's tool
  directory. User folders then remain vendor-standard and do not need generated
  `run` or manifest files.
- SteamUI patching is also build-specific: it accepts one index hash, two
  compatibility chunk hashes, a fixed chunk filename, and exact minified source
  anchors. A stable or updated Steam build can fail even after installer
  manifest detection is fixed.
- The standalone steamclient patcher likewise supports exactly the same two
  builds through fixed Mach-O UUID, full SHA-256, instruction bytes, and
  offsets. Removing these checks would be unsafe; stable/beta support requires
  independently verified build profiles or a narrower structural symbol/pattern
  discovery with byte-level validation.
- `patch_steamui.py` rescans compatibility tools only while installing/verifying
  the UI asset at Steam launch. The generated `config.js` remains static for
  the life of that Steam process, confirming there is no in-session hot-add.
- `script/install_runtime_package.sh` assembles one large immutable package by
  copying Wine four times and injecting GPTK, DXMT, DXVK, Steamworks, and
  project shims. This explains why RealSteamOnMac containers/runtimes consume
  far more space than a CrossOver bottle, which primarily stores per-bottle
  mutable state while sharing application-level engines and components.
- The bundled dependency catalog contains only VC++ 2015-2022 x64, VC++
  2015-2022 x86, and .NET Framework 4.8. The complaint that the component
  installer offers very little is accurate.
- Dependency download security is strong but currently limited to four
  Microsoft hosts and fixed installer receipts. Expanding the catalog needs
  reviewed official sources and checksums; blindly copying CrossOver metadata
  or proprietary payloads is neither technically robust nor license-safe.
- The native spawn hook redirects only when Steam supplies a path ending in
  `.exe`, the file already exists, its first bytes are `MZ`, and the AppID is
  managed. A nonexistent launch target, wrong test executable, or `.app` path
  fails before the compatibility runtime is invoked.
- Normal Steam launches use the executable path supplied by steamclient; the
  runtime's heuristic `discover_default_executable` is used by action/container
  workflows. Both sources therefore need correction: Steam launch metadata for
  Play and deterministic executable resolution for auxiliary actions.
- The Hook changes platform availability objects and the
  `GetAppForInstallation` platform veto, but it does not validate appmanifest
  state, installed depot files, bytes-on-disk, or the selected launch record.
  A stale manifest plus an empty directory can remain visually normalized as
  installed/launchable.
- The Aimlabs `.app` report is consistent with the hook boundary: `.app` can
  never pass `realsteamonmac_should_redirect_spawn`, even for a managed
  Windows-only AppID. Live app-details/launch-option inspection is required to
  determine why Steam selected that path.
- The native worker polls tracked Steam objects every 250 ms and performs a
  full writable-memory scan every 15 seconds once objects are tracked, or every
  2 seconds while none are tracked. Combined with the JavaScript one-second
  React/DOM reconciliation, this is a substantial polling architecture that
  should be reduced after event sources are identified.
- The install-gate trampoline is narrowly allowlist-scoped and preserves the
  original invalid-platform branch for all other AppIDs. Its safety boundary
  is sound; stale installation repair should be added outside this gate rather
  than broadening the patch.
- All four bundled `compat-tool/*/run` scripts only append diagnostics and exit
  zero. They do not launch games or runtimes; actual Play execution depends on
  the steamclient spawn redirect. Requiring equivalent `run` scripts in
  user-supplied folders has no functional justification in the current
  architecture.
- Tool capabilities are hard-coded in project JSON rather than derived from
  discovered files, framework versions, Wine features, or renderer exports.
  Static flags can expose unsupported DXR/MetalFX/MSync options or hide newly
  available features.
- The injection guard independently defaults to the same 30-second timer,
  confirming the delay is intentional at both launcher and guard layers.
- The update client downloads the next release's
  `RealSteamOnMac-Install.pkg` and either runs `installer` as root or opens the
  package. There is no separate `update.pkg` artifact or update-specific
  package identity.
- The main installer can reuse the prior clean backup when its state file
  matches the current Steam build, so in-place package upgrade is plausible,
  but it remains unverified against a real installed older release.
- Runtime packages use shared immutable engine trees, while each game PFX holds
  mutable container state. Further size reduction should deduplicate renderer
  trees in the shared package, not collapse per-game prefixes that provide
  isolation.
- Many shell tests are source-text contracts built from `grep`; they can pass
  while runtime behavior is broken. The language bug, hidden native row, inert
  log checkbox, and incorrect executable selection all survived this style of
  test.
- `test_steam_launcher.sh` explicitly forbids setting
  `STEAM_EXTRA_COMPAT_TOOLS_PATHS`, preserving the prior finding that native
  process-start tool discovery breaks Steam Cloud on the profiled macOS build.
  Native UI requirements must be met without reintroducing that environment
  variable.
- The existing API bridge offers a safer path: keep cloud-safe startup, make
  Steam's own compatibility React row render for managed apps, and supply
  discovered tools through the wrapped Apps API. This needs live interaction
  tests, not a replacement DOM panel.
- Existing compatibility-page probes explicitly search for
  `realsteamonmac-controls`, custom `input[data-control]`, and the hand-built
  combobox. They must be inverted to reject overlays and assert Steam-owned
  component/fiber identities.
- Current install tests construct only the public-beta manifest and explicitly
  expect unknown builds to fail. No fixture covers stable-channel manifest
  discovery or a profile-selection diagnostic.

## 2026-06-11 Live Machine Evidence

- Native Steam is currently running build `1780965181` through
  `realsteamonmac_launcher`; installed RealSteamOnMac is version `0.1.1`.
- The package directory contains both
  `steam_client_publicbeta_signed_osx.manifest` at build `1773367340` and
  `steam_client_publicbeta_signed-2_osx.manifest` at build `1780965181`.
  Filename alone does not identify the active channel/build; the running
  process reports `1780965181`.
- A Windows Steam client is simultaneously running inside CrossOver Preview.
  Native and CrossOver test evidence must be separated by process tree, prefix,
  and log path.
- The native hook log captured a registry transition from 34 managed AppIDs to
  zero, repeated restoration of the install gate while empty, and a later
  transition back to 34. This transient empty publication directly explains a
  window where Play/Install disappears or Windows-only state returns after
  restart.
- The registry refresh must distinguish “Steam stores not initialized” from a
  real empty owned library. It should retain the last valid snapshot and only
  publish removals after an authoritative initialized scan.
- Hook logs show Red Dead Redemption 2 reaches the redirect with
  `PlayRDR2.exe`. Its current failure occurs after Steam target selection and
  after the compatibility dispatch boundary, inside prefix/runtime/Rockstar
  handling.
- Red Dead Redemption 2 occupies about 122 GB and contains both `RDR2.exe` and
  `PlayRDR2.exe`. Runtime logs show the latter was launched through the DXMT
  renderer on both 2026-06-10 and 2026-06-11. The game is not missing; recovery
  must inspect the Rockstar bootstrap state and prefix rather than redownload
  the depot.
- Hogwarts Legacy occupies about 72 GB and contains both the top-level
  `HogwartsLegacy.exe` and
  `Phoenix/Binaries/Win64/HogwartsLegacy.exe`. The reported
  `Phoenix-Win64-Test.exe` path does not exist, proving the failure is stale or
  incorrectly synthesized launch metadata rather than a missing game depot.
- Aim Lab occupies about 18 GB and contains `AimLab_tb.exe` but no
  `AimLab.app`. A Windows-only title reaching an `.app` target proves that the
  native/macOS launch record is being selected or synthesized incorrectly
  before PE dispatch.
- `BlackMythWukong` currently occupies only about 1.1 MB and is effectively an
  empty shell. This is materially different from the Hogwarts and Aim Lab
  failures and supports the report that Steam accepted stale installed state
  after a one-second pseudo-download.
- The corresponding app manifests make the distinction explicit:
  - RDR2 and Aimlabs have `StateFlags=4`, nonzero `SizeOnDisk`, and populated
    `InstalledDepots`.
  - Hogwarts has `StateFlags=36`, a 74 GB installed depot, and
    `FullValidateAfterNextUpdate=1`; validation cannot repair a launch target
    that is absent from the depot manifest.
  - Black Myth: Wukong has `StateFlags=1026`, `SizeOnDisk=0`, no
    `InstalledDepots`, and a 149.8 GB entry only under `StagedDepots`. The
    bridge must not normalize this state into ready-to-launch or treat the
    empty install directory as a completed installation.
- RDR2 has no per-AppID configuration file, so it inherits
  `DEFAULT_CONFIG.renderer = "dxmt"`. Newer DX12 games do not currently receive
  a GPTK default or recommendation based on launch/depot characteristics.
- Hogwarts, Black Myth: Wukong, and Aimlabs are already explicitly configured
  for GPTK, so their current failures occur before or independently of renderer
  selection.
- Two Open C Drive jobs captured the exact failure. `/usr/bin/open` inherited
  DXMT's `DYLD_INSERT_LIBRARIES`, then the arm64e process aborted while trying
  to load the x86_64 visibility shim. Both jobs returned `exit_code=-6` but
  were persisted as `state="completed"`. Native macOS helper processes must run
  from a scrubbed environment, and nonzero exits must not be reported as
  completed.
- Task 1 now fixes both defects at their source. Native helper subprocesses
  receive only an explicit host-variable allowlist, and dependency/container
  nonzero exits transition the job to failed. A live `/usr/bin/open` smoke test
  against the People Playground `drive_c` returned zero even when the source
  environment contained the previously fatal x86_64 DXMT shim.
- Existing design, interface, README, probes, and tests are internally
  inconsistent with the deployed implementation. The documents claim Steam's
  native selector is retained, while commit `beee125` and the current UI hide
  that row and render a project-owned replacement. The published acceptance
  probes explicitly require `.realsteamonmac-controls`, Chinese labels, and
  project-owned inputs, so they cannot prove the newly required native UI.
- The old public tool contract requires `compatibilitytool.vdf`,
  `toolmanifest.vdf`, executable `run`, and `realsteamonmac.json`. That contract
  describes project wrappers, not the raw GPTK/Wine/DXMT/DXVK payload folders
  the user expects to drop into `compatibilitytools.d`.
- CrossOver Preview `27.0.0.40479` keeps its engine shared at application
  scope: approximately 359 MB under `lib`, 88 MB under `lib64`, and 513 MB
  under `share`. Bottles contain mutable registry/user/application state and
  reference the shared engine, explaining why a newly created bottle can be
  only a few hundred megabytes.
- CrossOver's GPTK payload exactly follows the requested vendor layout:
  `lib64/apple_gptk/external/D3DMetal.framework`,
  `external/libd3dshared.dylib`, and matching `wine/x86_64-unix` plus
  `wine/x86_64-windows` D3D/DXGI/NVAPI/NVNGX files. CrossOver names the
  MetalFX bridge `nvngx.dll`; the user-supplied GPTK image may expose
  `nvngx-on-metalfx.dll`, so discovery must recognize payload roles rather
  than one project-specific filename.
- CrossOver keeps DXMT and DXVK as shared component trees under `lib/dxmt` and
  `lib/dxvk`, while its base Wine tree lives under `lib/wine`. This supports a
  compositional runtime model: one Wine engine plus independently selectable
  graphics payloads, not four duplicated Wine installations.
- CrossOver ships explicit bottle templates for Win10, Win11, Win7, Win8,
  Vista, and XP under `share/crossover/bottle_templates`, shared bottle data
  under `share/crossover/bottle_data`, and dependency recipes in
  `share/crossover/data/crossover.tie`.
- The deployed compatibility directory contains only the four generated
  RealSteamOnMac wrapper folders; no raw vendor-format tool is currently
  installed there for acceptance testing.

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

- Active repository: `<repository-root>`.
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

## Per-Game Control Findings

- Native startup discovery through `STEAM_EXTRA_COMPAT_TOOLS_PATHS` remains
  prohibited because it removes Cloud settings on this Steam build. Four
  project tools can instead be injected only into managed compatibility pages
  while actual PE launch stays on the proven spawn dispatcher.
- A global per-AppID config is necessary before a game has a PFX and for newly
  purchased games. The canonical path is
  `~/Library/Application Support/RealSteamOnMac/apps/<appid>.json`; the
  PFX-local config remains a migration and inspection copy.
- The loopback control endpoint reuses the existing private registry token and
  rejects non-managed AppIDs. It accepts no command strings or filesystem
  paths, only renderer plus six booleans.
- The accepted renderer mapping is one-to-one:
  `realsteamonmac-gptk -> gptk`, `realsteamonmac-dxmt -> dxmt`,
  `realsteamonmac-dxvk -> dxvk`, and
  `realsteamonmac-wined3d -> wined3d`.
- MetalFX and DXR are GPTK-only. Presenting these switches as active under
  DXMT/DXVK/WineD3D would be a false UI contract, so both frontend and backend
  reject that state.
- Steam's independent properties popup is absent from
  `SteamUIStore.WindowStore.SteamUIWindows`. The shared context retains every
  popup window in `g_FriendsUIApp.m_IdleTracker.m_rgWindows`, which is the
  stable live path used by the accepted control mount.
- A combined selector containing `[class]` visits `<html>` before the
  compatibility combobox. Selector priority must be explicit or the mount
  silently chooses an anchor without a parent.
- Native app-detail callbacks must update the cache only. Calling a full
  reconcile from each callback amplifies 34 subscriptions into hundreds of
  startup scans; the fixed one-second reconcile loop and five-second stale
  retry are sufficient.
- Live selection of DXVK and DXMT changed both Steam's displayed tool and the
  package Wine path returned by runtime dry-run. A real Retina checkbox event
  wrote the canonical AppID config with mode `0600`; the final accepted state
  is DXMT, MSync enabled, and all other switches disabled.
- GPTK Wine 7.7 can open the shared Wine 11-updated PFX and run its registry
  tools. The observed game exit code `3` was not a general prefix-version
  failure.
- The exact GPTK failure was a managed Steamworks bridge mismatch. Unity
  reached D3DMetal, then the project `lsteamclient.dll` asserted at
  `steamclient_main.c:375` because its Wine 11 Unix side is not installed in
  the GPTK Wine 7.7 root.
- Moving only the two bridge DLLs whose hashes matched the private project
  ledger restored GPTK menu/map loading and a normal `WM_CLOSE` exit `0`.
  Unsupported renderers must deactivate those shared-PFX files, while
  DXMT/DXVK/WineD3D restore them atomically.

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
| Keep the native control API data-only | Fixed renderer/boolean fields can be validated and persisted safely; arbitrary command execution belongs to a later separately bounded workflow. |
| Make global AppID config canonical and retain PFX config as fallback | Settings can exist before install and survive prefix replacement while old deployments remain readable. |
| Reconcile shared-PFX Steamworks files per renderer | The Proton bridge is Wine-ABI-specific. GPTK must not inherit the Wine 11 bridge, while supported renderers must restore exactly the ledger-matched files. |

## 2026-06-10 UI And Release Findings

- The large persistent panel is a mount-guard bug, not a Steam layout limit.
  `findCompatControlAnchor()` accepts any bounded element whose text contains
  `RealSteamOnMac`, and `mountControlPanels()` searches every discovered Steam
  document. A library details document can therefore receive the compatibility
  controls.
- The compatibility page briefly renders normally because Steam builds its
  native page first; the recurring reconciliation pass inserts the project
  dashboard afterward.
- The standard Steam tool root already exists at
  `~/Library/Application Support/Steam/compatibilitytools.d`, but the deployed
  installation contains only the legacy experimental wrapper. Current four-tool
  entries come from a hard-coded browser configuration, not directory
  discovery.
- Re-enabling `STEAM_EXTRA_COMPAT_TOOLS_PATHS` is not an acceptable fix on the
  verified Steam build because prior A/B evidence showed that a valid tool
  removes Cloud settings fields.
- The repository is private and has no GitHub release as of 2026-06-10. Public
  release must wait for license/secret scans plus clean install, uninstall, and
  live rollback evidence.
- CrossOver Preview exposes Python setup libraries and localized UI resources
  suitable for behavior research. Its proprietary Wine/runtime components must
  not be copied into a public release merely because they are locally
  installed.
- The standard compatibility-tool root may contain notes, staging directories,
  or other unrelated user folders. Discovery now ignores folders with no tool
  manifest files, while a folder that presents any tool file must pass the
  complete bundle validation.
- Runtime package IDs are immutable build identifiers and can exceed the
  64-character tool-ID limit. They now use a separate 160-character bound.
- DXMT's official vendor-extension documentation requires `nvapi64.dll`,
  `nvngx.dll`, and `DXMT_ENABLE_NVEXT=1` for DLSS Super Resolution translated
  to MetalFX. The installed 0.80 runtime package contains both DLLs.
- Renderer alone is not a sufficient persistent selection because DXMT 0.70 and
  DXMT 0.80 share a renderer but can have different runtime packages and
  capabilities. The exact tool ID is now part of the AppID configuration.
- CrossOver's dependency recipes are stored in
  `Contents/SharedSupport/CrossOver/share/crossover/data/crossover.tie`, not in
  the thin Python UI bridge. The database contains download URLs, localized
  names, dependency graphs, and historical recipes, but many entries use old
  HTTP links, archives, or CodeWeavers mirrors and cannot be copied blindly
  into a public checksum-pinned catalog.
- A public one-click package cannot legally bundle Apple D3DMetal. The release
  installer therefore auto-detects a user-supplied official GPTK 3.0 image and
  otherwise builds an open runtime containing Wine, DXMT, DXVK macOS, and
  WineD3D.
- The machine has no Developer ID Installer identity and no configured
  `notarytool` profile. Release PKGs can be built and cryptographically hashed,
  but they must be described as unsigned and unnotarized until those Apple
  credentials exist.
- Update metadata uses an independent Ed25519 key rather than conflating
  package signing with release-integrity signing. The private key is mode 0600
  under `~/.config/RealSteamOnMac`; only the raw public key is in the repo.
- The uninstaller treats compatibility-tool metadata hashes as ownership
  evidence. Modified or user-replaced directories are preserved instead of
  being deleted.
- Microsoft updated the current Visual C++ v14 redistributables. The reviewed
  immutable downloads on 2026-06-10 are 18,731,856 bytes for x64 and 6,941,536
  bytes for x86, with SHA-256 values recorded in
  `config/dependencies.json`.
- Steam can transiently publish an empty `appStore.allApps` collection during
  restart even after the browser has synchronized a nonempty managed registry.
  Treating that empty collection as authoritative unregisters native detail
  subscriptions and recreates the reported delayed Play/Install or
  Windows-only state. The browser must retain its last accepted registry until
  Steam exposes an initialized nonempty overview store again.
- The existing 30-second native-engine delay has prior live evidence that it
  preserves Steam Cloud through the two-stage `steam_osx` startup. Removing it
  without a replacement readiness proof would reintroduce a known global
  settings regression, so registry retention and activation readiness are
  separate fixes.
- The flat string-pair ACF reader discarded section membership, so it could not
  distinguish `InstalledDepots` from `StagedDepots`. A structured read-only
  parser now requires a complete installed state before runtime actions.
- Live manifest classification on 2026-06-11:
  - RDR2: ready, state `4`, seven installed depots;
  - Aimlabs: ready, state `4`, one installed depot;
  - Hogwarts Legacy: repair required, state `36`, content present;
  - Black Myth: Wukong: download incomplete, state `1026`, zero installed
    depots and one staged depot.
- The installed SteamUI's `EDisplayStatus` enum is `0..39`; value `15` is
  undefined, `14` is InvalidPlatform, and `38/39` represent download/update
  failure. The previous browser bridge accepted any positive integer except
  `14`, so unknown future or corrupt values could become visible actions.
- `CAppOverview` already supplies `size_on_disk`, while selected per-client
  data supplies `installed`. These Steam-owned fields are sufficient to reject
  the specific contradictory state where details report ReadyToLaunch (`11`)
  but the client reports zero bytes or not installed.
- The current Steam client exposes all required repair primitives without
  manifest editing: `Apps.VerifyApp`, `Downloads.ResumeAppUpdate`, and
  `Installs.OpenInstallWizard`. A managed-only dispatcher can therefore route
  complete-but-damaged content to verification, staged/paused/failed downloads
  to resume, and truly absent content to Steam's install wizard.
- The spawn hook currently redirects only when Steam's requested path already
  exists and begins with `MZ`. A missing Hogwarts development target and
  Aimlabs' `.app` target therefore bypass the runtime before any recovery can
  occur.
- Steam appinfo contains both the wrong and correct launch records for the
  reported cases: Hogwarts has branch-specific `Phoenix-Win64-Test.exe`
  records plus release `HogwartsLegacy.exe` defaults, while Aimlabs has
  `AimLab_tb.exe` for Windows and `AimLab.app` for macOS. Launch selection must
  preserve Steam's decoded entry identity and OS instead of scanning the game
  directory for a plausible executable.
| Keep a thin fail-fast top-level installer over verified component installers | Users need one repeatable command, while checksum, signature, atomic package, and rollback ownership remain in the already tested lower layers. |

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
  `$HOME/RealSteamOnMac-Backups/steam-1780705203-20260607T083704Z`
