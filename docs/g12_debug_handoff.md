# G12 six-actor debug handoff (WIP)

This is a review-only snapshot. It is not an accepted production result and
has not been merged into `g12-scaling`.

## Identity and reproduction

- Parent commit: `9955d45f5f5021494b0e370ba003ed7427f06f3e`
- Review branch: `review/g12-six-actor-debug`
- Candidate ROM SHA-256: `0F8C5724E2123B86D80A361BE28EACEBFD2BDB2B454FEE89CA3D74D177E676E7`
- Matching `distribution/bor.msu` SHA-256: `CB44CF710C4F9A964AD5E96EE3AA5A6D50227CD1E15EDFE02F13C93AF0B6F0A0`
- Build command:
  `python -c "import build_rom; build_rom.build_audio.main=lambda: None; raise SystemExit(build_rom.main())"`
- Mesen executable: `E:\gh\Mesen2\bin\win-x64\Release\Mesen.exe`
- Mesen package used by the harness: `E:\gh\Mesen2\python\mesen_mcp`.
  The executable file size was 168448 bytes, last modified 2026-08-29
  21:55:19. No package version string was retained.

Exact failure commands, from the repository root after the build above:

```
python tools/verify/game_g12_six_actor_production.py
python tools/verify/game_g4_transition.py
```

The first command is the current six-actor contract gate. The second is the
existing G4 control; its early `Stage_Cleared` observation is known verifier
debt, while its later real transition passes.

## VRAM failure

Directly observed by `game_g12_six_actor_production.py`:

- Slot 4 was production-spawned at entity base `$7E0C14`, slot 5 at
  `$7E0C99`.
- Their `CHAR_TILE_COLUMN` values were `$20` and `$21`.
- The final check attempted slot 4/5 destinations `$9000/$9080` plus row
  strides of `$0200` for six 128-byte rows.
- Slot 4 current logical state was frame 0 idle with source identity
  `123690`; slot 5 current logical state was frame 0 idle with source identity
  `146762`.
- The check waited for `Msu1_StreamBusy == 0`, then allowed a two-frame settle,
  and read hardware VRAM. It reported:
  `completed uploads match identified MSU frame sources (12 rows): FAIL`.
- The earlier retained mismatch was actor 4 row 1, source `123690`; a later
  run using candidate-frame matching found no complete six-row match for
  either added actor. The final output did not retain a first differing byte.

Directly observed: six distinct OAM entries, tile columns `$20/$21`, distinct
palette slots, and correct added-slot facing state. The final VRAM comparison
also directly observed that the current hardware rows did not match any of
the candidate logical frame sources tested by the checker.

Inferred but not proven: a logical-frame-versus-completed-DMA lifetime mismatch
or a source/destination/queue boundary defect. The existing checker did not
capture the staging buffer immediately after `Msu1_LoadFrame`, did not capture
the six queue records at enqueue time, and did not latch an upload identity at
the completion boundary. No staging/DMA byte-for-byte comparison was
performed. The first failing boundary is therefore **not yet measured**.

The temporary row-0 search and per-frame completion debug prints used during
diagnosis were removed. Their raw output was **not retained**; no conclusion
depends on them beyond the retained final gate failure above.

## Stage-completion failure

Directly observed in the six-actor gate after production reuse of slot 4 as a
prop and with only slot 5 restored as a live enemy:

```
completion state before/after slot5 kill: 0 [56, 0, 0, 0, 0, 64] 7
stage remains uncleared while only added slot 5 enemy lives: PASS
completion final: 0 saw_clear=False advanced=False [56, 0, 0, 0, 0, 0] state=0 spawn=7 7 screen=863 true=863
stage completion includes and transitions after added slot 5 dies: FAIL
```

Directly verified: the queue was exhausted (`Spawn_Index == Spawn_Count == 7`),
the added-slot-only blocking case stayed uncleared while slot 5 HP was 64,
and after the test write slot 5 HP read 0. The player remained alive and
`Screen_PosX` read `Stage_TrueMaxX` (`863`).

Not yet measured: a complete before/after production trace of `Game_State`,
`Spawn_Waiting`, group state, `Stage_Cleared`, `Screen_MaxX`,
`Stage_LoadPending`, and `Game_StageIndex` at every transition boundary.
The gate did not establish which production implication fails. The known G4
early-observation issue is not being substituted for this missing transition.

## Retained scope and nonclaims

The candidate includes the six bounded actor allocation, added production
spawn/reuse path, slot-specific OBJ mapping, count-driven depth fixture, and
collision-boundary fixture. It retains the single staging buffer and existing
single-buffer transport. No cache, second queue, SA-1 redesign, two-player,
or sound redesign is included.

The prior 600-frame measurement observed only four active combat actors and
is not a six-actor performance claim. A valid six-actor measurement has not
been captured. The rejected transport research remains in the existing
checkpoint and is not revived here.

## Fix-forward execution evidence (2026-09-05)

Build command:

```
python -c "import build_rom; build_rom.build_audio.main=lambda: None; raise SystemExit(build_rom.main())"
```

