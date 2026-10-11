# Minimize total transfer cost after the physical peak

The lifetime allocator now minimizes the physical peak first, then total
transfer cost. The objective multiplier exceeds the complete frame's maximum
possible aggregate cost, so an aggregate improvement cannot worsen the peak.
Bounded lifetime repairs already used this ordering for their own interval.

The authored 80-piece frame's first search retains a 504-clock peak while
reducing total cost from 18848 to 9632 clocks. The next search reaches a complete
488-clock physical witness. All source operands, transparent pixels, fixed
piece bank selection, math controls and CGRAM packets remain exact. This still
exceeds the native-tested 336-clock transfer window; it is offline solver
evidence, with no native or concurrent-actor admission.

Focused validation passes 39 tests. A separate strict-bank-bound fixture checks
the independently replayed optimal peak and total costs. The width guard checks
9825 labels with no failures. All 17 protected files retain their hashes. No
runtime assembly changed and no color reduction was applied.
