# CrossOver Dependency Metadata Review

Date: 2026-06-10

## Scope

CrossOver Preview was inspected only as a behavior and layout reference. No
CrossOver Wine build, proprietary runtime, bottle template, installer payload,
or private recipe database is copied into this project.

The readable recipe database is located at:

```text
/Applications/CrossOver Preview.app/Contents/SharedSupport/CrossOver/share/crossover/data/crossover.tie
```

It contains localized names, dependency graphs, download locations, installer
arguments, and historical compatibility rules. The thin Python setup bridge is
not the source of those recipes.

## Decision

The CrossOver recipe set is not imported. Many entries use historical HTTP
links, archive mirrors, CodeWeavers infrastructure, or terms that require
case-by-case review. Importing it wholesale would weaken the existing
checksum-pinned supply-chain boundary.

RealSteamOnMac keeps a small independent catalog in
`config/dependencies.json`. Every entry must have:

- an official publisher URL;
- an exact byte size;
- an exact SHA-256 digest;
- fixed silent-install arguments;
- a bounded success-code list.

## Reviewed Entries

On 2026-06-10, Microsoft's current official Visual C++ v14 links were resolved
and pinned to immutable `download.visualstudio.microsoft.com` URLs:

- x64: 18,731,856 bytes, SHA-256
  `843068991daaa1f73ad9f6239bce4d0f6a07a51f18c37ea2a867e9beca71295c`;
- x86: 6,941,536 bytes, SHA-256
  `f0bab33a302b3cdb2e11113760d016f54fd3d2632c65ba7834fac4f0abd7f1a3`.

.NET Framework 4.8 remains pinned to its previously verified Microsoft offline
installer.

The DirectX June 2010 redistributable was reviewed but not added. Its outer
executable extracts another installer, while the current dependency contract
executes one checksum-pinned program. Adding it safely requires a separate
multi-stage recipe schema and tests rather than pretending extraction alone is
installation.

Chinese fonts were also not imported from CrossOver. A public release needs a
legally reviewed source and explicit font licensing before offering automated
installation.

## Sources

- Microsoft Visual C++ current redistributables:
  https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist
- Microsoft DirectX June 2010 runtime:
  https://www.microsoft.com/en-us/download/details.aspx?id=8109
