# Actual constructor to changing spawn weapon

The isolated native fixture now completes actual player construction, authored
JUMP frame zero and checked spawn recovery before saved weapon 1 changes the
source model through the existing native resolver and model-transition owner.
The target identity is derived from the source weapon list, without an actor-name
branch in the service bundle. Both direction cases pass.

Observed pending services are 1, 2, 3, 5, 6 and 7, followed by completion.
Service 4 executes synchronized animation inline during service-3 acknowledgement;
its native state is 2, branch 1 and source handle 40. The observer verifies the
inherited animation cache, scalar cached model, entity core including fallbacks
from the already verified constructed entity, retained health/MP and dynamic core
suffix, player identity, weapon metadata, script identity, alpha and RUN snapshot.
It writes no acknowledgement. Source model 3 changes to source model 4 while
the entity retains its player type.

This join exposed a shared scalar emitter defect: Poppy encoded the long
`ModelScalarService_Styles+2` expression with bank zero. The low word used the
correct bank; the high word came from unrelated ROM. An explicit high-word label
now retains the correct bank in the generated operand. Native word observations
and the full join pass after that correction.

A separate native scalar regression passes all 124 cases, including signed
32-bit style values with distinct nonzero high/low words, three entity slots
and stale-lease/request rejection. Those style inputs are explicitly synthetic;
source-derived alpha remains intact. The [wide-style receipt](receipts/byor-motu-model-scalar-wide-styles.json)
records the inputs, counts and artifact hashes.

The weapon child costs 649,216 and 649,334 master clocks, including native timing
table validation and model services, excluding construction/recovery. These are
measured component costs, without production frame-budget admission. Bank zero
is byte-identical. The fixture installs controlled foreign/global leases and
source tables; scalar media bindings, independent current-palette publication,
full spawnplayer, gameplay and MOTU profile registration remain unproven here.

The [receipt](receipts/byor-motu-player-spawn-model-change.json) retains bounded
native observations and hashes. The media alias was moved with an identity check
to avoid the filesystem hardlink limit. No PCM copies or color reduction.
