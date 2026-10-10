# Standalone native model frame child

A generic standalone model owner now consumes service 4 without a waiting
parent frame. It runs the real animation-init StartFrame, native frame owner,
scripts/effects and animation-init Ack, then resumes model services. External
frame tickets remain explicit and resumable. Generation, slot identities and
frame-stack ownership are checked before child execution. The runtime solves
no source semantics and contains no actor-name branch.

Twelve source-derived weapon-argument cases passed with a synthetic zero-sync
API argument. Another twelve cases passed with synchronization retained and
a synthetic missing current animation, derived from the actual inherited cache.
Their service traces are 1,2,3,4,4,5,6,7,0, with zero mismatches
and no observer acknowledgements. Every indexed view, core, cache, animation,
callback variable, scoped palette and CPU expectation is compared. The frame
is issued without dispatching a parent animation or source weapon frame event.

Expected restart behavior follows pinned BOR 4086 ent_set_anim: animation
restart does not perform set_idle's idling or velocity changes. Those fields
remain in the byte comparison with their actual pre-call values. This differs
from the nested parent weapon/set_idle proof's input context.

The [receipt](receipts/byor-motu-standalone-model-frame-child.json) records
native artifact hashes and a peak of 1,030,072 master clocks over three fields,
including interrupts. This does not establish a production tick budget.
Bank zero remains byte-identical. Full spawnplayer, production ownership,
foreign profile admission, lossless HBreath runtime and Demo completion remain
open. No color reduction or PCM copies.
