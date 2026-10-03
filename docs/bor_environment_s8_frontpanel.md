# S8 Normal full foreground — implementation in progress

The band-only runtime and `s8_frontpanel_hooks.patch` described below are
superseded and must not be integrated. Current integration is the unapplied
`s8_frontpanel_bg2_hooks.patch`; implementation lives in
`src/core/stage_frontpanel_bg2.pasm`, `stage_frontpanel_host.pasm`, and
`tools/bor_compile/stage_frontpanel_bg2.py`. All seven Normal FP stages use
authored cycles, including singleton declarations, and private BG1 composites
without baked foreground. Easy remains on its original path.

BG2 uses CHR base $3000 and map $6C00..$73FF. Its 256 character slots occupy
$3000..$3FFF: tile IDs 0..127, 128..191, and 192..255 are contiguous within
that range. BG1 tiles occupy $0000..$1FFF; BG3 HUD/frontpanel-cache/font tiles
use $2000..$2BFF; the exclusive 16-KiB source OBJ region is $4000..$5FFF.
BG1, BG3, and BG2 maps occupy $6000..$67FF, $6800..$6BFF, and $6C00..$73FF.

Isolated materialization `out/s8_fp_full_qyk0jzz7` measured full 28-row,
33-column peaks 163/94/108/25/51/35/35 for physical IDs
22/27/28/30/33/34/35; the corresponding 34-column active-plus-pending peaks
are 168/94/108/25/51/35/35. These are measurement artifacts, not a claim
that the currently running candidate contains this implementation.

Normal encoding locks palette 1 to actual Font_PaletteData (CGRAM4..7),
then lowers the indexed target losslessly to BG2 4bpp palette 0. Source
color quantization, eight-pixel cycle rounding, and integer camera
floor(Screen_PosX*7/5), vertical zero, remain ACCEPTED_COMPAT, not source
exactness. Final verification must compare actual post-Core_Text_Init CGRAM
and rendered pixels. The reported older-candidate magenta/striped HUD is
not evidence for the new encoding. Native visual/timing proof remains pending.

## Historical band-only implementation (superseded)

Implemented in `tools/bor_compile/stage_frontpanel.py` and the optional
`frontpanel_sequence=` API in `tools/bg_converter/convert_frontpanel.py`.
Only Normal IR supplied by the existing source cache is considered. Ordered-cycle
selection is `len(frontpanel declarations) > 1`, not a stage-name branch. All
seven Normal FP slots now also receive the font-palette correction. Declaration
order and all image hashes survive in the generated manifest. Scalar/default
conversion is unchanged, including accepted Easy binary output.

## Source and target contract

