# Concurrent source piece-bank rebalance

The source-exact retarget geometry remains 73 legal 8/16 OAM pieces,
18 sprites and 34 tile slivers at the scanline peaks. The generic piece-bank
balancer may change effect bank assignments inside their declared seven-bank
domain; the player stays in bank 3. Every piece's selected bank remains fixed
across its rows. Equal RGB555 words in one bank count once.

The necessary interval objective improves from 15.0 to 14.25 writes per line
after 9,443 sampled proposals and 3,384 accepted moves. This objective is not
a complete cache or physical transfer proof. The validated fractional cache
lower bound for the chosen assignment is 15.25 writes per line, with zero
dual residual and primal violation below 8e-15.

HiGHS produces an OPTIMAL write-minimizing integer cache in 12.016 seconds:
363 noninitial writes, a 21-write cap, two-line maximum prefetch latency and
a 416-clock ideal peak. A complete flow search produces another valid cache
in 90.094 seconds with a 296-clock ideal peak, 17 peak writes, 406 total
noninitial writes and 16-line maximum noninitial prefetch latency. Its
restricted-family lower bound is 269 clocks. Physical endpoint slots remain
relaxed in that result.

Independent source composition and palette replay match all 57,344 viewport
pixels, including 5,936 visible OBJ pixels, for the new assignment and both
cache schedules. The viewport hash remains
`7ea29ce30140a7ce840e5bec6ca9ad789978d195528aadaaf50c8e0cb4721450`.
Two focused piece-bank balancing tests pass. No geometry is reduced.

Exact physical placement at 344 clocks with the supplied write times returns
UNKNOWN after 90.077 seconds. It is not a native candidate or a raster
rejection. A broader diagnostic produces a source-exact 480-clock physical
layout. Four local cache-and-slot repairs reduce that peak to 424 clocks,
with three accepted complete witnesses. The 21-write cap and necessary
344-clock ideal bank bound hold across the entire frame. Independent source
replay also verifies the accepted physical witness. It remains above the
native window. Native concurrent admission, authored-stage peak alpha, live
composition and leases, compiler integration and the full MOTU Demo remain
open. NO color reduction or alpha adaptation applied.

Six further local repairs retain the 424-clock peak and reduce aggregate
commit cost from 10,064 to 9,904 clocks. Independent source replay again
matches all 57,344 pixels and the same viewport hash. A complete free-residency
search with 541 idle bank rows collapsed returns UNKNOWN after 60.225 seconds;
a forced 408-clock local repair returns UNKNOWN after 45.109 seconds. Neither
result rejects raster presentation.

Restricting this geometry to four or five effect banks plus player bank 3,
while preserving the necessary 21-write interval bound, produces INFEASIBLE
results in 11.302 and 12.318 seconds. These results apply only to those fixed
geometry/domain/bandwidth families. They do not reject seven effect banks,
other player allocations, generic subdivision, or raster presentation.

The generic physical solver can optionally preload banks whose complete-frame
color union fits fifteen slots, retaining a fixed slot layout and eliminating
their later writes. Sixteen focused tests verify packet and pixel identity,
including opaque RGB555 zero and a mixed static/dynamic bank case. This
concurrent assignment has bank word unions of 51, 26, 52, 31, 26, 25, 74 and
52, so no bank qualifies. In particular, the player bank itself requires
raster updates. The same-size complete search with this option returns
UNKNOWN after 60.132 seconds; it does not establish a new admission bound.

A broader bank relabel experiment makes all eight banks eligible for both
actors in this controlled precomposited context. It tests 22,479 permutations
and 256 slot reflections each in 45.047 seconds, without improving the
424-clock peak. The time limit leaves that family nonexhaustive.

