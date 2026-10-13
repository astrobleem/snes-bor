# Source-exact encoding and necessary transfer bound

The authored HBreath peak now has an independently replayed two-class cache
proposal with 20 peak color loads. The compiler derives exact operands and
scanline math controls from BOR 4086 SCREEN output. Both eligibility classes
have at most 60 resident words. No color reduction or alpha adaptation is used.

The generic solver includes a necessary transfer constraint: a class loading
`n` words needs at least `ceil(n/15)` affected banks. Even with ideal adjacent
banks and endpoint slots, the lower transfer cost must fit the selected window.
This is not a fixed-bank assignment or complete physical partition proof.
Tests distinguish 22 loads split 17/5 across the classes: their minimum cost
is 368 master clocks, exceeding a strict 357-clock window.

The source proof replays all 57,344 viewport pixels, including 2,668 encoded
effect pixels and 83 source pixels whose exact output equals the background.
The source frame hash remains
`4d1f01dece9f9a50ecde25d1efc3d9e3da2bc0ee3974fc2702650ee0d9cf2934`.
The proposal and bounded construction evidence are retained in
[the pool receipt](receipts/byor-motu-exact-encoding-transfer-pool.json) and
[the construction ledger](receipts/byor-motu-authored-kempe.json).

A restricted global word-bank constructor produces 144 small OBJ entries.
Generic legal 8/16 rectangle compaction preserves every indexed pixel and
reduces this to 90 entries, 27 sprites and 33 tile slivers at peak. That admits
effect-only geometry, not concurrent actor palettes, layers or transfer timing.
An independently checked fixed-bank LP requires at least 37 color writes for
this assignment, so its geometry witness is not a hardware timing witness.

Allowing word copies and scanline bank migration under the selected 20-load
class cache returns UNKNOWN after 90.124 seconds. The compiled OAM objects
still require fixed bank selection throughout their padded lifetimes.
UNKNOWN does not reject raster presentation. A wider-window geometry search
is used to obtain a verified guide before further timing refinement.

There is no production raster admission, native peak-frame proof, concurrent
gameplay proof or completed MOTU candidate from these experiments. The measured
344-clock conservative transfer budget and 356-clock maximum window remain
unchanged. Static source presentation remains unchanged. Bank 0 has no growth.

The wider-window bank construction replays 100 effect OAM entries, 29 sprites
and 34 tile slivers, with a 920-clock ideal peak. A fully verified warm hint
reduces that cost to 680 clocks and 36 writes (72 payload bytes), using 104
entries and the same line peaks. Eight-line earlier preloads retain 680 clocks
in a bounded LNS search. These constructions remain effect-only and unadmitted
for native timing.

Rebalancing the 90-piece geometry reduces its interval surrogate from 37 to
21 writes, but the independently certified cache LP still requires 23.615
writes. Cache-cut feedback finds assignments with bounds of 22.947 and then
22.857 writes, which still require at least 23 integer writes. The cuts apply
to fixed geometry and selected words, not every source-exact encoding.

A joint search permitting new exact operands and fixed rectangle banks
returns UNKNOWN after 94.693 seconds: 843,222 variables and 2,100,765
constraints, with no search branches. The 8/32 rectangle search with actual
player geometry reservation also returns UNKNOWN; its necessary horizontal
tile bound is 31. Neither result rejects the general presentation capability.

The compiler additionally supports minimizing total integer class-cache loads
under the same peak and necessary transfer constraints. It reports total loads
and peak loads separately. This searches for a temporally stable encoding;
it remains a class proposal requiring real bank and native transfer proof.

The initial total-load candidate replays 633 loads with a 22-load peak. Its
650-load model objective contains conservative slack, which is not counted as
actual CGRAM writes. A source-bound soft hint reduces the replay and model
objective to 528 loads after 120.277 seconds, still with a 22-load peak. The
source compiler checks source metadata, scene and final pixel digest before
the lower solver independently replays the hint's residency and pixel coverage.

Integer load variables now exactly represent absent-to-resident transitions.
The independent replay checks the modeled total against actual cache changes;
peak and total remain distinct report fields. Fractional lower-bound behavior
and the default peak objective remain unchanged.

