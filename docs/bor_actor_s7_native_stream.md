# S7 bounded native source-frame transport

This is a running opt-in source publisher. It is NOT six-actor real-time,
strict-latency, whole-model, arbitrary-animation, or arbitrary-PAK certification.
The previous CPU/deadline failures remain failed. ACCEPTED_COMPAT and shipped
artifacts are unchanged.

## Reproduce and evidence

From the canonical checkout with its existing PAK, production artifacts,
Poppy and Mesen toolchains, using a new output directory:

    python tools/verify/actor_s7_stream_publisher.py --output out/my_source_stream --live

Retained passing artifact: `out/s7_native_stream_13`.

- ROM: `bor.sfc`, SHA256
  `2736cfead18747c3b8e7ff8760166ca9bf87d25c21d09624fd033cbd4502aef1`.
- MSU: `bor.msu`, SHA256
  `ab80083ef34443b876387e30c4af662253820caf104cca38b33682170c4298ba`.
- Actual emulator screenshots: `source-frame0.png` through `source-frame5.png`.
- Independently captured PPU rasters: `verified-frame0.png` through
  `verified-frame5.png`; raw `raster-*.ppm`, OAM and timestamp sidecars retained.
- `stream-publication.json`: snapshot, native emission, post-hardware-DMA,
  transfer-byte/visible-lease checks, and pixel results.
- `world.pasm`, `world.sym`, `publisher-frame.json`, payloads and `link.json`
  preserve the generated code/data and final ROM/MSU identity.

All six source frames match: 1,835 / 2,188 / 2,342 / 2,294 / 2,360 / 2,334
nontransparent target pixels, 13,353 total. No expected OAM/frame state or
reference screenshot is injected. The target adaptation is explicitly
SNES_RGB555_TRUNCATE, with 5-bit replication for screenshot comparison.

MCP runs Mesen at maximum speed. The observer explicitly disables emulator
raster skipping, not source simulation updates. Lua file I/O is unavailable;
the observer logs actual getScreenBuffer pixels read-only. Mesen stores the
224-line picture at row7 in its239-line buffer; that documented border is
removed, without changing actor pixels. GUI screenshot sampling and raw PPU
raster results are recorded separately.

## Snapshot and publication contract

The same production slots, source scheduler and world execute. Capture occurs
before the catch-up pass it precedes. Each immutable32-byte snapshot holds its
completed source tick, role/frame, source coordinates/direction/base, model/map,
camera and source piece range, outside the OAM memory cleared by NMI.
Depth ordering is captured at that same boundary. Exact actors use this native
consumer instead of accepted frame selection. Other required services remain.

This implements sampled render-before-catch-up publication; it does not demand
a separate display for every intermediate simulation callback. Source descriptor
timing is unchanged. No frame is held or lengthened to cover transport misses.
Measured capture-to-consumption latency is evidence, not newly granted slack.

One retained chronology (master clocks; first capture/emitter/OAM completion):

| Frame | Snapshot tick | Capture | Emit | High OAM completed | Physical field |
|---|---:|---:|---:|---:|---:|
| 0 | 3 | 104354556 | 104460778 | 104661238 | 293 |
| 1 | 9 | 105073564 | 105206738 | 105376152 | 295 |
| 2 | 19 | 106147568 | 106287360 | 106448226 | 298 |
| 3 | 26 | 106880414 | 106997974 | 107162950 | 300 |
| 4 | 33 | 107595176 | 107699888 | 107877688 | 302 |
| 5 | 39 | 108309854 | 108446926 | 108592442 | 304 |

The physical raster following these transfers supplies the pixel proof.
Absolute startup phase may vary with the existing boot/input harness; these
measurements do not replace the original-epoch CPU benchmarks.

## Transport ownership

- Only OBJ VRAM words `$4000..4FFF`: two4KiB buffers inside the legal8KiB
  region, not two8KiB regions. Frame piece counts11/16/14/15/13/15 fit each
  buffer. No scaling or nontransparent crop. LARGE packer candidates are
  losslessly subdivided into supported SMALL16x32 pieces.
