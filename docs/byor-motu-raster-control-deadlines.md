# Native control deadlines and the scanline transfer window

A SNES scanline is 1,364 master clocks. The passing 344-clock delta-control
test already ends at clocks 76--84 of the following physical line. CGRAM
access is allowed before clock 88 or from clock 1096 onward. A 408-clock
retained-word padding test produces 430 unsafe commits and fails pixel
identity. Early-next-line access was already included in the measured window;
it is not additional bandwidth. This rejection concerns that executor and
packet witness, not all raster mechanisms.

Register traffic after palette DMA does not establish an authored alpha
deadline. The isolated executor now has an opt-in control-before-palette path.
Frame-constant window selector and logic values are initialized once. The
changing bounds and math-mode values are written before DMA. Removing a
redundant accumulator-width round trip restores sustained IRQ cadence.
The unchanged default executor ROM remains byte-identical to parent
`c2db5d9`; this introduces no production assembly or bank-zero growth.

The final native test uses HTIMER 120, the explicit idle DBR-zero/direct-page
`$4300` ABI, prepared byte counts, and actual production NMI service with
2,814 queued bytes. It passes three complete fields (12--14), all 57,344
viewport pixels, exact palette packet and OAM observers, and zero unsafe
CGRAM commits, OBJ overflow, IRQ or NMI context faults. Peak transfer span is
336 clocks, with 44 maximum packet bytes; most active rows use 328 clocks.
First high commits are 1096--1108. Peak IRQ entry-to-RTI is 1,170 clocks;
NMI completes within VBlank. Uniform 344-clock padding still has unsafe
commits under this control order and is retained as failed evidence.

All 3,360 observed changing control writes occur at clocks 874--992 on the
physical line preceding their target viewport row. The source deadline
checker conservatively includes every visible pixel in OBJ banks 4--7,
regardless of its gate. It proves writes happen after the preceding row's
last eligible pixel and before the next row begins, with an eight-clock
completion guard and a minimum remaining margin of 100 clocks. Tests reject
early writes, wrong physical-row alignment and missing register observations.

The native image remains the exact source SCREEN result on controlled black.
OBJ math selection is disabled while register traffic is exercised. The
deadline checker does not claim transfer of the authored RGB555 palette or
native authored alpha rendering. BG/subscreen routing and complete authored
palette execution remain separate requirements. Concurrent actors, live
underlays, production resource registration, active audio/VM/SA-1 workers and
MOTU gameplay remain unadmitted. No color reduction was applied.

The rebanked source-exact assignment has an integer 17-write residency witness
and a repaired 344-clock favorable bound, but fixed write-time slot placement
is infeasible. Flexible prefetch remains UNKNOWN. Its physical refinement
reaches 600 clocks, while the original assignment's best retained complete
physical witness is 536 clocks. These remain above the demonstrated native
window and do not reject different banking, word choices or raster schedules.

Receipts: `docs/receipts/byor-motu-raster-control-deadlines.json` and its gzip
companion retain successful and failed native observations, the source-bound
deadline proof, and the rebanked logical/physical witnesses.
