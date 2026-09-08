; ============================================================================
; core/ending.pasm -- Phase G10 (plan_game.md 10): ending/credits body. Own
; bank (like core/spawn.pasm/charselect.pasm/pausemenu.pasm/hud_boss.pasm/
; jump.pasm/depth_sort.pasm before it) purely for $C100-$FC00 ROM budget.
; Entered via `jsl Game_State_Play__ending` from core/game_state.pasm's
; GAME_STATE_ENDING dispatch (set once, by Game_State_Play__stageclear, the
; instant Game_StageIndex would advance past STAGE_COUNT -- see that file's
; own Phase G4 header). Every exit goes through the local
; Game_State_Play__ending_done (rtl), not the bank-0 Game_State_Play__done.
; Same bank-0 trampoline need and reasoning as core/charselect.pasm's own
; header (Core_Text_DrawString ends in `rts`, same-bank-only).
;
; Real-source-derived shape (claude_begin_g10_with_approval.md's own
; "G10 source-of-truth audit" requirement -- see DATA\LEVELS.TXT and
; DATA\SCENES\ENDING.TXT in the shipped BOR pak, both fetched and read
; directly, not guessed): the last level-order entry in every one of BOR's
; 3 difficulty sets is `scene data/scenes/ending.txt`, reached only once
; the final stage's own `next` marker advances past the last real level --
; exactly this project's own Game_StageIndex+1>=STAGE_COUNT edge
; (core/game_state.pasm's Game_State_Play__stageclear). ENDING.TXT itself
; is OpenBOR's real "scene" format (engine/openbor.c's playscene()): one
; `music` line, then a sequence of full-screen `animation <gif>` clips
; (falla/fallb/consp/creds/thanks.gif, 320x240, 71-1500 real hand-drawn
; frames each) played back to back. playscene()'s own animation dispatch
; (playgif()) treats ANY button (or ESC) as a real skip -- confirmed by
; reading its source directly, not assumed -- so a player-skippable
; sequence is real, sourced behavior, not an invented convenience.
;
; Documented SNES adaptation (per that same governing doc's explicit
; permission: "whether the credits are source-authored or need a
; documented SNES adaptation"): this project has no full-screen-video or
; arbitrary-cutscene-art pipeline -- only per-character sprite streaming
; and per-level BG tilemaps (see CLAUDE.md's own Architecture section).
; Losslessly porting 1500 real hand-drawn animation frames of pixel art is
; a whole new asset-conversion subsystem this task's own governing doc
; explicitly says not to invent ("do not invent a giant cinematic... build
; the smallest faithful ending/credits sequence supported by the real
; content and this project"). This project already HAS the primitive the
; real content structurally needs -- a paginated, skippable, full-row text
; sequence -- because Title_Step/CharSelect_Step/Pause_Step (core/
; game_state.pasm, charselect.pasm, pausemenu.pasm) are exactly that;
; Ending_Step below is one more instance of the SAME established idiom,
; not a new subsystem. It maps the real scene's own 3-beat structure
; (falla+fallb+consp = story beat, creds = credits, thanks = thank-you)
; onto 3 real text pages instead of pixel-art playback: a completion
; message, a real credits page (this project's own name/tools/original-
; game attribution -- the only text content honestly derivable from a
; scene whose real "creds.gif" is pixel art this project cannot losslessly
; transcribe), and a thank-you page. Skip/advance is real (any button
; advances the current page immediately, matching playgif()'s own any-
; button-skips behavior) with a bounded ~6s auto-advance fallback so the
; sequence can never soft-lock with no input, same discipline
; GAME_OVER_CONTINUE_FRAMES already established.
;
; Audio (G10 requirement 7, "if source-backed content exists"): ENDING.TXT
; starts a real distinct music track (`data/music/time.bor`). This
; project's own TAD audio pipeline has exactly ONE song converted and
; loaded, ever, at boot (main.pasm's scpu_boot, song_id=1) -- there is no
; second, ending-specific track in this project's audio conversion state,
; and authoring a whole new MML song + TAD conversion pass is real new
; content work outside a "reuse existing subsystems" ROM-adaptation task.
; No source-backed distinct ending track exists in THIS project (as
; opposed to the original PC game) -- so, same as every other non-PLAYING
; state already does (TITLE/PAUSED/CHARSELECT/GAMEOVER never stop or
; switch music either, per core/game_state.pasm's own PAUSED comment
; "Music keeps playing"), the ending leaves the one continuous background
; song exactly as it already is. Documented non-action, not an oversight.
;
; State reset (G10's own "State reset audit"): ending itself resets only
; its OWN step/timer (self-resetting, same discipline as Title_Step) before
; returning to GAME_STATE_TITLE -- it does NOT reset Game_Score/Game_
; StageIndex/spawn/entity/roster state itself. That reset lives at the
; single real choke point every "start a fresh game" path already shares --
; core/charselect.pasm's Game_State_Play__charselect_enter_playing, via the
; new Game_State_NewGameReset (core/game_state.pasm) -- so returning to
; TITLE from here behaves identically to returning to TITLE any other way
; (GAMEOVER timeout, pause-menu End Game): the player sees a real,
; genuinely-fresh CHARSELECT/PLAYING the next time they press Start,
; without this file needing to know anything about that reset itself.
; ============================================================================

; ----------------------------------------------------------------------
; Game_State_NewGameReset -- the single canonical "start a genuinely fresh
; game" reset. Called via `jsl` directly (bank 10 already ends in `rtl`,
; no bank-0 trampoline needed for THIS direction) from core/charselect.
; pasm's Game_State_Play__charselect_enter_playing -- the ONE real choke
; point every path into gameplay passes through (CHARSELECT is only ever
; entered from TITLE, see that file's own header; there is no separate
; mid-game reselect that reaches CHARSELECT). Lives here, not in bank-0
; core/game_state.pasm, because the full routine overflowed the $C100-
; $FC00 region the instant it was added there (confirmed empirically) --
; same "relocate, don't shrink" precedent core/spawn.pasm's own header
; cites. Reaches Stage_Load/Game_State_RespawnPlayer (both bank-0,
; same-bank-only `rts` routines) via the single combined Stage_
; LoadAndRespawn_Long trampoline (main.pasm) instead.
;
; Covers both the player's very first game (boot's own zero-init already
; matches these values, so this is a harmless no-op re-assertion that
; frame) and a real new game after GAME_STATE_ENDING returns to TITLE
; (where Game_Score/Game_StageIndex/etc. would otherwise still hold the
; JUST-FINISHED playthrough's values -- G10's own "state reset audit"
; requirement).
;
; Reuses Stage_Load (Phase G4's own full boot-style reload -- already
; proven safe across 9 consecutive real transitions by game_tmnt_campaign.
; py) for every piece of per-stage state a fresh game also needs reset
; (spawn queue/index, EntityN_IsBoss, stream caches, HUD-dirty flag,
; playfield border, camera clamp) instead of re-deriving any of it here --
; loading "stage 0" IS the correct reset for all of that, not a
; coincidence. Game_State_RespawnPlayer (Phase G3, already used by both
; the mid-game-death and GAME OVER continue paths) covers the player's own
; HP/hit-stun/facing/position the same well-tested way, and must run
; AFTER Stage_Load (it reads the current camera position, which Stage_
; Load itself resets for the new stage). Only the fields NEITHER of those
; two existing routines owns are set explicitly below: Game_Score, G13_P2Score,
; Game_Lives, and G13_P2Lives; the remaining stage cells are also reset here.
; Game_StageIndex/Bg_LoadScene_StageIndex/Stage_Cleared/Stage_
; LoadPending (Stage_Load's caller's job, same contract Game_State_Play__
; stageclear_next already follows).
;
; Deliberately NOT reset here (matches this project's own "don't blindly
; zero everything" discipline): CharSelect_Index (real BOR remembers the
; last-used roster selection into the next game; this project already
; carries it as an ordinary WRAM cell with no session boundary, and
; nothing about "returning to title" is documented anywhere in this
; project as clearing it), Options_MusicVolume/SRAM (a settings value, not
; session state).
;
; Entry/exit convention: .a16/.i16 in (matches every other routine
; core/charselect.pasm reaches via `jsl`); exit via `rtl`.
; ----------------------------------------------------------------------
Game_State_NewGameReset:
    sep #$20
.a8
    lda #GAME_LIVES_START
    sta.l Game_Lives
    sta.l G13_P2Lives
    lda #0
    sta.l G13_P1Out
    sta.l G13_P2Out
    lda #0
    sta.l Bg_LoadScene_StageIndex
    sta.l Stage_Cleared
    sta.l Stage_LoadPending
    rep #$31
.a16
.i16
    lda #0
    sta.l Game_Score
    sta.l G13_P2Score
    sta.l Game_StageIndex
    jsl Stage_LoadAndRespawn_Long
    jsl G13_ReapplyP1Out
    ; Stage_Load reinitializes the five non-player windows.  In two-player
    ; mode slot 1 is reserved for P2 for the entire session, so restore that
    ; actor through the same bounded roster-load path before PLAYING resumes.
    jsl G13_EnsureP2AfterStage
    rep #$31
.a16
.i16
    lda #GAME_STATE_PLAYING
    sta.l Game_State
    rtl

ENDING_ROW_LINE1 = 10   ; same physical BG3 rows title/pause/charselect
ENDING_ROW_LINE2 = 12   ; already reuse -- mutually exclusive in time

ENDING_PAGE_TIMEOUT = 360   ; ~6s @ 60Hz bounded auto-advance, same
                             ; discipline as GAME_OVER_CONTINUE_FRAMES

ENDING_STEP_DRAW_A1  = 0
ENDING_STEP_DRAW_A2  = 1
ENDING_STEP_WAIT_A   = 2
ENDING_STEP_CLEAR_A1 = 3
ENDING_STEP_CLEAR_A2 = 4
ENDING_STEP_DRAW_B1  = 5
ENDING_STEP_DRAW_B2  = 6
ENDING_STEP_WAIT_B   = 7
ENDING_STEP_CLEAR_B1 = 8
ENDING_STEP_CLEAR_B2 = 9
ENDING_STEP_DRAW_C1  = 10
ENDING_STEP_DRAW_C2  = 11
ENDING_STEP_WAIT_C   = 12
ENDING_STEP_CLEAR_C1 = 13
ENDING_STEP_CLEAR_C2 = 14
ENDING_STEP_RETURN   = 15

Ending_Step     = $7E2801   ; .db -- see ENDING_STEP_* above; zeroed at
                             ; boot (main.pasm) and self-reset on every
                             ; real return to TITLE (Game_State_Play__
                             ; ending_return below), same discipline as
                             ; Title_Step/CharSelect_Step/Pause_Step
Ending_NextStep = $7E2802   ; .db -- before-the-call parameter cell for
                             ; Game_State_Ending_DrawStepRow, same pattern
                             ; as Pause_NextStep/CharSelect_NextStep
Ending_Timer    = $7E2803   ; .dw -- frames remaining in the current WAIT
                             ; step before auto-advancing; reloaded to
                             ; ENDING_PAGE_TIMEOUT on every WAIT entry

; ----------------------------------------------------------------------
; Phase G10: ending/credits step dispatch. Same jmp-not-beq shape as
; title/charselect/pausemenu (this block is far enough from its own top to
; risk the real 65816 +-127-byte conditional-branch limit). Entry: .a16/
; .i16 (matches Game_State_Play's own convention, which the caller is
; still in when it issues the jsl). Exit: every path ends via
; Game_State_Play__ending_done (rtl).
; ----------------------------------------------------------------------
Game_State_Play__ending:
    sep #$20
.a8
    lda.l Ending_Step
    cmp #ENDING_STEP_WAIT_A
    bne Game_State_Play__ending_check_wait_b
    jmp Game_State_Play__ending_wait_a
Game_State_Play__ending_check_wait_b:
.a8
    cmp #ENDING_STEP_WAIT_B
    bne Game_State_Play__ending_check_wait_c
    jmp Game_State_Play__ending_wait_b
Game_State_Play__ending_check_wait_c:
.a8
    cmp #ENDING_STEP_WAIT_C
    bne Game_State_Play__ending_check_draw_a1
    jmp Game_State_Play__ending_wait_c
Game_State_Play__ending_check_draw_a1:
.a8
    cmp #ENDING_STEP_DRAW_A1
    bne Game_State_Play__ending_check_draw_a2
    jmp Game_State_Play__ending_draw_a1
Game_State_Play__ending_check_draw_a2:
.a8
    cmp #ENDING_STEP_DRAW_A2
    bne Game_State_Play__ending_check_clear_a1
    jmp Game_State_Play__ending_draw_a2
Game_State_Play__ending_check_clear_a1:
.a8
    cmp #ENDING_STEP_CLEAR_A1
    bne Game_State_Play__ending_check_clear_a2
    jmp Game_State_Play__ending_clear_a1
Game_State_Play__ending_check_clear_a2:
.a8
    cmp #ENDING_STEP_CLEAR_A2
    bne Game_State_Play__ending_check_draw_b1
    jmp Game_State_Play__ending_clear_a2
Game_State_Play__ending_check_draw_b1:
.a8
    cmp #ENDING_STEP_DRAW_B1
    bne Game_State_Play__ending_check_draw_b2
    jmp Game_State_Play__ending_draw_b1
Game_State_Play__ending_check_draw_b2:
.a8
    cmp #ENDING_STEP_DRAW_B2
    bne Game_State_Play__ending_check_clear_b1
    jmp Game_State_Play__ending_draw_b2
Game_State_Play__ending_check_clear_b1:
.a8
    cmp #ENDING_STEP_CLEAR_B1
    bne Game_State_Play__ending_check_clear_b2
    jmp Game_State_Play__ending_clear_b1
Game_State_Play__ending_check_clear_b2:
.a8
    cmp #ENDING_STEP_CLEAR_B2
    bne Game_State_Play__ending_check_draw_c1
    jmp Game_State_Play__ending_clear_b2
Game_State_Play__ending_check_draw_c1:
.a8
    cmp #ENDING_STEP_DRAW_C1
    bne Game_State_Play__ending_check_draw_c2
    jmp Game_State_Play__ending_draw_c1
Game_State_Play__ending_check_draw_c2:
.a8
    cmp #ENDING_STEP_DRAW_C2
    bne Game_State_Play__ending_check_clear_c1
    jmp Game_State_Play__ending_draw_c2
Game_State_Play__ending_check_clear_c1:
.a8
    cmp #ENDING_STEP_CLEAR_C1
    bne Game_State_Play__ending_check_clear_c2
    jmp Game_State_Play__ending_clear_c1
Game_State_Play__ending_check_clear_c2:
.a8
    cmp #ENDING_STEP_CLEAR_C2
    beq Game_State_Play__ending_clear_c2_go
    jmp Game_State_Play__ending_return
Game_State_Play__ending_clear_c2_go:
    jmp Game_State_Play__ending_clear_c2

; --- Draw steps: A = completion message (real trigger: Game_StageIndex+1
; >= STAGE_COUNT, i.e. every real stage genuinely cleared -- distinct
; wording from the ordinary per-stage "stage clear" text, matching G10
; requirement 2). B = credits. C = thanks. Clear steps reuse Text_Str_
; TitleBlank -- blank is blank regardless of which screen wrote the row.
; Same shared-epilogue shape as core/charselect.pasm/pausemenu.pasm's own
; DrawStepRow. ---
Game_State_Play__ending_draw_a1:
    sep #$20
.a8
    lda #ENDING_STEP_DRAW_A2
    sta.l Ending_NextStep
    lda #ENDING_ROW_LINE1
    rep #$31
.a16
.i16
    ldx #0
    ldy #(Text_Str_EndingA1 - Text_StringPool)
    jmp Game_State_Ending_DrawStepRow

Game_State_Play__ending_draw_a2:
    sep #$20
.a8
    lda #ENDING_STEP_WAIT_A
    sta.l Ending_NextStep
    lda #ENDING_ROW_LINE2
    rep #$31
.a16
.i16
    ldx #0
    ldy #(Text_Str_EndingA2 - Text_StringPool)
    jmp Game_State_Ending_DrawStepRow

Game_State_Play__ending_draw_b1:
    sep #$20
.a8
    lda #ENDING_STEP_DRAW_B2
    sta.l Ending_NextStep
    lda #ENDING_ROW_LINE1
    rep #$31
.a16
.i16
    ldx #0
    ldy #(Text_Str_EndingB1 - Text_StringPool)
    jmp Game_State_Ending_DrawStepRow

Game_State_Play__ending_draw_b2:
    sep #$20
.a8
    lda #ENDING_STEP_WAIT_B
    sta.l Ending_NextStep
    lda #ENDING_ROW_LINE2
    rep #$31
.a16
.i16
    ldx #0
    ldy #(Text_Str_EndingB2 - Text_StringPool)
    jmp Game_State_Ending_DrawStepRow

Game_State_Play__ending_draw_c1:
    sep #$20
.a8
    lda #ENDING_STEP_DRAW_C2
    sta.l Ending_NextStep
    lda #ENDING_ROW_LINE1
    rep #$31
.a16
.i16
    ldx #0
    ldy #(Text_Str_EndingC1 - Text_StringPool)
    jmp Game_State_Ending_DrawStepRow

Game_State_Play__ending_draw_c2:
    sep #$20
.a8
    lda #ENDING_STEP_WAIT_C
    sta.l Ending_NextStep
    lda #ENDING_ROW_LINE2
    rep #$31
.a16
.i16
    ldx #0
    ldy #(Text_Str_EndingC2 - Text_StringPool)
    jmp Game_State_Ending_DrawStepRow

Game_State_Play__ending_clear_a1:
    sep #$20
.a8
    lda #ENDING_STEP_CLEAR_A2
    sta.l Ending_NextStep
    lda #ENDING_ROW_LINE1
    rep #$31
.a16
.i16
    ldx #0
    ldy #(Text_Str_TitleBlank - Text_StringPool)
    jmp Game_State_Ending_DrawStepRow

Game_State_Play__ending_clear_a2:
    sep #$20
.a8
    lda #ENDING_STEP_DRAW_B1
    sta.l Ending_NextStep
    lda #ENDING_ROW_LINE2
    rep #$31
.a16
.i16
    ldx #0
    ldy #(Text_Str_TitleBlank - Text_StringPool)
    jmp Game_State_Ending_DrawStepRow

Game_State_Play__ending_clear_b1:
    sep #$20
.a8
    lda #ENDING_STEP_CLEAR_B2
    sta.l Ending_NextStep
    lda #ENDING_ROW_LINE1
    rep #$31
.a16
.i16
    ldx #0
    ldy #(Text_Str_TitleBlank - Text_StringPool)
    jmp Game_State_Ending_DrawStepRow

Game_State_Play__ending_clear_b2:
    sep #$20
.a8
    lda #ENDING_STEP_DRAW_C1
    sta.l Ending_NextStep
    lda #ENDING_ROW_LINE2
    rep #$31
.a16
.i16
    ldx #0
    ldy #(Text_Str_TitleBlank - Text_StringPool)
    jmp Game_State_Ending_DrawStepRow

Game_State_Play__ending_clear_c1:
    sep #$20
.a8
    lda #ENDING_STEP_CLEAR_C2
    sta.l Ending_NextStep
    lda #ENDING_ROW_LINE1
    rep #$31
.a16
.i16
    ldx #0
    ldy #(Text_Str_TitleBlank - Text_StringPool)
    jmp Game_State_Ending_DrawStepRow

Game_State_Play__ending_clear_c2:
    sep #$20
.a8
    lda #ENDING_STEP_RETURN
    sta.l Ending_NextStep
    lda #ENDING_ROW_LINE2
    rep #$31
.a16
.i16
    ldx #0
    ldy #(Text_Str_TitleBlank - Text_StringPool)
    jmp Game_State_Ending_DrawStepRow

; --- WAIT steps: real skip (any button, matching playgif()'s own
; FLAG_ANYBUTTON check, sourced from engine/openbor.c directly -- see this
; file's own header) OR a bounded ~6s auto-advance so the sequence can
; never soft-lock. Input_trigger is the FULL 16-bit "newly pressed this
; frame" word (core/input.pasm) -- any bit set, dpad included, counts as
; a real button press here, an honest SNES stand-in for BOR's own
; FLAG_ANYBUTTON|FLAG_ESC check. ---
Game_State_Play__ending_wait_a:
    rep #$31
.a16
.i16
    jsr Game_State_Ending_PollAdvance
    bcs Game_State_Play__ending_wait_a_advance
    jmp Game_State_Play__ending_done
Game_State_Play__ending_wait_a_advance:
    sep #$20
.a8
    lda #ENDING_STEP_CLEAR_A1
    sta.l Ending_Step
    jmp Game_State_Play__ending_done

Game_State_Play__ending_wait_b:
    rep #$31
.a16
.i16
    jsr Game_State_Ending_PollAdvance
    bcs Game_State_Play__ending_wait_b_advance
    jmp Game_State_Play__ending_done
Game_State_Play__ending_wait_b_advance:
    sep #$20
.a8
    lda #ENDING_STEP_CLEAR_B1
    sta.l Ending_Step
    jmp Game_State_Play__ending_done

Game_State_Play__ending_wait_c:
    rep #$31
.a16
.i16
    jsr Game_State_Ending_PollAdvance
    bcs Game_State_Play__ending_wait_c_advance
    jmp Game_State_Play__ending_done
Game_State_Play__ending_wait_c_advance:
    sep #$20
.a8
    lda #ENDING_STEP_CLEAR_C1
    sta.l Ending_Step
    jmp Game_State_Play__ending_done

; ----------------------------------------------------------------------
; Game_State_Ending_PollAdvance -- shared WAIT-step body: reloads Ending_
; Timer to ENDING_PAGE_TIMEOUT the FIRST frame a WAIT step is entered
; (detected via Ending_Timer itself already being 0 -- Ending_Step's own
; step-machine guarantees a WAIT step is only ever reached freshly once
; per page, immediately after its own DRAW_*2 step, so a genuinely-just-
; expired real 0 here is unreachable: this same routine always advances
; the step the instant the timer hits 0), then checks Input_trigger
; (any button) or the timer expiring. Returns carry SET if this page
; should advance now, carry CLEAR otherwise (caller just returns without
; changing Ending_Step, same as every other WAIT step's own "keep
; waiting" no-op path). Entry/exit convention: .a16/.i16.
; ----------------------------------------------------------------------
Game_State_Ending_PollAdvance:
.a16
    lda.l Ending_Timer
    bne Game_State_Ending_PollAdvance__have_timer
    lda #ENDING_PAGE_TIMEOUT
    sta.l Ending_Timer
Game_State_Ending_PollAdvance__have_timer:
    lda.l Input_trigger
    bne Game_State_Ending_PollAdvance__advance
    lda.l Ending_Timer
    dec a
    sta.l Ending_Timer
    bne Game_State_Ending_PollAdvance__no_advance
Game_State_Ending_PollAdvance__advance:
    sep #$20
.a8
    lda #0
    sta.l Ending_Timer
    sta.l Ending_Timer+1
    rep #$31
.a16
.i16
    sec
    rts
Game_State_Ending_PollAdvance__no_advance:
    clc
    rts

; ----------------------------------------------------------------------
; Game_State_Play__ending_return -- the sequence finished (all 3 pages
; shown and cleared). Real BOR: playscene() returning from ENDING.TXT
; falls the level-order loop out (current_level now >= numlevels), which
; unwinds back to the attract-mode/main-menu loop -- this project's own
; "nothing is running, waiting for Start" holding state is GAME_STATE_
; TITLE (G2's own header), so that is the faithful equivalent. Self-resets
; Ending_Step for the next time ENDING is entered, same discipline as
; every other *_Step cell in this project. Does NOT reset Game_Score/
; Game_StageIndex/spawn/entity state itself -- see this file's own header
; for why that reset correctly lives at core/charselect.pasm's
; Game_State_Play__charselect_enter_playing instead.
; ----------------------------------------------------------------------
Game_State_Play__ending_return:
    sep #$20
.a8
    lda #ENDING_STEP_DRAW_A1
    sta.l Ending_Step
    rep #$31
.a16
.i16
    lda #GAME_STATE_TITLE
    sta.l Game_State
    jmp Game_State_Play__ending_done

; ----------------------------------------------------------------------
; Game_State_Ending_DrawStepRow -- shared epilogue for every draw/clear
; step above: draw the row (A/X/Y already loaded exactly per Core_Text_
; DrawString's own convention), advance Ending_Step to Ending_NextStep
; (set by the caller before the jmp here), then finish. Reached via jmp
; (callers have no return-address use for it). Entry: .a16/.i16 in
; (Core_Text_DrawString's). Exit: Game_State_Play__ending_done (rtl).
; ----------------------------------------------------------------------
Game_State_Ending_DrawStepRow:
    jsl Core_Text_DrawString_Long
    sep #$20
.a8
    lda.l Ending_NextStep
    sta.l Ending_Step
    jmp Game_State_Play__ending_done

Game_State_Play__ending_done:
    rep #$31
.a16
.i16
    rtl
