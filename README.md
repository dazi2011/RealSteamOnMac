# RealSteamOnMac

[简体中文](README.zh-CN.md)

Run eligible Windows-only Steam games from the native macOS Steam library with
per-game GPTK, DXMT, DXVK macOS, or WineD3D selection.

> [!WARNING]
> This is experimental software that patches a specific macOS Steam build.
> Keep the generated rollback backup. Release `0.1.2` supports verified Steam
> builds `1780705203`, `1780965181`, `1781212412`, and `1781911235`.

## Highlights

- Uses native Steam library, downloads, Properties, Play, Steamworks, Workshop,
  and AutoCloud flows.
- Applies to all owned visible Windows-only games discovered at runtime.
- Keeps native and dual-platform macOS games on Steam's original path.
- Discovers side-by-side tools from
  `~/Library/Application Support/Steam/compatibilitytools.d/`.
- Persists the exact compatibility tool and immutable runtime package per game.
- Adds compact Steam-style controls for MSync, Retina mode, Metal HUD,
  MetalFX, DXR, and Rosetta AVX when supported.
- Uses Valve-owned controls in the native Compatibility page for running
  commands, installing dependencies, opening the C: drive, Wine tools,
  process control, and recoverable prefix removal.
- Creates Windows 10 prefixes and uses real `WINEMSYNC=1`.
- Ships reversible install/update/uninstall PKGs and an Ed25519-signed update
  manifest.

## Screenshots

Select independently installed compatibility tools from the normal Steam
Properties page:

![Compatibility tool selector](docs/images/compatibility-tools.png)

Run Command, dependency installation, and container actions expand directly
below Steam's original compatibility selector. No overlay or replacement
settings panel is mounted. For installed games that have never been launched,
these native sections remain visible but stay disabled until Steam has created
`steamapps/compatdata/<appid>/pfx`.

## Requirements

- Apple Silicon Mac.
- macOS 14 Sonoma or later.
- Native macOS Steam with build `1780705203`, `1780965181`, `1781212412`, or
  `1781911235`.
- Internet access and approximately 3 GB of free space.
- Apple Command Line Tools, including `/usr/bin/python3`.

Games requiring kernel anti-cheat, unsupported DRM, or Windows drivers are not
expected to work.

## Install

1. Download `RealSteamOnMac-Install.pkg` and `SHA256SUMS` from
   [Releases](https://github.com/dazi2011/RealSteamOnMac/releases).
2. Verify the package:

   ```bash
   shasum -a 256 -c SHA256SUMS
   ```

3. Optional GPTK support: independently download Apple's official Game Porting
   Toolkit 3.0 image and place it at
   `~/Downloads/Game_Porting_Toolkit_3.0.dmg`.
4. Open the installer package. It stops Steam, creates a clean rollback backup,
   installs the runtime and compatibility tools, then patches the verified
   Steam build.

Without the official GPTK image, installation still provides DXMT 0.80, DXVK
macOS 1.10.3, and WineD3D 11.10. Apple D3DMetal is never redistributed.

The current PKG is not Developer ID signed or notarized because no Developer ID
Installer identity is available. macOS may require **System Settings > Privacy
& Security > Open Anyway**. This limitation is visible in the release notes.

## Use

Open a Windows-only game's **Properties > Compatibility**, enable Steam Play,
then select a tool from the normal Steam dropdown. Settings and actions appear
as compact rows below it. Different games can use different tool versions and
users may install additional validated tool folders side by side.

User-added tools are immediate child directories of
`~/Library/Application Support/Steam/compatibilitytools.d/`. Supported raw
layouts include an Apple/CrossOver-style GPTK tree (`external/` plus `wine/`),
DXMT or DXVK component trees (`x86_64-*` and optional `i386-windows`), and a
complete Wine or CrossOver runtime root (`bin/wine`, `bin/wineserver`, and
`lib/wine`). Put each version in its own directory and restart Steam; no
project `run`, VDF, or JSON file is required. The scanner does not execute or
rewrite raw tools. Embedded payload versions and files determine the displayed
version and whether MSync, Retina, MetalFX, DXR, and Rosetta AVX are enabled.

## Update

The installed updater verifies the release manifest signature, Steam build,
package size, and SHA-256 before opening the distinct transactional
`RealSteamOnMac-Update.pkg`:

```bash
"$HOME/Library/Application Support/RealSteamOnMac/bin/check-for-updates" \
  --current-version "$(<"$HOME/Library/Application Support/RealSteamOnMac/VERSION")" \
  --steam-build 1781911235 \
  --public-key "$HOME/Library/Application Support/RealSteamOnMac/release-public-key.hex" \
  --verifier "$HOME/Library/Application Support/RealSteamOnMac/bin/verify-release-signature" \
  --install
```

Unknown Steam builds fail closed until a compatible release is published.
Update.pkg snapshots the Steam applications and mutable project files,
installs a side-by-side runtime, validates activation, and restores the prior
installation if any update step fails. Game depots, PFX containers, user-added
compatibility tools, and per-game configuration are outside the replacement
set.
When Steam changes between supported builds, uninstall RealSteamOnMac first,
allow Steam to update, then reinstall. This refreshes the clean rollback
snapshot instead of reusing a backup from the previous Steam build.

## Uninstall

Download and open `RealSteamOnMac-Uninstall.pkg`. It stops Steam, restores the
recorded clean snapshot, moves unchanged first-party compatibility tools into
`~/RealSteamOnMac-Rollback`, and preserves installed games and PFX containers.

## Data Locations

| Data | Path |
|---|---|
| Compatibility tools | `~/Library/Application Support/Steam/compatibilitytools.d/` |
| Runtime and settings | `~/Library/Application Support/RealSteamOnMac/` |
| Game prefixes | Steam library `steamapps/compatdata/<appid>/pfx/` |
| Backups | `~/RealSteamOnMac-Backups/` |
| Rollback material | `~/RealSteamOnMac-Rollback/` |
| Logs | `~/Library/Logs/RealSteamOnMac/` |

## Known Issues

- Steam updates can change binary or UI hashes; unsupported builds are rejected.
- Moving between supported Steam builds requires an uninstall/update/reinstall
  cycle so rollback data always matches the installed Steam runtime.
- Compatibility varies by game and renderer.
- The first installation downloads and expands a large Wine runtime.
- GPTK support requires the user's separately obtained official Apple image.
- The current public PKG is unsigned and not notarized.

## Development

```bash
node --test tests/*.mjs
/usr/bin/python3 -m unittest discover -s tests -p 'test_*.py'
for test_file in tests/test_*.sh; do sh "$test_file"; done
script/build_release_pkgs.sh
```

Architecture and recovery contracts are documented in
[docs/interfaces.md](docs/interfaces.md). Engineering history is in
[docs/project-history.md](docs/project-history.md).

## Acknowledgements

Thanks to the Wine, Wine Staging, DXMT, DXVK, Proton, and Gcenx macOS Wine
contributors. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for exact
versions, source links, and licenses.

RealSteamOnMac is independent software. It is not affiliated with, endorsed by,
or supported by Valve, Steam, Apple, CodeWeavers, or Microsoft.
