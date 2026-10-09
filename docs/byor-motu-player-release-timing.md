Attack-release timing first requires the source floating-point evaluation rule.
BOR 4086 initializes animation chargetime=2. For an integral nonnegative product
GAME_SPEED*chargetime <=65535, the pinned Windows -m32 GCC/x87 evaluation retains
exact integer operands and sum. The native WIN32_X87_EXTENDED primitive therefore
uses a widened 33-bit deadline and never wraps at UINT32_MAX.

The unchanged source comparison expression passes 7420 C-harness comparisons.
The pinned Makefile selects Windows x86, -m32 and -O2 without a floating-point
override. A reproducible current GCC -m32 -O2 probe of the unchanged expression
confirms FLT_EVAL_METHOD=2, four-byte pointers and x87 arithmetic. This is source
build-policy evidence, not disassembly of an original distributed 4086 engine.

BINARY32 is an explicit separate evaluation policy. It differs from the pinned
Windows policy in 1588 source test cases. Its native primitive rounds uint32
operands and the sum to nearest-even using 33-bit intermediates. It is not
silently substituted into the Windows source profile.

Both policies pass 1062 bounded native cases, including CPU/decimal flag and
input retention, timer endpoints, exponent boundaries and invalid-duration
rejection. The compiler must separately prove the animation duration product
fits the selected integral capability. Fractional/negative/unbounded products
require another numeric owner; they are never truncated.

These primitives do not bind the release-attack actor/query/frame/audio body,
the full player controller or MOTU gameplay. The proof leases private fixture
storage and does not add controller arena allocation. No color reduction,
PCM copies or bank-0 code are introduced.

The unchanged full release body passes 1914 C comparisons through mandatory
punch and frame services. It preserves the repeated CHARGEATTACK query order,
clears only combostep[0], and retains callback changes after frame execution.
Six synthetic post-sound mutations make the source read an undefined chain
index; those cases are excluded from C comparison and separately reject in the
reference continuation. They are not reported as source equivalence.

The source-derived INTEGRAL_CHARGETIME_WIN32_X87_ABSENT_CHARGEATTACK profile
records final source chain roles and exact 400-tick durations for authored
attackers. Effect models lacking a final attack retain an explicit undefined
active-release requirement, rather than silently selecting attack one. Native
release now has canonical native actor/query writes and explicit sound/frame continuations. Physical source audio and the full player controller remain required.


The B68F native release continuation uses the actual immutable chain reader and
animation resolver. Its 544-case native proof covers all 128 actor slots,
unsigned timer boundaries, repeated queries, exact prefix writes, source
priority rejection, fresh post-sound model selection and 25 admission guards.
The sound result and model mutation are instrumented; this is not physical
12-channel audio certification.

A separate 64-case proof constructs the actual source player, executes release
through the real animation and frame-zero owner, and completes the native
acknowledgement. It retains released input and instrumented post-frame changes
to the timer, combo, idle flag and velocities. A backend-busy result cannot
acknowledge the punch service; the source sound owner must accept the call or
reject it under the source priority rule before release resumes. These are
serialized continuations within one source controller invocation, not a grant
to advance the world or recycle its entity slot while a service is pending.

The controller address plan appends 128 bytes, including the threshold's 64
bytes: 6104 of 6400 bytes, leaving 296. Existing addresses remain unchanged.
The production arena lease and full player controller are still unbound. No
bank-0 code or source color changes are introduced.
