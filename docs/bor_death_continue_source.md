# BOR death, credits, continue, and score source audit

Status: source contract plus accepted P1-L1, L2, L3, and L4 lifecycle slices.
The stock/credit storage, source death/respawn path, credit-gated re-entry,
and final game-over/title-return path are implemented.

Sources used:

- Local authoritative PAK: `Beats of Rage Original [v.3.0 Build 4086].pak`,
  SHA-256 `A2A55CDD5E1145E845607ECEC3AD85A342529492E7120449A928F3A6EAEA81D6`.
  Relevant data is `DATA\CHARS\MISC\*.TXT` and the Easy level files.
- Original source: `BOR.C` from the historical Beats of Rage source tree,
  <https://github.com/Plombo/beatsofrage/blob/master/BOR.C>. Function and
  line references below refer to the fetched source snapshot used for this
  audit.
- Current implementation evidence is cited by local source path and symbol.

## Executive result

Original BOR does not use the current SNES model of a 20-life stock followed
by a global continue screen. The source model is:

1. `selectplayer()` clears both player records and starts with `credits = 4`.
2. Each player who joins consumes one credit and receives `lives = 3`.
3. A lethal player fall decrements that player's lives. With lives remaining,
   the same entity respawns immediately through the death state; with no lives,
   the entity is removed.
4. A player with no entity may join later by pressing Start while credits
   remain, including while the other player is still active. This is a new
   join with three lives, not a continue-screen transaction.
5. If all configured players are gone, the level timer gives a short join
   window. If that window expires without a join, the level ends and
   `playgame()` calls `gameover()`.
   `gameover()` displays `GAME OVER` for approximately eight `GAME_SPEED`
   units or until Start/Escape, then control returns to the title loop.

The original source does not establish a separate continue counter, a
per-player game-over menu, or a persistent 20-life stock.

## P1-L1 foundation status

The SNES foundation now uses `GAME_LIVES_START = 3` for both player slots.

## S1B.6 life-state representation

The bounded SNES representation for BOR player stock is now unsigned 16-bit.
The audited reachable original-campaign upper bound is 20,007 (initial stock,
score-threshold awards, and campaign 1UP placements), so 8-bit storage is not
sufficient while 16-bit storage is sufficient. Canonical P1/P2 life state and
HUD caches occupy the explicitly guarded WRAM block `$7E58E1-$7E58E8`.
S1B.6 changes storage width, lifecycle reads/writes, and cache comparison only.
S1C now restores source `addscore()` arithmetic: unsigned 32-bit addition,
the `999999999` cap, 50,000 threshold derivation, strict `>` comparison,
multiple awards, and per-player 16-bit life increments. Event/call-site award
amounts remain intentionally temporary until S1D.
`Game_State_NewGameReset` is the single canonical new-run boundary and writes
P1 lives, P2 lives, scores, and the one run-global `Game_Credits = 4` value.
Credits live at `$7E2694`, reclaimed from the retired `CharDirSeekTmp` byte;
there is no P1/P2 credit mirror.  Stage progression does not write this cell,
so the value persists across ordinary stage loads.  Credit consumption,
source re-entry, death timing, respawn behavior, and game-over replacement are
deliberately not part of P1-L1.

## Original life and credit model

| Question | Original BOR evidence | Result |
|---|---|---|
| Meaning of `s_player.lives` | `s_player` contains an integer `lives`; `selectplayer()` sets it to 3 on join and `player_die()` decrements it | Per-player remaining death stock, initialized to 3 |
| Credits | Global `credits`; `selectplayer()` initializes it to 4; a later Start decrements it and sets `joining` | Join credits, not lives and not a continue timer |
| Initial value | No player stock exists before selection; `memset()` clears both records, then the join path assigns 3 | Each joined player starts at 3 |
| Health depletion | `player_takedamage()` reduces health; a lethal or falling state enters `player_fall()`; after landing at zero health it enters `player_blink()` | Death is processed after the fall/landing sequence, not at the first HP write |
| Zero lives | `player_die()` kills the entity, clears `player[i].ent`, and leaves the player eligible for a later credit-based join | No automatic respawn at zero |
| Stock persistence | `playlevel()` carries the player record between level parts; after a completed part it resets `spawnhealth`, not lives | Lives persist across parts until death or a new join |

The relevant source is `selectplayer()` around BOR.C lines 5542–5612,
`player_die()` around 2981–3015, and `playlevel()` around 5514–5537.

## Death and respawn sequence

The source sequence is:

1. `player_takedamage()` clears attacking/jumping state, applies the force,
   and sends a lethal, dropped, or airborne player to `ANI_FALL` and
   `player_fall()` (BOR.C 3582–3617).
2. `player_fall()` advances the toss until the player lands. If health is
   zero, it sets `blink = 1`, schedules `stalltime = time + GAME_SPEED * 2`,
   and changes the thinker to `player_blink()` (BOR.C 3166–3226).
3. `player_blink()` waits until `stalltime`, then calls `player_die()`.
   This is the source death pause/blink interval; no separate death animation
   is selected in this path.
4. `player_die()` decrements lives. If the result is positive, it unlinks the
   entity and respawns it in a jump state with full model health:

   - scrolling left: `x = advancex + 290`, facing left;
   - other directions: `x = advancex + 20`, facing right;
   - `z = ((PLAYER_MIN_Z + PLAYER_MAX_Z) / 2) - 10`;
   - `a = 300`, `base = 0`, `jumping = 1`, `attacking = 0`;
   - `health = maxhealth`, animation `ANI_JUMP`, thinker `player_jump`;
   - all enemies are dropped and the level timer is reset.

   This is BOR.C 2981–3015.

5. `spawnplayer()` uses the selected model and, when `spawnhealth` is set,
   starts at `spawnhealth + 5`, clamped to model health (BOR.C 4677–4695).
   At a completed level part, `playgame()` clears both `spawnhealth` values
   before the next part. Thus a normal next part starts at model health,
   while a same-level respawn uses the full-health death path above.

There is no source respawn invulnerability counter. `blink` is the entity's
death/blink presentation state, not a documented post-respawn grace window.

## Two-player behavior

Original `predrawstatus()` handles each player independently (BOR.C
2114–2165):

- an active player is displayed with its own score and lives;
- a player with `joining` set is shown as a selectable hero;
- that player's Start/any-button confirmation assigns three lives, clears
  `joining`, sets `spawnhealth`, and calls `spawnplayer(i)`;
- a player with no entity can press Start while `credits` is nonzero, which
  consumes one credit and enters the same join flow.

Consequences:

- P1 may die while P2 remains active; P2's stage continues while P1 can join
  again if a credit remains.
- P2 may die while P1 remains active under the same rule.
- One player does not need to wait for the other to die before joining.
- The source has per-player lives and score fields, but the shared `credits`
  pool controls later entry.
- The source does not provide a dedicated per-player continue screen.
- The source does not establish a fixed P2 identity or a fixed P2 Leo rule.

`playlevel()` continues until `endgame`; its return value is true if either
player still has lives. `playgame()` calls `gameover()` only when a failed
level returns with both life stocks exhausted (BOR.C 5618–5652).

## Continue and game over

The closest source equivalent to a continue is credit-based re-entry:

- While a player is absent, `predrawstatus()` displays `Credit N` / `Press
  start` and accepts that player's Start.
- The player record is assigned a new model if needed, `lives = 3`,
  `joining = 1`, and one global credit is consumed.
- Confirmation then spawns the player and resets the level timer.
- The active level, the other player's entity, and the other player's score
  are not reset by this join path.

There is no source countdown labeled Continue. If all configured players are
absent, `player_die()` opens a re-entry window with
`timeleft = 10 * COUNTER_SPEED`, or `COUNTER_SPEED / 2` when no credits
remain. A player may still join during that window. Expiry reaches
`time_over()`; the failed `playlevel()` then leads to `gameover()`.

`gameover()` unloads the level presentation, plays `gameover.bor`, displays
`GAME OVER`, and exits after `time > GAME_SPEED * 8` or Start/Escape
(BOR.C 5407–5428). The caller then returns to the outer title loop.

No source save-data effect is attached to game over. The only persistent
completion update shown in this path is `savedata.times_completed++` after
the selected set's complete level sequence (BOR.C 5627–5649).

## Score, enemies, and pickups

### Enemy and hit score

`enemy_takedamage()` assigns the hit to `self->playerindex` and calls
`addscore(other->playerindex, force * 5)` for a player-caused hit (BOR.C
4390–4417). S1D now routes the represented ordinary player-hit path through
that force-based rule; the current represented attack force is 1. A boss kill
sets `level_completed` and otherwise follows the same damage path. The source
has no separate universal kill bonus.

