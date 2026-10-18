# BYOR MOTU eighth-pair direct DMA

**Result: `BYOR_MOTU_EIGHT_PAIR_DIRECT_PASS`.**

The supplied queue generator is unchanged. The eighth pair uses the completed 80-byte BW-RAM compositor scratch directly at `$42D680/$42D6C0`; the first seven staging sources and the existing seventh record-buffer lease remain intact. Capacity eight is selected only for at most 12 completed restorations and fault mode other than 2. Mode 2 and larger record counts retain capacity six. The eighth slot is `$42D670`; capacity moves to `$42D676`, with exact retry at `$42D674` unchanged.

Candidate: `out/byor-motu-eight-direct-v8/success/native/bor.sfc`, SHA256 `4a696c9bc6d94e153188c6226744b3daf8ccfdb5301e943bf280f2697de129e9`. The unchanged Q7 builder freshly reproduces `c2b429e86171f68cdab639511da61fb5d1679d34fc6c2b9ae6cc23f41e7d2604` in `out/byor-motu-eight-direct-q7-control-v1/native/bor.sfc`.

## Native timing

| Publication | Accepted Q7 clocks / fields | Q8 clocks / fields | Clock reduction |
|---|---:|---:|---:|
| Epoch 2 | 9,131,176 / 25 | 8,416,382 / 23 | 7.828061% |
| Epoch 3 | 13,106,162 / 36 | 12,748,862 / 35 | 2.726199% |

Boundaries are the original start-to-visible native callbacks. At 21,477.270 master clocks/ms, epochs 2/3 take 391.873921/593.597883 ms. Overlapping preparation and publication intervals are not additive. RIGHT takes 23 publication fields versus 25 for Q7.

Minimum complete-batch VBlank margin across all cases: **27,310 clocks**. Minimum map-commit completion margin: **14,650 clocks**. Both exceed 10,000. Independent HIGH/LOW completion fences and the fresh map-commit VBlank remain required.

## Transfer and source proof

Epoch 3 retains 105 HIGH/LOW pairs, 8,400 CHR bytes, 4,096 map bytes and 212 descriptors, in **13 batches of eight plus one batch of one**. Exactly 13 eighth HIGH/LOW transfers use `$42D680/$42D6C0`. Admission scratch bytes, direct-call bytes and DMA packet payloads match exactly, with the slot and scratch frozen through both completion fences. No eighth I-RAM staging copy occurs.

The first seven HIGH sources remain `$003500,$003550,$0035A0,$0035F0,$003640,$003690,$0034B0`, with each LOW at HIGH+64. Full batches append `$42D680` and `$42D6C0`; the last one-pair batch uses `$003500/$003540`.

The genuine JOY1 UP preserves the epoch-2 latch and changes the persistent source actor from X=81, Z=220 to X=81, Z=219.75. Exactly 1,816 RGB555 pixels differ at epoch 3. Allocation remains 95 actor tiles, ten restorations, 64 tail reservations plus the first 41 invalid homes, and 639 final referenced slots. Valid home 204 restores into tail 634 in the subsequent source-owned IDLE transaction.

## Eight cases and independent verification

All eight cases pass: **706 visible fields / 40,484,864 RGB555 pixels**, zero mismatches, zero resource faults and zero unsafe PPU operations. Every visible screenshot and the full 64-KiB physical VRAM/DMA replay are checked against the original independent source oracles. All original rollback, stale/budget rejection, LEFT/noop, brightness and CPU ownership checks remain active.

| Case | Fields | Verified pixels |
|---|---:|---:|
| Default UP | 91 | 5,218,304 |
| Valid home / source IDLE | 120 | 6,881,280 |
| Early rollback | 85 | 4,874,240 |
| READY rollback | 91 | 5,218,304 |
| Partial queue | 93 | 5,332,992 |
| Stale epoch | 91 | 5,218,304 |
| Insufficient budget | 74 | 4,243,456 |
| RIGHT control | 61 | 3,497,984 |

## ROM audit and preservation

Transaction code ends at `$39A687`, up **23 bytes** from `$39A670`, below `$39B000`. All 302 branch sites pass. Whole-ROM comparison permits only the exact supplied overlay plus the following operand-only helper relink:

- `$39B5DF`: `jsr NbFlushQueue`, `$39A41F` to `$39A429`; opcode and all other helper bytes remain identical.

The bank-42 direct-DMA routine is byte-identical to accepted Q7. The experiment adds two metadata bytes without another RAM region, VRAM arena, persistent allocation, media regeneration or PCM copy. All 29 inherited fingerprints, including the protected 17, match their pinned SHA256s. The takeover snapshot of all current tracked changes also matches exactly, including the unrelated prompt-file deletion.

## Adapter corrections

- Pin Q7 observer rewriting to its four capacity reads and three capacity comparisons, retaining every write guard.
- Copy identical matched Mesen runtime binaries and effective settings into a private portable runtime; change only screenshot/save output paths.
- Seed private save data with the original bor.srm input verbatim and retain its SHA256; preserve the original settings and SRAM files.
- Guard D676/D677 writes by the two exact post-STA callback PCs, including the final store completion at Q7PolicyDone; keep SA-1 rejection.
- Normalize live integer and serialized string transaction keys before comparing all original borrowing-order fields.
- Read partial-mode policy tuples as (completed records, mode, capacity); require a nonempty mode-2/capacity-6 policy and no eighth transaction-3 transfer.

