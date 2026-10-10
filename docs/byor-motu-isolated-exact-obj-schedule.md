# Isolated peak effect: exact fixed-bank schedule

The flexible pooled-residency search finds a valid banked schedule for source
HBreath idle frame 11 over the explicit GUILE2 stage underlay. It uses fixed
OAM bank identities, with normal palettes 0..3 and additive palettes 4..7.
Source SCREEN is computed in RGB8 before conversion to RGB555. Independent
piece-mask, slot and final-pixel replay verifies all 57,344 viewport pixels.
No source dimensions or colors were reduced.

The result has 128 OAM entries, 32 peak sprites and 32 peak tile slivers per
line. It writes at most 19 colors/38 CGRAM data bytes per line. It consumes all
OAM entries and therefore cannot admit required concurrent actors unchanged.
Generic 8-to-32 mask compaction reduces this to 97 entries, 28 peak sprites and
34 peak slivers. It preserves every pixel's bank/slot identity and selects
OBSEL's legal 8/32 mode. Full transparent rectangles still count towards all
line limits; the optimizer can reject otherwise useful merges.
Its source-context RGB555 hash is
`4d1f01dece9f9a50ecde25d1efc3d9e3da2bc0ee3974fc2702650ee0d9cf2934`.

The exact packet compiler finds up to 18 destination packets and 56 transfer
bytes (including address bytes), with that maximum at row 121. This exceeds
the previously tested native bursts before packet setup costs. The physical
slot layout and geometry need further work. The earlier pool interval family
did not find this candidate because it forbids the bank-residency changes used
by the flexible solution; that family is not a universal feasibility test.

This candidate's bank-update sets fail the prepared IRQ-DMA mechanism even
before choosing physical slots. DMA charges eight clocks per byte/channel.
Another range requires one address byte and two channel starts (24 clocks).
An adjacent bank bridge rewrites at least a transparent word (16 clocks) and
can save at most eight clocks. Granting all such bridges without charging
unused intermediate slots yields a favorable bound. Also granting the one
low-byte preload before HBlank yields at least 400 clocks between palette
commits on the busiest rows, exceeding the safe 356-clock CGRAM window by 44.
This rejects these bank-update sets under this mechanism, not every schedule
or alternative transfer mechanism.

Local Mesen DMA/PPU source establishes the costs and high-byte-only commit.
The retained 447-packet contiguous and split observations exceed the favorable
data-span bounds and show the expected 24-clock incremental switch cost.
The solver can now constrain this optimistic commit-span bound. Bank-label
symmetry is disabled for that search because address adjacency changes cost.
35 focused geometry, packet, joint and backend tests pass.

The timing-constrained 180-second search returns UNKNOWN, not infeasible.
It includes the favorable low-byte preload and preserves independent replay.
The native observer now tracks the CGRAM latch rather than treating every data
port byte as a commit. Across three complete fields/447 packets, the 38-byte
split has 8,493 high-byte commits with zero unsafe commits; the 40-byte split
has 8,940 commits with 255 unsafe commits. Both destinations and packet sizes
match their descriptors. An earlier one-field capture is retained as incomplete;
32 bounded frame attempts produce each complete capture. No universal DMA
maximum, production CPU-context preservation or source rendering is certified.

This is an offline isolated result, not RASTER_HBREATH_PROVEN or a gameplay
certificate. Native layer routing, transfer timing, actual CGRAM/OAM traces,
concurrent actors and final runtime completion remain open. Neither raster nor
the authorized BG/hybrid approach is universally rejected. No color reduction
applied.

[Candidate and packet hashes](receipts/byor-motu-isolated-exact-obj-schedule.json).
