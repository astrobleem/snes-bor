# BYOR MOTU native cost attribution

`BYOR_MOTU_NATIVE_COST_ATTRIBUTION_PASS`: profiling only, no optimization.
The profiled ROM is byte-for-byte the certified fused renderer from commit
`395b74daf08976f23c052702948809009b4003fe`:
`out/byor-motu-cost-profile-v3/native/bor.sfc`, SHA256
`01b757d34ec1ad568758d325678b63bb96ad2f5b87badedae4ee65e1ac711977`.
No program, asset, palette, resource lease or game behavior bytes changed.
Only the external Lua observer and host measurement driver changed. The entire
18-epoch macro timing record and previous helper timing record exactly match
`out/byor-motu-tile-fusion-v2/result.json`, including absolute master clocks.

The missing **75.256585 ms / 1,616,306 master clocks** occurs in epoch 17,
not the epoch with the largest composition/publication time. **100% is scoped
and reconciled**, with zero unknown interval residual. Named routines and inline
copies explain **84.7785%**; explicit caller-loop/setup regions explain the
remaining **15.2215% / 11.455180 ms / 246,026 clocks**. Those glue regions are
localized spans, not claims of individually attributed opcode costs.

## Ranked hotspots in the formerly-other work

The following warm maxima are ranked by *exclusive contribution outside*
preflight, composition and DMA. Maxima may come from different epochs.

| Hotspot | Master clocks | ms | Epoch | Reason |
|---|---:|---:|---:|---|
| WarmStage | 648,060 | 30.174226 | 17 | Copies every changed/restored 80-byte pair into staging via two MVNs, plus destination and run bookkeeping |
| WarmSparseMaps | 274,408 | 12.776670 | 17 | Scans the full 1,024-word map and extends changed ranges; child map DMA setup/transfer excluded |
| WarmCopyBackdrop | 143,060 | 6.660996 | 17 | Copies 30 evicted immutable HIGH/LOW home pairs from ROM into scratch |
| RestoreLoopGlue | 131,380 | 6.117165 | 17 | Tests pending slots/refcount flags across all 345 old/new-union cells, plus call/branch/flag-update overhead |
| MapCommitMVN | 109,736 | 5.109402 | several | Copies all 2,048 pending map bytes back into the committed map every changed epoch |

Additional maxima:
TileIterationTransferGlue 5.024288 ms / 107,908 clocks, WarmCompare 3.715835 ms /
79,806 clocks, WarmAdvance's restoration-only contribution 3.551382 ms / 76,274
clocks, WarmFlush CPU setup 2.109858 ms / 45,314 clocks, and map DMA submission
1.419547 ms / 30,488 clocks. The preflight portion of WarmAdvance is already
inside preflight and is not counted again in the missing time.

**Recommended next target: WarmStage**, at
`tools/verify/m4_opaque_warm_publisher.py:95`, native `39:D050`.
Epoch 17 stages 126 pairs / 10,080 bytes. Its two MVNs account for
**25.127961 ms / 539,680 clocks**, or 83.276% of its exclusive cost. The rest is
run checks, source/destination arithmetic, stack/bank saves and call overhead.
Astra should design a producer/staging ABI that avoids or replaces those
scratch-to-upload copies while preserving exact physical VRAM comparison,
coalescing, residency and publication fences. **No replacement is implemented.**

## Exact epoch-17 residual ledger

Production is **4,859,208 clocks / 226.248867 ms**. It equals the measured
preflight/allocation interval, composition interval, DMA intervals and the
formerly-other ledger below. The machine receipt contains the exact macro
clock values and non-overlapping attributed categories. Its preflight category
subtracts separately observed NMI service; that service must not be added again
to the inclusive preflight macro interval.

