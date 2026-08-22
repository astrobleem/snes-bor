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
| Jump, throw, grab, specials | BOR's actual moveset |
| ~~Items / pickups (entity kind, health)~~ | **Partial (G8, 2026-08-21)** — real prop kind + per-spawn HP, gates `game_g8_props.py`/`game_health_override.py`. Remaining level-format keyword gaps (`map`, `blockade`, `alias`, `direction`, `settime`, TMNT conversion itself) are fully enumerated, ordered, and gate-named in §8a — **read that table instead of asking what's next** |
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

Currently: walk and one attack. BOR Original has considerably more, and this is
what separates "tech demo" from "beat-'em-up."

- **Jump** (and jump attack) — needs a Z axis / ground-plane model the engine does
  not have. This is the largest single combat item.
- **Grab / throw** — proximity grab state, mutual entity locking.
- **Special** (HP-cost screen-clear), **run/dash**, **block** if the char has it.
- **Knockdown, getting up, invulnerability frames** — currently only hit stun.

**Content dependency:** `tools/bor_converter/convert_character.py` converts
idle/walk/attack only. Every move above needs its animation converted and packed,
which grows each roster slot's `bor.msu` footprint and re-shifts every downstream
offset (§4's note).

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
| 3 | `map` (per-spawn colormap/palette variant, 0-3) | **RE-VERIFIED 2026-08-21, bigger than first written above (that entry was wrong — corrected here rather than left to mislead the next session).** `spawn_parse.py` parses `SpawnEvent.map`, but a `map` index isn't a free-floating palette slot -- it indexes a PER-CHARACTER `remap <base.gif> <alt.gif>` table declared in that character's own `.TXT` (confirmed: `YASHIRO.TXT` has 3 `remap` lines pointing at `alt1.gif`/`alt2.gif`/`alt3.gif`, each a full alternate-palette copy of the base sprite). Closing this gap for real needs: (a) `entity_parse.py`/`convert_character.py` extended to read `remap` lines and extract each alt GIF's own embedded 16-color palette (new extraction work, not wiring an existing field), (b) packing N extra per-character palette variants into the MSU roster, and (c) CGRAM budget for them -- this project's own OBJ palette slots are already scarce (see `sa1_compositor_scaling_limit` project memory). Comparable sizing to a small G7 sub-item, not a G8/health-override-style keyword wire-through. Do not start this expecting an afternoon; scope it as its own plan-mode slice with real palette-budget analysis first. | Palette/CGRAM budget analysis (not yet done) | NOT STARTED, real scope |
| 4 | `boss` flag | `spawn_parse.py` already parses it (`SpawnEvent.boss`). Per-entity HP override (G9's own first prerequisite) is now DONE via the health-override slice — G9 itself (boss-specific AI, boss health bar) is the real remaining work, not a keyword-parsing gap. Tracked at §9, not here. | G6 (HUD, for a boss health bar) | see §9 |
| 5 | `blockade <n>` | Fully unparsed and unimplemented. Per `openbor_script_reference.txt` line 271 ("Limit x scroll back"): BOR's own scroll-back prevention, a one-way ratchet that advances as waves clear so the player can't retreat past an already-triggered wave. **Verified this engine has NO equivalent today** — `core/screen.pasm`'s `Screen_MinX` is set once at boot and never written anywhere else (grep-confirmed), so the camera can currently scroll backward to world X=0 at any point in a level, including past wave triggers. Real, self-contained fix: `build_spawn_table.py` gains a `blockade` event type (sibling to today's dropped `wait`/`group`), `core/spawn.pasm` (or `core/screen.pasm`) advances `Screen_MinX` when a blockade record's trigger is reached, same "single global queue, retried each frame" shape `Spawn_Play` already uses. **Re-verified 2026-08-21: neither of this project's two currently-shipped levels (`1AEASY.TXT`, `1BEASY.TXT`) use `blockade` at all — only TMNT's `STREETS.TXT` does.** Building this today has zero observable effect on the shipped game; its payoff is entirely gated on TMNT conversion (row 11), which itself waits on rows 3+7+8. Also note: the exact `<n>` semantics (offset from the triggering `at` position? an absolute world bound?) haven't been confirmed against BOR.C source in this codebase the way `levelpos`'s formula was (`spawn_parse.py`'s own header) — don't guess it into an unverified gate the way a wrong guess here couldn't be caught by any real content. | Real value blocked on row 11 (TMNT); semantics unconfirmed | NOT STARTED, low current priority |
| 6 | `music` / `bossmusic` | Fully unparsed. Needs a level-scoped music-track-select on top of TAD (today: one hardcoded audio blob loads at boot, no track switching exists at all). Content-gated like G11 (SFX) — only one track is authored/converted today, so there is nothing to switch *to* yet; do not start the code side before at least a second track exists in the pipeline. | Content (a 2nd authored TAD track) | NOT STARTED (blocked on content) |
| 7 | `alias` (spawn names a display alias; the SAME character resource, e.g. TMNT's `Foot01`/`foot02`/`foot03`, all alias to `Foot_Soldier`) | **Structural, not a small slice.** Every spawn today uses whichever roster character is *already streamed into the AI slot it lands in* — spawn events carry a `character` name but nothing reads it for identity (`build_spawn_table.py`'s own docstring: "position/timing fidelity is the goal; character identity is explicitly not"). `alias` only matters once spawns can select WHICH character to render, which doesn't exist for BOR either. This is a prerequisite for meaningful TMNT conversion (TMNT's whole roster is `alias`-driven) and overlaps G7 (moveset) territory — plan it as its own gated slice once G7 is underway, not before either exists in isolation. | G7 (character-identity spawning is naturally part of "the real BOR moveset" work extending to per-character rosters) | NOT STARTED, blocked |
| 8 | `direction` (TMNT's `STREETS.TXT`: `direction rightleft`, bidirectional scroll) | **The biggest single blocker to converting TMNT's own levels.** This engine's whole camera model (`core/screen.pasm`) is built for one-directional forward scroll with a soft-hold/unlock (G4's win condition). BOR's own stock levels never need bidirectional scroll (all `SCROLL_RIGHT` or `SCROLL_LEFT`, i.e. one direction each), so this has never had to be solved. Do not attempt inside a "level-format keyword" slice — this is camera-model-rewrite scope, sized like G7's jump/Z-axis item (§7/§13). Tracked here so it's not silently assumed away when TMNT conversion starts. | Its own dedicated phase (not yet named — add one when TMNT conversion is scheduled, see §12) | NOT STARTED, blocked |
| 9 | `settime` (level time limit) | Needs a HUD timer + a "time over" game-over path (`ATK_TIMEOVER` per `openbor_script_reference.txt`). Natural to fold into G6 (HUD) once that exists, not before. | G6 | NOT STARTED, blocked |
| 10 | `maxenemy` | **Not a real gap — document and close.** This engine hardcodes exactly 3 AI slots (`CLAUDE.md`'s "don't build a general entity-lookup system" rule); BOR's own `maxenemy` values in the stock/TMNT levels checked (4) are already satisfied trivially by that hardware ceiling. No code change is applicable here; `SPAWN_MAX_RECORDS`/the single-global-queue design (`core/spawn.pasm`'s own header) already reproduces BOR's wave-clustering behavior within that ceiling. | — | N/A — permanent engine constraint, not tracked further |
| 11 | TMNT pak conversion itself | Not a keyword gap — a content-pipeline task, gated on rows 3 (`map`, used pervasively in TMNT's own level), 7 (`alias`, load-bearing for TMNT's entire roster), and 8 (`direction`, TMNT's own level declares `rightleft`). Do not start TMNT asset conversion before at least rows 3 and 7 land — the converted assets would have no way to render correctly. Tracked under §12 (content and scale), not here. | Rows 3, 7, 8 | NOT STARTED, blocked |

**Reading order for "what's next" — re-verified 2026-08-21, both remaining
"unblocked" rows turned out lower-value than first written:** row 3 (`map`)
is real asset-pipeline + palette-budget work, not a quick slice (corrected
above). Row 5 (`blockade`) is cheap to build but has **zero observable
effect on either currently-shipped level** — its payoff is entirely gated
on TMNT conversion (row 11), and its exact `<n>` semantics aren't even
confirmed yet. **Neither is a good use of a "next slice" the way G8/health-
override were** (those closed live bugs in the currently-shipped game;
these two don't). Row 6 needs content before code. Rows 7/8 are real
phases in their own right once G7 is scheduled. Row 9 waits on G6. Row 10
is done being tracked. Row 11 (TMNT itself) waits on 3+7+8.

**Conclusion: §8a is temporarily exhausted of good next slices.** Return to
§13's own top-level order — **G6 (score, lives, a real HUD) is next**,
already fully scoped in §6, high-value (the current HUD is a raw debug
view), and blocks nothing in §8a from eventually landing. Do not re-open
§8a's remaining rows before G6 lands unless new information changes one of
their blockers.

---

## §9 — Phase G9: bosses

> **Prerequisite update, 2026-08-21:** "per-entity HP override" (this
> section's own first bullet, below) is now DONE — the health-override
> slice (§8's own status block) added exactly this to the spawn record.
> What's left here is boss-specific behavior, not data plumbing.

- ~~Per-entity HP override (the spawn table has no HP field today — add one).~~ **Done, 2026-08-21** (health-override slice, `+7 spawn_hp` in the spawn record).
- Boss-specific AI beyond "seek and attack."
- Boss health bar (G6), stage-gating (camera locks until defeated).
- The `boss` flag itself (`spawn_parse.py`'s `SpawnEvent.boss`, already
  parsed, not yet threaded into the record or read by the engine) — see
  §8a row 4.

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
them here. Rows 3 (`map`) and 5 (`blockade`) are unblocked *right now* and
don't need to wait for G7/G9; row 6 (`music`) waits on content; rows 7
(`alias`)/8 (`direction`) are real phases gated on G7 being scheduled; row
11 (TMNT conversion) waits on 7+8+3.

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
