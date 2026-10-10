# Exact context OBJ math: geometry fits; candidate bandwidth remains blocked

The generic explicit-pose probe encodes the final source RGB555 output as either
an opaque OBJ value in banks 0–3 or an additive residual in banks 4–7. Residuals
are computed after literal RGB8 SCREEN composition, over the actor-free source
BG. Every decoded visible pixel equals the source composite. Black remains an
opaque identity. This requires a corresponding subscreen and frontpanel routing;
no native layer architecture, runtime compositor or gameplay admission is made.

A bipartite minimum identity cover chooses 345 opaque and 91 additive identities.
The minimum global identity count is not a minimum traffic solution. Generic
selective subdivision of four legal 32x32 pieces into 8x8 children reduces this
candidate to 57 OAM entries, 14 sprites and 34 tile slivers per line. A fixed bank
assignment exists, with eligibility enforced. Compiled surface indices are
replayed against the per-line slot states; all surface pixels match. The
heuristic peaks at 41 writes / 82 data bytes. Its fixed assignment fails a
stronger interval bound: lines 129–137 require at least 463 data bytes where the
optimistic shared window supplies 352. The eligibility-pool relaxation does not
reject every possible assignment of this encoding. A search constrained by
22 writes per line and multi-line liveness reaches its bounded search limit;
that is not hardware infeasibility.

Two further source-derived policies have assignment-independent bandwidth
failures. Using residuals only for source alpha layers needs 375 data bytes
across lines 129–135, versus 264 available. Using residuals at every eligible
visible pixel needs 451 bytes across lines 128–135, versus 308. These bounds
allow ideal preloading in both 60-slot eligibility pools and one shared CGRAM
low-byte latch, and exclude addresses, setup and contention. Alternate pixel
mode choices and saturated-channel operands remain open. Raster presentation
has not been universally rejected. The BG/hybrid path has not been rejected.

Twenty-four focused tests pass, including exhaustive channel arithmetic,
bipartite cover comparison against brute force, source-exact subdivision,
shared-window accounting and bank eligibility/liveness. The width audit has
zero violations; all 17 protected tracked hashes remain unchanged. No shared
production presentation changed, no color reduction and no PCM copies.
[Measured receipt](receipts/byor-motu-exact-context-obj-math.json).
