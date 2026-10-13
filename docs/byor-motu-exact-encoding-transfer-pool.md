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
