# Legal OBJ size pairs and visible-pixel bounds

The joint source-pixel scheduler and CHR/OAM compiler now support the global
8/16, 8/32 and 16/32 square OBJ size pairs. Every emitted piece uses one fixed
palette bank throughout its height. Mixed geometry preserves source pixel
ownership and exact RGB555 replay; it does not permit three simultaneous sizes.
The existing 8/32 candidate retains its original CHR and OAM hashes.

Bounded 300-second searches of the isolated peak effect with 8/16 and 16/32
geometry returned UNKNOWN. These are retained solver trials, not hardware
infeasibility or native admission. The bounded receipt records their hashes and
solver statistics.

An independent optimistic geometry bound grants arbitrary row alignment, masks,
palette assignment and legal OBJ width. It counts the minimum eight-pixel tile
slivers needed for each actor's visible row. The current grouped player, enemy
and HBreath pose needs at least 15 slivers at its peak, below the hardware limit
of 34. Geometry therefore does not reject raster for that pose. This bound does
not prove the pose reachable or construct a complete fixed-piece schedule.

Focused tests cover legal size modes, decoded pixels, illegal global size pairs,
opaque black, clipping and exhaustive small interval-cover cases. No production
presentation path changes and no color reduction is applied.