| Formerly-other category | Clocks | ms |
|---|---:|---:|
| WarmStage | 648,060 | 30.174226 |
| WarmSparseMaps | 274,408 | 12.776670 |
| WarmCopyBackdrop | 143,060 | 6.660996 |
| RestoreLoopGlue | 131,380 | 6.117165 |
| MapCommitMVN_398AA0 | 109,696 | 5.107539 |
| TileIterationTransferGlue | 107,908 | 5.024288 |
| WarmAdvance | 76,034 | 3.540208 |
| WarmFlush | 45,314 | 2.109858 |
| WarmCompare | 43,220 | 2.012360 |
| WarmMapDmaHigh | 30,488 | 1.419547 |
| SnapshotValidationProjection | 5,374 | 0.250218 |
| BlankSetup | 828 | 0.038552 |
| PostBootstrapSetup | 328 | 0.015272 |
| MapCommitGlue | 208 | 0.009685 |

Ledger sum: **1,616,306 clocks / 75.256585 ms**. Unassigned residual:
**0 clocks / 0.000000 ms**. The 345-cell restoration loop is conservative union
work; only 30 cells need backdrop copies. WarmStage runs for those 30 restores
and all 96 changing actor pairs. Physical comparison exits early on the first
mismatching word; unchanged pairs can require all 32 HIGH and 8 LOW word reads.
It does not account for tens of milliseconds in this epoch.

Nested example: WarmStage inclusive elapsed is **35.685262 ms**, while exclusive
active cost is **30.174226 ms**. The difference contains nested WarmFlush CPU
work and DMA; adding its inclusive cost to WarmFlush or DMA would double count.
WarmSparseMaps inclusive elapsed is **14.519909 ms**, versus **12.776670 ms**
exclusive; its 64 child submissions transfer 464 map bytes. WarmFlush performs
62 CHR DMA descriptors / 10,080 bytes and costs **2.109858 ms CPU/bus-active**
plus **4.005165 ms** measured DMA. Combined epoch DMA is 126 descriptors /
10,544 bytes / 4.328856 ms.

## Per-epoch phase reconciliation

All values are milliseconds. W/A/R are worklist, allocation and restoration
iteration counts. Tiles/rows are actually composed, not just rectangle candidates.
Blank is the first renderer-owned INIDISP=128 write through INIDISP=15.
The receipt additionally records each duration in native master clocks, DMA
bytes/descriptors, allocation details and exact per-routine call maxima.

