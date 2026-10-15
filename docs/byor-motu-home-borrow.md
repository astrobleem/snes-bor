# Guarded backdrop-home borrowing

**BYOR_MOTU_BACKDROP_HOME_BORROW_PASS**

Eight final native fixtures verify **1,283 visible fields / 73,572,352 RGB555 pixels**, with **zero mismatches, resource faults or unsafe PPU operations**. **162 focused tests pass.**

The opt-in `--nonblank-home-borrow` backend preserves the accepted READY source safe-point and publishes both epoch 2 and the genuinely different epoch 3. It resolves the measured 41-pair deficit using previously invalid, invisible physical backdrop homes. No VRAM, artwork, palettes, compositor kernels or source-world services change.

Candidate: `out/byor-motu-home-borrow-success-v5/native/bor.sfc`.
SHA256: `061c574cb37a0d8dfabe731bb1fb8685610a091ec3b7d48fdb46ed9aabf38fda`.
Parent: `dd10d752bddb081e6b536cb0b0c75c9b904d9c44`.
Machine-readable certification: `docs/receipts/byor-motu-home-borrow.json`.

## Capacity before implementation

The retained blocked UP run was re-certified against its actual 64-KiB physical VRAM, both displayed maps, committed map, exact marked map, reference directory and native tail reservations. Its 95 exact actor tiles plus ten distinct restorations still require 105 reservations against 64 free tail pairs.

The inventory independently reproduces the completed restoration remaps in actual native allocation order. Before those remaps there are 32 eligible invalid homes and 20 valid homes. After the ten logical restoration identities are routed to their reserved tail destinations, there are **42 invalid and 20 valid eligible physical homes**. Restoration records read immutable ROM; their source-home identities do not lease the old physical home contents.

Complete sorted invalid candidates:

`297, 298, 299, 327, 328, 329, 356, 357, 358, 359, 360, 361, 387, 388, 389, 390, 391, 392, 393, 417, 418, 419, 420, 421, 422, 423, 512, 513, 514, 524, 525, 526, 529, 530, 544, 545, 550, 552, 574, 575, 576, 584`

Complete sorted valid candidates:

`204, 232, 233, 234, 264, 265, 266, 268, 269, 295, 296, 300, 325, 326, 330, 331, 355, 362, 528, 549`

All 596 homes have individual inventory rows in the receipt, including HIGH/LOW displayed references, committed count, planned pending references, physical validity flag, actual original-pair comparison, reservation status and exact CHR byte ranges. Every valid flag is checked against the immutable HIGH and LOW ROM data. The displayed map identities and full reference histogram agree. The queue is empty; the failed original transaction has no DMA. All existing restoration destinations are tails. **62 eligible homes exceed the required 41**, so the stop gate permits implementation.

The standard successful transaction uses the first 41 invalid candidates above, excluding 584. It takes **64 tail reservations + 41 borrowed homes = 105 total reservations**, then publishes a map with **639 referenced physical slots**. The first displayed map remains protected throughout preparation. The combined old referenced set and new reservations fit within the same 768 paired slots and unchanged 64-KiB layout.

## Allocation, journal and ownership

The option requires the conditional-capacity, source-safe-point, restoration-spill, six-pair batching and optimized component prerequisites. The existing tail scanner, conservative/exact retry, restoration record bound and source admission remain active. The new path is reached only after exact marking and the original restoration planning.

`BhPrepare` counts actor markers and remaining unreserved tails. When tails suffice, it returns to the existing allocator. Otherwise it computes the entire eligible home pool before actor composition or DMA. Candidates must have zero committed count, no reserved-directory bit, no committed-map occurrence and no pending physical-map requirement. A zero-count/committed-map inconsistency rejects. The single committed RAM map is the transaction-owned mirror of both paired physical maps; native observers independently check both actual VRAM maps before every home transfer.

The default scans invalid homes first, then valid homes, in ascending order. Eligibility comes from current maps and directory words. No home IDs, epochs, actor positions or benchmark outcomes are embedded in the ROM. The selected journal is complete before allocation; its cursor advances once per home reservation. The original tail scanner must exhaust before `BhTake` returns a home. The journal size is bounded at 64 entries; an insufficient pool or journal budget rejects before composition/DMA.

The new private BW-RAM lease is **`$42D700..$42D78F`, 144 bytes**, immediately above the old graphics lease and below physics at `$42D800`. It does not borrow the 20-byte READY latch, DP, 48 restoration records, six-pair queue, source actor state or returning-worker code.

