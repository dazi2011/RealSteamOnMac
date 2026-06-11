# Field Regression Remediation And Verified Release Design

Date: 2026-06-11

## Objective

Repair the reported Steam, launch, runtime, container, and packaging failures
without preserving the replacement compatibility UI that caused several of
them. The release must:

- use Steam's actual compatibility page, force-tool row, selector, setting
  rows, switches, buttons, and dialogs;
- accept user-dropped GPTK, Wine, DXMT, and DXVK payload directories under
  `~/Library/Application Support/Steam/compatibilitytools.d`;
- distinguish installed, staged, incomplete, and missing game content;
- launch the executable selected by Steam rather than guessing from the game
  directory;
- support native `.app` entries and compatibility-managed `.exe` non-Steam
  entries without confusing the two;
- use one compositional shared runtime instead of copying a full Wine tree per
  renderer;
- make Run Command, Finder, dependency installation, Rockstar recovery,
  stable/beta Steam installation, and in-place PKG updates verifiable;
- publish no compatibility or performance claim without direct evidence.

## Confirmed Root Causes

### Compatibility UI

The deployed code hides Steam's force-compatibility row and builds a project
`<select>`, switches, buttons, and full-screen modal layer with `innerHTML`.
Compatibility-page detection and acceptance probes depend on Chinese or English
text. This is a replacement UI, not Steam-native integration.

Steam already loads the real compatibility React component after the guarded
Linux-only page condition is relaxed. Its data path is
`GetAvailableCompatTools(appid)` and `SpecifyCompatTool(appid, tool)`. The
project already wraps those APIs, so the original selector can display project
tools without being replaced.

### Restart And Language Failures

The browser registry can publish a transient empty set while Steam stores are
still initializing. The native hook then restores the install gate for all
games before a later scan returns the 34 valid AppIDs. This produces delayed or
temporarily Windows-only actions.

Text matching for Chinese and English headings, buttons, and force-tool labels
breaks in other locales. AppID, React component identity, route, data model,
and native callbacks must replace localized text as control-flow inputs.

### Installation State

The runtime accepts an app manifest and an existing directory as an installed
game. It ignores `StateFlags`, `SizeOnDisk`, `InstalledDepots`,
`StagedDepots`, and Steam's authoritative display status.

Black Myth: Wukong proves the failure: `StateFlags=1026`, `SizeOnDisk=0`, no
installed depots, and a 149.8 GB staged depot coexist with an approximately
1.1 MB directory. This state must remain incomplete and downloadable.

### Executable Selection

The native dispatcher can redirect only the target Steam tries to spawn. When
that target is absent or is a macOS `.app`, dispatch never reaches the runtime.
The runtime's action path separately guesses an EXE by scanning up to 5000
files and ranking names.

Hogwarts Legacy has valid `HogwartsLegacy.exe` files but no
`Phoenix-Win64-Test.exe`. Aimlabs has `AimLab_tb.exe` but no `AimLab.app`.
These are wrong launch records, not missing depots. Steam's decoded app launch
configuration must be the authority, with a bounded correction only when its
selected Windows launch entry is absent.

### Container Helpers

Open C Drive runs `/usr/bin/open` with the selected Wine environment. DXMT's
`DYLD_INSERT_LIBRARIES` therefore reaches an arm64e native process, which aborts
while loading the x86_64 shim. Container jobs also mark a nonzero exit as
completed.

Run Command accepts only existing PE paths under the game or prefix. It is not
equivalent to Windows Run and rejects command aliases, control-panel entries,
documents, and selected external installers.

### Tool And Runtime Layout

The current scanner requires project VDF files, an executable `run`, private
JSON metadata, and a package ID. Raw vendor payloads are rejected.

CrossOver demonstrates the desired compositional layout:

- shared base Wine under `lib/wine`;
- graphics payloads under `lib/dxmt`, `lib/dxvk`, and
  `lib64/apple_gptk`;
