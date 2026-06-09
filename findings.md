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
- No `compatdata/1118200/pfx` exists yet, confirming the launch/container phase
  has not been implemented.

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

### Screenshot 2026-06-09 09:26:10

- CrossOver's `运行命令` dialog provides a useful reference UX:
  container selection, executable/command selection, environment variables,
  optional logging, log path, and Run.
- RealSteamOnMac should reproduce the capability per game/prefix, not depend on
  CrossOver or copy its bottle model.

## Technical Decisions

| Decision | Rationale |
|----------|-----------|
| Separate compatibility selection from runtime implementation | Steam UI can select stable wrappers while GPTK/Wine/DXMT packages update independently. |
| Generate an AppID registry from owned-library metadata | Supports new purchases and avoids a permanent single-game allowlist. |
| Keep global wildcard disabled | It risks changing native/dual-platform depot and update behavior. |
| Scope every setting to AppID and tool version | Prevents one game's experimental option from contaminating another prefix. |
| Use manifests and checksums for dependencies | Arbitrary remote installers are a supply-chain and reproducibility risk. |
| Diagnose cloud with read-only probes first | Remote saves and account state must not be changed during root-cause collection. |
| Reject Claude's global NOP as the production design | It broadens the backend gate beyond proven Windows-only games and is not paired with a complete UI predicate. |
| Preserve Claude's prototype on a recovery branch | It protects interrupted work while keeping incomplete behavior out of the verified mainline. |
| Identify targets from Steam app/depot metadata | A title must have a Windows launch/depot path and no usable macOS launch/depot path; `InvalidPlatform` alone is insufficient. |
| Restore Steam UI before any other rollback mutation | A failed UI restore now aborts before Steam.app, runtime binaries, or support files are moved. |

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| The requested scope spans several independent subsystems | Decomposed into audit/cloud, dynamic eligibility, runtime foundation, controls, and end-to-end launch phases. |
| The user requested uninterrupted autonomous execution while the brainstorming skill normally asks for approval | Treat the user's detailed architecture and explicit delegation of decisions as authorization; document decisions and proceed without pausing for approval. |
| The full test suite passed while the UI target predicate was missing | Add an integration contract that loads `config.js` and `ui.js` together and proves the compatibility-page predicate exists before accepting dynamic enablement. |
| Rollback tests did not cover Steam UI resource restoration | Resolved with a real patch-install/restore fixture in `tests/test_restore_steam_from_backup.sh`. |

## Resources

- Repository handoff: `docs/handoff/current-state-2026-06-08.md`
- Existing download design:
  `docs/superpowers/specs/2026-06-08-people-playground-native-download-design.md`
- Existing implementation plan:
  `docs/superpowers/plans/2026-06-08-people-playground-native-download.md`
- Steam backup recorded by the handoff:
  `/Users/wudazi/RealSteamOnMac-Backups/steam-1780705203-20260607T083704Z`
