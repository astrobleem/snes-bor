# Improved row-mask cache and free-alignment geometry

The resumed main-screen row-word bank search restores four dual certificates
and evaluates seven assignments in 252.156 seconds. Its best independently
validated fractional DMA span is 287.865658 clocks, improved from 304.336135.
The assignment still uses 128 legal 8x8 objects with 32 sprites and 32 tile
slivers per line. A fractional clock bound is insufficient for native admission.

The generic `raster_mask_retile.py` searches legal object rectangles at every
pixel alignment. A selected object keeps one fixed bank; its mask contains
only assigned source pixels. Independent replay verifies every source pixel's
bank, palette index and RGB555 operand, without changing the palette trace.
All rectangle rows count against sprite and tile limits, including transparent
padding. Optional 16x16 pieces use the legal 8/16 size pair and cost two tile
slivers on every row. Objects from different actors or banks cannot merge.
Resource limits may reserve capacity for other actors; this provides geometry
capacity only, never concurrent palette or layer admission.

The authored eight-pixel trial considers 13,474 rectangles for 60.046 seconds
and returns 121 objects, 31 sprites and 31 tile slivers. This is feasible,
not optimal. Its seven spare OAM entries and one spare sprite on the peak line
do not admit the representative player/enemy scene. Palette write timing and
pixel indices remain unchanged by this retiling.

HiGHS admits an integer cache with eighteen peak writes, thirty-six CGRAM data
bytes, 490 total noninitial writes and three-line maximum noninitial prefetch.
It proves the minimum total writes under that eighteen-write budget in 12.922
seconds, with zero integer constraint violation. It does not prove eighteen
is the minimum peak. The returned trace's optimistic bank-partition span is
408 clocks, above the isolated safe transfer window. Physical slot packing and
native execution have not been admitted.

The explicit linear range model now also supports minimizing peak transfer
span with CP-SAT or HiGHS. Its selected range cost is bounded by a common peak
variable; source cache variables remain integer unless explicitly relaxed.
The authored HiGHS trial returns UNKNOWN after 120.672 seconds. It supplies
neither a candidate nor an infeasibility certificate. The independent
dynamic-programming range optimizer is tested separately.

All 57,344 viewport pixels in the retained successful assignments and cache
replay against the current source PAK. Source alpha is exact BOR 4086 RGB8
SCREEN projected to RGB555. No color reduction or alpha adaptation is applied.
Twenty-one residency/range tests and five mask-retiling tests pass, including
bank separation, actor separation, complete transparent rectangle costs,
source math controls in schedule hashes and independent backend agreement.
The width audit has 9,825 labels and zero failures; all 17 protected file hashes
match. Full authored peak native presentation and MOTU completion remain open.
