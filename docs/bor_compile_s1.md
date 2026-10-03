# S1 shadow certification: layout reproduced, source gate blocked

Production authority: `0ef9a82bbd754aa979359df43d23821e48724ad8`.
Compiler predecessor: `1e072df8c667c1457d805a78057b9f01627d9938`.
Machine-readable evidence: [bor_compile_s1_evidence.json](bor_compile_s1_evidence.json).
Full reproducible IR/frame report: `out/bor_compile_s1/certification.json`.

No production file, catalog, queue input, ROM, MSU or availability flag changed.
This is **not full S1 closure**: binary reproduction passes; strict source
certification remains blocked. Do not enable Normal based on this report.

## Seven stale derived inputs

All paths below are tracked build inputs, not obsolete fixtures. In each case
the current source compiler output and corrected worktree file equal the
hash-pinned accepted MSU queue. Committed baseline files do not. Exact three-way
SHA-256 values and every decoded record difference are in the evidence JSON.

| Source | Tracked file | Changed records | Semantic delta to accepted MSU |
|---|---|---:|---|
| DATA\EASY\3AEASY.TXT | out/spawn_3easy/spawn_table.bin | 5 | K' runtime identity 31 and identified-enemy kind/subtype |
| DATA\EASY\3BEASY.TXT | out/spawn_3beasy/spawn_table.bin | 7 | K' runtime identity 31 and identified-enemy kind/subtype |
| DATA\EASY\3CEASY.TXT | out/spawn_3ceasy/spawn_table.bin | 4 | K' runtime identity 31 and identified-enemy kind/subtype |
| DATA\EASY\4AEASY.TXT | out/spawn_4aeasy/spawn_table.bin | 7 | K' runtime identity 31 and identified-enemy kind/subtype |
| DATA\EASY\4BEASY.TXT | out/spawn_4beasy/spawn_table.bin | 2 | K' identity 31; Mrbig identified boss identity 42 |
| DATA\EASY\5AEASY.TXT | out/spawn_5aeasy/spawn_table.bin | 25 | Actor identities/subtypes; Drum 39 and contained Meat 16 |
| DATA\EASY\5BEASY.TXT | out/spawn_5beasy/spawn_table.bin | 3 | Eiji identity 41 and identified-enemy kind/subtype |

All seven retain identical record counts, trigger/X/Y, facing, map and HP/2P
bytes. Differences are actor/item identity and record kind/subtype only.

The committed `build_rom.py` establishes the producer/consumer chain:

1. `SPAWN_TABLES` comes from `STAGE_CONFIGS[*].spawn`.
2. `check_spawn_table_freshness()` regenerates expected bytes with the current
   source/model roster lookup and **rejects**, rather than repairs, stale files.
3. `build_msu_assets()` reads the on-disk queue files and gives them to
   `pack_roster()`.

Thus the accepted MSU reflects the corrected derived inputs, not those seven
committed blobs. A pristine checkout with those old blobs fails the freshness
comparison. This audit proves the byte provenance; it does not invent an editor,
timestamp or historical command for the uncommitted corrections. They remain
untouched and excluded from the S1 commit.

## What now reproduces

- All 24 accepted BOR stage queues: byte-identical to the accepted MSU.
- Entire 32-stage MSU relink: byte-identical, 28,722,026 bytes.
- SHA-256: `e7fe744af2928939f926a1c9121f6ac9e7f1d378533b95366e4afefd6bfe90af`.
- VM module offset: `$585C50`, matching the committed constant.
- Stage count, catalog maximum, scroll count and music count: all 32.
- Source-derived stage/boss audio and scroll/mirror values agree with the
  committed generated tables for every golden stage.
- Content-signature reuse partitions match production BG/frontpanel reuse
  independently, without an Easy/Normal correspondence table.
- Normal prefix flags derive as `[0,0,1,1,0,0,1,0,1,0]` from LEVELS.TXT.
- RUGAL and ENDING bind to accepted scene IDs, audio, ordered media and exact
  frame timing. All frame pointers/IDs are checked; existing encoded pixels
  are reused under the source-PAK/MSU hash pins, not re-encoded.

RUGAL uses track 7/repeat 0; ENDING uses track 14/repeat 1 in this baseline.
Completion track 3 is source-bound for entries with `next`.

## Strict certification result

| Corpus | CERTIFIED | BLOCKED |
|---|---:|---:|
| Golden stages | 3 | 21 |
| Golden scenes (unique) | 2 | 0 |
| Easy logical entries | 4 | 12 |
| Complete Normal logical entries | 4 | 12 |
| Hard logical entries | 2 | 14 |
| Bonus logical entries | 0 | 2 |

The three golden stages without pending bindings are Easy 1B, Easy 6B and
Normal 1B. Normal 6B also certifies in the candidate full-set link. Repeated
RUGAL/ENDING references account for six certified scene entries across sets.
Overall: 10/50 logical entries certify; 40 remain blocked.

### Confirmed encoding losses versus unverified bindings

