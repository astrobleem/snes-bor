# Integer row-mask cache and transfer gate

The source-exact 128-entry row-mask assignment admits an integer cache with
twenty writes per scanline. HiGHS proves the minimum total write count for
that budget: 509 noninitial writes, zero integer constraint violation and
at most two scanlines of noninitial prefetch in the returned schedule.
Each palette slot and source pixel is independently replayed.

The resulting optimistic bank-partition span still reaches 440 clocks.
Its logical write count does not constitute a hardware transfer proof.
A 345-clock transfer-constrained CP-SAT search returns UNKNOWN after 180
seconds. Another 180-second search using the integer cache as a soft hint
also returns UNKNOWN. Neither result rejects raster or this family.

`raster_bank_residency.py --relax-cache` provides a separate HiGHS test:
cache residency and individual word writes may be fractional, while range
activation and transfer counts remain integer. This strengthens the earlier
fully fractional clock relaxation. A candidate is explicitly reported as
`FRACTIONAL_CACHE_INTEGER_TRANSFER_CANDIDATE`; it emits no tile/palette
schedule and cannot grant integer pixel, physical slot or native admission.
Sixteen focused residency tests pass, including this boundary and an
infeasible one-write fixture. The width audit passes with zero failures.

The source SCREEN output and source RGB555 word identities are unchanged.
No color reduction or alpha adaptation is applied. Concurrent actor space,
physical layout, native timing and MOTU gameplay remain open.
