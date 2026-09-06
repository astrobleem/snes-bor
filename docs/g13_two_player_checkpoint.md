# G13 two-player first-slice WIP checkpoint

Status: WIP review publication; not accepted and not merge-ready.

Parent/source commit: `3c0a75c6c303e383ec71f31f3baa6da3f407c8f0` on
`g13-two-player`. Published WIP source/evidence commits are
`4f8552a60f3d9fba9c3627d3c8110d4352d9da6b` and
`423399e687cf7e4c1a26e7e1b41827776b6cbeb1`, and
`ce5f3d8987ef9742500e3544ac66672dd0f81e09`; this fix-forward is the
jump-isolation review slice.

## Artifacts

- ROM: `E:\gh\snes-bor-g13\distribution\bor.sfc`
- ROM SHA-256: `0AE3143CBB4C2BF3B192D0D2E992053160A70C626E65E07FFE7A9B2C65DFA088`
- MSU: `E:\gh\snes-bor-g13\distribution\bor.msu`
- MSU SHA-256: `CB44CF710C4F9A964AD5E96EE3AA5A6D50227CD1E15EDFE02F13C93AF0B6F0A0`
- Build: `python -c "import build_rom; build_rom.build_audio.main=lambda:0; raise SystemExit(build_rom.main())"`
- Layout: `python tools\\rom_audit\\verify_layout.py src\\main.pasm src\\main.sym`
- Semantic probe: `python -u tools\\verify\\game_g13_semantic_boundary.py`
- Jump probe: `python -u tools\\verify\\game_g13_jump_isolation.py`
- P2 session: `python -u tools\\verify\\game_g13_p2_session.py`
- Input: `python -u tools\\verify\\game_g13_input.py`
- One-player capacity: `python -u tools\\verify\\game_g13_one_player_capacity.py`

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
- `python -u tools\\verify\\game_g13_input.py`: independent JOY1/JOY2
  edge proof and synchronized joint hardware edge PASS. The joint case
  installed `hold_input(BTN_X, port=0)` and `hold_input(BTN_A, port=1)`
  before one `run_frames_exact(1)`; raw JOY values were `0x0040` and
  `0x0080`, with matching independent triggers.
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
