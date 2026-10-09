# Generic foreign check_ai dispatcher

`source_foreign_ai_run_native.py` extends the actual check_ai runner using its
existing six-byte state/pending control allocation. New callback identities
select compiled owners; there are no actor-name tests. The unchanged legacy
dispatcher receives other requests with an identical saved CPU stack.

Fourteen isolated native cases execute real source construction, JUMPDELAY,
common_prejump, dojump sound continuation, source toss, JUMP frame, and the
common_jump/common_jumpland landing paths. Each action resumes the actual
check_ai sequence and animation-only think-script validation. The fixture
sets think absent and keeps the enclosing world service pending; it does not
commit the gameplay clock. Sound results and landing context are instrumented.

Twenty-eight invalid sound/frame continuations reject wrong service phase,
pending kind, callback identity, AI phase, child owner type, child slot, and
callback high word without modifying either jump owner or acknowledging its
frame. Completed common_prejump releases its temporary descriptor control
only after all dojump services finish. Persistent source jump arguments remain.

Fourteen further calls take the unchanged common_spawn dispatcher path through
real IDLE frame completion. Register, stack and status context checks pass.
No production assembly, bank-0 code, PCM data or palette presentation changes
are included. The standalone proof consumes no additional runtime control
arena storage. No color reduction is applied.

Reproduce with `tools/verify/m4_animation_callback_owner_native.py` using
`--canonical-tryjump --canonical-dojump --canonical-common-jump
--foreign-ai-jump`, the constructor/birth/frame-owner switches in the receipt,
and the pinned original BOR regression ROM. The bounded receipt is
`docs/receipts/byor-motu-foreign-ai-jump-native.json`; full reproducible scratch
is under `out/byor-motu-foreign-ai-jump-native`.

The separate `--player-controller --foreign-ai-player` native proof runs 248
constructor/controller cases through actual check_ai think callback 2. The 240
valid cases complete think, script validation and check_ai; eight stale ground
frame identities fault explicitly with the world service still pending. Their
complete controller vectors match the existing source-derived reference.
The fixture admits the same bounded controller capabilities as the prior
controller proof, including an empty item-search result and instrumented sound.

The controller occupies private ROM bank 39. Jump action and dispatcher code
occupy independently verified empty bank 57, with both sizes checked before
copying. The player receipt retains the hashes and bounded validation results;
the existing controller receipt retains full state comparison vectors.

Production world installation, physical sound playback, live item/grab/target
services and natural jump physics remain open. M4 is not complete.

`--natural-jump-delay` replaces the forced JUMPDELAY completion with actual
timed-animation execution. Fourteen cases retain animating=1 at tick 67 and
stop at the source-derived deadline 68, twenty ticks after the real frame-zero
initialization at tick 48. common_prejump then executes the real dojump path
at tick 68. Host instrumentation supplies the clock values; it does not write
animating. This proves the timed transition, not full world traversal/physics.
Timing and prefix descriptors occupy verified private ROM banks 55 and 56.

The timing capability requires autokill/cost/movement state enabled before
construction. A poisoned autokill row is cleared by the actual constructor
in all fourteen cases. Enabling that capability after birth exposes stale
storage and incorrectly requests kill instead of the source nonlooping stop;
the fixture now enforces the proper startup order. The existing reduced
animation-cache capacity still contains the 4,096-byte source animation map.

`--foreign-ai-world-ack` connects the player dispatch result to the actual
world phase-6 acknowledgment. All 240 completed controller cases release
the pending AI phase. All eight stale-frame faults retain pending=1 and set
the world fault. The clock stays at 48 in both cases; the proof neither skips
the remaining world services nor commits an incomplete tick.

The generic source type-filter inventory derives the actual 16-model declared
namespace and scans parsed functions and inline blocks. ITEM (4) and ENDLEVEL
(256) have no declared models. All 41 property writes across five libraries
and five inline blocks use known constant keys that neither replace model
data nor change type; the 65 script bindings have no diagnostics. Escaped,
dynamic, model/type keys, unknown APIs and binding diagnostics prevent this
inventory capability from being selected.

This supports the existing runtime-checked empty-candidate search for these
authored filters. It does not claim arbitrary engine services cannot mutate
type, and does not admit a live pickup implementation. A matching live
candidate still fails explicitly, as checked by the retained 334-case native
empty-search proof. Source-defined items are not an outstanding MOTU model
requirement; full combat targeting and live world traversal remain open.