The 528-load proposal's selected-word bank construction, including eight-line
earlier preloads, remains UNKNOWN after 90.219 seconds. Whole-frame word-cover
selection produces source-exact effect geometry with 107 OAM entries and peaks
of 20 sprites and tile slivers. Its balanced interval pressure is 25.727 loads,
so this construction does not meet the transfer budget either. These are
bounded, selected encoding families, with no general raster rejection.

With exact integer load accounting, a guided source solve reaches 500 total
loads with a 22-load peak after 90.310 seconds. Model and independent replay
totals agree. The older complete 400-clock schedule supplies a stronger
source-bound class proposal: 470 total loads, 20 peak loads and a 320-clock
peak under the necessary class-bank transfer relaxation. This proposal is
replayed before guiding a new total-load search; its real fixed-bank schedule
still costs 400 clocks. Pool cost is never substituted for that transfer cost.

The guided source solve reduces the class proposal to 358 total loads and a
19-load peak. Independently replayed frame-word selection compiles 89 effect
objects, with peaks of 19 sprites and tile slivers. Rebalancing lowers interval
pressure to 19.429; the stronger fixed-bank LP requires 21.571 loads. Certified
cache cuts improve the latter to 21.25, which still requires at least 22 integer
loads. The selected class-cache bank construction remains UNKNOWN after
90.195 seconds. None of these class or fractional witnesses admits CGRAM timing.

Integer cache construction for the 89-piece assignment finds 22 peak writes,
558 total writes and 15-line maximum prefetch latency. Complete ideal bank
partition replay requires 472 clocks. All 576 eligible fixed bank relabelings
retain that peak. Exact bank-cost optimization gives a 377-clock lower bound
within this fixed word/bank family and the 22-write cap. This rejects that
assignment against the measured window, while alternate bank masks remain open.

The source compiler can accept a mode/window-only guide independently of a
palette guide. Its choices stay soft; no palette contents or prior source
identity admission is imported. The actual He_ManB + HBreath pose retains all
31 ordinary source words statically while testing complete exact effect
operands and all four scanline math modes. Two LP methods time out at 30.283
and 60.206 seconds without a validated bound. The guided integer test returns
UNKNOWN after 96.470 seconds including construction. Its 122,858 variables
and 204,162 constraints do not certify concurrent feasibility or infeasibility.
Those results are retained in the separate
[concurrent source receipt](receipts/byor-motu-authored-peak-player-joint.json).

The generic cache-cut master has an optional SAT hint-repair strategy, preserving
all source, bank and geometry constraints. Resuming certified cuts lowers the
fractional write bound to 18.824, but consumes 128 effect OAM entries and peaks
of 32 sprites and tile slivers. That is not a concurrent gameplay allocation.
Its bounded integer transfer test at 344 clocks returns UNKNOWN after 90.108
seconds.

Repeating the mask search with the actual 33-entry player geometry reservation
enforced reaches a 20.333-write fractional bound. It uses 95 effect objects and
22 peak sprites/slivers; the complete source viewport still replays exactly.
This reservation accounts for geometry only, not player palettes or compositing.
The separate full actor tests above cover those demands without claiming admission.

Independent replay counts the selected reservation as 128 combined OAM entries,
26 peak sprites and 30 peak tile slivers. The selected masks' fixed-bank transfer
model is INFEASIBLE after 24.419 seconds at the strict 357-clock gate, which
permits at most 356 clocks. This rejects those masks and words. It does not
reject alternate source-exact bank masks or the general raster capability.

Generic geometry counts now use the shared wrapped OAM row and clipped sliver
helpers. Returned cache-cut candidates retain their reservation and independently
checked combined counts. Regression fixtures reject wrapped transparent padding
against a full top-row sprite reservation and correctly count one visible sliver
for a 64-pixel object at x=248. The evidence retainer independently replays these
resource counts instead of relying on the constructor's assertions.

The integer source solver also minimizes resident color-lines, then loads,
lexicographically. Its source-replayed proposal occupies 2,287 color-lines,
with 635 loads and a 22-load peak. The selected-word bank-copy search returns
UNKNOWN after 90.163 seconds. Its balanced 93-piece assignment has a checked
22.583-write lower bound, requiring at least 23 writes. Lower pool residency
is therefore not substituted for a valid bank schedule.

