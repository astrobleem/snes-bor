# Native early-capacity predictor: measured tradeoff

**EARLY_CAPACITY_MEASURED_TRADEOFF — optimization acceptance withheld.** The supplied predictor is natively correct and substantially accelerates the constrained 16->17 rescue. It also slows the ordinary changing-frame path from 30 to 32 fields. The extra two fields / 6.55% publication latency is a material ordinary-path regression for this experiment. The certified backend remains unchanged and selectable without the new flag.

Success candidate: `out/byor-motu-early-capacity-success-v1/native/bor.sfc`
SHA256: `1360c3ba58776a36c44d4f34851461149c4ba0f811d42e08c1ed623743032a60`.
Ordinary candidate: `out/byor-motu-early-capacity-regression-v1/native/bor.sfc`
SHA256: `17ffad03865feace7b40e813f24ab28b20cfbbb5a4b5938377f5a8f92e6ededa`.

## Integration and memory certification

`--early-capacity-admission` requires restoration spill and the complete existing nonblank/batch backend. `early_capacity.transform` runs after the existing batch/fault/spill transforms. The predictor borrows 76 bytes of dead restoration-record storage at 003480..0034CB before any record exists. No new memory, VRAM, palette or OBJ allocation is added. The six-pair queue at 003500..0036DF, 48-record capacity, exact foreground predicate, allocator and paired-map commit are unchanged.

All six supplied offline tests pass, including 110 randomized whole-map/refcount cases. Actual retained assembly exposed a compatibility defect in the supplied contract check: its first global `sta.l D606` belongs to cold bootstrap, not NbBeginRetry. The integration scopes the reset check to the retry block and requires exactly one zero reset there. Tests reject a missing or nonzero retry reset. The supplied emitted predictor instructions are unchanged.

Poppy assembles both candidates. Separate candidate-specific auditors require the exact transformation, actual instruction sizes and every branch displacement/binary target, code below 39:C000, a zero-filled extension lease, and whole-ROM equality outside A000 transaction code. The old size auditor lacks DEY; the new auditor sizes its one-byte token and independently checks the actual opcode 88. Old auditors are unchanged. The success fixture ends at 39:A5BF (1,471 transaction bytes), well clear of C000 and the unchanged D000/D400 routines.

Native execution callbacks observe both CPUs' physical shared I-RAM writes. At predictor entry, record count, queue count and exact-retry marker are zero. During prediction all writes remain within 480..4CB, by the S-CPU predictor only. The rescue clears 76 bytes and updates 30 distinct home bits through 60 further byte writes: 136 observed bitmap writes. The ordinary successful path updates six homes: 88 byte writes. Record production begins only after prediction returns. Existing queue, spill, padding/character-conversion/stack guards remain active, with zero resource faults.

A build with the flag disabled reproduces the certified spill backend SHA256 `05c3cef5f282113867b8dbc235e3bc72a7a718064023cbf58ff9bfc7410aa45d`. Historical renderer, batching and capacity controls remain reproducible. No source-world, artwork, compositor-kernel or palette change was made.

## Actual source-owned capacity decision

The initial picture is constructed through genuine controller-driven source epochs 0..16, with initial forced blank permitted. Normal brightness begins at epoch 16. Controller release creates the real IDLE epoch-17 snapshot; all source snapshot bytes match the retained control.

Native predictor output: **124 free tail slots, 96 actor tiles, 30 distinct restoration homes**. It recognizes 126 > 124 and enters NbCapacityPredictedRetry with marker zero. The original NbRestorePlan is never entered on the conservative attempt. The marker becomes one and NbBeginRetry regenerates the pending mark with exact foreground-aware coverage. There are two mark attempts but only **one restoration/allocation attempt**.

The exact plan admits **88 actors + 34 genuine restorations = 122 distinct reservations**, leaving two safe slots during preparation. Homes 529, 544, 575 and 576 are correctly restored. After commit releases old leases, 50 tail slots are free. Both HIGH/LOW planes and the complete pending READY picture match independent source RGB555 composition.

## Paired native measurements

| Same workload | Certified spill | Early predictor | Change |
|---|---:|---:|---:|
| Rescue publication fields | 95 | **69** | -26 |
| Rescue publication ms | 1,583.897302 | **1,151.275744** | **-432.621558 (-27.31%)** |
| Rescue planning ms | 1,178.863235 | 739.126062 | -439.737173 |
| Rescue CPU/other, excluding waits/DMA, ms | 1,378.085855 | 938.377550 | -439.708306 |
| Ordinary publication fields | **30** | 32 | **+2** |
| Ordinary publication ms | **508.344403** | 541.623679 | **+33.279276 (+6.55%)** |
| Ordinary planning ms | 151.621226 | 177.662338 | +26.041112 |
| Ordinary CPU preparation ms | 327.328660 | 353.362322 | +26.033662 |

