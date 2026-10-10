# Fixed OBJ banks with scanline math controls

The generic joint source OBJ solver accepts a source-replayed integer pool
candidate through `--scanline-math-candidate`. It binds the candidate to the
prepared scene metadata and exact RGB555 frame hash. It rejects clipping
relaxations, invalid register descriptors and missing source pixel coverage.
Inside the saved interval it uses the chosen scanline math modes, actual
two-window eligibility and resident operand choices. Outside that interval it
explicitly uses full addition with no color window and enumerates exact
operands. Full-frame source demand remains present in this joint search.

Pixel atoms distinguish background identity and window eligibility, including
darker outputs whose full-add residual is absent. This prevents distinct
subtraction requirements from being accidentally grouped together. OBJ bank
selection remains fixed per emitted piece. Lower banks store literal colors;
upper banks use the shared mode when the window enables math and literal colors
when it disables math. Candidate replay applies the actual RGB555 operation at
every emitted pixel. The compiled schedule hash includes its modes and windows.

This input restricts operand choices, not bank residency. The joint solver must
still allocate fifteen opaque slots per bank and account for all actors, OAM
entries, full sprite rectangles and tile slivers. It cannot inherit a pool's
22-write result as its own transfer count. Window register timing and native
alpha/layer routing remain separate, unproven admission requirements.

`--row-capacity-only` provides a smaller bank/geometry search. It requires
120 writes, zero lookahead and no prepared transfer window, pool residency or
schedule hint. It omits palette lifetimes between possible-use rows and builds
an independently replayed logical trace if a candidate exists. Its transfer
budget is explicitly relaxed; it does not admit an HBlank mechanism. Coverage
cuts require a selected eligible OAM mask for each atom, strengthening the
fractional search without removing valid integer renderings.

The corrected frame-14 He_ManB/HBreath/three-KnightBot/three-ShockBall pose
has no candidate in the initial sixty-second joint trial at 24 writes, the
sixty-second 120-write geometry trial, or the smaller sixty-second row-capacity
trial. A 120-second trial with coverage cuts and an OAM-minimizing objective
also returns UNKNOWN. All four are bounded no-candidate results. These bounded searches do not establish raster
infeasibility or trigger BG fallback. Trial statistics are retained in
`docs/receipts/byor-motu-fixed-obj-scanline-controls.json`.

Focused tests keep a single upper-bank piece across subtraction, half addition,
window-disabled pixels and an explicitly defaulted full-add row. They reject
missing operands, foreign source identity and clipping relaxation, and replay
row-capacity eviction/reuse. The combined joint/cover/window suite passes 42
tests; the width guard reports 9,825 labels, zero new violations, zero baselined
violations and zero stale entries. No production assembly or bank-0 allocation
changes. No color reduction is applied.
