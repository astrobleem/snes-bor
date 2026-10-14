# Six-pair native VBlank batching and capacity rescue

**NONBLANK_BATCH_PASS_CAPACITY_PENDING**. Batching passes native correctness, ownership, hard VBlank margins and latency improvement. The prepared 32-record capacity rescue cannot admit actual epoch 17; it rejects safely.

Candidate: `out\byor-motu-batch-rescue-v1\native\bor.sfc`
SHA256: `e710074d80cd6ad2354664956c7d0be867008c13a98006042f51d6fc9bd091ec`

The authentic changed source-player picture appears after **30 fields instead of 120 (75% fewer)**. The main READY-rollback/movement/noop/LEFT run verifies 83 consecutive visible fields. Partial-queue and stale-epoch runs verify 81 and 83 fields. Real 16->17 capacity rejection verifies 75 further visible fields: **322 fields, 18,464,768 RGB555 pixels, zero mismatches**. The separate lease diagnostic also verifies the retained 261-field control. Brightness remains 15 after each cold bootstrap.

## Memory and source integration

All 15 supplied offline tests pass; the original retained-source splice audit recognizes the actual 01c8167 publisher.pasm. Native Poppy exposed one missing f-string prefix in the supplied queue-address emitter, which left a literal Python expression in assembly. The integration fixes that single spelling and tests that no unresolved braces survive generation. No algorithm or renderer kernel was replaced.

The opt-in --nonblank-batch-rescue requires warm, occupancy, tile fusion, direct-pair DMA, rectangle maps and nonblank-slice. It applies the supplied source transformation after nonblank_slice and adds only isolated native fault controls: mode 1 aborts READY, mode 2 deliberately defers the last short batch, and mode 3 makes the pending epoch stale. Normal mode 0 uses the supplied batching algorithm. The old nonblank ROM auditor and certifier are untouched.

I-RAM leases: 003480-0034FF for 32 restoration records; 003500-0036DF for six 80-byte pairs. Existing DP 3400-347F, worker code 3200-33FF, padding 36E0-36FF, character-conversion region 3700-377F and possible stack 3780-37FF stay clear. Metadata D660-D66D and retry marker D674-D675 remain inside the existing unused fused-renderer CHUNK lease. No new VRAM, OBJ, BW-RAM arena, asset or bank-zero allocation.

No source symbols name the proposed S-CPU lease. A cold-only diagnostic ROM then observes physical shared-I-RAM writes from both CPUs over original boot, source services and real controller movement: **zero prior or unexpected writes**. Native S-CPU writes and reads back all 608 canary bytes, maintained over **265 fields**. SIWP and CIWP both read 255 at the probe. Native bank-00 HIGH/LOW DMA into unreferenced slot 767 reads back the exact 80-byte canary payload. The diagnostic changes are a cold JSR and B000 helper, not a production graphics injection.

The lease is conditional on the retained isolated service ownership: the returning graphics worker is held, audio/video service writers are withdrawn, and producer NMI is disabled. No future SA-1 worker coexistence or authored audio budget is inferred. Candidate observers enforce the sole S-CPU A000-code writer over 480-6DF and observe both CPUs for padding/CC/stack writes. Their canaries remain intact.

The new strict ROM auditor checks the exact prepared splice plus declared fault hooks, actual Poppy statement addresses, code placement and emitted bytes; every ROM byte outside the experimental A000 region remains identical to nonblank-v5. Both original kernels, source services, palettes, art and original renderer code are unchanged. A fresh build without batching reproduces baseline SHA256 `9f85b14626405c06295536e65b6f73a229849a6b6bebf0b99862792035f6130f`.

## Native timing

| Successful transition cost | One-pair control ms | Six-pair ms |
|---|---:|---:|
| Planning | 150.904282 | 151.603905 |
| Fused composition (subset) | 92.693718 | 92.641569 |
| CPU preparation | 296.585087 | 327.292156 |
| Waiting | 1666.772360 | 139.272077 |
| CHR DMA fences | 3.779996 | 3.716673 |
| Begin through returned VISIBLE | 2005.881660 | 508.346824 |

The successful transition uploads 108 pairs / 8,640 CHR bytes in **18 six-pair windows**, then commits 4,096 map bytes in a separate fresh VBlank. READY rollback uploads 111 pairs / 8,880 bytes in 19 windows, including a final three-pair batch. Partial deferral completes only 108 pairs; its last three remain queued, fail the pre-READY empty-queue guard, and are discarded before the next request. LEFT and the exercised subpixel projected noop perform zero DMA.

Across all three runs, the smallest batch margin is **34,246 master clocks (1.594523 ms)** before active display, versus the required 10,000. Measured PPU VBlank spans 50,464 clocks; worst batch edge-through-last-LOW fence uses 16,218 clocks. Six pairs fit; no reduction to four was needed.

