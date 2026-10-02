# S7: bounded two-instance native source streaming

The original two-instance action workload now publishes all six source frames
for both actors, with zero native readiness misses. This is a bounded publisher
implementation, **not** a strict-latency, six-actor, whole-model or S7-wide
certificate. The older CPU/cutoff failures remain failed. Production
ACCEPTED_COMPAT and its ROM/MSU are unchanged.

## Reproduction and retained artifacts

From `E:\gh\snes-bor`, with the existing PAK and local Poppy/Mesen toolchain,
choose an unused output directory:

```powershell
python tools/verify/actor_s7_stream_publisher.py --output out/my_two_instances --second-actor --instance-leases --live
```

Retained working build: `out/s7_instances_delivery/bor.sfc` and `bor.msu`.

- ROM SHA256: `67953df872febe68731b8e0d363ee2bdff4b21c8ee2598213ed13427c1285430`
- MSU SHA256: `ab80083ef34443b876387e30c4af662253820caf104cca38b33682170c4298ba`
- `stream-publication.json`: actual captures, hardware DMA completions,
  immutable packet identities, both-actor OAM/pixel proofs and diagnostics.
- `packet-0-0_1-0.png` through `packet-0-5_1-5.png`: actual emulator rasters.
- `raster-*.ppm/.oam/.bg.bin/.json`: raw screen, hardware OAM, foreground
  tile/palette data and timestamps. Screenshots are not reference drawings.
- `publisher-frame.json`, `publisher-assets.bin`, `world.pasm/.sym`, `link.json`:
  compiler-generated resources, code and exact artifact provenance.

`out/s7_instances_reproduce` independently reproduces the identical ROM from
the final source, including non-emitting width assertions. It also includes
the compiler's retained-working-set diagnostics under `resources`.

The accepted single command is preserved:

```powershell
python tools/verify/actor_s7_stream_publisher.py --output out/my_single_control --live
```

Run once as `out/s7_instances_single_control`: all six raw PPU pixel checks,
eight original 2-KiB transfers, zero misses/overwrites. ROM remains exactly
`2736cfead18747c3b8e7ff8760166ca9bf87d25c21d09624fd033cbd4502aef1`.
Its GUI screenshot sample lagged frame5; the separately timestamped raw PPU
raster matched all 2,334 pixels. This distinction remains in the evidence.

## The original three misses

Retained original trace: `out/s7_native_stream_two_02/stream-publication.json`.
Both source instances shared the requested frame; the missing dependency was
shared graphics, not a missing second actor state or a palette change.

| Snapshot / frame | Capture clock / field | Associated OAM-tail opportunity | First unavailable dependency |
|---|---|---|---|
| tick26 / 3 | 108552978 / 303 | 108823984 / 304, before next NMI305 | Frame3 first half unfinished at capture; completed108610990, but early rejection prevented timely second-half admission |
| tick33 / 4 | 109299048 / 305 | 109615914 / 306, before NMI307 | Frame4 payload not prepared; frame3's second half only completed109322200 / 306 |
| tick39 / 5 | 109723726 / 307 | 109944750 / 307, before NMI308 | Frame5 preparation had not followed the stalled frame4 handoff |

The old readiness decision ran at capture, before catch-up and required
services, even though completion could occur before its OAM tail. Moving the
decision alone was insufficient. `out/s7_instances_01` exposed a real mutable
OAM staging/NMI-clear race and four visible-tile overwrite references. That
failed artifact is retained. The fix is a coherent packet and resource leases,
not a CPU-rate change or a hidden extra field of slack.

## Per-instance state versus immutable graphics

Each real production slot retains its own source context, action/frame clock,
existence, position, facing, base altitude and selected map. Each independently
captured 32-byte render row carries source tick, role/frame, model/map, camera,
placement and piece range. Capture still precedes the catch-up it represents.
No expected frame or OAM is injected. The ordinary source action initializer
is unchanged for the original synchronous two-instance workload.

