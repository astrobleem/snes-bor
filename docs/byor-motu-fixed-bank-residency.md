# Fixed-bank residency and legal subdivision

The offline cache search now separates color residency from physical slot
placement. Each source piece keeps its palette bank. Every required RGB555
color must be resident on its source row; each bank has fifteen opaque slots.
Initial restore is free, later writes use bounded lookahead, and resident
colors survive until capacity requires replacement. Successful outputs rebuild
pixel indices and independently decode every source piece to check identity.
Banks with at most fifteen distinct colors can preload all of them.

For the isolated 62-piece mixed-encoding witness, the fractional cache lower
bound is 17.5714285714 writes per line. Its primal and dual residuals are below
3e-14. An integer witness reaches eighteen writes in 1.142 seconds, preserving
every source pixel. Thus eighteen is the exact logical peak minimum for this
fixed bank and pixel encoding family. The witness uses seventeen-line
prefetch, averages 2.2332 writes per line, and first reaches its peak on line
129. It requires 36 color-data bytes at peak.

This is not a physical transfer admission. Eleven rows exceed the 344-clock
favorable prepared-transfer target; the worst optimistic span is 368 clocks.
Endpoint slots are granted ideal packing, unchanged interior bank words are
charged, and up to four ranges are allowed. The production window, setup,
HDMA contention and interrupt latency still require native proof.

Transfer-constrained searches using interval selections and a computed
partition minimum return UNKNOWN at their bounded deadlines. Local repair
fixes cache residency outside rows 112 through 147 and also returns UNKNOWN.
A smaller table backend admits only single-bank ranges and disjoint adjacent
bank pairs; this is an explicitly restricted family, not an equivalence claim.
Its first source search returns UNKNOWN as well. No timeout rejects raster.
Extending lookahead to forty lines also returns UNKNOWN. The table frontend
now includes a redundant linear cost bound; a local repair search with that
bound returns UNKNOWN at sixty seconds. Eighteen targeted tests pass, alongside
the sixty-seven-test broader offline run made before the two newest tests.

The generic bank rebalance search preserves each piece's color-math eligibility
class. Exact nonempty 8x8 subdivision respects the global OBJ size pair and
checks actual rectangles against 128 OAM entries, 32 sprites and 34 tile
slivers per line. Splitting four original 32x32 pieces yields 116 entries,
31 sprites and 34 slivers at peak. Rebalancing lowers the interval demand
heuristic from 17.5714 to 17.4286. Independently emitted CHR/OAM indices decode
exactly: 7,072 CHR bytes, 221 occupied cells and 176 unique tiles. This has not
been rendered natively. The eighteen-write, 344-clock favorable cache search
is INFEASIBLE for this particular subdivided bank assignment, not for generic
subdivision or raster presentation.

Concurrent source poses are also refined from source authority. KnightBot's
idle and attack1 have seta 40; its attack1 frame 6 invokes ShockBall at altitude
74, facing its caster direction. He_ManB is the authored breath caster.
The corrected source-height stress scene retains three casters and three
projectiles. Exact simultaneous AI timing and sort identities remain unproven.
On rows 116 through 150, the all-color-math-mode fractional scene relaxation
has a matching primal/dual optimum of 16.125. The full-frame relaxation reaches
its deadline without a bound. Neither establishes a hardware failure.

No color reduction is applied. Alpha 1 remains the authoritative RGB8 SCREEN
operation before RGB555 conversion; these isolated context encodings do not
certify a live gameplay alpha compositor. Production presentation and bank
zero are unchanged. MOTU native raster admission and the complete Demo remain
open. Artifact hashes, measured statistics and explicit nonclaims are retained
in the [receipt](receipts/byor-motu-fixed-bank-residency.json).
