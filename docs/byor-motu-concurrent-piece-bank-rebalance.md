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
