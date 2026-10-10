# Reverse cache construction with forward admission

The generic reverse-search helper reverses the derived slot states and piece
pixels, keeping fixed OBJ banks. Cache construction then runs in the opposite
scanline direction. Its output is restored to source geometry and independently
replayed against each original piece pixel. A backwards fit cannot admit a
forward schedule.

Forward compilation folds each physical slot's first actual pixel use into
VBlank, removes palette phases with no pixel use, and defers later writes to the
forward lookahead bound. Actual changed slots, physical DMA ranges, bridge data,
latency and every CGRAM word are recomputed. A forward transfer-window failure
has a distinct status even when every source pixel is exact.

Four focused tests cover double reversal, exact opaque black/reloads, a bounded
heuristic failure, and a forward bandwidth failure with pixel identity retained.
The related slot-layout, row-state and heuristic suite passes 26 tests.

Eight isolated-frame seeds with a 356-clock window fail to construct a candidate.
Four trials retaining eight complete cache paths also fail, with or without
interval repacking. Four trials granting 640 clocks fail as well. These are
heuristic failures, not infeasibility proofs.

A relaxed 2,000-clock search produces a construction with a forward peak of
1,160 clocks. Recompilation against the measured 356-clock window explicitly
fails physical admission. All input piece colors and CGRAM packet identities
are independently verified; measured noninitial prefetch lead is seven lines.
The source RGB555 context hash, fixed source-sized geometry and piece banks are
retained. This is not a native HBreath proof or a raster rejection.

The [receipt](receipts/byor-motu-reverse-cache-search.json) retains artifact hashes,
bounded statistics and nonclaims. No production graphics code, bank-zero bytes,
PCM files or color reduction are introduced.