`addscore()` (BOR.C 2246–2264) caps score at `999999999`. S1C now implements
this primitive in the SNES runtime. It awards one life
for each crossed 50,000-point threshold using the source's strict
`s > next1up` loop, then stores the player's score. This is per-player.
The loop evaluates the final clamped score against every successive threshold
without intermediate score assignments: for example, `49999 + 100002` ends at
`150001` and awards three lives for 50000, 100000, and 150000. Landing exactly
on a threshold does not award it, and the next call recomputes `next1up` from
that exact current score, so the boundary is skipped permanently.

### Item values from the authoritative PAK

| PAK model | Source fields | Original pickup effect |
|---|---|---|
| `APPLE.TXT` | `health 30`, `type item` | Adds model health, clamped to max |
| `MEAT.TXT` | `health 100`, `type item` | Full/large health add, clamped to max |
| `MONEY.TXT` | `score 1000`, `type item` | Adds 1000 to the collecting player's score |
| `GOLD.TXT` | `score 5000`, `type item` | Adds 5000 to the collecting player's score |
| `1UP.TXT` | `health 0`, `type item`, name `1up` | Adds one life to the collecting player |
| `TIME.TXT` | `health 0`, no score, name `Time` | Resets the level timer |

`player_think()` checks a nearby `TYPE_ITEM` on attack input (BOR.C
3489–3517): score first, then health, then the exact `Time` name, otherwise
the item is treated as a 1UP. The item is moved off-field, marked for suicide,
and the player enters `ANI_GET`.

The PAK confirms the score values; the source confirms the effect dispatch.
The source's 50,000 score thresholds, rather than the current SNES 5,000
threshold, are authoritative.

### Two-player score ownership

Enemy score is attributed through `other->playerindex`. Item score and life
effects are attributed through the collecting player's index in
`player_think()`. There is no global shared score in the original structures.

The generic source attack mask also includes `TYPE_PLAYER` for a player
attacker, and `player_takedamage()` halves force from a player attacker
(BOR.C 2617–2629 and 3582–3600). This is direct evidence that the original
source permits player-v-player damage in its generic path; the current SNES
friendly-fire-off rule therefore remains a separate fidelity question, not a
source-backed assumption.

## `2pitem` semantics

`2pitem` is parsed in the original level loader as an item attached to a
breakable/obstacle spawn with `if2p = 1` (BOR.C 2010–2021). The later
`obstacle_takedamage()` path spawns the contained item only when:

```c
if(self->item[0] && (!self->if2p || count_ents(TYPE_PLAYER)>1))
```

(BOR.C 4552–4565).

Therefore `2pitem` means: the contained item is revealed only in a game with
more than one active player. It is not ownership-specific, not an alternate
item for P2, and not simply a second-player reward selector. The revealed
item is then collected by whichever player reaches it and uses that player's
normal pickup ownership. The SNES record preserves the source flag in the
existing spawn metadata; at the break/reveal boundary the bounded SNES
adaptation counts non-OUT P1/P2 entities in the active two-player session.

The original BOR Easy PAK contains `2pitem` occurrences in `1B`, `1C`, `2`,
`3B`, `3C`, `4A`, `4B`, `5A`, `5B`, and `6A`; examples include Apple, Money,
and Meat. This makes the feature reachable source content rather than an
unused keyword.

## P1-L2 implementation boundary

The accepted L2 production path is `Game_State_Play__playing` ->
`G13_HandleP2Death` -> `G13_SourcePlayerDeathP1`/`G13_SourcePlayerDeathP2`.
HP zero first stamps `CHAR_SELECTED = FALL`; the existing
`Anim_Play_Fall` path completes the fall/land phase and counts the
`DEATH_BLINK_FRAMES` value (120 NTSC frames, derived from
`GAME_SPEED * 2`).  Only after the terminal fall marker does the handler
decrement `Game_Lives` or `G13_P2Lives`.

With stock remaining, `G13_RespawnP1`/`G13_RespawnP2` restore
`CHAR_HP_MAX`, clear transient hit/grab state, enter `CHAR_SELECTED = JUMP`,
launch with the existing SNES jump representation, and place the player at
`Screen_PosX + 20`.  This is the rightward `advancex + 20` source rule for
the currently shipped right-scrolling levels.  `G13_DropAllEnemies` applies
the source `drop_all_enemies()` effect to live unlinked AI actors by entering
the existing FALL machine without damaging or despawning them.  The runtime
has no separate BOR `link` field, so the mutually exclusive grab-target and
grabbed-by fields are the narrow SNES equivalent.

The source path does not write `Player_InvulnFrames` or
`G13_P2_InvulnFrames`; the former 90-frame respawn grant is therefore absent
from L2.  When the decremented stock reaches zero, L2 marks the player OUT
and leaves credit use, re-entry, and final game-over semantics to P1-L3.

