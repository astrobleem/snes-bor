# Exact OBJ search under measured row budgets

The joint solver can enforce separate early/late write limits, remove bank-label
symmetry within each four-bank color-math eligibility group, and search for a
feasible incumbent without first minimizing OAM. Tests verify the early limit,
independent pixel replay, and equivalent bank permutations. The native isolated
IRQ burst measurements supply trial limits of 18 writes before row 75 and 21
thereafter; this does not admit a real production interrupt or scattered writes.

A new exact encoding option reuses scene-derived additive operands when saturated
channels permit several operands to produce the same final RGB555 pixel. Every
chosen operand is replayed against its actual underlay. This explores only the
corpus of minimum residual colors already derived elsewhere in the scene, not all
possible saturated operands. No color reduction or source-output change occurs.

Three 45-second joint searches reached bounded time limits: the concurrent pose
with pinned pooled residency and mixed geometry; the isolated peak effect with
32-pixel geometry; and the concurrent mixed geometry with saturated reuse and
unpinned residency. None produced an incumbent. These are search limits, not
universal raster rejection.

The isolated peak effect also has a fixed-bank opaque precomposite candidate:
47 OAM entries, 10 sprites and 12 tile slivers at peak. It preserves the exact
source-context output, but its heuristic requires 46 writes. More decisively,
rows 128–135 require at least 309 data bytes versus a theoretical 308 bytes, even
with all eight banks relaxed to a 120-slot pool and one preloaded low-byte latch.
This rules out only that opaque precomposite encoding. Exact mixed OBJ color
math and lossless BG/hybrid remain open. Neither source alpha nor live gameplay
has been certified by these offline searches.

33 focused tests pass. All 17 protected tracked hashes match. Production code,
bank zero, static presentation and media are unchanged. MOTU is not certified.
[Search receipt](receipts/byor-motu-obj-row-budget-search.json).
