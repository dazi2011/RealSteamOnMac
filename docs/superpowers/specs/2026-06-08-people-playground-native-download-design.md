# People Playground Native Download UI Design

Date: 2026-06-08

## Objective

Make Steam on macOS treat People Playground (`AppID 1118200`) as a
downloadable Windows title through the project's compatibility tool, while
preserving Steam's native library UI and install workflow.

The result must survive:

- leaving and reopening the game details page;
- switching library views;
- closing and reopening Steam;
- Steam rebuilding its front-end app overview objects;
- Steam rebuilding its native app state after the current startup worker exits.

The visible action must be Steam's native blue install/download button. Clicking
it must call Steam's original install action and reach the native install
configuration flow without `InvalidPlatform` error 29. The project must not
automatically confirm the final download step during development or tests.

## Confirmed Root Cause

Steam currently has two independently cached platform decisions:

1. The library front end resolves its primary action from
   `AppOverview.per_client_data[0].display_status`. Value `14`
   (`InvalidPlatform`) produces the disabled gray state; value `9`
   (`ReadyToInstall`) produces Steam's native blue `Install` action.
2. `SteamClient.Installs.OpenInstallWizard([1118200])` validates a separate
   native app state. If that state has returned to invalid-platform status, the
   wizard ends at state `15` with app error `29`, even when the button was made
   blue in JavaScript.

The existing compatibility-tool mapping is already present and loaded:
`windows -> macos` through `realsteamonmac-experimental`. The failure is not a
missing tool mapping. It is incomplete and time-limited state propagation.

## Scope

### Phase 1: Permanent People Playground behavior

- Use the project's explicit allowlist with `1118200` as the only enabled
  entry; do not hard-code the AppID into patch logic.
- Keep the native backend state for `1118200` eligible for installation for the
  lifetime of the Steam process.
- Keep the front-end overview state synchronized whenever the object is created,
  refreshed, or revisited.
- Preserve Steam's original action resolver, button component, CSS, click
  handler, install wizard, disk-space checks, and download queue.
- Add deterministic diagnostics and rollback controls.
- Update project scripts, tests, handoff notes, and research documentation.

### Phase 2: Generalized hybrid approach

- Validate the same allowlist-driven behavior with additional selected Windows
  games and remove any People Playground-specific assumptions in fixtures,
  diagnostics, or documentation.
- Expose Steam's existing compatibility settings component on macOS.
- Keep all behavior disabled for non-allowlisted games.

Phase 2 starts only after Phase 1 passes persistence and install-flow
verification.

## Chosen Architecture

Use a hybrid native and front-end patch with one source of truth: the project's
allowlisted AppIDs.

### Native state keeper

The injected native component will reapply the minimal data-only platform
eligibility override for `1118200` whenever relevant app state is requested or
rebuilt. A bounded fallback reconciliation loop may remain as a safety net, but
the primary mechanism must be event/request driven rather than a worker that
stops after 30 seconds.

The native component must not globally alter platform getters, IPC payload
shapes, or unrelated apps. Prior experiments showed that broad getter/IPC
interception has a substantially larger crash and compatibility surface.

### Front-end resource patch

A startup-loaded Steam UI patch will intercept the narrow app-overview/status
path used by the library action resolver. For allowlisted AppIDs that are not
installed, it will normalize only the invalid-platform display state to
ready-to-install.

It will not synthesize a custom button or call the install wizard directly.
Steam's existing resolver must produce `Install`, and Steam's existing executor
must call `GameActions.InstallApp`, which calls
`OpenInstallWizard([appid])`.

The patch must apply before the first relevant library render and remain active
for the full Steam UI process. A development-only CDP script is not a persistent
delivery mechanism.

### Compatibility settings exposure

In Phase 2, the resource patch will remove only the macOS visibility gate around
Steam's existing compatibility settings page. The page's native controls and
APIs remain unchanged:

- compatibility enable checkbox;
- `GetAvailableCompatTools(appid)`;
- compatibility tool selector;
- `SpecifyCompatTool(appid, tool)`.

The patch must not pretend the entire Steam client is Linux. It will target the
specific page visibility condition or insert the existing page component into
the settings navigation.

## Data Flow

1. Steam starts and loads the project's native injected component.
2. The component reads the explicit allowlist and ensures the compatibility
   tool mapping for `1118200` remains available.
