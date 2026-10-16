# Native shared-cell bitmap builder

This opt-in experiment installs Astra's supplied overlay on accepted commit `c028eff584f87de7ff2d67ea7a5c43701fd4e4dc`. It changes only the pinned `BhBitmapMapLoop` source block. For a committed raw backdrop home below 596 that exactly equals the pending raw word, one address/mask calculation inserts membership into both existing 76-byte bitmaps. Unequal homes and non-home committed words retain the original per-map behavior, including pending low-14-bit masking. The allocator, single-pass restoration resolver, bitmap representation, journal, source latch, uploader and compositor are unchanged.

Package: `motu_bitmap_shared_cells_c028eff.zip`, SHA256 `1a937123be4511aff9898bf5405a9818cf4e759675642d6ff080c88d00e0d6dc`. The archive was extracted privately into `out/byor-motu-bitmap-shared-package-v1`; README, `SOL_PROMPT.md` and manifest identities were checked. Only its five new Python files under `tools/` were installed. Existing files, including the repository README and accepted tests, were not overwritten.

## Native default measurements

| Interval | Accepted single-pass renderer: clocks / ms / fields | Shared-cell candidate: clocks / ms / fields |
|---|---:|---:|
| Epoch-3 bitmap construction | 1,407,502 / 65.534493 / — | 1,012,170 / 47.127498 / — |
| Epoch-3 BhPrepare | 1,926,876 / 89.716989 / — | 1,531,966 / 71.329643 / — |
| Epoch-3 restoration pass | 470,892 / 21.925133 / — | 470,892 / 21.925133 / — |
| Epoch-2 publication | 9,845,860 / 458.431635 / 27 | 9,845,860 / 458.431635 / 27 |
| Epoch-3 publication | 14,535,590 / 676.789462 / 40 | 14,178,234 / 660.150662 / 39 |

These are measured native master-clock intervals, converted at 21,477.270 clocks/ms. The offline synthetic instruction estimate is not used as a native timing claim. Bitmap construction is `BhBitmapLeaseBegin` through `BhBitmapBuilt` and is included in BhPrepare. BhPrepare runs from entry to its return-epilogue label, excluding caller JSR and final return epilogue as in the accepted baseline. Restoration runs from first `NbRestorePlan` entry to the actual completion/retry/abort boundary. Publication is the existing complete start-to-visible interval. These intervals overlap and must not be added together.

The actual native committed and pending maps contain **916 committed raw backdrop-home cells**, all **916** equal to the corresponding pending raw word. The shared branch therefore handles **916/916 = 100% of committed backdrop-home cells**, or **916/1,024 = 89.453125% of all map cells**. There are zero unequal committed-home cells; the other 108 cells have non-home committed words and retain the original pending path. These are full 1,024-word bitmap-input map counts, not visible-pixel counts or an assumed scene-wide ratio. Native execution callbacks count each branch, and the certifier independently recomputes those counts from captured native maps.

## Ownership and machine-code certification

Poppy and the independent instruction encoder agree on all 240 builder bytes, including 65816 opcode DF for indexed long CMP. The builder grows from 205 to 240 bytes; the helper ends at `$39B719`, safely below `$39C000`. The extra 35-byte ROM extension is checked zero-filled in the accepted ROM. All 297 branch sites pass the existing audit. The complete ROM comparison permits changes only in `$39B300..$39B718`; source services, original allocator, restoration code and all other ROM bytes are identical to the accepted single-pass ROM.

The overlay adds no RAM, VRAM, persistent state or stack frame. It uses only existing A/X and dead DP `$70/$78/$7A`; Y, DBR and DP remain unchanged. The bitmaps retain their existing 152-byte lease in the empty queue at `$003500..$003597`. All queue-empty, input-map/reference immutability, physical ownership, bitmap-lifetime and release-before-production guards remain active for both CPUs. No bitmap payload is uploaded as CHR. The original 48 restoration records, six-pair queue and immutable 20-byte source latch retain their ownership. The isolated-service and SA-1-reset configuration is unchanged; this is not SA-1 coexecution.

