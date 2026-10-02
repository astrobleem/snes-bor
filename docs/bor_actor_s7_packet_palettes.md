# Native palette replacement, not merely preloaded remap selection

Reproduce in a new output directory:

```
python tools/verify/actor_s7_multi_publisher.py --output out/s7_packet_palette_phase --case palette-phase --live
```

Artifact `out/s7_packet_palette_phase/bor.sfc` SHA256:
`ec03b7fd6ccb193803384b89d2d548f613256b1485dbb5d4f7c37fcdc10e2e7c`.
MSU SHA256: `ab80083ef34443b876387e30c4af662253820caf104cca38b33682170c4298ba`.

The explicit source-animation probe contains Crab walk frames 0..2 and Angel
pain frames 0..1, through source tick 36 (requested observation horizon 34).
Both animation states come from the existing source-world scheduler. Map-owner
test events select 0 -> 1 -> 4 -> 0. They are publication API inputs, not a claim
that Angel's source AI changes its own remap. No AI/numeric certification follows.

Four immutable palette identities now use two physical CGRAM slots. Tiles
remain shared by encoded identity and map changes do not duplicate them. The
admitted pinned tile pool is 7,680 bytes of the legal 8,192-byte window.

## Transaction and ownership

Each of the two existing immutable OAM packets owns a corresponding 64-byte
palette image at `$7FA840..A87F` or `$7FA880..A8BF`. These are after the second
packet/control allocation and before FP Slot2Tile `$7FB000`. A capture row's
word +28 identifies ROM palette bytes; +26 identifies the physical palette slot.
Absent instances explicitly contribute zero bytes, never an uninitialized ROM
pointer. The normal producer cannot rewrite either image until its OAM queue
request completes.

The opt-in NMI consumer recognizes the owned packet source and **608-byte**
transaction length. It DMA-transfers 64 CGRAM bytes followed by 544 OAM bytes in
one invocation; the existing queue clears ACTIVE only after both. There is no
second independently admitted request, no palette/OAM ordering race, and no
visible field containing the new palette with old OAM. All 608 bytes are charged
to the unchanged exclusive 2,816-byte admission cap. Ordinary OAM requests retain
the original operation. The production ROM/default compatibility path is untouched.

The native generator preserves D, DBR, X, Y, SP and A16/I16 at palette preparation
boundaries. Hardware observations verified every boundary, not only host code.
Preparation cost was 7,118 master clocks with two active rows; empty startup cost
4,498. These are measured additions, not an inferred streaming budget.

## Evidence and limits

`multi-proof.json`, `mesen.log`, `teardown.json`, and `publication-*.png` retain
snapshot, queue, actual CGRAM completion, OAM consumption and raw PPU pixels.
Twelve CGRAM/OAM transactions completed; all palette comparisons and both actors'
pixel/OAM comparisons passed, no live-buffer writes, no admission faults, and no
preparation-to-next-field misses in this bounded run. Native completion occurred
in VBlank (scanlines 226 or 232). Source-snapshot-next-field latency remains
**NOT_CERTIFIED**; the earlier CPU deadline failures are not erased.

The first post-`$420B` emulator exec hook can precede the pending DMA stall.
The completion hook is after the following instruction boundary; the OAM
completion fence is additionally checked against actual hardware state.

Rejected/diagnostic artifacts remain: `_01` had an incorrect register-save order
and unadmitted idle frames; `_02` needed a 9,984-byte pinned pool (not a simultaneous
hardware lower bound); `_03`'s actor overlapped opaque HUD pixels; `_05` observed
before the DMA stall; `_06` exposed uninitialized absent-row palette bytes, now
zeroed. The final layout places Angel below the HUD and declares that arrangement.

This is a coherent working palette capability, not by itself S7-wide closure.
Per-epoch pinned graphics release and other publication strategies retain their
existing explicit bounds; no general arbitrary-model dynamic cache is claimed.
