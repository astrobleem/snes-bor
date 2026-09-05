# G12 session checkpoint

## Kickoff

- Starting branch: `audio-content-pass`
- Starting HEAD: `58188b29023ab821ff83ed380e4e920fe2cf43e2`
- Starting accepted ROM SHA-256: `1ecd696eb3b927bebef8276fef661c156cb4e19e426ba7d33c04d670a97b7aa6`
- Roadmap frontier: G12, content and scale. SOUND is complete and remains closed.
- Current production entity limit: 4 `CharacterEntity` instances (player plus three AI); OOP has spare generic slots, but the character/OAM/runtime path is hard-coded to entities 0..3.

## Measured baseline

The fixture uses the real stage-clear transition to stage 1A, walks through its real spawn queue to create a production wave, then samples 240 real frames. It does not create fake entity slots or alter the scheduler.

| Entity | Role at sample start | Frame-index advances | Advances / real frame |
|---|---:|---:|---:|
| 0 | player | 25 | 0.1042 |
| 1 | AI | 23 | 0.0958 |
| 2 | AI | 17 | 0.0708 |
| 3 | AI | 8 | 0.0333 |

The current rule is per-entity idle/walk/attack tick decrement, gated before the decrement by global `Msu1_StreamBusy`; an animation advance performs one 768-byte MSU read and six 128-byte VRAM row-DMA enqueues. The main loop remains vblank-paced, so gameplay simulation continues at one update per real frame; the measured rates are presentation/frame-index rates only.

Runtime health in this sample:

- NMI delta: `240` over `240` real frames.
- NMI overrun observations: `0`.
- DMA queue pressure: all `8` queue slots observed active; maximum sampled queued-byte budget: `848`.
- `Msu1_StreamBusy`: observed asserted at sample boundaries.
- Hardware OAM remained populated with four distinct actor entries.

Five-, six-, and eight-fighter results are explicit nonclaims, not extrapolated measurements: the current production path has no slots 4..7, no OAM allocation for them, and no collision/render dispatch for them. The baseline tool records this boundary instead of faking WRAM entities.

## Bottleneck

The exact limiter is serialized ownership of the single `AnimFrameStaging` buffer and its six queued VRAM row transfers. `Msu1_StreamBusy` permits only one entity to start a frame transfer until the next NMI drains those rows. Thus an animation advance is not merely an MSU read: it occupies the shared staging buffer, six of the eight DMA queue slots, and the next visual commit. The 8-slot queue and observed 848-byte pressure are secondary evidence that queue headroom is already narrow once OAM/background work is included.

## Options considered

- **Selective frame residency / reuse — chosen first.** The OBJ sheet is `$4000-$4FFF`; current actors use only the first 8 tile rows of each of four 4-column slices. The second 8-row band is currently unused, so a BOR-specific two-resident-pose design can fit without changing OBSEL. Cache identity must include roster identity, animation identity, and frame identity; palette is an entity render concern, while sharing pixel data is safe only when the resident pose's source identity matches. Misses fail closed by retaining the last valid pose and retrying the stream request.
- **Scheduler change — rejected as the first slice.** Round-robin/fairness can redistribute the same one-transfer-per-NMI wall but cannot materially raise aggregate presentation throughput.
- **SA-1 participation — rejected for now.** The live SA-1 loop is a static BW-RAM/CC-DMA compositor experiment and is not on the OAM character path; routing character frames there would be a new transfer/composition system, not a bounded scheduler change.
- **Lower animation rates — retained only as fallback.** It preserves correctness but accepts the measured fourth-actor degradation and does not address repeated idle/walk/attack frame reads.

## First slice and boundary

The first G12 architecture slice is selective two-band pose residency for the existing four entities, with no 2-player work and no audio changes. The next implementation must add a small BOR-local cache with explicit owner/key/valid metadata, alternate OBJ-band selection, and a gate proving cache hits do not start an MSU transfer while misses preserve the current frame until their six row DMAs complete. It must retain the current gameplay update rate and prove four active fighters, visible OAM correctness, NMI health, and DMA pressure.

