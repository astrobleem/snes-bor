# MOTU publication fusion with guarded cancellation copy

Result: `BYOR_MOTU_ABORT_COPY_PASS`. The combined change passes **505 focused
tests**, all eight standard native cases, and an independently sealed owner-zero
branch probe. The strict timing gate compares every recorded committed and
aborted transaction with accepted reference-rebuild ROM `41c505ad…b9941`.

The original `NbMapsComplete` to `NbVisible` epoch-3 interval falls from
**453,628 to 340,216 SNES master clocks**,
**25.001102%**. This exceeds the unchanged 20% post-map
requirement. It describes that interval, rather than whole-frame throughput.
Ordinary epoch 2 improves from **7,943,412 to
7,829,932 clocks**, with **22 fields**;
epoch 3 improves from **11,203,624 to
11,090,114**, with **31 fields**.

| Case / transaction | Outcome | REF clocks | Combined clocks | REF / combined fields |
|---|---|---:|---:|---:|
| success / 2 | commit | 7,943,412 | 7,829,932 | 22 / 22 |
| success / 3 | commit | 11,203,624 | 11,090,114 | 31 / 31 |
| valid / 2 | commit | 7,943,412 | 7,829,932 | 22 / 22 |
| valid / 3 | commit | 11,203,622 | 11,090,118 | 31 / 31 |
| valid / 4 | commit | 7,814,280 | 7,700,938 | 22 / 22 |
| early / 2 | commit | 7,943,412 | 7,829,932 | 22 / 22 |
| early / 3 | abort | 9,055,908 | 9,047,862 | 25 / 25 |
| ready / 2 | commit | 7,943,412 | 7,829,932 | 22 / 22 |
| ready / 3 | abort | 10,842,810 | 10,834,672 | 30 / 30 |
| partial / 2 | commit | 7,943,412 | 7,829,932 | 22 / 22 |
| partial / 3 | abort | 11,914,888 | 11,906,742 | 33 / 33 |
| stale / 2 | commit | 7,943,412 | 7,829,932 | 22 / 22 |
| stale / 3 | abort | 10,842,772 | 10,834,742 | 30 / 30 |
| insufficient / 2 | commit | 7,943,412 | 7,829,932 | 22 / 22 |
| insufficient / 3 | abort | 5,133,244 | 5,125,222 | 14 / 14 |

The right-control certificate uses its own transaction-cost schema. Its first
total remains 6,533,914 clocks; transaction 2 improves from 7,943,358 to
7,829,962. Source movement remains 398,390 clocks and the transition remains
22 fields. These totals are checked separately against accepted RIGHT.

Every clock, field and transition comparison passes without a tolerance or
padding. All **666 consecutive standard fields / 38,191,104 exact RGB555
pixels** match, with zero pixel mismatches, resource faults or unsafe PPU
operations. The minimum complete-batch margin is **27,314 clocks**;
the map margin is **14,694**, above the unchanged **10,000** floor.
Allocation/reference snapshots, physically referenced tiles and inherited
canary/ownership checks remain exact. Workload and fallback capacities are fixed.

The 825-byte publication helper at `$39AB00..$39AE38` copies the pending map
into the committed map while rebuilding references under exclusive owner 4.
It preserves the final CPU state and per-resource write order. That helper
alone failed the all-case timing gate: its five small abort regressions remain
recorded in [the negative fusion receipt](receipts/byor-motu-commit-rebuild-fuse.json).
That negative record covers the standalone fusion root. Component pass receipts
inside the new combined root certify this combined ROM; acceptance requires its
final `abort-copy-receipt.json`.
The combined version also uses a 256-byte guarded cancellation helper at
`$39AE40..$39AF3F`. Owners 1 through 4 use a bank-local word copy; owner zero
and values at least 5 restore status and enter the unchanged original bytewise
MVN setup. Both helpers are required for this acceptance result.

Only two four-byte dispatches and the two checked zero-gap helper ranges
change relative to accepted REF. All original labels remain fixed; independent
literal opcodes and 321 branch sites match Poppy. The disabled build is exactly
the accepted REF ROM. No RAM region, VRAM allocation, DMA routine, queue limit,
asset or capacity is added. The changed global read/write interleaving is
validated under the fixture's exclusive owner, with no production concurrency
claim. SA-1 remains reset in this fixture.

Native monitors cover both CPUs from cancellation entry through the original
owner-clear store. Each of the **13 standard cancellation copies** checks
2,048 source reads, 2,048 destination writes, exact byte bus order, frozen source
and references, complete continuation registers/status/stack, and both zero-owner
store bytes. The separate probe changes the owner at the original dispatch
from a fast-eligible state to zero, then observes the legacy MVN path in the
identical ROM. Its **80 fields / 4,587,520 pixels** are additional branch evidence
and are excluded from the eight-case timing comparison. This injected probe
does **not** exercise the natural cold-preflight failure chain.

Both independent preflight review and final raw-evidence review pass. The first
same-process branch probe reused an import-cached executable path and wrote
the standard private save; its raw evidence and rejection receipt are retained.
That save is not used as the standard final-state oracle. The accepted probe
runs in a fresh Python process, records the actual Windows process image,
binds whole private-save before/after files, and leaves the standard save
unchanged. A Windows process job holds the worker and descendants; timeout
tests prove they exit before the shared lease is released. The fresh probe
also reproduces the entire disputed 262,144-byte save exactly, identifying
the first probe output behind the 202-byte difference from accepted RIGHT. All
120 preservation checks passed before the explicit publication-only
`.gitattributes` append. Inherited edits, the absent prompt, private assets,
accepted captures and rejected experiment bytes remain preserved. Each private
runtime's 63 binaries match the original executable directory; global settings
are unchanged, with exactly six private output-path settings redirected.
The original SRAM seed is retained. The read-only shared byte lease covered
serial capture and the probe, then released before offline collection. The
historical gate permission error was ordinary contention; no bypass was used.

The first incomplete fusion pilot and all rejected preload, READY-unroll,
borrow-invalidation and standalone fusion experiments remain retained. The
candidate-only host runner bounds waits and resumes exact remaining frame
counts with continuity and no overshoot. Completion must be paused; each RPC
response is flushed before optional diagnostics. ROM clocks, exact frames and
pixel checks are unchanged.

The [canonical receipt](receipts/byor-motu-abort-copy.json) pins all ten combined
implementation/test sources, tests, reviews, standard capture seals and separate
probe result. The standard raw root is `out/byor-motu-abort-copy-v1`; probe data
is `out/byor-motu-abort-copy-cold-probe-v2`; lease, validation, source review and
orchestration records are under `out/byor-motu-abort-copy-integration-v1`.
The candidate ROM SHA256 is `2ae50b27ac69986a07925e37fd99f5f5506044dec6195662ea54524a8ac4166f`.

This result covers the isolated MOTU fixture. It does not establish a complete
game, 30 FPS, audio, combat, HUD or production concurrency.
