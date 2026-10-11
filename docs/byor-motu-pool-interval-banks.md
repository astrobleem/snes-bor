# Authored alpha: bounded bank copies and logical cache21

The generic joint solver can now preserve a saved pool word's residency through
a whole interval or bounded chunks. Each chunk permits a configured number of
bank copies. The OAM bank remains fixed for every piece, and every newly loaded
copy consumes a palette write. Retaining a copy across chunk boundaries consumes
zero additional writes. Optional unused words may be omitted. Initial preloads
are restricted to words present in the first saved pool row; their slots remain
counted through the entire preceding screen interval.

The later optional future-preload, gap-bridge and inactive-prefix construction
is described in `docs/byor-motu-fixed-bank-refinement.md`. The first-row
restriction above remains the default, not a hardware limitation.

This is an explicitly restricted construction, not a complete raster solver.
Every visible non-underlay-equal source pixel must lie within the saved controls.
The existing source-bound math/window checks and independent pixel replay remain
required. Source hints supply geometry and pixel choices; their incompatible
per-row residency is not hinted into the interval variables. Defaults keep the
existing unrestricted residency search unchanged.

A three-piece test requires two copies of one shared word: one copy cannot fit
the fixed rectangles' 15-slot banks. A second test loads 22 distinct words plus
that duplicate on row one, proving 23 writes. A 22-write cap fails; a 23-write cap
replays exactly, with zero writes on the next two chunk boundaries. Both solver
backends also replay the simple single-bank interval fixture.

For the source peak HBreath frame over GUILE2, the formulation reduces the free
8/16 geometry model from 90,000-plus variables to 20,217 for whole intervals or
23,801 for eight-row chunks. Full-interval trials with sixteen-line lookahead
reject that residency restriction. Extending lookahead to 55 lines allows search
but finds no incumbent at sixty seconds on the free grid. The compact 51-object
fixed-rectangle layout rejects full intervals even with four permitted copies,
55-line lookahead and a 24-write cap. Both CP-SAT and HiGHS eight-row chunk
trials at 24 writes return UNKNOWN after sixty seconds. None rejects raster
presentation generally. Bounded trial summaries and hashes are retained in
`docs/receipts/byor-motu-authored-alpha-pool-interval-search.json`.

A separate residency solve for the source-exact rebalanced 48-object encoding
finds a **21-write full-frame fixed-bank logical schedule**. It preserves the
same final RGB555 hash as the fifteen-write class pool:
`4d1f01dece9f9a50ecde25d1efc3d9e3da2bc0ee3974fc2702650ee0d9cf2934`.
Geometry remains 48 objects, sixteen sprites and 34 tile slivers. The 55-line
allowed lookahead uses at most nineteen lines in replay. There are 539
noninitial writes. A twenty-write solve is infeasible for this fixed encoding.
The complete source-pixel and fixed-bank witness is retained as
`docs/receipts/byor-motu-authored-alpha-fixed48-cache21.json.gz`.

**This schedule has no physical transfer admission.** Its bank updates require
as much as 456 master clocks even with ideal endpoint packing and four prepared
ranges. On rows 134 and 139 this is the high-byte commit span; the corresponding
first-to-last byte span is 464 clocks. An even more optimistic bound granting
all adjacent bridges without intermediate charges is still 432 clocks.
Twenty-one writes means 42 logical palette bytes, not a native
transfer budget. A 356-clock residency search with freely packed endpoints
returns UNKNOWN after sixty seconds. Its restricted single/adjacent-pair range
variant is infeasible at 21 writes and 356 clocks. Physical slots, actual ranges, register
updates, native alpha routing and concurrent actors remain unresolved.

The focused joint, bank-residency and rebalance suites pass 54 tests. The width
guard has 9,825 labels and zero new, baselined or stale violations. All seventeen
protected files retain their hashes. No production assembly changes and no
color reduction applied. MOTU Demo certification remains incomplete.
