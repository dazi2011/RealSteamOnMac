# People Playground Native Download Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist Steam's native blue install action for allowlisted People Playground and make its click reach the original install configuration flow after navigation and full Steam restarts.

**Architecture:** Keep backend platform eligibility alive with the injected native hook for the entire Steam process. Install a fail-closed Steam UI resource patch before every launch; the patch observes Steam's existing React action components and normalizes only allowlisted, backend-ready `InvalidPlatform` overview state to `ReadyToInstall`.

**Tech Stack:** C11/macOS Mach APIs, POSIX shell, Python 3 standard library, browser JavaScript, Node test runner, Steam CDP for bounded live verification.

---

## File Structure

- `hook/compat_gate_hook.c`: continuously reconciles allowlisted native app objects for the lifetime of the Steam runtime.
- `ui/realsteamonmac_ui.js`: observes Steam's existing React tree and synchronizes allowlisted overview state only when app details report ready-to-install.
- `script/patch_steamui.py`: validates known Steam UI resources, installs/verifies/restores the injected scripts atomically, and generates the browser allowlist from `allowlist.txt`.
- `launcher/steam_launcher.c`: invokes the installed UI patcher before starting the Steam runtime and fails back to the original bootstrap if verification fails.
- `script/install_steam_injection.sh`: installs the patcher/UI asset and performs the initial resource patch.
- `tests/test_steamui_patch.py`: unit tests state normalization policy and resource patch lifecycle.
- `tests/test_steamui_patch.sh`: command-line patcher contract and current-build signature checks.
- Existing hook/launcher/installer tests: protect lifetime, bootstrap, and installed-file contracts.
- `probes/verify_people_playground_persistent_ui.js`: read-only live verification of native button styling and synchronized state.
- `README.md`, handoff, and research documents: record commands, evidence, limitations, rollback, and Phase 2 entry point.

## Allowed APIs and Evidence

- `SteamClient.Installs.OpenInstallWizard([appid])` is called only by Steam's
  existing install action; project probes must not call `ContinueInstall`.
  Evidence: `probes/open_people_playground_install_wizard_experiment.js` and
  `docs/handoff/current-state-2026-06-07.md`.
- Steam's current UI action resolver uses selected per-client
  `display_status`; `14` is invalid platform and `9` is ready to install.
  Evidence: `probes/enable_people_playground_ui_experiment.js` and
  `docs/research/technical-mixed-macos-windows-steam-library-research-2026-06-07.md`.
- The current Steam UI entry resource is `steamui/index.html`, SHA-256
  `55ced284314dbc65bff38fb1333d4f4bd617635895e2c0e2197b05028c243282`,
  with the exact `/library.js` script anchor.
- Use only Python standard-library APIs: `argparse`, `hashlib`, `json`,
  `os.replace`, `pathlib`, `shutil`, and `tempfile`.
- Use only existing launcher process APIs: `fork`, `execv`, `waitpid`, and
  normal fallback through `exec_original_bootstrap`.

Do not invent Steam APIs, synthesize a new button, globally report Linux, patch
non-allowlisted AppIDs, or automatically confirm an installation.

### Task 1: Native Reconciliation Lifetime

**Files:**
- Modify: `tests/test_compat_gate_hook.sh`
- Modify: `hook/compat_gate_hook.c`

- [ ] **Step 1: Write the failing lifetime contract**

Add assertions that reject the old bounded worker and require a process-lifetime
loop with a slower idle interval:

```sh
if grep -q 'DATA_OVERRIDE_ATTEMPTS' "$SOURCE"; then
    echo "native reconciliation must not expire after a fixed attempt count" >&2
    exit 1
fi
grep -q 'DATA_OVERRIDE_RECONCILE_DELAY_US' "$SOURCE"
grep -q 'while (is_steam_runtime_process())' "$SOURCE"
grep -q 'data override: reconciliation worker stopped' "$SOURCE"
```

- [ ] **Step 2: Run the test and verify RED**

Run:

```sh
sh tests/test_compat_gate_hook.sh
```

Expected: FAIL because `DATA_OVERRIDE_ATTEMPTS` still exists.

- [ ] **Step 3: Implement the minimal lifetime worker**

Replace the 30-attempt loop with:

```c
#define DATA_OVERRIDE_RECONCILE_DELAY_US 1000000

static void *data_override_worker(void *context) {
  (void)context;
  bool environment_cleared = false;
  while (is_steam_runtime_process()) {
    if (find_image_by_uuid(kSteamUIUUID) != NULL) {
      size_t patched = realsteamonmac_apply_data_overrides();
      if (patched > 0 && !environment_cleared) {
        clear_injection_environment();
        environment_cleared = true;
        log_line("data override: initial reconciliation completed");
      }
    }
    usleep(DATA_OVERRIDE_RECONCILE_DELAY_US);
  }
  clear_injection_environment();
  log_line("data override: reconciliation worker stopped");
  return NULL;
}
```

