# BYOR MOTU native online component proof

`BYOR_MOTU_ONLINE_COMPONENT_PASS`: one native ROM generates the display from
sealed source-world snapshots. It no longer selects precompiled actor-position
canvases. The bounded proof verifies 18 displayed epochs and
1,032,192 RGB555 pixels with zero mismatches. Candidate:
`out/byor-motu-online-v3/native/bor.sfc`, SHA256 `d58ea3f89e2130ee00723823e02bc04e3312fea4ce15c15884eb292f9faf332e`.

Real JOY1 input moves the persistent source-owned actor at `$414000`. Existing
constructor, input history, ground/frame, velocity and check_move services own
its state. The snapshot drives native integer projection of positive Q16
coordinates, source-indexed pixel gathering and the shared component residency
service's native planar encoder. The unchanged component PPU/DMA bootstrap
publishes HIGH/LOW tiles with a common runtime map and immutable palette.

The ROM holds one actor-free fixed-camera backdrop, a separate foreground
coverage mask, and original indexed SELECT/IDLE/WALK frame-zero artwork. The
200x250 SELECT and 310x220 IDLE/WALK images remain source-sized. Native row
addressing crosses ROM banks correctly. There are no complete actor canvases,
future-position tables or host graphics injections. The fixed backdrop retains
source RGB8 composition before RGB555; this actor and foreground capability is
opaque, so no dynamic alpha operation is approximated.

Preflight constructs pending maps, counts live backdrop references and allocates
paired slots before any PPU mutation. Forced blank retires the displayed lease;
the native producer restores immutable backdrop CHR, gathers and encodes dirty
tiles, transfers both planes/maps, and completes all DMA before its completion
epoch. INIDISP release is measured separately, and screenshots are captured
after complete visible fields. Partial bundles never count as successful frames.

| Resource | Explicit ownership |
|---|---|
| HIGH CHR | VRAM 0..49151; 768 slots of 64 bytes |
| LOW CHR | VRAM 49152..61439; same 768 slots of 16 bytes |
| Maps | VRAM 61440..63487 and 63488..65535 |
| Offset map | Disabled-enable-bit BG1 map alias; no extra arena |
| Graphics scratch | BW-RAM 42C000..42D6FF; physics begins at 42D800 |
| Producer DP | Borrowed IRAM 3400..343F; returning code 3200..33FF preserved |
| Native code/assets | Bank 57 producer; measured empty immutable banks E0..EA |
| OBJ/HUD | No additional VRAM allocation |

The private foreground owner retires legacy video writers and holds the legacy
SA-1 worker in reset during its graphics lease. Bank zero only receives an
existing-stub NMI redirect; the 2477-byte producer is in
bank 57. Peak paired tile ID is 704, below 768. Every epoch preserves adjacent
graphics bytes, source physics storage and returning-worker code. Resource
faults and unsafe PPU writes are zero.

The deterministic sequence is RIGHT x8, release, UP x4, release, RIGHT x2,
release. It reaches previously uncompiled integer positions (83,220), (84,220),
(84,219) and (85,219). Six subpixel pairs keep exactly the same pixels while
canonical coordinates change. Five movement-only pairs change source coverage.
Six same-frame pairs independently confirm visible vertical movement.
An actual LEFT input selects unsupported flipped art: preflight rejects it,
retains the prior epoch and preserves all VRAM and displayed pixels.

Independent replay recomposes source scenes after native publication, compares
all 256x224 screenshot pixels, and decodes actual VRAM/CG-RAM separately. Evidence
binds input, actor pointer, position/animation, snapshot, generated maps/CHR/
palette, completion epoch, DMA and measured clocks. See the JSON receipt and
`out/byor-motu-online-v3/native/` for per-epoch binaries, screenshots and logs.

Worst measured costs are 58,081,580 master clocks
(2704.328 ms) for source gathering plus planar encoding;
636,040 clocks (29.615 ms) for DMA, transferring at most
74,384 bytes in 458 transfers. Complete production
takes 2810.992 ms; publication through INIDISP release takes
2820.566 ms. Request-to-completion polling spans 126..171 fields,
plus two settling fields for screenshot capture. DMA measurement includes the
first post-DMA instruction: Mesen fetch callbacks precede pending DMA, and
same-clock completion callbacks are ordered as simultaneous fences. These are
emulated hardware-clock costs, not gameplay-rate or wall-clock performance.

All 28 focused tests pass. The passing 12-epoch and 75-field controls were
hash-checked and retained without native reruns. All 29 inherited dirty tracked
files, including the protected 17 and main.bin/sym/pansy, remain byte-identical.
The renderer was generalized through its input producer and shared encoder;
no unrelated outputs were regenerated and no PCM was copied.

Reproduce from the repository root using the assembled input and matching MSU
identities in the receipt:

```powershell
$env:PYTHONPATH='.;tools/bor_compile;tools/verify'
$env:MESEN_EXE='E:/gh/Mesen2-mcp-frameexact/bin/win-x64/Release/Mesen.exe'
out/byor-motu-solver-venv/Scripts/python.exe tools/verify/m4_online_component_native.py `
  --source 'Masters of the Universe [v.3.0 Build 4086].pak' --output out/byor-motu-online-NEW
out/byor-motu-solver-venv/Scripts/python.exe tools/verify/m4_online_component_evidence.py `
  --source 'Masters of the Universe [v.3.0 Build 4086].pak' --output out/byor-motu-online-v3
out/byor-motu-solver-venv/Scripts/python.exe -m unittest `
  test_m4_online_component test_m4_live_ground_component test_component_live_bundle `
  test_m4_component_publication test_bg_component_residency test_bg_component_deadlines test_bg_components -v
```

This proves bounded online composition correctness. Other models, maps,
directions, altitudes and animation frames reject; naturally timed animation,
full controller/world traversal at 200 Hz, stage collision/camera, authored
breath, multiple enemies, combat, HUD, audio timing and MOTU Demo completion
remain unproven. Non-blank, cadence-aware publication is the next milestone.
The measured computation cost needs substantial optimization before a
production deadline claim. No system/tool/inference limit was reached.
