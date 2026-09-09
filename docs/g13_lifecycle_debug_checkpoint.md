# G13 lifecycle / stage-transition debug checkpoint

Status: WIP advisor checkpoint; not acceptance and not a merge. This document
freezes the current local evidence without continuing root-cause debugging.

## Repository and artifacts

- Canonical worktree: `E:\gh\snes-bor-g13`
- Branch: `g13-two-player`
- Pre-checkpoint HEAD: `e70aac1beb86321a9d51d5c61bd6fa30836970d1`
- Upstream tracking ref: none configured locally
- Current production ROM: `distribution\bor.sfc`, SHA-256
  `E60148CA9A8C57D0CE68831E3651CDD27D3404B24146D8A7240CC571956FD617`
- Current MSU: `distribution\bor.msu`, SHA-256
  `CB44CF710C4F9A964AD5E96EE3AA5A6D50227CD1E15EDFE02F13C93AF0B6F0A0`
- `git diff --check`: passes; Git reports only its normal LF/CRLF warnings.

The generated tracked evidence currently has these hashes:

| Artifact | SHA-256 |
|---|---|
| `src/main.bin` | `AD714597A162AD22C63A5EA6808AF15EF280213B6FFD95EEE2909ADC607A72DA` |
| `src/main.pansy` | `5F76B39625410E1D08409E73560F76453EF5224A6F8DFF1D493B3F72A0FA0679` |
| `src/main.sym` | `B44E96ECD45D9E2EFC7F7ABD0E2E18050BDE9EF945F45F837EE95616EF70B6CC` |

The PAK inputs are already present at the required ignored root paths. The
authoritative copies found under `E:\gh\snes-bor` match byte-for-byte:

| PAK | Size | SHA-256 | Status |
|---|---:|---|---|
| `Beats of Rage Original [v.3.0 Build 4086].pak` | 62,663,611 | `A2A55CDD5E1145E845607ECEC3AD85A342529492E7120449A928F3A6EAEA81D6` | ignored |
| `Teenage Mutant Ninja Turtles [v.3.0 Build 4153].pak` | 34,357,090 | `F9AB7A086263F9E9E5D439388B2F69C85B4F054B1663E4F3F2B81DC6A951E182` | ignored |

No PAK was copied or staged in this checkpoint. The current required paths
are the same root-relative filenames under `E:\gh\snes-bor-g13`.

## Current implementation

The local production implementation includes changes in `src/main.pasm`,
`src/core/game_state.pasm`, `src/core/input.pasm`, `src/core/nmi.pasm`,
`src/core/pausemenu.pasm`, `src/core/player2_context.pasm`, and
`src/core/spawn.pasm`; generated `src/main.bin`, `src/main.pansy`, and
`src/main.sym`; and the G4 verifier `tools/verify/game_g4_transition.py`.
The local lifecycle verifier additions are listed in the machine-readable
artifact and are staged selectively with this checkpoint.

Accepted targeted behaviors include P2 HP/lives eligibility, P2 respawn and
OUT handling, P1 survivor behavior, owner-local pause/continue, wrong-
controller rejection, organic GAMEOVER in both death orders, owner-specific
GAMEOVER continues, simultaneous Start precedence/revival, timeout to TITLE,
and session teardown. These are locally proven targeted behaviors, not a
claim that the complete publication matrix is accepted.

Local fixes represented here are:

1. 1P slot-1 lifecycle gating.
2. P2 living-death eligibility HP guard.
3. Shared both-OUT predicate explicit A8 contract.
4. GAMEOVER timeout reload of TITLE after the session-disable helper.
5. Compact NMI Stop/Start shadow-plus-hardware contract.
6. Layout-preserving removal of the unmatched outer PHD in
   `G13_ClearOldStageActors`.
7. Caller-P preservation in `G13_ReapplyP1Out` and `G13_ReapplyP2Out`.

