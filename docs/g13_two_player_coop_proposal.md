# Provisional G13: bounded two-player co-op proposal

Status: proposal only. No co-op runtime, verifier, generated artifact, audio,
or shared-tool change is included in this document.

## Baseline and recommendation

The proposal is based on accepted G12 production commit
`836c0d4b1382420c30bf5849243b217a5a42e706`, ROM
`690F620E64D7645FCC750627C6A62C885D6527D1122C2795F6E1C8113A1C2C7A`, and
MSU `CB44CF710C4F9A964AD5E96EE3AA5A6D50227CD1E15EDFE02F13C93AF0B6F0A0`.
The final G12 checkpoint records six-actor lifecycle, presentation, stage,
and 600-frame workload acceptance. The single-buffer animation transport and
SOUND are closed and remain unchanged.

There is no Phase G13 in the current roadmap. This is a separately proposed
milestone, not a status claim. `tools/coverage_ledger/phase_status.json`
contains G1 through G11 only; §13 of `plan_game.md` is sequencing guidance.

Recommended first implementation slice:

* establish a two-player session before gameplay starts;
* retain player 1 in slot 0 and reserve slot 1 for player 2;
* restrict production NPC allocation to slots 2–5, for four NPCs maximum;
* give each player an independent controller edge/held state and player
  dispatch path;
* use one shared camera, shared score/lives policy, friendly fire off, and
  the existing six-actor rendering/animation allocation;
* exclude both player slots from enemy counts, group waits, and completion;
* exclude mid-game joining, split-screen, a new character-capacity pass,
  transport changes, and title-boot policy changes.

This fixed-session slice is the smallest coherent proof that two actors are
actually independently controlled. It intentionally does not claim full
co-op until death/continue, selection, pause, all combat interactions, and
content-wide behavior are separately proven.

## Current dependency map

