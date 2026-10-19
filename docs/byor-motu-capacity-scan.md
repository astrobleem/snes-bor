# Capacity prediction: measured gain, strict recovery-gate rejection

**No new accepted renderer.** The accepted native fixture remains the
[publication-fusion and cancellation-copy result](byor-motu-abort-copy.md).
The [current budget](byor-motu-current-budget.md) explains why runtime integration
now has priority over further capacity-scan tuning.

The opt-in experiment replaces only the conservative predictor entry with a
same-bank jump. Its bank-local pending-map/reference reads retain the original
1,024-word scan, 76-byte temporary bitmap, decision, final counters, CPU
registers/flags, DBR and stack. It adds no RAM/VRAM allocation. Both CPUs are
observed for forbidden authority/metadata writes. Only the exact bitmap-store
PCs in the empty-record/queue lifetime are admitted by the inherited guards.

The 179-byte candidate is ROM
`267d1f14cdb5d2e2b82135789695be9f28b870448f8243160d126ee574490454`.
The disabled build exactly reproduces the accepted ROM. Independent review
reconstructs the candidate from only its six-byte dispatch and helper range.

| Measured case | Accepted clocks / fields | Candidate clocks / fields |
|---|---:|---:|
| Ordinary epoch 2 | 7,829,932 / 22 | 7,829,932 / 22 |
| Ordinary epoch 3 | 11,090,114 / 31 | 10,732,786 / 30 |
| Valid-home transaction 4 | 7,700,938 / 22 | **7,700,970 / 22** |

The ordinary predictor entry-to-caller-return interval falls from 559,096 to
417,668 clocks: **25.295835%**. Its raw entry/return state matches the unchanged
instruction model. The ordinary publication saves 357,328 clocks and one field.
Valid-home recovery exceeds the inherited zero-clock-regression gate by 32
clocks. It remains exact and safe; the performance gate is unchanged and fails.
No all-eight-case or accepted optimization receipt was produced.

The two featured cases verify **198 fields / 11,354,112 RGB555 pixels**, with
consecutive coverage inside each case and zero mismatches, resource faults or
unsafe PPU operations.
Minimum complete-batch/map margins are **27,316/14,664 clocks**, above 10,000.
The remaining suite was stopped on this known gate failure. The task worker's
PID and image were verified before termination; its contained
descendants then stopped, job ActiveProcesses reached zero, and the normal
read-only shared byte-zero lease was released. The `early` expected-abort case
also completed with 80 exact fields, but is outside these two-case timing
totals. The interrupted `ready` case has no certificate or field result and
is excluded. The runtime's later private save is not treated as the final save
of either featured case.

Three earlier pilots are retained: the first used the wrong imported MCP
client, the second had malformed newly emitted Lua, and the third was rejected
by an inherited queue-owner guard outside the relocated helper range. Each
guest/job stopped and released its gate. The fresh fourth pilot passes those
checks. Failed logs were not filtered or recertified as passing.

After the strict recovery failure, two real redundancies were removed: an
unused initial scratch write and a repeated load whose value was still in A.
The resulting **175-byte prototype** is ROM
`436c735d908b0e6bfbb140a2a4bd87f08e83ad3940e6c0fc60c8385e9174b020`.
Ten model/adapter tests and a read-only static audit pass. It has **no native
measurement or acceptance**; its prepared fifth pilot was not launched after
runtime integration was prioritized. Neither candidate is selected by a
production build or promoted as a completed game capability.

The receipt is [byor-motu-capacity-scan.json](receipts/byor-motu-capacity-scan.json).
Per-case raw captures remain under `out/byor-motu-capacity-scan-pilot-v4/`;
reviews, lease proofs and attempt logs remain under
`out/byor-motu-capacity-scan-integration-v1/`. All 30 inherited tracked edits,
including the prompt-file deletion, remain preserved. No main-ROM source,
private artwork or PCM media was regenerated.
