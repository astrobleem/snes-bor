# MOTU measured function costs and fused exact coverage

**Result: `BYOR_MOTU_FUSED_COVERAGE_PASS`. All 355 focused tests pass.**
Local implementation from `a7a240b110df678a9968ed4d4be8ac1973d9fa3a`.
No commit or push; publication awaits approval.

## Unchanged-ROM function attribution

The profiler reproduces the accepted exact-coverage ROM
`0ad890b7390e83e593596e456469fece2ab37ab9378ac733c80b581a56841edd`
and the original absolute transaction clocks. Its epoch-3 boundary is the
accepted `NbBegin` through `NbVisible`, 12,034,092 master clocks / 560.317582 ms.
All 4,569 observed calls close; function exclusive spans plus root spans equal
the complete interval. Orthogonal categories reproduce the original ledger:

| Disjoint category | Clocks | ms |
|---|---:|---:|
| PREPARING | 5,683,806 | 264.642853 |
| Original TILE spans | 1,874,122 | 87.260718 |
| Explicit WAIT spans | 1,712,658 | 79.742816 |
| PACKET through DONE spans | 112,168 | 5.222638 |
| Setup/bookkeeping residual | 2,651,338 | 123.448557 |

The residual is fully assigned to function owners or named inline phases.
Largest exclusive owners are:

| Residual owner | Clocks | ms |
|---|---:|---:|
| READY validation inline loop | 479,820 | 22.340828 |
| Actor `NbPreloadPair` | 469,458 | 21.858365 |
| Publish reference counts | 304,248 | 14.166046 |
| Actor `BhInvalidate` | 285,378 | 13.287443 |
| Actor iteration inline work | 275,686 | 12.836175 |
| Clear reference counts | 153,490 | 7.146625 |
| Actor `OnlineRowPointers` | 139,218 | 6.482109 |
| Committed-map copy | 109,882 | 5.116200 |

The complete exact-mark interval, nested inside PREPARING, is independently
reconciled to 2,092,856 clocks / 97.445159 ms:

| Exact-mark exclusive owner | Clocks | ms |
|---|---:|---:|
| `OnlineRowMask` | 573,098 | 26.683931 |
| `OnlineStepRow` | 551,412 | 25.674213 |
| Mark-loop inline work | 353,162 | 16.443524 |
| `OnlineRowPointers` | 303,850 | 14.147515 |
| `EcCoverage` control | 200,964 | 9.357055 |
| Retry initialization | 110,370 | 5.138921 |

Call spans include caller JSR/JSL through the instruction after return;
exclusive spans remove child calls. Original helper profiles instead measure
entry through RTS fetch. These boundaries differ and their totals must not
be mixed. All spans include bus/interrupt time. TILE, WAIT, DMA and scheduling
intervals overlap some inclusive routines; only the disjoint ledger is additive.

### Corrected attribution boundary

Profile v1 passed native capture and unchanged transaction timing but rejected
the disjoint ledger: PREPARING was 72 clocks short and residual 72 clocks long.
Its probe was at `$39A139`, before `lda #2; sta.l $42D600`. The original
`NbPreloading` observer is at `$39A140`, after both instructions. The corrected
probe uses that same post-store instruction boundary. Profile v2 passes the
unchanged strict ledger; no expected total or raw record was adjusted.
Both attempts remain retained. A regression compares the generated probe
directly with the original observer, and source-anchor drift rejects.

## Bounded implementation

Luna owns `coverage_fused.py` and its independent instruction-level tests.
The new scanner at `$39A740..$39A79A` is 91 bytes and preserves the original
`OnlineRowPointers` setup. It inlines the exact row mask and source-pointer
step, preserving unsigned height clipping, signed negative-row stepping,
foreground inversion, both mask byte lanes, 24-bit carry and `$58` visit counts.
The boolean caller receives 0 or 1. The unused planar `$0C/$0E` stepping is
removed from this path; the next cell initializes its pointers again.

The existing `NbMarkTest` JSR changes target within the same page, so one
operand byte differs; the audit permits only its two-byte operand range.
The old exact scanner, full-mask coverage, row helpers,
compositor, allocator, queue, DMA and source services remain identical.
No original symbol moves. Independent literal opcodes and branch displacements
must match Poppy output; whole-ROM comparison rejects any other mutation.

Seven scanner tests execute the emitted instruction subset against per-pixel
expectations, including all 225 partial alignments, clipping, transparency,
occlusion, first/last hits, upper mask lanes, negative rows and pointer carry.
Adapter tests reject four independent ROM mutations, altered baseline profile
JSON, missing accepted checkpoint inventory and timing regressions.

