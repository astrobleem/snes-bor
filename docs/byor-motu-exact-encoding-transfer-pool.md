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