The generic source constructor now supports largest legal pieces of 8, 16 or
32 pixels. A larger piece whose row needs more than fifteen words subdivides
source-exactly into eight-pixel pieces, preserving the single global 8/16 or
8/32 size pair. Pixel masks retain their actual dimensions. Wrapped padding
and clipped slivers remain counted. The ordinary default is eight pixels.

Legal 16-pixel construction of the 358-load encoding uses 34 effect OAM entries,
12 peak sprites and 22 slivers. Its balanced fixed-bank LP requires 24.286 loads.
Allowing additional bank masks reduces the fractional bound to 19.643, with
71 entries, 19 sprites and 34 slivers. The complete fixed-bank transfer model
is INFEASIBLE at 344 clocks after 26.248 seconds; the 356-clock test remains
UNKNOWN after 60.163 seconds. Neither isolated geometry admits concurrent
actor palettes or a native timing witness.

Joint operand/bank construction with saved pool intervals uses only 17,038
variables and 52,725 constraints. Its original mask allowance is INFEASIBLE
after 1.919 seconds; allowing extra masks returns UNKNOWN after 60.080 seconds.
Two-line interval chunks with up to four charged bank copies remain UNKNOWN
after 90.104 seconds (28,429 variables and 78,111 constraints). The restrictions
are explicit and no universal raster rejection is inferred.

The production OAM authority uses OBSEL `$C2`, size mode 6, with 16×32 small
and 32×64 large rectangles (`src/core/oam.pasm`). The pinned Mesen PPU width
and height tables confirm those dimensions. The generic constructor and CHR
compiler now retain this legal rectangular family; they never substitute an
eight-pixel object under mode 6. Emitted OAM size bits, tile row strides and
decoded pixel indices are independently replayed for both rectangle sizes.

The source-exact mode-6 row-mask constructor uses 28 OAM entries, 16 peak sprites
and 32 slivers. Its global word-bank alternative exceeds the tile limit at 40
slivers. The admitted geometry emits 7,936 CHR bytes and 544 OAM bytes, with
exact index/bank replay. The selected balanced cache requires 24 writes in the
LP; bounded row-mask feedback reaches 23.833. Native timing is not admitted.

Raw palette demand is also independently remeasured from BR12.PNG: 204 colors,
54 peak scanline colors, 32 peak adjacent new colors and an 85-color adjacent
union. Rows 38/39 force at least 25 writes with sixty resident raw words, even
after arbitrary preload, eviction, bank assignment and geometry are relaxed.
The existing interval checker grants a preloaded low-byte latch and still
requires a 384-clock first-to-last commit span, exceeding 356 clocks. This
rejects the raw-word four-math-bank family, not the encoded operand schedules.
[Raw alpha-bank receipt](receipts/byor-motu-raw-alpha-bank-capacity.json).

The CHR compiler now hides unused OAM at X=-64, matching production authority.
Y=240 alone is unsafe for mode-6 height 32 because transparent padding wraps
onto top scanlines and can overflow sprite evaluation. All 128 emitted entries
are decoded independently; their sprite/sliver rows must equal the planner's
actual geometry. Scanline overflow is an explicit report failure even when
CHR pixel indices round-trip correctly. Used-entry high bits replace the
hidden defaults, rather than inheriting a stale X-high bit.

The corrected mode-6 OAM digest is
`002584f2baea052a20e563892d9a09adbdba3bae8e713727a46ce08d9dbd68aa`;
CHR bytes remain identical. Emitted geometry independently confirms 16 sprites
and 32 slivers. This is a code/data correctness proof, not native admission.
The continued rectangular cache-cut search retains a 23.833-write fractional
bound; its transfer-cost relaxation's best selected assignment requires
404.854 clocks. Neither result universally rejects rectangular raster rendering.

The source joint CLI's feasibility-only option is now forwarded to CP-SAT.
Earlier joint experiments requested feasibility but still optimized their
weighted objective; their retained objective label exposes that behavior.
No constraints or source replay are weakened by the fix. A focused native
backend fixture verifies FEASIBILITY_ONLY reporting and exact pixel replay.

