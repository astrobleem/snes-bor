# Generic actor bank domains and source-exact geometry

The controlled black concurrent source pose has a ten-color peak row for
He_ManB and a 59-color peak row for the exact precomposited HBreath output.
An explicit domain experiment confines actor index 0 to bank 3 and actor
index 1 to the other seven banks. These are experiment inputs, not model-name
conditions or production reservations.

The first bounded CSP search finds no candidate in 60.031 seconds. HiGHS
finds a valid fixed-bank assignment, and exact compaction reduces the 146
small objects to 45 legal objects. Peak geometry is 12 sprites and 33 tile
slivers per scanline. Source dimensions, opaque black and transparent pixels
remain intact. This is a geometry proof, not transfer admission.

That selected bank assignment is quantitatively unsuitable for the current
transfer window. Its independently validated fractional cache lower bound
is 33.5 writes per line, with primal violation below 8e-15 and zero dual
residual. Integer scheduling therefore needs at least 34 color writes on
some line, even before physical address/range overhead. The optimistic
first-to-last high-byte commit span is at least 16*(34-1) = 528 clocks,
exceeding both the measured 344-clock fixture window and the generous
356-clock bound. The 21-write integer search times out without a candidate;
the LP certificate, not the timeout, supplies this fixed-assignment rejection.
Other assignments in the same actor domains remain open.

The isolated compiler now accepts generic per-actor bank domains and the
existing CSP, HiGHS or bounded-integer CP-SAT bank search. Defaults retain the
existing CSP path.
Compaction preserves the intersection of merged child domains and rejects
an input bank outside its domain. Actor names do not select behavior.

The HiGHS assignment solver also accepts a necessary interval write bound.
For each tested interval, per-bank color unions exceeding 15 resident slots
must fit the permitted writes after the interval's first row. The resulting
assignment is independently checked against every interval bound. This
prevents geometry-only optimization from silently accepting arbitrary cache
bandwidth. It does not establish physical slots, CGRAM ranges or native timing.

Equivalent logical bank labels can use first-use precedence; distinct
per-piece eligibility signatures remain separate. Physical address costs are
absent from this assignment model and require a separate transfer search.
Both the complete interval model and its symmetry-reduced variant return
UNKNOWN in bounded CP-SAT searches; neither rejects the actor-domain family.
The original interval HiGHS run also reaches its limit without a candidate.

All 29 focused palette, compaction, reservation and isolated-context tests pass, including
bank-domain intersections, invalid domains and the exact 15-write boundary
for two disjoint fifteen-color rows. A reservation regression exposed an old
ordering bug: the input bank domain was narrowed before its old pixels were
replayed. Rebuild now reads the original valid input and applies narrowed
domains only to the proposed output. Input immutability and final reserved
bank exclusion are checked. All 31 downstream bank-order, constructive slot
and physical-layout tests pass as well. No production code or bank-zero code
changes. NO color reduction applied. Concurrent native admission and the
authored peak / full MOTU Demo gates remain open.
