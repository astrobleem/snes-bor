# Native single-pass restoration remapping

This experiment installs Astra's supplied restoration overlay on accepted bitmap commit `8d317e53828a741c6d0e79a0cfd5f64cee3c4024`. It replaces repeated full-map reroutes with one ordered pending-map pass and lookups in the existing restoration records. The allocator, bitmap planner, record order/capacity, home journal, invalidation, rollback, six-pair queue, source latch, source services and compositor are unchanged. No persistent or transient memory allocation is added.

The package `motu_restore_single_pass_8d317e5.zip` has SHA256 `d0db336a311ef1d35b223ca5f672cfa67a038e43d258844be37429ef7a0168f7`. It was extracted into `out/byor-motu-restore-single-package-v1`; its manifest, README and `SOL_PROMPT.md` were checked. Only its five new Python files under `tools/` were installed. The repository README and package reference files were not copied over repository files.

## Native measurements

The default real source sequence retains the original epoch-2 READY latch, executes JOY1 UP through the native source owner, seals epoch 3, commits the original epoch-2 picture, then renders and commits epoch 3. The two source pictures still differ by 1,816 RGB555 pixels.

| Interval | Accepted bitmap renderer: clocks / ms / fields | Single-pass candidate: clocks / ms / fields |
|---|---:|---:|
| Epoch-2 restoration pass | Not separately instrumented | 463,814 / 21.595575 / — |
| Epoch-3 restoration pass | Not separately instrumented | 470,892 / 21.925133 / — |
| Epoch-3 bitmap construction | 1,407,502 / 65.534493 / — | 1,407,502 / 65.534493 / — |
| Epoch-3 BhPrepare | 1,927,298 / 89.736638 / — | 1,926,876 / 89.716989 / — |
| Epoch-2 publication | 11,632,626 / 541.624983 / 32 | 9,845,860 / 458.431635 / 27 |
| Epoch-3 publication | 17,751,938 / 826.545366 / 49 | 14,535,590 / 676.789462 / 40 |

Epoch-3 publication improves 18.118% in native master clocks. Both acceptance gates pass in the default case: epoch 3 is below 49 fields and 17,751,938 clocks; epoch 2 is below 32 fields with no latency regression. The synthetic instruction reduction is not used as a native speedup measurement.

Restoration timing runs from the first `NbRestorePlan` entry to `NbActorPlanStart` (or the actual retry/abort boundary on failure). It includes allocation and record lookup/remapping, excludes the preceding pressure gate/predictor, and does not include BhPrepare. Each successful pass visits exactly 1,024 map cells in order. Epoch 2 performs 15 record-home probes; epoch 3 performs 45. Bitmap timing runs from `BhBitmapLeaseBegin` to `BhBitmapBuilt`; it is included within BhPrepare, which is measured from entry through the `BhPrepareOK` epilogue label. BhPrepare excludes its caller JSR and final return epilogue, matching the accepted measurement. Publication includes the full existing start-to-visible interval. These intervals overlap and must not be added together.

The immutable bitmap construction itself is unchanged. Its small BhPrepare elapsed-time difference is recorded rather than attributed to an algorithm change.

## Source, residency and stack ownership

Epoch 3 retains 95 actor tiles and ten restored backdrop identities. The restoration records remain ordered:

```text
417 -> 596   418 -> 597   423 -> 598   514 -> 599   530 -> 600
552 -> 601   574 -> 602   575 -> 603   576 -> 604   584 -> 605
```

The complete plan still reserves 64 tails and the same first 41 invalid homes:

```text
297 298 299 327 328 329 356 357 358 359 360 361 387 388 389
390 391 392 393 417 418 419 420 421 422 423 512 513 514 524
525 526 529 530 544 545 550 552 574 575 576
```

There are 105 physical reservations, 639 final referenced slots and no new default-path immutable-home invalidations. The transfer workload stays 105 pairs in 18 preload batches: 8,400 CHR bytes plus 4,096 paired-map bytes, 212 DMA descriptors.

Poppy verifies the main loop is 54 bytes and the resolver 140 bytes, replacing the original 141-byte block for a net 53-byte increase. `NbCodeEnd` is `$39A64D`, below `$39B000`, and the extension is verified zero-filled in the accepted ROM. The 296 audited branch sites and independent machine-byte comparisons pass. The source and bitmap helper sizes remain unchanged. Every ROM byte outside the established transaction ranges is identical to the accepted authorities.

