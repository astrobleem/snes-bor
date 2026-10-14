# First non-blank native component transition

BYOR_MOTU_NONBLANK_PRESENTATION_SLICE_PASS

Candidate: `out\byor-motu-nonblank-v5\native\bor.sfc`
SHA256: `9f85b14626405c06295536e65b6f73a229849a6b6bebf0b99862792035f6130f`

**261 consecutive observed visible fields, 14,966,784 RGB555 pixels, zero mismatches.** Every field has a complete screenshot, physical VRAM capture, independent planar decode and full-transfer replay. Brightness stays 15; no intervening black, stale, partial or mixed-component frame. The authentic displayed change is persistent source He-Man from IDLE at x=80 to WALK at x=81, with 4,260 changed pixels. Cold, deferred and moved canonical snapshots are byte-identical to retained epochs 0, 1 and 2.

The first RIGHT request advances the source player to x=80.5 and produces a fully preloaded pending frame, then an injected READY-stage failure deliberately retains the original display. The second RIGHT advances the same actor to x=81 and commits its new picture. Actual LEFT then changes the source direction to unsupported artwork and is rejected without DMA or display corruption. Fault injection changes only the experimental transaction control word; the host never writes graphics, maps, actors or source positions.

## Ownership and state model

`VISIBLE (0) -> PREPARING (1) -> PRELOADING (2) -> READY (3) -> COMMITTING (4) -> VISIBLE (0)`; rejected transactions also return to VISIBLE and report the retained fixture fault flag.

The source seals the canonical snapshot before native presentation begins. A synchronous single producer holds the transaction lock: source updates and new allocations cannot execute until it returns. Existing capability, model, palette/remap, lifetime and camera guards precede dispatch; the sealed snapshot epoch is checked again at READY. ROM palette/artwork authorities are immutable.

PREPARING initializes a private pending map from the immutable backdrop, applies the existing occupancy authority, plans backdrop relocations and monotonically reserves unreferenced tail slots. All admission/allocation happens before any preload. The old committed map and all committed reference counts remain untouched. No WarmCompare call or native physical-VRAM read occurs in this warm path; retained home-validity bits and the committed RAM reference counts authorize reuse/restoration. Conservative admission deliberately forgoes exact actor-tile reuse.

PRELOADING streams composition through the existing 80-byte HIGH/LOW scratch buffer: the unchanged fused tile compositor generates source pixels, and the unchanged backdrop copy helper supplies restorations. Each pair uses the existing direct-DMA service after waiting for a fresh VBlank. One pair per VBlank bounds the workload without an upload queue or second framebuffer. HIGH and LOW completion fences are logged separately; the pair-ready flag becomes 3 only after the synchronous pair routine returns. Actor pending tags are cleared after both transfers. READY requires complete tags, valid slot indices and unchanged sealed epoch. Independently replaying all data through READY and decoding the pending maps reconstructs the complete source oracle before any map commit.

COMMITTING invokes the existing WarmMapDmaHigh/Low service for two contiguous 2,048-byte maps in one fresh VBlank. It avoids running the millisecond-scale sparse scan inside the commit window. No map-base swap, second map allocation, forced blank or active-display map writes occur.

After both map fences, the producer retains its lock while copying pending to committed RAM, rebuilding reference counts, updating the successful visual key and publishing the displayed epoch. This RAM bookkeeping extends beyond VBlank; it does not touch the PPU. The COMMITTING owner protects both old leases and pending reservations during that interval, so no allocator or source request can observe partially updated ownership. The old leases retire only after the physical map commit; the visible transition itself is atomic at the video-field boundary.

Rollback after READY restores the pending RAM map from the committed map, preserves the committed directory and epoch, and releases the private reservations. Preloaded bytes may remain in unreferenced slots; they are never exposed. LEFT rejection precedes preparation and performs zero DMA. Subsequent requests are permitted and must pass the same conservative admission; this does not prove their general capacity.

The backend borrows only the scalar CHUNK lease 42:D600-D67F, unused by the fused renderer: transaction header and at most 16 restoration records. MAP remains 42:C000-C7FF; committed map C800-CFFF; refs D000-D5FF; HIGH/LOW scratch D680-D6CF. No new WRAM, BW-RAM, VRAM, palette, OBJ or ROM asset allocation. Extra code occupies 39:A000-A337, 823 bytes, clear of C000 helpers and D000/D400/E000/E200/F000 services.

## Measured coexistence

The 707-slot single-frame bound is not used as a two-frame proof. The retained physical maps and complete 80-byte tile identities give these per-transition measurements. Full lists of referenced/free slots, identity hashes and restoration homes are in the JSON receipt. No-op rows are analysis controls only.

| Retained transition | Live slots | Free tail slots | Exact reusable identities | Exact new identities | Restored homes | Conservative pairs | Deficit |
|---|---:|---:|---:|---:|---:|---:|---:|
| 0 -> 1 | 634 | 134 | 537 | 100 | 8 | 111 | 0 |
| 1 -> 2 | 642 | 126 | 540 | 97 | 4 | 106 | 0 |
| 2 -> 3 | 642 | 126 | 637 | 0 | 0 | 102 | 0 |
| 3 -> 4 | 642 | 126 | 544 | 93 | 1 | 104 | 0 |
| 4 -> 5 | 643 | 125 | 637 | 0 | 0 | 103 | 0 |
| 5 -> 6 | 643 | 125 | 543 | 93 | 2 | 104 | 0 |
| 6 -> 7 | 641 | 127 | 636 | 0 | 0 | 102 | 0 |
| 7 -> 8 | 641 | 127 | 543 | 91 | 2 | 104 | 0 |
| 8 -> 9 | 642 | 126 | 524 | 114 | 27 | 122 | 0 |
| 9 -> 10 | 641 | 127 | 522 | 112 | 21 | 125 | 0 |
| 10 -> 11 | 642 | 126 | 634 | 0 | 0 | 104 | 0 |
| 11 -> 12 | 642 | 126 | 634 | 0 | 0 | 104 | 0 |
| 12 -> 13 | 642 | 126 | 634 | 0 | 0 | 104 | 0 |
| 13 -> 14 | 642 | 126 | 521 | 115 | 29 | 122 | 0 |
| 14 -> 15 | 639 | 129 | 521 | 113 | 21 | 125 | 0 |
| 15 -> 16 | 642 | 126 | 539 | 97 | 1 | 109 | 0 |
| 16 -> 17 | 644 | 124 | 521 | 117 | 30 | 126 | 2 |
| 0 -> 2 | 634 | 134 | 540 | 97 | 6 | 108 | 0 |

