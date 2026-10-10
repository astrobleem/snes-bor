# Three-range native transfer and clipping relaxation

The synthetic native fixture now supports three opaque CGRAM ranges: 129–136,
161–166 and 193–198. This transfers twenty words without transparent-slot
padding. With changing math mode, the timer-60 trial fails: 6,358 unsafe high
commits and transfer spans up to 392 master clocks. Fixing math mode isolates
palette and window-bound transfer cost. The timer-70 trial verifies every packet's
destination and source word, but every packet spans 360 clocks, exceeding the
356-clock safe interval; 703 high commits are unsafe.

The fixture can also retire the completed dummy audio HDMA channel before palette
transfers and re-enable it in NMI. The timer-58 fixed-mode trial reduces the span
to 352 clocks. Its varying transfer start still causes 397 unsafe high commits
and 41,856 pixel mismatches. All 447 source-word packets and OAM bytes compare
exactly. This measured failure applies to this interrupt/packet timing layout;
it does not reject other raster mechanisms or establish a production audio lease.

The scene frontend also permits a generous main-color clipping relaxation:
output black or half the actor-free subscreen color needs no palette operand.
It omits clipping/window/mode correlations and any damage to main-screen BG.
Only four pixels in the explicit three-enemy frame-14 pose gain this exemption.
The 21-word mixed-mode/window MIP reaches its 180-second limit without a candidate.
A time limit is not an infeasibility proof. Exact authored pose reachability,
fixed piece banks, physical slots and native source-frame admission remain open.

The [bounded receipt](receipts/byor-motu-three-range-dma-clipping-trials.json)
retains report hashes, measured results and nonclaims. No color reduction,
production assembly changes or additional bank-zero allocation is applied.
