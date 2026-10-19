# MOTU register-indexed READY validation

**Result: `BYOR_MOTU_READY_VALIDATE_PASS`. All 381 focused tests pass.**
Local changes from accepted `f9fb79f0b7fae45f754e18af3eff9b0456d77740`.
No commit or push; publication awaits approval.

## Measured target

The existing function profile identifies READY validation as the largest
remaining bookkeeping owner: 479,820 exclusive root clocks / 22.340828 ms.
That attribution includes surrounding guard work and uses different boundaries
from the new helper measurement; the two figures are not directly subtracted.
No baseline profiling run was repeated.

The retained fused captures already log the last `NbQueueDrainDone` and the
original `NbReady` callback. The epoch-3 interval between those same markers
falls from **490,896 to 288,078 clocks**:
**202,818 clocks / 9.443379 ms saved
(41.315880%)**. This interval includes
unchanged final-drain return, borrowing validation and source-epoch guard work.
The new helper alone measures 276,550 clocks from entry to the original
source-epoch-check continuation. These are elapsed SNES master clocks, not host
emulator wall time; overlapping publication intervals must not be added.

| Original start-to-visible boundary | Accepted fused | READY register loop |
|---|---:|---:|
| Epoch 2 clocks / fields | 8,416,382 / 23 | 8,059,110 / 22 |
| Epoch 2 ms | 391.873921 | 375.239032 |
| Epoch 3 clocks / fields | 11,676,720 / 32 | 11,319,340 / 31 |
| Epoch 3 ms | 543.678037 | 527.038120 |

Both ordinary publications save one field. The fresh-VBlank schedule and all
CHR/map DMA routines remain unchanged.

## Bounded implementation and ABI

Luna owns `tools/bor_compile/ready_validate.py` and its independent interpreter
tests. The original loop reads each of 1,024 pending-map words twice and updates
the DP counter twice per word. The helper reads each word once, uses X for the
byte offset, checks bit 15 before stripping bit 14, rejects slots at least 768,
and stores the same accepted words in the same order.

On rejection it writes the current offset to DP $70 and preserves the original
A/X/status failure snapshot. Earlier accepted writes remain; the rejected word
and subsequent words are untouched. On success A=2048, X=2046, DP $70=2048,
and the original N/Z/C/V and width/interrupt/decimal state are retained. Y,
stack, DP and DBR remain unchanged. DP $70 is updated only on exit/rejection;
the accepted synchronous producer has no concurrent reader during this loop.

Five instruction-level tests compare against an independent original-loop
model, including both rejection forms at all 1,024 positions (2,048 cases),
ordered partial-write traces, slot 0/767, bit-14 masks, randomized maps and
16-bit CPU contexts. Source anchors include the preceding zero-counter reset;
drift, duplicate sites and reapplication reject. Disabled transformation is
the exact original input.

The helper occupies `$39A800..$39A836`, **55 bytes**, in a byte-checked zero gap.
The six-byte original prefix becomes `JMP RvValidate` plus three unreachable
NOPs, keeping every original symbol and guard body fixed. Return is a JMP to
the original source-epoch check at `$39A223`; no additional stack frame is used.
Independent literal encoding and all **312 branch sites**
match Poppy. Whole-ROM comparison permits only those six dispatch bytes and
the helper. No RAM lease, VRAM, palette, queue capacity, source service or asset
changes. The old fused scanner and all other ROM bytes remain identical.

Candidate ROM SHA256:
`ad04ee314d72a45c5f8785ea749decf612ae974af0366c0eb9bf48e57f724c00`.
The fresh disabled build reproduces accepted fused
`695e623a3eb5dab69feada4a3a72ff6d233227214cacbcfb570eb385dfec36f0`.

## Eight native cases

All eight original native cases pass: **666 consecutive
observed fields / 38,191,104 independently checked
RGB555 pixels**, zero pixel mismatches, resource faults or unsafe PPU operations.

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

Every screenshot and complete physical VRAM/DMA replay remains checked against
the independent source oracles. Exact checkpoint inventories and all f9 source,
allocation, reference-count and physically referenced tile identities match.
Native entry/exit hooks additionally capture full pending maps and all CPU
registers; the verifier reconstructs every 1,024-word transform and checks
context preservation. Both CPUs have active ownership guards for the new map
writer. SA-1 remains reset in this isolated fixture.

