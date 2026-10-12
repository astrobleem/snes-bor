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
output equals the underlay. Rows 128–135 require 275 distinct colors. Even
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
parents into legal 8×8 pieces. Geometry reaches 128 OAM entries, 32 sprites
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
scanline math modes and a two-window transition superset on rows 125–145.
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
and compiled windows replay over rows 125–145. This is a pressure-interval
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

Reopening exact operand choice while retaining the 74-piece source geometry,
original math classes and eligible bank domains also returns UNKNOWN after
120.246 seconds. This trial removes the prior preserved-word restriction,
keeps one fixed bank per rectangle/class, and enforces the favorable 345-clock
prepared partition bound with 21 writes and 55-line prefetch. Its 103,209
variables and 258,576 constraints produce no witness or infeasibility proof.

Eight-bank tests are explicitly HBreath-only, not a gameplay palette reservation.
The pool-derived local encoding has 100 objects and 19 sprites/slivers; exact
16×16 compaction yields 68 objects, 20 sprites and 29 slivers. Rebalancing lowers
its interval objective to 21, but its validated full cache bound is 22.6 writes,
which rejects this fixed encoding against the measured transfer window. A
viewport-aligned alternative retains 107 objects/19 sprites/slivers and has
validated bound 21.444444 after rebalancing.

Using capacities 60/60 with the selected pressure controls produces a complete
16-write integer pool in 9.459 seconds. Independent source replay covers all
2,668 non-bypassed pixels. A local encoding retains 103 objects/19 sprites/slivers;
its rebalanced full cache bound is 22.000000. A viewport-aligned encoding retains
111/19/19 and has bound 21.562500. Twelve alias-aware decomposition iterations
retain the 22-write bound, without claiming assignment optimality. A global
word-bank encoding compacts from 138 objects to 55/18/32 but has cache bound 31.
Restricting each two-row bank union to fifteen words creates 162 objects and
36 sprites/slivers, exceeding hardware geometry. These measured failures apply
to the respective encodings, not the generic raster strategy. Native execution,
concurrent actor admission and a live compositor remain unproved.

Mapping the complete 16-write pool's uninterrupted color lifetimes into actual
banks with mixed 8/16 geometry and a favorable 345-clock transfer partition
returns UNKNOWN after 120.084 seconds (23,381 variables, 85,109 constraints).
A transfer-relaxed 16-write trial that extends every selected color's first
interval to VBlank is INFEASIBLE. This is an explicit restricted preload policy,
not a general initial-palette theorem. Keeping later interval loads at their
saved natural times instead returns UNKNOWN at 120.075 seconds. A bounded
full-frame reoptimization of all four math modes and windows at 16 writes also
returns UNKNOWN at 164.315 seconds. No native frame is emitted from these trials,
and none rejects general raster scheduling or selects an alpha adaptation.

Eight-line residency chunks permitting up to two charged bank copies per color
return UNKNOWN at 120.082 seconds in the transfer-relaxed 21-write trial. The
specified mixed geometry and source-pixel ownership constraints still apply.
Its 24,461 variables and 50,517 constraints preserve all source alpha/output
requirements. A separately replayed fractional relaxation has primal violation
9.42e-14 and supplies 8,289 soft integer hints; no variables are pinned. The
hinted integer search continues without treating the relaxation as a witness.

The soft-hinted chunk trial returns UNKNOWN at 120.081 seconds, after
2,152,805 branches and 1,417,448 conflicts. It preserves the fractional hint
validation as solver evidence, not a bank assignment, palette schedule or
hardware rejection.

Restricting the exact decomposition to one ADD mode and a fully enabled color
window produces a complete 16-write class-pool witness in 11.338 seconds. This
still targets BOR4086 RGB8 SCREEN output exactly, using computed operands or
literal output words; it does not select the measured SCREEN-to-ADD adaptation.
The local and full-frame word covers each fit 99 pieces and 19 sprites/slivers.
Rebalanced fixed-bank bounds are 22.454545 and 21.666667, respectively. A
29-iteration cache-guided single-piece bank search reduces the latter to a
validated fractional bound of 21.000000. Whole viewport pixel replay remains
exact. Integer residency, physical slots and DMA/native admission remain open.
The constant-control chunked joint search independently returns UNKNOWN at
120.082 seconds, without a hardware rejection.

