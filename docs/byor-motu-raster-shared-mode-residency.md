# Source-exact shared scanline mode search

The authored peak context still has no admitted full raster schedule. No color
reduction was applied, and these measurements do not reject raster universally.

The generic bank residency search can now select one SNES color-math mode for
each scanline. Every OBJ piece retains its input bank across its entire geometry.
The two shared color windows determine whether upper-bank pixels use literal
output or exact arithmetic operands. Each mode considers a canonical exact
inverse and the input word when it remains exact. This is a bounded operand
family, not an exhaustive search over all RGB555 encodings.

Emission replays the complete source RGB555 frame, transparency masks, palette
state and physical CGRAM packets. The synthetic test has 64 distinct literal
outputs and 64 additive operands; its zero-write fixed-mode schedule is
infeasible. Shared scanline mode selection preserves all pixels with zero writes
on both CP-SAT and HiGHS. This tests arithmetic encoding, not an adaptation of
BOR's SCREEN alpha semantics.

Fresh 8-by-8 geometry with the source-replayed pool controls admits 103 OAM
entries, 19 sprites and 19 tile slivers per scanline. This proves geometry and
bank capacity only; its initial schedule needs 48 peak palette writes. Bank
rebalancing retains exact pixels and reduces its interval objective from 27.6
to 20.0 writes. Strict transfer searches remain UNKNOWN.

The existing 80-piece geometry yields a complete witness with nine changed
scanline modes, 19 peak writes, a 352-clock ideal transfer span and a 984-clock
emitted physical span. Its full viewport RGB555 hash remains
`4d1f01dece9f9a50ecde25d1efc3d9e3da2bc0ee3974fc2702650ee0d9cf2934`.
All 576 eligible permutations of its fixed write trace retain a minimum
352-clock ideal peak. The strict 337-clock search remains UNKNOWN; a physical
packing heuristic fails at line 128. These are restricted searches, not a
hardware impossibility proof.

A separate pure literal output construction admits 57 OAM entries and peaks of
10 sprites and 10 tiles. Its eight-line interval 128 through 135 contains 275
distinct output colors. Even granting an undifferentiated 120-color resident
pool and optimal preloading, 155 new commitments are necessary across seven
HBlanks: at least 23 commitments in one boundary and a 352-clock first-to-last
commit span. This rejects that pure literal family against the measured
336-clock native window. The artifact's original bound uses a 356-clock budget;
its non-rejection label must not be used as admission against 336 clocks.

Forty-nine focused tests pass. The width audit reports 9825 labels and zero new,
baselined or stale failures. All 17 protected fingerprints match. No runtime
assembly, bank-zero allocation or original BOR static presentation was changed.
Native authored presentation, concurrent actor admission, production resource
leases and MOTU Demo completion remain open.

The receipt and compressed complete offline witnesses are retained in
`docs/receipts/byor-motu-raster-shared-mode-residency.json` and its `.gz` sibling.