| Address | Meaning |
|---|---|
| D700 | Journal entry count |
| D702 | Diagnostic preference (default 0 = invalid-first) |
| D704 | Borrow reservation cursor |
| D706 | Required overflow pairs |
| D708 | Diagnostic early-abort control |
| D70A | Pool budget, default 64 |
| D70C | Inactive / prepared / rolling back |
| D70E | Diagnostic valid-prefix quota, default 64 |
| D710–D78F | 64 two-byte home records |

A record contains the physical home ID, its original invalid flag (bit 15) and a conservative may-have-been-written flag (bit 14). The source build has no compiled pending-jump rows or symbol claimant in the lease. Both CPUs' physical writes to the journal are trapped; only the measured S-CPU helper code may write it. The remaining `$42D790..$42D7FF` is a byte-checked canary before physics. The inherited isolated configuration withdraws character conversion and holds the returning worker in reset. This lease is not certified for enabling those services or adding pending-jump storage.

Poppy and the candidate-specific auditor verify branch bytes, actual instruction sizes, code placement and whole-ROM equality outside declared edits. New helpers occupy `$39B300..$39B638` (825 bytes), clear of the existing `$39B000..$39B263` safe-point code and C000 compositor. The A000 transaction ends at A618. The original 119 movement instructions remain independently binary-checked; the 175-byte row and 289-byte fused kernels, source services, assets, palette, F43000 refcount ROM and occupancy authority remain unchanged. No substantial bank-zero code is added.

## Validity and rollback

Before queueing an actor tile into a borrowed home, `BhInvalidate` rechecks its zero reference count, records possible damage, and sets the directory's invalid bit while preserving its low count bits. The flag is set before either physical component can be written. Existing independent HIGH/LOW DMA fences and queue-empty checks remain mandatory before READY. Successful publication keeps the invalid bit while rebuilding actual map reference counts.

Abort first discards unsubmitted queue entries. Already-invalid homes may retain invisible unreferenced CHR residue with their original flags. Every originally valid, possibly damaged home is restored from authoritative HIGH and LOW ROM data through the existing scratch/queue DMA path. Rollback temporarily permits the final partial queue to drain even in the partial-queue fault fixture. Only after the flush returns and both component fences complete does it clear newly introduced invalid flags. Committed maps, counts, displayed epoch and successful visual key remain unchanged. The journal is released after commit or completed rollback.

The flag observer tracks prior directory high bytes explicitly. Mesen selects these callbacks by physical RAM range but reports CPU bus addresses; the observer normalizes the address before indexing that mirror. Lua observer errors fail certification. Early callback/capture trials are excluded; the certified native runs are serial to avoid Mesen's shared screenshot-directory race.

Diagnostic valid-first quota 1 deliberately borrows **valid home 204 plus 40 already-invalid homes**, with the same actual map/refcount eligibility rules. This exercises one new invalidation without altering actor state or physical ownership. The normal backend remains invalid-first.

After epoch 3 commits, a real controller release advances the same source owner to IDLE epoch 4. Its source picture needs immutable backdrop identity **204** at map cell (8,10). The old picture still references physical home 204 as actor CHR, so it cannot be overwritten in place. The existing restoration planner copies the original HIGH/LOW pair to **tail slot 634**, reroutes the pending background reference and publishes the exact IDLE picture. Home 204 remains physically invalid afterward (`$8000`, count zero); it is never falsely marked original. This later publication takes **35 fields / 12,575,698 clocks / 585.535219 ms**.

## Real source pictures and timing

The source actor remains `$414000`. Actual JOY1 UP executes at epoch-2 READY through retained controller/history/ground/frame/velocity/check_move/seal services: X **81 → 81**, Z **220 → 219.75**, canonical epoch **2 → 3**. Epoch 2 commits with its immutable original key; `SpRenderCurrent` then requests epoch 3 without another movement. Its picture differs by exactly **1,816 RGB555 pixels** and performs a full changing transaction, not a projection noop. The source snapshots match the original blocked run byte-for-byte.

| Standard invalid-first publication | Fields | Master clocks | ms |
|---|---:|---:|---:|
| Epoch 2, including real UP safe-point | 32 | 11,632,626 | 541.624983 |
| Epoch 3, including home admission | 94 | 33,833,446 | 1,575.314088 |

Epoch 3 composes 95 actor tiles, restores ten backdrop identities, uploads **105 pairs / 8,400 CHR bytes in 18 batches**, then transfers both 2-KiB maps in a separate fresh VBlank. It uses 212 DMA descriptors. Minimum complete-batch margin in the standard run is **33,950 master clocks**, exceeding the required 10,000. The minimum complete-batch margin across the suite is **33,948 clocks**. Map completion and exact margins for every publication appear in the machine receipt. The CPU preparation is deliberately slow; this is correctness, not a performance improvement.

