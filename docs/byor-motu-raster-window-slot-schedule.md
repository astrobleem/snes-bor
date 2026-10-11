# Joint exact window and physical palette allocation

The new generic offline solver keeps OAM geometry, piece banks and shared row
math modes fixed. Each eligible pixel may use its exact literal output outside
the color windows or an exact math operand inside them. It chooses two positive
or two inverted windows, physical slots, residency and transfer ranges together.
This is a bounded operand family, not universal raster feasibility.

Input authority requires source-bound controls, the complete expected RGB555
frame hash and independent input math replay. Every output replays the complete
source frame, transparent masks and all CGRAM packets. Changed operands and
window gates, prefetch latency, dead writes, packet bytes and channels are
reported. No opaque alpha adaptation or color reduction is applied.

A saved authored witness, with all hinted values fixed, is reproduced exactly
at 536 clocks and 19 peak writes. It preserves the ideal 336-clock bank bound.
The free 336-clock gate remains UNKNOWN after 50 seconds. Starting from the
better physical witness, another search retains 472 clocks with 21 peak writes,
52 packet bytes, seven DMA channels and 12 lines of prefetch latency. It changes
three exact operands and three observed window gates; every rendered RGB555
pixel remains identical. No noninitial dead palette writes are present.

The coverage helper also now treats adjacent or overlapping hinted DMA packets
as one union run. Previously it incorrectly hinted multiple starts within a
continuous covered range. This was a solver hint contradiction, not hardware
infeasibility. Regression tests fix every hinted variable and verify the exact
strict-window cost. A separate window fixture proves that three positive runs
can be represented by two inverted windows while retaining a known hint.

The focused suite passes 40 tests. All 17 protected files retain their hashes;
the width guard checks 9825 labels with zero failures. No runtime assembly
changed. Authored native raster, concurrent-actor admission and MOTU completion
remain open. No color reduction was applied.

Mandatory identities now constrain each bank over every scanline interval:
if more than fifteen distinct required words occur, at least the excess must
be written after the interval's first palette. This counts prefetch and slot
moves without treating adjacent set differences as transfer bandwidth. The
authored frame adds 3990 necessary cuts. Its fixed witness still replays at
536 clocks; the native gate remains UNKNOWN. The 472-clock witness remains
source exact, with six changed operand/gate choices and one unused write.
Seven focused tests pass, including twenty mandatory colors in one fixed bank:
zero updates is infeasible, while a writable schedule preserves every pixel.

An optional exact operand reuse search considers other words in the bank's
candidate vocabulary that produce precisely the required RGB555 result under
the same source-bound math mode. It finds six such pixels in this authored
frame. Complete replay remains exact at 472 clocks; the native gate remains
UNKNOWN. Saturation reuse and a bounded repair interval have focused tests.
Repairs retain surrounding palette states and charge the boundary update.
Mandatory distinct words also receive explicit slot matching constraints.

The complete operand option enumerator examines all 32768 RGB555 words for
each eligible bank, retaining seeded words and coverage dominance witnesses.
The shared modes remain fixed. It finds the same six pixels with multiple
valid choices in this frame and retains the 472-clock result. All source math,
transparency and CGRAM identities replay exactly; twelve focused tests pass.
This rules out a missing operand vocabulary improvement for those fixed modes
and banks, but does not prove the slot schedule optimal or reject raster.

Optional joint physical bank assignment now searches selected pieces within
their source-derived eligibility and original color-math bank class. One bank
choice covers the entire piece, with no scanline changes to OAM. Physical slot
changes and DMA coverage are solved together. Geometry, transparency and full
source output replay are retained. Thirty-eight pieces spanning the crowded
rows were searched for fifty seconds; the 472-clock witness was retained with
the same assignments. This is a bounded search result, not infeasibility.
Nine focused tests pass, including eligibility and fixed lifetime assignment.
Required words receive optional distinct-slot matching and bank capacity cuts.