The generic `raster_physical_slot_permute.py` instead searches arbitrary fixed
permutations of the fifteen opaque slots in each bank. A fixed permutation
preserves every source word, its cache lifetime, write time, OAM bank and
geometry; pixel indices and packet data are remapped offline. The first
100,000 proposals reduce the physical peak to 408 clocks in 6.515 seconds;
300,000 further proposals reduce it to 392 clocks in 19.031 seconds. Both
complete physical witnesses replay all source pixels and CGRAM packets.
The peak write count remains 17. These witnesses remain above the measured
344-clock native window. Two focused permutation tests plus nineteen existing
packet/layout regression tests pass, including input immutability and aliased
prefetch-event lists. No native or gameplay admission is claimed.

Six local cache repairs of the 392-clock witness retain that peak and reduce
aggregate transfer cost from 9,936 to 9,792 clocks. Five complete candidates
are accepted; independent source replay again matches the complete viewport.
The full-frame 21-write cap and necessary bank-window check remain valid.

An exact 344-clock fixed-slot permutation search on the repaired cache returns
UNKNOWN after 60.054 seconds (4,536 variables, 8,843 constraints). A third
500,000-proposal heuristic retains the 392-clock peak, reducing the summed
excess above the requested 344-clock ceiling from 272 to 192 clocks. This is
progress within a restricted permutation family, not hardware rejection.

Selective subdivision of the five highest-union effect pieces intersecting
rows 125--147 produces 86 legal OAM entries, 20 sprites per scanline and 34
tile slivers. Full source replay remains identical. Subdivision of all 25
selected parents instead reaches 128 entries, 28 sprites and 32 slivers;
that exploratory geometry leaves no spare OAM entries for another actor and
is not a gameplay resource allocation. Bank balancing on the five-parent
geometry does not improve its interval objective. Restricting it to five
effect banks plus player bank 3 under the same necessary interval bound is
INFEASIBLE after 37.462 seconds, still only a geometry/domain family result.

The generic bank balancer now offers optional paired exchanges to cross
single-move capacity barriers, equivalent-best assignment sampling and a
peak-only interval objective. These remain source-derived heuristics with
independent full pixel replay. The default retains its original random draws,
assignment and compiled schedule hash: `bc1a1bb1db93506cfa6019c23393b66bf7e2b3ba63b8bbe89017837f818c25f7`
on the focused regression fixture. Three focused tests pass. Paired exchanges
alone do not improve the five-parent interval objective, and no physical
admission is asserted for those outputs.

Allowing both actors to share all eight eligible banks in the controlled
precomposited context, with paired exchanges and a peak-only objective,
reduces interval peak pressure from 14.25 to 13.5 writes per line. Geometry
stays at 73/18/34 and all viewport pixels replay identically. Mean interval
pressure increases from 2.157931 to 4.007333. Its independently validated cache
LP lower bound is 16.954545 writes per line (integer schedules need at least
17); maximum primal violation is below 9e-14 and dual residual below 4e-16.
This is not physical admission and does not allocate exclusive ownership of
all eight banks to the effect. Both actors' actual row demand is included.

A second shared-bank pass retains the 13.5 interval peak and reduces mean
pressure to 3.058660. Its validated fractional cache bound falls to
15.555556 writes per line, so integer schedules need at least sixteen.
Primal violation is below 1.1e-14 and dual residual below 3e-16. The complete
344-clock ideal-flow search returns UNKNOWN after 60.092 seconds, with a
259-clock restricted-model lower bound. It does not reject the allocation or
provide a physical schedule.

The shared-bank mean-balanced assignment has a complete write-minimizing cache:
HiGHS proves 496 total noninitial writes optimal in 27.969 seconds under the
21-write cap. Maximum noninitial prefetch is two lines; the ideal transfer peak
is 424 clocks. Strict 344-clock ideal-flow searches using that soft hint return
UNKNOWN from CP-SAT (60.101 seconds) and HiGHS (60.797 seconds). These are not
infeasibility verdicts. Independent source replay verifies the integer cache.

