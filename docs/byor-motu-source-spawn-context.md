The generic source callback timeline executes the actual spawn01 script body
through variant bytecode, retaining callback timing, model identity, binary32
position stores and declared child lifetimes. Allocation is assumed successful.
It does not certify child initialization, motion, collisions, interruptions,
loops or world reachability. Declared lifetime overlap is an upper bound on
live instances, not a count of visible pieces.

He_ManB freespecial4 creates HBreath at tick 48 with altitude 93 and lifespan
300 ticks. The uninterrupted parent animation lasts 312 ticks. Skeletor rise
contains sixteen spawn01 calls; their declared lifetimes overlap up to thirteen.
The bounded visual fixture executes the child spawn script at its frame one,
using the pinned first-stage player Z bounds 160 through 232. Two children are
killed by that guard at parent Z 220. check_ai precedes update_animation, so the
stopped eight-tick spawn animation returns to idle on the following tick.

The fixture samples every nominal visual transition during the rise. It holds
the parent positions fixed, pairs a breathing player pose and HBreath frame 11
with the source-timed Skeletor and surviving geysers, and replays RGB8 SCREEN
before RGB555 conversion. The color peak is 85 final visible OBJ colors on one
line at tick 329. At tick 341, separate actor ownership requires at least 36
eight-pixel slivers on a line, exceeding the hardware limit of 34. This bound
grants arbitrary row alignment, masks, bank allocation and legal OBJ widths.

The 36-tile result rejects separate actor-owned geometry for this conditional
pose. It does not reject cross-actor packing, other lossless architectures or
prove combat reachability: geyser collisions may interrupt the fixed player
pose. No native scene, foreign profile, gameplay or Demo completion is admitted.
Ten callback tests pass, the width audit is clean and the seventeen protected
fingerprints match. No color reduction is applied. The receipt archives the
timeline, scenes, transition sweep and independent row geometry bound.