The workload is unchanged: 95 actor tiles, ten restorations, 64 tails plus
41 borrowed homes, 639 referenced slots, 105 pairs, 8,400 CHR bytes,
4,096 map bytes and 212 descriptors in thirteen eight-pair batches plus one.
Valid home 204 is still restored into tail 634 by source-owned IDLE. Mode 2
retains six-pair capacity; insufficient budget performs no request-3 DMA.
Minimum complete-batch margin is **27,314 clocks**; minimum map-commit
margin is **14,650**, both above the unchanged 10,000-clock requirement.

## Complete evidence and preservation

The f9 timing receipt is pinned to SHA256
`50e6675c7637e1574018222515893d4479deccc230cfbbffa6d3c2d64a5d7bb2`
before parsing those same bytes. Both candidate epochs' timing keys have
same-ROM tampering rejection tests. Controls come from the digest-pinned
retained captures, including their immutable MSU asset.

The collector requires complete consecutive unique field records and exact
PNG/VRAM inventories. Fresh capture seals contain every native raw file plus
each case's fields and contract. Both source/destination mappings and hashes
are enforced before and after the original eight-case certifiers. Current
candidate seal covers **1,751 raw inputs**; the shared MSU
is independently pinned. Derived reports are reconstructed from those inputs.
Collection never creates or refreshes a seal and requires both explicit trusted
manifest digests. All baseline raw captures and 70 preservation controls remain
unchanged, including the 29 inherited fingerprints, accepted f9 files, original
settings/SRAM and the absent unrelated prompt file; 1,055 older native inputs
are also unchanged. Private Mesen binaries match their source hashes, with only
six output-path settings changed and the original SRAM seed retained. Mesen's
private SRAM save output is byte-identical to accepted fused RIGHT and matches
the final pending/committed/reference snapshots; it is not confused with the
unchanged original input seed.

The initial SRAM declaration is independently bound to the source path and
digest in the SHA256-pinned accepted f9 receipt. Both declared metadata and
actual seed bytes must match; the collector checks them before certification
and again before writing PASS. Six regressions cover a substituted seed with
a matching manifest hash, a changed declared hash, changed actual seed bytes,
missing/incorrect metadata, and rejection before the original certifiers.
The private emulator's final save is checked separately as legitimate output.
Four virtual corruptions against the actual retained inputs (deleted interior
field 10, duplicate field, frame-count gap and same-ROM baseline timing edit)
all reject before original certification or derived report writes; the capture
files themselves are never modified.

All **381 tests** ran after native completion and re-certification: the original
355 plus five helper tests and twenty-one adapter/evidence tests. Independent
review details are recorded in the compact receipt. All
attempt logs are retained; the initial static-audit metadata correction was
before Mesen and changed no emitted code.

## Reproduction and retained artifacts

```powershell
$py='E:/gh/_snes-bor-eight-pair-task-20261018/Scripts/python.exe'
$env:PYTHONPATH='.;tools/bor_compile;tools/verify'
$env:MESEN_EXE='E:/gh/Mesen2-mcp-frameexact/bin/win-x64/Release/Mesen.exe'
& $py -B -m unittest test_ready_validate test_ready_validate_adapter -v
& $py -B tools/verify/m4_ready_validate_native.py --output out/RV-NATIVE-NEW --suite
& $py -B tools/verify/m4_ready_validate_native.py --output out/RV-DISABLED-NEW --disabled --build-only
& $py -B tools/verify/m4_ready_validate_native.py --output out/byor-motu-ready-validate-v1 --collect-suite --provenance-sha256 bd889ec5ebcc8d68746c5fdf6e7975f3bdff0622077ef23352b9e3519e2f1e56 --raw-manifest-sha256 45add5d4518d6400db57b5b239199e2b6b6e71a3d76cee4815248cbae2fa6591
```

Native attempts use fresh roots and serial screenshot sessions. Retained native
captures are `out/byor-motu-ready-validate-v1`; static candidate is `build-v2`
and disabled control is `disabled-v1` under the same naming prefix. Integration
commands, logs, fingerprints and reviews are in
`out/byor-motu-ready-validate-integration-v1`. The full 381-test command is in
`focused-tests-result-v2.json`; compact receipt is
`docs/receipts/byor-motu-ready-validate.json`.

No 30-FPS, live 200-Hz MOTU world, SA-1 concurrency, audio, HUD, combat or
complete MOTU Demo claim. This experiment changes only bounded READY CPU work.
