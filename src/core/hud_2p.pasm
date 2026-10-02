; ============================================================================
; core/hud_2p.pasm -- player-facing fixed-session two-player HUD (G14).
;
; P2 is a source-normal selected player. This module only adds presentation
; for the already-owned Entity1/G13_P2Score/G13_P2Lives state.
; It uses the existing HudStaging/TextStaging buffers and queues at most one
; P2 bar and one P2 text row per gameplay service, just like the established
; P1 HUD path.  Rows 7-9 are free gameplay rows: row 6 remains the boss bar,
; rows 21-27 remain the frontpanel owner.
; ============================================================================

Hud_Play__2p:
    sep #$20
.a8
    lda.l G13_TwoPlayerEnabled
    beq Hud_Play__2p_done
    bcs Hud_Play__2p_bar_only
    jsr Hud_Play__2p_text
Hud_Play__2p_bar_only:
    jsr Hud_Play__2p_bar
Hud_Play__2p_done:
    rtl

Hud_Play__2p_bar:
    sep #$20
.a8
    lda.l G13_TwoPlayerEnabled
    beq Hud_Play__2p_bar_done
    lda.l Entity1_Hp
    cmp.l HudCachedP2Hp
    beq Hud_Play__2p_bar_done
    sta.l HudCachedP2Hp

    rep #$31
.a16
.i16
    ldx #$0000
Hud_Play__2p_bar_clear:
    rep #$31
.a16
.i16
    lda #$0000
    sta.l HudStaging,x
    inx
    inx
    cpx #HUD_STAGING_BYTES
    bcc Hud_Play__2p_bar_clear

    sep #$20
.a8
    lda.l HudCachedP2Hp
    rep #$10
.i16
    ldx #$0000
    jsr Hud_Play__2p_drawbar

    rep #$31
.a16
.i16
    lda #HudStaging
    sta.l DmaRequest_SourceAddrLow
    lda #(BG3_TILEMAP_VRAM_WORD + HUD_ROW_P2_BAR * TEXT_ROW_ENTRIES) * 2
    sta.l DmaRequest_TargetAddr
    lda #HUD_STAGING_BYTES
    sta.l DmaRequest_Length
    sep #$20
.a8
    lda #$7E
    sta.l DmaRequest_SourceBank
    lda #DMA_TYPE_VRAM
    sta.l DmaRequest_TypeFlags
    rep #$31
.a16
.i16
    jsl Core_Dma_Enqueue_Long
Hud_Play__2p_bar_done:
    rts

Hud_Play__2p_drawbar:
    sep #$20
.a8
    sta.l HudBarHp
    inx
    inx
    lda #HUD_TILE_CAP_LEFT
    sta.l HudStaging,x
    inx
    lda #HUD_ENTRY_HIGH
    sta.l HudStaging,x
    inx
    ldy #HUD_BAR_TILES
Hud_Play__2p_drawbar_body:
    sep #$20
.a8
    lda.l HudBarHp
    cmp #8
    bcc Hud_Play__2p_drawbar_partial
    lda #8
    sta.l HudBarFilled
    lda.l HudBarHp
    sec
    sbc #8
    sta.l HudBarHp
    bra Hud_Play__2p_drawbar_have
Hud_Play__2p_drawbar_partial:
    sep #$20
.a8
    sta.l HudBarFilled
    lda #0
    sta.l HudBarHp
Hud_Play__2p_drawbar_have:
    sep #$20
.a8
    lda.l HudBarFilled
    clc
    adc #HUD_TILE_FILL_BASE
    sta.l HudStaging,x
    inx
    lda #HUD_ENTRY_HIGH
    sta.l HudStaging,x
    inx
    dey
    bne Hud_Play__2p_drawbar_body
    lda #HUD_TILE_CAP_RIGHT
    sta.l HudStaging,x
    inx
    lda #HUD_ENTRY_HIGH
    sta.l HudStaging,x
    rts

Hud_Play__2p_text:
    rep #$31
.a16
.i16
    lda.l G13_P2Score32
    cmp.l HudCachedP2Score32
    bne Hud_Play__2p_text_score_changed
    lda.l G13_P2Score32+2
    cmp.l HudCachedP2Score32+2
    beq Hud_Play__2p_text_lives
Hud_Play__2p_text_score_changed:
    lda.l G13_P2Score32
    sta.l HudCachedP2Score32
    sta.l Text_ScoreValue32
    lda.l G13_P2Score32+2
    sta.l HudCachedP2Score32+2
    sta.l Text_ScoreValue32+2
    sep #$20
.a8
    lda #1
    sta.l Text_ScoreMode
    lda #HUD_ROW_P2_SCORE
    rep #$10
.i16
    ldx #HUD_LABEL_COL
    ldy #(Text_Str_HudP2Score - Text_StringPool)
    jsl Core_Text_DrawLabeledNumber_Long
    rts
Hud_Play__2p_text_lives:
    sep #$20
.a8
    lda.l G13_TwoPlayerEnabled
    beq Hud_Play__2p_text_done
    rep #$31
.a16
.i16
    lda.l G13_P2Lives
    cmp.l HudCachedP2Lives
    beq Hud_Play__2p_text_done
    sta.l HudCachedP2Lives
    sta.l Text_LabelValue
    sep #$20
.a8
    lda #HUD_ROW_P2_LIVES
    rep #$10
.i16
    ldx #HUD_LABEL_COL
    ldy #(Text_Str_HudP2Lives - Text_StringPool)
    jsl Core_Text_DrawLabeledNumber_Long
Hud_Play__2p_text_done:
    rts
