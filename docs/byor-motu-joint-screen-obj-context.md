# Joint SCREEN OBJ context: fixed banks fit, plain outputs exceed bandwidth

The generic probe reproduces the explicit source GUILE2 scene with He_ManB,
HBreath frame 11 and Knightbot. SCREEN blending runs in RGB8 before the existing
RGB555 projection. It retains original model/frame dimensions, palette sources,
flip and layer order. Hidden actor pixels are excluded only after the complete
source composition, including frontpanel coverage. Recombining the visible
precomposited actor pixels over the actor-free source scene matches every final
RGB555 pixel. No HUD, shadows, quake or gameplay reachability is certified.

This variant schedules all visible actors together across all eight banks. It
reserves no static actor palettes and uses no OBJ color math. A bounded CSP finds
and independently verifies a fixed bank assignment in mixed legal 8x8/32x32
geometry: 61 OAM entries, 12 sprites and 28 conservatively counted tile slivers
at peak. The 75-color peak line and 115-color adjacent union fit the relaxed
120-slot capacity. The heuristic schedule still peaks at 57 writes / 114 data
bytes. Those figures are an upper bound, not a hardware admission.

A stronger interval proof rejects this plain output encoding independently of
bank assignment, subdivision, liveness and lookahead. Source lines 126 through
135 need 354 distinct visible OBJ output colors. Even with an ideal shared pool
of all 120 opaque slots and one preloaded CGRAM low-byte latch, at least 467 data
bytes must be transferred across nine HBlanks. The generous data-only limit is
396 bytes: 44 per line at eight master clocks per byte in the 356-clock safe
window. At least one interval line needs 52 data bytes / 416 clocks. Addresses,
setup, synchronization and other runtime work have all been excluded in favor
of the candidate. The PPU/DMA sources and existing native bus trace are hashed
in the receipt. This is not the adjacent-line set difference called bandwidth.

The earlier opaque-palette MILP timed out without an incumbent. The CSP finds a
valid assignment; neither that timeout nor a later bounded search for seven
writes establishes infeasibility. A separate 20-write residency MILP rejects
one particular assignment. The interval bound is the assignment-independent
failure of this explicit precomposited, non-math output strategy.

Other OBJ math/residual encodings and BG/hybrid remain open. This is not a
universal raster rejection or PRODUCT_DECISION_REQUIRED. The original static
compiler and runtime paths are unchanged. Seventeen focused raster/static
compiler tests pass; the width audit has zero violations and all 17 protected
hashes are unchanged. No color reduction or PCM copies were made.
[Context receipt](receipts/byor-motu-joint-screen-obj-context.json).
