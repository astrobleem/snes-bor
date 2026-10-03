# S8 complete Normal implementation ledger

Status: NORMAL_COMPLETE for the bounded campaign-flow/runtime acceptance below.
This does not close the separate all-stage manual visual acceptance gate or
claim full manual combat-balance/source-exact certification. The sections below
record historical implementation checkpoints; the final closure record at the
end supersedes earlier candidate-only and “Normal remains unavailable” status
statements.

Baseline: S7 `c8cbd71b200cab869d3f953bdd07352c172577ed`.

Pre-existing local production artifacts (before the S8 build):

- `distribution/bor.sfc`: `df46b8b9a030186c567ee1227fd96fe7aa903bc313dc17d7247be80cf2edc96e`
- `distribution/bor.msu`: `b1c4e499d611445e83a67f80f5be88dc2c5c0e2d91ebc14901e7891b8bcd89fc`
- `src/main.bin`: `fe0ad558880e08dc4f99b17a20bf3a94618ade8fbc5cb99c56aa5a1fbb277880`
- `src/main.pansy`: `ed40acb7a7d29e1d90da32b3ca35153fa16e242232e32772e630f00d75db4977`
- `src/main.sym`: `ceef123a34a1c2a3b68b23269e76c6be049d050aef595dc88568f6751545c3ba`

The five dirty `out/g13_*.json` reports were present before S8 and are not S8
evidence. They remain untouched.

## Source-owned link

`production_campaign.py` resolves complete Easy and Normal from the exact
project IR. Each has 16 typed entries (14 stages and two scenes). Physical IDs
remain independent of logical order. Accepted media bindings are reused only
under matching source-content presentation signatures; unknown progression,
stage directives and missing scene/media bindings reject the link.

Normal's remaining physical records are appended at 32..35. Their queue
counts are 94, 107, 19 and 34. Queue capacity must be generated from the full
linked set, not the previous 92-record maximum. Normal is not enabled yet.

## Required runtime work

- Real Time item media plus source-selected timer reset, countdown and timeout.
- Real sparse Ramon media, authored default health, absent-attack handling.
- Depth-dependent blocked/endhole behavior and associated lifecycle.
- Water/rock presentation modes.
- Instance alias/opponent HUD, independent of model/effect identity.
- Source next/showcomplete flags for complete campaigns; exactly-once ending.

All existing actor compatibility adaptations remain ACCEPTED_COMPAT, not
SOURCE_CERTIFIED. S7 source-exact CPU/numeric/AI failures remain separate.

## Validation so far

Six focused compiler linkage tests pass. The first production build exposed
an audio reachability filter hard-coded to directory names; it now derives
reachability from selected full source identities. No native S8 acceptance
has run yet.

The campaign baseline test now pins S7 explicitly rather than reading mutable
HEAD. Eighteen campaign-link, model-binding and water-table checks pass; eleven
additional bounds-host/HUD checks pass, including isolated assembly. These
are structural/ABI evidence, not production runtime or visual acceptance.

Normal-only environment integration uses ROM bank 14 for the water/rocking
adapter and compiler tables, bank 15 for depth-boundary/pit handling, and bank
16 for the gameplay timer and effect host. Actual assembled bank bounds and
native behavior still require the production candidate build. The water
adapter uses the audited $7FB220..$7FB783 gap and HDMA channel 6; it does not
reuse either source-actor tile window or the frontpanel cache.

New Ramon media is independent and source-derived for idle/walk/pain/fall.
The ordinary-opponent ACCEPTED_COMPAT driver remains the selected adaptation
(shared target movement/ranges and target-speed constant, not exact source
AI/speed). Missing authored attacks now select idle without fabricating an
attack or consuming attack-choice RNG. Authored health defaults are lowered
for newly bound Normal models; Easy retains its explicitly inventoried old
queue bytes. These are compatibility choices, never SOURCE_CERTIFIED claims.

The first finalized pack attempt found the old 45-character soft cap. The
directory now reserves exactly the linked record count (47 for S8) under the
existing u8 count/50-byte record ABI. Two focused tests verify directory size,
every payload offset, the 255-count bound, and missing-delay compatibility
lowering. Ramon's manifests retain authored `delay: null`; the compatibility
encoder uses zero for that missing value instead of crashing in median(None).
The pinned BOR loader initializes its delay register to zero, and Ramon never
authors a delay. Time's one-frame delay retains the established u8 saturation
adapter; this does not delay or implement its independent timer-reset effect.

