# Fixed-geometry exact operand repair

The fixed-bank cache model now has an independent HiGHS MILP backend for its
integer linear interval-range formulation. Bounds and every rounded integer
constraint are replayed before a candidate can be accepted. The two backends
agree on both an exact-pixel fixture and an infeasible replacement fixture.
The original source witness reaches the MILP deadline at sixty seconds with
no candidate. This does not reject raster.

The joint source-context compiler can now keep each hinted pixel in its existing
OAM piece and palette bank while choosing other exact additive operands and
cache lifetimes. This differs from fixing the existing encoded operand colors.
The fixed pixel ownership comes from decoded source masks, including transparent
holes, rather than enclosing rectangles. Atoms spanning different fixed owners
are split by their actual pixels. Unselected OAM masks cannot enter the result.
Dimensions, source alpha-composed output and per-pixel color identity remain
checked by the existing independent RGB555 replay.

The mode is generic and requires a source-identity-matched schedule hint. It
cannot silently substitute pooled residency or bank symmetry. A regression
holds two halves of one atom in different fixed palette banks and verifies
that both mask geometry and every source output pixel survive compilation.
Ordinary compilation defaults to the existing free-geometry path.

The isolated source search fixes the existing 62-piece pixel ownership, permits
the complete exact additive operand cover and up to 23 logical writes, and
requires the favorable 344-clock partition bound. It returns UNKNOWN after
60.070 seconds: 29,308 variables, 74,545 constraints, 18,342 branches and
586 conflicts. Geometry is fixed; operand choices remain open. It supplies
neither a physical schedule nor an infeasibility proof.

The source schedule hint now includes cache residency and exact write
transitions, in addition to mask and operand choices. These remain soft hints.
The corresponding fixed-geometry source trial returns UNKNOWN at 60.074
seconds with 25,204 hinted variables. A fixed-encoding cache trial allowing
21 writes also returns UNKNOWN at sixty seconds; the logical write minimum is
not assumed to minimize DMA cost.

Critical-interval experiments retain only rows 128 through 135 and grant free
initial palettes. They are necessary relaxations of the fixed encoding, not
complete-frame witnesses. Both CP-SAT and HiGHS return UNKNOWN after sixty
seconds on 2,671 variables. Restricted pixel demand has a separate status and
explicit partial-frame proof flags; ordinary physical consumers reject it.
Valid compulsory-load cuts now count distinct required bank identities across
short intervals, subtracting the fifteen slots available at interval entry.

With 121 compulsory-load cuts, the critical interval has an integer witness
after 34.388 seconds: nineteen writes at peak, four-line actual prefetch and
a favorable 336-clock partition span. Every retained source piece pixel is
replayed. Physical endpoint slot packing and the remainder of the source frame
are unproven. A validated partial residency witness can now seed the full-frame
cache search without removing any complete-frame demand; a regression rejects
a hint whose retained source pixel differs.

The full-frame trial seeded from that interval includes 5,891 compulsory-load
cuts and returns UNKNOWN after 120.079 seconds (4,103,539 branches). It does not
prove complete-frame pixel identity for a new candidate. Its original report
erroneously set that flag from input scope before a candidate existed; the raw
report is retained with its hash, the normalized report clears the flag, and
the code now sets it only after successful pixel replay. An infeasible-fixture
regression guards this distinction.

The broader offline suite passes 74 tests; the twelve cache/backend/hint tests
pass after adding the partial-hint regression. No runtime assembly,
bank-zero allocation or production presentation is changed. Native raster
admission, authored simultaneous gameplay and full MOTU Demo completion remain
open. No color reduction is applied.
