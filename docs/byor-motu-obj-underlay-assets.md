# Static authored underlay assets for an OBJ alpha proof

`source_obj_underlay.py` compiles an actor-free source viewport into exact
Mode 3 BG1 assets. It uses nonzero CGRAM indices 1..127, leaving OBJ words
128..255 available. Visible black remains a nonzero BG index. The compiler
deduplicates planar 8bpp tiles, builds a 32x32 map and independently decodes
the emitted CHR/map/palette back to every source RGB555 pixel. Palette,
viewport and VRAM capacity failures are explicit.

The isolated GUILE2 viewport uses 58 colors and 596 unique tiles: 38,144 CHR
bytes, a 2,048-byte map and a 256-byte lower palette image. It fits BG1 CHR
below B000, a map at B000..B7FF and OBJ CHR at C000..FFFF. Its RGB555 hash is
`b709ce24b7bed3d5b275f5039619ef256f02f6b04a610994c096103b7c0d27c3`.
Asset hashes and source metadata are retained in
`docs/receipts/byor-motu-authored-obj-underlay-assets.json`.

This is preparation for raster OBJ math, not a fallback BG effect renderer.
It proves only offline static assets. Native main/subscreen routing, alpha
controls, foreground ownership, background streaming and combined timing
remain unproven. No production assembly or bank-0 changes.

The operand constructor also supports exact word selection shared across the
whole frame. Default row selection remains unchanged. This produces 136 small
source-exact masks, compacting to 52 legal 8/16 entries with seventeen sprites
and 33 tile slivers. Rebalancing preserves all pixel identities. Its interval
proxy is 18.1667; the independently validated cache LP is actually 20.7143.
Its twenty-write solve is infeasible. A 22-write, 356-clock single/adjacent-pair
transfer search is infeasible, while its general-range search returns UNKNOWN
at sixty seconds. These reject only their fixed encoding and range restrictions.

The joint search has an optional maximum bank masks per piece and math class.
Its default remains unrestricted. A focused test requires two banks for a
sixteen-color fixed rectangle without raster writes. In the HBreath eight-pixel
grid, one bank per class fails even with a 120-write allowance under the saved
pool controls and four-row chunks. Allowing two banks returns UNKNOWN at sixty
seconds with a 356-clock necessary transfer bound. The unrestricted fine and
mixed grids return UNKNOWN at ninety seconds. No universal raster rejection.

Fifty-eight joint/construction/residency/rebalance tests and three underlay
encoding/resource tests pass. No color reduction applied. Authored native alpha
and MOTU Demo completion remain unproven.
