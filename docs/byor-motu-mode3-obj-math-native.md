# Native Mode 3 underlay and OBJ math routing

The authored actor-free GUILE2 context needs 58 RGB555 identities. A static
8bpp BG1 palette fits below CGRAM 128, leaving all eight OBJ banks available.
The native proof uses Mode 3 with BG1 on both main and subscreen, OBJ on main,
and OBJ-only addition. BG1 itself bypasses color math. Its 596 deduplicated
tiles occupy 38,144 bytes; the tilemap occupies 2,048 bytes at VRAM F000.
Two sample OBJ tiles occupy 64 bytes at C000. No VRAM regions overlap and no
background raster palette writes are needed.

The sample masks come from the independently replayed peak effect schedule.
They are selected generically by static color capacity and source pixel count,
not model identity. They preserve 55 normal and 62 additive source pixels at
their original positions. Each expected RGB555 value is checked against the
literal source RGB8 SCREEN composite. Static sample palettes remap these
colors without reducing them.

Four native cases exercise banks 0/4, 1/5, 2/6 and 3/7. Each runs three fields
with zero viewport pixel mismatches across 57,344 pixels, exact CGRAM RAM and
port traces, exact OAM upload, and zero sprite/tile overflow flags. This proves
the normal/additive eligibility of all eight banks under the tested routing.
The screenshot is supporting evidence; RAM, port traces and pixel comparison
are independent checks.

Only 117 effect pixels are sampled. This does not render the complete effect,
execute its raster schedule, prove live underlay generation, bind production
NMI/audio, or certify MOTU gameplay. It resolves the immutable-underlay layer
routing seam while the complete timing and concurrency gates remain open.
No production assembly, bank-zero allocation, static BOR path or media changed.
No color reduction applied.

The optional solver hint maps an existing validated schedule's masks/pixels
onto the current Boolean graph. Metadata, source image identity and geometry
must match. Hints are soft and never replace constraints or independent replay.
Its 180-second timing-constrained trial with 10,348 hinted variables returns
UNKNOWN/no incumbent, not infeasibility. 24 joint/backend tests pass, including
a contradictory hint that must still obey the actual model constraints.

[Native evidence and search receipt](receipts/byor-motu-mode3-obj-math-native.json).
