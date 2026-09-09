# TEXT-1 — inherited DrawString bank-ownership defect

TEXT-1 was first reproduced before G14 at `e5d3583f52407fdb0ea180bb90d1d293d6afc7a4`.
The source bytes for `Text_Str_Hello` were correct, but the generated indexed
long read used the wrong bank. The same defect affected `CharSelect_NamePtrs`.

## Root cause

`Text_StringPool` was documented as bank-2 data but was textually emitted after
the bank-11 Footdie stream. `footdie.brr` is `32733` bytes (`$7FDD`) and its
`99`-byte fill (`$63`) makes an exact `$8040` footprint. Starting at bank 11
`$8000`, that placed the following pool at the next LoROM bank, `$0C:8040`
(ROM offset `$060040`), while generated indexed references used bank `$01`.

The same placement error put `CharSelect_NamePtrs` at `$0C:82BC`, while its
generated read used `$01:02BC`. The earlier explicit `$0C` operands were
diagnostic patches only and are not the architecture fix.

## Structural fix

The complete pool, all strings, and `CharSelect_NamePtrs` now follow
`Font_PaletteData` in `.bank 2`; Footdie remains in `.bank 11`. References are
symbolic again. A build-time layout guard rejects either table leaving
`FONT_DATA_BANK` and rejects a pool crossing a ROM bank.

The rebuilt symbols are:

```text
Text_StringPool            $02:85F8
Text_Str_Hello             $02:85F8
Text_Str_CharSelectHeader  $02:8664
Text_Str_CharSelectInstr   $02:8685
Text_Str_CharSelectInstr2P $02:86A6
CharSelect_NamePtrs        $02:8874
Text_StringPool_End        $02:8A26
```

The rebuilt operands are `LDA $02:85F8,X` in `Core_Text_DrawString` and
`LDA $02:8874,X` in `Game_State_CharSelect_DrawName`. Bank 2 uses
`$8000` through `$8A25` for font, palette, and pool data: `$0A26` bytes,
leaving `$75DA` bytes in the `$8000-$FFFF` bank window.

## Validation

After relocation, G1 exact text/palette/priority/numeric checks passed 3/3 and
G5 passed 3/3. G10 ending text passed 3/3. One unrelated OAM-hide assertion
remained flaky in one run; it is not a DrawString failure. DrawNumber, font
palette, priority bits, state transitions, and G14 presentation remain good.

TEXT-1 is closed for the DrawString defect. The isolated OAM observation is
tracked separately and is not evidence against this text fix.