- mutable bottles that reference the shared engine;
- GPTK payloads with `external/` and matching `wine/x86_64-*` directories.

The current package copies separate full Wine trees for GPTK, DXMT, DXVK, and
WineD3D, increasing package and update size.

### Steam Channel And Updates

The installer hard-codes a public-beta manifest filename and two build IDs.
Both beta manifest files coexist on the live machine, so a filename cannot
identify the active client. The running executable, installed Valve resources,
UUIDs, hashes, and package manifests must be reconciled.

The updater downloads `RealSteamOnMac-Install.pkg`; no distinct update artifact
or installed-over-installed acceptance test exists.

## Architecture

### 1. Native Steam React Integration

Keep the guarded compatibility-page patch that makes Steam instantiate its
existing compatibility component on managed macOS titles. Do not hide or clone
the force-tool row.

Patch data, not markup:

1. `GetAvailableCompatTools(appid)` returns Steam's original tools plus the
   validated project catalog.
2. `SpecifyCompatTool(appid, tool)` persists project selection and mirrors the
   selected record into app details.
3. The existing force checkbox and selector remain owned and rendered by
   Steam.
4. Extra project settings are inserted as React children using component
   constructors already loaded by Steam's compatibility/settings modules.
5. Project code must not create a `<select>`, element with `role="switch"`,
   copied Steam CSS, or a full-window modal layer.
6. Dialogs use Steam's dialog manager and native field/button components.

Component discovery is build-profiled. The patcher records the exact module
factory hashes and export shapes for each supported Steam build. Unknown
module shapes fail closed and leave the original page untouched.

The UI bridge identifies the properties context from React props containing
the same `overview.appid` and `details.unAppID`. Routes and component
identities may be supporting evidence; localized strings are never required.

### 2. Stable Registry Publication

Maintain two browser registry states:

- `lastAuthoritativeRegistry`: the last complete initialized scan accepted by
  the native endpoint;
- `candidateRegistry`: the current scan under construction.

A scan is authoritative only when:

- Steam's app overview collection reports initialized;
- all qualifying overview details resolve;
- the account/library identity matches the previous snapshot;
- no loader call failed;
- the native registry endpoint accepts the update.

An uninitialized or incomplete empty scan retains the previous registry. A real
empty library requires two authoritative empty scans separated by a native
library-change event before removals are published. Startup uses condition
signals and bounded retry rather than a fixed 30-second delay.

### 3. Authoritative Install State

Add a structured app-state parser shared by action and launch planning. It
records:

- manifest AppID and install directory;
- `StateFlags`, `SizeOnDisk`, build ID, update result;
- installed and staged depot counts and sizes;
- Steam detail status and `bHasAnyLocalContent`;
- whether the selected launch target exists and is PE.

An app is launchable only when Steam reports installed/ready, installed depots
are present, recorded size is nonzero, the install directory is nonempty, and
the selected launch target is valid. A staged-only or empty-directory state
remains installable. The bridge must never turn such a state into status 11.

RealSteamOnMac does not edit depot manifests to manufacture success. For stale
states it requests Steam's native repair/download transition and records the
before/after state. Recovery preserves staged files unless Steam itself elects
to replace them.

### 4. Launch Target Resolver

Introduce a launch-descriptor service populated from Steam's decoded app
details/appinfo launch entries. A descriptor contains AppID, launch-entry ID,
OS, executable, working directory, arguments, and optional launcher role.

Resolution order:

1. the exact Windows launch entry Steam selected;
2. another Windows entry explicitly marked as the default game launch;
3. a game-specific recovery rule supported by evidence;
4. fail with a diagnostic listing launch entries and existing executables.

Directory-wide filename heuristics are removed from normal launch. They remain
available only as a read-only diagnostic report.

RDR2 keeps `PlayRDR2.exe` and receives a Rockstar bootstrap state probe. An
interrupted launcher installation is repaired inside the existing prefix by
rerunning the depot-provided prerequisite or clearing only verified partial
installer state. The game depot and user data are never deleted.

