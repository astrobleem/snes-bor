# Shared geometry for exact math bank classes

The generic global-word bank constructor can now solve both eligible math
classes together under a shared scanline tile ceiling. Each word and eligibility
domain retains one fixed bank for the frame; every OAM mask keeps that bank.
Rolling palette unions and the requested tile ceiling are independently
replayed. OAM and sprite admission remain explicitly deferred to legal
compaction. The original separate-class construction stays the default.

The peak HBreath source frame over GUILE2 now has a two-row-retention
construction with 162 small objects, 33 sprites and 33 tile slivers. This raw
layout is rejected for OAM/sprite admission. Exact legal 8/16 compaction selects
40 merges and produces **80 objects, 24 peak sprites and 34 peak tile slivers**.
This improves on the earlier separately allocated two-row construction, which
could not meet the tile limit. All source pixels and words replay exactly.

The resulting fixed banks admit a **17-write full-frame logical schedule**,
matching the independently validated cache LP lower bound. There are 408
noninitial writes, 34 peak logical CGRAM bytes and sixteen-line maximum
prefetch. Schedule hash:
`121c0ffd01eca3c671dfc42aae78a591e1c26dc9eaa3419cc05d8262e2952110`.
The source output hash remains
`4d1f01dece9f9a50ecde25d1efc3d9e3da2bc0ee3974fc2702650ee0d9cf2934`.

Legal Mode-0 CHR/OAM compilation uses 6,400 CHR bytes, 200 occupied cells and
163 unique tiles. CHR hash:
`858cf9a60c837143b3e934aa285d584d89ecaeebf8e8fb1a3407bcd7d2debf18`;
OAM hash:
`bf833beb8c74aab5c64042c7d41e2cd20f50797d39fc30395f1018f6bd5c9d2a`.

**This is not physical transfer admission.** The favorable prepared high-byte
commit span peaks at 360 master clocks. Exhaustively checking all 576 fixed
bank permutations preserving math eligibility does not reduce that peak. This
rejects these fixed write times even against the full 356-clock hardware
window. A general-range residency search at 308 clocks returns UNKNOWN after
sixty seconds. Hinted restricted adjacent-range searches at 308 and 332 clocks
also return UNKNOWN. Neither rejects different residency or the raster
approach. The 332-clock trial is an isolated-path target informed by the older
held-BRA first-commit range; it is not the stressed runtime's admitted budget.

The complete logical witness, lower-bound certificate, exhaustive permutation
bound, CHR/OAM hashes and bounded trial summaries are retained in
`docs/receipts/byor-motu-joint-bank-classes-cache17.json` and its paired gzip.
Native authored alpha arithmetic is covered separately by the 55 static-row
cases. Full raster timing, concurrent actors, animated uploads and gameplay
remain open. No color reduction was applied.

Eleven focused global-bank, constructor and compactor tests pass, including
combined tile rejection, explicit raw sprite deferral, global word identity,
rolling union capacity, bank eligibility and source-exact constructor replay.
All seventeen protected tracked files retain their hashes.

Repairing only rows 127--145 finds a source-exact full-frame 19-write schedule
whose favorable endpoint bound is 352 clocks. It has 402 noninitial writes and
sixteen-line maximum prefetch. Fixed write-time physical slot placement in the
paired-range family is infeasible even at 356 clocks: ideal packing cannot be
assumed to respect live slots. Tightening the residency repair to 332 clocks
returns UNKNOWN, as does flexible rectangle-lifetime slot placement at 332.
These bounded results and the 352-clock logical witness are retained in
`docs/receipts/byor-motu-joint-bank-classes-physical-repair.json` and its gzip.
No physical admission follows from that witness.

The physical layout and greedy compilers now include source-bound math modes
and color-window descriptors in their schedule identity. Existing schedules
without those controls keep their original hash payload. Twenty-one focused
slot-layout/greedy tests pass; the width audit remains clean at 9,825 labels.

