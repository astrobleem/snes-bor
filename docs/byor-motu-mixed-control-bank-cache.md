# Changing-control exact bank cache

This experiment uses the existing source-exact BR12 encoding with 215 ADD
lines, four halved ADD lines, one halved SUBTRACT line and four SUBTRACT lines.
Its saved window descriptors remain bound to the source-composed frame.
This preserves the BOR 4086 RGB8 SCREEN result projected to RGB555; no alpha
adaptation or color reduction is applied.

The fixed-piece bank master evaluates nine assignments in 180.407 seconds.
All 104 interval bounds are independently replayed against the cache LP.
Its best fractional clock bound is 290.313464. Geometry remains 80 OAM entries,
24 sprites and 34 tile slivers. Bank changes stay within their math eligibility
classes, and every source operand and coordinate is preserved.

HiGHS admits an eighteen-write integer cache in 9.953 seconds: 438 total
noninitial writes, two-line maximum prefetch and zero integer constraint
violation. Its optimistic bank-partition span is 408 clocks.
An independent validated write LP gives exactly seventeen writes. A
seventeen-write integer cache is then admitted in 9.141 seconds: 440 total
writes, eleven-line prefetch, zero integer violation and a 392-clock optimistic
span. Thus seventeen is the minimum integer peak for this fixed assignment.
Neither cache fits the isolated 336-clock changing-control transfer window.
This does not reject other write timing, banks, operands or raster presentation.

The fixed-bank residency tool now supports a direct range-flow backend. It
selects at most four disjoint ranges, computes endpoint/bridge costs, and
retains all per-bank cache and source-pixel requirements. CP-SAT uses reified
range costs; HiGHS uses the equivalent integer linear form. Both agree with
the existing dynamic-programming, adjacent-range and explicit linear models
on the focused minimum-span fixture. Physical endpoint slot packing remains
relaxed. The authored 337-clock feasibility trial returns UNKNOWN after
120.225 seconds, with 30,828 variables and 69,555 constraints. It does not
reject this assignment or raster presentation.

A further flow search finds a source-exact integer cache with a 376-clock
optimistic span, nineteen peak writes, 451 total writes and twelve-line
prefetch. Its lower bound is 290 clocks, so this is not a minimum-span proof.
It still exceeds the changing-control window. A seventeen-write trial allowing
at most four active banks is INFEASIBLE in 29.661 seconds for this fixed
assignment only. Neither result rejects other bank assignments or encodings.

Independent current-PAK replay verifies every 57,344 viewport pixels for the
initial encoding, improved banks and all retained integer caches. The compact receipt
retains bounds and metrics; its gzip companion contains full schedules and
dual certificates. All 17 protected file hashes match. Physical slot layout,
native authored peak presentation, concurrent actors and MOTU completion
remain open.

Twenty-two residency/range tests, six mask-retiling tests and four
transfer-cache tests pass. The width audit has 9,825 labels and zero failures.
