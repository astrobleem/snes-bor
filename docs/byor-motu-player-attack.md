The ordinary attack reference preserves the unchanged player_think block in
the derived READONLY_ALTERNATE_ATTACK_ABSENCE_WITH_EMPTY_ITEM_SEARCH lane.
MOTU has no DUCKATTACK, ATTACKBACKWARD or THROWATTACK in its complete animation
universe. RUNATTACK and GET remain real conditional queries, not folded away.

The unchanged C block matches 6912 cases through instrumented chain, frame,
sound and empty-item services. Cases cover full-width input retention, airborne
short circuits, running integers, held DOWN, RUNATTACK/GET availability, weapon
subtypes, chain outcomes, sound presence and post-callback mutations. RUNATTACK
clears running and completes its frame before returning. Ordinary chains set
stalltime to the current unsigned time, complete the chain/frame service, then
read fresh attacking before requesting punch sound. A callback that clears
attacking suppresses that sound. Release has a different ordering and retains
its separate continuation.

An item search must prove its actual type-filtered candidate set is empty. A
matching live candidate requires the full player_test_pickable, GET, didhit,
didfind_item and common_get owners; it cannot be converted into a miss.

The native continuation passes 80 real-constructor/frame-owner cases across all
four player ports and both directions. It executes the actual readonly queries,
empty candidate search, attack-chain owner and frame acknowledgement. RUNATTACK
frame zero executes the real source entity toss owner with zero lift, preserving
altitude, vertical velocity and toss time; the actual frame-effect leaf then
sets horizontal velocity to source +/-2. Query traces verify the DOWN and
weapon-subtype short circuits, including subtype 65545 differing from 9.
Post-frame attacking changes suppress ordinary punch sound. Sound acceptance
and source priority rejection are fixture inputs; physical sound is unbound.

Its 48-byte control block appends to the foreign arena at 7FB7D8. The complete
address plan uses 6152 of 6400 bytes with 248 remaining. Production canvas
ownership, full player_think and physical sound remain required. This is a
component proof, not combat or MOTU gameplay certification. No color reduction,
bank-0 code or PCM copies are introduced.
