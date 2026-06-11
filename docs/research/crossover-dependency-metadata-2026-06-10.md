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

On 2026-06-10 and 2026-06-11, official Microsoft and NVIDIA downloads were
resolved, downloaded, measured, hashed, and represented as bounded recipes.
The production catalog now contains:

- current Visual C++ v14 x86 and x64;
- side-by-side Visual C++ 2013, 2012, 2010, and 2008 x86 and x64;
- .NET Framework 4.8;
- DirectX End-User Runtimes (June 2010);
- Microsoft XNA Framework 4.0 Refresh;
- NVIDIA PhysX Legacy 9.12.1031.

Every download has an exact byte count and SHA-256 digest in
`config/dependencies.json`. x64 Visual C++ recipes install their matching x86
runtime first, and XNA installs .NET Framework 4.8 first.

The DirectX outer executable is handled by a dedicated fixed strategy. It
extracts into a private temporary directory, requires `DXSETUP.exe`, runs that
one installer, and removes the extraction tree. Success is proven by exact
SHA-256 hashes for the native x86 and x64 `d3dx9_43.dll` files, not by file
existence. This matters because a fresh Wine prefix already contains builtin
DLLs with the same names.

Visual C++, .NET, XNA, and PhysX use product-specific registry keys queried by
Wine after installation. Receipts are written only after every required
postcondition passes. The catalog rejects unknown installer strategies,
untrusted download hosts, cyclic prerequisites, unsafe prefix paths, malformed
registry keys, and unpinned file hashes.

Live VC++ 2013 acceptance showed that its 32-bit Burn bootstrapper records both
x86 and x64 bundle uninstall keys below Wine's `Wow6432Node` view. The 2012
and 2013 x64 recipes therefore query that actual Wine registry location rather
than assuming the native Windows x64 uninstall view.

The .NET Framework 4.8 recipe uses Microsoft's final
`download.microsoft.com` URL rather than the `go.microsoft.com` redirector.
The final payload was independently re-downloaded and matched the existing
121,346,568-byte size and SHA-256 pin exactly. This avoids redirect-time TLS
chain differences. Downloads use macOS's fixed `/usr/bin/curl` with
SecureTransport, HTTPS-only protocols, bounded redirects, and a maximum file
size. The runtime still validates the final host, exact size, and SHA-256
before publishing the private cache file.

Chinese fonts were also not imported from CrossOver. A public release needs a
legally reviewed source and explicit font licensing before offering automated
installation.

## Sources

- Microsoft Visual C++ current redistributables:
  https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist
- Microsoft Visual C++ 2013 and older downloads:
  https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist#visual-studio-2013-vc-120
- Microsoft DirectX June 2010 runtime:
  https://www.microsoft.com/en-us/download/details.aspx?id=8109
- Microsoft Windows Installer command-line options:
  https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/msiexec
- NVIDIA PhysX Legacy System Software:
  https://www.nvidia.com/en-us/drivers/physx/physx-9-12-1031-legacy-driver/
