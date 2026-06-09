# Run Command And Dependency Workflow

Date: 2026-06-09

## Status

The fixed action protocol, runtime implementation, Steam properties UI, and
one-click installation assets are complete in the repository. The complete
pre-deployment matrix passes:

- 59 Node tests;
- 38 Python tests;
- all 22 shell contracts.

Live installation into the user's current Steam client is the next acceptance
gate. This document deliberately does not claim a successful live command or
dependency installation yet.

## Protocol

The delayed native engine extends its existing authenticated loopback service
with two endpoints:

```text
POST /action?token=<private-token>&appid=<managed-appid>
GET  /job?token=<private-token>&appid=<managed-appid>&job=<32-hex-id>
```

Only two URL-encoded action schemas are accepted:

```text
action=run-command&target=...&arguments=...&environment=...
action=install-dependency&dependency=...
```

The C service verifies the private token and live managed-AppID registry,
creates a random 128-bit job ID, and starts the Python runtime with
`posix_spawn`. It never invokes a shell. The browser polls a private JSON status
file until the job reaches `completed` or `failed`.

Job state is stored under:

```text
~/Library/Application Support/RealSteamOnMac/jobs/<appid>/
```

Directories use mode `0700`; status and log files use mode `0600`.

## Run Command Boundary

The runtime resolves the AppID from Steam app manifests and preserves the full
game installation root even when the selected default executable is nested.
Targets may be:

- relative paths under the game installation;
- `install:<relative-path>`;
- `prefix:<relative-path>`;
- Wine `C:\...` paths under the game's PFX.

The resolved target must remain below the game installation or
`steamapps/compatdata/<appid>/pfx`, must exist, and must begin with the PE `MZ`
signature. Arguments are parsed into an argv vector with no shell expansion.

User environment variables are limited to 32 entries. Steam, Wine, project,
and DYLD control variables are reserved and cannot be replaced. Each AppID has
one private `action.lock`, preventing two UI jobs from mutating the same PFX at
the same time.

## Dependency Boundary

The versioned catalog is:

```text
config/dependencies.json
```

Both installers copy it atomically to:

```text
~/Library/Application Support/RealSteamOnMac/dependencies/catalog.json
```

The initial catalog contains:

1. Microsoft Visual C++ 2015-2022 x64 redistributable.
2. Microsoft .NET Framework 4.8 offline installer.

The runtime does not accept a user-provided URL or installer path. Catalog
entries require an allowlisted Microsoft HTTPS host, a fixed filename, exact
byte size, lowercase SHA-256, fixed arguments, and fixed accepted exit codes.
Redirect destinations are checked again before bytes are read. Downloads are
stored in a private cache only after exact size and hash verification.

Successful installations write a receipt below:

```text
steamapps/compatdata/<appid>/realsteamonmac/dependencies/
```

The receipt records dependency ID, package ID, renderer, digest, timestamp, and
exit code.

Official source references:

- Microsoft Visual C++ redistributable:
  https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist
- Microsoft .NET Framework 4.8:
  https://dotnet.microsoft.com/en-us/download/dotnet-framework/net48

## Steam UI

The compatibility panel retains the existing Steam-native dark industrial
style and adds:

- target, argument, and environment fields for `运行命令`;
- an explicit `NO SHELL` boundary label;
- dependency search by package name, description, or publisher;
- per-package install buttons;
- running/completed/failed state and the private log path.

The UI receives only public catalog fields. Download URLs, hashes, arguments,
and accepted exit codes remain in the private installed catalog consumed by
the Python runtime.

## Rollback

Before live deployment, preserve the current support directory, launcher,
Steam runtime executable, Info.plist, UI resources, runtime entrypoint, and
dependency catalog. The existing clean Steam backup remains the authoritative
full rollback source:

```text
/Users/wudazi/RealSteamOnMac-Backups/
  steam-1780705203-20260607T083704Z
```

For a failed dependency acceptance, restore the tested PFX snapshot rather than
deleting or manually editing registry state without evidence.

## Next Acceptance

1. Quit Steam normally and create a pre-Phase-5B rollback snapshot.
2. Install the rebuilt native engine, launcher, UI, runtime entrypoint, and
   catalog.
3. Restart Steam with CEF debugging enabled.
4. Confirm the People Playground properties panel shows both new sections.
5. Run a harmless PFX `reg.exe query` command and verify the completed job,
   private log, and no shell interpretation.
6. Install Visual C++ 2015-2022 x64, verify the exact downloaded digest,
   completed receipt, and PFX registry/files.
7. Recheck dynamic Windows-only availability, native macOS exclusions, Cloud,
   all four renderer selections, and a real game launch/exit.
