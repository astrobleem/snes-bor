# Authored-frame physical palette search

The source-exact cache remains at twenty peak writes, 398 total writes,
eleven-line prefetch and an ideal 344-clock bank transfer span. This is not
a physical packet or native alpha admission.

Exhaustive eligible bank ordering evaluates 576 permutations. General bank
partitions and fixed adjacent pairs both have a minimum optimistic peak of
344 clocks. Unchanged-slot packet witnesses peak at 856 and 920 clocks,
respectively, and do not meet the native window. Source operands and packet
CGRAM identities are independently replayed by the ordering tool.

Flexible physical packing, bounded three-line timing repair, and paired
three-line repair all return UNKNOWN after their bounded searches. The paired
rectangle lifetime model also returns UNKNOWN after 90.067 seconds, using
7,854 variables and 13,766 constraints. No infeasibility follows from these
results. Full artifacts are retained in the compressed receipt.

The physical scheduler now supports an explicit feasibility-only objective.
It retains the same lifetime, palette bank, transfer window, packet CGRAM and
pixel identity constraints, while accepting any valid schedule rather than
minimizing its cost. All eighteen layout tests and three bank-order tests pass.
The seventeen protected files still match their original hashes.

Authored alpha native proof, concurrent actors and production admission remain
open. NO color reduction or alpha adaptation is applied.