A loose 2,000-clock slot solve supplies an independently replayed physical
hint with a 904-clock peak. This proves packet data and slot identities only;
it exceeds the hardware window. Allowing per-bank permutations of those hint
slots and flexible eight-line prefetch is infeasible at 332 clocks. A broader
two-line demand-gap rectangle search returns UNKNOWN. Neither result rejects
different lifetime groupings or unrestricted slot layouts. Thirty combined
global-bank, constructor, greedy and slot-layout tests pass.

The generic lifetime component recoloring follow-up preserves all 57,344
viewport output pixels, including exact source SCREEN over GUILE2. A new
complete integer cache limits write-active banks to six and has a 336-clock
optimistic bound, nineteen peak writes and ten-line maximum prefetch.
It solves in 10.151 seconds. Physical lifetime recoloring produces a valid
456-clock witness, still above the measured transfer window. Liveness shifts,
all 576 eligible bank permutations with 256 slot reflections, and three
twelve-second local slot repairs do not lower that peak. These are restricted
family results, not rejection of lossless raster presentation. The full
source replay and bounded schedules are retained in
[the authored follow-up receipt](receipts/byor-motu-authored-kempe.json)
and its compressed archive. No color reduction or alpha adaptation occurs.

A whole-piece reassignment lowers the interval-pressure relaxation from 16.5
to 15.142857 writes per line. Its sixteen-write integer cache is infeasible
even without range constraints. A seventeen-write logical cache is OPTIMAL
in 7.797 seconds with 444 writes, six-line prefetch and zero integer constraint
violation, but its optimistic physical span is 392 clocks. Constrained cache
searches and broader free-residency physical searches return UNKNOWN at
their bounded limits. The latter allow live slot moves, preload a static bank
and do not fix the supplied cache lifetimes. Their results still do not
reject the raster approach universally. All complete witnesses independently
replay exact source alpha over the entire viewport; bounded negative search
reports are retained separately from those witnesses in the same receipt.

Legal source-pixel subdivision improves the layout to 82 OAM entries,
25 peak sprites and 34 tile slivers, with a 15-write interval-pressure bound.
Its sixteen-write integer cache is OPTIMAL in 6.094 seconds: 421 total writes,
eight-line maximum prefetch and zero integer constraint violations. All
576 eligible bank permutations still require at least 376 optimistic clocks
at those fixed write times. Constrained sixteen/nineteen-write cache searches
return UNKNOWN. A compiled physical witness and lifetime recoloring remain
above the transfer window. These measured results preserve geometry limits
and exact source alpha, and do not reject other encoding/residency choices.

An explicit isolated-context experiment also allows pieces to change math
class by recompiling their palette operands. Original encoding bank domains
remain attached to the input pieces. The exact source-bound window/mode
replay verifies the output over all 57,344 pixels, including pieces that cross
the opaque/math bank boundary. Geometry remains 82/25/34. The interval bound
falls to 14.857143; the validated fractional cache lower bound is 15.933333,
with primal residual 1.42e-14 and dual residual 1.11e-16. A sixteen-write
integer cache is OPTIMAL in 6.969 seconds, with 444 total writes and eleven-line
prefetch. Its current optimistic peak is 376 clocks. This experiment claims
no concurrent-actor reservation or native alpha admission. Source colors and
rendered alpha remain exact; no compatibility approximation is selected.

The 180-second constrained re-encoding cache and 180-second flexible
rectangle-lifetime search return UNKNOWN. A seven-iteration cache-cut search
retains its initial bank assignment as the best fractional DMA bound at
274.474279 clocks; this is not an improvement over that assignment. A distinct
evaluated assignment with a 288.713445-clock fractional bound is also replayed
and tested, but its integer window-constrained cache returns UNKNOWN.
Complete RGB555 inverse operand covers inspect all 32,768 operands per math
bank; the fixed-mode physical search returns UNKNOWN at 120 seconds.
Allowing exact math modes and windows to change by scanline also returns
UNKNOWN at 120 seconds. These results do not establish infeasibility or
select the BG fallback. Full source output and bounded search evidence remain
in the authored receipt and archive.

