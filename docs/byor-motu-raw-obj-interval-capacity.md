# Raw OBJ palette capacity under color-math eligibility

The color-capacity tool now derives an optimistic interval bound for each bank
count from one through eight. Bank assignments and geometry are relaxed only
for a necessary impossibility bound; this can never establish feasibility.

The peak source HBreath frame still has 204 opaque RGB555 colors, 54 on its
busiest row and 32 maximum adjacent newly required colors. Source rows 38 and
39 together require 85 distinct colors. A direct presentation using only the
four color-math-eligible banks has sixty opaque slots, so at least 25 new color
commits are unavoidable between those rows. Lookahead cannot eliminate them:
the preceding row's required colors must also remain resident until used.

At the measured eight-clock data-byte rate, even granting a preloaded first
low byte and excluding all address/setup/contention costs, 25 high-byte commit
points span at least 384 clocks. That exceeds the measured 356-clock safe
window. This rejects direct raw-color presentation in four banks under that
transfer window. It does not reject exact context-derived mixed opaque/additive
encoding in eight banks, other presentation architectures or all raster methods.
The four-bank allocation alone also does not establish BOR SCREEN equivalence.

The older interval bound treated a transfer-point window as a byte-duration
budget and granted only one preloaded low byte across a multi-line interval.
The corrected calculation grants endpoint write points and a low preload for
each HBlank. For example, 23 commits can fit the optimistic 356-clock data-only
span bound (352 clocks); 25 cannot. Address/setup costs remain separate. Do not
use historical interval receipts as final hardware rejection without recomputing
them with this correction. The prepared-range setup bound is unchanged.

The bounded receipt records source and frame identities, every bank-count bound
and explicit nonclaims. No color reduction, runtime policy adaptation or gameplay
certification is introduced.
