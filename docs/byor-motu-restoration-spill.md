# Native restoration overflow capacity rescue

**BYOR_MOTU_NONBLANK_BATCH_CAPACITY_RESCUE_PASS.** Real source-controller epoch 16->17 now displays its new, source-exact picture without blanking. Conservative admission fails safely; foreground-aware retry succeeds. The certified six-pair queue and renderer kernels are unchanged.

Success candidate: `out/byor-motu-restore-spill-capacity-v2/native/bor.sfc`
SHA256: `cef4b429ff23d86d2daa352f7b73355b961dd7e5f5814d56e0857aa7d4d42034`.
Opt-in backend regression ROM: `out/byor-motu-restore-spill-regression-v1/native/bor.sfc`, SHA256 `05c3cef5f282113867b8dbc235e3bc72a7a718064023cbf58ff9bfc7410aa45d`.

The success fixture bootstraps actual source epochs 0..16 with the existing forced-blank renderer, then enables display. Authentic controller release selects IDLE at epoch 17. All 18 sealed snapshots match the retained source-world control byte-for-byte. The host requests steps, supplies controller inputs and reads evidence; it injects no actor state, graphics, maps or refcounts. Epoch 18 LEFT is rejected and retains epoch 17.

## Narrow integration and ownership

`--nonblank-restore-spill` requires the complete optimized batching backend. The supplied `restore_spill.transform` runs after batch rescue and its existing fault controls. Guard capacity rises from 32 to 48. Records 0..31 remain at 003480..0034FF; records 32..47 use 42D620..42D65F. Queue 003500..0036DF, metadata D660..D66D, exact-retry D674..D675 and composition scratch D680..D6CF are unchanged.

The spill lies within the already borrowed scalar CHUNK header, whose old restoration accesses were removed by batching. There is no source symbol in the spill range and no competing access in the retained batch assembly. Read-only physical BW-RAM callbacks observe writes from both CPUs beginning at boot. Only the native overflow store instructions write there: eight bytes for records 32 and 33. Native readback identifies homes 575 and 576 with destinations 676 and 677; all 34 produced restoration pairs match original immutable HIGH/LOW assets. This establishes writable ownership in the isolated fixture, not future concurrent SA-1 ownership. Existing queue, DP, character-conversion/stack guards remain active.

Candidate-specific auditors verify exact source transformations, actual Poppy instruction sizes, all relative branch ranges and bytes, code below bank-57 C000, and whole-ROM equality outside the declared transaction region. The additional capacity fixture changes only its initial source-epoch dispatch/brightness gate and a mode-4 preloading fault hook. Kernels, source services, palettes, art, D000/D400 code and all other banks remain byte-identical. The previous auditors and historical safe-rejection fixture are untouched. Building with spill disabled reproduces certified batch SHA256 `e710074d80cd6ad2354664956c7d0be867008c13a98006042f51d6fc9bd091ec`.

The first qualification run exposed an observer boundary error: Mesen reports the PC after a store, including the exact StoreDone address. That boundary was corrected, and the complete native run repeated with unchanged program bytes. No renderer substitution or safety exception was introduced.

## Capacity and exact native publication

| Native requirement | Conservative | Exact retry |
|---|---:|---:|
| Actor pairs | 96 | 88 |
| Genuine restoration identities | 30 | 34 |
| Reservations required | 126 | 122 |
| Safely unreferenced tail slots | 124 | 124 |
| Admission | Reject, retry before DMA | Success |

Exact filtering reveals additional restoration homes 529, 544, 575 and 576. The pending picture uses 122 distinct newly reserved slots; two safe slots remain unreserved during preparation. Successful commit releases the old frame's leases, leaving **50 free tail slots**, rather than retaining the old display's reservations indefinitely. The restoration list uses 34/48 records: 32 I-RAM records and two spill records (eight bytes).

There are 21 preload windows: twenty six-pair batches and one two-pair batch. All 244 CHR descriptors transfer 9,760 bytes from bank-00 queue sources into slots unreferenced by the old maps. Both planes complete before a pair is ready. Pending READY maps decode to the entire independent epoch-17 source RGB555 oracle before publication. A separate fresh VBlank commits both maps using two 2,048-byte descriptors, followed by RAM map/refcount ownership publication.

