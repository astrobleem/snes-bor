# Subscreen row-mask clock search and concurrent geometry reservations

The authored BR12 peak is tested with the previously validated subscreen ADD
operand encoding. This domain permits all eight OBJ banks for the isolated
effect. It preserves the RGB8 BOR 4086 SCREEN result projected to RGB555;
neither color reduction nor alpha adaptation is applied. Concurrent ordinary
actors have not been admitted to this screen routing.

The first row-word mask search evaluates five assignments and reaches a
405.960549-clock fractional cache bound in 189.203 seconds. Its geometry is
108 OAM entries, 32 sprites and 32 tile slivers per line. The resumed wider
search restores the five dual certificates and evaluates seven assignments,
reaching 401.384730 clocks in 264.031 seconds. The latter uses 128 OAM entries,
32 sprites and 32 tile slivers. Both exceed the isolated 344-clock window;
these assignments supply no integer or physical transfer candidate. These
bounded searches do not reject other assignments or raster presentation.

The compact receipt retains every iteration's independent dual, primal and
interval-bound checks. Its gzip companion retains both complete schedules
and cumulative certificates. Independent replay verifies the same 2,668
encoded source pixels, fixed rectangle geometry, bank eligibility and
source-composed frame hash. The 83 exact underlay bypasses remain intact.
All 17 protected file hashes match.

`raster_piece_cache_decomposition.py --geometry-reservation` now accepts other
actors' OAM count and per-line sprite/tile-sliver counts. The row-mask master
subtracts these from the actual 128/32/34 hardware limits. An initial seed
that exceeds the reservation can supply a valid cache dual cut but cannot be
returned as an admitted candidate. The reservation changes only the geometry
constraints; cached duals remain bound to the existing source/cache basis.
This option proves geometry capacity only. Palette, alpha, layer routing,
upload, lifetime and native timing admission remain separate requirements.

Twenty-seven focused decomposition, bank-cache, interval-cache and bank-class
tests pass. They include independently exhausted OAM, sprite and tile
reservations, valid reduced capacity and malformed reservation rejection.
The width audit has 9,825 labels and zero failures. Authored full-peak native
presentation, concurrent actor admission and MOTU completion remain open.
