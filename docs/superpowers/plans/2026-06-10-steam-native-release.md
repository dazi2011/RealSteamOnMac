# Steam-Native Compatibility And Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the mis-mounted branded control dashboard with Steam-native compatibility controls, support validated side-by-side tools from Steam's standard directory, and ship transactional install, uninstall, and update PKGs.

**Architecture:** Preserve the proven dynamic Windows-only registry and delayed native engine. Add a validated filesystem catalog and per-AppID tool identity, narrow UI mounting to actual compatibility popups, move complex actions to secondary dialogs, then wrap the existing installers in reversible PKG workflows.

**Tech Stack:** JavaScript in Steam SharedJSContext, Python 3 runtime/patcher, C dyld/native engine, POSIX shell, VDF/JSON metadata, macOS `pkgbuild`/`productbuild`, Node/Python/shell tests.

---

### Task 1: Record The New Baseline And Root Cause

**Files:**
- Modify: `task_plan.md`
- Modify: `progress.md`
- Modify: `findings.md`

- [ ] Add Phase 7 with the exact standard-directory, UI, runtime, packaging, documentation, and publication requirements.
- [ ] Record the confirmed weak-anchor root cause and the Cloud constraint.
- [ ] Record CrossOver inspection boundaries and the repository's current private/no-release state.
- [ ] Run `git diff --check` and confirm no whitespace errors.
- [ ] Commit the documentation baseline.

### Task 2: Prevent Library-Page Control Mounts

**Files:**
- Modify: `tests/test_steamui_runtime.mjs`
- Modify: `ui/realsteamonmac_ui.js`

- [ ] Add a failing DOM fixture proving a Windows library details document with project text receives no controls.
- [ ] Run `node --test tests/test_steamui_runtime.mjs` and confirm the new test fails because the old weak anchor mounts a panel.
- [ ] Add strict properties-popup, compatibility-page, combobox, and AppID evidence helpers.
- [ ] Remove the project-name text search as a mount criterion.
- [ ] Replace the dashboard with a compact settings root and ensure stale project roots are removed from nonmatching documents.
- [ ] Run the focused Node test and the complete Node suite.
- [ ] Commit the mount-guard fix.

### Task 3: Scan Standard Compatibility Tools

**Files:**
- Create: `runtime/compat_tool_catalog.py`
- Modify: `script/patch_steamui.py`
- Modify: `script/install_steam_injection.sh`
- Modify: `tests/test_steamui_patch.py`
- Modify: `tests/test_install_steam_injection.sh`
- Create: `tests/test_compat_tool_catalog.py`

- [ ] Add failing tests for valid side-by-side DXMT tools, duplicates, malformed metadata, symlink escapes, and mismatched VDF identifiers.
- [ ] Run the focused Python tests and confirm scanner tests fail before implementation.
- [ ] Implement bounded VDF extraction and schema-1 metadata validation.
- [ ] Add `--compat-tools-root` to the patcher and emit the scanned catalog into `config.js`.
- [ ] Install first-party tools into `~/Library/Application Support/Steam/compatibilitytools.d` and copy the scanner module beside the installed patcher.
- [ ] Stop copying the canonical tool repository under the project support root.
- [ ] Run focused Python and installer shell tests.
- [ ] Commit standard-directory discovery.

### Task 4: Persist Tool Identity And Runtime Package

**Files:**
- Modify: `compat-tool/*/realsteamonmac.json`
- Modify: `runtime/realsteamonmac_runtime.py`
- Modify: `hook/compat_gate_hook.c`
- Modify: `ui/realsteamonmac_ui.js`
- Modify: `tests/test_runtime_manager.py`
- Modify: `tests/test_native_registry_server.sh`
- Modify: `tests/test_steamui_runtime.mjs`

- [ ] Add failing tests for `compat_tool` migration, selection persistence, immutable package resolution, and invalid identifiers.
- [ ] Run focused Node, Python, and native harness tests and confirm the new assertions fail.
- [ ] Extend the fixed native config schema with a bounded `compat_tool`.
- [ ] Save both tool identity and renderer from Steam's dropdown.
- [ ] Resolve the selected tool metadata below the standard directory and load its immutable runtime package.
- [ ] Preserve migration from legacy renderer-only configs.
- [ ] Run focused suites and commit per-tool runtime selection.

### Task 5: Capability And DXMT MetalFX Rules

**Files:**
- Modify: `runtime/compat_tool_catalog.py`
- Modify: `runtime/realsteamonmac_runtime.py`
- Modify: `ui/realsteamonmac_ui.js`
- Modify: `tests/test_compat_tool_catalog.py`
- Modify: `tests/test_runtime_manager.py`
- Modify: `tests/test_steamui_runtime.mjs`

- [ ] Add failing tests for old DXMT without MetalFX, capable DXMT with required payload, and inconsistent capability metadata.
- [ ] Run focused tests and confirm failure.
- [ ] Make controls capability-driven and include disabled-reason text.
- [ ] Probe the selected runtime for the MetalFX payload before enabling it.
- [ ] Keep DXR and other renderer-specific settings bounded by metadata and runtime evidence.
- [ ] Run focused tests and commit capability-aware controls.

### Task 6: Steam-Style Settings And Secondary Dialogs

