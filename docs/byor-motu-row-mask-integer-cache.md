# Integer row-mask cache and transfer gate

The source-exact 128-entry row-mask assignment admits an integer cache with
nineteen writes per scanline. HiGHS proves the minimum total write count for
that budget: 509 noninitial writes, zero integer constraint violation and
at most four scanlines of noninitial prefetch in the returned schedule.
Each palette slot and source pixel is independently replayed.
The independently validated fractional write bound is 18.055556; therefore
nineteen is the minimum integer peak for this fixed bank assignment. The
previous twenty-write schedule also has 509 total writes and two-line
prefetch latency. Both full schedules are retained.

The resulting optimistic bank-partition span still reaches 424 clocks,
improved from 440 in the twenty-write schedule.
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
The authored integer-transfer/fractional-cache trial returns UNKNOWN after
180 seconds. It supplies neither a transfer candidate nor an infeasibility
certificate. Full viewport replay of the nineteen-write schedule matches all
57344 source-composed RGB555 pixels, including exact SCREEN alpha.

The source SCREEN output and source RGB555 word identities are unchanged.
No color reduction or alpha adaptation is applied. Concurrent actor space,
physical layout, native timing and MOTU gameplay remain open.
