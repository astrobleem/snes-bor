# Joint pixel encoding, OAM masks and palette liveness

The generic offline MILP now chooses between each pixel's exact source RGB555
output and its exact full-BG additive residual, assigns that pixel to one fixed
OAM bank mask, and chooses per-line palette residency with preloading. Opaque
bank eligibility is 0–3; additive eligibility is 4–7. It enforces 15 opaque
slots per bank, 128 OAM entries, 32 sprites and 34 tile slivers per line, and a
strict combined write limit. No bank selection changes inside an OAM piece.

An incumbent is independently replayed into physical slots and source pixel
indices. The final composite must match every source RGB555 pixel. This does
not admit the native subscreen/layer architecture, descriptor overhead, live
compositor, source reachability or actual MOTU runtime.

The explicit source GUILE2 pose reached the 45-second solver limit without an
incumbent for both 16x16 and 32x32 mask grids at 20 writes per line. The models
contain 249,232 / 247,560 variables and 168,134 / 165,073 constraints respectively.
Neither timeout is a hardware infeasibility verdict. Smaller mixed-size grids
and alternative saturated operands remain open.

Twenty-six focused tests pass. A synthetic 64-identity opaque frame cannot fit
four static opaque banks with zero writes; allowing one write per line produces
a source-exact fixed-bank schedule. Tests also preserve opaque black and force
negative residuals onto non-math banks. The width audit remains clean and all
17 protected tracked hashes are unchanged. No color reduction or PCM copies.
[Solver receipt](receipts/byor-motu-joint-encoding-solver.json).
