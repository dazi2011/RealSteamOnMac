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

## Acceptance Boundary

- Wine Game Controllers opens at a readable size.
- Closing or failing the panel restores the previous prefix DPI.
- Steam's native Steam Input configurator receives no project resize, zoom,
  overlay, replacement control, or polling path.
- Existing game files, depots, prefixes, and CrossOver processes remain
  untouched.
