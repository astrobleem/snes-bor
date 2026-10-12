# Exact reductions for complete-frame palette residency

The concurrent repaired source pose's complete-frame free-residency model
returns UNKNOWN after 120.471 seconds. It contains 73,643 variables and
136,233 constraints. Its restricted-model span lower bound is 232 clocks,
below the 344-clock target. All source demand stays in the model; there is
no incumbent, native admission or raster rejection.

An optional bank-idle reduction uses freely chosen initial palettes. Before
a bank's first required pixel row, its palette can already contain its state
at that first visible row. After its final required pixel row, retaining the
last palette removes unnecessary writes. A bank with no required pixels can
stay zero. These transformations preserve every visible pixel and never
increase the number of writes or contiguous transfer ranges. The initial
palette may preload the complete source frame, as already allowed by the
unreduced model. No source-demand interval is relaxed.

For this source pose, 563 bank-row states collapse. The model has 56,753
variables and 119,343 constraints. It returns UNKNOWN after 120.365 seconds;
the lower bound remains 232 clocks. The reduction improves search size, not
the measured hardware window. Both results remain scoped to their fixed
source pieces and bank assignments.

Physical coverage is also pruned outside the minimum and maximum addresses
that could change on a row. Constant-zero change flags do not create possible
dirty addresses. Any such outside coverage can be trimmed from its end,
reducing words without adding a range. Padding between possible dirty words
remains available, including transparent bank-zero slots. Hints use the
pruned boundary when identifying the first run. The resulting complete-frame
model has 41,408 variables and 88,384 constraints. It returns UNKNOWN after
120.243 seconds, retaining the 232-clock lower bound. A SAT-focused soft-hint
repair returns UNKNOWN after 90.187 seconds and rejects no source family.

Tests independently enumerate every contiguous partition of several sparse
address sets and compare exact costs for one, two and four DMA ranges. Padded
transfer hints and constant-zero events are included. Nineteen physical-layout
tests pass; fifteen row-slot tests check full source-word and CGRAM packet
identity, future bank preloads, opaque black and explicit invalid-domain
rejection, across portfolio and SAT-focused strategies. The existing solver
behavior remains the default until the optional
bank-idle flag is selected. Production code and bank zero are unchanged.

NO color reduction or alpha adaptation applied. Native concurrent admission,
authored-stage peak alpha and the full
MOTU Demo remain open.