The real JOY1 UP movement retains the persistent actor, changes canonical epoch 2 to epoch 3, preserves the original latched epoch-2 commit and produces the same 1,816 changed RGB555 pixels. Exact allocation stays 95 actor tiles plus ten restorations, 64 tail reservations plus the same first 41 invalid homes, 105 total reservations and 639 final referenced physical slots. The transfer workload remains 105 pairs in 18 preload batches: 8,400 CHR bytes plus 4,096 map bytes, 212 DMA descriptors. There are no new default-path home invalidations.

## Adapter integration

The supplied collector expected inherited fingerprints at the accepted receipt's top level. The actual accepted single-pass receipt stores them at `handoff.inherited_dirty_files_preserved`. The new adapter now reads that exact location and requires all 29 entries before checking each SHA256. A regression test covers the actual nesting, missing scope and incorrect count. This is a receipt-schema correction only: the supplied source overlay, machine-byte executor and algorithm tests remain byte-identical to the archive. No existing test, historical auditor or compiler is changed, and no native/Lua fault is filtered.

The initial suite process had already loaded the original collector before this correction was saved, so its final aggregation raised the original KeyError after all eight native runs. Running the corrected `--collect-suite` rechecked the native results, raw-map-derived branch counts, source/maps/references, performance and preservation gates successfully. No native captures or ROM bytes were replaced.

## Certification

**BYOR_MOTU_BITMAP_SHARED_CELLS_PASS.** Eight native cases verify **800 continuously visible fields / 45,875,200 RGB555 pixels**, with zero mismatches, resource faults or unsafe operations. Brightness remains 15 throughout warm transactions. All source snapshots, completed maps, references and palettes match accepted controls. Supplemental checks compare every displayed map and referenced HIGH/LOW CHR pair at retained checkpoints byte-for-byte with those controls; full physical VRAM/DMA replay is checked against each run's own initial VRAM. Unreferenced power-on residue is not assumed identical between emulator instances.

| Case | Observed visible fields | Verified RGB555 pixels | Outcome |
|---|---:|---:|---|
| Default UP | 104 | 5,963,776 | Two different pictures; epoch 3 publishes in 39 fields |
| Valid home / later IDLE | 137 | 7,856,128 | Epoch 3 publishes in 40 fields; source-owned IDLE restores home 204 into tail 634 |
| Early rollback | 96 | 5,505,024 | Original display retained; valid-home restoration fenced |
| READY rollback | 104 | 5,963,776 | Original display/references retained |
| Partial queue | 102 | 5,849,088 | Incomplete transfers rejected; original display retained |
| Stale epoch | 104 | 5,963,776 | Original display retained |
| Insufficient budget | 83 | 4,759,552 | Rejected before any transaction-3 DMA |
| RIGHT control | 70 | 4,014,080 | Successful publication remains 27 fields; LEFT retention and projected noops pass |

All seven borrowing cases record the same map-derived 916 shared hits, zero unequal committed-home hits and 1,024 loop visits. The RIGHT control records zero bitmap work. Minimum complete-batch VBlank margin is **33,946 master clocks**, above the 10,000-clock requirement; the longest measured batch in the UP fixtures is 14,884 clocks. Default paired-map completion margins are **15,062 clocks** for epoch 2 and **14,690 clocks** for epoch 3. The suite minimum map-completion margin is **14,658 clocks** in the valid-home case. Separate HIGH/LOW transfer fences, paired readiness and fresh VBlank map commit all pass.

The native bitmap reduction is **28.087491%**. Default epoch-3 publication decreases **2.458490%** in master clocks and loses one field; epoch 2 remains exactly identical. The successful RIGHT publication remains **9,845,806 clocks / 27 fields**, identical to its control. The earlier rejected RIGHT trial is 20 clocks longer, without affecting the publication field. Later IDLE publication retains 27 fields with a measured 38-clock increase (0.001769 ms); this is reported rather than hidden by the main-case improvement. All specified publication budgets pass.

All **211 accepted focused tests** pass, including 76,800 reference comparisons. The original 13 new tests pass, with one additional receipt-schema regression making **14 new / 225 total focused tests**. Existing tests remain unchanged. All 29 inherited dirty tracked files, including the protected 17, retain their original SHA256s; the unrelated prompt-file deletion remains unstaged. Original/disabled build commands freshly reproduce the accepted single-pass, bitmap, home-borrow, safe-point and conditional hashes. Exact control commands, paths and hashes are in the receipt.

