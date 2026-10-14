# BYOR MOTU fused native tile compositor

`BYOR_MOTU_FUSED_TILE_NATIVE_PASS` against certified commit
`1fb3def032e0449345c5607e821014ad29558b39`.

The opt-in `--tile-fusion` path applies Astra's `tile_fusion.fuse(lines)` after
the occupancy and warm-residency transforms. It replaces eight per-row driver
and kernel calls with one tile routine, preserving the foreground-aware mask,
exact HIGH/LOW planar expression, source-pointer clamping and 24-bit carries.
The old 175-byte row kernel remains byte-identical and selectable without the
flag. No new picture, artwork, palette, source-world or scheduling path is added.

Candidate: `out/byor-motu-tile-fusion-v2/native/bor.sfc`.
SHA256: `01b757d34ec1ad568758d325678b63bb96ad2f5b87badedae4ee65e1ac711977`.
The final-source rebuild reproduces this ROM exactly. Building without the flag
reproduces the certified control SHA256
`edbc7c2e1013cfddb602c29bb2691b2d3cbf79a284e5d1c1f2650b74d713c648`.
Source PAK SHA256 remains
`2a35ebb9beea7388a6823205dad21e1a718da4b5f747ea09792c0a0e719aa2e0`.

| Worst warm measurement | Control | Fused |
|---|---:|---:|
| Composition | 123.568 ms | 108.448 ms |
| Preflight + allocation | 52.139 ms | 52.139 ms |
| DMA | 4.342 ms | 4.329 ms |
| Other production | 75.255 ms | 75.257 ms |
| Total production | 245.569 ms | 231.014 ms |
| Publication | 257.298 ms | 240.665 ms |
| Blank-phase duration | 207.119 ms | 190.486 ms |
| INIDISP forced-blank duration | 207.111 ms | 190.478 ms |

Worst composition falls **12.236% / 15.120 ms** and worst publication falls
**6.465% / 16.633 ms**. Every changing warm epoch composes faster. These are
actual emulated master-clock measurements, not offline instruction estimates.
The performance gate requires at least 5% lower worst warm composition, lower
worst warm publication, and faster composition in every changing warm epoch.
The supplied candidate clears that gate. Column maxima occur in different
epochs and must not be summed as a single frame's costs.

Paired per-epoch measurements below are **control/fused milliseconds**.
Epoch 0 is cold; six noops acknowledge without graphics. Other production is
production minus preflight/allocation, composition and measured DMA intervals;
it covers existing restoration/maps/comparison/setup and is not a newly
instrumented finer attribution. Blank-phase duration uses OnlineBlank to
INIDISP=15, consistently with the supplied baseline. The receipt also contains
the actual first INIDISP=128 to INIDISP=15 durations (about 0.008 ms shorter).

| Epoch | Tiles/rows | Composition | Preflight + allocation | DMA | Other production | Publication | Blank phase |
|---|---:|---:|---:|---:|---:|---:|---:|
| 0 | 80/640 | 90.174/78.973 | 45.251/45.251 | 22.760/22.755 | 48.868/48.874 | 207.133/205.356 | 161.646/159.869 |
| 1 | 103/824 | 118.158/103.747 | 43.851/43.851 | 3.815/3.811 | 62.957/62.955 | 240.687/224.047 | 196.583/179.943 |
| 2 | 102/816 | 116.663/102.378 | 40.508/40.508 | 3.392/3.383 | 59.056/59.067 | 230.881/214.243 | 190.104/173.466 |
| 3 (noop) | 0/0 | 0.000/0.000 | 0.000/0.000 | 0.000/0.000 | 0.276/0.276 | 0.276/0.276 | 0.000/0.000 |
| 4 | 103/824 | 118.363/103.913 | 40.527/40.527 | 3.572/3.570 | 58.200/58.234 | 230.882/214.243 | 190.086/173.447 |
| 5 (noop) | 0/0 | 0.000/0.000 | 0.000/0.000 | 0.000/0.000 | 0.276/0.276 | 0.276/0.276 | 0.000/0.000 |
| 6 | 102/816 | 117.259/102.989 | 39.174/39.174 | 3.463/3.467 | 57.465/57.452 | 230.880/214.246 | 191.437/174.804 |
| 7 (noop) | 0/0 | 0.000/0.000 | 0.000/0.000 | 0.000/0.000 | 0.276/0.276 | 0.276/0.276 | 0.000/0.000 |
| 8 | 102/816 | 116.709/102.428 | 40.508/40.508 | 3.392/3.393 | 58.959/58.961 | 230.885/214.248 | 190.108/173.471 |
| 9 | 95/760 | 106.403/93.110 | 52.132/52.132 | 4.194/4.179 | 73.446/73.451 | 241.476/224.839 | 189.093/172.456 |
| 10 | 104/832 | 118.927/104.384 | 49.927/49.927 | 4.258/4.255 | 72.308/72.301 | 256.471/239.835 | 206.292/189.656 |
| 11 (noop) | 0/0 | 0.000/0.000 | 0.000/0.000 | 0.000/0.000 | 0.275/0.275 | 0.275/0.275 | 0.000/0.000 |
| 12 (noop) | 0/0 | 0.000/0.000 | 0.000/0.000 | 0.000/0.000 | 0.275/0.275 | 0.275/0.275 | 0.000/0.000 |
| 13 (noop) | 0/0 | 0.000/0.000 | 0.000/0.000 | 0.000/0.000 | 0.275/0.275 | 0.275/0.275 | 0.000/0.000 |
| 14 | 93/744 | 104.502/91.479 | 52.092/52.092 | 4.200/4.195 | 73.826/73.834 | 241.472/224.838 | 189.130/172.496 |
| 15 | 104/832 | 118.927/104.388 | 49.927/49.927 | 4.195/4.201 | 72.519/72.499 | 257.298/240.665 | 207.119/190.486 |
| 16 | 108/864 | 123.568/108.448 | 40.575/40.575 | 3.621/3.617 | 59.430/59.438 | 230.884/214.254 | 190.042/173.412 |
| 17 | 96/768 | 107.949/94.525 | 52.139/52.139 | 4.342/4.329 | 75.255/75.257 | 241.479/226.332 | 189.091/173.943 |