Both selected pictures fit the original scene simultaneously: the deliberately deferred 0->1 plan uses 103 actor pairs plus eight restorations (111 / 134 free tail slots); successful 0->2 uses 102 actor pairs plus six restorations (108 / 134). The old frame remains physically referenced throughout.

## Native transfer and timing evidence

| Transaction | CHR bytes | Pairs | Map bytes | DMA descriptors | Result |
|---|---:|---:|---:|---:|---|
| Deferred RIGHT | 8,880 | 111 | 0 | 222 | Old picture retained |
| Successful RIGHT | 8,640 | 108 | 4,096 | 218 | New picture committed |
| Unsupported LEFT | 0 | 0 | 0 | 0 | Previous picture retained |

Successful map commit: **35,156 master clocks (1.636893 ms)**. Measured VBlank edges: 275,836,088 to 275,886,552 (50,464 clocks). At commit start, **50,274 clocks (2.340800 ms)** remained. Completion margin: **15,118 clocks (0.703907 ms)** before active display. The budget comes from native PPU endFrame/startFrame events and actual DMA completion markers, with NMI disabled and HDMA withdrawn. It is not an assumed 10-KB transfer allowance.

**120 video fields** from the first movement-seal observation to the first new displayed field. This deliberately slow slice establishes non-blank correctness, not cadence performance.

| Transaction | Planning ms | Fused composition ms | CPU preparation ms | Waiting ms | CHR DMA ms | Begin-to-return ms |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 179.931434 | 93.850475 | 327.757857 | 1711.970749 | 3.804767 | 2043.537470 |
| 2 | 150.904282 | 92.693718 | 296.585087 | 1666.772360 | 3.779996 | 2005.881660 |

CPU preparation is PREPARING through READY elapsed clocks minus disjoint fresh-VBlank wait intervals and completed CHR DMA fences. It includes planning, composition, restore work and CPU/bus overhead. Fused composition is a subset, not an additional cost. Polling wait boundaries include their routine setup; DMA fences include the first post-DMA instruction, as in the retained controls. Exact clocks and every HIGH/LOW fence appear in the receipt.

The isolated retained fixture withdraws legacy NMI, audio and video writers, holds the returning SA-1 graphics worker, and disables NMI during preparation/preload/commit. Idle restores auto-JOY/minimal owned NMI, which acknowledges $4210. No authored audio timing or normal game NMI budget is proven.

## Independent evidence and preservation

Complete physical replay includes cold publication, the rejected preload, the successful preload/map commit and LEFT retention. Every one of the 261 physical captures matches an ordered full-DMA prefix; every visible capture matches a source-composition oracle. Both maps, palettes and final refcounts match native ownership. All warm CHR destinations are checked against the previous displayed maps and must be unreferenced tail slots. All warm transfer fences and the complete map commit fall within measured VBlank windows. Zero unsafe PPU accesses or resource faults.

The candidate-specific ROM auditor validates the exact fail-closed source transformation, every preserved instruction and required relocation, inserted Poppy bytes and all other ROM bytes. Kernels, assets, refcount authority, direct-DMA code, source services and all unrelated banks remain unchanged. A fresh forced-blank build without the experimental option reproduces SHA256 `52872d1546c26d2d9a0be438aaae32bb4ac764c74dc2a6b5a3632f90d4a179c0`. Existing control auditors remain intact.

**90 focused tests pass. All 29 inherited dirty tracked files remain byte-identical**, including the protected 17. Earlier diagnostic trials are retained privately; only final v5 evidence is certified. The final probes use the PPU actual VRAM address, capture the cold ownership handoff, and wait for the sealed world epoch before computing the host oracle. Master-clock execution behavior is unchanged by read-only probes. Frame-tool timeouts retry only the unadvanced remainder, without extra emulated fields or input changes.

## Reproduction

From the repository root, with retained assets/PAK, Poppy and Mesen toolchain, use a fresh private directory:

```powershell
$env:PYTHONPATH='.;tools/bor_compile;tools/verify'
$env:MESEN_EXE='E:/gh/Mesen2-mcp-frameexact/bin/win-x64/Release/Mesen.exe'
python tools/verify/m4_opaque_component_native.py --output out/byor-motu-nonblank-NEW --warm --occupancy out/astra-occupancy-assets-v1 --tile-fusion --direct-pair-dma --rect-map-diff --nonblank-slice
python -m unittest test_m4_nonblank_component -v
```

The compiled-fixture tests use the retained v5 artifact; a newly built directory can be independently audited and certified by m4_nonblank_component_native.audit_rom / certify. Omit --nonblank-slice to retain the established forced-blank backend.

No 30 FPS, general two-frame residency, continuous traversal, full-world scheduling, alpha expansion, authored audio scheduling, breath, HUD, combat, SA-1 migration or complete MOTU Demo claim. Stop at this single certified transition.
