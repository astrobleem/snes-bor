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
* use one shared camera and the existing six-actor rendering/animation
  allocation; score/lives, friendly fire, and death policy remain decisions,
  not defaults;
* exclude both player slots from enemy counts, group waits, and completion;
* exclude mid-game joining, split-screen, a new character-capacity pass,
  transport changes, and title-boot policy changes.

This fixed-session slice is the smallest coherent proof that two actors are
actually independently controlled. It intentionally does not claim full
co-op until death/continue, selection, pause, all combat interactions, and
content-wide behavior are separately proven.

The first slice is one fixed-session combat run on one existing stage. Its
entry condition is both players loaded before `PLAYING`; its exit condition is
the ordinary completion/next-stage handoff for that stage. It does not add a
new title flow, permit a player to join after the stage begins, or claim that
either player can independently continue after death. Those are later gates,
not hidden requirements of the initial proof.

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
| Character loading | `src/core/charselect.pasm`, `src/main.pasm:Anim_LoadCharacter`, `Game_State_CharSelect_ReloadPlayer` | MSU character loader, palette/tile setup, pre-game load | Current selection/load gate is singular and targets P1. First slice uses fixed preselected P2 roster identity before PLAYING; dual selection and dynamic reselect are later work. |
| Camera | `src/core/screen.pasm:Core_Screen__SetTargetPosition`, `Core_Screen_Focus` | Clamp, streaming watermark, and stage-edge handoff | Current camera follows one focused OOP handle. Recommended policy is a bounded midpoint of the two players, clamped to the stage and retaining the accepted stream-scroll contract. Exact dead-player and separation behavior needs approval. |
| Enemy/completion | `src/core/spawn.pasm:Spawn_Play` wait/group scans; `src/core/vm/vm_native_engine.pasm:Game_State_AnyActorAlive`; `src/core/game_state.pasm` stage logic | Existing exhausted-queue and alive-NPC contract | Count only combat actors in slots 2–5. Both player slots are always excluded; props remain non-blocking. Prove last NPC in slot 5 blocks completion until death, then camera unlock and real transition occur. |
| HUD/boss | `src/main.pasm:Hud_Play`; `src/core/hud_boss.pasm:Hud_Play__boss_bar`; `PlayerEntity_Hp`, `Game_Lives` | Existing player bar, score/lives, and boss bar DMA | HUD is single-player (`PlayerEntity_Hp`, `Game_Lives`); boss-bar source checks only the older slots 1–3. Co-op needs two player bars and an NPC-only boss scan over slots 2–5. Score/lives is unresolved, not a convenient default. |
| Score/pickups | `src/main.pasm:Game_Score_Award`; `src/core/jump.pasm` pickup paths | Existing score award and break/reveal/collection behavior | Current score is global and pickup effects are actor-triggered. Shared score, per-player score, and reward ownership are policy decisions; no adaptation is selected here. |
| Pause/reset | `src/core/pausemenu.pasm`; `src/core/game_state.pasm:Game_State_NewGameReset`; `src/core/charselect.pasm` reset path | One global pause and new-game lifecycle | Pause ownership is unresolved; either-controller pause is only a proposed adaptation. Reset must clear both input contexts, both player records, and reserve slot 1 again. |
| Rendering | `src/core/depth_sort.pasm:EntityDpBaseTable`, `Character_RenderPass`; `CHAR_TILE_COLUMN`, `CHAR_PALETTE_SLOT` in `src/main.pasm` | Six-slot depth traversal and accepted OAM/OBJ mapping | Reuse slot ownership: P1 `$00`, P2 `$04`, NPC slots 2/3 `$08/$0C`, slots 4/5 `$20/$21`; palettes 0–5. Prove actor identity remains distinct from roster identity and OAM order. |

## Persistent state and hardware implications

