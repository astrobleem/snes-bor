# Source movement callback

`player_trymove` delegates directly to `common_trymove` in the pinned 4086
engine. The generic reference preserves the order of grab attempts, bounds,
holes, obstacles, platforms, walls, `testmove`, position publication, and
movement scripts. It also retains the source distinction between wall-policy
truth in `common_trymove` and a positive wall policy in `testmove`.

The unchanged three C functions pass 23,031 service-order comparisons against
the reference. The shim instruments geometric queries, random results, and
script events, recording their order and float argument bits. It does not prove
those service bodies or scripts that mutate actors during a callback.

Two failed reference runs are retained. The first had 36 mismatches, and the
second had 30. Inspection found integer source depth globals and different
Watcom x87 treatment of screen expressions: `common_trymove` spills reused
expressions to float, while `testmove` compares unspilled expressions. The
final reference matches the measured compiler corpus. This is not proof of
the original executable's floating-point behavior.

The source-derived `SOURCE_FLAT_CLOSED_TRYMOVE` capability requires an immutable
stage with no walls, holes or basemaps, no platform declarations, no grab/throw
animations, and no movement/block event scripts. Both authored MOTU stages and
all 16 models satisfy those static requirements. Runtime mutations must revoke
the lease. No actor-name condition selects this capability.

The isolated native callback passes 414 cases against the repaired production
ROM baseline. It reads actual typed entity positions and movement, lifecycle
callback IDs 3/9, per-entity bounds policies, mutable animation caches, the
source camera viewport/depth bounds, and the separate process-wide CRT random
stream. It applies stage and screen bounds and returns source result 0, 1 or 2.
Both world state 1 and the post-update owner state 2 are covered. Coordinates
use the existing explicit `ACCEPTED_COMPAT_Q16_16` adaptation.

When obstacle policy is positive, every live pool slot is scanned for obstacle
or trap type bits, excluding the caller. A matching candidate produces status
4, requiring a geometric owner; it is never fabricated as a null search. Dead
candidates and unrelated high type bits are covered. Invalid leases, callback
IDs, geometry, cache handles and identities produce status 3. Success is status
2. Actor publication is limited to the two position values; sibling actors,
movement inputs, model copies and callbacks stay intact. No world ticket is
acknowledged.

The 96-byte caller region is borrowed from `attack_chain_controls` only in this
isolated fixture. Its B6A5 lease includes status at +2, result at +4, current
stage at +6, model count at +8, actor slot at +10, generation at +12, and zero
hole/script requirements at +16/+18. The production root has not established
the serialized phase lifetime needed to reuse this region.

The enclosing `check_move` owner remains unbound for non-null callbacks. It
still needs persistent `pathblocked`/`grabwalking`, linked movement handling,
actual birth hooks, displacement/timer publication and a joined phase11 owner.
This callback proof is not player movement or MOTU Demo certification. The
MOTU source profile remains unregistered. No color reduction is applied.
