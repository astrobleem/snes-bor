# Bounded seventh-pair native staging

**BYOR_MOTU_SEVEN_PAIR_SPILL_PASS.** Astra's supplied assembly overlay passes native correctness, ownership and timing budgets on accepted starting commit `ea9a992fb22c7fd31fc02e785cb9c10fa2ef6395`. The assembly generator and its original policy/source tests are unchanged. Existing renderer, allocator, restoration, bitmap, source, assets and historical auditor files remain unmodified.

The package `motu_seven_pair_spill_ea9a992.zip` has SHA256 `448176bd7555473551c18ddb784a5465d36d1ab0effd72e25beb8f6d595bac67`. It was extracted into `out/byor-motu-seven-pair-package-v1`; README, `SOL_PROMPT.md` and manifest hashes were checked. Only the four specified new Python files were installed.

## Native timing and transfer result

| Publication | Accepted six-pair: clocks / ms / fields | Candidate: clocks / ms / fields |
|---|---:|---:|
| Epoch 2 | 9,845,860 / 458.431635 / 27 | 9,131,176 / 425.155339 / 25 |
| Epoch 3 | 14,178,234 / 660.150662 / 39 | 13,106,162 / 610.234075 / 36 |

The same native start-to-visible boundaries and source workloads are used. These are master clocks converted at 21,477.270 clocks/ms; neither offline queue arithmetic nor instruction estimates are reported as native timing. Epoch 3 still uploads exactly **105 pairs, 8,400 CHR bytes, 4,096 paired-map bytes and 212 descriptors**, now in **15 batches of seven pairs**. Its 15 seventh HIGH sources are all `$0034B0`; each is followed by LOW at `$0034F0` to the corresponding physical LOW tile. First-six source order remains exactly `$3500,$3550,$35A0,$35F0,$3640,$3690`.

For epoch 3, measured seventh-HIGH DMA intervals are 558–566 clocks and LOW intervals 214–222 clocks, from actual PACKET to DONE callbacks. Every pair has separate completion fences before active display. The complete seven-pair batches in the default run take 18,262–18,326 clocks from first DMA submission through `NbQueueDrainDone`. The suite's minimum **complete-batch** margin is **30,350 clocks**, and its minimum **map-commit completion** margin is **14,674 clocks**. Both exceed the required 10,000 clocks. These newly measured margins include drain-loop completion, rather than treating the last LOW fence as the complete-batch boundary.

The default two publications have map-completion margins of 15,098 and 14,698 clocks. Exact per-batch windows, HIGH/LOW timings, descriptors and full physical replay remain in the receipt. Bitmap, BhPrepare, source-event and composition timings are retained separately; these intervals overlap publication and must not be added together.

## Ownership and actual code placement

The finished restoration count and fault mode select capacity at `BhActorPlanAdmitted`, before production:

- At most 12 records and mode other than 2: capacity seven.
- More than 12 records, or mode 2: capacity six.

No actor, epoch, position or picture identity participates in this policy. The original restoration limit remains 48.

| Storage | Ownership |
|---|---|
| `$003480..$0034AF` | First 12 live restoration records, unchanged |
| `$0034B0..$0034EF` | Seventh HIGH, 64 bytes, only after completed count <=12 |
| `$0034F0..$0034FF` | Seventh LOW, 16 bytes, same policy/lifetime |
| `$003500..$0036DF` | Original six 80-byte pairs, unchanged |
| `$42D620..$42D65F` | Original restoration overflow records, unchanged |
| `$42D66E..$42D66F` | Seventh physical-slot word |
| `$42D670..$42D671` | Dynamic capacity word |
| `$42D674..$42D675` | Existing exact-retry marker, unchanged |

The additional pair reuses the dead remainder of the 128-byte I-RAM restoration area; it does not overlap any live record under the selected policy. The borrowed bitmap queue lease expires before policy/production. No VRAM, OBJ arena, persistent actor, journal or source latch allocation is added. The 20-byte source latch, source physics, returning-worker/conversion/stack authorities and spill records retain their original ownership. Both CPUs' physical write guards remain active; SA-1 remains reset under the accepted isolated fixture. DMA source use is independently checked against the live capacity, completed count, queue index and completion fences. This is not SA-1 concurrency.

Poppy measures a net **35-byte** increase in the transaction region: `$39A64D` becomes `$39A670`, below `$39B000`. All 300 branch sites pass the existing branch audit. Four existing B000/B300 call/jump operands are relinked to relocated A000 entries. The adapter independently reconstructs those operand-only changes and requires every other helper opcode/instruction/padding byte unchanged. The complete ROM is compared with its accepted base, permitting only the exact A000 overlay and those operand fixups. The source/world code, both graphics kernels, asset/palette authorities and two DMA descriptor bodies are unchanged.

