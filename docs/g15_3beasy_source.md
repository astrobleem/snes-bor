# G15 Batch D — BOR 3BEASY

3BEASY is imported from the authoritative BOR v3.0 PAK at physical catalog
index 13. Logical BOR Easy progression is source-ordered and now ends at the
temporary TITLE boundary after `1A -> 1B -> 1C -> 2EASY -> 3AEASY -> 3BEASY`.
The physical catalog remains separate from campaign order; TMNT and standalone
test content are not BOR campaign successors.

The source `DATA\\EASY\\3BEASY.TXT` (`# Boat`) contains three boat panels and
24 ordered panel entries, 38 ordered queue records, 31 spawns, two waits, five
groups, and four Box obstacle records. Two Box records contain Meat, including
one `2pitem` record; two contain Apple. The level has no `hole`, `endhole`, or
`blocked` records, and no authored boss flag.

Source identities are Ralf, Joe, Box, Shermie, K', Angel, and Yashiro. Batch C
already supplies all required runtime identities and generic behavior: Angel
29, Shermie 30, K' 31, and Box 33 are appended runtime-only identities; Ralf,
Joe, and Yashiro retain their existing identities. The selectable roster
remains 13 and actor capacity remains six.

The authored final encounter is three K' records followed by the final wait,
not a boss-flagged actor. Completion uses the existing queue-exhaustion/clear
boundary and returns to TITLE. No new generic primitive was required in Batch
D; the accepted identified-enemy, obstacle/item, `2pitem`, wait/group, and
six-actor machinery is reused.

Angel's source colourmap set contains more variants than the packed level map
field can encode; the existing bounded SNES presentation adaptation remains
explicit.
