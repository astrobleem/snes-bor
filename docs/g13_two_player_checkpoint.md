# G13 two-player first-slice WIP checkpoint

Status: WIP review publication; not accepted and not merge-ready.

Parent/source commit: `67f0ef14d12b1bf2ee9843d9b80dd994d397e36d` on
`g13-two-player`. Published WIP source/evidence commits are
`4f8552a60f3d9fba9c3627d3c8110d4352d9da6b` and
`423399e687cf7e4c1a26e7e1b41827776b6cbeb1`; the latter is the current
published source SHA.

## Artifacts

- ROM: `E:\gh\snes-bor-g13\distribution\bor.sfc`
- ROM SHA-256: `7012DC5C1A497261F59CED00A8F76D0ABC4CCCE0A0D0B25C0079279D933B8895`
- MSU: `E:\gh\snes-bor-g13\distribution\bor.msu`
- MSU SHA-256: `CB44CF710C4F9A964AD5E96EE3AA5A6D50227CD1E15EDFE02F13C93AF0B6F0A0`
- Build: `python -c "import build_rom; build_rom.build_audio.main=lambda:0; raise SystemExit(build_rom.main())"`
- Layout: `python tools\\rom_audit\\verify_layout.py src\\main.pasm src\\main.sym`

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
  and attack cases pass when each edge is delivered independently.

Known red gate, reproduced by:

`$s='E:\\gh\\Mesen2\\bin\\win-x64\\Release\\settings.json'; $b=[IO.File]::ReadAllBytes($s); try { $t=[Text.Encoding]::UTF8.GetString($b); $i=$t.IndexOf('"Port2"'); $j=$t.IndexOf('"Type": "None"',$i); $t=$t.Remove($j,18).Insert($j,'"Type": "SnesController"'); [IO.File]::WriteAllText($s,$t,(New-Object Text.UTF8Encoding($false))); python -u tools\\verify\\game_g13_two_player_input.py } finally { [IO.File]::WriteAllBytes($s,$b) }`

The failing assertion is `simultaneous distinct attack edges remain
distinct`. After replacing sequential neutral pulses with a synchronized
two-port neutral hold, the latest retained sample was:

`SIMULTANEOUS_ATTACK (2, 0, '004000400000', '004000400000', '00400040')`

where the tuple is P1 selected, P2 selected, P1 press/trigger/old, P2
press/trigger/old, and the two raw-latch words. Both raw words are the
expected Y value (`0x4000`) and both trigger contexts are present in the same
BOR update, but only P1 enters attack state. This localizes the current red
gate past controller delivery and before successful P2 action entry. The
separate synchronized hardware control passes, and independent attack
controls pass in fresh sessions.

The old all-zero tuple occurred before the synchronized neutral correction
and is retained only as historical verifier evidence, not as the current
classification.

The old outer-session action attempts were contaminated by repeated reset and
input setup; those are not used as acceptance evidence. No production combat
or transport change was made to hide this red result.

## Explicit nonclaims

This WIP does not claim a complete two-player slice, jump isolation,
friendly-fire proof, AI hit attribution, camera/pause, score/pickup,
stage-handoff, or a valid continuous 600-frame two-player workload. It also
does not claim `confirmed_busy_denials`; that remains unmeasured/null.

Protected audio files and unrelated dirty files are excluded from the WIP
publication.
