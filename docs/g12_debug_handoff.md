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