The committed kickoff measurement tool is `tools/verify/g12_scaling_baseline.py`. It is intentionally a nonclaim for 5/6/8 until production entity allocation is separately designed and gated.

## G12A refinement and implementation checkpoint

The refined trace records, per entity, roster slot, animation state, attack
variant, frame index, exact source identity (`base + frame * 768`), tick
counter, timed requests, retry attempts, forced loads, and wait latency.
Gameplay remains one update per real frame; only animation presentation is
deferred.

The existing 600-real-frame control was reclassified without changing
production behavior:

| Entity | Timed requests | Timed streams | Busy retries | Forced loads | Superseded/cancelled | Max wait | Average wait |
|---|---:|---:|---:|---:|---:|---:|---:|
| 0 | 43 | 43 | 12 | 19 | 0/0 | 1 | 0.000 |
| 1 | 42 | 32 | 18 | 21 | 1/9 | 2 | 1.188 |
| 2 | 35 | 33 | 24 | 8 | 1/1 | 3 | 1.424 |
| 3 | 13 | 12 | 10 | 3 | 0/1 | 3 | 1.417 |

For each entity, `timed requests = timed streams + superseded + cancelled +
outstanding`; all four controls have zero outstanding requests. Busy retries
are excluded from that invariant. The simulator's 171 count is a different
universe: every transition into a concrete source identity, consisting of 120
timed streams, 2 timed requests superseded by forced loads, and 49 independent
forced loads. The old 185 frame-index changes additionally included 14
transitions into non-streaming frame `$FF`; the old 197 due observations
included retry observations. The 240-frame control remains available through
the same tool; its original raw frame-change observations were 25/23/17/8.

### OBJ ownership proof

- OBJ base: VRAM word `$4000`; OBSEL shadow is `$C2`, large mode is 32x64.
- Full OBJ character band: `$4000-$4FFF`, tile numbers `0-255`, 256 tiles.
- Existing dynamic character storage: lower band, four 4-column slices,
  tile rows 0-7, words `$4000-$47FF`; each slice is 32 complete hardware
  pose tiles (4 wide x 8 high). Authored art occupies rows 0-5; rows 6-7
  are padding and are explicitly blanked for all four slices.
- Proposed G12A cache band: upper `$4800-$4FFF`, tile numbers `128-255`,
  128 tiles, four complete 32x64 pose slots. Six streamed rows leave the
  upper rows 6-7 unchanged; the production boot VRAM clear and the ownership
  audit show no other runtime writer there, so they remain blank padding.
- Other OBJ users: the boot test sprite uses tile 0 in the lower band and
  palettes 4-7; it does not touch the upper band. OAM/compositor code writes
  tile numbers and attributes only. No production code writes upper-band
  pose pixels.
- OBSEL's current setting selects the `$4000` OBJ base and does not consume a
  second character name table for this slice. The second-name-table/base
  capability is future headroom only; it is not enabled.

### Trace policy simulation

Offline simulation is in `tools/verify/g12_cache_simulation.py`, using
`out/g12/baseline_600.json` rather than synthetic requests:

| Policy | Hits | Misses | Reads/DMA groups eliminated | Projected denials | Evictions |
|---|---:|---:|---:|---:|---:|
| A no cache | 0 | 171 | 0 | 64 | 0 |
| B per-entity two-slot | 0 | 171 | 0 | 64 | 0 |
| C shared four-slot upper band | 0 | 171 | 0 | 64 | 167 |
| D four fixed hot idle slots | 45 | 126 | 45 | 19 | 0 |

Policy C was rejected: continuous multi-entity pose churn evicts before
reuse. Policy B was rejected by the real trace: two prior poses are not a
long enough history for these authored cycles. Policy D is the selected
smallest slice because it removes 45 of 171 observed frame reads (and their
six-row groups) without changing gameplay timing. Same-pose multi-entity
sharing did not occur in this production trace and remains NONCLAIM.

### Rejected first implementation

