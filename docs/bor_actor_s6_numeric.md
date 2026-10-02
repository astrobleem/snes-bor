# S6 numeric observational audit — bounded sidecar only

## Verdict

The discrete RNG recurrence, sample selection, and source tick decisions can be
specified exactly without emulating host C floating point. Nominal rational
motion can be certified for a restricted exact-binary translation domain, but
**not for all NONE/WALK speeds and samples**, and not for a whole actor.

The existing `.9 + 3*k/256` driver remains an explicitly visible approximation.
Changing it to exact nominal `.9 + 3*r/1000` fixes the sample-domain mismatch but
does **not** establish equivalence to repeated source floating-point updates.
No new compatibility permission or certificate is granted here.

Only `source_actor_numeric.py`, `test_source_actor_numeric.py`, and this document
belong to this task. No runtime, production, scheduler, ModelIR, or GUI changes.

## Source boundary and provenance

`out/bor_compile_s6/BOR.C`, verified SHA256:
`68c54a190c5713b1a42b75898ae9ff5246896de0ded3f8c1247c507681735f41`.

Relevant source anchors in that exact file:

- Lines45–46: `GAME_SPEED=200`, `THINK_SPEED=2`.
- Lines697–708: in-air threshold and `randf`.
- Lines1318–1323: authored integer speed divided by10, clamped to .5..30.
- Lines2718–2775: gravity pass, then ascending entity-index think pass.
- Lines2847–2860: sprite queue receives position expressions.
- Lines3675–3682: strict outside-bounds test before drift addition.
- Lines4663–4669: NONE with WALK, one speed sample, sign from authored X<160.
- Lines5035–5047: timer interval, pause, 100-tick cap, per-tick catch-up.

The same-commit `GAMELIB3/RAND32.ASM` and `.H` supplied in
`out/bor_compile_s6` have now both been read completely and separately pinned:

- RAND32.ASM SHA256:
  `a89ddbf982072216d971fdc6a739b51fb1655bd0131b8aeeaa4abfb999ce6a0a`.
- RAND32.H SHA256:
  `41ab7452bc9200e4ed54482307586f384e4fa54392a09224fda7cc9bd61e6950`.

The header declares an unsigned-int return in EAX, clobbers EAX/EDX, and passes
the `srand32(int)` argument in EAX. The assembly uses386 unsigned32 instructions
and a `dd` seed initialized to1234567890. These files mechanically validate the
previously supplied recurrence; missing RNG implementation/header provenance
is **resolved**, not a remaining blocker. Original compiler/FPU settings are
still not established. Golden vectors are reference vectors checked against an
interpreter of the pinned x86 steps, not an original-executable gameplay trace.

## Classification

| Observation/domain | Classification | Limit |
|---|---|---|
| u32 RNG state/returned bits, unsigned remainder, zero-max no-call | EXACT_DISCRETE_SEMANTIC | Pinned x86/header validated; target implementation/call order not proved |
| Source nextthink equality, +2 tick default, pause and cap | EXACT_DISCRETE_SEMANTIC | Given source timer intervals and callback schedule |
| Integer/unit-speed bounded translation with exact inputs | EXACT_DISCRETE_SEMANTIC | Numeric subdomain only; not enemy AI, collision, or complete actor |
| `.9+3*k/256` replacing nominal `.9+3*r/1000` | NUMERIC_APPROXIMATION_VISIBLE | Concrete positive-pixel witness retained |
| Nominal rational versus conditional repeated binary32 stores | NUMERIC_APPROXIMATION_VISIBLE | Conditional witness, not a historical executable verdict |
| Different fractions inside the same pixel/boundary cell | IMPLEMENTATION_DETAIL_NOT_OBSERVABLE | Only for the proven finite observation window; may become visible later |
| Carry/multiply implementation with identical state/returned bits | IMPLEMENTATION_DETAIL_NOT_OBSERVABLE | Includes discarding product bits48..63 after lower carries are resolved |

`BLOCKED`/unproven is not a fourth semantic equivalence class and must not be
silently relabeled an implementation detail. In particular, missing runtime
call order and unknown C expression evaluation remain unproven.

## Discrete RNG contract for a 65816 implementation

Initial seed is unsigned32 `1234567890` (`0x499602D2`). On each actual call:

1. Compute unsigned wide product `seed * 1103515245 + 12345`.
2. Save bits0..31 as the next seed.
3. Return bits16..47 as an unsigned32 word. This is **not** the next seed and
   not merely its high16 bits.
4. For nonzero `randf(max)`, consume exactly one call and take unsigned `%1000`.
   For `max==0`, return zero without advancing the seed.

For 16-bit seed limbs `lo,hi`, multiplier `0x41C6:0x4E6D`:

```
p0 = lo*0x4E6D + 12345
p1 = hi*0x4E6D + lo*0x41C6 + (p0 >> 16)
p2 = hi*0x41C6 + (p1 >> 16)
next_seed = low16(p0) | low16(p1)<<16
returned  = low16(p1) | low16(p2)<<16
```

Intermediates need their real carries: `p1` is not a 16-bit temporary. The tests
exhaust every low16 value with high16=0 and65535, and compare the recipe against
the wide formula. The bit-serial `%1000` reference shifts all32 returned bits,
keeps remainder<1000, and needs at most one subtraction per bit. No signed
division, byte RNG, rejection/resampling, or divide-by256 substitution.

### Mechanical x86 validation

The test extracts the actual instructions from `rand32_ proc near` through
`endp`, verifies their shape, then runs them in a separate unsigned32 register
and carry-flag interpreter. It compares8192 sequential seed transitions and
explicit boundary seeds against the wide recurrence. Boundary seeds are
constructed using the multiplier's inverse modulo2^32, forcing the low-product
addition just below and at carry-out; this does not rely on encountering a rare
carry in a short random trace.

The seemingly unusual `shl edx,16; add eax,12345; adc edx,0FFFFh` is intentional:
after unsigned `mul`, write its high word as H and low word as L. The shift
leaves `(H & 65535)<<16` in EDX, with low16 zero. `add eax,12345` produces the
new seed and carry c. Adding `65535+c` to shifted EDX leaves its upper16
unchanged when c=0, or increments them when c=1. Masking with`FFFF0000` then
ORing `new_seed>>16` returns precisely bits16..47 of the complete product-plus-
increment. Shift-generated flags do not leak into this result: the intervening
ADD supplies the carry consumed by ADC. The three equivalent references
(pinned x86 interpreter, wide formula, 16-bit limb recipe) are not target CPU
execution tests.

If returned words were uniformly enumerated, residues0..295 would occur4294968
times and296..999 would occur4294967 times. Preserve this modulo mapping, not
an invented uniform sampler. This count is **not** a claim that the actual
correlated LCG returned-word sequence is uniform or independent.

First eight sequential calls from the specified seed:

| Call | Next seed | Returned unsigned word | `%1000` |
|---|---:|---:|---:|
| 1 | 2317836195 | 390629927 | 927 |
| 2 | 754553504 | 68103417 | 417 |
| 3 | 951082585 | 889796784 | 784 |
| 4 | 1907194398 | 2981851565 | 565 |
| 5 | 1397117695 | 453071686 | 686 |
| 6 | 3530897612 | 1559876213 | 213 |
| 7 | 218072853 | 3398372607 | 607 |
| 8 | 858987050 | 4075434803 | 803 |

All source users share the stream. Conditional enemy decisions, toss/drop
randomness, and any other intervening call affect which residue a spawn sees.
Do not invent per-actor seeds or an extra speed sample every think. A target
binding needs a traced call ordinal, caller/event and branch predicate, seed
before/after, full returned word, and chosen mask/remainder. The sidecar does
not mutate or instrument a live global RNG.

### Seed lifetime within the pinned source scope

RAND32.ASM has two seed writers: `rand32_` stores the next state and
`srand32_` simply copies EAX to seed. Static data initializes seed at program
load. A comment/string-stripped inventory of the entire pinned BOR.C finds
**no `srand32`, `srand`, `randomize`, or direct `seed` identifier**. Its nine
direct `rand32()` call sites are lines705,3814,4054,4066,4094,4108,4230,4272,4279.
Line705 is the `randf` wrapper, which is also reached by conditional spawn,
toss, and other callers.

Consequently BOR.C contains no new-game/title/stage reset of this RNG: its
stream continues across those transitions in the same process. A fresh program
load starts at the static seed. That resolves the BOR.C reseed-path question.
It does not prove absence of external `srand32` calls elsewhere in all linked
library code, nor establish dynamic consumption/order for a particular run.
Do not reset per actor/stage in a target simply because a fixture restarts there.

## Rational analysis before any rounding oracle

For the test speed9/10 and residue `r` in0..999, nominal positive velocity is
`(900+3*r)/1000`. An integer grid of1/1000 source pixel represents every such
velocity and repeated rational addition exactly, within integer capacity.
The existing1/2560 grid represents only40 of1000 velocities: exactly `r%25==0`.
For example, `r=1` requires velocity2311.68 in1/2560 units. This is a
representation fact, not proof that a1/1000 implementation matches C floats.

Observable tests explicitly inspect integer pixels and strict outside-bounds
branches. Negative source-to-pixel conversion is not silently assumed:
`pixel()` supports truncation and floor. All retained pixel discrepancies use
positive positions, so either policy gives the same discrepancy. BOR.C alone
does not pin the sprite queue function prototype or the SNES coordinate/raster
conversion; target4/5 projection and negative-coordinate raster alignment need
their own proof. No source pixels are silently treated as target pixels here.

