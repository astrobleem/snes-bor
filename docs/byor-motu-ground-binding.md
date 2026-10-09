# Canonical ground-controller state binding

The opt-in compiler emitter binds the ground continuation's actor fields to
the production source-world arrays. It does not provide a complete player
controller or grant a RAM lease. No model name selects behavior.

`GroundBinding_Capture` reads running, direction, turntime, speed, X/Z velocity,
takeaction and idling from their canonical owners. Turning remains a full
signed DWORD in the module-tail entity row. Runspeed comes from the entity's
immutable RUN handle, preserving its snapshot across later shared-cache
inheritance. The current model identity selects source-derived facing and
turndelay. These two loader fields have zero defaults and signed integer
assignment; the 160-byte cached-core packing remains unchanged.

`GroundBinding_Publish` writes direction, turntime, X/Z velocity, takeaction,
idling and turning after validation. Running and speed are inputs owned by
other services. A model change between capture and publication rejects the
write. The wrapper checks the loaded VM slot count and generation through the
actual player-state owner on both entries. It retains all other actor bytes
and sibling state. The enclosing controller must serialize these services and
recapture after callbacks; this binder is not a lifetime token for an actor
that dies and is reborn in the same slot.

The ground snapshot's private `common_turn` wire value 42 is rejected before
actor writes. A real action dispatcher must bind that service before this path
can admit a turn animation. Animation, item search, item pickup, walk-family
selection and idle services remain mandatory. Level context, source time,
notinair and the entry-captured player input row belong to the enclosing
controller, not this binder.

The binder requires 32 caller-owned control bytes. `W+0` is readiness B67C,
`W+2` is success 2 or fault 3, `W+4` is the physical slot, `W+20` captures the
model identity. The remaining bytes are private arithmetic and continuation
controls. Ground, player-state, RUN and handle regions must be distinct.

The authority and native receipts record their exact scope. The native proof
uses the actual source-world ABI and player-state accessors with instrumented
module/root installation, exercising every physical slot and both RUN tuples.
It checks signed integer values, decimal-mode entry, CPU retention and complete
actor-array preservation outside declared writes. It does not prove production
player dispatch, MOTU gameplay or a live lossless effect renderer.

No color reduction is applied.
