# Transfer budgets compiled to an exact integer cache

The interval-preserving transfer budget hint admits a fractional cache at a
strict 353-clock bound in 1.343 seconds. This is not integer residency or
pixel admission. New optional per-bank caps let the existing residency solver
check that budget directly. Every cap is domain checked, fingerprinted and
independently replayed against the compiled writes.

HiGHS then admits an exact integer cache in eight seconds: eighteen peak
writes, 389 total writes, ten-line prefetch and zero integer violation. Its
source SCREEN result is independently replayed for every 57,344 viewport
pixels. Geometry and source controls remain fixed at 80 objects, 24 sprites
and 34 tile slivers. Only lines 131 and 132 have a 352-clock ideal span.
Physical endpoints and native authored presentation remain open.

A CP search at the native 344-clock bound with exactly these caps is
INFEASIBLE in 11.737 seconds. This rejects this capped family only. The same
fixed assignment with other budgets remains open. A bank-permuted local
repair also returns UNKNOWN, so no larger family is rejected.

An independent two-line phase construction checks all seventy balanced
four-bank phases. Each satisfies every bank's row capacity; its best
retain/prefetch heuristic takes 432 clocks. This rejects no alternative cache
liveness or phase construction and grants no physical/native admission.

Nineteen residency and six transfer-decomposition tests pass, including both
CP and HiGHS cap enforcement, exact pixels and an insufficient-cap rejection.
The width audit has zero failures. NO color reduction or alpha adaptation is
applied. Concurrent actors, authored peak native alpha and MOTU completion
are not certified.
