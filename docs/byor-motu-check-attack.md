# Source attack gate and persistent hit identities

The source-derived native check_attack gate joins actual world phase 8 to the
current live collision frame. It reads the actor's current animation cursor,
not the pre-switch parent handle. Source falling/projectile and drop short
circuits precede the real freeze predicate. Inactive gates reset the actor's
unsigned attack_id. Active gates return DO_ATTACK (0x8108) and retain the pending
world phase. No hit, damage or acknowledgement is invented for an active gate.

The generic world continuation optionally binds this service by capability.
It acknowledges phase 8 only when the gate completes without an attack request,
then returns actual health phase 9 with pending=1. Other world requirements and
external frame tickets remain the caller's responsibility. No actor-name branch
selects this path. Production assembly and ordinary static presentation are
unchanged; emitted proof code remains outside bank 0.

Unmodified pinned BOR 4086 check_attack C matches 12,348 generic decision cases.
The matrix includes signed DWORD extremes, nonzero high-word values, both attack
pointer-presence tests and unsigned attack identity boundaries. Freeze and
DO_ATTACK are instrumented in this C proof. Its source function, input matrix
and output hashes are retained; it does not certify do_attack or damage.

The native gate passes 891 cases: all 836 authored source collision frames,
21 falling/projectile/drop/freeze-deadline early-exit cases and 34 stale-input
guards. It uses the actual B4FC QueryEntity reader. Every case compares actor
arenas, sibling rows and CPU context, preserves decimal mode, and checks that
world phase 8 remains pending. Active frames preserve attack and hit-by identities.
Inactive frames clear only attack_id. Source frame descriptors, model source
hashes, ROM identity, full inputs and results are in the retained receipt.

The twelve joined authored weapon cases also pass through real phase-7 issue,
timed frame/model/nested-idle completion, real phase-7 Ack and the inactive
attack gate. Their real collision query observes the new idle handle/frame zero.
Real Ack8 then advances the owner to health phase 9, pending=1. The fixture
installs completed phase 6 and the memory leases. It does not execute preceding
world phases, constructor hooks, health, hit resolution or clock commitment.
The added freeze-row comparison exposed the source-required update_mark=1;
the expected result now accounts for that actual timed-frame mutation.

Persistent attack_id and hit_by_attack_id storage occupies 128 generation-bound
16-byte rows at 42C400..42CBFF. Sixty-four serialized control bytes occupy
42C3C0..42C3FF. The existing pending-jump rows begin at 42CC00. This takes 2,112
bytes from serialized CHR staging and leaves 50,112 staging bytes. The compiler
retains every tile in both conversion jobs at every pool capacity from 1 to 128;
chunking retains source pixels and colors. All production CHR producers must
adopt the reduced boundary and retire prior conversion/DMA before enabling this
lease. The layout is not a production memory grant. No controller arena grows.

Native identity storage passes 544 cases: four operations at every physical
slot plus 32 stale-input guards. Birth clears both identities, read/write retain
all unsigned bits, and inactive-attack reset preserves hit_by_attack_id. The
independent expected generation comes from X/Y; zero/stale generations reject.
Sibling rows, sentinels and CPU/decimal context remain intact. Actual constructor
and model-copy hooks remain unbound. Source model switching must retain these
entity identities rather than clear them.

The initial broad native run timed out in the emulator frame request. A later
bootstrap failed to enter the fixture. Neither is counted as PASS. Four-case
batches completed the full matrix on a fresh run. The earlier joined comparison
failure on update_mark likewise remains a failed run, not a runtime defect.
Receipts under docs/receipts are byor-motu-check-attack-authority.json,
byor-motu-check-attack-native.json, byor-motu-source-hit-state-layout.json,
byor-motu-source-hit-state-native.json and
byor-motu-model-world-attack-gate-native.json.

MOTU profile admission, physical lossless presentation, audible audio backend,
real hit resolution, sustained authored combat and Demo completion remain open.
NO color reduction applied. No PCM copies. No TMNT work.
