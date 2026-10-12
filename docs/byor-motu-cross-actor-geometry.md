# Source-exact cross-actor OBJ geometry probe

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
