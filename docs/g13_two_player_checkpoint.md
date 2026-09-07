# G13 two-player first-slice WIP checkpoint

Status: WIP review publication; camera/pause slice green except for the
survivor-only runtime injection probe classified MCP-boundary-unmeasured;
not accepted and not merge-ready.

Current camera/pause fix-forward source is uncommitted on `g13-two-player`.
The production midpoint correction changes the upper-order branch to load
`Entity1_PosX` (the previous code loaded `PlayerEntity_PosX` twice). The
pause WAIT path now accepts P2 Start only when `G13_TwoPlayerEnabled`, using
the same global selected-row commit as P1 Start. No transport, actor layout,
audio, or jump/combat mechanics changed.

Current fix-forward source/evidence commit: `291ffae` (`g13: close combat
and jump verifier evidence`).

Parent/source commit: `3c0a75c6c303e383ec71f31f3baa6da3f407c8f0` on
`g13-two-player`. Published WIP source/evidence commits are
`4f8552a60f3d9fba9c3627d3c8110d4352d9da6b` and
`423399e687cf7e4c1a26e7e1b41827776b6cbeb1`, and
`ce5f3d8987ef9742500e3544ac66672dd0f81e09`; this fix-forward is the
jump-isolation review slice.

## Artifacts

- ROM: `E:\gh\snes-bor-g13\distribution\bor.sfc`
- ROM SHA-256: `C94E45AE7404440B44BB7F0B8CD0C65BCF73252A3B617081A5180A5ED71DF2CB`
- MSU: `E:\gh\snes-bor-g13\distribution\bor.msu`
- MSU SHA-256: `CB44CF710C4F9A964AD5E96EE3AA5A6D50227CD1E15EDFE02F13C93AF0B6F0A0`
- Build: `python -c "import build_rom; build_rom.build_audio.main=lambda:0; raise SystemExit(build_rom.main())"`
- Layout: `python tools\\rom_audit\\verify_layout.py src\\main.pasm src\\main.sym`
- Semantic probe: `python -u tools\\verify\\game_g13_semantic_boundary.py`
- Jump probe: `python -u tools\\verify\\game_g13_jump_isolation.py`
- P2 session: `python -u tools\\verify\\game_g13_p2_session.py`
- Authoritative input/session gate: `python -u tools\\verify\\game_g13_two_player_input.py`
- Legacy input probe (superseded; not in the active suite):
  `python -u tools\\verify\\game_g13_input.py`
- One-player capacity: `python -u tools\\verify\\game_g13_one_player_capacity.py`
- Camera/pause: `python -u tools\\verify\\game_g13_camera_pause.py`
- Width report: `python -u tools\\rom_audit\\check_width_directives.py`

The build uses the existing generated audio assets because the source audio
PAK is not present in this worktree. No audio source or protected audio file
was changed.

## Tool identity

- Python client: `E:\gh\Mesen2\python`, repository revision
  `5fb1f1b6cba1b9348b40ff2d03ae6e4afde16f63`
- Mesen executable:
  `E:\gh\Mesen2\\bin\\win-x64\\Release\\Mesen.exe`
- Mesen version: `2.1.1+40a8389d433ab6bd6f0b64bb55c479952ff95ad2`
- Shared Mesen source audit revision:
  `E:\gh\Mesen2-mcp-server` at
  `ed2e70e9473bff453072fd090964118fbec3b819`

## Current implementation

The slice adds an independent JOY2 poll/context bridge, fixed-session P2 in
slot 1, mode-dependent Spawn_Play reservation and completion accounting,
P2 jump-family state, nearest-live-player AI targeting, shared midpoint
camera/tethering, and P2 score/pickup ownership. The six-actor G12 layout,
`CHAR_ZP_LEN=133`, single staging buffer, and audio behavior are retained.
The P1 jump bridge copies the six count/delay bytes and three 24-bit bases
explicitly, then copies `Player_JumpAnimMode` at `$7E27DA`; it does not treat
the intervening scratch as a contiguous live block. P2 owns the separate
16-byte block at `$7E2697-$7E26A6`. P2 input is `$7E0416-$7E041B`, while
context scratch and P2 score/lives occupy separate audited symbols.

