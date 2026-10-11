# Geometry search hints preserve palette evidence

A new offline constructor regrids exact operands into small masks while
preserving every pixel's bank and the entire palette transition trace. Such
inputs use the explicit SOURCE_EXACT_GEOMETRY_SEARCH_HINT status and carry no
hardware or native admission. Ordinary palette consumers reject them; only
explicit geometry searches can request their validated operand demand.

The authored peak's 87-piece palette witness becomes 162 8x8 masks, with 33
sprites and 33 tiles per line. This exceeds both OAM and sprite limits and is
not a runnable candidate. Its 2668 operands and all palette transitions remain
exact. The hardware-constrained joint search attempts to reduce those masks
while meeting an optimistic 337-clock activity bound. It returns UNKNOWN after
65 seconds; no hardware feasibility or universal rejection follows.

The joint solver also preserves explicit allowed-bank restrictions from each
hinted pixel owner. Tests cover restricted bank reassignment, source coordinates,
source pixel coverage, default-consumer rejection and native-admission flag
rejection. A separate fixed-bank residency search using the improved physical
member as a hint returns UNKNOWN after 90 seconds at the 337-clock gate.

The complete physical witness remains 552 clocks against the native-tested
336-clock window. The focused suite passes 60 tests. The width guard checks
9825 labels with zero failures; all 17 protected files retain their hashes.
No shared runtime assembly changed. No color reduction was applied. Authored
native raster, concurrent actor admission and MOTU Demo completion remain open.