The compiler keys shared resources by encoded block bytes, not actor slot.
`source_frame_transport.py` places lossless 16x32 footprints in the same legal
32-slot / 8-KiB OBJ region: VRAM **words `$4000..4FFF`**, bytes `$8000..9FFF`.
There is no second overlapping window. SMALL subdivision retains every source
pixel and source offset. Future-use grouping only reduces transfer fragmentation.
Palette identity is separate and explicit; this link admits map0/palette6 only.
Another model or map does not implicitly inherit this resource pool.

Frames0/1 and the 32-byte palette enter through the existing actual DMA fences
before the source-clock epoch. Later frames use immutable bank33 ROM payloads:

| Destination frame | New tile bytes | Native jobs |
|---|---:|---:|
| 2 | 3584 | 8 |
| 3 | 3584 | 7 |
| 4 | 1536 | 4 |
| 5 | 3840 | 15 |
| Total | 12544 | 34 |

Two instances do not duplicate these transfers. Adjacent retained frame sets
0/1, 1/2, 2/3, 3/4 and 4/5 require respectively 6912, 7680, 7168, 5376 and
7168 encoded bytes. These are requirements of this lossless block encoding,
not proven minimum hardware requirements under every possible packer.

## Packet, lease and completion ownership

- Main still constructs OAM through the production compositor and depth path.
  Exact actors replace their accepted frame selection; shared services remain.
- An immutable **544-byte complete OAM packet** at `$7F8D00..8F1F` owns the
  hardware submission. It survives NMI's normal mutable-shadow clear. Main
  explicitly clears staging before the next construction; it does not set the
  legacy OAM-upload flag for this separate packet.
- `$7F8F20..8F3F` holds packet ownership, consumed/pending minimum frame,
  source snapshot tick and packet sequence. `$7F8F40..8FFF` is at most96 job
  status words (34 used). Both remain below BG staging `$7F9000` and beyond
  snapshot `$7F8C00..8CFF`. Queue arena `$7F9200` is untouched.
- Job state is NEW, QUEUED(returned slot), or COMPLETED. Actual queue ACTIVE
  clearing after hardware DMA is the fence. Unique immutable source addresses
  also distinguish completed/reused queue slots. Host placement never claims
  hardware readiness.
- Before OAM submission, overwrite eligibility uses the last **consumed**
  packet's minimum retained frame. After submission, eligible retirement work
  follows the complete OAM packet in the real FIFO. Both instances' references
  participate; advancing/disappearing one actor cannot retire its partner's
  displayed or queued resources.
- Required tile jobs may precede dependent OAM in the same NMI FIFO; the actual
  tile transfer must finish before that OAM transfer. This is not a host-ready
  substitute. The observer checks tile bytes and displayed OAM footprints at
  each hardware completion, then the full544 OAM bytes and actual CGRAM at
  packet consumption. All34 jobs and all13 consumed packets pass.
- The existing exclusive2816-byte admission and8 slots remain unchanged.
  Reserve544 bytes before packet submission; do not reserve it a second time
  after it is already charged to the queue. No transfer margin is certified.
- Immutable jobs resolve into4548 bytes of bank34 code. That previously empty
  bank is checked by the linker. ROM container size is unchanged. D/DBR are
  not changed by the new transport; explicit A16/X16 boundaries and the existing
  DMA wrapper contract apply. Tail PHP/PLP preserves the caller's width flags.

This is a bounded forward, non-looping linked animation plan, not a new general
cache. Restart, other roles/models/maps, arbitrary phase sets and unrelated
writers to the same allocation require their own admission/invalidation proof.

## Actual two-instance consumption

One retained run below. Preparation is packet-submission entry; consumption is
the real post-OAM-DMA boundary. Both rows belong to the same captured source
tick. The subsequent raster supplies both-actor pixels and low/high OAM proof.