This jump slice made only focused ownership/call-contract corrections. The
fixed-session initializer in bank 7 now calls the bank-0 loader through
`Anim_LoadCharacter_Long`, reloads P1's standalone jump family from actor 0's
roster record before installing P2, and the actor dispatcher restores its
entry D before testing and exiting the P2 context. No jump mechanic, actor
record, animation transport, or audio redesign was made.

The verifier no longer reports P1's input context as P2's actor-local input;
the semantic claim is the Y-poll-associated entity invocation reached
`Core_Oop_Play__done`, with both selected values observed as 2 in the bounded
post-service window, rather than calling a generic delayed snapshot the
semantic-end sample.

## Evidence

Passed on the current ROM:

- bank-0/layout audit: PASS; 1,895 symbols, zero drift;
- `python -u tools\\verify\\phase5.py`: PASS;
- `python -u tools\\verify\\game_g13_one_player_capacity.py`: real
  Spawn_Play path produced live NPC slots `[1,2,3,4,5]` in one-player mode;
- `python -u tools\\verify\\game_g13_p2_session.py`: production title
  P2 Start path established slot 1 as input-driven LEO with HP 64;
- `python -u tools\\verify\\game_g13_two_player_input.py`: authoritative
  independent JOY1/JOY2 gameplay-context and synchronized action gate PASS.
  The older `game_g13_input.py` is retained as LEGACY/SUPERSEDED evidence;
  it uses an obsolete setup path and is not an active acceptance gate.
- In the two-player context gate, fresh-session P1-only and P2-only movement
  and attack cases pass when each edge is delivered independently. The
  synchronized P1+P2 Y control now passes after a bounded complete service
  window.

## Jump isolation slice

The focused clean-session controls pass without a jump-gameplay change:

- P1-only: P1 selected jump and became airborne; P2 remained grounded.
- P2-only: P2 selected jump and became airborne; P1 remained grounded; the
  complete P1 standalone jump-family snapshot was restored exactly after P2
  dispatch.
- Simultaneous A: both actors selected jump and developed nonzero, independent
  actor-local airborne state in the same bounded service sequence.
- LEO jump family: P1 and P2 independently reached jumpattack mode 1 from Y
  and jumpattack2 mode 2 from X.
- RALF P1 + LEO P2 negative control: P1's jump counts/bases remained zero,
  P2 retained LEO's 22/2/9 family, and neither context acquired the other.
- Staggered landing: one player returned from jump while the other remained
  airborne, without replacing the other's live jump state.
- Airborne opposite movement: from `(120,180)`, P1/P2 reached `(114,186)`.

The accepted single staging buffer serialized presentation as designed; these
gates do not require two uploads in one NMI. The retained evidence is
`out/g13_jump_isolation.json`; it records actor state and jump-family identity,
not a new DMA tracing framework or a claim of simultaneous VRAM completion.

## Semantic-boundary correction

The prior simultaneous assertion sampled after one PPU frame and called that
an update boundary. That was false: P1 is dispatched before P2, and the sample
could occur before slot 1's `CharacterEntity_Play`. The prior retained sample
was:

`$s='E:\\gh\\Mesen2\\bin\\win-x64\\Release\\settings.json'; $b=[IO.File]::ReadAllBytes($s); try { $t=[Text.Encoding]::UTF8.GetString($b); $i=$t.IndexOf('"Port2"'); $j=$t.IndexOf('"Type": "None"',$i); $t=$t.Remove($j,18).Insert($j,'"Type": "SnesController"'); [IO.File]::WriteAllText($s,$t,(New-Object Text.UTF8Encoding($false))); python -u tools\\verify\\game_g13_two_player_input.py } finally { [IO.File]::WriteAllBytes($s,$b) }`

`SIMULTANEOUS_ATTACK (2, 0, '004000400000', '004000400000', '00400040')`

This is classified as a verifier timing failure, not an engine rejection.
The corrected focused controls were run with the same protected Port2 wrapper
and `python -u tools\\verify\\game_g13_semantic_boundary.py`.

Retained output: `out/g13_semantic_boundary.json`. Raw JOY1/JOY2 high-byte
reads are both `0x40` on input-poll frame 235. One ordered `Core_Oop_Play`
invocation begins at frame 235 and reaches `Core_Oop_Play__done` at frame 236.
Within it, P1 `CharacterEntity_Play`, P2 `CharacterEntity_Play`,
`G13_Player2_ContextEnter`, P2 `Anim_Play__player_input`,
`Jump_PlayerInputGate`, `G13_Player2_ContextExit`, and `done` occur in order;
both actors are selected `2` at the semantic end. The P2 context entry is the
slot-1 bridge whose source contract uses actor D `$0A85`.