The constant-control cache admits an OPTIMAL integer 21-write schedule in
15.844 seconds: 582 noninitial writes, five-line maximum prefetch latency,
complete source pixel/color identity replay and zero integer constraint
violation. Its ideal prepared span is 456 clocks, so it is not a hardware
candidate. A complete prepared-flow search at 345 clocks returns UNKNOWN at
121.062 seconds. The separate fractional DMA-guided cache bound for the initial
assignment is 385.363564 clocks even after granting all adjacent bridge savings;
this rejects that fixed bank assignment at the measured transfer window.

The DMA-guided tool encountered tiny positive numerical solver multipliers at
strict dual-certificate replay. Fresh solver values up to 1e-9 are now clipped
inward to zero before certificate installation; actual positive multipliers
fail explicitly. Strict resumed-certificate sign and stationarity checks remain
unchanged. Ten focused tests pass, including invalid-certificate rejection and
seed-bank diagnostic ordering. This changes only offline tooling, with no
production assembly or bank-zero growth.

Using the verified integer cache as a soft hint still returns UNKNOWN at
121.141 seconds for the complete 345-clock flow search. Reopening assignment
selection under an unconstrained 120-word count ceiling improves the optimistic
fractional DMA span from 385.36 to 354.586291 clocks after 13 evaluations. That
ceiling is a search relaxation, not a runtime bandwidth allowance. The selected
assignment still fails the conservative 345-clock gate; source pixel identity
replays across the whole viewport, while integer transfers and native admission
remain unproved. A resumed bank search retains independently checked dual cuts
and continues from this assignment.

The resumed fixed-piece DMA search retains the 354.586291-clock fractional
bound. Integral optimistic packet costs are multiples of eight clocks, so that
specific assignment needs at least 360 clocks and exceeds even the measured
356-clock maximum window. This rejects that assignment, not raster generally.

Allowing source-exact row/color masks lowers the validated fractional DMA bound
to 337.554147 clocks. The resulting fixed-bank geometry uses 128 OAM entries,
32 sprites and 32 tile slivers at peak. It fits the isolated effect but leaves
no sprite headroom on its peak line; concurrent gameplay is not admitted.
The independently validated fixed-cache lower bound is 19.733333 writes.
An OPTIMAL integer cache at a 21-write ceiling preserves every viewport pixel,
uses 566 noninitial writes and needs at most four lines of prefetch. Its ideal
transfer span is 456 clocks, so it is not a native candidate. The complete
345-clock integer flow and joint row-mask searches both return UNKNOWN.
Physical slots, actual transfer timing and concurrent actors remain open.

The earlier HiGHS trial accepted the residency hint argument, but its SciPy
MILP adapter does not pass a warm start to HiGHS. That trial is retained as an
unhinted bounded search; it supplies no evidence about warm-start effectiveness.
A CP-SAT search now receives the independently verified integer cache as an
actual soft hint. No source alpha adaptation or color reduction is selected.

The actual CP-SAT hinted flow search proves INFEASIBLE at 345 clocks in
31.074 seconds for this fixed row-mask assignment and 21-write ceiling. This is
a family-scoped rejection, not a universal raster verdict. The independently
constrained physical-slot search returns UNKNOWN at 121.173 seconds. Backend
reports now distinguish an accepted hint argument from a hint consumed by the
solver; all 20 focused residency tests pass, including both backend reports.

The 353-clock CP-SAT flow search returns UNKNOWN after 120.173 seconds.
Its family lower bound is 346 clocks (at least 352 after integral packet-cost
rounding), rather than a witness. Six further bank-refinement evaluations retain
the 337.554147 fractional incumbent; none supplies a physical/native schedule.

A feasibility-only 353-clock integer search returns UNKNOWN at 180.187 seconds.
Two- and 32-decision local searches retain the same fractional incumbent; a
compacted-rectangle variant reaches 353.163436 clocks, which rounds above the
measured maximum for that assignment. Exact isolated compaction reduces the
128-entry row-mask witness to 85 OAM entries, 23 sprites and 34 tile slivers.
Adding the independently measured player geometry makes that compaction family
INFEASIBLE. Palette and layer concurrency remain unproved.

