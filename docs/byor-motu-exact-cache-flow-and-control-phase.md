# Exact cache flow and authored control timing

Searching the original changing-control bank assignment gives a source-exact
352-clock optimistic cache span, nineteen peak writes, 456 total writes and
25-line prefetch. Its bounded lower span is 312 clocks. All 576 eligible bank
permutations retain the 352-clock peak; unchanged-slot physical packets take
840 clocks and are not admitted.

Exact partition hints now provide concrete interval choices and their costs
from a saved valid cache row. They add no constraints. One hundred randomized
rows plus empty and prepared-packet cases agree with the independent endpoint
dynamic program. A 90-second refinement preserves the 352-clock incumbent,
reduces total writes to 450 and reaches a 300-clock lower bound. It does not
prove a minimum or reject raster presentation. Current source replay verifies
every 57,344 viewport pixel for all three retained schedules.

A separate native transport probe combines the seven-bank black-matte palette
packets with actual authored window/mode control traffic and the 2,814-byte
production NMI test queue. Color-math layer selection is disabled; this is
transport timing evidence only. Delta controls preserve complete packet and
control delivery and IRQ context, but seven CGRAM high commits are unsafe.
First-high clocks range from 1092 to 1140 and physical CGRAM identity fails.
This result is explicitly FAIL. Its 344-clock packet span is insufficient to
admit the full control pipeline.

The added IRQ phase observer measures a 1,258-clock maximum entry-to-RTI
interval. For example, a field-12 IRQ entering line 142 at H=772 reaches RTI
on line 143 at H=666, after the next H=648 interrupt trigger. Other fields
show the same overrun. This explains delayed subsequent palette updates and
requires a complete handler/deadline budget, not just packet span.

Twenty-two cache and native-compiler tests pass; the width audit has 9,825
labels and zero failures. Code in bank zero is unchanged. Authored alpha,
concurrent native rendering, production resource leases and MOTU completion
remain open. NO color reduction or alpha adaptation is applied.