`RpResolveRestore` is entered and left with JMP. Its `NbFree` JSR therefore retains the original unwind depth when allocation exhaustion removes that return address and jumps to retry/abort. A/X and existing DP `$30/$2C/$70` are scratch; Y, DP, DBR and stack depth are preserved. The original `$18` cell cursor, `$2E` tail cursor, 48 records and pending-map outputs retain their lifetimes. The split records remain at `$003480..$0034FF` and `$42D620..$42D65F`; queue, source latch and home journal ownership are unchanged. Both CPUs' physical write guards remain installed under the accepted isolated-service configuration; this is not SA-1 coexecution.

The read-only native observers verify ordered cell visitation, record probes/order, completed-map equality with an independent eager-planner oracle, frozen committed maps/references, current-cell-only private map writes, and no queue/latch/journal writes during restoration. A rejected pre-DMA map is checked against the correct visited-prefix invariant. Unvisited cells need not equal the old eager planner's intermediate map; the unchanged retry/abort must discard that private map and restore the same final state. Existing historical auditors are not edited or weakened.

The retained eight native cases exercise graphics rejection/rollback after completed restoration plans. Allocation-exhaustion unwind, the 49th-record rejection and rejected-restoration prefix cases are covered by the supplied encoded-instruction and trace tests; those offline checks are not represented as additional native fault runs.

## Integration correction

The supplied native observer joined callback bodies directly to Lua `end`, producing tokens such as `1end`/`endend`. The first native attempt stopped at cold initialization with a retained Lua syntax error in `out/byor-motu-restore-single-v1/success/native/mesen.log`. The new adapter now inserts a separating space; the adapter test explicitly rejects those concatenations. The planner, its machine-byte executor and algorithm tests remain byte-identical to the ZIP. No native or Lua fault is filtered. A second adapter correction makes returned record pairs JSON-native lists: aggregation previously compared saved lists with freshly reconstructed tuples and rejected the identical RIGHT trace. The exact equality assertion remains in place, with a new serialization round-trip regression test. This correction affects receipt values only; ROM bytes and native captures are unchanged. Certified runs use the fresh directory `out/byor-motu-restore-single-v2`.

## Certification and preservation

**BYOR_MOTU_RESTORATION_SINGLE_PASS_PASS.** The eight native cases verify **807 continuously visible fields / 46,276,608 RGB555 pixels**, with zero pixel mismatches, resource faults or unsafe operations. Brightness remains 15 throughout warm transactions. All source snapshots, completed pending/committed maps, reference directories and palettes match their accepted bitmap controls. Supplemental checks also compare every displayed map and referenced HIGH/LOW CHR pair at retained checkpoints byte-for-byte with those controls; full 64-KiB DMA replay is independently checked against each run's own initial VRAM. Unreferenced power-on VRAM residue is not assumed identical across emulator instances.

| Case | Visible fields | Verified pixels | Native outcome |
|---|---:|---:|---|
| Default UP | 105 | 6,021,120 | Epochs 2 and 3 publish; 27 and 40 publication fields |
| Valid home / later IDLE | 138 | 7,913,472 | Epoch 3 publishes in 41 fields; source-owned IDLE epoch 4 restores home 204 into tail 634 and publishes in 27 fields |
| Early rollback | 97 | 5,562,368 | Previous picture retained; valid-home restoration fenced |
| READY rollback | 105 | 6,021,120 | Previous picture and references retained |
| Partial queue | 103 | 5,906,432 | Incomplete queue rejected; previous picture retained |
| Stale epoch | 105 | 6,021,120 | Previous picture retained |
| Insufficient budget | 84 | 4,816,896 | Rejected before transaction-3 DMA |
| RIGHT control | 70 | 4,014,080 | Original source safe-point, projected noop and LEFT retention pass; publication improves from 32 to 27 fields |