Current rebuilt `bor.sfc` SHA-256: `7895C13A045E250DFE5DDACC22A36BDF09D2224D22D4F13CBDD4C19BC77321A2`.
Matching `bor.msu` SHA-256: `CB44CF710C4F9A964AD5E96EE3AA5A6D50227CD1E15EDFE02F13C93AF0B6F0A0`.

The camera correction makes `Core_StreamScroll_PickColumn` derive demand from
`Screen_TargetX` while retaining the camera clamp. In the fresh slot-5-last-
enemy fixture, exact chunk logs showed the watermark advancing from 106 to
139, `Screen_PosX` reaching `Stage_TrueMaxX=863`, and `Game_StageIndex`
advancing to 1. This directly observed transition now passes.

The remaining attack blocker is directly observed. Immediately before reuse,
the player had `CharSelect_Loaded=1`, `CharSelect_RosterCount=13`, and
`Msu1Present=1`. After production reuse of slot 4 as a prop, its role was 3,
object roster 18, item roster 14, and idle count 1, but the shared load state
was `CharSelect_Loaded=0`, `CharSelect_RosterCount=0` for 20 exact one-frame
polls. `AnimHeaderStaging` at `$7E2320` was sixteen zero bytes. The player
attack edge was delivered (`Input_press=0x4000`, `Input_trigger=0x4000`), but
`CHAR_SELECTED` stayed 0 and target HP stayed 4. The first failing boundary
is therefore the spawn-driven `Anim_LoadCharacter` header/load-status handoff,
before collision or reveal. The attempted save/restore around
`Spawn_DoRosterReassign` did not resolve it; no force write is used as proof.

No valid six-actor performance measurement or publication claim exists yet.

## DBR correction and current results (2026-09-05)

The all-zero header was confirmed at the bank boundary: slot45 entered the
reassignment helper with actor D, DBR=$7E; `Anim_LoadCharacter` then accessed
absolute `$2000-$2003` as `$7E2000-$7E2003`. The zero seek cleared those WRAM
bytes and the header loop read sixteen zeros. The helper now saves/restores
DBR and establishes DBR=$00 only around the loader call, preserving D and
stack balance. This is directly confirmed by header
`01010164646401ffaa6e060000000000`, matching `distribution/bor.msu`'s
selected header, with `CharSelect_Loaded=1` and roster count 13 restored.

The slot-3 reveal omission was also corrected. `game_g8_pickup_chain.py`
passes real packed Chair damage -> reveal -> Money collection -> one reward
-> removal. Collision, four/six depth ordering, and the complete six-actor
production gate pass. The camera-demand correction remains in place; the
slot-5-last-enemy trace reaches `Stage_Cleared=1`, camera true edge 863, and
stage index 1.

Current artifact hashes are ROM
`C9B0026593A149309EEDDBD7945021C982EB962D0555168DB46C0D4DD343EB7D` and
MSU `CB44CF710C4F9A964AD5E96EE3AA5A6D50227CD1E15EDFE02F13C93AF0B6F0A0`.
The six-actor 600-frame trace is retained at
`out/g12_six_actor_measurement.json`; all five non-player actors stayed
HP-positive and role 2 in six exact 100-frame chunks. Requests/streams/
retries were `[44,37,4,7,92,54]` / `[44,33,4,6,84,45]` /
`[9,11,0,6,44,36]`; max waits `[1,2,0,2,3,4]`, DMA high-water 8 slots /
856 bytes, NMI 600/600, overruns 0. Slots 2/3 entered non-streaming state;
that is retained as an explicit per-actor observation.

The current VRAM proof remains bounded candidate-frame snapshot evidence;
staging and queued-row bytes were not independently latched at enqueue time.
This is an evidence limitation, not a claimed transport failure.

## Liveness and grab-link fix-forward (2026-09-05)

Analysis of the retained trace found actors 2/3 first entered
`selected=0, frame=$FF, tick=1` at samples 28/16, with longest complete
residences of 28 samples. Loaded idle counts and bases were valid. The state
is therefore classified as `pending_initial_frame`; it is not silently
excluded as non-streaming. The refreshed six-actor trace measured actor 2 as
140 due / 5 serviced / 402 busy-denied / 134 cancelled / 1 outstanding and
actor 3 as 152 / 7 / 394 / 144 / 1. Source inspection identifies the first
early-return boundary as the existing `Msu1_StreamBusy` gate before the
animation tick decrement. This is directly evidenced starvation under the
single-buffer transport; no new transport architecture was added.

The concrete grab defect was that byte link fields held CharacterEntity byte
offsets, truncating all offsets above 255. Links now store validated bounded
slot IDs and resolve them through `EntityOffsetTable` at every follow, throw,
release, AI-throw, death, and reuse consumer. `game_g7_grab.py` passes its
original-slot control, reciprocal-link, timer-release, AI-grab, and RALF
regression checks.

Roster reassignment now captures the target loader's actual
`CharSelect_Loaded` result before restoring the player's saved selection
state; reveal metadata is cleared only on successful target load.
