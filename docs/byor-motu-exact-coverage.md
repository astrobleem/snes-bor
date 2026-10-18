# BYOR MOTU exact coverage early exit

**Result: `BYOR_MOTU_EXACT_COVERAGE_PASS`. Local changes for review; no commit or push.**

Baseline is Q8 at `e00e1c720f03833e792df17088a37edcc9dbb4af`. Candidate ROM SHA256:
`0ad890b7390e83e593596e456469fece2ab37ab9378ac733c80b581a56841edd`. The independently regenerated disabled control
reproduces Q8 `4a696c9bc6d94e153188c6226744b3daf8ccfdb5301e943bf280f2697de129e9` exactly.

## Native result

| Original start-to-visible boundary | Q8 | Exact coverage early exit |
|---|---:|---:|
| Epoch 2 clocks / fields | 8,416,382 / 23 | 8,416,382 / 23 |
| Epoch 3 clocks / fields | 12,748,862 / 35 | 12,034,092 / 33 |
| Epoch 3 ms | 593.597883 | 560.317582 |

Epoch 2 is unchanged. Epoch 3 saves two fields and
33.280301 ms.
This meets the bounded target of at least one saved epoch-3 field with no epoch-2 regression.
The elapsed publication still takes about 560 ms; this does not establish a 30-FPS update cadence.

## Instrumentation and exactness

The unchanged-Q8 observer reproduces the original transaction clocks and fields exactly.
It measures the exact `NbBeginRetry` entry through `NbRestorePlanStart`, and the
207 individual coverage entries through RTS fetch. Helper spans exclude the caller JSR
and final RTS; all spans include bus and interrupt time.

| Epoch-3 exact pass | Q8 | Candidate |
|---|---:|---:|
| Coverage calls / positive cells | 207 / 95 | 207 / 95 |
| Rows visited | 1656 | 1037 |
| Coverage helper clocks | 2,574,580 | 1,610,508 |
| Coverage helper ms | 119.874640 | 74.986625 |
| Complete exact mark clocks | 3,056,666 | 2,092,856 |
| Complete exact mark ms | 142.320975 | 97.445159 |

Every queried cell has the same order and boolean verdict as the unchanged-Q8
capture. The earlier approximate 142.326-ms estimate is superseded by this explicit
entry-to-entry measurement of 142.320975 ms.

Only the exact-retry `NbMarkTest` call changes. It consumes coverage through
`cmp #0` / `beq NbMarkNext`; it never consumes the full OR mask. The new helper
returns on the first nonzero result of the existing `OnlineRowMask`. That original
routine retains source clipping, subpixel alignment, source transparency and inverted
fixed-foreground masks. Empty cells still scan all eight rows. There is no cache,
new validity key or allocation approximation.

The old full-mask `OnlineCoverage`, row pointer/mask/step helpers, compositor,
allocator, source owner, queue policy and DMA routines remain byte-identical.
DP $58 is the helper's row counter; the original source has no consumers outside
`OnlineCoverage`. $5A is likewise private to the original reduction. The caller
does not consume the early-exit row pointers, and each next cell reinitializes them.

## Code and ownership audit

The helper occupies $39A700..$39A71E (31 bytes) in a verified zero gap; code end
is $39A71F, below $39B000. The only original ROM changes are the two JSR operand
bytes at $39A06D. Every original symbol remains fixed.
Literal 65816 opcode checks independently certify all helper bytes and both branch
displacements. All 304 branch sites pass.
Whole-ROM comparison rejects any additional mutation; four deliberate in-memory
ROM mutations (call opcode, operand, helper and unrelated byte) all reject.
No additional memory lease, queue capacity, VRAM arena or media regeneration is introduced.

## Review gap closure

The collector requires exact checkpoint inventories for both candidate and Q8
before calling any original certifier: 30 checkpoint files for ordinary cases,
36 for valid-home, and 32 for RIGHT. Missing and unexpected captures reject;
a directory cannot stand in for a file. State parity comparisons iterate the
required inventory rather than whichever files happen to exist.

The transform also pins `beq NbMarkNext` immediately after `cmp #0`. Missing,
nonzero/sign/overflow branches and an incorrect zero-branch target reject.
The reviewed baseline profile JSON digest is pinned in the adapter as
`d9f35a7b5e5597a543bdcaf178f874012297f4a1c74f462d3941b6f2186cad5e` and checked before JSON use or certification;
the independent Q8 ROM hash check remains required.

Twelve additional test methods cover these guards, including nine rejection tests for missing candidate
and control captures and altered baseline JSON with an unchanged control ROM.
All 27 targeted tests pass, including a positive collection regression separating
profile data from timing records. A fresh Poppy rebuild reproduces the existing ROM,
publisher binary and publisher source byte-for-byte. All 1,055 retained native
input hashes match the pre-hardening snapshot, so the existing eight native
runs were re-certified without another emulator run.

## Native cases and regression

All eight original cases pass: 686 continuously observed fields,
39,337,984 independently checked RGB555 pixels, zero mismatches,
resource faults or unsafe PPU operations. Full original screenshot/source oracles,
physical VRAM/DMA replay, ownership guards, rollback/rejection cases, source latch,
home restoration and allocation checks remain active. State checkpoints and physically
referenced tile identities additionally match Q8 exactly.

| Case | Fields | Verified RGB555 pixels |
|---|---:|---:|
| success | 89 | 5,103,616 |
| valid | 117 | 6,709,248 |
| early | 82 | 4,702,208 |
| ready | 88 | 5,046,272 |
| partial | 90 | 5,160,960 |
| stale | 88 | 5,046,272 |
| insufficient | 71 | 4,071,424 |
| right | 61 | 3,497,984 |

