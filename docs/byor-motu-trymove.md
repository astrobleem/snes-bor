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

The emitted `check_move` capability now joins the actual flat callback with
the actual freeze query, displacement, timer and update-mark publication.
It passes 2,658 native cases. A second unchanged C proof joins `check_move`
with both actual movement callbacks and `testmove`, passing 15,552 cases.
It checks unsigned `pathblocked` wrap, callback return handling, duplicate
updates, due timers, freeze gates, and restoration of the previous `self`.
Its linked-move and freeze service bodies are instrumented.

Persistent movement rows store unsigned `pathblocked` and signed `grabwalking`
at 42BB80..42BF7F. Controls at 42BB40..42BB7F precede the rows. Existing pain,
hit-identity, pending-jump and physics addresses stay fixed. The extra 1,088
bytes reduce staging from 49,024 to 47,936 bytes. Conversion descriptors retain
all 896 8bpp and 512 2bpp tiles by splitting transfers. All 128 pool extents
are checked for fixed neighbors and safe descriptor boundaries.

Movement storage passes 558 native cases. Pain storage passes another 558
at the new boundary; pending-jump storage passes 1,434 across its original
capacity and the progressively smaller hit, pain and movement boundaries.
All reject zero capacity and overlap. Birth clears movement state; model
changes retain it. The native joined owner reads actual movement rows and
updates blocked-path state using the real callback return. If both grabbing
and grabwalking are nonzero, it explicitly requires the linked-movement owner.

These remain isolated, emitted capabilities. Actual constructor hooks, the
serialized arena lifetime, production CHR grants and the full phase11 owner
are unbound. This is not MOTU Demo certification. The MOTU source profile
remains unregistered. No color reduction is applied.
