# Authored parent pose during the HBreath peak

The source callback that creates HBreath is He_ManB freespecial4 frame 4.
Actual spawn01 bytecode places it eighteen units forward and ninety-three
units above the parent; for the measured right-facing parent at (80,220,0),
the child position is (98,220,93). The He_Man declaration lists He_ManB in its
weapon models. This does not certify runtime weapon-model selection.

The pinned loader converts centisecond frame delays to 200 Hz ticks. The
spawn callback is at parent tick 48. HBreath frame 11 occupies nominal ticks
114..120. He_ManB holds frame 6, breath7.png, from tick 72 through 312, so the
previous overlapping player/effect scene uses the matching nominal pose.
The generic query tool derives this intersection from source frame records
and actual spawn01 script bytecode; it has no actor-name behavior switch.

Four spawn timeline and pose tests pass, including expiry clipping and exact
spawn position. Successful allocation, child idle startup at birth, fixed
parent position and an uninterrupted animation are assumptions. Constructor
phase, damage/cancellation, input reachability, motion, collisions, repeated
casts and native gameplay remain unbound. This is not a universal count bound.

NO color reduction or alpha adaptation is applied.
