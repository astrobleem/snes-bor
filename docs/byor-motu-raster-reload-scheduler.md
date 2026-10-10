# Bounded physical palette reload scheduler

`raster_slot_greedy.py` constructs schedules from a validated exact-pixel joint
schedule. It retains actual pieces and whole-piece palette banks, reconstructs
row demands from source pixel masks, and permits eviction and reload between
uses. Compatible resident colors stay in their slots by default. Bounded
lookahead may preload future colors in otherwise unused slots. Opaque RGB555
zero remains distinct from an empty slot.

The physical range partition uses exact dynamic programming over ordered bank
intervals, including padding and transparent words. It enforces the optimistic
prepared-DMA span `16 * words + 24 * ranges - 40 < window`, for at most four
ranges. Reports distinguish changed-color bytes from actual packet bytes and
record the chained DMA channel requirement. Native timing remains unadmitted.

Optional interval repacking remaps bitmap rows offline while preserving every
pixel color. Optional fixed bank permutation stays inside color-math eligibility
classes. A global beam keeps alternative full palette states across scanlines;
these are bounded heuristics, with explicit failure rather than raster rejection.
Every successful result independently replays full CGRAM packets and each
visible piece pixel. This does not replace the separate full-context/native gate.

For the isolated mixed HBreath construction, a relaxed run gives a correct
schedule with 101 reload events, 14-line maximum noninitial prefetch lead,
four transfer ranges and seven chained DMA channels. Its peak physical packet
contains 152 bytes and spans **1,272 master clocks**, exceeding the measured
**356-clock** window. It is retained as a scheduler correctness witness only.
The 96 original measured-window trials fail at scanlines 130–131; 24 interval
repacking trials fail at line 131. Bank permutation and global-beam trials are
also retained with their exact bounds, without universal rejection.

The [receipt](receipts/byor-motu-raster-reload-scheduler.json) records artifact
hashes and bounded summaries. Production presentation, bank zero and the
ordinary static path are unchanged. No color reduction is applied. MOTU native
presentation and full Demo remain open.
