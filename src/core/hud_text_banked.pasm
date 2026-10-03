; Existing dirty-gated HUD text execution, relocated from fixed bank 0.
; Long text entry preserves the established calling convention.
Hud_Play__text_banked:
    rep #$31
.a16
.i16
    lda.l Game_Score32
    cmp.l HudCachedScore32
    bne Hud_Play__text_banked_score_changed
    lda.l Game_Score32+2
    cmp.l HudCachedScore32+2
    beq Hud_Play__text_banked_check_lives
Hud_Play__text_banked_score_changed:
    lda.l Game_Score32
    sta.l HudCachedScore32
    sta.l Text_ScoreValue32
    lda.l Game_Score32+2
    sta.l HudCachedScore32+2
    sta.l Text_ScoreValue32+2
    sep #$20
.a8
    lda #1
    sta.l Text_ScoreMode
    lda #HUD_ROW_SCORE
.i16
    ldx #HUD_LABEL_COL
    ldy #(Text_Str_HudScore - Text_StringPool)
    jsl Core_Text_DrawLabeledNumber_Long
    bra Hud_Play__text_banked_marked

Hud_Play__text_banked_check_lives:
    rep #$31
.a16
.i16
    lda.l Game_Lives
    cmp.l HudCachedLives
    beq Hud_Play__text_banked_check_stage
    sta.l HudCachedLives
    sta.l Text_LabelValue
    sep #$20
.a8
    lda #HUD_ROW_LIVES
.i16
    ldx #HUD_LABEL_COL
    ldy #(Text_Str_HudLives - Text_StringPool)
    jsl Core_Text_DrawLabeledNumber_Long
    bra Hud_Play__text_banked_marked

Hud_Play__text_banked_check_stage:
    rep #$31
.a16
.i16
    lda.l Game_StageIndex
    inc a                    ; 1-based for display
    cmp.l HudCachedStageIndex
    beq Hud_Play__text_banked_done
    sta.l HudCachedStageIndex
    sta.l Text_LabelValue
    sep #$20
.a8
    lda #HUD_ROW_STAGE
    rep #$10
.i16
    ldx #HUD_LABEL_COL
    ldy #(Text_Str_HudStage - Text_StringPool)
    jsl Core_Text_DrawLabeledNumber_Long
Hud_Play__text_banked_marked:
    sec
    rtl
Hud_Play__text_banked_done:
    clc
    rtl
