# plan_game.md — from hardware proof-of-concept to a complete, releasable game

> **This is the critical path.** Everything in this file is required to turn the
> current ROM into something a person could sit down and play from title screen
> to ending.
>
> **None of the menu/HUD/game-state machinery in this file requires the script
> VM** (`plan_vm.md`) to be *implemented* — but as of 2026-08-19, `plan_vm.md`
> is required and prioritized project-wide: the goal is the full converted
> OpenBOR content library (14 stages, ~24 characters), and hand-written
> stand-ins for VM-driven content (the fixed spawn table, hard-coded roster)
> are to be phased out as VM gates land, not kept forever. This file's own
> "text gets the low end because it is on the critical path and the VM is not"
> byte-budget framing (below) is from before that decision — re-check
> `plan_vm.md` §0.3 rather than assuming the VM still yields priority in their
> shared ROM region.
>
> Read `README.md`'s "Current Status" first — it is the authoritative list of
> what actually works today. This file assumes it.

---

## §0 — Where the game actually is

Be precise about this, because the engine is genuinely impressive in ways that
make it easy to overestimate how close a *game* is.

**What exists and works:** SA-1 boot and CC-DMA, MSU-1 asset streaming, TAD music,
a 4-entity system with per-instance state, dpad player control, AI that seeks and
attacks, AABB collision with hit stun, HP with a BG3 health-bar HUD, a soft-kill
at 0 HP for AI, two converted real levels with a streaming tile cache, horizontal
camera scrolling, a frontpanel foreground layer, a 4-character roster with live
Select-cycling, convert-time spawn tables driving real enemy waves, a font/text
renderer (G1), a game state machine (G2), and player death/lives/continues/game
over (G3).

**What that adds up to:** one level that boots, scrolls, and lets you punch three
enemies until they die back at you — and if they win, you get a game-over screen
and a continue, not a soft freeze. There is still no win condition, no second
level reachable from the first, and no menus with real content (title/char-select/
pause all exist as state-machine stops with no drawn screen yet — text CAN be
drawn since G1, nothing calls it for a menu yet).

**The honest gap list**, none of which is started (past G1–G3, done above):

| Missing | Blocks |
|---|---|
| ~~Font / text renderer~~ | **Done (G1, 2026-08-21)** — `core/text.pasm`, gate `game_g1_text.py` |
| ~~Game state machine~~ | **Done (G2, 2026-08-21)** — `core/game_state.pasm`, gate `game_g2_states.py` |
| ~~Player death~~ | **Done (G3, 2026-08-21)** — lives/continues/game over, gate `game_g3_death.py` |
| Win condition | Any reason to finish a level |
| Level transition | Stage 2 existing |
| Menus (title, char select, pause, options) | Being a product |
| ~~Score / real HUD~~ | **Done (G6, 2026-08-21)** — gate `game_g6_hud.py` |
| Jump, throw, grab, specials | BOR's actual moveset — **run/dash done (G7 first slice, 2026-08-22)**, gate `game_g7_run.py`; **AI invuln frames done (G7 second slice, 2026-08-22)**, gate `game_g7_invuln.py`; **knockdown/getting-up done (G7 third slice, 2026-08-22)**, gate `game_g7_knockdown.py`; jump/grab/special/block still open, see §7 |
| ~~Items / pickups (entity kind, health)~~ | **Partial (G8, 2026-08-21)** — real prop kind + per-spawn HP, gates `game_g8_props.py`/`game_health_override.py`. §8a (level-format-keyword parity) is now fully exhausted — every row DONE, a permanent no-op, or waiting on a real dependency outside the table (see §8a's own "Conclusion" for what's actually next) — **read that table instead of asking what's next** |
| Bosses | Stage climaxes; HP-override prerequisite done (§9) |
| Ending / credits | Finishing |
| SFX | Every impact feeling real (blocked on content, §11) |

**One structural constraint that shapes everything below.** Two deliberate
shortcuts are load-bearing in the current engine and will need revisiting for a
full game — but not until the phase that actually needs them:

- **"The player is always slot 0."** Entity 0 is created first, never killed, and
  reachable at fixed absolute addresses; `Entity1/2/3_Base` are compile-time WRAM
  literals. This is correct for single-player and must not be "generalized" for
  its own sake — but 2-player co-op (§12) genuinely breaks it.
- **One entity streams one animation frame per frame** (`Msu1_StreamBusy`). With
  N entities, each animates at most every N frames. At the current N=4 that is
  ~15fps of animation. This is *correct behavior, not a bug* — but it is a hard
  scaling wall the moment a stage wants six enemies on screen, and §12 is where
  that gets confronted.

---

## §1 — Phase G1: a font and text renderer (hard prerequisite, do this first)

**Nothing else in this file can start until text can be drawn.** There is no font
anywhere in the codebase today — `core/error.pasm`'s header even notes that
upstream SuperBossGaiden rendered an on-screen register dump and this port
dropped it.

### Scope

1. **A font converter** (`tools/bg_converter/make_font_tiles.py`) — mirror
   `make_hud_tiles.py`, which already emits BG3 2bpp tiles and is the closest
   working precedent. Emit an 8×8 2bpp tileset for `A–Z`, `0–9`, and basic
   punctuation. BOR's own menu font can be lifted from the pak, or use a clean
   public-domain 8×8 font — pick one and document which.
2. **A text-draw routine** (`src/core/text.pasm`) — `Core_Text_DrawString` writing
   tilemap entries into a BG3 (or BG1, when BG3 is busy with the frontpanel)
   tilemap region, plus `Core_Text_DrawNumber` for scores/timers.
3. **Reuse the existing streaming/HUD plumbing.** BG3 already carries the HUD and
   proves per-tile priority above OBJ. Text is the same mechanism with different
   tiles.

### Watch out

- BG3 is 2bpp and its palettes **overlap BG1's 4bpp palettes** — a documented trap
  from Phase 6 (memory `snes_bor_phase6_bg_backdrop_hud`). Allocate the font's
  palette deliberately, don't assume a free slot.
- On levels with a frontpanel (stage 1A has one; 1B does not), BG3 is already
  fully committed to the frontpanel streaming cache. Menus draw when no level is
  loaded, so this is mostly fine — but the **pause menu and in-level HUD text
  overlap the frontpanel case** and need a decided answer. Simplest: pause menu
  draws on BG1 under forced-blank-free conditions, or the frontpanel resolver is
  suspended while paused.
- **ROM budget — the gap is divided, use your half.** `$C100`–`$FC00` has only
  ~1913 bytes free, so `core/text.pasm` goes in the bank-0 gap instead. That gap
  (`$8C60`–`$AC00`, 8096 bytes) is **shared with `plan_vm.md` and already
  allocated**:

  | Range | Size | Owner |
  |---|---|---|
  | **`$8C60`–`$9000`** | **928 B** | **`core/text.pasm` — this phase** |
  | `$9000`–`$AC00` | 7168 B | the script VM (`plan_vm.md`) |

  Text gets the low end because it is on the critical path and the VM is not.
  **`.org $8C60`, and keep `core/text.pasm` under 928 bytes.** If it doesn't fit,
  take the space from the VM's half and update `plan_vm.md` §0.3 in the same
  change — do not silently grow past `$9000`. Overflow here is silent (Poppy
  truncates `.org` regions without error) and lands on `LoadAudioData`, so it
  presents as an *audio* bug.

  Occupancy check for this phase:

  ```bash
  python - <<'EOF'
  import re
  syms=[(int(m.group(2),16),m.group(3))
        for l in open('src/main.sym',encoding='utf-8-sig')
        if (m:=re.match(r'([0-9A-F]{2}):([0-9A-F]{4})\s+(\S+)',l.strip()))
        and m.group(1)=='00']
  cand=[a for a,_ in syms if 0x8C60<=a<0x9000]
  top=max(cand) if cand else 0x8C60
  print(f'text region top ${top:04X}, {0x9000-top} bytes left before $9000')
  assert top < 0x9000, 'TEXT REGION OVERFLOW — would collide with the VM half'
  print('region OK')
  EOF
  ```

**Gate** (`tools/verify/game_g1_text.py`): draw a known string at a known
position; read the BG3 tilemap back from VRAM and assert each tile index matches
the converter's own character→tile mapping, byte for byte. Ground truth is the
converter's output, not a screenshot — per memory `mesen_screenshot_stale_hud_layer`,
screenshots show a stale BG3 layer even when VRAM is correct.

---

## §2 — Phase G2: a game state machine