Guard allowlist loading so repeated scans do not reload configuration or flood
the log. Log reconciliation only when at least one object changed.

- [ ] **Step 4: Run focused and full tests**

Run:

```sh
sh tests/test_compat_gate_hook.sh
node --test tests/steam_cdp.test.mjs
for test_file in tests/test_*.sh; do sh "$test_file"; done
```

Expected: all PASS.

- [ ] **Step 5: Commit and push**

```sh
git add hook/compat_gate_hook.c tests/test_compat_gate_hook.sh
git commit -m "fix: keep native platform reconciliation alive"
git push origin codex/people-playground-experiment
```

### Task 2: Front-End State Synchronizer

**Files:**
- Create: `ui/realsteamonmac_ui.js`
- Create: `tests/test_steamui_policy.mjs`

- [ ] **Step 1: Write failing policy tests**

Load the UI module through an exported CommonJS-compatible policy function and
assert:

```js
assert.deepEqual(
  decideOverviewPatch({
    allowlisted: true,
    detailsStatus: 9,
    overviewStatus: 14,
    installed: false,
  }),
  { normalize: true },
);
assert.deepEqual(
  decideOverviewPatch({
    allowlisted: true,
    detailsStatus: 14,
    overviewStatus: 14,
    installed: false,
  }),
  { normalize: false },
);
assert.deepEqual(
  decideOverviewPatch({
    allowlisted: false,
    detailsStatus: 9,
    overviewStatus: 14,
    installed: false,
  }),
  { normalize: false },
);
```

Add preservation cases for installed and active download/update statuses.

- [ ] **Step 2: Run the test and verify RED**

Run:

```sh
node --test tests/test_steamui_policy.mjs
```

Expected: FAIL because `ui/realsteamonmac_ui.js` does not exist.

- [ ] **Step 3: Implement the policy and observer**

Implement constants and a pure policy:

```js
const INVALID_PLATFORM = 14;
const READY_TO_INSTALL = 9;

function decideOverviewPatch(state) {
  return {
    normalize:
      state.allowlisted &&
      !state.installed &&
      state.detailsStatus === READY_TO_INSTALL &&
      state.overviewStatus === INVALID_PLATFORM,
  };
}
```

At browser startup:

1. Read `globalThis.__REALSTEAMONMAC_CONFIG__.appids`.
2. Scan only `[role=button], button` nodes.
3. Walk React ancestors to find matching `overview`, `details`, and an action
   component with `forceUpdate`.
4. Normalize `display_status`, `is_available_on_current_platform`, and
   `is_invalid_os_type` only when the pure policy returns true.
5. Debounce a `MutationObserver` and retain a low-frequency reconciliation
   interval so page navigation and object refreshes are covered.
6. Record counters in `globalThis.__REALSTEAMONMAC_UI_STATUS__`; do not call any
   install, launch, update, or compatibility-setting API.

Expose the pure policy through `module.exports` only when `module` exists so
Node tests do not start the browser observer.

- [ ] **Step 4: Run focused tests**

Run:

```sh
node --test tests/test_steamui_policy.mjs
sh tests/test_enable_people_playground_ui_experiment.sh
```

Expected: PASS.

- [ ] **Step 5: Commit and push**

```sh
git add ui/realsteamonmac_ui.js tests/test_steamui_policy.mjs
git commit -m "feat: synchronize allowlisted Steam install actions"
git push origin codex/people-playground-experiment
```

### Task 3: Signed Resource Patcher and Rollback

**Files:**
- Create: `script/patch_steamui.py`
- Create: `tests/test_steamui_patch.py`
- Create: `tests/test_steamui_patch.sh`

- [ ] **Step 1: Write failing resource lifecycle tests**

Create a temporary `steamui/index.html` matching the current one and verify:

```python
patch_steamui(steamui_root, ui_source, allowlist)
assert 'src="/realsteamonmac/config.js"' in index.read_text()
assert 'src="/realsteamonmac/ui.js"' in index.read_text()
assert json.loads(extract_config(config_path))["appids"] == [1118200]
first = index.read_bytes()
patch_steamui(steamui_root, ui_source, allowlist)
assert index.read_bytes() == first
verify_steamui(steamui_root)
restore_steamui(steamui_root)
assert index.read_bytes() == original
```