The joint bank/cache solver now accepts independently replayed source-exact
assignment hints across different mask geometry. It verifies every pixel's
owner, word and bank eligibility and checks source/control identity. Conflicting
coarser decisions are omitted from the hint; no choices are pinned. Seven
focused tests pass, including malformed hint rejection and proof that a legal
four-object hint cannot admit an infeasible two-object configuration. The new
hinted full joint search continues without claiming physical/native admission.

The complete joint search consumes 1,908 independently validated soft bank-choice
hints and the integer cache residency, then returns UNKNOWN at 180.485 seconds.
It reopens every row/color bank choice under the real 128/32/34 geometry limits;
no palette transfer or source-geometry constraints are removed. The result does
not reject raster or prove any gameplay palette reservation.

The adjacent-only range family is INFEASIBLE at 353 clocks in 65.128 seconds.
This does not resolve the general flow search: a nonadjacent range can bridge
an intervening complete bank and remains allowed by that model. The hinted
joint SAT trial independently returns UNKNOWN at 120.331 seconds; 101,110
branches and 18,369 conflicts do not constitute an infeasibility certificate.

Four alternative evaluated row-mask assignments are reconstructed with strict
bank-domain checks and complete operand replay. They use 117..128 OAM entries
and 31..32 sprites/slivers. Two complete fixed-bank 345-clock cache searches
prove INFEASIBLE in 61.382 and 60.052 seconds. These reject those assignments,
not other bank choices. The generic joint solver now offers the existing
SAT hint-repair policy; all seven focused tests pass, including rejection of
the geometrically impossible hinted fixture.

The two additional fixed assignments remain UNKNOWN after 75-second complete
353-clock flow searches at 21 writes. A broader trial now permits 22 writes:
twenty-two words in two adjacent banks can have a 352-clock ideal packet span.
That count is excluded by the conservative 345-clock gate, but must not be
excluded merely by the earlier 21-write search ceiling when testing the larger
measured window. Phase-safe native timing is still a separate gate.

The 22-write complete-flow and adjacent-only 353-clock trials remain UNKNOWN
at 120.263 and 90.257 seconds. Joint SAT hint repair remains UNKNOWN after
150.246 seconds; it supplies neither an assignment nor a rejection. Peak-span
objective hints now derive from the actually selected residency hint instead
of the unrelated input greedy trace, so an integer incumbent can guide span
optimization at a deliberately looser window. All twenty residency tests pass.

An incumbent-based CP-SAT span minimization at a deliberately loose 465-clock
window finds an exact 22-write cache with a 440-clock optimistic peak. It uses
569 noninitial writes and at most eight lines of prefetch. The family lower
bound is 345 clocks, rounded to at least 352 by integral packet costs; neither
the upper nor lower bound is native admission. All 576 eligible bank orders
retain the 440-clock peak. Emitting unchanged physical slots costs 1,256 clocks,
so that diagnostic packet witness cannot run safely. Cache lifetimes and slot
packing remain separate constraints; another incumbent optimization continues.

The next incumbent optimization reduces the ideal peak to 424 clocks after
180.216 seconds: 22 peak writes, 587 noninitial writes and 24-line prefetch.
A separate LNS trial retains 424 clocks after 180.155 seconds, with 615 writes
and 25-line prefetch. A fractional-cache/integer-range HiGHS trial returns
UNKNOWN after 91.047 seconds. None fits the measured transfer window. The next
source-bound search keeps every physical piece bank and pixel ownership fixed
while reopening exact operands; geometry and source alpha remain unchanged.

Reopening all exact operands while retaining every physical pixel owner/bank
returns UNKNOWN at 120.116 seconds (42,245 variables, 108,902 constraints).
SAT repair also remains UNKNOWN at 180.169 seconds. Source controls and alpha
stay exact; neither result rejects other geometry, encodings or schedules.