## Native result

| Original start-to-visible boundary | Accepted exact coverage | Fused row scanner |
|---|---:|---:|
| Epoch 2 clocks / fields | 8,416,382 / 23 | 8,416,382 / 23 |
| Epoch 3 clocks / fields | 12,034,092 / 33 | 11,676,720 / 32 |
| Epoch 3 ms | 560.317582 | 543.678037 |
| Exact-mark clocks / ms | 2,092,856 / 97.445159 | 1,749,038 / 81.436700 |
| Coverage-helper clocks / ms | 1,610,508 / 74.986625 | 1,267,152 / 58.999677 |

Epoch 3 saves one field / 16.639545 ms. Epoch 2 is unchanged. All seven
UP-style cases retain the exact 207 cell queries, 95 positive cells and
1,037 visited rows. RIGHT performs no exact retry and retains its 23 fields.
Every case's profile is compared with a digest-pinned accepted profile;
cell order, boolean verdict and first-hit row must match.

All eight native cases pass after full re-certification: **679 continuously
observed fields / 38,936,576 independently checked RGB555 pixels**, zero
pixel mismatches, resource faults or unsafe PPU operations.

| Case | Fields | Verified pixels |
|---|---:|---:|
| success | 88 | 5,046,272 |
| valid | 116 | 6,651,904 |
| early | 81 | 4,644,864 |
| ready | 87 | 4,988,928 |
| partial | 89 | 5,103,616 |
| stale | 87 | 4,988,928 |
| insufficient | 70 | 4,014,080 |
| right | 61 | 3,497,984 |

Independent source composition, every visible screenshot, full physical
VRAM/DMA replay, READY residency, allocation order, rollback and ownership
guards remain active. Epoch 3 still uses 95 actor tiles, ten restorations,
64 tail reservations plus 41 borrowed homes, 639 referenced slots, 105 pairs,
8,400 CHR bytes, 4,096 map bytes and 212 descriptors in thirteen eight-pair
batches plus one single pair. Valid home 204 restores into tail 634 later.
Mode-2 partial queue remains six; insufficient budget emits no transaction-3 DMA.

Minimum complete-batch margin is **27,306 clocks**, and minimum map-commit
margin is **14,650**. Both exceed 10,000. All paired completion fences remain
required. Fresh-VBlank policy and its fifteen calls are unchanged.

Candidate ROM SHA256:
`695e623a3eb5dab69feada4a3a72ff6d233227214cacbcfb570eb385dfec36f0`.
All 309 branch sites pass. There are 75 actual differing ROM bytes, confined
to the old JSR operand and the new helper. The CLI `--disabled --build-only`
fresh rebuild reproduces the accepted exact-coverage ROM byte-for-byte.

### Retained attempts and certification provenance

The first seven cases completed in native v1. RIGHT then stopped during cold
startup: the unchanged frame tool requested ten fields, advanced nine and
reported its wall-time cap. The assertion and failed raw logs are retained.
No frame assertion or native checker was changed. A fresh RIGHT v2 run passed
with the identical ROM, driver and original capture inputs.

The successful seven cases and the complete fresh RIGHT case were copied
into a new certification directory. All 1,842 copied files matched their
sources; immutable MSU files are hardlinks. The complete original eight-case
certifiers were rerun there, followed by comparison with accepted exact
checkpoints and all case profiles. All **1,769 raw certification inputs**
remain byte-identical afterward. Failed attempts are excluded from passing
field totals and preserved separately.

### Complete capture and timing guards

Collection now loads the accepted timing receipt through `fused_timing_baseline.py`.
Its SHA256 `fc1a9f5a77ceba0e8d945addb044306d1327308b547a0f4c54d87c89564b2221`
is checked before JSON parsing, and those same verified bytes are parsed. The
accepted ROM identity is also required. Same-ROM edits to either candidate
epoch's field count or clocks reject before any native certifier runs.

`fused_capture_evidence.py` requires nonempty field records, unique ordered
indices exactly 0 through N-1, and unique consecutive integer PPU frame counts.
It requires the exact PNG and VRAM inventory, rejects nested/extra/missing captures
and directories standing in for files, and verifies each capture's metadata hash.

