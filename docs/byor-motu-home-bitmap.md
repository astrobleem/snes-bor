# Native home-borrow bitmap planner

The opt-in bitmap adapter retains the accepted home-borrow allocator and replaces its repeated per-candidate map searches with Astra's exact membership indexes. The existing compiler, historical auditors, artwork, source movement, journal, invalidation, rollback, latch, compositor and uploader are unchanged.

The package is `motu_home_borrow_bitmap_836e8a9.zip`, SHA256 `945f83323a8658ebed6f962a4de392b8508b479a40fa2e287c6fa2f013db9472`, extracted into `out/byor-motu-home-bitmap-package-v1`. Its instruction file is named `SOL_PROMPT.md`; there is no `SOL_TASK.md` in this archive. Both that instruction file and README were read.

## Native timing boundaries

The comparison uses the accepted `836e8a9` receipt and the same real source sequence. Clock conversion is 21,477.270 master clocks/ms.

| Interval | Accepted planner: clocks / ms / fields | Bitmap candidate: clocks / ms / fields |
|---|---:|---:|
| Epoch-3 BhPrepare | 17,991,078 / 837.679929 / — | 1,927,298 / 89.736638 / — |
| Bitmap initialization and two map passes | — | 1,407,502 / 65.534493 / — |
| Epoch-2 publication | 11,632,626 / 541.624983 / 32 | 11,632,626 / 541.624983 / 32 |
| Epoch-3 publication | 33,833,446 / 1,575.314088 / 94 | 17,751,938 / 826.545366 / 49 |

BhPrepare is measured from its entry through the `BhPrepareOK` epilogue label, matching the baseline; caller JSR and final return epilogue are excluded. Bitmap timing is `BhBitmapLeaseBegin` through `BhBitmapBuilt`, covering initialization and the map passes. Entry guards and final return are outside that subinterval and included in BhPrepare/publication. These are nested intervals and must not be added. Publication includes the full existing request-to-visible interval, including waits and source safe-point work. Native BhPrepare decreases 89.287%; epoch-3 publication decreases 47.531%. The offline instruction estimate is not used as native timing.

## Ownership and exactness

The two 76-byte indexes occupy `$003500..$003597` only while the six-pair queue is empty. Queue count, pair completion and journal state are checked before the lease. The index is built after restoration reroutes, with one 1,024-word pass over each actual native input map. Committed membership uses raw words; pending membership uses low 14 bits. Both maps and the reference directory are frozen until `BhPrepareOK`/`BhPrepareBad` releases the index, before allocation, queue production, DMA or source movement. Both CPUs retain their physical write guards. The S-CPU queue exception permits only builder PCs and the 152 borrowed bytes under the empty-queue/state guards; SA-1 remains prohibited. The observer independently reconstructs every bitmap from the captured native maps and rejects live-lease mutation, rescans and queue use.

Poppy places the helper at `$39B300..$39B6F5`, ending `$39B6F6`: 1,014 bytes, 189 bytes larger than the accepted helper. The whole-ROM auditor retains the established authorized code ranges and requires all other bytes identical, including source services and both opaque kernels. No persistent RAM or VRAM allocation is added. Source physics, source latch, restoration records and the journal are outside the bitmap lease. The isolated service configuration and SA-1 reset ownership remain those of the accepted fixture.

The successful second picture uses 95 actor tiles and 10 backdrop restorations: 64 tail reservations and these first 41 invalid homes, in unchanged order:

```text
297 298 299 327 328 329 356 357 358 359 360 361 387 388 389
390 391 392 393 417 418 419 420 421 422 423 512 513 514 524
525 526 529 530 544 545 550 552 574 575 576
```

There are 105 total reservations and 639 final referenced physical slots; the default path creates no new immutable-home invalidations. Epoch 3 still differs from epoch 2 by 1,816 RGB555 pixels. It uploads 105 pairs in 18 preload batches: 8,400 CHR bytes plus 4,096 map bytes, 212 DMA descriptors. Full HIGH/LOW fences, physical VRAM replay and fresh VBlank map commit remain mandatory. Each continuously visible field is checked independently against source composition, with brightness 15 throughout warm operation.

## Integration correction and controls

The first build assembled and passed the ROM auditor but stopped before launching Mesen because the supplied adapter expected `ONLINE_OBSERVER_BEGIN`. The actual retained bootstrap uses `NONBLANK_OBSERVER_BEGIN`. Only the new adapter's fail-closed extraction marker was corrected, with a new regression test requiring exactly one marker. The planner itself, restricted machine-byte executor and reference source remain byte-identical to the ZIP. No fault log is filtered. The abandoned pre-execution attempt remains at `out/byor-motu-home-bitmap-v1`; certified native runs use `out/byor-motu-home-bitmap-v2`.

Fresh unchanged build commands reproduce:

| Control output under `out/` | SHA256 |
|---|---|
| `byor-motu-home-bitmap-original-v1/native/bor.sfc` | `061c574cb37a0d8dfabe731bb1fb8685610a091ec3b7d48fdb46ed9aabf38fda` |
| `byor-motu-home-bitmap-disabled-sp-v1/native/bor.sfc` | `7cf213a9aaa467c7c1248dc0e40d35027f8dbd56a6ac3e9f81d373d216cc431b` |
| `byor-motu-home-bitmap-disabled-conditional-v1/native/bor.sfc` | `9ccbb5310ceb73f97ba6bdcfddfeeedb98f0378c448c8c0e98f543581c6ddeea` |

The candidate ROM is `out/byor-motu-home-bitmap-v2/success/native/bor.sfc`, SHA256 `487be884b06db56ad3755feb5a3549b85837f0965d58459d0949ab3b0f92a52d`.