The optional native HiGHS 1.15.1 interface now supplies the validated soft MIP
start through its setSolution API, unlike SciPy's adapter. It uses the same
explicit linear constraints, integer domains and independent incumbent replay.
Tests compare exact pixels and the optimal span across backends and confirm
that a warm start cannot make an impossible write budget pass. All 22 residency
tests pass. This is an offline dependency; the ordinary compiler/runtime path
and bank zero remain unchanged. Interface authority is the
[official HiGHS Python documentation](https://ergo-code.github.io/HiGHS/dev/interfaces/python/example-py/)
and the installed version's typed API.

The native HiGHS trial consumes all 39,124 hinted variables and retains the
424-clock integer witness after 121.375 seconds. It replays with zero constraint
violation but supplies no improved hardware candidate or lower-bound verdict.
Nonfinite incumbents now fail explicitly instead of entering witness replay.

Exact bank-mask retiling on an 8/16 grid reduces the isolated witness to 71 OAM
entries, 20 sprites and 32 slivers, preserving every pixel's bank and slot.
Three other sampled grid phases are INFEASIBLE in that aligned family. The
71-entry cover plus the complete measured player reservation uses 104 OAM
entries but reaches 40 slivers. A separate horizontal 8-pixel coverage bound
is only 31 combined slivers, so this does not reject non-grid packing. The
reservation includes the entire player geometry without shared occlusion;
concurrent palette, alpha and layer admission remain separate.

A generic sampled non-grid mask cover now preserves each visible source pixel's
owner, fixed bank and physical slot while considering legal 8/16 or 8/32
rectangles anchored on pixel corners/midpoints and the input rectangles. Its
constraints count full transparent padding, OAM, sprites and slivers, with an
optional complete per-line actor reservation. Four focused tests pass, including
opaque black, unchanged palette traffic, reservation rejection and ambiguous
visible ownership rejection. Source metadata/dimensions are retained; changed
geometry requires fresh native validation.

The isolated sampled 8/16 cover improves to 70 OAM entries, 19 sprites and 30
slivers after 60.255 seconds. It preserves the 424-clock palette cache, which
still exceeds the measured window. Two player-reserved searches remain UNKNOWN
at 45.196 and 60.452 seconds. These are bounded candidate-family results, not
universal geometry or raster rejections; palette/layer concurrency is unadmitted.

The player-reserved repair trial remains UNKNOWN after 90.256 seconds. Valid
per-bank horizontal interval cuts now strengthen the sampled geometry model:
each bank's opaque pixels require at least their exact eight-pixel interval
coverage, and full rectangle padding still counts. The combined lower bound
is 31 slivers. A 90.321-second trial with these cuts remains UNKNOWN, with no
incumbent; it does not reject arbitrary legal packing. All four focused tests
pass, including a reservation whose measured lower bound exceeds 34 slivers.

Reopening whole-piece bank choices on the 70-entry non-grid witness evaluates
twelve assignments in 89.547 seconds. The best fractional transfer lower bound
remains 337.554147 clocks. This relaxation is not an integer transfer schedule,
and the complete 424-clock witness remains above the measured hardware window.

Equivalent-mask reduction removes 2,610 rectangle choices only when their
opaque pixel sets and full per-line hardware costs are identical. Input
rectangles receive preference to preserve the soft start. The reduced CP-SAT
player-reserved trial remains UNKNOWN after 90.343 seconds; an 8/32 trial also
remains UNKNOWN after 90.409 seconds. Row-word bank reopening evaluates eight
assignments in 130.250 seconds without improving the fractional timing bound.

The optional native HiGHS backend finds a source-exact player-reserved 8/16
cover after 91.234 seconds: 87 HBreath rectangles plus 33 reserved player
rectangles, 120 combined OAM entries, 26 sprites and 34 slivers at peak. Every
source pixel retains its owner, bank and physical slot; the palette trace is
unchanged. The integer constraint replay has zero violations and the complete
authored viewport is replayed separately by the retainer. All 27 geometry and
residency tests pass. This proves this geometry reservation only: player
palette/layer concurrency, authored reachability and native transfer admission
remain unproven, and the unchanged 424-clock cache still exceeds the window.