The ordinary baseline is the same certified spill ROM, not a sum of unrelated maxima. Its exact 508.344403-ms result is approximately the earlier 508.347-ms batching reference. CPU preparation and composition are overlapping intervals, not additive costs.

| Rescue interval | Actual master clocks | ms |
|---|---:|---:|
| Predictor call including JSR/RTS | 591,492 | 27.540372 |
| Complete planning | 15,874,410 | 739.126062 |
| Fused composition, included in preparation | 1,697,272 | 79.026431 |
| Preparation through READY | 23,892,372 | 1,112.449208 |
| All fresh-VBlank waits | 4,445,932 | 207.006384 |
| All DMA fence intervals | 126,540 | 5.891810 |
| Total through returned VISIBLE | 24,726,260 | 1,151.275744 |

Ordinary epoch 2 predictor: **559,160 clocks / 26.034966 ms**. Its total grows from 10,917,850 to 11,632,598 clocks. The precheck scans all 1,024 pending-map cells and 172 tail references on ordinary successful updates too; that measurable cost explains the regression. No further optimization or conditional-predictor redesign was undertaken.

Rescue uses 21 preload windows: twenty six-pair batches and one two-pair batch; 244 CHR descriptors / 9,760 bytes, followed by two map descriptors / 4,096 bytes in a separate fresh VBlank. Minimum rescue batch margin is **34,256 master clocks**, above the required 10,000; across all runs the minimum is **34,250**. Map commit takes 35,124 clocks and leaves 14,664 clocks before active display. Warm forced-blank duration is zero. CPU and transfer time are emulator-native measurements, not Python timing estimates.

## Pixel, DMA and rejection evidence

| Native case | Visible fields | Result |
|---|---:|---|
| Source-owned 16->17 success and LEFT | 80 | Nonblank new picture, exact retry before conservative allocation |
| Mode 4: overflow records written, before preload | 52 | Zero DMA; old maps/refcounts/display retained |
| Mode 1: READY rollback | 74 | Complete pending picture rejected, old display retained |
| Mode 2: final partial queue rejected | 72 | Never READY, queued two-pair remainder discarded |
| Mode 3: stale pending epoch | 74 | Never READY, old display retained |
| Ordinary deferred/success/noop/LEFT regression | 87 | Pixel-exact; successful transition now 32 fields |

**439 continuously visible fields / 25,174,016 RGB555 pixels / zero mismatches.** Brightness remains 15; all HIGH/LOW completion fences and map commits fit measured VBlank windows. Every field's screenshot and full physical VRAM capture is independently checked against source pixels and complete DMA replay. All six inherited projected noops and the ordinary subpixel noop remain graphics-free. Unsafe PPU operations and resource faults are zero.

Source snapshots, committed/pending maps, refcounts and referenced CHR contents match corresponding controls. Whole cross-run VRAM byte equality additionally encounters differing initial contents in unreferenced slots. After successful preload only the two unreserved slots (766/767) differ. These bytes are excluded only from cross-run identity comparison because they have zero references; each run's entire physical 64-KiB VRAM is still verified by independent DMA replay for every field. No cause is asserted for the initial unused contents.

**138 focused tests pass.** All 29 inherited dirty tracked files, including the protected 17, remain byte-identical. No reset/stash/clean, master merge, unrelated media rebuild or PCM duplication.

## Reproduction

From the repository root with retained assets, Poppy and Mesen:

```powershell
$env:PYTHONPATH='.;tools/bor_compile;tools/verify'
$env:MESEN_EXE='E:/gh/Mesen2-mcp-frameexact/bin/win-x64/Release/Mesen.exe'
python tools/verify/m4_early_capacity_fixture.py --output out/early-capacity-success-NEW
# Repeat fresh directories with --fault-mode 4, 1, 2 and 3.
python tools/verify/m4_opaque_component_native.py --output out/early-capacity-ordinary-NEW --warm --occupancy out/astra-occupancy-assets-v1 --tile-fusion --direct-pair-dma --rect-map-diff --nonblank-slice --nonblank-batch-rescue --nonblank-restore-spill --early-capacity-admission
python -m unittest test_early_capacity test_m4_early_capacity_component -v
# Independently re-certify this handoff's retained cases and paired measurements:
python tools/verify/m4_early_capacity_evidence.py
```

The receipt includes predictor counters/cycles, all batch/fence timings, field identities, cross-run unreferenced residue and exact paired publication measurements. Screenshots, physical VRAM, native logs, source snapshots and READY-map captures remain in the private case directories.

**No BYOR_MOTU_EARLY_CAPACITY_ADMISSION_PASS:** the ordinary-path regression fails the acceptance condition. This is a selectable, verified experiment; the certified backend remains the reference. No general capacity, 30 FPS, 200-Hz scheduling, SA-1 coexecution, authored audio, breath, HUD, combat or full Demo claim. Stop after reporting this tradeoff.
