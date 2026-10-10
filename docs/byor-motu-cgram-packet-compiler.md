# Offline CGRAM destination compiler

The compiler converts independently validated physical-slot traces into exact
destination/payload descriptors. It checks sequential slot identity, packs
RGB555 words little-endian, excludes transparent slot zero, and confines each
range to one OBJ bank. A dynamic program chooses a partition minimizing data
bytes plus a configurable destination cost. Known unchanged slots may bridge a
gap; unknown slots cannot. Every packet is independently replayed, including
unchanged resident colors and continuity between scanlines.

The default cost includes one CGADD transfer byte per packet. It excludes CPU
instructions, DMA channel setup, IRQ context preservation and HDMA/NMI
contention. The resulting descriptors do not establish native timing admission.
Cross-bank ranges or different slot assignments may improve another schedule;
this compiler does not reject those possibilities.

The existing isolated opaque/precomposited schedule reaches 108 transfer bytes
and 22 packets on its respective peak rows. The corresponding concurrent
schedule reaches 134 bytes and 26 packets. Neither fits the isolated native
bursts previously measured. These are the original heuristic schedules, not
lower bounds for every possible exact OBJ encoding.

The 300-second isolated saturated-operand search with full pool-interval
retention returns UNKNOWN with no candidate (41,632 variables, 53,240
constraints). This remains a restricted search result, not hardware
infeasibility. A new necessary bound counts OAM masks forced by available pixel
encoding kinds and distinct forced row colors; the solver still independently
replays every incumbent.

Seven packet tests pass, including stale state, unknown gaps, transparent slot
exclusion and continuity. Seventeen existing joint/backend tests also pass.
No production assembly, media or static presentation path changes. No color
reduction applied. MOTU remains unregistered and uncertified.

[Receipt](receipts/byor-motu-cgram-packet-compiler.json).