Candidate MSU packing no longer replaces distribution/bor.msu before ROM
assembly/layout validation succeeds. Both current distribution hashes still
match the pre-S8 artifacts above. Normal availability remains false.

## Candidate integration checkpoint

The combined runtime assembled successfully after explicit bank-layout repair:
the water Begin/End bracket moved intact into the Game_State_Play entry/common
return, cold audio/water initialization shares a banked ordered wrapper, and
the existing dirty-gated HUD text body moved to HUD bank 5 through the existing
long text entry. The boot ends at $FF9E, leaving two bytes before the fixed NMI
stub; the text-bank and score-memory guards pass. No reserved window was reduced.
The widened AI idle branch is required by the new sparse-attack guard's code size.

Focused checks: 32 selector/timer/probe tests, 11 campaign/binding/catalog tests,
11 HUD tests (including S7 text-body and emitted trampoline equivalence), and
six isolated candidate-output/gating tests pass. The width guard has zero new
violations. These checks do not establish native campaign acceptance.

`python build_rom.py --normal-candidate` enables Normal only in the explicit
test target `build/s8_candidate/bor.*`; the default release gate remains closed.
The full candidate build and native traversal are still required. No S8
runtime, complete-set, or SOURCE_EXACT certification is claimed here.

## Native scene correction and first complete skip traversal

The opt-in candidate now completes the real TITLE -> Normal -> player select
route and all 16 authored entries with their compiled direct/showcomplete flags.
`out/s8_scene_edge_skip.json` records Rugal and Ending fresh-input skip,
clean transport teardown, exactly two scene continuations, return to TITLE,
and exactly one set-completion increment. This is accelerated campaign/control
flow evidence, not a fight-through or foreground pixel certification.

Two production scene defects were exposed rather than bypassed in the harness:
uninitialized `SceneVideo_MsuDmaProbe` inherited 29 and disabled natural
prefetch; and an A16 read at `Input_trigger+1` included the neighboring
`Input_old` byte, manufacturing a skip edge from held A. Cold initialization
now clears scene-owned controls, public authored requests disable the diagnostic
probe, and scene input reads each player's complete trigger word exactly once.
Six focused scene init/input/fence tests pass; the native skip run keeps the
strict fresh-edge requirement. `out/s8_scene_edge_natural.json` separately
passes the complete natural route: Rugal 126 frames, Ending 1997 frames/four
clip transitions, clean transport, two scene continuations, and exactly one
completion credit retained during TITLE dwell. Release Normal availability
remains gated pending the remaining gameplay/presentation checks.

## Encounter checks and source identity correction

`out/s8_scene_edge_easy.json` passes the bounded three-clear Easy control,
including its first showcomplete transition and unchanged TimesCompleted.
This is not whole-Easy pixel or combat acceptance.

`out/s8_ramon_native_02/report.json` observes independent roster45/HP6,
native down-stage drop and recovery, walk movement, no invented attack,
actual VRAM bytes matching Ramon's own encoded frame, controller damage,
compatibility pain and native death. The preceding failure exposed a shared
`Character_Throw_Play` selector bug: THROWN was rejected before integration,
and a later comparison used velocity-high rather than the selector. The fix
restores selector dispatch without changing gravity arithmetic. Airborne
initial-frame publication still needs separate validation.

Time native02 observed reset, exact 600-source-tick retirement, timeout death,
pause/resume and actual timer text in VRAM, but failed three ownership/probe
checks. Native03 confirms zero pending-item OAM submissions after the renderer
filter and actual concurrent admission, while its reuse check remains failed.
These reports remain failures, not blanket timer acceptance.

The reuse investigation exposed a genuine Normal identity violation: legacy
ordinary records below roster29 retained a slot's prior art, including Time.
Normal now selects an explicit source-identity queue lowering policy; all 614
spawns bind their own source model using the existing identified-enemy subtype.
Easy alone retains its pinned legacy queue policy. Twelve focused linkage and
binding tests pass, including map/flag preservation, roster0, missing identities,
and unchanged Easy queues. Fresh MSU generation and native acceptance of the
new Normal queues are required; earlier candidate receipts do not cover them.

## Combined candidate: queue-safe foreground and explicit Easy policy

