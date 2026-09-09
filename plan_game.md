# plan_game.md — from hardware proof-of-concept to a complete, releasable game

> **Source-fidelity correction (2026-09-09):** `STAGE_CONFIGS` is a physical
> packed-stage catalog; it is not campaign progression. Build-generated
> logical campaign maps now resolve BOR and TMNT authored `LEVELS.TXT` order
> to physical entries. Standalone test/boss records are not implicit campaign
> members. Current BOR ends at its temporary TITLE development boundary after
> `1C`; Batch B/`2EASY` is not started. See
> [`docs/bor_source_fidelity_audit.md`](docs/bor_source_fidelity_audit.md) for
> source-vs-runtime classifications. No gameplay-fidelity rewrite is implied.

> **This is the critical path.** Everything in this file is required to turn the
> current ROM into something a person could sit down and play from title screen
> to ending.
>
> Read `README.md`'s "Current Status" first — it is the authoritative list of
> what actually works today. This file assumes it.

> **Roadmap rebaseline after accepted G13 (2026-09-08).** G1–G10, G12, and
> G13 are closed for their accepted scopes. Six actor slots are production:
> P1 is slot 0, fixed P2 LEO is slot 1, and NPCs occupy slots 2–5. One-player
> mode supports five NPCs; two-player mode supports four. The accepted G13
> slice includes independent P1/P2 input and score/lives/continue ownership,
> either-controller pause, shared camera/tether behavior, and 1P/2P stage
> handoff. Sections below retain historical implementation evidence; when
> they conflict with this banner or README, this banner is current authority.
>
> **G14 — player-facing two-player completion/polish — is complete for its
> accepted scope.** P1 remains normally selectable; P2 is fixed LEO with
> explicit presentation. Independent P1/P2 HUD state, accepted G13 lifecycle,
> and two-player/four-NPC regression are retained. Do not redesign transport,
> increase actor count, add a script VM, or reopen unrelated audio work.
> **Following milestone: G15 — finish the original Beats of Rage
> campaign/content.** The source-fidelity audit and campaign/catalog
> separation are now recorded; no 2EASY conversion has started. TEXT-1 is
> closed at `3775afbc7af333853f852f6f1e2078949e509ebb`.
>
> Planning rule: new engine architecture is added only when reachable game
> content proves that it is needed. Animation residency redesign, SA-1
> compositor work, a generic script VM, Double Dragon Moto, arbitrary actor
> growth, and speculative cache redesign are future R&D, not current blockers.

---

## §0 — Where the game actually is

Be precise about this, because the engine is genuinely impressive in ways that
make it easy to overestimate how close a *game* is.

**What exists and works:** SA-1 boot and CC-DMA, MSU-1 asset streaming, an operational
TAD/SPC700 runtime with one real landed-hit SFX,
a 4-entity system with per-instance state, dpad player control, AI that seeks and
attacks, AABB collision with hit stun, HP with a BG3 health-bar HUD, a soft-kill
at 0 HP for AI, two converted real levels with a streaming tile cache, horizontal
camera scrolling, a frontpanel foreground layer, a 4-character roster with live
Select-cycling, convert-time spawn tables driving real enemy waves, a font/text
renderer (G1), a game state machine (G2), and player death/lives/continues/game
over (G3).

**What that adds up to (updated 2026-08-24):** ten real stages (indices
0-9) — the original 2 BOR levels, the full real TMNT pak converted on top
of them: 3 standalone TMNT boss stages (Bebop/Rock/Leatherhead), the real
4-level TMNT main campaign (`sewer0`→`streets`→`streets2`→`sewer`, with
Rock and Bebop fought again as *story* bosses on top of their standalone
encounters), and the last standalone TMNT level (`foot.txt`, no boss
despite its name) — a real win condition and stage transition generalized
across all of them (G4), and a full title→character-select→playing menu
flow plus a real pause menu with real drawn content and SRAM-persisted
options (G5, **PARTIAL — corrected 2026-08-28**: navigation/pause/SRAM
work and are gated, but the real `waiting`/char-select portrait pose is
unimplemented, and title logo art/attract mode remain unbuilt polish — see
§5). Real boss fights are reachable in play (G9,
fully done), and the per-spawn character-identity gap this file used to
describe as a genuine architectural fork is now CLOSED for the case that
actually matters: **spawn-driven roster reassignment** (real user
instruction, same day as the TMNT campaign) — a boss spawn whose real
character is in the actual shipped roster (Rock and Leather were added as
real roster members specifically for this, indices 6/7) now re-streams
that AI slot with its own real converted character
(`core/spawn.pasm`'s `SPAWN_KIND_BOSS_IDENTIFIED`/`Spawn_DoRosterReassign`,
reusing the exact same live mid-game `Anim_LoadCharacter` reload the
player's own Select-button reselect already used), proven end-to-end by
`tools/verify/game_spawn_roster_reassign.py` (`GATE SPAWN-ROSTER-REASSIGN:
PASS`) — a live entity's real (idle,walk,attack) frame-count triple
measurably changes from whatever roster member it booted with to the
boss's own real converted numbers, the moment its real spawn record
triggers. **Follow-up, same day (roster-growth slice)**: the roster format's
8-slot cap was investigated and genuinely grown, not re-flagged as blocked —
`pack_msu_roster.py`'s `MAX_CHARACTERS` was grown to 15 then (STALE as of
`finish_g8_with_runtime_asset_swapping.md`: this was never actually a
hardware ceiling after this same slice's own directory-seek rewrite to a
16-bit accumulate loop — see `MAX_CHARACTERS`'s own corrected comment;
it's now 17). Bebop was converted fresh and added as roster slot 8, so its own boss
stage now identifies for real too (`GATE G9-TMNT-BOSS` updated accordingly).
**Follow-up, same day (LEO slice)**: added LEO (TMNT) as roster slot 12 —
`data\MODELS.TXT` shows this pak's own author only actively loads Leo as a
playable turtle (`load leo ...`; `don`/`mike` are real character data but
commented out in the pak's own config, and no Raphael file exists in this
pak at all — checked directly). Leo's real `.TXT` declares 21 anims; only
the 7 this engine's role table knows (idle/walk/attack1/attack2/pain/fall/
rise) are wired to behavior — jump/slide/grab-throw/special are real
OpenBOR mechanics this engine doesn't implement (plan_game.md's own
long-standing gap, not invented here). Verified via `phase12_roster.py`,
already fully generalized from earlier roster growths: Leo cycles in via
the real Select-button mechanism and matches his own converted
`palette.txt` ground truth.

Converting Leo surfaced two real bugs, both fixed:
1. **`convert_character.py`'s "second attack" role heuristic** picked the
   first declared anim not already claimed by another role as a
   character's `attack2` — correct for RALF/JOE/JHUN (whose real second
   moves are distinctly-named, not literally "attack2"), but wrong for any
   character declaring a non-combat anim earlier in the file than its real
   second attack. Leo declares `waiting` (a menu-select pose) before his
   real `attack2`, so the old heuristic wired the second-attack input to a
   menu pose. Checked the already-shipped roster for the same shape and
   found it twice more: **Bebop and Rock were both shipped with their
   attack2 input wired to `riseattack` (a getup-only move) instead of their
   real `attack2` anim**, since both declare `riseattack` earlier in the
   file. Fixed by preferring a literal anim named `attack2` before falling
   back to the old heuristic; re-verified RALF/JOE/JHUN/YASHIRO unaffected
   (none declare a literal `attack2`). Bebop and Rock were reconverted with
   the fix and now play their real second attack.
2. **`CharSelect_NamePtrs`** (main.pasm) — the same hand-synced table that
   already broke twice before (roster growing past its length) broke a
   third time: it simply had no entry for Leo. Caught by
   `game_g5_menus.py`'s wrap-to-last-slot check, fixed by adding Leo's
   entry. This table has now needed a manual fix at every roster growth;
   noted in-file as a candidate for a future generalization if a 4th
   growth needs it.

