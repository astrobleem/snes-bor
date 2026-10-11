# Row masks improve the authored palette clock bound

Using the improved whole-piece assignment as a seed, the row-word mask
search lowers the assignment-specific fractional clock bound from 353.923 to
304.336. Each emitted OAM entry still has one fixed bank. Source words may
use different entries across rows; the compiler masks their pixels exactly.

The four-second master trial returns UNKNOWN. Its resumed trial gives each
master up to sixty seconds and permits up to sixty-four changed row-word
choices. Three evaluated assignments give bounds of 353.923, 309.561 and
304.336. These bounds grant fractional cache residency and optimistic bank
bridges. They are not integer residency or physical DMA schedules.

Independent replay preserves all 2668 encoded source pixels, bank eligibility,
source-word identity and full rectangle geometry. The best candidate reaches
128 OAM entries, 32 sprites per line and 32 tile slivers per line. This is an
HBreath-only construction with no OAM headroom for concurrent actors. It does
not admit gameplay or reserve all palettes for the effect in production.

The source composed RGB555 hash remains
`4d1f01dece9f9a50ecde25d1efc3d9e3da2bc0ee3974fc2702650ee0d9cf2934`.
Alpha encoding remains exact BOR 4086 RGB8 SCREEN projected to RGB555.
No color reduction or alpha adaptation is applied. Integer cache scheduling,
physical slots, native timing, concurrent actors and MOTU completion remain
open. The receipt retains both complete search artifacts and source hashes.
