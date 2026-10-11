# Native authored-underlay OBJ alpha arithmetic

All 55 source effect rows pass isolated native arithmetic and bank-routing
checks over the exact GUILE2 underlay. Each separate case displays one source
row at its original screen position, using the existing fixed OAM banks,
source-derived palette words and compiled two-window descriptor. Registers and
palette are installed while blanked. This does not execute a raster schedule.

The 165 native fields cover 46 add rows, four half-add rows, four subtract rows
and one half-subtract row. All 2,668 non-underlay-equal source pixels match.
The other 83 opaque source pixels equal the underlay and retain that exact
value. Every case checks all 57,344 viewport pixels, CGRAM, OAM, BG/OBJ CHR,
BG tilemap and actual palette/OAM/register observer traces. There are zero
mismatches and no range/time-over flags. BG1 uses nonzero lower-half palette
indices, so black underlay pixels remain real subscreen pixels for halving.

Collecting the observed source rows reconstructs the complete expected RGB555
hash `4d1f01dece9f9a50ecde25d1efc3d9e3da2bc0ee3974fc2702650ee0d9cf2934`.
This is a programmatic collection of separate static cases, not a screenshot
or a claim that a full raster frame ran. The 110 by 90 source frame's 204 RGB555
colors remain unquantized; its authored SCREEN result has 546 RGB555 colors.
The SNES add/half/subtract operands are an exact decomposition of authoritative
BOR SCREEN output, not a half-alpha compatibility adaptation.

The complete reports and observer traces are retained in
`docs/receipts/byor-motu-native-authored-alpha-rows.json.gz`; a concise per-row
report and one actual row-128 screenshot accompany it. The fixture retains
one reproducible ROM path, overwritten only after each emulator session closes.
No PCM is copied. Production assembly and bank zero have no added code.

The independent bank-assignment search keeps all source rows' bank capacity
but relaxes cache continuity outside a selected interval. It independently
rebinds every source word and checks the resulting full-frame cache bound.
An optional HiGHS search keeps piece banks integer while relaxing only cache
variables and logically derived OR domains. These results never admit an
integer interval or full-frame schedule. The default CP-SAT mode independently
replays integer interval residency and favorable prepared transfer costs.

The first full-budget joint search returns UNKNOWN at sixty seconds. The
smaller 128--135 interval trials also return UNKNOWN under their bounded
searches. A 128--132 trial finds a 19-write logical interval, but its favorable
transfer span is 408 clocks and its full-frame cache lower bound rises to
21.928571. It is rejected as a runtime candidate. Trial hashes are retained in
`docs/receipts/byor-motu-bank-interval-refinement.json`.

The subdivided source-exact 70-object encoding now has a full-frame logical
21-write witness: 498 noninitial writes, seventeen-line maximum prefetch,
23 peak sprites and 31 peak tile slivers. Its favorable peak commit span is
still 456 clocks. The complete witness is retained in the interval receipt's
paired gzip. It has no physical or native transfer admission.

Raster feasibility, concurrent actors, register timing alongside palette DMA,
production leases and MOTU Demo certification remain open. No color reduction
was applied.

Validation: 74 focused tests pass. The width audit has 9,825 labels, zero new
violations, zero baselined violations and zero stale baseline entries. The
seventeen protected tracked files retain their hashes.
