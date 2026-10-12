# Source-context OBJ retarget and local fixed-bank repair

A source-exact seed mask can be reused in a new explicit source composition
without treating its old palette words as the new output. The generic offline
operation verifies actor identity, frame hash, dimensions, palette selection,
flip, alpha and geometry origin. It derives new words from the source scene,
adds other actors with explicit bank domains and discovers over-capacity bank
rows. Only affected seed pieces receive movable bank choices. Each resulting
piece keeps its selected bank across every row.

For the controlled He_ManB + peak HBreath pose, the seven-bank effect seed
exceeds capacity on rows 125 and 126 in bank 7. The derived repair set contains
four seed pieces. Moving one piece to bank 1 solves both rows. The player uses
bank 3. Legal 8/16 OBJ geometry is 73 entries, 18 sprites and 34 tile slivers
at the scanline peaks. Source-owned visible pixels and transparency replay
exactly across all 57,344 viewport pixels, including 5,936 OBJ pixels.

The generic implementation reproduces the initial experiment's pieces,
masks, palette trace and compiled schedule hash exactly. No actor name is
tested to select behavior. Explicit mapping is source effect actor 0 to
concurrent scene actor 1; domains are supplied by the caller.

The validated fractional cache lower bound is 15.5 writes per line. The
integer write-minimizing cache is OPTIMAL after 10.86 seconds, with 364 total
noninitial writes and a 21-write cap. A complete optimistic range-flow search
then produces a source-exact cache with a 312-clock ideal peak, 17 peak writes,
402 total noninitial writes, six active banks at the transfer peak and
20-line maximum noninitial prefetch latency. Its restricted-family lower
bound is 283 clocks. Endpoint slots remain relaxed in that cache result.

Fixed-time physical slot placement returns UNKNOWN after 90.110 seconds at
344 clocks. This neither admits the transfer nor rejects raster presentation.
A broader diagnostic finds a fully replayed physical witness with a 616-clock
peak and a restricted-family lower bound of 312 clocks; it exceeds the native
window and is not admitted. Movable three-line timing neighborhoods return
UNKNOWN after 90.087 seconds. Four local cache-and-slot repairs reduce the
physical peak from 616 to 504 clocks and total span from 11,632 to 10,848
clocks. Every accepted state retains all source pixels, the 21-write cap,
fixed OAM banks and the necessary 344-clock ideal bank-partition bound.
Independent source replay checks the accepted 504-clock witness. It remains
above the native window; no admission or universal rejection follows.
Six further local repairs reduce the peak to 488 clocks. Exhaustive evaluation
of 5,040 eligible bank permutations and 256 slot reflections per permutation
keeps that peak and chooses the existing labels and slot direction. Both
complete witnesses independently replay all source pixels. This exhausts
only the relabel/reflection family for that supplied cache and slot layout.
A third six-repair pass retains the 488-clock peak and reduces total span
to 10,568 clocks. Its complete viewport replay passes. Wider complete-frame
free-residency scheduling remains a separate search; no local timeout or
plateau rejects it.
Constructive eviction/reload searches stop at row 127 with beam 32/global 8,
and row 129 with eligible bank permutations at beam 32/global 16 and beam
48/global 32. They use the validated cache's initial colors, interval repacking
and 55-line lookahead at the 344-clock target. These bounded failures do not
reject raster or admit a frame. The receipt records their complete parameters.
Native concurrent presentation, authored-stage peak alpha, live composition
and leases, compiler selection and the full MOTU Demo remain open.

Two focused tests pass, covering added actor admission, source frame mismatch,
uncovered source pixels, input immutability and invalid actor mapping. Source
and hardware geometry replay also run on the actual source assets. NO color
reduction or alpha adaptation applied. New work is offline; bank zero and
the production static presentation path are unchanged.