### 5. Non-Steam EXE Support

Patch Steam's existing non-Steam shortcut picker filters so `.app` and `.exe`
are both selectable. Do not replace the Add a Game dialog.

- `.app` shortcuts keep Steam's native macOS launch behavior.
- `.exe` shortcuts store the absolute PE path and a project-managed shortcut
  identity.
- the compatibility page is enabled for managed PE shortcuts;
- the prefix lives below a stable shortcut ID, not a fake store AppID;
- the native dispatcher redirects only a validated PE shortcut target.

External EXEs are not required to live under `steamapps`.

### 6. Standard Payload Discovery

Each immediate child of `compatibilitytools.d` is inspected without requiring
project files. Discovery recognizes payload roles by bounded filesystem and
binary evidence.

Supported roots:

- GPTK: `external/D3DMetal.framework`,
  `external/libd3dshared.dylib`, and `wine/x86_64-*`;
- Wine: a valid Wine launcher plus `x86_64-unix` and
  `x86_64-windows` trees;
- DXMT: `winemetal.so` or the equivalent Unix driver and D3D/NVAPI payloads;
- DXVK: DXGI/D3D DLLs plus required Vulkan/MoltenVK payload;
- generated legacy project wrappers, for migration only.

The catalog derives:

- stable tool ID from normalized directory identity plus payload fingerprint;
- display name from safe directory/version metadata;
- renderer/component roles;
- architecture and minimum macOS;
- capabilities from actual files, exports, and version metadata;
- incompatibilities and disabled reasons.

Optional project metadata may override display text but cannot claim a
capability absent from the payload. `run` and VDF files are generated into a
private cache used by the bridge; the user's source directory is not rewritten.

Directory changes are watched and invalidate the Steam API cache so newly
dropped tools appear without reinstalling RealSteamOnMac.

### 7. Compositional Shared Runtime

Publish one versioned base Wine engine and separate versioned component
payloads. A launch plan selects:

- base Wine;
- one graphics backend;
- optional GPTK/D3DMetal files;
- optional Steamworks bridge compatible with that Wine ABI;
- optional MetalFX/DLSS files;
- per-game environment and prefix.

The plan is materialized through a private runtime view made of symlinks or
hardlinks where safe, not duplicated Wine trees. Payload sources are immutable;
prefix mutations are recorded in hash ledgers.

Capability switches are enabled only when the complete selected plan supports
them. DXR, MetalFX/DLSS, MSync, AVX, and HUD options expose an explicit reason
when unavailable.

### 8. Run Command And Container Actions

Run Command supports Windows shell semantics without invoking a host shell:

- executable paths and Windows aliases such as `cmd`, `regedit`, `control`,
  `winecfg`, and `explorer`;
- control-panel applets;
- documents and registered file associations through Wine `start`;
- absolute external PE installers chosen by the native picker;
- arguments parsed into a bounded argv vector;
- optional per-job log capture.

Native macOS operations run with a scrubbed environment containing only a
minimal allowlist. Wine/DYLD variables never reach `/usr/bin/open`,
`osascript`, Finder, or package tools.

Every action treats nonzero process exit as failure unless its fixed recipe
declares that code successful.

Install Application To Container becomes the sole install entry. Its native
Steam dialog offers:

- reviewed dependency recipes;
- Browse for a local installer;
- installed receipts and repair/reinstall actions.

The separate Windows Components section is removed.

### 9. Dependency Recipes

Use an independent, versioned recipe schema informed by CrossOver but sourced
from official publishers. Recipes may contain multiple verified stages:

- download with final-host, size, and SHA-256 checks;
- extract to a private temporary directory;
- run one or more fixed commands;
- accept a bounded exit-code set;
- validate registry/files after installation;
- write a per-prefix receipt.

