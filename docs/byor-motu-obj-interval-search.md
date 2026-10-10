# Exact OBJ interval search

The isolated peak HBreath pose has a pooled integer residency candidate with
15 new colors per line and a fractional lower bound of 14.428571. The concurrent
pose's corresponding candidate needs 20. Neither candidate establishes fixed
OAM banks, physical slots, transfer destinations or native timing.

An optional restricted search keeps each pooled residency interval in one bank.
This tests a constructive family, not every possible schedule. The concurrent
45-second and isolated 60-second trials return UNKNOWN without an incumbent.
The isolated trial has 41,632 Boolean variables and 52,776 constraints. These
results do not reject lossless raster presentation.

A reload after a pool gap now consumes writes even if that color was in the
initial VBlank palette. A regression forces an intervening full palette and
checks that a later zero-write window cannot reload the evicted color for free.
Selected OAM masks must own visible pixels; omitting unused masks preserves
valid rendering and removes useless search decisions.

The backend retains only its last 64 log lines, each bounded to 512 characters.
Worker logs demonstrate substantial search even when the primary worker's
counters remain low: one concurrent 180-second trial recorded 3,538,592
conflicts in the no-LP worker. No candidate was found. This is a bounded search
result, not measured hardware infeasibility.

All 55 focused tests pass. The 17 protected tracked hashes match; the width
guard has 9,825 labels and zero new, baselined or stale sites. No production
assembly, bank-zero bytes, media or static presentation path changed. No color
reduction was applied. MOTU remains unregistered and uncertified.

[Evidence receipt](receipts/byor-motu-obj-interval-search.json).