| Epoch | W/A/R | Tiles/rows | Preflight+alloc | Composition | DMA | Production | Publication | Formerly other | Actual blank | Unknown clocks/ms |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 165/165/165 | 80/640 | 45.251 | 78.973 | 22.755 | 195.852 | 205.356 | 48.874 | 159.862 | 0 / 0.000 |
| 1 | 253/253/253 | 103/824 | 43.851 | 103.747 | 3.811 | 214.364 | 224.047 | 62.955 | 179.935 | 0 / 0.000 |
| 2 | 207/207/207 | 102/816 | 40.508 | 102.378 | 3.383 | 205.336 | 214.243 | 59.067 | 173.458 | 0 / 0.000 |
| 3 noop | 0/0/0 | 0/0 | 0.000 | 0.000 | 0.000 | 0.276 | 0.276 | 0.276 | 0.000 | 0 / 0.000 |
| 4 | 207/207/207 | 103/824 | 40.527 | 103.913 | 3.570 | 206.243 | 214.243 | 58.234 | 173.439 | 0 / 0.000 |
| 5 noop | 0/0/0 | 0/0 | 0.000 | 0.000 | 0.000 | 0.276 | 0.276 | 0.276 | 0.000 | 0 / 0.000 |
| 6 | 207/207/207 | 102/816 | 39.174 | 102.989 | 3.467 | 203.082 | 214.246 | 57.452 | 174.796 | 0 / 0.000 |
| 7 noop | 0/0/0 | 0/0 | 0.000 | 0.000 | 0.000 | 0.276 | 0.276 | 0.276 | 0.000 | 0 / 0.000 |
| 8 | 207/207/207 | 102/816 | 40.508 | 102.428 | 3.393 | 205.289 | 214.248 | 58.961 | 173.463 | 0 / 0.000 |
| 9 | 345/345/345 | 95/760 | 52.132 | 93.110 | 4.179 | 222.873 | 224.839 | 73.451 | 172.448 | 0 / 0.000 |
| 10 | 345/345/345 | 104/832 | 49.927 | 104.384 | 4.255 | 230.866 | 239.835 | 72.301 | 189.648 | 0 / 0.000 |
| 11 noop | 0/0/0 | 0/0 | 0.000 | 0.000 | 0.000 | 0.275 | 0.275 | 0.275 | 0.000 | 0 / 0.000 |
| 12 noop | 0/0/0 | 0/0 | 0.000 | 0.000 | 0.000 | 0.275 | 0.275 | 0.275 | 0.000 | 0 / 0.000 |
| 13 noop | 0/0/0 | 0/0 | 0.000 | 0.000 | 0.000 | 0.275 | 0.275 | 0.275 | 0.000 | 0 / 0.000 |
| 14 | 345/345/345 | 93/744 | 52.092 | 91.479 | 4.195 | 221.600 | 224.838 | 73.834 | 172.488 | 0 / 0.000 |
| 15 | 345/345/345 | 104/832 | 49.927 | 104.388 | 4.201 | 231.014 | 240.665 | 72.499 | 190.478 | 0 / 0.000 |
| 16 | 207/207/207 | 108/864 | 40.575 | 108.448 | 3.617 | 212.077 | 214.254 | 59.438 | 173.404 | 0 / 0.000 |
| 17 | 345/345/345 | 96/768 | 52.139 | 94.525 | 4.329 | 226.249 | 226.332 | 75.257 | 173.935 | 0 / 0.000 |

## Routine invocation counts and exclusive costs

Each cell is **calls / exclusive active milliseconds**. WarmAdvance here
includes preflight, allocation and restoration; only its restoration part is
in the formerly-other ledger. All six noops have zero calls to these routines.
Inline MVN time remains inside its owning routine's exclusive cost and is
reported separately only as a diagnostic subset.

| Epoch | WarmStage | WarmCopyBackdrop | WarmSparseMaps | WarmCompare | WarmFlush | WarmAdvance |
|---|---:|---:|---:|---:|---:|---:|
| 0 | 80 / 19.159 | 0 / 0.000 | 1 / 12.342 | 80 / 1.660 | 17 / 1.089 | 495 / 5.218 |
| 1 | 111 / 26.576 | 8 / 1.774 | 1 / 12.656 | 103 / 1.922 | 24 / 1.638 | 759 / 8.011 |
| 2 | 103 / 24.658 | 4 / 0.889 | 1 / 12.265 | 102 / 3.306 | 22 / 1.489 | 621 / 6.688 |
| 4 | 104 / 24.890 | 1 / 0.221 | 1 / 12.690 | 103 / 1.881 | 20 / 1.363 | 621 / 6.711 |
| 6 | 104 / 24.902 | 2 / 0.445 | 1 / 12.396 | 102 / 2.075 | 21 / 1.424 | 621 / 6.702 |
| 8 | 99 / 23.694 | 2 / 0.443 | 1 / 12.631 | 102 / 3.716 | 22 / 1.493 | 621 / 6.685 |
| 9 | 122 / 29.231 | 27 / 5.991 | 1 / 12.720 | 95 / 2.153 | 29 / 1.974 | 1035 / 10.608 |
| 10 | 124 / 29.701 | 21 / 4.659 | 1 / 12.715 | 104 / 2.293 | 28 / 1.894 | 1035 / 10.617 |
| 14 | 122 / 29.220 | 29 / 6.425 | 1 / 12.710 | 93 / 2.084 | 29 / 1.976 | 1035 / 10.636 |
| 15 | 122 / 29.223 | 21 / 4.659 | 1 / 12.712 | 104 / 2.998 | 28 / 1.897 | 1035 / 10.604 |
| 16 | 108 / 25.849 | 1 / 0.223 | 1 / 12.517 | 108 / 2.635 | 20 / 1.363 | 621 / 6.703 |
| 17 | 126 / 30.174 | 30 / 6.661 | 1 / 12.777 | 96 / 2.012 | 31 / 2.110 | 1035 / 10.645 |