Selective subdivision reuses the existing bank subdivision implementation,
retains its palette packets as an exact optimization hint, and independently
compares every source position, word and bank. Ten selected 16x16 parents
produce 107 OAM entries and 33 sprites on one line: explicitly rejected. Nine
produce 104 entries, 32 sprites and 34 tile slivers: admitted for offline
geometry only. Joint physical bank search retains 472 clocks after fifty
seconds. The full alpha output, masks and CGRAM packets replay exactly.
Eighteen focused tests pass. Native timing for this layout remains untested.

Rebalancing the nine-parent layout lowers the validated fractional write bound
from 17 to 15.857142857. Three further bounded neighborhoods reach the same
bound. An exact integer residency uses eighteen peak writes with a 360-clock
ideal bank estimate; all 576 eligible bank orders retain that estimate for
the saved trace. Physical packing reaches 680 clocks, then retiming reaches
648 clocks. The complete source alpha output and every CGRAM packet replay.
Free physical residency at the 336-clock gate remains UNKNOWN after fifty
seconds. The original geometry's 472-clock witness remains better; neither
layout has authored native admission. These bounds do not reject raster.

The general row-slot solver had an invalid auxiliary bound charging twenty
clocks per active bank. Counts `[1,15,4]` in three adjacent banks have one
22-word transfer: 376 raw clocks and a 336-clock prepared span. The old cut
demanded 380 raw clocks and excluded this valid case. It is removed from the
general solver; the restricted adjacent-pair solver's separate twenty-clock
bound remains valid and unchanged. The exact counterexample is admitted at
the strict 337-clock gate and rejected at 336. Thirty-eight focused tests pass.
Previous general row-slot failures using the optional necessary-bank bound
must not be relied on without the corrected solve. Independent DP and physical
packet replay are unchanged. The corrected authored gate remains UNKNOWN.

Window/slot search now reports branch and conflict counts and permits bounded
solver probing configuration. The probing-zero authored native gate explores
411225 branches in fifty seconds but remains UNKNOWN. It grants no admission.

The general row solver also exposes the probing setting, retaining its default.
Its probing-zero corrected native gate remains UNKNOWN; the joint bank/slot
probing-zero search retains the source-exact 472-clock witness with unchanged
piece banks. Fourteen row-slot tests pass, including the strict three-bank
boundary with probing disabled. All protected hashes and width checks pass.

When piece banks are movable, redundant interval cuts now count mandatory
identities within each color-math class's sixty opaque slots. The complete
bank-specific fifteen-slot and physical-transfer model remains in force;
these pooled cuts cannot admit a schedule by themselves. A sixty-four-color
fixture proves that bank reassignment cannot avoid required palette writes,
including opaque RGB555 zero. Ten focused tests pass. The authored 472-clock
hint remains valid with all hints fixed. The low-sprite 103-piece layout gains
1092 cuts but its fifty-second joint native gate remains UNKNOWN.

Emitted CHR/OAM replay verifies the actual tile footprint: the original
80-piece layout uses 6400 bytes and the 104-piece subdivision uses 6304 bytes,
both with 163 unique tile patterns. These fit the isolated OBJ region. This
does not admit animation upload bandwidth or production VRAM leases.

Bank-class decomposition now supports explicit partial schedules, bounded
physical ranges and per-line budgets. Partial output masks exclude the other
class and clear complete-frame proof flags. Ordinary schedule consumers reject
these outputs unless they explicitly request restricted demand. A generic
recombiner validates both classes against the same complete source schedule,
fixed piece geometry and bank eligibility, then replays every source pixel,
transparency mask and physical CGRAM packet. Its trace reports retained,
evicted, prefetched and written words with future-use latency.

Independent loose class schedules recombine to a source-exact complete frame,
but need 632 clocks, 24 writes and 72 transfer bytes at peak. This misses the
strict 337-clock gate and is worse than the retained 472-clock witness. It
proves recombination correctness, not native admission or raster infeasibility.
Thirty-six focused tests pass; nine window-scheduler tests also pass after
adding the reserved-cost objective for coordinated line budgets. The width
audit and all seventeen protected fingerprints remain clean.
