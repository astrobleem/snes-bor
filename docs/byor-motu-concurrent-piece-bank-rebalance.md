# Concurrent source piece-bank rebalance

The source-exact retarget geometry remains 73 legal 8/16 OAM pieces,
18 sprites and 34 tile slivers at the scanline peaks. The generic piece-bank
balancer may change effect bank assignments inside their declared seven-bank
domain; the player stays in bank 3. Every piece's selected bank remains fixed
across its rows. Equal RGB555 words in one bank count once.

The necessary interval objective improves from 15.0 to 14.25 writes per line
after 9,443 sampled proposals and 3,384 accepted moves. This objective is not
a complete cache or physical transfer proof. The validated fractional cache
lower bound for the chosen assignment is 15.25 writes per line, with zero
dual residual and primal violation below 8e-15.

HiGHS produces an OPTIMAL write-minimizing integer cache in 12.016 seconds:
363 noninitial writes, a 21-write cap, two-line maximum prefetch latency and
a 416-clock ideal peak. A complete flow search produces another valid cache
in 90.094 seconds with a 296-clock ideal peak, 17 peak writes, 406 total
noninitial writes and 16-line maximum noninitial prefetch latency. Its
restricted-family lower bound is 269 clocks. Physical endpoint slots remain
relaxed in that result.

Independent source composition and palette replay match all 57,344 viewport
pixels, including 5,936 visible OBJ pixels, for the new assignment and both
cache schedules. The viewport hash remains
`7ea29ce30140a7ce840e5bec6ca9ad789978d195528aadaaf50c8e0cb4721450`.
Two focused piece-bank balancing tests pass. No geometry is reduced.

Exact physical placement at 344 clocks with the supplied write times returns
UNKNOWN after 90.077 seconds. It is not a native candidate or a raster
rejection. A broader diagnostic produces a source-exact 480-clock physical
layout. Four local cache-and-slot repairs reduce that peak to 424 clocks,
with three accepted complete witnesses. The 21-write cap and necessary
344-clock ideal bank bound hold across the entire frame. Independent source
replay also verifies the accepted physical witness. It remains above the
native window. Native concurrent admission, authored-stage peak alpha, live
composition and leases, compiler integration and the full MOTU Demo remain
open. NO color reduction or alpha adaptation applied.

Six further local repairs retain the 424-clock peak and reduce aggregate
commit cost from 10,064 to 9,904 clocks. Independent source replay again
matches all 57,344 pixels and the same viewport hash. A complete free-residency
search with 541 idle bank rows collapsed returns UNKNOWN after 60.225 seconds;
a forced 408-clock local repair returns UNKNOWN after 45.109 seconds. Neither
result rejects raster presentation.

Restricting this geometry to four or five effect banks plus player bank 3,
while preserving the necessary 21-write interval bound, produces INFEASIBLE
results in 11.302 and 12.318 seconds. These results apply only to those fixed
geometry/domain/bandwidth families. They do not reject seven effect banks,
other player allocations, generic subdivision, or raster presentation.

The generic physical solver can optionally preload banks whose complete-frame
color union fits fifteen slots, retaining a fixed slot layout and eliminating
their later writes. Sixteen focused tests verify packet and pixel identity,
including opaque RGB555 zero and a mixed static/dynamic bank case. This
concurrent assignment has bank word unions of 51, 26, 52, 31, 26, 25, 74 and
52, so no bank qualifies. In particular, the player bank itself requires
raster updates. The same-size complete search with this option returns
UNKNOWN after 60.132 seconds; it does not establish a new admission bound.

A broader bank relabel experiment makes all eight banks eligible for both
actors in this controlled precomposited context. It tests 22,479 permutations
and 256 slot reflections each in 45.047 seconds, without improving the
424-clock peak. The time limit leaves that family nonexhaustive.

The generic `raster_physical_slot_permute.py` instead searches arbitrary fixed
permutations of the fifteen opaque slots in each bank. A fixed permutation
preserves every source word, its cache lifetime, write time, OAM bank and
geometry; pixel indices and packet data are remapped offline. The first
100,000 proposals reduce the physical peak to 408 clocks in 6.515 seconds;
300,000 further proposals reduce it to 392 clocks in 19.031 seconds. Both
complete physical witnesses replay all source pixels and CGRAM packets.
The peak write count remains 17. These witnesses remain above the measured
344-clock native window. Two focused permutation tests plus nineteen existing
packet/layout regression tests pass, including input immutability and aliased
prefetch-event lists. No native or gameplay admission is claimed.

Six local cache repairs of the 392-clock witness retain that peak and reduce
aggregate transfer cost from 9,936 to 9,792 clocks. Five complete candidates
are accepted; independent source replay again matches the complete viewport.
The full-frame 21-write cap and necessary bank-window check remain valid.
