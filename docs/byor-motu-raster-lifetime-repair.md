# Physical packing by palette lifetime

Assigning physical slots separately to color lifetimes improves the authored
80-piece frame from the previous valid 552-clock physical witness to 536 clocks.
The complete schedule has 19 peak actual palette writes and retains the source
write times. All source pixel operands and complete CGRAM packets replay exactly.
It still exceeds the 336-clock native-tested window.

The exact retained-time lifetime model proves INFEASIBLE at the exclusive
337-clock gate in 31.914 seconds. This rejects only this saved fixed-bank trace
with its fixed write times and a fixed slot throughout each color lifetime.
Changing prefetch times, live slot moves, other bank assignments and other exact
operand encodings remain open. The larger row-slot model returned UNKNOWN;
neither outcome rejects general raster presentation.

The generic lifetime solver now supports bounded repairs. Only lifetimes wholly
inside the requested interval may change slots; crossing lifetimes remain at
their proven hint slots. The solver checks the complete frame and minimizes the
repair interval's peak and aggregate transfer cost. Portfolio and LNS search are
available. A 120..155 repair, including 357 complete lifetimes, retains the
536-clock peak with both searches. Its source identities remain exact.

The focused suite passes 47 tests; the updated LNS repair test separately passes.
The width guard checks 9825 labels with no new, baselined or stale violations.
Protected files retain their hashes. No shared runtime assembly changed. No
color reduction was applied. Authored native raster and MOTU completion remain
unproven.