## Certification

**BYOR_MOTU_HOME_BORROW_BITMAP_PASS.** All eight serial native cases use the same candidate ROM. They verify 968 continuously visible fields / 55,508,992 RGB555 pixels, with zero mismatches, resource faults or unsafe PPU operations. Brightness stays 15 after bootstrap. Seven borrowing plans each execute exactly one 1,024-word pass per map; the RIGHT control executes none. The ordinary/conservative and tails-sufficient calls also execute no bitmap work. The queue remains empty for each complete bitmap lifetime, and no index bytes are uploaded as tile payload.

| Native case | Fields | Independently verified pixels | Outcome |
|---|---:|---:|---|
| Default UP success | 126 | 7,225,344 | Both distinct pictures published |
| Valid home and later IDLE | 166 | 9,519,104 | Home 204 borrowed; source-owned IDLE restores its immutable artwork into safe tail 634 |
| Early rollback | 117 | 6,709,248 | Prior picture retained; valid-home restoration fenced |
| READY rollback | 125 | 7,168,000 | Prior picture retained |
| Partial queue | 123 | 7,053,312 | Prior picture retained; incomplete queue discarded |
| Stale epoch | 125 | 7,168,000 | Prior picture retained |
| Insufficient budget | 104 | 5,963,776 | Rejected before any transaction-3 DMA |
| RIGHT control | 82 | 4,702,208 | Original safe-point, LEFT retention and projected noop pass; publication remains 32 fields with identical native transaction costs |

Minimum complete-batch VBlank margin is **33,950 clocks** across the suite; maximum observed complete-batch duration in the default run is 14,884 clocks. Default map-commit completion margins are 15,110 clocks for epoch 2 and 14,694 for epoch 3. The suite's smallest map-completion margin is 14,666 clocks in the valid-home epoch-3 case. These are newly measured margins, not inherited estimates. Full per-batch timings, separate HIGH/LOW DMA fences and all map completion margins are in the receipt. Independent physical replay covers all 64 KiB at checkpoints and every visible field.

All 162 inherited focused tests pass, including 76,800 reference comparisons. The 21 supplied tests pass; the final suite has 22 tests after adding the bootstrap-marker regression, for **184 passing focused tests** in total. Test logs and SHA256 identities are retained in the package scratch directory and receipt. All 29 inherited dirty tracked files, including the protected 17, retain their original byte fingerprints. The unrelated prompt-file deletion remains unstaged. Only the new implementation, tests, reference, findings and receipt are committed.

## Reproduction

Run serially from the repository root; substitute a fresh output directory for a new suite.

```powershell
$env:PYTHONPATH='.;tools/bor_compile;tools/verify'
$env:MESEN_EXE='E:/gh/Mesen2-mcp-frameexact/bin/win-x64/Release/Mesen.exe'
python -m unittest test_home_borrow_bitmap test_home_borrow_bitmap_adapter -v
python tools/verify/m4_home_borrow_bitmap_native.py --output out/byor-motu-home-bitmap-NEW --suite
# Re-certify an existing non-RIGHT case without executing it again:
python tools/verify/m4_home_borrow_bitmap_native.py --output out/byor-motu-home-bitmap-v2/success --collect
# Aggregate the retained eight-case native evidence and enforce acceptance gates:
python tools/verify/m4_home_borrow_bitmap_evidence.py
```

The suite runs default success, valid-home/later-IDLE restoration, early rollback, READY rollback, partial queue, stale epoch, insufficient budget and RIGHT control. It reuses strict existing certifiers through candidate-specific adapters. Native folders retain screenshots and full VRAM for every field, source snapshots and oracles, full Lua logs, DMA payloads/fences and bitmap membership/lifetime evidence. Initial/unreferenced VRAM power-on residue differs between emulator instances; every referenced CHR pair and displayed map is compared byte-for-byte with its accepted control, and complete physical replay is checked against each run's own captured initial VRAM. The successful final epoch-3 VRAM also matches all 65,536 baseline bytes. The machine-readable handoff is `docs/receipts/byor-motu-home-bitmap.json`.

No 30-FPS, 200-Hz world scheduling, general capacity, SA-1 coexecution, authored audio, HUD, combat or MOTU Demo claim. The measured second publication still takes roughly 827 ms; this change removes redundant planning scans and does not establish gameplay cadence.

The inherited focused command (162 tests) is:

```powershell
python -m unittest test_m4_home_borrow test_m4_source_safepoint test_m4_conditional_capacity test_early_capacity test_m4_early_capacity_component test_restore_spill test_m4_restore_spill_component test_batch_rescue test_generated_splice test_m4_nonblank_batch_component test_m4_nonblank_component test_rect_map_opt test_m4_rect_map_component test_direct_pair_dma test_m4_direct_pair_component test_m4_native_cost_accounting test_tile_fusion test_m4_tile_fusion_component test_phase_occupancy test_m4_occupancy_component test_m4_opaque_component test_m4_online_component test_m4_live_ground_component test_component_live_bundle test_m4_component_publication test_bg_component_residency test_bg_component_deadlines test_bg_components -q
```

The original build command is unchanged:

```powershell
python tools/verify/m4_opaque_component_native.py --output out/home-bitmap-original-NEW --warm --occupancy out/astra-occupancy-assets-v1 --tile-fusion --direct-pair-dma --rect-map-diff --nonblank-slice --nonblank-batch-rescue --nonblank-restore-spill --early-capacity-admission --source-safepoint --nonblank-home-borrow --build-only
# Omit --nonblank-home-borrow for the accepted safe-point control.
# Omit --source-safepoint as well for the accepted conditional-capacity control.
```
