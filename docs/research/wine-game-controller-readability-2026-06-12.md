# Wine Game Controller Readability

Date: 2026-06-12

## Correct Target

The controller interface reported as too small is Wine's Game Controllers
control-panel applet:

```text
wine64 control.exe joy.cpl
```

It is not Steam's `SP Controller Configurator_*` Steam Input window. The
earlier implementation that scanned and resized the Steam popup was therefore
removed.

## Live A/B Measurement

The test used AppID 1118200 (People Playground), its existing prefix at
`/Volumes/990pro/games/mac/steamapps/compatdata/1118200/pfx`, and the active
DXMT Wine 11.10 runtime.

| Wine `LogPixels` | Scale | Window size | Result |
|---:|---:|---:|---|
| 96 | 100% | 250x311 points | Text and controls too small |
| 144 | 150% | 373x436 points | Improved, still smaller than desired |
| 192 | 200% | 496x562 points | Readable, complete, no clipping |

The setting is `HKCU\Control Panel\Desktop\LogPixels` inside the selected
game's Wine prefix. Because this registry value applies to the whole prefix,
the product must not change it permanently.

## Runtime Policy

For the `controllers` container operation:

1. Read and validate the existing `LogPixels` DWORD.
2. Use the larger of the existing value, 96, and 192.
3. Apply the temporary value only when it differs.
4. Run `control.exe joy.cpl` synchronously.
5. Restore the exact original DWORD in `finally`, or delete the value if it
   was originally absent.
6. Never reduce an existing value above 192.

The live 192 DPI probe was closed normally. A subsequent Wine registry query
returned `LogPixels REG_DWORD 0x60`, proving that the active prefix returned
to its original 96 DPI state.

## Installed Product Acceptance

The repository runtime and UI were atomically deployed after preserving the
previous installed files at:

```text
~/Library/Application Support/RealSteamOnMac/backups/wine-controller-readability-20260612T104827Z
```

Two product paths passed:

1. Calling the installed runtime action directly opened a `496x562` panel,
   reported controller DPI 192, exited with code zero, and restored 96 DPI.
2. In People Playground's Steam-owned compatibility page, the real container
   `DialogDropDown` selected Game Controllers and the native Execute button
   started the action. UI status reached one start, one completion, zero
   failures, and no error. The panel again measured `496x562`; closing it
   restored `LogPixels` from `0xc0` to `0x60`.

After a native Steam restart, the old popup-scanner status fields were absent.
A 15-second, 60-sample trace of Steam's compatibility checkbox and selector
recorded one stable state and zero transitions. The checkbox remained checked
and enabled, DXMT remained selected, and no legacy panel or modal appeared.

A separate visible Wine Program Error was traced to `rundll32.exe` PID 63690,
started on 2026-06-11 at 22:51, before this acceptance run. It was not created
or closed by either controller test.

## Acceptance Boundary

- Wine Game Controllers opens at a readable size.
- Closing or failing the panel restores the previous prefix DPI.
- Steam's native Steam Input configurator receives no project resize, zoom,
  overlay, replacement control, or polling path.
- Existing game files, depots, prefixes, and CrossOver processes remain
  untouched.
