# Post-G12 two-player proposal — independent advisor review

**Status: PLANNING ONLY. No implementation or integration authorized.**

“G13” is a provisional milestone name. `plan_game.md` §13 is sequencing guidance, not an existing Phase G13. Its §12 expressly assigns two-player co-op its own plan. The detailed G5/G10 status sections and the phase ledger supersede older opening-summary claims about missing portraits or ending. G12’s accepted six-actor migration and SOUND remain closed. [S0, S1]

## 1. Baseline and evidence boundary

Repository: `astrobleem/snes-bor`. Worker path: `E:\gh\snes-bor`.

- Accepted source: `836c0d4b1382420c30bf5849243b217a5a42e706`.
- Production ROM: `690F620E64D7645FCC750627C6A62C885D6527D1122C2795F6E1C8113A1C2C7A`.
- MSU: `CB44CF710C4F9A964AD5E96EE3AA5A6D50227CD1E15EDFE02F13C93AF0B6F0A0`.
- `g12-scaling` and `review/g12-six-actor-debug` are the accepted integration/evidence branches. `audio-content-pass` remains `58188b29023ab821ff83ed380e4e920fe2cf43e2`.

The final checkpoint and `out/g12_prod_*.log` retain the worker’s production-ROM regressions, including RALF’s original 64→60 damage assertion, six-slot lifecycle/reuse/pickup, real stage transition, depth/jump, and the continuous six-by-100-frame workload. That workload records five non-player combat actors at every sample, NMI delta 600, zero observed overruns, and DMA high-water 8 records / 856 bytes. These are retained worker executions, not emulator tests independently rerun for this proposal. Snapshot frame changes are not completed uploads; `confirmed_busy_denials` remains null/unmeasured. [S1]

This review inspected published source and retained documentation. All proposed two-player behavior, timing, memory placement, and gates below are **untested**. No broad regression run or binary rebuild was performed.

## 2. Recommendation and first implementation boundary

Propose a **fixed two-player session using the existing six actor slots**. P1 stays slot 0. P2 uses slot 1 only when the session is two-player. One-player mode retains NPC slots 1–5; two-player mode has NPC slots 2–5. Physical actor identity, roster identity, input owner, and draw rank remain separate concepts.

Slot 1 is the recommended P2 slot because it uses an already-proven lower-band pose allocation, keeps players together in a small bounded ownership map, and does not move any existing actor structure. This is an engineering choice, not a hardware requirement. Reserving slot 5 instead would still require auditing every fixed-player assumption; it would not avoid the actual work.

**First slice: G13A, dual-controller ownership and presentation foundation.** Build independent controller snapshots, explicit session/slot ownership, serialized initialization of both player appearances, P2 idle/walk/facing, NPC reservation, and correct enemy-count/stage-clear exclusion. Use an explicit opt-in test-session setup before gameplay through the session-initialization path, not ad hoc writes that turn an NPC into a player halfway through an update. Keep the normal one-player boot and menu policy unchanged.

This first slice is deliberately **not playable co-op**. P2 attack, jump, grab, special, pickup, damage/death, personal HUD, camera leadership, and pause/menu participation are not enabled merely by setting `CHAR_INPUT_DRIVEN=1`. In the opt-in foundation fixture they must be excluded explicitly so that partially migrated player globals cannot corrupt P1. Existing one-player behavior stays intact. P1/NPC combat may continue as the control workload; P2 is not yet an AI target or a friendly-fire target. Those exclusions must be visible in the gate and completion report, not concealed behind a “co-op PASS.”

Why this slice first: the renderer already supports six separately owned poses and stable depth ordering, whereas input, player state, targeting, and lifetime rules still contain single-player assumptions. Prove independent ownership before porting the entire moveset and session lifecycle. No evidence calls for another animation-transport experiment. [S2–S6]

## 3. Source rules versus proposed SNES policy

