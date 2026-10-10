# Exact precomposited OBJ raster encoding

`--color-math precomposited` stores the exact final RGB555 result derived from
the source alpha operation and the specified underlay. All eight OBJ banks
carry ordinary colors; OBJ color math must be disabled. This gives a different
lossless raster candidate family from the four opaque/four additive routing.
The source canvas, colors, position and identity remain intact. It is a fixed
context proof; a moving underlay still requires a live compositor.

The joint solver accounts for all eight banks individually, including fixed
OAM bank assignment and 15 opaque slots per bank. Pool and hint identities
include color-math mode, preventing reuse of an incompatible additive pool.
Independent replay uses the declared mode. A 120-color single-line regression
uses all eight physical banks, preserves opaque black, and verifies every pixel.

The native sample renders two source-derived masks in banks 0 and 7 with OBJ
color math disabled. Three complete fields match all 57,344 expected pixels;
CGRAM RAM, CGRAM observer and OAM observer match exactly, with no OBJ overflow.
This proves sampled alpha routing, not full HBreath or raster execution.

With bank geometry relaxed and optimal initial residency/unbounded preloading,
the isolated peak requires at least 22.143 writes per line, hence at least 23
whole-color writes. The player/enemy/effect context requires at least 26.429,
hence at least 27. These are validated primal/dual pooled liveness bounds,
not adjacent-line set differences. The concurrent integer trial at 23 writes
has no candidate; its pinned rounding family does not prove universal failure.

For the prepared-DMA range family, C newly written colors need at least
P = ceil(C/15) banks. R ranges cross at least P-R transparent words and cost
24 clocks each. Granting ideal slots, the data-span subtraction and first-low
preload yields a necessary minimum commit span of 16*(C+P-2) clocks for C>0.
The bound is attained by dense endpoint packing in the independent partition
dynamic program for every count from 1 through 120. Scattered banks cannot
improve it. At most 22 colors fit the strict 356-clock window: 22 require 352,
23 require 368, and 27 require 432. Thus both precomposited contexts fail this
prepared-DMA mechanism even before fixed-bank geometry and runtime contention.
This does not reject other raster transfer mechanisms or the additive family.

The same count constraint now prunes the physical partition search before
its detailed range constraints. All 67 focused tests pass. The 17 protected
dirty files retain their recorded hashes. Production presentation and bank zero
are unchanged. Full native HBreath and MOTU Demo remain unproven. NO color
reduction applied.

[Native, pool and solver receipts](receipts/byor-motu-precomposited-raster.json).
