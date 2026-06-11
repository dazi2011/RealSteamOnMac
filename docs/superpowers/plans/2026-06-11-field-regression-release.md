# Field Regression Remediation And Verified Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Repair the reported Steam state, launch, compatibility-tool, container, dependency, channel, and update failures while replacing the simulated compatibility UI with Steam-owned React controls.

**Architecture:** Preserve the delayed native install/launch bridge, but make browser registry publication authoritative and event-driven. Feed discovered raw compatibility payloads into Steam's existing compatibility API and React component tree, resolve launches from Steam descriptors, compose a shared Wine runtime from versioned components, and ship independently verified install/update/uninstall packages.

**Tech Stack:** Steam SharedJSContext JavaScript, React and Steam webpack modules, Python 3, C/dyld hooks, POSIX shell, VDF/ACF/JSON, Wine/GPTK/DXMT/DXVK, macOS `pkgbuild`, Node/Python/shell/native harness tests.

---

### Task 1: Fail Native Helper Jobs Correctly

**Files:**
- Modify: `tests/test_runtime_manager.py`
- Modify: `runtime/realsteamonmac_runtime.py`
- Modify: `findings.md`
- Modify: `progress.md`

- [x] **Step 1: Write failing tests for Finder environment isolation and nonzero container exits**

Add tests that call `execute_container_action(... open-c-drive ...)`, capture
the environment passed to `run_job_process`, and assert that Wine, Steam, and
DYLD variables are absent. Add an `action_job` test whose container action
returns `-6` and assert the final JSON state is `failed`.

- [x] **Step 2: Run the focused tests and verify RED**

Run:

```bash
/usr/bin/python3 -m unittest \
  tests.test_runtime_manager.RuntimeManagerTests.test_open_c_drive_scrubs_wine_environment \
  tests.test_runtime_manager.RuntimeManagerTests.test_container_nonzero_exit_fails_job -v
```

Expected: FAIL because `/usr/bin/open` receives the Wine environment and
container nonzero exits are written as completed.

- [x] **Step 3: Implement the minimal fix**

Add `build_native_helper_environment()` with an explicit allowlist of required
host variables. Use it only for native macOS helper commands. In `action_job`,
raise `RuntimeErrorWithContext` for nonzero dependency and container exits just
as the run-command path already does.

- [x] **Step 4: Verify GREEN and regression**

Run the two focused tests, then:

```bash
/usr/bin/python3 -m unittest tests.test_runtime_manager -v
```

Expected: all runtime-manager tests PASS.

- [x] **Step 5: Commit and push**

```bash
git add tests/test_runtime_manager.py runtime/realsteamonmac_runtime.py \
  findings.md progress.md
git commit -m "fix: isolate native container helpers"
git push
```

### Task 2: Retain The Last Authoritative Steam Registry

**Files:**
- Modify: `tests/test_steamui_runtime.mjs`
- Modify: `tests/test_steamui_policy.mjs`
- Modify: `ui/realsteamonmac_ui.js`
- Modify: `progress.md`

- [x] **Step 1: Write a failing startup-race integration test**

Build a VM fixture where the first complete scan returns two managed AppIDs,
the next scan observes an uninitialized empty `appStore`, and the third scan
returns the same AppIDs. Assert that the browser never POSTs an empty registry,
never unregisters native detail subscriptions, and never makes the managed
predicate false.

- [x] **Step 2: Verify RED**

Run:

```bash
node --test tests/test_steamui_runtime.mjs
```

Expected: FAIL with an empty POST or removed AppID after the second scan.

- [x] **Step 3: Add explicit scan authority**

Require initialized overview storage before accepting an empty scan. Keep the
last accepted registry and native subscriptions when Steam temporarily exposes
an empty `allApps` store, then allow removal only after a later nonempty scan is
authoritative.

- [ ] **Step 4: Replace fixed startup delay with readiness**

**Files:**
- Modify: `launcher/steam_launcher.c`
- Modify: `hook/injection_guard.c`
- Modify: `tests/test_steam_launcher.sh`
- Modify: `tests/test_hook_environment_isolation.sh`

