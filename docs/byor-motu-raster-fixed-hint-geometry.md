# Fixed legal source rectangles and literal palette limit

The joint offline solver now accepts source-exact subdivided rectangles in
fixed-geometry and fixed-rectangle searches. Previously it required a hint to
match the freshly generated canonical grid, preventing reuse of legal compacted
or subdivided schedules. The new path checks legal sizes, actor identity,
source coordinates and complete visible pixel ownership before building atoms.
Independent source output replay remains required for every candidate.

When words and math classes are fixed and each rectangle has a single bank,
pixel choices share the piece bank variable. This preserves the constraints
while reducing repeated variables and equalities. The focused suite passes 49
tests, including subdivided hints, coordinate and missing-pixel rejection,
fixed bank ownership and reassignment with source word replay.

Six bounded maximal subdivision trials reach 128 OAM entries, 28–31 sprites and
33–34 tile slivers per line. Interval demand heuristics range from 15 to 15.286
writes; the full liveness LP bounds are 15.857–16.6. These are HBreath-only
layouts with no spare OAM capacity for other actors. The selected geometry's
residency search finds an optimistic 360-clock witness with 18 writes. A joint
bank and residency search at 337 clocks times out in both HiGHS and CP-SAT;
those results are UNKNOWN, not infeasibility.

A separate exact final-output alternative precomposites source SCREEN against
the authored underlay into literal RGB555 OBJ words. Its relaxed 120-slot pool
has a validated dual lower bound of 22.142857 writes, requiring at least 23
integer writes on some line despite unlimited initial preload. The minimum
span in the prepared-DMA family is 368 clocks, above the native-tested 336.
That rejects this literal prepared-DMA family for this source context; it does
not reject the color-math operand approach or every raster mechanism.

The source output hash remains
`4d1f01dece9f9a50ecde25d1efc3d9e3da2bc0ee3974fc2702650ee0d9cf2934`.
All 17 protected files retain their hashes. The width guard checks 9825 labels
with zero failures. No shared runtime assembly changed, no color reduction was
applied, and authored native raster or concurrent actor admission is not claimed.
