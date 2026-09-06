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
; rather than inventing a menu shape): a "Pause" header plus two selectable
; rows, "Continue"/"End Game", toggled by Up/Down (this project's cursor is
; a "> "/"  " prefix baked into two string variants per row -- see
; main.pasm's Text_Str_Pause* -- rather than a real sprite cursor, matching
; the existing text-only title/charselect menu style, since there's no
; cheap way to recolor a single BG3 tile here). Start commits: Continue
; resumes PLAYING with zero other state changed (real BOR: same); End Game
; sets Game_Lives to 0 and returns straight to GAME_STATE_TITLE -- real
; BOR's End Game also zeroes every player's lives and sets a hard `endgame`
; flag that unconditionally tears the session down with no continue
; offered, which this project has no equivalent of beyond TITLE (the
; existing "nothing is running" holding state, G2's own header) -- skipping
; the GAMEOVER continue-countdown entirely is deliberate, not a shortcut:
; real BOR's End Game is an intentional quit, not a death.
;
; Phase G5 SRAM slice (2026-08-23): a third row, "MUSIC VOL", the one real,
; buildable item from real BOR's savedata-backed options (see
; core/options.pasm's own header for the full real-source scope
; justification -- music volume only, nothing else has real content behind
; it in this project). Real BOR reaches its options screen from pausemenu()
; via a dedicated FLAG_SCREENSHOT key (menu_options() -> menu_options_
; sound()); this hardware has no spare button for a whole separate screen,
; so the one real, buildable option is folded directly into this same
; three-row list instead of inventing a second screen this project can't
; reach. Left/Right adjust it (matching menu_options_sound()'s own
; dir-based +/-step behavior) and persist to SRAM immediately, same as real
; BOR's own no-separate-save-step behavior; Start on this row just resumes
; PLAYING (there is no state to commit -- the value's already live and
; already saved).
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
PAUSE_ROW_VOLUME   = 14   ; Phase G5 SRAM slice -- row 14 is otherwise
                            ; unused by title/charselect/HUD (see
                            ; core/game_state.pasm/main.pasm's own *_ROW_*
                            ; constants), safe to reuse the same way 8/10/12
                            ; already are

PAUSE_STEP_DRAW_HEADER   = 0
PAUSE_STEP_DRAW_CONTINUE = 1
PAUSE_STEP_DRAW_ENDGAME  = 2
PAUSE_STEP_WAIT          = 3
PAUSE_STEP_CLEAR_HEADER  = 4
PAUSE_STEP_CLEAR_CONTINUE = 5
PAUSE_STEP_CLEAR_ENDGAME  = 6
PAUSE_STEP_REDRAW_ENDGAME = 7   ; middle third of the Up/Down toggle's
                                  ; three-frame full-redraw drip -- see
                                  ; Game_State_Play__pausemenu_wait_toggle's
                                  ; own comment
PAUSE_STEP_DRAW_VOLUME    = 8   ; Phase G5 SRAM slice, added below
PAUSE_STEP_CLEAR_VOLUME   = 9
PAUSE_STEP_REDRAW_CONTINUE = 10 ; first third of the toggle redraw drip
PAUSE_STEP_REDRAW_VOLUME   = 11 ; last third

PAUSE_SELECTOR_CONTINUE = 0
PAUSE_SELECTOR_ENDGAME  = 1
PAUSE_SELECTOR_VOLUME   = 2   ; Phase G5 SRAM slice

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
    bne Game_State_Play__pausemenu_check_draw_volume
    jmp Game_State_Play__pausemenu_redraw_endgame
Game_State_Play__pausemenu_check_draw_volume:
.a8
    cmp #PAUSE_STEP_DRAW_VOLUME
    bne Game_State_Play__pausemenu_check_clear_volume
    jmp Game_State_Play__pausemenu_draw_volume
Game_State_Play__pausemenu_check_clear_volume:
.a8
    cmp #PAUSE_STEP_CLEAR_VOLUME
    bne Game_State_Play__pausemenu_check_redraw_continue
    jmp Game_State_Play__pausemenu_clear_volume