- Frames0/1 plus palette6 are resident before source execution begins.
  Later frames2..5 use eight2048-byte ROM-to-VRAM requests total. Payloads
  are immutable bank33 data, not reused WRAM staging.
- The request owns its returned queue slot. Resident metadata advances only
  after the production post-DMA consumer clears ACTIVE. Host readiness is
  never substituted for that completion.
- At the actual game OAM tail, a needed final half precedes dependent OAM;
  prefetch into the retiring buffer follows new low/high OAM. An already queued
  final half is not submitted again. Existing NMI/PPU/channel7 ownership remains.
- In this live trace, all16,384 streamed bytes match compiled ROM bytes at
  actual completion. Every transfer also verifies no visible palette6 source
  OAM references the destination buffer. No overwrite violations occurred.
- Maximum observed post-entry DMA bytes in one field:2,133 (2,048 tiles plus
  85 OAM). Existing exclusive2,816 cap is unchanged. The683-byte arithmetic
  difference is NOT a measured CPU/VBlank/other-actor transfer allowance.
- Native diagnostics: D701 final-half admission failure; D702 incompatible
  simultaneous frame cohort; D703 unavailable current-frame resources.
  Miss counters and faults remain visible; the live command fails if the
  requested full pixel/transfer proof does not pass.

The source-generated bank0 OAM-tail seam replaces the original call. Its5-byte
gate occupies audited zero padding `$FFA8..FFAC`, between NMI and IRQ stubs.
The linker checks old call bytes and gate ownership before copying assembler
output. Publisher code resides in bank31; compiled assets in32/33. Existing
resident/direct-dispatch, conditional BG-validity and unrolled fetch code are
reproduced by the build. Fixed-stride addressing remains off.

## Multi-actor and remaining limits

Two source instances sharing frame0 already passed22-piece hardware OAM and
visible rendering in `out/s7_native_entry_two_01` (entry publisher commit).
This is a shared-model test, not distinct-model residency support.

The next streaming workload was actually run from normal2P setup and queue:

    python tools/verify/actor_s7_stream_publisher.py --output out/my_two_source_stream --second-actor --live

It is NOT admitted as a complete-animation PASS. Retained investigation
`out/s7_native_stream_two_02` rendered frames0..3 but counted three readiness
misses. First miss: snapshot tick26/frame3 at clock108552978, before its first
half completed at108610990; its second half completed109322200. Frames4/5 then
lacked preparation. The four actual transfers were byte-correct and did not
overwrite visible tiles. A duplicate-pending-half false fault was corrected;
the remaining misses are not hidden or called green.

- CPU: old six-actor latency failures are unchanged; this is not a fresh
  six-actor integrated performance result. No transfer margin is certified.
- DMA/scheduling: shared-frame2P workload misses the current prefetch schedule.
  Low/high OAM queue admission under arbitrary contention is not certified.
- VRAM: this link owns both4KiB buffers for one frame cohort. Distinct models,
  independently changing frames and other maps need separately admitted leases.
- Semantics: other roles/maps, partial-edge clipping, unrestricted numeric
  movement, runoff driver13, Time and foreign dialects remain outside this proof.
  Unlinked source actors do not silently fall back to accepted graphics.
- Palette: actual map0 palette completion is proven; alternate/>=4 streaming
  palette transactions remain unimplemented in this bounded publisher.

## Focused checks

Nine source-world-link tests and nine frame-publication tests pass. Changed
Python compilation and diff hygiene pass; width audit reports0 new findings,
and the generated candidate assembles without warnings. Post-change exact
control `out/actor_s6_production_world_hyjldbpa` retains100->95; compatibility
control `out/actor_s6_production_world_526sed80` retains100->96, no source ticks.
No campaign, numerical archaeology or all-PAK sweep was performed.