| Area | Current source and labels | Reusable behavior | Required co-op work / open point |
|---|---|---|---|
| Controller input | `src/core/input.pasm:Core_Input_Poll`, `Input_press`, `Input_old`, `Input_trigger` | Poll/edge-detector mechanics and button masks | Current state is one global JOY1 record. Add a bounded P1/P2 input context, likely JOY1 `$4218` and JOY2 `$421A`, then pass/select the context for the actor being updated. The second-pad hardware and existing Mesen delivery path need a focused proof before implementation. |
| Player identity | `src/main.pasm:PlayerEntity_*`; `src/core/game_state.pasm:Game_State_RespawnPlayer`, `Game_State_HandlePlayerDeath` | Slot-0 semantics for P1 | Keep slot 0 as P1. Add explicit P2 identity/state rather than relabeling P1 aliases. Decide whether P2 has independent lives/continue or shares the session pool. |
| Actor storage | `src/main.pasm:CHARACTER_ACTOR_COUNT`, `CharacterEntity_Init`, `CharacterEntity_Play` | Six 133-byte character windows and generic OOP dispatch | Existing capacity is sufficient: convert slot 1 from NPC to a second input-driven player before the spawn queue starts. Do not create a seventh actor or an ECS. |
| Allocation/reuse | `src/core/spawn.pasm:Spawn_Play`, `Spawn_Play__find_slot`, slot handlers, `Spawn_Index`, `Spawn_Count` | Existing bounded initialization, roster, boss, prop, and reuse paths | Reserve slot 1 permanently for P2 in this mode. Free-slot, death/reuse, prop, boss, and spawn initialization scans must target only slots 2–5. |
| AI and targeting | `src/main.pasm:CharacterEntity_Play`; `src/core/vm/vm_native_engine.pasm:Character_HitApply_VsAllGeneric`, `Character_HitApply_VsPlayer` | Per-actor AI update and indexed collision paths | Player attacks must target NPC slots only. AI must choose from both live players according to a deterministic nearest/priority rule. Friendly fire is proposed off. |
| Attack input | `src/main.pasm:Anim_Play`, `Character_PlayFrame`; `src/core/jump.pasm:Jump_PlayerInputGate` | Existing attack, jump, special, grab, and throw state machines | Route the active player's context instead of global `Input_*`. Preserve P1 behavior byte-for-byte where possible; give P2 equivalent gates and a separate jump/special state. |
| Grab/throw | `src/core/vm/vm_native_engine.pasm:Character_Grab_SlotToOffset`, `Character_Grab_Play`, `Character_Throw_Play` | Slot-ID links, reciprocal link clearing, follow/release/throw lifecycle | Slot IDs already fit six actors. Target filters and player ownership must permit P2/NPC links while rejecting player-to-player grabs if friendly interaction is not approved. |
| Character loading | `src/core/charselect.pasm`, `src/main.pasm:Anim_LoadCharacter`, `Game_State_CharSelect_ReloadPlayer` | MSU character loader, palette/tile setup, pre-game load | Current selection/load gate is singular and targets P1. For the first slice, use a fixed P2 roster identity selected before PLAYING, or a two-step pre-game selection screen. Do not imply dynamic mid-game reselect. |
| Camera | `src/core/screen.pasm:Core_Screen__SetTargetPosition`, `Core_Screen_Focus` | Clamp, streaming watermark, and stage-edge handoff | Current camera follows one focused OOP handle. Recommended policy is a bounded midpoint of the two players, clamped to the stage and retaining the accepted stream-scroll contract. Exact dead-player and separation behavior needs approval. |
| Enemy/completion | `src/core/spawn.pasm:Spawn_Play` wait/group scans; `src/core/vm/vm_native_engine.pasm:Game_State_AnyActorAlive`; `src/core/game_state.pasm` stage logic | Existing exhausted-queue and alive-NPC contract | Count only combat actors in slots 2–5. Both player slots are always excluded; props remain non-blocking. Prove last NPC in slot 5 blocks completion until death, then camera unlock and real transition occur. |
| HUD/boss | `src/main.pasm:Hud_Play`; `src/core/hud_boss.pasm:Hud_Play__boss_bar`; `PlayerEntity_Hp`, `Game_Lives` | Existing player bar, score/lives, and boss bar DMA | HUD is single-player (`PlayerEntity_Hp`, `Game_Lives`); boss-bar source checks only the older slots 1–3. Co-op needs two player bars and an NPC-only boss scan over slots 2–5. Shared score/lives is recommended for the first slice, pending approval. |
| Score/pickups | `src/main.pasm:Game_Score_Award`; `src/core/jump.pasm` pickup paths | Existing score award and break/reveal/collection behavior | Recommended shared score and reward ownership by the collecting player only for attribution. Define whether lives are shared before implementation; do not silently retain P1-only ownership. |
| Pause/reset | `src/core/pausemenu.pasm`; `src/core/game_state.pasm:Game_State_NewGameReset`; `src/core/charselect.pasm` reset path | One global pause and new-game lifecycle | Shared pause is recommended: either controller's Start edge pauses. Reset must clear both input contexts, both player records, and reserve slot 1 again. |
| Rendering | `src/core/depth_sort.pasm:EntityDpBaseTable`, `Character_RenderPass`; `CHAR_TILE_COLUMN`, `CHAR_PALETTE_SLOT` in `src/main.pasm` | Six-slot depth traversal and accepted OAM/OBJ mapping | Reuse slot ownership: P1 `$00`, P2 `$04`, NPC slots 2/3 `$08/$0C`, slots 4/5 `$20/$21`; palettes 0–5. Prove actor identity remains distinct from roster identity and OAM order. |

## Hardware and memory implications

The six character windows are 133 bytes each. Their current DP bases are
`$0A00`, `$0A85`, `$0B0A`, `$0B8F`, `$0C14`, and `$0C99`, represented by
`EntityDpBaseTable`/`EntityOffsetTable`. P2 consumes the already allocated
slot-1 window; NPC capacity falls from five to four. No new character struct
or actor base is needed. Any extra P2 input/jump state must be allocated only
after auditing the existing fixed WRAM/scratch ownership and fixed layout
guards.

The accepted OBJ layout already fits six actors. The existing six mappings
use tile columns `$00,$04,$08,$0C,$20,$21`, and the accepted G12 source uses
six OBJ palette slots. OAM has 128 entries; six character entries are not a
hardware limit. P2 therefore reuses slot 1's tile and palette ownership. The
renderer, padding initialization, and row-DMA destination must continue to
derive from the actor slot allocation, never from roster identity.