## Pixel, residency and fault certification

All eight native cases pass: **744 continuously visible fields / 42,663,936 independently verified RGB555 pixels**, with zero mismatches, unsafe operations or resource faults. Brightness stays 15 after cold bootstrap. Full physical VRAM and DMA replay, all visible fields, palette identity, referenced CHR contents and completed maps/refcounts pass. Cross-run checks compare displayed maps and referenced HIGH/LOW CHR with the accepted six-pair controls; unreferenced power-on residue is not assumed identical between emulator instances.

| Case | Fields | Verified pixels | Result |
|---|---:|---:|---|
| Default UP | 96 | 5,505,024 | Original epoch-2 latch and real JOY1 UP epoch 3 both publish |
| Valid home / IDLE | 126 | 7,225,344 | Home 204 restored into tail 634 by the subsequent source-owned IDLE transaction |
| Early rollback | 90 | 5,160,960 | Original display/refs retained; valid-home restoration fenced |
| READY rollback | 96 | 5,505,024 | Original display/refs retained |
| Partial queue | 97 | 5,562,368 | Transaction 3 uses six, never resolves/uploads a seventh pair, and exercises the original partial-queue rejection |
| Stale epoch | 96 | 5,505,024 | Original display/refs retained |
| Insufficient budget | 78 | 4,472,832 | No transaction-3 DMA |
| RIGHT control | 65 | 3,727,360 | Original safe-point, LEFT retention and graphics-free projected noops pass; publication takes 25 fields |

Epoch 3 retains **95 actors, ten restorations, 64 tails plus the original first 41 invalid homes, 105 total reservations, 639 final referenced slots and the exact 1,816 changed source pixels**. There are no new default-path home invalidations. Policy logs show partial-case transactions 1/2 legitimately use seven, while only its mode-2 transaction 3 selects six. The native cases exercise record counts 6, 8, 9 and 10; larger-count fallback is covered by the supplied offline policy/source tests, not claimed as an additional native scene.

All **225 accepted focused tests** remain unchanged and pass, together with the 16 supplied tests and six adapter-regression tests: **247 tests total**, including 76,800 inherited reference comparisons. This full test run was performed after native completion and re-certification. All 29 inherited dirty tracked files, including the protected 17, retain their SHA256s. The unrelated prompt-file deletion remains unstaged.

## Adapter corrections, with no oracle relaxation

1. The supplied observer called the shared observer through an entrypoint that had just been patched to itself. The v1 attempt stopped before Mesen on recursion. Capturing the original function fixes this; a regression reproduces the patched-entrypoint call.
2. RIGHT uses a separate original batch certifier. Its accepted source list and deterministic source sequence required the exact seventh address. Its READY-fence predicate is extended to include that source as well. All original pixel, per-field VRAM replay, destination, source-world/latch and DMA fence checks remain. Exact source anchors fail closed on drift; tests reject wrong sources/fences or altered certifier structure.
3. The partial-case aggregate originally prohibited seventh DMA anywhere in that run. The correction requires capacity six and no seventh source resolution/DMA specifically in its mode-2 request, while retaining seven for its earlier ordinary requests.
4. Re-certification invokes the complete original home and RIGHT source/pixel/replay oracles, not just cached result flags. Additional checks enforce exact per-batch source order and at least 10,000 clocks at complete drain/map completion, with synthetic negative tests for insufficient margins and changed original-six source addresses.

The v2 process had already loaded the older RIGHT certifier; after all 65 RIGHT fields were captured it rejected `$34B0` as an old six-source descriptor. The corrected `--collect-suite` re-certified the completed eight-case output without another emulator run or source step. All native logs remain unfiltered and retained. No supplied assembly or memory lease was changed. The failed pre-Mesen v1 attempt is excluded from certified field/pixel totals.

## Reproduction and artifacts

```powershell
$env:PYTHONPATH='.;tools/bor_compile;tools/verify'
$env:MESEN_EXE='E:/gh/Mesen2-mcp-frameexact/bin/win-x64/Release/Mesen.exe'
python -m unittest test_seven_pair_spill test_seven_pair_adapter -v
python tools/verify/m4_seven_pair_native.py --output out/byor-motu-seven-pair-NEW --suite
# Only after the native run completes:
python tools/verify/m4_seven_pair_native.py --output out/byor-motu-seven-pair-NEW --collect-suite
```

