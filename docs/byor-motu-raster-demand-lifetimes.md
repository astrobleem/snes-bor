# Physical palette lifetimes from pixel demand

`raster_slot_layout --demand-gap N` rebuilds each bank/color lifetime from the
lines that actually use it. Requirements separated by at most N unused lines
share a resident lifetime. It retains the fixed piece bank assignments and exact
RGB555 identities. `--flexible-prefetch` then schedules writes before first use
with physical-slot exclusion through the last use. No runtime allocator is added.

For the isolated mixed HBreath candidate, gap two produces 615 used lifetimes.
The 300-second search with a 348-master-clock limit returned UNKNOWN. A separate
60-second search with a relaxed 4096-clock limit found an exact physical-slot and
packet construction with a peak span of 1064 clocks and four ranges. Its packets
and every indexed pixel replay exactly, but the span exceeds the measured
356-clock CGRAM window. This construction is not native timing admission and
does not prove that a better layout is impossible.

An optional `--layout-hint` supplies slots and write times from a previously
verified physical layout with matching pieces, source image identity and opaque
masks. The hint does not grant admission: the constraints and independent CGRAM
and pixel replay still decide validity. The hinted 356-clock search returned
UNKNOWN after 1200 seconds. A 300-second follow-up disabled the expensive default
probing and SAT inprocessing, matching the joint Boolean scheduler's existing
configuration. It performed 78057 branches and 29885 conflicts and also returned
UNKNOWN. These bounded trials do not reject the raster strategy.

Focused tests exercise short-gap retention, hint identity rejection, exact packet
replay and opaque black. No color reduction is applied. Raster remains unproven
for the complete authored concurrent scene and production runtime.

`--reorder-banks` additionally permits a global, bijective permutation of fixed
piece banks. Additive presentation retains banks 0..3 and 4..7 in their respective
color-math classes; precomposited presentation may use all eight. Each piece
keeps its chosen bank for its entire height. Physical packets and pixel replay
use the permuted addresses, including required-versus-prefetch classification.
The 356-clock, gap-two, 16-line-lookahead trial returned UNKNOWN after 300.97
seconds (879310 branches, 350656 conflicts). This remains a bounded search
result, not a hardware rejection. Four focused layout tests pass.
