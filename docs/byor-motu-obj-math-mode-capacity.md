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

The [receipt](receipts/byor-motu-obj-math-mode-capacity.json) retains the bounded
results and exact scope. No source pixels or colors are reduced. The ordinary
static presentation path and bank zero are unchanged; native raster and MOTU
Demo certification remain open.
