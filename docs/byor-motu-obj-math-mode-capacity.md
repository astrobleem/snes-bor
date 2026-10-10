# Remaining OBJ math-mode capacity

The full-additive three-enemy bound does not cover every SNES math operation.
The generic cover enumerator now examines addition, halved addition,
subtraction and halved subtraction across all 32,768 RGB555 operands. Its
formulas follow the [Mesen PPU implementation](https://raw.githubusercontent.com/SourMesen/Mesen2/master/Core/SNES/SnesPpu.cpp):
addition halves before saturation; subtraction saturates before halving.
This is formula authority, not native presentation certification for the new modes.

Equivalent and dominated operands are removed only when their entire coverage
is retained. Mode-tagged enumeration preserves coverage separately for each
operation, so a global replacement remains valid when the shared mode changes
between lines. Tests compare every operand against brute force on small
contexts, including an output that halved addition cannot reach.

For the three-enemy frame 14, a permissive per-pixel mode relaxation gives a
validated liveness lower bound of **21.4** writes per line. Independent interior
point and dual-simplex solves agree, with checked primal/dual residuals.
This prevents rejection of all remaining math routes from the full-additive
23.8 bound. The real PPU cannot independently choose a mode for each pixel.
The pooled multi-mode result is explicitly excluded from fixed-bank schedule
compilation and native admission.

`raster_math_mode_liveness.py` strengthens the relaxation to one shared mode
per scanline. It can enforce mode integrality while leaving palette residency,
geometry and per-bank assignment relaxed. Its tests distinguish impossible
per-pixel mode mixing from a valid mode change between lines with a retained
operand. A feasible relaxation is still not a schedule. Mode-register updates
and their runtime cost remain outside these optimistic capacity bounds.

On lines 120 through 152 of the same three-enemy frame, whole-pixel union
coverage and removal of modes that force more than 60 opaque colors tighten
the shared-mode lower bound to **23.8**. This permits optimal initial residency
and unlimited preloading; geometry, bank assignment and slot integrality remain
relaxed. At least 24 whole color writes are necessary somewhere in that interval.
Their data-only high-commit span is at least 368 master clocks, exceeding the
measured 356-clock window before setup. This rejects that non-windowed route
for this explicit context, whose authored pose timing is not yet certified.

Color-math windows can also bypass math on upper OBJ banks. Three fixed
horizontal windows (84..193, 110..174 and 130..164) yield validated bounds of
23.8, 23.75 and 26.75 writes respectively, rejecting those particular masks.
A per-pixel arbitrary-window relaxation reaches **20.690678**, leaving other
masks open. Literal bypass and enabled math contexts are kept separate during
operand dominance reduction, preserving every exact RGB555 option.

The generic solver now supports masks with at most four horizontal transitions
per line, a necessary superset of the SNES's two-window masks. Eligibility and
shared math modes can independently be made integral. Palette residency remains
fractional, and neither feasible masks nor solver timeouts certify or reject a
fixed-bank native schedule. Tests distinguish a mask requiring two windows from
one that a single window can represent. Window register descriptors and their
runtime cost still need a native proof.

The strengthened fractional two-window solve reaches **20.690678**, with
independently checked primal and dual residuals. An integral shared-mode/window
solve at a 22-write budget reached its 180-second limit without a candidate;
that is not infeasibility. The earlier weaker fractional model and timed-out
dual-simplex run are retained with their distinct scope.

An isolated native descriptor proof now exercises four masks on successive
lines: full eligibility, union of two windows, inverted union and no eligibility.
It alternates ordinary and upper OBJ banks and full/halved addition against a
real BG subscreen operand. All **57,344 pixels** match the exact RGB555 expected
image; all **1,568 register writes**, 544 OAM bytes and 512 CGRAM bytes match.
It uses 56 OAM entries, eight sprites and 32 slivers per line. Four HDMA channels
transfer seven descriptor/mode bytes per line; the observed first-to-last
register-write span is 48 master clocks. This span excludes HDMA setup and
therefore is not an available palette-transfer budget. This component proof
does not bind HBreath, BOR alpha, concurrent palette DMA or the gameplay lease.

The [receipt](receipts/byor-motu-obj-math-mode-capacity.json) retains the bounded
results and exact scope. No source pixels or colors are reduced. The ordinary
static presentation path and bank zero are unchanged; native raster and MOTU
Demo certification remain open.