The capture probe uses the original MCP screenshot API and proves two paused captures leave CPU state and frame count unchanged. Private binary hashes match the selected frame-exact executable/DLL set. Source settings and SRAM hashes are unchanged. The original SRAM input hash is `a7574d35205ca9a5b724f78a6cc5d1a7f499b894892aae31dbfaa69902fa8fa1`; its byte-for-byte retained copy and source settings are under `out/byor-motu-eight-direct-integration-v1/capture-inputs`.

The original unfiltered v1-v7 failures are retained and excluded from certified totals. Version 8 captured all eight cases; corrected `--collect-suite` reran the original certifiers and every supplied aggregate gate without emulator advancement. No observer fault was suppressed.

## Tests and reproduction

**277 focused tests pass**: the accepted 247, all 24 supplied Q8 tests, and six added adapter regressions. The complete run followed native completion and re-certification. Its durable log/result are `out/byor-motu-eight-direct-integration-v1/focused-tests-v2.log` and `focused-tests-result-v2.json`. An earlier 263-test driver run omitted the separate 14-test bitmap-shared block and is explicitly excluded as the complete regression result.

PowerShell from the repository root; use a fresh native output directory and keep screenshot cases serial:

```powershell
$py='E:/gh/_snes-bor-eight-pair-task-20261018/Scripts/python.exe'
$env:PYTHONPATH='.;tools/bor_compile;tools/verify'
$env:MESEN_EXE='E:/gh/Mesen2-mcp-frameexact/bin/win-x64/Release/Mesen.exe'
& $py -B -m unittest test_eight_pair_direct test_m4_eight_pair_adapter -v
& $py -B tools/verify/m4_eight_pair_native.py --output out/byor-motu-eight-direct-NEW --suite
# Only after the eight native captures finish:
& $py -B tools/verify/m4_eight_pair_native.py --output out/byor-motu-eight-direct-NEW --collect-suite
& $py -B -m unittest test_restore_single_pass test_restore_single_pass_adapter test_home_borrow_bitmap test_home_borrow_bitmap_adapter test_m4_home_borrow test_m4_source_safepoint test_m4_conditional_capacity test_early_capacity test_m4_early_capacity_component test_restore_spill test_m4_restore_spill_component test_batch_rescue test_generated_splice test_m4_nonblank_batch_component test_m4_nonblank_component test_rect_map_opt test_m4_rect_map_component test_direct_pair_dma test_m4_direct_pair_component test_m4_native_cost_accounting test_tile_fusion test_m4_tile_fusion_component test_phase_occupancy test_m4_occupancy_component test_m4_opaque_component test_m4_online_component test_m4_live_ground_component test_component_live_bundle test_m4_component_publication test_bg_component_residency test_bg_component_deadlines test_bg_components test_home_bitmap_shared_cells test_m4_bitmap_shared_adapter test_seven_pair_spill test_seven_pair_adapter test_eight_pair_direct test_m4_eight_pair_adapter -q
& $py -B tools/verify/m4_seven_pair_native.py --output out/byor-motu-eight-direct-q7-control-NEW --build-only
```

The native runner creates a private portable capture runtime with byte-identical emulator binaries and a verbatim initial SRAM copy. The existing task venv installs NumPy 2.2.6/SciPy 1.15.3 locally and reuses existing Miniconda site packages; global Python and emulator settings are unchanged. The committed receipt contains exact source/config/binary/log hashes and all per-case native data.

## Epoch-3 batch detail

HIGH/LOW costs below are the eighth packet-to-DONE fence durations. Batch cost extends through `NbQueueDrainDone`; margins use the physical VBlank end. Full source lists and absolute start/end clocks are in the receipt.

| Batch | Pairs | Eighth HIGH source / clocks | Eighth LOW source / clocks | Complete batch clocks | Margin |
|---:|---:|---|---|---:|---:|
| 1 | 8 | `$42D680` / 566 | `$42D6C0` / 174 | 21,288 | 27,322 |
| 2 | 8 | `$42D680` / 558 | `$42D6C0` / 182 | 21,280 | 27,318 |
| 3 | 8 | `$42D680` / 558 | `$42D6C0` / 174 | 21,272 | 27,360 |
| 4 | 8 | `$42D680` / 566 | `$42D6C0` / 174 | 21,288 | 27,310 |
| 5 | 8 | `$42D680` / 558 | `$42D6C0` / 174 | 21,280 | 27,328 |
| 6 | 8 | `$42D680` / 558 | `$42D6C0` / 174 | 21,280 | 27,360 |
| 7 | 8 | `$42D680` / 558 | `$42D6C0` / 174 | 21,280 | 27,372 |
| 8 | 8 | `$42D680` / 558 | `$42D6C0` / 174 | 21,272 | 27,368 |
| 9 | 8 | `$42D680` / 558 | `$42D6C0` / 174 | 21,272 | 27,332 |
| 10 | 8 | `$42D680` / 558 | `$42D6C0` / 174 | 21,280 | 27,336 |
| 11 | 8 | `$42D680` / 558 | `$42D6C0` / 174 | 21,272 | 27,344 |
| 12 | 8 | `$42D680` / 558 | `$42D6C0` / 182 | 21,280 | 27,322 |
| 13 | 8 | `$42D680` / 558 | `$42D6C0` / 174 | 21,280 | 27,344 |
| 14 | 1 | — | — | 1,676 | 46,962 |

This completes only the bounded Q8 experiment. It does not establish 30 FPS, 200-Hz scheduling, SA-1 concurrency, audio, HUD, combat or a complete MOTU Demo.
