# Physical word-count bounds and coherent solver hints

The row-slot solver now reports its objective bound and a conservative peak
commit-span lower bound for the specific model being searched. Local repair
uses a lexicographic weight larger than every possible aggregate row cost.
The full fixed-bank, fixed-word search has a 256-clock lower bound and a
536-clock complete-frame witness. The gap remains unresolved; a 501-clock
search returns UNKNOWN after 45 seconds.

Slot-value hints now agree with their physical-change hints and range
membership. Frozen repair rows remain constants; cumulative liveness hints
include their exact known writes. Fixed-multiset rank hints use distinct ranks
even when unused slots hold duplicate zero values. A regression pins every
hinted variable and still produces valid packet and pixel replay in both
fixed-multiset and free-residency modes. These hints never replace constraints.

An optional physical-write cap counts all changed slots, including prefetch
and live movement. Initial VBlank preload remains free. Local repairs enforce
the cap only through the repaired interval and its exit transfer, with an
explicit complete-frame nonclaim. Full-frame and local 21-write trials remain
UNKNOWN. A synthetic zero-write test preloads all required colors and retains
exact opaque-zero pixel identity.

The new generic physical relabeler exhausts 576 eligible bank permutations
and 256 whole-frame slot reflections per permutation: 147,456 combinations.
Each fixed OAM bank and pixel index is remapped consistently. Every emitted
packet, physical palette state and source pixel is independently replayed.
Geometry, transparency and math eligibility are unchanged.

None lowers this trace's 536-clock peak. Its peak 27 changed opaque slots
require at least 432 clocks even with ideal bank/slot packing. Thus relabeling
this residency trace cannot meet the native window. This quantified rejection
applies only to that trace and relabeling family; different residency, fixed
banks, words or geometry remain possible. No universal raster rejection or
native admission is claimed. No color reduction was applied.

Receipts: `docs/receipts/byor-motu-raster-physical-write-bounds.json` and its
gzip companion retain the complete reflected witness and bounded trials.
