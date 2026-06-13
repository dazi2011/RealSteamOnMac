# Steam public beta 1781212412 validation

Date: 2026-06-13

## Scope

This note records the read-only validation evidence collected for Steam public
beta build `1781212412`. It covers the binary identities and profile offsets
needed to support the build, SteamUI resource reuse, the local compatibility
tool loader layout, the observed fail-closed behavior with the previous
profile, and the remaining dynamic acceptance work.

The analysis did not modify or launch Steam, attach LLDB, access CrossOver, or
change any game, depot, prefix, bottle, or Steam configuration.

## Build identity

The installed public-beta package manifest reports version `1781212412`.

| Image | Architecture | UUID |
|---|---|---|
| `steamclient.dylib` | x86_64 | `5931251B-5C27-3C45-9453-75CE6EFBD2DF` |
| `steamclient.dylib` | arm64 | `BAF0A603-23F9-3F14-A019-73825732E82F` |
| `steamui.dylib` | x86_64 | `92A89004-2E35-3E3A-AA3E-62FF9A4C2127` |
| `steamui.dylib` | arm64 | `68D2AAA9-2289-34EA-ACFC-94C4F1221EE5` |

| Image | Scope | SHA-256 |
|---|---|---|
| `steamclient.dylib` | universal file | `234a51d3ed72fadffc88b5dd3d176b372475fc0eb49442d3936802180c574cb6` |
| `steamclient.dylib` | arm64 slice | `fc91f889e8f775c61ef90de23e479df0bbd203051c4126c6776e7a8ff6b53e4b` |
| `steamui.dylib` | universal file | `1807e0f607c2f43e2b361b2ec2001ba925ede6a1b6408002d21a2e244765a89c` |

These identities must be matched exactly. Profiles for earlier builds are not
valid for this build even where nearby code remains structurally similar.

## arm64 profile offsets

All offsets in this section are arm64 image-relative offsets. A runtime
address is the image load address plus the listed offset.

| Target | Offset | Expected instruction or binding |
|---|---:|---|
| compatibility gate | `0x00A03EF8` | `0xD101C3FF` (`sub sp, sp, #0x70`) |
| compatibility gate next word | `0x00A03EFC` | `0xA9054FF4` (`stp x20, x19, [sp, #0x50]`) |
| install gate | `0x006279D8` | `0x37200188` (`tbnz w8, #4, 0x627A08`) |
| install fallthrough | `0x006279DC` | `0x371002E8` (`tbnz w8, #2, 0x627A38`) |
| install invalid target | `0x00627A08` | `0x94371DE1` (`bl 0x13EF18C`) |
| error-29 marker | `0x00627A24` | `0x528003A8` (`mov w8, #0x1d`) |
| SteamUI platform-flags getter | `0x005EDF44` | `0xB9401C00` (`ldr w0, [x0, #0x1c]`) |
| SteamUI getter return | `0x005EDF48` | `0xD65F03C0` (`ret`) |
| `posix_spawn` lazy pointer | `0x018FD500` | `__DATA,__la_symbol_ptr`, `libSystem/_posix_spawn` |

The corresponding universal-file offsets are:

```text
compatibility gate       0x02407EF8
install gate             0x0202B9D8
install fallthrough      0x0202B9DC
install invalid target   0x0202BA08
SteamUI flags getter     0x0160DF44
posix_spawn pointer      0x03301500
```

The compatibility-gate prologue is not unique by itself. The previous
three-function size sequence `0x160, 0x174, 0x17C` maps uniquely to
`0xA03D98, 0xA03EF8, 0xA0406C`, with `250/276` relocation-normalized
instructions matching. The install function maps to `0x627898`, retains size
`0x940`, and has a unique 48-byte gate context. The getter's two-instruction
body occurs more than once, but its body plus the following prologue is
unique. Both dyld fixup data and LLVM lazy-bind output identify exactly one
arm64 `_posix_spawn` entry at the listed slot.

## SteamUI resource reuse

Build `1781212412` reuses the same `steamui_websrc_all` package and the same
compatibility-page resources as build `1781139754`. No new SteamUI resource
profile or hash allowance is required.

