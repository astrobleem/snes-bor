# Physical palette write caps and fixed slot permutations

This remains a lossless offline feasibility investigation. No authored native
raster admission, concurrent actor admission, MOTU candidate or completion is
claimed. No color reduction was applied.

The earlier 536-clock physical witness changes 27 words on its busiest line.
That trace cannot fit the measured 336-clock control-before-palette window,
even with ideal physical packing. Improving its addresses alone is insufficient.

The earlier 19-write lifetime schedule is a different starting point. Eligible
bank permutations and slot reflections reduce its span from 864 to 792 clocks.
The new generic fixed slot-permutation solver explores all opaque slot positions
within each bank, with an optional joint permutation of eligible banks. Its
compiled result preserves palette write lifetimes, transparent slot zero, fixed
OAM bank selection, source geometry, exact pixel colors and color-math eligibility.
Every packet and source pixel is independently replayed after remapping.

This reduces the 19-write schedule to 616 clocks in a bounded search. Subsequent
free-residency local refinement reaches 584 clocks while enforcing a full-frame
21-word cap. The previous local refinement could improve transfer spans by
introducing too many physical word changes; the new cap charges live moves and
prefetch as well as required colors. Initial preload remains outside HBlank.
The input hint and every accepted complete schedule must satisfy the cap, so
freezing rows outside a repair cannot silently bypass it.

Full-frame large neighborhood search subsequently reaches 568 clocks. Joint
fixed slot/bank permutation then reaches 552 clocks, still with at most 21
changed words per line. These complete schedules remain above the native window.
The new fixed-address coverage encoding accounts for sixteen clocks per covered
CGRAM word and twenty-four per contiguous run, with at most four runs. It
reduces the full-frame model from 41,791 variables and 107,982 constraints to
28,831 variables and 49,608 constraints. Focused tests verify its optimum costs
against the independent packet partitioner, including transparent gaps and the
strict transfer-window boundary. This is a solver encoding improvement, not an
increase in available hardware bandwidth.

A separate 17-write schedule reaches 712 clocks under fixed slot permutation.
Its fixed-lifetime/fixed-bank model has a conservative 337-clock lower bound.
This bound applies only to that restricted model. Allowing different residency,
bank assignment, operand choices or geometry remains open. Neither bounded
search failure nor these witnesses rejects raster presentation universally.

The measured native control-before-palette ceiling remains 336 clocks in the
isolated idle ABI proof. A schedule must still pass authored-background native
execution, exact alpha replay, concurrent scenes and production resource leases
before it can be admitted. The black-underlay native proof is not a substitute.

The receipt retains bounded search metadata and complete offline schedules.
Focused tests cover source identity, packet replay, eligible bank permutations,
write-cap preservation and rejection of invalid hints. No shared runtime path
changed in this increment.
