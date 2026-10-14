# Rectangle-bounded native tilemaps

BYOR_MOTU_RECT_MAP_DIFF_PASS

Candidate: `E:\gh\snes-bor\out\byor-motu-rect-map-v1\native\bor.sfc`
SHA256: `52872d1546c26d2d9a0be438aaae32bb4ac764c74dc2a6b5a3632f90d4a179c0`

Opt-in `--rect-map-diff` scans the inclusive clipped previous/current actor union and commits only those row spans after the existing map-DMA and flush fences. It requires warm residency, occupancy, fused tiles and direct-pair DMA. The certified default remains unchanged.

Worst warm production: **207.137 -> 197.223 ms (4.786% reduction)**. Every changing warm epoch improves, exceeding the 2% gate. Worst publication: 208.204 -> 207.384 ms. Worst forced blank: 157.203 -> 157.197 ms. VBlank release alignment limits the latter maxima; this is not gameplay-rate presentation.

## Paired native measurements

All durations are milliseconds. Scan and commit show inclusive / exclusive cost. Exclusive scan excludes measured map DMA fences; commit has no DMA. Both execute once per changing epoch and zero times per noop. Routine entry through actual caller return fetch is measured. Control commit spans PHB through PLB and ends at OnlineComplete. DMA fences include the first post-DMA instruction, consistently with the established driver. NMI is disabled during forced-blank production. No timing instructions or ROM instrumentation were added. The unchanged direct-DMA control macro costs match its retained baseline exactly. Exact clocks, DMA totals and descriptors are in the JSON receipt.

