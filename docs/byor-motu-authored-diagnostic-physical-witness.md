# Authored-frame physical diagnostic witness

A fixed-write-time physical schedule is found in 25.011 seconds. It passes
CGRAM packet and source operand replay, with 20 peak writes and eleven-line
prefetch. Its 536-clock peak exceeds the measured transport bound; it is a
diagnostic seed, not native admission. Expensive runtime proof is not run
against a schedule already exceeding the window.

Independent composition from the current PAK confirms all 57,344 viewport
pixels against authored RGB8 SCREEN projected to RGB555, source hash
4d1f01dece9f9a50ecde25d1efc3d9e3da2bc0ee3974fc2702650ee0d9cf2934.
Geometry remains 80 OAM entries, 24 sprites and 34 tile slivers. Source metadata
also matches. No alpha adaptation or color reduction is applied.

Exhaustive eligible bank permutations and slot reflections retain a 536-clock
peak. Four bounded exact local repairs retain all packet and pixel identities
and reduce aggregate span from 22,056 to 12,016 clocks, but the peak remains
536. The repairs retain a 21-write cap and a 344-clock ideal bank bound for the
full frame. Neither diagnostic search nor local repair rejects raster.

Authored alpha native proof, concurrent actors and production admission remain
open. NO color reduction applied.

Eight further repairs expand local windows through lines 126..149. All return
FEASIBLE and preserve the full-frame pixel/CGRAM identities, write cap and
ideal bank bound. Six improvements reduce aggregate span to 11,624 clocks;
the peak remains 536 clocks. No native admission follows.
