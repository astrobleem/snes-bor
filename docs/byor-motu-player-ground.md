The ground-movement controller preserves the literal tail of pinned BOR 4086
player_think, from the PLAYER_MIN_Z branch through endthinkcheck. It runs after
the earlier player gates and running cancellation.

Duck and turn animation transitions, item search/didhit/collection, and ordinary
walk/backwalk/up/down/idle animation helpers are mandatory service boundaries.
The controller keeps its local action across item callbacks, then reads fresh
entity and level state when choosing the final animation. Duck clears velocity
after its callback; turn clears it before its callback. The second backwalk
level-facing test retains the literal source RIGHT comparison.

The authority proof compares 7,936 cases and 1,428,480 bytes with the unchanged
pinned C block. It compares ordered animation queries and service requests as
well as final fields. Five callback modes exercise direction, facing, velocity,
idling, timer and action mutations. Timer wrap and opposing-key precedence are
included. Service implementations are explicit instrumented stubs in this
authority test. Source floating-point speeds remain binary32 in this model.

Native actor storage, these services, earlier player branches and the production
dispatcher still require binding. This proof does not certify MOTU gameplay or
completion. No color reduction is applied.

The native continuation proof covers 2,653 cases, including seven readiness,
pending-owner, acknowledgement, request-echo and numeric-domain guards. It runs
the complete query/service protocol, compares ordered traces and callback-mutated
fields, and checks CPU/stack retention with decimal mode set. All requested
services are instrumented in this proof. The 128-byte caller snapshot is not a
canonical actor row; a production binder must refresh/publish its fields at each
source boundary. Snapshot action 42 denotes common_turn only on this wire.

Native speeds use the existing finite Q16 scalar ABI. An odd Q16 speed requiring
division by two fails explicitly; negation outside signed Q16 fails explicitly.
The tested source speeds and callback velocity values are exactly representable.
The compiler arena plan reserves 128 bytes for this serialized continuation.
