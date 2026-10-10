# Controlled source raster OBJ proof

The peak HBreath idle frame 11 now has a lossless native raster OBJ witness.
This is an isolated LoROM experiment over a constant black underlay, not a
production SA-1 runtime admission or an authored MOTU scene certification.

The compiler reads the original model, animation frame and model palette. Only
the fixture underlay is virtual. BOR 4086 alpha 1 is SCREEN in RGB8; SCREEN over
black equals the source color, so precompositing this controlled context retains
all 204 opaque RGB555 colors and all 2,751 opaque pixels. The original 110 by 90
canvas remains unchanged. Its peak row has 54 colors and its peak adjacent new
color count is 32. No color reduction is applied.

Generic per-color bank assignment limits each bank to 26 colors across the
frame. Source-exact 8 by 8 masks select one bank for their entire OAM lifetime.
The result uses 107 OAM entries and peaks at 24 sprites and 24 tile slivers per
line. A cache scheduler retains resident colors and preloads future colors. A
matching fractional lower bound of 7.8888888889 proves the integer peak cannot
be less than eight writes for this fixed bank encoding. The eight-write
schedule minimizes total noninitial writes to 201 and needs at most seven
lines of prefetch. Physical slot placement then emits at most four ranges.
Eight changed colors require 16 logical bytes; unchanged words bridging ranges
raise the peak actual CGRAM payload to 28 bytes. CGADD streams and DMA channel
overhead are included in the measured transfer span below.

The native executor uses DMA channels 1 through 7: color payloads alternate
with one-byte CGADD address streams. Channel 0 is unused. Payload source cursors
advance in hardware; the IRQ sets lengths and starts the precompiled transfer.
Code is in banks 39 and 40 and payloads in bank 42. Bank zero has size-neutral
reset/vector substitutions and no growth. This fixture changes the cartridge
header to standalone LoROM; production SA-1 mapping and resource leases are
explicitly unproven.

The observer measured a peak first-high to last-high span of 216 master clocks.
First high commits occur at horizontal clocks 1104 through 1120, inside the
356-clock safe CGRAM window spanning clocks 1096 through 87 of the next line.
All four observed fields have exactly the expected CGRAM address/value packets,
with zero unsafe high commits. The full 256 by 224 screenshot is checked against
the source-derived RGB555 image: 57,344 pixels match with zero differences.
Both OAM RAM and its write trace match, overflow flags remain clear, and 1,032
IRQ context checks find zero faults. The worst IRQ entry-to-RTI cost is 1,220
master clocks under the fixture's held CPU context.

Native debugging established two authorities: OBSEL's tile base is in 8K-word
units, and the screenshot's row indexing requires row y's packet at hardware
scanline y HBlank. Complete field traces and source pixels verify that mapping;
the screenshot alone is not the proof.

The sparse joint residency model also now counts initial preloads against bank
capacity until their first legal prefetch row. Its previous gap could admit a
logical schedule that the independent pixel/liveness replay rejected. A
regression holds a full early row and a sixteenth late color and checks both
the infeasible zero-lookahead case and the valid one-line preload case.

The remaining raster gate includes authored textured underlays, player and
enemy palettes, source alpha across changing scene pixels, animation changes,
and production NMI/audio/background contention. This controlled witness does
not reserve eight palettes for an actual gameplay configuration and does not
reject any other lossless presentation family. MOTU selection, combat and full
Demo completion remain uncertified.
