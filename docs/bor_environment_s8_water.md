# S8 Normal water / rocking adapter

## Compiler integration update

`build_rom.prepare_stage_environment_assets()` now performs real Normal-only
water/rock BG materialization and emits these files before packing/assembly:

- `src/generated/stage_water_tables.pasm` (bank 14).
- `src/generated/stage_bounds_tables.pasm` via `stage_bounds.emit_pasm(..., bank=15)`.
- `src/generated/hud_opponent_names.pasm` via `generate_hud_names.render`.
- `src/generated/stage_environment_materialization.json` with source identities,
  bounds, names, materialized paths and artifact hashes.

The selected catalog currently contains 14 Normal stages (physical 22..35),
with active water/rock records at 26..29, plus 47 source-bound HUD names.
These are observed layout results, not constants in the generation logic.
Water and bounds share the same parsed Normal IR; HUD reuses the source cache.
`build_msu_assets()` passes the returned private BG paths to the MSU packer.
It retains the original HUD/FP associations, physical order, shared catalog,
and Easy media files. Water assets live under content-addressed directories
in `out/compiler_campaign/stage_water`; source, encoder and blob hashes guard
cache reuse. A corrupted generation is retained and a separate retry directory
receives fresh output. Failed validation does not publish new table outputs.

Main owns actual materialization, candidate assembly, audio and native tests.
This worker does not run a second materialization concurrently. There is no
metadata-only switch in the current preparation API: calling it will encode
missing or invalid water assets. The integration tests mock only the expensive
BG encoder and write their fixture artifacts into temporary directories.

Boot-order correction: the original late Init recommendation below was
incorrect. The first `Bg_LoadScene` runs in `msu1_done` before `Core_Nmi_Init`,
and Core_Nmi_Init can enable an NMI before it returns. Main's single water
Init hook has therefore been moved to immediately after `Tad_StreamInit`,
before either operation. Cold Init clears only water-owned bytes; Reset skips
NMI shadow accesses when neither Enabled nor Pending is set. The first
Bg_LoadScene reset cannot consume uninitialized ownership or NMI shadow bytes.

Focused verification: 15 tests pass across `test_stage_water` and
`test_stage_environment_build`, including exact bounds/HUD helper output,
Normal-only substitutions, one Normal IR parse per stage, cache reuse and
corruption rejection, unchanged Easy hashes, and cold-boot ordering. No
native test or full ROM/audio build was run by this worker.

The following source/asset audit records the original isolated implementation;
the integration and Init positioning in this update supersede its handoff state.

Implemented in new files only: `src/core/stage_water.pasm`,
`tools/bor_compile/stage_water.py`, and its targeted tests. This document is the
integration handoff. No ROM/media build, emulator run, or commit was performed.
The shared compiler capability matrix is deliberately untouched. This is an
implemented **target adaptation**, not a lossless source-renderer certificate
or a claim that complete Normal has passed visual acceptance.

## Current evidence

The local `out/bor_compile_s6/BOR.C` matches the existing pin at commit
`eba02fe6c9e97e388126c51560a92024f406d8c0`, SHA256
`68c54a190c5713b1a42b75898ae9ff5246896de0ded3f8c1247c507681735f41`.
The original PAK read for this audit has SHA256
`a2a55cdd5e1145e845607ecec3ad85a342529492e7120449a928f3a6eaea81d6`.

`BOR.C:1898` loads the water bitmap and clamps the operand to at least 2.
It is a distortion amplitude, not a renderer-mode enum. `BOR.C:4834` and
following select the wave renderer without rocking and the perspective-plane
renderer with rocking. The source's integer `200/30` is **6**, while `200/8`
is 25. Thus horizontal motion advances every six source ticks, and the
32-entry rock sequence advances every 25 ticks. The additional panel/entity
Y displacement is `-rockoffs[index]`; the existing baseline `quake-4` is
separate. Source background parallax and the plane offset also use advancex/2.