Initial acceptance covers current VC++ x64/x86, .NET Framework 4.8, DirectX
June 2010, and one common font/runtime recipe with reviewed redistribution or
download terms. Old HTTP and CodeWeavers-only URLs are not imported.

### 10. Steam Stable And Beta Installation

Detect candidate Steam installations from the application bundle and active
runtime, then identify the running build from Valve-owned package metadata and
binary/resource fingerprints. Manifest filenames are diagnostic inputs only.

Each supported build profile contains:

- channel-independent Valve resource hashes;
- arm64 Mach-O UUIDs and source instruction bytes;
- SteamUI chunk/module hashes;
- patch offsets and expected post-patch hashes.

Stable and beta may share a profile when every fingerprint matches. Unknown
builds fail closed with a diagnostic package that can be used to add a profile.

### 11. Update Package

Build three artifacts:

- `RealSteamOnMac-Install.pkg` for clean installation;
- `RealSteamOnMac-Update.pkg` for an existing matching installation;
- `RealSteamOnMac-Uninstall.pkg`.

The update package verifies current install state, Steam build, rollback
snapshot, package signature/hash, and available space. It snapshots all files
it changes, installs side by side, runs post-install tests, atomically switches
active components, and rolls back on failure. It preserves game depots,
prefixes, user-added tools, and per-game configuration.

The signed release manifest has a distinct `updater` artifact and supports
upgrade-path validation from the previous public release.

## Testing Strategy

Every production change follows red-green-refactor.

Automated tests cover:

- native React component integration and absence of replacement HTML controls;
- locale-independent page/action discovery;
- authoritative registry retention across empty startup scans;
- installed, staged-only, empty, validating, and corrupt manifest fixtures;
- exact launch-entry resolution for Hogwarts, Aimlabs, RDR2, and non-Steam
  EXEs;
- raw GPTK/Wine/DXMT/DXVK payload discovery and hot-add;
- capability derivation and impossible-option disabling;
- native helper environment scrubbing and nonzero job failure;
- Windows Run aliases, associations, external installers, and log capture;
- multi-stage dependency recipes;
- stable/beta profile selection;
- clean install, in-place update, rollback, uninstall, and artifact signatures.

Live acceptance records process trees, logs, windows, renderer evidence,
frame-time/FPS samples where available, Steam status, Cloud completion, and
prefix mutations. The initial matrix is:

- older DX10/DX11 titles through DXMT;
- newer DX12 titles through GPTK;
- Hogwarts Legacy, Aimlabs, RDR2, Black Myth: Wukong, People Playground, and
  other already downloaded Windows games;
- one or two DLSS titles with MetalFX conversion;
- CrossOver control runs when a RealSteamOnMac launch fails.

Failure to launch in both products is recorded as a game/environment result,
not proof of RealSteamOnMac correctness. A CrossOver-only success is a
RealSteamOnMac compatibility gap.

## Safety And Rollback

- Never delete a game depot, staged depot, prefix, bottle, or user tool during
  diagnosis.
- Prefix repair begins with a timestamped snapshot and a mutation ledger.
- Real Steam files are replaced only after exact fingerprint validation and
  backup.
- CrossOver is inspected and used for licensed local comparison only; public
  artifacts do not copy proprietary binaries or private recipes without an
  explicit redistribution right.
- LLDB research uses scripted attach, breakpoint/trace, and immediate detach;
  no instruction patching or persistent CrossOver modification is permitted.
- Unknown state fails closed and leaves Steam launch behavior unchanged.

## Documentation And Release Gate

README and interface documentation must describe the implemented behavior, not
the intended design. Screenshots showing project-owned replacement controls are
removed from the product claims.

A release is publishable only after:

- all automated suites pass;
- clean install and `Update.pkg` upgrade pass;
- stable and beta profile selection is proven;
- native Steam UI inspection proves no replacement selector or overlay;
- the game and CrossOver comparison matrix is recorded honestly;
- package signatures/hashes and remote assets are reverified;
- all code/document changes are committed and pushed.
