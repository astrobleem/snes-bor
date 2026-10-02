# S6 bounded production-world integration

This supersedes the **world/AI integration pending** statements in the earlier
S6 progress log for the admitted grounded domain. It is not a complete-model
SOURCE_CERTIFIED claim, a production policy migration, or a new content build.

## World ownership and policy

`actor_source_bridge.pasm` binds six existing 133-byte production characters,
at $0A00, $0A85, $0B0A, $0B8F, $0C14 and $0C99, to execution contexts at
$1900..$1EFF. The contexts hold scheduler state, not another allocator/world.
World scratch is $1700..$17FF; the combined allocation is 1792 bytes. OOP memory
through $1629, old S5 scratch $1800..$18FF and stack $1F00..$1FFF do not overlap.

Position, health, existence, identity, facing, fixed altitude/base and target
publication are imported/exported through this bridge. Nonintegral lattice
conversions, live grab links, airborne state and out-of-byte health are rejected,
not truncated. Altitude remains separate from voluntary jump/throw state.

The opt-in image guards original instruction bytes before installing hooks:

- normal Stage_Load and Spawn_Play allocate the acceptance enemy;
- normal CharacterEntity_Play delegates unchanged under ACCEPTED_COMPAT;
- SOURCE_EXACT skips that compatibility actor simulation and executes one
  shared source pass after the real OOP pass, before the real render pass;
- real occupancy, wait/group/alive predicates use existence for exact actors;
- the normal HUD health consumer reads exact displayed health;
- removal clears real target references and player ownership flags.

Handles remain real slot addresses. Native source target pointers are transient
execution references translated at the bridge. Source BOR itself uses reusable
entity pointers; unlink clears references and each AI decision rescans live
entities. Binding clears the paired context. No generation-ID scheme was added.
Live retarget-after-unlink is proven; a separate live slot-reuse cycle is not.

The test-only image patches existing ROM bytes and a private MSU queue. There is
no main.pasm include or automatic production SOURCE_EXACT selection. The same
host code runs both live world gates; native target selection is not rewritten.

## Final bounded gates

| Gate | Evidence directory under out/ | Result |
|---|---|---|
| Organic ordinary opponent | actor_s6_production_world_66s1sh12 | PASS, 173 source ticks |
| Kula exact world hit | actor_s6_production_world_9txz4a4q | PASS, 43 source ticks |
| Same compatibility control | actor_s6_production_world_j588wydn | PASS, no source ticks |
| Retarget/unlink/wait | actor_s6_production_world_cm8rr3g0 | PASS, 173 source ticks |

Each directory retains link/proof JSON, immutable input/module hashes, private
ROM/MSU, WRAM, and read-only tick/hit traces. `proof.json` binds `link.json` by
SHA-256. Linking alone is explicitly not a runtime PASS.

The queue fixture retains authored record 86 from exact PAK path
`DATA\EASY\5BEASY.TXT`, physical stage 18 derived from the accepted catalog.
Its ten accepted bytes are `0000e8ffb00100400000`: source Joe, x=-30, z=220,
trigger 0, map 0. Normal queue activation owns allocation; observed slot 2
resolves roster 2. Legacy kind zero relies on that observed slot-default
identity; this does not certify arbitrary allocation of legacy generic kinds.
The private queue is an explicit one-record subset, not a full-stage proof.

Joe naturally chooses among two actual players, executes source preparation
(50 + RNG%20), attack selection, eleven-frame timing, force-18 hit resolution,
and recovery to the source runoff **decision**. Both players change 64 -> 46;
the actual HUD consumer observes 46. The gate stops before decimal runoff
movement, which remains numerically unproven. It does not set a test target.

Kula uses the same one source IR and real slots. Exact attack1 residence is
[8,8,8,8,4,4] at 200Hz, corresponding to source delays [4,4,4,4,2,2]. The
collision pass activates only frames 2-3. At tick 18 force 5 changes Joe
100 -> 95 and enters pain. The source attack rectangle is [161,138,200,154],
victim body [144,120,170,220]. Authored frame movement changes production X
100 -> 108 -> 116 -> 108 -> 100. No attack remains active after frame 3.
The matched ACCEPTED_COMPAT setup uses normal Y input, deals 4 HP (100 -> 96),
and never enters the native source scheduler. Fixture positions and initial
invulnerability clearing are explicit matched preconditions, not movement proof.

Removing P1 through the real world seam retargets Joe from $0A00 to $0A85.
Displayed health becomes zero for the removed player. A controlled HP-zero,
still-existing enemy continues to hold the real wait gate; unlink releases it.
Natural airborne death-to-removal is **not** proven by this accounting test.