## P1-L3 implementation boundary

`G13_HandleOutContinue` is now the source-gated re-entry path.  It checks an
OUT player’s own Start edge and the single `Game_Credits` byte.  With a
positive balance it decrements credits once, restores that player’s stock to
`GAME_LIVES_START` (3), and calls the existing player-specific respawn path
for full health/state restoration.  P1 uses controller 1; P2 uses controller
2 and is eligible only in a 2P session.  An active player, a held/failed
attempt, and a zero-credit attempt do not consume credits.  The other
player’s stock and state are untouched.

The OUT flag is the current bounded SNES representation of the source
absent-entity/`joining` boundary; there is no second per-player credit cell.
The old 300-frame `GAME_STATE_GAMEOVER` continuation path is no longer used
by BOR gameplay. Its generic storage/routines remain only as deferred
compatibility machinery. P1-L4 now owns the accepted both-player terminal
detection, GAME OVER presentation, timing, and return to TITLE.

## P1-L4 implementation boundary

`Game_State_Play__check_all_out` observes the source-equivalent condition:
all configured SNES players are OUT. It arms a 600-frame SNES grace window
when credits remain, or a 30-frame no-credit window. Start re-entry during the
positive-credit window remains available through the accepted P1-L3 path and
clears that timer without consuming a second credit. Expiry with no re-entry
enters the frozen `GAME_STATE_GAMEOVER`; no credit is consumed by this
transition.

`Game_State_Play__gameover_Long` presents the source-equivalent `GAME OVER`
text for 480 frames (the 60 Hz adaptation of source `GAME_SPEED * 8`) or
until either controller produces an input edge, then returns to TITLE through
`G13_DisableP2Session`. The title return itself does not begin a new run:
`Game_State_NewGameReset` remains the source-defined reset boundary reached by
the next normal difficulty/player-selection flow, where lives become 3 and
global credits become 4 again.

## Comparison with current SNES

| Behavior | Original BOR | Current SNES | Classification | Required correction |
|---|---|---|---|---|
| `GAME_LIVES_START` | Three lives are assigned when each player joins; four global credits govern entry | `GAME_LIVES_START = 3` now initializes both player slots; one `Game_Credits` cell is initialized at `Game_State_NewGameReset` | SOURCE_ADAPTATION | Later slices must replace synthetic continue/re-entry behavior with source credit consumption |
| Death delay | Fall, land, blink for `GAME_SPEED * 2`, then `player_die()` | HP-zero enters the existing fall machine; the terminal blink marker gates stock consumption | SOURCE_ADAPTATION | Retain the source ordering; L3 owns what follows zero stock |
| Respawn | Same entity, full health, directional `advancex` offset, jump entry, enemies dropped | `G13_RespawnP1/P2`: full HP, rightward `Screen_PosX + 20` for shipped stages, jump state, enemy fall/drop pass | SOURCE_ADAPTATION | Add left-scroll representation only when such source content is shipped |
| Respawn invulnerability | No source respawn-invulnerability counter | Source respawn path no longer writes the 90-frame counter | SOURCE_MATCH | Keep deferred synthetic continue machinery separate |
| Respawn health across parts | Same-level respawn full model health; completed part clears `spawnhealth` so next part starts normally | Full HP reset path | SOURCE_ADAPTATION | Preserve only after source-position/death timing is corrected |
| Independent P1/P2 stock | Per-player `lives`, shared join `credits` | Independent `Game_Lives` and `G13_P2Lives` | SOURCE_ADAPTATION | Retain ownership split, replace 20-life/credit semantics |
| Continue | No continue screen; absent player re-enters through Start and remaining credits | OUT player’s Start consumes one global credit and restores 3 lives/full health; no BOR countdown path | SOURCE_ADAPTATION | Accepted P1-L3 source re-entry |
| Game over | All configured players absent, re-entry window expires, then `gameover()` and title | All configured SNES players OUT arms the source-equivalent grace window; expiry enters frozen GAMEOVER, any button or the display timeout returns TITLE | SOURCE_ADAPTATION | Accepted P1-L4 terminal path |
| Hit score | `force * 5` per player-caused enemy hit | S1D force-based wrapper; represented ordinary force=1, so +5 | SOURCE_ADAPTATION | Per-attack source-force data remains limited by the current runtime model |
| Score thresholds | Crossed 50,000 multiples award one life; strict `>` boundary quirk and multi-crossing are implemented by S1C | Canonical 32-bit addscore primitive; represented event path now routes force*5 | SOURCE_ADAPTATION | Source stage/item call-site audit remains bounded follow-up |
| Money/Gold | PAK values 1000/5000, awarded to collector | Current values 1000/5000 and owner-local collector | SOURCE_ADAPTATION for values/ownership |
| 1UP | Name-special-case pickup adds one life | Current ONEUP pickup adds one life | SOURCE_MATCH for isolated effect; stock model remains divergent |
| `2pitem` | Reveal contained item only when more than one player exists | Parser preserves the flag; break/reveal gates it on the active-player count, while collection remains normal collector ownership | SOURCE_ADAPTATION | Keep source predicate and verify OUT-player boundary |
| Friendly fire | Generic source attack mask/player damage path supports it | Current G13 rule disables it | SOURCE_FEATURE_MISSING or SOURCE_ADAPTATION, pending full source input/path audit | Resolve separately; do not change here |

