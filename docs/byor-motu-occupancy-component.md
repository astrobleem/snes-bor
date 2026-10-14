# BYOR MOTU occupancy preflight

`BYOR_MOTU_OCCUPANCY_PREFLIGHT_PASS` from the retained `4746507d` control.
The native producer now admits actor tiles through an immutable source-local
occupancy lookup for eight horizontal and eight vertical alignments. It keeps
the foreground-aware row blitter, exact 175-byte kernel, source simulation,
persistent residency, restoration, sparse DMA and forced-blank fences unchanged.
No complete actor-position pictures or finite position selector were introduced.

Candidate: `out/byor-motu-occupancy-v1/native/bor.sfc`.
SHA256: `edbc7c2e1013cfddb602c29bb2691b2d3cbf79a284e5d1c1f2650b74d713c648`.
A separate build from the final sources reproduces exactly this ROM. The retained
control SHA is `8b2350b578d926c024ed55490c2d85b8ab88062ec756f098234649af942af637`.
Detailed identities and per-epoch measurements are in
`docs/receipts/byor-motu-occupancy-component.json` and the retained native result.

| Worst warm measurement | Previous | Occupancy |
|---|---:|---:|
| Coverage helper | 130.019 ms | 8.443 ms |
| Preflight plus allocation | 173.635 ms | 52.139 ms |
| Allocation alone (subset) | 17.054 ms | 17.225 ms |
| Composition | 113.271 ms | 123.568 ms |
| DMA | 4.061 ms | 4.342 ms |
| Production to completion | 350.451 ms | 245.569 ms |
| Complete publication | 357.951 ms | 257.298 ms |

Coverage falls 93.507%, from 2,792,456 to 181,322 observed master clocks,
with up to 225 native calls per changing epoch. These are emulator master-clock
callback intervals, including actual bus/refresh behavior, not nominal CPU-cycle
estimates. Helper intervals run from entry to RTS fetch, consistently with the
retained control. DMA completion is observed at the first post-DMA instruction.
Column maxima may belong to different epochs; the helper/allocation subsets
must not be added to their containing preflight measurement.

Ignoring foreground during admission adds at most 10 tiles in this sequence.
The real blitter still applies exact foreground masks, so composition and DMA
costs increase slightly: up to 108 composed tiles, 864 row calls, 10,544 warm
DMA bytes and 126 descriptors. Source occupancy over all alignments is SELECT
85, IDLE 103, WALK 111; 596 backdrop identities plus 111 requires 707 of 768
paired slots. The immutable payload is 39,616 bytes, not display canvases.

Astra's five supplied tests pass, including 76,800 synthetic comparisons.
Independent original source-index checks pass 860,160 full-viewport tile
comparisons across all 64 alignments of all three poses and negative/clipped
origins. The original foreground-aware predicate has no TRUE/new-FALSE cases
in the actual 18 source contexts. Native admission counts match independently
calculated source occupancy exactly. Signed floor projection uses arithmetic
shifts; out-of-range signed local tile coordinates reject before indexing.

One native ROM passed all 18 JOY1 epochs and all 1,032,192 RGB555 pixels against
independent source composition, screenshots and physical VRAM decoding. All 18
sealed world snapshots are byte-identical to the retained warm/scalar control.
Actual DMA descriptor/payload replay verifies all 1,179,648 physical VRAM bytes;
residency counts and intact backdrop homes agree with the committed maps.
The six repeated subpixel projections perform no composition, DMA or blanking.
Actual invalid LEFT rejects while retaining the previous full VRAM and display.
Resource faults and unsafe PPU writes are zero; ownership canaries remain intact.
All 45 focused tests pass. The unchanged 12-epoch and 75-field controls were
retained by identity without broad reruns.

The new immutable ROM lease is F43600..F4D0BF for payload and F4D100..F4D6FF
for 1,536 geometry/pointer bytes. The prior candidate contains only zero bytes
throughout the lease; the emitter checks absence of conflicting bytes before
writing, regenerates tables against phase-mask inputs and checks capacity/hash
identities. F43000..F435FF refcounts remain byte-identical. Native helper code
stays in measured bank 57 below the E000 kernel. DP additions 3466..346F fit
the existing 3400..347F scratch lease. BW-RAM and the full 64-KiB HIGH/LOW/map
VRAM plan are unchanged, with no added OBJ arena. No source simulation, audio,
WRAM, SA-1 or displayed CHR ownership change was made.

Forced blank still lasts up to 207.119 ms; publication is not gameplay-rate.
At the worst publication epoch, 72.519 ms of production remains outside measured
preflight/allocation, composition and DMA, covering existing restoration/map
comparison, setup and other producer overhead. This residual is not assigned
an invented finer breakdown. Cold publication is 207.133 ms including 58,904
DMA bytes/22.760 ms; it is separate from the warm maxima. Source row composition
is now the largest measured warm phase. No seamless publication, 30-Hz target,
dynamic SCREEN alpha, breath, HUD, combat, audio timing, natural 200-Hz world
traversal or full MOTU Demo is claimed.

All 29 inherited dirty tracked files, including the protected 17, retain their
pre-implementation SHA256 fingerprints. No stash/reset/clean, unrelated media
regeneration, PCM copy or master merge occurred.

Reproduce from the repository root with retained source assets, source PAK,
assembled source identity and MSU companion available. Use fresh output paths:

```powershell
$env:PYTHONPATH='.;tools/bor_compile;tools/verify'
$env:MESEN_EXE='E:/gh/Mesen2-mcp-frameexact/bin/win-x64/Release/Mesen.exe'
out/byor-motu-solver-venv/Scripts/python.exe -m unittest test_phase_occupancy test_m4_occupancy_component test_m4_opaque_component test_m4_online_component test_m4_live_ground_component test_component_live_bundle test_m4_component_publication test_bg_component_residency test_bg_component_deadlines test_bg_components -v
out/byor-motu-solver-venv/Scripts/python.exe tools/bor_compile/phase_occupancy.py --phases out/astra-opaque-assets-v1 --output out/astra-occupancy-NEW
out/byor-motu-solver-venv/Scripts/python.exe tools/verify/m4_opaque_component_native.py --output out/byor-motu-occupancy-NEW --phases out/astra-opaque-assets-v1 --occupancy out/astra-occupancy-NEW --warm
```

The driver checks real source occupancy before compilation, executes the exact
18-epoch controller sequence, verifies pixels/resources/DMA replay, compares
world snapshots and certifies the measured reduction. Omit `--occupancy` to
retain the original preflight control. Stop after this optimization; cadence-aware
non-blank publication remains a separate milestone.
