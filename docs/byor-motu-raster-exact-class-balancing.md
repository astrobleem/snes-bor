# Exact literal and math bank balancing

The generic interval-demand bank balancer can re-encode eligible source pieces
between literal lower banks and exact arithmetic upper banks. It derives words
from the validated source viewport, its RGB555 underlay and the shared scanline
math/window controls. A piece cannot enter the upper class if an enabled pixel
has no exact operand. Explicit bank restrictions remain enforced. Each selected
bank stays fixed across all rows of its OAM piece.

The emitted schedule remaps indices, retains source transparency and replays
the full viewport against the original source. Geometry remains unchanged.
Default balancing retains the previous word-preserving class behavior. Tests
force re-encoding in both directions and reject restricted banks or a changed
source context. Fifty-five focused tests pass, the width audit passes with 9825
labels and zero failures, and all 17 protected fingerprints match.

The fresh authored 103-piece witness remains exact, with 19 sprites and 19 tile
slivers per line. Its interval objective remains 20.0 peak, while aggregate
pressure improves from 56742 to 51914 and bank identity duplication from 637 to
625. Those objectives are scheduling lower bounds, not physical admission.
The full RGB555 viewport hash remains
`4d1f01dece9f9a50ecde25d1efc3d9e3da2bc0ee3974fc2702650ee0d9cf2934`.

Sixty-second strict shared-mode residency searches with 16- and 55-line lookahead
both remain UNKNOWN. A two-minute joint search with the admitted geometry as a
soft hint also remains UNKNOWN. Restricting each rectangle to one bank per math
class gives no candidate in sixty seconds. Searching the original shared-mode
witness with exact operands and physical slots remains UNKNOWN even at a
473-clock transfer gate.

Retaining each saved pool color in one bank for its complete interval rejects
the 16-line preload family during presolve. The same family with 55-line
lookahead remains UNKNOWN. This demonstrates why an offline lookahead policy
failure cannot be reported as a hardware impossibility. No universal raster
rejection or native admission follows from these results.

No color reduction or runtime assembly change was made. Native authored
presentation, concurrent actor admission and the MOTU Demo candidate remain
open. The receipt and compressed witnesses are retained under
`docs/receipts/byor-motu-raster-exact-class-balancing.json` and its `.gz` sibling.
