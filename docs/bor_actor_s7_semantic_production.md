# Persistent SA-1: semantic closure and opt-in runtime

## Result

Classification: `PERSISTENT_SA1_PRODUCTION_READY` for the bounded six-actor
workload and the explicitly selected candidate path described here.

The persistent SA-1 owner passes the targeted hit, ordering, retarget, unlink,
wait/group, and between-snapshot event cases. The six-actor full-30 workload
still reaches tick 306 with bounded debt. The worker is now available as a
separately built, explicitly selected runtime image; the shipped
`distribution/bor.sfc` S-CPU implementation remains the fallback.

This is bounded opt-in readiness, not a full campaign or all-roster
certification. The candidate smoke uses the real Easy5 stage services and
production source-visual catalog, with a repeated authored Joe spawn record
to form the six-actor stress setup. It does not certify authored queue order,
all spawn/respawn paths, or general source actor coverage.

## Ownership and communication

The canonical mutable world and actor contexts stay resident in SA-1-visible
BW-RAM for the admitted epoch. The S-CPU queues 8-byte source-tick/input
records and continues input polling, audio, BG/world service, and sampled
presentation. It does not import or export whole actor contexts per tick.
Double-buffered 272-byte snapshots are sequence-acknowledged at dependency
boundaries; presentation reads only a committed buffer.

Gameplay events are a separate stream, not fields in the sampled render
snapshot. A 128-record ring uses 16-byte records at `$412450..$412C4F`, with
head/tail/overflow at `$412430..$412434`. The SA-1 producer sequences frame,
hit, and unlink records. The S-CPU verifies the expected sequence before
dispatch and acknowledgement. Full rings and bad sequence numbers fail closed;
unread events are never overwritten. Hit delivery queues the existing landed-
hit sound once without replaying damage. Unlink delivery updates the S-CPU
slot/accounting consumer once. Removal requests are applied at a source-tick
boundary, not by copying the world back.

## Targeted semantic cases

- Kula's real SOURCE_EXACT attack frames land force 5: victim HP `100 -> 95`,
  followed by the source pain role/frame. The SCPU and SA-1 runs have the same
  `S6HIT` witness at source tick 18; the SA-1 hit record carries attacker
  `0x1900`, victim `0x1B00`, HP 95, force 5 and is delivered in order. The
  delivery path calls the existing S-CPU hit-sound queue exactly once.
- Same-pass visibility: Joe `0x1B00` lands one force-18 hit on P1 `0x1900` at
  source tick 30. Later actor `0x1D00` sees HP 46, the hit ID, and pain state
  during that same pass; it does not apply a duplicate. The ordered hit witness
  matches on SCPU and SA-1.
- Retarget/unlink: the fixture begins with the enemy targeting P1 `0x0A00`;
  P1 is unlinked and the next selected target is P2 `0x0A85`. Both fixture
  proofs assert the removed row is gone, P1 accounting is updated, and the
  final target is P2.
- Wait/group: a dead-but-existing actor holds the wait. Its one unlink clears
  the actor and releases the wait once (`[1, 0]`). The SA-1 path transports one
  16-byte unlink record, catches tail up to head, and records zero overflow;
  the SCPU reference invokes its host unlink callback once.
- Multiple events between sampled snapshots: the SA-1 burst run emits two
  ordered hit records (sequence 26 and 28) for source tick 88. Both delivery
  callbacks precede the next snapshot/presentation boundary in the raw Mesen
  log, between the preceding sampled field and that boundary. The production
  smoke independently observes two tick-88 damage records at PPU field 331,
  after sampled field 326 and before sampled field 334.

For the exercised source ticks, SCPU and SA-1 `S6HIT` rows match exactly and
the visible world RNG state words match at equal source ticks (including the
Kula, same-pass, retarget, wait, and burst witnesses). The 306-tick comparison
also compares the complete world prefix containing RNG/attack state at every
tick. No fixture injects expected actor state into the runtime.

The per-case runtime proofs are retained under `out/actor_s7_kula_*` and
`out/actor_s7_semantic_closure/{samepass,retarget,wait,burst}_{base,sa1}`.
Their `proof.json` files are emitted only after each case's source assertions
pass; raw `mesen.log`, event rows, snapshots, and presentation observations are
kept beside them.

## Six-actor bounded performance

The matched profiled rerun compares the SCPU fallback with the persistent
worker through completed source tick 306. Both use six live actors, source-
exact workload, 16-KiB OBJ, and full-visual 30-Hz presentation.

| Measure | SCPU reference | Persistent SA-1 |
|---|---:|---:|
| Tick 241 completion field | 396 | 359 |
| Tick 247 completion field | 399 | 361 |
| Tick 306 completion field | 424 | 378 |
| Final due / completed | 462 / 306 | 309 / 306 |
| Debt min / max / final | 9 / 156 / 156 | 3 / 6 / 3 |
| Elapsed to final release | 49,145,236 MC | 32,666,922 MC |

This production-input-enabled replay of the exact accepted six-actor fixture
matches all 306 SCPU snapshots and all 70 ordered event rows. Elapsed falls by
16,478,314 MC (33.53%). Against the estimated 32.86M-MC bounded-workload
budget, the measured persistent run retains about 193K MC of margin. SA-1 used
3,576,697 cycles (7,153,394 MC), averaging 23,377 MC per source tick. The
S-CPU recorded 91 snapshot/flush boundaries; it did not wait after each of the
306 tick commands. Production input capture was enabled, but no gameplay input
was injected in this neutral-trajectory A/B.

