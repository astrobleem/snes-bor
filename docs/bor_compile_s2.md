# S2 — typed model/environment analysis, not production migration

Production reference: `0ef9a82bbd754aa979359df43d23821e48724ad8`.
S1 compiler reference: `a2b16614256805b0b61e6cf35f924148ef3584db`.

## Contract and evidence

`model_ir.py` parses before validation. ModelIR includes project/source identity,
raw model properties, remap assets, animation roles, timing, frame paths and
hashes/dimensions, offsets, body/attack boxes, force/drop/type, movement and
model dependencies. Frame-state snapshots preserve source ordering; geometry
resets at `anim`, while delay carries. Unknown directives/roles, malformed
scalars and missing assets fail closed. No scripts are executed.

`analyze.py` inventories independent PAKs with the same parser, scopes identities
by canonical project-content digest, assigns deterministic candidate IDs,
checks dependency closure and emits compatibility JSON/Markdown. Candidate
IDs do not replace accepted actor IDs. Unsupported dialect constructs survive
as diagnostics. Null ROM/MSU estimates explicitly mean encoding/linking is
not yet available; no complete arbitrary-PAK build emitter is claimed.

`certify.py` now consumes the same ModelIR validator and environment/resource
checks. Accepted encoded assets and stable IDs remain an explicit legacy
adapter, not a second generic model-name map. No stage-name exceptions added.

Machine-readable evidence: `bor_compile_s2_bor.json`,
`bor_compile_s2_tmnt.json`,
`bor_compile_s2_motu.json`, and `bor_compile_s2_certification.json`.
Full raw per-frame comparisons and diagnostics are regenerated under
`out/bor_compile_s2/`; the compact evidence does not discard them from the IR.

## Source authority and interpretation