The combined candidate ROM `cb09e8d79a86439190309511dc7cb040c70ad6b48d3b6cf298c28bbc9a8b2c41`
and MSU `266f8a32129882831e9d5992488c5f7c1978689304b7e936deff39d75c30825d`
include all Normal identity bindings, full foreground data, the source-drop
initial idle publication, and explicit Easy completion compatibility.
Queue layout passes without reducing its reserved arena; foreground private
state is now at `$7EE020..$7EEAB5`, not inside that arena. Bank0 ends at
`$FF9E`, retaining the existing two-byte margin before the fixed NMI stub.

`out/s8_fullfp_easy_01.json` passes the bounded native three-clear control
with S7-compatible Easy showcomplete behavior. Authored Easy `next` flags
remain separate; Normal continues to use its authored flags. This supersedes
the earlier three-clear report as the compatibility control, not as a full
Easy campaign proof.

`out/s8_timer_native_05/report.json` passes the native behavioral gates,
including 600-tick retirement, pending-OAM exclusion, correct ordinary-model
slot reuse, pause/resume, timeout and respawn. Native04's failed retirement
check sampled an intermediate callback state; the recorded retirement itself
was exact. The failed report is retained. Visual acceptance is still withheld:
the 5A screenshot has a separate background presentation defect to resolve.

`out/s8_ramon_native_03/report.json` observes Ramon's own airborne idle tiles,
landing/recovery, controller damage and native death, but its final source-spawn
journal check fails. It remains a failed report pending observer diagnosis.
The first full-foreground probe matches actual VRAM/CGRAM but fails its seam
capture and has an empty event journal; neither pixel-composite nor transfer
ownership acceptance is claimed from that incomplete probe.

Normal production availability remains false. These are candidate integration
results, not S8 completion or SOURCE_EXACT certification.

## NORMAL_COMPLETE closure — 2026-10-02

The closure candidate identity is ROM SHA-256
`05edd46023b3173f8432087f8cfcbf182726c35ecfb918b5c996ec23e414ba1f` and
MSU SHA-256 `8eb71123e3baa3e2bb3f696775ca3d0dad42a5fa2d64ea7373b1dfd6f50bf3c6`.
The full hashes for all recorded artifacts, receipt digests, and extracted
route/completion evidence are in
`docs/review/normal_complete_receipt_manifest.json`.

These `luna29/luna27/luna25` receipts are the final-closure evidence because
their embedded ROM hash matches this candidate. The earlier
`s8_normal_sa1_*_luna01.json` receipts are historical evidence for the distinct
ROM SHA-256 `7ef9d232e688c77d8aa54c01c45d44d3868dbc21ef5a67a3750fccd2bb9186dd`;
their passing runs do not validate this final candidate. Neither receipt set
is a campaign rerun of the subsequent focused runtime repairs. Those repairs
have focused tests and assembly evidence only.

The final compiler-owned Normal candidate is selectable and traversed on the
persistent SA-1/source-sized path. This closure supersedes the earlier
candidate-only status notes above; it does not change the independent manual
visual-acceptance gate in `tools/verify/S8_ACCEPTANCE.md`.

Runtime receipts, generated from the same candidate ROM/MSU pair:

- Natural, full authored route and all-spawn traversal: `out/s8_normal_full_natural_candidate_luna29.json`
- Legitimate scene-skip route: `out/s8_normal_full_skip_candidate_luna27.json`
- Bounded Easy control: `out/s8_normal_full_easy_candidate_luna25.json`

Natural Normal passed all 83 receipt checks across all 16 authored entries:
1A, 1B, 1C, 2, 3A, 3B, 3C, 4A, 4B, 5A, 5B, 6A, 6B, Rugal, 6C, Ending.
The 735 expected spawn records all completed (614 model-bearing records),
including the authored 6B → Rugal → 6C → Ending boundaries. Natural Ending
completion advanced `TimesCompleted` exactly once, 7 → 8. The independent skip
receipt passed 68 checks across the same 16 entries; Rugal and Ending each
took the legitimate skip path and campaign completion advanced exactly once,
6 → 7. The first three Easy entries passed 25 checks and left its completion
counter unchanged, 6 → 6.

The Normal receipt observed persistent SA-1 ownership active at the end of the
run, with no host error, worker error, or event-ring overflow. Source-sized
publication was exercised: 38,259 source visual calls and 8,617 successful
source OAM presentations. There was no silent legacy-renderer fallback.

