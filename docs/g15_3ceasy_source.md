# G15 Batch E — BOR 3CEASY

3CEASY is imported at physical catalog index 14. Logical BOR Easy progression
is `1A -> 1B -> 1C -> 2EASY -> 3AEASY -> 3BEASY -> 3CEASY -> TITLE`;
physical catalog order remains separate and TMNT/test content is not a BOR
campaign successor.

The authoritative `DATA\\EASY\\3CEASY.TXT` (`# Boat`) contains one panel and
one ordered panel entry, 31 ordered queue records, 30 spawns, and one group.
It has a direct 1UP, two Crates containing Meat (one source `2pitem`), and a
Robert spawn with alias `Steven`, health 300, and `boss 1`. The remaining
authored wave uses Yashiro, Ralf, Shermie, K', Angel, and Joe. There are no
`hole`, `endhole`, or `blocked` records.

Runtime-only identities appended after Batch D are Furnace 34, Steamer 35,
Crate 36, Robert 37, and Steam 38. The selectable roster remains 13 and the
actor capacity remains six. Existing generic obstacle/item, `2pitem`,
identified-enemy, wait/group, and score/life ownership machinery is reused.
Robert is packed as an identified boss; the five source non-enemy records are
kept as prop records.

The source `TYPE_STEAMER` behavior (`steamer_think()` periodically spawning
animated `Steam` entities) is represented by the generic runtime steamer
subtype. It uses the authored Steamer/Steam identities, source camera bounds,
source cadence range, and the existing six actor windows; an exhausted pool
skips an emission safely. Steam children retire when their finite animation
ends. No known 3CEASY source behavior remains missing in this area.
The authored completion boundary is otherwise the existing queue-clear path
and returns to TITLE.