Epoch 17 detailed call statistics below illustrate inclusive/exclusive and
maximum individual call costs. JSON supplies these same fields for every epoch.
Own DMA columns belong to that routine directly; parent inclusive DMA fields
in JSON also include children and must not be added to child DMA fields.

| Routine | Calls | Inclusive ms | Exclusive ms | Max inclusive call ms | Max exclusive call ms | Own DMA bytes/descriptors |
|---|---:|---:|---:|---:|---:|---:|
| WarmStage | 126 | 35.685262 | 30.174226 | 0.803547 | 0.243606 | 0/0 |
| WarmSparseMaps | 1 | 14.519909 | 12.776670 | 14.519909 | 12.776670 | 0/0 |
| WarmCopyBackdrop | 30 | 6.660996 | 6.660996 | 0.222654 | 0.222654 | 0/0 |
| WarmCompare | 96 | 2.012360 | 2.012360 | 0.078874 | 0.078874 | 0/0 |
| WarmFlush | 31 | 6.115023 | 2.109858 | 0.563666 | 0.071424 | 10080/62 |
| WarmAdvance | 1035 | 10.644835 | 10.644835 | 0.022629 | 0.022629 | 0/0 |
| WarmSourcePresence | 225 | 8.868446 | 8.868446 | 0.040135 | 0.040135 | 0/0 |
| OnlineRowPointers | 96 | 6.351087 | 6.351087 | 0.067886 | 0.067886 | 0/0 |
| WarmMapDmaHigh | 64 | 1.743238 | 1.419547 | 0.032220 | 0.023374 | 464/64 |
| AstraOpaqueTile | 96 | 86.021734 | 86.021734 | 1.054231 | 1.054231 | 0/0 |
| NMI | 3 | 0.045816 | 0.045816 | 0.015272 | 0.015272 | 0/0 |

## Fused tile routine: same-epoch breakdown

At epoch 16, 108 tiles / 864 rows are composed. The original entry-to-AstraTileDone
body is **2,107,822 clocks / 98.141989 ms**, and blending is **924,246 clocks /
43.033682 ms**. Their same-epoch difference is **1,183,576 clocks / 55.108308 ms**,
fully attributed to masks, addressing, pointer progression and control below.
The new full-call boundary also measures final PLY/PLX/PLP/RTL: **16,032 clocks /
0.746464 ms**, giving **2,123,854 clocks / 98.888453 ms** for the full routine.
These are nested subsets; do not add them to whole composition again.

| Tile region | Invocations | Clocks | ms | Maximum region clocks |
|---|---:|---:|---:|---:|
| tile_setup | 108 | 17,248 | 0.803082 | 196 |
| foreground_mask | 864 | 406,488 | 18.926428 | 502 |
| source_row_pointer | 864 | 204,880 | 9.539387 | 270 |
| blend_body | 864 | 924,246 | 43.033682 | 1472 |
| row_pointer_progression | 864 | 433,912 | 20.203313 | 528 |
| row_loop_control | 864 | 121,048 | 5.636098 | 178 |
| tile_register_restore | 108 | 16,032 | 0.746464 | 184 |