> **Status: DONE** (2026-08-21). `GATE G2: PASS` — `core/game_state.pasm` adds
> `Game_State`/`Game_StatePrev` and all 7 `GAME_STATE_*` constants; `scpu_main_loop`
> now calls one `jsr Game_State_Play` (replacing the ~11-line straight-line
> gameplay list it used to run unconditionally, which is budget-*positive* for
> the tight `$FC00`-`$FF90` region, not neutral). `GAME_STATE_PLAYING = 0` is
> the boot default (so the existing zero-init-before-`Core_Nmi_Init` step
> doubles as the state choice) — every existing routine gate keeps passing
> unchanged, since they all drive the ROM from boot expecting gameplay already
> running. TITLE and PAUSED are real (reachable via a forced `Game_State`
> write today; no menu content yet, that's G5) and correctly one-shot-hide/
> restore hardware OAM on the PLAYING transition edge; CHARSELECT/GAMEOVER/
> STAGECLEAR/ENDING are explicit no-op stubs. `CharSelect_Index`'s hard-coded
> roster logic was deliberately NOT wired into `GAME_STATE_CHARSELECT` here —
> CLAUDE.md says that's to be phased out as VM gates land, not invested in
> further. Gate: `tools/verify/game_g2_states.py`.

Today `scpu_boot` falls straight into `scpu_main_loop`, which unconditionally
runs the gameplay subsystems forever. There is no concept of "not in gameplay."

### Scope

Add `Game_State` (a WRAM byte) and dispatch `scpu_main_loop` on it:

```
GAME_STATE_TITLE       title screen, waiting for Start
GAME_STATE_CHARSELECT  character select
GAME_STATE_PLAYING     current behavior
GAME_STATE_PAUSED      frozen, pause menu drawn
GAME_STATE_GAMEOVER    game over, continue countdown
GAME_STATE_STAGECLEAR  stage cleared, transition
GAME_STATE_ENDING      credits
```

Each state gets its own `Play` routine; the loop calls exactly one per frame.

### Watch out

- **`Core_Nmi_WaitFrame` must still be called once per iteration in every state.**
  Omitting it in a new state reproduces the confirmed vblank-overrun bug that
  corrupts the top of every frame (`CLAUDE.md`; four recurrences).
- **Subsystems that unconditionally enqueue DMA must not run in non-playing
  states.** `Core_Oam_Play` and `Hud_Play` are the ones to check. A title screen
  that still runs the entity system will keep streaming character frames from
  `bor.msu` for entities nobody can see.
- Zero all new state cells **before `Core_Nmi_Init`** (memory
  `boot_nmi_race_before_oam_init`).

**Gate** (`game_g2_states.py`): drive Start/Select through `m.set_input` and assert
`Game_State` transitions in the expected order, that `Nmi_FrameCounter` keeps
advancing 1:1 in every state, and that the DMA queue never saturates in a
non-playing state. Note `set_input` is wall-clock/sleep-based, not frame-exact
(memory `mesen_set_input_wall_clock`) — assert on transitions, never on exact
frame counts.

---

## §3 — Phase G3: player death, lives, continues, game over

> **Status: DONE** (2026-08-21). `GATE G3: PASS` — `core/game_state.pasm`'s
> `Game_State_Play__playing` now checks `PlayerEntity_Hp == 0` once per frame
> and dispatches to `Game_State_HandlePlayerDeath` (entirely separate from the
> AI soft-kill path, per the "watch out" below). A death with lives remaining
> decrements `Game_Lives` and calls `Game_State_RespawnPlayer` — full HP, zeroed
> hit-stun/facing/animation-selection, placed at the camera's left edge, and
> `Player_InvulnFrames` armed (90 frames, ~1.5s) so the respawn can't be
> instantly re-hit (`Character_HitApply_VsPlayer` early-outs while it's
> nonzero). No death animation exists in the MSU roster (idle/walk/attack
> only), so the existing generic hit-stun reaction stands in for it, per this
> section's own allowance. Exhausting the last life enters
> `GAME_STATE_GAMEOVER` with a 300-frame (~5s) continue countdown; Start
> restores fresh `Game_Lives` and full HP and returns to `GAME_STATE_PLAYING`;
> letting the countdown expire falls back to `GAME_STATE_TITLE`. Gate:
> `tools/verify/game_g3_death.py`.
>
> **`GAME_LIVES_START` is 20, not a small arcade-style number** — deliberately,
> for gate-suite safety rather than difficulty: with 3, unattended AI combat
> reached `GAME_STATE_GAMEOVER` by ~frame 1200 (measured), and GAMEOVER skips
> `Game_State_Play__playing`'s entire body (no `Core_Oop_Play`/`Core_Oam_Play`/
> streaming) — several existing routine gates run longer than that with no
> player input and would have silently frozen mid-gate on unlucky combat RNG.
> `phase6.py`/`phase8.py`/`phase9.py` were also updated: `phase6.py` accepts a
> `Game_Lives` drop as alternate evidence of damage (a death+respawn can now
> complete inside its test window); `phase8.py`/`phase9.py` force
> `Player_InvulnFrames` during their held-input holds so organic combat can't
> interrupt an unrelated camera/streaming test (`phase9.py`'s held-right
> reliably killed the unprotected player and froze the run's back half,
> confirmed 3/3 runs before the fix — a real confound, not flakiness).
> Re-tune `GAME_LIVES_START` for actual difficulty in a later phase; don't
> lower it without re-checking the long-running gates' total frame budgets
> first.

The player is currently *exempt* from the damage system by design — HP reaches 0
and nothing happens.

### Scope

- Player death at `CHAR_HP == 0`: death animation if the roster has one (it does
  not today — the converter only emits idle/walk/attack, so either extend
  `convert_character.py` to convert a `fall`/`die` animation, or accept a fade).
- Lives counter, decrement on death, respawn at the camera's left edge with brief
  invulnerability.
- `GAME_STATE_GAMEOVER` on last life, with a continue countdown and a Start-to-
  continue path back into the current stage.

### Watch out

- **Do not use `core/oop.pasm`'s generic kill/GC path for the player.** Phase 11
  established why: GC compacts `OopObjRam` and rewrites surviving entities'
  `OopDp`, silently breaking every hardcoded `EntityN_Base` reference. Player
  death must be a soft state on entity 0, exactly like the AI soft-kill.
- Respawn must reset hit stun, animation selection, and facing — not just HP.

**Gate** (`game_g3_death.py`): force player HP to 0; assert lives decrement, the
state machine reaches `GAME_STATE_GAMEOVER` after the last life, and continue
restores a playable state. Sample animation state at a **prime** frame stride
(37, not 40) — memory `phase15_fourth_character` documents a false FAIL caused by
a sampling stride that divided a character's animation cycle period.

---

## §4 — Phase G4: win condition and stage transition

> **Status: DONE** (2026-08-21). `GATE G4: PASS` (`tools/verify/game_g4_transition.py`).
> A real second stage now exists: `BG_SCREENS`/`FP_SCREENS`/`SPAWN_TABLES`
> (`build_rom.py`) are parallel lists — index 0 is stage 1B ("The bar",
> unchanged since Phase 14), index 1 is stage 1A ("The street", the level
> Phase 14 replaced as the shipped default; its converted assets stayed
> committed the whole time for exactly this). The hand-synced
> `SPAWN_MSU_OFFSET`/`SPAWN_COUNT` constants this section's own "watch out"
> flagged are gone entirely — `pack_msu_roster.py`'s bg record grew a v6
> spawn_offset/spawn_count pair (hung off the record it belongs to, same
> pattern v5 used for `fp_offset`), and `core/spawn.pasm`'s `Spawn_Init` now
> reads its stage's own offset/count from WRAM cells `Bg_LoadScene`
> populates every load, boot and transition alike — no build-time
> `check_spawn_constants()` needed any more (deleted). Win condition: queue
> exhausted (`Spawn_Index == Spawn_Count`) AND all three AI entities'
> `CHAR_HP == 0` unlocks the camera's `Screen_MaxX` from a pre-clear soft
> hold (derived from `Spawn_LastTriggerX`, the stage's own last spawn
> record's trigger position — not a hand-authored "combat zone" table);
> reaching that newly-unlocked true edge is the real stage-clear trigger.
> `Stage_Load` (`core/game_state.pasm`) is a full, blocking, boot-style
> reload — deliberately NOT the live per-frame streaming path, which is
> designed for small per-frame deltas, not swapping an entire level at
> once.
>
> **Real bug found and fixed via this gate, not by inspection:**
> `Bg_LoadSceneFp_Streaming`'s CGRAM palette write (unconditional CGADD=4
> before a 24-byte loop, unchanged code that works fine at boot) landed
> scrambled — some colors correct-value-wrong-slot, others simply
> unwritten — every time it ran via `Stage_Load` instead of only at boot.
> Root cause: `sei` does **not** mask NMI (memory
> `nmi_handler_no_register_save_reentrancy` had already flagged this exact
> gap as "unverified"), and NMI genuinely IS enabled during a live-gameplay
> stage transition (unlike at boot, where `Core_Nmi_Init` hasn't run yet —
> the same `sei`-only pattern in `Bg_LoadScene`/`Bg_LoadSceneFp_Streaming`
> is safe there for that reason alone, not because `sei` itself helps). A
> real vblank landing mid-load fired `Core_Nmi_Play`, which writes CGRAM
> color 0 every vblank, scrambling the FP loader's own auto-incrementing
> CGADD sequence. Fixed with `Core_Nmi_Stop`/`Core_Nmi_Start`
> (`core/nmi.pasm`) — both already existed, already documented for exactly
> this ("useful around a sequence that would be corrupted by an NMI firing
> mid-way through"), and had never had a real caller before this phase.
> `Stage_Load` also force-blanks the screen for the same VRAM/CGRAM-write-
> during-active-display reason boot gets for free by having the screen off.
>
> Both `tools/verify/phase8.py` and the new `game_g4_transition.py` needed
> to explicitly work around the new pre-clear camera hold to test what they
> actually test (raw camera clamp mechanics, not the win condition) — see
> `phase8.py`'s own comment on why forcing `Stage_Cleared=1` without also
> overwriting `Stage_TrueMaxX` triggers a REAL stage transition mid-test
> (reproduced once, then fixed).

The piece that makes a *second* level exist.

### Scope

- **Win condition.** BOR's is "all spawned enemies defeated and the level's spawn
  queue is exhausted, then reach the right edge." `core/spawn.pasm` already tracks
  queue position; the missing half is an "all AI slots dead AND queue exhausted"
  check, then unlocking the camera's right clamp.
- **Stage clear → transition.** `GAME_STATE_STAGECLEAR`, then tear down the
  current level's streaming caches and load the next.
- **A stage table.** `BG_SCREENS` is a single hardcoded tuple today. Generalize to
  an ordered list with per-stage BG / frontpanel / spawn-table / music, and a
  `Game_StageIndex`.

### Watch out

- This is the phase where **`SPAWN_MSU_OFFSET`-style hand-synced constants stop
  scaling.** Every stage added shifts every later `bor.msu` offset. The build
  already guards one such constant (`check_spawn_constants`); with N stages this
  needs to become a real per-stage directory read at runtime, like
  `CharSelect_RosterCount` already is. **Do that here, not later.**
- Tearing down and reloading both streaming caches (`stream_cache.pasm`,
  `stream_cache_fp.pasm`) mid-run has never been exercised — they are only ever
  initialized at boot. Expect real bugs, and re-run `phase9_syncscroll_test2.py`
  and `phase10_frontpanel.py` (the non-routine, real-wall-clock gates) after.

**Gate** (`game_g4_transition.py`): clear stage 1, assert the transition fires,
the next stage's tilemap matches *its own converter output* (not stage 1's), and
the streaming caches are consistent after reload.

