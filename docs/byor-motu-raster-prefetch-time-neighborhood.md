# Bounded prefetch timing with lifetime slot allocation

The generic lifetime solver can now restrict each write to a neighborhood of a
verified physical hint. Slot allocation remains independent. Existing lookahead,
capacity and physical transfer constraints still apply. Free initial palette
loading is preserved when the idle prefix is collapsed. Invalid or incomplete
timing hints fail explicitly.

For the authored 80-piece frame, a one-line timing neighborhood reduces the
model from 43381 variables and 125559 constraints to 7262 variables and 17648
constraints. The resulting physical peak improves from 536 to 504 clocks, with
19 peak actual palette writes, 402 noninitial writes and at most 15 lines of
prefetch latency. All source pixel identities and CGRAM packets replay exactly.

The new trace's ideal bank span is 368 clocks: improved physical packing has
changed the bank event pattern. Neither physical nor ideal cost meets the
336-clock native-tested window. Further timing/bank optimization remains open;
this bounded search does not reject raster presentation.

Focused tests pass 37 cases, including independent packet and pixel replay and
timing-neighborhood validation. The width guard checks 9825 labels with zero
new, baselined or stale violations. All 17 protected files retain their hashes.
No runtime assembly changed. No color reduction was applied. Authored native
raster presentation and MOTU completion remain unproven.
