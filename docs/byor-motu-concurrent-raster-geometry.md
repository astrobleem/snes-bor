# Concurrent raster geometry and authored alpha routing

The explicit source-height KnightBot/ShockBall/player/HBreath frame-14 pose has
a legal source-exact fixed-bank encoding. A generic rectangle cover changes
tile alignment and selects 8/16 OBJ squares before palette solving. It counts
the complete width and height of each object, including transparent rows.
Pixel ownership is independently checked against every visible source pixel.

The initial 16-grid geometry uses 117 objects and 48 tile slivers and fails the
34-sliver limit. Aligned covering gives 104 objects and 34 slivers; phase 2,2
gives 97 objects and 32 slivers. Phase 4,4 admits a 100-object, 30-sliver cover.
These covers initially omit palette masks. They are geometry constructions,
not universal minimums across all legal layouts.

Ordinary actors require at most 15 raw RGB555 words on any visible scanline
of this explicit pose. The compiler can therefore fix all alpha-zero actors
to one shared bank, checking combined row demand. It records the bank restriction
for later search tools. Alpha effects retain their separate exact operands.
An ADD encoding on the phase-4,4 cover uses 101 OAM entries, 17 sprites and 32
slivers and independently replays the composed source pixels. Its fixed-bank
cache lower bound is 34 writes, so this encoding fails the measured DMA budget.

Selected two-window controls from the critical 15-row integer witness can also
drive the joint compiler. Exact operands may be reselected while preserving
those controls. Generic subdivision permits each source pixel to use either
its large parent square or a legal 8-pixel child; OAM masks and per-line sprite
and tile limits remain enforced. The resulting full-pose encoding uses 114
objects, 19 sprites and 34 slivers. Its class-cache lower bound is 25.142857
writes, and its fixed-bank bound is 34.6. This encoding also fails the measured
transfer budget. Neither construction rejects other encodings or all raster.

The native fixture now supports authored main-screen OBJ math with BG1 on the
subscreen. It validates complete source-bound controls and independently
replays literal lower-bank pixels and eligible upper-bank math pixels against
the actual actor-free underlay. A source first-frame control passes four complete
fields with zero RGB555 mismatches, exact actual CGRAM/OAM, OBJ CHR and underlay VRAM,
and exact observed register traffic. It has no raster palette traffic, so it
does not establish peak-frame transfer feasibility or production ownership.

The existing isolated peak BR12 schedule is now verified with the full CGRAM
shadow observer: 204 source colors, 2751 opaque pixels, 107 OAM entries, 24
sprites/slivers, eight peak scheduled writes, a 216-clock observed transfer
span, exact actual OBJ CHR and 124 actual CGRAM checks with zero faults. Source
opaque-mask replay verifies all 2751 opaque pixels, including opaque black.
It executes the production
NMI service with a 2814-byte queue and preserves the source SCREEN result over
a black matte. The authored peak and actual concurrent scene are still open.

No color reduction, source resizing or production static-path change is applied.
No universal raster failure or MOTU completion is claimed.
