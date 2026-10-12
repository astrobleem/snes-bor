# Source-exact cross-actor OBJ geometry probe

The complete all-actor constant-ADD pool18 local encoding now has a checked
fixed-bank horizontal lower bound of 44 slivers at rows 152 and 154. This bound
allows arbitrary legal rectangle positions, rather than only an aligned grid:
each actor/bank's visible x coordinates require their minimum eight-pixel
interval coverage. It rejects that exact word/bank assignment under the 34-sliver
limit, including non-grid retiling. Other bank assignments and exact operands
remain open; raster is not universally rejected. Six focused geometry tests
pass, including an interleaved-bank fixture whose exact lower bound is 64.
The source pose remains conditional and its reachability is not certified.

A generic row-only solver now allows every bank reassignment within the input
encoding's domains and arbitrary eight-pixel sliver positions, with eight
separate fifteen-slot caches. For the local18 words, row 152 requires exactly
43 slivers after 7.311 seconds; the actual 34-sliver gate is INFEASIBLE after
4.991 seconds. The diagnostic 128-sliver bound explicitly exceeds hardware
and admits no frame. Vertical geometry, OAM lifetimes and transfers are relaxed.

Reopening all exact ADD operands and literal choices under the same source-bound
global controls removes that row conflict. Rows 152 and 154 each have optimal
32-sliver witnesses after 17.945 and 17.920 seconds respectively. Their per-bank
capacity, indexed pixel identity and all 256 source output pixels are replayed
independently against the actual archive. Source alpha remains exact; no
compatibility adaptation is selected. This proves neither a fixed bank across
the complete OAM piece lifetime nor palette liveness or transfer feasibility.
Thirty-seven focused row, geometry and residency tests pass. These results
confirm that the word-specific failure cannot reject raster generally.

A compact full-frame word-option model now shares palette membership clauses
instead of expanding a pixel decision for every candidate operand. Every OAM
mask keeps one bank through its full legal rectangle. Separate per-row bank
capacities and complete padded OAM/sprite/sliver limits are enforced; palette
liveness and transfers remain relaxed. The selected source-derived 33-rectangle
cover is INFEASIBLE after 84.467 seconds with 177,069 variables and 317,788
constraints. This rejects that geometry family, not other legal subdivision.

Generic 8-pixel subdivision adds 445 parent/child candidates while preserving
all 22,179 encoded source pixels. Its first trial remains UNKNOWN after 150.404
seconds (327,161 variables, 611,764 constraints). Equivalent pixel decisions
now coalesce only when row word domains and geometry owners match. Optional
class bank-label symmetry first verifies all eligible domains are identical;
bank-order transfer costs are explicitly outside this geometry-only model.
The coalesced model removes 10,474 repeated pixel decisions, leaving 191,993
variables and 330,960 constraints. It returns UNKNOWN after 150.862 seconds.
A feasibility-only trial of the same model also returns UNKNOWN after 151.040
seconds. Both retain all bank and hardware geometry constraints; removing the
OAM minimization objective does not produce a witness or infeasibility proof.

The generic source-bound frame CLI can restrict demand to a declared scanline
interval while counting each selected rectangle's full padded hardware cost.
It verifies archive, viewport and row context identity before reopening exact
operands. Interval witnesses cannot admit a complete frame. Rows 144–159 still
return UNKNOWN after 60.086 seconds, with 72 candidate rectangles, 3,865 pixels
and 35,893 variables. Forty-four focused tests pass. No complete-frame hardware
timing admission or universal raster rejection is asserted.

