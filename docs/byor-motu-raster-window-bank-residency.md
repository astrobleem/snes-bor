The generic window/residency solver separates source color encoding from
physical slot placement. Every palette bank retains its own fifteen-slot
capacity and every OBJ piece keeps its bank. Upper-bank pixels may use an
exact color-math operand inside the two hardware windows or literal output
outside them. Row math modes and source geometry remain fixed.

Noninitial writes can preload a potential requirement at most sixteen lines
ahead. Initial residency may preload the entire frame. Colors leave the model
after their final possible use; emitted CGRAM keeps unused physical words until
they are replaced. Required, retained, evicted, prefetched and written words,
future-use latency and transfer bytes are reported independently.

Bank transfer intervals use a disjoint flow formulation equivalent to the
independent ideal endpoint DP. It permits transfers across empty middle banks
and charges all padding. Both reified and linear forms match all 256 bank
activity patterns. The three-bank boundary costs 336 clocks and remains legal
under the strict 337-clock gate. The linear form supports an independent HiGHS
backend; a capacity fixture proves six writes insufficient, seven sufficient,
and preserves opaque RGB555 zero with both backends.

For the authored peak HBreath context, a complete replayed residency witness
needs twenty peak writes and a 368-clock ideal span. Its first physical slot
assignment needs 952 clocks and 112 transfer bytes. It has twelve-line maximum
prefetch latency and no noninitial dead writes. Neither physical slots nor
native timing are admitted. The strict 337-clock gate remains UNKNOWN with
both bounded solver backends. The complete physical witness retained from
the previous search still needs 472 clocks.

A twenty-minute joint physical/bank-class search also remains UNKNOWN after
2965062 branches and 1781469 conflicts. Local fixed-boundary repairs and the
physical solver with redundant interval-flow bounds remain UNKNOWN. These
results reject no universal raster strategy and select no BG fallback.
Thirty-one focused tests pass, the width audit is clean and all seventeen
protected fingerprints match. No assembly or ordinary static presentation
path changes. No color reduction is applied.
