# Per-line player geometry reservation

The mask retiler now accepts an explicit other-actor reservation: total OAM
entries and a sprite/tile-sliver count for every viewport scanline. Its master
adds these to every selected effect rectangle before enforcing the hardware
limits. Independent output replay repeats the same combined checks. A seed
that exceeds the reservation cannot become an admitted candidate.

The representative He_ManB freespecial4 frame 6 uses 33 legal 16x16 pieces,
with at most five sprites and ten tile slivers per line. Its viewport position
is y=220. Rows begin at 108, 124, 140, 156, 172, 188, 204 and 220 with
3, 4, 5, 3, 5, 4, 5 and 4 entries respectively. The retained vectors count
the full rectangle rows and include the viewport-clipped final group.
These are counts from the existing source-replayed isolated player schedule,
not an assumption that its peak applies to every effect line.

Reserving those vectors in the authored BR12 fixed-bank mask search considers
37,850 legal 8/16 rectangles. The 120.128-second trial returns UNKNOWN without
a geometry candidate. The independent effect row lower bound is 24 tile
slivers. Neither that lower bound nor the timeout proves combined geometry
infeasible. Player palette residency, the effect's changed underlay/alpha
context, actual pose reachability and native concurrent presentation remain
unadmitted. The receipt names these limits explicitly and retains the vectors,
search result and hashes of the source schedules.

Six focused mask-retiling tests pass, including a successful combined
128/32/34 reservation boundary and an exhausted per-line sprite reservation.
The width audit has 9,825 labels and zero failures. All 17 protected file hashes
match. No color reduction is applied.
