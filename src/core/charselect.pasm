; ============================================================================
; core/charselect.pasm -- Phase G5 (plan_game.md 5): character-select screen
; body. Split into its own bank (like core/spawn.pasm before it -- see that
; file's own header for the precedent) purely for ROM budget: this dispatch
; is real content (7 steps, two roster-cycling directions, a shared name-
; lookup redraw) and did not fit alongside the rest of core/game_state.pasm
; in the $C100-$FC00 window. Re-skins the roster machinery that already
; exists (CharSelect_Index/RosterCount/Loaded, Anim_LoadCharacter -- the
; same live-reselect path the Select button has used since plan.md Phase 5)
; as a real screen, rather than inventing new roster logic.
;
; Entered via `jsl Game_State_Play__charselect` from core/game_state.pasm's
; own top-level dispatch (Game_State_Play__check_charselect); every exit
; path here goes through the local Game_State_Play__charselect_done label
; (rtl), NOT the bank-0 Game_State_Play__done -- the caller does its own
; `jmp Game_State_Play__done` immediately after the jsl returns. Anim_
; LoadCharacter and Core_Text_DrawString both live in bank 0 and end in
; `rts` (same-bank-only return) -- calling them directly with `jsl` from
; here would corrupt the stack (jsl pushes a 3-byte return address; rts
; only pops 2, leaving the bank byte behind for the next `rts` to
; misinterpret as a return address byte). main.pasm's Anim_LoadCharacter_
; Long/Core_Text_DrawString_Long are small bank-0 trampolines
; (`jsr <real routine> / rtl`) built for exactly this: a normal same-bank
; `jsr` in, a long `rtl` back out to this bank. Neither trampoline changes
; the original routine or any of its existing same-bank callers.
;
; Same one-DrawString-per-frame drip discipline as the title screen (see
; core/game_state.pasm's own Phase G5 header) -- TextStaging is one shared
; buffer with a QUEUED DMA, so at most one Core_Text_DrawString call may
; happen per frame, including the redraw triggered by a Left/Right press.
; ============================================================================

; ----------------------------------------------------------------------
; Phase G5: character-select step dispatch. Same jmp-not-beq shape as the
; title dispatch in core/game_state.pasm (this block is far enough from its
; own top to risk the real 65816 +-127-byte conditional-branch limit).
; Entry: .a16/.i16 (matches Game_State_Play's own convention, which the
; caller in core/game_state.pasm is still in when it issues the jsl).
; Exit: every path ends via Game_State_Play__charselect_done (rtl).
; ----------------------------------------------------------------------
Game_State_Play__charselect:
    ; notjustfreespecial.txt G5 slice: this state never ran any OAM render
    ; path at all before this (see core/jump.pasm's CharSelect_PortraitUpdate
    ; header for the confirmed-by-inspection finding) -- refresh the real
    ; char-select portrait sprite every frame this state is dispatched,
    ; regardless of which step below runs (and stream a pending reselect's
    ; new frame, deferred one frame past the reselect itself -- see that
    ; routine's header for why). Self-contained (own php/rep/sep bracket,
    ; any entry width), exits .a8.
    jsl CharSelect_PortraitUpdate
    sep #$20
.a8
    lda.l CharSelect_Step
    cmp #CHARSELECT_STEP_WAIT
    bne Game_State_Play__charselect_check_draw_header
    jmp Game_State_Play__charselect_wait
Game_State_Play__charselect_check_draw_header:
.a8
    cmp #CHARSELECT_STEP_DRAW_HEADER
    bne Game_State_Play__charselect_check_draw_name
    jmp Game_State_Play__charselect_draw_header
Game_State_Play__charselect_check_draw_name:
.a8
    cmp #CHARSELECT_STEP_DRAW_NAME
    bne Game_State_Play__charselect_check_draw_instr
    jmp Game_State_Play__charselect_draw_name
Game_State_Play__charselect_check_draw_instr:
.a8
    cmp #CHARSELECT_STEP_DRAW_INSTR
    bne Game_State_Play__charselect_check_clear_header
    jmp Game_State_Play__charselect_draw_instr
Game_State_Play__charselect_check_clear_header:
.a8
    cmp #CHARSELECT_STEP_CLEAR_HEADER
    bne Game_State_Play__charselect_check_clear_name
    jmp Game_State_Play__charselect_clear_header
Game_State_Play__charselect_check_clear_name:
.a8
    cmp #CHARSELECT_STEP_CLEAR_NAME
    bne Game_State_Play__charselect_check_clear_instr
    jmp Game_State_Play__charselect_clear_name
Game_State_Play__charselect_check_clear_instr:
.a8
    cmp #CHARSELECT_STEP_CLEAR_INSTR
    bne Game_State_Play__charselect_check_done
    jmp Game_State_Play__charselect_clear_instr
Game_State_Play__charselect_check_done:
    ; Step >= CHARSELECT_STEP_CLEAR_INSTR+1 -- all three rows are clean,
    ; finish the transition into PLAYING.
    jmp Game_State_Play__charselect_enter_playing

; --- Draw/clear steps below all funnel through Game_State_CharSelect_
; DrawStepRow (A=row, Y=string offset, CharSelect_NextStep set first) --
; a jsr'd shared epilogue instead of 6 near-identical inline copies, same
; reasoning as core/game_state.pasm's own Stage_ApplyWinClamp. Clear steps
; reuse Text_Str_TitleBlank -- blank is blank regardless of which screen
; wrote the row. ---
Game_State_Play__charselect_draw_header:
    ; notjustfreespecial.txt G5 slice: DRAW_HEADER runs exactly once per
    ; fresh charselect entry (CharSelect_Step always resets here -- see
    ; Game_State_Play__charselect_enter_playing) -- flag the currently-
    ; loaded player's real waiting portrait (if any) to stream, picked up
    ; by CharSelect_PortraitUpdate (core/jump.pasm) on ITS next call (a
    ; cheap flag set, not a direct stream -- see that routine's header for
    ; why the actual Msu1_LoadFrame call is deliberately deferred a frame).
    sep #$20
.a8
    lda #1
    sta.l CharSelect_PortraitPending
    lda #CHARSELECT_STEP_DRAW_NAME
    sta.l CharSelect_NextStep
    lda #CHARSELECT_ROW_HEADER
    rep #$31
.a16
.i16
    ldx #0
    ldy #(Text_Str_CharSelectHeader - Text_StringPool)
    jmp Game_State_CharSelect_DrawStepRow

Game_State_Play__charselect_draw_name:
    jsr Game_State_CharSelect_DrawName
    sep #$20
.a8
    lda #CHARSELECT_STEP_DRAW_INSTR
    sta.l CharSelect_Step
    jmp Game_State_Play__charselect_done

Game_State_Play__charselect_draw_instr:
    sep #$20
.a8
    lda #CHARSELECT_STEP_WAIT
    sta.l CharSelect_NextStep
    lda #CHARSELECT_ROW_INSTR
    rep #$31
.a16
.i16
    ldx #0
    ldy #(Text_Str_CharSelectInstr - Text_StringPool)
    jmp Game_State_CharSelect_DrawStepRow

; --- WAIT: poll Left/Right (edge-triggered, reuses Anim_LoadCharacter --
; the same live-reselect call the Select button already makes) and Start
; (edge-triggered, advances to the clear/teardown steps). At most one of
; these fires per frame, and the Left/Right case draws at most once (the
; name-row redraw), so this never risks a second same-frame DrawString. ---
Game_State_Play__charselect_wait:
    rep #$31
.a16
.i16
    lda.l Input_trigger+1
    and #$0002                     ; Left -- bit1, same layout Character_
                                     ; PlayFrame's own dpad check uses
    beq Game_State_Play__charselect_wait_check_right
    sep #$20
.a8
    lda.l CharSelect_Index
    bne Game_State_Play__charselect_left_dec
    lda.l CharSelect_RosterCount
    dec a
    bra Game_State_Play__charselect_left_set
Game_State_Play__charselect_left_dec:
    dec a
Game_State_Play__charselect_left_set:
    sta.l CharSelect_Index
    jsr Game_State_CharSelect_ReloadPlayer
    sep #$20
.a8
    jmp Game_State_Play__charselect_wait_redraw
Game_State_Play__charselect_wait_check_right:
    rep #$31
.a16
.i16
    lda.l Input_trigger+1
    and #$0001                     ; Right -- bit0
    beq Game_State_Play__charselect_wait_check_start
    sep #$20
.a8
    lda.l CharSelect_Index
    inc a
    cmp.l CharSelect_RosterCount
    bcc Game_State_Play__charselect_right_set
    lda #0
Game_State_Play__charselect_right_set:
    sta.l CharSelect_Index
    jsr Game_State_CharSelect_ReloadPlayer
    sep #$20
.a8
Game_State_Play__charselect_wait_redraw:
    jsr Game_State_CharSelect_DrawName
    jmp Game_State_Play__charselect_done
Game_State_Play__charselect_wait_check_start:
    rep #$31
.a16
.i16
    lda.l Input_trigger+1
    and #$0010                     ; Start -- same high-byte layout as
                                     ; the title screen's own check
    bne Game_State_Play__charselect_wait_start_pressed
    jmp Game_State_Play__charselect_done
Game_State_Play__charselect_wait_start_pressed:
    sep #$20
.a8
    lda #CHARSELECT_STEP_CLEAR_HEADER
    sta.l CharSelect_Step
    jmp Game_State_Play__charselect_done

Game_State_Play__charselect_clear_header:
    sep #$20
.a8
    lda #CHARSELECT_STEP_CLEAR_NAME
    sta.l CharSelect_NextStep
    lda #CHARSELECT_ROW_HEADER
    rep #$31
.a16
.i16
    ldx #0
    ldy #(Text_Str_TitleBlank - Text_StringPool)
    jmp Game_State_CharSelect_DrawStepRow

Game_State_Play__charselect_clear_name:
    sep #$20
.a8
    lda #CHARSELECT_STEP_CLEAR_INSTR
    sta.l CharSelect_NextStep
    lda #CHARSELECT_ROW_NAME
    rep #$31
.a16
.i16
    ldx #0
    ldy #(Text_Str_TitleBlank - Text_StringPool)
    jmp Game_State_CharSelect_DrawStepRow

Game_State_Play__charselect_clear_instr:
    sep #$20
.a8
    lda #7                          ; any value >= CHARSELECT_STEP_CLEAR_
                                     ; INSTR+1 works; falls through to
                                     ; Game_State_Play__charselect_enter_
                                     ; playing the very next frame
    sta.l CharSelect_NextStep
    lda #CHARSELECT_ROW_INSTR
    rep #$31
.a16
.i16
    ldx #0
    ldy #(Text_Str_TitleBlank - Text_StringPool)
    jmp Game_State_CharSelect_DrawStepRow

Game_State_Play__charselect_enter_playing:
    sep #$20
.a8
    lda #CHARSELECT_STEP_DRAW_HEADER
    sta.l CharSelect_Step       ; reset for the next time CHARSELECT is entered
    ; Phase G10 (plan_game.md 10): CHARSELECT is the one real choke point
    ; every path into gameplay shares (only ever entered from TITLE -- see
    ; this file's own header) -- the right place for the single canonical
    ; "start a genuinely fresh game" reset (Game_Score/Game_StageIndex/
    ; spawn+entity/player HP-position, via Stage_Load + Game_State_
    ; RespawnPlayer), not just core/game_state.pasm's own pre-G10 direct
    ; `Game_State=PLAYING` write. See Game_State_NewGameReset's own header
    ; (core/game_state.pasm) for the full reasoning -- it sets Game_State
    ; itself, so nothing further is needed here.
    jsl Game_State_NewGameReset
    jmp Game_State_Play__charselect_done

; ----------------------------------------------------------------------
; Game_State_CharSelect_DrawStepRow -- shared epilogue for every draw/clear
; step above: draw the row (A/X/Y already loaded exactly per Core_Text_
; DrawString's own convention), advance CharSelect_Step to CharSelect_
; NextStep (set by the caller before the jmp here), then finish. Reached
; via jmp (not jsr -- callers have no return-address use for it).
; Entry: .a16/.i16 in (Core_Text_DrawString's). Exit: Game_State_Play__
; charselect_done (rtl).
; ----------------------------------------------------------------------
Game_State_CharSelect_DrawStepRow:
    jsl Core_Text_DrawString_Long
    sep #$20
.a8
    lda.l CharSelect_NextStep
    sta.l CharSelect_Step
    jmp Game_State_Play__charselect_done

; ----------------------------------------------------------------------
; Game_State_CharSelect_ReloadPlayer -- calls Anim_LoadCharacter (via the
; bank-0 trampoline) with Direct Page correctly pointed at the PLAYER's own
; CharacterEntity window first. Anim_LoadCharacter writes DP-relative
; CHAR_* fields (CHAR_IDLE_FCOUNT, CHAR_PALETTE_BASE_LO/HI, etc. --
; core/oop.pasm's per-instance-window convention, same one CharacterEntity_
; Play's whole class body relies on) -- it has NO caller-DP convention of
; its own (unlike its width convention, which its header does document)
; because its only prior caller, Anim_Play, always runs already inside the
; right instance's DP window via Core_Oop_Play's own `lda.l OopDp,x / phd /
; tcd` dispatch (core/oop.pasm). This game-state code runs OUTSIDE any
; per-entity OOP dispatch, so without this, Anim_LoadCharacter silently
; writes into whatever entity's window Core_Oop_Play last left DP pointed
; at (found the hard way: CharSelect_Index/Loaded advanced correctly, but
; the player's own CGRAM palette never changed -- a real Mesen2 CGRAM
; readback caught it, not a screenshot). The player is always object slot
; 0 (CLAUDE.md's own documented shortcut), so this is just `lda.l OopDp`
; with no ,x offset needed. `phd`/`pld` isolate the switch exactly like
; Core_Oop_Play's own dispatch does. Entry/exit convention: .a8 in, .a8 out
; (matches both call sites in the WAIT step above).
; ----------------------------------------------------------------------
Game_State_CharSelect_ReloadPlayer:
    rep #$31
.a16
.i16
    lda.l OopDp
    phd
    tcd
    jsl Anim_LoadCharacter_Long
    pld
    ; notjustfreespecial.txt G5 slice: a live reselect can change whether
    ; (and which) real waiting-portrait data applies -- flag it to restream
    ; so Left/Right eventually reflects the NEWLY loaded character, not the
    ; previous one's stale VRAM tile. NOT streamed directly here (same
    ; frame as Anim_LoadCharacter's own palette DMA above) -- see
    ; CharSelect_PortraitUpdate's (core/jump.pasm) header for why that's a
    ; real DMA-queue-overrun regression, not just style. CharSelect_
    ; PortraitUpdate (called every charselect frame regardless) picks up
    ; the FCOUNT==0/!=0 OAM-visibility change on its own immediately;
    ; only the DMA stream itself needs the deferred flag.
    sep #$20
.a8
    lda #1
    sta.l CharSelect_PortraitPending
    rts

; ----------------------------------------------------------------------
; Game_State_CharSelect_DrawName -- draws the current CharSelect_Index's
; name at CHARSELECT_ROW_NAME via CharSelect_NamePtrs (main.pasm, hand-
; synced to build_rom.py's ROSTER_PREFIXES order). Shared (jsr'd, returns)
; by the initial draw step and the Left/Right redraw in the WAIT step --
; both callers finish (via Game_State_Play__charselect_done) themselves
; after it returns. Entry/exit convention: .a8 in, .a8 out.
; ----------------------------------------------------------------------
Game_State_CharSelect_DrawName:
    sep #$20
.a8
    lda.l CharSelect_Index
    rep #$31
.a16
.i16
    and #$00FF
    asl a                          ; index -> word offset into CharSelect_NamePtrs
    tax
    lda.l CharSelect_NamePtrs,x
    tay
    sep #$20
.a8
    lda #CHARSELECT_ROW_NAME
    rep #$31
.a16
.i16
    ldx #0
    jsl Core_Text_DrawString_Long
    sep #$20
.a8
    rts

Game_State_Play__charselect_done:
    rtl