The external gameplay reference inspected here is the historical `Plombo/beatsofrage` **BOR.C** at `eba02fe6c9e97e388126c51560a92024f406d8c0`. Its rules are not automatically the rules of every later OpenBOR revision or TMNT mod. This review did not establish a matching shipped OpenBOR engine revision or a complete set of co-op-specific pak overrides. Existing converted content and accepted SNES move semantics remain authoritative for already-working attacks; do not replace them with historical BOR constants. [B1–B4]

| Topic | What the inspected source establishes | Recommended disposition |
|---|---|---|
| Friendly fire | `player_takedamage()` halves force when the attacker is a player. `player_grab()` has a player-victim throw path with half `THROW_DAMAGE`. Teammate interaction is not universally disabled. | Do not silently choose friendly-fire-off. Recommend source-compatible teammate interaction for a later combat slice, subject to shipped-content/version checks and explicit approval. Damage rounding and throw timing need their own assertions. |
| Enemy targeting | `enemy_find_target()` chooses the sole present player; when between two players in X it chooses the one it faces; otherwise it compares `abs(dx)+abs(dz)`. Equal-distance fallback is player 2 in that source. | Prefer this bounded rule over an invented nearest-X-only selector. SNES ground Y corresponds to the source’s ground-depth Z for this comparison; jump height is separate. Preserve current one-player AI behavior. |
| Camera | `update_scroller()` uses the midpoint of two present players, the sole present player otherwise, with direction-specific progression and enemy-wait gates. `player_trymove()` constrains players to the visible field. | Propose midpoint focus feeding the existing SNES camera/easing and stage bounds. Use the actual SNES viewport, not BOR’s 320-pixel constants. Preserve streaming and wait semantics. Exact clamp adaptation is a full-co-op decision, not G13A work. |
| Score and pickups | The pickup branch calls `addscore(self->playerindex, ...)`, heals `self`, or increments that player’s lives. It removes the item from subsequent contact after collection. | Recommend collector-owned rewards and per-player score/lives while retaining accepted SNES reward magnitudes. Simultaneous pickup attempts must resolve exactly once in stable simulation order. Do not split rewards or create a shared life pool by assumption. |
| Death and continues | `player_die()` decrements that player’s lives and clears only that player’s entity when exhausted; its both-absent check refers to global credits/time. | Recommend independent death/respawn and no team game-over while a surviving participant can continue. Full credit/rejoin semantics and mod overrides remain unverified. A fixed-session continue policy requires approval before implementation; no mid-game joining is included here. |
| Pause and selection | The SNES code currently uses the single `Input_trigger` and one selection context. | Proposed adaptation: sequential pre-game P1/P2 selection, and later either player may pause with one explicit pause-menu owner. Do not implement or claim these in G13A. |

Historical BOR’s special-move costs and respawn side effects differ from some accepted SNES behavior. They are not authorization to reopen G7 or SOUND. The proposal separates ownership changes from gameplay rebalancing.

## 4. Dependency map: actual code and required changes

Paths below are pinned by the source links. Named labels are audit entry points; this is not a claim that changing one label completes the whole subsystem.

