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

## Concurrent layered context and contiguous IRQ replay

The generic solver now accepts per-piece palette eligibility, including equal
RGB555 colors residing in different banks on different actors. Its scene mask
model checks a shared OBSEL size mode, fixed banks, 128 OAM entries, 32 objects
and 34 slivers per line. Explicit HBreath/player and HBreath/player/Knightbot
pose searches reached solver time limits without an incumbent; **neither is
classified infeasible**. Source pose tools retain that distinction.

`source_scene_bg.py` adds the source GUILE2 background, panel and frontpanels,
He_ManB, Knightbot and peak HBreath, in an explicit camera-zero pose/tie order.
It composes 32-bit source SCREEN before RGB555 high-bit conversion. This is
a sampled pose, not certified script reachability, HUD/shadow/quake behavior
or an online compositor. The source dimensions of HBreath remain 110 by 90.
It yields 698 frame colors, at most 90 on a line. Scanlines 125 through 140
require 475 distinct colors: even 239 resident slots require 236 writes over
15 boundaries, forcing a peak of at least 16. Seven-write HDMA schedules fail
with both 175 and 239 slots. The unrestricted exact slot model finds a
16-write schedule with 239 slots, but does not establish contiguous transfer
destinations.

`contiguous_palette.py` independently finds an 18-slot contiguous burst
schedule with exact index reconstruction and no burst across reserved HUD
entries 112 through 127. The 16/17-slot heuristic failures are **not** hardware
infeasibility claims. Artifacts are
`out/byor-motu-bg-layered-contiguous18.json` and its adjacent directory.

`m4_bg_irq_native.py` replays that composed scene with a bank-1 IRQ body,
DMA channel 7, and four APU-port bytes per line on HDMA channel 0. A preparation
IRQ at dot 80 arms a masked-IRQ WAI wake at dot 239; this bounds phase variation
before the 36-byte palette burst. It passes all 57,344 rendered RGB555 pixels,
all 8,288 expected CGRAM register writes, 448 first/last timing samples with
zero sampled active-window writes, and reserved HUD palette identity. All
actors in this fixture are BG-composited; no OBJ is enabled. CHR is 42,944
bytes, palette restoration is 478 bytes per field, and schedule payload plus
destinations is 8,288 bytes. No production bank-0 code is added by this fixture.

The measured IRQ service is substantial: 249,982 master clocks for 224 visible
lines, with a peak of 1,118 clocks per service (about 70 percent of a complete
NTSC field, before production integration overhead). This cost must be
budgeted, not hidden. One host observer-budget timeout yielded within a field;
bounded retries completed exactly five fields without over-advancement. The
observer and pixel checks prove replay, **not** real TAD protocol, moving-scene
upload latency, production CPU capacity, combat or MOTU completion. Native
ROM, screenshot, observer and result remain under the artifact's `native/`
directory. No color reduction is applied.

