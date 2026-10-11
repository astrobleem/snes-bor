# Foreground deadline and alternate transfer master

The optimized authored-control transport is rerun with a foreground WAI
observer. Native execution passes four complete fields with zero pixel
mismatches, unsafe commits or IRQ context faults. Every observed foreground
WAI entry on the following active line precedes the H=648 interrupt trigger.
The tightest entry is H=638, leaving ten master clocks. Full phases and source
control traffic are retained compressed. WAI execution observation is enabled
only for the WAI foreground, avoiding logs from a busy polling loop.

A measured integer cost expression follows packet words/ranges, distinct
next-line count loads, count-register stores, shared width switches and
zero/nonzero control stores. Across 1,120 earlier observed active-line IRQs
its residual is minus four to plus six clocks. This is an empirical bound for
the measured fixture, not a universal hardware cost or production lease proof.

The exact-alpha cache searches remain unresolved: a fractional-cache/integer-
range HiGHS trial at 336 clocks returns UNKNOWN; complete and local CP searches
at 344 clocks also return UNKNOWN. The local trial fixes residency outside
lines 126..142 rather than discarding outside pixels.

The transfer/cache decomposition now has an independent HiGHS integer master
for the linear flow graph. Its focused fixture admits a fractional-cache
budget candidate without pixel/native claims and rejects an insufficient
budget for the fixed family only. On the authored frame its 60-second first
master returns UNKNOWN, with no dual cut or universal rejection. Six
decomposition tests and four native-compiler tests pass. Width remains clean.
NO color reduction or alpha adaptation is applied.

A bounded interval-preserving budget search performs 270,457 proposals in
45 seconds, reducing seven over-budget rows to two. Its remaining peak is
352 clocks; it proves no cache feasibility. Per-line budget hints are now
domain checked and grant no admission. A 60-second CP master with this hint
also returns UNKNOWN. All prior constraints and independent cache checks
remain in force.
