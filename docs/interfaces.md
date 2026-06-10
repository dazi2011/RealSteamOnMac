# Public Interfaces

## Compatibility Tool Package

Supported tools live below:

```text
~/Library/Application Support/Steam/compatibilitytools.d/<tool-id>/
```

Each directory contains `compatibilitytool.vdf`, `toolmanifest.vdf`, executable
`run`, and `realsteamonmac.json`. Schema 1 metadata declares the exact tool ID,
display name, renderer, version, immutable runtime package, and capability
booleans. `runtime/compat_tool_catalog.py` is the canonical validator.

User-created tool directories are preserved. Install and uninstall replace or
move only the first-party directory names recorded in `install-state.json`.

## Per-Game Configuration

Private AppID configuration is stored at:

```text
~/Library/Application Support/RealSteamOnMac/apps/<appid>.json
```

The authenticated loopback service accepts fixed renderer, tool, and boolean
fields. Arbitrary command execution is not part of this configuration API.

## Background Jobs

Run-command, dependency, file-picker, and container operations use authenticated
jobs below:

```text
~/Library/Application Support/RealSteamOnMac/jobs/<appid>/
```

Targets are restricted to the selected game directory or its PFX unless an
explicit native file picker operation is used. Dependency downloads require an
entry in the checksum-pinned catalog.

## Installation State

`install-state.json` records:

- project version and verified Steam build;
- clean backup, Steam app, runtime, support, and tool roots;
- active immutable runtime package;
- managed compatibility-tool names and metadata hashes.

The uninstaller refuses unsafe state paths, restores the clean snapshot first,
then moves only unchanged managed tool directories into the rollback area.
Game depots and `steamapps/compatdata` prefixes remain in place.

## Release Manifest

`release-manifest.json` schema 1 includes the semantic version, repository,
supported Steam builds, platform requirements, package names, sizes, hashes,
and HTTPS release URLs. The detached signature is Ed25519 and is verified with
`config/release-public-key.hex`.

Unknown fields, unknown Steam builds, cross-repository URLs, incorrect sizes,
and incorrect SHA-256 digests fail closed.

## Recovery

Automatic backups are created below `~/RealSteamOnMac-Backups`. Replaced files
and removed tool directories are retained below
`~/RealSteamOnMac-Rollback`. Prefix removal from Steam's compatibility page is
also recoverable because the PFX is moved into the AppID recovery directory.
