# Ordered source attack scan

`AttackLoop_Begin` executes the actual native attack gate, owner preparation
and unsigned identity assignment. `AttackLoop_Poll` scans physical source slots
in order through the actual target predicate and normal/counter collision
helpers. It uses the remaining eight bytes of the existing pain/contact
controls: cursor +56, admitted slot +58, state +60, and reserved +62.
It adds no persistent arena or CHR allocation.

The unchanged pinned `do_attack` loop header and outer predicate pass 768
32-bit C scan-prefix cases. The hit body is instrumented to change the current
animation pointer at the first admitted target, proving the source `!followed`
stop condition. Collision results are instrumented in that C proof; the native
proof uses the real collision routines.

The corrected isolated native proof passes 778 cases. It checks every pool
size 1..128, first and last attacker slots, empty scenes, all-live scenes with
real collision misses, first admitted targets, repeated pending polls, and
invalid generations/tables/world leases. The observer records each slot
presented to `AttackTarget_Run`; the complete ordered trace must match the
expected prefix. Persistent actor, hit and pain rows are compared separately.
The initial run failed because a Lua observer used a reserved keyword as a
field expression; it produced no valid scan traces and is retained as FAIL.

No-hit completion returns zero. An admitted target returns `8111`, the required
hit-service ticket, before either `ondoattack` callback. Polling that ticket
does not repeat target selection or consume another attack identity. No API
accepts a fabricated damage result, and no world-phase acknowledgement occurs.
The hit contact and original preparation record remain available to the real
callback owner. Actual hit services must eventually resume the rest of the
source loop and its post-loop behavior.

Preparation now accepts a positive CHR capacity below the original pain-row
boundary, with matching hit/contact descriptors. The loop proof uses 47,936
bytes, agreeing with the movement-state carve. The original 310-case
preparation matrix also passes against the repaired ROM with the new emitter.
Bank 0 is byte-identical to that ROM in both proofs.

This is not complete `do_attack`. The earlier defense-threshold expression,
`ondoattack`, ownership/ground exclusions after confirmation, blocking, damage,
effects, followups, pause, pain timing, hit-ID publication and final sound/cost
services still require their real owners. Original-binary float equivalence is
not claimed; collision uses the explicit Q16 coordinate adaptation. The MOTU
profile remains unregistered and gameplay is unproven. No color reduction is
applied.
