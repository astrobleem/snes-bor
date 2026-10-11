# Logical residency reaches the measured 344-clock target

Repairing rows 127--145 of the exact fixed-bank encoding produces a complete
source-frame residency witness with **19 peak writes, 38 peak logical bytes,
403 total noninitial writes and sixteen-line maximum prefetch**. Its favorable
prepared transfer span peaks at **344 clocks**, matching the private native
transport/control-traffic test's measured span. Schedule hash:
`c34503bd3e80836ead996a5aaf596abae9280db53101d3f3355a67bee2be8471`.
Geometry remains 80 OAM entries, 24 peak sprites and 34 peak tile slivers.

This favorable endpoint bound is not a physical schedule. General-range slot
placement proves these fixed write times infeasible at the strict 348-clock
window. Allowing live slot moves while keeping these resident sets returns
UNKNOWN after sixty seconds. Neither result rejects different residency,
banking, word selection or the raster approach.

The row model now accepts source-word-verified physical hints, uses dense word
identity codes without altering RGB555 values, and includes 7,413 per-bank
interval liveness cuts. Local repairs freeze surrounding states and account
for the exit transfer into the following fixed row. Only current demands and
boundary-resident words need occupy a repaired interval; other temporary dead
words can be replaced without increasing writes. Every changed physical word
is charged, and emitted ranges are independently minimized and replayed.

The broader free-residency search has a complete, source-exact physical witness
with a 792-clock peak. Local refinement reduces aggregate span substantially,
but that peak still exceeds the measured window. A geometry-only persistent
index search now removes equivalent slot-label permutations using a co-live
anchor; the authored trial remains UNKNOWN. None is native admission.

`docs/receipts/byor-motu-raster-fixed-bank-repair344.json` retains these results
and hashes. Its gzip retains the complete 344-clock logical witness. Full
authored native raster, concurrent actors and MOTU Demo certification remain
open. No color reduction was applied.