The retained 392-clock physical witness compiles to legal Mode0 8/16 OBJ CHR
and OAM: 73 entries, 271 occupied tile cells, 202 unique tiles and 8,832 CHR
bytes. Decoding emitted OAM and bitplanes reproduces every compiled pixel
index and fixed bank. This constructive allocation stays below the 512-cell
OBJ limit, but does not prove live upload bandwidth, concurrent enemy leases,
native palette timing or gameplay.

Starting from the valid cache in a wider diagnostic window produces another
complete shared-bank cache in 60.106 seconds: 336-clock ideal peak, eighteen
peak writes, 519 total writes and 36-line maximum noninitial prefetch.
Independent source replay matches the complete viewport. The fixed-time
physical placement search at 344 clocks returns UNKNOWN after 60.065 seconds
(638 lifetime segments, 3,822 variables, 8,739 constraints). Thus this cache
also remains physically unadmitted.

A wider fixed-time physical diagnostic produces an 800-clock complete witness
in 30.066 seconds, with a restricted-family lower bound of 328 clocks. Exact
partitioning of its unchanged dirty words removes unnecessary padding to give
a 760-clock starting layout. A 300,000-proposal fixed-slot permutation search
then reduces the peak to 536 clocks in 21.406 seconds. Independent full source
and CGRAM replays verify both physical witnesses. They remain above the native
window and do not supersede the earlier 392-clock best physical result.

Six local repairs retain the shared-bank witness's 536-clock peak and reduce
aggregate transfer cost from 14,224 to 13,952 clocks. All accepted candidates
retain the full-frame write cap, necessary bank window and source identity.

The generic residency model can now optionally alias each bank's invisible
prefix to its freely chosen initial VBlank residency. Its first visible demand
is still enforced; subsequent loads retain the same write and lookahead rules.
This moves no required source pixel and relaxes no bank capacity. Twenty
focused residency tests pass, including both solver backends and opaque zero.
The option is disabled by default and is incompatible with fixed-outside local
residency repairs.

On the shared-bank scene this exact reduction removes 1,878 residency variables
and finds a complete 320-clock ideal cache in 60.079 seconds: eighteen peak
writes, 528 total writes, 49-line maximum noninitial prefetch and six peak
active banks. The restricted-model lower bound is 260 clocks. Independent
full source replay verifies the complete viewport. Physical placement and
native timing remain open; this result is not a raster presentation PASS.

Strict fixed-time physical placement of the prefix cache returns UNKNOWN in
60.135 seconds. Adding fixed bank permutations also returns UNKNOWN in
60.085 seconds. Neither result rejects the cache or raster presentation.
The reordering model now intersects every destination with the declared
domains of all pieces using that bank, and independently checks those domains
in the emitted result. A regression fixture rejects a cheaper 32-clock layout
that requires moving a reserved bank; the legal 40-clock layout retains source
pixels. Twenty physical-layout tests pass, followed by the focused receipt
assertion. The residency default also retains its original compiled hash
`d72cc368bf864f90b87ec5ac74068ce19a2c83d575468f2f3bc20e867f822d3b`.

A wider physical diagnostic of the prefix cache yields a complete 624-clock
layout in 45.075 seconds, with a 320-clock restricted-family lower bound.
Source and CGRAM identity, piece domains and fixed bank selection are checked.
It remains a diagnostic rather than native admission.

Generic slot-liveness retiming now reduces the best locked-bank physical
witness from 392 to 376 master clocks. Five invisible-slot loads move to
other legal lines, including two initially unused slots that can preload in
VBlank. Source pixel indices and OAM banks stay fixed. Row-boundary opaque
slot swaps then reduce aggregate packet cost from 9,824 to 9,576 clocks;
every palette relocation write at a live boundary is charged and source
pixel indices are remapped offline. The worst transfer remains 376 clocks.