The main map commit uses **35,164 clocks**, with **15,076 clocks** of remaining VBlank margin. Native field edges, every descriptor payload, independent HIGH/LOW completion fences and every per-batch margin are in the JSON receipt. No timing instruction is inserted into the ROM.

CPU preparation and composition are not additive; composition is a subset. Queue copying increases CPU preparation relative to the one-pair control while removing most waiting. Publication remains a roughly half-second operation, not a 30-Hz claim.

## Exact pixels, transactions and DMA

Every captured visible field is source-oracle exact and brightness 15. Every full physical VRAM capture matches an ordered independent replay of actual native DMA payloads, and independent planar decoding matches source RGB555. Pending READY residency also reconstructs the source oracle before map publication. Queue descriptors use bank 00 sources 3500+80*i / 3540+80*i, exact 64/16-byte sizes, matching HIGH/LOW physical slots and completed fences. No displayed-reference CHR slot is overwritten.

All final partial batches flush before READY in normal mode. A queued-but-incomplete mode-2 transaction never reaches READY. Mode-3 stale generation likewise rejects before READY. Mode-1 READY rollback, mode-2 incomplete deferral, mode-3 stale rejection and unsupported LEFT retain committed maps, refcounts, palettes and pixels. Queue counts are zero at all completion/rollback checkpoints; subsequent valid movement reuses fresh queue contents. The exercised projected noop updates the source/display epoch without any graphics DMA. Six inherited noop controls remain reproducible by the byte-identical old backend.

## Real capacity result: the supplied 118-slot witness is incorrect

| Requirement at 16->17 | Conservative | Exact foreground filtering |
|---|---:|---:|
| Actor admissions | 96 | 88 |
| Backdrop restoration identities | 30 | **34** |
| Required reservations | 126 | **122** |
| Free tail slots | 124 | 124 |

Eight source-opaque tiles are fully foreground-occluded. Removing them reveals four additional overwritten backdrop homes: **529, 544, 575, 576**. Their actual HIGH/LOW physical contents differ from immutable home assets, so these are real restoration requirements, not stale flags. Exact filtering can fit 122 slots, but the proposed 32-record array cannot store its 34 restorations. Writing the extra records would overlap the queue; the guard correctly forbids it.

A separate audited fixture constructs epoch 16 by the genuine source-owned controller sequence while the initial scene remains blank. The host never injects player state, graphics, maps or refcounts. All 17 bootstrap snapshots and the released epoch-17 snapshot match retained source-world bytes. Once scene 16 becomes visible, every subsequent field is verified. The native conservative pass exhausts allocation and retries precise OnlineCoverage; the exact pass reaches the **32-record restoration guard and aborts**. Both attempts perform zero warm DMA. All 75 observed fields, physical VRAM, committed maps/refcounts and brightness remain unchanged, with an empty queue and retry marker 1.

This proves native retry execution and safe second-pass failure, **not successful native capacity rescue**. The reported classification stays pending. The next correction needs storage or safe reuse for those extra restoration identities; it is not implemented here.

## Reproduction

Use fresh private output directories from the repository root with retained PAK/assets and Poppy/Mesen installed.

```powershell
$env:PYTHONPATH='.;tools/bor_compile;tools/verify'
$env:MESEN_EXE='E:/gh/Mesen2-mcp-frameexact/bin/win-x64/Release/Mesen.exe'
python tools/verify/m4_batch_lease_audit.py --output out/byor-motu-batch-lease-NEW --build
python tools/verify/m4_batch_capacity_assets.py --output out/byor-motu-capacity-NEW.json
python tools/verify/m4_opaque_component_native.py --output out/byor-motu-batch-NEW --warm --occupancy out/astra-occupancy-assets-v1 --tile-fusion --direct-pair-dma --rect-map-diff --nonblank-slice --nonblank-batch-rescue --batch-fault-mode 1
# Repeat in fresh directories with --batch-fault-mode 2 and 3.
python tools/verify/m4_batch_capacity_native.py --output out/byor-motu-batch-capacity-NEW
python -m unittest test_batch_rescue test_generated_splice test_m4_nonblank_batch_component -v
```

The builder requires the retained lease PASS receipt at out/byor-motu-batch-lease-v1/result.json. A new lease run is independently reproducible; it does not silently substitute an unaudited ownership result.

**110 focused tests pass; all 29 inherited dirty files, including the protected 17, remain byte-identical.** Archive originals and diagnostic outputs are retained privately. No stash/reset/clean, master merge, unrelated build regeneration or PCM copies.

No joint BYOR_MOTU_NONBLANK_BATCH_RESCUE_PASS, 118-slot admission, general scene capacity, SA-1 migration/coexecution, 200-Hz scheduling, 30 FPS, authored audio, alpha expansion, breath, HUD, combat or full Demo claim. Stop at this measured batching result and precise capacity blocker.