## Recommended correction slices

1. **P1-A: source life/credit state.** Add an explicit per-player source life
   stock initialized to 3 and a shared or source-equivalent credit state
   initialized to 4 at game entry. Keep current state cells only as a
   temporary compatibility layer during migration.
2. **P1-B: source death state.** Separate lethal fall/blink/death timing from
   the current immediate HP-zero handler, then implement directional respawn,
   full model health, enemy drop, and no invented invulnerability unless a
   separate source reason is established.
3. **P1-C: credit-based re-entry and 2P lifecycle.** Replace the global
   continue screen with independent absent-player Start re-entry while the
   partner remains active, plus the source both-out timeout/game-over path.
4. **P1-D: source scoring call sites.** S1C restores canonical 32-bit
   addscore arithmetic, cap, threshold quirk, and threshold-life ownership.
   S1D now carries the represented ordinary attack force into per-player
   `force * 5` scoring with no kill bonus. Biker and source stage-completion
   call-site coverage remain explicitly tracked where the current runtime has
   no corresponding source path.
5. **P1-E: `2pitem`.** Implement the source's two-active-player reveal gate
   and verify collector ownership separately from reveal eligibility.
6. **P2: friendly-fire and other combat fidelity.** The source evidence above
   warrants a dedicated audit, but it is outside this task.

## Existing G13 gates requiring semantic replacement

The following accepted gates historically tested the implementation contract.
The dedicated P1-L2, P1-L3, and P1-L4 gates now carry the source-fidelity
lifecycle proofs:

- `tools/verify/game_g3_death.py`: historical assumptions included
  `GAME_LIVES_START`, automatic respawn, a 300-frame global continue
  countdown, and Start restoring fresh lives; dedicated P1-L2/L3/L4 gates now
  carry the source lifecycle assertions.
- `tools/verify/game_g13_stage_lifecycle.py` and related lifecycle gates:
  assume independent 20-life stocks, OUT flags, and current same-frame death
  handling. Their ownership assertions can be retained, but their death
  semantics must be replaced.
- `tools/verify/game_g13_continue_semantic.py`: assumes a player-owned
  continue can restore one player from GAMEOVER/OUT using Start. It should be
  replaced by source credit-based re-entry and both-player game-over tests.
- `tools/verify/game_g13_score_pickup.py`, `game_g6_hud.py`, and score-related
  gates: ownership checks remain useful; source force*5 and 50,000 primitive
  contracts now own the score expectations, while remaining event/call-site
  coverage is tracked separately.
- `tools/verify/game_g8_pickup.py`, `game_g8_pickup_chain.py`, and prop gates:
  isolated Money/Gold/1UP value and collector checks remain useful; they must
  gain separate `2pitem` reveal coverage rather than treating every item as
  immediately eligible.

Historical G3/G13 assertions that referred to the retired synthetic continue
path are not source-fidelity gates; the dedicated P1-L2/L3/L4 gates provide
the current lifecycle evidence.

## Current status

P1-L1, P1-L2, P1-L3, and P1-L4 are accepted locally. L1 provides
`GAME_LIVES_START = 3` and one run-global `Game_Credits` cell initialized to
4. L2 provides the source fall/blink/decrement/respawn sequence. L3 provides
   credit-gated Start re-entry with three lives and full health; the old
   300-frame BOR continuation path is no longer used by gameplay. L4 provides
   the source-equivalent all-out grace, frozen GAME OVER, and TITLE return.

Source scoring, `2pitem`, and Batch B/2EASY remain separate work.