| Area | Existing implementation / boundary | Required work and reuse |
|---|---|---|
| Input | `src/core/input.pasm`: `Core_Input_Init`, `Core_Input_Poll`; `Input_press`, `Input_trigger`, `Input_old` describe one controller. The edge detector computes new AND NOT previous press. [S3] | Maintain separate immutable-per-update snapshots for both controllers. Actor consumers choose their controller explicitly. A second poll must not erase an edge before that actor consumes it. Reuse the proven released-poll-before-press fixture discipline. |
| Identity and dispatch | `src/main.pasm`: `CharacterEntity_Init`, `Character_PlayFrame`, `Anim_Play`; actor-local `CHAR_INPUT_DRIVEN` controls behavior, while player positions/input still have global consumers. [S4] | Add explicit session ownership independent of HP, temporary freeze state, roster, and OAM rank. Do not equate every input-driven actor with P1 or use `CHAR_INPUT_DRIVEN` as the allocator’s sole reservation flag. |
| Spawn and reuse | `src/core/spawn.pasm`: `Spawn_Play`, `Spawn_DoRosterReassign`; added slots already use real roster reloads. [S5] | All free-slot selection, respawn/reuse, wait/group counts, and contained-item reveal traversal must respect session NPC eligibility. Slot 1 stays reserved even while P2 is dead, absent awaiting continue, or loading. Never advance a spawn record merely because reserved slot 1 has zero HP. |
| AI movement and attack | `Character_PlayFrame` / `Anim_Play` in `main.pasm` use the current player position and attack decisions. [S4] | Later select an eligible player actor ID, resolve its ground position, and use the same target consistently for facing/range/damage. Exclude dead/loading/ineligible players. G13A retains P1 targeting and expressly does not claim two-target combat. |
| Damage and scoring | `src/core/vm/vm_native_engine.pasm`: `Character_HitApply`, `Character_HitApply_VsPlayer`, `Character_HitApply__ScoreAndFinish`; `Game_Score_Award` in the game-state path. [S6, S7] | Split attacker ownership, target role, and reward owner. Current AI-vs-player work cannot keep writing P1 HP/invulnerability when P2 is hit. Player-vs-target traversal must use an explicit teammate policy, not assume slots 1–5 are all enemies. |
| Grabs and throws | `Character_Grab_SlotToOffset`, `Character_Grab_Play`, `Character_Grab_Throw`, `Character_Throw_Play`, `Character_Special_ReleaseGrab`; links and thrown-height state are already actor-specific. [S6] | Reuse bounded slot resolution and accepted invalid-link cleanup. Audit player-specific launch/damage/landing/reset branches. Verify all participant permutations; generic link following does not prove generic player input or death handling. |
| Jump and move state | `src/core/jump.pasm`: `Jump_PlayerTick`, `Jump_ApplyOamYOffset`, `Jump_PlaySpecialAdvance`, `Jump_PlayMoveSlotAdvance`. `Player_JumpZPos`/`Player_JumpZVel` are globals; throw Z fields are actor-local. [S8] | Later separate player jump state and audit dash/double-tap, slide, special, grab-move, and invulnerability ownership field by field. Keep actor-local move metadata and shared advance helpers. Do not run the current global player tick twice. |
| Character loading | `Anim_LoadCharacter`, `Anim_LoadCharacter_Long`, `Msu1_LoadFrame`, `CharSelect_Index`/`CharSelect_Loaded` in `main.pasm`; `Game_State_CharSelect_ReloadPlayer` in `charselect.pasm`. [S4, S9] | Serialize P1/P2 loads through the existing loader and staging lifetime. Save identities in their owning actors/session records; temporary loader selection is not both players’ persistent selection. Gate each actor until its palette/pose is valid. Never overlap palette/frame staging use. |
| Presentation | `src/core/depth_sort.pasm`: `CharacterDepth_DpBases`, `CharacterDepth_BuildOrder`; `Character_PlayFrame` and the existing six-row upload path. [S2, S4] | Reuse six physical allocations and stable ground-depth ordering unchanged. P2 is a change of ownership, not a seventh sprite or a new pose cache. |
| Camera | `src/core/screen.pasm`: `Core_Screen_Play`; player-position follower inputs and existing `Screen_PosX`/target state. [S10] | Later derive one session focus before the camera update. Preserve existing scroll budgets, bounds, foreground progress, and wait locks. G13A does not change the camera policy. |
| HUD, pickups, lifecycle | `Game_Lives`, `Player_InvulnFrames`, `GameOver_ContinueTimer`, `Game_Score`; `Game_State_HandlePlayerDeath` and `Game_State_NewGameReset`; existing pickup/reveal/scoring paths. [S6, S7] | Later allocate player-owned state and thread collector/attacker identity through reward paths. HUD must show both players without violating the one-text-staging-buffer discipline. New game and stage reload must initialize both players, clear links/transients, and preserve fixed membership appropriately. Exact full-context field layout remains an implementation audit item. |
| Pause, selection, reset | `src/core/charselect.pasm`: `Game_State_Play__charselect`, `Game_State_Play__charselect_wait`, `Game_State_Play__charselect_enter_playing`; existing `pausemenu.pasm` flow. [S9, S11] | Keep the canonical new-game reset choke point. Later distinguish menu owner, selected player, and session size. Prevent one player’s held Start from instantly committing another menu action. No title-boot policy change. |
| Completion | `Game_State_AnyActorAlive` in `vm_native_engine.pasm` reads the five fixed non-player HP locations; game-state/spawn paths decide clear/reload. [S6, S7] | In 2P mode exclude slots 0 and 1, then apply existing NPC enemy/prop rules. A living P2 must not hold a cleared stage open; a dead P2 must not turn into a reusable enemy slot. Do not revise unrelated completion semantics. |