Also assert that an unknown clean index hash is rejected without changing any
file, duplicate/invalid allowlist entries are filtered, and restore refuses a
missing or inconsistent backup.

- [ ] **Step 2: Run tests and verify RED**

Run:

```sh
python3 -m unittest tests/test_steamui_patch.py -v
sh tests/test_steamui_patch.sh
```

Expected: FAIL because the patcher is absent.

- [ ] **Step 3: Implement atomic patch, verify, and restore modes**

The patcher must:

```python
KNOWN_INDEX_SHA256 = {
    "55ced284314dbc65bff38fb1333d4f4bd617635895e2c0e2197b05028c243282"
}
ANCHOR = '<script defer="defer" src="/library.js"></script>'
INJECTION = (
    ANCHOR
    + '<script defer="defer" src="/realsteamonmac/config.js"></script>'
    + '<script defer="defer" src="/realsteamonmac/ui.js"></script>'
)
```

Use an atomic temporary-file plus `os.replace` for index/config/UI writes.
Create `index.html.realsteamonmac.original` before the first patch. On a marked
index, verify rather than append duplicate tags. Generate config from positive,
unique numeric AppIDs only. Support:

```text
patch_steamui.py install --steamui-root PATH --ui-source PATH --allowlist PATH
patch_steamui.py verify --steamui-root PATH
patch_steamui.py restore --steamui-root PATH
```

- [ ] **Step 4: Run focused and full tests**

Run:

```sh
python3 -m unittest tests/test_steamui_patch.py -v
sh tests/test_steamui_patch.sh
for test_file in tests/test_*.sh; do sh "$test_file"; done
```

Expected: all PASS.

- [ ] **Step 5: Commit and push**

```sh
git add script/patch_steamui.py tests/test_steamui_patch.py tests/test_steamui_patch.sh
git commit -m "feat: add guarded Steam UI resource patcher"
git push origin codex/people-playground-experiment
```

### Task 4: Bootstrap Installation and Automatic Reapplication

**Files:**
- Modify: `tests/test_steam_launcher.sh`
- Modify: `tests/test_install_steam_injection.sh`
- Modify: `launcher/steam_launcher.c`
- Modify: `script/install_steam_injection.sh`

- [ ] **Step 1: Write failing launcher and installer contracts**

Require support assets:

```sh
test -f "$SUPPORT/patch_steamui.py"
test -f "$SUPPORT/ui/realsteamonmac_ui.js"
test -f "$RUNTIME_APP/Contents/MacOS/steamui/index.html.realsteamonmac.original"
grep -q '/realsteamonmac/ui.js' \
    "$RUNTIME_APP/Contents/MacOS/steamui/index.html"
```

Extend the launcher fixture with a clean `steamui/index.html`, run dry mode, and
assert output includes `steamui=verified`.

- [ ] **Step 2: Run both tests and verify RED**

Run:

```sh
sh tests/test_steam_launcher.sh
sh tests/test_install_steam_injection.sh
```

Expected: FAIL because no UI patcher/assets are installed or invoked.

- [ ] **Step 3: Install and invoke the patcher**

`install_steam_injection.sh` copies:

```text
script/patch_steamui.py -> $SUPPORT_ROOT/patch_steamui.py
ui/realsteamonmac_ui.js -> $SUPPORT_ROOT/ui/realsteamonmac_ui.js
```

It then runs `python3 ... install` against the runtime `steamui` directory
before signing/verifying the app.

The launcher builds patcher, UI source, allowlist, and steamui paths; forks and
executes:

```text
/usr/bin/python3 PATCHER install
  --steamui-root STEAMUI
  --ui-source UI_SOURCE
  --allowlist ALLOWLIST
```

If the child exits nonzero, call `exec_original_bootstrap` with a resource-patch
failure reason. In dry-run mode, still run and report patch verification so the
contract exercises the real bootstrap path.

- [ ] **Step 4: Run full regression suite**

Run:

```sh
sh tests/test_steam_launcher.sh
sh tests/test_install_steam_injection.sh
node --test tests/*.mjs
python3 -m unittest tests/test_steamui_patch.py -v
for test_file in tests/test_*.sh; do sh "$test_file"; done
```

Expected: all PASS.

- [ ] **Step 5: Commit and push**

```sh
git add launcher/steam_launcher.c script/install_steam_injection.sh \
  tests/test_steam_launcher.sh tests/test_install_steam_injection.sh
git commit -m "feat: install persistent Steam UI bootstrap patch"
git push origin codex/people-playground-experiment
```

### Task 5: Safe Live Installation and Persistence Verification

