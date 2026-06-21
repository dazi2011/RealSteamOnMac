# Steam Public Beta 1781911235 Validation

Date: 2026-06-21

## Scope

This note records the static and live evidence used to support Steam public
beta build `1781911235`. The existing injection architecture was retained; no
broad binary scanning or relaxed build checks were introduced.

## Binary identities

| Image | Universal SHA-256 | arm64 UUID |
|---|---|---|
| `steamclient.dylib` | `ba7168140b6e6505c54ad9a0a940a807f4e2773a6ed9f40612b66028686bf435` | `6886D7F5-2B8B-35D3-9008-6ACABF64DF57` |
| `steamui.dylib` | `81e30df7c208f7cbb284736350280dc49a66fc2d040ab891aa071394dceba9f1` | `879F08BB-DC65-3967-8834-714D804A53F9` |
| `steam_osx` | `4597dceeac3433a8dec22605b691dfeace6aede7d8c7612c138234357d06983c` | `D3E10461-8AC0-365C-A25D-7C4709BA33C2` |

## arm64 profile

| Target | Image-relative offset | Expected behavior |
|---|---:|---|
| compatibility gate | `0x00A03A3C` | `sub sp, sp, #0x70` |
| compatibility gate next word | `0x00A03A40` | `stp x20, x19, [sp, #0x50]` |
| install gate | `0x006254B4` | `tbnz w8, #4, 0x6254E4` |
| install fallthrough | `0x006254B8` | `tbnz w8, #2, 0x625514` |
| install invalid target | `0x006254E4` | invalid-platform path |
| error-29 marker | `0x00625500` | `mov w8, #0x1d` |
| `_posix_spawn` lazy pointer | `0x018FD500` | unique libSystem binding |
| SteamUI platform-flags getter | `0x005EFE70` | `ldr w0, [x0, #0x1c]; ret` |

The compatibility function maps uniquely through its function-size sequence
and normalized instruction body. The install gate retains its exact 48-byte
context and AppID register contract. The `_posix_spawn` binding did not move.

## SteamUI resources

The index resource remains unchanged:

- `index.html`: `55ced284314dbc65bff38fb1333d4f4bd617635895e2c0e2197b05028c243282`

The clean compatibility chunk is new:

- `chunk~2dcc5aaf7.js`:
  `58b133db3f5db69768dc6889579aea1dcd7993bf86c332be79493b68879a7fee`

All five guarded anchors retain their expected counts. Applying the current
transform produces chunk SHA-256
`5cb466bd85af75a42d7381910ae662c98d70e8bd2a2897270e6ea4d4a00af7fa`.
Only the clean hash is allowlisted.

## Live installation evidence

The previous installation was formally uninstalled into
`~/RealSteamOnMac-Rollback/uninstall-20260621T091843Z`. Game and prefix
sentinels were preserved. Valve's updater then installed build `1781911235`.

The current source installer created the matching clean rollback snapshot
`~/RealSteamOnMac-Backups/steam-20260621T092529Z`, installed the runtime,
helpers, hook, native engine, launcher, compatibility tools, and SteamUI patch,
and recorded build `1781911235` with channel `publicbeta`.

After launch, the native log reported:

- install-gate patch success for build `1781911235`;
- allowlist-scoped spawn redirect installation;
- typed registry publication for 34 store apps;
- initial SteamUI object reconciliation.

A system screenshot confirmed that Steam reached its normal Simplified Chinese
store interface. No game was launched. Steam resumed an existing download
queue automatically; RealSteamOnMac did not initiate a game download.

## Remaining acceptance

This validates installation, startup, strict profile matching, and basic UI
health. It does not validate every game, download route, compatibility option,
non-Steam shortcut, or container action. Those remain user-directed manual
tests.
