; ============================================================================
; Generic source SCROLL_DOWN support for vertical BOR stages.
; ============================================================================

Entity1_ThrowZPos_H2 = $7E0A00 + CHAR_ZP_LEN + CHAR_THROW_ZPOS
Entity1_ThrowZVel_H2 = $7E0A00 + CHAR_ZP_LEN + CHAR_THROW_ZVEL
Entity1_Selected_H2  = $7E0A00 + CHAR_ZP_LEN + CHAR_SELECTED
Entity2_ThrowZPos_H2 = $7E0A00 + CHAR_ZP_LEN*2 + CHAR_THROW_ZPOS
Entity2_ThrowZVel_H2 = $7E0A00 + CHAR_ZP_LEN*2 + CHAR_THROW_ZVEL
Entity2_Selected_H2  = $7E0A00 + CHAR_ZP_LEN*2 + CHAR_SELECTED
Entity3_ThrowZPos_H2 = $7E0A00 + CHAR_ZP_LEN*3 + CHAR_THROW_ZPOS
Entity3_ThrowZVel_H2 = $7E0A00 + CHAR_ZP_LEN*3 + CHAR_THROW_ZVEL
Entity3_Selected_H2  = $7E0A00 + CHAR_ZP_LEN*3 + CHAR_SELECTED

.include "../../tools/audio/stage_scroll_config.pasm"

Stage_SetScrollDirection:
    php
    rep #$31
.a16
.i16
    lda.l Game_StageIndex
    and #$00FF
    tax
    sep #$20
.a8
    lda.l Stage_ScrollDirectionMap,x
    sta.l Stage_ScrollDirection
    lda.l Stage_MirrorMap,x
    sta.l Stage_Mirror
    cmp #STAGE_SCROLL_DOWN
    beq Stage_SetScrollDirection__down
    bra Stage_SetScrollDirection__done
Stage_SetScrollDirection__down:
    sep #$20
.a8
    lda.l Stage_ScrollMaxTriggerMap,x
    sta Screen_MaxY
    lda #0
    sta Screen_MaxY+1
Stage_SetScrollDirection__done:
    plp
    rtl

Stage_StreamInitialColumn:
    rep #$31
.a16
.i16
    lda #0
    sta.l StreamScroll_StagedLo
    lda.l Stage_ScrollDirection
    and #$00FF
    cmp #STAGE_SCROLL_LEFT
    bne Stage_StreamInitialColumn__done
    lda.l BgRecordStaging+2
    sec
    sbc #STREAM_STAGE_VIEWPORT_COLS
    sta.l StreamScroll_StagedLo
Stage_StreamInitialColumn__done:
    rtl

Stage_SetEntryCamera:
    rep #$31
.a16
.i16
    lda.l Stage_ScrollDirection
    and #$00FF
    cmp #STAGE_SCROLL_LEFT
    bne Stage_SetEntryCamera__left_edge
    lda.l Stage_TrueMaxX
    bra Stage_SetEntryCamera__store
Stage_SetEntryCamera__left_edge:
    rep #$31
.a16
.i16
    lda #0
Stage_SetEntryCamera__store:
    sta.l Screen_PosX
    sep #$20
.a8
    stz.w Screen_PosXFrac_Lo
    rep #$31
.a16
.i16
    rtl

Stage_RespawnP1Position:
    rep #$31
.a16
.i16
    lda.l Stage_ScrollDirection
    and #$00FF
    cmp #STAGE_SCROLL_LEFT
    bne Stage_RespawnP1Position__right
    lda.l Screen_PosX
    clc
    adc #240
    bra Stage_RespawnP1Position__store
Stage_RespawnP1Position__right:
    rep #$31
.a16
.i16
    lda.l Screen_PosX
    clc
    adc #PLAYER_RESPAWN_X_MARGIN
Stage_RespawnP1Position__store:
    sta.l PlayerEntity_PosX
    rtl

Stage_RespawnP2Position:
    rep #$31
.a16
.i16
    lda.l Stage_ScrollDirection
    and #$00FF
    cmp #STAGE_SCROLL_LEFT
    bne Stage_RespawnP2Position__right
    lda.l Screen_PosX
    clc
    adc #216
    bra Stage_RespawnP2Position__store
Stage_RespawnP2Position__right:
    rep #$31
.a16
.i16
    lda.l Screen_PosX
    clc
    adc #20
Stage_RespawnP2Position__store:
    sta CHAR_POS_X
    rtl

Stage_ApplyWinClamp_Banked:
    php
    rep #$31
.a16
.i16
    lda.l Stage_ScrollDirection
    and #$00FF
    cmp #STAGE_SCROLL_DOWN
    beq Stage_ApplyWinClamp_Banked__vertical
    cmp #STAGE_SCROLL_LEFT
    beq Stage_ApplyWinClamp_Banked__left
    lda Screen_MaxX
    sta.l Stage_TrueMaxX
    lda.l Spawn_LastTriggerX
    beq Stage_ApplyWinClamp_Banked__no_hold
    cmp.l Stage_TrueMaxX
    bcs Stage_ApplyWinClamp_Banked__no_hold
    sta Screen_MaxX
Stage_ApplyWinClamp_Banked__no_hold:
    lda Screen_MaxX
    sta.l Spawn_PreClearHoldX
    sep #$20
.a8
    lda #0
    sta.l Stage_Cleared
    plp
    rtl
