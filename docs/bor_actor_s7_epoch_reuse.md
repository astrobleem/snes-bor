# S7 native release/reuse and final publication scope

Historical milestone: the shared-picture and allocation defects discovered
after this report are corrected in [publication guards](bor_actor_s7_publication_guards.md).
Use [the closure record](bor_actor_s7_closure.md) and the current machine report
for final artifacts and timings. The older measurements below remain retained.

This supplements the earlier bounded delivery, adding actual palette streaming
and a reusable native publication lifecycle. It does not promote engine, PAK or
strict-latency certificates.

## Reproduce

Use new output directories (the retained directories already exist):

```
python tools/verify/actor_s7_multi_publisher.py --output out/repro_palette_phase --case palette-phase --live
python tools/verify/actor_s7_multi_publisher.py --output out/repro_epoch_reuse --case epoch-reuse --live
```

Selected artifacts:

| Directory | ROM SHA256 |
|---|---|
| `out/s7_packet_palette_phase` | `ec03b7fd6ccb193803384b89d2d548f613256b1485dbb5d4f7c37fcdc10e2e7c` |
| `out/s7_epoch_selected` | `072a55c0cf8136d3deb097f891d599ea086aba1594d08e83145a0a009545124f` |

Each contains runnable `bor.sfc`, `bor.msu`, generated assembly, manifests,
`mesen.log`, raw PPU `publication-*.png`, and `multi-proof.json`.
MSU SHA256 remains
`ab80083ef34443b876387e30c4af662253820caf104cca38b33682170c4298ba`.
The selected epoch ROM is byte-identical to the initial uncached epoch proof.

## Native lifecycle

The explicit opt-in owner posts close/open requests at `$7FA8C0`. No simulation
state is reset or replayed. Source simulation continues while publication is
explicitly closed. This API is **not** used to delay an active source frame or
hide an overloaded transition.

1. Reopen while the epoch is live is rejected with D707, without releasing it.
2. Close waits for both queued OAM packets, then queues a complete hidden packet.
3. Only its actual completion sets the release cookie `$7FA8C2` and phase 3.
4. Reopen requires that cookie, phase 3, no pending buffers, and ready=0.
5. The existing entry loader reloads the same admitted immutable set through real
   DMA. Generation `$7FA8C4` advances only after all transfers complete.
6. Source publication resumes at the current source snapshot, not a manufactured
   pre-close state. Final teardown again retires all hardware references.

This is deterministic epoch-granularity reclamation of the pinned strategy, not
an arbitrary-model eviction cache or a seamless different-pool transition. The
separate accepted compact streamer retains its per-block displayed/queued leases.
The native lifecycle storage ends at `$7FA8C6`, below the audited `$7FB000` owner.

## Actual evidence

The selected run contains 16 verified 1,024-byte tile transfers (initial load and
reload), 112 atomic palette/OAM transactions, 108 pixel-checked pictures, all eight
Crab walk and all six Gold idle frames, and two safe closes. The trace verifier
reconstructs displayed/queued ownership from actual queue and hardware events:
zero VRAM overwrite while referenced, zero packet/palette-buffer overwrite, and
zero terminal source references. One intentional D707 remains latched as fault
evidence; there were no unexpected admission faults.

The same native OAM consumer also completed **26 ordinary compatibility OAM
transfers** with every transferred byte matching the production source buffer.
The old exact 100->95 / compatibility 100->96 controls and accepted single/sync/
staggered ROM hashes remain preserved. Default shipped files were not rebuilt or
modified by this opt-in work.

The independent-phase/remap run uses 7,680 pinned bytes, with a peak physically
displayed+queued union of 6,144 bytes. It checks ten pictures and twelve native
palette/OAM transactions, including selector 4. Its next-field-from-preparation
miss count is zero. Strict next-field-from-source-snapshot latency remains
NOT_CERTIFIED, distinctly reported.

The longer epoch run has 30 next-field-from-preparation misses. These are kept
as **CPU/publication timing failures**, not converted to readiness passes. Its
purpose proves correct release/reload and resumed pixels, not real-time capacity.
The original six-actor and attack-burst failures also remain failed.

## Measured optimization retained as experiment

`--palette-staging-cache` keys each private palette image by immutable ROM address,
invalidates on reset and absent-row identity, and publishes its key only after
the copy completes. It never substitutes for a hardware completion fence.
The actual A/B (`out/s7_epoch_reuse_01` vs `_02`) preserved all pixels, frames,
calling conventions and leases. Median staging cost fell 7,118 -> 762 clocks,
but next-field misses were 30 -> 32. Therefore it is **not selected by default**;
no net deadline benefit is claimed. Its audited key cells are `$7FA8D0..A8D7`.

## Acceptance boundary

The publisher supports compiler-generated source frames, coherent source-world
snapshots, native compositor output, real tile/CGRAM/OAM completion, legal 8-KiB
ownership, simultaneous instances, independent phases, distinct models, live
alternate maps, and deterministic release/reuse. Content-addressed resources
are not duplicated merely for instance or map identity. Resource diagnostics
distinguish mandatory live blocks, optional future data, palette transaction
lifetimes and conservative emitted-layout bounds.

Admitted pinned sets still have finite compiler limits: 8,192 bytes, sixteen
frame/map keys, and two simultaneous palette-bearing instances. An oversized
future pool is a **policy admission block**, not a proven minimum simultaneous
SNES requirement. The existing compact streamer is a separate admitted strategy;
there is no hidden fallback or automatic migration of production actors.

S7 publication capabilities are complete under these explicit bounded contracts.
Strict real-time SOURCE_EXACT execution, a complete source engine and whole-PAK
certification are **not** complete. Remaining CPU, NUMERIC, AI (including runoff
13), MEDIA, DIALECT, RESOURCE and ENVIRONMENT limits are enumerated in the delivery
report. Time, SEWER, foreign dialects and unrestricted physics were not implemented.
