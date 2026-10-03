# S6 execution core: preserved partial work

S6 is **IN PROGRESS**, not a completed actor compiler milestone. No S6 commit
has been made. Production remains `352a10c5d2a0286449375c04cb16370b057b8fd2`.
All new native files are opt-in libraries/fixtures, excluded from `src/main.pasm`.
No source actors, campaigns or production assets were enabled or replaced.

## Source authority and policy

One ModelIR is parsed before lowering. SOURCE_EXACT does not fall back to
ACCEPTED_COMPAT. The source scheduler reference is pinned
[BOR.C](https://github.com/Plombo/beatsofrage/blob/eba02fe6c9e97e388126c51560a92024f406d8c0/BOR.C),
SHA256 `68c54a190c5713b1a42b75898ae9ff5246896de0ded3f8c1247c507681735f41`.
Local pinned references live in `out/bor_compile_s6/`, including RAND32.ASM,
RAND32.H, SPRITE.C and SPRITEQ.C. Numeric provenance and counterexamples are
in [bor_actor_s6_numeric.md](bor_actor_s6_numeric.md).

The original source [readme](https://github.com/Plombo/beatsofrage/blob/eba02fe6c9e97e388126c51560a92024f406d8c0/readme.txt)
identifies a Watcom DOS/4GW or PmodeW build. The pinned tree contains no makefile,
project settings or executable; its readme expressly omits build instructions.
An exact historical floating evaluation/rounding contract is not established.

## Mechanically measured blocker baseline

`tools/bor_compile/actor_blocker_matrix.py` derives this from strict S5 model
reports before native edits. It retains each diagnostic and input hash in
`out/bor_compile_s6/before/blockers.json`. Counts are distinct models per
capability, overlap, and must not be summed. Zero is not certification.

| Capability | BOR | TMNT | He-Man |
|---|---:|---:|---:|
| FRAME_RASTER | 44 | 67 | 16 |
| ANIMATION_TIMING | 21 | 14 | 4 |
| ROLE_TRANSITION | 22 | 10 | 5 |
| ATTACK_ACTIVATION | 24 | 13 | 0 |
| DAMAGE_FORCE | 24 | 13 | 0 |
| COLLISION | 39 | 37 | 4 |
| PAIN | 22 | 10 | 4 |
| FALL | 29 | 50 | 4 |
| RISE | 20 | 10 | 4 |
| DEATH | 0 | 0 | 0 |
| DROP | 24 | 13 | 0 |
| AI | 44 | 67 | 16 |
| RNG | 1 | 0 | 0 |
| CADENCE | 1 | 0 | 0 |
| SPECIAL_EFFECT | 6 | 0 | 0 |
| MEDIA | 44 | 67 | 16 |
| DIALECT | 4 | 67 | 16 |
| STATS | 44 | 67 | 16 |
| PALETTE | 21 | 5 | 0 |
| FRAME_MOVEMENT | 7 | 0 | 1 |
| RESOURCE | 0 | 0 | 0 |
| UNCLASSIFIED | 26 | 13 | 4 |

## Implemented native contract and evidence scope

`actor_source_scheduler.pasm` consumes the existing source frame ABI, extended
with authored integer movement and raster identity in reserved words28/30.
It owns signed frame advancement, authored delays, absolute32-bit deadlines,
loops, nonloop completion and autokill. `set_anim` with the same role is a no-op;
`reset_anim` restarts but preserves source lastanimpos. A null think callback
does not advance nextthink. Think callbacks run on equality and can replace
the default nextthink=time+2. Frame events and behavior drivers are required
link hooks, not hidden compatibility fallbacks.

`source_actor_link.py` deterministically emits role/frame records from lowered
source descriptors without editing IR. Unknown role semantics stay blocked.
Successful descriptor linking alone does not certify a model.

`actor_source_world.pasm` performs separate source-order lost, gravity, think,
animation, collision and displayed-health passes. Lost/gravity are level-only.
Collision parity comes from the sparse source slot ordinal, not compact live
actor position. Every later pass rechecks existence. It validates bound policy
before any callback and propagates callback failures. Lost/pit/hole numerics,
whole attack-target scans/effects and health-display consumers remain required
hooks; the pass-order fixture logs them and does NOT pretend to implement them.

The current bounded actor context is256 bytes in bank0 mirror WRAM; a world
context is another256 bytes. `link_world_contexts` rejects overlap, duplicates,
stack-page use, misalignment, nonexact policy and a pointer-table bank crossing.
The source slot table may retain150 sparse slots, but this is NOT150 live actors:
$0100..$1E00 has30 pages before reserving world/other storage. At most29 actor
pages exist in this restricted ABI before further reservations. A future larger
actor arena needs an explicit addressing/layout change, not truncation.

`actor_source_hit.pasm` supplies descriptor activation, inclusive source boxes,
shared32-bit attack IDs, pain/hit-by filtering and a grounded enemy damage
callback. The native control's source force5 produces HP20->15. Unsupported
drop/blast/air/death/link paths fail; the effects hook is only a fixture event
sink. Upper-counter/world target scan, player damage and full effects remain
unbound. No claim of a complete source damage callback.

`actor_source_damage.pasm` also consumes explicit inair to wait/release initial
drop, grounded pain/rise completion, lie/stall/rise, and dead blink followed by
delayed removal. It never infers THROWN from altitude. Numeric velocities have
their own caller-owned pointer and are zeroed explicitly. Gravity, bounce and
full fall/landing callbacks are not implemented by this discrete slice.

`actor_source_rng.pasm` reproduces the pinned32-bit integer recurrence and
unsigned modulo1000. It does not establish the complete world's RNG call order.

## Raster proof and target limits

The isolated raster compiler preserves source indexed pixels, canvas/offsets,
frame-local movement and facing. Kula attack1 uses6 source frames and mode6
SMALL16x32 chunks. Source pixel geometry is verified in both directions.
Palette conversion is explicitly `SNES_RGB555_TRUNCATE` and labelled ADAPTED;
it is not RGB8 source-color certification. Strict RGB8 mode fails when necessary.

Kula's87 unique chunks require22272 bytes, exceeding a16KiB preload window.
The fixture streams the selected frame, at most5120 VRAM bytes in four
coalesced DMA runs. With a full512-byte low-OAM upload it missed vblank; the
rejected attempt is retained. WRAM preparation occurs before vblank and the
successful path uploads the low-OAM prior/current high-water region plus all32
high-table bytes. Retired slots receive the trusted hidden state. This proves
one actor's bounded DMA admission, NOT a multi-actor budget.

The timed host consumes measured NTSC field intervals into rational200Hz ticks,
executes the due source ticks before the next render commit, and checks PPU
field parity plus end-of-DMA blank status. Logical ticks are batched, not CPU
callbacks physically delivered every5ms. Original source timer equivalence,
overload/pause/slow-motion integration and multi-actor admission remain open.

## Latest retained proof set

| Proof | Evidence | Scope |
|---|---|---|
| Native scheduler/hit/lifecycle/RNG | `out/actor_s6_scheduler_lwmrk6q6/proof.json` |117 CPU cases PASS |
| Native shared pass order | `out/actor_s6_world_r9jgyuk5/proof.json` |7 cases PASS; hooks logged, not live AI/physics |
| Source frame geometry | `out/actor_s6_raster_z9b6v5uw/proof.json` |12 frame/facing cases PASS |
| Timed raster | `out/actor_s6_raster_rxgyrn8g/proof.json` |30 fields PASS; no missed field/DMA deadline |
| Retained S5 compat/entity controls | `out/actor_s5_entity_y84k6wc6/proof.json` |PASS; actual entity HP control, not organic AI |

The timed Kula control uses source delays `[4,4,4,4,2,2]`, multiplied by2 source
ticks, and attacks only on frames2/3 with force5. Native scheduled hit at tick116
sets target HP15/pain deadline156 and credits the fixture hit event once. The
same IR was not rewritten to the accepted4-HP approximation.

Focused Python suite:94 PASS. Production width audit:2343 labels,0 new violations,
187 pre-existing baselined entries. New core width and no-name-selection guards
pass. Native scheduler/world label-drift audits:107/93 labels,0 drift.
These are partial-work validation results, not S6 closure.

## Reference-only work and genuine unresolved numeric question

`source_actor_execution.py` models ordinary enemy spawn, target/range decisions,
walk/preparation/attack/recovery and damage events. Its speed1 ordinary-enemy
control passes with exact bounded dyadic positions. That is a Python reference,
not a native ordinary-enemy AI certificate. Fraction motion is explicitly only
a reference; source events/world features fail rather than disappearing.

Rational decimal drift is not generally observation-equivalent to possible
binary32 storage. A retained conditional example reaches pixel29 versus28 at
update10; gravity's `>-6` branch differs at update70. These are possible-rounding
witnesses, NOT a claim about an unobserved historical executable. Fixed-point
drift or gravity cannot be called SOURCE_EXACT without establishing the actual
numeric/evaluation contract or an observation-equivalence proof. The integer
RNG and dyadic controls do not resolve non-dyadic motion.

Needed reference: pinned historical executable/build settings or an explicitly
approved numerical semantic target. Do not select historical floating behavior
by guess, do not call it unobservable, and do not silently use accepted adapters.

## Certification remains fail-closed

Whole-model SOURCE_EXACT counts remain BOR0/44, TMNT0/67, He-Man0/16.
BOR ACCEPTED_COMPAT remains36 adapter-equivalent/8 unbound,1201 inventory records.
`out/bor_compile_s6/after/blockers.json` is unchanged because bounded native
capabilities have not yet been bound/certified as complete actors.

Important report provenance: the accepted policy tool pins its delegate proof
to S4's committed environment JSON. Rerunning with S5's ROM fails that old
artifact assertion. The successful BOR adapter inventory explicitly uses the
retained S4 ROM (`out/bor_compile_s5/accepted/bor.sfc`) and S4 commit, as S5 did.
This is not a production corruption or permission to weaken its hash check.

`out/bor_compile_s6/entries.json` updates MODEL results over the prior entry
report. Its environment/media evidence is retained historical evidence, NOT
fresh environment recertification; some old diagnostic text predates S4. Do
not present its carried-forward scene/environment rows as new S6 proofs.

Still unfinished S6 plumbing: native ordinary AI, complete world/target/effect
binding, production-sized actor layout/admission, and compiler integration of
fully bound execution results. These are NOT relabelled genuine engine blockers.
Numerical evaluation, source player/controller semantics, grab/throw/events,
unimplemented special behaviors and missing media also need explicit closure.

Time remains blocked by the missing source-equivalent timer/effect lifecycle.
Ramon's independent S5 media/catalog proof is not live source AI certification.
Crab's drift proof is not exact fractional/RNG-call-order/cadence certification.
Lobster's five maps and fall-frame descriptor are not a complete fall/damage/AI
certificate. SEWER and environment/dialect work remain outside this batch.

## Production preservation

`build` and `distribution` hashes remain:

- ROM: `4f0314db7a03c196a7de0c772d77df924cfc956d111457c63a411f3b6bdf30be`
- MSU: `b1c4e499d611445e83a67f80f5be88dc2c5c0e2d91ebc14901e7891b8bcd89fc`

No production rebuild is needed for unincluded fixture libraries. No full
campaign was replayed. Unrelated tracked G13 proof edits and foreign/untracked
attempts are preserved. No staging, cleanup, worktree or repo copy was used.

## Bounded historical-family continuation

`numeric_capabilities.py` and the durable
`fixtures/watcom_numeric_vectors.json` distinguish retained-input
`HISTORICAL_FAMILY_PROVEN`, conditional whole-domain
`OBSERVATIONALLY_EQUIVALENT`, and `NUMERIC_BLOCKED`. The fixture embeds probe
sources, outputs and executable provenance. Executed candidates are NT
executables; DOS execution is not proven. Literal constant casts do not prove
general runtime float-to-int conversion. No universal IEEE policy was selected.

The analytic checker admits individual addition/subtraction/comparison and
integer-identity conversion over explicit bounded dyadic domains only when
all declared assumptions hold. This is not authorization for arbitrary
compositions, gravity, decimal walking, or Crab drift. Historical walk pixel28
and gravity branch witnesses remain hard regression evidence.

New unincluded native components:

- `actor_source_target.pasm`: pinned `enemy_find_target` ordering, strict
  straddling/facing and Manhattan tie behavior. Admission requires genuinely
  integral source coordinates in -4096..4095, not truncated float state.
  Runtime bounds reject out-of-domain coordinates when comparison is needed.
  World44/46 are explicit player pointers, never inferred from actor order.
- `actor_source_lifecycle.pasm`: existence/type-mask counting (zero health
  does not release ownership), unlinked removal with player/opponent reference
  cleanup, and signed one-unit displayed-health convergence. Linked removal
  remains explicitly unsupported; this does not fake unlink.
- World linker rejects reserved storage overlapping its world context and
  limits immutable slot tables to explicit LoROM ROM windows. Production
  133-byte actor records cannot be used as aligned256-byte source contexts.

Fresh focused evidence:

- Python104 PASS, including8 numeric capability tests and2 new layout tests.
- `out/actor_s6_scheduler_r2dit4ib/proof.json`: original117 native cases PASS.
- `out/actor_s6_world_tn0j892u/proof.json`: original7 pass-order cases,77 native
  target cases,9 native lifecycle/accounting cases PASS.

These are component proofs, NOT the required organic production-world fixture.
Common AI driver, source spawn/scroller admission, actual renderer-slot bridge,
hit effects and full lifecycle dispatch remain unfinished integration work.
They must not be renamed numeric blockers or used to claim S6 closure.
No model/source-certification count has been promoted by these component tests.

Production-world audit: six actors use133-byte records in the OOP arena
at0A00..15FF; S6 must preserve ownership and use independent contexts.
Calling source passes separately inside each compat actor tick would violate
shared-pass order. Production positive-HP occupancy predicates differ from
source existence predicates and need explicit opt-in world consumers. Source
boss-death mass damage uses force1000000, beyond the current signed16 damage
slice: a genuine width/callback capability gap, not just a boss counter.