`BhPrepare` is measured from entry through its return label. The standard overflow plan consumes **17,991,078 master clocks / 837.680 ms**, dominated by guarded map scans. Early rollback takes **357,814 elapsed clocks**, including **314,910 wait clocks**, **772 DMA clocks** and **42,132 CPU clocks** (1.961701 ms). READY rollback takes **233,182 elapsed clocks** with the same 42,132 CPU clocks; its shorter VBlank wait accounts for the elapsed difference. Invalidation, readiness and all other rollback/wait spans are recorded separately per transaction. Helper spans exclude caller JSR/final return epilogues; complete publication intervals include all work. The fault-true early-abort hook has no separate return-label span and remains included in transaction timing. No unmeasured component is claimed to cost zero.

## Certification and reproduction

The receipt aggregates successful invalid and valid borrowing, later immutable restoration, rollback after initial borrowed-home writes, READY rollback, partial queue, stale epoch, insufficient leased-pool budget, and the fresh RIGHT safe-point/LEFT/noop control. Every visible field is compared with independent RGB8 source composition projected to RGB555, decoded from full physical VRAM, and checked against ordered complete DMA replay. READY residency is reconstructed independently from actual native plans and reservations before map commit. Original maps/references remain intact on each rejected attempt. Both component fences precede every valid-home flag clear.

The insufficient-budget diagnostic exposes only 40 home leases against the measured need for 41: 64 tails + 40 leased homes is one short of 105. It rejects before any DMA without falsifying physical references. This is a deliberate transaction-budget fault, not a claim that the actual 62-home physical pool is insufficient.

The disabled option reproduces the accepted safe-point ROM `7cf213a9aaa467c7c1248dc0e40d35027f8dbd56a6ac3e9f81d373d216cc431b`. Disabling safe-point as well reproduces conditional ROM `9ccbb5310ceb73f97ba6bdcfddfeeedb98f0378c448c8c0e98f543581c6ddeea`. Retained conditional ordinary/rescue/fault/unit evidence re-certifies 518 fields / 29,704,192 pixels; those retained pixels are excluded from the new-run aggregate. All 29 inherited dirty tracked files, including the protected 17, have before/after byte fingerprints.

From the repository root:

```powershell
$env:PYTHONPATH='.;tools/bor_compile;tools/verify'
$env:MESEN_EXE='E:/gh/Mesen2-mcp-frameexact/bin/win-x64/Release/Mesen.exe'
python tools/verify/m4_home_borrow_capacity.py
python tools/verify/m4_opaque_component_native.py --output out/home-borrow-NEW --warm --occupancy out/astra-occupancy-assets-v1 --tile-fusion --direct-pair-dma --rect-map-diff --nonblank-slice --nonblank-batch-rescue --nonblank-restore-spill --early-capacity-admission --source-safepoint --nonblank-home-borrow
# For each diagnostic, build a fresh directory with the same flags plus --build-only, then run one case:
python tools/verify/m4_home_borrow_native.py --folder out/home-valid-NEW --policy 1 --valid-limit 1 --later-restore
python tools/verify/m4_home_borrow_native.py --folder out/home-early-NEW --policy 1 --valid-limit 1 --fault 1
python tools/verify/m4_home_borrow_native.py --folder out/home-ready-NEW --policy 1 --valid-limit 1 --mode 1
python tools/verify/m4_home_borrow_native.py --folder out/home-partial-NEW --policy 1 --valid-limit 1 --mode 2
python tools/verify/m4_home_borrow_native.py --folder out/home-stale-NEW --policy 1 --valid-limit 1 --mode 3
python tools/verify/m4_home_borrow_native.py --folder out/home-insufficient-NEW --limit 40
python tools/verify/m4_home_borrow_native.py --folder out/home-right-NEW --right-control
# Re-certify the retained final handoff runs and regenerate the combined receipt:
python tools/verify/m4_home_borrow_evidence.py --collect
python -m unittest test_m4_home_borrow test_m4_source_safepoint test_m4_conditional_capacity -q
```

Run native screenshot cases sequentially. Startup/tool timeouts retry only unfinished frame advances, preserving the exact total. Native artifacts include each source snapshot, source oracle, PNG, full VRAM field capture, DMA payload, completion fence, journal and validity event. No reset, stash, clean, unrelated media regeneration, PCM duplication or master merge is used.

No general scene/multi-actor capacity, 30 FPS, 200-Hz scheduling, SA-1 coexecution, authored audio, HUD, combat or MOTU Demo claim. Stop after this bounded borrowing and restoration experiment.