Game_State_Play__pausemenu_check_redraw_continue:
.a8
    cmp #PAUSE_STEP_REDRAW_CONTINUE
    bne Game_State_Play__pausemenu_check_redraw_volume
    jmp Game_State_Play__pausemenu_redraw_continue
Game_State_Play__pausemenu_check_redraw_volume:
.a8
    cmp #PAUSE_STEP_REDRAW_VOLUME
    beq Game_State_Play__pausemenu_check_redraw_volume_go
    jmp Game_State_Play__pausemenu_done
Game_State_Play__pausemenu_check_redraw_volume_go:
    jmp Game_State_Play__pausemenu_redraw_volume

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
    lda #PAUSE_STEP_DRAW_VOLUME
    sta.l Pause_Step
    jmp Game_State_Play__pausemenu_done

Game_State_Play__pausemenu_draw_volume:
    jsr Game_State_Pause_DrawVolumeRow
    sep #$20
.a8
    lda #PAUSE_STEP_WAIT
    sta.l Pause_Step
    jmp Game_State_Play__pausemenu_done

; --- WAIT: poll Up/Down (edge-triggered, cycles Pause_Selector among the
; three rows and redraws all three over a three-frame drip -- see below),
; Left/Right (edge-triggered, adjusts the volume row and persists to SRAM
; when it's the selected row -- Phase G5 SRAM slice), and Start
; (edge-triggered, commits the selection and advances to the clear/
; teardown steps). At most one of these fires per frame.
;
; Up/Down redraws CONTINUE this frame, then advances through
; PAUSE_STEP_REDRAW_ENDGAME/_REDRAW_VOLUME to redraw the other two rows one
; per frame -- NOT same-frame Core_Text_DrawString calls (an earlier
; version of this file did exactly that for the original two-row menu and
; hit the real "1024-BOR" bug it otherwise only warned about: TextStaging
; is one shared WRAM buffer with a QUEUED, not synchronous, DMA -- two
; calls in one frame corrupt each other, the first call's bytes
; overwritten by the second's before its own DMA ever drains. Caught by
; tools/verify/game_g5_pause.py's own "CONTINUE row redrawn unselected"
; check reading back a value neither call actually wrote. Same
; one-DrawString-per-frame drip discipline as every other menu in this
; project, now with a third row.) Redrawing all three rows on every
; Up/Down (not just the two whose selected/unselected state actually
; changed) trades two harmless extra frames of latency for never having to
; track "which row was previously selected" -- each DrawXRow already reads
; the current Pause_Selector itself, so redrawing is always correct
; regardless of which transition happened. ---
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
    jmp Game_State_Play__pausemenu_wait_toggle_up
Game_State_Play__pausemenu_wait_check_down:
    rep #$31
.a16
.i16
    lda.l Input_trigger+1
    and #$0004                     ; Down -- bit2
    beq Game_State_Play__pausemenu_wait_check_left
    sep #$20
.a8
    jmp Game_State_Play__pausemenu_wait_toggle_down

Game_State_Play__pausemenu_wait_toggle_up:
.a8
    lda.l Pause_Selector
    bne Game_State_Play__pausemenu_wait_toggle_up_dec
    lda #PAUSE_SELECTOR_VOLUME      ; wrap 0 -> 2
    bra Game_State_Play__pausemenu_wait_toggle_common
Game_State_Play__pausemenu_wait_toggle_up_dec:
    dec a
    bra Game_State_Play__pausemenu_wait_toggle_common

Game_State_Play__pausemenu_wait_toggle_down:
.a8
    lda.l Pause_Selector
    cmp #PAUSE_SELECTOR_VOLUME
    bne Game_State_Play__pausemenu_wait_toggle_down_inc
    lda #PAUSE_SELECTOR_CONTINUE     ; wrap 2 -> 0
    bra Game_State_Play__pausemenu_wait_toggle_common
Game_State_Play__pausemenu_wait_toggle_down_inc:
    inc a
Game_State_Play__pausemenu_wait_toggle_common:
.a8
    sta.l Pause_Selector
    lda #AUDIO_SEMANTIC_BEEP
    ldx #SFX_BEEP_ID
    jsl Audio_QueueResidentSemantic
    jsr Game_State_Pause_DrawContinueRow
    lda #PAUSE_STEP_REDRAW_ENDGAME
    sta.l Pause_Step
    jmp Game_State_Play__pausemenu_done

Game_State_Play__pausemenu_redraw_endgame:
    jsr Game_State_Pause_DrawEndGameRow
    sep #$20
.a8
    lda #PAUSE_STEP_REDRAW_VOLUME
    sta.l Pause_Step
    jmp Game_State_Play__pausemenu_done

Game_State_Play__pausemenu_redraw_continue:
    jsr Game_State_Pause_DrawContinueRow
    sep #$20
.a8
    lda #PAUSE_STEP_WAIT
    sta.l Pause_Step
    jmp Game_State_Play__pausemenu_done

Game_State_Play__pausemenu_redraw_volume:
    jsr Game_State_Pause_DrawVolumeRow
    sep #$20
.a8
    lda #PAUSE_STEP_WAIT
    sta.l Pause_Step
    jmp Game_State_Play__pausemenu_done

Game_State_Play__pausemenu_wait_check_left:
    rep #$31
.a16
.i16
    lda.l Input_trigger+1
    and #$0002                     ; Left -- bit1
    beq Game_State_Play__pausemenu_wait_check_right
    sep #$20
.a8
    jmp Game_State_Play__pausemenu_wait_volume_left
Game_State_Play__pausemenu_wait_check_right:
    rep #$31
.a16
.i16
    lda.l Input_trigger+1
    and #$0001                     ; Right -- bit0
    beq Game_State_Play__pausemenu_wait_check_start
    sep #$20
.a8
    jmp Game_State_Play__pausemenu_wait_volume_right

; --- Left/Right only do anything while the volume row is selected -- real
; BOR's menu_options_sound() likewise only reacts to Left/Right on its own
; volume selector row. Not selected: fall straight through to WAIT with no
; change (real BOR's dir-based adjust is gated the same way, one big `if
; (selector == N)` per row). Adjust + persist via core/options.pasm's
; Options_VolumeUp/Down (own bank, jsl), then a single-frame redraw of just
; the volume row -- no cursor moved, so unlike Up/Down this needs only the
; one DrawVolumeRow call, not the three-row drip. ---
Game_State_Play__pausemenu_wait_volume_left:
.a8
    lda.l Pause_Selector
    cmp #PAUSE_SELECTOR_VOLUME
    beq Game_State_Play__pausemenu_wait_volume_left_go
    jmp Game_State_Play__pausemenu_done
Game_State_Play__pausemenu_wait_volume_left_go:
    jsl Options_VolumeDown
    jsl Options_ApplyMusicVolume_Long
    jsr Game_State_Pause_DrawVolumeRow
    jmp Game_State_Play__pausemenu_done

Game_State_Play__pausemenu_wait_volume_right:
.a8
    lda.l Pause_Selector
    cmp #PAUSE_SELECTOR_VOLUME
    beq Game_State_Play__pausemenu_wait_volume_right_go
    jmp Game_State_Play__pausemenu_done
Game_State_Play__pausemenu_wait_volume_right_go:
    jsl Options_VolumeUp
    jsl Options_ApplyMusicVolume_Long
    jsr Game_State_Pause_DrawVolumeRow
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
    lda #AUDIO_SEMANTIC_BEEP2
    ldx #SFX_BEEP2_ID
    jsl Audio_QueueResidentSemantic
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
    lda #PAUSE_STEP_CLEAR_VOLUME
    sta.l Pause_NextStep
    lda #PAUSE_ROW_ENDGAME
    rep #$31
.a16
.i16
    ldx #0
    ldy #(Text_Str_TitleBlank - Text_StringPool)
    jmp Game_State_Pause_DrawStepRow

Game_State_Play__pausemenu_clear_volume:
    sep #$20
.a8
    lda #PAUSE_ROW_VOLUME
    rep #$31
.a16
.i16
    ldx #0
    ldy #(Text_Str_TitleBlank - Text_StringPool)
    jsl Core_Text_DrawString_Long
    sep #$20
.a8
    ; Commit the selection now that all four rows are clean -- Continue and
    ; Volume both just resume PLAYING untouched (Volume has nothing to
    ; commit: the value was already applied+saved live on every Left/Right
    ; press -- see this file's own header); End Game zeroes lives and
    ; returns to TITLE (see this file's own header for why TITLE, not
    ; GAMEOVER).
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

; ----------------------------------------------------------------------
; Game_State_Pause_DrawVolumeRow -- Phase G5 SRAM slice: draw the volume
; row's label+cursor and current value in ONE Core_Text_DrawLabeledNumber
; call (see that routine's own header -- it composes both column ranges
; into a single TextStaging pass before its one flush, so it's exactly as
; safe to call once per frame as Core_Text_DrawString, unlike calling
; DrawString then a separate DrawNumber would be). Entry/exit: .a8 in,
; .a8 out (matches DrawContinueRow/DrawEndGameRow above).
; ----------------------------------------------------------------------
Game_State_Pause_DrawVolumeRow:
    sep #$20
.a8
    lda.l Options_MusicVolume
    rep #$31
.a16
.i16
    and #$00FF
    sta.l Text_LabelValue
    sep #$20
.a8
    lda.l Pause_Selector
    cmp #PAUSE_SELECTOR_VOLUME
    bne Game_State_Pause_DrawVolumeRow_unsel
    lda #PAUSE_ROW_VOLUME
    rep #$10
.i16
    ldx #0
    ldy #(Text_Str_PauseVolumeSel - Text_StringPool)
    jsl Core_Text_DrawLabeledNumber_Long
    sep #$20
.a8
    rts
Game_State_Pause_DrawVolumeRow_unsel:
.a8
    lda #PAUSE_ROW_VOLUME
    rep #$10
.i16
    ldx #0
    ldy #(Text_Str_PauseVolumeUnsel - Text_StringPool)
    jsl Core_Text_DrawLabeledNumber_Long
    sep #$20
.a8
    rts

Game_State_Play__pausemenu_done:
    rtl

Options_Initialized = $7E27B1   ; .db -- Phase G5 SRAM slice, see
                                  ; Game_State_Pause_CheckEntry below;
                                  ; power-on-zero, same precedent as every
                                  ; other *_Step "zeroed at boot" WRAM cell

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
;
; Phase G5 SRAM slice: also does the one-time SRAM read (core/options.pasm's
; Options_Init) and initial TAD volume apply (main.pasm's bank-0
; Options_ApplyMusicVolume_Long trampoline) on the very first call ever --
; NOT at scpu_boot, deliberately: this routine is already jsl'd from bank 0
; every PLAYING frame with zero additional bank-0 ROM cost, whereas two
; more permanent jsl's living in scpu_boot would cost 8 bytes in a bank
; that was already over its $C100-$FC00 budget building this feature.
; Practically identical timing either way -- this fires on the first
; PLAYING frame after boot, well before any player action reaches a real
; input read, not a meaningfully later point.
; ----------------------------------------------------------------------
Game_State_Pause_CheckEntry:
.a16
    sep #$20
.a8
    lda.l Options_Initialized
    bne Game_State_Pause_CheckEntry_options_done
    inc a
    sta.l Options_Initialized
    jsl Options_Init
    jsl Options_ApplyMusicVolume_Long
Game_State_Pause_CheckEntry_options_done:
    rep #$31
.a16
.i16
    lda.l Input_trigger+1
    and #$0010
    bne Game_State_Pause_CheckEntry__enter
    lda.l G13_TwoPlayerEnabled
    and #$0001
    beq Game_State_Pause_CheckEntry_no
    lda.l Input2_trigger+1
    and #$0010
    beq Game_State_Pause_CheckEntry_no
Game_State_Pause_CheckEntry__enter:
    lda #AUDIO_SEMANTIC_PAUSE
    ldx #SFX_BEEP2_ID
    jsl Audio_QueueResidentSemantic
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