The three critical rows 152–154 now admit shared fixed-bank OAM rectangles:
22 objects, 22 sprites and 34 tile slivers, after 8.831 seconds. All 751 encoded
pixels and the 768 source output pixels are checked independently. The selected
banks remain fixed through each complete rectangle, whose padding is included
in the hardware counts. Demand outside this three-line interval is relaxed;
palette liveness, slot assignment and transfers are unproved. A generic soft
geometry hint can reuse this subset witness without fixing decisions in the
wider search. Invalid hinted word domains are rejected. Forty-five focused
tests pass; no full-frame or native admission follows.
The wider rows 144–159 trial receives 691 soft witness hints but remains
UNKNOWN after 60.105 seconds. Hints are domain checked and do not fix bank,
word or ownership decisions. This result is not an infeasibility certificate.

The full conditional Skeletor rise tick-341 context reproduces the retained
36-sliver separate-actor lower bound and source viewport hash
44ad1ccb4a3ea068fe624d6fafa37344058b96e3183a166779698b4f2685e0de.
Packing the final visible actor pixels together admits legal 8/32 OBJ geometry:
92 OAM entries, 17 sprites and 32 tile slivers. Every one of the 22,247 opaque
pixels and all 57,344 viewport pixels replay exactly. The 584 composed RGB555
colors retain authoritative RGB8 SCREEN alpha semantics for this fixed pose.
No color reduction or alpha adaptation is selected.

This construction disproves a geometry-only rejection of all OBJ presentation
for this conditional pose. It requires cross-actor compiled mask ownership and
a live source compositor; neither source reachability nor production/runtime
admission follows. Its initial greedy palette schedule peaks at 81 writes.
Even before bank assignment, a validated 120-slot pooled fixed-output cache
bound is 23.666667, forcing at least 24 integral writes. That exceeds the
356-clock transfer window for the plain precomposited family. Its particular
fixed-bank assignment has bound 52.5. Mixed color-math encodings remain open.

The subset without He_ManB/HBreath has a separate-actor bound of 28.
It contains 37 raw RGB555 colors and has fused geometry of 47 objects, 11
sprites and 32 slivers, with 18,881 opaque pixels replayed. Its greedy palette
schedule peaks at 14 writes; physical transfer and native timing remain unproved.
The source layer list is sorted by depth, so per-actor vectors must be paired
with prepared metadata, not input scene array order. In the full pose at row
152 HBreath contributes seven slivers; He_ManB contributes three. The source
hash and total 36-sliver result remain unchanged.

Receipt: docs/receipts/byor-motu-cross-actor-geometry.json and its bounded gzip
archive. Every successful mask/index schedule receives an independent complete
viewport replay. No BG fallback, gameplay or Demo certification is claimed.

Allowing every final visible actor pixel to use any exact main-screen math
operand, rather than reserving ordinary actors as literal colors, gives a
validated fractional class-pool lower bound of 13.836735 over rows 125–145.
The two-window four-transition relaxation uses capacities 60/60; actual banks,
integer residency, geometry and transfer packing remain relaxed. Its 18-write
integral extension returns UNKNOWN in 92.926 seconds. The synthetic composite
flag only chooses the shader-cover measurement branch: authoritative source
metadata and RGB8 SCREEN output remain unchanged. This is not an alpha
adaptation, emitted source frame or hardware palette schedule.

Repeating the plain precomposited fixed-bank and pooled cache bounds with
224-line lookahead gives the same bounds, 52.5 and 23.666667. This permits
preloading across the whole frame and removes the 55-line lookahead restriction
as an explanation of that family's transfer failure. The complete-frame
all-pixel shader relaxation reaches its 121.634-second limit without a
validated bound; its UNKNOWN result is retained, not called infeasible.

A soft fractional residency hint subsequently produces an integral 18-write
class-pool candidate in 115.309 seconds for rows 125–145. Independent replay
verifies all 4,862 non-bypassed visible source pixels in that interval. The
candidate retains exact RGB555 output and compiles its window descriptors;
fixed banks, geometry and physical transfers remain unproved. Extending it
with the current default full-ADD operand selection reaches 64 upper-class
colors on an outer row, above the 60-slot class capacity. This rejects only
that extension policy; a complete-frame operand/mode search is in progress.