---

## §5 — Phase G5: menus

> **Status: PARTIAL** (2026-08-21) — title screen only. `GATE G5: PASS`
> (`tools/verify/game_g5_menus.py`). Per an advisor consult for this phase:
> `GAME_STATE_PLAYING` stays the boot default (flipping it would mean editing
> every existing gate to press Start/force-write `Game_State` first); TITLE
> is exercised the same way `game_g2_states.py` already does, a forced
> `Game_State` write, and is organically reachable via a real GAME OVER
> timeout (Phase G3) — this phase gives that stop actual content without
> changing when it's entered. `core/game_state.pasm`'s `Game_State_Play__title`
> is a `Title_Step`-driven multi-frame drip (draw title row → draw "PRESS
> START" row → wait for Start → clear both rows → PLAYING), **not** a
> single draw-everything-on-entry routine — `core/text.pasm`'s
> `Core_Text_DrawString` shares one WRAM staging buffer with a QUEUED (not
> synchronous) DMA, so two calls in the same frame corrupt each other (the
> documented "1024-BOR" bug). Every string drawn fills the full 32-column
> BG3 row (real text padded with trailing spaces), sidestepping a related
> hazard: TextStaging's untouched columns hold whatever a *previous*
> DrawString call (to a different row) left there, so a short string alone
> would leave stale garbage in the columns past its own text.
>
> Character select was explicitly **not** built here — CLAUDE.md and G2's own
> header both say the hard-coded `CharSelect_Index` roster is to be phased
> out as `plan_vm.md` gates land, not invested in further. Pause menu content
> is also deferred (the state already freezes correctly since G2; it
> collides with `core/text.pasm`'s own documented BG3-frontpanel-vs-text
> unresolved question, so it isn't bundled with a phase that didn't need to
> touch that). Options (SRAM persistence) untouched.
>
> **ROM budget note:** this phase's ~6-byte boot-time `Title_Step` zero-init
> in `scpu_boot` overflowed the fixed `$FC00`-region budget by exactly 6
> bytes (Poppy's overlap error caught it immediately, per CLAUDE.md's
> "errors now instead of silently truncating"). Fixed the same way four
> prior pushes in this file's history did: `nmi_handler`/`irq_handler` moved
> `$FF90`/`$FFA0` → `$FFA0`/`$FFB0` (`build_rom.py`'s NMI/IRQ vector
> constants updated to match — still comfortably below `$FFE4`). Separately,
> the title dispatch's own code size pushed several existing `Game_State_Play`
> top-level `beq`s (to `__playing`/`__paused`/`__gameover`) out of the real
> 65816 ±127-byte conditional-branch range — fixed by converting every
> top-level state check (and the title step-machine's own inner dispatch) to
> a short `bne`-past-a-`jmp` pattern instead of a direct `beq`, since `jmp`
> has no range limit.

Now that text exists (G1) and states exist (G2), these are mostly content.

- **Title screen** — logo (convert BOR's own title art through `convert_bg.py`),
  "PRESS START", attract-mode timeout optional.
- **Character select** — the roster already supports 8 slots, loads at runtime
  from the `.msu` header, and Select already cycles it live. This is largely
  re-skinning existing machinery as a proper screen with portraits and names.
- **Pause menu** — freeze on Start during play; resume / restart / quit.
- **Options** — music/SFX volume (MSU-1 volume is `$2006`; TAD has its own),
  difficulty (the pak ships EASY/NORMAL/HARD variants of every stage, so this maps
  directly onto which level file the converter packs), controls.

**Watch out:** persisting options across a reset needs SRAM. The ROM header
already declares battery-backed RAM (`$35`, RAM size `$08`) but nothing uses it.
Note: **roster-slot persistence specifically was declined and is not wanted** —
it is not part of Beats of Rage. Options persistence is a different question and
is genuinely expected.

**Gate** (`game_g5_menus.py`): navigate each menu via `set_input`, assert the
selected index and the resulting state transition.

---

## §6 — Phase G6: score, lives, and a real HUD

> **Status: DONE, 2026-08-21.** `GATE G6: PASS`
> (`tools/verify/game_g6_hud.py`). The 3 raw AI HP bars are gone -- no
> "currently engaged enemy" concept exists without a boss to justify one
> (deferred to G9, whose own first prerequisite, per-entity HP override,
> was already satisfied by the health-override slice between G8 and G6).
> Row 0 keeps the player's own bar unchanged; rows 1-3 (freed by dropping
> the AI bars) now show SCORE/LIVES/STAGE, each independently dirty-gated
> and redrawn at most one row per frame (checked in that priority order --
> the common case, score changing on every hit, draws immediately; a
> same-frame lives/stage change is simply caught the very next frame,
> self-correcting with no explicit step machine needed).
>
> New primitive `Core_Text_DrawLabeledNumber` (`core/text.pasm`) draws a
> short label immediately followed by a decimal value (no leading zeros)
> then blanks every remaining column through 32, all in ONE
> `Text_FlushRow` -- built specifically so a scoreboard row never needs
> the 2-calls-across-2-frames drip plain `DrawString`+`DrawNumber` would
> require (that file's own documented TextStaging-sharing hazard), and so
> a shrinking value can never leave a stale trailing digit from a longer
> previous draw.
>
> Scoring: `Character_HitApply_VsEntity1/2/3` (the player-lands-a-hit
> leaves) now `jsr Game_Score_Award` right after their existing HP-clamp
> step -- `HIT_SCORE` (10) always, `+KILL_SCORE` (90, a round 100 total)
> when that hit also brings the target to exactly 0 HP. `Game_Score_Award`
> also checks whether the addition crossed a new `EXTEND_LIFE_SCORE`
> (5000) multiple and, if so, awards +1 `Game_Lives` -- reuses
> `Core_Math_Div` (already used by `Text_DrawNumber__digit`) rather than a
> new divide routine. `Character_HitApply_VsPlayer` (AI hits the player)
> deliberately never calls this -- no score for taking damage. `Game_Score`
> is a real, new piece of game state (`core/game_state.pasm`, alongside
> `Game_Lives`/`Game_StageIndex`), clamped at 65535 (not wrapped --
> `Core_Text_DrawNumber` only draws 16-bit values, a real documented
> display ceiling), persists across a GAMEOVER continue (only zeroed at
> boot, matching classic arcade convention of keeping score but resetting
> lives on continue).
>
> **Real gate-writing lesson, not an engine bug**: an early version of
> `game_g6_hud.py` tried forcing `CHAR_SELECTED=2` directly via WRAM write
> to simulate "the player is attacking" -- silently never worked, because
> `Anim_Play` (which runs before `Character_HitApply` every frame, per
> that routine's own header) recomputes `CHAR_SELECTED` from real button
> state and clobbers a forced value before `Character_HitApply` ever sees
> it. Fixed by driving a REAL `m.set_input(m.BTN_Y, ...)` Y-press instead
> (the player's own attack trigger has no proximity check, unlike the AI's
> seek/attack range, so overlapping position + a real press reliably
> lands a hit). A second, separate gate-writing pitfall: real background
> AI combat is already underway by the time any gate reaches frame 300,
> and a stunned player (`CHAR_HIT_STUN > 0`) ignores the attack-button
> trigger entirely -- the gate now neutralizes entities 2/3
> (`CHAR_HP := 0`, sticky per the soft-kill design) once and clears the
> player's own `CHAR_HIT_STUN` before every forced attack.
>
> **Deliberately not done** (see this session's plan file for the full
> reasoning): a specific `1up`-named prop granting an extra life directly
> (needs the spawn record to distinguish `1up` from `trash`/`table`/
> `chair`, which it doesn't today -- natural small G8 follow-up now that
> a score/lives system exists to award into); a boss health bar and the
> `boss` flag itself (G9); a currently-engaged-enemy indicator.
>
> Full regression suite passes, including a real fix in
> `game_g4_transition.py` and `pack_msu_roster.py`/`vm_load.pasm`
> resyncing needed by the earlier health-override slice's own record-size
> growth (unrelated to this phase, caught in the same session).

The HUD used to be four raw HP bars — a debug view, not a game HUD. Player
HP bar, lives, score, stage number, and score-on-hit/kill with an
extend-life threshold are now real (see the status block above). Uses G1's
text renderer throughout; `Hud_Play`'s dirty-gating (it enqueues nothing on
a frame where nothing changed) is the right pattern and was kept and
extended, not replaced, since the DMA queue has 8 slots and one entity
frame-load already takes 6.

---

## §7 — Phase G7: the real BOR moveset

> **Status: PARTIAL (first two slices DONE, 2026-08-22).** `GATE G7-RUN:
> PASS` (`tools/verify/game_g7_run.py`), `GATE G7-INVULN: PASS`
> (`tools/verify/game_g7_invuln.py`). Run/dash shipped first, deliberately,
> because it's the only item below that needs no new animation content —
> OpenBOR's own reference (`openbor_script_reference.txt:982`) treats run as
> walk/idle frames driven at higher velocity, not a distinct move, so this
> was implementable as a pure speed modifier on the existing walk code.
> Holding B now doubles the player's per-frame movement speed. Implemented
> entirely inside `Character_PlayFrame`'s existing `__right`/`__left`/
> `__down`/`__up` blocks in `main.pasm`: after the existing
> `adc`/`sbc #PLAYER_SPEED` step and before the existing clamp, a held-B
> check (`Input_press` bit15 in the 16-bit X blocks, `Input_press+1` bit7 in
> the 8-bit Y blocks — B was the one button in the already-read input byte
> nothing else claimed) conditionally applies a second
> `adc`/`sbc #PLAYER_SPEED`, `pha`/`pla`-stashing the post-first-step value
> across the test. **NOT player-only for free — this project's own first
> assumption here was wrong, caught by pre-commit review, not by the gate
> as first written.** `__right`/`__left`/`__up`/`__down` are shared code:
> `__ai_x`/`__ai_y` (above these blocks in the same routine) deliberately
> reuse them for AI-driven entities, and only the *dpad dispatch*
> (`__dpad_x`/`__dpad_y`) is gated on `CHAR_INPUT_DRIVEN==1` — `Input_press`
> itself is a global controller read with no entity context. A version of
> this change without a mode check inside the movement blocks themselves let
> every AI entity run at 2x speed whenever the player merely held B. Fixed
> by adding an explicit `CHAR_INPUT_DRIVEN==1` check directly inside each
> movement block (in the 16-bit X blocks this means narrowing to 8-bit
> around the check — A is already saved via `pha` — then widening back
> before the `pla`; the already-8-bit Y blocks needed no width toggle). No
> new struct field either (the entity struct is fully packed, no spare byte,
> and `Entity1/2/3_Base` are hand-synced literal offsets, another reason to
> avoid touching it). No converter/roster/MSU changes.
>
> **Real cost hit doing this**: inserting the new branches pushed several
> pre-existing `bra`/`beq` instructions in this routine out of 8-bit branch
> range against their targets (`Character_PlayFrame__hold`/`__hold_y`) —
> this project has hit this exact class of cost before when widening this
> routine (see Phase 8's own history). Fixed by converting the `bra`s to
> `brl` directly, and the `beq`s by inverting the condition and branching
> around a `brl`.
>
> New gate `tools/verify/game_g7_run.py`: measures the actual position delta
> over a held walk vs. a held run(+B) window of identical nominal length and
> asserts a ~2x ratio, rather than exact frame-count arithmetic — an earlier
> version of this gate tried predicting the exact pixel delta from
> `Nmi_FrameCounter`-measured elapsed frames and found the per-frame rate
> itself never hit exactly `PLAYER_SPEED` (this project's own
> `mesen_set_input_wall_clock` lesson: `set_input`'s frame count is a
> wall-clock lower bound, not exact), even though the walk-vs-run *ratio*
> came out clean (exactly 2.0 on both X and Y once the Y-axis measurement
> window was fixed to not saturate `PLAYER_MAX_Y` — an earlier version of
> the gate had silently been measuring the clamp, not run speed, on Y).
> Also asserts holding B alone (no dpad) never moves the player, and —
> the check that actually catches the AI-speed bug above — that a forced,
> actively-seeking AI entity's movement rate is unchanged whether or not the
> player holds B (measured with matched `set_input` calls on both arms;
> mixing `set_input` and `run_frames` for the two arms was tried first and
> produced a false failure, since the two helpers advance the emulator
> through different, not-exactly-frame-equal paths). Full regression suite
> passes (`audit_all.py`, `check_label_drift.py`,
> `check_width_directives.py` — zero new violations, `phase5.py`–`phase8.py`,
> `phase11_damage.py`, `phase12_roster.py`).
>
> **Second slice DONE, 2026-08-22: post-hit invulnerability frames (AI
> entities).** `GATE G7-INVULN: PASS` (`tools/verify/game_g7_invuln.py`).
> Generalizes the "brief can't-be-re-hit window" concept BOR's own combat
> has, but as a **parallel, AI-only** mechanism — the player's existing
> `Player_InvulnFrames` (`core/game_state.pasm`, armed only on respawn) is
> deliberately untouched; five existing gates depend on its exact semantics
> as a manually-armable "god mode" knob. `Character_HitApply_VsEntity1/2/3`
> previously had no invuln check at all, only a dead-target (`HP==0`) skip —
> a landed hit now also stamps a new per-entity invuln cell to
> `AI_POST_HIT_INVULN_FRAMES` (`CHAR_HIT_STUN_FRAMES + 12`, i.e. it
> deliberately outlasts stun by a fixed grace window) alongside the existing
> `HitStun` stamp, and a subsequent hit is suppressed (reuses the
> `__dead_skip` label's bare-`rts` "no hit landed" shape) for as long as that
> cell is nonzero.
>
> **Real regression found and fixed mid-implementation, not by design
> review:** the first implementation added this as a new `CharacterEntity`
> struct field (`CHAR_INVULN`, struct offset 36, `CHAR_ZP_LEN` 36→37) —
> exactly the same kind of change Phase 6 made once before adding `CHAR_HP`,
> and `audit_all.py` already auto-verifies the three hand-synced
> `EntityN_Base` literals against `CHAR_ZP_LEN`, so this looked safe. Build
> was clean and every static check passed. But `phase5.py`/`phase6.py`
> failed at runtime: growing `CHAR_ZP_LEN` shifts every entity's *absolute*
> WRAM address, and this flipped which physical slot the boot-time spawn
> table landed an AI in — entity 1 stayed a "prop" instead of becoming a
> live AI enemy, entity 3 never spawned. **Fix: don't grow the struct.**
> Reimplemented as three standalone WRAM scalar bytes
> (`Entity1/2/3_InvulnFrames`, `core/game_state.pasm`, declared and
> decremented the same way `Player_InvulnFrames` already is — decrement
> lives in `Game_State_Play__playing`, NOT in `Anim_Play`'s per-entity
> dispatch, since there's no per-entity DP context out there) — zero WRAM
> layout change for anything else, and the regression disappeared. General
> lesson: in this codebase, growing the entity struct is not safe by
> default even with the audit's literal-sync check passing; prefer a
> standalone cell (mirroring how `Player_InvulnFrames` itself already lives
> outside the struct) for anything that doesn't need per-entity DP-relative
> addressing.
>
> New gate's own timing lesson: `set_input(BTN, N)`'s wall-clock/sleep-based
> overrun (`mesen_set_input_wall_clock` project memory) easily burns more
> real frames than the 24/36-frame stun/invuln windows this gate needs to
> observe mid-decay — a first version using `set_input(BTN_Y, 10)` +
> `run_frames(20)` settle windows saw the invuln cell already decayed by the
> time it read state. Fixed by throwing each attack with a single minimal
> `set_input(BTN_Y, 1)` (just enough to register the edge-triggered press)
> followed by frame-exact `run_frames(1)` polling every single frame until
> the hit visibly lands. Full regression suite passes (`audit_all.py`,
> `check_label_drift.py`, `check_width_directives.py` — zero new violations,
> `phase5.py`–`phase8.py`, `phase11_damage.py`, `phase12_roster.py`,
> `game_g1_text.py`, `game_g2_states.py`, `game_g3_death.py`,
> `game_g4_transition.py`, `game_g5_menus.py`, `game_g6_hud.py`,
> `game_g7_run.py`, `game_g8_props.py`).
>
> **Converter extended, 2026-08-22 (asset-pipeline only, no gameplay yet)**:
> `convert_character.py` now also converts `fall`/`rise` (knockdown/getting-up)
> for all 4 roster characters, sharing the same unified palette idle/walk/
> attack1 already use. See the bullet list below for what's still needed
> before this ships as a real gameplay feature (roster-record format growth +
> engine dispatch wiring + a knockdown-trigger design, none done yet).
>
> **Struct-growth regression root-caused and fixed, 2026-08-22**: the
> `CHAR_ZP_LEN` growth regression above (line 579-600) was worked around by
> avoiding struct growth, not root-caused, at the time. A dedicated
> prerequisite investigation (see `struct_growth_regression_root_cause`
> project memory) found the real cause: `core/vm/vm_native_engine.pasm`'s
> `Vm_NativeEntityByteOff` table was a **hardcoded literal**
> `.dw 0, 36, 72, 108` — a fourth, previously-unknown hand-synced copy of the
> entity byte-stride, entirely separate from `EntityN_Base` and invisible to
> `audit_all.py`'s literal-sync check. The VM's `spawn()`/
> `changeentityproperty()` natives (driven by the Gate 6 SPAWN000.C test
> script, which runs unconditionally every frame via `Vm_Run` ahead of
> `Spawn_Play`) used this stale-stride table to write into the wrong
> entity's memory whenever `CHAR_ZP_LEN` grew — colliding with
> `core/spawn.pasm`'s own placement. Fixed by deriving the table from
> `CHAR_ZP_LEN` symbolically (`.dw 0, CHAR_ZP_LEN, CHAR_ZP_LEN*2,
> CHAR_ZP_LEN*3`); verified 3x-deterministic PASS on `phase5.py`/`phase6.py`
> at both a +1 byte and a +10 byte throwaway struct growth, then reverted
> the throwaway growth and re-ran the full regression suite clean at the
> shipped 36-byte size. **Struct growth is now verified safe** — the
> invuln-frames slice's standalone-cell workaround (line 589-600) was a
> reasonable choice for that slice but is no longer a required pattern; the
> fall/rise slice below may grow `CHAR_ZP_LEN` directly if that's the
> better design, without re-triggering this class of bug.
>
> **Knockdown/getting-up wired, 2026-08-22.** `GATE G7-KNOCKDOWN: PASS`
> (`tools/verify/game_g7_knockdown.py`, 3 checks). Reproduces OpenBOR's real
> `checkdamagedrop()`/`set_fall()`/`common_lie()`/`set_rise()` state machine
> (traced from `rofl0r/openbor-legacy`'s actual C source, not invented — see
> that gate's own module docstring for the full sourced derivation and NTSC-
> frame conversions), NOT a "fatal hit only" or "every hit knocks down" rule
> the user explicitly rejected mid-slice. `pack_msu_roster.py`'s record grew
> fall/rise frame-count/delay into its existing spare padding bytes (no
> `data_offset` ripple); `CharacterEntity` struct grew 36→49 bytes
> (`CHAR_KNOCKDOWN_COUNT`/`_TIMER`, `CHAR_FALL_STATE_TIMER`, fall/rise
> fcount/delay/base fields) using the struct-growth fix confirmed safe above.
> `attack1`'s own real `attack_drop` is authored 0 for all 4 roster
> characters (confirmed against the source pak) — a killing blow alone still
> reaches the fall reaction (real OpenBOR: `health<=0` independent of
> knockdown force), but the *non-fatal* accumulation path is dormant until a
> future drop-carrying move (Ralf's `upper`, Joe's `grab`, Jhun's
> `jumpattack` — none implemented) exists; verified via a debug-only forced
> `CHAR_KNOCKDOWN_COUNT` write in the gate, never a fake in-game trigger.
> Props (`CHAR_INPUT_DRIVEN_PROP`) are deliberately exempted from the fall
> reaction — always take ordinary stun instead, since this port's props
> share the loaded roster character's asset (no separate prop art) and real
> OpenBOR obstacles have their own death handling.
>
> Two real engine bugs found and fixed by this slice, not by inspection:
> (1) `Anim_Play__ai_seek`'s per-frame attack-trigger re-decision had no
> concept of "already reacting" — it unconditionally stomped a freshly-set
> `CHAR_SELECTED=FALL` back to `ATTACK` on the very next frame, so the gate
> never observed the fall state settle at all until `Anim_Play__not_stunned`
> was widened to also skip re-triggering while `CHAR_SELECTED` is FALL/RISE
> (same "already reacting, ignore input" shape the existing attack-latch
> check already used). (2) `Anim_Play_Fall`'s death-blink state-timer
> decrement originally sat behind the `Msu1_StreamBusy` early-out, so with
> 4 entities contending for the one streaming slot the 120-frame blink
> window and 6-frame blink cycle would stretch under contention instead of
> staying real-time accurate (real OpenBOR ticks this off `borTime`, not
> animation progress) — fixed by moving the state-timer maintenance above
> the streaming gate; only actual frame-streaming still respects the
> one-entity-per-frame budget.
>
> **Structural ROM-budget fix, 2026-08-22** (not specific to this slice, but
> landed alongside it after 3 repeated bank-0 `$C100`-`$FC00` overflows):
> `core/spawn.pasm` (its only two entry points, `Spawn_Init`/`Spawn_Play`,
> both `jsr`'d from bank 0, zero internal `jsr` fan-out of its own) was
> relocated whole into its own `.bank 3`, reached via `jsl`/`rtl` instead —
> freed ~1.5KB of bank-0 headroom (previous fixes only bought back tens of
> bytes at a time via routine-by-routine extraction to bank 1, which was
> proving to be a treadmill). `game_state.pasm`/`oop.pasm` are the next
> candidates if bank 0 fills again, but call out to many other bank-0
> routines each, so moving those is real follow-on work, not a quick repeat
> of this fix.
>
> Full regression suite clean: `audit_all.py`, `check_label_drift.py`,
> `check_width_directives.py` (zero new violations), `phase5.py`–`phase8.py`,
> `phase11_damage.py`, `phase12_roster.py`, every `game_g*.py` gate including
> the new `game_g7_knockdown.py`.
>
> **A real second attack move shipped, 2026-08-23** (`GATE G7-ATTACK2: PASS`,
> `tools/verify/game_g7_attack2.py`, 16 checks). Investigation first found
> jump/block/special have NO real anim in the source pak for any of the 4
> roster characters — nothing to convert, art-authoring blockers, not
> engine slices. But RALF (`upper`)/JOE (`grab`)/JHUN (`jumpattack`) each
> already had one real extra move, converted and inert since the moveset-
> generalization slice below. The user was asked whether to route this
> through the VM (the prior deferral's own plan) or build it hand-written;
> mid-research, direct `BOR.C` inspection showed real OpenBOR player-move
> dispatch (including grab) is native C (`player_grab()`, a `self->think`
> function-pointer state machine), never script-driven — routing it
> through `openborscript` would be non-canonical. User confirmed:
> hand-written, matching how BOR.C itself does it.
>
> **Deliberately NOT real grab semantics.** Real `grab` is a mutual
> entity-lock triggered by movement collision (position averaging,
> `ents_link`), not a button. This slice ships the generic `attack2` role
> (resolved by exclusion — first anim beyond the 6 known roles — not
> hardcoded to any character name, `convert_character.py`) as a second
> attack move: same `Character_HitApply` CHAR_SELECTED==2 damage check
> attack1 already uses (confirmed no attack-variant-specific code exists
> there — zero changes needed), triggered by X (free, unused elsewhere:
> Y=attack1, B=run, Select=roster cycle). Full mutual-lock grab semantics
> remain future work, called out the same way jump's Z-axis need is.
>
> **No `RECORD_SIZE` growth.** `pack_msu_roster.py`'s roster record
> repurposed its last 2 reserved bytes for `attack2_frame_count`/`delay`,
> and attack2's variable-length frame data was inserted into the blob
> right BEFORE the existing remap-palette section (not after) — so
> `map_base`'s existing chain (`rise_base + rise_frame_count*768`) just
> gained one more hop (`attack2_base = rise_base + rise_frame_count*768`;
> `map_base = attack2_base + attack2_frame_count*768`, collapsing back to
> the old formula exactly when attack2_count==0). Zero ripple into
> `HEADER_SIZE`/character `data_offset`s/the BG directory — only the real
> new frame bytes shifted `VM_MSU_OFFSET`, needing the same
> `check_vm_constants` resync the `map` slice already established as
> routine. `CharacterEntity` grew 56→62 bytes
> (`CHAR_ATTACK2_FCOUNT/DELAY/BASE_LO/HI`, `CHAR_ATTACK_VARIANT`) — struct
> growth pre-verified safe by `struct_growth_regression_root_cause`,
> re-confirmed clean by the full phase suite. `Anim_Play_Attack` gained a
> duplicated (not parametrized — matches this file's own existing style
> for variant-selected blocks) tail for the attack2 case. AI is untouched
> (attack2 is player-only in this slice, same restraint G7's run/dash
> first slice used before broader generalization was confirmed safe).
> Full regression suite clean (build, `audit_all.py`, `check_label_drift.py`,
> `check_width_directives.py` — 2 new sites baselined with explicit
> width directives, zero silent violations, phase5–phase9/11/12, every
> `game_g*.py`/`vm_gate*.py` gate; `game_g7_knockdown.py`'s pre-existing
> flaky check reproduced its documented 2/3 pass rate, unrelated to this
> slice).
>
> **Still fully open** (all need new animation content the converter doesn't
> produce today — see "Content dependency" below): jump/jump-attack (the
> largest remaining item, needs a Z axis and forces Y-sorted depth priority),
> real grab/throw mutual-lock semantics, special, block.
>
> **Moveset pipeline generalized, 2026-08-22** (before any of the above was
> attempted). User explicitly rejected scoping "give Ralf a real second move
> (uppercut)" as the next slice: *"no. not just uppercuts. you're being too
> specific. this should all be generalized... you're also going to be
> running turtles, and whatever else might get converted by the scripts."*
> `convert_character.py`'s old `ANIMS` list hardcoded exactly
> `[idle, walk, attack1, fall, rise]`; real pak data measured directly shows
> BOR has 20 distinct anim names across 45 characters (max 19/char), TMNT 24
> names across 81 characters (max 21/char), DDM 80 names across 227
> characters (max 33/char) — no fixed list can cover this.
>
> Fixed: `convert_character.py` now enumerates every `anim <name>` block a
> character's real `.TXT` declares (via `entity_parse.py`, already generic),
> converts each to its own ordinal-indexed directory, and writes a
> `<prefix>_moveset.json` manifest resolving the engine's 6 known roles
> (`idle`/`walk`/`pain`/`fall`/`rise`/`attack` — `attack` matches the first
> declared `attack*`-prefixed anim, since OpenBOR's own convention reserves
> `attack1` for the base attack) to real ordinals, `None` if a character
> lacks one. No move or animation name appears in any `.pasm` file — name
> matching happens exactly once, in this Python manifest step.
> `pack_msu_roster.py` now reads that manifest and resolves role
> directories generically instead of assuming fixed `<prefix>_{idle,walk,
> attack,fall,rise}` names.
>
> **Scope was deliberately bounded** (see the approved plan and advisor
> review that shaped it): this slice eliminates the *hardcoding*, not adds
> multi-move combat. `main.pasm` needed **zero changes** — verified by
> regenerating all 4 shipped characters with the new converter and diffing
> every resolved role's `(frame_count, delay)` against the pre-change
> values: all 20 values (4 chars x 5 roles) matched exactly, so the packed
> record's existing fixed idle/walk/attack/fall/rise layout (`RECORD_SIZE`
> still 16) still gets fed the right numbers. Non-role animations each
> character's real data also has now (`pain` for all 4; `upper` for RALF,
> `grab` for JOE, `jumpattack` for JHUN — YASHIRO has none) are converted
> and listed in the moveset manifest but deliberately excluded from the
> packed MSU blob — nothing downstream reads them yet, and multi-move
> dispatch is explicitly deferred to whenever `plan_vm.md`'s script VM is
> wired to drive `CHAR_SELECTED` (or a future scoped slice), not built here
> as a second hand-written non-VM combat system. Full regression suite
> clean (`audit_all.py`, `check_label_drift.py`, `check_width_directives.py`,
> `phase5`–`phase9`, `phase11_damage`, `phase12_roster`, every `game_g*.py`
> gate). `game_g7_knockdown.py`'s rise->idle check is confirmed flaky
> independent of this change (reproduced both failing and passing 3/4 runs
> against byte-identical ROMs, isolated via a throwaway `git worktree` at
> the pre-generalization commit) — not a regression, see
> `moveset_pipeline_generalization` project memory.
>
> **Level-content prop/item classification generalized, 2026-08-22**
> (follow-up asked for by name — "what else is not generalized?" /
> "do 1 now"). `tools/bg_converter/build_spawn_table.py`'s entity-kind
> classifier was a hardcoded name set, `PROP_CHARACTER_NAMES = {'1up',
> 'trash', 'table', 'chair'}`, explicitly documented in G8's own status
> block as "BOR-only... TMNT hasn't been converted at all yet, so its own
> decorative prop names are a follow-up." Real entity `.TXT` files already
> self-declare this via their own `type` line (measured directly: BOR has 8
> `obstacle` + 6 `item` characters, TMNT has 19 `obstacle` + 7 `item`, not
> overlapping BOR's list at all — e.g. `hydrant`/`mail`/`epole`/`crate`).
> `build_type_lookup()` now reads each spawned character's real `type` from
> its own entity file at spawn-table build time (`obstacle`/`item` = prop,
> everything else = enemy) instead of a name list. Verified zero-regression
> by regenerating both shipped stages' spawn tables and byte-comparing
> against the committed `out/spawn_stage1a`/`1b` binaries (identical) before
> also confirming the lookup correctly classifies TMNT's real prop/item
> roster (never shipped, never tested before) with no TMNT-specific code.
> Note: level/stage content's *other* generalization gap — `level_parse.py`
> discarding real `openborscript` — turned out on investigation to be moot
> for BOR/TMNT specifically (both have zero script content anywhere, level
> or entity; only DDM's paks use `script`/`aimove`/`aiattack`, confirmed by
> direct pak scan), so that part is deferred to `plan_vm.md`'s own gated
> track rather than duplicated here.

Currently: walk, run, and one attack. BOR Original has considerably more, and
this is what separates "tech demo" from "beat-'em-up."

- **Jump** (and jump attack) — needs a Z axis / ground-plane model the engine does
  not have. This is the largest single combat item.
- **Grab / throw** — proximity grab state, mutual entity locking.
- **Special** (HP-cost screen-clear), **block** if the char has it.
- ~~**Run/dash**~~ — **Done (G7 first slice, 2026-08-22)**, see status block above.
- ~~**Invulnerability frames (AI entities)**~~ — **Done (G7 second slice,
  2026-08-22)**, see status block above. Player's own respawn-invuln
  mechanism was already there since G3.
- ~~**Knockdown, getting up**~~ — **Done, 2026-08-22**, see status block
  above (`GATE G7-KNOCKDOWN: PASS`). Reproduces OpenBOR's real fall/lie/
  rise/death-blink state machine; the non-fatal accumulation path is real
  but currently dormant (today's only move has authored `attack_drop=0`)
  until a future drop-carrying move exists.

**Content dependency:** `tools/bor_converter/convert_character.py` converts
idle/walk/attack1/fall/rise (fall/rise added 2026-08-22, wired into the
roster format and engine dispatch the same day — see status block above).
Every OTHER move above (jump, grab/throw, special, block) still needs its
animation converted and packed, which grows each roster slot's `bor.msu`
footprint and re-shifts every downstream offset (§4's note) — same
constraint fall/rise itself was blocked on before this slice.

**Watch out:** a Z axis changes depth sorting. The original spec (§3.6) calls for
Y-sorted priority; today all four entities are plain OAM sprites with no sorting
at all. Adding jump forces this to be solved properly.

---

## §8 — Phase G8: items and pickups

> **Status: PARTIAL (first slice DONE, 2026-08-21).** `GATE G8: PASS`
> (`tools/verify/game_g8_props.py`). This section's own opening claim above
> was **false** and got corrected as part of landing this slice: the spawn
> tables didn't "already silently discard" `1up`/`trash`/`Table`/`Chair` --
> verified against the real, previously-shipped `out/spawn_stage1a/
> spawn_table.bin` (byte-identical to a fresh regeneration from the pak)
> that they were spawning as ordinary full-HP, AI-seeking, attacking
> enemies. Stage 1B (the currently-shipped DEFAULT level) had the same live
> bug with `Table`/`Chair`, both at `trigger_x==0` -- i.e. one was fighting
> the player from frame one of the game everyone actually boots into.
>
> Fixed with a real third `CHAR_INPUT_DRIVEN` mode (`CHAR_INPUT_DRIVEN_PROP
> = 3`, main.pasm): idle-only and never-attacking for free (`Anim_Play`'s
> and `Character_HitApply`'s existing mode-dispatch chains already treat
> anything that isn't mode 1/2 as "static" / "no attack"), but widened to
> get the SAME soft-kill/sprite-hide-at-HP==0 treatment mode 2 (AI) already
> has (`Anim_Play`/`Character_PlayFrame`'s two dead-check gates: `cmp #2 /
> bne` -> `cmp #2 / bcc`, i.e. "mode >= 2" instead of "mode == 2"). The spawn
> record's previously-always-zero "reserved" byte (+6) is now `entity_kind`
> (0=enemy, 1=prop -- fully backward compatible, no format version bump);
> `build_spawn_table.py` classifies `{'1up', 'trash', 'table', 'chair'}` by
> name and gives props a fixed HP of `CHAR_HP_PER_HIT` (one hit kills, never
> partially damaged) instead of `CHAR_HP_MAX`; `core/spawn.pasm`'s
> `Spawn_Play` now writes `CHAR_INPUT_DRIVEN` per-slot (it never did before
> -- every AI slot kept whatever `CharacterEntity_Init` set at boot forever)
> alongside the existing HP write. Both shipped stages' spawn tables
> (`out/spawn_stage1a`, `out/spawn_stage1b`) were regenerated with the fix.
>
> **Deliberately still not done** (see this session's plan file for the
> full reasoning): real prop/pickup sprite art -- a prop renders using
> whichever roster character is already streamed into its slot (visually
> wrong, behaviorally real); score/life/item-reveal reward effects (no score
> system exists yet, G6); TMNT's own decorative prop names (TMNT hasn't been
> converted at all yet); the `boss` flag (`angel`/stage 1A, `Angel`/stage
> 1B -- unrelated to props, still spawn as full-HP AI enemies, see G9);
> weapons.
>
> **Follow-up, same day, a sibling level-format-keyword gap (not itself a
> numbered phase -- `tools/verify/game_health_override.py`, `GATE
> HEALTH-OVERRIDE: PASS`):** `spawn_parse.py` already parsed each spawn's own
> `health <n>` line, but `build_spawn_table.py` discarded it -- every enemy
> spawned at a hardcoded `CHAR_HP_MAX` regardless of the level author's own
> tuning (real values in the shipped pak run 25-100, a percentage-like
> scale). Fixed by growing the spawn record to 8 bytes (`+7 spawn_hp`,
> scaled `health*CHAR_HP_MAX/100`, clamped `[1, CHAR_HP_MAX]`) and having
> `core/spawn.pasm`'s enemy path read it instead of the old immediate; the
> prop path deliberately still ignores it (a prop's HP stays the fixed
> `CHAR_HP_PER_HIT` engine invariant). Both shipped stages' spawn tables
> were regenerated again; `pack_msu_roster.py`'s `SPAWN_RECORD_SIZE` and
> `src/core/vm/vm_load.pasm`'s hand-synced `VM_MSU_OFFSET` both needed
> re-syncing since the record-size change shifted every later MSU offset.

The spawn tables **used to be believed to silently discard non-enemy
spawns** — that turned out to be false, and the entity-kind gap it pointed
at is now half-closed (see the status block above). Still open:

- Breakable props that drop items; health/score/1up pickups (reward effects).
- Weapons (BOR has knives/bats) if the moveset work in G7 lands.
- Real prop/pickup sprite art, converted from the source pak.

Cheap and high-value, since the level data is already there.

---

## §8a — Remaining level-format-keyword gaps (spawn-table/level-parser parity)

**Read this section instead of asking "what's next" for BOR/TMNT parity
work.** Verified 2026-08-21 against the real BOR and TMNT paks: every
level-file keyword either parser reads (`level_parse.py`/`spawn_parse.py`)
but doesn't act on, or doesn't read at all, is listed below in the order to
close them. Each row is self-contained unless its "Blocked by" column says
otherwise — pick the first `NOT STARTED` row whose blocker is `—` or
already `DONE`, plan-mode it (same weight as G8/health-override got), gate
it, update this table's `Status` column and `README.md`'s Current Status,
commit. Do not wait to be told which row is next; that is what this table
is for.

| # | Keyword(s) | What's missing | Blocked by | Status |
|---|---|---|---|---|
| 1 | `entity_kind` (props: `1up`/`trash`/`table`/`chair`) | — | — | **DONE** (Phase G8, 2026-08-21, `game_g8_props.py`) |
| 2 | `health` | — | — | **DONE** (2026-08-21, `game_health_override.py`) |
| 3 | `map` (per-spawn colormap/palette variant, 0-3) | — | — | **DONE** (2026-08-22, gate `game_map_remap.py`, GATE MAP-REMAP: PASS — see `map_keyword_palette_data_done_runtime_hang` project memory for the full story, including a real boot-hang scare that turned out to be a contaminated bisection state, not a real bug). Converter: `convert_character.py`'s `_derive_remap_palettes` derives one real 16-color BGR555 palette per `remap` pair via mode-voting (RALF=3, JOE=3, JHUN=2, YASHIRO=3, matching real pak data); `pack_msu_roster.py` appends them per character blob. Runtime: `CharacterEntity` grew `CHAR_PALETTE_BASE`/`CHAR_MAP_BASE`/`CHAR_MAP_INDEX` (`CHAR_ZP_LEN` 49→56), `Anim_LoadCharacter` computes `map_base` inline, a new `Anim_ApplyMapPalette` (mirrors `Anim_LoadCharacter`'s own palette-load section) is called by `core/spawn.pasm`'s slot1/2/3 dispatch on every spawn (`record_kind`'s spare bits 3-4 carry the map index, same technique `group`'s min/max used). **Verified against ground truth, not just "didn't crash"**: `game_map_remap.py` forces synthetic spawn records (including a JHUN map=1/2 pair, JOE's highest index map=3, a map==0 restore-to-base check, and a combined `SPAWN_KIND_BOSS`+map decode check) and reads back live CGRAM, comparing byte-for-byte against each character's own `<char>_moveset.json` `remap_palettes` — all 10 checks PASS. Full regression suite (build, `audit_all.py`, `check_label_drift.py`, `check_width_directives.py`, phase5/6/7/8/9/11/12) also all PASS. |
| 4 | `boss` flag | `spawn_parse.py` already parses it (`SpawnEvent.boss`). Per-entity HP override (G9's own first prerequisite) is now DONE via the health-override slice. **The flag itself is now real DATA plumbing too** (2026-08-22, "wait/group/boss" slice): `record_kind==4` in the spawn record, read at spawn time into a new sticky `EntityN_IsBoss` WRAM cell — see `core/spawn.pasm`'s own header. Nothing reads that flag yet (no boss HUD, no boss-specific AI, no stage-gating), and it's verified only via a hand-authored synthetic record (`game_g9_wait_group_boss.py`) since neither shipped BOR stage uses `boss` at all — real end-to-end coverage needs TMNT conversion (row 11). G9 itself (boss-specific AI, boss health bar) is the real remaining work. | G6 (HUD, for a boss health bar) | data plumbing DONE, behavior see §9 |
| 5 | `blockade` | **Row's own premise was wrong, corrected 2026-08-23.** There is no `blockade` keyword in real `BOR.C` (Plombo/beatsofrage) at all — grep-confirmed, zero hits. The real keyword in the level-header switch (~line 1966) is **`blocked`**, one letter off, and it is NOT scroll-back prevention: `else if(stricmp(command, "blocked")==0){ level->exit_blocked = atoi(...); }`, part of an entirely different `hole`/`blocked`/`endhole` trio (~line 1961-1971) that implements level PIT HAZARDS (`level->holes[]`, drawn as sprites at runtime ~line 4925-4926, checked for player fall-through ~line 2606-2607) with an exit gated shut until a numeric condition (`exit_blocked`, checked ~line 3105/3998) — not a camera scroll-back ratchet at all. This engine has no pit/hole/fall-through mechanic of any kind today (separate from anything `core/screen.pasm` does), so implementing the REAL `hole`/`blocked`/`endhole` trio is a new hazard-entity feature, not a `Screen_MinX` one-liner. Re-verified 2026-08-23: neither shipped BOR level (`1AEASY.TXT`, `1BEASY.TXT`) uses `hole`/`blocked` at all — real value is entirely gated on TMNT conversion. | Row 11 (TMNT); real semantics need re-deriving as a hole/pit system, not scroll-back | NOT STARTED, premise corrected, low current priority |
| 6 | `music` / `bossmusic` | Fully unparsed. Needs a level-scoped music-track-select on top of TAD (today: one hardcoded audio blob loads at boot, no track switching exists at all). Content-gated like G11 (SFX) — only one track is authored/converted today, so there is nothing to switch *to* yet; do not start the code side before at least a second track exists in the pipeline. | Content (a 2nd authored TAD track) | NOT STARTED (blocked on content) |
| 7 | `alias` | **Not a real gap — document and close, 2026-08-23. This row's own premise was wrong.** Read `BOR.C` directly (Plombo/beatsofrage, repo root, not `engine/`): `smartspawn()` (~line 4589) spawns the entity using the REAL `spawn <name>` argument (`props->name`) first — that's what selects the character model/moveset. Only *after* that does it do `if(props->alias[0]) strncpy(e->name, props->alias, MAX_NAME_LEN);` (line 4593) — `alias` purely overwrites the spawned *instance's* display-name string, for on-screen name UI (`font_printf(... player[i].ent->name ...)` at line 2116, HUD player-select at 2130) — it never redirects which resource is spawned. Confirmed against real TMNT pak data too: `data\CHARS\FOOT01\FOOT01.TXT`/`FOOT02.TXT`/`FOOT03.TXT` are three genuinely distinct character models (own `health`/`speed`/`type` each), each spawned via its own real `spawn Foot01`/`spawn Foot02`/etc. line; `alias Foot_Soldier` just gives all three the same *displayed* name for narrative consistency — there is no `Foot_Soldier` model anywhere in the pak. This project's engine has **no per-entity name display anywhere** (grep-confirmed: `spawn_parse.py` already parses `alias` and its own comment calls it "display name override (cosmetic, unused here)"), so there is nothing for it to attach to — `alias` is a genuine no-op here, same call as row 10 (`maxenemy`). **The real gap row 7 was actually gesturing at — spawns never reading their own `character`/model-name field, always rendering whichever roster character is already streamed into the landing AI slot — is real, but has nothing to do with `alias` and is NOT keyword-slice scope**: `Anim_LoadCharacter` is a blocking boot-time MSU seek+read under forced blank (`CharacterEntity_Init`), `Msu1_StreamBusy`'s one-stream-per-frame budget is load-bearing (CLAUDE.md), and OBJ tile columns are statically per-slot — per-spawn character identity means re-streaming both tiles and palette mid-gameplay, not a small addition. That's `§12` (content and scale) territory, tracked there, not resurrected under this row. | — | N/A — permanent no-op in this engine, not tracked further |
| 8 | `direction` | **Row's own premise was wrong, corrected 2026-08-23 — this is NOT a camera-model-rewrite blocker.** Real `BOR.C`'s parser (~line 1904-1909): `value = findarg(...); if("up") SCROLL_UP; else if("down") SCROLL_DOWN; else if("left") SCROLL_LEFT; else SCROLL_RIGHT;` — exactly 4 recognized values (up/down/left, default right), no "rightleft"/bidirectional case exists anywhere in this source (grep-confirmed: the literal string `rightleft` appears NOWHERE else in `BOR.C`, and `scrolldir` is read as a strict `==SCROLL_LEFT`/`==SCROLL_RIGHT`/etc. comparison everywhere it's used, ~15 call sites checked). TMNT's real `STREETS.TXT` does say `direction rightleft` (confirmed directly against the pak) — but run through THIS engine's actual parser, an unrecognized value silently falls through to the `else` branch: plain `SCROLL_RIGHT`. **TMNT's own `direction rightleft` line is therefore a no-op in this specific engine version** (possibly meaningful in some other/newer OpenBOR fork, but not the Plombo/beatsofrage source this project sources from) — real gameplay is ordinary one-directional right-scroll, which this project's existing camera model (`core/screen.pasm`) already implements. **This row is not a blocker for row 11 (TMNT conversion) at all.** | — | N/A — TMNT's real behavior is plain one-directional scroll this engine already supports; not tracked further |
| 9 | `settime` | **Not a real gap today — corrected 2026-08-23, document and close (same call as row 10 `maxenemy`).** `settime` IS a real keyword (unlike `blockade`/row 5) — it's just not in `BOR.C`'s own level-header parser at all (grep-confirmed: zero hits for `settime`/`maxtime` in the source), meaning this specific engine version doesn't act on it even where a level declares it; the real timer mechanism that exists (`timeleft`/`time_over()`, ~line 4701-4714) always hardcodes a fixed 100-second reset at stage load, never reads a per-level value. **More importantly: real content never actually enables it.** Checked every `settime` occurrence across every available pak — zero in either shipped BOR level, and all 4 real TMNT occurrences (`SEWER.TXT`, `SEWER0.TXT`, `STREETS.TXT`, `STREETS2.TXT`) are `settime 0` (disabled). There is no real content anywhere this project has access to that would ever exercise an enabled time limit — building the HUD timer/time-over path described here would have zero real data to build toward or verify against, a worse case than `blockade`'s "gated on TMNT" (TMNT disables it too). | — | N/A — no real enabled usage exists in any available pak; not tracked further |
| 10 | `maxenemy` | **Not a real gap — document and close.** This engine hardcodes exactly 3 AI slots (`CLAUDE.md`'s "don't build a general entity-lookup system" rule); BOR's own `maxenemy` values in the stock/TMNT levels checked (4) are already satisfied trivially by that hardware ceiling. No code change is applicable here; `SPAWN_MAX_RECORDS`/the single-global-queue design (`core/spawn.pasm`'s own header) already reproduces BOR's wave-clustering behavior within that ceiling. | — | N/A — permanent engine constraint, not tracked further |
| 11 | TMNT pak conversion itself | Not a keyword gap — a content-pipeline task. **Row 8 (`direction`) is cleared, 2026-08-23** (its real behavior for TMNT is plain one-directional scroll this engine already supports — see row 8's corrected entry). Row 3 (`map`) is done. The one real remaining blocker is §12's per-spawn character-identity gap (see row 7's corrected entry): TMNT's whole roster needs spawns to select which character streams into a slot, which doesn't exist for BOR either. Tracked under §12 (content and scale), not here. | §12 character-identity spawning | NOT STARTED, blocked on §12 only |
| 12 | `wait` | — | — | **DONE** (2026-08-22, "wait/group/boss" slice, `game_g9_wait_group_boss.py`) |
| 13 | `group` | — | — | **DONE** (2026-08-22, same slice) |

**Reading order for "what's next" — rewritten 2026-08-23 after re-sourcing
every remaining row directly against `BOR.C`.** Rows 3 (`map`) and 7
(`alias`) were already DONE/closed. This pass found rows 5, 8, and 9 were
ALL built on premises that don't match the real engine source (same class
of error `alias` had): row 5's keyword doesn't exist (real one is
`blocked`, a pit-hazard flag, not scroll-back — closed, needs
re-deriving, not tracked as ready work); row 8 (`direction`) is NOT a
camera-model-rewrite blocker — TMNT's `rightleft` value isn't recognized
by the real parser and silently resolves to plain `SCROLL_RIGHT`, which
this engine already supports (cleared entirely, removed as a row 11
blocker); row 9 (`settime`) is a real keyword but every actual occurrence
across every available pak disables it (`settime 0`) — building a time
limit feature would have zero real content to verify against, closed the
same way row 10 (`maxenemy`) was. Row 6 (`music`) checks out as originally
scoped (real, simple, content-gated — no correction needed). Row 11
(TMNT itself) now only waits on §12's character-identity-spawning gap.

**Conclusion, updated 2026-08-23:** §8a is now genuinely, fully exhausted
— every row is either DONE, a permanent no-op (7, 9, 10), correctly
content-gated (6), or waiting on real remaining work outside this table's
scope (5's real hole/pit system needs re-deriving before it's buildable;
11 waits on §12). There is no more unblocked, self-contained row left to
pick. The next slice is a roadmap-priority choice, not a table lookup:
G7's remaining jump/grab/special items (each blocked on new animation
conversion, real grab needing full mutual-entity-lock semantics), row 5's
real hole/pit hazard system (needs its own semantics re-derivation first),
or `plan_vm.md`'s content-breadth work (script-to-script `CALL` codegen —
the runtime already supports it per Gate 6/7's own header notes; only the
compiler's codegen path is missing, and it's a genuinely large addition,
not a small slice — see `vm_gate7_measured_no_action_needed` memory).
Surface this choice rather than picking unilaterally.

---

## §9 — Phase G9: bosses

> **Prerequisite update, 2026-08-22:** both "per-entity HP override" and
> "the `boss` flag itself" (this section's own first two bullets, below)
> are now DONE — the health-override slice and the "wait/group/boss" slice
> respectively. What's left here is boss-SPECIFIC BEHAVIOR only: nothing
> today reads `EntityN_IsBoss` for anything other than existing as a
> correctly-set flag. See `core/spawn.pasm`'s own header and the
> `wait_group_boss_spawn_mechanics` project memory for what's already real
> vs. still missing, and its explicit synthetic-only-verification caveat
> (no buildable pak exercises `boss` end-to-end yet — only TMNT, not
> converted).

- ~~Per-entity HP override (the spawn table has no HP field today — add one).~~ **Done, 2026-08-21** (health-override slice, `+7 spawn_hp` in the spawn record).
- ~~The `boss` flag itself (`spawn_parse.py`'s `SpawnEvent.boss`, already parsed, not yet threaded into the record or read by the engine).~~ **Done, 2026-08-22** (`record_kind==4`, `EntityN_IsBoss` sticky flag) — real data plumbing, verified only via a hand-authored synthetic record (no shipped BOR stage uses `boss`).
- Boss-specific AI beyond "seek and attack" — still not built, and `EntityN_IsBoss` is not read anywhere yet.
- Boss health bar (G6), stage-gating (camera locks until defeated) — still not built.

`out/bg_boss_level` already exists as converted assets from an earlier phase.

---

## §10 — Phase G10: ending and credits

Stage table exhausted → ending sequence → credits → back to title. Uses G1's text
renderer and G2's state machine; mostly content once those exist.

---

## §11 — Phase G11: SFX (blocked on content, not code)

`soundwork/tad/build/audio-enums.inc` exports exactly one placeholder effect
(`sfx_stub = 0`). **A real punch/hit sound must be authored in the Terrific Audio
Driver project first**; only then is there anything to trigger from
`Character_HitApply`. The engine side is a few lines. This is a content task
wearing a code task's clothes — schedule it accordingly, and do not let it block
anything else.

---

## §12 — Phase G12: content and scale

The two shortcuts from §0 come due here.

- **Stages.** 2 of 14 converted (stage 1A, 1B), 1 shipped at a time. The converter
  pipeline is proven and level-agnostic — Phase 14 swapped levels with *zero*
  engine changes — so this is throughput, not research.
- **Characters.** 4 of ~24 converted. Same story.
- **Enemies on screen.** The `Msu1_StreamBusy` one-stream-per-frame rule caps
  effective animation rate at 1/N. Six enemies means ~10fps animation. Options,
  roughly in order of cost: keep frequently-used frames VRAM-resident instead of
  re-streaming; give the SA-1 a real role in decompression/composition (it is
  currently doing a static test blit); or accept lower animation rates for
  background enemies.
- **2-player co-op.** BOR's headline feature, and the one thing that genuinely
  breaks "the player is always slot 0." Do not attempt it before §7, and treat it
  as its own plan.

---

## §13 — Suggested order, and what is actually hard

**Do in this order** — each genuinely unblocks the next:

```
G1 text  →  G2 states  →  G3 death  →  G4 win/transition  →  G5 menus
         →  G6 HUD  →  G8 items  →  G7 moveset  →  G9 bosses  →  G10 ending
```

**§8a's level-format-keyword rows slot in around G8/G9/G12 specifically** —
see §8a's own table for the exact per-row blockers instead of re-deriving
them here. §8a is now fully exhausted (re-sourced against `BOR.C`
2026-08-23): rows 3/7 DONE; rows 7/9/10 are permanent no-ops; row 5's real
keyword is `blocked` (a pit-hazard flag, not scroll-back) and needs its
own semantics re-derivation before it's buildable; row 6 (`music`) waits
on content; row 8 (`direction`) turned out to be a no-op for TMNT under
this engine's real parser, not a camera-model blocker — cleared; row 11
(TMNT conversion) now only waits on §12's character-identity-spawning gap.

G11 (SFX) slots in anywhere once the content exists. G12 is continuous.

**Genuinely hard** (expect real research and real bugs):
- **G7's jump / Z axis** — changes movement, collision, and depth sorting at once.
- **G4's cache teardown/reload** — never exercised; two streaming caches.
- **G12's enemy scaling** — a real hardware bandwidth wall, not a code smell.
- **2-player co-op** — breaks a load-bearing architectural shortcut.

**Mostly routine** (the pipeline already proves them):
- Converting more stages and characters.
- Menus and HUD, *once G1 exists*.
- Items, since the level data already carries them.

**A note on effort.** Phases 0–15 got the engine here. §§G1–G10 is a comparable
body of work, and G12 is open-ended. That is not a reason to avoid it — it is a
reason to keep taking one phase at a time with a committed verify gate at each
boundary, exactly as this project has done for fifteen phases.

---

## §14 — Rules that apply to every phase here

Inherited from `CLAUDE.md` and fifteen phases of hard-won experience. These are
not optional.

1. **`python build_rom.py` after every change.** No incremental step exists.
2. **`python tools/rom_audit/check_label_drift.py`** after touching any `.pasm`.
   Its original reason (Poppy sizing `jsl` as 3 bytes and emitting 4, drifting
   every later label cumulatively) is **fixed in the current fork** — this is
   now the regression detector for that fix, not defense against a live bug.
   `audit_all.py` is structurally blind to this class regardless.
3. **Apply the Poppy checklist to every new line of assembly — re-measure
   against CLAUDE.md's "Fixed in the fork" table before assuming an item below
   is still live; most of this list is now historical, not active defense.**
   Still live: redundant `sep`/`rep` at every routine and branch-target label
   (poppy#386, the one remaining live bug) and the real 65816 fact that
   conditional branches only reach ±127 bytes (keep them within ~15 source
   lines or invert-and-`brl` — not a Poppy bug, still a hardware constraint).
   **Now fixed, no longer needed in new code**: `nop` guards before labels
   (jsl sizing/label drift fixed), avoiding dot-prefixed local labels (fixed),
   avoiding macros in branch-skipped code (fixed — macros were never actually
   broken here, per poppy_assembler_bugs.md). `.l` vs `.w` for indexed `$7E`
   and `.l Symbol,y` are still correct style (neither addressing mode is valid
   on real 65816 regardless of Poppy), but Poppy now hard-errors on both
   instead of silently mis-assembling, so a mistake here is now a loud build
   failure, not a silent landmine. `plan_vm.md` §0.6 has the full current list
   with rationale.
4. **Watch `.org` region occupancy.** `$C100`–`$FC00` had ~1913 bytes free as
   of 2026-08-16 (re-measure, don't trust this number). Overflow used to be
   silent and corrupt the next region — the current fork now errors on it
   ("overlaps previously emitted bytes") instead, so a *new* overflow will
   fail the build loudly.
5. **Verify against ground truth the engine did not produce** — converter output,
   the packed `bor.msu`, raw ROM bytes. Never trust the engine's own status bytes;
   Phase 7 read `PLAYING` at full volume while loading pure zeros.
6. **Don't accept "probably just flaky."** Several past "nondeterminism" symptoms
   in this codebase were 100%-reproducible logic bugs. Phase 15's was a sampling
   artifact, found by checking rather than shrugging.
7. **Commit at each phase boundary**, update `README.md`'s Current Status,
   `handoff.md`'s recommended-next-step, and this file's phase status.
