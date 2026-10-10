# Fixed-bank mask compaction before OAM admission

The controlled player/effect pose has 146 occupied 8 by 8 source cells before
bank masking. That lower bound rejects an all-small layout, but does not reject
legal larger OBJ pieces. The offline global-color bank allocator can now defer
only its total OAM constraint while the source-context compiler attempts exact
32/8 compaction. Per-line 32-sprite and 34-tile constraints remain active during
bank assignment. The final compacted rectangles must satisfy all three limits;
failed compaction emits an explicit unadmitted status.

No source color, source pixel, palette index or bank identity changes during
compaction. A regression with 144 small cells rejects the original layout and
checks that exact merging produces legal final hardware geometry. The ordinary
allocator still enforces 128 OAM entries by default.

Global-color bank variables now share one identity across all scanlines rather
than allocating duplicate row variables with equality constraints. This is the
same mathematical restriction with a smaller solver model. Both MILP and CP-SAT
tests independently check source color and row-capacity identity.

The measured controlled HBreath plus He_ManB pose uses the original freespecial4
frame 6 caster and idle frame 11 effect. Source alpha is precomposited in RGB8,
including any actor overlap. It requires 293 opaque output RGB555 colors and
peaks at 69 per line. The initial unbalanced bank assignment compacts to 53 OAM
entries, 16 sprites and 34 tiles, but a matching primal/dual cache relaxation
proves a peak of at least 28 writes for that particular encoding. This exceeds
even a favorable 356-clock pure CGRAM transfer window.

A balanced assignment limiting each bank to 37 full-frame colors has a smaller
cache bound. The compact variable model produces 89 OAM entries, 22 sprites,
34 tiles and a greedy peak of 19 writes. Its independently validated fractional
bound is 16.2, requiring at least 17 integer writes for that encoding. Physical
slot scheduling and native execution for this concurrent pose are still open.
These are controlled poses, not AI synchronization or authored route proofs.

No color reduction is applied. The isolated native HBreath-only witness remains
valid. No gameplay configuration has been admitted with eight effect-only banks.