Joint fixed-piece bank/class/slot scheduling also returns UNKNOWN at its
120-second limit. This is retained without an infeasibility claim.

The separate plain precomposited OBJ family has a stronger measured limit.
Exact RGB8 SCREEN over the authored background produces 541 distinct RGB555
effect outputs and 64 peak scanline colors after omitting 83 pixels whose
output equals the underlay. Rows 128â€“135 require 275 distinct colors. Even
granting 120 resident opaque slots, 155 colors must enter over seven HBlanks,
forcing at least 23 commits in one HBlank. Prepared DMA ranges must cross
transparent bank slots or pay another range setup; the best possible span
is 368 master clocks, above the full 356-clock window. This rejects that
prepared-DMA precomposited family independently of piece bank assignment
and lookahead. It does not reject mixed color math, other transfer mechanisms,
or lossless raster presentation universally. The generic interval tool keeps
its prior pool relaxation by default and makes the stronger bank-gap bound
explicit. Eight focused interval/partition tests pass. The stronger bound
requires the SNES eight-clock DMA byte domain and at most 120 opaque slots.
No color reduction
or alpha adaptation is selected.

The bank-residency solver now offers a feasibility-only objective and reports
the emitted witness's independently recomputed ideal DMA cost. Both search
objectives retain physical-slot and native-admission nonclaims. Six focused
residency tests pass, including feasibility-only CP-SAT and HiGHS replay.
The original six-bank logical input produces a complete source-exact witness
in 4.568 seconds with 19 peak writes, ten-line prefetch and a 336-clock ideal
bound. Its emitted physical placement requires 968 clocks. Later recolored
inputs do not retain the original ideal bound: one has 352/368-clock rows.
This explains why it cannot serve as a feasible hint inside a 345-clock
residency search. The complete witness and bounded search reports are retained
without claiming improved physical admission.

At those fixed write times, the complete physical rectangle-lifetime model
is INFEASIBLE at 345 clocks in 33.196 seconds. Allowing one-line retiming
around the verified physical hint returns UNKNOWN at 50 seconds. Both results
are restricted to the stated lifetimes and bank assignment. Hint comparison
now normalizes empty derived demand rows while retaining real row colors,
piece geometry, frame hash and independent pixel-mask checks; four focused
hint/timing/source-control tests pass.

A separate source-exact subdivision experiment splits eighteen pressure-row
parents into legal 8Ã—8 pieces. Geometry reaches 128 OAM entries, 32 sprites
and 33 tile slivers; it is effect-only and makes no concurrent-actor admission
claim. Exact math-class re-encoding has a validated fractional write bound of
16.666667 with primal residual 3.20e-14 and dual residual 1.11e-16, so the added
geometry does not improve the measured bound. Row/word fixed-bank mask search
retains its initial assignment as best at 287.824510 fractional DMA clocks.
Its alternate assignment needs 360.062024 fractional clocks; another has no
fractional cache solution. These results do not establish a universal lower
bound. Complete source replays and restricted search evidence are retained.

Minimizing ideal bank-transfer span with the original residency hint produces
a different complete cache witness: 401 writes, 19 peak writes, six peak
write-active banks and a 336-clock ideal span. Its fixed-family objective
lower bound is 305 clocks at the 50-second limit. Lifetime recoloring preserves
every viewport pixel but requires 504 physical clocks. Joint bank permutation
and physical placement at the original fixed times returns UNKNOWN at
345 clocks. These witnesses remain unadmitted; no fallback is selected.

The same bank-permutation model returns UNKNOWN at 353 clocks. Limiting the
original encoding to five write-active banks also returns UNKNOWN. Neither
result proves a hardware limit.