The six character windows are 133 bytes each. Their current DP bases are
`$0A00`, `$0A85`, `$0B0A`, `$0B8F`, `$0C14`, and `$0C99`, represented by
`EntityDpBaseTable`/`EntityOffsetTable`. P2 consumes the already allocated
slot-1 window; NPC capacity falls from five to four. No new character struct
or actor base is needed. Any extra P2 input/jump state must be allocated only
after auditing the existing fixed WRAM/scratch ownership and fixed layout
guards.

The accepted OBJ layout already fits six actors, but two units must not be
conflated. `CHAR_TILE_COLUMN` is the encoded DMA allocation index, while the
OAM base tile is the hardware tile number derived from it:

| Actor slot | `CHAR_TILE_COLUMN` | row-0 DMA byte base | OAM base tile (`column * 4`) |
|---:|---:|---:|---:|
| 0 | `$00` | `$8000` | `$00` |
| 1 | `$01` | `$8080` | `$04` |
| 2 | `$02` | `$8100` | `$08` |
| 3 | `$03` | `$8180` | `$0C` |
| 4 | `$20` | `$9000` | `$80` |
| 5 | `$21` | `$9080` | `$84` |

The six mappings use OBJ palette slots 0–5. OAM has 128 entries; six
character entries are not a hardware limit. P2 therefore reuses slot 1's
tile and palette ownership. The renderer's OAM tile field must use the OAM
base-tile value, while animation row DMA uses `CHAR_TILE_COLUMN * $80` in
VRAM byte units. Roster identity selects source data only; it never selects
a tile allocation.

There is a concrete persistent-state hazard. `Anim_LoadCharacter` copies the
currently loading `CHAR_INPUT_DRIVEN==1` actor's jump-family metadata into
the global `Player_JumpFCount`, `Player_JumpDelay`, `Player_JumpAttack*`,
`Player_JumpBase*`, and `Player_JumpAnimMode` cells at `$7E27BC..$7E27CA`
and `$7E27DA`. Loading P2 after P1 would overwrite P1's jump command/base
state (and vice versa). The existing per-actor fields are the right storage:
`CHAR_THROW_ZPOS`/`CHAR_THROW_ZVEL` at offsets 67/69 hold height and velocity,
`CHAR_SPECIAL_FCOUNT`/`DELAY`/`BASE` at offsets 71–75 hold special metadata,
and the remaining jump/attack frame/base fields already live in each 133-byte
character record where defined. The first implementation must make the jump
family counts/delays/bases and `CHAR_*` animation mode actor-local, reusing
those fields rather than adding a second global P2 copy.

The budget is zero additional character windows, zero additional OAM entries
beyond the existing six, zero additional palettes, and no new animation
staging buffer. The only new persistent state is two-controller input context
plus any actor-local jump mode byte missing from the existing record. A
The concrete new-state budget is 6 bytes for P2 press/old/trigger (three
16-bit values), plus 0 bytes for actor metadata if the existing per-actor
fields are reused; reserve at most 1 additional byte only as a measured
contingency for a missing per-actor jump animation mode. Thus the design
budget is 6 bytes normally, 7 bytes maximum, outside the character windows.
The final placement is not approved until
`src/core/allocate_wram.pasm` and its fixed layout guards prove a nonoverlap;
no address is invented here. `Player_Jump*` may remain a compatibility view
for slot 0 during transition, but cannot be ownership storage for either
player.

The single animation staging buffer, one-frame stream admission, DMA queue,
background streaming, and NMI budget remain the accepted production design.
Two players plus four NPCs is still six total actors, so this proposal makes
no performance promise beyond reproducing the accepted six-actor control.
`confirmed_busy_denials` remains unmeasured/null in the G12 baseline; a future
co-op proof must not turn inferred waits into confirmed denials.

## Source-backed gameplay semantics and proposed adaptations

