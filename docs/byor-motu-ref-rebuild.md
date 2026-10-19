# MOTU bank-local reference rebuild

Result: `BYOR_MOTU_REF_REBUILD_PASS`. All **408 focused tests** and eight native
cases pass. Local review changes from accepted `d5803ef7d9ede527a9eeb8f47a8779072fd92775`.
Validation completed locally before publication of this checkpoint.

The same original `NbMapsComplete` to `NbVisible` epoch-3 interval falls from
**569,326 to 453,628 SNES master clocks**:
**20.321925%**, saving 115,698 clocks / 5.386998 ms.
Every captured publication improves across the same two markers. The collector
requires at least 20% success epoch-3 post-map improvement, strict improvement
for every transaction and improved epoch clocks without a field regression.

| Original start-to-visible boundary | Accepted READY | Reference rebuild |
|---|---:|---:|
| Epoch 2 clocks / fields | 8,059,110 / 22 | 7,943,412 / 22 |
| Epoch 2 ms | 375.239032 | 369.852034 |
| Epoch 3 clocks / fields | 11,319,340 / 31 | 11,203,624 / 31 |
| Epoch 3 ms | 527.038120 | 521.650284 |

The retained profile attributed 457,738 root clocks to the old clear/recount
loops. That profile uses different boundaries; it is not subtracted from the
new helper measurements. No baseline emulator profiling was repeated.

The helper temporarily sets DBR to $42, uses bank-local reads/writes, and
unrolls both loops in groups of sixteen. It clears all 768 reference words to
their bit-15 ownership flag and recounts every one of the 1,024 committed map
slots in the original order. Native entry/exit snapshots independently check
all words, all **3,584 byte writes**, map identity, registers and status. DP,
DBR, stack pointer and the original counter remain preserved. Three temporary
bytes on the existing S-CPU stack are balanced before the continuation. The final original
CPY status is restored after PLB; decimal, interrupt, width and overflow flags
retain the original behavior. Both CPUs have reference-writer ownership guards;
SA-1 remains reset in this fixture.

The helper occupies `$39A900..$39AAB2` (435 bytes) in a checked zero gap. Only
the three-byte dispatch and helper range may change; all original symbols,
guards, other helpers, RAM leases, queue limits, assets and DMA routines remain
fixed. Independent literal bytes and all **316 branch sites** match Poppy.
The disabled build reproduces accepted READY ROM `ad04ee314d72a45c5f8785ea749decf612ae974af0366c0eb9bf48e57f724c00`.

Eight native cases verify **666 consecutive observed fields /
38,191,104 exact RGB555 pixels** with zero mismatches,
resource faults or unsafe PPU operations. Checkpoints, allocation/reference
snapshots and physically referenced tile identities match accepted READY.

| Case | Fields | Verified RGB555 pixels |
|---|---:|---:|
| success | 86 | 4,931,584 |
| valid | 113 | 6,479,872 |
| early | 80 | 4,587,520 |
| ready | 85 | 4,874,240 |
| partial | 88 | 5,046,272 |
| stale | 85 | 4,874,240 |
| insufficient | 69 | 3,956,736 |
| right | 60 | 3,440,640 |

The workload and six-pair partial fallback remain unchanged: 95 actor tiles,
ten restorations, 64 tails, 41 borrowed homes, 639 referenced slots, 105 pairs,
8,400 CHR bytes, 4,096 map bytes and 212 descriptors. Valid home 204 still
restores to tail 634 through source-owned IDLE; insufficient budget performs
no request-3 DMA. Minimum complete-batch margin is **27,318 clocks**;
minimum map-commit margin is **14,646**, both above the unchanged 10,000 floor.

The first eight-word-unroll candidate passed correctness but its 19.869108% gain
missed the required 20% gate. Its five source snapshots, static build, native
captures, failed collector log and seal remain under the v1/integration paths.
The retained sixteen-word version uses fresh v2 builds and native captures.

The earlier gate `PermissionError(errno=13)` was ordinary lease contention:
an intentionally held local lock reproduced it, then the existing shared gate
was acquired/released read-only and both suites acquired it normally. Each
wrapper holds byte 0 for the entire serial suite and releases it in `finally`.
Coordination messages were delivered to Windows packaging task
`01a1477a-760e-76cd-b39a-f069dfaa20d8`. No gate bytes, shared emulator settings
or unrelated processes were changed; there was no gate bypass.

All 77 preservation controls, inherited edits, absent prompt, 1,055 older raw
inputs and the accepted fused/READY sealed captures remain unchanged. Mesen
binaries match their source hashes; only six private output paths differ.
The original SRAM seed remains bound to the accepted receipt, and private
SRAM output matches accepted RIGHT plus final native snapshots. Four virtual
corruptions of actual retained inputs reject before certifier calls or report
writes. Fresh seals cover 1,759 raw inputs plus the independently
pinned immutable MSU. Collection requires both trusted digests and never seals.

Reproduction (use new output roots for fresh builds/capture):

```powershell
$py='E:/gh/_snes-bor-eight-pair-task-20261018/Scripts/python.exe'
$env:PYTHONPATH='.;tools/bor_compile;tools/verify'
$env:MESEN_EXE='E:/gh/Mesen2-mcp-frameexact/bin/win-x64/Release/Mesen.exe'
& $py -B -m unittest test_ref_rebuild test_ref_rebuild_adapter -v
# Capture only while holding the documented shared emulator gate:
& $py -B tools/verify/m4_ref_rebuild_native.py --output out/RF-NEW --suite
& $py -B tools/verify/m4_ref_rebuild_native.py --output out/RF-DISABLED-NEW --disabled --build-only
& $py -B tools/verify/m4_ref_rebuild_native.py --output out/byor-motu-ref-rebuild-v2 --collect-suite --provenance-sha256 f1597aefea2a14cdf684185cdf099d4807cff4927fb6a9c50f3ccba4ac4bbb6f --raw-manifest-sha256 c946fd6639cbcf95cea495bd7bfbbab92bec33629086c4f4dadb0e016bd279fa
```

The five implementation/test files are under `tools/bor_compile` and
`tools/verify`; compact receipt is `docs/receipts/byor-motu-ref-rebuild.json`.
Native captures are `out/byor-motu-ref-rebuild-v2`, static candidate is
`out/byor-motu-ref-rebuild-build-v2`, and disabled control is
`out/byor-motu-ref-rebuild-disabled-v1`. Integration commands, regression logs,
independent reviews, gate records and preservation evidence are retained in
`out/byor-motu-ref-rebuild-integration-v1`.

This isolated fixture establishes no complete game, 30 FPS, live 200-Hz world,
audio, combat, HUD or production SA-1 concurrency claim.
