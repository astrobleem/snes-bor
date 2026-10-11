# Physical residency search with live slot movement

The slot solver can fold every write through the first visible source row
into VBlank initialization. No source pixel precedes that row, and replacing
the initial palette with the state at that row preserves every later source
use. This avoids redundant pre-visibility write-time choices. The authored
peak starts at row 112. Focused replay tests cover the reduction and opaque
RGB555 zero.

The prefix-reduced rectangle search returns UNKNOWN at both 356 and 600
clocks. General physical ranges prove the existing 352-clock logical witness
infeasible at fixed write times; the earlier paired-range rejection was not
the only physical obstacle.

A separate generic row-slot model allows live colors to move between slots,
charging every changed CGRAM word. Keeping that witness's exact resident sets
is still infeasible at 356 clocks. Allowing any source-required word in its
fixed bank, with independently replayed row demands and arbitrary slot moves,
returns UNKNOWN after sixty seconds. Prefetch is bounded by the complete
54-line visible interval, with VBlank initial residency free. Dead-word moves
are charged too. These are fixed-bank search results, not a universal raster
rejection. Every successful small test replays packets, pixels, opaque zero
and source-bound math-control hashes.

Trial statistics and artifact hashes are retained in
`docs/receipts/byor-motu-raster-slot-residency-search.json`. Native authored
raster, concurrent palette admission and MOTU Demo certification remain open.
No color reduction was applied.
