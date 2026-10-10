# Complete additive operands in the fixed-bank search

The offline joint scheduler can now examine every RGB555 additive operand,
including operands that are neither a source pixel's minimum residual nor one
of its min/max corners. Each operand must produce the literal source RGB8
SCREEN result after RGB555 conversion over the supplied immutable underlay.
No source colors or dimensions change.

The helper groups identical operand coverage and discards only coverage sets
contained in another retained set. A global replacement preserves every pixel
previously represented by the old operand and cannot increase bank occupancy
or palette writes. Its digest covers every valid operand's replacement; the
scheduler independently replays any resulting fixed-bank incumbent. This is
complete additive coverage for the supplied context, not a moving-world proof.

Use `--complete-additive-cover` in the joint scheduler or its pooled lower-bound
mode. Optional `--underlay-bypass` removes draw pixels whose final RGB555 value
already equals the actor-free background. It keeps the original source canvas,
identity and dimensions, copies inputs before modification, and preserves opaque
black where it differs from the background. This removes 83 of the isolated
frame's 2,751 visible pixels without changing the full-context RGB555 hash.

The isolated peak has 671 additive requirements and 396 valid operands. All
396 distinct coverage sets are maximal. The pooled liveness lower bound remains
14.428571 writes per line, with an integer residency candidate at 15. The supplied
player/enemy/effect pose has a lower bound of 19.428571 and a candidate at 20.
These relax geometry and bank assignment; they are not hardware schedules.
Reported candidate write counts now come from exact rounded-residency transitions
rather than the floating solver objective.

Three 180-second fixed-bank timing searches returned UNKNOWN: write limit 19,
write limit 23, and write limit 23 with exact residency-write indicators. Each
retains the optimistic 356-master-clock prepared-DMA commit-span constraint.
A larger write allowance lets the search consider more contiguous transfers.
Exact write indicators remove surplus writes of resident words from the graph.
These search limits do not prove raster infeasible. Other geometry, residency,
slot layout and native execution still require work.

38 focused tests pass, including a shared exact operand missed by both pixels'
corner families and independent compiled-pixel replay in both solver backends.
The width guard has zero violations and all 17 protected tracked hashes match.
Production presentation and bank zero are unchanged. Full HBreath native raster
execution, concurrent gameplay and MOTU Demo completion remain unproven.
NO color reduction applied.

[Bounded reports and hashes](receipts/byor-motu-complete-additive-search.json).
