# Authored HBreath alpha: full-frame integer pool at fifteen writes

The source peak HBreath frame has 204 opaque RGB555 identities and a peak of
54 source colors on one scanline. Over the authored GUILE2 underlay, BOR 4086
SCREEN alpha produces 546 distinct final opaque RGB555 outputs. This isolated
pose uses the original effect at source size and authored alpha; it does not
establish an authored simultaneous gameplay state.

Independent replay of the existing source-exact fixed-bank cache trace yields
a full-frame class pool at twenty writes. The generic math/window solver can
now validate that pool and use its palette residency and controls as soft
CP-SAT hints. Exact seed operands remain available even when equivalent
coverage would otherwise replace them through dominance. Hints fix no
variables and do not grant a hardware admission. A focused test improves a
one-write hinted schedule to zero writes by changing both its modes and words.

The first eighteen-write search without a source hint returns UNKNOWN at
sixty seconds. With the verified twenty-write pool as a soft hint, an
eighteen-write search finds a **fifteen-write full-frame class-pool witness**
at the end of its 120-second solve. It is not proven optimal. All 2,668
non-underlay-equal source pixels replay exactly using the actual resident
RGB555 words, chosen shared scanline modes and compiled two-window descriptors.
The other 83 source pixels equal the underlay and are explicitly bypassed.
No source demand outside the interval is removed and no black/clipping pixel
relaxation is used. Both palette classes stay within sixty slots. The 55
effect rows use 46 full-add, four half-add, four subtract and one half-subtract
mode. An independent unbounded-budget hinted trial finds sixteen writes;
neither trial establishes a minimum.

The frame output SHA256 is
`4d1f01dece9f9a50ecde25d1efc3d9e3da2bc0ee3974fc2702650ee0d9cf2934`.
The source PAK SHA256 is
`2a35ebb9beea7388a6823205dad21e1a718da4b5f747ea09792c0a0e719aa2e0`.
The exact pool witness is retained in
`docs/receipts/byor-motu-authored-alpha-integer15-pool.json.gz`, with its
provenance and hashes in the adjacent JSON summary.

**This pool is not a fixed-bank hardware schedule.** Fifteen writes means
thirty logical palette bytes, not a measured CGRAM transfer cost. Individual
banks, physical slots, transfer ranges, register timing, background routing,
concurrent actors and native alpha remain admission requirements.

A separate greedy exact operand construction can assign fixed banks for this
same source frame. Its initial 137 small objects compact to 48 legal 8/32
objects, with peaks of sixteen sprites and 34 tile slivers. Compaction
independently preserves every source pixel's bank and slot. Emitted CHR/OAM
replay verifies 7,296 CHR bytes, 228 occupied cells and 138 unique tiles.
The CHR SHA256 is
`04bbc2a96a03bb58f531c0eb2ab1177b5eef4fc8c8b15e255de2ce10e3a25555`.
The OAM SHA256 is
`17eee74fa0cfab9c03e529c50a733b9fb75fbcb4cdd7b153a774ee6ecea2e7df`.

That construction's greedy trace peaks at 41 writes. Its fixed-word/bank
cache LP has independently validated lower bound 34; bank rebalancing lowers
the bound to about 20.2857143 while preserving geometry and pixel identities.
An optimum fractional fixed-geometry search with flexible pool operands still
reports 34 for the original assignment. Thus this legal geometry cannot
inherit the fifteen-write pool's transfer result. The coupled eighteen-write
search returns UNKNOWN at ninety seconds; its geometry-hinted variant returns
UNKNOWN at 120 seconds. Neither rejects raster generally.

The joint solver also supports `--fixed-rectangles`: preserve hinted rectangle
positions, pixel-to-rectangle ownership and original multiplicity while
selecting new fixed palette banks offline. A test moves a source-exact literal
rectangle to a math bank under changed scanline controls, keeping one object
and all pixels exact. The stricter `--fixed-geometry` still preserves its
original per-pixel bank ownership and can supply a fractional geometry bound.
Compaction, residency optimization and bank rebalancing bind modes/windows
into the compiled schedule hash when those controls are present.

The 8/16 compaction alternative uses 51 entries, seventeen sprites, 33 tile
slivers and 5,696 CHR bytes. A generic fewest-merges option retains finer
pieces while checking all hardware limits: three merges produce 128 entries,
25 sprites, 28 tile slivers and 4,384 CHR bytes. This last isolated layout
leaves no OAM entries for concurrent actors. Fixed-rectangle eighteen-write
trials on the 8/32, compact 8/16 and fine 8/16 layouts each return UNKNOWN at
120 seconds. They are not a universal raster rejection. Preferring already
resident words in the separate greedy constructor still produces a 44-write
trace, so that heuristic result is not admitted either.

Eighty-three focused tests pass. The width guard reports 9,825 labels and zero new,
baselined or stale violations. No production assembly or bank-0 code changes.
No color reduction is applied. Native authored-alpha timing and the MOTU Demo
remain unproven.
