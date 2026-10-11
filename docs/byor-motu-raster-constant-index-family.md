# Constant word indices and quantified mapping limits

This optional family assigns each RGB555 operand word a constant opaque slot
inside its fixed bank. It preserves source pixels and source alpha controls;
it is more restrictive than general raster OBJ presentation. No color
reduction was applied.

Longer-interval subdivision search finds an 88-piece layout with 25 sprites and
34 tiles per line. Its validated cache lower bound remains 15.857142857 writes.
Bank 7 cannot assign all its word identities constant indices in 15 slots.
A bounded bank-move search finds a source-exact assignment with one piece moved
to bank 4. All eight conflict graphs then fit 15 slots. Its validated cache
lower bound is 15.933333333 writes.

The generic constant-index template compiler constructs a complete source-exact
layout, preserving transparent index zero, including opaque RGB555 zero through
nonzero indices. All CGRAM packets and source pixel identities are replayed.
Templates have no noninitial prefetch; their high transfer peaks are exploratory
starting points, not native admissions.

For the selected mapping, 150 noninitial palette transitions have both release
and deadline inside lines 129–135. Consequently at least one of those seven
lines requires 22 changed opaque words, even with unlimited initial preload and
lookahead. The necessary physical-bank prepared-DMA span for 22 opaque words is
352 clocks, above the measured 336-clock native window. Merely permuting its
slots or eligible banks cannot change that write-window density. The lifetime
solver independently reports INFEASIBLE at the 337-clock strict bound while
allowing prefetch and eligible bank/slot permutation.

That rejection applies to this mapping and these operand choices. It does not
reject all constant-index mappings or general raster presentation. The row
residency solver now optionally searches new constant word-index assignments
jointly with palette liveness. With a coherent template hint it finds another
complete physical witness at 1224 clocks; that witness is still above the native
window. The earlier unseeded bounded search returns UNKNOWN.

The more general mutable-index 87-piece search reaches 600 clocks with an
18-word cap. The 80-piece 552-clock witness remains the better physical result.
Two necessary bank-activity repairs at the strict 337-clock bound return
UNKNOWN, not infeasibility. The saved operand corpus has no alternative exact
word for any of the 2668 required pixels; a separate bounded canonical-operand
probe does not improve its distinct-word count. Wider operand policies remain
outside that conclusion.

The focused suite passes 56 tests; the width guard checks 9825 labels with zero
failures. All 17 protected files retain their saved hashes. No shared runtime
assembly changed. The receipt retains bounded metadata and compressed complete
schedules. Authored native raster, concurrent actor admission and MOTU gameplay
completion remain unproven.