The epoch-3 workload remains 95 actor tiles, ten restorations, 64 tail reservations
plus 41 borrowed homes, 639 referenced slots, 105 HIGH/LOW pairs, 8,400 CHR bytes,
4,096 map bytes and 212 descriptors. Batching remains thirteen groups of eight plus
one group of one. Minimum complete-batch margin is 27,318 clocks; minimum
map margin is 14,648, both above 10,000. All HIGH/LOW completion fences remain required.

All 304 focused tests pass after native re-certification: the original 277 plus eight
independent per-pixel/transform tests and nineteen adapter regressions. The per-pixel
tests sweep all 225 partial alignments and explicit fully clipped, fully occluded
and transparent cases. All 29 inherited fingerprints and the takeover snapshot
match; the unrelated prompt-file deletion remains. All 1583 original
tracked Python sources under tools match HEAD contents (651 existing CRLF
checkouts require newline normalization for that Git comparison). The four Q8
Python files match HEAD bytes exactly; its 2 documentation files use
existing CRLF checkouts and match HEAD after newline normalization. No checkout
endings are rewritten.
Original emulator settings and SRAM hashes are unchanged.

## Separate fresh-VBlank scheduling constraint

The queue still invokes `NbFreshVblank` 15 times during epoch 3: fourteen CHR
windows and one map window. That routine waits for VBlank to end, then for a fresh
VBlank to start, even when entered during VBlank. Thus the unchanged schedule
requires at least fourteen field periods (about 233 ms) from the first CHR window
to the map window. This is a property of this publication schedule, not a measured
hardware lower bound. Its elapsed interval overlaps computation and explicit waits;
it must not be added to their costs.

Measured preparation clocks fall from 6,647,616 to
5,683,806; explicit waits change from
1,464,318 to 1,712,658.
Post-map bookkeeping remains separately visible in the receipt. Coverage is inside
preparation; those intervals must not be summed. This experiment changes no VBlank
scheduling, source-world scheduling or CPU concurrency.

## Reproduction and retained evidence

Use the existing task interpreter, PYTHONPATH `.;tools/bor_compile;tools/verify`,
and the matched frame-exact Mesen executable from the Q8 findings. Every native
attempt needs a fresh root; capture runtime lives at the root and the Q8 builder
receives an absent case child. Its fresh-output guard remains enabled.

```powershell
$py='E:/gh/_snes-bor-eight-pair-task-20261018/Scripts/python.exe'
$env:PYTHONPATH='.;tools/bor_compile;tools/verify'
$env:MESEN_EXE='E:/gh/Mesen2-mcp-frameexact/bin/win-x64/Release/Mesen.exe'
& $py -B -m unittest test_exact_coverage test_exact_coverage_adapter -v
& $py -B tools/verify/m4_exact_coverage_native.py --output out/EC-PROFILE-NEW --profile-only
& $py -B tools/verify/m4_exact_coverage_native.py --output out/EC-CANDIDATE-NEW --suite --profile-baseline out/EC-PROFILE-NEW/success
& $py -B tools/verify/m4_exact_coverage_native.py --output out/EC-DISABLED-NEW --disabled --build-only
# Re-certify retained captures without advancing the emulator:
& $py -B tools/verify/m4_exact_coverage_native.py --output out/EC-CANDIDATE-NEW --collect-suite --profile-baseline out/EC-PROFILE-NEW/success
# Complete focused cluster after native capture and certification:
& $py -B -m unittest test_restore_single_pass test_restore_single_pass_adapter test_home_borrow_bitmap test_home_borrow_bitmap_adapter test_m4_home_borrow test_m4_source_safepoint test_m4_conditional_capacity test_early_capacity test_m4_early_capacity_component test_restore_spill test_m4_restore_spill_component test_batch_rescue test_generated_splice test_m4_nonblank_batch_component test_m4_nonblank_component test_rect_map_opt test_m4_rect_map_component test_direct_pair_dma test_m4_direct_pair_component test_m4_native_cost_accounting test_tile_fusion test_m4_tile_fusion_component test_phase_occupancy test_m4_occupancy_component test_m4_opaque_component test_m4_online_component test_m4_live_ground_component test_component_live_bundle test_m4_component_publication test_bg_component_residency test_bg_component_deadlines test_bg_components test_home_bitmap_shared_cells test_m4_bitmap_shared_adapter test_seven_pair_spill test_seven_pair_adapter test_eight_pair_direct test_m4_eight_pair_adapter test_exact_coverage test_exact_coverage_adapter -q
```

The full 304-test module list and result are retained in
`out/byor-motu-exact-coverage-integration-v1/focused-tests-result-v2.json`.
Candidate native captures and the complete aggregate are under
`out/byor-motu-exact-coverage-v1`; unchanged-ROM profiling is under
`out/byor-motu-exact-coverage-profile-v4`. The compact repository receipt is
`docs/receipts/byor-motu-exact-coverage.json`.

Implementation and tests:
`tools/bor_compile/exact_coverage.py`,
`tools/verify/m4_exact_coverage_native.py`,
`tools/verify/test_exact_coverage.py`, and
`tools/verify/test_exact_coverage_adapter.py`.
Their exact hashes are included in the compact receipt.

The initial output-root collision, nonexistent synthetic READY symbol and Lua
token-spacing failures are retained in profile-v1/v2/v3 logs and excluded from
certified totals. They were corrected in the new adapter; no original observer,
certifier, resource assertion or fault log was weakened or suppressed.

No 30-FPS, 200-Hz, SA-1 concurrency, audio, HUD, combat or complete MOTU Demo claim.
