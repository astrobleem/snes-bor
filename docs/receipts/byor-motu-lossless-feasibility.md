# M4 lossless presentation investigation

Status: **IN_PROGRESS**. This is a feasibility receipt, not MOTU gameplay
certification. No color reduction has been applied. TMNT has not been started.
The previously pending presentation decision is superseded by Chad's policy:
lossless raster OBJ first, then lossless BG/hybrid if raster reaches a measured
limit. Neither ordinary engineering work nor a heuristic failure is a rejection.

## Source and alpha authority

PAK SHA-256: `2a35ebb9beea7388a6823205dad21e1a718da4b5f747ea09792c0a0e719aa2e0`.
Peak HBreath source frame: `data/chars/he-man/fx/br12.png`, SHA-256
`03641355e8c352b47593d481e81f66573766bf0c9d9c1f60c00f9663c02123e7`.
It is 110 by 90 pixels with 2,751 opaque pixels, 204 opaque RGB555 identities,
54 colors on the busiest line and at most 32 new colors relative to the previous
line. The last figure is not the scheduled write count.

The [Build 4086 port's engine identification](https://github.com/MiSTerOrganize/MiSTer_OpenBOR_4086)
points to upstream commit `af23dc9c2316bb7853bb266ccf40986aa9765aeb`.
That exact commit is present in the local full upstream history. Its
[model loader](https://github.com/DCurrent/openbor/blob/af23dc9c2316bb7853bb266ccf40986aa9765aeb/engine/openbor.c)
reads alpha directly, and its
[pixel-format implementation](https://github.com/DCurrent/openbor/blob/af23dc9c2316bb7853bb266ccf40986aa9765aeb/engine/source/gamelib/pixelformat.c)
selects the first blend-table function for alpha 1: screen blending. The 32-bit
table path blends each RGB8 channel as `255 - ((255-s)*(255-d)//255)`.
Alpha 6 is average blending. The context probes use screen blending before
the named RGB8-high-bits-to-RGB555 hardware adapter. They do not render opaque.

SNES addition is not screen blending. Exhaustive channel-pair comparison finds
up to eight RGB555 channel steps of error for saturated addition and sixteen
for average blending relative to this source operation. Neither has been
classified ACCEPTED_COMPAT or admitted for gameplay.

## Raster OBJ result

`raster_palette.py` models fixed bank assignments, per-bank row color unions,
legal object dimensions, physical OAM rectangles and line tile slivers. It
also supports disjoint color masks in overlapping legal objects. Each source
pixel is retained in exactly one mask. Its strict residency MILP bounds total
newly resident identities per line; its separate heuristic retains live slots
and preloads future colors. A solver timeout with a verified incumbent is a
feasible assignment, not an optimum or an infeasibility result.

The peak frame has a valid eight-bank assignment with 57 8-by-8 objects,
at most ten sprites and ten tile slivers per line. Those dimensions require a
different global OBSEL mode from production and are not admitted for concurrent
production actors. Restricting a single object per such cell to banks 4–7 is
MILP-infeasible for that fixed grid, not a universal geometry rejection.

Disjoint masks solve fixed assignment in production's 16-by-32 small-object
geometry using banks 4–7: 20 objects, ten sprites and twenty tile slivers per
line. Pixel reconstruction is exact. The current heuristic schedule peaks at
37 color writes / 74 CGRAM data bytes, averaging 9.2584 writes per intervening
line. It is not an optimum.

There is also a geometry-independent bandwidth lower bound for the four
banks eligible for OBJ color math. Adjacent source lines require 53 and 51
colors, with a union of 85. Sixty resident opaque slots therefore require at
least 25 new colors / 50 data bytes between those lines even with ideal
preloading. In the inspected PPU implementation, safe CGRAM access extends
from HClock 1096 through the line boundary to HClock 88: at most 356 master
clocks on a normal line. DMA costs eight clocks per byte, so this minimum
already costs 400 clocks, before addresses, setup, synchronization or other
actors. CPU writes and HDMA do not improve the per-byte lower bound.

The bounded native polling probe verifies eight clocks per successive DMA
byte and observes the 50-byte transfer crossing into active display. This
rejects the four-bank OBJ color-math path. It does not reject raw eight-bank
opaque color scheduling, an exotic active-display CGRAM exploit, or the
authorized software-composited BG/hybrid approach. Source screen alpha is
not directly implemented by SNES OBJ color math in any case.

## Isolated BG proofs

The generic context compiler blends the source-sized effect over an explicitly
selected source background and solves its RGB555 slot liveness offline.
Contexts are samples, not certified stage compositions: panel, frontpanel,
actors, moving camera and HUD graphics are not drawn in these samples.

| Sample | Full-frame colors | Peak line colors | BG slots available | Peak scheduled writes | CHR bytes after deduplication |
| --- | ---: | ---: | ---: | ---: | ---: |
| Jungle background | 210 | 51 | 111 | 7 | 22,016 |
| Gray background | 365 | 78 | 175 | 7 | 31,936 |

Both use a 256-by-224 sample viewport and the unchanged 110-by-90 effect at
(80,90). This placement is an explicit probe input, not an authored spawn
placement claim. The gray sample with 175 slots is provably unschedulable at
three writes per line but has a verified seven-write schedule. The gray sample
with 111 slots is infeasible at seven writes; that reservation is not the
authored second-stage resource configuration and is not a BG rejection.

Seven direct HDMA channels use mode 3 at CGADD: duplicate address, then low
and high color bytes. Each channel changes one arbitrary palette identity
per line. Channel 0 concurrently transfers four bytes to APU ports as a
service-path bus stress fixture. This is not a production SPC/audio proof.
The eight channels transfer 32 register bytes on a full update line; the seven
palette changes themselves represent 14 CGRAM data bytes. The measured first
through last CGRAM register-write span is 216 clocks. With channel 0 active,
the sampled writes start near HClock 1168–1172 and finish near the next line's
HClock 16–24, inside the safe access interval.

Both native proofs advance exactly three frames, compare all 57,344 displayed
RGB555 pixels programmatically with the independently composed source context,
and match all 6,272 observed CGADD/CGDATA register writes against compiled
descriptors. Reserved entries 112–191 retain their initial hash. A screenshot
is retained alongside the traces, not used alone as evidence. Each proof uses
2,048 tilemap bytes and 8,968 HDMA-table bytes. Presentation code is in fixture
bank 1; its separate bank-0 reset trampoline is not a production-bank edit.

Replay now explicitly restores owned initial palette slots every VBlank:
222 bytes for the jungle reservation, 350 for gray. The observer verifies those
bytes independently. The queue-style DMA uses channel 7, then its HDMA mode,
destination and table source are restored before the next field. Reserved
actor/HUD entries are untouched by these transfers. This ongoing per-field
cost must be included in production admission even when the scene is unchanged.

Reproducible artifacts are under `out/byor-motu-bg-gray-seven/` and
`out/byor-motu-bg-jungle-layers/`, with native ROM, screenshot, register observer,
timing samples and result JSON under each `native/` directory. The raw HBlank
probe is under `out/byor-motu-cgram-probe/`. These are bounded experiments,
not a final MOTU candidate.

## Required continuation

Static production presentation has not been redirected into these tools.
There is no gameplay raster/BG capability consumer yet. The intended generic
capability boundary is static OBJ, schedulable raster OBJ, or a separately
admitted lossless BG/hybrid compositor; actor names must not choose code paths.
Unscheduled frames and unresolved alpha/layer semantics must fail explicitly.

The BG proofs leave ordinary engineering work: concurrent source actor/effect
admission, foreground/depth ordering, runtime context composition and palette
planning, visual-upload latency, channel-7 restoration after queued NMI DMA,
and production TAD/MSU interaction. The source-profile/script, selector,
combat, route and completion work also remains. No BG impossibility, MOTU boot,
full traversal or completion is claimed.

The width guard is now repaired at all 132 new sites with explicit assertions,
without adding baseline entries. Before/after Poppy output is byte-identical
(884,906 bytes, SHA-256
`dc7b4ff89dd65e502b0dd77d85e84cdf86404d2951e3246741e0cda30a4be4ae`).
All ROM audits pass; 183 older baselined sites remain reported. See
[the annotation receipt](byor-motu-width-repair.json). Production bank 0 gains
zero bytes and still has two bytes free before NMI. All 17 protected tracked
files retain their preserved hashes. No PCM was copied.

## Source timing and baseline production census

`tools/bor_compile/dialect_4086.py` now produces a separate, explicitly selected
4086 source IR. It cites loader commit
`af23dc9c2316bb7853bb266ccf40986aa9765aeb`; this does not authenticate the engine
used to author the archive. AT copies and clears the pending spawn structure,
including a zero initialized entry. Demo therefore contains **35** authored
queue entries (22 spawns and one empty entry), rather than the strict earlier
survey's 34. Reset directives replace pending entries. Source modifiers,
scripts and declarations remain retained; no SNES queue or script consumer is
claimed by this IR.

Frame delay persists across ANIM, while offset and collision bounds reset.
SOUND is consumed by one FRAME. The He_ManB breath event is at frame index 4,
tick 48 on the 200 Hz source clock (24 centiseconds); its uninterrupted
animation lasts 312 ticks. Skeletor's rise declares 16 geyser calls at ticks
208, 258, 308, 358, 408 and 456. These are event declarations, not yet a
certified simultaneous visibility bound: lifespan countdown, freeze, hit
removal, and interruption semantics still matter. Four focused IR tests pass.
The reproducible full IR is `out/byor-motu-4086-ir.json`.

The existing persistent original-BOR Easy candidate (ROM SHA-256
`46d7e21f23b81653ba626610d0c2c462c1fea2a858af02423b625705cf8a8e2a`)
passed a fresh-process cold boot, Kula selector and first-stage smoke, with
zero source visual admission fault. `tools/verify/m4_runtime_bus.py` records
four bounded production fields in `out/byor-motu-static-bus/result.json`.
All sampled queued DMA uses channel 7; HDMA enable returns to zero. Sampled
VRAM traffic is 0, 786, 0 and 64 register bytes per field; no sampled CGRAM
data writes. The longest sampled forced-blank commit lasts 21,330 master
clocks and releases near scanline 241. This is a baseline census, **not** a
worst-case transfer budget, production audio stress proof or admission of the
new raster schedule. No complete campaign was rerun.