The repository's BOR/OpenBOR-derived implementation notes and converters are
the authority for current semantics: `src/core/spawn.pasm` documents the
`TYPE_ENEMY`-style exclusion of props and the `Spawn_Play` wait/group
algorithm; `tools/bor_converter/spawn_parse.py` and `build_spawn_table.py`
consume shipped stage spawn records; and `pack_msu_roster.py` plus
`entity_parse.py` establish numbered attacks, `ANI_GET` pickup behavior,
`ANI_SELECT`, and character-specific action availability. The SNES routines
cite corresponding OpenBOR `engine/openbor.c` paths, including `count_ents`,
`player_think`, `perform_atchain`, `drawstatus`, and pause/continue handling.
These are source and shipped-content dependencies, not claims that co-op
behavior already exists.

The current adaptation has one P1: AI attacks target slot 0 in
`Character_HitApply_VsPlayer`; player attacks use the indexed all-entity path;
`Game_Score_Award` writes one global score; `Game_Lives` and respawn/continue
are global; `Core_Screen__SetTargetPosition` follows one focused entity; and
`Hud_Play__boss_bar` has a fixed older-slot scan. BOR single-player semantics
therefore do not determine a two-player policy. The following are proposed
adaptations and require approval:

* friendly fire off, with players excluded from each other's target set;
* AI target selection over both live players using a deterministic rule;
* either player may collect an item, with the existing effect applied once and
  reward ownership recorded;
* a bounded midpoint camera, including separation and one-player-dead rules;
* shared or independent score/lives, selected before implementation rather
  than inferred from the current global cells;
* pause ownership, since `pausemenu.pasm` currently implements one global
  state.

The actual predicates must be traced in the implementation pass: current
`Spawn_Play` has explicit slot checks and its wait/group scans test HP and
`CHAR_INPUT_DRIVEN_PROP`; `Game_State_AnyActorAlive` has explicit actor
operands; and `Game_State_Play` gates clear on exhausted queue plus that
helper. The co-op proof must show that both player slots are excluded and
only combat NPCs in slots 2–5 participate. It must not assume that an HP
check alone distinguishes player, enemy, and prop.

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
   either valid player; friendly fire follows the approved policy. If disabled,
   no player-to-player damage or stun may occur.
   Prove P2-to-NPC grab/follow/release/throw and reciprocal slot-ID links,
   including timeout, death, and reuse. A player must not write another
   player's state through a stale link.
5. **Production spawn/completion.** Reach four NPCs through `Spawn_Play`,
   distinguish props from enemies, exercise slot 4/5 death and reuse, retain
   metadata isolation, and prove the last enemy in slot 5 blocks completion.
   After its real combat death, prove `Stage_Cleared`, camera unlock, true
   right-edge travel, `Stage_LoadPending`, and next-stage loading.
6. **Player combat-state boundary.** Prove both players' HP, hit-stun, jump,
   special, grab, and throw state is actor-owned during this stage. Death/
   respawn, score/lives ownership, pause, and new-game reset are not silently
   accepted as P1-only behavior; they remain explicit full-co-op gates listed
   below unless the advisor expands the first slice to include them.
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

The following are settled for the proposed first slice:

* slot 1 is reserved for P2 only in two-player mode; one-player mode keeps
  NPC slots 1–5;
* both characters are fixed and preselected before gameplay; no dual selector
  interface is included;
* total capacity remains six actors and the single-buffer transport remains.

Remaining decisions requiring advisor approval:

1. Select camera policy, including separation and one-player-dead behavior.
2. Select friendly-fire and AI-target policy.
3. Select shared versus independent score/lives and the death/continue rule.
4. Confirm whether either controller may pause, or P1 alone owns pause.

The source-backed prerequisites before implementation are approval of these
policies, an allocation audit for the persistent-state budget above, and the
bounded JOY2/$421A delivery proof. JOY2 remains a future targeted
implementation gate, not a claimed result. No new shared armory tooling is proposed: the
existing input/debugger capability should be audited and reused first.

## Explicit nonclaims

No two-player co-op runtime exists in this branch. Independent input,
P2-specific presentation, P2 lifecycle, co-op targeting, shared camera/HUD,
and two-player stage completion are untested. G12 one-player six-actor
production, SOUND, the single-buffer transport, and accepted evidence remain
the baseline and are not modified by this proposal.
