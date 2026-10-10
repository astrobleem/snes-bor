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

`--fix-hint-slots` constrains the physical positions to those from the verified
hint while allowing write times and optional fixed-bank permutation to change.
It requires a matching verified hint for every used lifetime. The gap-two trial
with four ranges, a 356-clock window and 16-line lookahead returned INFEASIBLE in
11.43 seconds (511 branches, 51 conflicts). This rejects that fixed-slot family
only. Other slot positions, piece assignments, encodings and transfer mechanisms
remain open. The focused tests verify that frozen slots retain the exact indices.

With the transfer limit relaxed to 4096 clocks, that fixed-slot family reaches
OPTIMAL in 45.01 seconds: its minimum peak prepared span is 776 clocks. This is
above the measured 356-clock window. The resulting schedule has 31 peak writes
and 62 color-data bytes; its full physical CGRAM and pixel replay pass. The
optimal construction is retained under out, with a bounded hash/statistics
receipt. It remains outside native timing admission.

Hints can now carry a verified global bank permutation. The compiler validates
the bijection, color-math classes, piece geometry, source identity and opaque
masks, and translates update times back to source bank lifetimes. New solver
constraints and independent replay still determine admission. The 356-clock
trial using the optimal fixed-slot construction as a soft hint returned UNKNOWN
after 300.92 seconds (573722 branches, 35264 conflicts). A separate gap-zero
trial, with 823 shorter lifetimes, returned UNKNOWN after 301.16 seconds. Neither
is a universal rejection.
