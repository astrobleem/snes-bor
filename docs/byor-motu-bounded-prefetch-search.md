# Bounded prefetch and pixel repair searches

The joint cache search now has a selectable soft-hint repair strategy. It
retains the exact integer constraints and never pins an invalid hint. The
default strategy remains unchanged. A focused test repairs an invalid bounded
integer transfer hint and independently checks the resulting values.

Increasing lookahead from 16 to 90 lines does not produce a candidate in the
retained 120-second trial. A separate 18-write cache search without range costs
returns UNKNOWN after 60 seconds. Hint repair at the 345-clock target also
returns UNKNOWN; it spends its bounded run before normal search begins. These
outcomes do not establish a limit on lookahead or reject raster.

A source-exact mixed mode/window schedule is then tested at the stricter
337-clock target. The search permits new literal/math bank classes and one
additional fixed-bank mask per rectangle, retaining all OBJ limits. It returns
UNKNOWN after 120 seconds and 1,218,473 branches. Alpha remains the exact
source-derived RGB8 SCREEN output projected to RGB555; mode changes are
alternative exact encodings of that output.

`--pixel-repair-interval` restricts new bank and word choices to a selected
scanline interval. Outside it, source pixels retain their hinted words and
banks; palette residency and prefetch timing remain free across the frame.
Every emitted OAM mask keeps a fixed bank and contributes its full rectangle
to hardware geometry. Invalid intervals or missing fixed rectangles reject.
The first authored trial, rows 124 through 145, returns UNKNOWN after 120
seconds. Its failure cannot reject changes outside that interval. A synthetic
test independently verifies pixel ownership and outside-word/bank identity.

The receipt binds all five trials to current source metadata and composed
RGB555 output. Sixty-three focused tests pass, and the width audit reports
9825 labels with zero failures. All 17 protected file hashes match. No color
reduction or alpha adaptation is applied. Authored peak native presentation,
concurrent actor admission and production/MOTU completion remain open.
