# Empty find_ent_here candidate sets

The generic `SourceFindHereEmpty_Execute` capability proves the live candidate
set is empty before the geometric portion of `find_ent_here`. It reads actual
canonical existence and per-entity modeldata.type, excluding the caller's slot.
It accepts an exact 32-bit type mask and checks all installed pool slots.
Mutating a live actor to TYPE_ITEM is therefore observable even if the authored
model registry contains no items. It does not substitute an authored-model
count for the live search.

A matching non-excluded live actor produces an explicit
`CANDIDATE_OWNER_REQUIRED` failure. Such an actor still needs source geometry,
vulnerability and the specified predicate. This capability does not claim that
every type candidate would be returned by the full source search. Null is
returned successfully only when the source short circuit cannot reach those
later tests. It cannot be used as an unconditional no-op item service.

The 24-byte caller controls contain B67D readiness, status at +2, excluded slot
at +4 (FFFF is source NULL), mask at +6/+8, and the zero result pointer at
+16/+18. Status 2 proves an empty candidate set, 3 requires the candidate
owner, and 4 rejects the lease/world argument. The result is cleared even on
failure; callers must check carry and status. The root must serialize calls and
own the control region. B4EB entity-core and B4A3 source-world leases must agree
on the active pool extent.

The native proof checks every pool size 1 through 128, low and high type bits,
non-boolean existence values, live/dead/excluded candidates, eight guards,
decimal entry, CPU retention and all actor bytes. The unchanged pinned C search
is compiled in a 32-bit authority shim; its geometric and predicate operations
are unreachable for every admitted empty candidate set. Matching type cases
also demonstrate why an explicit admission fault is needed: their geometric
tests can reject the actor even though the earlier type filter matches.

The reported master-clock peak includes fixture runtime/NMI work. It is not a
production frame-budget admission. The enclosing ground/player controller and
full item touch/pickup owner remain unbound. MOTU gameplay is not certified.
No color reduction is applied.