## 5. Allocation and calling constraints

The existing actor DP bases are `$0A00`, `$0A85`, `$0B0A`, `$0B8F`, `$0C14`, `$0C99`. Their spacing is `$85`; it must not be confused with an asserted new `CHAR_ZP_LEN`. Keep the existing structure and bases for G13A. [S2]

| Actor slot | Physical tile-column value | OAM base tile | First frame-row VRAM byte address |
|---|---:|---:|---:|
| 0 | 0 | `$00` | `$8000` |
| 1 | 1 | `$04` | `$8080` |
| 2 | 2 | `$08` | `$8100` |
| 3 | 3 | `$0C` | `$8180` |
| 4 | 32 | `$80` | `$9000` |
| 5 | 33 | `$84` | `$9080` |

These are six existing 32×64 pose allocations, with six 128-byte art rows per streamed 32×48 frame plus padding. OAM base tiles are not tile-column values; the VRAM addresses above are bytes, not words. Two players do not require additional actor OAM entries, pose storage, or palette owners. Palette contents still need independent correct loading, including when both players select the same roster character. [S1, S2, S4]

A second press/trigger/old triplet adds **six bytes of input state**. Session count/ownership and later per-player lifecycle/move sidecars add further bytes; six is not a total co-op RAM estimate. Recommend a small explicit ownership representation, with NPC eligibility equivalent to mask `$3E` in 1P and `$3C` in 2P, rather than several independently mutable copies of the same fact. These masks are proposed mappings, not existing symbols.

Do not assert `$7E5900` or any other apparent gap is free. Before allocating sidecars, check all symbols, scratch ranges, runtime-indexed spans, and retained diagnostic reservations. Avoid changing actor stride simply to obtain player storage. The full player-context size and final addresses remain unmeasured.

The production checkpoint reports bank-0 `runtime_end=$FF54`, only 76 bytes before NMI in that specific region. That is not 76 bytes of total ROM free space. Prefer small bank-0 call sites with helper bodies in verified available banks. Preserve layout guards, actual M/X widths, DP/DBR, stack balance, and JSR/RTS versus JSL/RTL contracts. Shared loader/frame routines remain serialized; NMI must never consume staging that a second actor has overwritten. No audio-owned RAM, DMA, or ROM space is available by assumption. [S1, S4, S9]

## 6. Proposed G13A gates

These are acceptance requirements for a future implementation, not results.

