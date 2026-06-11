# Steam Public Beta 1780965181 June 11 Refresh

Date: 2026-06-12

## Finding

Valve replaced the active arm64 `steamclient.dylib` and `steamui.dylib` on
June 11, 2026 while retaining client build number `1780965181`. Build number
alone is therefore not a sufficient binary-patch authority.

The replacement files retain Valve Developer ID signatures timestamped
June 11, 2026. They are not locally modified project artifacts.

## Fingerprints

| Artifact | Previous 1780965181 variant | June 11 refresh |
|---|---|---|
| `steamclient.dylib` arm64 UUID | `04B50ECB-07FF-30DF-A03B-1EB9292B856B` | `4678FB72-BAE9-3D1B-8313-D9A5667EA814` |
| `steamclient.dylib` SHA-256 | `d0945fc67880d048d163cf071ec9cc264cb3618c56cfb73520da36de0188f13e` | `15c231465c4df4f557ece6aba070e7601e00b2b17b3772d2248655d41dbbeae2` |
| `steamui.dylib` arm64 UUID | `87B914EC-F267-3559-8063-F21D85D896DE` | `609EA3D9-E344-340E-AEBC-FD6F386F9A28` |
| `steamui.dylib` SHA-256 | `a2ce5b3a5607057d860bdb3f0b09a173b62b3e40b904d98bd9f6930011d15851` | `451faf3ec8555961d3e9bc1dc7c81c40ca16e843abfe0889f909f558eba5146f` |

## Verified ARM64 Locations

| Operation | Previous 1780965181 variant | June 11 refresh |
|---|---:|---:|
| compatibility gate | `0x00A00874` | `0x00A03DA4` |
| installation platform gate | `0x00624600` | `0x00627884` |
| installation fall-through | `0x00624604` | `0x00627888` |
| invalid-platform target | `0x00624630` | `0x006278B4` |
| SteamUI platform getter | `0x005EAC24` | `0x005EDF44` |
| `posix_spawn` lazy-bind slot | `0x018F9500` | `0x018FD500` |

The installation gate and SteamUI getter were found by unique long-sequence
matching against the previously validated Valve binaries. The compatibility
gate retained 114 of 128 surrounding bytes and the same expected first two
instructions. The lazy-bind slot comes from `dyld_info -fixups`, not a raw
pointer scan.

Short, read-only LLDB attachments then confirmed the live process still held
the original compatibility-gate sequence `0xD101C3FF, 0xA9054FF4` and the
original install instruction `0x37200188`. The current hook had not patched
either location because its UUID profile rejected the refreshed images.

## Failure Signature

Current-session hook logs contained the refreshed SteamUI UUID diagnostic and
registry acceptance, but no current-session Steam client install-gate patch.
A fresh Black Myth: Wukong install therefore failed with native error 29
(`InvalidPlatform`) even though the browser policy rendered an install action.

## Rule

Every supported Steam variant must be authorized by all of:

1. Exact arm64 Mach-O UUID.
2. Exact source SHA-256 for offline mutation.
3. Expected instruction bytes at every patched location.
4. Structurally verified branch destinations.
5. A live current-session log and memory check after deployment.

Build number remains diagnostic metadata only.