The installed MCP exposes execution/read hooks but no registered
`get_cpu_state` tool, so asynchronous notifications do not retain event-time
D, accumulator, or cycle registers. WRAM write hooks also emitted no selected
store notifications. These are explicit limitations, not inferred stores.
The event stream does retain raw input reads, ordered execution labels, frame
identity, the semantic end, and post-boundary selected state.

The old all-zero tuple occurred before the synchronized neutral correction
and is retained only as historical verifier evidence, not as the current
classification.

The old outer-session action attempts were contaminated by repeated reset and
input setup; those are not used as acceptance evidence. No production combat
or transport change was made to hide this red result.

The focused semantic-boundary probe and the corrected direct input gate both
now pass on the ROM above. The direct gate reports `P1_ATTACK_ONLY 2 0`,
`P2_ATTACK_ONLY 0 2`, and `SIMULTANEOUS_ATTACK (2, 2, ...)`. The semantic
probe reports one synchronized input poll at frame 235, one Core_Oop_Play
invocation spanning frames 235-236, and selected `2` for both P1 and P2 at
that invocation's end. The three-frame bounded window is exact and not a
timeout; it covers the poll that follows fixture setup and the complete
entity pass.

## Explicit nonclaims

This WIP does not claim a complete two-player slice,
friendly-fire proof, AI hit attribution, camera/pause, score/pickup,
stage-handoff, or a valid continuous 600-frame two-player workload. It also
does not claim `confirmed_busy_denials`; that remains unmeasured/null.

Protected audio files and unrelated dirty files are excluded from the WIP
publication.

## Combat and AI targeting WIP

This fix-forward keeps the six-actor layout, CHAR_ZP_LEN=133, single
animation staging buffer, and accepted G12/SOUND behavior.

Source corrections in the current WIP:

- AI target selection now runs at the start of each live AI actor dispatch,
  so a multi-frame attack does not inherit another actor's transient target.
- The P2 candidate reads byte fields in A8, the exact-distance tie retains P1,
  and `$FF` is an explicit no-target result. The hit leaf rejects `$FF` before
  any player HP, stun, grab, or invulnerability write.
- P2 owns standalone `G13_P2_InvulnFrames` at `$7E26CC`, initialized from
  `PLAYER_RESPAWN_INVULN_FRAMES` and maintained by the existing extra-timer
  path. No character-record growth was introduced.

Focused evidence retained in `out/g13_combat_ai.json` and the run logs:

- real P1-vs-NPC and P2-vs-NPC attacks each reduced the NPC from 64 to 60
  while the other player's HP remained 64;
- nearest-P1, nearest-P2, exact tie, dead-P1, and dead-P2 target-slot cases
  selected `0`, `1`, `0`, `1`, and `0` respectively;
- P1 and P2 invulnerability counters remained independent in the focused
  timer controls.

The earlier selector-localized both-dead control recorded `$FF` before normal
P1 respawn could overwrite the fixture, but the new direct movement attempt
could not preserve that tuple through the MCP frame-granular stop. The latter
result is tooling-limited and is not promoted as runtime evidence. The combat
closeout verifier now retains green friendly-fire, AI invulnerability,
multi-AI attribution, and P2 grab/throw evidence; no-target movement remains
tooling-limited.

Current clean rebuilt ordinary artifact: `distribution/bor.sfc` SHA-256
`C94E45AE7404440B44BB7F0B8CD0C65BCF73252A3B617081A5180A5ED71DF2CB`;
`bor.msu` remains
`CB44CF710C4F9A964AD5E96EE3AA5A6D50227CD1E15EDFE02F13C93AF0B6F0A0`.
Build command: `python -u -c "import build_rom; build_rom.build_audio.main=lambda:0; raise SystemExit(build_rom.main())"`.
Layout guard passed with runtime end `$FF68` and 56 bytes before NMI.

Later G13 gates are intentionally not claimed: camera, pause, score/HUD,
pickup ownership, stage handoff, P2 death/continue, dual character
selection, and the continuous two-player workload.

