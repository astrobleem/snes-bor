# Authored peak fixed-bank integer cache

BR12 HBreath over the authored GUILE2 background has a source-exact fixed-bank
integer palette cache at 21 writes per line. Generic subdivision changes all
16-by-16 rectangles in the earlier encoding to legal 8-by-8 pieces. It preserves
every pixel's word and original bank and yields 101 objects, 20 peak sprites and
20 peak tile slivers. Subsequent bank assignment preserves encoding eligibility
and source pixels; each compiled OAM entry keeps one fixed bank.

The first balanced assignment has a validated fixed-bank cache LP bound of
21.45 and is infeasible at 21 writes. A cache-guided search with single-piece
bank changes finds 20.875. That bound independently checks with a 16-line
lookahead. The integer cache solver then returns a complete OPTIMAL feasibility
witness at 21 writes, 42 payload bytes and at most 16 lines of noninitial
prefetch. Initial slots are loaded once in VBlank. This solves fixed banks and
integer cache residency, not physical slot placement or transfer timing.

Independent replay against the current source PAK, actor-free authored underlay
and composed source SCREEN output matches all 256-by-224 RGB555 pixels. The
non-bypassed source opaque mask matches all 2668 drawn pixels with no duplicate
ownership. The remaining opaque source pixels equal the underlay and require
no draw. Source dimensions remain 110 by 90. No color reduction or alpha
adaptation is used.

The current cache's ideal transfer span peaks at 440 clocks. Exhaustively
checking all 576 eligible fixed bank permutations cannot reduce that peak.
The construction therefore does not meet the native transfer window. Prefetch
times and residency can still change; a 337-clock necessary-bound search returns
UNKNOWN after 120 seconds. Warm-started searches at 337 and 345 clocks also
return UNKNOWN. None of these outcomes rejects raster generally.

The receipt retains source and compiled hashes, the complete cache, geometry,
validated bounds and bounded search results. Twenty-three focused subdivision,
bank/cache and decomposition tests pass. The width audit has 9825 labels and
zero failures; all 17 protected tracked-file hashes match. Authored peak native
execution, concurrent actors and production/MOTU completion remain open.

An additional certified cache LP charges palette payload and destination-range
overhead together. For the next write-count-optimized assignment, its lower
bound is 380.918 clocks with a 21-write cap, or 359.650 clocks when writes are
unrestricted. It grants fractional residency, free initial residency and all
adjacent-bank bridges simultaneously, so these are optimistic bounds. Both
exceed the 344-clock constant-control native witness. This rejects that fixed
assignment for the measured prepared-DMA family, not other assignments,
encodings, transfer mechanisms or raster presentation generally.

The compiler tool now accepts `--objective dma-window`; the default write-count
objective is unchanged. Bounded one-piece and three-piece neighborhood searches
do not improve the clock bound. Source words, positions and bank eligibility
are independently replayed for every retained candidate. The supplemental
`byor-motu-fixed-bank-dma-cache-bound` receipt retains complete candidates and
verified primal/dual residuals. Twenty-five focused tests and the width audit
pass. No color reduction is applied.