The masked-IRQ wake behavior is documented by WDC in sections 2.24 and 7.13
of its [W65C816S datasheet](https://www.westerndesigncenter.com/wdc/documentation/w65c816s.pdf):
with I set, IRQ releases WAI and execution continues without another vector
entry. The fixture has a fixed accumulator/index ABI. A production consumer
must preserve the real caller's registers, widths, direct page and data bank,
and measure the resulting overhead; the fixture cost is not that admission.

## Lossless Mode 4 component presentation

`bg_components.py` preserves every RGB555 bit by splitting each channel into
disjoint high and low components. For the admitted Mode 4 configuration,
BG2 carries the least significant green and blue bits in four colors
`[0, 32, 1024, 1056]`; BG1 carries the remaining thirteen bits. Native additive
color math recombines them exactly, without rounding, saturation or color
reduction. Source SCREEN blending is computed in RGB8 before conversion and
decomposition. This does not substitute SNES addition for BOR SCREEN.
The exhaustive unit check reconstructs all 32,768 RGB555 colors.

The same layered peak pose has 698 final colors, 433 high-component colors
and at most 81 high-component colors per line. Its exact liveness scheduler
fits seven updates per line into 236 high-component CGRAM slots. Slots 0--3
hold BG2; slots 4--239 hold BG1; slots 240--255 remain reserved for HUD OBJ.
High CHR is 42,880 bytes, low CHR is 9,984 bytes at VRAM byte address 49,152,
and tilemaps occupy 61,440 and 63,488. A zero BG3 offset tilemap at 43,008
prevents unintended Mode 4 offset-per-tile behavior. No IRQ is enabled.

`m4_bg_components_native.py` verifies both br12 and adjacent br13 composed
poses. Each passes 57,344 exact RGB555 pixels, 6,272 CGRAM register events,
448 first/last transfer timing observations with zero active-window samples,
and unchanged low-component/HUD palette hashes. Five fields advance exactly
one at a time without observer timeout. Seven palette HDMA channels coexist
with four APU-port bytes on channel 0; this is a bus stress fixture, not the
production TAD protocol. VBlank restores 472 bytes and rearms channel 7 after
DMA. Code resides in fixture bank 1; production bank 0 is unchanged.

The br13 pose contains 697 final colors, 430 high-component colors and at
most 77 high-component colors per line. High/low CHR are 43,072/10,016 bytes;
the zero offset tilemap moves to 45,056. It also fits VRAM and seven updates.
Native receipts are in `byor-motu-component-bg-native.json`; bounded artifact
directories are `out/byor-motu-bg-components{,-next}-mode4/native/`.

Animation upload admission remains open. Only 62 source tile cells change
between these poses, but independently allocated high-component indices
change all 896 cells. This would require 57,344 high-plane bytes with a stable
tile-cell layout, plus 992 changed low-plane bytes, before maps/descriptors.
The 2,816-byte existing queue policy cannot admit that upload in one field.
It is an allocator problem, not proof that lossless BG animation is impossible.
`bg_component_group.py` tests the sufficient strategy of one palette schedule
for the union of both frames. All three two-bit decompositions are exactly
infeasible under that additional union restriction and seven writes per line.
Frame-specific schedules remain feasible; joint slot identity, hybrid OBJ
placement and real production upload timing still require investigation.

This proof contains no live compositor, source-reachable combat, actual HUD
drawing, moving actors, two-player certification or MOTU Demo completion.
No color reduction is applied.

## Foreign script frontend continuation

`script_ir_4086.py` parses source function bodies generically with pycparser,
preserves argument expressions, and resolves frame commands against each
model's supplied animation script library. It parses five libraries containing
27 functions, binds all 65 frame commands with exact arity, and retains five
inline script bodies. Function names select source ASTs, not handwritten
actor-specific implementations. Unsupported AST syntax fails explicitly.

The exact 4086 parser ignores variable/parameter declared types; numeric
spelling selects variant values. `ScriptVariant.h` stores decimals as DOUBLE,
and `ScriptVariant.c` copies assignment types, truncates integer division
toward zero, and produces VT_EMPTY on division by zero. Those facts are
recorded as compiler requirements, not replaced by fixed-point assumptions.
All authority paths refer to commit
`af23dc9c2316bb7853bb266ccf40986aa9765aeb`. Native script execution, API hooks,
inline wrapper semantics and numeric equivalence remain explicitly unbound.
No foreign profile is admitted through the historical builder.

`script_bytecode.py` now compiles all 27 source functions into 3,737 bytes of
generic variant instructions. Constants retain signed INTEGER32 and binary64
DECIMAL identity. Logical operands evaluate eagerly, as the exact 4086 parser
emits AND/OR after both expressions. A bounded host reference requires explicit
engine API hooks and fails when a hook or unproven numeric case is encountered.
It does not stand in for native execution.

`script_dispatch_4086.py` also derives per-model main wrappers from physical
directive order: animation-handle guards, frame guards and inline script bodies.
Seven model programs contain 7,101 instruction bytes and reference 80 immutable
animation handles. Handle identity is compiler-remapped globally; it remains
separate from gameplay ANI constants. The original default `nocmdcompatible=0`
is verified; a nonzero policy fails explicitly pending its wrapper lowering.
Host tests execute actual source bodies: left-facing spawn01 produces x-18,
unchanged z and altitude+93, both ShWave commands on one frame execute in order,
and a distinct default-model wrapper does not match the weapon model's handle.
The runtime must execute current and distinct default model scripts, retain the
local frame snapshot through script changes, and honor update_frame interruption
before later frame side effects. Native VM/API binding and numeric certification
remain open; these compiler artifacts are not a MOTU runtime candidate.

### Anchored palette identities and bounded tile caching

The no-effect background/player/enemy context contains 101 final RGB555
colors and 100 high-component colors. `bg_component_anchored.py` keeps those
100 component slots fixed and schedules the remaining 136 as a contiguous
suffix. The peak and adjacent poses need heuristic bursts of 11 and 13 colors,
respectively. These are successful schedules, not minimum-write claims.
Both replay natively with an ordinary dot-172 HIRQ and channel-7 DMA, while
channel 0 emits four APU-port bytes per line. They require no masked-IRQ WAI
preparation. Bank-1 fixed-ABI handlers pass every source pixel and CGRAM event,
all 448 first/last **CGDATA** samples (CGADD itself need not be in HBlank),
and low/HUD palette hashes. IRQ service totals are 138,208 and 145,284 master
clocks per visible field, with peaks 620 and 652; roughly 39--41 percent of a
complete NTSC field. Actual production ABI/interrupt phase and real TAD
protocol still need admission. Bounded observer retries handle one zero-field
host timeout on each receipt without over-advancement.

Anchoring cuts each plane's changing tile cells to exactly 62. A shared two-pose
cache compiled by `bg_component_cache.py` needs 46,848 high CHR bytes and
10,976 low CHR bytes. Low CHR starts at 49,152; the zero offset tilemap fits at
47,104. Both poses fit simultaneously. The compiled transition needs only
two tilemap DMA descriptors, each 512 bytes, plus 472 palette restore bytes;
there is no CHR upload for this cached transition. This fits the existing
2,816-byte queue policy by byte count, but **native animated cache replay and
production timing are not yet certified**. Initial preload, subsequent cache
refill, live source blending/moving actors and full MOTU remain open.

Optional previous-frame residency/slot-lock experiments retain explicit
optimization failure classifications; their failures do not reject the
successful contiguous path or all hardware renderers.

### Native cached transition proof

`m4_bg_component_animation.py` now preloads the shared two-pose cache and
alternates br12/br13 every field. Both use 13-color contiguous bursts. Four
successive displayed fields match their corresponding source canvases with
zero mismatches across all 57,344 pixels; the first two fields are forced-blank
preload. Two full CGRAM observer vectors match all 6,048 events each. Both
tilemap observers match all 1,024 transition bytes, and 896 first/last CGDATA
timing samples have zero unsafe writes. Measured transition service is
14,430/14,440 master clocks, beginning on line 225 and ending on line 235,
including 472 palette bytes, 1,024 VRAM bytes and descriptor setup.

The animated foreground instruction phase exposed 75 unsafe sampled writes
at dot 172, despite matching register identities. Moving the IRQ to dot 160
eliminates those misses and restores pixel identity. This retains the hardware
failure and corrects the fixture; static-dot-172 proof is not a general
production timing admission. Mesen frame skipping is disabled per process,
with `--donotsavesettings`; no user emulator settings are changed.

The passing ROM hash is
`366b4566fbce6b77696cedeb64689e5a508246095d7fac5c8a137c8b230d5b1e`.
Receipt: `byor-motu-component-animation-native.json`. Artifact root:
`out/byor-motu-bg-animation-native/`. This proves a bounded cached transition,
not original source cadence, an online SCREEN compositor, moving backgrounds,
two-player concurrency, subsequent cache refill or production integration.
No color reduction is applied.

### Native script module lowering

All seven source-derived animation programs lower to the existing slot VM,
with explicit `ACCEPTED_COMPAT_Q16_16` policy and generic name/arity API IDs.
The modules total 37,002 bytes; individually they range from 680 to 15,772
bytes and fit the 32 KiB module bound. Shared loading and actor attachment
remain unimplemented. Native APIs retain full arguments and source strings,
without selecting the earlier fixed-player fixture hooks.

A bounded Mesen probe on the unchanged original-BOR ROM executes the lowered
branch/call/parameter/return instructions: independent source calculations
produce 9, 7 and 97, matched natively with no fault and both guards intact.
This admits lowering only; MOTU engine APIs and gameplay remain unproven.
Fifteen focused host tests pass. Receipt: `byor-motu-script-native-lowering.json`.

Build 4086 decimal NEG falls through from DOUBLE sign negation to LONG
low-word negation in its union; unary POS does nothing for every variant.
The binary64 host reference now retains those behaviors, with signed overflow
refused. The native Q16 arithmetic remains an explicit adaptation and is
not called numeric source equivalence. No color reduction is applied.

### Typed native return boundary

Native CALL now stores complete source variants through code in bank 28.
Legacy IDs retain the existing INTEGER ABI. Seven bytes are freed in the
bank-0 VM window; runtime still has two bytes before NMI. Stable source
API IDs depend on name/arity, never a module requirement subset. Currently
only NULL is bound; other source APIs fail explicitly. Build 4086 system_NULL
clears its result to EMPTY. Native NULL returns all eight zero bytes.
Typed entity locals, pointer comparisons and other engine APIs remain open.

Fresh original-BOR regression ROM
`4cc7ba32b5503514fc7590e6b6155c09263364143d837c1947211b09115f83f3`
passes cold boot, Kula selection, first stage and static source presentation
without faults. Native branch/call/parameter/return checks pass, including
source NULL and both memory guards. MSU and PCM companions are hardlinks;
no PCM copies and no complete campaign reruns were made.

The ROM audit previously filtered cross-bank edges after recursively
following them with flat bank-0 indexing. A shifted layout exposed a false
bank-0 edge from that invalid walk. Its input is now bounded to the declared
bank-0 scope before decoding. Two tests prove foreign bytes cannot manufacture
a violation while a real unowned bank-0 call still fails. Full audit passes;
width guard has zero new violations. No baseline failures are suppressed.
Receipt: `byor-motu-typed-native-boundary.json`.

### Native frame locals and real VM storage ownership

Caller-installed self/frame/animnum/animhandle now return complete variants.
Self retains its supplied pointer token rather than aliasing the player.
Literal and existing dynamic string keys are read by identity; persistent
local writes and entity APIs remain unbound. An invalid caller context fails
explicitly. The native He_ManB breath wrapper returns before the command on
frame 3; frame 4 reaches and rejects unbound getentityproperty (ID 520).
With no context lease, getlocalvar fails at ID 521. Module bytes stay intact
in every case. These are dispatch/binding checks, not effect execution.

The former nominal 32 KiB code reservation overlapped scene-video staging
and telemetry at $7E6200..$7E9A9B. This did not corrupt the video-inactive
probe, but could not support larger modules concurrently with scene video.
Code now owns $7E9AA0..$7EDFFF (17,760 bytes), disjoint from video and the
fixed guard at $7EE000. The linker checks those actual intervals and packing
counts all module sections against the real bound. All seven MOTU modules
fit; the largest is 15,772 bytes. Code loading/actor attachment remain open.

Native typed locals, authored frame guards, the original BOR selector and
first-stage static presentation all pass on ROM
`5fcd6eb097d2f931e87096fae770988861e1671c02f7401d35a9436711a08aa4`.
Nineteen focused host tests and the ROM audit pass, with no new width errors.
The authored checks take 3/12/12 observed fields at the existing host's VM
checkpoint; this is not admission of 200 Hz source script timing. Runtime
code remains in bank 28 and the bank-0 NMI margin remains two bytes.
Receipt: `byor-motu-frame-locals-native.json`. No color reduction is applied.

### Native immutable script residency

All seven model programs link without removing functions or commands into
2,890 instruction records (23,120 ROM bytes), 12,640 bytes of compact RAM
metadata and 693 variant slots (5,544 bytes). Strings are interned jointly;
branch targets, function calls, slot operands and argument lists are relocated
by ABI role. B48R has a distinct identity and cannot enter the legacy B48S
loader accidentally. Metadata fits the checked 17,760-byte reservation;
slots fit the existing 8,192-byte arena. No module paging is required.

The generic native fetch kernel executes either the ordinary RAM path or
an explicitly enabled ROM descriptor. Instructions reserve bank 38 because
the persistent source host/worker owns banks 29 through 37. New kernel code
is in bank 28. The former fetch fault path abandoned a nested call/P frame;
fetch now returns an error to the dispatch loop, which unwinds its own frame.
The native out-of-range check proves VMERR_BAD_JUMP without a stale return.

Native He_ManB root 461 preserves the authored frame guard: frame 3 returns,
frame 4 reaches unbound getentityproperty, and a missing caller lease fails
getlocalvar. Disabling ROM fetch rejects B48R with VMERR_BAD_OPCODE; IP 2890
rejects with VMERR_BAD_JUMP. RAM metadata identity remains intact in all
five cases. Passing debug ROM:
`6abe6859d540e4f830eb0b5c6ddf84f7c1f58932a3dac89c5b578314d7b9fa03`.

The ordinary RAM path passes original BOR selector/first-stage static smoke
on `7d99b37a24051ddf0a79d16b69ee5e2a4c0dd5c1c8fa30c7ab4b6d3f99e566d9`.
Twenty-one focused host checks and the ROM audit pass. NMI margin remains
2 bytes. Metadata is still installed through bounded debug injection;
production loading, entity/spawn APIs, world attachment and source 200 Hz
cadence remain unproven. Receipt: `byor-motu-rom-script-native.json`.
No color reduction is applied.

### Generic typed entity read view

A model-independent read view binds the seven getentityproperty names used by
MOTU scripts: a, animationID, direction, health, playerindex, x and z. Altitude
and positions retain DECIMAL variants; other fields retain INTEGER variants.
The existing Q16.16 position representation remains ACCEPTED_COMPAT, not a
claim of binary64 numeric equivalence. Names follow the authority's ASCII
case-insensitive mapping; y and animnum aliases retain the same field/type.
EMPTY and null pointer handles return EMPTY. No legacy player-index alias is
used. A world owner must install a leased one-bank WRAM table with opaque
32-bit tokens; dead/stale handles, absent leases, bank spill, unknown properties
and malformed requested variants fail explicitly.

The native proof supplies two generic records, selects the second by token,
and reads all seven full variants, including signed/fractional coordinates.
A dynamically concatenated animationID key works. Five bounded native cases
pass: valid view, stale token, missing lease, bank spill and wrong variant tag.
This exposed a real boot initialization omission: old string fixtures manually
zeroed pool headers, but cold runtime boot did not. The boot owner now clears
all 64 refcount/length headers before VM use, outside bank 0.

Twenty-three focused host checks, the full ROM audit and original BOR
selector/first-stage static smoke pass on ROM
`6fd85a1463aaaf4c3ff0e8a1e50df47c5f722663f6287e237cbbc96b656d35af`.
Code remains in bank 28; the runtime still has two bytes before NMI. This is a
read-view binding proof with injected records, not a production world allocator,
source effect spawn proof, 200 Hz cadence proof or MOTU gameplay certification.
Receipt: `byor-motu-entity-read-native.json`. No color reduction is applied.

### Native source pointer keys and equality

The source-context variant kernel now supports STR+PTR, PTR+STR, PTR/EMPTY
EQ/NE and PTR truthiness. Build 4086 ScriptVariant.c formats pointers with #
and signed 32-bit LONG decimal. Four native cases cover zero, one, the signed
minimum and all bits set. Each proves both concatenation orders, self equality,
PTR versus EMPTY inequality, EMPTY equality, and pointer truthiness. PTR zero
remains a distinct type from EMPTY while being false in a condition. Opaque
world tokens replace host addresses; no legacy character-index alias is used.
Ordered pointers and other mixed variants still fail explicitly. Source caller
leases enable the extension; legacy paths retain their prior behavior. All new
logic resides in bank 28, with thin redirects reducing bank-0 VM bytes.

Twenty-four focused host checks and the full ROM audit pass. The NMI margin
remains two bytes. Native pointer proof ROM:
`a4e5591cc56a4baab02a03439458b87e57680b810fd047f66e54840b368464c4`.
Persistent script locals, world allocation, spawning and MOTU gameplay remain
unbound. Receipt: `byor-motu-pointer-native.json`.

The old static smoke sampled a sticky last-error byte after twelve fields.
An observed $27 cannot establish a hard admission failure by itself: native
source authority also uses it for pending owned DMA/staging and palette/block
allocation deferrals. The strengthened bounded observer records post-Emit
source OAM publication, deferrals by actor record and all other errors.
Kula selector/first-stage entry and observed player source OAM publication pass
in both images. A later in-flight lease can clear its presentable snapshot
without erasing that observed earlier publication. The additional all-actor
recovery check FAILS: record 32 has not published within the bounded window.
A byte-checked previous-commit control reproduces this failure. Control ranges
restore the VM window, bank 28 and the relocated G13 Div32 call operand together.
All remaining ROM bytes are identical; source visual runtime bytes are unchanged.
This broader concurrent actor result remains FAIL. Its cause and relevance to
production foreign-world integration remain open. No full original campaign
was rerun. No color reduction is applied.

### Authored caller binding and measured interpreter cost

With a leased generic caller view, the actual He_ManB breath wrapper returns
on frame 3 and reaches clearspawnentry (stable generic ID 518) on frame 4.
Missing caller context still rejects getlocalvar; wrong external format and
out-of-range ROM fetch still reject precisely. All five native cases pass;
resident metadata hashes remain intact. This does not execute an effect spawn.

The bounded observer exposed why arbitrary paused-field injection is unsafe:
a CPU may already be inside the previous VM invocation. Injection now uses a
Lua debugger break and verifies bank 0 PC Vm_Run+3, after PHP/REP and before
the first VmState read. Clock observation starts at that exact boundary.
Observed no-command wrapper: 24 instructions, 151,152 master clocks.
Observed frame-4 path to the unbound spawn boundary: 41 instructions, 297,200
master clocks. Execution windows include intervening runtime work and exclude
host checkpoint waiting; entry PHP/REP and terminal return are outside them.
Passing patched script-payload ROM:
`477d6b87d23219af7c1734926d127e676c1f2b785a642b6e4fc21395d5ff326d`.

Both intervals exceed a single 200 Hz time quantum (107,386 NTSC or 106,407
PAL master clocks). Source animation callbacks occur on frame updates rather
than every physics tick, so this is neither whole-workload infeasibility nor
200 Hz timing admission. Offline frame dispatch and real event-burst/owner
integration remain required. Source spawning, persistent locals, production
loading and MOTU gameplay remain unbound. The seven current property bindings
cover the C helper libraries; the authored inline bodies additionally require
maxhealth, whose generic binding remains to be added. Receipt:
`byor-motu-authored-script-cost.json`. No color reduction is applied.

### Inline maxhealth binding and versioned entity view

The authored inline bodies additionally read maxhealth. Build 4086 returns
VT_INTEGER ent->modeldata.health, distinct from the current ent->health.
The generic view now contains eight full variants in an 80-byte V2 record;
magic B48B explicitly rejects old B48D descriptors rather than interpreting
old strides silently. The native proof reads maxhealth 4096 and health 271
independently, preserving their full integer width. All eight properties,
dynamic animationID key, null handle and five negative cases pass. Six native
cases use a verified pre-state-read VM injection checkpoint. World allocation
and source spawning remain unbound; no gameplay certification is implied.

Twenty-four focused host checks and the full ROM audit pass on ROM
`7fee55439695ff3195cd8c550dc8de05be97e689602f1f98023ffe28b7931f82`.
The NMI margin remains two bytes. The previously observed inherited all-actor
static recovery failure remains open, not reclassified as PASS. Receipt:
`byor-motu-entity-read-native-v2.json`. No color reduction is applied.

### Offline frame routing and exported VM roots

The generic frame compiler routes 576 of 687 authored scripted-model frames
to an explicit empty entry. It preserves all source-order inline bodies and
their frame guards, including the possibility of an inline assignment to the
local frame snapshot. Non-inline command frames receive separate exported
roots. Mutually exclusive root temporaries share an arena; helper temporaries
remain separate, and exported-mode locals are cleared on each invocation.
Authored animation scripts with their own main are explicitly unsupported by
this optimization rather than discarded. The legacy single-root lowering path
reproduces both previous linked instruction and metadata hashes exactly.

All 1,374 frame/facing host comparisons preserve ordered engine effects.
The linked output uses 3,127 instructions, 670 slots and 12,400 metadata bytes.
A 2,678-byte ROM dispatch table includes global frame counts, checked identities,
empty sentinels, payload CRC and paired instruction/metadata CRCs. Instructions
and dispatch together occupy 27,694 bytes of the reserved 32 KiB ROM bank.
Invalid caller context or frame identity must fail before an empty route skips
the VM; the host contract checks this. Production dispatch remains unbound.

The native frame-4 root reaches the same unbound clearspawnentry boundary with
32 instructions and 210,134 observed master clocks, versus 41 instructions and
290,732 clocks in a repeated baseline using the same corrected observer. All
four specialized-entry cases and five baseline cases pass. The first attempt
missed its initial timing span because the debugger checkpoint's exec callback
had already fired. Observation now starts at the next instruction, after the
first status LDA, and records every case. Failed and corrected reports are
retained. These spans include intervening runtime work and exclude host waiting;
they are partial callbacks, not source spawning or 200 Hz workload admission.
Twenty-three focused script tests pass. Receipt: `byor-motu-frame-dispatch.json`.
No color reduction is applied.

### Source model identity, loaded-state lookup and result ownership

The compiler now derives a generic B4MR model registry from the source cache
declarations. The pinned engine uses those cache names as model identity and
`findmodel` searches only loaded models after case folding. The 16-record MOTU
table is 1,048 bytes; its immutable records include source health and alpha.
`init_model` uses calloc and supplies no nonzero health/alpha initializer:
undeclared effect health is zero, while He_Man/He_ManB are 150, Skeletor 400 and
Knightbot 70. This table does not load models or allocate entities.

Native `setspawnentry("name", value)` now resolves this table against a separate
loaded-model bitmap and sets a portable model identity in the spawn request.
Case-insensitive names, unloaded and missing models, and a missing table lease
pass bounded native checks. Unknown/unloaded names produce a null identity and
still return the complete INTEGER 1, as the source engine does. Other spawn
properties remain explicitly unbound. Cold boot clears the table lease and
loaded bitmap; the proof's checked leases are injected, not a production loader.

The eleven-case authored frame proof passes on the rebuilt image. The breath
callback reaches the next unbound API, `spawn()`, after 48 VM instructions and
422,320 observed master clocks including routing and intervening runtime work.
The native return observer captures the name setter's INTEGER 1 before later
property calls overwrite the shared result buffer. This is not complete spawn
execution or source cadence certification.

Typed native results also release an owned dynamic string before overwriting
their destination. An isolated seven-byte no-release control exhausts the
64-object pool after 64 successful lookups; the fixed image completes 80 and
leaves zero live strings. Returning a STR remains unbound until its separate
retain/borrow ownership is implemented. The full ROM audit and focused host
tests pass. The inherited concurrent static recovery failure remains open.
Receipt: `byor-motu-model-name-native.json`. No color reduction is applied.

### Definite local initialization in exported scripts

The exported-root lowering now uses checked CFG must-analysis to initialize
only locals that can be read before a source STORE or parameter installation.
Source declarations already initialize their slots; repeating those stores in
the prologue was redundant. Self-referential initializers still receive EMPTY,
including when a different exported root previously used the shared arena.
Generated non-inline handlers declare frame/animhandle only when their command
expressions actually reference them. Inline bodies remain unchanged.

All 1,374 source frame/facing comparisons and 24 focused script tests pass.
The output drops to 2,568 instructions, 616 slots and 11,812 metadata bytes.
All eleven native dispatch cases pass with the optimized ROM payload. The
partial authored frame-4 callback now executes 19 VM instructions in 151,372
observed master clocks including dispatch, versus 32 instructions and 234,092
clocks before this optimization. It still stops at unbound clearspawnentry;
spawning and 200 Hz workload admission are not proven. The legacy single-root
linked instruction and metadata hashes remain unchanged. Receipt:
`byor-motu-frame-dispatch-optimized.json`. No color reduction is applied.

### Native shared spawn-request reset and corrected fixture ownership

The generic clearspawnentry binding implements the pinned engine's shared
request reset and complete EMPTY return. The portable request uses explicit
null model IDs and three signed 32-bit index fields set to -1; remaining
supported fields default to zero. Model-name assignment, other spawn-entry
properties and smartspawn/world allocation remain unbound and fail explicitly.
The authored callback now passes clearspawnentry and stops at setspawnentry
(stable API ID 529). It executes 22 VM instructions in 173,496 observed master
clocks including dispatch. No entity has been spawned by this proof.

An expanded seeded test exposed an invalid earlier fixture ownership claim:
the frontpanel has 257 stamp bytes at $7FB800, so its final byte is $7FB900.
The old fixture started on that owned byte. Fixture placement now derives the
exclusive end from actual source constants and aligns after it at $7FB920.
An ownership regression check rejects an oversized fixture reservation.
Earlier injected read-view/script receipts do not prove absence of interference
with that final stamp. They are superseded for fixture ownership by the corrected
six-case entity read proof and eleven-case seeded spawn-reset proof. The earlier
SA-1 mutation-fence halt is retained as a failed attempt; no causal claim beyond
the demonstrated fixture overlap is made.

All corrected native cases pass, including all eight entity properties, dynamic
string property lookup, EMPTY/null handling and negative leases/identities.
Only an actually executed clear mutates the seeded request; empty/invalid jobs
leave it untouched. Full ROM audit, 24 script tests and the fixture ownership
check pass. Bank 0 still has two bytes free. Receipt:
`byor-motu-clearspawn-native.json`. The inherited concurrent static recovery
failure remains open. No color reduction is applied.

### Native checked frame routing

The opt-in native dispatcher consumes one submitted callback and validates the
installed caller lease, self type, frame/animation-handle types and ranges,
ROM instruction lease, immutable table header, descriptor bounds and selected
entry IP before executing or skipping. An empty route returns DONE without
fetching a VM instruction. A four-byte JSL replaces the existing four-byte
status load; new routines and scratch live outside bank 0. Cold boot disables
the table and job leases. The ordinary path retains legacy VM status behavior.
Production world ownership and the B48R/CRC loader are still unbound; the native
proof installs an externally checked, immutable ROM table lease.

Eleven native cases pass: empty frame, authored spawn callback up to its unbound
API, missing context, invalid frame, missing ROM lease, invalid program, missing
table lease, ROM bank spill, header/count mismatch, zero handle and a busy
yielded interpreter. Every empty/invalid case fetches zero VM instructions and
each job is consumed once. The empty dispatch takes 12,332 observed master
clocks; the partial frame-4 path including dispatch takes 234,092 clocks and
32 VM instructions. These are bounded injected-context measurements, not full
spawn or workload certification. Receipt: `byor-motu-frame-dispatch-native.json`.

The full ROM audit and 23 focused script tests pass. The bounded original-BOR
selector/first-stage/player-source-publication checks pass on the new image,
but the stronger concurrent actor recovery check still FAILS as before. That
result is retained explicitly; it is not a passing gameplay regression gate.
No color reduction is applied.

### Checked source entity property mutations

Generic source `changeentityproperty` now binds position, direction, x/z/a/y
and health, with full EMPTY results. A separate authoritative mutation lease is
required in addition to the V2 entity identity/read lease. No writes to the
original-BOR actor layout are used. The production world owner and allocator
remain unbound; these are bounded injected-owner primitive proofs.

Thirteen native cases pass: full/partial position writes, independent numeric
conversion failure, signed truncation, dynamic/case-folded property names,
Q16 coordinate endpoints, read-only and stale rejection, null no-op, unsupported
property rejection, coordinate range rejection and malformed record tag. Fields
not named by the call remain byte-identical. Non-numeric position components
remain unchanged independently, as the pinned source does. Integers outside the
signed Q16 coordinate range fault explicitly instead of wrapping. Coordinates
remain ACCEPTED_COMPAT_Q16_16, not a binary64 equivalence claim.

The shared checked entity lookup passes the existing six-case typed read-view
regression. The first mutation build failed because Poppy encoded a ROM
`label+1,x` expression with bank zero; incrementing X and using the plain ROM
label fixes the emitted operand. Failed attempts and bounded rejection traces
are retained. The full ROM audit and 24 script tests pass; bank 0 still has two
bytes free and all 17 protected tracked files are unchanged. The inherited
concurrent static recovery failure remains open. Receipt:
`byor-motu-property-mutation-native.json`. No color reduction is applied.

### Source animation numbers and checked effect birth

A pinned engine authority snapshot now supplies animation enum values, loader
aliases, default arrays and the exact global expansion order. MOTU maxfollows
10 produces 168 engine animation numbers: follow5/follow6 are 162/163. Loader
waiting selects ANI_SELECT (59), while select selects ANI_PICK (25). These
engine animation numbers are distinct from the compiler's immutable frame
handles. The authored breath caller now installs engine animation ID 44 and
compiler frame handle 36. Compiler instruction/metadata encodings are unchanged
by that additional identity metadata.

Generic SOURCE_NONE_IDLE_BIRTH templates derive health, alpha, lifespan, initial
animation/frame identity, delay and physics flags from source. Seven models are
admitted to this initial birth capability. A model requiring type-specific
initial actions, scripts, sound/frame effects or environment queries fails
explicitly until that initialization is bound. This is birth initialization
admission, not a claim that all model behavior, collisions or presentation exist.

An opt-in native allocator uses a separately leased physical BW-RAM region
$41:4000..$41:87ff: 128 80-byte property records and 128 64-byte birth sidecars.
Stable pool tokens survive slot reuse. The allocator initializes all supported
state before publishing alive=1; it never aliases original-BOR actor indices.
Read/mutation access to these BW-RAM records requires that exclusive pool owner.
Cold boot leaves the owner disabled. Production pool startup remains unbound.

The eleven-case authored callback proof passes. The source command clears the
request, resolves HBreath, allocates it, applies position/direction and returns
normally. Its born coordinates are (62,220,93) for the left-facing caller;
model/default identity 5, idle handle 47, frame zero, alpha 1 and 300-tick lifespan
are retained. At time 48 it has nextanim 54 and nextthink/nextmove 49. The observer
captures a complete stable pool PTR at spawn return. The complete callback takes
64 VM instructions and 639,634 measured master clocks, including routing and
intervening runtime work. This does not prove a 200-Hz workload budget.

Ten separate native allocation cases pass: birth, absent level, absent owner,
missing model, unadmitted initializer, full pool, invalid base/count/template and
zero free-slot token. Failure paths leave both pool arrays unchanged; absent
level/model and full pool return EMPTY. Fixtures wait for twelve legacy startup
fields and require complete pool writeback before granting their injected owner.
An earlier skipped-frame fixture failed ownership before that startup boundary;
its result is retained without a more specific causal claim.

The full ROM audit and 30 focused compiler tests pass. Bank 0 still has two bytes
free and all 17 protected tracked files are unchanged. Live source world ticking,
additional API policies, selector/combat/Demo completion and effect presentation
are still unbound. The inherited concurrent static recovery failure remains open.
Receipt: `byor-motu-world-birth-native.json`. No color reduction is applied.

### Persistent entity script variables

Pinned Script_Copy and Varlist authority establishes that variables belong to
an entity script instance. Current/default animation callbacks share that list;
model identity is not the namespace. Names are case-sensitive. Cleanup empties
values while retaining the named nodes, including installed frame locals.

An opt-in native store uses the separate $41:8800..$41:e7ff owner lease with
384 named 64-byte records. It supports full EMPTY/INTEGER/DECIMAL/PTR variants.
Stored STR values, indexed keys and oversized names fail explicitly. The
instance owner is checked against the original caller snapshot, so changing
the installed self variable does not change ownership of the variable list.
Production callback installation, slot retirement/reuse and world startup are
still unbound; fixtures install a checked namespace externally.

Twelve native cases pass: dynamic names, persistence, another entity, cleanup,
overwriting self, empty name, unsupported stored string/indexed key, absent
owner, incorrect instance, oversized key and full store. Complete namespace
bytes are checked against the source oracle; other owners/scopes are unchanged.
Two variable ownership tests and two source-dispatch tests pass. The ROM audit
passes with zero new width violations, and all 17 protected files are unchanged.
The inherited static concurrent recovery failure remains open. Receipt:
`byor-motu-script-variables-native.json`. No color reduction is applied.

### Installed animation-local lifecycle

The bank-28 frame gateway now accepts an opt-in owner BEGIN/END protocol.
BEGIN validates the caller and animation instance, preflights capacity for
all four installed names before changing the namespace, and installs the
original self/frame/animnum/animhandle snapshots. Both model programs can share
that boundary. END requires a terminal interpreter and the same original
snapshot; it empties only the four installed values, retains their names and
other persistent variables, and expires the source context. Busy/reentrant,
wrong-scope, stale-snapshot and insufficient-capacity requests fail explicitly.
Cold boot disables the protocol. Live world traversal remains unbound.

Eleven native lifecycle cases and the twelve-case variable-store regression
pass. Complete namespace bytes, caller-context lifetime and consumed requests
are checked. The first attempt exposed incorrect literal/heap discrimination
after adding internal ROM names; that bug is corrected and its failed attempt
is retained. Three source ownership/lifecycle tests and the full ROM audit pass.
All 17 protected files remain unchanged; bank 0 still has two bytes free.
Concurrent static recovery remains FAIL in the fresh bounded smoke, with queue,
cache and CPU diagnostics retained. Receipt:
`byor-motu-callback-lifecycle-native.json`. No color reduction is applied.