The enclosure helper uses rational intervals, an explicit caller-supplied
velocity error radius, and a bounded normal-store relative error allowance.
With start20, nominal speed.9, radius1e-6, its first nine updates have the same
integer pixel and bounds decisions across the enclosure; update10 straddles
an integer boundary. That is **ambiguity**, not a counterexample or permission
to select whichever old/new position passes. The radius/store assumptions
must be justified before applying this conditional finite-window result.

## Retained counterexamples and exact controls

1. **Byte-domain approximation:** nominal residue1 gives speed.903; nearest
   byte-domain sample0 gives speed.9. From X20, update333 yields pixel320
   versus319, both still within the drift lifetime. This compares numeric
   sample domains, not a claim that two different PRNGs produce correlated
   sample ordinals.
2. **Conditional repeated-store pressure:** start20, speed.9, residue0,
   positive direction. Nominal update10 is exactly29; the explicit nearest,
   ties-even binary32 operation/store oracle gives `7602175/262144`, pixel28.
   Residue0 is reachable: call118 has seed-before2514399119,
   seed-after3236463132, returned word2730017000. This does not assert that
   any particular gameplay spawn occurs on call118.
3. **Gravity branch pressure:** nominal toss velocity1, repeated subtraction
   of.1. At update70, rational velocity is-6; conditional binary32 store
   velocity is `-12582905/2097152`, still greater than-6. The source `>-6`
   branch therefore differs. Starting height240 keeps this pressure window
   airborne (nominal height68.5 after70 steps); this is not a complete landing,
   hole, or gravity lifecycle certificate.

The optional rounding oracle is integer/rational code with an explicitly
limited normal binary32 domain. It does **not** use host floats. It is invoked
only to investigate/retain witnesses after the rational analysis. It does not
model historical x87 excess precision, double unsuffixed literals, spills,
compiler flags, or original executable behavior. A possible permitted rounding
path is enough to reject an unconditional rational equivalence claim; it is not
enough to claim the historical game definitely took that path.

An exact positive control does not need that oracle: integer initial position,
velocity±1 (also suitable bounded dyadic velocities such as1/2), and exactly
representable thresholds produce exact binary additions whenever every
intermediate is representable. Tests cover10000 steps from20 and reject a
one-unit step beyond2^24 where binary32 exactness fails. This is the useful
ordinary speed1 control proposed for K' or Heavy, **not** a name-based rule,
biker rule, imported-model certificate, or proof of all their movement modes.
Already-exact operands are essential: a nominal dyadic sum of rounded decimal
operands is not automatically an exactly produced input.

## Cadence and ordering contract

Source time advances in200Hz logical ticks from `timer_getinterval`. Ordinary
think checks `nextthink == time`, installs default `time+2`, then calls the
handler. Handlers can replace that deadline. Gravity checks `toss_time<=time`
and reschedules by2. These are distinct predicates; never replace equality by
`>=` without proof. Initial nextthink phase is per actor, not assumed global
frame parity. Entity index/pass order and spawn/callback timing remain part
of the caller's scheduler/lifecycle proof.

`update()` consumes each tick in `[time,newtime)`; it does not jump over missed
think deadlines. Pause consumes none. Slow motion changes the timer rate
argument to100; dividing a previously sampled interval by2 is not automatically
equivalent. Per-call elapsed time is capped at100 ticks. Batching two75-tick
updates is not equivalent to one150-tick update because of that cap. Unsigned
time wrap and timer implementation are outside these bounded tests.

An integer accumulator fed measured NTSC master intervals can exactly partition
those supplied intervals into200Hz counts. The test alternates357368/357364 at
rate21477270 and proves sum/remainder arithmetic. It does **not** identify those
counts with BOR's timer implementation or certify target elapsed time during
skipped OOP commits, pause/resume, slow motion, overload or differing render
sampling phases. An average-frame adapter or dropping source ticks can change
visible positions and branch times; neither is an unobservable detail by fiat.

## Verification and remaining certificate boundary

Run only this targeted suite:

```
python -m unittest discover -s tools/bor_compile -p test_source_actor_numeric.py
```

21 tests PASS: all three source hashes, pinned x86 instruction/carry validation,
BOR.C reseed inventory, formula vectors/carries, unsigned samples/no-call,
representability, observational windows/witnesses, exact control, tick order,
cap/pause, and accumulator arithmetic. No original-C executable, 65816
implementation, GUI, runtime behavior, or complete actor acceptance is tested.

Certifiable now: the specified discrete reference and explicitly bounded
exact-input translation subdomain. Full sampled-decimal rational equivalence
remains **BLOCKED**. Needed next evidence: original evaluation/rounding contract
or observation traces, complete shared RNG call order (including any external
library callers), source timer delivery, and target observation mapping.
The missing RNG-header/implementation blocker and BOR.C reseed audit are
resolved. No existing ModelIR or compatibility classification is changed.