The single animation staging buffer, one-frame stream admission, DMA queue,
background streaming, and NMI budget remain the accepted production design.
Two players plus four NPCs is still six total actors, so this proposal makes
no performance promise beyond reproducing the accepted six-actor control.
`confirmed_busy_denials` remains unmeasured/null in the G12 baseline; a future
co-op proof must not turn inferred waits into confirmed denials.

## Acceptance gates for the first slice

1. **Session setup and ownership.** From a clean new game, establish exactly
   two input-driven players in slots 0 and 1, four production NPC slots 2–5,
   distinct roster identities, correct six actor bases, tile columns,
   palettes, and OAM entries. No spawn record may overwrite slot 1.
2. **Independent input.** With a released-input poll between edges, P1-only
   movement, P2-only movement, simultaneous different directions, and
   independent attack/jump/special/grab edges must affect only the intended
   actor. Record raw controller values, per-player press/old/trigger, the
   consuming update, and actor-specific state changes. Two sprites responding
   to one global edge is a failure.
3. **Presentation.** For both player actors and NPCs, match an identified
   completed upload to its source bytes and destination, including transparent
   padding, facing, palette, and neighboring-pixel protection. Verify depth
   ordering, equal-depth tie behavior, jump/landing, and camera clamp.
4. **Combat and links.** Each player independently damages NPCs; AI can attack
   either valid player; friendly fire is absent under the proposed policy.
   Prove P2-to-NPC grab/follow/release/throw and reciprocal slot-ID links,
   including timeout, death, and reuse. A player must not write another
   player's state through a stale link.
5. **Production spawn/completion.** Reach four NPCs through `Spawn_Play`,
   distinguish props from enemies, exercise slot 4/5 death and reuse, retain
   metadata isolation, and prove the last enemy in slot 5 blocks completion.
   After its real combat death, prove `Stage_Cleared`, camera unlock, true
   right-edge travel, `Stage_LoadPending`, and next-stage loading.
6. **Player lifecycle.** Prove both players' HP, hit-stun, death/respawn,
   score/lives ownership, pause, and new-game reset. The first slice may use
   shared lives only if that policy is approved and explicitly tested.
7. **Performance regression.** Run the accepted continuous 600-frame
   workload with two live players plus four live NPCs in one session, using
   six verified 100-frame chunks. Report active counts by slot, presented
   poses/source matches, DMA high-water, NMI 1:1, overruns, and gameplay rate;
   compare to the accepted one-player six-actor result.

## Gates still required for full co-op

Full co-op must additionally prove both-player character selection and
reselection policy, independent death/continue semantics, all stage/boss/HUD
content, every pickup ownership rule, pause from each controller, all attack
variants and special routes for both players, every collision boundary, all
spawn/wait/group/prop cases, repeated stage transitions, reset/title/ending
behavior, and long-run presentation on the complete shipped roster. Mid-game
joining is explicitly a nonclaim of this first slice. Split-screen, multitap,
SA-1 work, transport/cache/fairness changes, additional actor capacity, and
audio changes are also nonclaims.

## Decisions requiring advisor approval

1. Approve slot 1 as the permanently reserved P2 slot, with NPCs limited to
   slots 2–5.
2. Choose fixed pre-game P2 roster identity for the first slice (recommended)
   versus building a two-step dual character-selection flow immediately.
3. Approve JOY2/$421A as the P2 source after a focused hardware/input proof.
4. Approve shared midpoint camera, friendly-fire-off targeting, and shared
   score/lives for the first slice; decide the policy when one player dies.
5. Confirm whether either controller may pause, or P1 alone owns pause.

The source-backed prerequisite before implementation is approval of these
policies plus the bounded JOY2 delivery proof. No new shared armory tooling
is proposed: the existing input/debugger capability should be audited and
reused first.

## Explicit nonclaims

No two-player co-op runtime exists in this branch. Independent input,
P2-specific presentation, P2 lifecycle, co-op targeting, shared camera/HUD,
and two-player stage completion are untested. G12 one-player six-actor
production, SOUND, the single-buffer transport, and accepted evidence remain
the baseline and are not modified by this proposal.