Add failing contract tests that reject a fixed `30` second activation as the
only condition. Start the worker when the final Steam runtime process and
required modules are present, with a bounded timeout only as fallback.

- [ ] **Step 5: Verify and commit**

Run:

```bash
node --test tests/test_steamui_runtime.mjs tests/test_steamui_policy.mjs
sh tests/test_steam_launcher.sh
sh tests/test_hook_environment_isolation.sh
```

Commit and push:

```bash
git add ui/realsteamonmac_ui.js launcher/steam_launcher.c \
  hook/injection_guard.c tests/test_steamui_runtime.mjs \
  tests/test_steamui_policy.mjs tests/test_steam_launcher.sh \
  tests/test_hook_environment_isolation.sh progress.md
git commit -m "fix: retain authoritative Steam registry"
git push
```

### Task 3: Parse Authoritative App Installation State

**Files:**
- Create: `runtime/steam_app_state.py`
- Create: `tests/test_steam_app_state.py`
- Modify: `runtime/realsteamonmac_runtime.py`
- Modify: `tests/test_runtime_manager.py`
- Modify: `progress.md`

- [x] **Step 1: Add real-shape manifest fixtures**

Create temporary ACF fixtures for:

- fully installed RDR2/Aimlabs shape;
- validating Hogwarts shape;
- Black Myth staged-only `StateFlags=1026` shape;
- manifest plus empty directory;
- missing installed depot.

- [x] **Step 2: Write failing state tests**

Assert that only a nonzero installed-depot state with nonempty content can be
launchable. Assert that staged-only and empty-directory states remain
installable/incomplete and expose a diagnostic reason.

- [x] **Step 3: Verify RED**

Run:

```bash
/usr/bin/python3 -m unittest tests.test_steam_app_state -v
```

Expected: import or assertion failure because the parser does not exist.

- [x] **Step 4: Implement the structured parser**

Use the existing VDF pair parser, but preserve nested section membership for
`InstalledDepots` and `StagedDepots`. Return an immutable dictionary containing
flags, sizes, depot counts, build/update state, directory evidence, and
`launchable`.

- [x] **Step 5: Integrate without editing manifests**

Make `find_app_installation` reject staged-only and empty-shell states for
launch/action context. Return a typed diagnostic instructing callers to use
Steam's install/repair action.

- [x] **Step 6: Verify and commit**

Run:

```bash
/usr/bin/python3 -m unittest \
  tests.test_steam_app_state tests.test_runtime_manager -v
```

Commit and push:

```bash
git add runtime/steam_app_state.py runtime/realsteamonmac_runtime.py \
  tests/test_steam_app_state.py tests/test_runtime_manager.py progress.md
git commit -m "fix: validate Steam installation state"
git push
```

### Task 4: Preserve Native Download And Repair States

**Files:**
- Modify: `tests/test_steamui_policy.mjs`
- Modify: `tests/test_steamui_runtime.mjs`
- Modify: `ui/realsteamonmac_ui.js`
- Modify: `hook/compat_gate_hook.c`
- Modify: `tests/test_native_registry_server.sh`

- [x] **Step 1: Add failing Black Myth state tests**

Model details/overview data for staged-only status, update error, validating,
downloading, and ready states. Assert that reconciliation never maps staged or
errored content to ready-to-launch status 11.

- [x] **Step 2: Verify RED**

Run:

```bash
node --test tests/test_steamui_policy.mjs tests/test_steamui_runtime.mjs
```

- [x] **Step 3: Narrow normalization**

Normalize only invalid-platform status 14 to the exact authoritative native
detail status when that status is a valid install/play/update state. Preserve
active update and error states. Do not infer status 11 merely from an existing
directory.

- [x] **Step 4: Add a native repair request boundary**

Expose a bounded action that asks Steam's existing install manager to validate
or resume the selected AppID. It must not rewrite ACF files or delete staged
depots.

- [x] **Step 5: Verify and commit**

Run the focused Node and native harness suites, then commit and push:

```bash
git add ui/realsteamonmac_ui.js hook/compat_gate_hook.c \
  tests/test_steamui_policy.mjs tests/test_steamui_runtime.mjs \
  tests/test_native_registry_server.sh
git commit -m "fix: preserve Steam download state"
git push
```

