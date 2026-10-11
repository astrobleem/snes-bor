# Subscreen OBJ operands over the source background

The four-bank OBJ color-math restriction applies to the main-screen OBJ pixel,
not a subscreen OBJ operand. Mesen's PPU source checks `palette > 3` only while
setting the main pixel's math flag. Its subscreen OBJ path samples all eight
palettes. Native source-derived row tests now verify that distinction.

The generic joint scheduler has an explicit `subscreen-additive` encoding.
Every source output must admit an exact additive RGB555 operand over the
source-derived background. The main screen uses BG1 with color math; the
subscreen uses OBJ with fixed color zero where no OBJ is visible. Main-screen
OBJ is disabled and subscreen backgrounds are disabled. Outputs darker than
the background fail explicitly. This is exact arithmetic encoding of BOR's
RGB8 SCREEN result, with no color reduction or alpha adaptation.

The palette-bank restrictions are derived from the screen routing. Eight-bank
subscreen and precomposited schedules can use all eight banks in bank balancing,
physical relabeling and slot construction. Existing main-screen additive
encoding retains its four literal and four math banks. Unknown eligibility
modes fail explicitly.

For the authored peak frame, the source underlay remains exact. The relaxed
120-slot operand pool has a validated write lower bound of 18.2, both with the
canonical words and the complete operand cover. A 56-piece construction fits
10 sprites and 10 tiles per line, but the balanced fixed-bank encoding fails
the strict 337-clock optimistic transfer gate. This rejects that assignment,
not all subscreen schedules.

A global word-to-bank construction admits 95 OAM entries, 20 sprites and 20
tiles per line, preserving all source operands and transparency. It has 396
distinct operands across the frame. Its fixed-bank residency also fails the
strict gate. A joint bank/transfer interval relaxation remains UNKNOWN.
Four- and eight-row word epochs allow word-bank choices to change between row
groups while each emitted OAM mask keeps one fixed bank. These bounded searches
also remain UNKNOWN. Interval unions count repeated RGB555 identities once;
aggregate transfer certificates independently replay their counts and bank
partitions, and never claim physical slot or cache admission.

Native static rows 112 through 166 pass: 55 source rows, 165 fields and
9461760 complete-viewport pixel comparisons with zero mismatches. CGRAM, OAM,
VRAM and register observer identities all match, with zero OBJ overflow flags.
The 2668 drawn source pixels and 83 exact underlay bypasses cover the original
2751 opaque source pixels. Combining the independently measured row results
reproduces RGB555 hash
`4d1f01dece9f9a50ecde25d1efc3d9e3da2bc0ee3974fc2702650ee0d9cf2934`.
The row-128 screenshot is a static row measurement, not a full raster frame.

The main-screen row-128 regression passes on the same ROM bytes as the earlier
native proof: `97d258885596020d5d309dfa236794e24bc4997f0a0a888b741d061c8add090b`.
Eighty-three focused tests pass. The width audit passes with 9825 labels and zero
failures, and all 17 protected fingerprints match. The complete native row
proof occupies 1683751 bytes; no PCM copies were made. Production runtime and
bank-zero code were not changed.

The generic word-bank balancer changes whole-frame word assignments while
rebuilding exact fixed-bank masks. It checks each row's fifteen-slot capacity,
actual OAM entries, sprite count and tile slivers. Its interval objective is
explicitly a relaxation; retained source pixels are independently replayed.
Overlapping unequal eligibility domains fail because their alias accounting
is not implemented. All eight subscreen bank permutations are available to
the residency bound and fixed-slot optimizer; the default main path retains
its separate four-bank groups.

A twelve-seed, 20000-proposal frontier produces a validated fractional cache
bound of 19.75 writes, compared with 42 for the initial 95-mask assignment.
The retained frontier uses 128 OAM entries. Another interval-optimal candidate
has an 18.2 interval bound but a 22-write cache bound, demonstrating why the
interval score alone cannot admit a schedule. These are HBreath-only offline
constructions; no actor capacity reservation or physical transfer proof follows.

Existing native constant-control transport admits 344 clocks, with first-high
positions 1096 through 1104 and zero unsafe commits. The 336-clock bound includes
variable prepalette source control traffic. Subscreen addition uses constant
controls, so the 344-clock transport is the relevant private-fixture starting
budget. Full authored raster execution and production contention remain open.
The retained frontier's bounded 345-clock strict cache search is UNKNOWN after
45 seconds. It does not reject the assignment or the subscreen route.

This route has an explicit concurrent-layer constraint: its main-screen OBJ
layer is disabled. Regular actors cannot be assumed to retain their normal OBJ
presentation under that configuration. Concurrent actor routing, full raster
CGRAM execution, production resources and the MOTU Demo remain open. No lossless
BG fallback was selected and no universal raster rejection follows.

The receipt and compressed source/native witnesses are retained under
`docs/receipts/byor-motu-raster-subscreen-obj-routing.json` and its `.gz` sibling.