Live integration found and fixed three concrete native defects: stale processor
flags after PLD/PLX, collision scratch overwriting persistent actor bridge and
display-health fields, and compatibility player-death service prematurely
ending the exact two-player pass. The compatibility service remains unchanged
unless both players explicitly belong to the exact fixture policy.

## Certification and remaining capabilities

`source_actor_world_link.py` generates driver/program records from source type,
roles, stats and effects, never model names. It admits controlled player attack1
or grounded in-range single-attack opponents. It fails closed on extra attack
selection roles, unsupported frame events, invalid media pointers, unsupported
types, health widths and foreign dialects. This is bounded program admission,
not permission to discard other source roles.

`source_actor_world_report.py` analyzes fresh project reports without changing
the source IR or weakening shipped-target certification:

| Project | Models | Whole source-certified | Bounded programs linkable |
|---|---:|---:|---:|
| BOR | 44 | 0 | 8 |
| TMNT | 67 | 0 | 0 |
| He-Man | 16 | 0 | 0 |

Eight linkable programs are not eight live proofs. No whole model is promoted.
The retained accepted-policy inventory remains 36 adapter-equivalent / 8
unbound, 1201 explicit records. That inventory is historical S4/S5 evidence,
not freshly regenerated from the S6 no-baseline actor reports (which correctly
have no compatibility pins). The fresh reports preserve the unchanged shipped
fixed-slot target's limitations separately from bounded core capability.

Normal and Hard each have 16 source entries; Bonus has 2. None becomes a fully
source-certified publishable set. Fresh environment diagnostics retain alias
HUD, water/rocking/depth requirements; source media linking remains distinct
from already-accepted Rugal/Ending playback. SEWER is not encoded here.

Per-capability status must not be flattened:

- Lobster: five-map and fall-attack descriptor proofs retained. Full actor
  blocked by additional attack selection, airborne numerical/lifecycle domain,
  source presentation/effects. No new live integrated Lobster claim.
- Crab: prior organic spawn/render/parameterized driver proof retained. Integer
  PRNG component proven; full drift call-order/numerical integration is not.
  Decimal drift remains NUMERIC_BLOCKED, not the reason this world bridge ran.
- Ramon: source health 10, source roles idle/walk/pain/fall retained. Independent
  media proof retained; attackless opponent behavior is outside the admitted
  attack1 driver. Pain-media limitations are separate from AI semantics.
- Time: parsed effect remains reset_timer; source-equivalent gameplay timer
  and pickup/effect lifecycle absent. No invented timer or name branch.

There are 25 BOR player/enemy/drift models requiring general movement/gravity
numerical certification and 4 requiring the full player controller. These are
overlapping requirements, **not** counts of models blocked *only* numerically.
One reset-timer requirement is source-derived. Foreign projects retain their
own dialect contracts; they never inherit original-BOR compatibility policy.

Explicit nonclaims of the live core: source raster publication through the
production compositor, flash/audio/combo effect entities, general fractional
movement, natural airborne death, grab/throw/player control, and extra-role AI.
The fixture still uses the accepted renderer. Isolated source raster/DMA proofs
do not establish that missing compositor binding. Hit effects currently publish
an event counter, not a complete source effect implementation. These outstanding
bindings must remain visible; this document does not call them numerically solved.

## Regression and reproduction

Focused Python: 113 PASS. Native scheduler/hit: 118 PASS (original 117 plus
scratch preservation). Native world: 7 ordering + 77 target + 20 consumer PASS.
Final native proof directories: `actor_s6_scheduler_x7486pg4` and
`actor_s6_world_ykl9dmbt`. Preserved raster geometry and 30-field DMA/timing
proofs were not relabelled as live world rendering proofs.

Run each real-world gate with:

```
python tools/verify/actor_s6_production_world.py --run --scenario enemy
python tools/verify/actor_s6_production_world.py --run --scenario kula
python tools/verify/actor_s6_production_world.py --run --scenario compat
python tools/verify/actor_s6_production_world.py --run --scenario retarget
```

These require the genuine local BOR PAK, accepted distribution/symbol files,
Poppy and Mesen tooling. Native reference fixtures additionally require pinned
BOR.C/RAND32 inputs documented in the numeric progress files. No dependency is
silently downloaded. All outputs are isolated under out/, not a repository copy.

Width audit: 278 S6 labels, zero violations; production 2343 labels, zero new
violations (187 existing baseline). No source numerical policy was changed.
The historical-family tier remains bounded to retained evidence/domain proofs.

Production build/distribution bytes remain unchanged:

- ROM SHA-256: `4f0314db7a03c196a7de0c772d77df924cfc956d111457c63a411f3b6bdf30be`
- MSU SHA-256: `b1c4e499d611445e83a67f80f5be88dc2c5c0e2d91ebc14901e7891b8bcd89fc`