A separate complete-operand class-capacity relaxation permits all four shared
scanline math modes and a two-window transition superset on rows 125â€“145.
With only the sixty upper-bank slots, the validated fractional write bound is
26.771574, forcing at least 27 integral writes and rejecting that prepared-DMA
family even before bank assignment. Adding 15, 30 or 45 lower-class slots gives
bounds 19.937500, 16.500000 and 13.645833. Initial residency and preloading are
optimistic; geometry, fixed banks and physical slots remain relaxed. These
measurements identify capacity tradeoffs without reserving actor resources or
claiming a complete frame schedule. No compatibility alpha approximation is
selected.

The five-bank-capacity integer pool remains UNKNOWN at both 20 and 21 writes
and under a feasibility-only objective. The generic bounded-integer backend
now accepts that objective explicitly and never marks it cost-optimal.
Eight matrix-constraint tests and nineteen existing mode/liveness tests pass;
every consumer still independently replays an emitted incumbent. No five-bank
schedule or concurrent-actor reservation is admitted by these searches.

The six-bank-capacity integer pool at seventeen writes also returns UNKNOWN.
The mode/liveness solver now accepts soft mode/window-only hints separately
from palette residency. Such hints may be changed by the solver; they pin no
variables and grant no source or hardware admission. Twenty-one mode/liveness
tests and eight bounded-integer matrix tests pass, including examples where
the solver must change a hinted mode and wrong window gates to meet the
required write budget. A source-bound control hint from the verified original
encoding still returns UNKNOWN at seventeen writes in 51.300 seconds.

With the same six-bank capacities and source control hints, a twenty-one-write
integer pool is found in 25.560 seconds. Its residency, source-pixel coverage
and compiled windows replay over rows 125â€“145. This is a pressure-interval
witness, not a full-frame, fixed-bank, physical-slot or native schedule.
The full-frame integer extension and full-frame fractional run both reach
their bounded limits without a candidate or validated bound.

The generic source-pool constructor now accepts explicit eligible bank sets
within each OBJ math class. Defaults remain the existing four/four split.
Exact replay tests also restrict construction to opaque bank 3 and math bank 7,
including joint geometry and persistent-index modes. Wrong classes, duplicate
and empty bank sets fail explicitly. Four focused construction tests pass.
This expresses resource domains without claiming that banks left outside an
effect domain admit another actor automatically.

The pressure-interval controls now also seed a complete source-exact six-bank
construction. A generic optional preference selects valid ADD operands outside
the controlled interval before literal colors; full-frame window descriptors
record the existing full-ADD default explicitly. Five construction tests pass.
The 119 eight-by-eight pieces use 30 sprites and 30 tile slivers at peak. Exact
compaction gives 56 OAM entries, 20 sprites and 34 tile slivers. These are effect
geometry measurements only: leaving banks 0 and 1 unused does not admit concurrent
actors, and the compact construction leaves no tile headroom on its peak line.

The initial assignment has a validated fractional cache bound of 27.4 writes.
A bounded bank rebalance reduces it to 23.714286, still forcing at least 24
integral writes and a minimum prepared transfer span of 384 master clocks,
above the measured 356-clock window. Twelve cache-cut iterations do not improve
that assignment. Separately pooling its fixed exact operands within the two
math eligibility classes, with capacities 30 and 60, gives a validated bound
of 20.2 writes. That optimistic relaxation permits bank reassignment and forces
at least 21 writes; it is not an SNES palette schedule or hardware admission.
These results reject the measured fixed assignment, not lossless raster
presentation. All 57,344 viewport pixels replay exactly; no color reduction or
alpha approximation is applied, and no authored peak native proof is claimed.

A fifteen-iteration cache-cut search on the uncompacted 119-piece encoding
finds no qualifying improvement: its best fractional bound is 24.733333
within 50.484 seconds. This is another bounded fixed-encoding search, not a
universal feasibility verdict. Eighty-three focused constructor, mode/liveness
and Boolean backend tests pass, including their imported coverage.

