# Enforced and replayed palette prefetch lead

The joint encoding/residency solver now limits each noninitial color write to
a selected source-pixel use within the requested lookahead. This applies to
pooled-residency inputs as well as unconstrained residency. Previously the
variable domain bounded a color's earliest possible residency, while pooled
inputs supplied their own domains. Neither necessarily limited every later
prefetch against actual selected pixel use.

The original isolated mixed candidate has a measured maximum noninitial lead
of 17 lines despite reporting a requested lookahead of 16. Its source-pixel
replay and write-count evidence remain valid; its old lookahead label is not
proof of a 16-line deadline. The physical relayout tool now measures input and
output lead, and rejects retained input times outside the requested bound.

The joint solver exposes `--lookahead` and independently replays each emitted
write against actual bank/color pixel demand. Initial palette contents may be
restored in VBlank for the whole compiled frame. Focused tests force a future
color to load after a full bank set has been used: zero-line lookahead rejects,
one-line lookahead admits, and the measured lead is exactly one line. No solver
hint or pooled candidate can bypass this check.

The full joint test suite passes. A new 17-line source peak trial is running with
the strict constraint and the optimistic prepared-range bandwidth bound. Native
transfer/setup/contention admission and the complete MOTU runtime remain open.
No color reduction is applied.
