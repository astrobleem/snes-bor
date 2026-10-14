# Conditional early capacity admission — native acceptance

**BYOR_MOTU_CONDITIONAL_EARLY_CAPACITY_ADMISSION_PASS.** Both explicit acceptance budgets pass. Ordinary movement returns to 30 fields without the full predictor; the real 16->17 rescue retains its 69-field, 27.31% latency improvement. The certified renderer remains available byte-identically without the opt-in flag.

Success ROM: `out/byor-motu-conditional-capacity-success-v1/native/bor.sfc`
SHA256: `c4182ef4eda6c00dbfe5d1e93b56849f73221f31c3885aebd0763a217cd6ef9c`.
Ordinary ROM: `out/byor-motu-conditional-capacity-regression-v1/native/bor.sfc`
SHA256: `9ccbb5310ceb73f97ba6bdcfddfeeedb98f0378c448c8c0e98f543581c6ddeea`.

## Hypothesis and implementation

The retained native receipt confirms rescue free/actors/restorations = **124/96/30**, ordinary epoch 1 = **134/103/8**, and ordinary epoch 2 = **134/102/6**. The unconditional predictor cost 26.125015 and 26.034966 ms on the two ordinary epochs despite their conservative plans fitting. This caused the measured 30->32-field regression.

Only the opt-in `early_capacity.transform` renderer path changes. It now calls NbCapacityPressureGate before the unchanged exact capacity predictor. The gate reads existing tail reference words for slots 596..767, tests precisely `word & 3FFF == 0`, and increments existing transient DP $70. It returns skip immediately on finding the 129th free slot; exhausting the tail with 128 or fewer returns run. It clobbers A/X/$70; Y, source-world state, committed references and storage ownership are unchanged. No bitmap initialization, pending-map scan, record production, allocation, VRAM access or persistent allocation occurs in the gate.

Exact retry branches around both gate and predictor. A heuristic skip enters the original NbRestorePlan; it never bypasses NbFree bounds checks, the 48-record guard or the existing precise fallback. The 129 threshold is a workload heuristic, not a universal capacity proof.

The original unconditional transformation is retained as legacy_transform for strict historical ROM auditors and source reconstruction. Its emitted predictor is byte-for-byte unchanged. Older control auditors explicitly use that retained transform; the new candidate has its own exact-source/ROM audit rather than weakening a historical identity check. The existing `--early-capacity-admission` flag selects the conditional path and retains all backend dependencies.

## Native decisions and separate gate cost

| Source-owned case | Actual free slots | Gate count | Reference words read | Gate master clocks | Gate ms | Full predictor calls |
|---|---:|---:|---:|---:|---:|---:|
| Ordinary epoch 1 | 134 | 129 | 167 | 43,332 | 2.017575 | **0** |
| Ordinary epoch 2 | 134 | 129 | 167 | 43,332 | 2.017575 | **0** |
| Rescue epoch 17 | 124 | 124 | 172 | 43,694 | 2.034430 | **1** |

The actual free counts are independently checked from source-owned native refcount captures. Gate timers include JSR/RTS and are separate from full-predictor timing. Runtime observers confirm the entire 608-byte record/queue arena is unchanged across each gate call, no map read occurs, and all reference reads are inside the declared tail range. Both CPUs' storage writes remain guarded. Ordinary bitmap writes and predictor invocations are zero.

The rescue full predictor uses **591,490 clocks / 27.540279 ms**, reports **96 + 30 > 124**, and triggers exact retry before any conservative NbRestorePlan entry. There is exactly one gate call and one predictor call across both mark attempts. The original exact plan allocates **88 + 34 = 122** distinct slots, correctly restores all 34 identities, and commits the new source-owned picture. Two safe slots remain unreserved during preparation; 50 tail slots are free after old leases are released.

## Same native publication intervals

| Workload | Certified spill | Unconditional predictor | Conditional candidate |
|---|---:|---:|---:|
| Rescue fields | 95 | 69 | **69** |
| Rescue master clocks | 34,017,790 | 24,726,260 | **24,726,208** |
| Rescue ms | 1,583.897302 | 1,151.275744 | **1,151.273323** |
| Ordinary fields | 30 | 32 | **30** |
| Ordinary master clocks | 10,917,850 | 11,632,598 | **10,917,854** |
| Ordinary ms | 508.344403 | 541.623679 | **508.344589** |

Rescue meets <=70 fields and >=25% improvement: **27.313891%** faster than certified spill. Ordinary overhead is **four master clocks / 0.000186 ms / 0.0000366%**, with no extra field; the <=1% budget passes. Those four clocks are a measured difference, not a claim of instruction-level precision beyond this execution.

No CPU cost was excluded to meet the gate. Ordinary planning rises from 3,256,410 to 3,299,874 clocks; CPU preparation rises from 7,030,126 to 7,073,670 clocks. Waiting shrinks from 2,990,348 to 2,946,812 clocks, absorbing the roughly 2-ms gate cost in the retained publication schedule. Composition and DMA remain included in total publication. This is a bounded observed timing result, not a general cadence guarantee.

Rescue planning is **15,918,594 clocks / 741.183307 ms**, preparation through READY is 23,892,402 clocks, composition is 1,697,152 clocks (a subset), waits use 4,401,932 clocks, and all DMA fence intervals use 126,604 clocks. Costs and individual batch/fence intervals are included in the JSON receipt; overlapping intervals are not added as independent phases.

