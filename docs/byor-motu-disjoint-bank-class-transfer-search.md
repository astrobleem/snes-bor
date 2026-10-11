# Transfer-aware fixed-bank mask searches

The global-word interval-transfer solver now accepts disjoint palette-bank
eligibility classes. Literal presentation and eligible OBJ color math can
therefore participate in the same transfer calculation. Overlapping domains
still reject explicitly because their row-capacity aliases require a separate
model. The existing uniform-domain path remains the default. A selectable SAT
strategy changes search execution while retaining the same model and replay.

The authored BR12 encoding produces a complete global-word geometry witness at
50 OAM entries, 17 sprites and 34 tile slivers. Independent fixed-bank cache
analysis gives a 31-write lower bound. Word balancing changes geometry to 62
entries and 18 sprites, still at 34 tiles, but its interval bound remains 29
writes. These encodings exceed the demonstrated prepared-DMA window.

Three transfer-aware trials return UNKNOWN after 60 seconds each: the native
345-clock strict target with portfolio and SAT strategies, and a relaxed
9999-clock target that retains the 21-write limit. UNKNOWN supplies no
infeasibility proof.

The cache decomposition solver additionally accepts row-word masks. A source
word can use different fixed-bank masks on different rows. Each emitted OAM
mask retains one bank, and its full rectangle contributes to the 128-entry,
32-sprite and 34-tile limits. This does not change OAM bank selection during a
scanline. Both retained neighborhood trials preserve all 2668 non-bypassed
source pixels, their exact RGB555 operands, positions and bank eligibility.
The initial 33-object family has a fractional clock bound of 408.665; the
101-object family has 359.650. Neither bounded search improves its initial
bound. These are assignment-specific lower bounds, not universal raster
rejection. Integer cache residency, physical slots and native execution remain
unadmitted.

The receipt retains complete witnesses, bounded trials and hashes. All 17
protected file hashes match. Thirty-eight focused tests and the width audit
pass with 9825 labels and zero failures. Source alpha remains exact BOR 4086
SCREEN, followed by RGB555 conversion. No color reduction is applied.
