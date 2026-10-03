# S5: explicit policies and bounded live actor bindings

## Scope

One source-exact ModelIR feeds explicit SOURCE_EXACT and ACCEPTED_COMPAT
lowering. StageIR/SceneIR remain profile-independent. No exact compile falls
back to an adapter. Foreign projects default to SOURCE_EXACT with no BOR pins
or adaptations. All shipped model activation flags remain zero; no new actor,
set, scene, campaign or production asset is enabled.

The milestone is live generic primitives plus strict diagnostics, not a
complete source-exact actor engine. All remaining whole-model failures are
retained. Compatibility delegates the immutable accepted S4 actor data;
ADAPTER_EQUIVALENT does not certify source semantics or new raster encoding.

## Runtime and compiler contracts

- Source frame descriptor: 32 bytes, u16 200Hz delay, vulnerability, signed
  offset-relative body/attack corners, force, drop and attack kind. Range and
  bank bounds fail closed. Attacking/projectile state stays behavior-owned.
- Project-scoped descriptor catalog: deterministic model/role/profile keys;
  missing keys fail closed. Controlled entity fixture consumes actual runtime
  actor ID and frame, rather than host-supplied descriptor pointers.
- Exact clock primitive accumulates rational master-clock time, not median
  timing. Isolated scheduler hooks prove actual entity-frame advancement;
  they are not automatic whole-engine renderer/state scheduling support.
- Generic experimental NONE+WALK driver selects semantic flags, never source
  names. Its live projection/retirement contract is tested. Byte RNG,
  fixed-point arithmetic and OOP clock feeding are explicitly not exact BOR
  rand32/randf/IEEE-float/think scheduling.
- Effect descriptors preserve source intent. No fake timer effect: the target
  lacks source timeleft countdown/timeout and the delayed pickup lifecycle.
- Actor media is limited by actual 24-bit pointers, despite 32-bit MSU seeks.
  Shared packer/compiler guard rejects extents beyond 16MiB. Fixtures use a
  bounded private inactive scene extent, never production scene replacement.

## Final live controls

`out/actor_s5_entity_338c1885/proof.json`:

- Kula attack1: identical source fingerprint for both policies. Exact source
  frames2/3 subtract5HP, other frames inactive; signed source-box miss rejects
  collision. Compatibility delegates accepted4HP damage and acknowledges
  post-hit continuation. Source delays4,4,4,4,2,2 become ticks8,8,8,8,4,4;
  CPU-driven transitions are8,16,24,32,36,40 without host frame writes.
- Lobster: own map4/5 CGRAM bytes; fall frame1 force15 activates only with
  attacking/projectile ownership. Frame0 and unflagged fall remain inactive.
- Ramon: own2336-byte media loads independently; zero-delay/nonvulnerable
  descriptors are consumed. No visual alias. Fixed-slot pain media and
  source role-aware randomized AI remain unsupported.
- Catalog/missing-key controls and source/current-ROM hashes pass.

`out/actor_s5_isolated_rai9ztk8/proof.json`: 90 native cases, uniform/variable
timing, zero delay, signed boxes/depth/base altitude, parameterized drift.

`out/bor_compile_s5/oam-fixed-drift/runtime/proof.json`: two organic queue
spawns, authored sign independent of facing, source health sidecar, projection,
random sample and offscreen retirement. Own Crab raster is visibly rendered
by permanent production OBJ setup; no diagnostic register write. This remains
an experimental parameterized-driver proof, not full Crab certification.

## Strict results

Original BOR has44 source models: SOURCE_EXACT **0 certified /44 blocked**.
ACCEPTED_COMPAT **36 adapter-equivalent /8 unbound**. Inventory1201 explicit
policy records; not1201 distinct demonstrated discrepancies. The four new
subjects Time/Ramon/Crab/Lobster have no accepted compatibility delegation.

All36 accepted actors were independently re-encoded/compared:21 full blobs
identical,15 different;168 identical raster roles,47 accepted repeated or
synthetic roles,11 mismatched roles. Palette bytes match34/36. Distinct real
raster differences remain for chair,table,trash,trolly. No changed raster is
published merely to make comparison green.

Time: exact effect BLOCKED. Ramon: loader/descriptor subset passes; pain role,
stats and role-aware AI BLOCKED. Crab: visible organic experimental movement
passes; exact numeric/RNG/scheduler contract BLOCKED. Lobster: widened maps
and fall-role attack subset pass; full activation/damage/drop/AI BLOCKED.

Normal and Hard each retain14 blocked stages plus2 historical scene
certificates; neither complete set is source-certified or publishable. Bonus
EXTRA remains blocked (166spawns,50Crab,27Lobster,184packed records); SEWER is
a separate MEDIA blocker. The entry report replaces MODEL evidence only in
the supplied pre-S4 historical certificate. It does not re-certify historical
environment/layout claims. Current environment inventory is separate.

TMNT67/67 and He-Man16/16 models remain source-exact BLOCKED; no foreign
compatibility adapters. Their own role/directive inventories are reported,
not guessed historical defaults. Strict CLI failure was exercised on TMNT;
`--analysis-only` explicitly permits report generation, not publication.

Machine reports: `out/bor_compile_s5/closure-actors/actors.json`,
`closure-summary.json`, `closure-entries.json`, `closure-tmnt-summary.json`,
`closure-motu-summary.json`. Compiler CLI can regenerate them from local PAKs.

## Remaining engine capabilities

MODEL: arbitrary source raster dimensions/offsets/color preservation versus
fixed32x48/16-color adaptation; complete role media (including pain); exact
stats/default arbitration; automatic source scheduler/render/state transitions;
full target filters/attack IDs/damage types/drop callbacks; source AI decisions;
per-frame movement events; exact RNG/float cadence; timer and pickup lifecycle.

ENVIRONMENT: alias/opponent HUD, water waves, rocking, depth-dependent
blocked/endhole. MEDIA: SEWER encoding/link. DIALECT: foreign animation/control,
palette/audio semantics and unestablished engine defaults. RESOURCE: explicit
queue/actor/frame/media limits remain fail-closed. No content was truncated.

## Validation and production deltas

41 focused compiler tests PASS, native and entity fixtures PASS, visible organic
fixture PASS, no-name-selection guard PASS. Width2343labels/0new and label drift0;
py_compile/diff checks PASS. Production build PASS with unchanged MSU. Older
queue tests still pin the pre-S4 MSU oracle; their three rejected stale-oracle
checks are preserved in the progress log and were not bypassed.

OAM prerequisite committed separately as `4cf234c`; see
`oam_initialization_contract.md`. S5 also repairs the discovered A16->A8 hit-tail
return with a real SEP. The legacy four-HP control now proves CPU continuation,
not merely the HP store before a malformed instruction stream.

ROM SHA256:
`4f0314db7a03c196a7de0c772d77df924cfc956d111457c63a411f3b6bdf30be`

MSU SHA256:
`b1c4e499d611445e83a67f80f5be88dc2c5c0e2d91ebc14901e7891b8bcd89fc`

Next source-exact engine work should target the role/media and automatic
scheduler/AI contracts, not publish complete Normal under a false certificate.
