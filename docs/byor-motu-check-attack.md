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

The offline checkhit reference now matches unmodified pinned checkhit and diff
C across 166,661 cases, with zero result or last-hit position/type mismatches.
It covers every pair of the 31 source attack records and 48 source bounding
boxes, both directions, normal/counter collision, seven fractional position
pairs, the pinned default grabdistance 36 and a fractional grabdistance probe.
Five pointer/vulnerability/self exclusions also preserve the no-hit result.
Source endpoints, depth adjustment, integer-anchor truncation, inclusive edges
and last-hit x/y/z publication follow source authority. The numeric domain is
explicitly finite bounded binary32 positions and signed source endpoints; this
is an offline reference, not native Q16 collision certification or do_attack.
The receipt is byor-motu-checkhit-source-geometry-authority.json. Function,
collision source data, input and complete output hashes are retained without
giant per-case logs. The initial authority check used the wrong textual form
of the default; the checked pinned global default and model assignment now
match the actual source. No failed authority run is counted as PASS.

A separate existing-Q16 compatibility measurement retains a FAIL for equivalence.
Against the same 166,661 source-C cases, projected collision differs in 8,682
results, including 512 hit decisions. Every difference in this matrix comes from
coordinate projection; the cases whose input coordinates retain binary32
identity show no fixed-arithmetic difference. With the actual default grabdistance
36 alone, 4,341 results and 256 hit decisions differ. The retained tiny-altitude
probe is below Q16 resolution and can affect source integer-anchor truncation.
This is an explicit coordinate adaptation boundary, not a native geometry pass
or universal source-equivalence claim. The source-C reference itself still passes
all cases. No palette or pixel color changes occur in this arithmetic tooling.
Receipt: byor-motu-checkhit-q16-compatibility.json. Existing coordinate adaptation
must remain classified in the foreign profile; native hit resolution remains open.

The isolated zero-depth native collision proof passes 3,127 cases. It reads
actual current animation cursors through the paired B4FC reader; all 48 source
bounding boxes and 31 attack identities are covered, with normal/counter checks,
both directions and positive/negative fractional Q16 positions. Missing boxes,
self targets, generation/token/coordinate/table guards and bounded signed
overflows preserve the contact record. Successful contacts publish x/y/z/type/
confirm exactly against the explicit Q16 reference; actor arenas, hit identities,
world pending phase and CPU/decimal context remain intact. Source models share
the pinned immutable default grabdistance 36; all source depth offsets are zero.
Dynamic grabdistance writers and nonzero-depth frames are outside this capability.

The first native failure was a ROM-address emission defect: Poppy retained only
the offset in local label arithmetic, so long LUT operands read bank zero. The
emitter now qualifies each table operand with its caller-selected code bank.
A subsequent short-window run completed 1,484 matching rows but exhausted the
harness field limit; it remains FAIL. The complete fresh bounded run passes.
Receipt: byor-motu-checkhit-zero-depth-native.json; ROM SHA-256
27835b44d634c3f60dbc15560841f18660713b96e82b3083597b91da2b50423c.
Bank zero remains byte-identical. This is an isolated native collision component,
not full do_attack, damage resolution, a production memory lease or MOTU combat.
The binary32/Q16 equivalence FAIL above remains unchanged. NO color reduction.

Pinned do_attack identity assignment passes 81 unmodified source-C boundary
cases. The native identity component passes 246 cases across slots 0, 1 and 127,
including initialize then assign, double assignment, high-bit identities and
unsigned wrap. Existing nonzero entity IDs remain unchanged; zero IDs increment
the global sequence, skipping zero. Initial sequence 1 makes the first new ID 2.
The native path validates canvas generation, issued world phase/slot/time/relative
geometry, live canonical token and independent hit-row generation. Sibling rows,
hit-by IDs, actor state and CPU context remain unchanged. No world Ack is faked.

The sequence plus initialization marker consumes six of the existing eight spare
foreign controller bytes. Capacity stays 6,400, with 6,398 used and two remaining.
All preceding region addresses remain identical at capacities 1..128. Repeated
initialization rejects, and zero/uninitialized sequences reject assignment.
Actual production foreign initialization and full do_attack remain unbound;
fixtures install the memory/world leases. No production assembly changes.
Receipts: byor-motu-attack-identity-authority.json and
byor-motu-attack-identity-native.json. Bank zero remains unchanged.