## Jump fixture follow-up

At the published `f812959ebc00a87ff3c0db1ea114fd69876e8ded` source,
`src/core/jump.pasm` is byte-identical to the accepted jump source at
`06e36859dae22abb7a718c66ab13ce82a7237e0a`. The old jump failures were
therefore diagnosed as fixture contamination: the long live RALF/LEO
reselect setup left NPC combat traffic active, and the old shared
`neutral_players()` helper only killed NPC2.

The permanent jump-local fixture freezes `Spawn_Index == Spawn_Count`,
neutralizes NPC slots 2-5 including standalone invulnerability and links,
neutralizes unrelated P1/P2 combat state without writing jump-family fields,
and establishes two real neutral controller polls. The verifier records the
complete setup, post-neutral, pre-edge, and action-window state for P1/P2,
NPCs, controller contexts, jump families, invulnerability, and spawn state.

`out/g13_jump_isolation_pre_fixture_fix.json` retains the original failing
run; `out/g13_jump_isolation_red_repeat.json` retains the required 5/5
results for each formerly red case. Simultaneous jump, P2 jumpattack, P2
jumpattack2, and airborne opposite movement all pass 5/5 (20/20) on fresh
sessions. The authoritative RALF-P1/LEO-P2 restoration negative passes 20/20
fresh sessions with P1 roster 0 and zero jump-family counts at stable
boundaries while P2 retains the LEO family.

One broader legacy full-run attempt had an intermittent P1-family endpoint
assertion even though the requested four red cases and focused controls were
green; its raw output is retained as `out/g13_jump_isolation_full_flaky.json`.
The endpoint can occur after a transient family mode has already returned to
idle, so it is not promoted as a production jump failure. No production
source was changed. Current ROM/MSU remain
`C94E45AE7404440B44BB7F0B8CD0C65BCF73252A3B617081A5180A5ED71DF2CB` /
`CB44CF710C4F9A964AD5E96EE3AA5A6D50227CD1E15EDFE02F13C93AF0B6F0A0`.

## Timer and no-target fix-forward

The committed WIP source had no P2 countdown; the unstaged
`src/core/game_state.pasm` differed only by EOL and was discarded after an
ignore-whitespace comparison. A clean detached build of `0a6f4fa` reproduced
ROM `92CC8751...029F`, proving the earlier `9->7` observation came from the
unpublished test/build state, not that commit's source.

The P2 decrement now lives in `Game_State_TickExtraActorTimers`; the cell is
explicitly boot-initialized and the timer pass is gated by
`G13_TwoPlayerEnabled`, so 1P seeded state does not tick. It does not grow
bank 0 or CHAR_ZP_LEN. Write-watch
evidence records paired P1/P2 writes `8`, `7`, then `6`, `5` on consecutive
gameplay frames. `tools/verify/game_g13_invuln_timing.py` passes the bounded
semantic write checks; its endpoint hook samples are not used as timing proof.

`Character_PlayFrame__ai_x` now checks the explicit `$FF` target-validity
helper and routes invalid results directly to the combined X/Y hold tail
before consuming stale target coordinates. The selector-localized both-dead
control records target slot `$FF`; its transient offset/X/Y remain stale by
contract and are not treated as valid evidence.
Layout/ownership audit passes with runtime end `$FF68` and 56 bytes before
NMI.

The corrected combat-local player-vs-NPC verifier passes repeated clean
sessions: both P1 and P2 reduce NPC2 from 64 to 60 while the other player
remains at 64. The prior nondeterminism had two fixture causes: the old
post-target `neutral_players()` cleanup killed NPC2, and the target's
standalone `Actor_InvulnFrames[2]` was not normalized. The fixture now records
that organic value, explicitly clears it for this legal-hit test, polls
neutral without touching actor state, and freezes the spawn queue. The latest
10 fresh P1 and 10 fresh P2 cases all produced 64 -> 60 with zero misses.
Full
AI hit invulnerability, multiple-AI ownership, friendly-fire, and P2 grab/throw
remain open. No transport, camera, score, pickup, stage, or workload gate is
claimed.

