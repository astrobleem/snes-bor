# S8 audio gate handoff

The S8 **Normal ACCEPTED_COMPAT source/SFX build gate is PASS**. Command:
`python tools/audio/build_audio.py --sfx-only` (about 5.3 seconds).
This is a scoped build/data result, not source-exact certification or audible
acceptance. Main still owns the combined ROM build and roster directory limit.

## TIMEOVER binding for main / Dewey

Target collaborator: `01a0a0fd-5fdd-7c22-91ee-6ef651285dbe`. No agent messaging
tool was available; this is the shared-workspace handoff.

- `src/main.pasm`: `STAGE_TIMER_TIMEOVER_SFX_ID = 12`,
  `AUDIO_SEMANTIC_TIMEOVER = $1D`.
- `src/core/stage_timer_host.pasm` already dispatches these through
  `Audio_QueueResidentSemantic`, with campaign 3 gating. The host was not edited.
- Actual BOR `DATA/SOUNDS/TIMEOVER.WAV`, raw SHA256
  `b2b70433a077412a3e3f6d0fd8c9f1a31ad9f6047dc6901e21201d967ee20018`.
- Full 0.9142857-second signal resampled from 22050 to 11025 Hz. TAD uses the
  new sample's actual rate and `play_note 0 115`; no substitute or silent stub.
  Native-rate BRR would require 11340 bytes and exceed current capacity;
  the new sample requires 5670 bytes. Existing samples were not resampled.
- Appended `sfx_timeover = 12`, existing effect IDs 0 through 11 unchanged.
- `soundwork/tad/build/audio-data.bin`: 61291 bytes, SHA256
  `4c2ff4eb3713c6ce7a511cccc07929fa140425441c659e365db63d6761aefe8f`.
- TAD common data: 57709 bytes; resident allocation: 61167 bytes;
  reported ARAM free: 3857 bytes. Patched driver hash remains unchanged.

## Build ownership

`build_audio.py` calls `plan_action_residency.py --runtime-actions` and
`verify_sfx_production_banks.py --runtime-actions`. Legacy exploration and the
reload-fixture bank catalog remain independently callable and unmodified as
artifacts; production no longer depends on their stale report hashes.

The runtime inventory includes 47 roster models, all four source-normal BOR
players, RAMON, MISC/TIME, and current source engine events. It records 401
requirements over 45 assets. It makes no simultaneous-residency claim.

The linked runtime verifier checks pinned compiler/driver identity, compiled
blob hash, source/output seal, ARAM, resident IDs, source/canonical/stream
hashes, and TIMEOVER linkage. `seal_runtime_audio.py` can refresh its seal only
after the pinned compiler's reproducibility check passes. Patch text identity
uses LF normalization, while binary/compiler identity remains byte-exact.

Source/SFX checks now run **before** music encoding. `--sfx-only` runs this gate
without music. No music cache was introduced and no PCM music was re-encoded.

## Normal scope, preserved adapters, and evidence

`s8_audio_scope.py` derives Normal's closure from its 14 source stage queues,
contained items, and four source-selected players: 37 roster entries. It
mechanically reads S7 `c8cbd71b200cab869d3f953bdd07352c172577ed`, verifies the
baseline resident blob against its driver seal, and pins source PAKs, existing
movesets, resident samples/effects, old Batch-B tables/config, stream sources,
and shared runtime audio code. It does not trust the stale explorer reports.

The earlier 12-assets/17-requirements exact-source audit was broader than S8's
authorized ACCEPTED_COMPAT contract. Existing actor mappings, including the
old >=21 death exclusions, are explicitly `ADAPTER_EQUIVALENT`, never exact
source coverage. Foreign requirements are `OUTSIDE_NORMAL_SCOPE` and do not
force TMNT changes. New unknown/unhandled source requirements still fail.

The new Normal death table preserves all 45 S7 entries and appends source
selection for Ramon (roster45, real DIE1 stream1, semantic1). Time (roster46)
has no source diesound, so none is fabricated. `AudioSemantic_EmitDiesound`
selects this 47-entry table only for campaign3, retains the legacy21 path for
other campaigns, and records physical slots4/5 correctly. No existing stream
data/config or legacy generated table was changed. The implementation is in
the actual `src/core/vm/vm_native_engine.pasm`; `src/core/audio_semantics.pasm`
does not exist in this checkout.

`runtime_audio_coverage.json`: PASS; 47 nonempty requirements classified
`ADAPTER_EQUIVALENT`, 38 `OUTSIDE_NORMAL_SCOPE`, two `NEW_SOURCE_BOUND`
(Ramon death and TIMEOVER), plus the checked Time-item MONEY/reset audio.
No unclassified new requirements remain.

Validation: eleven focused `test_s8_audio_gate` tests passed, including isolated
assembly of the death selector, unchanged old table selection, and rejection
of unknown new diesounds, adapter drift, blob/sample corruption, and wrong
TIMEOVER semantics. The pinned TAD `rebuild.py --check` passed in the TIMEOVER
integration turn. No additional audio encoding, ROM build, emulator, audible
acceptance, broad regression, or music encoding was performed in this pass.
TIMEOVER and Ramon still need main's combined ROM/link validation and later
runtime acceptance.
