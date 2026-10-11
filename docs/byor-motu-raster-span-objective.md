# Palette bank span objective

The offline residency solver can now minimize the peak optimistic prepared-DMA
span directly. It retains fixed piece banks, exact source RGB555 operands,
transparent index zero, palette liveness and bounded lookahead. Both the
dynamic-programming and adjacent-bank partition backends support the objective;
physical slot placement and native admission remain separate requirements.
An optional CP-SAT LNS strategy searches the same constraints.

The 87-piece source-exact layout reaches a 344-clock optimistic peak with
17 writes per line. Physical lifetime placement and permutation require 664
clocks; bounded repairs reduce that to 600 while enforcing an 18-word cap.
The original 80-piece layout also reaches a 344-clock optimistic peak, with
19 writes. The prior complete physical witness at 552 clocks remains best.
The native-tested control-before-palette window is 336 clocks. None of these
authored physical schedules is admitted to it.

A probe exhausts 243 assignments of the five pieces originally in bank 2 to
banks 0, 1 and 3. All preserve row capacity, exact pixels and alpha eligibility,
leaving bank 2 unused. The best interval demand lower bound is 18.75 writes
per line. This assignment family therefore requires at least 19 writes on
some line. It does not prove admission of a player palette, and packet copying
through the reserved bank is not authorized by this probe.

The focused suite passes 71 tests. All 17 protected files retain their hashes.
No shared runtime assembly changed. The receipt retains complete compressed
offline artifacts and packet replay results. No color reduction was applied.
General raster feasibility, authored native alpha raster and concurrent actor
admission remain open; restricted bounds are not universal rejection.
