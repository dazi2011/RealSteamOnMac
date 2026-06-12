# Native Steam compatibility interface discovery

Date: 2026-06-12

## Scope

This note records read-only reverse engineering of the current Valve-signed
macOS Steam client build `1780965181`. The objective is to find the native
compatibility service that owns Steam's real compatibility dropdown and depot
selection without restoring `STEAM_EXTRA_COMPAT_TOOLS_PATHS` at startup or
adding a replacement UI.

No process memory, Steam manifest, game file, prefix, or CrossOver bottle was
modified during these probes.

## Correct `CreateInterface` factory

An earlier `dlsym(RTLD_DEFAULT, "CreateInterface")` probe returned
`0x10456bdd4`. LLDB image lookup proved that address belongs to
`crashhandler.dylib`, not `steamclient.dylib`.

The current images and exact Steam factory were:

| Image | Base / symbol |
|---|---:|
| `steamclient.dylib` | `0x12a8f8000` |
| `steamclient.dylib!CreateInterface` | `0x12babb000` |
| `steamui.dylib` | `0x11cc08000` |
| `libRealSteamNativeEngine.dylib` | `0x1295ac000` |

Calling the exact Steam factory returned non-null interfaces with return code
zero for `SteamClient016` through `SteamClient023`. The current
`SteamClient023` wrapper was `0x12c215ad8`.

Direct factory requests for `IClientCompat`,
`IClientCompat001`, and `CLIENTCOMPAT_INTERFACE_VERSION001` correctly returned
null. These are client-internal services, not top-level factory exports.

## Client engine path

The same exact factory returned:

```text
CreateInterface("CLIENTENGINE_INTERFACE_VERSION005")
  -> 0x12c216278
  return_code = 0
```

Two independent reverse-engineered interface definitions place
`GetIClientCompat` in nearby but version-dependent slots:

- OpenSteamClient/OpenSteamworks commit
  `0044ad3655b0a9f4e27230f9f2a9925a2ca2516c`: slot 72.
- OpenSteamClient/OpenSteamClient commit
  `8d4d18742555959b21453cde0efcd42f336735ee`: slot 75.

The current binary was resolved dynamically rather than trusting either table.
A temporary Steam pipe and global-user connection were created through the
current engine, candidate getters were called, and the returned Itanium RTTI
was inspected:

```text
engine slot 17 -> "14IClientAppsMap"
engine slot 72 -> "16IClientCompatMap"
engine slot 75 -> null
```

The temporary user connection and pipe were then released successfully.
Therefore slot 72 is the verified current `GetIClientCompat` entry.

## Current compatibility map

The current `IClientCompatMap` vtable starts at `0x12c1773e8` and contains 19
method entries. Its first five current method addresses are:

| Slot | Address | Current interface-map meaning |
|---:|---:|---|
| 0 | `0x12b2fbda4` | `BIsCompatLayerEnabled` |
| 1 | `0x12b2fbf18` | `GetAvailableCompatTools` |
| 2 | `0x12b2fc094` | `GetAvailableCompatToolsFiltered` |
| 3 | `0x12b2fc248` | `GetAvailableCompatToolsForApp` |
| 4 | `0x12b2fc3e4` | `SpecifyCompatTool` |

Disassembly shows that these are serialized client-interface stubs. The
object stores interface ID `48`, pipe/session state, and an IPC connection;
the vector-returning methods pass an in-process output pointer through the
request payload.

The method order is cross-checked by the current binary's method-name strings
and the 19-entry vtable boundary. The current interface omits the older
`EnableCompat` entry and includes `SpecifyCompatExperiment`,
`GetCompatExperiment`, and `GetAppCompatCategories`.

## Negative result from the browser API

A breakpoint on the verified map's `GetAvailableCompatTools` stub did not fire
when SharedJSContext called:

```javascript
SteamClient.Apps.GetAvailableCompatTools(1118200)
```

The browser call returned the four project entries only because
`ui/realsteamonmac_ui.js` merges them after calling its saved original method.
This proves the SharedJSContext WebUI bridge does not traverse this local
`IClientCompatMap` client stub in `steam_osx`; it does not prove native tool
registration.

## Consequence

The native client-internal compatibility service is now reachable and
version-resolved without a hard-coded current object address. The remaining
work is narrower:

1. Locate the server-side `CCompatManager` instance or the handler reached by
   interface ID `48`.
2. Identify and validate the post-initialization manifest/cache refresh path,
   including `YldProcessCompatManifests`, `YldRegisterTool`, or
   `RunCacheOffJob`.
3. Register standard user-dropped tool trees after Steam initialization.
4. Re-run the bounded Black Myth install plan and require a non-zero Windows
   depot plan before any download is allowed.

The browser merge remains presentation-only and must not be treated as the
final implementation.
