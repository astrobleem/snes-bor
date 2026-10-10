# Mixed OBJ geometry and physical slot layout

The 1,200-second mixed 8/32 search produces a source-pixel-exact isolated
candidate with 62 OAM entries, 19 peak sprites, 34 peak tile slivers and 19
maximum color writes (38 data bytes). Average writes are 2.220 per line. Its
strong physical-bank range lower bound peaks at 352 commit clocks on line 128,
below the 356-clock accessible window. This bound still grants ideal endpoint
slots and excludes setup/contention; it is not native admission.

The generic CHR/OAM compiler emits 7,264 bytes in 227 tile cells (176 unique
tiles), with eleven 32-pixel and 51 eight-pixel objects. It decodes emitted OAM
attributes and native 16-tile-pitch CHR footprints to reproduce every original
piece index and palette bank. The occupied first page at VRAM C000 ends at
DC60, below the isolated underlay's F000 map; its 38,144-byte BG CHR ends before
the OBJ base. This proves this allocation constructively, not concurrent scenes.
The tile compiler supports reserved cells and both OBJ name pages; greedy
placement exhaustion is explicitly not an impossibility proof.

The physical slot planner colors palette lifetimes, assigns exact destination
ranges and reindexes each piece row offline. Its packet replay checks every
upper-CGRAM word, including transparent zero and bridged unchanged slots. The
fixed update times cannot be placed within either the 348- or 356-clock range
model. Dropping unused residents and shortening lifetimes to their last actual
pixel use still yields no fixed-time solution. These results reject that fixed
lifetime/update family; they do not reject raster virtualization.

`--flexible-prefetch` lets a needed lifetime begin during VBlank or within a
bounded lookahead before its first actual use. Optional physical-slot intervals
prevent overwriting live colors. The first 300-second, 16-line trial returned
UNKNOWN. Longer hinted prefetch and tighter joint geometry/residency searches
continue separately. Neither a timeout nor a necessary range bound admits the
production runtime.

Six focused new tests check physical packet/color replay, opaque black,
preloading under a tiny transfer window, every 4bpp value, second-page name and
size bits, palette-independent tile sharing and reserved cells. Production
presentation and bank zero are unchanged. Full native raster HBreath, authored
concurrency and MOTU Demo remain unproven. NO color reduction applied.

[Candidate and bounded layout receipts](receipts/byor-motu-mixed-raster-layout.json).
