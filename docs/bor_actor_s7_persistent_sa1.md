# Persistent SA-1 source-world worker: six-actor measurement

Result: `PERSISTENT_SA1_SUFFICIENT` for the measured six-actor trajectory
through tick 306. This is a bounded private runtime proof. The worker is
opt-in fixture instrumentation; production ownership and policy are unchanged.

## Feasibility and old-pilot audit

The accepted six-actor, full-30-Hz anchor is approximately 46.19M emulated
master clocks (MC), against approximately 32.86M MC for 306 source ticks. The
required reduction is therefore about 13.33M MC. The accepted S-CPU
simulation/world attribution is 30,965,440 MC; the remaining workload is about
15,224,560 MC.

The retained pilot report `out/actor_s7_resident_comparison.json` records the
old SA-1 worker body at 1,352,738 MC / 43 ticks = 31,459 MC/tick. Normalized to
306 ticks this is 9,626,454 MC. With the unchanged 15,224,560-MC remainder, the
projection is 24,851,014 MC. At most 8,008,986 MC of synchronization and
snapshot work could fit under the 32.86M budget.

That old design lost because ownership was temporary. Its exclusive
`Relay_Acquire` and `Relay_Flush` costs were 1,388,956 and 1,280,960 MC
respectively, 2,669,916 MC combined over six acquisition/release batches. The
old pilot moved whole contexts into SA-1 for a bounded batch, then mirrored
them back and released ownership. Its 1,352,738-MC worker body was not the
problem; repeated context transfer erased the saving. The retained comparison
measured the SA-1 path 683,140 MC slower end-to-end than resident S-CPU.

## Persistent candidate

The private worker keeps the canonical mutable source world and six actor
contexts in the shared BW-RAM region after one acquisition. The regions are
defined in `tools/verify/actor_s7_persistent_worker.py`: world `411700..4117FF`,
actor contexts `411900..411EFF`, callback environment `412100..41241D`, an
8-byte-record tick ring `413000..413FFF`, and alternating 256-byte render
snapshots `414000..4141FF`. The persistent relay is sequenced through the
existing SA-1 shared control bytes.

S-CPU to SA-1 traffic is one initial 2,594-byte world/context/environment and
global-input import, then 306 eight-byte tick records (2,448 bytes). There is
no context copy in either direction per tick. The record carries elapsed-field
demand plus camera/spawn inputs; this measured trajectory is neutral and has no
post-initialization controller writes. Each of 91 dependency boundaries drains
the queued target, requests a sequence-acknowledged snapshot, and only then
projects the selected state to S-CPU presentation mirrors. Each snapshot is
256 bytes (23,296 bytes total SA-1 to S-CPU payload); request/completion bytes
are protocol control, not included in those payload totals. The S-CPU does not
wait after each of the 306 queued ticks.

The same ordered world-pass implementation runs on SA-1: lost/lifecycle,
gravity, targeting/think, animation, attack/collision, and health passes stay
inside the worker. The world prefix included in each semantic sample contains
the source RNG/attack state; actor samples include positions, target, health,
role/frame, and lifecycle fields. Render state is read only after the
double-buffer sequence acknowledgement. Tick demand is capped before tick 307;
the run stops before the runoff-driver-13 path.

## Runtime result

The S-CPU and persistent-SA-1 runs use the same six-actor, 16-KiB-OBJ,
full-visual-30 fixture and reach source tick 306. The semantic comparison has
306 exact world/actor snapshots and 70 equal ordered event rows. All six actor
slots remain live. The only recorded event kind in this neutral trajectory is
`FrameChanged`; it contains no hit/damage or unlink transition, so those event
classes were not exercised by this particular trace.

| Measurement | S-CPU baseline | Persistent SA-1 |
|---|---:|---:|
| Tick 241 completion field | 396 | 359 |
| Tick 247 completion field | 399 | 361 |
| Tick 306 completion field | 424 | 378 |
| Final NMI due / completed | 462 / 306 | 309 / 306 |
| Debt min / max / final | 9 / 156 / 156 | 3 / 7 / 3 |
| Debt trend | grows overall | bounded; falls from peak to 3 |
| Measured elapsed through final release | 49,145,236 MC | 32,661,160 MC |

