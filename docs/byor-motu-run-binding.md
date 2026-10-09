# Canonical running cancellation

The generic binder separates player_think entry capture from running
cancellation after preinput/callbacks. CaptureEntry reads the old signed running
value and validates/captures the entry player's typed index. Cancel reads fresh
running and X/Z velocities from canonical actor storage and fresh held keys
from that entry-captured player history row. Changing playerindex during a
callback does not retarget the source's already captured `pl` pointer.

Runupdown comes from the entity's immutable RUN snapshot through the actual
tuple reader. A later shared cached RUN mutation does not change this entity's
earlier copied flags. The actual running predicate determines the result and
publishes only running to its canonical AI scalar row. Nonzero signed running
values retain their exact bits when allowed. Other actor fields are unchanged.

The binder needs 32 control bytes alongside the existing 48-byte running
predicate and 64-byte tuple controls. B681 is readiness, +2 is lifecycle state
0 idle/1 entry captured/2 cancellation complete/4 fault; +4 is captured physical
slot, +6 is captured player index, +8 is signed oldrunning. Cancellation requires
the same selected slot and a ready history owner. All calls are serialized under
the enclosing controller's lease. It does not independently certify actor birth
identity across a death/reuse of the same slot.

The native constructor/ground callback proof instruments the preinput boundary
to change running, velocities, playerindex and cached RUN flags. It then runs
the real bound predicate, ground continuation and WALK/RUN/IDLE frame owners.
The preinput mutations and input/level/root installer are explicit test context,
not authored input execution or full player_think certification. Production
input refresh, preinput, earlier controller gates and the complete foreign root
remain required.

No color reduction is applied.
