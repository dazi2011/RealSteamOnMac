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

## Live `CCompatManager` instance and platform gate

The refreshed arm64 `steamclient.dylib` slice has SHA-256
`643241ec454ce3d69ef630c54d1d1b24c57ccbac35d463253d03949187e0ce17`.
Its current live slide is `0x127c24000`.

Static string cross-references identify these current arm64 offsets:

| Function / path | Image-relative offset |
|---|---:|
| `CCompatManager::InternalSpecifyCompatTool` | `0x728eb0` |
| `CCompatManager::RunCacheOffJob` | `0x730dbc` |
| `CCompatManager::YldRegisterTool` | `0x72e960` |
| local-tool worker setup | `0x73326c` |
| all-list processing from the cache job | `0x733e64` |

A reversible People Playground mapping refresh was performed after backing up
and hashing `config.vdf`. A breakpoint at `InternalSpecifyCompatTool` fired on
the engine IPC thread with:

```text
x0 = 0x0000000baf2b28a0  CCompatManager this
x1 = 0x0000000000110ff8  AppID 1118200
x2 = "realsteamonmac-dxmt"
x3 = ""
x4 = 0x00000000000000fa  priority 250
```

The mapping was restored to DXMT, the deployed registry remained healthy, and
CrossOver Preview was never attached or stopped.

The constructor explains why mapping persistence and native availability have
diverged. Near `0x725a84`, Steam obtains the current platform string, compares
it case-insensitively with the literal `linux`, and writes the equality result
to `CCompatManager + 0x798`:

```text
0x725a84  load "linux"
0x725a90  call V_strnicmp
0x725a98  cset w8, eq
0x725a9c  strb w8, [x19, #0x798]
```

The live macOS object contains zero at both `+0x798` and the post-logon flag
`+0x799`. Every important native method, including
`BIsCompatibilityToolEnabled`, `OnPostLogonState`,
`OnAppConfigInitialized`, and `RunCacheOffJob`, checks `+0x798` and returns
early when it is zero. `RunCacheOffJob` additionally requires `+0x799`.

This is the first direct root-cause proof that macOS native tool registration
is blocked before manifest parsing. The next experiment must enable only this
manager instance after normal macOS login, launch its normal cache-off job,
and verify that Steam Cloud remains intact. Globally impersonating Linux at
startup remains rejected.

## Safe post-login bridge shape

The first instruction of the current arm64
`CCompatManager::InternalSpecifyCompatTool` is exactly:

```text
offset 0x728eb0
bytes  ff 43 02 d1
word   0xd10243ff
asm    sub sp, sp, #0x90
```

This gives the native engine a fail-closed, UUID-gated interception point. A
near trampoline can preserve the five method arguments, call a one-shot
project helper on the same `IPC:CSteamEngine` thread, reproduce the displaced
stack instruction, and branch to `0x728eb4`. Calling Steam's internal Job API
from the existing background reconciliation pthread is rejected because the
local-tool path assumes Steam's Job/thread context.

`LaunchLogOnCompatProcessingJob` at `0x731e50` is the normal entry point. It
sets `CCompatManager + 0x799` to one, verifies app-state readiness, and
tail-branches to `RunCacheOffJob` with the reason string
`LaunchLogOnCompatProcessingJob`. The local-tool job then invokes
`CLoadLocalToolListJob::ThreadedListLocalToolManifests` and iterates its
Steam-owned path vector, logging `Processing local tool list at %s...` before
registering manifests. The bridge therefore needs to set only the existing
platform-enabled byte at `+0x798` and invoke this normal entry point once.

The earlier backtrace address `0x7356b8` is not a reliable call-return site.
Bounded static disassembly shows it is eight bytes into an internal callback
object constructor. It must not be used as a post-call hook.

## Live late-enable result

A reversible LLDB experiment on native Steam PID `8939` hit
`InternalSpecifyCompatTool` on `IPC:CSteamEngine` for People Playground and
verified the expected entry word, manager pointer, AppID, tool name, and
priority. The experiment then:

1. changed only manager byte `+0x798` from zero to one;
2. invoked the current build's `LaunchLogOnCompatProcessingJob` at runtime
   address `0x128355e50`;
3. observed manager byte `+0x799` change from zero to one;
4. resumed Steam and allowed the normal cache job to finish.

`compat_log.txt` proves the call path was valid:

```text
CCacheOffSteamPlayStateJob: start job, reason: LaunchLogOnCompatProcessingJob
CCacheOffSteamPlayStateJob ... processing all compat lists..
CCacheOffSteamPlayStateJob ... complete
```

The Cloud schema, values, and `CloudStorage.WriteKey` API were unchanged after
the job. `loginusers.vdf` was byte-identical. The expected mapping write
changed `config.vdf`, and People Playground was restored to
`realsteamonmac-dxmt` before detaching LLDB.

