# Exact concurrent cache witness

The controlled source He_Man/HBreath pose now has a complete, independently
replayed fourteen-write fixed-bank cache schedule. Its unchanged geometry is
97 OAM entries, 22 peak sprites and 34 tile slivers. It preserves all 293
opaque output RGB555 identities, including source SCREEN alpha on the fixed
black underlay. Bank rebalancing duplicates seven color identities across
banks without altering any source pixel. The validated fractional bound is
12.8333333333; the exact witness uses 359 noninitial writes and at most
seventeen lines of prefetch.

This remains a cache witness. Checking all 40,320 global bank permutations
against its 37 distinct write-count patterns gives an optimistic minimum
peak prepared span of 344 clocks. It grants ideal endpoint slots. The
physical-layout searches remain open, and the previous foreground stress
loop's 44-clock entry spread cannot simply be added to that span and called
admitted inside the 356-clock safe window.

The physical solver additionally supports a restricted adjacent-bank-pair
family. It uses at most four ranges, retains palette-slot lifetimes and exact
packet replay, and allows inactive pairs between active ones. The fixed-time
pair family is infeasible at 348 clocks for the tested original and permuted
encodings. Flexible-time trials reach their thirty-second bounds without a
candidate. These results reject neither arbitrary ranges nor raster overall.
Short-demand lifetimes with eviction/reload remain under investigation.

Rebalanced outputs now move earlier bank-search restrictions into
`input_bank_search`. Their old frame-color cap and rolling-window restriction
are input provenance, not certifications of the new assignment. Current
pieces, traces and the rebalancing authority describe the resulting encoding.

Seventeen focused rebalancing/layout tests pass, including inactive paired
range gaps, opaque black, exact source pixel replay and prior-constraint
provenance. The reproducible cache witness is compressed without a timestamp
in `docs/receipts/byor-motu-player-effect-cache14.json.gz`; its uncompressed
SHA-256 is
`3ca07482b23457dd568b939cd4fc061d805996614fa1265b91bac3cbd6ceeecd`.
No color reduction is applied. Authored background alpha, actor reachability,
native concurrent presentation and full MOTU gameplay remain unproven here.
