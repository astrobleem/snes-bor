# Authored alpha bank-cap experiment

The exact GUILE2 peak-frame solve now finds an opaque/additive encoding with
at most sixty full-frame color identities in each OBJ bank. The earlier
unhinted bounded solve remained unresolved. A matching exact source witness
supplies a soft hint; the solver changes the encoding and independently
replays every RGB555 pixel before declaring success.

The resulting geometry is 66 OAM entries, 19 sprites per line and 34 tile
slivers. It retains source-sized HBreath and source SCREEN alpha on the actual
authored underlay. Banks 0..3 contain literal colors; banks 4..7 contain exact
BG-additive operands. All 32,768 operands were considered with their full
coverage preserved. Eighty-three pixels whose source alpha output equals the
underlay can bypass OBJ while retaining the exact rendered result. This is
an immutable-context witness, not live underlay or gameplay admission.

Initial scheduling peaks at 33 writes. A separate fixed-bank cache solve
produces a complete exact twenty-write schedule, with 515 noninitial writes
and seventeen lines of maximum prefetch. The independently checked fractional
lower bound is 19.2857142857. Its current optimistic prepared span reaches
440 clocks, exceeding the measured 356-clock safe window. The cached colors
therefore cannot be treated as physical transfer admission.

A further solve fixes this 66-piece geometry while allowing exact operand
choices and residency to change. The twenty-one-write, 344-clock prepared
family is infeasible in 17.79 seconds. The twenty-two-write, 356-clock trial
reaches its sixty-second bound without a candidate. Neither result rejects
other geometries, math/window routes or raster presentation overall.

Rebalancing this new geometry gives a validated bound of 19.1428571429,
still above the older 62-piece encoding's 17.5714285714 bound. Balancing
full-frame color counts alone is therefore not sufficient to minimize
transfer pressure. Those distinct artifacts are retained; none is reported
as a better native schedule merely because it has a per-bank cap.

Evidence: `docs/receipts/byor-motu-authored-alpha-balanced-banks.json` and
the compressed exact cache witness
`docs/receipts/byor-motu-authored-alpha-cache20.json.gz`.
No color reduction is applied. Full authored raster and MOTU Demo completion
remain unproven.
