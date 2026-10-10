# Common action dispatch through check_ai

The generic offline emitter recognizes source function identities for pain,
grabbed, block, land and fall, then executes their compiled native owners.
It borrows the existing serialized common-idle controls and releases them only
after the actual child completes. Unknown callbacks enter the existing dispatcher
with its saved CPU stack. Optional fallback entries permit composition with the
foreign player and jump dispatcher without actor-name branches.

Five native tests pass 12 cases each through real check_ai, source model/cache
services, animation initialization and frame ownership. Each uses a fixture-installed
stopped actor, due nextthink, canonical self and null think pointer. The test calls
check_ai twice and observes exactly one frame-zero issue. Fall includes its
common_land successor: doland changes the actor's takeaction, so compiling only
common_fall correctly faults on the next call. That incomplete test remains FAIL.

Retained tickets propagate unchanged. Resume validates the captured world action
lease before entering the actual frame owner; it cannot use the ordinary AI idle
check while a frame callback remains active. These synchronous cases do not prove
ticket resumption. No production dispatcher consumer, complete world tick, damage
callback or MOTU gameplay is admitted by this proof.

Bank 0 is unchanged, no foreign arena bytes are added, and all 17 protected tracked
hashes match. The width audit has zero violations and zero baseline entries.
No PCM copies or color reduction are applied.

[Bounded receipt](receipts/byor-motu-common-action-check-ai-native.json).
