# Exact additive-only OBJ capacity bound

The generic joint scheduler can reserve banks 0–3 with `--additive-only`.
This constrains every visible effect pixel to banks 4–7, whose additive color
math eligibility is required by the existing native routing proof. It rejects
precomposited math mode rather than silently changing the requested policy.
The pooled necessary relaxation uses capacities `(0, 60)` and permits optimal
initial residency and unlimited preloading. Geometry and individual bank
assignment are relaxed; an LP candidate is never an admitted schedule.

For isolated HBreath idle frame 11 over the explicit GUILE2 background, complete
enumeration of exact saturated additive operands gives a validated peak-write
lower bound of **42**. Primal violation and dual residual are both zero. Even
granting one preloaded low byte, 42 CGRAM word commits span at least
`16 * (42 - 1) = 656` master clocks, exceeding the measured optimistic
**356-clock** legal window. Transfer setup and contention can only increase
the requirement. Thus this four-bank exact additive-only route fails bandwidth.

This is an exact fixed-context encoding of BOR 4086 RGB8 SCREEN followed by
RGB555 conversion. It does not assert that SNES addition implements SCREEN
globally. It does not reject the mixed opaque/additive route, which may use
normal-bank slots alongside other actors, or alternative BG allocation.
Source colors and dimensions remain unchanged; no color reduction is applied.

The [bounded receipt](receipts/byor-motu-additive-only-raster-bound.json) retains
artifact hashes, the complete-cover enumeration metadata and the exact scope.
The standalone native HBreath gate and MOTU gameplay remain open.