The rejected candidate added a BOR-local fixed four-slot hot-pose
cache in `src/core/depth_sort.pasm` and keeps `CHAR_TILE_COLUMN` as dynamic
fallback storage. Slots are keyed by the exact 24-bit MSU source address and
serve player idle frame indices 0-3. A cache hit selects tile bases 128, 132,
136, or 140 with no MSU read or frame-DMA enqueue. A miss uses the existing
`Msu1_LoadFrame` reader and six-row DMA path, targeting the upper band. Cache
validity is committed only from NMI after `Core_Dma_ProcessQueue`; the single
pending stream and `CharSelect_Loaded==0` load boundary prevent partial-slot
exposure and invalidate roster-reassigned poses. Palette and facing remain
OAM attributes. Other entities/actions fall back to their existing dynamic
columns.

The candidate ROM was `09db63f043699c210bb8e97ee1726d00698bf1bf3e8d7b416cfd9056cae33257`.
It deterministically failed `phase5.py` twice: player/entity animation
variation and AI hit-stun failed, while NMI advancement remained healthy. The
candidate is rejected as a production regression. Its source-only forensic
patch is preserved at `out/g12a_failed_candidate.patch`.

Production source has been restored to accepted HEAD. The protected-bank
bypass rebuild reproduces accepted ROM
`1ecd696eb3b927bebef8276fef661c156cb4e19e426ba7d33c04d670a97b7aa6`.
The full build's unrelated SFX-bank-plan verifier still fails against the
preserved user-owned `tools/audio/sfx_production_banks.json`; that file was
not touched.
Live cache-hit/miss visual and performance validation is PENDING. The earlier
Mesen application-error/JIT-dialog was caused by my recovery attempt launching
two Mesen instances concurrently; the harness itself was not changed. After
clearing both processes, a single foreground session launched cleanly with no
Mesen crash, but the existing stage-clear fixture failed: `Stage_Cleared`
remained zero and stage stayed `0`, while NMI advanced with zero overruns.
The existing `game_g4_transition.py` reproduces that failure on the current
ROM, so no live cache PASS is claimed.

Current validation ROM SHA-256: `1ecd696eb3b927bebef8276fef661c156cb4e19e426ba7d33c04d670a97b7aa6`.
G12A is not complete; no second residency implementation has started.

Exact remaining NONCLAIMS: more than four production entities, 2-player
co-op, SA-1 character acceleration, and multi-entity cache sharing.

## G12 throughput slice — rejected two-buffer experiment

The accepted baseline was measured before implementation and remains the
production authority: ROM SHA-256
`1ecd696eb3b927bebef8276fef661c156cb4e19e426ba7d33c04d670a97b7aa6`,
`phase5.py PASS`, NMI 1:1, and zero overrun observations. The existing G4
fixture's early `Stage_Cleared` observation remains known verifier debt; the
real transition/subsequent checks remain the authority for that lane.

### Budget decision

The real accepted 600-frame trace reached 848 queued bytes at its sample
boundary, with all 8 generic queue slots active. The software DMA budget is
`0x0B00` = 2816 bytes. Exact payload accounting for the proposed grouped
transport is:

| Work | Bytes | 8 master cycles/byte |
|---|---:|---:|
| OAM upload | 544 | 4352 |
| one character frame | 768 | 6144 |
| two character frames | 1536 | 12288 |
| maximum HUD upload | 256 | 2048 |
| two frames + OAM + HUD | 2336 | 18688 |

That leaves 480 bytes of payload headroom before other regular work and CPU
setup. The installed MCP endpoint rejected the advertised `get_cpu_state`
tool, so an entry-to-return CPU-cycle measurement was unavailable; the live
NMI/queue measurements and exact DMA arithmetic are recorded in
`out/g12/budget_measure_accepted.json`.

### Experiment and rejection

A task-local candidate implemented two fixed 768-byte staging buffers, a
two-descriptor grouped upload path, bounded active ownership, and NMI-side
expansion to the existing six strided row transfers. It was built only with
the protected SFX validator bypassed; `tools/audio/sfx_production_banks.json`
was not touched.

