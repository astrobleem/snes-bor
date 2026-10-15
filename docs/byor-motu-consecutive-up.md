# Consecutive changing-picture UP experiment — capacity blocked

**BYOR_MOTU_CONSECUTIVE_CHANGING_PUBLICATION_BLOCKED**

Starting/retained commit: `dd10d752bddb081e6b536cb0b0c75c9b904d9c44`.
No renderer changes were made. The native ROM is byte-identical to the accepted source READY safe-point candidate:

`out/byor-motu-consecutive-up-v2/native/bor.sfc`

SHA256: `7cf213a9aaa467c7c1248dc0e40d35027f8dbd56a6ac3e9f81d373d216cc431b`.

The authentic UP transition is supported and visibly different. The second picture cannot be admitted by the current allocator while retaining the first picture: **105 required tail slots versus 64 free, a deficit of 41**. Stop here; no capacity expansion, alternative actor state, residency reset or allocator change was attempted.

## Source validation

The driver queues real JOY1 UP while epoch 2 is being prepared. The unchanged READY wrapper invokes the original source controller/history/ground/frame/velocity/check_move/snapshot-seal implementation. Native controller evidence records `$0800`, not a host-written source event. Exactly one movement runs inside the graphics transaction.

Persistent actor `$414000`, X **81 → 81**, Z **220 → 219.75**, canonical epoch **2 → 3**. The adapter projects fractional Z to integer screen Y **220 → 219**. Source composition resolves `He_Man`, WALK, authored frame 0, direction 1; the native artwork guards also admit the second request into `NbBegin`. The source epoch-3 oracle differs from epoch 2 by **1,816 RGB555 pixels**. No artwork admission was bypassed.

| Identity | Epoch 2 | Epoch 3 |
|---|---|---|
| Snapshot SHA256 | `9c590346903387b0f96080d9f0625f2fc04f2ca8f61780ce4b085223d9afc3c8` | `e9ba9648514c05b8921d756caaa23c28692a476c5e807b245bbeb043457c24f7` |
| RGB555 SHA256 | `66b9758e9bc9f003e3e021d077edd519830369bb4d6dbcb2a4c22fd38b752ffc` | `ce2b25bd924909bbba6fa85541c2e4639b8de8ee3d6118b34a83eca966271feb` |

The 146-byte snapshots differ at byte offsets 61, 62, 104, 118, 121, 122, 123 and 144. Source composition and the movement delta are checked before requesting presentation of epoch 3. The host supplies controller input and command words, captures snapshots and calculates independent expected images; it never changes actor state or injects graphics.

## Actual native ordering

| Event | Master clock | Field |
|---|---:|---:|
| Epoch-2 `NbBegin` | 200,481,846 | 561 |
| Epoch-2 READY | 210,582,216 | 589 |
| Original epoch-2 latch sealed | 210,583,332 | 589 |
| Real source UP starts | 210,846,036 | 590 |
| Source UP completes, canonical epoch 3 | 211,263,204 | 591 |
| Epoch-2 map commit | 211,510,452 | 592 |
| Epoch-2 published/visible | 212,114,478 | 593 |
| `SpRenderCurrent` invokes `OnlinePublish` | 212,940,398 | 596 |
| Epoch-3 `NbBegin` | 212,946,378 | 596 |
| Conservative prediction rejects; exact retry | 214,188,368 | 599 |
| Exact allocator exhausted | 221,013,376 | 618 |
| Epoch-3 transaction aborts | 221,013,400 | 618 |
| Reject returns | 221,123,426 | 618 |

The original epoch-2 visual key matches the immutable latch at the first commit, although the canonical source is already epoch 3. P/A/X/Y/DP/DBR/SP restoration and the existing source/graphics ownership watchers pass. No DMA overlaps the source operation. `SpRenderCurrent` executes no further movement and does enter a changing graphics transaction; it is not a projected noop. It cannot reach PRELOADING, READY, COMMITTING or VISIBLE.

UP costs **417,168 master clocks / 19.423698 ms**. The first publication takes **32 fields / 541.625262 ms**, measured `NbBegin → NbVisible`. The second attempt takes **8,177,048 clocks / 380.730326 ms** from `NbBegin` to `OnlineReject`. There is no second publication latency or successful second publication field count.

## Capacity and rollback evidence

Native callbacks capture actual pending map and physical refcount bytes at both admission passes. The certifier independently recounts free slots, actor markers and distinct invalid backdrop homes from those captured bytes; it also records every `NbFreeFound` reservation.