### Task 5: Resolve Exact Steam Launch Descriptors

**Files:**
- Create: `runtime/steam_launch_descriptor.py`
- Create: `tests/test_steam_launch_descriptor.py`
- Modify: `runtime/realsteamonmac_runtime.py`
- Modify: `hook/compat_gate_hook.c`
- Modify: `tests/test_spawn_redirect.sh`

- [x] **Step 1: Add failing launch-entry fixtures**

Cover:

- Hogwarts with a stale `Phoenix-Win64-Test.exe` entry and valid default
  `HogwartsLegacy.exe`;
- Aimlabs with erroneous `.app` and valid Windows `AimLab_tb.exe`;
- RDR2 with `PlayRDR2.exe` launcher role;
- multiple legitimate launch options;
- no valid Windows launch entry.

- [x] **Step 2: Verify RED**

Run:

```bash
/usr/bin/python3 -m unittest tests.test_steam_launch_descriptor -v
```

- [x] **Step 3: Implement descriptor parsing**

Consume a bounded JSON descriptor exported from Steam's decoded app details.
Validate AppID, OS, executable, working directory, arguments, and launch-entry
ID. Select the requested/default Windows entry and verify its PE target.

- [x] **Step 4: Remove normal-path EXE guessing**

Use `discover_default_executable` only for a diagnostic report. Normal launch,
action context, and recovery use the descriptor.

- [x] **Step 5: Add missing-target redirection**

When Steam presents a missing or `.app` target for a managed Windows-only
AppID, the hook launches the runtime with the validated descriptor instead of
returning Steam's executable-missing error. Unmanaged and native apps retain
the original spawn.

- [x] **Step 6: Verify and commit**

Run:

```bash
/usr/bin/python3 -m unittest \
  tests.test_steam_launch_descriptor tests.test_runtime_manager -v
sh tests/test_spawn_redirect.sh
```

Commit and push:

```bash
git add runtime/steam_launch_descriptor.py runtime/realsteamonmac_runtime.py \
  hook/compat_gate_hook.c tests/test_steam_launch_descriptor.py \
  tests/test_spawn_redirect.sh
git commit -m "fix: launch Steam-selected Windows targets"
git push
```

### Task 6: Recover Interrupted Rockstar Bootstrap State

**Files:**
- Create: `runtime/launcher_recovery.py`
- Create: `tests/test_launcher_recovery.py`
- Create: `docs/research/rdr2-rockstar-recovery-2026-06-11.md`
- Modify: `runtime/realsteamonmac_runtime.py`
- Modify: `config/dependencies.json`
- Modify: `progress.md`
- Modify: `findings.md`

- [ ] **Step 1: Snapshot the current RDR2 prefix**

Record hashes and sizes for Rockstar installer files, relevant registry keys,
launcher directories, and runtime logs. Do not mutate the prefix in this step.

- [ ] **Step 2: Write failing recovery-plan tests**

Given a depot-provided Rockstar installer plus partial launcher registry/files,
assert a plan that reruns the prerequisite and preserves game/user data.
Unknown partial state must fail closed with a snapshot path.

- [ ] **Step 3: Verify RED**

Run:

```bash
/usr/bin/python3 -m unittest tests.test_launcher_recovery -v
```

- [ ] **Step 4: Implement evidence-driven recovery**

Create a timestamped prefix snapshot, run only the verified depot prerequisite,
validate the launcher executable and registry afterward, and retain a mutation
report. Never delete the game directory or whole prefix automatically.

- [ ] **Step 5: Live RDR2 recovery acceptance**

Select GPTK, run recovery, launch `PlayRDR2.exe`, and record process/log/window
evidence. If it fails, run the existing CrossOver RDR2 bottle as the control.

- [ ] **Step 6: Commit and push**

```bash
git add runtime/launcher_recovery.py runtime/realsteamonmac_runtime.py \
  tests/test_launcher_recovery.py config/dependencies.json \
  docs/research/rdr2-rockstar-recovery-2026-06-11.md \
  progress.md findings.md
git commit -m "fix: recover interrupted Rockstar launcher"
git push
```

