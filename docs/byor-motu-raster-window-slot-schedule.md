# Joint exact window and physical palette allocation

The new generic offline solver keeps OAM geometry, piece banks and shared row
math modes fixed. Each eligible pixel may use its exact literal output outside
the color windows or an exact math operand inside them. It chooses two positive
or two inverted windows, physical slots, residency and transfer ranges together.
This is a bounded operand family, not universal raster feasibility.

Input authority requires source-bound controls, the complete expected RGB555
frame hash and independent input math replay. Every output replays the complete
source frame, transparent masks and all CGRAM packets. Changed operands and
window gates, prefetch latency, dead writes, packet bytes and channels are
reported. No opaque alpha adaptation or color reduction is applied.

A saved authored witness, with all hinted values fixed, is reproduced exactly
at 536 clocks and 19 peak writes. It preserves the ideal 336-clock bank bound.
The free 336-clock gate remains UNKNOWN after 50 seconds. Starting from the
better physical witness, another search retains 472 clocks with 21 peak writes,
52 packet bytes, seven DMA channels and 12 lines of prefetch latency. It changes
three exact operands and three observed window gates; every rendered RGB555
pixel remains identical. No noninitial dead palette writes are present.

The coverage helper also now treats adjacent or overlapping hinted DMA packets
as one union run. Previously it incorrectly hinted multiple starts within a
continuous covered range. This was a solver hint contradiction, not hardware
infeasibility. Regression tests fix every hinted variable and verify the exact
strict-window cost. A separate window fixture proves that three positive runs
can be represented by two inverted windows while retaining a known hint.

The focused suite passes 40 tests. All 17 protected files retain their hashes;
the width guard checks 9825 labels with zero failures. No runtime assembly
changed. Authored native raster, concurrent-actor admission and MOTU completion
remain open. No color reduction was applied.
