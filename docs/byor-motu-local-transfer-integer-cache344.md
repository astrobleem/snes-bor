# Exact integer cache at the measured transport bound

A local integer transfer master fixes the prior hinted budgets outside lines
126..142 while keeping the cache LP free to rearrange residency over the full
frame. It finds a 344-clock ideal budget in 12.578 seconds. Its fractional
cache deficit is zero, independently validated with zero primal violation
and a 1.11e-16 maximum dual residual.

HiGHS compiles these caps to integer residency in 7.375 seconds: twenty peak
writes, 398 total writes, eleven-line prefetch and zero integer violation.
The ideal range span is 344 clocks. Every 57,344 viewport pixel is independently
replayed against the current source RGB8 SCREEN result projected to RGB555.
Geometry stays at 80 objects, 24 sprites and 34 tile slivers.

Physical packing with retained write times rejects that fixed lifetime/slot
family in 1.205 seconds. It does not reject movable prefetch timing, other
residency or bank assignments. The earlier cap plan with one extra write per
active bank over lines 120..142 is also infeasible at 344 clocks; that capped
family alone is rejected. No universal raster rejection is claimed.

The decomposition now exposes an explicit budget repair interval. A local
rejection has a separate scope flag and cannot reject the entire fixed-bank
family. All pixels and cache lifetimes remain modeled outside the interval.
Nineteen residency and seven decomposition tests pass. Physical scheduling,
authored alpha native proof, concurrent actors and production admission remain
open. NO color reduction or alpha adaptation is applied.