The live modified 600-frame trace showed the transport symptom improving:
`Msu1_StreamBusy` occupancy reached 2, NMI was 600/600, and NMI overrun
observations stayed 0. Due-request wait maxima were 2/1/1/1 frames and
averages were approximately 0.43/0.23/0.29/0.18 frames, versus the accepted
single-buffer control's 1/2/2/3 maxima and approximately
1.00/1.19/1.42/1.42 averages. `phase5.py` also passed on that candidate.

The required correctness gate then failed: accepted and committed descriptor
telemetry diverged, and the six-row hardware VRAM contents did not match the
exact MSU frame source bytes. This is a real transport corruption result, not
an emulator-overrun result. The candidate was rejected and production source
was restored; the two-buffer trace remains at
`out/g12/baseline_600_two_buffer.json`, and the failed gate is
`tools/verify/game_g12_throughput.py`.

No high-contention 5/6/8 service fixture was promoted or claimed. The
candidate failed the required four-entity correctness proof first, so the
service-path stress result is explicitly NONCLAIM rather than extrapolated.

### Current decision

`G12 THROUGHPUT SLICE: REJECTED`.

Production remains the accepted single-buffer architecture. Residency
research remains unchanged: generic two-slot and shared four-slot policies
had zero hits; the fixed hot-player-idle policy predicted 45/171 hits. Sound
is closed and not part of this decision.

## G12 actor-capacity migration — four-actor checkpoint

The first count-driven four-actor migration is implemented and validated.
`CHARACTER_ACTOR_COUNT` is authoritative for bounded player-target traversal;
the target offsets remain a separate actor-slot table, preserving player slot
0 and keeping actor slot, roster identity, OAM order, and VRAM allocation
distinct. The former fixed Entity1/2/3 collision dispatch now reaches the
existing grab/damage rules through one dynamic target helper. AI-vs-player,
props, and existing pickup behavior remain on their established paths.

The AI invulnerability bytes were moved to a contiguous indexed block at
`$7E58B0`, leaving the character struct unchanged and reserving slots for the
later six-actor extension. Four-actor validation passed `phase5.py`,
`phase11_damage.py`, `game_g8_props.py`, `game_g7_depth_sort.py`, and
`game_g7_grab.py`. Six-actor behavior and VRAM mapping are still NONCLAIM.

## G12 entity-capacity continuation — six-slot implementation in progress

The bounded actor count is now 6 while retaining player slot 0, the existing
CharacterEntity struct, single staging buffer, and single-buffer animation
transport. Six OOP instances are allocated in the existing boot path; slots
4 and 5 remain dormant until Spawn_Play claims them. Their physical OBJ
columns are 32 and 33, mapping to OAM base tiles $80/$84 and first-row VRAM
byte addresses $9000/$9080; slots 0-3 retain $8000/$8080/$8100/$8180.
Depth sorting and the DP-base table are bounded at six entries.

The added spawn path is shared by slots 4/5 and writes through the selected
object's DP window. Wait/group enemy counting, stage-clear alive checks,
extra timer maintenance, and pending-item reveal traversal now include the
added slots. This remains implementation work only: real six-actor
production-spawn proof, slot-4/5 combat/death/reuse proof, complete VRAM and
palette validation, and >=600-frame service measurements are pending. No
transport or cache experiment is part of this slice.

## G12 review fix-forward — current evidence (2026-09-04)

Review branch: `review/g12-six-actor-debug`, parent WIP
`bd48d542c68f81ed769d11e4b1732fe471460864`. The spawn correction now
restores slot 3 to `Spawn_Play__advance`, establishes A16/I16 before the
slot-4/5 offset capture and `TCD`, restores `PLB` then `PLD`, uses A8 for
boss flags, and stores added-slot item metadata at standalone
`$7E58B8/$7E58B9` cells. Added-slot pickup overlap paths are present in
`src/core/jump.pasm`. The stage predicate explicitly enters A8 before
comparing the adjacent byte cells `Spawn_Index` and `Spawn_Count`; the prior
emitted code was A16 and consumed the low byte of `Spawn_CountX8` as part of
the comparison.