**Files:**
- Modify: `ui/realsteamonmac_ui.js`
- Modify: `tests/test_steamui_runtime.mjs`
- Modify: `hook/compat_gate_hook.c`
- Modify: `runtime/realsteamonmac_runtime.py`
- Modify: `tests/test_runtime_manager.py`

- [ ] Add failing tests for Steam-style toggle rows, compact actions, modal open/close, browse payloads, and no inline run/dependency forms.
- [ ] Run the focused Node tests and confirm failure.
- [ ] Build compact vertical rows using inherited Steam typography, spacing, buttons, and switch styling.
- [ ] Add Run Command, Install Component, and Container Operations dialogs.
- [ ] Add native actions for Finder reveal, file selection, Wine configuration, restart, task manager, quit-all, and recoverable PFX removal.
- [ ] Run focused Node/Python/native tests and commit each dialog/action group.

### Task 7: Windows 10 Prefix And MSync Verification

**Files:**
- Modify: `runtime/realsteamonmac_runtime.py`
- Modify: `tests/test_runtime_manager.py`
- Modify: `docs/research/runtime-prefix-and-msync-2026-06-10.md`

- [ ] Add failing tests proving new prefixes set Windows 10 and MSync emits `WINEMSYNC=1`.
- [ ] Run the focused Python tests and confirm failure.
- [ ] Initialize new PFX state to Windows 10 before game launch.
- [ ] Keep `WINEESYNC=1` only as the documented D3DMetal compatibility hint and never label it FSync.
- [ ] Run the focused tests and a dry-run environment probe.
- [ ] Commit prefix/MSync behavior.

### Task 8: CrossOver Dependency Research

**Files:**
- Create: `docs/research/crossover-dependency-metadata-2026-06-10.md`
- Modify: `config/dependencies.json`
- Modify: `tests/test_runtime_package_installer.sh`

- [ ] Inspect CrossOver's readable setup libraries, bottle templates, and recipe/index locations without copying proprietary runtime payloads.
- [ ] Document which metadata is local, which is fetched, and which licenses permit reuse.
- [ ] Add only independently verified official dependency URLs with exact size and SHA-256.
- [ ] Run catalog validation tests and commit the reviewed catalog.

### Task 9: Transactional PKG Install, Uninstall, And Update

**Files:**
- Create: `packaging/scripts/preinstall`
- Create: `packaging/scripts/postinstall`
- Create: `packaging/uninstall/scripts/postinstall`
- Create: `script/build_release_pkgs.sh`
- Create: `script/uninstall_realsteamonmac.sh`
- Create: `script/check_for_updates.py`
- Create: `config/release-manifest.schema.json`
- Create: `tests/test_release_packaging.sh`
- Create: `tests/test_uninstall_realsteamonmac.sh`
- Create: `tests/test_update_manifest.py`

- [ ] Add failing isolated-root tests for process stop, rollback creation, owned-file removal, PFX preservation, and manifest rejection.
- [ ] Run focused tests and confirm failure.
- [ ] Implement transactional install and uninstall entrypoints.
- [ ] Build `RealSteamOnMac-Install.pkg` and `RealSteamOnMac-Uninstall.pkg`.
- [ ] Implement signed-manifest update checking with hash and Steam-build validation.
- [ ] Run isolated-root install/uninstall/update tests and inspect package contents.
- [ ] Commit release packaging.

### Task 10: Product Documentation And Repository Cleanup

**Files:**
- Rewrite: `README.md`
- Create: `README.zh-CN.md`
- Create: `docs/project-history.md`
- Create: `docs/interfaces.md`
- Modify: `progress.md`
- Modify: `task_plan.md`

- [ ] Move progress-report material out of README.
- [ ] Write bilingual features, requirements, install, uninstall, update, tool-package, known-issues, acknowledgements, licenses, and Valve/Steam non-affiliation sections.
- [ ] Add verified screenshots with accessible captions.
- [ ] Document public interfaces and recovery procedures.
- [ ] Run link/path checks and commit documentation.

### Task 11: Full Verification And Live Acceptance

**Files:**
- Modify: `progress.md`
- Create: `docs/handoff/current-state-2026-06-10.md`

- [ ] Run all Node tests.
- [ ] Run all Python tests.
- [ ] Run every shell contract sequentially.
- [ ] Build native components with warnings treated as errors.
- [ ] Back up live Steam and install through the release PKG.
- [ ] Verify Cloud, native titles, Windows-only registry, scrolling, tool selection, dialogs, one game launch, normal exit, and AutoCloud.
- [ ] Uninstall through the release PKG and verify exact Steam restoration plus PFX preservation.
- [ ] Reinstall and capture final screenshots and hashes.
- [ ] Record every command, result, artifact hash, and remaining limitation.

### Task 12: Publish

**Files:**
- Modify: `README.md`
- Modify: `README.zh-CN.md`

- [ ] Run secret, license, large-file, and repository-history checks.
- [ ] Confirm the working tree contains only intended release changes.
- [ ] Create a focused release commit and push the branch.
- [ ] Create a tagged GitHub Release with both PKGs, checksums, bilingual notes, and known issues.
- [ ] Change repository visibility from private to public only after the release assets are remotely verified.
- [ ] Confirm the public repository, tag, release assets, default branch, and downloadable checksums.