The original provenance and 1,769-row raw manifest remain byte-identical and
are independently digest-pinned before parsing. Every raw input must appear
exactly once, match the actual complete raw inventory, map to the corresponding
declared source case and relative filename, and match both the origin and
destination hashes. All 1,842 declared source-copy hashes are checked. Derived
case reports may be rewritten by the original certifiers; raw inputs may not.
The shared MSU asset is excluded from the historical raw manifest but now has
its own accepted SHA256 pin:
`eb781b14d4df082f574df8eb58cb90d5714969a5a91913fdcbd70902da77b1cf`.
Both source and destination MSUs must match that pin for every case.

All capture checks run before the original certifiers and again afterward.
Only then may the fused PASS receipt be written, with its field total reconciled
to the verified complete record count. Existing collection never creates or
refreshes provenance. A fresh native suite seals its captures once before
collection and prints both manifest pins. Re-collecting another suite requires
its trusted `--provenance-sha256` and `--raw-manifest-sha256`; the default pins
are exclusively for the retained certified suite.

The negative regressions cover deletion of index 10, duplicated/reordered/gapped
records, shortened endpoints, missing/extra PNG and VRAM files, altered raw
inputs/manifests/origins/mappings/MSUs, post-certification mutation and timing
tampering. CLI tests cover paired pin requirements and both collection paths
without resealing. Independent read-only review found no concrete remaining
verifier defect. A fresh Poppy rebuild preserves the ROM, publisher binary,
publisher source and symbols byte-for-byte. Retained captures were re-certified
without another emulator run; their totals and timing are unchanged.

## Regression and preservation

The final focused cluster ran after native completion and re-certification:
**355 tests pass** (the original 304, seven scanner tests, twelve adapter tests,
two profiler-boundary tests, six timing-loader tests and 24 capture-evidence tests).
Existing accepted test files are unchanged.
The complete command, count and durable log hash are recorded in the receipt.

Final preservation checks require the 29 inherited fingerprints, six accepted
exact-coverage files, 21 takeover entries including the absent prompt file,
and original emulator settings/SRAM to match. The 1,055 original native input
hashes are also checked against the accepted pre-hardening snapshot.
The original baseline and all failed attempts remain retained.

## Reproduction

Use the existing task interpreter, accepted artifacts and matched frame-exact
Mesen executable. Native attempts require fresh directories; screenshot cases
run serially. The command-line disabled control rebuilds the accepted exact
scanner. Collection re-runs the independent certifiers without advancing Mesen.

```powershell
$py='E:/gh/_snes-bor-eight-pair-task-20261018/Scripts/python.exe'
$env:PYTHONPATH='.;tools/bor_compile;tools/verify'
$env:MESEN_EXE='E:/gh/Mesen2-mcp-frameexact/bin/win-x64/Release/Mesen.exe'
& $py -B -m unittest test_coverage_fused test_fused_coverage_adapter test_function_cost_profile test_fused_timing_baseline test_fused_capture_evidence -v
& $py -B tools/verify/m4_function_cost_native.py --output out/FC-PROFILE-NEW
& $py -B tools/verify/m4_fused_coverage_native.py --output out/FC-NATIVE-NEW --suite
& $py -B tools/verify/m4_fused_coverage_native.py --output out/FC-DISABLED-NEW --disabled --build-only
& $py -B tools/verify/m4_fused_coverage_native.py --output out/byor-motu-fused-coverage-certified-v1 --collect-suite
```

The complete 355-test command is in
`out/byor-motu-fused-hardening-v1/focused-tests-result-v1.json`.
Repository receipt: `docs/receipts/byor-motu-fused-coverage.json`.

## Retained evidence

- Unchanged-ROM profile: `out/byor-motu-function-profile-v2/success/function-cost-profile.json`.
- Raw failed profile: `out/byor-motu-function-profile-v1`.
- Certified aggregate: `out/byor-motu-fused-coverage-certified-v1`.
- Initial native suite and failed RIGHT startup: `out/byor-motu-fused-coverage-v1`.
- Fresh successful RIGHT: `out/byor-motu-fused-coverage-right-v2`.
- Static build: `out/byor-motu-fused-coverage-build-v1`.
- Disabled CLI baseline rebuild: `out/byor-motu-fused-coverage-disabled-v2`.
- Integration logs and fingerprints: `out/byor-motu-function-cost-integration-v1`.
- Hardening tests, fresh build comparison and preservation: `out/byor-motu-fused-hardening-v1`.
- Byte-identical hardening rebuild: `out/byor-motu-fused-hardening-build-v1`.

No 30-FPS, 200-Hz, SA-1 concurrency, audio, HUD, combat or full MOTU Demo claim.
