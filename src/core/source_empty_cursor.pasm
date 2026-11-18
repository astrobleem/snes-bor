; Conservative lowest-empty scan cursor. Every earlier row was proven
; occupied by the exact original ascending scan. Every State0 writer resets
; the cursor, so the existing lowest-slot and victim choices are unchanged.
SourceEmpty_Cursor = $7EEFD0
SourceEmpty_GetStart:
    php
    rep #$30
.a16
.i16
    lda.l Game_CampaignId
    and #$00FF
    cmp #3
    bne SourceEmpty_GetStart__zero
    lda.l SourceVisual_CompletedMagic
    cmp #$C04D
    bne SourceEmpty_GetStart__zero
    lda.l SourceEmpty_Cursor
    cmp #SOURCE_VISUAL_TILE_BLOCKS+1
    bcc SourceEmpty_GetStart__done
SourceEmpty_GetStart__zero:
.a16
.i16
    lda #0
SourceEmpty_GetStart__done:
.a16
.i16
    plp
    rtl
SourceEmpty_Claimed:
    php
    rep #$30
.a16
.i16
    pha
    lda.l Game_CampaignId
    and #$00FF
    cmp #3
    bne SourceEmpty_Claimed__done
    lda.l SourceVisual_CompletedMagic
    cmp #$C04D
    bne SourceEmpty_Claimed__done
    lda.l SourceEmpty_Cursor
    cmp #SOURCE_VISUAL_TILE_BLOCKS
    beq SourceEmpty_Claimed__done
    lda.l SourceVisual_BlockScan
    cmp #SOURCE_VISUAL_TILE_BLOCKS
    bcs SourceEmpty_Claimed__done
    inc a
    sta.l SourceEmpty_Cursor
SourceEmpty_Claimed__done:
.a16
.i16
    pla
    plp
    rtl
SourceEmpty_Reset:
    php
    rep #$30
.a16
.i16
    pha
    lda #0
    sta.l SourceEmpty_Cursor
SourceEmpty_Reset__done:
.a16
.i16
    pla
    plp
    rtl