**Files:**
- Create: `probes/verify_people_playground_persistent_ui.js`
- Create: `tests/test_verify_people_playground_persistent_ui.sh`
- Modify only through project scripts: installed Steam bootstrap/runtime/UI resources.

- [ ] **Step 1: Write the failing read-only probe contract**

Require the probe to report AppID, overview/details status, button pointer
events, computed background, and UI patch status. Reject:

```sh
if grep -Eq 'ContinueInstall|RunGame|ResumeAppUpdate|SpecifyCompatTool' "$PROBE"; then
    echo "persistent UI verification must remain read-only" >&2
    exit 1
fi
```

- [ ] **Step 2: Implement the read-only probe and pass its static test**

The probe finds the `1118200` React context and returns:

```js
{
  appid: 1118200,
  overviewStatus: selected.display_status,
  detailsStatus: details.eDisplayStatus,
  pointerEvents: getComputedStyle(visibleButton).pointerEvents,
  background: getComputedStyle(visibleButton).backgroundImage,
  patchStatus: globalThis.__REALSTEAMONMAC_UI_STATUS__,
}
```

Run:

```sh
sh tests/test_verify_people_playground_persistent_ui.sh
```

Expected: PASS.

- [ ] **Step 3: Build, stop Steam cleanly, and install**

Run the existing build scripts, request normal Steam quit, confirm the runtime
process is gone, then run `install_steam_injection.sh` with the existing clean
backup. Do not kill the process or modify live resources.

Expected installer output includes launcher, hook, compatibility tools,
allowlist, and verified Steam UI resource patch.

- [ ] **Step 4: Verify a fresh start**

Start Steam with `-cef-enable-debugging`, navigate to People Playground, and run:

```sh
node script/steam_cdp.mjs \
  --target-title Steam \
  --expression-file probes/verify_people_playground_persistent_ui.js
```

Expected:

```text
overviewStatus=9
detailsStatus=9
pointerEvents=auto
background contains linear-gradient
```

- [ ] **Step 5: Verify navigation and lifetime**

Leave the page, return, wait longer than 30 seconds, and repeat the probe.
Close Steam normally, reopen it, return to the page, and repeat again.

Expected: the same ready/native-blue result in all cases.

- [ ] **Step 6: Verify original click flow without downloading**

Click the actual visible Steam button, inspect install manager state, and require:

```text
eInstallState=7
eAppError=0
rgApps[0].nAppID=1118200
```

Cancel through the existing cancellation probe. Confirm no download began and
no `ContinueInstall` call appears in project probes/logs.

- [ ] **Step 7: Commit evidence and push**

```sh
git add probes/verify_people_playground_persistent_ui.js \
  tests/test_verify_people_playground_persistent_ui.sh
git commit -m "test: verify persistent People Playground install UI"
git push origin codex/people-playground-experiment
```

### Task 6: Documentation, Handoff, and Phase 2 Gate

**Files:**
- Modify: `README.md`
- Modify: `docs/handoff/current-state-2026-06-07.md`
- Modify: `docs/research/technical-mixed-macos-windows-steam-library-research-2026-06-07.md`

- [ ] **Step 1: Update current behavior and commands**

Document:

- permanent native reconciliation;
- front-end fail-closed condition (`details=9` before overview normalization);
- UI resource hash and marker;
- install, verify, and restore commands;
- successful restart/navigation/click evidence;
- known Steam update compatibility boundary;
- Phase 2 work: additional allowlist validation and native compatibility-page
  exposure.

- [ ] **Step 2: Run documentation and anti-pattern checks**

Run:

```sh
rg -n '30-second|temporary UI|CDP injection|error 29|display_status|patch_steamui' \
  README.md docs
rg -n 'ContinueInstall|global.*linux|PLATFORM.*linux' ui script launcher hook
git diff --check
```

Expected: old temporary limitations are clearly superseded; no automatic
install confirmation or global Linux impersonation exists.

- [ ] **Step 3: Run final verification**

Run:

```sh
node --test tests/*.mjs
python3 -m unittest tests/test_steamui_patch.py -v
for test_file in tests/test_*.sh; do sh "$test_file"; done
git status --short
```

Expected: all tests PASS and only intended documentation changes remain.

- [ ] **Step 4: Commit and push**

```sh
git add README.md docs/handoff/current-state-2026-06-07.md \
  docs/research/technical-mixed-macos-windows-steam-library-research-2026-06-07.md
git commit -m "docs: record persistent native Steam install flow"
git push origin codex/people-playground-experiment
```

Phase 1 is complete only after the live restart and real-button cancellation
checks pass. Phase 2 begins from that verified commit, not from an unverified
resource patch.
