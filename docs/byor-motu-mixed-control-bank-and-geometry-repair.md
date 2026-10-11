# Exact changing-control bank and geometry repair

Exhausting all 576 eligible bank permutations of the saved 376-clock cache
leaves its optimistic peak unchanged. The emitted unchanged-slot physical
witness takes 1,272 clocks and is not admitted. This rejects only the bank
permutation family for that fixed trace.

A joint bank/cache repair frees eight pieces crossing worst scanline 127,
keeping all other banks and all source operands fixed. At a strict 337-clock
bound and nineteen-write ceiling it returns UNKNOWN after 90.212 seconds;
no family or universal infeasibility is claimed.

Generic free-alignment 8/16 retiling preserves every encoded pixel bank, slot
and word. It finds 73 objects, 22 peak sprites and 33 tile slivers, compared
with the prior 80/24/34. The independent fixed-bank row lower bound is 22
tile slivers. Geometry is not optimal or concurrent-actor admission.
Source SCREEN controls stay bound to the exact authored source frame.
NO color reduction or alpha adaptation is applied.