The complete-frame extension then produces an integral 18-write class-pool
candidate in 141.153 seconds. Outside the pressure interval it may select any
exact math mode with an enabled color window; pressure controls remain fixed.
An independent source replay verifies every one of the 22,179 non-bypassed
visible actor pixels. Source identity remains 44ad1ccb…e0de. Actual individual
banks and transfer descriptors remain relaxed.

A greedy exact row cover of this resident pool uses peaks of 52 literal and
25 math colors. Assigning one fixed bank to each resulting 8×8 class piece is
proven infeasible in the lower class. Allowing per-row word bank ownership with
fixed-bank split masks replays the whole viewport but needs 687 entries and
68 sprites/tile slivers per line. These failures reject these selected small
piece constructions only. A joint legal 8/32 bank/operand/geometry search
continues; no native or production admission is claimed.

The generic offline bound tool now exposes `--reencode-all-visible-actors`.
It covers exact final source outputs for ordinary actors as well as effects
without rewriting alpha metadata or reserving ordinary colors as literal
words. Cross-actor compiled mask ownership is an explicit requirement; no
live compositor capability is admitted. Eight focused tests pass, including
unchanged ordinary reservation behavior and exact all-actor shader demand.

Joint 8/32 fixed-bank searches against the complete-frame candidate remain
bounded UNKNOWN: the selected resident operands use 114,764 variables; reopening
all exact operands uses 984,928. An exact geometry-only rectangle cover reaches
33 objects, eight sprites and 32 slivers, but its color/bank assignment is not
proved. Reopening operands on that cover with legal 8×8 subdivision also returns
UNKNOWN at 121.467 seconds. Restricting the operand corpus to the verified pool's
416 upper-class words reduces the graph to 445,844 variables; it returns UNKNOWN
at 120.503 seconds. A 30-second fractional hint trial produces no primal witness,
and the following integer trial also returns UNKNOWN. None of these results
constitutes hardware infeasibility or permits rejecting raster generally.

The generic geometry constructor exposes `--composite-visible-geometry` and
retains all 12 source actor records, original dimensions and alpha metadata,
plus owner hash 185cb24a68eb29c49f6c8132be98a5d40aa9aa825fe224302959e5a9ad60fbdb.
The generic source-bound replay reproduces the small-piece bank rejection;
there is no synthetic source-alpha flag or live compositor admission. Sixteen
focused tests pass, including explicit overlap, unclipped visible-pixel and
noninteger/out-of-range RGB555 rejection.

A complete-frame all-actor pool restricted to constant ADD and a fully enabled
math window admits 18 peak writes in 106.041 seconds. All 22,179 non-bypassed
pixels are independently checked against the exact source SCREEN output;
source alpha metadata is preserved and no adaptation is selected. The first
local fixed-bank construction reaches 536 OAM entries and 55 sprites/slivers;
its 8/32 compaction is INFEASIBLE. Shared frame-wide word coverage reduces the
count to 528 entries but retains the 55-sliver peak. These reject the selected
constructions only. A joint operand/bank search on an exact 33-object geometry
cover with legal subdivision continues. Source reachability, live compositing
and native concurrent presentation remain unproved.

The constant-control joint cover search returns UNKNOWN at 120.529 seconds
with 439,564 variables and 876,889 constraints. It permits legal subdivision
and reopens exact operands within the whole-frame pool operand corpus; 592,195
branches and 215,409 conflicts provide no infeasibility certificate. The exact
33-object source rectangle cover is a geometry witness only.

Opening the complete exact operand domain and applying safe palette-label
symmetry in the transfer-relaxed geometry search still returns UNKNOWN at
180.926 seconds (643,660 variables, 1,282,277 constraints). The label symmetry
is restricted to this timing-free search; it does not assume adjacent banks
are interchangeable in a CGRAM transfer schedule.