Resource busy behavior was fail-closed. The natural run recorded 1,246
media-stream-busy fields across 420 intervals (longest 186 fields). It recorded
467 `$27` residency-busy actor samples; these samples were skipped/hidden, not
drawn using stale OBJ data. The final `SourceVisual_Error` values `$A0`/`$AA`
are loader phase markers, not runtime error counts. D705 is not a marker in
this candidate's current source; an obsolete empty D705 trace is not evidence
of zero events. No corruption or gameplay-state fault was reported.

Explicit nonclaims:

- Accelerated, input-driven unlink traversal is not a manual combat-balance
  playthrough and does not claim every recorded unlink was a combat kill.
- All-stage manual visual acceptance remains outstanding. A bounded 1A
  presentation probe is not an all-stage actor-pixel audit.
- Campaign-specific peak OBJ residency, maximum OAM entries, and scanline
  pressure were not measured by these campaign receipts; the separate
  six-actor bounded proof is not a campaign-wide measurement.
- Transient residency-busy samples fail closed and may skip visible actor
  samples; this is not a claim of uninterrupted animation.
- This is not SOURCE_EXACT certification of every authored AI/action, nor a
  complete Easy campaign proof.

Candidate identity:

```text
ROM: build/s8_normal_sa1_rtl_candidate_luna05/bor.sfc
SHA-256: 05EDD46023B3173F8432087F8CFCBF182726C35ECFB918B5C996EC23E414BA1F
MSU: build/s8_normal_sa1_rtl_candidate_luna05/bor.msu
SHA-256: 8EB71123E3BAA3E2BB3F696775CA3D0DAD42A5FA2D64EA7373B1DFD6F50BF3C6
```

Focused verifier regression after the final harness cleanup: 93 tests and 14
subtests passed. Full candidate build and receipt reproduction (requires the
local BOR source PAK and project toolchain):

```powershell
py -3.10 -B tools/bor_compile/build_normal_sa1_candidate.py --output build/s8_normal_review_candidate
$env:BOR_TEST_ROM = (Resolve-Path 'build/s8_normal_review_candidate/bor.sfc').Path
$env:S8_NORMAL_CANDIDATE_DIR = (Resolve-Path 'build/s8_normal_review_candidate').Path
$env:S8_NORMAL_CANONICAL_P1_CONTROLLER = '1'
$env:S8_NORMAL_BOUNDED_MESEN_IO = '1'
$env:S8_NORMAL_SCENE_FIELDS = '40000'
$env:S8_NORMAL_TRAVERSAL_START_LIVES = '99'
$env:S8_NORMAL_AUTOFIGHT = '1'
py -3.10 -B tools/verify/game_s8_normal_campaign.py --mode natural --spawn-traversal --stage-fields 300000 --report out/s8_normal_natural_review.json
py -3.10 -B tools/verify/game_s8_normal_campaign.py --mode skip --stage-fields 300000 --report out/s8_normal_skip_review.json
py -3.10 -B tools/verify/game_s8_normal_campaign.py --mode easy --stage-fields 300000 --report out/s8_easy_review.json
```

## Verifier source reconstruction update — 2026-10-03

The public campaign verifier now runs from readable reconstructed Python in
`tools/verify/game_s8_normal_campaign.py` and
`tools/verify/_game_s8_normal_campaign_base.py`; it no longer requires the
retained CPython 3.10 bytecode at runtime. This is a reconstruction, not the
original lost source text. The active and protected 160,137-byte bytecode
copies remain unchanged at SHA-256
`4b8596c4b6b2081ef3c4acf68306af00068fec06cbd786d5a76915f62c92522`.

Native CPython 3.10 offline comparison passed 13,869 helper/Lua cases, 108
nested-helper cases, and 18 stubbed control-flow scenarios. An isolated,
cache-free import/`--help` check passed against the repository runtime sources
with no external process launch. Focused repository tests passed: 39 Normal
projection tests and five selected traversal-contract tests, using small
in-memory metadata stubs. The full source-queue traversal test module remains
blocked at import because its setup requires the absent original BOR PAK; no
PAK was copied or replaced. Consequently these checks are not proof of real
PAK-backed spawn traversal or full emulator-path equivalence.

No campaign receipt, ROM build, Mesen session, or gameplay traversal was run
for this source reconstruction. Existing receipts continue to validate only
their embedded candidate ROM/MSU hashes. See
`docs/review/normal_complete_review_handoff.md` for the exact test scope and
remaining validation limits.
