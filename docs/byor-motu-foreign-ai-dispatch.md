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

Production world installation, player-think dispatcher integration, physical
sound playback and natural jump physics remain open. The emitter's optional
player lane is not admitted by this jump-only proof. M4 is not complete.
