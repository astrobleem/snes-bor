# S5 actor compiler — preserved chronological progress

This is the historical work log, including superseded blockers and failed
attempts. Current results and exact limits are in `bor_actor_s5_closure.md`.

Production baseline: `946796cf9f8dfa276c9d3adbf471c9f98005a12a`.
The continuation adds experimental generic runtime primitives and inactive
production hooks. Bounded live primitive/entity checks pass; automatic exact
actor integration is still in progress. No
production asset, campaign or actor-catalog migration is authorized by these
results, and this document is not an S5 completion claim.

## Explicit lowering policy

Parsing produces one source-exact IR. `lowering_policy.py` takes that immutable
description and an explicit target policy; it never writes adaptations back
into the source. `SOURCE_EXACT` is the default, including foreign projects.
`ACCEPTED_COMPAT` requires an explicit committed baseline and source/project
identity binding. No adapter is inherited by an unshipped or foreign model.

The compatibility inventory reads the actual committed roster records, frame
manifests, map directory and runtime constants. Its equivalence proof delegates
to the immutable accepted ROM/MSU, whose hashes must match committed evidence.
That is **ADAPTER_EQUIVALENT**, not proof of source fidelity or proof of a newly
rewritten consumer. The report exposes both policies, and strict source mode
fails even when an accepted compatibility binding is available.

CLI certification is fail-closed by default (`--source-exact` exits nonzero
for blocked actors). Use `--analysis-only` explicitly to generate diagnostic
reports with a successful report-only exit; it grants no build permission.

Kula attack1 is the control: the same source fingerprint retains active frames
2/3, force 5, frame boxes and delays `[4,4,4,4,2,2]`. The explicit accepted
adapter delegates state-gated activation, fixed 4-HP damage, fixed collision
extents and the packed delay 4. Those differences are target policy records.

`actor_frame_abi.py` packs source-exact frame descriptors separately from the
legacy 50-byte roster record: sixteen words / 32 bytes per frame, including
200-Hz timing, vulnerability, signed body/attack corners, force, drop and kind.
It rejects overflow and table-bank crossing rather than truncating. It does
not claim to install an actor or implement every damage/AI lifecycle.

## Implemented shadow layer

`tools/bor_compile/actor_lowering.py` emits independent role/frame descriptors
from ModelIR. It preserves frame asset identity, dimensions, offsets, body
boxes, attack kind/box/force/drop, movement, timing, raw properties and unknown
directives. Historical source box corners and 200 Hz delay values are explicit;
foreign dialects do not receive guessed source bindings.

The original Python role-independent lookup remains a **source reference**;
the continuation tests a separate 65816 descriptor consumer. The
attacking/projectile flag remains behavior-owned. A fall
frame containing a hit box must not automatically turn an entity into an
attacker. Project-scoped allocation supports pinned accepted IDs and reserves
foreign accepted slots; it rejects mixed projects, collisions and overflow.

The report separates all eleven requested runtime certification categories.
Every missing consumer remains BLOCKED. Existing candidate labels are retained
separately: LOWERABLE_WITH_ADAPTER does not mean CERTIFIED.

`certify_actors.py` can shadow-encode named test subjects through the existing
generic raster adapter. Missing manifest delay values are supplied from ModelIR
only for the pinned historical dialect. This does not edit production generated
assets. The legacy converter accepts an optional centralized image resolver;
its default production invocation is unchanged. Encoded role counts and packed bytes are
reported separately; the fixed-slot packer can omit converted animation roles.

## Pinned source evidence