Pinned original [BOR.C](https://raw.githubusercontent.com/Plombo/beatsofrage/eba02fe6c9e97e388126c51560a92024f406d8c0/BOR.C)
is the `historical-bor` profile, not a claim about all OpenBOR versions.

Aliases replace spawned display names after resolving the real model; they
do not allocate actor identities. The timer pickup compares **model** name,
not alias. Pickup precedence is score, health, engine-defined timer effect,
then extra life. The profile table describes that source rule; no new
name-specific production behavior is installed.

Authored speed is integer/10 clamped to 0.5..30 (default 1). Type-none walkers
use randomized horizontal drift and offscreen removal, not enemy AI. Signed
spawn altitude is independent of depth. Smartspawn overrides altitude for
certain onscreen enemy drops; the compiler preserves the original value and
does not claim all third coordinates should simply become a thrown state.

EnvironmentIR separates geometry, source scroll mode, holes, endholes, water,
blocked, rocking, mirror, altitude and aliases. Horizontal/down/left queue
transforms and mirror/hole adapters remain accepted. Alias HUD binding,
signed-altitude encoding, depth-dependent exit clamp/pit, texture-wave and
rocking rendering remain explicit source-fidelity blockers. Existing vertical
drop or water-stage acceptance is not proof of every original engine effect.

## Palette-map width: exact limitation, no model workaround

The source parser and converted remap list retain the full values. Constraints:

- `build_spawn_table.py` clamps map 0..3; bits 3..4 of the ten-byte queue kind
  byte encode the selector. Other bits already have meanings.
- `spawn.pasm`: `SPAWN_MAP_MASK=$03`; map scratch/index and actor map state are
  already bytes, not two-bit fields.
- `pack_msu_roster.py` retains `remap_palettes[:3]`.
- `Anim_ApplyMapPalette` performs byte-indexed palette arithmetic, but lacks
  a per-model map-count bounds contract.

No runtime widening in S2. The minimum safe follow-up is a versioned queue
selector sidecar (or wider record), full palette emission and map-count bounds.
A one-byte sidecar costs one byte per queue record (90 bytes at current
capacity); an 11-byte inline record also costs 90 bytes and cannot use the
current allocation without moving scratch. Each additional palette costs
32 MSU bytes (Lobster needs 64 beyond the packed three). Actor state and
selected-palette CGRAM allocation need not grow. This is an ABI/allocation and
focused-regression dependency, **not** a claim that SNES cannot afford maps.

## Newly exposed queue resource blocker

`SpawnTable_Wram=$7E550F`, `SPAWN_MAX_RECORDS=90`, ten bytes per record: the
allocation ends at `$7E5893` exclusive, where scratch begins. `Spawn_Init`
multiplies the stage's count by ten and copies that many bytes with no capacity
clamp. `main.pasm` loads the stage count byte without capping it. This static
ownership conflict is a blocker; no runtime corruption reproduction is claimed.

| Source | Candidate packed records | Capacity |
|---|---:|---:|
| Easy 6A | 92 | 90 |
| Normal 5B | 94 | 90 |
| Normal 6A | 107 | 90 |
| Hard 2 | 115 | 90 |
| Hard 5B | 104 | 90 |
| Hard 6A | 119 | 90 |
| EXTRA | 184 | 90 |

These are not total-spawn concurrency estimates. Group bounds do not prove
simultaneous actor needs. Reports also expose current catalog settings (32
stages, 45 actors), u8 ID/frame bounds, 32x48 actor canvas, 768-byte encoded
frames, palette requirements and 256x192/384-tile scene target. Resolution
conversion and full tile/ROM/MSU budgets remain encoding gates; nothing is
silently cropped or certified by these estimates.

## Golden and new-model results

All 24 accepted queues and the complete accepted MSU shadow layout remain
byte-identical. RUGAL and ENDING retain full production scene certification.
36 accepted BOR actor bindings pass through ModelIR: 16 adapter candidates,
20 blocked. The report compares roles/counts, raw offsets/boxes/attacks/timing,
maps/stats; omitted defaults remain distinguishable. Accepted manifests omit
original GIF paths, so complete pixel/frame provenance is not claimed.

Stricter model checks apply equally to existing IDs: all 24 golden stages now
block full source certification (S1 blocked 21). This is stricter proof, not a
changed ROM. Fall-role hit dispatch, remap truncation and other unverified
bindings cannot be waived simply because an actor already has a runtime ID.

| Model | Result |
|---|---|
| Time | Assets resolve; idle item; timer-reset effect needs a generic target binding. |
| Ramon | Source capability adapter candidate; idle/walk/pain/fall, health 10, speed 0.5; no new semantic blocker detected. Encoding/default-stat/AI binding still not certified. |
| Crab | Assets resolve; idle/walk, health 10, speed 0.9; noncombat randomized drift/offscreen driver missing. Not a generic enemy. |
| Lobster | Assets resolve; health 100, five maps; map-width and active fall-role attack binding block. No actor substitution. |

Full Normal: 2 scenes certified, 14 stages blocked. Hard: same counts, with
Time/Ramon binding requirements at 5A. Neither set is production-ready.
Bonus: both entries blocked. EXTRA retains 50 Crab, 27 Lobster, 166 spawns,
184 records (7 waits, 11 groups). SEWER source music/repeat and Sewer/Thanks
order/timing parse, but accepted encoded scene/media-directory binding is
missing. No media re-encoding or Bonus availability change.

## Independent local PAKs

| Input | Sets | Stage entries | Scenes | Declared models | Certified |
|---|---:|---:|---:|---:|---:|
| Original BOR | 4 | 43 | 7 | 44 | See accepted-adapter certification above |
| TMNT build 4153 | 1 (`Play_Demo`) | 4 | 2 | 67 | 0 |
| Masters of the Universe build 4086 | 1 (`Demo`) | 2 | 0 | 16 | 0 |

No downloads, fabricated fixtures or game-specific parsers. TMNT adds dialect
controls, blockade/layers and model behaviors; its 67 source declarations
exceed the current 45-actor build setting, not the hardware ID domain. MOTU
adds scripts (`@script`, `@cmd`, `animationscript`), combat/movement/palette
constructs. Scripts are retained as unknown semantics, never executed. Queue
counts are marked incomplete where unknown source constructs prevent a full
inventory. No entry in either extra PAK is certified or data-only classified.

## Seven stale derived inputs: closure

These active production queue inputs were stale in committed baseline bytes:

```
out/spawn_3easy/spawn_table.bin
out/spawn_3beasy/spawn_table.bin
out/spawn_3ceasy/spawn_table.bin
out/spawn_4aeasy/spawn_table.bin
out/spawn_4beasy/spawn_table.bin
out/spawn_5aeasy/spawn_table.bin
out/spawn_5beasy/spawn_table.bin
```

S1 pinned-source/compiler/MSU hashes and decoded deltas establish provenance;
accepted production used their already-regenerated dirty bytes. These are
derived inputs, not obsolete fixtures. S2 commits those exact accepted bytes.
`regenerate_queues.py` lowers from source through the existing accepted adapter,
checks all 24 candidates against pinned MSU before writing, then installs only
owned queue paths. The test starts from committed old queue bytes in an empty
temporary tree, forbids reading worktree queues, regenerates exactly seven
changes, checks all 24 results, and repeats with zero changes. Full clean-ROM
media rebuild independence is not claimed.

## Validation and next boundary

Focused compiler/model/integration tests, Python compilation and diff hygiene
only; production assembly/media and published ROM/MSU remain untouched. No
gameplay sweep is warranted for analysis tooling and already-accepted bytes.

Next: close the generic versioned queue/resource/map/altitude contracts and
model/environment encoding proofs, then target compiler-owned **complete
Normal**. Do not resume one-stage surgery or enable content based on queue
reproduction alone. S2 provides a tested diagnosis/IR harness, not a completed
arbitrary-PAK ROM builder.
