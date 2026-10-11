# Source-exact operand retiling

The generic offline retiler rebuilds legal 8x8 pieces from decoded source
operands, crossing earlier palette bank boundaries while preserving color-math
eligibility and explicit allowed-bank restrictions. It assigns fixed banks,
checks OAM and scanline limits and independently replays every source operand.
Opaque RGB555 zero uses a nonzero pixel index; transparency remains index zero.
Source alpha controls remain part of the compiled schedule hash.

For the authored peak frame, a bounded search over 64 grid origins finds an
origin at (3,7) with 103 pieces and 18 sprites/tile slivers per line. All 2668
drawn source operands remain exact; the existing 83 underlay-equal pixels still
bypass OBJ drawing. This leaves scanline headroom compared with the previous
80-piece layout's 34-tile peak. It is not a concurrent actor admission.

The selected bank assignment remains above the transfer gate. Rebalancing and
39 LP-guided proposals lower its validated cache bound from 21.625 to
21.583333, still requiring at least 22 writes on some line. Joint searches can
optionally add fixed bank masks to hinted rectangles while retaining complete
OAM, sprite and tile constraints. Both a 337-clock activity-bound search and
an 18-write bank-symmetric search return UNKNOWN. They do not reject general
raster presentation.

The joint solver can also collapse the actor-free prefix outside the pinned
pool family. VBlank chooses the first visible palette and holds it through
that prefix, with all palette slots counted. The full joint model drops from
218390 to 101559 variables. The focused suite proves source replay, capacity,
zero prefix writes and reduced model size. A separate test demonstrates that
one extra fixed bank mask preserves a 16-color piece lifetime with zero raster
writes while the one-bank family is correctly infeasible.

Further complete physical repairs preserve the 21-word cap and improve the
aggregate span from 11568 to 11264 clocks. The peak remains 552, above the
native-tested 336-clock window. All physical packets are independently replayed.
The 55 focused tests pass; the width guard checks 9825 labels with zero failures.
All 17 protected files retain their hashes. No shared runtime assembly changed.
No color reduction was applied. Authored native raster, concurrent gameplay
and MOTU Demo completion remain unproven.
