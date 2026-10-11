# Preserve the necessary bank transfer window during slot repair

The physical slot solver can now constrain the ideal bank partition of every
actual palette change. This includes live slot moves and prefetches. The bound
does not substitute for the physical range cost: both are checked separately.
Local refinement inherits the bound from its input and independently verifies
it across the complete resulting frame, including the repair exit boundary.

For the reordered 80-piece authored frame, a 337-clock exclusive bound preserves
the 336-clock necessary bank gate. The first free-residency search produced a
792-clock physical witness; four local repairs reached 760. Starting instead
from the valid 600-clock fixed permutation retained 600. These witnesses replay
all source pixel identities and CGRAM packets, but do not meet native timing.
The prior 552-clock witness remains better physically and has a different bank
order. No result here rejects general raster presentation.

Focused validation passes 47 tests, including a one-word strict-window boundary
and full-frame inheritance checks. The width audit checks 9825 labels with zero
new, baselined or stale violations. No shared runtime assembly changed. All 17
protected files retain their hashes. No color reduction was applied. Authored
native raster presentation, concurrent actors and MOTU completion remain open.