### Task 7: Discover Raw Compatibility Payloads

**Files:**
- Replace: `runtime/compat_tool_catalog.py`
- Modify: `tests/test_compat_tool_catalog.py`
- Create: `runtime/compat_payload_probe.py`
- Create: `tests/test_compat_payload_probe.py`
- Modify: `script/patch_steamui.py`

- [ ] **Step 1: Add failing raw-layout tests**

Create fixtures for:

- GPTK `external/` plus `wine/x86_64-*`;
- CrossOver-style base Wine;
- DXMT component tree;
- DXVK component tree;
- side-by-side versions;
- malformed/symlinked payloads;
- optional legacy project wrapper migration.

- [ ] **Step 2: Verify RED**

Run:

```bash
/usr/bin/python3 -m unittest \
  tests.test_compat_tool_catalog tests.test_compat_payload_probe -v
```

- [ ] **Step 3: Implement role and capability probes**

Inspect safe paths, Mach-O/PE architecture, known payload filenames, version
metadata, and required exports. Derive capability booleans from evidence.
Optional metadata may rename a tool but cannot invent capabilities.

- [ ] **Step 4: Generate private bridge metadata**

Generate VDF/run adapter files under the project support cache. Never require
or write them inside the user-dropped source directory.

- [ ] **Step 5: Add hot-add invalidation**

Fingerprint immediate child directories and rebuild `config.js`/browser tool
cache when the fingerprint changes.

- [ ] **Step 6: Verify and commit**

Run:

```bash
/usr/bin/python3 -m unittest \
  tests.test_compat_tool_catalog tests.test_compat_payload_probe \
  tests.test_steamui_patch -v
```

Then commit and push:

```bash
git add runtime/compat_tool_catalog.py runtime/compat_payload_probe.py \
  tests/test_compat_tool_catalog.py tests/test_compat_payload_probe.py \
  script/patch_steamui.py
git commit -m "feat: discover raw compatibility payloads"
git push
```

### Task 8: Restore Steam's Native Compatibility Controls

**Files:**
- Modify: `script/patch_steamui.py`
- Modify: `ui/realsteamonmac_ui.js`
- Modify: `tests/test_steamui_patch.py`
- Rewrite: `tests/test_steamui_runtime.mjs`
- Rewrite: `tests/test_steamui_policy.mjs`
- Rewrite: `probes/verify_people_playground_compatibility_page.js`

- [ ] **Step 1: Write tests that reject the replacement UI**

Assert that production source contains no native-row hiding,
`.realsteamonmac-controls`, custom `<select>`, `role="switch"`,
`innerHTML` control rendering, or `.realsteamonmac-modal-layer`.

- [ ] **Step 2: Add a failing native-selector integration fixture**

Instantiate the real compatibility component module shape and assert that
merged project tools appear in its original selector and selections call the
 project bridge.

- [ ] **Step 3: Verify RED**

Run:

```bash
node --test tests/test_steamui_runtime.mjs tests/test_steamui_policy.mjs
/usr/bin/python3 -m unittest tests.test_steamui_patch -v
```

- [ ] **Step 4: Profile Steam React modules**

For each supported Steam build, record exact module factory hashes and export
shapes for React, compatibility row, settings row, toggle, field, button, and
dialog manager components. Unknown shapes fail closed.

- [ ] **Step 5: Mount native React children**

Keep Steam's force row untouched. Insert project settings/actions with Steam
components through the existing React tree or a React root attached to the
native compatibility section. Use Steam's dialog manager for secondary
content. Remove all handcrafted control CSS and markup.

- [ ] **Step 6: Remove locale-dependent behavior**

Use AppID props, component identity, and route state. Localized text is display
data only.

- [ ] **Step 7: Verify and commit**

Run all Node and patcher tests, then commit and push:

```bash
git add script/patch_steamui.py ui/realsteamonmac_ui.js \
  tests/test_steamui_patch.py tests/test_steamui_runtime.mjs \
  tests/test_steamui_policy.mjs \
  probes/verify_people_playground_compatibility_page.js
git commit -m "fix: use Steam native compatibility controls"
git push
```