The compact NMI contract writes the shadow before `$4200`: Stop selects `$01`
(auto-joypad on, NMI off), Start selects `$81` (auto-joypad on, NMI on), and
the shared setter performs `STA.L Nmi_InterruptFlags`, `STA $4200`, `PLP`,
`RTS`.

## G4 status

Normal G4 functional products and the corrected 2P semantic handoff pass in
the current ROM: stage index/data, palette, width, frontpanel, spawn data,
and NMI progress. The prior unresolved handoff was explained by two
production defects: an unmatched outer PHD shifted PLP/RTL by two bytes, and
the reapply helpers leaked A8 into the 1P caller and latent 2P PLA restore.

```text
00:DA51  JSL $07:86B6  G13_ClearOldStageActors
00:DA55  JSL $07:8656  G13_ReapplyP1Out
00:DA59  JSL $07:840C  G13_EnsureP2AfterStage
00:DA5D  LDA #$0000
00:DA60  STA.L $7E2750 Game_State
00:DA64  JMP stageclear_done

07:86B6 entry executes
07:8714 PLD executes
07:8715 PLP executes
07:8716 RTL executes
00:DA55, 07:8656, 07:840C, DA5D/DA60 and stageclear_done execute
Game_State becomes PLAYING ($0000)
```

The observed outer JSL frame is `$001FFA=$54`, `$001FFB=$DA`,
`$001FFC=$00`. Later NMI samples repeatedly observed `54 DA 00` at those
locations. Those bytes are not yet validly classified as an interrupted
foreground PBR:PC because the S value at NMI entry was not independently
established.

Current classification:

`G13/G4 lifecycle fixes locally green; focused acceptance remains scoped to
the listed regression matrix.`

The old post-RTL unresolved classification is retired. The internal
`G13_EnsureP2AfterStage__done` hook is observer-unreliable in the 2P verifier,
but helper entry, caller continuation, PLAYING store, and state invariants
pass.

## Retired hypotheses

The following are retired for this issue unless new evidence is produced:

- StreamScroll branch-target Poppy #392 theory.
- Frontpanel branch-target theory.
- Bg_LoadScene theory.
- BG3-clear-loop theory.
- Stream-cache initializer theory.
- Active-NMI causality in G13 cleanup.
- Core_Nmi_Play inherited-D nonzero causality.
- Static G13 push/pop imbalance as an unproven hypothesis; replaced by the
  confirmed unmatched outer PHD defect and fixed.

## Emitted raw evidence

Current symbol/raw locations include:

```text
Stage_Load                         $00:DACF
Stage_Load__bg3_clear              $00:DB09
Stage_Load__skip_fp                $00:DB26
Stage_Load__fp_done                $00:DB28
Stage_Load__streaming              $00:DB44
Stage_Load__border_go              $00:DB4E
Core_Nmi_Play                      $00:D11A
Core_Nmi_Stop                      $00:D241
Core_Nmi_Start                     $00:D248
nmi_handler                        $00:FFA0
G13_EnsureP2AfterStage             $07:840C
G13_ReapplyP1Out                   $07:8656
G13_ClearOldStageActors            $07:86B6
G13_ClearOldStageActors__after_slot5 $07:8715
G13_ClearOldStageActors__one       $07:8717
```

Raw caller tail bytes are `22 B2 86 07 22 56 86 07 22 0C 84 07 A9 00 00 8F
50 27 7E 4C 19 DA`.

Raw G13 cleanup begins `08 0B E2 20 AF BD 26 7E D0 0F 0B  F4 85 0A 2B 20 13
87`; its final sequence is `2B 20 13 87 A9 00 8F B1 58 7E 2B  E2 20 0B F4
93 0C 2B 20 13 87 A9 00 8F B5 58 7E 2B 08 6B` (the routine's slot-body
continues between these excerpts; see `src/core/player2_context.pasm` and
`src/main.bin`/`src/main.sym` for the complete generated stream).

NMI raw bytes:

```text
D241 08 E2 20 A9 01 80 05
D248 08 E2 20 A9 81 8F 03 50 7E 8D 00 42 28 60
D11A C2 30 48 DA 5A 8B 0B E2 20 A9 00 48 AB ...
FFA0 20 1A D1 40
```

The NMI handler prologue/epilogue is represented by the current generated
symbols and source; no NMI source change is being proposed here.

## Toolchain and observer identity

- Poppy DLL used by `build_rom.py`: `E:\gh\poppy-astrobleem\src\Poppy.CLI\bin\Release\net10.0\poppy.dll`
- Poppy DLL SHA-256: `2FF9AEA492A8126737BF8F205A9964C6EA6AE7284AD72BBA28F118A173747918`
- Poppy repository HEAD: `ec005c196eedabf7d0c25ff6336398c427dd43ac`
- Build command: `C:\Program Files\dotnet\dotnet.exe <poppy.dll> src/main.pasm -s src/main.sym`, invoked by `build_rom.py`.
- Poppy #392 reference: `8ee859b33bad94e3a01e9c78026803e482292801`; the current BOR ROM was not built with that reference.
- Mesen executable: `E:\gh\Mesen2\bin\win-x64\Release\Mesen.exe`
- Mesen SHA-256: `66FC84E03481DEDC521B095D0AA3022297F09E48DDCC3B8BEABD019F96C0B268`
- Mesen2 HEAD: `5fb1f1b6cba1b9348b40ff2d03ae6e4afde16f63`; checkout is dirty in unrelated SPC/test-output paths.
- MCP package: `E:\gh\Mesen2\python\mesen_mcp`; source files include `session.py`, `tools.py`, `McpServer.cs`, and `McpTools.cs`.
- The MCP catalog exposes exec/write hooks, notifications/mesen/hookFired, memory reads, disassembly, trace logging, and `get_cpu_state`; the installed server used in the historical trace rejected `get_cpu_state` as an unknown tool. This discrepancy is retained for advisor review.

## Width and stack snapshot

The current width audit reports 1,788 labels, 180 baselined warnings, and 11
known unrelated NEW warnings; zero new G13/NMI warnings are present. The 11
known warnings are recorded in `out/g13_lifecycle_width_final_current.log`.

The static G13 cleanup ledger is balanced: outer JSL frame -3; PHP -1; outer
PHD -2; each slot net zero; final PLD +2; final PLP +1; RTL +3. Entry S was
observed as `$1FF9`. The ledger alone does not classify the live post-RTL
return behavior.

## Directory hygiene

No directory was created or deleted. `E:\gh\snes-bor-g13` is the only active
development worktree for this checkpoint. Existing registered diagnostic
worktrees remain untouched, including the byte-ladder set, G13 telemetry/
tailtrap/shadowoff/test-R/test-N directories, `snes-bor-g13-final`,
`snes-bor-g13-plan`, `snes-bor-known-good`, `snes-bor-production`, and
`snes-bor-review-build`. They are cleanup candidates for a separately
approved cleanup task, not this checkpoint.

Protected unrelated evidence/audio state was not cleaned, reset, stashed, or
blanket-staged. In particular `tools/audio/sfx_production_banks.json` and
`tools/audio/action_residency.json` were not modified by this task.

## Exact observer files

The checkpoint stages the existing G13/G4 observers without rewriting them:

```text
tools/verify/_harness.py
tools/verify/game_g4_transition.py
tools/verify/game_g13_camera_pause.py
tools/verify/game_g13_continue_semantic.py
tools/verify/game_g13_input.py
tools/verify/game_g13_phase5_lifecycle_diag.py
tools/verify/game_g13_p2_session.py
tools/verify/game_g13_stage_handoff_trace.py
tools/verify/game_g13_stage_lifecycle.py
tools/verify/game_g13_two_player_input.py
tools/verify/test_r_diag.py
```

The latest retained trace is in `out/g13_stage_transition_trace_current.txt`.
Temporary patched ROMs, PAKs, emulator binaries, large generated binaries,
old logs, and unrelated audio/combat evidence are intentionally excluded.
