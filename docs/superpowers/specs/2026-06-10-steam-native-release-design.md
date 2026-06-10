# Steam-Native Compatibility And Release Design

Date: 2026-06-10

## Objective

Make the macOS Steam client present Windows compatibility as if Steam Play
were natively supported on macOS:

- compatibility tools live under
  `~/Library/Application Support/Steam/compatibilitytools.d`;
- multiple GPTK, DXMT, DXVK, and WineD3D versions can coexist and be selected
  per game from Steam's existing compatibility dropdown;
- per-game controls look and behave like Steam settings instead of a branded
  project dashboard;
- run-command, dependency, and container actions open bounded secondary
  dialogs;
- every owned visible Windows-only game uses the same eligibility and launch
  path;
- installation, removal, and updates are shipped as signed-installable PKG
  workflows with bilingual release documentation.

## Evidence And Constraints

The current Steam Public Beta build is `1780705203`. Existing A/B evidence
shows that setting `STEAM_EXTRA_COMPAT_TOOLS_PATHS` to a valid tool directory
removes Cloud fields from Steam's settings bridge. Therefore the standard tool
directory will be the canonical repository, but startup-time native discovery
will remain disabled. A project scanner will validate the directory and feed
the resulting tools into Steam's existing compatibility API.

The large panel shown in the supplied screenshots is not a native Steam
properties page. `ui/realsteamonmac_ui.js` scans all Steam documents for text
containing `RealSteamOnMac`, then inserts a large custom section after the
matched element. A weak anchor can belong to the library details page, which
explains the persistent right-side panel. The fix is to require positive
properties-dialog and compatibility-page evidence before mounting any control.

CrossOver is useful as a behavioral and layout reference, but its proprietary
runtime binaries and recipes will not be copied into the public release.
Open-source or redistributable metadata may be studied; third-party payloads
must retain their own licenses and download terms.

## Approaches Considered

### 1. Enable Steam's native compatibility-tool discovery

This would be closest to Linux Steam Play, but it is rejected for the current
Steam build because live evidence shows a Cloud regression.

### 2. Keep four hard-coded project tools

This is the smallest change, but it cannot support side-by-side versions or
user-installed tools and keeps project branding in the normal Steam workflow.

### 3. Validate the standard directory and bridge it into Steam

This is the selected design. A scanner reads supported tool packages from
`compatibilitytools.d`, validates their VDF and project metadata, and writes a
bounded catalog into SteamUI configuration. Steam's original compatibility
checkbox and dropdown remain the selection surface. This preserves Cloud,
supports side-by-side versions, and keeps filesystem/runtime decisions outside
the browser UI.

## Tool Package Contract

Each supported directory contains:

```text
compatibilitytools.d/<tool-id>/
  compatibilitytool.vdf
  toolmanifest.vdf
  run
  realsteamonmac.json
```

`realsteamonmac.json` uses schema 1 and contains:

- `tool`: the VDF tool identifier;
- `display_name`: the user-visible name;
- `renderer`: `gptk`, `dxmt`, `dxvk`, or `wined3d`;
- `version`: a bounded display version;
- `runtime_package`: an immutable package ID below the project runtime root;
- `capabilities`: booleans for `msync`, `retina`, `metal_hud`, `metalfx`,
  `dxr`, and `avx`.

The scanner rejects duplicate identifiers, symlink escapes, missing executable
entrypoints, unsupported renderers, unbounded strings, mismatched VDF names,
and runtime package paths outside the immutable package root.

Selection persists both `compat_tool` and `renderer` in the per-AppID config.
The runtime resolves the immutable package selected by tool metadata instead of
assuming the global `current` package. Existing seven-field configs migrate to
the current default tool.

## Steam UI

The compatibility page retains Steam's native force-compatibility checkbox and
dropdown. Project code adds only a compact vertical settings group beneath the
dropdown:

