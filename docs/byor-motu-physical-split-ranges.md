# Physical CGRAM range partitioning

`raster_slot_layout --split-bank-ranges` permits up to four disjoint prepared
DMA ranges over physical OBJ CGRAM addresses. Ranges may split within a bank
or bridge banks, including transparent word zero. Packet construction fills
bridges from the actual resident state and independently replays all CGRAM
words and indexed pixels. Fixed OAM bank assignment and color-math classes
remain mandatory. This is offline scheduling, not runtime timing admission.

Direct address expressions avoid expanding each event into every possible
bank destination. `--permute-hint-slots` permits a bijective permutation of the
fifteen slots in each bank while retaining the verified hint's lifetime groups.
That family permits cheaper precedence constraints than the unrestricted slot
search. Hints also include packet ranges and event membership; they remain soft
and never grant admission. Tests compare interval costs with exhaustive small
partitions and exercise opaque black, full-bank replacement and bank classes.

For the existing isolated mixed-encoding candidate, the fixed slot family with
16-line lookahead reaches an OPTIMAL minimum of 760 clocks, compared with 776
for the previous bank-hull range family. Both exceed the measured 356-clock
window. The fixed family also fails with 64-line lookahead. Fixed original write
times with free slots fail with identity bank ordering. These results reject
only their specified families.

The unrestricted split-range search and the per-bank slot-permutation search
return UNKNOWN at their 300-second bounds. The relaxed unrestricted search
finds a replay-correct 952-clock construction, outside timing admission. A
separate relaxed permutation search is ongoing. Full scheduler artifacts remain
under out; bounded trial statistics, hashes and nonclaims are in the receipt.

No color reduction is applied. No production assembly, graphics path or bank-zero
allocation changes. The full authored concurrent scene and gameplay remain open.