The pinned [TEXTURE.C implementation](https://raw.githubusercontent.com/Plombo/beatsofrage/eba02fe6c9e97e388126c51560a92024f406d8c0/GAMELIB3/TEXTURE.C)
defines a 256-entry rounded sinusoidal distortion table. The wave renderer
advances its phase by five per source scanline. The plane renderer increments
factor 10 to 11 and changes horizontal sampling scale with depth. The adapter
does not claim to reproduce that plane's changing camera-dependent sampling.

| Normal source stage | Water amplitude | Rock | Source background | Source texture |
|---|---:|---:|---|---|
| 3A | 15 | 1 | BOAT2/BACK.GIF, 520x80 | BOAT2/WATER.GIF, 520x84 |
| 3B | none | 1 | BOAT/BACK.GIF, 479x81 | none |
| 3C | none | 1 | BOAT3/BACK.GIF, 479x81 | none |
| 4A | 2 | 0 | PIER/BACK.GIF, 424x80 | PIER/WATER.GIF, 424x58 |

All 14 Normal stage entries were parsed. These four are the only active
water/rock occurrences; source directives, not stage names, drive binding.
The two texture hashes are respectively
`371c13700d511b802aa45d252efcb864e2abe543e17eb9ae7ecb8cc38a4e489b` and
`369e036af294dc651f6821961175438d5c6c09f45c72ab74e6fb298cc9d98b2d`.

Current presentation assets are `out/bg_3easy`, `out/bg_3beasy`,
`out/bg_3ceasy`, and `out/bg_4aeasy`. Their manifests report 28-row streaming
BG1 maps, widths 600/480/32/382 tiles, and 1678/1435/676/6879 unique tiles.
Their tiles.bin SHA256 values, in that order, are:

```
fcc9ecafc0153780f7712d97a5c5633ce285ba56dbc2797a4c3b59f3e7a96fab
dd9374b1a68033f779a7f94ec8ce68a7ee398620edf306d17a8d0ee276829486
3598a88158b5ce8bac430a598d5a707744e406c84f7f8b13202cb4cef9466fe4
a8e8278553f1f6bdf9e55e712346deb9ed38b8f96b4f9d524ea8dbf4d7ff7608
```

`level_parse.py` does not parse water. `composite_scene._composite` vertically
tiles the background and then flattens panels/frontpanels; it never inserts
the texture. These are not independently scrollable source layers. The
existing 3C preview was also inspected: it is a flattened cabin wall/floor.
The real-source composite tests prove that inserting the two missing textures
changes visible pixels, preserves opaque panels, and leaves pixels outside
the source water band unchanged. Existing encoded assets were not regenerated.

## Deliberate target adaptation

Identifier: `S8_FLATTENED_BG1_BOUNDED_RASTER_V1`.

- New Normal-only BG records bake source water under the panels. The boat
  texture uses a depth-dependent, time-zero plane, repeated per 320px source
  viewport; safe modulo fixes the source plane's `s==width` indexing edge.
  The pier bakes the mean distortion and applies a changing scanline delta.
- The 256 wave samples use the pinned source formula with host double math,
  then scale X by 4/5. This is not a Watcom floating-point equivalence proof.
  Amplitude 15 produces deltas -12..12; amplitude 2 produces -2..1. Rounding
  and resampling may differ by a pixel from rendering at source resolution.
- Rock overrides waves as in BOR. Its horizontal drift is derived from
  `time/6`, but wraps after 20 source pixels and is centered at -8 target
  pixels: range -8..7. It affects the flattened top band through source Y159.
  It does not preserve unbounded translation or source half-camera parallax.
  These bounded displacements fit inside the accepted 16px edge mask.
- Rock Y uses the source 32-entry sequence, scaled 224/240 to match the BG
  image, and shifts BG1 plus character OAM. BG1 includes baked background and
  panels, so both rock together. The source rocks panels/entities separately
  from its background. BG3/HUD/frontpanel scrolling is left with its existing
  owner; this is a visible limitation for independent frontpanels. Actor depth,
  collision, world coordinates, and the accepted baseline/quake behavior are
  not changed. Rows exposed at the bottom are deliberately black.
- A declared 60Hz presentation clock samples `floor(frame*200/60)`. Its 5760
  frame cycle simultaneously wraps wave, rock, and bounded drift phases. It
  freezes outside PLAYING and restarts at load. This is not the S6 absolute
  source-world clock or a claim that NTSC is exactly 60Hz. Slow frames slow
  this presentation clock. A pause recognized inside the dispatcher can
  retain the already prepared sample for that iteration.

Neither motion of flattened foreground pixels nor static perspective scaling
is presented as lossless. Manual visual acceptance and hardware contention
measurement remain integration work. Two bytes of BG1 scroll HDMA per visible
line are new bus work alongside TAD, with no throughput claim here.

## WRAM / ROM / publication contract

`StageWater_Work=$7FB220`, end-exclusive `$7FB784`, exactly 1380 bytes:
32 bytes state; two 674-byte slots, each containing 224 `(1,HOFSlo,HOFShi)`
records plus one terminator and one padding byte. The FP reverse map remains
`$7FB000..$7FB201`; stamps remain `$7FB800..$7FB900`. Searches of current
source and compiler/audio allocation literals found no other owner inside
this gap. The spawn arena remains `$7F9200..$7F9FFF`; it is not reused.

Reserve HDMA channel 6, mode 2 to BG1HOFS `$210D`. The module masks only bit
6 of the HDMA shadow; TAD channel 0 and ordinary DMA channel 7 remain owned
by their existing code. Active Normal Begin holds `Nmi_FrameBusy`; End
publishes the inactive table last and restores the prior busy byte. NMI
respects both existing busy gates, consumes a completed table, programs its
pointer and vertical scroll, and lets Core_Nmi_Play perform the hardware
HDMA-enable commit. A skipped commit retains the previous immutable table.

Put code and generated tables in **bank 14**, not bank 13. Tables occupy
19008 bytes. The source-only instruction-length audit verifies code plus
tables fit a 32KiB bank and checks all relative branch ranges; it is not an
assembled placement proof. Leave room for any other bank-14 environment
routines in the integrator's bank budget.

## Exact main.pasm hooks (not applied)

Use these label/text anchors rather than historical line numbers; shared
files changed concurrently during this task. All public calls preserve
P/A/X/Y/D/DBR. Begin, End, Reset, Init, and Nmi accept either M/X width;
the main loop's normal input is A16/I16, D unchanged, DBR as established by
the caller. ApplyOamY is placed at an A8 actor-render site. ClearGuard is
called in forced blank with A16/I16; it uses long MMIO addresses and does
not require DBR0. Decimal arithmetic is cleared internally and P restored.

1. Immediately after the existing `jsl Tad_StreamInit`, insert:

```asm
    jsl StageWater_Init
```

Use Init, not Reset, here: Init never reads uninitialized ownership or NMI
shadow bytes. This must precede the first Bg_LoadScene, not follow Core_Nmi_Init.

2. At `Bg_LoadScene`, after its existing `php` / `sei`, insert:

```asm
    jsl StageWater_Reset
```

The loader must already be in its existing forced-blank/no-commit load
window. SEI by itself does not block NMI. Reset releases any adapter frame
lease, drops pending state, removes its prior Y offset, and masks channel 6.
Retain the caller's existing NMI/blanking protocol.

3. At `Bg_LoadScene__hud_done`, before its `plp` / `rts`, insert:

```asm
    jsl StageWater_ClearGuard
```

This clears VRAM words `$6380..$63FF` and `$6780..$67FF` (the four unused
bottom rows in each BG1 map page) for Normal rocking entries only, using
the loader's index. It depends on the streaming loader's reserved blank
tile zero. The supported affected records are 28-row streaming records.
Do not use this adapter on a 32-row vertical/static record.

4. In `scpu_main_loop`, replace the single dispatcher call with:

```asm
    jsl StageWater_Begin
    jsr Game_State_Play
    jsl StageWater_End
```

Do not put End after a wait or an early return. Begin must precede actor
rendering; End must follow Core_Oam_Play and the final camera shadow update
inside the dispatcher. Do not add calls to shared game_state.pasm. Begin
gates on target `Game_CampaignId==3`; this is distinct from source Normal
set ID 1. Reset remains necessary on every scene load, including reload of
the same physical stage. The boot loop gains eight bytes: verify the fixed
bank-0 end against `$FFA0` when builds are authorized.

5. In Character_RenderFrame, immediately after `jsl Jump_ApplyOamYOffset`:

```asm
    jsl StageWater_ApplyOamY
```

This must stay before subsequent actor hiding/culling decisions. Input and
output remain A8 with the actor DP/DBR unchanged. Do not apply it again
to already emitted OAM or to the `$F0` hidden-sprite sentinel.

6. The interrupt stub becomes:

```asm
.org $FFA0
nmi_handler:
    jsl StageWater_Nmi
    jsr Core_Nmi_Play
    rti
nmi_handler_end:
```

Do not append the hook after Core_Nmi_Play: HDMAEN has already been committed
there. The hook saves full A and P before inspecting either interrupted
width. It does not touch X/Y/D/DBR. The new stub is eight bytes and remains
below the IRQ stub at `$FFB0`.

7. Add this in the banked include section (before any following bank's own
`.bank` / `.org`, never at the fixed bank-0 vector/header location):

```asm
.bank 14
.org $8000
.include "core/stage_water.pasm"
.include "generated/stage_water_tables.pasm"
```

The generated table file is an integration product, not created by this
task. Its bare long labels retain Poppy bank metadata. No WRAM definition
is needed in main: the new module binds `$7FB220` itself.

## Compiler integration API (not applied to shared files)

With `tools/bor_compile` on PYTHONPATH:

```python
from stage_water import metadata, emit_tables, encode_background
rows = metadata(selected_physical_configs, 'out/bor_compile_s6/BOR.C')
assembly_text = emit_tables(rows)
# Write assembly_text to src/generated/stage_water_tables.pasm at generation.
```

`metadata` accepts the selected physical catalog in its exact physical order,
with the existing `family`, `pak`, and `source_level` fields. It skips foreign
families, verifies BOR.C, and rejects unsupported amplitudes, vertical scroll,
uncertain IR, and unsupported background heights. Last source assignment
wins, including `rock 0`; authored water below 2 clamps to 2. `emit_tables`
rejects duplicate physical IDs. This metadata is not itself media acceptance.

For each active Normal binding, load its `PakIndex` and `load_level` from
`composite_scene`, then call `encode_background(index, level, row)`. It returns
`(manifest, blobs)` with the accepted streaming format: 28-row column-major
tilemap, 4bpp tiles, and the existing palette budget. The caller writes the
three blobs and manifest into **new Normal-only paths**, then uses those
paths in Normal's physical records. Even a source-identical Easy/Normal
stage must not share a mutated media record. Easy keeps its accepted assets.

The encoder uses the accepted quantization/encoding primitives and rejects
tile-ID overflow. Its real media encoding was not executed because builds
were excluded. Only source-resolution composition and metadata/reference
tests ran. Do not arm these tables against old assets that omit water;
do not flip general water/rock `certified` flags merely from table emission.

## Verification

Run only:

```powershell
$env:PYTHONPATH='tools/bor_compile'
python -m unittest tools.bor_compile.test_stage_water -v
```

Nine targeted tests pass: current source pin/call audit, all Normal entries,
renamed-stage independence, last assignment and failure cases, the full
5760-frame clock cycle, both wave amplitudes, plane precedence, HDMA bounds
and Easy no-op reference, real source texture insertion/opaque-panel retention,
table budget, WRAM boundaries, no illegal long addressing forms, width lint,
and relative branch reach. No assembler, ROM build, emulator, full regression,
generated production file edit, or commit is part of this result.