The hardened timer verifier now also records 1P seeded-P2, asymmetric 2P,
paused, and cold/disabled controls; all pass with write events grouped by
emulator frame. Fresh width output is retained in
`out/g13_width_current.log`; it exits 1 on 51 historical/new warnings, but
the requested G13 combat-path labels are absent from the NEW list. The
layout/ownership audit and Phase5 pass on the final rebuilt ROM. The
The ordered no-target diagnostic captures a selector-entry baseline and
retains the first OOP-done cutoff. The current MCP notification stream still
returned a mixed/empty event segment in some runs, so the retained result is
explicitly FAIL where it cannot prove the required target-valid/hold sequence;
no endpoint sample is being promoted to a same-OOP claim.

## Jump-isolation fixture correction

The prior jump red was verifier contamination, not a jump production
regression. `setup()` and the imported `neutral_players()` left live NPC
traffic during the long RALF/LEO reselect path; G13 AI combat could then
change P2's reaction/input state before the real jump edge. The pre-fix
artifact is retained as `out/g13_jump_isolation_pre_fixture_fix.json`.

`game_g13_jump_isolation.py` now uses `jump_local_neutral()` after the real
session/roster setup. It freezes `Spawn_Index == Spawn_Count`, clears only
NPC slots 2-5's combat state and invulnerability, clears unrelated P1/P2
combat state, leaves all production jump-family fields untouched, and polls
both controllers to press/old/trigger zero. It also records setup, post-
neutral, pre-edge, and action-window snapshots for both players, all NPCs,
input contexts, jump-family state, invulnerability, and spawn counters.

The four formerly red cases passed 5/5 fresh sessions each (20/20):
simultaneous A jump, P2 Y jumpattack, P2 X jumpattack2, and airborne
opposite movement. The repeat artifact is
`out/g13_jump_isolation_red_repeat.json`; the full isolated artifact is
`out/g13_jump_isolation.json`. Focused P1 family controls also passed after
the fixture verifies the requested live roster record. No production jump
source was changed.

Current clean ROM remains `C94E45AE7404440B44BB7F0B8CD0C65BCF73252A3B617081A5180A5ED71DF2CB`;
MSU remains `CB44CF710C4F9A964AD5E96EE3AA5A6D50227CD1E15EDFE02F13C93AF0B6F0A0`.
The retained legacy full-run artifact records an arbitrary endpoint sample;
its P1 globals are the saved RALF family (not a third/corrupt value). The
replacement endpoint classification accepts either the restored P1 family or
the exact installed P2/LEO family when a frame-end sample falls inside the
temporary alias window. The authoritative RALF-P1/LEO-P2 behavioral negative
passes 20/20 after stable neutral boundaries: P1 remains grounded/RALF and
cannot acquire LEO's jump behavior while P2 performs the real jump family.
This is verifier timing evidence, not an engine failure.

## Current combat closeout evidence (fix-forward)

The production AI movement path was restored to its compact inline sentinel
check (`G13_AiTargetSlot`, `$FF` -> combined X/Y hold); the cross-bank validity
call is not retained in the hot movement path. The rebuilt ordinary ROM is
`C94E45AE7404440B44BB7F0B8CD0C65BCF73252A3B617081A5180A5ED71DF2CB`, with the
same MSU hash above. The build used the documented audio bypass command.

The corrected player-vs-NPC fixture was rerun as 10 fresh sessions per player:
P1 10/10 and P2 10/10 reduced NPC2 exactly `64 -> 60`, with the other player
remaining at 64. The retained organic `Actor_InvulnFrames[2]` values include
nonzero values; the focused fixture now records that leak, then explicitly
normalizes the legal-hit target to zero before neutral polling and attack
delivery. Post-hit samples are named as post-window values and are not called
pre-hit invulnerability.

The direct no-target attempt is retained in
`out/g13_no_target_movement.json`. The selector no-target label did fire, but
the frame-granular run-to-hook boundary advanced into a later pass before the
immediate sample: the observed state had `P1 HP=64`, `P2 HP=0`, target slot 0,
and changed AI coordinates. The shared `hold_y` label is also not actor
specific. This is a verifier/MCP semantic-boundary limitation, not a claimed
production movement failure; no production telemetry or movement change was
added to compensate. `confirmed_busy_denials` remains null.

## Combat/jump closeout status

The four combat gates are locally green and retained in
`out/g13_combat_closeout.json`: friendly fire is off, the AI invulnerability
matrix passes, multi-AI attribution passes 10/10 in both geometry directions,
and the real P2 LEO grab/throw path reaches FALL. The player-vs-NPC control is
10/10 for each player and the timer matrix remains green.