### Task 9: Add Non-Steam EXE Shortcuts

**Files:**
- Modify: `script/patch_steamui.py`
- Modify: `ui/realsteamonmac_ui.js`
- Modify: `hook/compat_gate_hook.c`
- Create: `runtime/nonsteam_shortcut.py`
- Create: `tests/test_nonsteam_shortcut.py`
- Create: `tests/test_nonsteam_exe_live_probe.mjs`

- [ ] **Step 1: Add failing picker/shortcut tests**

Assert `.app` keeps native behavior and `.exe` creates a validated PE shortcut
with a stable shortcut ID and compatibility prefix.

- [ ] **Step 2: Verify RED**

Run:

```bash
/usr/bin/python3 -m unittest tests.test_nonsteam_shortcut -v
```

- [ ] **Step 3: Extend Steam's existing picker**

Patch only the native file type filter and shortcut serialization path. Do not
replace the Add a Game dialog.

- [ ] **Step 4: Route managed PE shortcuts**

Allow an absolute external PE target, create
`compatdata/nonsteam-<stable-id>/pfx`, and expose the native compatibility page.

- [ ] **Step 5: Verify and commit**

Run:

```bash
/usr/bin/python3 -m unittest tests.test_nonsteam_shortcut -v
node --test tests/test_nonsteam_exe_live_probe.mjs
sh tests/test_spawn_redirect.sh
```

Then commit and push:

```bash
git add script/patch_steamui.py ui/realsteamonmac_ui.js \
  hook/compat_gate_hook.c runtime/nonsteam_shortcut.py \
  tests/test_nonsteam_shortcut.py tests/test_nonsteam_exe_live_probe.mjs \
  tests/test_spawn_redirect.sh
git commit -m "feat: add non-Steam Windows shortcuts"
git push
```

### Task 10: Make Run Command Match Windows Run

**Files:**
- Modify: `runtime/realsteamonmac_runtime.py`
- Modify: `tests/test_runtime_manager.py`
- Modify: `ui/realsteamonmac_ui.js`
- Modify: `tests/test_steamui_policy.mjs`

- [ ] **Step 1: Write failing command-resolution tests**

Cover `cmd`, `regedit`, `control`, `winecfg`, a `.cpl`, a document through
`start`, an external selected installer, `.bat`/`.cmd`, malformed arguments,
reserved environment variables, and optional log capture.

- [ ] **Step 2: Verify RED**

Run the named runtime tests and confirm command aliases are rejected.

- [ ] **Step 3: Implement typed command plans**

Return a command plan with kind `builtin`, `pe`, `batch`, `association`, or
`control-panel`. Construct fixed Wine argv vectors without a host shell.

- [ ] **Step 4: Persist picker selection**

Keep the Steam dialog mounted while the native picker job runs, and write the
selected absolute path back only after a successful completed status.

- [ ] **Step 5: Verify and commit**

Run:

```bash
/usr/bin/python3 -m unittest tests.test_runtime_manager -v
node --test tests/test_steamui_policy.mjs
```

After live `regedit`, `cmd`, and external fixture acceptance, commit and push:

```bash
git add runtime/realsteamonmac_runtime.py tests/test_runtime_manager.py \
  ui/realsteamonmac_ui.js tests/test_steamui_policy.mjs
git commit -m "feat: implement Windows Run semantics"
git push
```

### Task 11: Merge Application And Dependency Installation

**Files:**
- Create: `runtime/dependency_recipes.py`
- Create: `tests/test_dependency_recipes.py`
- Modify: `config/dependencies.json`
- Modify: `runtime/realsteamonmac_runtime.py`
- Modify: `ui/realsteamonmac_ui.js`
- Modify: `tests/test_runtime_manager.py`
- Modify: `tests/test_steamui_policy.mjs`

- [ ] **Step 1: Write failing multi-stage recipe tests**

Cover pinned download, redirect validation, extraction, fixed command stages,
success codes, post-install file/registry checks, receipt creation, and cleanup.

- [ ] **Step 2: Verify RED**

Run:

```bash
/usr/bin/python3 -m unittest tests.test_dependency_recipes -v
```