The old picture remains visible through every preparation/preload field. Every screenshot and full 64-KiB physical VRAM capture is independently checked against source pixels and an ordered complete DMA replay. No intervening black, partial or mixed component frame occurs. Brightness stays 15; unsafe PPU operations and resource faults are zero.

## Measured timing

Success transition: **95 fields**, **34,017,790 master clocks / 1,583.897302 ms**, from NbBegin through returned VISIBLE. This larger capacity-rescue transition includes two admission attempts; it is distinct from the preserved 30-field batching control.

| Interval | Master clocks | ms |
|---|---:|---:|
| Planning, both attempts | 25,318,764 | 1,178.863235 |
| Fused composition (subset) | 1,697,272 | 79.026431 |
| Preparation through READY | 33,183,900 | 1,545.070672 |
| All fresh-VBlank waits | 4,293,600 | 199.913676 |
| All DMA completion intervals | 126,668 | 5.897770 |
| CPU and other elapsed work, excluding waits/DMA | 29,597,522 | 1,378.085855 |
| Paired-map commit | 35,124 | 1.635403 |

These intervals overlap where identified; composition is included in preparation. Exact foreground-aware retry/admission dominates latency. No optimization beyond record storage was undertaken.

Minimum six-pair batch margin: **34,248 clocks / 1.594616 ms**, exceeding the 10,000-clock requirement. Map commit leaves **14,652 clocks / 0.682210 ms** before active display. All per-batch edges, descriptor fences and margins are recorded in the receipt. Warm forced-blank duration is zero. Initial bootstrap may blank. Legacy NMI/audio/video services and the returning graphics worker remain withdrawn under the retained isolated fixture; no authored audio or service-coexistence timing is certified.

## Native cases and regressions

| Case | Visible fields | Result |
|---|---:|---|
| Real 16->17 success plus LEFT | 106 | Exact new picture, non-blank commit |
| Mode 4: overflow written, before preload | 78 | Old VRAM/maps/refcounts retained, zero DMA |
| Mode 1: READY rollback | 100 | 122 pairs preloaded; old maps/refcounts/display retained |
| Mode 2: final partial queue deferred | 98 | 120 pairs complete; queued final two discarded, never READY |
| Mode 3: stale pending epoch | 100 | Never READY; old display retained, queue empty |
| Original batching transition with spill enabled | 83 | **30-field transition retained**, READY rollback/noop/LEFT pass |

Total: **565 visible fields, 32,399,360 RGB555 pixels, zero mismatches**. Each capacity case reboots the same audited ROM and constructs source epoch 16 naturally. All six inherited projected noops at epochs 3,5,7,11,12,13 perform zero tile composition and DMA. The ordinary batching regression also exercises a genuine new subpixel projected noop. Historical controls are verified by retained ROM identities, not unnecessarily rerun.

All eight supplied offline tests and **124 focused tests** pass. All 29 inherited dirty files, including the protected 17, remain byte-identical. No reset/stash/clean, unrelated rebuild, PCM copy or master merge was used.

## Reproduction

From the repository root, with retained PAK/assets, Poppy and Mesen:

```powershell
$env:PYTHONPATH='.;tools/bor_compile;tools/verify'
$env:MESEN_EXE='E:/gh/Mesen2-mcp-frameexact/bin/win-x64/Release/Mesen.exe'
python tools/verify/m4_restore_spill_capacity_native.py --output out/restore-spill-success-NEW
# Repeat fresh fixtures with --fault-mode 4, 1, 2 and 3.
python tools/verify/m4_opaque_component_native.py --output out/restore-spill-regression-NEW --warm --occupancy out/astra-occupancy-assets-v1 --tile-fusion --direct-pair-dma --rect-map-diff --nonblank-slice --nonblank-batch-rescue --nonblank-restore-spill
python -m unittest test_restore_spill test_m4_restore_spill_component -v
# Re-certify this handoff's retained screenshots, VRAM and DMA evidence:
python tools/verify/m4_restore_spill_evidence.py
```

Per-field screenshots/VRAM, native logs, sealed snapshots, READY map capture, restoration records and full events remain in each private output directory. The receipt contains per-field identities, per-case costs and every batch/fence. The original source-owned 32-record rejection remains reproducible through `m4_batch_capacity_native.py`.

No general scene/animation capacity, SA-1 coexecution, 30 FPS, 200-Hz scheduling, dynamic alpha, authored audio, breath, HUD, combat or complete MOTU Demo claim. Stop at this certified restoration capacity rescue.
