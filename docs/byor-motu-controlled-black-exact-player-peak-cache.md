# Exact player/effect composite cache on black

Combining the source He_ManB freespecial4 frame 6 and HBreath BR12 frame 11
changes the effect's visible source-composed palette to 266 RGB555 words.
Source assets are unchanged; exact RGB8 SCREEN is evaluated over the player
before RGB555 projection. The player has 3,185 final visible pixels and
31 words; the effect has 2,751 pixels. Combined peak row demand is 69 words.
This explicit pose does not prove source gameplay reachability.

The generic two-line global-word construction admits 94 fixed-bank objects,
nineteen peak sprites and 34 tile slivers. An integer cache minimizes total
writes to 303 at the imposed eighteen-write ceiling, with two-line prefetch
and zero integer constraint violation. Its optimistic transfer span is 392
clocks, exceeding the isolated constant-control 344-clock window. This does
not establish the minimum peak or reject this bank assignment.

A direct flow-cache feasibility search at a strict 345-clock bound returns
UNKNOWN after 120.097 seconds. Physical slots, concurrent native rendering,
authored underlays and production admission remain open. Independent current
source replay verifies all 57,344 viewport pixels for both compiled schedules.
Full schedules and the source-bound scene are retained compressed.
NO color reduction or alpha adaptation is applied.
