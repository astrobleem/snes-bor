# Authored alpha: exact bank refinement and prefix residency

The generic bank refinement tool evaluates bounded piece moves and swaps with
the independently checked fixed-bank cache LP, including optional validated
capacity dual pressure. Every accepted assignment independently replays the
original per-pixel words. LP improvement remains a necessary bound only.

For the isolated GUILE2 HBreath peak, the 48-object layout remains at
20.285714 required peak writes in the relaxation. The 52-object frame-cover
layout improves from 20.714286 to 20.142857. Targeted follow-up moves do not
improve either result. Subdividing eight selected 16-pixel squares into legal
8-pixel squares preserves source pixels and produces 70 objects, 23 sprites
and 31 tile slivers; the fixed-bank lower bound remains 20.142857. Subdivision
now regenerates the schedule hash and removes inherited physical/native
admission. It does not reuse the input's compiled schedule identity.

The joint bank search can preserve exact hinted words and color-math classes
while changing each rectangle's fixed bank. Optional pool gaps count occupied
slots, future initial preloads count slots throughout their lifetime, and an
actor-free screen prefix can hold the first required row's palette selected
during VBlank. A preload bug previously attached the initial restriction to
later chunks; those old failed trials are excluded from resource verdicts.
Tests require a full fifteen-slot bank to load a sixteenth future word later,
and check gap retention and inactive-prefix replay.

Both corrected fixed-48 controls reproduce source-exact 21-write schedules.
Their total noninitial writes are 535 and 506, respectively; maximum prefetch
latency is nine lines. Both still require a favorable prepared-DMA high-byte
commit span of 456 master clocks. They have no physical transfer admission.
This exceeds the full 356-clock CGRAM hardware window; the measured stressed
runtime has a tighter budget. Lower total writes have not resolved peak cost.

A separate two-row global word-bank retention construction preserves pixels
but uses 161 objects, 36 sprites and 36 tile slivers. Its bounded 8/16 compactor
finds no legal merge selection. The compactor now returns that explicit
geometry failure rather than losing its report to an assertion. This rejects
that constructed layout, not raster rendering or all two-row assignments.

Bounded summaries and artifact hashes are retained in
`docs/receipts/byor-motu-fixed-bank-refinement.json`; corrected full witnesses
are retained in its paired gzip. Source SCREEN alpha remains exact in the
offline pixel replay. Native authored alpha, physical slots and transfers,
concurrent actors and MOTU gameplay certification remain open. No color
reduction or production assembly change was made in this work.

Validation: 69 focused joint, bank, refinement, compactor and constructor tests
pass. The width audit reports 9,825 labels and zero new, baselined or stale
violations. All seventeen protected tracked files retain their original hashes.
