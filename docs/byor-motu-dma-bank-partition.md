# Physical bank extents in the prepared-DMA search

The objective-guided isolated search produces another exact fixed-bank schedule:
126 OAM entries, 32 sprites/slivers per line and 19 maximum color writes.
Independent replay matches all 57,344 pixels and the retained source-context
RGB555 hash. Generic compaction reduces this to 96 OAM entries, 28 peak sprites
and 34 slivers. Source dimensions and colors remain unchanged.

The earlier optimistic bridge bound admits this candidate at 352 master clocks.
Its independent range-partition bound rejects it: row 126 requires at least
376 clocks between commits, versus the 356-clock accessible CGRAM window. A
range spanning three banks traverses every word in its middle bank; two adjacent
bridges cannot both ignore that extent. These counts still grant ideal endpoint
slot packing, a first low-byte preload, and no CPU setup or contention cost.
The actual greedy packet layout has up to 18 packets and 54 transfer bytes.
This is rejection of this candidate for the prepared-DMA mechanism, not universal
raster infeasibility.

`--prepared-dma-partition` now constrains nonoverlapping CGRAM ranges covering
all banks written on each line. Endpoint write counts are charged directly;
intermediate banks occupy all 16 words, including transparent zero. The CP-SAT
adapter admits bounded integer transfer counts while retaining Boolean pixel,
mask and liveness variables. Independent incumbent replay verifies the stronger
bound. This is a necessary favorable bound, not slot-layout or native admission;
channel availability, setup and runtime contention still need proof.

The stronger 300-second search returned UNKNOWN. A different 4/4 tile-grid offset
also returned UNKNOWN under the earlier bound. `--grid-padding-x/y` lets generic
legal pieces begin before their visible bounds without altering the source
canvas, RGB555 identity or pixel positions. All 64 small-grid phases are retained
in a geometry-only inventory; it does not claim bank assignment feasibility.

59 focused tests pass. They check exact integer-domain witnesses, range admission
against an independent dynamic program at both sides of the timing boundary,
opaque black, source-pixel replay and legal grid padding. The width guard remains
clean. Production code, bank zero and ordinary static presentation are unchanged.
MOTU Demo and full native HBreath raster execution remain unproven. NO color
reduction applied.

[Candidate, packet, compaction and bounded search hashes](receipts/byor-motu-dma-bank-partition.json).