[BOR.C](https://raw.githubusercontent.com/Plombo/beatsofrage/eba02fe6c9e97e388126c51560a92024f406d8c0/BOR.C)
commit `eba02fe6c9e97e388126c51560a92024f406d8c0`:

- `load_cached_model` starts delay at zero. `addframe` converts centiseconds
  into 200 Hz ticks. Frame boxes become offset-relative corners.
- `update_ents` gates attack processing with attacking/projectile state and
  nonzero frame force. `checkhit` also uses depth, target vulnerability and
  frame-specific boxes; it does not just compare actor centers.
- `smartspawn`: type NONE with WALK selects `anything_walk`. It samples speed
  once as model speed plus a random value below three. Authored X selects the
  velocity sign. `anything_walk` checks camera-relative bounds before motion.
  The Python reference explicitly preserves this ordering and 100 Hz cadence.
- `randf(3)` uses unsigned `rand32() % 1000`, followed by floating-point
  division by `1000/3`. The source generator returns bits 16..47 of
  `seed*1103515245+12345`, retaining low 32 bits as the new seed. An injected
  fixed-point drift sample proves a parameterized driver, not this RNG or
  repeated floating-point position arithmetic. A byte-based sample is an
  explicit experimental adaptation, never a source-exact actor certificate.
- The pickup code checks model score, then health, then the historical engine
  timer-item identity. The existing dialect adapter resolves that source rule;
  new effect descriptors consume only `reset_timer`, not a model name or alias.
  Source reset value is 40,000 ticks. No matching target countdown/timeout
  lifecycle has been established, so this effect remains blocked.

## Current target ABI findings

| Layer | Current ownership / limitation |
|---|---|
| Source metadata | ModelIR retains directives and frame state |
| Raster conversion | `convert_character.py`; shared 16-color palette, 32x48 canvas adaptation |
| Actor directory | `pack_msu_roster.py`, 50 bytes; fixed role counts/delays and derived frame bases |
| Timing | `gen_pasm_animset.load_manifest` takes per-animation median, then byte delay saturation |
| Remaps | S4 byte selector; full emitted maps; generated per-model count table |
| Stats | No complete source stat/default record in the actor directory |
| Entity | 133-byte DP window; selected animation, variant and behavior driver remain separate fields |
| Attack dispatch | `Character_HitApply` gates selected attack state and the missing-attack jump fallback |
| Collision | Fixed `CHAR_HITBOX_W/H` comparisons; no general frame-body-box/vulnerability consumer |
| Damage | Existing fixed `CHAR_HP_PER_HIT` path is not a full frame force/type/drop descriptor consumer |

Derivable source facts include stats, exact role presence/order, frame timing,
geometry, maps and boxes. Canvas/palette reduction, timing conversion and AI
cadence require explicit adaptation policy and proof. Accepted compatibility
IDs and target slot/layout details are engine-specific metadata, not source
semantics. Current role fallback heuristics are adaptation policy, not proof
that a source role means another role in every engine dialect.

## Evidence generated in this worktree

`out/bor_compile_s5/{bor,tmnt,motu}/actors.json` and `actors.md` contain complete
descriptors/category matrices. `*-summary.json` contains compact evidence.
These are analysis outputs, not publishable build inputs.

Initial BOR report: 44 models, 17 legacy adapter candidates / 27 blocked;
36 accepted identities bind, with 15 candidates / 21 blocked under the current
validator. Strict full runtime certificates remain zero. All compared golden
animation frame counts match; that does not certify timing, collision or AI.

The four encoding probes produce:

| Subject | Encoding result | Still not proved |
|---|---|---|
| Time | 800 bytes | timer lifecycle/effect |
| Ramon | 2,336 bytes after source-default delay binding | zero-box vulnerability, zero-delay runtime semantics, behavior |
| Crab | 6,944 bytes; idle + walk | live drift driver, source cadence, offscreen removal |
| Lobster | 62,400 bytes; five alternate palettes | role-independent runtime attack dispatch/geometry and behavior |

TMNT: 67 parsed models. He-Man: 16. No full runtime actor certificates; foreign
dialect semantics remain unbound. The role inventory exposes He-Man's block,
follow, numbered freespecial, jumpdelay/jumpland, run/runattack/select/spawn
roles without mapping them by character name.

## Required continuation before S5 can be committed as complete

1. Implement and test the real role-independent target attack descriptor
   consumer while retaining an explicit accepted-behavior compatibility path.
2. Implement source-selected noncombat drift and prove one real subject through
   spawn, motion and removal. Python reference tests are not this proof.
3. Complete golden encoded asset/stat/frame comparisons, classify intentional
   adaptations and certify only supported runtime categories.
4. Complete live/new-model binding proofs, then integrate strict actor results
   into the existing S4 entry certificate without losing scene/layout evidence.
5. Re-run affected runtime checks/build only if production changes. Do not
   publish sets or replace accepted actors wholesale to obtain a certificate.

## Continuation evidence (not full actor certification)

`out/actor_s5_isolated_ulx18mwn/proof.json` records 90 passing native CPU
cases and 232 logical source ticks across 70 observed vblank intervals.
Kula's source transitions occur at ticks 8,16,24,32,36,40. The fixture covers
frame force/eligibility, signed collision/depth/altitude tests, zero-delay
completion and parameterized noncombat drift. It explicitly does not prove
organic spawning, source raster alignment, full damage callbacks or source
RNG/floating-point equivalence.

The production-clone entity fixture passes at
`out/actor_s5_entity_dbda485q/proof.json`. Kula source frames 2/3 subtract 5 HP;
the compatibility control subtracts 4 HP. Post-delegate CPU acknowledgement 21
proves continued execution rather than merely observing HP mutation. Lobster
fall frame 1 subtracts 15 HP only with behavior-owned attack/projectile flags;
unflagged fall and frame 0 do not hit. Its own maps 4/5 match live CGRAM.
Ramon loads its own 2,336-byte payload and consumes four zero-delay/nonvulnerable
descriptors; its pain raster role is still omitted by the fixed-slot packer.

The clone-only actor media occupies a documented inactive scene extent below
16 MiB. Actor frame/palette pointers are 24-bit even though MSU seek supports
32-bit offsets. `tools/actor_media_abi.py` now rejects actor extents beyond that
limit in the production packer. No scene or actor assets move in production.
Earlier above-16-MiB fixture results were invalid and are retained as failures.

The organic parameterized driver passes at
`out/bor_compile_s5/live-drift-final/runtime-commit-coldload/proof.json` using
synchronous read-only Lua snapshots at completed OOP updates. Both queue spawns,
authored X-dependent signs independent of facing, source-health sidecars,
movement/projection and bounds retirement are observed. This is not exact source
RNG, IEEE floating-point or full clock-cadence equivalence. Visual acceptance
is separate. Failed attempts remain under `out/actor_s5_*` and the fixture's
runtime directories. None of these PASS results is a full actor certificate.

The continuation production build passed with unchanged MSU SHA-256
`b1c4e499d611445e83a67f80f5be88dc2c5c0e2d91ebc14901e7891b8bcd89fc`.
The current built ROM SHA-256 is
`9aa88e2219f81e43bab88ba81fc324802637372fb5832af5ed5eeb7224a7eb35`.
Layout remains
32 stages, VM offset `$585D10`, queue capacity 92 / record size 10.

No full Normal/Hard/Bonus certification or S5 acceptance commit is claimed
by these partial results.

The focused policy/model/catalog/contract tests currently pass 41 cases. An additional
53-case compiler-only run passed 50 and hit three old queue-oracle hash guards:
`test_clean_committed_queue_tree_regeneration`, `test_accepted_queues_unchanged`,
and `test_unseen_normal5b_full_queue_shadow`. They still use the pre-S4
`0ef9a82` / `e7fe744a...` MSU oracle. No queue ABI/content change occurred in
this continuation; both archived accepted S4 and rebuilt MSUs hash identically.
These older tests were not rewritten or bypassed to obtain a green count.

The live compatibility control exposed a pre-existing call-width defect.
Committed S4 `Character_HitApply__ScoreAndFinish` enters A16 before calling
`G13_Game_Score_Award`. That wrapper saves/restores P, hence returns A16,
but the next immediate was assembled for A8 without a real SEP. Accepted
ROM bytes at `$00:E3DB` are `C2 20 A9 01 00 22 25 8F 07 A9 01 85 22`.
The candidate had the same defect at the shifted address. HP mutation alone
had concealed the subsequent invalid instruction stream in the initial
fixture. A post-delegate CPU acknowledgement is now mandatory.

The continuation adds only `SEP #$20` at that return boundary. Fixed damage,
source-force scoring policy, collision and median-timing adaptations are not
changed. The rebuilt production-clone fixture now proves the real continuation
after this repair. Width audit: 2,341 labels, zero new findings, 187 baselined.

## Current comparison and remaining integration

Across 44 original source models: SOURCE_EXACT has 0 whole-model certificates;
ACCEPTED_COMPAT has 36 immutable-build adapters and 8 unbound models. Foreign
projects inherit none: TMNT 67/67 blocked, He-Man 16/16 blocked under exact policy.
The inventory contains 1,201 explicit policy records, not 1,201 distinct proven
behavioral differences. Original accepted runtime IDs are preserved.

Full re-encoding of the 36 accepted actors yields 21 byte-identical full blobs
and 15 different layouts/payloads. Per-role comparison identifies 168 identical
roles, 47 accepted synthetic/repeated roles, and 11 raster mismatches. Base and
alternate palette bytes match for 34/36 actors. In particular, chair/trolly fall
and table/trash raster differences are not declared source-equivalent. The
immutable accepted adapter preserves these bytes; no production encoder migration
is claimed. Earlier prefix-only byte comparisons were insufficient.

`live_actor_evidence.py` attributes current-ROM/source-hash-scoped entity evidence
without promoting a whole-model certificate. Fixed-slot certification still
describes that target, not a universal absence of the newly tested primitives.
The bounded catalog integration now passes at
`out/actor_s5_entity_nhblc208/proof.json`: actual actor ID, source role, profile
and frame select 37 exact catalog entries plus one explicit compatibility
control. Missing keys fail closed. Forty CPU-driven frame updates produce
transitions at ticks 8,16,24,32,36,40 without host frame writes after start.
This private clock hook is not a certificate of general scheduler/render
coupling or complete source damage/AI lifecycles.

Actor-only entry recertification retains the supplied pre-S4 historical scene/
layout/environment evidence; it is not a fresh environment certificate. All
14 stage entries per Easy/Normal/Hard remain blocked by strict actor requirements;
their two existing scene certificates are retained. Bonus's two entries remain
blocked. Current environment analysis is reported independently; this work does
not close waves, rocking, depth-dependent hazards, alias HUD or SEWER media.

## Confirmed OAM prerequisite: S5 remains uncommitted

The serialized organic fixture delivered the actor's own walk tiles to VRAM,
its palettes to CGRAM, and consistent OAM entries, but sprites were not visible.
The production `Core_Oam_Init` sets `Nmi_ObjSel` to `$C2`; the production NMI
does not write that shadow to hardware `$2101`. Actual PPU state remained
OBJ base 0 / size mode 0 rather than base word `$4000` / mode 6.

The isolated causal diagnostic is
`out/bor_compile_s5/live-drift-final/runtime-objsel-causal-lua/proof.json`.
A real bus write of `$C2` makes Crabs and players visible. It also reveals
top-edge ghost sprites: the existing `$F0` hiding Y wraps with 64-pixel large
sprites. Merely applying the register initialization is therefore not a safe
standalone production fix. Emulator layer-hide settings and a private
frontpanel-removal control did not explain the failure.

No production OAM initialization/hiding change has been made. All S5 changes,
failed probes and successful bounded evidence are preserved. S5 is not committed
or declared complete; a focused OAM initialization/hiding prerequisite needs
direction before proceeding. The diagnostic screenshot is
`out/bor_compile_s5/live-drift-final/runtime-objsel-causal-lua/objsel-after-two-frames.png`.
