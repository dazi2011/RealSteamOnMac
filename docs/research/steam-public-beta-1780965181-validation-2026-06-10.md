# Steam Public Beta 1780965181 Validation

Date: 2026-06-10

## Scope

This note records the offline validation used to add Steam Public Beta build
`1780965181` without weakening the existing build-specific fail-closed checks.
The previous supported build remains `1780705203`.

The cached Valve VZip archives were checked against the new package manifest,
then decompressed with `valvevz` v1.0 from:

https://github.com/OpenMandrivaSoftware/valvevz

The upstream source needed a local macOS-only include adjustment from
`<bits/types/FILE.h>` to `<cstdio>` to compile. That temporary build change is
not part of this repository.

## Binary Fingerprints

| Artifact | Build 1780705203 | Build 1780965181 |
|---|---|---|
| `steamclient.dylib` arm64 UUID | `B2950628-803A-3EFD-99EF-3AD6B7B65D1C` | `04B50ECB-07FF-30DF-A03B-1EB9292B856B` |
| `steamui.dylib` arm64 UUID | `BF95203F-385E-3AF0-82B6-AC509AE1224D` | `87B914EC-F267-3559-8063-F21D85D896DE` |
| `steamclient.dylib` SHA-256 | `f9c1df763087900a66020635f22559f49533edd3290f0880eb13f46d2dfe2ed5` | `d0945fc67880d048d163cf071ec9cc264cb3618c56cfb73520da36de0188f13e` |
| clean `index.html` SHA-256 | `55ced284314dbc65bff38fb1333d4f4bd617635895e2c0e2197b05028c243282` | same |
| compatibility chunk SHA-256 | `6d28c06fafb32f99c695f4bc4d1b8a8b8fb5bc1efc425f2a78abb8697af81349` | `f77316131cbed91865a800103bbda855a43395eecfb2bc866bc58c33fdea4c69` |
| `steamui.dylib` SHA-256 | not used as a patch authority | `a2ce5b3a5607057d860bdb3f0b09a173b62b3e40b904d98bd9f6930011d15851` |
| `steam_osx` SHA-256 | not used as a patch authority | `20a7c5043208194c9cfe15c2611aacb02a69fd76349884835fdd84cd2d090d5a` |

The new Valve binaries are universal `x86_64`/`arm64` Mach-O files and retain
Valve's Developer ID signature.

## Verified ARM64 Offsets

| Operation | Build 1780705203 | Build 1780965181 |
|---|---:|---:|
| compatibility gate | `0x00A012D0` | `0x00A00874` |
| installation platform gate | `0x0062505C` | `0x00624600` |
| installation fall-through | `0x00625060` | `0x00624604` |
| invalid-platform target | `0x0062508C` | `0x00624630` |
| SteamUI platform getter | `0x005EAC3C` | `0x005EAC24` |
| `posix_spawn` pointer slot | `0x018F9500` | `0x018F9500` |

The compatibility and installation gates moved by `-0xA5C`. The SteamUI
getter moved by `-0x18`. The installation instruction remains
`0x37200188`, decoded as `tbnz w8, #4`, and both decoded branch targets match
the recorded fall-through and invalid-platform control flow.

The 16-byte SteamUI getter sequence maps uniquely in the new arm64 slice.
Rosetta/x86_64 native-engine profiles remain intentionally absent so the hook
fails closed outside native arm64 Steam.

## UI Resource Validation

The new compatibility chunk contains exactly two expected compatibility-page
anchors. Applying the guarded patch produces:

`f53e16c4066cecb367c12d9a9f4e93843467d5cbe298929bedda3e3c43581515`

The patched `index.html` remains:

`01603212f3ac26aa27208a6f0d09f51c6f563c0e550e86978a2c67284df58a51`

Unknown UUIDs, source hashes, resource hashes, and instruction bytes continue
to fail closed.

## Rollback Rule

An existing clean backup is tied to its recorded Steam build. The installer
now refuses to reuse that backup when the current Steam manifest reports a
different build. The supported transition is:

1. Uninstall RealSteamOnMac and restore the recorded clean snapshot.
2. Let the official Steam bootstrap update to the new build.
3. Install RealSteamOnMac again so it captures a new clean snapshot.

This prevents a later uninstall from replacing a newer Steam runtime with an
older backup.
