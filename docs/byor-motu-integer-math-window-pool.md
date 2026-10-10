# Whole-color math/window capacity witness

The generic math/window liveness tool can now require integer palette
residency and use CP-SAT. Integer modes and window eligibility remain required
when using that backend. Fractional palette values cannot be reported as
whole resident colors. Saved candidates support independent source replay,
including direct RGB555 arithmetic for the resident words rather than reliance
on a particular operand-dominance representative.

The corrected source-height attack pose contains He_ManB, HBreath frame 14,
three source-queue KnightBots at authored altitude 40 and three ShockBalls
spawned at altitude 74. Simultaneous AI timing remains unproven. On rows
120..152, CP-SAT finds an integer class-pool candidate at 22 writes. The
attempted fifteen-second LP hint times out and supplies zero hints; the
successful integer result must not be credited to an LP hint.

The initial candidate omits four clipping-compatible black pixels. Direct
source replay identifies all four as uncovered. Replacing an unused initial
literal word 13839 with RGB555 black in rows 120..123 restores them without
adding a noninitial write: the original word is already evicted at row 124.
All 4,605 non-underlay-equal source pixels in the interval now replay exactly
under the chosen modes and compiled two-window masks. Each class remains at
most sixty colors, and independent residency replay peaks at 22 writes.
The saved full-source interval witness has no clipping-pixel relaxation.

This is a **necessary class-pool witness**, not an eight-bank schedule. Fixed
OAM banks, individual fifteen-slot banks, actual OBJ geometry, physical DMA
ranges and register/update timing remain unproven. Demand outside rows
120..152 is excluded and initial residency/preloading is unrestricted. It
does not certify full-frame alpha, live gameplay or raster feasibility overall.

Candidate replay keeps solver statistics as input-generation provenance,
distinct from verification of the repaired colors. Scope checks bind source
PAK, scene bytes, exact RGB555 output hash, modes and window/clipping policy.
Focused tests reject missing source colors and understated write counts, and
exercise integer palette admission with both solver backends. Twenty-three
mode/cover/window tests pass. No color reduction is applied.

The exact witness and source-replay fields are retained in
`docs/receipts/byor-motu-integer-math-window-pool.json.gz`.