The 306-tick run delivered 70 ordered frame-change records (1,120 event
bytes), queued 306 eight-byte commands (2,448 bytes), and acknowledged 91
272-byte snapshots (24,752 payload bytes). The measured S-CPU relay path was
777,522 MC total and the queue-call interval was 439,616 MC; these profiler
intervals overlap and are not additive. Snapshot waits were 642,164 MC and
tick-drain waits 4,796,140 MC, also overlapping. The worker error remained
zero; publisher readiness ended at 18 resources, zero in flight. The raw
legacy source-frame tail diagnostic remains nonzero (57 in the worker run
versus 65 in the SCPU reference, latch `D705`); it is retained as an admission
diagnostic, not reported as zero. The established six-actor static OBJ peak is
13,056 / 16,384 bytes; maximum observed OAM was 80 entries with no limiting
scanline/range/time-over condition.

The 70 frame-change records consumed 23,924 SA-1 cycles (47,848 master clocks)
to produce 1,120 bytes. S-CPU event draining consumed 138,262 master clocks
across 91 drain calls. These are separate CPU-side costs, not elapsed-clock
addends. The neutral 306-tick trajectory contained no hit or unlink events;
their payload/order/consumer behavior is covered by the targeted semantic
cases and the real-input production smoke.

## Opt-in production image and smoke

`tools/verify/actor_s7_production_runtime.py` builds a separate candidate from
the selected production source ROM/MSU, installs the persistent worker, and
leaves `distribution/bor.sfc` untouched. The candidate uses the 3,640-entry
production source-visual catalog, 16-KiB OBJ range `$8000..$BFFF`, BG2
character base `$3000`, BG3 base `$2000`, sequenced input, sequenced snapshots,
the gameplay event ring, and the full-visual 30-Hz policy. All 25 PCM files
are verified hardlinks.

One bounded Mesen smoke reached worker tick 116 and then stopped at an
acknowledged boundary before the runoff path. A real Y input edge (`$4000`)
was consumed at worker tick 10. Six actor rows remained live; opponent
role/frame state advanced. Two real tick-88 damage events changed both player
health mirrors from 64 to 46. All 51 produced event records were delivered in
sequence (`head=tail=51`, overflow 0); the two damage events were between
sampled fields 326 and 334. Source mode 1 was visible at full brightness with
68 actual OAM entries. PPU evidence shows BG2/BG3 character bases at `$3000`
and `$2000`.

The smoke retained a source-OBJ residency-busy diagnostic (`0x27`) from a
staging lease that was still owned by DMA. This path fails closed rather than
overwriting live tile data; later sampled frames rendered and no mailbox or
resource corruption was observed. This is not a claim of zero transient
source-frame admission misses. The smoke screenshot and VRAM/CGRAM/OAM dumps
are in `out/actor_s7_semantic_closure/production_runtime_final9/`.

Candidate ROM SHA-256:

- Opt-in worker ROM: `8835b095dae63bbf539ca28eb1f7efb1045eb6a9c55020a390b3ca0088182029`
- Opt-in worker MSU: `95a6ed3c09a556284d9468c316750c600d77e68494f8e015e9f52e478d8a9130`
- Source production ROM: `c2c8a78e30adb1d12f6a29b94e191598006b4e6a05cd6069f765d75260c3508e`
- Source production MSU: `6ad027df5ff878f4b3c49c7f1193ddbade94a30a83e8f74dc87c333b3d75b92c`

The exact accepted-fixture production-input A/B artifacts use ROM hashes
`806d3798967af8d09b8914de91b355263c5cb81d175551b2cf7f9bcc6a9f2799`
(SCPU) and `1239e1781d7d178a99a83b398a05db5f8308d1d568e5400f211012dea53635d2`
(persistent), with shared MSU SHA-256
`9b4e05534bc11f80678018c9e26188d5cb33c81e88a3d4babf0d936cc2007d61`.

## Reproduction

From the repository root, using the retained accepted six-actor input:

```powershell
python tools/verify/actor_s7_dma_audit.py --world-control --resident --continuous --profile --detail --replay-dir out/codex_s7_six_pub_30_fix8
python tools/verify/actor_s7_dma_audit.py --world-control --resident --persistent-worker --persistent-production --continuous --profile --detail --semantic-prefix 306 --replay-dir out/codex_s7_six_pub_30_fix8
python tools/verify/actor_s7_persistent_report.py out/actor_s7_dma_0jt6m7hm/dma.json out/actor_s7_dma_4hnkvumh/dma.json
python tools/verify/actor_s7_production_runtime.py --output out/actor_s7_semantic_closure/production_runtime_repro --base distribution --source-rom out/actor_s7_semantic_closure/production_runtime_candidate3-relinked.sfc --run-smoke
```

The final command creates a new opt-in image and performs the single bounded
production smoke. To validate the retained smoke evidence without launching
another emulator:

```powershell
python tools/verify/actor_s7_production_runtime.py --output out/actor_s7_semantic_closure/production_runtime_final9 --validate-existing-smoke
```