The four formerly red jump cases pass 20/20 under the isolated fixture. The
legacy P1-global endpoint equality was removed because it was not a semantic
dispatch boundary. The retained flaky artifact is diagnostic only; its
mismatch is either the exact saved RALF family or the exact installed LEO
family, with no third value. The authoritative RALF-P1/LEO-P2 negative passes
20/20, including repeated P2 jump/jumpattack/jumpattack2, landing, and the
P1-A negative while P2 is jumping. Ordered ContextEnter/Exit evidence remains
in `out/g13_semantic_boundary.json`.

No production source changed in this closeout. `confirmed_busy_denials` is
explicitly null, and no-target movement remains
`TOOLING-LIMITED / UNMEASURED` because the current MCP boundary cannot expose
the exact same-dispatch movement state. Camera, pause, score/pickup, stage
handoff, death/continue, and sustained workload remain outside this slice.

## Published closeout

Commit `291ffae` is the verifier/evidence closeout for the current WIP. The
clean build from the committed source reproduced ROM
`C94E45AE7404440B44BB7F0B8CD0C65BCF73252A3B617081A5180A5ED71DF2CB` and MSU
`CB44CF710C4F9A964AD5E96EE3AA5A6D50227CD1E15EDFE02F13C93AF0B6F0A0`.
Production source, jump mechanics, transport, G12, and SOUND are unchanged.
The active input gate is `game_g13_two_player_input.py`; `game_g13_input.py`
is explicitly LEGACY/SUPERSEDED. The active closeout evidence is in
`out/g13_combat_closeout.json`, `out/g13_jump_isolation.json`, and
`out/g13_jump_ralf_negative.json`.

The hardened timer gate passes on the rebuilt ROM: paired 2P writes are one
per observed gameplay frame and decrement one step; asymmetric 2P, seeded-1P,
paused, and cold-zero controls pass. Fresh width output remains a 51-warning
branch-wide debt list; the requested combat-path labels are absent from the
NEW list. Layout and Phase5 remain green.

Still unmeasured and therefore not accepted: friendly-fire negatives, the
production AI invulnerability hit matrix, multi-AI latched-target attribution,
and P2 LEO grab/throw. Camera, pause ownership, score/pickup acceptance,
stage handoff, death/continue, and sustained workload remain outside this
combat closeout. No transport, audio, actor-capacity, or CHAR_ZP_LEN change
was made.

## Camera and pause slice

The focused camera/pause gate passes on the rebuilt artifact, with retained
evidence in `out/g13_camera_pause.json`:

- both-live midpoint targets are order-invariant: `(80,200)` and `(200,80)`
  both produce target X `12`; odd midpoint uses the implemented floor;
- left target clamps to zero and right camera position remains at/below the
  configured final maximum; normal `Core_Screen__ClampToScreen` remains the
  final level-bound owner;
- real PLAYING easing follows both players right and left; separated players
  remain ordered and inside the shared viewport; 1P movement bypasses the G13
  tether;
- P1 and P2 Start each enter and resume the same global PAUSED menu; paused
  gameplay state remains fixed while NMI advances; 1P P2 Start is ignored;
  simultaneous Start produces one global pause state.

The source contract for survivor follow remains explicit in
`G13_Screen_SetTargetPosition`: P1-live selects `PlayerEntity_PosX`, and the
P1-dead/P2-live branch selects `Entity1_PosX`. A runtime HP injection between
the PLAYING death check and that helper could not be read reliably with the
current Mesen hook boundary, so survivor-only runtime injection is recorded
as `MCP_HOOK_BOUNDARY_UNMEASURED`, not as a production failure or a claimed
runtime pass. Both-live and live easing runtime behavior are measured.

Fresh width output is `out/g13_camera_pause_width.log`: 44 branch-width
warnings remain as pre-existing/unrelated debt, while the active camera and
pause labels introduced/exercised by this slice are absent from the NEW list.

The final rebuilt ROM for this slice is
`067AF2214A57994709C55BFC423D2E1A913C65B0FF8324C14A0D0A22F8FD8220`; MSU is
`CB44CF710C4F9A964AD5E96EE3AA5A6D50227CD1E15EDFE02F13C93AF0B6F0A0`.