The corrected 16-pixel interval search returns UNKNOWN after 90.089 seconds,
with 1,436,371 reported branches and 1,035,043 conflicts. Collapsing the inactive
prefix and coalescing equal pixel contexts reduces the unrestricted model from
433,846 variables/1,083,373 constraints to 94,675/237,265, but the bounded run
remains UNKNOWN after 120.180 seconds. The prior ten-minute run likewise returns
UNKNOWN. Its zero response-level branch count does not mean workers did no
search: the retained bounded log includes millions of feasibility-jump moves.
There is still no broad infeasibility certificate or native peak-frame witness.

The joint exact-operand scheduler now accepts fixed source-bound mode-6
rectangles (16x32 / 32x64). It uses hardware Y wrapping for mandatory
geometry, constraints and independent result replay. A fixture at X=248,
Y=220 verifies wrapped transparent padding, clipped tile slivers and emitted
CHR/OAM data; an illegal rectangular hint fails explicitly. The authored
mode-6 search has 225,095 variables and 559,453 constraints and returns
UNKNOWN after 90.744 seconds. This neither admits timing nor rejects raster.

The exact pool constructor can also require at most fifteen whole-frame
words per bank and initialize every word during VBlank. This keeps ordinary
actor palette demand distinct from dynamic effect palettes. The isolated
He_Man pose preserves all 31 RGB555 words in three banks (15/3/13), with zero
scanline writes, 23 mode-6 OAM entries, eight sprites and sixteen tile slivers
at peak. All 57,344 viewport pixels and emitted CHR/OAM data are independently
replayed in [the static player receipt](receipts/byor-motu-player-static-mode6.json).
The earlier 17-entry layout reused one bank dynamically and is not a static
player admission.

Combining those selected static player pieces with the current 28-entry
effect family requires 51 OAM entries and 24 sprites, but reaches 48 slivers
on 32 lines. That selected combination fails geometry. Its isolated effect
encoding is not a concurrent alpha witness, and other geometry/encoding
families remain open. A new full player/effect source-context integer class
proposal preserves the 31 ordinary words, replays every viewport pixel and
requires 32 peak pool loads. Its selected mode-6 row-mask construction
requires 53 OAM entries, 22 sprites and 44 slivers, so it also fails selected
geometry. That construction may reencode ordinary pixels; it is not a proof
that the production static path coexists with raster effects. No native or
production admission, alpha adaptation or color reduction follows.

The focused joint/backend/constructor suite passes 118 tests.

The shared bank-mask solver now accepts explicitly selected mode-6 shapes and
can change exact word bank ownership by scanline epoch while retaining fixed
OAM bank masks. Tests cover clipped rectangular slivers and top-line wrapping.
The selected full player/effect operands fail joint geometry even when each
row may choose fresh word bank ownership. This rejects those operands on that
grid, not alternative exact operands.

Allowing fresh exact operands finds a full source-context geometry witness
in 4.810 seconds: 54 mode-6 entries, seventeen sprites and 34 slivers at peak.
All viewport pixels are independently replayed; CHR packing uses 14,208 bytes
and legal rectangular sizes. CHR SHA-256 is
`ad10704698ed3a0a2ee91f21f05cf0f5c485f552b695e020ba304cac1d90f312`;
OAM SHA-256 is
`5312e2ca77b24a1d11cccecfb3d794b86e65459e1bacbd9fbbbc29ffec4f5703`.
This has sixty peak row palette writes and grants unrestricted transfer
bandwidth. It reencodes 244 ordinary player pixels into math-eligible banks;
their source outputs remain exact for this context, but the ordinary static
path is not preserved by this witness. Neither native timing nor gameplay
is admitted. Evidence is retained in the full player/effect receipt.

Source-exact overflowing constructors may now supply geometry search hints.
The input is independently replayed and explicitly labeled a hint; the returned
solution must still pass every hardware geometry constraint. It grants no
initial geometry admission. The focused suite passes 132 tests.

A fractional exact-operand cache bound for this fixed pixel/bank assignment
is optimal at 46.667 writes per line (primal residual 1.42e-14). Even before
transfer setup, integer schedules need at least 47 words, far beyond HBlank.
This rejects the selected assignment/control family for timing; it is not
a broad infeasibility result because changing pixel bank ownership, controls
or geometry can change the bound.