- MSync
- High resolution
- Metal HUD
- DLSS to MetalFX
- Rosetta AVX
- DXR where supported
- Open C: drive
- Run command
- Install application
- Install Windows component
- Wine configuration
- Controllers
- Simulate restart
- Task manager
- Quit all applications
- Delete container

Boolean settings use Steam-style toggle rows, not checkboxes in a branded
card. Destructive actions use explicit warning styling and confirmation.
Unsupported capabilities are disabled with a short version/capability reason.

The mount guard requires all of:

- a Steam properties popup document;
- a compatibility-page route or localized compatibility heading;
- exactly one compatibility combobox;
- one unambiguous managed AppID from the popup's React tree.

Any failed condition removes project-owned controls from that document. The
library details page can never satisfy the guard.

## Secondary Dialogs

Run Command opens a Steam-styled modal with target, Browse, arguments,
environment variables, log creation, log channel, and Run. Browse is delegated
to a native macOS file picker through a bounded native action.

Install Windows Component opens a searchable catalog modal. The existing
fixed-size and SHA-256 checks remain mandatory. The first public release uses a
small reviewed catalog; CrossOver metadata is research evidence, not an
unreviewed download source.

Container actions are mapped to native macOS operations:

- Open C: drive uses Finder;
- Install application uses NSOpenPanel-compatible file selection;
- Wine configuration, controller tools, restart, task manager, and quit-all
  run through the selected per-game PFX;
- Delete container requires confirmation and moves the PFX to a timestamped
  recovery location instead of immediately erasing it.

## Runtime Semantics

New prefixes are Windows 10 by default. MSync uses `WINEMSYNC=1`; the separate
`WINEESYNC=1` compatibility hint remains only where D3DMetal requires it and is
not presented as FSync.

MetalFX is capability-driven rather than renderer-name-only. A DXMT tool may
enable it only when its metadata declares support and a runtime probe confirms
the required files/exports. Older DXMT packages remain selectable but expose a
disabled MetalFX row with the detected version.

All owned visible Windows-only games continue to use the dynamic registry.
Native and dual-platform macOS games remain excluded.

## Packaging, Updates, And Removal

The release produces:

- `RealSteamOnMac-Install.pkg`
- `RealSteamOnMac-Uninstall.pkg`

The installer stops Steam gracefully, creates a rollback snapshot, installs
runtime/support files, installs first-party tool packages into the standard
directory, patches the known Steam build, verifies signatures and hashes, then
relaunches Steam only after success.

The uninstaller stops Steam, restores the clean Steam backup, removes only
project-owned tool/support files, preserves game depots and PFX directories by
default, and writes a removal report.

Updates use a signed release manifest containing version, Steam build
compatibility, artifact SHA-256, and download URL. The installed updater checks
explicitly or at a bounded interval, downloads to a private cache, verifies the
manifest and package, and invokes the same transactional installer. Unknown
Steam builds fail closed.

## Documentation And Publication

`README.md` becomes a bilingual product document covering purpose, features,
requirements, installation, uninstallation, updates, compatibility tools,
known issues, screenshots, acknowledgements, licenses, and the statement that
the project is unaffiliated with Valve or Steam.

Historical progress moves to `docs/project-history.md`. Technical handoff and
interface documents remain under `docs/`. The repository is made public only
after secret/license scanning, clean installation and removal tests, live Steam
acceptance, and release artifact checksum verification.

## Verification

Automated verification covers scanner validation, config migration,
capability/version rules, strict mount guards, dialog action payloads, runtime
package selection, Windows 10 prefix creation, installer/uninstaller
transactions, updater manifest validation, and documentation links.

Live verification covers:

- no panel on any library details page;
- no compatibility-page flash-to-dashboard replacement;
- scrolling and toggles in properties;
- side-by-side tool selection and persistence;
- one installed and one uninstalled Windows-only title;
- native/dual-platform exclusion;
- run-command and dependency dialogs;
- install PKG, update path, uninstall PKG, and rollback;
- Cloud settings and AutoCloud after installation.

