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