- [ ] **Step 3: Implement the versioned recipe engine**

Keep all stages structured. Do not accept arbitrary URLs or shell commands.

- [ ] **Step 4: Expand the reviewed catalog**

Add current VC++ x64/x86, .NET 4.8, DirectX June 2010, and one legally reviewed
font/runtime recipe from official sources with exact hashes and sizes.

- [ ] **Step 5: Replace the two UI entries**

Expose one Steam-native Install Application dialog with catalog, local Browse,
receipts, and repair actions. Remove the standalone Windows Components row.

- [ ] **Step 6: Verify and commit**

Run:

```bash
/usr/bin/python3 -m unittest \
  tests.test_dependency_recipes tests.test_runtime_manager -v
node --test tests/test_steamui_policy.mjs
```

After live-installing representative runtimes in a disposable prefix snapshot,
commit and push:

```bash
git add runtime/dependency_recipes.py tests/test_dependency_recipes.py \
  config/dependencies.json runtime/realsteamonmac_runtime.py \
  ui/realsteamonmac_ui.js tests/test_runtime_manager.py \
  tests/test_steamui_policy.mjs
git commit -m "feat: unify container application installs"
git push
```

### Task 12: Compose Shared Wine And Graphics Components

**Files:**
- Create: `runtime/runtime_components.py`
- Create: `tests/test_runtime_components.py`
- Modify: `runtime/realsteamonmac_runtime.py`
- Modify: `script/install_runtime_package.sh`
- Modify: `tests/test_runtime_package_installer.sh`
- Modify: `THIRD_PARTY_NOTICES.md`

- [ ] **Step 1: Write failing component-plan tests**

Model base Wine plus GPTK, DXMT, DXVK, WineD3D, Steamworks, and MetalFX
components. Assert ABI/capability conflicts are rejected and valid plans use
one base Wine tree.

- [ ] **Step 2: Verify RED**

Run:

```bash
/usr/bin/python3 -m unittest tests.test_runtime_components -v
```

- [ ] **Step 3: Build immutable component packages**

Install one base engine and separate graphics/bridge payloads. Create a private
runtime view per selected plan with safe links and a manifest fingerprint.

- [ ] **Step 4: Migrate existing per-renderer packages**

Keep old package IDs readable during migration. Do not delete existing packages
until all configured AppIDs resolve to component plans and rollback is proven.

- [ ] **Step 5: Verify size and launch behavior**

Compare package size, prefix size, launch plans, and all four renderer dry-runs.

- [ ] **Step 6: Commit and push**

Run:

```bash
/usr/bin/python3 -m unittest tests.test_runtime_components -v
sh tests/test_runtime_package_installer.sh
```

Then commit and push:

```bash
git add runtime/runtime_components.py tests/test_runtime_components.py \
  runtime/realsteamonmac_runtime.py script/install_runtime_package.sh \
  tests/test_runtime_package_installer.sh THIRD_PARTY_NOTICES.md
git commit -m "refactor: compose shared runtime components"
git push
```

### Task 13: Support Stable And Beta Steam Profiles

**Files:**
- Create: `runtime/steam_build_profile.py`
- Create: `tests/test_steam_build_profile.py`
- Modify: `script/install_realsteamonmac.sh`
- Modify: `script/install_steam_injection.sh`
- Modify: `script/patch_steamui.py`
- Modify: `hook/compat_gate_hook.c`
- Modify: `tests/test_install_realsteamonmac.sh`

- [ ] **Step 1: Add failing channel-independent fixtures**

Cover one stable manifest name, both observed beta manifest names, coexisting
stale manifests, active process evidence, matching fingerprints, and unknown
build rejection.

- [ ] **Step 2: Verify RED**

Run the profile and installer tests.

- [ ] **Step 3: Implement fingerprint-based profile selection**

Select by Valve resource hashes, Mach-O UUIDs, instruction bytes, and running
runtime metadata. Treat manifest filenames as non-authoritative hints.

- [ ] **Step 4: Produce an unknown-build diagnostic**

On rejection, write a read-only report containing hashes, UUIDs, resource
names, and manifest versions without patching Steam.

