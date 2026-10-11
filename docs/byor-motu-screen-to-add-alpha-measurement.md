# Measured additive alpha alternative

BOR 4086 alpha 1 remains RGB8 SCREEN followed by RGB555 projection. The new
generic tool measures SNES full ADD using unchanged source RGB555 identities;
it does not select or implement an ACCEPTED_COMPAT policy.

For the authored GUILE2 BR12 peak viewport, ADD changes 2,447 of 57,344 pixels.
Maximum channel error is eight RGB5 steps; mean absolute error among changed
pixel channels is 2.124915. Exhaustive comparison covers all 65,536 pairs of
RGB8 channel inputs, with projected errors from minus one to plus eight.
The HBreath source retains all 204 RGB555 identities and 2,751 opaque pixels.
No color reduction, artwork resizing or opaque-effect substitution occurs.

Source layer order places the foreground after the effect. The measurement
replays that order but proves no native layer routing, compiled raster schedule
or concurrent-actor admission. Alpha compatibility remains unselected.

The exhaustive comparison test passes. Retained receipts bind current source
PAK and composite hashes and identify both exact and alternative output hashes.