The complete witness has eighteen peak color writes (36 data bytes),
1.87444 average writes per visible-frame line, and sixteen lines of maximum
noninitial prefetch. It retains 73 OAM entries, eighteen peak sprites and
34 tile slivers. Independent replay against source RGB8 composition verifies
all 57,344 viewport pixels, followed by full CGRAM packet replay. Five focused
liveness/reindex tests pass. No color reduction is applied.

Lines 130, 131, 133, 135 and 136 still exceed the measured 344-clock native
window. A further 500,000 fixed-slot proposals preserve the 376-clock peak.
This is neither native admission nor universal raster rejection. The proof
uses the controlled black scene and offline exact BOR SCREEN composition;
authored-background peak presentation, live composition and gameplay remain
open. Full schedules and replay results are retained in the receipt archive.

An exact fixed-index event-time scheduler improves the physical peak to 360
clocks. It models 421 loads with 24,559 variables and 39,669 constraints,
retains each slot's ordered event sequence and initial palette, and charges
actual four-range physical coverage. The 377-clock search proves OPTIMAL in
13.391 seconds with a matching 360-clock lower bound. Independent complete
source and CGRAM replay verifies the emitted schedule. The same fixed-index
family is infeasible below 345 clocks in 7.719 seconds; this excludes neither
other indices, different residency/event sequences, nor raster presentation.

Subsequent source-exact row-boundary reindexing retains the 360-clock peak
and reduces aggregate transfer cost to 9,328 clocks, leaving four overloaded
rows. Exact load-time scheduling of that remapped family also rejects the
345-clock target in 7.047 seconds. Seven focused tests pass, including a
restricted infeasible family, a valid exact schedule and rejection of a load
that overwrites a required source pixel. Native timing remains unadmitted.

A bounded annealing phase can now explore non-improving intermediate
row-boundary permutations while retaining only the best complete source-exact
state. Sixty thousand proposals and 1,273 accepted transitions retain the
360-clock peak and reduce aggregate transfer cost by sixteen clocks, to
9,312. The eight focused tests verify source identity, charged relocations,
input preservation and best-state retention. This does not admit timing.
A 45.121-second exact free-residency/slot repair over lines 124..146 returns
UNKNOWN; its 244-clock restricted lower bound does not reject raster.

Focused remapping of changing slots retains the 360-clock peak and reduces
aggregate cost to 9,296 clocks. An exhaustive fixed bank/reflection search
then checks all 5,040 eligible bank permutations, each with 256 slot
reflections, in 13.391 seconds and finds no better layout in that family.
A separate complete lifetime-to-slot reassignment search returns UNKNOWN
at 45.073 seconds. The shared-actor-bank cache also fails the 345-clock
fixed-index event-time family in 7.235 seconds; source banks, residency and
indices remain alternative search dimensions. No result rejects raster
universally and no native timing claim is added.

The generic row-slot solver now supports explicitly selected mutable banks.
All other banks retain the validated hint's residency; source word matching,
physical packet coverage and per-piece OAM bank selection remain enforced.
Bank-6-only repairs at the 345-clock strict window return UNKNOWN after
25.031 and 45.065 seconds, with a 344-clock restricted lower bound. A
feasibility-only variant also returns UNKNOWN after 45.035 seconds. It reports
no objective lower bound. Eighteen focused row-slot tests pass, including
unselected-bank preservation and feasibility-only source/CGRAM replay.

The latest 360-clock witness constructs legal mode-0 8/16 CHR/OAM with 73
entries, 271 occupied cells, 202 unique tiles and 8,832 CHR bytes. Decoded
bitplanes and OAM reproduce compiled indices. Its CHR SHA256 is
`470dbfd5963e2a2837f7d81af7364c1e8b01180cf94f0670f159d41dcbe59a6b`.
This remains an offline allocation proof, not live upload/native admission.
An alternative legal bank assignment retains 14.25 interval pressure but its
35-second cache search and 25-second minimum-write search both return UNKNOWN.
All source-exact witnesses and bounded search reports are retained; no color
reduction, alpha adaptation or fallback selection occurs.

