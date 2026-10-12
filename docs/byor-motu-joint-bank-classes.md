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

Repairing only rows 127--145 finds a source-exact full-frame 19-write schedule
whose favorable endpoint bound is 352 clocks. It has 402 noninitial writes and
sixteen-line maximum prefetch. Fixed write-time physical slot placement in the
paired-range family is infeasible even at 356 clocks: ideal packing cannot be
assumed to respect live slots. Tightening the residency repair to 332 clocks
returns UNKNOWN, as does flexible rectangle-lifetime slot placement at 332.
These bounded results and the 352-clock logical witness are retained in
`docs/receipts/byor-motu-joint-bank-classes-physical-repair.json` and its gzip.
No physical admission follows from that witness.

The physical layout and greedy compilers now include source-bound math modes
and color-window descriptors in their schedule identity. Existing schedules
without those controls keep their original hash payload. Twenty-one focused
slot-layout/greedy tests pass; the width audit remains clean at 9,825 labels.

A loose 2,000-clock slot solve supplies an independently replayed physical
hint with a 904-clock peak. This proves packet data and slot identities only;
it exceeds the hardware window. Allowing per-bank permutations of those hint
slots and flexible eight-line prefetch is infeasible at 332 clocks. A broader
two-line demand-gap rectangle search returns UNKNOWN. Neither result rejects
different lifetime groupings or unrestricted slot layouts. Thirty combined
global-bank, constructor, greedy and slot-layout tests pass.

The generic lifetime component recoloring follow-up preserves all 57,344
viewport output pixels, including exact source SCREEN over GUILE2. A new
complete integer cache limits write-active banks to six and has a 336-clock
optimistic bound, nineteen peak writes and ten-line maximum prefetch.
It solves in 10.151 seconds. Physical lifetime recoloring produces a valid
456-clock witness, still above the measured transfer window. Liveness shifts,
all 576 eligible bank permutations with 256 slot reflections, and three
twelve-second local slot repairs do not lower that peak. These are restricted
family results, not rejection of lossless raster presentation. The full
source replay and bounded schedules are retained in
[the authored follow-up receipt](receipts/byor-motu-authored-kempe.json)
and its compressed archive. No color reduction or alpha adaptation occurs.