Stage_ApplyWinClamp_Banked__left:
    lda Screen_MaxX
    sta.l Stage_TrueMaxX
    lda.l Spawn_LastTriggerX
    beq Stage_ApplyWinClamp_Banked__left_no_hold
    cmp.l Stage_TrueMaxX
    bcs Stage_ApplyWinClamp_Banked__left_no_hold
    lda.l Stage_TrueMaxX
    sec
    sbc.l Spawn_LastTriggerX
    sta Screen_MinX
    bra Stage_ApplyWinClamp_Banked__left_done
Stage_ApplyWinClamp_Banked__left_no_hold:
    rep #$31
.a16
.i16
    lda #0
    sta Screen_MinX
Stage_ApplyWinClamp_Banked__left_done:
    sep #$20
.a8
    lda #0
    sta.l Stage_Cleared
    plp
    rtl
Stage_ApplyWinClamp_Banked__vertical:
    bra Stage_ApplyWinClamp_Banked__no_hold

; Source update_scroller() adaptation for SCROLL_DOWN. The source advances
; advancey by .5 every GAME_SPEED/100 tick. At 60Hz and the established 0.8
; scene scale this is represented as 171/256 SNES pixels per frame. Screen_
; PosY is the scaled levelpos consumed by Spawn_Play; the NMI shadow receives
; the source background offset (advancey + .5) / 2 over the 224px period.
Stage_ScrollPlay:
    php
    sep #$20
.a8
    lda.l Stage_ScrollDirection
    cmp #STAGE_SCROLL_DOWN
    beq Stage_ScrollPlay__down
    bra Stage_ScrollPlay__done
Stage_ScrollPlay__down:
    rep #$31
.a16
.i16
    lda.w Screen_PosY_Lo
    cmp Screen_MaxY
    bcs Stage_ScrollPlay__write_bg_y
    sep #$20
.a8
    lda.l Screen_PosYFrac_Lo
    clc
    adc #STAGE_DOWN_STEP_FRAC
    sta.l Screen_PosYFrac_Lo
    bcc Stage_ScrollPlay__no_carry
    rep #$31
.a16
.i16
    inc.w Screen_PosY_Lo
Stage_ScrollPlay__no_carry:
    rep #$31
.a16
.i16
Stage_ScrollPlay__write_bg_y:
    rep #$31
.a16
.i16
    lda.w Screen_PosY_Lo
    lsr a
    cmp #224
    bcc Stage_ScrollPlay__store_bg_y
    sec
    sbc #224
Stage_ScrollPlay__store_bg_y:
    sta.l Nmi_Bg1ScrollY
Stage_ScrollPlay__done:
    plp
    rtl

; BOR.C smartspawn() adaptation for SCROLL_DOWN.  The source gives an
; in-range enemy an altitude of 240+randf(40); the existing SNES thrown
; state is the generic per-entity airborne/drop path, so the bounded
; representation uses the lower authored altitude and source gravity.
Spawn_ApplyVerticalDrop:
    php
    ; The slot-specific entry stubs below set Spawn_ScratchSlotOfs after all
    ; slot-selection state is known; this routine then applies one shared
    ; source rule to the selected actor.
    sep #$20
.a8
    lda.l Stage_ScrollDirection
    cmp #STAGE_SCROLL_DOWN
    beq Spawn_ApplyVerticalDrop__direction_ok
    brl Spawn_ApplyVerticalDrop__done
Spawn_ApplyVerticalDrop__direction_ok:
    rep #$31
.a16
.i16
    lda.l Spawn_ScratchSlotOfs
    cmp #CHAR_ZP_LEN
    beq Spawn_ApplyVerticalDrop__slot1
    cmp #CHAR_ZP_LEN*2
    beq Spawn_ApplyVerticalDrop__slot2
    cmp #CHAR_ZP_LEN*3
    beq Spawn_ApplyVerticalDrop__slot3
    brl Spawn_ApplyVerticalDrop__done
Spawn_ApplyVerticalDrop__slot1:
.a16
.i16
    lda #$7800
    sta.l Entity1_ThrowZPos_H2
    lda #0
    sta.l Entity1_ThrowZVel_H2
    sep #$20
.a8
    lda #CHAR_SELECTED_THROWN
    sta.l Entity1_Selected_H2
    bra Spawn_ApplyVerticalDrop__done
Spawn_ApplyVerticalDrop__slot2:
.a16
.i16
    lda #$7800
    sta.l Entity2_ThrowZPos_H2
    lda #0
    sta.l Entity2_ThrowZVel_H2
    sep #$20
.a8
    lda #CHAR_SELECTED_THROWN
    sta.l Entity2_Selected_H2
    bra Spawn_ApplyVerticalDrop__done
Spawn_ApplyVerticalDrop__slot3:
.a16
.i16
    lda #$7800
    sta.l Entity3_ThrowZPos_H2
    lda #0
    sta.l Entity3_ThrowZVel_H2
    sep #$20
.a8
    lda #CHAR_SELECTED_THROWN
    sta.l Entity3_Selected_H2
    bra Spawn_ApplyVerticalDrop__done
Spawn_ApplyVerticalDrop1:
    sep #$20
.a8
    lda #CHAR_ZP_LEN
    sta.l Spawn_ScratchSlotOfs
    jsl Spawn_ApplyVerticalDrop
    rtl
Spawn_ApplyVerticalDrop2:
    sep #$20
.a8
    lda #CHAR_ZP_LEN*2
    sta.l Spawn_ScratchSlotOfs
    jsl Spawn_ApplyVerticalDrop
    rtl
Spawn_ApplyVerticalDrop3:
    sep #$20
.a8
    lda #CHAR_ZP_LEN*3
    sta.l Spawn_ScratchSlotOfs
    jsl Spawn_ApplyVerticalDrop
    rtl
Spawn_ApplyVerticalDrop__done:
    plp
    rtl
