# MOTU opaque native optimization

`BYOR_MOTU_OPAQUE_OPTIMIZATION_PASS`. The final native candidate verifies the
same 18 source-owned movement epochs and 1,032,192 full-screen
RGB555 pixels with zero mismatches. All snapshots are byte-identical to the
scalar reference. Candidate: `out/byor-motu-opaque-warm-v4/native/bor.sfc`,
SHA256 `8b2350b578d926c024ed55490c2d85b8ab88062ec756f098234649af942af637`. This remains forced-blank, bounded opaque correctness;
it is not 30-Hz or full Demo admission.

Astra's ZIP was extracted into a fresh scratch directory. All 13 package tests
passed before source edits. Its retained-asset analyzer checked 1,032,192 source
oracle pixels, 8,752 emitted row-kernel executions and sparse DMA tile identities,
with zero mismatches. This was offline validation, not native timing. The
assembled 175-byte kernel matches Astra's emitted bytes exactly. The first
row-only native stage passed all 18 epochs before transfer residency changed;
the scalar implementation remains intact as a reference.

The successful projected key includes source model/handle/frame, remap and
direction, integer projection, source-world owner and stage, plus immutable
palette/layer/camera generation words 1/1/0. Invalid contexts reject before the
key check. Epochs 3,5,7,11,12,13 acknowledge newly sealed world snapshots with
zero coverage/kernel calls, composed tiles, DMA bytes/descriptors and forced
blank. World/input/animation processing continues. Key/ack CPU work is about
0.32 ms; zero graphics work does not mean zero world or acknowledgement cost.

The actor assets have eight horizontal alignment phases, reused at arbitrary
positions. Transparent cropping preserves original dimensions and offsets;
vertical position is row addressing, not another set of pictures. A row record
contains duplicated source coverage and five plane-pair words. Native code
computes a full 24-bit source-row pointer per tile, advances it by row stride,
and merges five words using the supplied kernel. Effective zero coverage is
excluded before allocating an actor slot. Palette and source SCREEN semantics
in the immutable backdrop retain their established authority; no dynamic alpha
operation or SCREEN table was introduced.

Warm publication retains maps and slot/refcount state, invalidates the union
of old/new coverage, restores only required overwritten backdrop homes, and
reuses identical actor pairs using a complete 80-byte physical VRAM comparison.
It emits changed contiguous map ranges and coalesces consecutive HIGH/LOW CHR
uploads in batches of up to sixteen pairs. It never assumes a numerical
backdrop slot still contains its original picture. All initial CHR/maps/CGRAM
bootstrap traffic is cold-only. No Python dictionary/global content scan was
ported into the native allocator.

| Measured worst cost | Scalar baseline | Row-only stage | Final warm |
|---|---:|---:|---:|
| Gather + encoding / fused composition | 2704.328 ms | 169.783 ms | 113.271 ms |
| DMA | 29.615 ms | 25.138 ms | 4.061 ms |
| DMA bytes | 74,384 | 64,224 | 9,864 |
| DMA descriptors | 458 | 204 | 122 |
| Production | 2810.992 ms | 454.442 ms | 350.451 ms |
| Publication through INIDISP | 2820.566 ms | 457.790 ms | 357.951 ms |

Scalar gather and encode were 30,514,840 and 27,566,740 master clocks. Its
admission/allocation interval was 61.542 ms
(combined boundary; no separately observed allocator marker). Final allocation
alone is 17.054 ms, within
173.635 ms of total preflight/allocation.
The effective-coverage helper accounts for 130.019 ms and
is the remaining dominant named cost. Kernel body accounts for
42.973 ms within fused composition; row address/setup/iteration
and caller overhead remain substantial. These measured helper intervals are
subsets, not independent additive whole-frame costs.

Cold graphics initialization separately transfers 58,064 bytes in 56
descriptors: 22.417 ms DMA,
288.560 ms publication.
Warm composed tiles are 86..98 (cold SELECT 70), versus scalar 165..225.
Warm DMA is 7,796..9,864 bytes; no-op samples are zero. Warm polling waits are
20..23 fields, with two visible settling fields for capture. Timings are actual
Mesen master-clock boundaries at 21,477,270 Hz. DMA includes the first post-DMA
instruction; kernel profiling ends before its cleanup/RTL. Python's nominal
instruction estimates are not reported as observed native performance.

The final run checks all output pixels against source composition, screenshots
and independently decoded VRAM. It additionally replays the actual captured
DMA source payloads/descriptors against 1,179,648 physical VRAM bytes across
18 epochs. Every slot's reference count matches the committed map; every home
marked intact matches its immutable 80-byte identity. Actual LEFT input retains
the last valid epoch, complete VRAM and picture. Unsafe PPU writes and resource
faults are zero.

VRAM remains HIGH 0000..BFFF, LOW C000..EFFF and maps F000..FFFF. There is no
OBJ/HUD arena. BW-RAM ownership remains 42C000..42D6FF: pending/committed maps,
1536-byte directory, existing row scratch, and key/bounds. After sparse map DMA,
the retired committed-map region stages HIGH C800..CBFF and LOW CC00..CCFF;
the committed map is restored before publication. DP grows to 3400..347F in
the existing returning scratch page; returning code 3200..33FF and source
physics beginning at 42D800 remain intact. Native code stays in measured bank
57; immutable phase/row data uses checked empty banks EB..F4. Source coverage
over all X/Y alignments is bounded at SELECT 85, IDLE 103, WALK 111, so even the
conservative 596+111 target fits 707 of 768 paired slots. No 596+225 reservation
is made. Forced blank retires visible references before overwrites, and all
transfers finish before a coherent display/epoch. A post-transfer failure must
remain blank; previous-display retention applies to preflight rejection.

All 34 focused repository tests and 13 supplied package tests pass. All 29
inherited dirty files remain byte-identical. No PAK rebuild, PCM copy, source
main.bin/sym/pansy regeneration, new renderer, OBJ research or broad old native
control rerun occurred. An added foreign-work guard initially rejected this
standalone ground fixture, whose full controller lease is not enabled; it was
corrected to the actual source-world/self/lifetime owners. Observer fence
callbacks are gated by real DMA requests so a skipped tile cannot manufacture
a completion. These were ordinary integration fixes, not external limits.

Reproduce from the root (existing retained assets and assembled-source/MSU
identities are required):

```powershell
$env:PYTHONPATH='.;tools/bor_compile;tools/verify'
$env:MESEN_EXE='E:/gh/Mesen2-mcp-frameexact/bin/win-x64/Release/Mesen.exe'
out/byor-motu-solver-venv/Scripts/python.exe tools/verify/m4_opaque_assets.py `
  --assets out/byor-motu-online-v3/assets `
  --observations out/byor-motu-online-v3/native/observations.json `
  --output out/astra-opaque-assets-NEW --check-emitted-kernel
out/byor-motu-solver-venv/Scripts/python.exe tools/verify/m4_opaque_component_native.py `
  --output out/byor-motu-opaque-NEW --phases out/astra-opaque-assets-NEW --warm
```

Omit `--warm` to reproduce the row-only control. The final 357.951-ms warm
publication still misses an eventual 33.333-ms target. Non-blank/cadence
publication, natural 200-Hz world traversal/animation, dynamic SCREEN, authored
breath, HUD, combat, audio timing and full MOTU Demo remain unproven.