Native screenshot cases remain serial. A native retry must use a new output directory. `--collect-suite` reuses completed captures and runs no source movement. The full focused-test command is the accepted 225-test module list from the previous bitmap-shared findings, plus `test_seven_pair_spill test_seven_pair_adapter`; its 247-test log and SHA256 are recorded in the receipt.

Candidate: `out/byor-motu-seven-pair-v2/success/native/bor.sfc`, SHA256:

```text
c2b429e86171f68cdab639511da61fb5d1679d34fc6c2b9ae6cc23f41e7d2604
```

The final adapter rebuild reproduces that candidate byte-for-byte at `out/byor-motu-seven-pair-final-build-v1`. The unchanged accepted build reproduces SHA256 `04eba01445dbae69638ba0858c18aef28d0a0172e250deeb6099585acf88dc57` at `out/byor-motu-seven-pair-disabled-v1`. Build it with the unchanged `m4_bitmap_shared_native.py --output <fresh> --build-only`; no overlay is applied by default.

Per-case native folders retain every visible screenshot/VRAM field, source snapshot/oracle, unfiltered log, physical reservation, queue policy, DMA payload and completion fence. The reproducible native aggregate is `out/byor-motu-seven-pair-v2/seven-pair-receipt.json`; the committed handoff is `docs/receipts/byor-motu-seven-pair-spill.json`.

No 30-FPS, 200-Hz scheduling, SA-1 concurrency, audio, HUD, combat or Demo-completion claim. This remains a bounded correctness/performance experiment with roughly 610-ms default second publication.

## Epoch-3 seventh-pair timing records

All clocks are native master clocks. Every row uses HIGH `$0034B0` and LOW `$0034F0`, each targeting its paired physical slot; LOW VRAM word is `$6000 + HIGH_word/4`. Exact VBlank edges and margins are included in the receipt.

| Batch | Physical pair slot | HIGH start | HIGH done | LOW start | LOW done |
|---:|---:|---:|---:|---:|---:|
| 1 | 602 | 213672804 | 213673362 | 213673930 | 213674144 |
| 2 | 609 | 214030208 | 214030774 | 214031342 | 214031556 |
| 3 | 616 | 214387540 | 214388098 | 214388666 | 214388880 |
| 4 | 623 | 214744916 | 214745474 | 214746042 | 214746256 |
| 5 | 630 | 215102292 | 215102850 | 215103418 | 215103632 |
| 6 | 745 | 215459628 | 215460186 | 215460754 | 215460968 |
| 7 | 752 | 215817068 | 215817626 | 215818194 | 215818408 |
| 8 | 759 | 216174372 | 216174930 | 216175498 | 216175712 |
| 9 | 766 | 216531780 | 216532338 | 216532906 | 216533120 |
| 10 | 329 | 216889146 | 216889704 | 216890272 | 216890494 |
| 11 | 387 | 217246526 | 217247084 | 217247652 | 217247866 |
| 12 | 417 | 217603832 | 217604398 | 217604966 | 217605180 |
| 13 | 512 | 217961200 | 217961766 | 217962334 | 217962548 |
| 14 | 530 | 218318574 | 218319132 | 218319700 | 218319914 |
| 15 | 576 | 218675996 | 218676554 | 218677122 | 218677336 |

## Per-case native transaction intervals

Clocks / milliseconds / fields; rejected attempts end at abort rather than a new presentation. The original source/control workloads are unchanged. Epoch 2 is 9,131,176 clocks / 425.155339 ms / 25 fields in all UP cases.

| Case and epoch | Accepted six-pair | Seven-pair candidate | Outcome |
|---|---:|---:|---|
| success, epoch 3 | 14,178,234 / 660.150662 / 39 | 13,106,162 / 610.234075 / 36 | published |
| valid, epoch 3 | 14,535,588 / 676.789368 / 40 | 13,463,520 / 626.872968 / 37 | published |
| valid, epoch 4 | 9,716,926 / 452.428358 / 27 | 8,644,654 / 402.502460 / 24 | published |
| early, epoch 3 | 11,199,952 / 521.479313 / 31 | 10,842,744 / 504.847404 / 30 | rejected; previous image retained |
| ready, epoch 3 | 14,058,870 / 654.592972 / 39 | 12,986,946 / 604.683277 / 36 | rejected; previous image retained |
| partial, epoch 3 | 13,344,126 / 621.313882 / 37 | 13,344,350 / 621.324312 / 37 | rejected; previous image retained |
| stale, epoch 3 | 14,058,840 / 654.591575 / 39 | 12,986,984 / 604.685046 / 36 | rejected; previous image retained |
| insufficient, epoch 3 | 6,440,872 / 299.892491 / 18 | 6,440,876 / 299.892677 / 18 | rejected; previous image retained |
