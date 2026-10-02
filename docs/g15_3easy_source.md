# G15 Batch C — BOR 3AEASY

3AEASY is imported from the authoritative BOR v3.0 PAK as physical catalog
index 12 and is resolved logically, rather than by catalog adjacency, as:

`1A -> 1B -> 1C -> 2EASY -> 3AEASY -> TITLE`.

The source level is `DATA\\EASY\\3AEASY.TXT` (`# Boat`): six `boat2` panels,
30 ordered panel entries, 31 active spawn records, three waits, four groups,
two Box records containing Apple/Gold, and no hole, endhole, blocked, or
2pitem directives. Existing wait/group, breakable/item, six-actor, and
2pitem machinery is reused.

The appended runtime-only identities are Angel 29, Shermie 30, K' 31, Billy
32, and Box 33. They are not selectable; the normal player-selection roster
remains 13. New enemy records use the identified ordinary-enemy subtype so
their source model is loaded without acquiring boss status. Angel's fifth
source remap is outside the two-bit level map selector; the first three
source-ordered remaps are packed as a bounded SNES presentation adaptation.

The level has no authored `boss` flag. Its final Yashiro/Ralf/Billy wave is
therefore a normal source enemy queue; completion is the existing all-enemy-
clear plus queue-exhaustion boundary and returns to TITLE. Heavy, holes, and
the distinct Biker-K' runtime are not part of this level.