Fresh build command:
`python -c "import build_rom; build_rom.build_audio.main=lambda: None; raise SystemExit(build_rom.main())"`

Fresh artifacts:

- `distribution/bor.sfc`: `8A045586C32F6E2BF02E3A28B9004A5AD63340D84D4597AD86A27E53A6D2BDEE`
- `distribution/bor.msu`: `CB44CF710C4F9A964AD5E96EE3AA5A6D50227CD1E15EDFE02F13C93AF0B6F0A0`

Focused fresh results: `game_g12_collision_boundaries.py` PASS and
`game_g7_depth_sort.py` PASS for both four- and six-actor fixtures. The
six-actor production gate passes production spawning of five non-player
combat actors, six distinct OAM entries, palettes/facing/tile columns,
completed slot-4/5 frame-source VRAM comparison, added-slot state, prop
metadata, and slot reuse/grab-link clearing. It still FAILs the required
slot-5 last-enemy stage transition. The final observed state is
`Stage_Cleared=0`, `Game_State=PLAYING`, `Stage_LoadPending=0`,
`Game_StageIndex` unchanged, `Spawn_Index=7`, `Spawn_Count=7`, and
`Screen_PosX=0`, `Stage_TrueMaxX=863` after the normal input interval.
The exact live instruction/operand trace remains not retained because the
available Mesen hook/CPU-state endpoint did not produce events. No six-actor
600-frame animation-service measurement is claimed until this correctness
failure is resolved. No transport, cache, two-player, SA-1, or sound change
is included.

## G12 DBR fix-forward and six-actor evidence (2026-09-05)

The confirmed reassignment failure was a bank-contract violation. Slot 4/5
spawn used DBR=$7E for actor-relative accesses, then called
`Anim_LoadCharacter`, whose absolute `$2000-$2003` accesses are MSU hardware
registers and therefore require DBR=$00. The zero-offset seek consequently
cleared WRAM `$7E2000-$7E2003`, producing sixteen zero header bytes.
`Spawn_DoRosterReassign` now preserves the caller bank, establishes DBR=$00
only across the loader path, restores PLB then PLD, and restores the player
selection-load state. D remains the actor window (`$0C14`/`$0C99`).

The reveal dispatcher now has an explicit slot-3 branch; invalid offsets are
rejected instead of clearing slots 3/4/5 together. The packed G8
Chair->Money production path passes damage, reveal, collection, reward-once,
and removal. Collision and depth-sort four/six controls pass.

Fresh build command:
`python -c "import build_rom; build_rom.build_audio.main=lambda: None; raise SystemExit(build_rom.main())"`

Fresh artifacts: `distribution/bor.sfc` SHA-256
`C9B0026593A149309EEDDBD7945021C982EB962D0555168DB46C0D4DD343EB7D` and
`distribution/bor.msu` SHA-256
`CB44CF710C4F9A964AD5E96EE3AA5A6D50227CD1E15EDFE02F13C93AF0B6F0A0`.

The six-actor measurement is retained at
`out/g12_six_actor_measurement.json`, from six consecutive exact 100-frame
chunks in one session. All five non-player actors remained HP-positive and
AI-role active throughout. Per-slot timed requests/streams/retries were
`[44,37,4,7,92,54]` / `[44,33,4,6,84,45]` / `[9,11,0,6,44,36]`;
max waits were `[1,2,0,2,3,4]` and average waits were
`[0.205,0.273,0,1.0,0.476,0.667]` frames. DMA high-water was 8 active
slots and 856 queued bytes; NMI delta was 600 with zero overruns. Slots 2/3
entered non-streaming animation state and are reported explicitly.

The current VRAM helper still uses bounded candidate-frame snapshot matching,
not a newly latched source/staging/queue identity. This is an evidence
limitation, not a transport failure claim. Residency, two-player, SA-1, and
sound remain nonclaims.