Foreground_mask runs AstraTileNextRow through AstraTileNoSource: clipping,
foreground byte load, duplicated inverse mask and source opacity intersection.
Source_row_pointer runs AstraTileNoSource through AstraTileRow: 24-bit source
pointer +2, carry and row X calculation. Row_pointer_progression runs
AstraTilePixelDone through `inc $1E`: signed-Y source stepping, foreground index,
and 24-bit backdrop progression. Row_loop_control is `inc $1E` through the next
row or AstraTileDone. Tile setup/restoration cover the register and counter ABI.
OnlineRowPointers is measured separately once per composed tile and is already
part of the enclosing composition interval. No foreground/read arithmetic is
silently assigned to the blend-only category.

## Publication, NMI and cold work

OnlineBlank through OnlineComplete covers blanked production including maps,
restoration, composition, compare/stage/flush and final map commit. The per-epoch
blanked-production interval is production minus the measured admission-to-blank
prefix; actual blank additionally includes commit and presentation polling.
The receipt supplies start/complete/publication and register-boundary clocks.

OnlineComplete to OnlineVblank commits bounds, keys, immutable generations and
the displayed epoch. OnlineVblank repeatedly reads $4212 until VBlank; this is
**busy CPU polling, not WAI, DMA or an interrupt wait**. It is outside the
production interval and therefore cannot explain the missing 75 ms.

| Epoch | Authority/epoch commit ms | VBlank busy-poll ms | Poll-loop iterations |
|---|---:|---:|---:|
| 0 | 0.075149 | 9.428759 | 2586 |
| 1 | 0.075149 | 9.607739 | 2635 |
| 2 | 0.075149 | 8.831662 | 2422 |
| 4 | 0.075149 | 7.924471 | 2173 |
| 6 | 0.077012 | 11.087256 | 3041 |
| 8 | 0.075149 | 8.883066 | 2436 |
| 9 | 0.075149 | 1.891116 | 518 |
| 10 | 0.075149 | 8.893682 | 2439 |
| 14 | 0.075149 | 3.163344 | 867 |
| 15 | 0.075149 | 9.575891 | 2626 |
| 16 | 0.075149 | 2.101943 | 576 |
| 17 | 0.077012 | 0.005774 | 1 |

Cold epoch 0 has three unowned legacy NMI service calls, **1.466387 ms**, inside
preflight. Its map/refcount initialization copies 2,048 + 1,536 bytes, then the
normal pending-map copy adds another 2,048 bytes. Their active MVN costs are
5.107539, 3.835031 and 5.109402 ms, all inside preflight. The cold bootstrap
itself is **20.346627 ms inclusive**, containing **20.078902 ms DMA** for six
bootstrap descriptors / 52,288 bytes and **0.267725 ms** register/setup activity.
Warm epochs have no cold bootstrap. Warm NMI service is zero or three
calls (0 or 0.045816 ms), always within preflight; NMI is disabled for
blanked production. It is not the 75-ms problem.

## Locations and measurement boundaries

- WarmStage/WarmFlush: `tools/verify/m4_opaque_warm_publisher.py:95` and `:101`,
  native 39:D050 and 39:D09C. Stage MVNs at D07F/D095 copy HIGH/LOW into C800/CC00.
- WarmCopyBackdrop: same file `:93`, native 39:D029; MVNs D039/D04B read E0/E1
  into D680/D6C0 scratch. Their epoch-17 cost is 6.000763 ms of the 6.660996 ms.
- WarmSparseMaps/WarmMapFind/WarmMapExtend: same file `:115`, native
  39:D171/D176/D18E; aliases WarmMapDmaHigh and WarmMapDmaLow share 39:D1CC.
- WarmCompare: same file `:110`, native 39:D125, word loops D137/D15C and early
  mismatch exit D16F.
- WarmAdvance: same file `:90`, native 39:D000; called three times per union cell.
- WarmRestore: same file `:72`, native label in the retained publisher; its
  measured glue excludes WarmAdvance, copying, staging, flush and DMA.