1. **Controller separation and edge consumption.** Opposing simultaneous directions move only their owning actors; one released pad does not clear the other. Observe release at the engine poll before a new press, and confirm independent trigger words from the same update. Holding one button must not retrigger; disconnect/invalid-pad handling must not fabricate input. Exercise actual controller-2 delivery rather than writing trigger bytes to simulate success.
2. **Two valid live presentations.** Initialize two different roster identities through the real serialized loader, then verify bounded live VRAM/MSU source matches, padding, palette ownership, facing and OAM identity for both players while the other actors continue updating. Show idle/walk pose progress, not just changed logical frame indices. Also cover the same roster selected twice without palette/identity leakage.
3. **Ownership under pressure.** In 1P all five NPC slots remain available. In opt-in 2P only 2–5 are allocatable. Exercise spawn exhaustion, slot reuse, roster reassignment and pending-item work; a zero-HP/loading P2 is never claimed. Queue position and wait/group counts remain correct when all four NPC slots are occupied.
4. **Completion exclusion and foundation combat boundary.** Both living and zero-HP reserved P2 cases are excluded from enemy-alive checks. Verify no early clear while an eligible enemy remains and real transition after the last one dies. In the foundation fixture P2 cannot accidentally attack, collect, take P1-targeted damage, enter a player-global special/jump path, or be treated as an NPC by P1’s target scan. P1/NPC behavior remains the control, not a claim of P2 combat.
5. **Regression and resource integrity.** Retain the accepted 1P six-actor gates, including RALF/input-edge, invalid links, throws, collision, lifecycle, depth/jump and real transition. Run the appropriate 2+4 workload only after focused gates pass. Report NMI/queue observations on the ordinary build; do not derive confirmed busy-denial totals from snapshots or claim a universal DMA ceiling from one run.

No lossless global tracing framework is required. Use existing bounded debugger observation, independent source-byte comparisons, and explicit artifact identities.

## 7. Remaining gates before claiming full co-op

A later coherent combat/lifecycle slice must prove P1 and P2 can independently execute the already-supported moves; simultaneous jumps and specials cannot share height/timers; attacks select and damage the intended actor; two-target AI follows the chosen policy; and friendly fire/grab/throw behavior follows the approved rules. Include P2-only survival and attacks targeting P2 while P1 is unavailable.

Then prove independent score, pickup ownership, lives, invulnerability and respawn; deterministic simultaneous pickup resolution; one player dying without resetting or freezing the other; the approved continue/game-over policy; both-player and sole-survivor camera focus/clamps; two-player menu selection and pause ownership; and stage/ending/title/new-game round trips with no stale links, input edges or session membership.

Same-roster selection, player/npc slot reuse boundaries, delayed initial loads, and a full 2+4 workload remain mandatory. Preserve the 1+5 baseline throughout. Passing G13A alone may only be labeled **dual-controller foundation**, never complete co-op.

## 8. Shared armory and unresolved verification

The BOR `_harness.py` adapter imports `retro_harness` and its session helpers via the existing Mesen tools environment. The handoff identifies `E:\gh\retro-harness`, `E:\gh\retro-tooling`, `E:\gh\Mesen2`, and `E:\gh\poppy` as shared armory, not disposable project-local copies. The RALF investigation already established that an exact frame-count helper does not prove the game consumed a new button edge. [S12]

This review does **not** establish that the currently installed emulator endpoint exposes a working controller-2 override. Before G13A implementation, inspect the installed tool schema/implementation and run one bounded two-pad delivery probe. Reuse existing port-aware input/hold/release support if present. If absent, report the exact missing endpoint capability for separate authorization; do not create a new harness or edit foreign worktrees speculatively. No shared tool changes are proposed in this document.

Remaining source-verification limits: matching OpenBOR revision and co-op-specific pak overrides; complete continue/credit policy; final per-player context field inventory and memory placement. These limit full-co-op fidelity claims, not the feasibility of testing independent input and slot ownership. They must be resolved before their dependent implementation, not silently replaced with generic beat-em-up conventions.

## 9. Decisions for advisor approval

**A. Approve the first slice:** fixed two-player membership, P2 in slot 1, two players plus four NPCs, and a test-only dual-controller foundation before playable co-op. No mid-game join or title-boot change.

**B. Select eventual gameplay policy:** source-compatible teammate damage/grabs/throws, per-player reward/life ownership, and BOR-derived targeting are recommended, with the stated content-version verification. Friendly-fire-off, shared lives or simplified targeting would be explicit adaptations, not discovered source behavior.

**C. Approve the later session adaptation:** midpoint focus using existing SNES bounds/easing; sequential pre-game selection; defined pause ownership; and an explicit fixed-session continue policy. These are not authorized by approving G13A alone.

