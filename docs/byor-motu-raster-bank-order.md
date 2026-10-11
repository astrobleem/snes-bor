# A 336-clock necessary bank schedule

The generic bank-order optimizer exhausts eligible permutations for an existing
source-exact write trace. It preserves fixed piece banks, source operands,
palette lifetimes, transparency and color-math eligibility. Its objective grants
ideal endpoint slot packing; independently replayed physical packets retain the
input slot layout. The two costs are reported separately.

Among 576 eligible orders, the 80-piece authored schedule reaches a 336-clock
optimistic peak, matching the native-tested control-before-palette window.
Its mapping is [2,3,0,1,7,4,6,5], with 19 peak logical writes and unchanged
lookahead/lifetimes. This resolves the previous necessary bank-span gap for
this trace, but does not prove physical slot placement.

Unchanged slots require 1000 clocks. Fixed lifetime slot permutation reduces
that to 600, and four bounded repairs reach 584 with a verified 21-word cap.
The prior complete 552-clock physical witness remains best. A constant word
index graph for bank 3 is INFEASIBLE in 15 indices, so that restricted index
family cannot represent this assignment; mutable per-row indices remain legal.
Neither result rejects general raster presentation.

The 87-piece and alternate dynamic-bank-4 traces remain at optimistic minima
of 344 and 360 under exhaustive eligible ordering. Those statements apply to
the fixed saved traces. The focused suite passes 51 tests. All 17 protected
files retain their hashes and the width guard checks 9825 labels with zero
failures. No shared runtime assembly changed; no color reduction was applied.
Authored native raster and concurrent gameplay admission remain unproven.