- Map commit: same file `:85`, MVN at 39:8AA0; pending C000 to committed C800.
- Frame key and release: same file `:86`,
  `tools/verify/m4_opaque_component_publisher.py:107`, and
  `tools/verify/m4_online_component_publisher.py:166`/`:167`.
- Fused regions: `tools/bor_compile/tile_fusion.py:48`, native 39:E200..E320;
  initial source/background addressing in
  `tools/verify/m4_opaque_component_publisher.py:115`, native OnlineRowPointers.

The profiler discovers direct calls from the immutable machine bytes and
checks their counts against the retained assembly. Routine exits are actual
caller return instruction fetches; entry records read only the native stack.
Nested calls, MVN blocks and DMA form non-overlapping active-owner intervals.
NMI returns are validated by restored PC and SP, including returns to an
already registered MVN/loop point. Open calls, mismatched macro sums or altered
source/DMA identities fail closed. Routine inclusive time includes child calls,
DMA and observed interrupt service; exclusive active excludes all three.
MVN and fused-region diagnostics remain subsets of their owning routines.

Measurement limits are explicit: CPU/bus-active master clocks include memory
access waits and DRAM refresh, not nominal instruction-only cycles. OnlineNmi
is observed after hardware/vector dispatch; that small dispatch interval is not
separately resolved and remains within the scoped preflight region. DMA uses
the same first-post-DMA instruction fence as the control, including that
instruction. Scoped caller glue is not individually split by opcode, and its
maximum individual loop-iteration cost is not claimed. **No unassigned elapsed
interval remains**, but this is not a claim of exact electrical CPU-cycle or
interrupt-dispatch timing.

## Verification and reproduction

One complete final profiling run uses the exact 18 controller epochs. All
1,032,192 source RGB555 pixels match independently composed source frames,
screenshots and decoded VRAM. Snapshots, occupancy, CGRAM, committed directory,
expected frames and actual DMA packets match the retained fused control.
Independent full DMA replay verifies 1,179,648 physical VRAM bytes. Noops
3,5,7,11,12,13 have zero graphics calls/work/blank. Invalid LEFT retains the
previous full VRAM and display. Resource faults and unsafe PPU writes are zero.
All 61 focused tests pass, including nested DMA/NMI accounting and failure of
unresolved return traces. All 29 inherited dirty files, including the protected
17, remain byte-identical. No old control ROM was rerun or rebuilt.

Profiling slows host execution enough to hit Mesen's 233-ms single-frame wall
cap. The driver retries only the unadvanced remainder with verified contiguous
frame counters; it never adds simulation frames or changes input ordering.
There were 141 capped step attempts in this run. The macro/helper clock records
still exactly match the control. Earlier attempts are retained: v1 exposed
legacy preflight INIDISP writes and a step cap; v2 passed all pixels but its
ledger rejected a missed NMI return probe. Corrected read-only probes produced
v3. These were measurement integration issues, not optimization or external
limits. Raw events, observer, resolved probe plan and artifact hashes are in
`docs/receipts/byor-motu-native-cost-attribution.json`.

```powershell
$env:PYTHONPATH='.;tools/bor_compile;tools/verify'
$env:MESEN_EXE='E:/gh/Mesen2-mcp-frameexact/bin/win-x64/Release/Mesen.exe'
out/byor-motu-solver-venv/Scripts/python.exe tools/verify/m4_native_cost_attribution.py --output out/byor-motu-cost-profile-NEW --warm --occupancy out/astra-occupancy-assets-v1 --tile-fusion
out/byor-motu-solver-venv/Scripts/python.exe -m unittest test_m4_native_cost_accounting -v
```

Use a fresh output directory and retained assets/source PAK/MSU. The driver
copies the certified ROM, symbols and source bootstrap, hardlinks MSU, appends
read-only probes, runs the existing sequence and writes the complete attribution.
No optimization, seamless/30-Hz scheduling, SA-1 migration, general alpha,
breath, HUD, combat, audio timing or full MOTU Demo work was undertaken.
