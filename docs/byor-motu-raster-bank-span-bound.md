# Interval demand with general bank transfer ranges

The new offline bound counts each fixed bank's required colors over every
scanline interval. At most 15 can be resident at the interval start; the rest
must be written later in that interval. Aggregate write counts are integral,
but individual color residency and physical slot placement remain relaxed.
General range partitions include transparent bridge words and at most four
prepared DMA ranges. This is not a 120-color undifferentiated pool.

Both CP-SAT dynamic programming and linear range selection are supported. The
linear model can use HiGHS. Source-trace hints are checked against every bank
interval; returned aggregate counts are replayed through the independent
partition routine. Small tests establish exact 32-clock adjacent-bank and
40-clock separated-bank bounds, and agreement between all backends.

For the 87-piece authored layout, the validated aggregate lower bound is 256
clocks and the compulsory peak is 16 opaque writes. CP-SAT retains an aggregate
344-clock witness after 35 seconds. HiGHS returns UNKNOWN at the same limit.
The lower bound therefore leaves the 336-clock native gate open; the aggregate
witness does not prove a color residency schedule or physical placement.

The whole-frame physical search with a coherent hint retains the 552-clock
witness and its 21-word cap. The 26 focused tests pass. The width guard checks
9825 labels with zero failures; all 17 protected files retain their hashes.
No shared runtime assembly changed and no color reduction was applied.
Authored native raster and concurrent actor admission remain unproven.
