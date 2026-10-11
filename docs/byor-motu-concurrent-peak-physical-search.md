# Concurrent source peak cache and physical transfer search

The source-derived nominal spawn timeline pairs He_ManB freespecial4 frame 6
at [80,220,0] with HBreath idle frame 11 at [98,220,93]. This experiment
uses a controlled black underlay. It does not prove native weapon selection,
authored-stage alpha, live pose synchronization or MOTU gameplay.

Independent source composition and palette replay match all 57,344 viewport
pixels, including 5,936 visible OBJ pixels. The viewport RGB555 SHA256 is
`7ea29ce30140a7ce840e5bec6ca9ad789978d195528aadaaf50c8e0cb4721450`.
The exact BOR4086 RGB8 SCREEN operation is composed before RGB555 conversion;
the concurrent output contains 293 colors, with 69 on its busiest scanline.
There is no opaque alpha adaptation or color reduction.

The complete fixed-bank cache search produces an ideal 336-clock span,
17 peak writes (34 data bytes), 410 noninitial writes and 46-line maximum
noninitial prefetch latency. Geometry remains 94 OAM entries, 19 sprites
and 34 tile slivers at the scanline peaks. Actor colors are jointly scheduled.
Ideal endpoint packing is a necessary bound, not a physical transfer proof.

A fixed-timing physical search returns UNKNOWN at 344 clocks. A broader
diagnostic produces source-exact CGRAM packets with a 600-clock peak and
a restricted-family lower bound of 336 clocks. Movable three-line timing
neighborhoods also return UNKNOWN. Exhaustive evaluation of 40,320 eligible
bank permutations retains a 336-clock ideal paired-range bound. The selected
paired bank order with fixed write times is INFEASIBLE at 344 clocks; this
rejects only that ordering, lifetime grouping, timing and range family.

The 600-clock layout was deliberately executed as a negative native test.
It fails with 419 unsafe CGRAM commits and 51,731 pixel mismatches. OAM and
OBJ CHR identities, overflow flags and the production NMI queue payload
remain valid. This failure measures the supplied layout; it does not reject
lossless raster presentation or authorize fallback.

The native compiler now independently replays controlled-context palettes
against source composition before generating a ROM. It rejects wrong source
pixels and overlapping visible piece masks. Native reports identify every
source actor frame, retaining the legacy first-frame hash. Seven focused
native compiler tests pass. A separate known 344-clock HBreath-only source
binding regression passes three fields, with zero pixel mismatches, unsafe
commits or IRQ context faults; it is not a concurrent native proof.

The receipt retains full schedules and bounded native observers in a compressed
bundle, with hashes and compact summaries. No production presentation path or
bank-zero code is changed. Authored peak native admission, concurrent native
admission, live leases, compiler integration and the full MOTU Demo remain open.

NO color reduction applied.