Saved scanline pool coverage is now independently checked against actual
visible source pixels before either the joint solver or pool constructor
uses it. Relaxing saved operand identities still requires the input guide
to be truthful. Tests reject a guide whose correct source hash and declared
replay flag conceal missing source colors. Reports include the actual checked
pixel count. Earlier bounded experiments retain their original fields; this
consumer check is newly enforced. CLI summaries omit full scanline arrays.

Source-400 guided operand repair remains UNKNOWN (209,981 variables, 522,441
constraints, 62.126 seconds). Preserving original words while allowing fresh
bank masks also remains UNKNOWN (103,063 / 257,659, 60.284 seconds). These
results provide no hardware rejection.

The cache-cut master now handles infeasible proposed bank assignments using
a phase-I LP. It independently checks positive minimum slack and dual signs,
unbounded-variable stationarity and bounded-variable residuals before adding
a feasibility cut. Outward-rounded cuts and exact certified-assignment
exclusions preserve the remaining domain. A timeout or an infeasible solver
label alone never adds this cut. The witness has positive certified slack
0.0004118616; search continues through eight further proposals. Resuming the
retained feasibility certificate also passes. The original assignment still
has the best optimistic fractional transfer bound, 331.330 clocks; no integer
cache, physical transfer or native admission follows. Future iteration reports
retain the exact decision assignment rather than relying on ordering.

The actual player/effect source-bound warm cache search with 31 static ordinary
words remains UNKNOWN after 96.142 seconds. It does not reject concurrent
raster presentation. The focused solver/consumer suite passes 133 tests, and
the final constructor coverage check passes its nine cases.

The recovered twenty-piece bank change retains source pixels and 86 entries
(22 sprites / 27 slivers). Its fixed-bank integer search returns UNKNOWN
after 90.143 seconds, with a valid optimistic objective lower bound of
349 clocks. This assignment cannot satisfy the conservative 344-clock budget;
a physical/native witness within the 356-clock maximum window is still absent.

A new integration test starts with a genuinely infeasible zero-write bank
assignment, verifies its positive slack certificate, confirms that search
continues, and resumes its certificates before any feasible cache has been
found. Fourteen cache-decomposition tests pass. No color reduction is applied.

The precomposited pool relaxation incorrectly exposed sixty additive slots
in addition to the 120 literal OBJ slots. That is corrected: precomposited
pixels have no additive operand alternatives and the pool capacities are
120/0. A 121-color simultaneous fixture now fails explicitly. The fixed-bank
joint model already used the correct eight-bank domain; this fix concerns
its pool-only relaxation.

For the authored player/effect scene, literal precomposited output uses 630
non-bypassed RGB555 identities and 75 at peak on one line. Its independently
checked liveness LP is optimal at 26.428571 writes (dual residual 2.22e-16;
primal residual 1.78e-14). An integer schedule therefore needs at least 27
changed words on some line. Even granting a preloaded first low byte and
ignoring addressing/setup, consecutive high-byte commits span at least
16*(27-1)=416 master clocks, above the measured 356-clock maximum. This rejects
the literal precomposited OBJ policy for this source context, with all eight
banks and geometry relaxed. It does not reject encoded math operands or
other lossless presentation strategies. The broad 329,869-variable joint
precomposited search is UNKNOWN, which is not itself rejection evidence.

A separate necessary relaxation allows each effect pixel its own exact
add/half-add/subtract/half-subtract mode and window gate. Ordinary player
words remain statically reserved. Restricting cache variables to the effect
interval retains those reservations while reducing the model from 413,405
variables to 86,863. The reduced LP is optimal at 16.3 writes; fixed banks,
physical slots and shared scanline controls remain relaxed. Thus encoded
math remains open. Fixed-color operands and main-screen zero clipping are
not modeled, so no universal rendering rejection is claimed.

Fractional cache weights can now guide legal two-window masks through a
bounded-transition dynamic program. An exhaustive small fixture verifies
its weighted optimum and register-mask replay. This guide imports no palette
residency and grants no source pixel or native admission. Its suggested
55 controlled rows use 35 full-add and twenty half-add modes. The existing
joint/backend/capacity suite passes 132 tests; window and static-demand
fixtures pass eighteen cases. No alpha adaptation or color reduction is used.

The source-bound fractional control guide still returns UNKNOWN in the full
integer class cache after 94.975 seconds. No palette residency was imported
from the LP, and no infeasibility follows from the timeout.
