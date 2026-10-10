# Temporal bank assignment

The generic fixed-bank color-mask solver has an optional rolling residency
window. It restricts each bank's union of required colors across nearby rows
to fifteen opaque slots before physical slot allocation. Defaults and ordinary
static source presentation are unchanged. Final source pixel replay,
compaction, OAM, sprite and tile admission remain mandatory.

In the controlled black-underlay He_Man/HBreath pose, a two-row window with
at most forty distinct full-frame colors per bank produces a source-exact
97-OAM encoding, peaking at 22 sprites and 34 tile slivers. Greedy logical
scheduling needs sixteen peak writes. The separately validated fractional
cache bound is fourteen, compared with 16.2 for the previous balanced-37
encoding. The scene retains 293 opaque output colors and 69 peak row colors.
These are improved bank assignments, not physical/native timing admission.

The three-row restriction has a measured failure: rows 129 through 131 need
123 distinct RGB555 colors, while eight OBJ banks have 120 opaque slots. The
compiler reports `WINDOW_UNION_CAPACITY_LIMIT` without invoking a solver and
marks universal raster rejection false. Raster may evict between these rows;
that remains permitted outside this restricted family.

Fourteen-write/312-clock and fifteen-write/328-clock cache searches reach
their thirty-second solver bounds without a candidate. Physical fixed-time
and hinted slot-permutation searches likewise remain unresolved. Greedy
physical searches fail at line 128. None of these outcomes reject raster
universally. The retained artifacts distinguish exact pixel witnesses,
fractional necessary bounds, restricted infeasibility and solver limits.

Focused palette/context/compaction/CHR tests pass (23 tests); the added
window tests exercise both integer backends and preserve the original
sixteen-color row identities through splitting. The width guard reports
9,825 labels, zero new failures, zero baselined failures and zero stale entries.
No color reduction is applied.

The private native executor also skips DMA register setup on 193 empty rows
of the controlled effect schedule. A fresh four-field SA-1/production-NMI
2,814-byte-queue proof remains pixel exact, with no packet, OAM, context or
unsafe-commit faults. It does not admit a production gameplay lease.

Evidence summary: `docs/receipts/byor-motu-temporal-bank-assignment.json`.
