# Continuous source-exact palette cache witnesses

The authored source-height KnightBot/ShockBall/player/HBreath frame-14 pose
has a constant ADD, no-window integer cache witness with 19 peak writes on
lines 108 through 171. The corresponding fractional bound is 18.5. Ordinary
actors require literal words only on their visible scanlines. Independent
replay checks the source-composited RGB555 output, including ordinary actors.
Neither witness assigns individual OBJ banks.

Extending the cache to all 224 viewport lines retains its contents across both
boundaries. The extension permits at most 21 writes per line and independently
replays 10,810 non-bypassed visible source pixels. There is one initial preload,
with no later free reset. A separate mixed-mode witness also covers the full
viewport at 21 writes; its overlapping subproblems pin identical palette states
at their boundaries. Source-bound segment merging rejects palette resets,
missing ordinary literal words, invalid controls and excess writes.

The generic slot heuristic now accepts per-line prefetch limits to share a
write budget between independent caches. Required misses remain measured rather
than suppressed. The source math solver accepts an explicit mode subset and
initial cache state. No-window witnesses compile math enabled everywhere; an
ordinary-only endpoint participates in residency replay even when it contains
no effect pixels. Row-capacity search may use a validated geometry hint, while
retaining its explicit relaxed transfer claim.

The peak BR12 HBreath frame over the authored background also has a constant
ADD integer cache witness at 15 writes. Its source-exact phase-4,4 geometry cover
uses 18 objects and peaks at 10 tile slivers before palette masks. The source
opaque canvas remains 110 by 90 with 204 RGB555 colors. The final composed
colors are checked against BOR SCREEN semantics; this is not an opaque-effect
adaptation.

The cache proofs use two eligibility classes of 60 words each, corresponding
to banks 0–3 and 4–7. They are prerequisites for fixed-bank search, not hardware
admission. The concurrent interval-restricted and unrestricted joint searches
returned UNKNOWN. Restricting the new cache's operands to the prior 101-object
geometry returned INFEASIBLE, including one extra bank mask per rectangle.
Those outcomes reject no universal raster policy. The standalone authored peak
fixed-bank/physical search remains in progress.

The receipt retains complete cache witnesses and bounded search summaries.
Independent source replay, 86 unique focused tests, the width audit
(9825 labels, zero failures), and all 17 protected tracked-file hashes pass.
No production presentation path, ROM bank-zero code, or inherited dirty evidence
was changed. No color reduction is applied. MOTU runtime completion is open.