| Epoch | Scan before -> after (incl / excl) | Commit before -> after | Preflight before -> after | Composition before -> after | DMA before -> after | Other before -> after | Production before -> after | Publication before -> after | Blank before -> after | Map bytes / descriptors |
|---:|---|---|---|---|---|---|---|---|---|---|
| 0 | 13.205 / 13.052 -> 3.743 / 3.587 | 5.115 / 5.115 -> 1.159 / 1.159 | 45.251 -> 45.251 | 78.975 -> 78.977 | 23.044 -> 23.047 | 33.110 -> 19.695 | 180.381 -> 166.970 | 188.715 -> 172.078 | 143.220 -> 126.583 | 216 / 32 |
| 1 | 14.195 / 13.896 -> 5.989 / 5.687 | 5.115 / 5.115 -> 1.770 / 1.770 | 43.851 -> 43.851 | 103.739 -> 103.739 | 4.219 -> 4.208 | 40.951 -> 29.413 | 192.761 -> 181.211 | 192.842 -> 190.770 | 148.730 -> 146.658 | 452 / 56 |
| 2 | 12.959 / 12.833 -> 4.245 / 4.122 | 5.115 / 5.115 -> 1.540 / 1.540 | 40.508 -> 40.508 | 102.373 -> 102.373 | 3.748 -> 3.762 | 38.688 -> 26.388 | 185.317 -> 173.030 | 197.606 -> 180.968 | 156.822 -> 140.183 | 160 / 26 |
| 3 | 0 / 0 -> 0 / 0 | 0 / 0 -> 0 / 0 | 0.000 -> 0.000 | 0.000 -> 0.000 | 0.000 -> 0.000 | 0.276 -> 0.276 | 0.276 -> 0.276 | 0.276 -> 0.276 | 0.000 -> 0.000 | 0 / 0 |
| 4 | 14.277 / 13.983 -> 5.481 / 5.185 | 5.115 / 5.115 -> 1.540 / 1.540 | 40.527 -> 40.527 | 103.918 -> 103.916 | 3.963 -> 3.966 | 37.789 -> 25.421 | 186.197 -> 173.831 | 197.608 -> 180.969 | 156.804 -> 140.165 | 420 / 58 |
| 5 | 0 / 0 -> 0 / 0 | 0 / 0 -> 0 / 0 | 0.000 -> 0.000 | 0.000 -> 0.000 | 0.000 -> 0.000 | 0.276 -> 0.276 | 0.276 -> 0.276 | 0.276 -> 0.276 | 0.000 -> 0.000 | 0 / 0 |
| 6 | 13.372 / 13.193 -> 4.613 / 4.436 | 5.115 / 5.115 -> 1.540 / 1.540 | 39.174 -> 39.174 | 102.991 -> 102.987 | 3.854 -> 3.853 | 36.948 -> 24.620 | 182.967 -> 170.635 | 183.048 -> 180.972 | 143.597 -> 141.521 | 244 / 36 |
| 7 | 0 / 0 -> 0 / 0 | 0 / 0 -> 0 / 0 | 0.000 -> 0.000 | 0.000 -> 0.000 | 0.000 -> 0.000 | 0.276 -> 0.276 | 0.276 -> 0.276 | 0.276 -> 0.276 | 0.000 -> 0.000 | 0 / 0 |
| 8 | 14.027 / 13.783 -> 5.257 / 5.011 | 5.113 / 5.113 -> 1.542 / 1.542 | 40.508 -> 40.508 | 102.432 -> 102.432 | 3.745 -> 3.733 | 39.298 -> 26.961 | 185.983 -> 173.634 | 197.606 -> 180.972 | 156.821 -> 140.187 | 340 / 52 |
| 9 | 14.358 / 14.053 -> 7.337 / 7.024 | 5.113 / 5.113 -> 2.229 / 2.229 | 52.132 -> 52.132 | 93.108 -> 93.107 | 4.599 -> 4.608 | 49.082 -> 39.181 | 198.922 -> 189.028 | 208.204 -> 191.556 | 155.813 -> 139.165 | 444 / 60 |
| 10 | 14.360 / 14.053 -> 7.332 / 7.021 | 5.115 / 5.115 -> 2.229 / 2.229 | 49.927 -> 49.927 | 104.375 -> 104.393 | 4.692 -> 4.692 | 47.650 -> 37.721 | 206.644 -> 196.733 | 206.725 -> 206.551 | 156.538 -> 156.364 | 452 / 60 |
| 11 | 0 / 0 -> 0 / 0 | 0 / 0 -> 0 / 0 | 0.000 -> 0.000 | 0.000 -> 0.000 | 0.000 -> 0.000 | 0.275 -> 0.275 | 0.275 -> 0.275 | 0.275 -> 0.275 | 0.000 -> 0.000 | 0 / 0 |
| 12 | 0 / 0 -> 0 / 0 | 0 / 0 -> 0 / 0 | 0.000 -> 0.000 | 0.000 -> 0.000 | 0.000 -> 0.000 | 0.275 -> 0.275 | 0.275 -> 0.275 | 0.275 -> 0.275 | 0.000 -> 0.000 | 0 / 0 |
| 13 | 0 / 0 -> 0 / 0 | 0 / 0 -> 0 / 0 | 0.000 -> 0.000 | 0.000 -> 0.000 | 0.000 -> 0.000 | 0.275 -> 0.275 | 0.275 -> 0.275 | 0.275 -> 0.275 | 0.000 -> 0.000 | 0 / 0 |
| 14 | 14.361 / 14.044 -> 7.329 / 7.017 | 5.113 / 5.113 -> 2.229 / 2.229 | 52.092 -> 52.092 | 91.481 -> 91.479 | 4.613 -> 4.601 | 49.470 -> 39.563 | 197.656 -> 187.735 | 208.200 -> 191.567 | 155.850 -> 139.217 | 468 / 60 |
| 15 | 14.363 / 14.040 -> 7.329 / 7.013 | 5.113 / 5.113 -> 2.229 / 2.229 | 49.927 -> 49.927 | 104.384 -> 104.373 | 4.628 -> 4.627 | 48.198 -> 38.296 | 207.137 -> 197.223 | 207.389 -> 207.384 | 157.203 -> 157.197 | 468 / 60 |
| 16 | 13.697 / 13.478 -> 4.944 / 4.729 | 5.113 / 5.113 -> 1.540 / 1.540 | 40.575 -> 40.575 | 108.437 -> 108.446 | 4.015 -> 4.023 | 38.287 -> 25.944 | 191.313 -> 178.988 | 197.603 -> 180.968 | 156.752 -> 140.118 | 284 / 44 |
| 17 | 14.523 / 14.196 -> 7.490 / 7.160 | 5.115 / 5.115 -> 2.229 / 2.229 | 52.139 -> 52.139 | 94.528 -> 94.512 | 4.740 -> 4.759 | 50.029 -> 40.110 | 201.436 -> 191.520 | 208.199 -> 191.602 | 155.802 -> 139.206 | 464 / 64 |