A warm start from the source-verified 21-write pressure-interval pool returns
UNKNOWN at 18 writes. A separate movable-mode/window residency run on the
56-piece six-bank construction also returns UNKNOWN at the conservative
345-clock threshold. Neither result rejects raster. Holding the pressure
controls fixed and permitting exact operand choices across the full frame
gives a validated class-pool lower bound of 20.2 writes; an 18-write integral
run proves that restricted control/operand family infeasible. Bank assignment
and physical transfer remain relaxed in this bound.

The full-frame fixed-mode relaxation with movable window eligibility yields
a validated fractional write bound of 20.000000. This allows all exact operands
under each selected mode and relaxes bank assignment, integer residency and
physical slots. It does not constitute an emitted window or hardware schedule.

A seven-bank domain (opaque 0–2, math 4–7) leaves bank 3 outside the effect
domain. The pressure-control construction preserves the full viewport with
119 OAM entries and peaks of 29 sprites and 29 tile slivers. Its initial fixed
assignment has a validated 30-write fractional bound; bounded rebalancing
reduces that to 22.5, still forcing 23 integral writes. Actor coexistence is
not admitted.

Separately, a full-frame fixed-control class-pool relaxation with capacities
45 and 60 gives a validated fractional bound of 17.333333. An integral
18-write witness is found in 8.515 seconds and independently replayed against
all 2,668 encoded authored source pixels; the 83 exact underlay matches remain
bypassed. This is a complete-frame pool witness with fixed source controls,
not fixed OAM banks, physical slots, transfer timing or concurrent admission.
The generic piece constructor is being evaluated against its resident colors.

Mapping the full-frame 18-write pool to global fixed-word banks initially
requires 136 eight-by-eight pieces, exceeding OAM. Generic legal 16×16
compaction preserves exact source pixels and yields 127 OAM entries, 27
sprites and 29 tile slivers. Minimizing OAM instead gives 58 entries, 20
sprites and 34 tile slivers. These two constructions are effect-only; the
compact variant provides OAM space but leaves no tile headroom at its peak.
The pool's 18-write bound does not carry over automatically to either fixed
bank assignment. No native or concurrent admission is claimed.

The generic compactor now accepts explicit concurrent OAM/sprite/tile geometry
reservations, including the complete rows added by transparent padding. Seven
focused tests pass. Applying the measured He_Man freespecial4 frame-6
reservation (33 OAM entries, per-line sprite and tile arrays) proves the
136-piece pool-derived encoding's available 16×16 merge family infeasible.
This preserves the evidence and rejects only that fixed encoding/merge family;
palette/layer admission and more general geometry remain separate. No
concurrent proof or universal raster rejection is asserted.

The full-frame fixed-control class-pool family proves 17 writes infeasible,
consistent with its validated 17.333333 fractional bound and 18-write
witness. The denser pool-derived geometry's bounded rebalance still has a
validated fixed-bank lower bound of 22.133333 writes, forcing 23 and exceeding
356 clocks even with ideal prepared transfer packing. A one-second master
search on the original seven-bank small pieces returns UNKNOWN before a new
assignment; its initial 30-write bound is retained as restricted evidence.

The generic constructor now optionally assigns one fixed bank per local 8×8
class piece, allowing an identical RGB555 word to occupy different banks in
different pieces. It does not change an OAM bank between rows. Applying this
family to the source-verified full-frame pool reduces geometry from 136 to
100 OAM entries and from 29 to 19 peak sprites/tile slivers. Compaction with
the explicit He_Man geometry reservation then produces 74 effect entries,
18 sprites and 26 tile slivers; combined geometry is 107 OAM entries, 23
sprites and 34 tile slivers. This proves only geometric capacity with that
measured reservation, not source compositing, palette, timing or concurrent
actor admission. Thirteen focused construction/compaction tests pass.

