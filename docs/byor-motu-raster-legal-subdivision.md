# Legal subdivision and lower-write palette residency

The generic bounded subdivision search replaces selected legal square OBJ
pieces with nonempty 8x8 children, then searches fixed bank assignments within
the existing source color-math classes. It checks OAM, per-line sprite and tile
limits for each candidate. Source pixels and color operands remain exact.
Interval-demand scores guide search; they are not measured CGRAM bandwidth.

For the authored HBreath peak over GUILE2, 117 bounded candidate trials select
three subdivisions. Geometry grows from 80 to 87 OAM entries, with 25 peak
sprites and 34 peak tile slivers per line. The validated fractional cache lower
bound improves from 16 to 15.857142857 words per line. Independent primal and
dual residual checks pass. The integer cache solver then finds an exact
16-write schedule, with 405 total noninitial writes and ten lines of maximum
noninitial prefetch latency.

Physical timing is still unresolved. Across all 576 eligible bank orders, this
particular 16-write trace needs at least 376 clocks even with freely packed
endpoint slots. Therefore addresses alone cannot make that trace fit the
measured 336-clock isolated native window. This does not reject other residency
timing, operands, piece assignments or geometry.

The source-exact physical lifetime layout starts at 728 clocks. Arbitrary fixed
slot and bank permutation reaches 680; local free-residency refinement with an
18-word full-frame write cap reaches 616. Every accepted packet and source
pixel is independently replayed. The necessary 337-clock range search returns
UNKNOWN at its time limit; this is not infeasibility.

The address-coverage model now includes a necessary transparent-slot crossing
cut. Its exact optimum is checked against an independent partitioner, including
all 120 opaque slots. The fixed-permutation solver's exploratory window also
allows that full-domain case. Local refinement can select either physical range
encoding and either solver search strategy; defaults remain unchanged.

The focused suite passes 53 tests. All 17 protected tracked files retain their
saved hashes. No runtime assembly changed. This is not an authored native raster
or concurrent gameplay proof. No color reduction was applied; the selected
source alpha policy remains BOR 4086 RGB8 SCREEN followed by RGB555 conversion.
The compressed receipt retains complete bounded offline schedules and evidence.