- [ ] **Step 5: Verify on installed beta and an isolated stable fixture**

Run:

```bash
/usr/bin/python3 -m unittest \
  tests.test_steam_build_profile tests.test_steamui_patch -v
sh tests/test_install_realsteamonmac.sh
sh tests/test_install_steam_injection.sh
sh tests/test_native_hook_build.sh
```

Then commit and push:

```bash
git add runtime/steam_build_profile.py tests/test_steam_build_profile.py \
  script/install_realsteamonmac.sh script/install_steam_injection.sh \
  script/patch_steamui.py hook/compat_gate_hook.c \
  tests/test_install_realsteamonmac.sh
git commit -m "fix: detect stable and beta Steam builds"
git push
```

### Task 14: Build And Test A Real Update Package

**Files:**
- Modify: `script/build_release_pkgs.sh`
- Modify: `script/check_for_updates.py`
- Modify: `tests/test_release_packaging.sh`
- Modify: `tests/test_update_manifest.py`
- Create: `packaging/update/scripts/preinstall`
- Create: `packaging/update/scripts/postinstall`
- Create: `tests/test_update_realsteamonmac.sh`

- [ ] **Step 1: Add failing manifest/update tests**

Require an `updater` artifact distinct from the installer. Test matching
installed state, mismatched Steam build, insufficient rollback data, failed
postinstall, automatic restoration, and preservation of games/PFX/user tools.

- [ ] **Step 2: Verify RED**

Run:

```bash
/usr/bin/python3 -m unittest tests.test_update_manifest -v
sh tests/test_release_packaging.sh
sh tests/test_update_realsteamonmac.sh
```

- [ ] **Step 3: Build transactional update scripts**

Snapshot changed files, install side by side, verify, atomically activate, and
restore on any failure.

- [ ] **Step 4: Verify an installed-over-installed upgrade**

Install the previous public PKG into an isolated root, apply the new update
PKG, and compare state, rollback, prefix, tool, and configuration hashes.

- [ ] **Step 5: Commit and push**

After the RED tests pass with the implementation, commit and push:

```bash
git add script/build_release_pkgs.sh script/check_for_updates.py \
  tests/test_release_packaging.sh tests/test_update_manifest.py \
  packaging/update/scripts/preinstall \
  packaging/update/scripts/postinstall \
  tests/test_update_realsteamonmac.sh
git commit -m "feat: add transactional update package"
git push
```

### Task 15: CrossOver Static And Dynamic Reference Study

**Files:**
- Create: `docs/research/crossover-runtime-and-bottle-study-2026-06-11.md`
- Create: `script/trace_crossover_lldb.sh`
- Create: `tests/test_trace_crossover_lldb.sh`

- [ ] **Step 1: Record static layout and callable tools**

Document shared engine sizes, GPTK/DXMT/DXVK paths, bottle templates, recipes,
launcher binaries, environment variables, and bottle configuration files.

- [ ] **Step 2: Write a safe LLDB trace script**

The script accepts a PID, verifies the exact signed CrossOver executable,
attaches, sets named/symbolic breakpoints where available, logs backtraces and
selected arguments, detaches, and never writes process memory.

- [ ] **Step 3: Test script safety**

Use a fixture process and mock LLDB transcript to prove signature/path checks,
immediate detach on error, and absence of memory-write commands.

- [ ] **Step 4: Trace bounded operations**

Capture create bottle, run command, registry editor, dependency installation,
and application launch boundaries. Record only technical behavior, not secrets
or license material.

- [ ] **Step 5: Commit and push**

Run:

```bash
sh tests/test_trace_crossover_lldb.sh
sh -n script/trace_crossover_lldb.sh
```

Then commit and push:

```bash
git add docs/research/crossover-runtime-and-bottle-study-2026-06-11.md \
  script/trace_crossover_lldb.sh tests/test_trace_crossover_lldb.sh
git commit -m "docs: trace CrossOver runtime behavior"
git push
```

### Task 16: Automated And Live Game Matrix