3. When Steam creates or refreshes native app state, the component reapplies the
   minimal eligibility override for the allowlisted AppID.
4. Steam's UI loads the front-end patch before or during library bootstrap.
5. When `AppOverview` for `1118200` is created or refreshed, only an
   invalid-platform, not-installed state is normalized to ready-to-install.
6. Steam's unmodified action resolver emits the native `Install` action and
   native blue styling.
7. A user click follows Steam's original call chain into
   `OpenInstallWizard([1118200])`.
8. The native state keeper ensures the wizard sees an eligible backend state,
   so it reaches the install configuration page instead of error 29.
9. Steam performs its own install-location, disk-space, confirmation, download,
   update, and progress handling.

## State Rules

The patch may change presentation/action eligibility only when all are true:

- the AppID is explicitly allowlisted;
- the title has Windows content but no native macOS content;
- the title is not currently installed;
- Steam reports invalid platform solely because the host is macOS;
- the configured compatibility tool is available.

The patch must defer to Steam for installed, downloading, updating, paused,
uninstalling, missing-license, purchase-required, family-sharing, and explicit
error states. It must not overwrite active download or launch statuses.

## Persistence

Persistent means the behavior is installed into the normal project bootstrap,
not manually injected after startup.

- Native installation and UI resource patch installation must be idempotent.
- Re-running setup must update existing project-owned files without duplicating
  entries.
- Steam updates may replace patched resources, so the launcher/bootstrap must
  detect the expected Steam build/resource signature and reapply a compatible
  patch when possible.
- If signatures do not match, the system must fail closed, log the mismatch,
  leave non-allowlisted apps untouched, and provide a documented restore path.
- Original Steam files must be backed up before modification and restorable by
  a project script.

## Diagnostics and Failure Handling

Logs must distinguish:

- allowlist/configuration loading;
- native backend override application;
- front-end overview normalization;
- compatibility tool discovery;
- install-wizard entry and resulting state/error;
- resource signature mismatch;
- rollback or patch-disable actions.

If the native state cannot be made eligible, the front end must not knowingly
advertise a usable blue button. The preferred behavior is to retain Steam's
original disabled state and log the backend readiness failure.

No code path may automatically invoke `ContinueInstall` in automated or manual
verification. Tests stop at the install configuration page and cancel.

## Testing Strategy

### Automated tests

Add failing tests before implementation for:

- exact allowlist matching and rejection of unrelated AppIDs;
- invalid-platform to ready-to-install normalization;
- preservation of installed/download/update/error statuses;
- idempotent resource patch installation;
- resource signature mismatch and rollback behavior;
- native state keeper lifetime beyond the old 30-second window;
- documentation/config fixtures matching generated output.

### Live Steam verification

For `1118200`, verify:

1. Fresh Steam start shows the native blue install/download button.
2. Leaving and reopening the page preserves the button.
3. Switching views and forcing app-overview refresh preserves the button.
4. Waiting longer than the old worker lifetime preserves backend eligibility.
5. Closing and reopening Steam preserves both layers.
6. Clicking the visible button reaches native install configuration with
   `eAppError=0`.
7. Canceling the wizard starts no download.
8. A non-allowlisted Windows-only game remains unchanged.
9. Disabling or rolling back the project restores Steam's original behavior.

Phase 2 additionally verifies that the compatibility page appears for the
target game, lists `realsteamonmac-experimental`, persists tool selection, and
does not expose or alter unrelated settings.

## Delivery and Git Boundaries

Large changes are committed and pushed separately:

1. Design and implementation plan.
2. Phase 1 tests and native lifetime fix.
3. Phase 1 front-end persistent resource patch.
4. Bootstrap, rollback, and diagnostics.
5. Documentation and full Phase 1 verification evidence.
6. Phase 2 generalization and compatibility settings exposure.
7. Final verification and handoff updates.

Every commit must keep the repository testable. Generated caches, Steam
binaries, credentials, and machine-specific artifacts remain excluded.

## Success Criteria

Phase 1 is complete only when People Playground reliably shows Steam's native
blue install/download action after page navigation and a full Steam restart,
and a real click reaches the native install configuration flow with no
invalid-platform error.

Phase 2 is complete only when that mechanism uses the explicit allowlist,
continues to isolate unrelated apps, and exposes Steam's existing compatibility
settings UI on macOS without globally impersonating Linux.
