# Shared geometry for exact math bank classes

The generic global-word bank constructor can now solve both eligible math
classes together under a shared scanline tile ceiling. Each word and eligibility
domain retains one fixed bank for the frame; every OAM mask keeps that bank.
Rolling palette unions and the requested tile ceiling are independently
replayed. OAM and sprite admission remain explicitly deferred to legal
compaction. The original separate-class construction stays the default.

The peak HBreath source frame over GUILE2 now has a two-row-retention
construction with 162 small objects, 33 sprites and 33 tile slivers. This raw
layout is rejected for OAM/sprite admission. Exact legal 8/16 compaction selects
40 merges and produces **80 objects, 24 peak sprites and 34 peak tile slivers**.
This improves on the earlier separately allocated two-row construction, which
could not meet the tile limit. All source pixels and words replay exactly.

The resulting fixed banks admit a **17-write full-frame logical schedule**,
matching the independently validated cache LP lower bound. There are 408
noninitial writes, 34 peak logical CGRAM bytes and sixteen-line maximum
prefetch. Schedule hash:
`121c0ffd01eca3c671dfc42aae78a591e1c26dc9eaa3419cc05d8262e2952110`.
The source output hash remains
`4d1f01dece9f9a50ecde25d1efc3d9e3da2bc0ee3974fc2702650ee0d9cf2934`.

Legal Mode-0 CHR/OAM compilation uses 6,400 CHR bytes, 200 occupied cells and
163 unique tiles. CHR hash:
`858cf9a60c837143b3e934aa285d584d89ecaeebf8e8fb1a3407bcd7d2debf18`;
OAM hash:
`bf833beb8c74aab5c64042c7d41e2cd20f50797d39fc30395f1018f6bd5c9d2a`.

**This is not physical transfer admission.** The favorable prepared high-byte
commit span peaks at 360 master clocks. Exhaustively checking all 576 fixed
bank permutations preserving math eligibility does not reduce that peak. This
rejects these fixed write times even against the full 356-clock hardware
window. A general-range residency search at 308 clocks returns UNKNOWN after
sixty seconds. Hinted restricted adjacent-range searches at 308 and 332 clocks
also return UNKNOWN. Neither rejects different residency or the raster
approach. The 332-clock trial is an isolated-path target informed by the older
held-BRA first-commit range; it is not the stressed runtime's admitted budget.

The complete logical witness, lower-bound certificate, exhaustive permutation
bound, CHR/OAM hashes and bounded trial summaries are retained in
`docs/receipts/byor-motu-joint-bank-classes-cache17.json` and its paired gzip.
Native authored alpha arithmetic is covered separately by the 55 static-row
cases. Full raster timing, concurrent actors, animated uploads and gameplay
remain open. No color reduction was applied.

Eleven focused global-bank, constructor and compactor tests pass, including
combined tile rejection, explicit raw sprite deferral, global word identity,
rolling union capacity, bank eligibility and source-exact constructor replay.
All seventeen protected tracked files retain their hashes.