## Reproduction

Run screenshot cases serially from the repository root. Use a fresh output directory for a new suite.

```powershell
$env:PYTHONPATH='.;tools/bor_compile;tools/verify'
$env:MESEN_EXE='E:/gh/Mesen2-mcp-frameexact/bin/win-x64/Release/Mesen.exe'
python -m unittest test_home_bitmap_shared_cells test_m4_bitmap_shared_adapter -v
python tools/verify/m4_bitmap_shared_native.py --output out/byor-motu-bitmap-shared-NEW --suite
# Re-aggregate retained native evidence without executing another source step:
python tools/verify/m4_bitmap_shared_native.py --output out/byor-motu-bitmap-shared-v1 --collect-suite
```

The retained candidate is `out/byor-motu-bitmap-shared-v1/success/native/bor.sfc`, SHA256:

```text
04eba01445dbae69638ba0858c18aef28d0a0172e250deeb6099585acf88dc57
```

Native folders retain per-field screenshots and physical VRAM, source snapshots/oracles, unfiltered logs, branch counts, restoration/bitmap timing, slot reservations, DMA payloads and separate HIGH/LOW fences. The reproducible native aggregate is `out/byor-motu-bitmap-shared-v1/bitmap-shared-receipt.json`; the committed handoff is `docs/receipts/byor-motu-bitmap-shared-cells.json`.

No 30-FPS, 200-Hz scheduling, SA-1 coexecution, audio, HUD, combat or Demo claim. The measured default second publication still takes about 660 ms.

The accepted 211-test command is unchanged:

```powershell
python -m unittest test_restore_single_pass test_restore_single_pass_adapter test_home_borrow_bitmap test_home_borrow_bitmap_adapter test_m4_home_borrow test_m4_source_safepoint test_m4_conditional_capacity test_early_capacity test_m4_early_capacity_component test_restore_spill test_m4_restore_spill_component test_batch_rescue test_generated_splice test_m4_nonblank_batch_component test_m4_nonblank_component test_rect_map_opt test_m4_rect_map_component test_direct_pair_dma test_m4_direct_pair_component test_m4_native_cost_accounting test_tile_fusion test_m4_tile_fusion_component test_phase_occupancy test_m4_occupancy_component test_m4_opaque_component test_m4_online_component test_m4_live_ground_component test_component_live_bundle test_m4_component_publication test_bg_component_residency test_bg_component_deadlines test_bg_components -q
```

## Per-case native transaction intervals

Clocks / milliseconds / fields; rejected intervals end at abort rather than visible publication. Epoch 2 is the identical 9,845,860-clock / 27-field interval in each UP case. Full phase, DMA, bitmap, BhPrepare, restoration and source-event clocks remain in the machine-readable receipt.

| Case and epoch | Accepted | Candidate | Outcome |
|---|---:|---:|---|
| success, epoch 3 | 14,535,590 / 676.789462 / 40 | 14,178,234 / 660.150662 / 39 | published |
| valid, epoch 3 | 14,892,950 / 693.428448 / 41 | 14,535,588 / 676.789368 / 40 | published |
| valid, epoch 4 | 9,716,888 / 452.426589 / 27 | 9,716,926 / 452.428358 / 27 | published |
| early, epoch 3 | 11,557,302 / 538.117833 / 32 | 11,199,952 / 521.479313 / 31 | rejected; old image retained |
| ready, epoch 3 | 14,416,240 / 671.232424 / 40 | 14,058,870 / 654.592972 / 39 | rejected; old image retained |
| partial, epoch 3 | 13,701,484 / 637.952775 / 38 | 13,344,126 / 621.313882 / 37 | rejected; old image retained |
| stale, epoch 3 | 14,416,202 / 671.230655 / 40 | 14,058,840 / 654.591575 / 39 | rejected; old image retained |
| insufficient, epoch 3 | 6,835,782 / 318.279837 / 19 | 6,440,872 / 299.892491 / 18 | rejected; old image retained |