Fused instrumentation counts AstraOpaqueTile once and AstraTileRow eight times
per composed tile; the original AstraOpaqueRow executes zero times. At most
108 tiles / 864 rows are composed. Tile entry to AstraTileDone measures fused
mask/blend/pointer/loop work, up to 98.142 ms; it excludes final register restore
and RTL. AstraTileRow to AstraTilePixelDone measures blend bodies, up to
43.034 ms. This narrower blend interval differs from the old row kernel's
entry-to-AstraDone interval; use OnlineTile-to-OnlineEncode composition for
comparable A/B performance. CPU callbacks do not advance emulated clocks.

The same 18 real JOY1/controller epochs pass **1,032,192 RGB555 pixels with zero
mismatches** against independent source composition, displayed screenshots and
physical VRAM decoding. All sealed snapshots, CGRAM, occupancy admission,
committed directory counts and expected frames are byte-identical to the
control. Foreground ordering and backdrop restoration are exact. All 1,194 DMA
packets, including payloads, match the control exactly; independent full VRAM
replay verifies 1,179,648 bytes from the candidate's captured initial VRAM.

Raw full-VRAM A/B buffers contain 9,885..10,588 different bytes left by legacy
boot in unreferenced slots. The verifier admits these only when the slot has
zero references, neither producer has DMA-written the byte, and each value
still matches its own captured initial VRAM. Every resident and producer-written
byte matches the control. A tampered resident byte fails the comparison. Full
native DMA replay remains required; this is not a claim that all unused boot
storage is byte-identical between separate emulator boots.

Noops at epochs 3,5,7,11,12,13 perform zero composition, DMA, fused tile/row calls
and blank work. Actual invalid LEFT preserves the previous epoch, complete VRAM
and displayed pixels. Unsafe PPU writes and resource faults are zero; source
physics, returning worker code and graphics-end ownership canaries pass.

Poppy assembles exactly 289 bytes at bank 57 E200..E320, leaving 3,295 bytes
before the F000 NMI entry. The certified baseline's entire new code lease is
zero. Actual symbols and byte audits preserve the E000..E0AE reference kernel,
NMI code and all bytes outside bank 57. Consequently all immutable occupancy,
phase, foreground, palette, backdrop and refcount leases remain identical,
including F43000..F435FF. No additional DP, BW-RAM, WRAM or VRAM lease is needed;
the existing DP 3400..347F and BW-RAM 42C000..42D6FF are retained. Source physics
starts at 42D800. The full 64-KiB HIGH/LOW/maps VRAM plan and 707/768 occupancy
bound remain unchanged, with no OBJ arena. The existing forced-blank retirement,
residency and DMA publication fences stay in force.

The supplied six offline tests and branch audit pass; all **56 focused tests**
pass, including assembled lease tampering, actual DMA replay, native tile/row
accounting and preservation of the certified control. One initial emulator run
returned a frame-step timeout at epoch 14 after verifying 14 displayed epochs.
Its artifacts remain in `out/byor-motu-tile-fusion-v1`; a fresh run of the
identical ROM completed all 18 epochs. No native code change was needed between
attempts. An overly strict raw-VRAM A/B check was corrected to distinguish
independently verified resident data from untouched, unreferenced boot storage.
Neither event is classified as an external limit.

All 29 inherited dirty tracked files, including the protected 17, remain
byte-identical to `out/byor-motu-fusion-dirty-before.json`. No stash/reset/clean,
media regeneration, PCM copy, master merge or unrelated native rerun occurred.

Reproduce from the repository root with retained source assets/toolchain/PAK/MSU
available, using a fresh output directory:

```powershell
$env:PYTHONPATH='.;tools/bor_compile;tools/verify'
$env:MESEN_EXE='E:/gh/Mesen2-mcp-frameexact/bin/win-x64/Release/Mesen.exe'
out/byor-motu-solver-venv/Scripts/python.exe -m unittest test_tile_fusion test_m4_tile_fusion_component test_phase_occupancy test_m4_occupancy_component test_m4_opaque_component test_m4_online_component test_m4_live_ground_component test_component_live_bundle test_m4_component_publication test_bg_component_residency test_bg_component_deadlines test_bg_components -v
out/byor-motu-solver-venv/Scripts/python.exe tools/verify/m4_opaque_component_native.py --output out/byor-motu-tile-fusion-NEW --phases out/astra-opaque-assets-v1 --occupancy out/astra-occupancy-assets-v1 --warm --tile-fusion
```

Omit `--tile-fusion` to reproduce the certified row renderer. Full artifacts,
paired clock counts, helper measurements and hashes are bound in
`docs/receipts/byor-motu-tile-fusion.json` and
`out/byor-motu-tile-fusion-v2/result.json`.

Composition at 108.448 ms, other producer work at 75.257 ms and preflight at
52.139 ms remain substantial; DMA is only 4.329 ms warm. Forced blank remains
up to 190.478 ms at the register boundary. No 30-Hz rendering, seamless/non-blank
publication, SA-1 scheduling, dynamic SCREEN alpha, breath, HUD, combat, audio
timing, natural 200-Hz traversal or full MOTU Demo completion is claimed.
Stop after this measured opt-in optimization.
