# Exact pixel alternatives: pooled liveness reaches 20 writes; banks remain open

The generic cover/liveness LP models every visible pixel as requiring either its
exact source RGB555 output or its exact additive operand over the actor-free
BG. Opaque and additive eligibility are separate 60-slot pools. Both consume
one combined write budget. Initial residency is optimal at first visibility;
unbounded preloading is allowed. Banks, OAM and physical slot positions are
relaxed. A feasible pool result is expressly not a hardware schedule.

The full explicit GUILE2 source pose has a fractional peak lower bound of
19.428571 writes per line. Primal and dual residuals are checked; the validated
dual bound matches the objective. An integer schedule needs at least 20 writes
in this encoding family. This does not reject the optimistic 44-data-byte safe
window. A second integer optimization, pinning integral LP residencies, finds a
20-write pooled residency candidate. It does not prove fixed-bank feasibility
or transfer descriptor overhead.

Using the solution to guide exact pixel modes gives legal mixed-size geometry,
but heuristic fixed assignments still fail bandwidth. The joint physical
solver also admits a hierarchy of legal 32x32 parent and 8x8 child masks, with
disjoint pixel ownership and fixed bank selection for each OAM mask. It emits
packed per-piece indices and replays those masks against physical palette slots.
Initial rows before first visibility are folded into VBlank palette loads.
Horizontal tile clipping follows the retained Mesen fetch model; source scene
native OAM proof remains required.

The fixed 32x32 grid cannot realize this particular pinned pool candidate at
20 writes. The 16x16 grid reaches its bounded limit. The mixed-size grid, with
22 writes allowed, reaches a five-minute limit without an incumbent (84,480
variables, 104,194 constraints). This leaves the physical bank/OAM proof open;
neither a timeout nor failure of a pinned pool solution rejects all raster
strategies. Alternate residency/pixel choices and saturated operands remain
open. BG/hybrid remains open. MOTU is not certified.

Thirty-one focused tests pass, covering exact pixel masks, opaque black,
negative residuals, pooled/integer nonclaims, liveness, widths and fixed bank
eligibility. The width audit has zero violations and the 17 protected tracked
hashes match. No production presentation changed, color reduction or PCM copies.
[Measured receipt](receipts/byor-motu-pooled-cover-liveness.json).