A separate ten-iteration bank/cache cut run on the original seven-bank
pressure encoding improves its validated fractional bound from 22.5 to
21.944444. This still requires at least 22 writes and does not admit an
integer/physical schedule. All full geometry witnesses are retained with
exact viewport replay; failed merge families are retained without a replay
or admission claim from the evidence retainer.

Local piece witnesses preserve their explicit bank domains for every later
optimizer; bank 3 remains excluded. A bounded cache-cut run on the 100-piece
local encoding gives a best validated fractional bound of 23.142857 across
nine iterations. A separate compaction-preserving bank rebalance does not
admit transfer timing. The source geometry reservation remains unchanged.

The source-bound joint search on the corrected 74-piece local encoding
preserves per-pixel operands, math classes, rectangles and bank domains while
searching new fixed banks and cache residency. At the conservative 345-clock
prepared-transfer threshold it returns UNKNOWN in 50.255 solver seconds
(103,278 variables and 258,627 constraints). The hint is soft. This is not
an infeasibility verdict or native admission.

An exact full-frame word-cover variant also fits the measured player geometry:
74 effect entries, 18 sprites and 25 tile slivers; combined peaks are 107
entries, 23 sprites and 33 slivers. Its initial fixed-bank fractional cache
bound is 33 writes. The earlier local encoding's domain-preserving rebalance
has bound 23.583333, forcing 24 writes and exceeding the measured window.
The word-cover DMA-cut search has no candidate because its initial fixed-bank
LP is infeasible under the 21-write cap; this is a restricted initial
assignment failure, not a universal raster or bank-assignment verdict.

Two constant class-write partitions on the local fixed-piece encoding are
rejected: opaque/math caps 12/9 and 15/6 both prove opaque fixed-bank
assignment infeasible under all eight-row interval cuts. These are necessary
cache-write constraints for those explicit constant class caps. They do not
reject variable per-line class budgets, alternate exact operand selection,
additional legal pixel masks or lossless raster generally.

A physical greedy run on the earlier effect-only encoding, with 55-line
lookahead, sixteen bank/slot beams and sixteen frame beams, fails at line 128
under the 345-clock threshold. Heuristic failure is retained without a
hardware infeasibility claim.

The row-word mask cache-cut family now includes the explicit measured player
geometry reservation. Its short master returns UNKNOWN. Resuming the
independently certified cut with twenty-second masters improves the best
validated fractional bound from 32.666667 to 25.571429 over three iterations
in 67.094 seconds. Any emitted assignment must still satisfy the complete
OAM rectangles plus player reservation. Neither this fractional result nor
its unproved integer extension admits transfer timing or concurrent palettes.

Extending the geometry-reserved row-word search to sixteen iterations, with
thirty-second masters and restored verified cuts, completes six iterations
in 203.735 seconds. Its best fixed-assignment fractional bound is 24.583333,
forcing at least 25 writes for that selected encoding/assignment. Geometry
remains checked against the measured player arrays, while concurrent palettes
and source compositing are unproved. Other assignments and operands remain
open; this result does not reject raster universally.

An eight-row word-epoch construction removes global frame-long word-bank
identity, retaining one bank for each emitted OBJ mask. With conservative
effect limits of 95 OAM entries and 24 tile slivers, and necessary prepared
transfer interval cuts at 345 clocks, the bounded run returns UNKNOWN in
50.134 seconds (7,769 variables and 32,383 constraints). These constant
geometry limits reserve the player's maximum resource demand on every row,
so they are deliberately more restrictive than its measured row arrays.
They do not prove a universal concurrent limit or a physical schedule.

The corrected source-bound joint fixed-rectangle/operand search also returns
UNKNOWN after 600.472 solver seconds, with 249,414 conflicts. A no-hint
SAT-only feasibility run returns UNKNOWN after 120.255 seconds, with 222,809
conflicts; it retains the same source, bank-domain, geometry and prepared
transfer constraints. The eight-row word-epoch SAT run returns UNKNOWN at
120.059 seconds. None of these time limits establishes a hardware boundary.
