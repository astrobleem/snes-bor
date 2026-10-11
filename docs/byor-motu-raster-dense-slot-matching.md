# Explicit matching for dense palette-bank rows

The free-residency solver now explicitly matches distinct demanded words to
distinct slot indices. When all fifteen words are demanded, slot values are
restricted to those fifteen words and are distinct. These are redundant source
capacity constraints; duplicate residents remain allowed in banks with spare
capacity. Fixed OAM banks, pixel identity and physical change accounting remain
unchanged.

The focused suite passes 34 tests. A dense-bank fixture preserves opaque RGB555
zero, replaces all fifteen colors between rows and independently replays its
224-clock physical packet. The exclusive 225-clock gate succeeds; 224 fails.

The authored free-residency 336-clock gate remains UNKNOWN after a bounded
50-second search. A looser search retains a 536-clock complete witness while
preserving the 336-clock ideal bank bound. Separately, lifetime timing searches
reach a complete 472-clock physical witness, with 21 peak changes and an ideal
bank peak of 400 clocks. Geometry remains 80 OAM entries, 24 sprites and 34
tile slivers at peak. Neither witness meets native timing.

The authored underlay has 58 source colors, 596 tiles and separate lower-half
CGRAM ownership. Exact canonical mode alternatives exist on 27 rows under the
saved bank assignment; the crowded middle rows retain only add. Twelve legal
single-bank move probes find a 536-clock greedy witness, which lifetime packing
reduces to 520. A separate 32-proposal LP search does not improve the saved
assignment's validated 17-write fractional lower bound. These are bounded
family/search results, with no universal raster rejection.

All 17 protected files retain their hashes; the width audit checks 9825 labels
with zero failures. No runtime assembly changed. No color reduction was applied.
Authored native raster, concurrent actors and MOTU completion remain open.
