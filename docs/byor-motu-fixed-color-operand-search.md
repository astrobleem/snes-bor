# Shared fixed-color operands: source-exact family remains open

Continuation starts from `0ed0d89fb5308fa09adb5da1ffcbdadf00dc636e` on
`feat/byor-motu`. The original continuation state and transfer-pool ledger were
read before edits. All seventeen protected hashes and twenty inherited
content-dirty tracked hashes still match. No color reduction or BG fallback
is selected. MOTU compilation, native authored gameplay and Demo completion
remain unfinished.

The new degree of freedom is the SNES COLDATA operand shared by a scanline,
instead of the actor-free BG subscreen operand. Only OBJ math is enabled;
ordinary visible player words stay statically reserved in the lower class.
The cache experiment retains all 31 ordinary words for the actual He_ManB /
HBreath pose. Its source RGB555 digest is
`079de2d8ffbbe72c9779904f3a0ef2fe6d0283331dd49838a79ed2cc7e889f45`.
There are 2,670 non-bypassed effect pixels, 81 effect pixels exactly equal to
background, and 2,762 visible ordinary pixels. Source composition still uses
BOR4086 SCREEN in RGB8 before projection to RGB555.

`source_fixed_color_obj_bound.py` supports selected legal fixed colors, four
source-derived guides, shared mode/guide choices and optional two positive
windows. Integer candidates independently replay cache changes, residency,
actual math, ordinary pixels, bypass pixels and the entire viewport. Their
report has a separate schema; no existing production candidate admission is
borrowed. Fixed banks, slots, legal OAM/CHR and transport remain separate gates.

The no-window necessary bounds below hold even with fractional residency and
optimal initial preload. They reject only their selected guides. Commit spans
exclude every address/setup cost and grant a preloaded first low byte.

| Selected guide and allowed modes | Checked LP bound | Necessary integer words | High-byte commit span |
| --- | ---: | ---: | ---: |
| Channel minima, full add | 34.285714 | 35 | 544 clocks |
| Bright-row guide, half add | 30.307692 | 31 | 480 clocks |
| Channel headroom, subtract | 29.339623 | 30 | 464 clocks |
| Bright-row guide, all four modes | 30.307692 | 31 | 480 clocks |

The channel-minimum add/window LP has no primal candidate after 71.853 seconds.
Joint choice among all four fixed-color guides and all four modes has no LP
candidate after 45.637 seconds. The corresponding no-window integer cache
test has no candidate after 56.932 seconds. Adding the positive two-window
family has no integer candidate after 104.741 seconds, including construction.
Both integer runs enforce 22 peak loads and the necessary strict 357-clock
class-transfer gate. These are UNKNOWN, never hardware infeasibility.
Arbitrary RGB555 fixed-color choices have not been exhausted.

## Native mechanism proof

The existing isolated automatic-cursor fixture now optionally uses COLDATA,
cycles add / half-add / subtract / half-subtract, and publishes three COLDATA
bytes per scanline on DMA channel 4. It retains two palette ranges on channels
1..3 and positive-window/mode controls on channels 6..7. Channel 0 retains the
73-row dummy APU HDMA pattern. Dynamic COLDATA cannot silently reuse the general
window or third-palette-range channel allocation; those combinations fail.

The constant-color case at timer 81 and dynamic-color cases at timer 71 all
match 57,344 RGB555 pixels, final CGRAM and OAM, 447 complete palette packets
and 8,493 safe high-byte commits over three fields. The dynamic cases directly
replay all 2,016 COLDATA bytes against their DMA source cursors. For visible
fixture objects the last COLDATA write is H=112 and the last window/mode write
is H=168, before their first math-enabled pixel at X=128. The palette commit
span remains 320 clocks. The IRQ entry-to-RTI peak increases from 1,104 to 1,176
clocks; this excludes hardware entry, gateway and RTI execution.

Both interrupted 16/16 context and 8/8 context with decimal mode preserve the
observed registers, stack and hardware return status. These are synthetic
component proofs, without production NMI/gameplay ownership, authored HBreath
palette placement or actual source-pixel deadlines. The 344-clock conservative
budget and 356-clock maximum are unchanged. No timing-model discount is admitted.

The first native attempt used the default older Mesen binary, which lacks
`get_cpu_state`; the frame-exact binary is required. Native pixel replay also
caught a reversed fixture window gate: CGWSEL `$20` produced 8,192 mismatches;
changing it to `$10` preserves the original prevent-outside policy. That failed
receipt is retained. Default component ROM bytes and expected pixels remain
identical to the preserved commit.

The focused suite passes 34 tests. The compact
[receipt](receipts/byor-motu-fixed-color-operands.json) records exact artifact
hashes, checked bounds, native results and nonclaims. Its gzip companion retains
full reports, palette/control traces, ROMs, expected pixels and screenshots for
independent replay. Solver logs were not expanded and PCM was not copied.

## Resume commands

Use the retained solver environment, rather than the base Python without OR-Tools:

```powershell
out/byor-motu-solver-venv/Scripts/python.exe tools/bor_compile/source_fixed_color_obj_bound.py --source 'Masters of the Universe [v.3.0 Build 4086].pak' --stage DATA/LEVELS/GUILE2.TXT --scene out/byor-motu-fixed-color-continuation/scene.json --candidate-policy zero --candidate-policy add-minimum --candidate-policy subtract-headroom --candidate-policy half-add-bright --math-mode add --math-mode half-add --math-mode subtract --math-mode half-subtract --positive-windows-only --integer-budget 22 --time-limit 90 --output out/byor-motu-fixed-color-continuation/joint-four-guides-four-modes-positive-window-integer22.json
```

This exact bounded formulation is already retained as UNKNOWN. Expand its
fixed-color domain, sharpen its valid constraints or add independently replayed
hints before spending another run on it. `--fixed-colors` accepts an explicit
RGB555 word for every demanded effect scanline. It does not import a palette.

Native reproduction:

```powershell
$env:PYTHONPATH='tools/bor_compile'
$env:MESEN_EXE='E:/gh/Mesen2-mcp-frameexact/bin/win-x64/Release/Mesen.exe'
out/byor-motu-solver-venv/Scripts/python.exe tools/verify/m4_cgram_window_pixels.py --dma-windows --timer 71 --fixed-color 0x2ce3 --dynamic-fixed-color --output out/byor-motu-fixed-color-continuation/native-four-mode-dynamic-observed
```

For interrupted 8/8 decimal context add `--context-widths 8/8 --decimal-context`
and select a different output directory. Focused validation uses
`PYTHONPATH=tools/bor_compile;tools/verify` and the four test files
`test_source_fixed_color_obj_bound.py`, `test_source_static_obj_math_bound.py`,
`test_raster_obj_math_cover.py` and `test_m4_fixed_color_component.py`.