**Files:**
- Create: `script/run_game_acceptance.py`
- Create: `tests/test_game_acceptance.py`
- Create: `docs/research/game-matrix-2026-06-11.md`
- Modify: `progress.md`
- Modify: `findings.md`

- [ ] **Step 1: Implement a non-destructive acceptance harness**

Record AppID, manifest state, selected descriptor, runtime/component plan,
process tree, exit code, window evidence, renderer logs, FPS/frame-time source,
Cloud completion, and prefix mutation summary.

- [ ] **Step 2: Unit-test parsing and timeout behavior**

Use fixture logs/process data. The harness must never delete a game or prefix.

- [ ] **Step 3: Run the downloaded-library matrix**

Use GPTK for newer DX12 titles and DXMT for older DX10/DX11 titles. Test
Hogwarts, Aimlabs, RDR2, People Playground, and every other downloaded
Windows-only game that can be launched without destructive setup.

- [ ] **Step 4: Test representative DLSS conversion**

Select one or two games whose payload and runtime logs prove DLSS/MetalFX use.
Record enabled capability, copied DLL hashes, renderer evidence, and observed
behavior.

- [ ] **Step 5: Run CrossOver controls for RealSteamOnMac-only failures**

Use the existing dedicated bottles. A CrossOver success is recorded as a
project compatibility gap; failure in both is recorded separately.

- [ ] **Step 6: Commit and push**

Run:

```bash
/usr/bin/python3 -m unittest tests.test_game_acceptance -v
```

Then commit and push:

```bash
git add script/run_game_acceptance.py tests/test_game_acceptance.py \
  docs/research/game-matrix-2026-06-11.md progress.md findings.md
git commit -m "test: record Windows game acceptance matrix"
git push
```

Do not claim untested games as working.

### Task 17: Documentation, Packages, Publication, And Remote Proof

**Files:**
- Rewrite: `README.md`
- Rewrite: `README.zh-CN.md`
- Modify: `docs/interfaces.md`
- Modify: `docs/project-history.md`
- Create: `docs/handoff/current-state-2026-06-11.md`
- Modify: `task_plan.md`
- Modify: `progress.md`
- Modify: `findings.md`

- [ ] **Step 1: Update documentation to actual behavior**

Remove screenshots and claims for replacement controls. Document raw tool
layouts, stable/beta detection, EXE shortcuts, command semantics, update PKG,
known game results, rollback, legal boundaries, and unsigned/notarization
status.

- [ ] **Step 2: Run the complete source matrix**

```bash
node --test tests/*.mjs
/usr/bin/python3 -m unittest discover -s tests -p 'test_*.py'
for test_file in tests/test_*.sh; do sh "$test_file"; done
```

Expected: all PASS with no warnings or unexpected output.

- [ ] **Step 3: Run syntax, formatting, secret, license, and large-file checks**

Compile Python, check every shell file with `sh -n`, check JavaScript syntax,
build native components with warnings as errors, run `git diff --check`, and
scan the release tree/history for credentials and unlicensed proprietary
payloads.

- [ ] **Step 4: Build and inspect all three PKGs**

Build install, update, and uninstall packages. Expand them independently,
verify versions, scripts, payload hashes, supported Steam profiles, manifest
signature, package signatures, and rollback files.

- [ ] **Step 5: Run live install/update/uninstall acceptance**

Back up live Steam, install the package, verify native controls and the game
matrix, apply Update.pkg, verify preservation, uninstall, prove exact Steam
restoration, then reinstall the release candidate.

- [ ] **Step 6: Commit and push final documentation**

Commit only after all required evidence exists:

```bash
git add README.md README.zh-CN.md docs/interfaces.md \
  docs/project-history.md docs/handoff/current-state-2026-06-11.md \
  task_plan.md progress.md findings.md
git commit -m "docs: publish verified release guidance"
git push
```

- [ ] **Step 7: Publish and verify remotely**

Tag the final commit, create the GitHub release, upload PKGs, checksums,
manifest, and signature, redownload every asset, verify byte identity and
signature, and confirm the latest-release API.

- [ ] **Step 8: Close the goal**

Mark the persistent goal complete only after the release and remote proofs are
finished. Report any unsupported game or unsigned package limitation plainly.