Until approved: no runtime, converter, audio, generated-artifact or shared-tool changes. Keep both accepted G12 branches, `audio-content-pass`, other planning branches, protected audio and unrelated dirty worktrees untouched. This proposal is the only new file on its own planning branch.

## Sources — immutable review references

All SNES references below use the accepted SHA, not a moving branch. External BOR links are historical comparison sources, not proof of a matching TMNT engine revision.

- [S0: roadmap](https://github.com/astrobleem/snes-bor/blob/836c0d4b1382420c30bf5849243b217a5a42e706/plan_game.md) and [phase ledger](https://github.com/astrobleem/snes-bor/blob/836c0d4b1382420c30bf5849243b217a5a42e706/tools/coverage_ledger/phase_status.json).
- [S1: G12 checkpoint and retained-log references](https://github.com/astrobleem/snes-bor/blob/836c0d4b1382420c30bf5849243b217a5a42e706/docs/g12_session_checkpoint.md).
- [S2: depth sorting / actor DP table](https://github.com/astrobleem/snes-bor/blob/836c0d4b1382420c30bf5849243b217a5a42e706/src/core/depth_sort.pasm).
- [S3: controller polling](https://github.com/astrobleem/snes-bor/blob/836c0d4b1382420c30bf5849243b217a5a42e706/src/core/input.pasm).
- [S4: actor, animation, loader and main-loop implementation](https://github.com/astrobleem/snes-bor/blob/836c0d4b1382420c30bf5849243b217a5a42e706/src/main.pasm).
- [S5: spawn and roster reassignment](https://github.com/astrobleem/snes-bor/blob/836c0d4b1382420c30bf5849243b217a5a42e706/src/core/spawn.pasm).
- [S6: native combat, links and actor-alive predicate](https://github.com/astrobleem/snes-bor/blob/836c0d4b1382420c30bf5849243b217a5a42e706/src/core/vm/vm_native_engine.pasm). The legacy directory name is not a proposal to introduce a script VM.
- [S7: game state, score and lifecycle](https://github.com/astrobleem/snes-bor/blob/836c0d4b1382420c30bf5849243b217a5a42e706/src/core/game_state.pasm).
- [S8: jump / shared move helpers / portrait](https://github.com/astrobleem/snes-bor/blob/836c0d4b1382420c30bf5849243b217a5a42e706/src/core/jump.pasm).
- [S9: character selection](https://github.com/astrobleem/snes-bor/blob/836c0d4b1382420c30bf5849243b217a5a42e706/src/core/charselect.pasm).
- [S10: screen follower](https://github.com/astrobleem/snes-bor/blob/836c0d4b1382420c30bf5849243b217a5a42e706/src/core/screen.pasm).
- [S11: pause menu](https://github.com/astrobleem/snes-bor/blob/836c0d4b1382420c30bf5849243b217a5a42e706/src/core/pausemenu.pasm).
- [S12: BOR harness adapter](https://github.com/astrobleem/snes-bor/blob/836c0d4b1382420c30bf5849243b217a5a42e706/tools/verify/_harness.py).
- [B1: BOR player death](https://github.com/Plombo/beatsofrage/blob/eba02fe6c9e97e388126c51560a92024f406d8c0/BOR.C#L2940-L3015).
- [B2: BOR player grab/throw](https://github.com/Plombo/beatsofrage/blob/eba02fe6c9e97e388126c51560a92024f406d8c0/BOR.C#L3080-L3390).
- [B3: BOR pickup ownership and teammate damage](https://github.com/Plombo/beatsofrage/blob/eba02fe6c9e97e388126c51560a92024f406d8c0/BOR.C#L3400-L3660).
- [B4: BOR enemy target selection](https://github.com/Plombo/beatsofrage/blob/eba02fe6c9e97e388126c51560a92024f406d8c0/BOR.C#L3800-L3900) and [camera / spawn-wait logic](https://github.com/Plombo/beatsofrage/blob/eba02fe6c9e97e388126c51560a92024f406d8c0/BOR.C#L4740-L4870).
