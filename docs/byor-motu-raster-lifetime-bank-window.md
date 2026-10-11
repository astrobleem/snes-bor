# Constrain bank cost while moving lifetime prefetches

The lifetime slot allocator now supports a necessary bank transfer window in
addition to its physical range window. Each noninitial lifetime write is counted
in its fixed bank, including prefetches. The ideal bank partition is constrained
and independently replayed. Bank permutation is deliberately excluded from this
option so count labels retain their physical meaning.

For the authored 80-piece frame, both one-line and four-line timing neighborhoods
preserve the exclusive 337-clock bank gate. Their complete physical witnesses
remain at 536 clocks, with 19 peak writes and 402 noninitial writes. Thus the
unbounded-bank 504-clock witness and these 336-clock ideal-bank witnesses solve
different objectives. None meets the actual native transfer window.

Focused validation passes 34 tests, including strict 32/33-clock boundary checks
and independently replayed lifetime bank costs. All 17 protected files retain
their hashes. The width guard checks 9825 labels with no failures. No runtime
assembly changed and no color reduction was applied. General raster feasibility,
authored native raster presentation and MOTU completion remain open.