The generic reindexer now also removes genuinely redundant loads only when
every future required bank word remains resident until that slot's next
change, then remaps pixel indices to surviving compatible slots. Finite
interval swaps charge both the opening and restoring palette writes. On the
best witness these changes reduce the overloaded-line count from four to
three and aggregate span to 9,248 clocks; lines 130, 133 and 136 remain at
360 clocks. Exact fixed-index retiming rejects the 345-clock target for this
new event family in 6.687 seconds. It does not reject raster universally.

A generic mixed-transfer planner enumerates sparse-word subsets, combining
up to three mode-2 CGRAM ranges with one mode-3 sparse stream, or retaining
four ordinary ranges. Mode 3 at $2121 writes CGADD twice and then the RGB555
low/high bytes. Independent B-bus descriptor replay verifies CGRAM words;
enumeration is explicitly bounded at 21 dirty words and channel 0 is unused.
The peak remains 360 clocks with at most seven channels. Per-line channel
modes, setup and first-high-byte alignment remain unadmitted natively. This
alternative transport therefore does not bridge the current witness's gap.

Transfer pattern and eight-clock channel/byte timing were checked against
Mesen source revision `18c05d3f076728d05310c6e591b7d0a08d604d42`,
`Core/SNES/SnesDmaController.cpp` lines 8..11 and 74..96. CGADD latch reset
and CGDATA low/high behavior come from `Core/SNES/SnesPpu.cpp` lines
2100..2125. The pinned primary implementation is available at
https://github.com/astrobleem/Mesen2/blob/18c05d3f076728d05310c6e591b7d0a08d604d42/Core/SNES/SnesDmaController.cpp . No new native transport
code is added from this offline exploration.

All 31 focused scheduler tests pass in 7.392 seconds, including exact event
scheduling, frozen banks, feasibility-only bounds, redundant-load source
identity, finite restoring writes, sparse DMA address/color bytes and
bounded enumeration. The 17 protected files match their saved SHA256 values.
No color reduction, alpha adaptation or production raster admission occurs.

The current piece-bank assignment's validated fractional cache lower bound
is 15.25 peak writes (primal residual 7.1e-15, dual residual zero). A generic
integer cache with a sixteen-write ceiling is OPTIMAL in 8.891 seconds,
with 363 total writes, two-line prefetch and zero integer constraint violation.
Its ideal peak remains 360 clocks because some lines touch seven/eight banks.

Adding a six-active-bank ceiling and the strict 345-clock ideal partition
window yields a complete cache in 40.050 seconds: 304-clock ideal peak,
sixteen peak writes, 386 total writes, twenty-two-line maximum noninitial
prefetch and five peak active banks. Independent complete viewport replay
passes. Physical slot placement returns UNKNOWN in 45.076 seconds; this
cache remains unadmitted. Two smaller line-130 repairs also return UNKNOWN
at thirty seconds each. No timeout is treated as hardware infeasibility.

A wider physical diagnostic of the new sixteen-write cache produces a
600-clock valid witness in thirty seconds, with a 304-clock restricted lower
bound. Exact dirty-address partitioning removes unnecessary packet padding
to start at 568 clocks. Fixed-slot permutation reduces it to 424 clocks in
thirty seconds. Liveness retiming and finite swaps reduce excess/aggregate
cost without lowering that peak; they may increase a line's write count, so
the original cache's sixteen-write ceiling is historical, not admission of
those later repairs. The prior 360-clock witness remains best.

Fixed-time lifetime placement can now use the equivalent rectangle encoding:
fixed scanline lifetimes are paired with single-slot intervals and constrained
by NoOverlap2D. The default retains its existing encoding. Both focused
rectangle cases pass, and the physical-layout regression suite passes all
21 tests in 11.712 seconds. The 45.072-second strict rectangle search returns
UNKNOWN. Exhaustive bank/reflection search retains the new cache's 424-clock
physical peak. No timeout or restricted family excludes raster universally.
