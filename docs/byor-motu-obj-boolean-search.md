# Exact OBJ Boolean search and initial VBlank residency

The palette-cover liveness relaxation now accepts multiple exact additive operands
per source output. The concurrent scene retains a validated lower bound of
19.428571 writes/line and an integer pooled candidate of 20. This is not a bank,
OAM, physical-slot or transfer-descriptor schedule. Fixed 32-pixel geometry is
infeasible for that particular pinned candidate. Mixed 32/8 geometry trials with
45-second HiGHS bounds still return no incumbent, including grids aligned to
visible source bounds. Original source canvases remain authoritative and every
selected mask is independently replayed at its original coordinates.

Initial palettes can now preload colors in VBlank even when their bounded
lookahead horizon starts after row zero. A new zero-raster-write test exposed
and fixes the old cold-start restriction. Previous no-incumbent results from
that restricted model never proved universal hardware infeasibility.

An optional CP-SAT backend represents the same integral constraints with Boolean
variables, including write indicators. It rejects fractional matrix coefficients,
uses integer objective weights, and retains the independent exact pixel replay.
A 45-second full-scene trial and a 180-second trial with pre-search probing
disabled both return UNKNOWN/no incumbent. Both report their actual search
statistics. Neither is a raster rejection. The latter change tests a suspected
presolve cost; the statistics do not establish where all solver time was spent.
The backend follows the [official CP-SAT interface](https://developers.google.com/optimization/cp/cp_solver).

The separate environment uses requirements-raster-cpsat.txt inside
out/byor-motu-solver-venv. No global Python packages were changed. The environment
also caught that the shared RGB555 helper silently truncated high channels for
uint8 arrays. Explicit int32 promotion now makes white 32767, green 992 and blue
31744 under both tested NumPy versions. Production scene composition already
uses int32; its RGB555 hash is unchanged. This helper belongs to the experimental
scene probes, not the registered original-BOR compiler presentation path.

42 focused tests pass in the original environment and 51 with the optional
backend replay tests. Nine backend tests were rerun after disabling probing.
Width audit: 9825 labels, zero new/baselined/stale sites. All 17 protected tracked
hashes match. No production bank-zero code, static path or media changes.
MOTU remains unregistered and uncertified; lossless raster and BG/hybrid remain
open. [Search receipt](receipts/byor-motu-obj-boolean-search.json).
