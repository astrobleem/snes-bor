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
didfind_item and common_get owners; it cannot be converted into a miss. Native
ordinary-attack binding and physical source sound remain required. This is a
component semantics proof, not combat or MOTU gameplay certification. No color
reduction, bank-0 code or PCM copies are introduced.