The rescue still uploads 122 paired tiles in 21 fresh VBlanks, including a final two-pair batch, followed by two 2,048-byte map transfers in a separate fresh VBlank. Minimum successful rescue batch margin is **34,260 clocks**; minimum across certified runs is **34,246**, exceeding the 10,000-clock requirement. Map commit completes in **35,116 clocks**, leaving **14,718 clocks** before active display. No warm forced blank occurs.

## Native threshold and safe-fallback probe

A separate cold-only diagnostic ROM executes the same candidate pressure gate and actual NbFree routine using controlled reference words. It is an instruction/branch test, not a synthetic source-world presentation. It backs up 344 tail-reference bytes in the dead queue at 003500..003657, temporarily uses the existing header word D61E as a diagnostic return flag, and restores every reference byte before original cold rendering. The gate itself still writes only DP $70. Both CPUs' writes to the temporary table/backup are audited; source services, artwork and persistent actor state are unchanged.

| Native controlled free count | Words read | Pressure decision | Actual full-predictor invocation |
|---|---:|---|---|
| 124 | 172 | Run | Yes |
| 128 | 172 | Run | Yes |
| 129 | **129** | Skip | No |
| 134 | **129** | Skip | No |

The probe uses high-bit flags C000 for free words and 8001 for occupied words, explicitly confirming the low-14-bit rule. It then requests **135 reservations with 134 free slots** after a heuristic skip. The actual unchanged NbFree makes 134 successful allocations, safely exhausts, sets EXACT_RETRY=1 and reaches the existing retry target. Repeating exhaustion with exact retry already set reaches the existing rejection target. Diagnostic target hooks record those branches and return to the probe; no synthetic frame is published. Real exact-retry dispatch and retention are independently verified by the source-owned rescue and fault runs.

Probe ROM: `out/byor-motu-pressure-unit-v4/native/bor.sfc`, SHA256 `2d8ed7dd8a307cac32573b21c8b679fdc36297eeba6959e3e3ddd7ea2fab3cf3`. The diagnostic has separately audited cold-call/return hooks and a measured zero-filled B000 helper lease. A diagnostic NOP separates the predictor-return and skipped-call labels so a shared address cannot falsely report an invocation. This extra code does not exist in either performance candidate.

## Exactness, faults and preservation

Real rescue plus LEFT verifies 80 fields; overflow-before-preload rollback 52; READY rollback 74; partial-queue rejection 72; stale-epoch rejection 74; ordinary READY rollback/movement/noop/LEFT 83; the separate threshold/fallback probe also verifies 83 subsequent genuine movement fields. Total: **518 visible fields / 29,704,192 RGB555 pixels / zero mismatches**.

Every visible field remains at brightness 15 and matches independent source composition. Whole physical VRAM is checked against complete DMA replay; pending READY pixels, palettes, committed maps, references and referenced CHR agree with controls. Unreferenced cross-run VRAM residue is recorded explicitly rather than treated as a referenced identity change. No displayed-reference CHR writes, stale queued transfers, unsafe PPU operations or resource faults occur. All six inherited graphics-free noops and the ordinary subpixel noop retain zero graphics work.

The candidate-specific ROM audit permits only the declared A000 transaction change, checks Poppy sizes/branch bytes/code placement, and enforces full equality elsewhere. The diagnostic has its own stricter declared mutation plan. The no-flag build reproduces certified spill SHA256 `05c3cef5f282113867b8dbc235e3bc72a7a718064023cbf58ff9bfc7410aa45d`. Original row/fused kernels, source assets, palettes, six-pair queue, 48-record capacity and source-world services are intact.

**147 focused tests pass. All 29 inherited dirty tracked files, including the protected 17, remain byte-identical.** No reset/stash/clean, master merge, unrelated rebuild or PCM duplication was used.

## Reproduction

```powershell
$env:PYTHONPATH='.;tools/bor_compile;tools/verify'
$env:MESEN_EXE='E:/gh/Mesen2-mcp-frameexact/bin/win-x64/Release/Mesen.exe'
python tools/verify/m4_conditional_capacity_fixture.py --output out/conditional-rescue-NEW
# Repeat fresh directories with --fault-mode 4, 1, 2 and 3.
python tools/verify/m4_opaque_component_native.py --output out/conditional-ordinary-NEW --warm --occupancy out/astra-occupancy-assets-v1 --tile-fusion --direct-pair-dma --rect-map-diff --nonblank-slice --nonblank-batch-rescue --nonblank-restore-spill --early-capacity-admission
python tools/verify/m4_pressure_gate_unit_native.py --output out/pressure-unit-NEW
python -m unittest test_m4_conditional_capacity test_early_capacity test_m4_early_capacity_component -v
# Re-certify this handoff's retained fields, native branches and exact budgets:
python tools/verify/m4_conditional_capacity_evidence.py
```

The same isolated NMI/audio/video/returning-worker configuration is retained. No general capacity improvement, 30 FPS, 200-Hz scheduling, SA-1 coexecution, audio scheduling, breath, HUD, combat or full Demo readiness claim. Stop at this accepted bounded conditional-admission milestone.
