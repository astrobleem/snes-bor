# S7 native entry-frame publisher: bounded running artifact

This is a real native publisher, not an animation/deadline or whole-model
certificate. The old six-actor CPU failures remain failed and unchanged.

## Reproduce

From the repository root, with the existing Poppy and Mesen toolchains:

    python tools/verify/actor_s7_native_publisher.py --output out/my_source_entry --live

The output directory must not already exist. The command creates a runnable
`bor.sfc`, queue-fixture `bor.msu`, PCM links, generated assembly/symbols,
compiler asset manifest, hardware dumps, screenshot and event trace.

Two admitted source instances sharing the same resident frame:

    python tools/verify/actor_s7_native_publisher.py --output out/my_source_entry_two --second-actor --live

The second-player option supplies an initial attack action through the existing
source control interface, not a frame index or OAM injection.

## Native ownership

- Opt-in world builder compiles the existing resident source runtime. No new
  binary instruction hooks were added for publication: its existing render
  seam resolves to the generated compositor, which reuses the production
  depth-sort/OAM code and calls the native source consumer for exact slots.
- At the pre-catch-up boundary it captures live source role/frame, existence,
  position/direction/base, model/map owners, camera and depth ordering.
  It does not export a full execution context to render it.
- Snapshot/control storage is `$7F8C00..8CFF`, between the tile-cache tables
  ending `$7F8BFE` and tile staging beginning `$7F9000`; outside cleared OAM
  and the resident source/legacy behavior contexts. Six32-byte records start
  at `$7F8C20`. Current implementation is S-CPU-owned; NMI does not mutate it.
- Entry residency uses only VRAM words `$4000..4FFF`. Eight1KiB queue transfers
  initialize that physical image; one32-byte transfer initializes OBJ palette6
  (CGRAM bytes448..479). This bounded build starts its source clock only after
  these entry transfers complete. It does not lengthen source frame durations.
- Each request records the actual queue slot. The loader advances only after
  the slot's active bit is cleared by the real post-DMA consumer. Queued data
  alone is not ready. Existing byte cap, DMA channel and NMI ownership remain.
- Exact slots use source pieces, not `Character_RenderFrame`. Compatibility
  slots retain the accepted function. Unadmitted roles/frames/maps are hidden
  in this explicitly entry-only fixture; there is no accepted-frame fallback.
  Such absence is NOT source-certified rendering.

The compiler uses the optimized lossless packer's nontransparent coverage and
maps it into legal SMALL footprints. It currently subdivides LARGE candidates;
the LARGE descriptor/oracle capability is not claimed as a native consumer.
The admitted scene is fully onscreen, base0, map0. Partial-edge clipping and
other environment/resource domains are not certified by this artifact.

## Actual proof

Retained single-instance output: `out/s7_native_entry_05`.

- Source Kula attack1 frame0, compiler-selected role0, eleven SMALL pieces.
- All8192 uploaded tile-image bytes match the compiled physical image.
- All32 palette bytes match the declared `SNES_RGB555_TRUNCATE` target encoding.
- Hardware low OAM matches all11 source pieces; inspected high OAM is SMALL.
- The screenshot matches all1,835 nontransparent source pixels after the
  declared target-color conversion (5-bit replication for screenshot RGB).
- No expected OAM, frame, or rendered image is injected into the emulator.

One recorded chronology, in master clocks:

| Event | Clock | Physical field / snapshot |
|---|---:|---|
| Palette DMA completed | 104659864 | field293 |
| Native readiness fence passes | 104713694 | entry resources complete |
| Coherent frame0 capture | 105780272 | field296, completed source tick3 |
| Native piece emitter enters | 106021356 | snapshot3 |
| Low OAM DMA completed | 106446818 | field298, snapshot3 |
| High OAM DMA completed | 106448024 | field298, snapshot3 |

The following raster is the screenshot. These are measured preparation and
consumption events, not a latency PASS; the snapshot remains the pre-catch-up
image even though simulation has advanced by the time hardware consumes it.

ROM SHA256:
`b745ab6302ca9b47a6303cd4e06c0a7c92b4733594b6bc64a37f6bcf21b89cce`

MSU SHA256:
`d26337daabf7f9f07387caa9cb392e0304d9978ca752a179038150261ed163ba`

Two-instance output: `out/s7_native_entry_two_01`: slots0/1,22 hardware pieces,
both visible. This is shared-model multi-slot proof, not two different models.
The automated pixel count currently covers the first actor; both OAM sets match.

Accepted-compat control: `out/actor_s6_production_world_z7y1d8xt`, victim100→96,
mode5, no source ticks/errors. Shipped ROM/MSU were not rewritten.

## Remaining implementation

Update: the six-frame native transport now has a bounded live proof in
`bor_actor_s7_native_stream.md`. The paragraph below records the entry-commit
boundary, not the current absence of a native animation publisher.

Frame1..5 transport, transactional tile replacement, per-publication completion
identity, full six-frame visual timing, and a different-model publication case
remain unfinished. The current entry loader uploads an8KiB image including
padding; this is not an optimized transition streamer or a transfer budget.

Measured optimized adjacent working sets for Kula frames0..5 are
11,27,30,28,21,28 SMALL blocks (256bytes each, counting current/next union).
They fit32 blocks individually; that is placement evidence, NOT a multi-field
deadline/fence proof. New-block bytes for transitions are
2816,4096,3584,3584,1536,3840. Continue with live transition transport using the
same snapshot/native consumer, without returning to the six-actor CPU gate.
