# Third-Party Notices

RealSteamOnMac's own source is licensed under the MIT License. Runtime packages
download, build, patch, or interoperate with separate third-party projects.
Their licenses remain controlling.

Verbatim license files for the shipped open-source and Steamworks-derived
components are included in `third_party/licenses/`.

## Wine and Wine Staging

- Wine 11.10 source: https://github.com/wine-mirror/wine/tree/wine-11.10
- Wine Staging 11.10 source:
  https://github.com/wine-staging/wine-staging/tree/v11.10
- Binary distribution source:
  https://github.com/Gcenx/macOS_Wine_builds
- License: GNU LGPL 2.1 or later.
- Project patch:
  `patches/wine-11.10-dxmt-macdrv-compat.patch`

The exact corresponding source tags and the project patch are public and may
be used to rebuild the modified Wine components.

## DXMT

- Source and release: https://github.com/3Shain/dxmt/tree/v0.80
- Version: 0.80
- License for this release: MIT.

DXMT changed its main development branch to LGPL after v0.80. This project
currently installs the separately released v0.80 binary.

## DXVK macOS

- Source: https://github.com/Gcenx/DXVK-macOS
- Tag: `v1.10.3-20230507-repack`
- License: zlib.

## Proton lsteamclient

- Source commit:
  https://github.com/ValveSoftware/Proton/tree/25880e88befb52c5aa7ff162c5b00b6b8825e494
- Wine source commit:
  https://github.com/ValveSoftware/wine/tree/2f70bfd4d0f4e67a8a599c4a09760579bc2a4fa4
- Project patch: `patches/proton-lsteamclient-macos.patch`
- Proton top-level license: BSD 3-Clause.
- The `lsteamclient` directory also includes Valve's Steamworks SDK license.

Redistribution and use must comply with all terms in Proton's `LICENSE`,
`LICENSE.proton`, and `lsteamclient/LICENSE`.

## Apple Game Porting Toolkit

Apple Game Porting Toolkit and D3DMetal are not distributed by this repository
or its public PKG. If the user independently downloads Apple's official GPTK
3.0 image and places it at
`~/Downloads/Game_Porting_Toolkit_3.0.dmg`, the installer can import required
files locally. Apple's license and acknowledgements are copied into that local
runtime package.

Official page:
https://developer.apple.com/games/game-porting-toolkit/

## Microsoft Runtime Installers

The optional dependency catalog downloads installers directly from Microsoft,
validates exact byte sizes and SHA-256 digests, and executes them only inside
the selected Wine prefix. Microsoft retains all rights in those installers.

## CrossOver

CrossOver was inspected as a UX and dependency-workflow reference. No
CodeWeavers or CrossOver runtime binary, recipe database, or proprietary
component is included.

## Valve and Steam

Steam, Steamworks, and related names and marks belong to Valve Corporation.
RealSteamOnMac is an independent project and is not affiliated with, endorsed
by, or supported by Valve.
