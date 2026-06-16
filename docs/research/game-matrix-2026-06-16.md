# Game Matrix Acceptance, 2026-06-16

This note records the read-only RealSteamOnMac game-library acceptance pass
run on 2026-06-16 Asia/Shanghai. It is intentionally conservative: a game is
not treated as launch-accepted until both Steam's manifest state and the
resolved Windows launch target are usable.

## Command

```sh
python3 script/run_game_acceptance.py \
  --steam-root "$HOME/Library/Application Support/Steam" \
  --appid 1174180 --appid 1237970 --appid 1326470 --appid 242050 \
  --appid 2943650 --appid 4000 --appid 517630 --appid 714010 \
  --appid 730 --appid 990080 --appid 1118200 --appid 2358720 \
  --output /tmp/realsteamonmac-game-acceptance-2026-06-16.json
```

Report SHA-256:
`b15edc27c1901b021ca4c3b6b201b561b577b5453113365b127a64da8768b577`

Summary:

- Requested: 12
- Ready by manifest state plus Windows launch target: 4
- Blocked: 7
- Manifest/app discovery errors: 1

## Runtime Fingerprint

The installed runtime binary matches the current source, but the installed
launch-descriptor helper does not:

| File | Matches source | Source SHA-256 | Installed SHA-256 |
| --- | --- | --- | --- |
| `realsteamonmac-runtime` | yes | `7474c61731d7e5dcf9fddd0431f8a6372d9b212c4a59de7d3806d5fabb77cf99` | `7474c61731d7e5dcf9fddd0431f8a6372d9b212c4a59de7d3806d5fabb77cf99` |
| `steam_launch_descriptor.py` | no | `8496dd4c5e9d45f69549c9f2c5a692378fbe86dbff89ba30d57e625fbebd0bd3` | `397146ced8d7dee0c514fd051283a9060ecf881d56c682e7ff505a41aa85de48` |

This explains the current field symptom where Aimlabs still launches through
the stale `.app` path even though the source resolver now selects
`AimLab_tb.exe`.

## Game Results

| AppID | Game | Manifest diagnostic | Launch target | Container | Result |
| --- | --- | --- | --- | --- | --- |
| 1174180 | Red Dead Redemption 2 | ready | `PlayRDR2.exe` | exists | Static launch-ready; Rockstar/bootstrap still needs live recovery validation. |
| 1237970 | Titanfall 2 | ready | none | missing | Steam appinfo is protocol-only (`link2ea`), so there is no safe Windows launch record to redirect. |
| 1326470 | Sons Of The Forest | ready | `SonsOfTheForest.exe` | exists | Static launch-ready with GPTK config. |
| 242050 | Assassin's Creed IV Black Flag | repair-required | missing | missing | Only installer/partial content is present; default Windows target is missing. |
| 2943650 | FragPunk | ready | `FragPunk.exe` | exists | Static launch-ready; parser now accepts single `.exe` records without explicit OS metadata. |
| 4000 | Garry's Mod | state-blocked | missing | missing | Steam state says update-required; expected Windows launch targets are missing. |
| 517630 | Just Cause 4 | state-blocked | missing | missing | Steam state says update-required; default Windows launch targets are missing. |
| 714010 | Aimlabs | repair-required | `AimLab_tb.exe` | missing | Source resolver chooses the correct Windows target, but Steam still reports files-missing and installed runtime helper is stale. |
| 730 | Counter-Strike 2 | state-blocked | none | missing | Steam state says update-required and appinfo has no valid default Windows target. |
| 990080 | Hogwarts Legacy | repair-required | `HogwartsLegacy.exe` | missing | Source resolver avoids stale `Phoenix-Win64-Test.exe`, but Steam still reports files-missing. |
| 1118200 | People Playground | ready | `People Playground.exe` | exists | Static launch-ready with DXMT config. |
| 2358720 | Black Myth: Wukong | manifest missing | none | n/a | The appmanifest is absent after uninstall; this aligns with the reported empty-folder/one-second pseudo-download failure path. |

## Steam RunGame Evidence

Current Steam build `1781212412` exposes
`SteamClient.Apps.RunGame(appid, "", -1, flag)`. A single-argument call fails
with:

```text
Apps.RunGame requires 4 arguments; only 1 given
```

The SteamUI bundle contains call sites of the form:

```js
SteamClient.Apps.RunGame(t.GetGameID(), "", -1, i)
```

Future live launch probes must use the four-argument native shape and must
record the selected SteamUI launch flag instead of guessing from the old
single-argument pattern.

## Conclusions

- Aimlabs and Hogwarts are not depot-loss-only issues: their Windows
  executables exist and the source resolver can select them. Their current
  blocking state is a combination of Steam manifest `files-missing` plus stale
  installed launch-descriptor code.
- Black Myth: Wukong currently has no appmanifest, so the acceptance harness
  correctly treats it as not installed and does not create a prefix.
- Several older titles are blocked before runtime compatibility can be tested
  because Steam marks them update-required or their expected Windows targets
  are missing.
- The next package/install validation must prove that
  `steam_launch_descriptor.py` is updated in the installed runtime before
  claiming the Aimlabs `.app` regression is fixed for users.