What's still a reskin: every ordinary non-boss enemy — only characters
deliberately added to the roster (currently 13 of 15 slots used) have
anything real to identify against; most spawned names in these levels still
aren't roster members, and that's a content decision, not a remaining code
gap. See §9/§12 for the precise remaining scope. G10 ending/credits is DONE;
the accepted G11/SOUND scope is closed, while broader audio content remains
future work. **G7 (BOR's real moveset) is
complete as of the 2026-08-28 content-audit slice** — the earlier same-day
"fully exhausted" claim was premature (it checked its own existing
checklist, not the raw converted source content); a real source-content
audit found real, already-converted, still-inert animations (LEO's
`atchain` combo/`grab`/`slide`/`grabattack`, BEBOP/ROCK/LEATHER's
`riseattack`, FOOT01/FOOT02's `atchain`/`attack3`), all now implemented
and gated (`GATE G7-CONTENT-AUDIT`). Every real G7 mechanic across both
shipped paks is now implemented / content-inapplicable / assigned to
another phase, each with real sourcing — see §7's own coverage ledger for
the definitive per-mechanic table. Double Dragon Moto (the third pak in
this repo) stays unconverted — its levels need the openborscript VM,
which remains explicitly shelved.

**The honest gap list**, updated as phases land:

| Missing | Blocks |
|---|---|
| ~~Font / text renderer~~ | **Done (G1, 2026-08-21)** — `core/text.pasm`, gate `game_g1_text.py` |
| ~~Game state machine~~ | **Done (G2, 2026-08-21)** — `core/game_state.pasm`, gate `game_g2_states.py` |
| ~~Player death~~ | **Done (G3, 2026-08-21)** — lives/continues/game over, gate `game_g3_death.py` |
| ~~Win condition / level transition~~ | **Done (G4, 2026-08-21)** — gate `game_g4_transition.py` |
| Menus (title, char select, pause, options) | **PARTIAL (G5). CORRECTED 2026-08-28**: title, char select navigation, pause menu, and options/SRAM all work (gates `game_g5_menus.py`/`game_g5_pause.py`/`game_g5_sram.py` pass), but the real `waiting`/`ANI_SELECT` char-select portrait pose is NOT implemented — char-select plays each character's ordinary idle animation, not a distinct select pose — and title logo art / attract mode are unbuilt polish (see README.md's Current Status). See §5. |
| ~~Score / real HUD~~ | **Done (G6, 2026-08-21)** — gate `game_g6_hud.py` |
| Jump, throw, grab, specials | **G7 complete, 2026-08-28 reopened-again slice.** BOR's actual moveset, source-content-audited (not just checklist-checked): run/dash, AI invuln, knockdown/getting-up, attack2, jump/jumpattack/jumpattack2 (LEO), grab mutual-lock (JOE), depth sort, throw, special (LEO) — plus the content-audit slice's real `atchain` combo (LEO/FOOT01/FOOT02), generic `grab`/`slide`/`grabattack` (LEO), `riseattack` (BEBOP/ROCK/LEATHER) — plus this reopening's `freespecial` (double-tap-forward+attack, LEO), all reached via a real generic move-slot table, not per-move copy-paste. See §7's coverage ledger for the definitive table. `block`/`land` remain content-inapplicable (zero real config anywhere in either pak, sourced against `engine/openbor.c`); `waiting`→G5 (still PARTIAL, not actually implemented — see G5 row above), `get`→G8. |
| ~~Items / pickups (entity kind, health)~~ | **Partial (G8, 2026-08-21)** — real prop kind + per-spawn HP, gates `game_g8_props.py`/`game_health_override.py`. §8a (level-format-keyword parity) is now fully exhausted |
| ~~Bosses~~ | **Done (G9, 2026-08-23), full TMNT pak converted (2026-08-24)** — 10 real stages (0-9): 2 BOR levels, 3 standalone TMNT boss stages (Bebop/Rock/Leather), the real 4-level TMNT campaign, and `foot.txt`; `EntityN_IsBoss` + boss health bar reachable in play from real converted data throughout, gates `game_g9_tmnt_boss.py` (12 checks) + `game_tmnt_campaign.py`; synthetic gates `game_g9_boss_bar.py`/`game_g9_wait_group_boss.py` kept and still pass |
| Ending / credits | **DONE (G10, 2026-08-30)** — ending sequence and credits are implemented and gated |
| SFX | **CLOSED for accepted G11/SOUND scope** — broader source audio inventory remains future content work |

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
- **ROM budget.** `$C100`-`$FC00` has only ~1913 bytes free, so
  `core/text.pasm` goes in the bank-0 gap instead: `$8C60`-`$AC00`, 8096
  bytes, all of it free (a since-dropped script VM plan once reserved part
  of this gap; that reservation no longer applies). `.org $8C60`;
  `core/text.pasm` shipped under 928 bytes. Overflow here is silent (Poppy
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

> **Status: DONE, corrected again 2026-08-30** (claude_close_g7_g8_before_
> g10.md Part 4 phase-status audit) — the 2026-08-28 PARTIAL correction
> below is now itself stale: real `waiting`/`ANI_SELECT` char-select
> portrait presentation shipped the same day it was flagged missing
> (commit `ab1b94b`, `CharSelect_PortraitUpdate` in `core/jump.pasm`,
> `GATE G5-PORTRAIT: PASS` via `tools/verify/game_g5_portrait.py`), but
> this status block was never updated to say so — exactly the "docs vs.
> ledger" contradiction `tools/coverage_ledger/verify_phase_status.py` now
> exists to catch. Title screen (2026-08-21), character select navigation
> (2026-08-23), the pause menu (2026-08-23), options/SRAM persistence
> (2026-08-23), and the real select-screen portrait (2026-08-29) are all
> shipped and gated (`GATE G5: PASS`, `GATE G5-PAUSE: PASS`, `GATE
> G5-SRAM: PASS`, `GATE G5-PORTRAIT: PASS`). Title logo art and attract
> mode (an idle-timeout demo loop) remain unbuilt — cosmetic polish, not a
> missing gameplay mechanic, and were never part of what `verify_ledger.py`
> tracks as a shipped-content role. Per an advisor consult for this phase:
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
> **Character select shipped 2026-08-23** (`core/charselect.pasm`, new
> `GAME_STATE_CHARSELECT`, entered from title's own teardown instead of
> going straight to PLAYING): a header row, the current roster character's
> name, an instructions row, and Left/Right cycling that re-skins the
> existing `CharSelect_Index`/`Anim_LoadCharacter` machinery (the same
> live-reselect path the Select button already used) rather than inventing
> new roster logic. Moved to its own ROM bank (`.bank 4`, same reason
> `core/spawn.pasm` got one) purely for `$C100`-`$FC00` budget — see that
> file's own header for the two small bank-0 trampolines this needed
> (`Anim_LoadCharacter_Long`/`Core_Text_DrawString_Long`) since both real
> routines end in `rts`, same-bank-only. Found and fixed a real bug along
> the way: `Anim_LoadCharacter` writes Direct-Page-relative `CHAR_*`
> fields, and this code runs outside any per-entity `Core_Oop_Play`
> dispatch (which is what normally points DP at the right entity) — the
> fix (`Game_State_CharSelect_ReloadPlayer`) explicitly switches DP to the
> player's own window (`OopDp`, slot 0) before calling it, same
> `phd`/`tcd`/`pld` pattern `Core_Oop_Play` itself uses. `GATE G5: PASS`
> (21 checks) exercises the full title → charselect (draw/cycle/wrap) →
> playing round trip, not just the title screen.
>
> **Pause menu shipped 2026-08-23** (`core/pausemenu.pasm`, new, its own
> ROM bank for the same `$C100`-`$FC00` budget reason charselect got one).
> Real-OpenBOR-sourced content (fetched `engine/openbor.c`'s own
> `pausemenu()` rather than inventing a menu shape): a "PAUSE" header plus
> exactly two selectable rows, "CONTINUE"/"END GAME", toggled by Up/Down
> (a "> "/"  " cursor prefix baked into two string variants per row, this
> project's existing text-only menu style — no cheap way to recolor a
> single BG3 tile). Start commits: Continue resumes PLAYING untouched; End
> Game zeroes `Game_Lives` and returns to `GAME_STATE_TITLE` (real BOR's
> End Game is an intentional quit — it hard-tears the session down with no
> continue offered — and this project has no "quit to system" state beyond
> TITLE, G2's own "nothing is running" holding state). Entered from
> `Game_State_Play__playing` via an edge-triggered Start check, itself
> moved into the new bank (`Game_State_Pause_CheckEntry`, called via a
> `jsl`+`bcs` — only 6 bytes in the hot bank-0 routine — rather than
> inlining the check there) once the inline version alone overflowed the
> region by 19 bytes. Found and fixed two real bugs along the way: (1) the
> Up/Down redraw originally issued two `Core_Text_DrawString` calls in the
> same frame, hitting the exact "1024-BOR" shared-staging-buffer hazard
> this file's own header warns about elsewhere — both rows read back
> showing the second call's string; fixed with a two-frame drip
> (`PAUSE_STEP_REDRAW_ENDGAME`), same one-DrawString-per-frame discipline
> as every other menu here. (2) `Pause_Selector` was first left sticky
> across sessions; real BOR's `pausemenu()` resets `pauselector = 0` on
> every call, so a second pause entry after selecting End Game (aborted by
> re-entering rather than committing) would silently commit End Game again
> on a bare Continue press — fixed by resetting the selector in
> `Game_State_Pause_CheckEntry` on every entry. `GATE G5-PAUSE: PASS`
> (18 checks).
>
> **Options/SRAM persistence shipped 2026-08-23** (`core/options.pasm`, new,
> own ROM bank for the same budget reason). Real-OpenBOR-sourced scope:
> `engine/openbor.c`'s `savedata` struct persists several settings, but this
> project ships exactly one — music volume — because everything else (key
> remap, gamma/brightness, SFX volume, difficulty) has no real content to
> attach to here (same closure logic as §8a's `settime`/`maxenemy`: no
> control-remap infrastructure exists; gamma/brightness are a CRT concept,
> meaningless on a fixed-palette cart; SFX volume would control zero real
> SFX content limited to the one G11 landed-hit path; difficulty picks between mod-defined content
> sets and only the EASY variant of any level has ever been converted).
> Folded into the existing pause list as a third "VOLUME" row (real BOR
> reaches its own options via a dedicated `FLAG_SCREENSHOT` key/screen this
> hardware has no spare button for) rather than inventing an unreachable
> second screen; Left/Right adjust ±32 with saturating clamp and persist to
> SRAM immediately, matching real BOR's own `menu_options_sound()` (no
> separate "save" step). Uses TAD's `SET_GLOBAL_MUSIC_VOLUME` (=16), not
> `SET_MAIN_VOLUME` (=10) — the latter's own doc says it resets on every
> song load, which would silently revert a persisted setting.
>
> **Real bug found and fixed**: the classic S-CPU SRAM window
> (`$6000-$7FFF`) turned out to be unreadable in this project's own
> architecture. Verified straight from Mesen2's C++ core:
> `Sa1::UpdateSaveRamMappings()` registers that window with the *same*
> `CpuBwRamHandler` class used for the `$40-$4F` CC-DMA window, and
> `CpuBwRamHandler::Read` unconditionally diverts through Type-1 character
> conversion whenever `CharConvDmaActive` is set — for any address reached
> through that handler, not just the CC-DMA range. This project's
> persistent SA-1 recomposite loop (`sa1_loop`) arms `CharConvDmaActive`
> once, early in boot, and never clears it again, so every SRAM read from
> that point on silently returned bogus converted-tile bytes instead of
> real save data — writes were unaffected (`CpuBwRamHandler::Write` has no
> such check), which is why the write/persist-to-disk half worked
> immediately while every read-back came back zeroed. Fixed in
> `Options_Init` by briefly ending character conversion (shared register
> `$2231`, writable by either CPU) around the 4-byte SRAM read, then
> restoring it and re-arming via `$2236` exactly like `sa1_loop`'s own
> steady-state re-arm — safe against the SA-1's own loop because it only
> writes `$2231` once, in its pre-loop setup, never per-iteration. Caught
> because the gate genuinely spans two separate Mesen2 *processes*
> (`reset_emulator()` alone never flushes/reloads the `.srm` file, so a
> weaker single-session check would have missed this entirely) —
> `GATE G5-SRAM: PASS` (12 checks: default-on-fresh-boot, in-menu lower,
> on-disk `.srm` byte-exact, then a second process load, WRAM ground truth,
> and the on-screen row, all against the persisted, non-default value).
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

- **Title screen** — done (2026-08-21). Real logo art (convert BOR's own title
  art through `convert_bg.py`) and an attract-mode timeout are still optional
  polish, not required.
- **Character select** — done (2026-08-23, `core/charselect.pasm`). Portraits
  (a real character sprite/thumbnail on the screen, not just the name) are
  the one piece not built — text-only for now.
- **Pause menu** — done (2026-08-23, `core/pausemenu.pasm`). Freeze on Start, CONTINUE/END GAME, real BOR-sourced content.
- **Options** — done (2026-08-23, `core/options.pasm`). Music volume only,
  SRAM-persisted; see the write-up above for why SFX volume/difficulty/
  controls are explicitly out of scope rather than unbuilt.

Note: **roster-slot persistence specifically was declined and is not wanted** —
it is not part of Beats of Rage. Options persistence is a different question and
was genuinely expected, and is now shipped.

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

> **Status: COMPLETE as of the 2026-08-28 content-audit slice.** See "G7
> content-audit slice (Reopen G7)" at the end of this section for the
> definitive per-mechanic coverage ledger — the prior "G7 fully exhausted"
> claim (same-day, earlier commit `8c3fa69`) was premature: it checked its
> own existing checklist, not the raw converted source content, and real,
> already-converted animations (LEO's atchain combo/grab/slide/grabattack,
> BEBOP/ROCK/LEATHER's riseattack, FOOT01/FOOT02's atchain/attack3) sat
> inert. That gap is now closed; the ledger below is what makes this
> status trustworthy going forward, not the sentence itself. `GATE G7-RUN:
> PASS` (`tools/verify/game_g7_run.py`), `GATE G7-INVULN: PASS`
> (`tools/verify/game_g7_invuln.py`), `GATE G7-KNOCKDOWN: PASS`
> (`tools/verify/game_g7_knockdown.py`, one known-flaky check documented
> below — retry once), `GATE G7-ATTACK2: PASS`
> (`tools/verify/game_g7_attack2.py`), `GATE G7-JUMP: PASS`
> (`tools/verify/game_g7_jump.py`, fifth slice, 2026-08-28 — see its own
> writeup below). Special/block and real grab/throw mutual-lock semantics
> remain fully open (see "Still fully open" below). Run/dash shipped first, deliberately,
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
> **Fifth slice DONE, 2026-08-28: real jump, jumpattack, jumpattack2.**
> `GATE G7-JUMP: PASS` (`tools/verify/game_g7_jump.py`, 15 checks). Sourced
> directly from real OpenBOR (DCurrent/openbor, `engine/openbor.c`) per this
> project's own behavioral source-of-truth rule (distinguish real-BOR vs.
> later-OpenBOR vs. PAK-content vs. SNES-adaptation vs. deliberate
> simplification, don't invent):
> - **Real BOR.C-sourced**: `tryjump()/dojump()/toss()` — jumpheight IS the
>   initial upward velocity directly (`toss(self, jumpheight)` sets
>   `velocity.y = jumpheight`), not a peak-height requiring a physics solve.
>   `check_gravity()` — `position.y += velocity.y` every tick, `velocity.y +=
>   gravity` every tick (real default `-0.1`), land when `position.y <= 0 AND
>   velocity.y <= 0` — a two-part condition, not position alone (a large
>   downward velocity can step position past 0 in one tick). Ground-jump
>   trigger is `FLAG_JUMP && notinair`, edge-triggered-then-consumed — this
>   project's A button (the one genuinely free button left) plays that role.
>   A jump-attack button press while airborne (mode 0 only) plays a
>   jump-attack instead of a ground attack — real BOR.C behavior, mapped here
>   to this project's existing Y=attack1/X=attack2 buttons.
> - **PAK-content-confirmed**: LEO (TMNT pak, `data\CHARS\LEO\LEO.TXT`) is
>   the ONLY roster member with real `jump`/`jumpattack`/`jumpattack2` anim
>   data and a real `jumpheight 5`. Every other roster slot's A-button press
>   is a real no-op (`Player_JumpFCount==0` for anyone but LEO) — not a bug,
>   there is no real source data for anyone else to jump with.
> - **SNES-specific adaptation**: Q8.8 fixed point (16-bit signed, 8
>   fractional bits) stands in for BOR.C's float `position.y`/`velocity.y`
>   (SNES has no float unit); `JUMP_INITIAL_VEL`/`JUMP_GRAVITY` are the
>   literal real BOR.C magnitudes (5.0, -0.1) scaled by 256, not a
>   feel-tuned conversion.
> - **Deliberate simplifications (explicitly NOT sourced claims)**: (1) real
>   BOR.C's height-vs-depth split (`position.z` height, separate from
>   `position.y` depth/lane) is translated here onto a **visual-only OAM Y
>   offset** against the already-computed sprite Y — this project has no
>   ground-plane/lane axis at all (see the resolved "G7's jump / Z axis"
>   item in §13), so no depth sort was built or is needed; jump only moves
>   the sprite up on screen while airborne, `CHAR_POS_Y` itself (collision/
>   world position) is untouched. (2) horizontal movement while airborne
>   reuses the existing continuous per-frame dpad-read walk code rather than
>   porting BOR.C's one-shot ballistic X-velocity model — this project has
>   no parallel X-velocity system and building one would be a redundant,
>   imperceptible change. (3) landing falls through to normal ground
>   dispatch the SAME frame for responsiveness, a control-feel choice. (4)
>   AI jump was never built — real BOR.C AI think loops don't autonomously
>   jump either, so this is not a missing feature.
>
> **Implementation**: new `src/core/jump.pasm`, own bank (`.bank 8`,
> jsl-entry/rtl-exit, same ROM-budget pattern as `core/pausemenu.pasm`/
> `core/options.pasm` — `$C100-$FC00` is chronically near zero free bytes).
> `Jump_ComputeBases` (called from `Anim_LoadCharacter`, every entity load)
> chains 3 new base offsets (jump/jumpattack/jumpattack2, player-only) onto
> the existing `rise_base`/`attack2_base` chain. `Jump_PlayerTick` (called
> from `Anim_Play__player_input`) owns the grounded-trigger and airborne-
> integration/landing state machine; `Anim_Play_Jump` (called from
> `Anim_Play__dispatch`) owns the per-frame `Msu1_StreamBusy`-gated frame
> advance for all 3 jump-family anims, same shape as `Anim_Play_Attack`/
> `Attack2`. `Jump_ApplyOamYOffset` (called from `Character_PlayFrame`,
> right after `OamSetSprite_Y` is set from `CHAR_POS_Y`, for every entity —
> no-ops for anyone but the airborne player) applies the visual offset; also
> moved to its own bank after an initial inline version overflowed bank 0's
> ROM budget by 88 bytes. `RECORD_SIZE` in `pack_msu_roster.py` grew 17→23
> (6 new bytes: jump/jumpattack/jumpattack2 frame_count/delay pairs), which
> in turn forced `Anim_LoadCharacter`'s directory-seek arithmetic off its old
> 8-bit-only scheme (its safe ceiling would have dropped below LEO's own
> slot 12) into a real 16-bit accumulate-by-repeated-add loop — removing the
> seek ceiling entirely, not just patching around LEO. No `CHAR_ZP_LEN`
> struct growth (`Player_Jump*` are standalone WRAM globals, matching the
> `Player_InvulnFrames` precedent — growing the shared struct for
> player-only state has broken spawn-slot assignment before).
>
> New gate `tools/verify/game_g7_jump.py` (`GATE G7-JUMP: PASS`, 15 checks):
> loads LEO onto the player via the real in-game Select-button reselect path
> (not a synthetic memory write); confirms a real A press arms
> `CHAR_SELECTED_JUMP` and, since `set_input`'s own wall-clock sleep
> (`mesen_set_input_wall_clock` project memory) makes the exact arm frame
> unobservable, confirms the observed `(Player_JumpZPos, Player_JumpZVel)`
> exactly matches a from-scratch simulation of the real integration formula
> from `JUMP_INITIAL_VEL`/`JUMP_GRAVITY` at some small elapsed tick count;
> confirms height genuinely rises then falls (not static); confirms landing
> within a bounded frame count resets both Z cells to 0 and returns
> `CHAR_SELECTED` to idle/walk; confirms a real, nonzero OAM Y offset while
> airborne that disappears on landing; confirms jump and jumpattack stream
> from genuinely different MSU base offsets; confirms a Y-button press
> mid-air (mode 0) really enters jumpattack (`Player_JumpAnimMode=1`)
> without leaving `CHAR_SELECTED_JUMP`. AI entities 1-3 are neutralized
> (HP=0, hit-stun cleared every polled frame) throughout, same reasoning as
> `game_g6_hud.py`/`game_g7_invuln.py` — background AI combat is already
> live by frame 300 and a stray hit landing mid-flight would force
> `CHAR_SELECTED` back to 0 via the unrelated hit-stun path, which would
> look like a broken landing to this gate but has nothing to do with jump.
>
> Full regression suite clean: build, `audit_all.py`, `check_label_drift.py`,
> `check_width_directives.py` (0 new violations, 1 baseline entry cleaned up
> for `Anim_Play__player_input` gaining an explicit `.a8`), `phase5`–`phase9`/
> `11`/`12`, every `game_g*.py` gate including a from-clean-baseline-isolated
> re-confirmation that `game_g7_knockdown.py`'s intermittent failure is
> genuinely pre-existing and unrelated to this slice (stashed all jump
> changes, rebuilt the last-committed baseline, reproduced the identical
> failure there too).
>
> **Still fully open**: real grab/throw mutual-lock semantics, special,
> block — all still need new animation content the converter doesn't
> produce today for any roster character (see "Content dependency" below).
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
> dispatch is not built here; a future scoped slice can pick this up. Full
> regression suite clean (`audit_all.py`, `check_label_drift.py`, `check_width_directives.py`,
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
> direct pak scan), so that part is simply out of scope for this project
> (no script VM exists or is planned).

Currently: walk, run, and one attack. BOR Original has considerably more, and
this is what separates "tech demo" from "beat-'em-up."

- ~~**Jump** (and jumpattack/jumpattack2)~~ — **Done (G7 fifth slice,
  2026-08-28)**, see status block above (`GATE G7-JUMP: PASS`,
  `tools/verify/game_g7_jump.py`). Sourced directly from real OpenBOR
  (DCurrent/openbor, `engine/openbor.c`: `tryjump()/dojump()/toss()` —
  jumpheight IS the initial upward velocity, not a peak-height solve —
  and `check_gravity()` — position += velocity, velocity += gravity every
  tick, land when position<=0 AND velocity<=0, a two-part condition).
  LEO (TMNT pak) is the only roster member with real jump/jumpattack/
  jumpattack2 anim data (`jumpheight 5`); every other roster slot no-ops
  the A-button trigger (`Player_JumpFCount==0`). Q8.8 fixed point for
  height/velocity (`JUMP_INITIAL_VEL`/`JUMP_GRAVITY`, literal 256x-scaled
  real BOR.C constants). **What this slice alone was NOT**: no Z-axis/
  depth-sort system was built in it — the real BOR.C `position.z` (height)
  vs `position.y` (depth) split was translated onto a single 2D sprite Y as
  a **visual-only OAM offset** (subtract the Q8.8 height's integer byte
  from the already-computed `OamSetSprite_Y`), not a new gameplay axis (the
  depth-sort axis itself shipped one slice later — see the next bullet).
  Horizontal movement while airborne deliberately reuses the existing
  continuous per-frame dpad-read walk code rather than porting BOR.C's
  one-shot ballistic X-velocity model — a **deliberate simplification**
  (this project has no parallel X-velocity system and one would be
  imperceptible here), not a sourced behavior. Landing the same frame falls
  through to normal ground dispatch immediately — a **control-feel
  choice**, not a real-source claim. AI jump was never built (real BOR.C AI
  think loops don't autonomously jump either — not a missing feature).
  Player only (slot 0), matching every other G7 slice.
- ~~**Actor ground-depth sort**~~ — **Done (G7 sixth slice, 2026-08-28)**,
  `GATE G7-DEPTH-SORT: PASS`, `tools/verify/game_g7_depth_sort.py`. Closes
  the gap the jump slice above (and §3.6/§12) flagged: real hardware always
  draws the lower-OAM-index sprite in front at equal priority, and every
  entity here always shares the same fixed priority, so OAM emission order
  IS depth order. `src/core/depth_sort.pasm` (own bank) sorts the 4 fixed
  entities by real ground `CHAR_POS_Y` (a selection sort, N=4 fixed, read
  strictly before jump's own OAM-Y offset is applied to anyone this frame);
  `main.pasm`'s old `Character_PlayFrame` (movement + inline OAM emission)
  splits into a pure movement routine and `Character_RenderFrame` (the OAM-
  emission tail), the latter driven by `Character_RenderPass` once per
  frame in depth-sorted order via real per-entity `phd`/`tcd` DP-window
  switching (same convention `core/oop.pasm`'s dispatcher already uses).
  Splitting movement from render surfaced two real pre-existing-shape bugs
  the split itself introduced (`OamSetSprite_X`/`OamSetSprite_Hi` are
  single shared per-frame WRAM cells that used to be safely written mid-
  movement only because movement and OAM emission were one interleaved
  pass; both are now recomputed fresh inside `Character_RenderFrame`
  instead). The gate inspects only real hardware OAM (never the internal
  `Depth_RenderOrder` array, never assumes OAM slot N == entity N) to prove
  static depth order, that jump altitude never perturbs anyone's rank, and
  that landing restores the exact pre-jump baseline. Updating several
  existing gates that had assumed OAM-slot-equals-entity-index (`phase8.py`,
  `phase11_damage.py`, `game_g2_states.py`, `game_g7_knockdown.py`,
  `game_g8_props.py`) to identify entities by real on-screen X/palette
  instead was part of this slice, not scope creep — those assumptions were
  silently false the moment depth-sorted OAM order shipped. AI jumping,
  throw, special, block, pits, multiplayer, arbitrary entity-count scaling,
  and SA-1 compositor changes are explicitly out of scope for this slice.
- ~~**Grab**~~ — **Done**, `GATE G7-GRAB: PASS`, `tools/verify/game_g7_grab.py`.
  Real mutual-lock semantics (`adjust_grabposition`'s one-time X-average-
  then-separate snap, `check_link_move`'s per-frame rigid offset-follow,
  fixed-timer auto-release), sourced from `engine/openbor.c`
  (DCurrent/openbor), for JOE only (the only roster member whose real
  attack2 anim is literally named `grab`, converter-derived via
  `attack2_is_grab`, never hardcoded per character). Player-initiated only
  (AI never grabs, matching real BOR.C's own player-only `player_grab()`
  dispatch). This docs entry was itself stale until the throw slice below
  touched it -- grab shipped earlier and was never updated here.
- ~~**Throw**~~ — **Done (G7 seventh slice)**, `GATE G7-THROW: PASS`,
  `tools/verify/game_g7_throw.py`. Real `common_throw()`/`toss()` semantics
  (same `engine/openbor.c` fetch the jump slice already sourced from):
  release the mutual link, apply real damage/knockdown/HP-clamp/kill
  decision through the SAME `Character_HitApply__ApplyDamage` leaf every
  landed hit uses, then -- unless that hit was a kill -- override its
  stun-or-fall pick with an airborne launch (real `toss()` always results
  in airborne motion, never a mere stun). Landing enters the SAME fall/
  rise knockdown pipeline a landed hit produces; no unique "thrown" art
  exists in any roster pak (same "no unique art" precedent jump's own
  jumpattack2 reuse established), so no new animation content was needed.
  **Real prerequisite found and built, not invented around**: the
  player-only, single-global-cell Z-axis system `core/jump.pasm` shipped
  (`Player_JumpZPos`/`ZVel`) can't represent a non-player victim's
  airborne height -- grew `CHAR_ZP_LEN` 67→71 for two new per-instance
  fields (`CHAR_THROW_ZPOS`/`ZVEL`, identical Q8.8 physics to jump's own)
  instead, plus a new `CHAR_SELECTED_THROWN` state reachable from AI
  dispatch (not just player input). `Jump_ApplyOamYOffset` (bank 8)
  generalized to apply either the player's jump offset or any entity's own
  throw offset. New `Character_Grab_Throw`/`Character_Throw_Play`
  (`vm_native_engine.pasm`, same bank as grab) own the cross-entity launch
  and the per-entity gravity tick (twin of `Jump_PlayerTick__airborne`).
  Depth sort needed zero new code -- it already keys purely off
  `CHAR_POS_Y`, which no Z-system ever touches, so "depth stays
  ground-based during an airborne throw" was already structurally
  guaranteed; the gate proves it, not the implementation. **Real bugs found
  the hard way**: (1) `ApplyDamage`'s own stun branch can stamp
  `CHAR_HIT_STUN` nonzero, and `Anim_Play`'s hit-stun check runs BEFORE
  this slice's own THROWN-aware gate and unconditionally resets
  `CHAR_SELECTED` back to 0 on the victim's very next frame -- silently
  wiping the THROWN state within a frame; fixed by clearing `CHAR_HIT_STUN`
  when throw overrides ApplyDamage's own reaction pick. (2) The
  depth-sort slice's own hand-synced `Entity{1,2,3}_DpBase` literals
  (`Character_RenderPass`'s per-entity DP-window switch) silently went
  stale the moment `CHAR_ZP_LEN` grew -- not caught by
  `check_entity_base_sync`, a SEPARATE literal covering the same offsets;
  `Character_RenderPass` switched DP to the wrong window for every AI
  entity, rendering garbage struct bytes as position/tile data, confirmed
  via `phase11_damage.py`/`game_g7_knockdown.py` both losing entity 1's
  real OAM position. Fixed, and closed structurally (not just the
  instance) with a new `check_dp_base_sync` in `tools/rom_audit/audit_all.py`
  so this class of drift fails loudly next time `CHAR_ZP_LEN` changes.
  Attacker (thrower) returns to idle immediately after throwing -- no
  unique throw-swing animation in any pak, same simplification precedent.
  Killing via throw takes the existing sticky-`CHAR_HP==0` soft-kill path
  (no real OOP kill/GC, preserving the fixed-address `EntityN_Base`
  scheme) -- a lethal throw still runs its real fall sequence to
  completion before the dead-hide blink gate hides it, exactly like any
  other killing hit. AI throwing, special, block, pits, multiplayer,
  arbitrary entity-count scaling, and SA-1 compositor changes are
  explicitly out of scope for this slice.
- ~~**Special**~~ — **Done (G7 eighth slice, 2026-08-28)**, `GATE G7-SPECIAL:
  PASS`, `tools/verify/game_g7_special.py`. Real `check_special()`/
  `player_check_special()` semantics (`engine/openbor.c`, DCurrent/openbor,
  same fetch every G7 slice has sourced from): releases any active grab
  link before triggering, then plays the special animation, then deducts
  `energy_cost.cost` from HP/MP only if nonzero (a no-op for a zero cost,
  not a shortcut this project took). LEO (TMNT pak) is the only roster
  member with real `special` data — 6 frames, a real `attack` hitbox line,
  no `energycost` line at all, so genuinely free. Bound to L, the other
  free button in this project's map (jump already claimed A). This was
  the "invented guess" the plan carried for months (**"HP-cost
  screen-clear"** was never sourced from real BOR.C or any roster
  character's real data — corrected here, not implemented as guessed).
  Reuses attack1/attack2's exact shape: a third `CHAR_ATTACK_VARIANT`
  value (2) selecting a new `CHAR_SPECIAL_FCOUNT/DELAY/BASE_LO/BASE_HI`
  struct quartet (`CHAR_ZP_LEN` 71→76), chained onto the existing
  `attack2_base + (attack2+jump+jumpattack+jumpattack2 fcount)*768`
  base-offset math one hop further (`map_base` now chains off
  `special_base` instead, so it still skips past special's frames to
  reach the remap-palette table). Damage goes through the SAME
  `Character_HitApply` `CHAR_SELECTED==2` check every other move already
  uses — no variant-specific hit code exists there. **Real prerequisite
  found and built, not invented around**: bank 0 (`$C100-$FC00`) was
  already at its ROM-budget ceiling, so the frame-advance/revert-to-idle
  logic itself was moved to a new bank-8 routine (`Jump_PlaySpecialAdvance`,
  `core/jump.pasm`) that signals via carry whether the bank-0 caller still
  needs to make the one call that can't move (`Msu1_LoadFrame`, same-bank-
  only constraint) — mirrors how `Jump_ComputeBases`/`AnimBase_Compute*`
  were relocated for the same reason in earlier slices. Freed additional
  budget by finishing the nop-guard cleanup this slice's own interrupt
  started: removed all 188 remaining stale "Poppy branch-target label
  misalignment" `nop` guard lines from `main.pasm` (label drift and
  backward-branch misalignment were both fixed upstream in the astrobleem
  fork — `check_label_drift.py` confirms `0 nop-guarded, 0 DRIFTED` after
  removal). **No genuine grab+special interaction exists in any real
  roster data** — JOE (the only grabber) has no `special` role, LEO (the
  only character with `special`) has no `grab` role — so the gate verifies
  the grab-release call structurally (forcing `CHAR_GRAB_TARGET` nonzero on
  LEO before triggering), not as a claim about LEO's own real data. No
  smartbomb/screen-clear/AoE behavior exists anywhere in this slice — LEO's
  model declares none, and inventing one would be exactly the
  never-sourced guess this entry used to carry. **Block investigated
  exhaustively immediately after this slice, not deferred** (2026-08-28):
  every real character `.TXT` in BOTH shipped paks — all 24 BOR characters
  (RALF/JOE/JHUN/YASHIRO plus every other fighter in the pak, not just
  this project's converted roster) and all 13 TMNT characters (BEBOP/LEO/
  MOUSER/FOOT01-05/LEATHER/ROCK/DON/MIKE) — grepped directly for a `block`
  animation line: zero exist anywhere, in either pak, on any character.
  Real BOR.C's own `check_blocking_rules()` (`engine/openbor.c`) hard-gates
  ALL blocking logic on `validanim(ent, ANI_BLOCK)` returning true first —
  no anim, no blocking, full stop, regardless of `blockodds`/guard-point
  settings — so this is not a partial or borderline gap, it's completely
  unbuildable with real sourced data today. Permanently content-blocked;
  revisit only if a future pak with real `block` animation data is
  converted. **§7 is now genuinely, fully exhausted** — every mechanic
  with real, buildable data has real, gated, sourced engine code; block is
  the sole remaining item, and it's a content wall, not an open code task.
  AI use of jump/special (no roster member's AI think-loop uses either in
  real source), pits, multiplayer, arbitrary entity-count scaling, and
  SA-1 compositor changes remain explicitly out of scope for G7 as a
  whole, not just this slice.
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
roster format and engine dispatch the same day — see status block above),
plus jump/jumpattack/jumpattack2 (added 2026-08-28, see the jump bullet
above — LEO is the only roster member with real data for these). Every
remaining move above (grab/throw, special, block) still needs its
animation converted and packed, which grows each roster slot's `bor.msu`
footprint and re-shifts every downstream offset (§4's note) — same
constraint fall/rise and jump were both blocked on before their slices.

**Watch out (historical — resolved by scoping, not by solving):** this
section originally warned that a Z axis would change depth sorting and
that jump would force §3.6's Y-sorted-priority spec item to be solved. The
shipped jump slice avoided that entirely by not building a Z axis or depth
sort — see the jump bullet above. §3.6's real sorting gap, if it matters
later, is still open independent of jump.

### G7 content-audit slice (Reopen G7), 2026-08-28

**Why this reopened a "done" phase.** The prior "G7 fully exhausted" claim
checked this file's own existing checklist (jump/special/grab/throw/run/
invuln/knockdown/attack2/depth-sort) but never re-audited the raw source
content itself. A real audit — every character `.TXT` in both shipped
paks, cross-referenced against `DCurrent/openbor`'s real `engine/
openbor.c` for exact trigger semantics, not assumed ones — found real,
already-converted-and-sitting-in-`out/*_moveset.json` animations with zero
runtime code: LEO's real `atchain` combo, `grab` (a role distinct from
JOE's attack2-is-grab), `slide`, `grabattack`; BEBOP/ROCK/LEATHER's real
`riseattack`; FOOT01/FOOT02's `atchain`/`attack3`. Per the reopening
instruction, "no gameplay-relevant converted animation remains inert
merely because the SNES role/runtime layer never wired it" — this section
is the proof that is now true.

**Architecture — a real generic move-slot table, not more copy-paste.**
Every prior G7 slice added one full field-set (`CHAR_X_FCOUNT/DELAY/
BASE_LO/BASE_HI`) per move, by hand. This slice's own scope (6 more real
moves at once) made that pattern untenable, so it was replaced:
`NEW_MOVE_SLOT_NAMES = [attack3, attack4, grab, slide, riseattack,
grabattack]` (`pack_msu_roster.py`) is a fixed-order table — the packer
resolves and bakes all 6 generically (one loop, not 6 hand-written
blocks), `RECORD_SIZE` grew 25→44 (+19 bytes: 12 fcount/delay + 6
`atchain` steps + 1 `chainlength`), and the engine mirrors this with a
real generic dispatcher: `CHAR_ATTACK3_FCOUNT`..`CHAR_GRABATTACK_BASE_HI`
are 6 identically-shaped 5-byte structs at consecutive DP offsets (main
.pasm, `CHAR_ZP_LEN` 76→115), and ONE shared bank-8 routine
(`Jump_PlayMoveSlotAdvance`, `core/jump.pasm`) plays whichever slot
`CHAR_ATTACK_VARIANT` (3-8) selects via direct-page-indexed-by-X
addressing (`lda CHAR_ATTACK3_FCOUNT,x`), not six copies of `Anim_Play_
Attack2__advance`. The `CHAR_MAP_BASE` offset chain (`plan_game.md` 8a
row 3, `map`) now runs 7 hops instead of 1 through a second shared
subroutine, `Jump_HopBase` (`new_base = prev_base + prev_fcount*768`),
also to avoid re-duplicating that arithmetic per slot.

**Real triggers wired** (all reusing the existing `CHAR_SELECTED==2`
attack hit-check unmodified, matching this project's own attack2/special
precedent — no new per-move damage code anywhere):
- **atchain combo** (`perform_atchain()`, real `engine/openbor.c`): Y is
  the sole chain button for a chain-bearing character (`CHAR_CHAINLENGTH
  !=0` — LEO, FOOT01, FOOT02); repeated presses **during** the in-progress
  swing (not just after it finishes — the actual point of a combo chain)
  advance `CHAR_COMBOSTEP` through the character's real declared sequence
  (`CHAR_ATCHAIN0-5`, pre-translated at pack time from real BOR attack-
  numbers to local `CHAR_ATTACK_VARIANT` values); a lapsed `CHAR_COMBOTIMER`
  window resets to step 0. The independent X-attack2 trigger is
  unreachable for these characters (real BOR has no separate attack2
  button either) — every other roster member is untouched.
- **Generic `grab`** (R button) and **`grabattack`** (R+Y, takes priority
  over plain R): LEO-only. Real BOR.C grabattack requires an active grab
  *hold*; this project's `grab` role is deliberately shipped the same way
  this project's own precedent already treats a second move without full
  mutual-lock machinery (see `game_g7_attack2.py`'s own docstring on
  JOE's `grab`-as-generic-attack2 choice) — a one-shot attack move, no
  `CHAR_GRAB_TARGET` link — so R+Y is this slice's own stand-in trigger
  shape for "attack while grabbing," not real dograb()/adjust_
  grabposition() semantics. JOE's existing real mutual-lock (attack2-is-
  grab) is completely untouched and non-conflicting (LEO's `attack2` role
  and `grab` role are always disjoint by construction — see
  `convert_character.py`'s resolution order).
- **`slide`** (A+Down, real `player_think()` trigger): LEO-only.
- **`riseattack`** (`player_lie_check()`: UP-held+Y-edge while lying, HP>0,
  not mid-fall-animation, not the terminal dead-park state): BEBOP/ROCK/
  LEATHER-only, player-only scope (matches every other G7 trigger's
  established player-only boundary).

**A real bug found and fixed mid-implementation** (not by design review):
the first riseattack wiring replaced the FALL-state's unconditional
`beq Anim_Play__reacting` (the pre-existing "already reacting, ignore
input/AI-seek, let it finish" lock — see its own long-standing comment)
with a conditional path that, when the trigger declined, fell through to
the RISE/THROWN checks instead of the lock. For an AI-driven lying entity
(riseattack always declines for `CHAR_INPUT_DRIVEN!=1`) this let `Anim_
Play__ai_seek` re-decide its `CHAR_SELECTED` mid-fall — exactly the bug
that lock exists to prevent, per its own comment. Caught by `GATE
G7-KNOCKDOWN` regressing from 1 flaky check to 8 hard failures (fatal
hits no longer even entering the FALL animation). Fixed: FALL state now
*always* unconditionally lands on `Anim_Play__dispatch` regardless of the
riseattack trigger's outcome (dispatch reads live `CHAR_SELECTED`, so
either a newly-triggered riseattack or the still-lying state is handled
correctly either way).

**Content classified INAPPLICABLE or belonging to another phase** (not
gated — no runtime code exists for them, confirmed absent by this
audit, not merely unbuilt):
- **`freespecial`**: real `engine/openbor.c` confirms this move is
  AI-exclusive in this source version — `player_check_special()` never
  references `animspecials[]`/`ANI_FREESPECIAL` at all. Consistent with
  (an inversion of) this project's own repeatedly-established "every G7
  attack trigger is player-only" scope: this one is the AI-only mirror of
  that same boundary, and no roster AI currently uses it, so it is
  genuinely unreachable today, not deferred.
- **`land`/`ANI_LAND`** (`doland()`): gated in real source on
  `BLAST_TOSS`+specific `attack_force` flags; zero configuration
  anywhere in either shipped pak (`forcedirection`/`projectile`/`blast`/
  `autoland`/`ATTACK_FORCE` all absent from every roster character's real
  `.TXT`, grepped directly) — content-inapplicable, same class as
  `block`'s own permanent content-block above, not a missing feature.
- **`waiting`/`ANI_SELECT`**: real char-select portrait pose. **CORRECTED
  2026-08-28: NOT actually implemented anywhere.** The prior claim that G5
  "already implements" this was false — grepped `src/main.pasm` and found
  no `ANI_SELECT`/portrait/waiting-pose code at all; char-select
  (`core/charselect.pasm`-era logic, now inline in `main.pasm`) just plays
  each roster member's ordinary idle animation while browsing, not a
  distinct select-screen pose. G5 status is therefore **PARTIAL**, not
  done, until a real `waiting` presentation is built and gated. See §5.
- **`get`**: real item-pickup pose — G8 scope, matching the reopening
  instruction's own explicit example of a semantic reassignment.
- **`alias`**: real cosmetic no-op per BOR.C (see
  `alias_keyword_is_cosmetic_not_identity` project memory) — not an
  animation at all, nothing to gate.

**Definitive coverage ledger** (every real animation/mechanic this
audit's own full-roster pak grep found, roster-wide):

| Mechanic | Real source characters | Status |
|---|---|---|
| `attack1` | every roster member | Done (pre-existing) |
| `attack2` (generic second move) | RALF/JOE/JHUN/LEATHER/LEO/BEBOP/ROCK/FOOT01-04 (varies) | Done (pre-existing, `GATE G7-ATTACK2`) |
| `fall`/`rise` (knockdown) | every roster member | Done (pre-existing, `GATE G7-KNOCKDOWN`) |
| `jump`/`jumpattack`/`jumpattack2` | LEO only | Done (pre-existing, `GATE G7-JUMP`) |
| `special` | LEO only | Done (pre-existing, `GATE G7-SPECIAL`) |
| grab mutual-lock (attack2-is-grab) | JOE only | Done (pre-existing, `GATE G7-GRAB`) |
| `throw` | JOE only (grabber-side) | Done (pre-existing, `GATE G7-THROW`) |
| run/dash | every roster member | Done (pre-existing, `GATE G7-RUN`) |
| AI post-hit invulnerability | every AI entity | Done (pre-existing, `GATE G7-INVULN`) |
| actor ground-depth sort | every roster member | Done (pre-existing, `GATE G7-DEPTH-SORT`) |
| **`atchain` combo (attack1-4 cycling)** | LEO, FOOT01, FOOT02 | **Done (this slice), `GATE G7-CONTENT-AUDIT`** |
| **`attack3`/`attack4`** | LEO (both), FOOT01/FOOT02 (`attack3` only) | **Done (this slice, reached via atchain), `GATE G7-CONTENT-AUDIT`** |
| **generic `grab` role (R button)** | LEO only | **Done (this slice), `GATE G7-CONTENT-AUDIT`** |
| **`grabattack` (R+Y)** | LEO only | **Done (this slice), `GATE G7-CONTENT-AUDIT`** |
| **`slide` (A+Down)** | LEO only | **Done (this slice), `GATE G7-CONTENT-AUDIT`** |
| **`riseattack` (UP+Y while lying)** | BEBOP, ROCK, LEATHER | **Done (this slice), `GATE G7-CONTENT-AUDIT`** |
| `block` | none (zero real anim data in either pak) | Content-inapplicable (pre-existing finding, unchanged) |
| **`freespecial` (double-tap-forward + attack)** | LEO only | **Done (reopened-again slice), `GATE G7-CONTENT-AUDIT`. CORRECTED 2026-08-28: the prior "AI-exclusive" classification was wrong — real `player_preinput()`->`check_combo()` (openbor.c, BEFORE `player_check_special()`) makes this genuinely player-reachable via a `model_init_defaultreadme()`-installed default command.** |
| `land`/`ANI_LAND` | none configured | Content-inapplicable — zero `attack_force`/`blast` config anywhere |
| `waiting` | most roster members | **NOT implemented. CORRECTED 2026-08-28** — see this section's own `waiting`/`ANI_SELECT` entry above; G5 is PARTIAL until this is built and gated. |
| `get` | some roster members | Assigned to G8 (item-pickup pose) |
| `alias` | some roster members | Cosmetic no-op, not an animation |

**G7 caveats as of 2026-08-28: none known in the attack/move dispatch
system itself** (freespecial closed this reopening's flagged gap; the
generated ledger above has zero `partial`/`unhandled-error` rows and
`GATE G7-CONTENT-AUDIT` covers every row marked Done). This claim is scoped
to G7 only — it does NOT cover G5 (`waiting`, genuinely PARTIAL, see
above) or title-logo-art/attract-mode (unbuilt polish, see README.md's
Current Status). Prior "G7 fully exhausted, no known caveats" language
mixed those in; this line intentionally does not repeat that mistake.

Full regression after this slice: `build_rom.py`, `audit_all.py`,
`check_label_drift.py`, `check_width_directives.py` (0 new violations),
`phase5.py`-`phase9.py`, `phase11_damage.py`, `phase12_roster.py`, every
`game_g7_*.py` (including the pre-existing nine), `game_g1_text.py`
through `game_g9_wait_group_boss.py` — all PASS (two individually-known-
flaky Mesen timing checks, `GATE G7-JUMP`'s OAM-Y-on-landing and `GATE
G7-KNOCKDOWN`'s rise-completes-to-idle, each reproduced the identical
flakiness on the pre-slice codebase too, confirmed by direct A/B testing
before attributing either to this slice).

---

## §8 — Phase G8: items and pickups

> **Status: item/pickup work COMPLETE as of the seventh slice (2026-08-29,
> see bottom of this section) -- all 7 targeted gates pass, and
> `phase12_roster.py`/`phase11_damage.py` are green too (fixed the same
> day -- see bottom of this section; the "AnimHeaderStaging shared-scratch
> collision" theory below turned out to be wrong on live tracing and has
> been corrected).**
>
> **Status: DONE, closed 2026-08-30 (claude_close_g7_g8_before_g10.md).**
> The prior COMPLETE claim above still had two real gaps, both closed the
> same day: (1) LEO's real converted `get` (item pickup pose) animation
> was resolved to no engine role at all (real OpenBOR source traced --
> `player_test_pickable`/`didfind_item` -- GET is a cosmetic pose on
> touch-collect, reward applied instantly, not gated on the pose
> completing; `GET_MOVE_VARIANT`, `Character_Pickup_CheckOverlap__
> TriggerGet`/`Jump_PlayGetAdvance` in `core/jump.pasm`, `GATE
> G8-GET-LEO: PASS` via the new `tools/verify/game_g8_get_leo.py`); (2)
> a real shipped item, GOLD (`DATA\EASY\1BEASY.TXT`'s own `item gold`
> line, score=5000), had never been converted at all -- an earlier audit
> pass wrongly claimed it was unused by any shipped level. Converted
> (`out/gold_*`), given its own `PICKUP_TYPE_GOLD`/`PICKUP_SCORE_GOLD`
> distinct from MONEY's value, and verified live against stage 1B's real
> packed spawn record (`GATE G8-PICKUP: PASS`, `tools/verify/
> game_g8_pickup.py`). `tools/coverage_ledger/ledger.json` now has zero
> `partial`/`unhandled-error` rows anywhere in the G8 scope, and `tools/
> coverage_ledger/verify_phase_status.py` (new, Part 4 of the same
> closure doc) mechanically enforces that a phase can't be marked done
> while an unfinished ledger row still exists under it.
>
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

> **Second slice DONE, 2026-08-29 (notjustfreespecial.txt audit).** `GATE
> G8-PICKUP: PASS` (`tools/verify/game_g8_pickup.py`, 12 checks). Real
> health/score/1-up pickup effects, sourced from a direct pak scan (`DATA\
> CHARS\MISC` in the BOR pak has genuine, previously-unconverted item
> content the plan above didn't even enumerate: `APPLE.TXT` `health 30`,
> `MEAT.TXT` `health 100`, `MONEY.TXT` `score 1000`, `1UP.TXT`, real
> OpenBOR's own name=="1up" special case for an extra life), wired to the
> real spawn data that already references them (`DATA\EASY\1AEASY.TXT`'s
> own `spawn 1up` and `item meat`/`item apple`/`item money` lines,
> `1BEASY.TXT`'s own `item Apple`/`item Money`; verified byte-exact
> against a fresh regeneration of both shipped spawn tables, including
> genuinely reproducing a real typo in the pak's own data -- 1BEASY's
> Table spawn writes `2pitem Apple` instead of `item Apple`, so real
> OpenBOR itself would also fail to parse that line and Table correctly
> carries no pickup in this engine either).
>
> Implementation: a new `CHAR_PICKUP_TYPE` struct field (main.pasm, grew
> `CHAR_ZP_LEN` 127->128 -- `Entity1/2/3_Base`/`DpBase` literals updated,
> caught clean by `audit_all.py`'s existing hand-sync guards), packed into
> the spawn record's `record_kind` byte's last 3 spare bits (5-7 -- all 8
> bits of that byte are now in use) by `build_spawn_table.py`'s new
> `classify_pickup`, written by `core/spawn.pasm`'s `Spawn_Play` alongside
> the existing prop HP/mode writes (and explicitly zeroed on the non-prop
> path, so a slot reused later for an ordinary enemy can't inherit a stale
> pickup), and consumed exactly once -- at the real moment a
> `CHAR_INPUT_DRIVEN_PROP` entity's HP reaches 0 from a landed player hit
> -- by a new `Character_HitApply__ApplyPickup` leaf (`core/jump.pasm`,
> bank 8 for ROM budget, same pattern as this file's other routines).
> Effects reuse this project's existing HP-clamp and `Game_Score`-clamp
> idioms; a killing hit still also awards the ordinary combat
> `HIT_SCORE+KILL_SCORE` on top (pre-existing behavior, unchanged by this
> slice -- breaking a real item source nets both the fight-score and the
> item's own value).
>
> **Third slice DONE, same day: value-matched classification + full TMNT
> item/weapon audit.** `classify_pickup` used to name-match `apple`/`meat`/
> `money` -- a real per-pak hardcoding smell. Generalized to match by REAL
> `health`/`score` VALUE instead (health=30 -> APPLE-equivalent, health=100
> -> MEAT-equivalent, score=1000 -> MONEY-equivalent, name=="1up" -> extra
> life), verified against a full spawn-data scan of BOTH shipped paks: **all
> 29 BOR level files** (not just the 2 shipped ones) and **all 10 TMNT level
> files** (8 shipped + `streets3.txt`/`test.txt`, not currently converted).
>
> Real finding from that scan: TMNT's own `data\CHARS\MISC\PIZZA.TXT`
> (`type item`, `health 100`, `subtype touch`) is spawned for real in 3 TMNT
> levels (`streets.txt`, `streets2.txt`, `streets3.txt`) -- a genuinely
> different item name from BOR's roster, previously unhandled by name-based
> matching. The value-based rule above picks it up automatically (same real
> heal value as MEAT) with zero TMNT-specific code. Both shipped TMNT
> stages that spawn it (`out/spawn_stage6streets`, `out/spawn_stage7streets2`)
> were regenerated with `--roster` (preserving their existing
> `RECORD_KIND_BOSS_IDENTIFIED` records, verified unchanged) and now carry
> real pickup bits for it; `GATE G8-PICKUP` and every TMNT boss/roster-
> reassignment gate (`game_g9_tmnt_boss.py`, `game_spawn_roster_reassign.py`,
> `game_g9_wait_group_boss.py`) re-verified clean against the regenerated
> tables.
>
> **Weapons (KNIFE/STAR), resolved, not deferred by assumption:** both are
> real MISC entities in BOTH paks (`type enemy`, an attack hitbox on their
> own idle frame -- a "thrown projectile acting as a fake enemy" trick, not
> `type weapon`; real DCurrent/openbor source confirms `type weapon` exists
> as a distinct, unrelated subtype this pak's data never uses). Verified via
> a direct spawn-data scan, not assumption: **KNIFE/STAR/GOLD are spawned by
> ZERO levels in either pak** (all 29 BOR + all 10 TMNT level files
> checked). This is genuinely content-inapplicable -- there is no real,
> reachable spawn data anywhere in either pak for a weapon/projectile
> mechanic to implement against, so there is nothing to gate. If a future
> pak or a currently-unconverted level ever spawns one, this classification
> must be re-checked, not assumed to still hold.
>
> **TIME**, also a real MISC entity (`type item`) in both paks: genuinely
> spawned by real level data (`DATA\EASY\5AEASY.TXT`/`5AHARD.TXT`, BOR), but
> that level is not currently converted/shipped (only 1A/1B are). Real
> OpenBOR's own TIME semantics add to a level countdown timer this engine
> doesn't have (no G10 pacing/timer system exists) -- correctly
> `unshipped-source-content`, not implemented, not silently ignored.
>
> **Deliberately still not done:** real prop/pickup sprite art -- a prop
> still renders using whichever roster character is already streamed into
> its slot (visually wrong, behaviorally real; the converter's ROLE_NAMES
> architecture requires idle/walk/pain/fall/rise, which single-frame item
> entities like APPLE/MONEY don't have at all, so this isn't a quick
> extension of the existing character pipeline -- it needs its own,
> smaller asset path); the `boss` flag (unrelated to props, see G9, already
> real and gated).

**Fourth slice DONE, same day: real end-to-end chain gate.**
`tools/verify/game_g8_pickup_chain.py`, `GATE G8-PICKUP-CHAIN: PASS` (8/8
checks). Closes the "still open" chain-trace item below using stage 1B's
own real, unmodified spawn data (its Chair/Money record) with zero forced
writes to the entity under test: locates the real AI slot Spawn_Play landed
it in (found empirically, not assumed) by its real CHAR_INPUT_DRIVEN_PROP +
CHAR_PICKUP_TYPE state, lands a real BTN_Y attack, and independently
verifies score award + OAM hide + pickup-type consumption -- proving
source->conversion->packed data->runtime spawn->break->reveal->reward->
removal end-to-end, not just the isolated effect.

**Fifth slice DONE, same day: real prop/pickup sprite art (a representative
real example).** `GATE G8-PROP-ART: PASS`. Closes the last "still open"
item below. New `tools/bor_converter/convert_prop.py` -- a real, minimal,
idle-only converter for MISC item entities (`type item`, e.g. `APPLE.TXT`),
NOT a reuse of `convert_character.py` (verified directly: APPLE/MEAT/MONEY/
1UP all declare exactly one `anim idle`, 1 frame, no walk/pain/fall/rise at
all -- `convert_character.py` hard-requires all 5 and raises loudly if one
is missing, which is the real, sourced reason this needed its own pipeline
rather than a quick extension). Converts the item's real (and only) frame
through the exact same crop/scale/palette-quantize pipeline every fighter
uses, then replicates that real converted directory across the other 4
struct-required roles (walk/attack/fall/rise) -- documented as the correct
representation of "this entity has no distinct animation in the source
data," not fabricated content; `CHAR_INPUT_DRIVEN_PROP` never dispatches
into walk/attack/fall/rise playback anyway, so that data is real but
structurally inert, same rationale already established for a prop's other
struct-required-but-unused fields.

APPLE (a real MISC item, `DATA\CHARS\MISC\APPLE.TXT`) added as roster slot
13 (`build_rom.py`'s `ROSTER_PREFIXES`) -- one representative real example,
not every pickup type (money/meat/1up still render via the pre-existing
borrowed-character behavior until they get their own `convert_prop.py`
pass). Wiring reuses the EXACT SAME mechanism `SPAWN_KIND_BOSS_IDENTIFIED`
already built for real boss character reassignment (`core/spawn.pasm`'s
`Spawn_DoRosterReassign`) rather than inventing a parallel one:
`build_spawn_table.py` now also resolves a prop's real item name (`spawn
apple` standalone, or an `obstacle`'s `item <name>` line) against the
`--roster` list the exact same way a boss's name already is, packing a real
roster_idx into the same +8 byte (0 = "no converted sprite yet," backward
compatible); `core/spawn.pasm`'s dispatch-time `Msu1_StreamBusy` gate and
each slot's prop branch were widened to also call `Spawn_DoRosterReassign`
when a prop record carries a nonzero roster_idx. Both shipped BOR spawn
tables (`out/spawn_stage1a`, `out/spawn_stage1b`) regenerated with the full
14-name `--roster` list; stage 1A's real `item apple` record (index 36)
now carries `roster_idx=13`.

`tools/verify/game_g8_prop_art.py` reaches stage 1A via the same real
force-win idiom `game_spawn_roster_reassign.py` already established (no
direct stage-load path exists in this engine), drives the real single
global spawn queue to the real apple record, and proves the reassignment
against real hardware-visible state: the landing slot's (idle,walk,attack)
frame-count triple becomes `(1,1,1)` -- apple's own real converted moveset,
distinct from every real fighter's triple -- not whatever generic character
the slot had loaded before. (A secondary check against `CHAR_ROSTER_INDEX`,
main.pasm struct offset 12, was dropped after this gate's own development
found it dead: grep-confirmed nothing in main.pasm ever writes it, a
pre-existing gap unrelated to this slice, not a regression it caused.)
Adding a 14th roster slot shifted the packed VM module's MSU offset;
`src/core/vm/vm_load.pasm`'s hand-synced `VM_MSU_OFFSET` was re-synced
(`build_rom.py`'s own `check_vm_constants` catches this class of drift
automatically). Full regression re-verified clean after this slice: `audit_
all.py`, `check_label_drift.py`, `check_width_directives.py`, phase5,
phase11, phase12, `game_g8_pickup.py`, `game_g8_pickup_chain.py`, and
`game_spawn_roster_reassign.py` (the shared boss-reassignment path this
slice's own code sits next to) all still pass.

Still open:

- Real prop/pickup sprite art for money/meat/1up (the same `convert_prop.py`
  pipeline, just not yet run for those three item names -- apple is the
  one converted, gated, representative example this slice added).
  **Roster-cap caveat, checked directly against `pack_msu_roster.py`'s own
  `MAX_CHARACTERS = 15`:** 14 slots are shipped today (indices 0-13,
  `build_rom.py`'s `ROSTER_PREFIXES`), so exactly ONE slot remains. Adding
  all three of money/meat/1up as separate roster entries does not fit
  without first raising `MAX_CHARACTERS` (touches `pack_msu_roster.py`'s
  directory-size math and the packed header layout) -- not "just run the
  converter again" for more than one of the three.

Sixth slice (gate hardening, same day): `game_g8_prop_art.py`'s surviving
proof was an (idle,walk,attack) frame-count triple -- real, but animation
metadata, not the tile/palette identity check the standing bar calls for.
Added a real CGRAM OBJ-palette comparison against apple's own converted
`palette.txt` (same idiom `phase12_roster.py` already established for
fighters), polled to convergence since CGRAM commits through the same
WRAM-shadow/NMI-DMA pipeline as OAM (a fixed short settle read back a
stale in-flight palette once). Separately, `game_g7_depth_sort.py`'s
crossover-step settle (previously a fixed 3-frame wait, itself a fix for
an earlier fixed-2-frame flake) was replaced with a real deterministic
poll against the same CHAR_POS_Y-derived expected-order ground truth the
gate's own post-loop cross-check already uses -- removing the magic
number rather than growing it again. Both re-verified clean across
repeated runs.

**Seventh slice DONE (finish_g8_with_runtime_asset_swapping.md): the
remaining three items get real sprite art, `MAX_CHARACTERS` raised
15->17.** `out/money`/`out/meat`/`out/1up` converted via the same
`convert_prop.py` pipeline apple used, added as roster slots 14/15/16
(`build_rom.py`'s `ROSTER_PREFIXES`); `pack_msu_roster.py`'s `MAX_CHARACTERS`
raised to accommodate. A real slot-reuse art-leak bug found and fixed along
the way: when an AI slot previously carrying a prop got reassigned to a
plain enemy/boss (not another prop), `core/spawn.pasm` never restored it
off the prop's borrowed art -- fixed via `Spawn_ScratchPrevWasProp` capture
+ restore in `Spawn_Play__slot1/2/3`. A second real bug, `CharSelect_Index`
corruption across `Spawn_DoRosterReassign` calls, fixed via save/restore
around the reassignment.

All 7 targeted G8-cluster gates pass clean on the current tree:
`game_g8_pickup.py`, `game_g8_pickup_chain.py`, `game_g8_props.py`,
`game_spawn_roster_reassign.py`, `game_g8_prop_art.py`,
`game_health_override.py`, `game_g8_asset_swapping.py` (new gate for this
slice's own slot-reuse fix). `game_g8_prop_art.py`'s own pre-check had a
real bug fixed in this slice too: it compared the generic (idle,walk,attack)
`(1,1,1)` triple shape, which EVERY `convert_prop.py`-converted item shares
(apple/money/meat/1up all look identical by that metric) -- a different,
legitimately-earlier prop spawn could false-positive it. Fixed to check
`CHAR_PICKUP_TYPE` identity instead.

**`phase12_roster.py`/`phase11_damage.py` corruption -- FIXED, 2026-08-29.
The `AnimHeaderStaging` shared-scratch theory above was a live, honestly
documented hypothesis at the time (real bisection did show the corruption
predates this slice's own roster growth), but it did NOT hold up under
live Mesen2 write-hook tracing and has been corrected. The real root cause
is unrelated to `AnimHeaderStaging` entirely.**

Real chain, traced instruction-by-instruction: `Anim_LoadCharacter`'s
documented calling convention requires callers to be in `.a16`/`.i16`, and
every one of its exit paths re-asserts `rep #$31`/`.a16`/`.i16` before its
own `rts` to guarantee that on return. `core/spawn.pasm`'s
`Spawn_DoRosterReassign` calls it via `jsl Anim_LoadCharacter_Long` from
inside an explicit `sep #$20`/`.a8` region, then -- immediately after the
call returns -- ran its `CharSelect_Index` save/restore pair
(`lda.l Spawn_SavedCharSelectIndex` / `sta.l CharSelect_Index`) still
assuming 8-bit `A`, without re-asserting `.a8` after the callee's `.a16`
exit. Both instructions silently executed as 16-bit instead: the `lda.l`
pulled in `Spawn_SavedCharSelectIndex`'s real byte plus one incidental
adjacent WRAM byte as a bogus high byte, and the `sta.l` then wrote BOTH
bytes across `CharSelect_Index` ($7E53B6, correct) AND the very next byte,
`CharSelect_RosterCount` ($7E53B7, incidentally zeroed). This is a
same-thread, fully synchronous accumulator-width leak across a `jsl`/`rtl`
boundary -- not NMI interruption, not a deferred/multi-frame load lifetime,
not another-entity processing, and not a WRAM address/lifetime conflict of
any kind; `AnimHeaderStaging` was never involved. Fixed with the single
missing `sep #$20`/`.a8` directive right after the `jsl` return, before the
restore pair (see `spawn.pasm`'s own comment there for the full trace
evidence). Verified deterministic (100% reproducible once the width state
was traced, not a race), and confirmed the fix alone (not any diagnostic
side effect) resolves it via extended live-frame checks with the fix
stashed in and out.

Two further, genuinely separate and pre-existing failures surfaced once
that corruption was gone: `phase11_damage.py`'s "entity 3 still animating"
and `phase12_roster.py`'s "Entity #3's CGRAM palette matches slot-3"
checks both failed against stage 1B's real, unmodified spawn table (`git
stash` of the width-leak fix reproduced both identically, proving they are
unrelated to it). Root cause: `core/spawn.pasm`'s live spawn-table path
(`Spawn_Play__slot3`) converts entity slots 2/3 from
`CHAR_INPUT_DRIVEN_AI` to `CHAR_INPUT_DRIVEN_PROP` by ~frame 60 of stage
1B's real content -- confirmed by direct WRAM trace, and confirmed for
entity 3 specifically to also load a genuinely different CGRAM palette at
that same point (not just a flag flip). Both gates' own test setups
predated Phase G8's prop spawn path and assumed entities 2/3 stayed live
AI controls for the whole run; that assumption is simply stale now, not an
engine bug -- a static, single CGRAM palette and a static single-frame
moveset are the CORRECT behavior for a real prop. Fixed in the gates
themselves: `phase11_damage.py` now reads each entity's real
`CHAR_INPUT_DRIVEN` at sample time and only requires frame-index variation
from whichever are still genuinely AI (a prop's own static frame index is
treated as expected, not a failure); `phase12_roster.py` now snapshots
each non-player entity's boot-time CGRAM palette at frame 30 (after
`CharSelect_RosterCount`/entity init settle, confirmed stable by frame 20,
but before the ~frame-60 prop conversion), since its own claim ("each
entity loaded its assigned roster slot at boot") is a boot-time claim.
Both gates, the full static-audit pair, and `phase5`-`phase9` all pass
clean, twice back-to-back, on the fixed tree.

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
| 4 | `boss` flag | **DONE, 2026-08-23 — including real end-to-end coverage.** `record_kind==4`/`EntityN_IsBoss` (2026-08-22) plus the boss health bar (2026-08-23) were already gated against a synthetic record; a real TMNT level (`data\LEVELS\BEBOP.TXT`, one real `boss 1` line) is now converted and shipped as stage index 2, proving the exact same code path against real pak data with zero engine changes — see §9. | — | DONE, see §9 |
| 5 | `blockade` | **Row's own premise was wrong, corrected 2026-08-23.** There is no `blockade` keyword in real `BOR.C` (Plombo/beatsofrage) at all — grep-confirmed, zero hits. The real keyword in the level-header switch (~line 1966) is **`blocked`**, one letter off, and it is NOT scroll-back prevention: `else if(stricmp(command, "blocked")==0){ level->exit_blocked = atoi(...); }`, part of an entirely different `hole`/`blocked`/`endhole` trio (~line 1961-1971) that implements level PIT HAZARDS (`level->holes[]`, drawn as sprites at runtime ~line 4925-4926, checked for player fall-through ~line 2606-2607) with an exit gated shut until a numeric condition (`exit_blocked`, checked ~line 3105/3998) — not a camera scroll-back ratchet at all. This engine has no pit/hole/fall-through mechanic of any kind today (separate from anything `core/screen.pasm` does), so implementing the REAL `hole`/`blocked`/`endhole` trio is a new hazard-entity feature, not a `Screen_MinX` one-liner. Re-verified 2026-08-23: neither shipped BOR level (`1AEASY.TXT`, `1BEASY.TXT`) uses `hole`/`blocked` at all — real value is entirely gated on TMNT conversion. | Row 11 (TMNT); real semantics need re-deriving as a hole/pit system, not scroll-back | NOT STARTED, premise corrected, low current priority |
| 6 | `music` / `bossmusic` | Fully unparsed. Needs a level-scoped music-track-select on top of TAD (today: one hardcoded audio blob loads at boot, no track switching exists at all). Content-gated like G11 (SFX) — only one track is authored/converted today, so there is nothing to switch *to* yet; do not start the code side before at least a second track exists in the pipeline. | Content (a 2nd authored TAD track) | NOT STARTED (blocked on content) |
| 7 | `alias` | **Not a real gap — document and close, 2026-08-23. This row's own premise was wrong.** Read `BOR.C` directly (Plombo/beatsofrage, repo root, not `engine/`): `smartspawn()` (~line 4589) spawns the entity using the REAL `spawn <name>` argument (`props->name`) first — that's what selects the character model/moveset. Only *after* that does it do `if(props->alias[0]) strncpy(e->name, props->alias, MAX_NAME_LEN);` (line 4593) — `alias` purely overwrites the spawned *instance's* display-name string, for on-screen name UI (`font_printf(... player[i].ent->name ...)` at line 2116, HUD player-select at 2130) — it never redirects which resource is spawned. Confirmed against real TMNT pak data too: `data\CHARS\FOOT01\FOOT01.TXT`/`FOOT02.TXT`/`FOOT03.TXT` are three genuinely distinct character models (own `health`/`speed`/`type` each), each spawned via its own real `spawn Foot01`/`spawn Foot02`/etc. line; `alias Foot_Soldier` just gives all three the same *displayed* name for narrative consistency — there is no `Foot_Soldier` model anywhere in the pak. This project's engine has **no per-entity name display anywhere** (grep-confirmed: `spawn_parse.py` already parses `alias` and its own comment calls it "display name override (cosmetic, unused here)"), so there is nothing for it to attach to — `alias` is a genuine no-op here, same call as row 10 (`maxenemy`). **The real gap row 7 was actually gesturing at — spawns never reading their own `character`/model-name field, always rendering whichever roster character is already streamed into the landing AI slot — is real, but has nothing to do with `alias` and is NOT keyword-slice scope**: `Anim_LoadCharacter` is a blocking boot-time MSU seek+read under forced blank (`CharacterEntity_Init`), `Msu1_StreamBusy`'s one-stream-per-frame budget is load-bearing (CLAUDE.md), and OBJ tile columns are statically per-slot — per-spawn character identity means re-streaming both tiles and palette mid-gameplay, not a small addition. That's `§12` (content and scale) territory, tracked there, not resurrected under this row. | — | N/A — permanent no-op in this engine, not tracked further |
| 8 | `direction` | **Row's own premise was wrong, corrected 2026-08-23 — this is NOT a camera-model-rewrite blocker.** Real `BOR.C`'s parser (~line 1904-1909): `value = findarg(...); if("up") SCROLL_UP; else if("down") SCROLL_DOWN; else if("left") SCROLL_LEFT; else SCROLL_RIGHT;` — exactly 4 recognized values (up/down/left, default right), no "rightleft"/bidirectional case exists anywhere in this source (grep-confirmed: the literal string `rightleft` appears NOWHERE else in `BOR.C`, and `scrolldir` is read as a strict `==SCROLL_LEFT`/`==SCROLL_RIGHT`/etc. comparison everywhere it's used, ~15 call sites checked). TMNT's real `STREETS.TXT` does say `direction rightleft` (confirmed directly against the pak) — but run through THIS engine's actual parser, an unrecognized value silently falls through to the `else` branch: plain `SCROLL_RIGHT`. **TMNT's own `direction rightleft` line is therefore a no-op in this specific engine version** (possibly meaningful in some other/newer OpenBOR fork, but not the Plombo/beatsofrage source this project sources from) — real gameplay is ordinary one-directional right-scroll, which this project's existing camera model (`core/screen.pasm`) already implements. **This row is not a blocker for row 11 (TMNT conversion) at all.** | — | N/A — TMNT's real behavior is plain one-directional scroll this engine already supports; not tracked further |
| 9 | `settime` | **Not a real gap today — corrected 2026-08-23, document and close (same call as row 10 `maxenemy`).** `settime` IS a real keyword (unlike `blockade`/row 5) — it's just not in `BOR.C`'s own level-header parser at all (grep-confirmed: zero hits for `settime`/`maxtime` in the source), meaning this specific engine version doesn't act on it even where a level declares it; the real timer mechanism that exists (`timeleft`/`time_over()`, ~line 4701-4714) always hardcodes a fixed 100-second reset at stage load, never reads a per-level value. **More importantly: real content never actually enables it.** Checked every `settime` occurrence across every available pak — zero in either shipped BOR level, and all 4 real TMNT occurrences (`SEWER.TXT`, `SEWER0.TXT`, `STREETS.TXT`, `STREETS2.TXT`) are `settime 0` (disabled). There is no real content anywhere this project has access to that would ever exercise an enabled time limit — building the HUD timer/time-over path described here would have zero real data to build toward or verify against, a worse case than `blockade`'s "gated on TMNT" (TMNT disables it too). | — | N/A — no real enabled usage exists in any available pak; not tracked further |
| 10 | `maxenemy` | **Not a real gap — document and close.** This engine hardcodes exactly 3 AI slots (`CLAUDE.md`'s "don't build a general entity-lookup system" rule); BOR's own `maxenemy` values in the stock/TMNT levels checked (4) are already satisfied trivially by that hardware ceiling. No code change is applicable here; `SPAWN_MAX_RECORDS`/the single-global-queue design (`core/spawn.pasm`'s own header) already reproduces BOR's wave-clustering behavior within that ceiling. | — | N/A — permanent engine constraint, not tracked further |
| 11 | TMNT pak conversion itself | Not a keyword gap — a content-pipeline task. **DONE, 2026-08-23/24**: the full real TMNT pak converted — 10 real stages, full campaign, standalone boss stages, real roster growth to 8 slots, then genuinely grown further to 15 (roster-growth slice, same week) with Bebop/FOOT02-04 added, then LEO added the same day — 13 of 15 slots now used. **Follow-up**: the per-spawn character-identity gap this row used to cite as still-blocking is now closed for every identified boss (Rock/Leather/Bebop all render as themselves via spawn-driven roster reassignment, see §9's own follow-ups) — not universally (ordinary non-boss enemies still reskin, since only characters deliberately given a roster slot have anything real to identify against), but the specific blocker this row named is resolved. | — | DONE (full pak, real roster/campaign, real boss-identity reassignment for every roster-identified boss) |
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

**Historical note (Part 5 doc reconciliation, 2026-08-30):** the "next
slice" framing below (jump/special blocked, real grab mutual-lock still
open) reflects 2026-08-23's real state, before it was resolved -- G7 is
now COMPLETE (see this section's own top-of-§8 status marker analog at
§7) and JOE's grab mutual-lock specifically shipped and is gated (`GATE
G7-GRAB: PASS`, row "grab mutual-lock (attack2-is-grab)" in §7's own
coverage table above). Left as-is below for the historical record of the
decision point, not as a current claim.

**Conclusion, updated 2026-08-23:** §8a is now genuinely, fully exhausted
— every row is either DONE, a permanent no-op (7, 9, 10), correctly
content-gated (6), or waiting on real remaining work outside this table's
scope (5's real hole/pit system needs re-deriving before it's buildable;
11 waits on §12). There is no more unblocked, self-contained row left to
pick. The next slice is a roadmap-priority choice, not a table lookup:
G7's remaining jump/special items (blocked on new animation conversion --
no real anim exists in the source pak for any roster character; note that
`grab` here means only the generic attack2 move that happens to use JOE's
`grab`-named animation role -- real grab mutual-lock semantics are, per
§7's own text, still fully open, not done), or row 5's real hole/pit hazard
system (needs its own semantics re-derivation first). Surface this
choice rather than picking unilaterally.

---

## §8b — Organic vertical-slice integration gate (not a phase, not G10)

`tools/verify/game_vertical_slice.py` chains the real screens and
subsystems every G1-G9 gate above already proves individually, in the
same order a player experiences them in a single continuous session, to
prove they compose -- it adds no new subsystem of its own and is
explicitly NOT Phase G10 (ending/credits, §10 below, remains untouched
pending explicit authorization).

Segments, each the same real mechanism its own dedicated gate already
exercises (reused via direct Python import from
`game_spawn_roster_reassign.py`/`game_g8_pickup_chain.py` where a segment
is byte-for-byte the same chain, rather than reimplemented): forced-title
-> real Start -> char-select (real Right cycles the roster, real Start
finishes the teardown drip into PLAYING) -> real gameplay combat (a real
landed Y attack, no forced HP writes) -> the real, unmodified stage 1B
Chair/Money breakable-prop chain (break -> real `PICKUP_SCORE_MONEY`
reward -> OAM hide) -> a forced player death with lives remaining
(auto-respawn) -> every remaining life exhausted (`GAME_STATE_GAMEOVER`,
continue countdown armed) -> a real Start press continues with fresh
lives -> the real win-condition chain through stages 1-3 -> Rock's real
boss reassignment (stage 3, `check_boss_stage()` reused verbatim) ->
one more real stage transition past the boss. 28 checks, all real
hardware-visible state, no screenshots.

One real, harness-only bug found building this: the combat segment
already held `BTN_Y` for the earlier attack; re-pressing it for the
prop-break segment without an intervening release was invisible to
`input.pasm`'s press-edge detection (Core_Input_Poll only fires on a
fresh press, not a still-held button) -- so no new attack landed. Fixed
by releasing all input for 5 frames before the next press, in the test
harness only; not an engine defect (every other gate in this project
either starts each `open_session` fresh or already releases between
presses).

Run standalone (`python tools/verify/game_vertical_slice.py`); like the
other multi-stage force-win gates in this project, it is not part of the
routine CLAUDE.md regression list (it takes real Mesen2 wall-clock time
comparable to `game_spawn_roster_reassign.py`) -- run it directly after
touching `core/game_state.pasm`, `core/spawn.pasm`, `core/charselect.pasm`,
or the Phase G8 pickup-reward path.

---

## §9 — Phase G9: bosses

> **Status: DONE, reachable in play, 2026-08-23.** A real TMNT boss stage
> is now converted and shipped as stage index 2: `Teenage Mutant Ninja
> Turtles [v.3.0 Build 4153].pak`'s `data\LEVELS\BEBOP.TXT` (`out/
> bg_stage2boss`, `out/spawn_stage2boss`), verified straight from the
> extracted pak text to contain exactly one real `boss 1` line (on `spawn
> Bebop`) plus a decorative `spawn Hydrany` (`type obstacle` → converts to
> `RECORD_KIND_PROP`) and a closing `wait`. `build_spawn_table.py`'s
> `elif e.boss: record_kind = RECORD_KIND_BOSS` branch — already built and
> gated 2026-08-22 against a hand-authored synthetic record — needed **zero
> code changes** to fire correctly against this real data; the only changes
> anywhere were `build_rom.py`'s `BG_SCREENS`/`FP_SCREENS`/`SPAWN_TABLES`
> lists (a 3rd entry) and `core/game_state.pasm`'s `STAGE_COUNT` (2 → 3),
> both already-generalized per-stage mechanisms from G4/Phase 14 — no new
> `.pasm` logic anywhere. `GATE G9-TMNT-BOSS: PASS`
> (`tools/verify/game_g9_tmnt_boss.py`, 12 checks): the real spawn table's
> boss record decodes to `record_kind==4` at the byte level; driving the
> real win condition twice (stage 0→1→2, the untested has-frontpanel →
> no-frontpanel direction) lands cleanly on stage 2 with CGRAM matching
> `out/bg_stage2boss`'s own converter output; the real level's own trigger
> then sets some entity's `EntityN_IsBoss` from actual gameplay advancement
> (a short real held-Right past Bebop's small real `trigger_x`, not a WRAM
> poke); the boss health bar renders a real, non-blank, non-sentinel bar
> for it. The two pre-existing synthetic gates (`game_g9_boss_bar.py`,
> `game_g9_wait_group_boss.py`) were kept, not retired — they still pass
> and still isolate the HUD/flag mechanics from level-conversion variables.
>
> **Real bugs found while building the gate, not the engine** (the engine
> side needed no fixes at all): (1) the first attempt drove the 1→2
> transition by holding Right the same way `game_g4_transition.py` does
> for 0→1 — but stage 1A is 408 tiles wide (real converted data), and a
> real held-Right walk across it never reached the camera-clamp edge
> within a reasonable gate runtime. Fixed by writing `Screen_PosX :=
> Stage_TrueMaxX` directly once `Stage_Cleared` is set, the same "safe to
> write directly" precedent already used for `Spawn_Index`/`CHAR_HP`,
> applied to the other side of the same edge check instead of walking to
> it. (2) `Spawn_Play` arms on `Screen_PosX` (the camera), not player
> position — after landing on the fresh stage 2, the camera sat at 0 and
> Bebop's boss record (real `trigger_x`) never fired until the gate
> actually moved the camera; fixed by holding Right briefly post-landing
> (genuine gameplay, since this specific check exists to prove the real
> trigger fires under real advancement, not another direct write).
>
> **Deliberate scope decision, grounded in this project's own existing
> precedent, not invented for this slice:** the boss entity renders using
> whichever roster character already occupies the AI slot its real spawn
> record lands on (confirmed here: slot 1) — `build_spawn_table.py`'s own
> header has documented this as intended, unchanged behavior since Phase 8
> ("every record spawns using whichever roster character is already wired
> to the slot it lands in"); stage 1A's own `angel` spawns already do
> this today. Converting Bebop's own sprite art and adding it as a new
> roster character was considered and rejected: the fixed 4-entity/roster-
> slot model assigns each entity's roster character once at boot (see
> [[phase15_fourth_character]]/[[phase12_roster_expansion]]), not per-
> stage, so making a boss visually *be* Bebop specifically would need new,
> real per-stage roster-reassignment engine code — a materially bigger,
> riskier slice than "make the already-built G9 plumbing reachable," which
> is now done with zero new `.pasm`. This is the same character-identity
> gap §12 already tracks, not a new one.

> **Corrected premise, 2026-08-23:** the previous version of this section
> (below, both now-struck bullets) assumed real OpenBOR has boss-specific AI
> and a boss-exclusive health bar. It doesn't. Fetched the real source
> (`DCurrent/openbor`, `engine/openbor.c`) to check: `boss` only (a) fires
> `bossmusic` on spawn and (b) decrements `level->bossescount` toward the
> win condition on death — no boss-specific behavior tree exists anywhere
> in `combat.c`/`openbor.c`. The "boss health bar" in real BOR
> (`drawstatus()`'s `elife`) isn't boss-exclusive either — it's a generic
> "current opponent" bar shown for whatever entity `player[i].ent->opponent`
> points at, gated on that entity not having `nolife` set. This project has
> neither an opponent-pointer nor a `nolife` concept, and building the
> generic mechanic has no other use here, so the health bar ships gated
> directly on the existing `EntityN_IsBoss` flag instead (lowest-numbered
> *living* boss-flagged entity wins). "Stage-gating" needed no new code:
> G4's win condition (all AI dead + spawn queue exhausted before the camera
> unlocks) already covers a boss stage with the exact same mechanism as any
> other stage.

- ~~Per-entity HP override (the spawn table has no HP field today — add one).~~ **Done, 2026-08-21** (health-override slice, `+7 spawn_hp` in the spawn record).
- ~~The `boss` flag itself (`spawn_parse.py`'s `SpawnEvent.boss`, already parsed, not yet threaded into the record or read by the engine).~~ **Done, 2026-08-22** (`record_kind==4`, `EntityN_IsBoss` sticky flag) — real data plumbing, verified only via a hand-authored synthetic record (no shipped BOR stage uses `boss`).
- ~~Boss-specific AI beyond "seek and attack".~~ **Cleared, 2026-08-23** — not a real OpenBOR concept (see corrected premise above); no code needed.
- ~~Boss health bar, stage-gating (camera locks until defeated).~~ **Done, 2026-08-23** (`core/hud_boss.pasm`, `Hud_Play__boss_bar`, own bank for ROM budget, entered `jsl` from `main.pasm`'s `Hud_Play`) — gates directly on `EntityN_IsBoss`+HP>0, lowest-numbered living boss wins, blank row when none. Found and fixed two real bugs along the way: `HUD_ROW_BOSS` initially collided with the pre-existing boot-time G1 text demo on row 4 (moved to row 6), and `Hud_DrawBar` (the existing player-bar routine) hardcodes its target buffer as `HudStaging` with no parameter, so an earlier version that called it directly for the boss bar silently drew into the player's own buffer — fixed by duplicating the draw body into `Hud_Play__boss_bar_drawbar` against its own `HudBossStaging`/DMA, per this project's own "small duplicated block over a parameterized shared one" precedent. Stage-gating needed no new code — see corrected premise above. **GATE G9-BOSSBAR: PASS** (`tools/verify/game_g9_boss_bar.py`, 11 checks, hand-authored synthetic force since no shipped BOR stage uses `boss`).

`out/bg_boss_level` already exists as converted assets from an earlier phase.

> **Follow-up, 2026-08-23/24: the full TMNT pak converted, not just one
> boss stage.** The user asked directly why G9 wasn't fully closed out if
> its only real gap was "no shipped level uses `boss`" — the honest answer
> was that this project had only ever converted a single BOR pak's two
> levels; TMNT (a full separate pak already sitting in this repo) had
> real, playable boss content nobody had converted. Rather than declare
> the gap permanently content-blocked, converted the whole real TMNT pak.
> Ten real stages ship now (indices 0-9): the original 2 BOR levels
> (0-1), Bebop's standalone boss stage (2, done first, see above), Rock's
> and Leatherhead's standalone boss stages (3-4), the real 4-level TMNT
> main campaign in its real `Play_Demo` order — `sewer0` → `streets` →
> `streets2` → `sewer` (5-8) — and `foot.txt`, the last standalone TMNT
> level (9). Scene cutscenes (`STORY.TXT`/`ENDING.TXT`) were left out —
> this project has no cutscene-image renderer and building one wasn't in
> scope here.
>
> **Real content facts, verified by extracting and reading every level
> file directly, not assumed:** `streets.txt` and `streets2.txt` each
> have their own real `boss 1` line — Rock and Bebop are fought again as
> *story* bosses, separate spawn tables from their standalone practice
> stages. `sewer0.txt`/`sewer.txt` have none (waves of `mouser`/`foot0X`
> only). `foot.txt`, despite its "Foot Soldier Test" framing, has **no**
> `boss 1` line at all — `spawn Foot3 / alias Foot_Soldier / health 500`
> is just a single reinforced-HP encounter (`alias` was already known to
> be cosmetic here, not identity — see §12). Every prop/decoration name
> in the campaign levels (`Epole`/`Hydrant`/`Plant`/`Tree`/`trash*`/
> `Parkm`/`Pipef*`/`car`/`guy`/`mail`/`Pizza`/`White*`/`Light*`/`Smoke`/
> `Wdrop`) is real TMNT data with `type` = `panel`/`obstacle`/`none`/
> `item` — genuine background scenery or a pickup, not a combatant —
> skipped the same way `Hydrany` was skipped in the Bebop stage.
>
> **Character roster:** converted every real `enemy`-type fighter the
> campaign actually references — `MOUSER` and `FOOT01`-`FOOT04` (5
> characters, same `convert_character.py` pipeline as every prior roster
> addition). Hit a real, hard format limit doing this: the packed
> roster directory is capped at 8 slots (`pack_msu_roster.py` byte
> 0x09), and 4 were already spent (RALF/JHUN/JOE/YASHIRO) — only 4 more
> fit, not 5. FOOT01-04 are mechanically identical in the source data
> (same anim set, same HP=70), so FOOT01 was added as the roster's 6th
> member; FOOT02-04's converted assets are real, committed, and unused
> pending either a roster-capacity rework or the identity fix below.
>
> **A real, load-bearing architectural finding, not a code fix**: per-
> spawn character identity — every enemy, TMNT or BOR, rendering as
> *itself* rather than whatever roster member already occupies its AI
> slot — is not simply unwired data plumbing. `CharacterEntity_Init`'s
> `(role<<8)|roster_index` param and the per-instance `CHAR_ROSTER_INDEX`
> field already exist, but they're only ever set ONCE, at boot — the 3 AI
> entities are created at boot with a fixed roster index each, and
> `Spawn_Play` only ever recycles them (new HP/position/flags), by
> design: the fixed-address `EntityN_Base` scheme can't survive the
> generic OOP kill/GC path (see [[phase11_damage_system_softkill]]).
> Making a spawn load its own character would mean re-triggering
> `Anim_LoadCharacter` — a real asset stream with its own busy-wait/DMA-
> queue sequencing — from inside `Spawn_Play`'s per-frame call, risking
> the one-entity-streams-per-frame invariant this project has broken and
> fixed before. Not attempted; every enemy still renders as whichever
> roster member already occupies its AI slot. This is the same gap §9's
> Bebop section and §12 both already flag — now confirmed, not just
> assumed, to be a real architectural fork rather than a quick slice.
>
> **A real regression found and fixed while running the full suite** (not
> by the new content itself, but by the roster growing past what a
> hand-synced table anticipated): `main.pasm`'s `CharSelect_NamePtrs` —
> one word-pointer entry per roster slot, indexed by `CharSelect_Index`
> — still only had 4 entries after the roster grew to 6. Wrapping to
> slot 4/5 read 2 words of garbage past the table's own end as a string
> pointer. Caught by `game_g5_menus.py`'s own wrap check failing loudly,
> not silently; fixed by adding the 2 missing entries. Two verify
> scripts that hardcoded the old 4-slot roster (and would have masked
> the same bug shape again later) were also fixed: `game_g5_menus.py`'s
> wrap-target name, and `game_g7_grab.py`'s "2 Select presses wraps JOE
> back to RALF" (now derives the press count from the real
> `CharSelect_RosterCount`, never a hardcoded roster size).
>
> **Gate**: `tools/verify/game_tmnt_campaign.py`, `GATE TMNT-CAMPAIGN:
> PASS` — byte-level `RECORD_KIND_BOSS` verification against every new
> stage's real converted spawn table, plus a live force-win walk through
> all 9 real stage-transition edges (0→9), plus CGRAM ground truth on
> the final stage. Deliberately does NOT force stage 6's own story-boss
> (Rock) to fire live in-gate: measured directly that its real
> `trigger_x` (2240) is gated by a real, already-verified `wait` scroll-
> lock mechanic that a quick gate isn't worth fighting to push past — the
> byte-level check plus the already-passing Bebop/Rock-standalone live
> gates already prove the mechanism end-to-end. `game_g9_tmnt_boss.py`
> and the two synthetic G9 gates were kept and still pass.
>
> Full regression suite verified clean at each commit: `build_rom.py`,
> `audit_all.py`, `check_label_drift.py`, `check_width_directives.py`,
> phases 5-12, and every `game_g1`-`game_g9`/`game_health_override`/
> `game_map_remap`/`game_tmnt_campaign` gate.
>
> **Explicitly still open, not silently dropped**: FOOT02-04's converted
> assets sit unused (roster-capacity-capped); the per-spawn character-
> identity gap above; Double Dragon Moto (a separate pak, needs the
> openborscript VM for real level logic — explicitly out of scope, the
> VM stays shelved per standing instruction); scene cutscenes.
>
> **Follow-up, same day (roster-growth slice): the "architectural fork"
> above was real, but not a wall — it got built, not re-deferred.**
> `Anim_LoadCharacter` was already a reusable, mid-game-callable routine
> (the player's own Select-button reselect already invoked it live) —
> `core/spawn.pasm`'s `Spawn_DoRosterReassign` DP-switches to the target AI
> slot and re-runs it, proven end-to-end by
> `tools/verify/game_spawn_roster_reassign.py` (Rock/Leather really render
> as themselves now). That made the roster's OWN 8-slot format cap
> (`pack_msu_roster.py`'s `MAX_CHARACTERS`) the real remaining limiter, not
> the streaming/entity architecture — grown to 15 (a real ceiling of
> `main.pasm`'s existing 8-bit directory-seek arithmetic, `index*17+0x10` in
> one accumulator with no carry; 15 is the largest index that doesn't
> silently wrap, not an arbitrary number). The spawn record itself also
> grew 8→9 bytes: `record_kind`'s 3 spare bits (0-7) couldn't address 15
> slots, so `roster_idx` moved to its own dedicated byte. Bebop was
> converted fresh (it never had real character art before — its boss stage
> always rendered a reskin) and added as roster slot 8; `game_g9_tmnt_boss.py`
> updated accordingly (RECORD_KIND_BOSS_IDENTIFIED, roster_idx=8, same
> mechanism as Rock/Leather). FOOT02-04 also added (slots 9-11), closing out
> the "converted but unused" note above. **Real bugs found while doing
> this**: `SPAWN_MAX_RECORDS` was still 48 — stale since before the TMNT
> campaign shipped — while `streets2` alone real-packs 86 records; every
> stage with >48 records (`sewer0`/`streets`/`streets2`/`sewer`) was
> silently overrunning `SpawnTable_Wram`'s WRAM allocation by hundreds of
> bytes into whatever followed it. Grown to 90. Also: `game_g5_menus.py`'s
> wrap-to-last-slot check caught `CharSelect_NamePtrs` falling behind the
> roster size a *third* time (this exact bug class, twice previously
> documented above) — fixed, and `phase12_roster.py`'s own all-pairs
> palette-distinctness check was found to be the wrong invariant once real
> content included genuine duplicate art (FOOT01-04 are literal palette-
> identical clones in the source pak) — replaced with a ground-truth check
> against each slot's own real converted `palette.txt` instead of a
> pairwise comparison. What's still, correctly, a reskin: every ordinary
> non-boss enemy — only characters deliberately added to the roster (12 of
> 15 slots now used) have anything real to identify against.
>
> Full regression suite re-verified clean after this slice: `build_rom.py`,
> `audit_all.py`, `check_label_drift.py`, `check_width_directives.py`,
> phases 5-12, and every `game_g1`-`game_g9`/`game_health_override`/
> `game_map_remap`/`game_tmnt_campaign`/`game_spawn_roster_reassign`/
> `game_g5_sram`/`game_g5_pause` gate.

> **Follow-up, same day: the per-spawn character-identity gap above is now
> CLOSED for the case that's actually real — real user instruction, not a
> re-investigation that changed its mind.** The "architectural fork" framing
> two paragraphs up was about a GENERAL mechanism (every possible spawned
> name gets its own live sprite); what actually shipped is narrower and
> real: **spawn-driven roster reassignment**. Rock and Leather were added as
> genuine roster members (indices 6/7, `build_rom.py`'s `ROSTER_PREFIXES`,
> same `convert_character.py` pipeline as every prior roster addition — no
> new conversion work, their assets already existed from the standalone
> boss stages). `tools/bg_converter/build_spawn_table.py` now emits
> `RECORD_KIND_BOSS_IDENTIFIED` (record_kind==5) instead of the plain
> `RECORD_KIND_BOSS` (4) for any `boss 1` spawn whose real character name IS
> in the actual shipped roster, carrying that roster index in the record's
> own previously-always-zero spare bits (bits 5-7 of byte +6 — the `map`
> slice already proved bits 3-4 were real, reusable spare space the same
> way; bits 5-7 were provably always zero before this). `core/spawn.pasm`'s
> `Spawn_Play` gates the WHOLE record (not just the reassignment step) on
> `Msu1_StreamBusy` BEFORE `find_slot` even runs and before any HP/position
> write touches a slot — deferring cleanly, with zero side effects, exactly
> like the existing "no free slot"/"trigger not reached" cases, if another
> entity already streamed this frame (a real ordering hazard caught by
> tracing the actual per-frame call order, `Core_Oop_Play` then `Spawn_Play`
> in `game_state.pasm`, not assumed). `Spawn_DoRosterReassign` then
> DP-switches (`phd`/`tcd`/`pld`) to the target AI entity's own window and
> re-runs `Anim_LoadCharacter` (via its existing `Anim_LoadCharacter_Long`
> bank-0 trampoline) — the EXACT SAME live mid-game character reload the
> player's own Select-button reselect already used, just DP-targeted at an
> AI slot instead of always the player. This is not new streaming
> machinery and does not touch the one-entity-streams-per-frame invariant's
> mechanism, only its scheduling.
>
> **Real proof, not a flag check**: `tools/verify/game_spawn_roster_reassign.py`
> (`GATE SPAWN-ROSTER-REASSIGN: PASS`) reaches Rock's and Leather's real
> standalone stages via the real force-win chain, snapshots a live entity's
> (idle,walk,attack) frame-count triple BEFORE the boss's real spawn record
> triggers, then again after — and shows it actually changing from whatever
> roster member the slot booted with (e.g. Joe's real `(10,7,11)`) to the
> boss's own real converted numbers (Rock's real `(6,12,9)`, Leather's real
> `(2,12,5)`), sourced directly from `out/rock_moveset.json`/
> `out/leather_moveset.json`, never invented. `game_tmnt_campaign.py`'s own
> byte-level boss-record check was updated to treat `RECORD_KIND_BOSS` and
> `RECORD_KIND_BOSS_IDENTIFIED` as one family (both still set
> `EntityN_IsBoss`) — Rock's story-boss record in `streets.txt` (stage 6)
> and its standalone record (stage 3) were both regenerated with the real
> identification; Bebop's two boss records (stages 2 and 7) are unchanged
> (`RECORD_KIND_BOSS`, no identification) since Bebop was never added to the
> roster — verified byte-identical before/after regenerating with the
> `--roster` flag, not assumed.
>
> **What is still, correctly, a reskin**: any spawn whose character was
> never added to the roster — Bebop (no `out/bebop_*` character assets
> exist at all), and every ordinary non-boss enemy in every level. The
> roster format's real 8-slot cap (`pack_msu_roster.py` byte 0x09) means
> most spawned names still have nothing real to identify against; this was
> never "give every enemy its own sprite," it was "let an identified boss
> render as itself," and that's what shipped.
>
> Full regression suite re-verified clean after this change (all of
> `build_rom.py`/`audit_all.py`/`check_label_drift.py`/
> `check_width_directives.py`/phases 5-12/every `game_g1`-`game_g9`/
> `game_health_override`/`game_map_remap`/`game_tmnt_campaign` gate, plus
> the new gate above) — including one real, unrelated pre-existing test
> constant that needed updating for the new 8-slot roster:
> `game_g5_menus.py`'s hardcoded "roster's last slot" expectation (was
> `FOOT SOLDIER`, now genuinely `LEATHERHEAD`) — same class of hand-sync
> gap this file already documents having been bitten by once before,
> caught the same way (a gate failing loudly, not silently).
>
> **Follow-up, same day (roster-growth slice): "Bebop was never added to
> the roster" above is no longer true — see this file's roster-growth
> paragraph a few blocks up for the full story.** Bebop was converted fresh
> and added as roster slot 8 once the format's 8-slot cap was grown to 15;
> `game_g9_tmnt_boss.py` now expects `RECORD_KIND_BOSS_IDENTIFIED` with
> `roster_idx=8` for stage 2's boss record, same mechanism proven here for
> Rock/Leather. The roster's real cap is no longer 8 — it's 15, with 12
> slots currently used (RALF/JHUN/JOE/YASHIRO/MOUSER/FOOT01/ROCK/LEATHER/
> BEBOP/FOOT02/FOOT03/FOOT04). What is STILL correctly a reskin, unchanged
> by that slice: every ordinary non-boss enemy — the identification
> mechanism only ever applied to bosses whose real character got a roster
> slot, and most spawned names across these levels still aren't roster
> members. That was a content/scope decision, not a code gap.

---

## §10 — Phase G10: ending and credits

> **Status: DONE, closed 2026-08-30 (`claude_begin_g10_with_approval.md`).**

Stage table exhausted → ending sequence → credits → back to title. Reuses G1's
text renderer (drip-draw step machine, same pattern as Title/CharSelect/Pause)
and G2's state machine (new `GAME_STATE_ENDING` case, real body in
`core/ending.pasm`, own ROM bank). No new subsystem invented.

Source-of-truth: BOR's `DATA\SCENES\ENDING.TXT` plus `DATA\LEVELS.TXT`'s
scene-after-last-level structure show a `playscene()`/`playgif()`-driven
sequence — real content, but pixel-art GIF playback with no SNES equivalent.
Documented adaptation: 3 real text pages stand in for that sequence (credit
text drawn from the shipped scene copy where practical), any-button skip is
faithfully ported (`Input_trigger` advance-or-timeout, matching the source's
skip behavior), no dedicated ending music track since this project's audio
pipeline only ever loads one song.

Implemented: `Game_State_ENDING` dispatch body (`core/ending.pasm`, bank 10,
16-step draw/wait/clear machine); real return-to-title; canonical
`Game_State_NewGameReset` (lives/score/stage-index/spawn/stage reload) called
from the one real choke point every path into gameplay shares
(`CharSelect_Game_State_Play__charselect_enter_playing`), replacing the old
ad hoc per-path reset gaps. Dedicated gate: `tools/verify/game_g10_ending_credits.py`
(`GATE G10`), 14 checks, drives the real stage-clear → ending → 3 credits
pages → title → new-game runtime path (not a direct-write shortcut past the
transition itself), and audits state-reset (score/lives/stage-index cleared
on the real CharSelect→Playing transition).

Full G1-G9-plus-G10 gate suite and static audits re-verified clean on this
build; per-phase ledger verifier confirms G1-G9 remain `done` while this
phase was `partial`, then flips to `done` here.

---

## §11 — Phase G11: real landed-hit SFX (DONE)

> **Status: DONE — implemented, hardened, and verified by the separately
> authorized complete regression suite.**

One real hit sound (BOR's own `DATA\SOUNDS\BEAT1.WAV`) now plays on every
accepted, non-grab landed hit — player-vs-AI (`Character_HitApply_VsEntity1/
2/3` → `Character_HitApply__ScoreAndFinish`) and AI-vs-player
(`Character_HitApply_VsPlayer`) alike, via `soundwork/tad/build/audio-enums.
inc`'s `sfx_hit = 1` (additive; `sfx_stub` stays 0).

The blocker this section used to describe — no authoring project existed for
`soundwork/tad/build/audio-data.bin`, only its compiled outputs survived —
was resolved by forensic reconstruction, not by treating it as a stop
condition. `soundwork/tad/project/02_coin.terrificaudio` (checked in) was
rebuilt from the surviving artifacts: a from-scratch bytecode disassembler
(grounded in the real `audio-driver/src/bytecode.inc` source) decoded the
shipped `s02_coin` song's actual note/instrument/timing content, re-encoded
it back to MML, and recompiling that MML reproduces 336/341 identical bytes
against the original — the remaining 5 bytes are isolated to non-melodic
echo/pan header settings and are tracked, not silently dropped, in
`soundwork/tad/project/reconstruction_oracle.json`. The shared BRR sample was
recovered losslessly (extracted verbatim, not re-encoded) and reused
byte-for-byte.

**Correction found the project file's `_about.version` claim (`0.4.2`) did
not match any real compiler on this machine or in either sibling TAD-using
repo** (`snes-outrun-sa1`, `SNES-SuperMonkeyIsland` both vendor `tad-compiler
0.3.0`) — that field is the TAD *project file format* version, tracked
independently of the compiler CLI version, and the original reconstruction
never actually round-tripped through a real compiler run. It does now:
`soundwork/tad/rebuild.py` uses the real `0.3.0` binary (see its own header
comment on why 0.4.2 was a bad assumption, not ground truth).

**Correction also found `beat1` was misconfigured as a pitched musical
instrument** (`octave` pitch mode, arbitrary `500.0` Hz tuning, note `c3`,
duration `12` SFX ticks ≈ 96 ms) instead of what it actually is — a recorded
~0.379 s impact WAV. Fixed to TAD's `sample_rates: [11025]` one-shot form
(the real source rate), triggered via `play_note 0 48` (bare numeric
sample-rate-table index, not a note name — a musical note name would have
compiled to the same bytes here since a sample-rate instrument only has one
table slot, but the numeric form is the semantically correct one and is what
this project now uses), `48` SFX ticks (source is ≈47.35 ticks at TAD's
125-tick clock — the smallest tick count that doesn't truncate the encoded
one-shot), non-looping, flat `gain F127` envelope (no ADSR note-shaping on a
recorded hit). Regenerating after this fix changed `audio-data.bin` by 10
bytes larger and ~5450 bytes of content-diff against the pre-fix blob — real,
substantial, not cosmetic. `s02_coin`'s own compiled bytes are unaffected
(only `beat1`'s own sample entry and `sfx_hit`'s own bytecode changed);
verified via `soundwork/tad/rebuild.py --check`.

**Removed an accidental `1 == sfx_hit` coupling**: both landed-hit call sites
used to `lda #1` once for `CHAR_HIT_APPLIED` and reuse that same accumulator
value for the SFX id, because both values happened to be `1`. Those meanings
are unrelated. Both sites now explicitly `lda #SFX_HIT_ID` before queueing.
`SFX_HIT_ID` is a hand-maintained Poppy literal (Poppy cannot `.include` a
ca65 `.enum`) kept honest by `tools/rom_audit/check_sfx_id_sync.py`, which
parses the real generated `audio-enums.inc` and fails the build on drift —
now wired into `audit_all.py`.

**Reproducibility tooling added**: `soundwork/tad/rebuild.py --check`/
`--update` recompiles the checked-in project with a real, version-checked
`tad-compiler` binary and diffs against the committed `build/` outputs
(temp-dir first, only overwrites on `--update`); `soundwork/tad/
verify_project.py` is a fast, no-compiler-required hash/metadata check
against `reconstruction_oracle.json` (song/SFX id ordering, TAD IO version,
sample/driver/loader hashes). Neither existed before this hardening pass —
"edit the project, forget to regenerate, ship stale `audio-data.bin`" was a
real silent-failure mode.

**Building that tooling caught a second, more serious real bug in the
process, found only because `tools/verify/phase7.py` asserts ground truth
(the real final transfer address) rather than trusting TAD's own status
byte**: `soundwork/tad/build/tad_blob_syms.pasm` — the Poppy-syntax
constants `main.pasm`'s `LoadAudioData` actually reads at runtime,
hand-ported from ca65 syntax when TAD was first integrated and never wired
into any regeneration step since — went stale by exactly the number of
bytes the beat1 fix grew common data. `Tad_DataTable`'s offset was still the
old, pre-fix value; `LoadAudioData` read the real audio blob's directory
table from the wrong location and, interpreting adjacent unrelated ROM bytes
as if they were a `(source address, size)` pair, streamed something on the
order of 10KB of garbage as "song data." **This did not visibly fail**:
`TadPrivate_state` still reached `PLAYING`, the S-DSP still left reset with
non-zero main volume, and `phase7.py`'s own weaker checks all passed —
exactly the class of false-positive this project's own Phase 7 history
warns about (see this file's Testing section and CLAUDE.md's matching note).
Only `phase7.py`'s exact-address ground-truth assertion (`final queue
address ... is the end of the audio blob`) caught it, landing at `$F767`
instead of the real `$9A14`. Fixed two ways: the stale value corrected, and
`soundwork/tad/rebuild.py` extended to regenerate `tad_blob_syms.pasm`
itself (parsed from a fresh compile's real `audio-data.s` exports, anchored
to `__Tad_AudioData_0`'s real bank:address via `src/main.sym`) on both
`--check` and `--update`, so this exact silent-staleness class cannot
recur unnoticed.

A real, project-specific engine bug surfaced and got fixed along the way:
the new SFX call sites run under a `CharacterEntity`'s own per-instance
`OopDp` window (see CLAUDE.md's entity-system section), but
`Tad_QueueSoundEffect`'s `Tad_sfxQueue_sfx`/`Tad_sfxQueue_pan` are
bare-DP-addressed and assume `D=$0000` (true for every pre-G11 caller, which
only ever ran at boot or from the pause menu). Confirmed via
`add_write_hook`/`add_exec_hook`/`trace_log` instrumentation (not guesswork)
that the write genuinely executed but landed on the wrong physical byte;
fixed with a shared `Tad_QueueSoundEffect_D0` helper (`phd`/`pea $0000`/
`pld` ... `pld`/`rts`) both call sites tail-jmp into. **This engine fix is
preserved unchanged by this hardening pass** — only the SFX id load and the
audio-data content around it changed.

**Architecture note (not a scope change): TAD/SPC700 owns short, low-latency
gameplay/UI sound effects; MSU-1 PCM owns the eventual full-quality
soundtrack.** `s02_coin`'s TAD material is a reconstructed test/placeholder
song, not authorization to move the production soundtrack onto TAD. A hit
SFX request must never write, stop, restart, or otherwise touch MSU-1 track
selection, volume, or play/repeat control — the two audio paths are
independent. The MSU-1 PCM soundtrack path itself remains unbuilt and is
tracked as future work, not silently forgotten by this note.

Gate: `tools/verify/game_g11_sfx.py` — rewritten this hardening pass to
derive every structure offset via `pasm_constant()`/generated sources
instead of hand-copied literals, to observe a new dedicated WRAM counter
(`G11_HitSfxRequestCount`, verification telemetry only, incremented exactly
once per accepted landed-damage SFX request) instead of racing the transient
SFX queue, and to remove retry-as-success loops in favor of deterministic
per-frame observation of each real case: whiff (delta 0), landed hit (delta
1, HP down), continued overlap in the same attack cycle (still delta 1),
second independent hit (delta 2), AI-vs-player (delta 1), grab (delta 0, real
JOE mutual-lock), and invulnerability/rejected-damage (delta 0) — plus an
isolated S-DSP audibility check correlating the request counter to actual
non-silent SPC output through the encoded one-shot's real duration. See the
script's own module docstring for the exact per-case procedure.

This phase intentionally stops at the defined landed-hit SFX scope. The full
BOR SFX library and soundtrack remain future work; see `docs/audio_inventory.md`.

---

## §12 — Phase G12: content and scale (DONE / CLOSED)

G12 is closed. Its accepted production result is the six-actor layout and
single-buffer animation transport: one-player mode supports five NPCs, while
accepted G13 reserves slot 1 for fixed P2 LEO and supports four NPCs in slots
2–5. The transport is not an open redesign project.

The two shortcuts from §0 come due here.

- **Stages.** 10 real stages shipped (2 BOR + the full real TMNT pak: 3
  standalone boss stages, the real 4-level TMNT campaign, and TMNT's last
  standalone level), all reachable via G4's stage transition, generalized
  to N stages with no hand-synced per-stage constants. Double Dragon Moto
  (the third pak in this repo) stays unconverted — its levels need the
  openborscript VM, explicitly shelved. BOR's own remaining ~12 stages
  were never a priority once TMNT proved the pipeline is level-agnostic
  across paks — this is throughput, not research, whenever it's wanted.
- **Characters.** 13 of ~24+ fighters converted and in the roster (RALF/
  JHUN/JOE/YASHIRO from BOR; MOUSER/FOOT01/ROCK/LEATHER/BEBOP/FOOT02/
  FOOT03/FOOT04/LEO from TMNT), plus 4 real non-playable prop/item records
  (APPLE/MONEY/MEAT/1UP, `finish_g8_with_runtime_asset_swapping.md`) — 17
  of `MAX_CHARACTERS`'s current 17-slot cap used. **The old "8→15 is a
  real hardware ceiling" story was WRONG and is corrected here**: `main.
  pasm`'s directory-seek was rewritten to a real 16-bit accumulate loop in
  the very same roster-growth slice that grew the cap, so nothing about
  the seek arithmetic has capped this since — `MAX_CHARACTERS` (`pack_
  msu_roster.py`) is a soft, freely-adjustable Python-side sanity number,
  raised again 15→17 for the two new prop entries with zero engine-side
  seek changes needed, and can be raised again the same way. A frequency/
  shape analysis of every real spawn across all 9 TMNT levels (`mouser`
  67×, the Foot Soldier family 130× combined, Rock/Bebop/Leather 1-3× each
  as named bosses) confirms every recurring FIGHTER shape already has a
  dedicated slot — there is no hidden 6th fighter archetype waiting on
  headroom. Adding more real content past 17 total is a one-line constant
  bump, not an architecture change.
- **Enemies on screen.** The `Msu1_StreamBusy` one-stream-per-frame rule caps
  effective animation rate at 1/N. Six enemies means ~10fps animation. Options,
  roughly in order of cost: keep frequently-used frames VRAM-resident instead of
  re-streaming; give the SA-1 a real role in decompression/composition (it is
  currently doing a static test blit); or accept lower animation rates for
  background enemies.
- **2-player co-op.** This former G12 frontier is now accepted G13 scope. The
  current policy is fixed-session P1 slot 0/P2 LEO slot 1, NPC slots 2–5,
  independent player state, either-controller pause, shared camera/tether, and
  stage handoff. Future player-facing completion/polish is G14.

---

## §13 — Post-G13 roadmap and current frontier

The historical G1–G10 sequence below is retained as implementation history.
The current forward roadmap is:

```text
G14 player-facing two-player completion/polish
  → G15 finish the original Beats of Rage campaign/content
```

### G14 — player-facing two-player completion/polish — COMPLETE

P1 remains normally selectable and P2 remains fixed LEO, explicitly shown in
the player-facing session flow. The HUD presents independent P1/P2 HP, lives,
and score. Accepted G13 lifecycle/combat ownership, one-player/five-NPC
capacity, two-player/four-NPC capacity, stage handoff, pause, and regression
coverage remain intact. The single TextStaging architecture is retained, with
G14 HUD text serialized to at most one flush per gameplay frame.

TEXT-1 was inherited from before G14 and is now closed by restoring the string
pool's bank ownership; see `docs/text_drawstring_inherited_defect.md`.

### G15 — finish the original Beats of Rage campaign/content — BATCH A COMPLETE

G15 Batch A is complete and accepted: the shipped original BOR prefix is
`1AEASY -> 1BEASY -> 1CEASY` (3 of 14 Easy parts), while the existing TMNT
development tail remains after it. Batch B is next, starting with `2EASY`.
The remaining campaign is still audit/plan-only at this point;
the source-backed audit is `docs/g15_bor_campaign_audit.md`.

New engine architecture is added only when reachable game content proves that
it is needed. Animation residency redesign, SA-1 character compositor work,
generic scripting, Double Dragon Moto, arbitrary actor-count growth, and
speculative cache redesign remain future R&D rather than current blockers.

**G15 proposed batch order** — each batch remains playable and ends with a
real transition gate:

```
 A finish original stage 1 (1C; normalize 1A→1B→1C)
 B original stage 2 (2EASY)
 C original stage 3 (3A→3B→3C)
 D original stage 4 (4A→4B)
 E original stage 5 (5A→5B)
 F original final stage 6 (6A→6B→6C) and Rugal handoff
 G 1P full-campaign/ending/title restart plus 2P campaign smoke
 H optional Bonus extra.txt/sewer scene
```

**§8a's level-format-keyword rows slot in around G8/G9/G12 specifically** —
see §8a's own table for the exact per-row blockers instead of re-deriving
them here. §8a is now fully exhausted (re-sourced against `BOR.C`
2026-08-23): rows 3/7 DONE; rows 7/9/10 are permanent no-ops; row 5's real
keyword is `blocked` (a pit-hazard flag, not scroll-back) and needs its
own semantics re-derivation before it's buildable; row 6 (`music`) waits
on content; row 8 (`direction`) turned out to be a no-op for TMNT under
this engine's real parser, not a camera-model blocker — cleared; row 11
(TMNT conversion) is DONE, including spawn-driven roster reassignment for
every identified boss (Rock/Leather/Bebop) and a genuinely grown roster
format (8→15 slots, 12 used) — see §9's own follow-ups for exactly what's
still a reskin (ordinary non-boss enemies only — every character
deliberately given a roster slot now identifies for real).

G11/SOUND is closed for its accepted scope; broader source-backed audio content
remains future work. G12 is closed. Current G13 qualifications remain
explicit: no-target AI movement is TOOLING-LIMITED / UNMEASURED,
confirmed_busy_denials is null/unmeasured, and the synthetic instant-MONEY
branch is NOT_APPLICABLE_UNMEASURED for current packed content.

**Genuinely hard** (expect real research and real bugs):
- ~~**G7's jump / Z axis**~~ — **Done, 2026-08-28** (see §7's jump bullet).
  The real BOR.C height-vs-depth split was translated onto a visual-only 2D
  OAM offset, not a new gameplay axis.
- ~~**G7's actor ground-depth sort**~~ — **Done, 2026-08-28** (see §7's
  depth-sort bullet, the slice right after jump). Revises the line above --
  real depth sorting WAS needed and was built the very next slice, closing
  the gap the jump slice's own header had flagged.
- **G4's cache teardown/reload** — never exercised; two streaming caches.
- **G12's enemy scaling** — a measured hardware bandwidth boundary, not a
  current G13/G14 feature requirement.
- **G14 presentation/regression** — the current bounded player-facing frontier.

**Mostly routine** (the pipeline already proves them):
- Converting more stages and characters.
- Menus and HUD, *once G1 exists*.
- Items, since the level data already carries them.

**A note on effort.** Phases 0–15 and G1–G13 brought the project to the current
accepted two-player slice. Continue with bounded, game-first milestones and a
committed verification gate at each boundary.

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
   failure, not a silent landmine. `CLAUDE.md`'s Poppy toolchain section has
   the full current list with rationale.
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

## G15 Batch A — original BOR stage 1

Batch A is complete when the real Easy prefix is ordered and shipped as
`1AEASY -> 1BEASY -> 1CEASY`, with the existing TMNT stages retained after
it. It does not claim BOR stage 2 or full-campaign completion. The focused
gate is `tools/verify/game_g15_stage1_campaign.py`; see
`docs/g15_batch_a_stage1.md` for the source-content audit. The next bounded
step is Batch B (`2EASY`), not a runtime architecture rewrite.