Pinned BOR.C SHA256:
`68c54a190c5713b1a42b75898ae9ff5246896de0ded3f8c1247c507681735f41`.
BOR.C 4929–4940 steps by `frontpanels[0]->width`, cycles
`frontpanels_loaded`, and uses integer `advancex*1.4` horizontally, zero
vertically. `loadfrontpanel` clips the bitmap and preserves trim offsets in
the sprite center. The matching primary
[BITMAP.C](https://raw.githubusercontent.com/Plombo/beatsofrage/eba02fe6c9e97e388126c51560a92024f406d8c0/GAMELIB3/BITMAP.C)
defines this opaque-bounds clipping. The compositor retains original masked
image placement and uses the first opaque bounding width for stride.

Normal 1A declarations at lines 8–11 are STREET F00, F01, F02, F03. All have
183-pixel opaque width, giving a 732-pixel source cycle. The explicit target
adapter compiles this cycle once at 584 pixels (nearest 8-pixel boundary after
4/5 scaling), then repeats it to the existing 408-column BG1 extent. It retains
the existing 240-to-224 vertical crop/nearest-resize and three 2bpp palettes
1–3, with HUD palette 0 untouched. This is documented target adaptation,
not lossless PC raster rendering or source 1.4 parallax. Sprite overhang beyond
the first stride fails closed rather than being silently clipped at repetition.
Nontransparent target pixels outside runtime FP rows also fail closed.

Straight whole-level resizing produced 1456 unique tiles and was rejected;
evidence remains in `out/s8_fp_sequence_yxrr146g`. Tile-aligned cycle conversion
in `out/s8_fp_cycle_p90z6w2f` produced 320 tiles and a worst 32-column resident
window of 161 tiles. Runtime limits are read from assembly on every fresh/cache
admission: 768 Tile2Slot IDs, 256 usable slots, 32 columns, rows 21–27. No cache
allocation or palette budget was enlarged. These are static media checks,
not runtime service/deadline or visual acceptance.

## Build integration (already wired)

`build_rom.prepare_stage_environment_assets` invokes FP materialization after
water with the same source objects and Normal IR. It returns copied bindings,
changing only the Normal multi-FP slot's `frontpanel` path. Content-addressed
outputs live beside the water output root under `stage_frontpanel/`.
`stage_environment_materialization.json` includes `frontpanel_media`.
Manifest fingerprints bind source level/image hashes, declaration lines,
pinned BOR source, encoder files, library versions, dimensions and placement;
cache reuse revalidates binaries and live resource limits. Corrupted outputs
are preserved and regenerated under a retry path.

`build_msu_assets` now passes
`fps=[cfg['frontpanel'] for cfg in environment_configs]` to the packer.
Motion requires the banked helper and generated table described below.
A pack already started with old bindings does not contain this sequence;
main must run preparation/packing after that process finishes. This lane did
not run shared preparation, ROM/MSU assembly, native generation or emulator.

## Runtime owner handoff

`src/main.pasm:Core_StreamScrollFp_PickColumn` reads 16-bit `Screen_PosX`,
shifts three times, and uses that column for the FP window. Seek/resolve/commit
use existing world columns and the 32-column ring. Commit starts at row 21;
the fetch budget remains two tiles per call. `src/core/nmi.pasm` owns
`Nmi_Bg3ScrollX=$7E501F` and writes it to BG3HOFS ($2111). Current gameplay
does not populate this shadow; scene-video/init clears it. Thus current
column replacement alone is not continuous camera scrolling or BOR parallax.
Main owns any generic FP camera/HOFS implementation and HUD interaction.
The accepted BG1 composite also contains legacy scalar F03: that baked art
can show through transparent BG3 pixels. It is unchanged here; eliminating
that duplicate requires a separately coordinated Normal BG1 recomposition.

Focused tests cover exact source pixels for all four panels and a repeated/
scrolled cycle, declaration-driven selection, fresh/cache/corrupt-cache
materialization, source/byte provenance, resource boundary rejection, and
byte-identical legacy Easy conversion. Integration tests additionally hash
all original BG/FP assets before and after private materialization.

## Final font correction and motion handoff

The measurements above (320 tiles / 161 residents) predate the font correction.
`Core_Text_Init__pal_loop` (`src/core/text.pasm` 185–210) overwrites CGRAM 4–7
after FP loading. `Font_PaletteData` is bound to `src/assets/font_palette.bin`
by the actual main incbin. Normal conversion now fixes palette 1 to those four
BGR555 words, optimizes two remaining three-color palettes, then assigns each
tile to the least-error of all three palettes (transparent pixels excluded).
This retains three palettes / nine nontransparent slots, though the font owns
three of those colors. No CGRAM 16+ allocation changes. The exact font bytes,
hash and owner are in every Normal manifest and fingerprint; cached media and
motion table generation reject a mismatch. Default Easy conversion remains
byte-identical. Scalar Normal geometry remains the existing atlas; only its
palette quantization changes. This is explicitly color adaptation, not exact
source RGB reproduction.

Isolated final-color conversion in `out/s8_fp_font_8hwql3mj` produced:

| Physical ID | Tiles / 768 | 33-column FP-band residents / 256 |
| --- | ---: | ---: |
| 22 | 312 | 163 |
| 27 | 314 | 1 |
| 28 | 108 | 1 |
| 30 | 309 | 27 |
| 33 | 490 | 104 |
| 34 | 43 | 15 |
| 35 | 33 | 10 |

These are isolated encoder results, not a claim about main's concurrent pack.
The compiler additionally admits the full 28-row boot window, live 768-ID
domain, 33-column runtime band, and cyclic seam against 256 usable cache slots.

`docs/s8_frontpanel_hooks.patch` is a zero-context unified patch for main/NMI;
dry-run command: `git apply --check --unidiff-zero docs/s8_frontpanel_hooks.patch`.
Main applies it, not this lane. It includes `core/stage_frontpanel.pasm` and
`generated/stage_frontpanel_tables.pasm` in bank 18. Preparation already emits
the latter from the same Normal IR (no duplicate source compiler/parser).
Cold/reset wrappers replace the existing JSLs, retaining water's cold order
and adding FP state initialization without growing those bank-0 callsites.

Hook ABI: Pick receives/returns A16/I16, returns C=1/A=selected Normal column
or C=0 to execute legacy Easy; clobbers A/X/P. SourceColumn receives A16 world
column and X16 stride, returns wrapped A while preserving X/Y. TargetWord
returns the VRAM word in A16 and preserves X/Y. Window updates the resident
window, clobbering A/X. Nmi and Init preserve P/A/X/Y/D/DBR; Reset preserves
the same state. Nmi is called after FP CommitColumn inside the accepted
forced-blank commit, not from the pre-commit NMI stub.

Normal camera is `floor(Screen_PosX*7/5)`, with `down` mapped to zero. The
compiler checks the generated maximum `max(0,width_tiles*8-256)*7//5 <= 65535`;
it does not claim the result fits for arbitrary 16-bit input. Period zero is
rejected at generation and defensively handled at runtime. Multi-image source
columns repeat the 73-column cycle; scalar target atlases repeat their accepted
whole width. Presentation is clamped to committed residency: this intentionally
backpressures FP motion when the existing two-tile producer has not caught up.
That is `ACCEPTED_COMPAT_NORMAL_FP_SCREEN_X_7_OVER_5_V1`, not source timing exact.

Normal alone uses a 64-column BG3 map and 33-column resident window. This avoids
the wrap alias that a 32-column map would show at nonzero fine scroll. VRAM
page A remains $6800–$6BFF; page B is $6C00–$6FFF, with the BG2 map continuing
through $73FF. Fixed gameplay allocations are BG1 tiles $0000–$1FFF, BG3 tiles
$2000–$2BFF, BG2/frontpanel characters $3000–$3FFF, source OBJ $4000–$5FFF,
and BG1/BG3/BG2 maps at $6000/$6800/$6C00. Scene video uses tile banks
$0000/$2000 and maps $6000/$6400, outside this gameplay ownership. This is
source layout evidence, not emulator proof. HUD remains on BG3 page A.

WRAM $7FB784–$7FB79F follows water's exclusive end and precedes FP SlotStamp
$7FB800. Existing FP cache tables remain untouched. Channel 5 mode 2 writes
BG3HOFS: zero for rows 0–167, committed FP offset for 168–223. Only the accepted
NMI commit writes the table or channel-5 MMIO, after global HDMA disable and
the column fence. Main-thread Init/Reset clear only the first ten state bytes,
NEVER table bytes. A ready flag blocks publication after reset until a producer
request exists. Skipped NMIs reuse the old table; no frame-duration assumption
is used to make a main-thread rewrite safe.

## Explicit remaining completeness gap

This helper moves the existing FP band, not arbitrary FP artwork behind HUD.
Normal 3B/3C art occupies target rows 0–3; 4B/6B/6C also have art above row 21.
Those pixels remain in the materialized 28-row assets and are recorded as
`authored_rows_outside_streamed_band`, but the existing streamer does not
animate them. In particular, a blank boat FP band has no visible FP motion.
Resolving this needs a coordinated renderer/HUD ownership change. Do not mark
complete Normal FP source coverage from these compiler/helper passes. No
emulator, production assembly, concurrent pack or commit was run by this lane.