| Plan | Free tail slots | Actor tiles | Restoration homes | Required | Deficit | Actual reservations |
|---|---:|---:|---:|---:|---:|---:|
| First successful epoch 2 | 134 | 102 | 6 | 108 | 0 | 108 |
| Second conservative epoch 3 | 64 | 100 | 8 | 108 | 44 | 0 |
| Second exact epoch 3 | 64 | 95 | 10 | 105 | **41** | 64 |

The pressure gate invokes the predictor with 64 free slots; it switches directly to the existing exact retry before conservative restoration allocation. The exact planner reserves 10 restoration slots, then 54 of the 95 actor slots, exhausting all 64 unreferenced tail slots. Every reservation belongs to the captured free set and is unique within its attempt. No physical residency was discarded or manufactured.

Exact restoration homes: **417, 418, 423, 514, 530, 552, 574, 575, 576, 584**. The conservative pass has 8 homes (omitting 574 and 575). The 48-record limit is sufficient; the failure is available tile-pair capacity in the existing tail-only allocator. This is not a universal hardware memory lower bound or a claim about a different allocator.

The second attempt performs **zero composition tiles, preload batches, DMA descriptors and DMA bytes**. After failure, physical VRAM, palette, pending map, committed map and complete refcount bytes are identical to the first committed picture. The queue is empty and its tile metadata is unchanged. Only the expected transient exact-retry word at `$42D674` changes from 0 to 1. Canonical epoch remains 3 and displayed epoch remains 2. A separately injected second READY rollback is not executed because this source state cannot reach READY; the natural second-transaction capacity failure demonstrates retention before preloading. The earlier READY rollback remains exercised by the retained first deferred transaction.

The first successful publication transfers **108 tile pairs / 8,640 CHR bytes**, in **18 six-pair batches**, plus **4,096 map bytes**. Its 218 DMA descriptors are replayed independently. Minimum batch VBlank margin is **34,246 clocks**; paired-map commit is **35,164 clocks**, ending **15,056 clocks** before active display resumes. No referenced CHR is overwritten.

## Verification and preservation

All **99 observed visible fields / 5,677,056 RGB555 pixels** match independent source composition with **zero mismatches**, continuous brightness 15 and no warm blank. The certifier reopens every screenshot, recomposes the original source snapshots, decodes each full physical VRAM capture, and checks ordered complete DMA replay, queue fences and current-map refcounts. Resource faults and unsafe PPU operations are zero.

The candidate-specific certifier reuses the original batch certifier with only its checkpoint manifest adapted to this experiment (`cold`, `deferred`, `moved`, `after-second`). Its no-DMA-on-rejection, referenced-slot, map/refcount, palette, per-field replay and VBlank requirements remain intact. The original auditors and native drivers are unchanged.

**153 inherited focused tests pass** (including the accepted safe-point tests; 76,800 reference comparisons). The prior RIGHT native proof is re-certified successfully: 82 fields / 4,702,208 pixels. Its original renderer and rejection fixtures remain reproducible. The flag-disabled conditional ROM still hashes to `9ccbb5310ceb73f97ba6bdcfddfeeedb98f0378c448c8c0e98f543581c6ddeea`. All 29 inherited dirty tracked files, including the protected 17, remain byte-identical. No tracked renderer, continuation state, artwork or source service file was modified.

The BLOCKED diagnostic, receipt and native artifacts are retained locally. No implementation commit or push is made because the user conditioned delivery on success; local and remote feature tips remain the accepted `dd10d752bddb081e6b536cb0b0c75c9b904d9c44`.

## Reproduction

```powershell
$env:PYTHONPATH='.;tools/bor_compile;tools/verify'
$env:MESEN_EXE='E:/gh/Mesen2-mcp-frameexact/bin/win-x64/Release/Mesen.exe'
python tools/verify/m4_consecutive_up_native.py --output out/consecutive-UP-NEW
# Re-certify the retained native run without starting the emulator:
python tools/verify/m4_consecutive_up_native.py --output out/byor-motu-consecutive-up-v2 --certify-existing
python -m unittest test_m4_source_safepoint test_m4_conditional_capacity -q
```

Machine-readable receipt: `docs/receipts/byor-motu-consecutive-up.json`. Native snapshots, source-composed RGB555 oracles, every-field screenshots/VRAM captures, plans, reservations, physical DMA payloads, fences and event clocks are retained under `out/byor-motu-consecutive-up-v2`.

No claim of two consecutive changing publications, continuous rendering, 30 FPS, full scheduling, 200-Hz updates, SA-1 concurrency, authored audio, combat, HUD or Demo readiness. Stop at the measured 41-slot capacity blocker.