However, the job processed only Steam's built-in AppID `891390` tool list. It
did not log any path below the standard user `compatibilitytools.d`
directory. Every built-in Proton/Linux tool was rejected as targeting
`linux`, and the project tools remained unregistered. The resulting native
details temporarily reported no valid selected tool, causing the JavaScript
dynamic registry to remove AppID `1118200`.

Subsequent bounded disassembly corrected the initial explanation for this
result. `CLoadLocalToolListJob` itself, beginning at `0x732df4`, always builds
its root vector. It inserts:

```text
/usr/share/steam/compatibilitytools.d
/usr/local/share/steam/compatibilitytools.d
STEAM_EXTRA_COMPAT_TOOLS_PATHS entries, when present
<Steam user-data base>/compatibilitytools.d
```

The user path is assembled around `0x733050..0x733174` by calling Steam's
existing base-path provider at `0xac4528`, appending
`/compatibilitytools.d`, and inserting the resulting `CUtlString` into the
Job-owned vector. The macOS manager constructor therefore did not omit the
path vector. The remaining fault lies after or inside that path construction:
the base path may differ from the expected Application Support root, or
`ThreadedListLocalToolManifests` may reject the deployed child layout.

A fresh native Steam process refined that conclusion again. Before the first
late-enable transition, LLDB breakpoints were installed at the user-path
insertion (`0x733174`) and after the threaded enumerator returned
(`0x73328c`). The normal one-shot `IPC:CSteamEngine` transition completed and
`CCacheOffSteamPlayStateJob` logged its start, all-list processing, and
completion, but neither local-tool breakpoint fired. Thus the path builder is
not receiving a wrong base path: `CLoadLocalToolListJob` is not scheduled at
all on this macOS execution path.

`RunCacheOffJob` at `0x730dbc` only validates manager state and allocates the
`CCacheOffSteamPlayStateJob`. The next target is the cache job's condition
that decides whether to instantiate `CLoadLocalToolListJob`; that condition
must be corrected before any path or manifest-format work can be evaluated.

A second LLDB attempt tried to invoke `LaunchLogOnCompatProcessingJob` again
from the stopped main thread solely to inspect that path. This is invalid:
the already-completed manager had no active Steam Job callback context, and
the queued callback dereferenced a null function pointer. Steam aborted after
the debugger skipped the original access violation. The direct release path
must remain one-shot and run only from the first normal
`IPC:CSteamEngine` mapping transition. Future path inspection must set
breakpoints before that first transition rather than manually re-running the
post-login Job.

## Startup-only local-loader correction

The prior conclusion that `CCacheOffSteamPlayStateJob` conditionally creates
`CLoadLocalToolListJob` was wrong. Mach-O chained fixups identify the
`CLoadLocalToolListJob` typeinfo and vtable:

```text
typeinfo name       0x155b0ad
typeinfo object     0x184ceb8
vtable address      0x184ce20
job run method      0x732df4
```

Code references to that vtable lead back to `CCompatManager` construction:

```text
0x725cc4  mov   w0, #0x248
0x725cc8  bl    operator new
0x725cd4  bl    base job constructor
0x725cd8  adrp/add CLoadLocalToolListJob vtable
0x725ce0  str   vtable, [job]
0x725d04  bl    queue job
```

The local-loader job is therefore startup-only. The late cache experiment
could never reach its path builder, regardless of the cache job's platform
state.

Immediately before creating the job, the same manager constructor computes
its Linux capability:

```text
0x725a84  load "linux"
0x725a90  call V_strnicmp
0x725a94  cmp  w0, #0
0x725a98  cset w8, eq       ; 0x1a9f17e8
0x725a9c  strb w8, [x19, #0x798]
```

## Rejected constructor-wide enable experiment

For current arm64 beta UUID
`4678FB72-BAE9-3D1B-8313-D9A5667EA814`, a guarded experiment changed only
`0x725a98` from `cset w8, eq` to `mov w8, #1`. The patch applied before
`steamclient` initializers exactly as designed, but Steam then reproducibly
reported:

```text
Assertion Failed: CSteamEngine::BMainLoop appears to have stalled > 15 seconds
```

No project local-manifest registration completed. The installed guard and
engine were restored from the pre-experiment backup, and the early-patch
source was removed. Manager byte `+0x798` is therefore a broad Linux
capability switch, not a release-safe local-loader switch.

A second startup used the unmodified Steam binary and supplied the valid
four-tool directory through `STEAM_EXTRA_COMPAT_TOOLS_PATHS`. It reproduced
the same main-loop stall. Historical empty-directory starts remained healthy.
This moves the root cause downstream: the macOS startup path fails when local
enumeration produces at least one valid manifest.

A read-only all-thread LLDB trace captured the main thread waiting in Steam's
startup event chain while `IPC:CSteamEngine` slept in its normal loop. One
transient thread had `PC=0`; this is consistent with an uninitialized macOS
completion callback but is not yet sufficient proof. Investigation continues
through the local-tool job completion/dispatch chain. No further global
manager enable patch is permitted without a narrower proven call boundary.