Epoch 17 scan exclusive: **304,896 -> 153,772 clocks (14.196 -> 7.160 ms)**; late map copy: **109,858 -> 47,870 clocks (5.115 -> 2.229 ms)**. Production: 4,326,304 -> 4,113,318 clocks. Map DMA remains 464 bytes / 64 descriptors. Cold production: 180.381 -> 166.970 ms; cold DMA: 58,904 bytes / 198 descriptors.

## Verification and ownership

**18 epochs, 1,032,192 independently source-composed RGB555 pixels, zero mismatches.** Source-world snapshots, palettes, residency directories and expected images are byte-identical to control. Foreground and backdrop restoration remain exact. Six projected-frame noops perform zero graphics work. Invalid LEFT retains VRAM, committed map and pixels. Zero unsafe PPU writes and resource faults.

Read-only probes capture pending/committed maps before scan, before late commit and after commit. No early committed mutation is allowed. Final pending and committed maps agree over all 2,048 bytes, including undrawn rows 28-31. Pending differences outside the union are rejected. Independently constructed row runs verify every HIGH/LOW map DMA descriptor and payload. Full DMA replay verifies all 65,536 VRAM bytes across 18 epochs (1,179,648 bytes). A/B resident and previously written bytes must agree; any differing untouched, unreferenced bootstrap bytes must equal their respective initial captures. Direct CHR packet lists remain identical.

Poppy: scan 39:D171, commit 39:D208, map DMA 39:D24F, final D000 routine end 39:D2C1: **319 bytes clear before D400**. No new resource allocation. Candidate-specific whole-ROM audit checks the exact source transformation, 1,624 unchanged instruction statements, required relocations, inserted Poppy bytes and every other ROM byte. D400 direct DMA, 175-byte row kernel, 289-byte fused tile routine, NMI, palettes, occupancy and F43000-F435FF refcounts are unchanged. The old direct-pair auditor is untouched; full committed-to-pending initialization is unchanged.

The retained emitter spells two long map operands in decimal. The fail-closed package guard accepts only those exact equivalent spellings; tests reject operand drift. **84 focused tests pass**, including 325 randomized generated-assembly interpreter cases, branch sizing, actual Poppy placement and forbidden asset/kernel/direct-DMA mutations. All **29 inherited dirty tracked files** match pre-edit SHA256 fingerprints. Native artifacts and their hashes are recorded in the receipt.

## Reproduction

Run from the repository root with the retained source PAK/assets and Poppy/Mesen toolchain. Use fresh private output directories.

```powershell
$env:PYTHONPATH='.;tools/bor_compile;tools/verify'
$env:MESEN_EXE='E:/gh/Mesen2-mcp-frameexact/bin/win-x64/Release/Mesen.exe'
$env:MOTU_RECT_CONTROL='out/byor-motu-rect-control-NEW'
python tools/verify/m4_rect_map_evidence.py --prepare-control $env:MOTU_RECT_CONTROL
python tools/verify/m4_opaque_component_native.py --output $env:MOTU_RECT_CONTROL --run-existing
python tools/verify/m4_opaque_component_native.py --output out/byor-motu-rect-map-NEW --warm --occupancy out/astra-occupancy-assets-v1 --tile-fusion --direct-pair-dma --rect-map-diff
python -m unittest test_rect_map_opt test_m4_rect_map_component -v
```

Remaining worst warm costs: composition 108.446 ms, preflight/allocation 52.139 ms, DMA 4.759 ms, other production 40.110 ms. Column maxima may belong to different epochs. No non-blank or seamless presentation, 30-Hz scheduling, SA-1 migration, general alpha, breath, HUD, combat, audio timing or complete MOTU Demo claim. Stop at this optimization milestone.