| Frames P1/P2 | Snapshot tick | Prepare clock | Hardware consumed clock | Physical field |
|---|---:|---:|---:|---:|
| 0/0 | 3 | 106730746 | 106808218 | 299 |
| 1/1 | 9 | 107521088 | 107880310 | 302 |
| 2/2 | 19 | 108912030 | 108952392 | 305 |
| 3/3 | 29 | 109967222 | 110024488 | 308 |
| 4/4 | 33 | 110493056 | 110739256 | 310 |
| 5/5 | 39 | 110942366 | 111096600 | 311 |

26,610 visible source pixels match across both actors/all six frames. Ordinary
OBJ overlap accounts for84 covered P2 pixels; actual high-priority BG3 font
pixels account for12 more. The verifier decodes hardware BG3 tiles/CGRAM,
not a guessed screen mask. Source color adaptation remains explicitly
SNES_RGB555_TRUNCATE. Zero tile-byte mismatches, visible overwrite violations,
packet-byte mismatches, palette mismatches, readiness misses or native faults.

Catch-up/service partitions can change with execution cost. The new trace
captures frame3 at tick29, not the old tick26 opportunity. **Zero native
readiness misses does not recertify the old absolute cutoffs.** No source
delays, epoch or service rules were changed, and strict latency remains false.

## Independent staggered case and retained failure

```powershell
python tools/verify/actor_s7_stream_publisher.py --output out/my_stagger --second-actor --instance-leases --stagger-ticks 1 --live
```

This deliberately remains a failing full-run command; retain its diagnostic
artifact. P2 receives its one initial source action one logical tick later,
then runs independently. No frame values are supplied by the harness.

`out/s7_instances_stagger_delivery` proves native pairs **1/0 at snapshot9**
and **4/3 at snapshot33**, plus equal-frame pairs. Both actors' actual OAM,
palette, offsets and visible pixels match. Screenshot `packet-0-4_1-3.png`
contains2,360 P1 and2,294 P2 visible source pixels. The targeted final trace
prepares that packet110462754 and consumes it110739232 in physical field310.

The full staggered sequence is **not admitted**:

- First failed attempt: clock110885228, field310, source snapshot39, both
  actors frame5. Last consumed packet still retains frames4/3, minimum3.
- Seven frame5 jobs totaling2240 bytes require retirement minimum4 and remain
  NEW. The first unavailable dependency is tile placement/lease, not palette
  completion or a lost ready flag.
- Displayed4/3 plus pending5/5 requires36 distinct encoded blocks = **9216
  bytes**, 1024 beyond8192. The current static layout also conflicts in slots
  9..16. Retaining these resources, rather than overwriting P2's frame3, is
  intentional. This is a current allocation/strategy limit, not proof that a
  different SNES packing/transaction design is impossible.
- At snapshot43 P1 no longer has an admitted source role; P2 still requests5.
  The second D703 miss preserves the old packet's resources. No mixed new/old
  snapshot is submitted to hide either miss.27 completed jobs remain byte- and
  overwrite-correct. The native fault and failed exit status are retained.

Stagger ROM SHA256: `4c038f4fb17121eb85662ac81b87fcdb2bf6a26dd7271d8321ea96b4ee1092f6`.
MSU is identical to the working two-instance artifact. Bounded independent
frame publication is proven; complete staggered-animation readiness is not.

## Validation and nonclaims

Eight focused instance-transport tests pass: source pixels, shared identity,
lease lifetime, pending/disappearing consumers, physical/job bounds, compiler
readiness nonclaims and generated completion/admission operations. Production
width check has0 new findings; generated transport width check has0 violations.
Changed Python compilation, candidate assembly and diff hygiene pass.

Only opt-in fixture/publication code changed. The original single ROM hash is
unchanged; accepted exact/compat damage100->95 versus100->96 code was not
modified. No campaigns, numerical suites, processor work or PAK sweeps ran.
Known six-actor CPU failures, runoff13, alternate-map streaming, distinct-model
residency and whole-model semantics remain separate outstanding work.