The unchanged outer do_attack target predicate passes 25,136 source-C cases.
Coverage varies pairs of full-width fields and a deterministic 20,000-case
combination set. Rejections retain source order: exists/dead, exact invincible
value 1 with item exception, attackone/lasthit, type mask, strict unsigned
pain_time < time, takedamage, hit identity, over-the-ground and juggle rules.
Normal collision executes first; counter collision runs only after its miss
and a nonzero counterattack value. Instrumented collision-call counts match.
OTG and ATK_ITEM enums are read from the same pinned engine header and checked
at C execution. This is an offline predicate proof, with callbacks and damage
excluded; it does not certify the native target loop. Receipt:
byor-motu-attack-target-filter-authority.json. The initial C fixture missed a
newline after the source trailing line comment and did not build; the corrected
fixture passes. No failed build is counted as PASS.

Pain timing and current juggle state have a separate eight-byte persistent row
per physical entity. Controls occupy 42BF80..42BFBF; rows occupy
42BFC0..42C3BF. Existing hit identities, hit controls and pending-jump addresses
remain fixed. This adds 1,088 bytes and leaves 49,024 CHR staging bytes. At every
pool capacity 1..128, both conversion jobs retain all 896 eight-bit and 512
two-bit tiles through chunking. The compiled module has 616 live VM slots and
only 192 spare bytes after player state; it cannot hold these 1,024 row bytes.

The generic identity storage now accepts a positive staging capacity up to its
fixed identity boundary; it rejects zero or an overlapping capacity. Native
proof passes 1,058 cases across the prior and new staging capacities. The contact
component requires the exact smaller boundary from both paired descriptors.
All CHR and pending-jump producers still must adopt that boundary before a
production lease can be granted. No existing production memory owner is enabled.

Native contact storage passes 556 cases: birth/read/write/model-copy at every
physical slot, initialization and 43 stale-input guards. Birth clears pain and
installs a supplied source juggle current; model replacement retains pain while
replacing current juggle; read/write retain all 32 bits. Hit identities, siblings
and CPU/decimal context remain intact. Inputs are fixture-installed; actual
constructor/model-metric providers and damage callers remain unbound. The first
fixture accidentally fell through from model-copy to initialization and compared
paired diagnostic scratch as persistent data. That run remains FAIL. Corrected
full proof passes, with paired control diagnostics excluded and persistent
identity/slot/ready bytes still checked. Bank zero stays byte-identical.

Pinned model defaults and source directives derive zero initial juggle current
and maximum for all 16 MOTU models. Source modeldata copying replaces both
metric values; entity pain_time is retained. This remains a derived input table,
not a native installation claim. Receipts: byor-motu-hit-contact-capacity-native,
byor-motu-hit-contact-native and byor-motu-juggle-metric. NO color reduction.

The generic native target predicate passes 182 live-state cases. It validates
canvas generation, actual issued world geometry/time/slot, paired collision-bank
and extent, core/lifecycle counts, and current target model provenance. Type
masks retain all 32 bits; exact invincibility, strict pain deadline, actual
takedamage identity, hit-by identity, falling/juggle and OTG tests match pinned
source. The real zero-depth native collision routine runs only after admission
checks; observed normal/counter call counts match source short-circuit behavior.
Contacts match the Q16 reference. Actor arenas, persistent hit/contact rows and
issued world phase remain unchanged; attacker control slot is restored after
paired target storage queries. Bank zero and CPU/decimal context are preserved.

All 80 authored animation attackone values derive as -1 from the pinned loader
and source directives. Positive grab defaults are derived from translate_ani_id;
none occur in this source set. A nonpositive followup inheritance retains false
attackone>0, so this capability does not need mutable lasthit filtering state.
Positive or dynamic attackone sources require a different explicit capability.
No actor-name branch selects this behavior. common_lie receives semantic ID 21,
appended after the existing 20 stable IDs; its executable AI body remains unbound.

The initial basic run passed. An expanded run failed because a bad table extent
reached collision before rejection. The native predicate now checks the exact
paired bank/extent before processing; the full fresh matrix passes. Registry and
callback compiler tests pass. Receipt: byor-motu-attack-target-native.json. This
is a synchronous target predicate, not the ordered all-target do_attack owner,
hit callback execution, damage, world Ack or sustained MOTU combat.