- **Map selector:** `build_spawn_table.convert_events()` clamps to 0..3 and
  `src/core/spawn.pasm` uses `SPAWN_MAP_MASK = $03`. Authored maps 4, 5 and 6
  cannot be preserved by merely widening a compiler acceptance predicate.
- **Alias:** the parser retains the display alias; the ten-byte encoder has
  no alias output. `spawn_parse.py` explicitly documents it as unused. Source
  model identity and display alias remain separate; no identity substitution.
- **Altitude:** three-component `coords` remains explicit in IR; the accepted
  queue encoder consumes X/Y only. Generic vertical drop is not proof that
  arbitrary authored altitude (+49 or -5) was represented.
- **Environment:** water/rock/blocked/endhole have retained source values but
  no certified separate runtime binding. These are labeled unverified binding
  gaps, not assumed absent merely because a keyword search found no handler.
  Existing hole records and direction/mirror metadata remain linked.
- **Model contracts:** the existing model parser ignores directives including
  load, blast/burn, throwframe/shootframe/jumpframe and secret. The validator
  exposes these per model. This does not prove every corresponding runtime
  mechanic is absent; it means an automatic source-to-runtime binding is not
  established. A pinned actor ID cannot make unknown semantics disappear.

These gates deliberately do not redefine previously accepted gameplay.
They explain why acceptance of an adapted runtime is not the same as strict
source-compiler certification. Production fixes were not authorized here.

## Complete Normal: mechanical layout succeeds, publication blocked

All remaining Normal stages discover existing presentation assets by source
content. The generic shadow linker appends four independent encounter records
for 5B, 6A, 6B and 6C while retaining all existing physical IDs.

- Candidate physical count: 36.
- Candidate MSU size: 29,007,854 bytes (+285,828).
- Candidate VM offset: `$5CB8D4`.
- Candidate SHA-256: `935a9d2284d780c974770647b7273335036e0bd169dfac7f6704438da8ec316c`.

This is an in-memory layout calculation, not a published artifact or a
source-fidelity PASS. Normal 5B/6A/6C retain map/alias/Z or model-contract
blockers. Normal 5A additionally references **Time and Ramon**, as does Easy
5A; the S0 emphasis on Hard 5A did not make them Hard-only content.

Hard also has inherited alias/map/environment/model-contract blockers. Its
complete candidate link stops at the withheld Hard 5A queue with unbound
Time/Ramon. Hard is **not** currently blocked only by new graphics/models.

## Bonus and model diagnostics

EXTRA confirms 184 authored records: 166 spawns, 7 waits and 11 groups.
Crab accounts for 50 and Lobster for 27 spawns (case-folded identity matching).
No fabricated packed queue count or borrowed-actor queue is emitted.

- **Crab:** type `none`, health 10, speed 9, idle 1 frame, walk 8 frames.
  Source image files resolve. No accepted runtime identity/encoded actor
  exists. The backend groups `none` with props; that is not a certified
  speed-9 walk/AI binding. Whether an additional runtime movement primitive
  is needed remains a behavioral validation question, not a guessed enemy AI.
- **Lobster:** enemy, health 100, speed omitted (source default unresolved
  for a new binding), five remaps. All source frames resolve; roles are idle
  5, pain 3, fall 25, walk 12, rise 5, attack1 14, attack2 20. No accepted
  encoded actor/ID. Map domain and attack annotations in fall require explicit
  binding/dispatch validation, beyond adding a roster number.
- **Time:** item, health 0, idle 1 frame; no accepted actor ID or validated
  item-effect binding. Current `classify_pickup()` yields NONE for these stats.
- **Ramon:** enemy, health 10, speed 1, four one-frame roles (idle/walk/pain/fall),
  no attack role. Images exist; encoding/default-stat/AI binding remains to be
  validated. No generic enemy substitution is certified.

SEWER parses TIME/repeat 1, then Sewer (10,000 + 10,000 ms), then Thanks
(5,000 ms), both source images 320x240. TIME audio is already bound; Thanks
already has production clip 6. Sewer still needs an encoded payload, explicit
clip/scene directory binding and finalized link. No new scene-runtime
primitive is inferred merely from this missing media binding.

## Next decision

The compiler **cannot yet fully certify complete Normal**. Do not resume
Normal-5B surgery. The next bounded work should resolve the generic map/alias/Z,
environment and model-binding contracts, deciding explicitly which accepted
adaptations are permissible and which need source-faithful runtime extensions.
Only after the strict golden gate passes should the next production content
batch be **compiler-owned complete Normal**.

No manually maintained production table has changed ownership in S1. The
compiler owns shadow evidence, candidate IDs/layout calculations and binding
decisions only. Accepted ID seeds, encoded assets/media and legacy packer ABI
remain pinned adapters until migration is authorized.

## Validation

Focused compiler tests (27): PASS. They assert both positive reproduction and
correct negative certification results. `--require-golden` must return 2 for
this baseline. No gameplay suite or production rebuild is appropriate for this
tools-only change. Production ROM/MSU hashes remain unchanged.