The suite records 24 completed restoration passes: 24,576 ordered map-cell visits and 695 record-home probes. Every pass visits exactly 1,024 cells. Bitmap membership/lifetime checks, physical slot reservations, full physical VRAM replay, paired completion fences, stale/rollback/partial-queue guards and original latch checks remain active. The measured minimum complete-batch VBlank margin is **33,946 master clocks**, above the retained 10,000-clock requirement. Default map-completion margins are **15,062 clocks** for epoch 2 and **14,704 clocks** for epoch 3; the suite minimum is 14,704. Actual per-batch and per-map measurements are retained in the receipt, rather than inherited from earlier instruction schedules.

All **184 accepted focused tests** pass, including 76,800 reference comparisons. All 26 supplied tests pass; the additional JSON round-trip regression makes 27 new tests, for **211 passing focused tests** total. Logs and hashes are retained in the package scratch directory and receipt. All 29 inherited dirty files, including the protected 17, remain byte-identical. The unrelated prompt-file deletion remains unstaged. No existing compiler, bitmap planner or historical auditor is edited.

The candidate is `out/byor-motu-restore-single-v2/success/native/bor.sfc`, SHA256:

```text
f1f03464e47d9736ceb2af6b66067bea76960c09e9dd3880795fd1f46b6aa81e
```

Fresh original/disabled builds reproduce all four accepted hashes:

| Private control output under `out/` | SHA256 |
|---|---|
| `byor-motu-restore-single-control-bitmap-v1/native/bor.sfc` | `487be884b06db56ad3755feb5a3549b85837f0965d58459d0949ab3b0f92a52d` |
| `byor-motu-restore-single-control-home-v1/native/bor.sfc` | `061c574cb37a0d8dfabe731bb1fb8685610a091ec3b7d48fdb46ed9aabf38fda` |
| `byor-motu-restore-single-control-safe-v1/native/bor.sfc` | `7cf213a9aaa467c7c1248dc0e40d35027f8dbd56a6ac3e9f81d373d216cc431b` |
| `byor-motu-restore-single-control-conditional-v1/native/bor.sfc` | `9ccbb5310ceb73f97ba6bdcfddfeeedb98f0378c448c8c0e98f543581c6ddeea` |

Exact original build commands are recorded in the committed receipt. They use only private output directories and existing media.

## Reproduction

Run from the repository root. Use a fresh output directory for a new native suite; cases must remain serial.

```powershell
$env:PYTHONPATH='.;tools/bor_compile;tools/verify'
$env:MESEN_EXE='E:/gh/Mesen2-mcp-frameexact/bin/win-x64/Release/Mesen.exe'
python -m unittest test_restore_single_pass test_restore_single_pass_adapter -v
python tools/verify/m4_restore_single_pass_native.py --output out/byor-motu-restore-single-NEW --suite
# Re-certify retained native output without executing another source step:
python tools/verify/m4_restore_single_pass_native.py --output out/byor-motu-restore-single-v2 --collect-suite
```

The standalone runner is the opt-in path. Existing compiler/default commands remain unchanged. Native folders retain every visible-field screenshot and physical VRAM capture, source snapshots/oracles, DMA payloads/fences, bitmap evidence, restoration-pass traces and unfiltered logs. The reproducible aggregate is `out/byor-motu-restore-single-v2/single-pass-receipt.json`; the committed handoff is `docs/receipts/byor-motu-restore-single-pass.json`.

No 30-FPS, 200-Hz world scheduling, SA-1 coexecution, audio, HUD, combat or Demo claim. Even after this optimization, the default second publication takes about 677 ms.

The accepted 184-test command is:

```powershell
python -m unittest test_home_borrow_bitmap test_home_borrow_bitmap_adapter test_m4_home_borrow test_m4_source_safepoint test_m4_conditional_capacity test_early_capacity test_m4_early_capacity_component test_restore_spill test_m4_restore_spill_component test_batch_rescue test_generated_splice test_m4_nonblank_batch_component test_m4_nonblank_component test_rect_map_opt test_m4_rect_map_component test_direct_pair_dma test_m4_direct_pair_component test_m4_native_cost_accounting test_tile_fusion test_m4_tile_fusion_component test_phase_occupancy test_m4_occupancy_component test_m4_opaque_component test_m4_online_component test_m4_live_ground_component test_component_live_bundle test_m4_component_publication test_bg_component_residency test_bg_component_deadlines test_bg_components -q
```