The table is the matched profiled rerun; the previously accepted lighter
full-30 S-CPU run completed tick 306 at field 423. This rerun completed it at
field 424. Both semantic traces end at the same source tick and state.

The matched profiled elapsed reduction is 16,484,076 MC (33.54%). Against the
accepted unprofiled 46.19M-MC anchor, the measured SA-1 run is about 13.53M MC
lower (29.3%), clearing the estimated 13.33M reduction by about 0.20M MC. The
small remaining budget margin makes this a bounded-workload result, not a
general production guarantee.

The SA-1 body consumed 3,536,921 SA-1 cycles = 7,073,842 MC total, or 23,117
MC/source tick on average. The 91 S-CPU flushes accounted for 4,736,026 MC
waiting for tick drain and 600,914 MC waiting for snapshot acknowledgement.
Other measured costs were 230,672 MC for the one-time acquire, 275,284 MC for
306 queue calls, and 612,518 MC for 306 relay calls. The wait totals and
exclusive relay profile intervals overlap; do not add them to each other or to
the SA-1 body as if they were serial elapsed costs.

Selected exclusive S-CPU costs (MC):

| Service | S-CPU baseline | Persistent SA-1 |
|---|---:|---:|
| BG stream/scroll | 7,892,380 | 7,525,700 |
| Actor visual preparation | 784,554 | 737,816 |
| Publisher capture + entry | 1,300,786 | 1,181,374 |
| Input poll | 120,688 | 119,574 |
| Audio stream frame + late service | 155,560 | 155,902 |
| HUD | 433,374 | 429,838 |
| NMI/DMA measured body | 3,259,846 | 825,538 |

The exact A/B profile summaries and the bounded runtime rows are retained in
the two run directories named by the reproduction command below. The accepted
visual manifest requires 13,056 / 16,384 OBJ bytes (51 blocks). The established
six-actor OAM proof remains 80 entries with no scanline/range/time-over limit.
In this run the source publisher ended at 18 resources complete, zero
in-flight, ready; persistent preparation/publication counts were 50/49 and the
worker error byte was zero. The raw legacy `S7Multi_OamTail__missing` diagnostic
is not zero in either run (65 baseline, 57 worker; D705 remains latched in both).
It is inherited from this fixture's source-frame admission path, not a new
worker/mailbox fault, and is kept visible here rather than relabeled as zero.
The worker uses the identical publisher code and assets; this experiment proves
resource readiness and no worker-side publication regression, not zero raw
source-frame admission misses for every animation state.

ROM SHA-256:

- S-CPU: `806d3798967af8d09b8914de91b355263c5cb81d175551b2cf7f9bcc6a9f2799`
- Persistent SA-1: `31d03e915ee1377033b84768bcfd05bb2d65209e9278db09da18f8a190af4dab`
- Shared MSU: `9b4e05534bc11f80678018c9e26188d5cb33c81e88a3d4babf0d936cc2007d61`

## Reproduction

From the repository root, using the retained six-actor input at
`out/codex_s7_six_pub_30_fix8`:

```powershell
python tools/verify/actor_s7_dma_audit.py --world-control --resident --continuous --source-tick-horizon 306 --profile --detail --replay-dir out/codex_s7_six_pub_30_fix8
python tools/verify/actor_s7_dma_audit.py --world-control --resident --persistent-worker --continuous --profile --detail --semantic-prefix 306 --replay-dir out/codex_s7_six_pub_30_fix8
python tools/verify/actor_s7_persistent_report.py out/actor_s7_dma_0jt6m7hm/dma.json out/actor_s7_dma_1j5r6qju/dma.json
```

Both audit runs hardlink immutable PCM/MSU inputs. The persistent report asserts
snapshot/event equality, six live actors, complete tick ranges, no worker fault,
and publisher resource readiness, then prints debt, elapsed cost, and transfer
accounting.
