; ============================================================================
; core/pausemenu.pasm -- Phase G5 (plan_game.md 5): the pause menu body.
; Own bank (like core/spawn.pasm/core/charselect.pasm/core/hud_boss.pasm
; before it) purely for $C100-$FC00 ROM budget. Entered via
; `jsl Game_State_Play__pausemenu` from core/game_state.pasm's
; Game_State_Play__paused stub; every exit goes through the local
; Game_State_Play__pausemenu_done (rtl), not the bank-0 Game_State_Play__
; done. Same bank-0 trampoline need and reasoning as core/charselect.pasm's
; own header (Core_Text_DrawString ends in `rts`, same-bank-only).
;
; Real-OpenBOR-sourced content (engine/openbor.c's pausemenu(), fetched to
; ground this per the project's "the code is already written" mandate
; rather than inventing a menu shape): a "Pause" header plus exactly two
; selectable rows, "Continue"/"End Game", toggled by Up/Down (this
; project's cursor is a "> "/"  " prefix baked into two string variants per
; row -- see main.pasm's Text_Str_Pause* -- rather than a real sprite
; cursor, matching the existing text-only title/charselect menu style,
; since there's no cheap way to recolor a single BG3 tile here). Start
; commits: Continue resumes PLAYING with zero other state changed (real
; BOR: same); End Game sets Game_Lives to 0 and returns straight to
; GAME_STATE_TITLE -- real BOR's End Game also zeroes every player's lives
; and sets a hard `endgame` flag that unconditionally tears the session
; down with no continue offered, which this project has no equivalent of
; beyond TITLE (the existing "nothing is running" holding state, G2's own
; header) -- skipping the GAMEOVER continue-countdown entirely is
; deliberate, not a shortcut: real BOR's End Game is an intentional quit,
; not a death.
;
; Entered from core/game_state.pasm's Game_State_Play__playing via an
; edge-triggered Start check (real BOR's pausemenu() is likewise entered on
; FLAG_START during gameplay); reuses the same physical BG3 rows as the
; title/charselect screens (8/10/12) since PAUSED is mutually exclusive
; with both in time (only ever entered from PLAYING).
; ============================================================================

PAUSE_ROW_HEADER   = 8
PAUSE_ROW_CONTINUE = 10
PAUSE_ROW_ENDGAME  = 12

PAUSE_STEP_DRAW_HEADER   = 0
PAUSE_STEP_DRAW_CONTINUE = 1
PAUSE_STEP_DRAW_ENDGAME  = 2
PAUSE_STEP_WAIT          = 3
PAUSE_STEP_CLEAR_HEADER  = 4
PAUSE_STEP_CLEAR_CONTINUE = 5
PAUSE_STEP_CLEAR_ENDGAME  = 6
PAUSE_STEP_REDRAW_ENDGAME = 7  ; second half of the Up/Down toggle's
                                ; two-frame drip -- see Game_State_Play__
                                ; pausemenu_wait_toggle's own comment

PAUSE_SELECTOR_CONTINUE = 0
PAUSE_SELECTOR_ENDGAME  = 1

Pause_Step     = $7E27AD   ; .db -- see PAUSE_STEP_* above; zeroed at boot
                            ; (main.pasm) and reset back to DRAW_HEADER by
                            ; Game_State_Play__pausemenu_enter_playing/
                            ; _enter_title below, same self-resetting
                            ; discipline as Title_Step/CharSelect_Step
Pause_NextStep = $7E27AE   ; .db -- before-the-call parameter cell for
                            ; Game_State_Pause_DrawStepRow, same pattern as
                            ; CharSelect_NextStep
Pause_Selector = $7E27AF   ; .db -- PAUSE_SELECTOR_*, which row is
                            ; highlighted; reset to PAUSE_SELECTOR_CONTINUE
                            ; on every entry (Game_State_Pause_CheckEntry
                            ; below), matching real BOR's own `int
                            ; pauselector = 0;` -- a fresh local, reset
                            ; every pausemenu() call, not sticky across
                            ; sessions

; ----------------------------------------------------------------------
; Phase G5: pause-menu step dispatch. Same jmp-not-beq shape as title/
; charselect (this block is far enough from its own top to risk the real
; 65816 +-127-byte conditional-branch limit). Entry: .a16/.i16 (matches
; Game_State_Play's own convention, which the caller is still in when it
; issues the jsl). Exit: every path ends via Game_State_Play__pausemenu_
; done (rtl).
; ----------------------------------------------------------------------
Game_State_Play__pausemenu:
    sep #$20
.a8
    lda.l Pause_Step
    cmp #PAUSE_STEP_WAIT
    bne Game_State_Play__pausemenu_check_draw_header
    jmp Game_State_Play__pausemenu_wait
Game_State_Play__pausemenu_check_draw_header:
.a8
    cmp #PAUSE_STEP_DRAW_HEADER
    bne Game_State_Play__pausemenu_check_draw_continue
    jmp Game_State_Play__pausemenu_draw_header
Game_State_Play__pausemenu_check_draw_continue:
.a8
    cmp #PAUSE_STEP_DRAW_CONTINUE
    bne Game_State_Play__pausemenu_check_draw_endgame
    jmp Game_State_Play__pausemenu_draw_continue
Game_State_Play__pausemenu_check_draw_endgame:
.a8
    cmp #PAUSE_STEP_DRAW_ENDGAME
    bne Game_State_Play__pausemenu_check_clear_header
    jmp Game_State_Play__pausemenu_draw_endgame
Game_State_Play__pausemenu_check_clear_header:
.a8
    cmp #PAUSE_STEP_CLEAR_HEADER
    bne Game_State_Play__pausemenu_check_clear_continue
    jmp Game_State_Play__pausemenu_clear_header
Game_State_Play__pausemenu_check_clear_continue:
.a8
    cmp #PAUSE_STEP_CLEAR_CONTINUE
    bne Game_State_Play__pausemenu_check_clear_endgame
    jmp Game_State_Play__pausemenu_clear_continue
Game_State_Play__pausemenu_check_clear_endgame:
.a8
    cmp #PAUSE_STEP_CLEAR_ENDGAME
    bne Game_State_Play__pausemenu_check_redraw_endgame
    jmp Game_State_Play__pausemenu_clear_endgame
Game_State_Play__pausemenu_check_redraw_endgame:
.a8
    cmp #PAUSE_STEP_REDRAW_ENDGAME
    beq Game_State_Play__pausemenu_check_redraw_endgame_go
    jmp Game_State_Play__pausemenu_done
Game_State_Play__pausemenu_check_redraw_endgame_go:
    jmp Game_State_Play__pausemenu_redraw_endgame

; --- Draw/clear steps below funnel through Game_State_Pause_DrawStepRow
; (A=row, Y=string offset, Pause_NextStep set first) -- same shared-
; epilogue shape as core/charselect.pasm's own DrawStepRow. Clear steps
; reuse Text_Str_TitleBlank -- blank is blank regardless of which screen
; wrote the row. ---
Game_State_Play__pausemenu_draw_header:
    sep #$20
.a8
    lda #PAUSE_STEP_DRAW_CONTINUE
    sta.l Pause_NextStep
    lda #PAUSE_ROW_HEADER
    rep #$31
.a16
.i16
    ldx #0
    ldy #(Text_Str_PauseHeader - Text_StringPool)
    jmp Game_State_Pause_DrawStepRow

Game_State_Play__pausemenu_draw_continue:
    jsr Game_State_Pause_DrawContinueRow
    sep #$20
.a8
    lda #PAUSE_STEP_DRAW_ENDGAME
    sta.l Pause_Step
    jmp Game_State_Play__pausemenu_done

Game_State_Play__pausemenu_draw_endgame:
    jsr Game_State_Pause_DrawEndGameRow
    sep #$20
.a8
    lda #PAUSE_STEP_WAIT
    sta.l Pause_Step
    jmp Game_State_Play__pausemenu_done

; --- WAIT: poll Up/Down (edge-triggered, toggles Pause_Selector and
; redraws both option rows over TWO frames -- see below) and Start
; (edge-triggered, commits the selection and advances to the clear/
; teardown steps). At most one of these fires per frame.
;
; Up/Down redraws CONTINUE this frame, then advances to
; PAUSE_STEP_REDRAW_ENDGAME to redraw END GAME next frame -- NOT two
; same-frame Core_Text_DrawString calls (an earlier version of this file
; did exactly that and hit the real "1024-BOR" bug it otherwise only
; warned about: TextStaging is one shared WRAM buffer with a QUEUED, not
; synchronous, DMA -- the first call's bytes get overwritten by the
; second call's before the first's DMA ever drains, so both rows landed
; showing the SAME (second) string. Caught by tools/verify/game_g5_pause.py's
; own "CONTINUE row redrawn unselected" check reading back a value neither
; call actually wrote. Same one-DrawString-per-frame drip discipline as
; every other menu in this project. ---
Game_State_Play__pausemenu_wait:
    rep #$31
.a16
.i16
    lda.l Input_trigger+1
    and #$0008                     ; Up -- bit3 (Character_PlayFrame__dpad_y's
                                     ; own documented "bit11 of the word = bit3
                                     ; of this byte" layout)
    beq Game_State_Play__pausemenu_wait_check_down
    sep #$20
.a8
    jmp Game_State_Play__pausemenu_wait_toggle
Game_State_Play__pausemenu_wait_check_down:
    rep #$31
.a16
.i16
    lda.l Input_trigger+1
    and #$0004                     ; Down -- bit2
    beq Game_State_Play__pausemenu_wait_check_start
    sep #$20
.a8
Game_State_Play__pausemenu_wait_toggle:
.a8
    lda.l Pause_Selector
    eor #$01
    sta.l Pause_Selector
    jsr Game_State_Pause_DrawContinueRow
    lda #PAUSE_STEP_REDRAW_ENDGAME
    sta.l Pause_Step
    jmp Game_State_Play__pausemenu_done

Game_State_Play__pausemenu_redraw_endgame:
    jsr Game_State_Pause_DrawEndGameRow
    sep #$20
.a8
    lda #PAUSE_STEP_WAIT
    sta.l Pause_Step
    jmp Game_State_Play__pausemenu_done
Game_State_Play__pausemenu_wait_check_start:
    rep #$31
.a16
.i16
    lda.l Input_trigger+1
    and #$0010                     ; Start -- same high-byte layout as
                                     ; title/charselect's own check
    bne Game_State_Play__pausemenu_wait_start_pressed
    jmp Game_State_Play__pausemenu_done
Game_State_Play__pausemenu_wait_start_pressed:
    sep #$20
.a8
    lda #PAUSE_STEP_CLEAR_HEADER
    sta.l Pause_Step
    jmp Game_State_Play__pausemenu_done

Game_State_Play__pausemenu_clear_header:
    sep #$20
.a8
    lda #PAUSE_STEP_CLEAR_CONTINUE
    sta.l Pause_NextStep
    lda #PAUSE_ROW_HEADER
    rep #$31
.a16
.i16
    ldx #0
    ldy #(Text_Str_TitleBlank - Text_StringPool)
    jmp Game_State_Pause_DrawStepRow

Game_State_Play__pausemenu_clear_continue:
    sep #$20
.a8
    lda #PAUSE_STEP_CLEAR_ENDGAME
    sta.l Pause_NextStep
    lda #PAUSE_ROW_CONTINUE
    rep #$31
.a16
.i16
    ldx #0
    ldy #(Text_Str_TitleBlank - Text_StringPool)
    jmp Game_State_Pause_DrawStepRow

Game_State_Play__pausemenu_clear_endgame:
    sep #$20
.a8
    lda #PAUSE_ROW_ENDGAME
    rep #$31
.a16
.i16
    ldx #0
    ldy #(Text_Str_TitleBlank - Text_StringPool)
    jsl Core_Text_DrawString_Long
    sep #$20
.a8
    ; Commit the selection now that all three rows are clean -- Continue
    ; resumes PLAYING untouched; End Game zeroes lives and returns to
    ; TITLE (see this file's own header for why TITLE, not GAMEOVER).
    lda.l Pause_Selector
    cmp #PAUSE_SELECTOR_ENDGAME
    beq Game_State_Play__pausemenu_endgame
    lda #PAUSE_STEP_DRAW_HEADER
    sta.l Pause_Step            ; reset for the next time PAUSED is entered
    rep #$31
.a16
.i16
    lda #GAME_STATE_PLAYING
    sta.l Game_State
    jmp Game_State_Play__pausemenu_done
Game_State_Play__pausemenu_endgame:
    sep #$20
.a8
    lda #PAUSE_STEP_DRAW_HEADER
    sta.l Pause_Step            ; reset for the next time PAUSED is entered
    lda #0
    sta.l Game_Lives
    rep #$31
.a16
.i16
    lda #GAME_STATE_TITLE
    sta.l Game_State
    jmp Game_State_Play__pausemenu_done

; ----------------------------------------------------------------------
; Game_State_Pause_DrawStepRow -- shared epilogue for the header draw/clear
; steps above: draw the row (A/X/Y already loaded per Core_Text_DrawString's
; own convention), advance Pause_Step to Pause_NextStep (set by the caller
; before the jmp here), then finish. Reached via jmp (callers have no
; return-address use for it). Entry: .a16/.i16 in (Core_Text_DrawString's).
; Exit: Game_State_Play__pausemenu_done (rtl).
; ----------------------------------------------------------------------
Game_State_Pause_DrawStepRow:
    jsl Core_Text_DrawString_Long
    sep #$20
.a8
    lda.l Pause_NextStep
    sta.l Pause_Step
    jmp Game_State_Play__pausemenu_done

; ----------------------------------------------------------------------
; Game_State_Pause_DrawContinueRow/DrawEndGameRow -- draw one option row
; with the correct selected/unselected string per Pause_Selector. Shared
; (jsr'd, returns) by the initial two-step draw sequence and the Up/Down
; redraw in WAIT -- all three call sites finish (via Game_State_Play__
; pausemenu_done) themselves after these return. Entry/exit: .a8 in, .a8
; out (matches every call site).
; ----------------------------------------------------------------------
Game_State_Pause_DrawContinueRow:
    sep #$20
.a8
    lda.l Pause_Selector
    cmp #PAUSE_SELECTOR_CONTINUE
    bne Game_State_Pause_DrawContinueRow_unsel
    rep #$31
.a16
.i16
    lda #PAUSE_ROW_CONTINUE
    ldx #0
    ldy #(Text_Str_PauseContinueSel - Text_StringPool)
    jsl Core_Text_DrawString_Long
    sep #$20
.a8
    rts
Game_State_Pause_DrawContinueRow_unsel:
    rep #$31
.a16
.i16
    lda #PAUSE_ROW_CONTINUE
    ldx #0
    ldy #(Text_Str_PauseContinueUnsel - Text_StringPool)
    jsl Core_Text_DrawString_Long
    sep #$20
.a8
    rts

Game_State_Pause_DrawEndGameRow:
    sep #$20
.a8
    lda.l Pause_Selector
    cmp #PAUSE_SELECTOR_ENDGAME
    bne Game_State_Pause_DrawEndGameRow_unsel
    rep #$31
.a16
.i16
    lda #PAUSE_ROW_ENDGAME
    ldx #0
    ldy #(Text_Str_PauseEndGameSel - Text_StringPool)
    jsl Core_Text_DrawString_Long
    sep #$20
.a8
    rts
Game_State_Pause_DrawEndGameRow_unsel:
    rep #$31
.a16
.i16
    lda #PAUSE_ROW_ENDGAME
    ldx #0
    ldy #(Text_Str_PauseEndGameUnsel - Text_StringPool)
    jsl Core_Text_DrawString_Long
    sep #$20
.a8
    rts

Game_State_Play__pausemenu_done:
    rtl

; ----------------------------------------------------------------------
; Game_State_Pause_CheckEntry -- called every PLAYING frame from bank 0
; (core/game_state.pasm's Game_State_Play__playing) to check Start and
; enter PAUSED. Deliberately just this one check, not the whole PAUSED
; dispatch above -- called unconditionally every PLAYING frame, so its
; bank-0 call site's own footprint (jsl+bcs, 6 bytes) matters far more
; than this routine's own size, unlike Game_State_Play__pausemenu itself
; (called only while already PAUSED). Entry: .a16/.i16. Exit: carry set
; if PAUSED was just entered this frame (caller skips the rest of
; __playing this frame, same as any other PLAYING exit); carry clear
; otherwise. Clobbers A.
; ----------------------------------------------------------------------
Game_State_Pause_CheckEntry:
.a16
    lda.l Input_trigger+1
    and #$0010
    beq Game_State_Pause_CheckEntry_no
    lda #GAME_STATE_PAUSED
    sta.l Game_State
    sep #$20
.a8
    lda #PAUSE_SELECTOR_CONTINUE
    sta.l Pause_Selector        ; real BOR resets pauselector=0 every entry
    rep #$31
.a16
.i16
    sec
    rtl
Game_State_Pause_CheckEntry_no:
    clc
    rtl
