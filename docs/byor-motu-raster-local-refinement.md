# Physical palette residency refinement

The generic row-slot solver now supports explicitly restricted scanline
experiments. These retain fixed source geometry and banks but relax pixels
outside the selected interval. They carry `RESTRICTED_SCANLINE_DEMAND_ONLY`,
cannot claim complete-frame identity, and are rejected by the normal complete
schedule reader. A 348-clock interval search returns UNKNOWN, not infeasible.

Complete-frame local repair replaces frozen rows with constants and retains
their known write costs in interval liveness constraints. The following row's
transfer remains part of the repair objective. The eight-row experiment drops
from 41,792 variables to 8,496 while retaining every source pixel. A wider repair
reduces the physical peak from 856 to 712 clocks.

`raster_slot_refine.py` makes bounded repairs around the highest-cost rows and
retains only an improving complete schedule. It independently replays every
packet against all physical CGRAM slots before accepting either the initial
hint or a candidate. It retains bounded solver statistics and explicitly keeps
native timing unadmitted. Tests reject corrupted packet data and restricted
proofs; meeting an offline target still does not claim native admission.

The first six repairs reduce the exact authored full-frame physical peak from
712 to 560 clocks. Two further bounded passes reach 536 clocks. This remains above the private idle-CPU transport's measured
344-clock span. The favorable logical residency bound remains 344 clocks;
physical slot placement is still the unresolved requirement. Neither the
incomplete searches nor these oversized schedules reject raster universally.

The existing generic bank rebalancer also redistributes pieces into lightly
used banks, preserving math eligibility and geometry. Its independently
validated full-frame fractional residency bound is 16 writes per line,
compared with 17 for the original assignment. A 17-write integer search and
348-clock physical greedy construction find no candidate within their bounds.
These results are not hardware infeasibility.

The compiled pieces retain 80 OAM entries, 24 peak sprites and 34 tile slivers.
Source pixels, RGB555 identities, fixed OAM banks and source-bound alpha
operands remain exact. Full authored native raster, concurrent actor palettes,
production resource admission and MOTU Demo completion remain open. No color
reduction was applied.

Receipts: `docs/receipts/byor-motu-raster-local-refinement.json` and its gzip
companion, which retains the best complete schedule.