| Clean upstream resource | Size | SHA-256 |
|---|---:|---|
| `steamui/index.html` | 457 | `55ced284314dbc65bff38fb1333d4f4bd617635895e2c0e2197b05028c243282` |
| `steamui/chunk~2dcc5aaf7.js` | 14,336,540 | `387e1b1aacdcbddd5b1fbf65b64c9f5222cfe60d917568999c2c7ddedfdf6b0a` |

The package archive SHA-256 is
`bf912e146d74b198edda02ccbc78401f70cb68ae7b97da09009295c2d2c08f74`.
The installed-file database sizes and CRC32 values match the clean
`.realsteamonmac.original` copies, and applying the existing transformations
to those copies reproduces the installed patched resources byte-for-byte.
Patched-resource hashes must not be added as accepted clean inputs.

## Local-tool loader layout

The `CCompatManager` and `CLoadLocalToolListJob` path is structurally unchanged
from build `1780965181`. Every meaningful old trace point moved by exactly
`+0x154`; the generic worker adapter moved by `+0xC`.

| Path point | Build `1780965181` | Build `1781212412` |
|---|---:|---:|
| capability-byte store | `0x725A9C` | `0x725BF0` |
| local-job allocation | `0x725CC4` | `0x725E18` |
| local-job vtable materialization | `0x725CD8` | `0x725E2C` |
| queue startup-only job | `0x725D04` | `0x725E58` |
| threaded enumerator | `0x732A84` | `0x732BD8` |
| worker return | `0x732D68` | `0x732EBC` |
| job run method | `0x732DF4` | `0x732F48` |
| after worker dispatch | `0x73328C` | `0x7333E0` |
| valid-root result | `0x733318` | `0x73346C` |
| process valid local list | `0x733380` | `0x7334D4` |
| `YldProcessCompatManifests` | `0x72DF48` | `0x72E09C` |
| local-loop complete | `0x7333D8` | `0x73352C` |
| post-list state | `0x7333F4` | `0x733548` |
| successful job return | `0x733550` | `0x7336A4` |

The current constructor is at `0x725788`. It writes the platform capability
byte at `CCompatManager + 0x798` from the case-insensitive comparison with
`"linux"` at `0x725BE4..0x725BF0`, initializes the post-logon byte at
`+0x799`, allocates the local-list job, and queues it through Steam's normal
job machinery.

The current worker callback is explicitly initialized to `0x732BD8`.
`0x73C758` calls the stored pointer, so static evidence does not support an
uninitialized callback at this site. The valid-manifest path reaches
`YldProcessCompatManifests` at `0x72E09C` and `YldRegisterTool` at
`0x72EAB4`.

## Observed fail-closed state

Before a `1781212412` profile existed, the previous engine correctly rejected
the unknown arm64 UUID instead of applying old offsets. A bounded launch
already performed during the build transition reached a healthy Steam startup
in approximately `7.19` seconds. The platform hook initialized its registry,
but no previous-build steamclient compatibility-gate or spawn-redirection
patch reported success, and no new local-manifest processing occurred.

This is evidence that the existing UUID gate fails closed. It is not evidence
that the new binary profile, native compatibility-tool registration, or game
launch path has passed dynamic acceptance.

## Remaining dynamic acceptance

The following checks remain mandatory after the exact build profile is added:

1. Verify the UUID and universal-file SHA-256 before patching, then verify all
   expected instruction words and the `_posix_spawn` fixup at runtime.
2. Confirm that the compatibility gate, install gate, SteamUI getter, and
   spawn-redirection profile each reports a successful match for
   `1781212412`, with no fallback to an older profile.
3. Trace the bounded local-loader path at `0x7333DC`, `0x73C758`,
   `0x7333E0`, `0x73346C`, `0x72E09C`, `0x733548`, and `0x7336A4` to
   distinguish worker return, root parsing, manifest processing, and
   downstream completion.
4. Confirm that standard tools under
   `~/Library/Application Support/Steam/compatibilitytools.d/` are registered
   in Steam's native compatibility service and appear in Steam's original
   compatibility dropdown without a replacement or overlay UI.
5. Confirm that the loader does not reproduce the prior approximately
   15-second main-loop stall, that the compatibility checkbox remains stable,
   and that Steam Cloud, login state, AppID mappings, downloads, and existing
   game files remain unchanged except for the intended tool selection.
6. Exercise a Windows game through the selected native tool and verify the
   resulting executable, prefix, and process routing before declaring this
   Steam build supported.

No dynamic result should be inferred from the static `+0x154` correspondence.
