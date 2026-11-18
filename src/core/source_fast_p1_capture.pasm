; Existing P1 capture only: owner LUT and bulk immutable copies.
SourceCaptureFast_Enter:
.a16
.i16
    php
    rep #$30
    pha
    phx
    phy
    phb
    cld
lda.l Game_CampaignId
    and #255
    cmp #3
beq SourceCaptureFast_Campaign
    brl SourceCaptureFast_Fallback
SourceCaptureFast_Campaign:
.a16
.i16
lda.l Game_State
    cmp #0
beq SourceCaptureFast_Play
    brl SourceCaptureFast_Fallback
SourceCaptureFast_Play:
.a16
.i16
lda.l $7E175E
    cmp #2
beq SourceCaptureFast_Owner
    brl SourceCaptureFast_Fallback
SourceCaptureFast_Owner:
.a16
.i16
lda.l $7E1760
    cmp #1
beq SourceCaptureFast_Active
    brl SourceCaptureFast_Fallback
SourceCaptureFast_Active:
.a16
.i16
lda.l $7E46DC
    cmp #1
beq SourceCaptureFast_Persistent
    brl SourceCaptureFast_Fallback
SourceCaptureFast_Persistent:
.a16
.i16
lda.l $7E46DE
    cmp #0
beq SourceCaptureFast_Foreground
    brl SourceCaptureFast_Fallback
SourceCaptureFast_Foreground:
.a16
.i16
lda.l SourceVisual_CompletedMagic
    cmp #$C04D
beq SourceCaptureFast_Magic
    brl SourceCaptureFast_Fallback
SourceCaptureFast_Magic:
.a16
.i16
tdc
    cmp #$0A00
beq SourceCaptureFast_Player
    brl SourceCaptureFast_Fallback
SourceCaptureFast_Player:
.a16
.i16
lda.l SourceVisual_PieceCount
    cmp #66
bcc SourceCaptureFast_Count
    brl SourceCaptureFast_Fallback
SourceCaptureFast_Count:
.a16
.i16
lda #0
    sta.l SourceVisual_CompletedValid
    sep #$20
.a8
    lda #$39
    pha
    plb
    rep #$30
.a16
.i16
ldx #0
SourceCaptureFast_BlocksLoop:
.a16
.i16
lda.l SourceVisual_BlockCache+4,x
    and #255
    tay
    sep #$20
.a8
    lda.w SourceCaptureFast_Owners & $FFFF,y
    sta.l SourceVisual_BlockCache+4,x
    rep #$30
.a16
.i16
lda.l SourceVisual_BlockCache+12,x
    and #255
    tay
    sep #$20
.a8
    lda.w SourceCaptureFast_Owners & $FFFF,y
    sta.l SourceVisual_BlockCache+12,x
    rep #$30
.a16
.i16
lda.l SourceVisual_BlockCache+20,x
    and #255
    tay
    sep #$20
.a8
    lda.w SourceCaptureFast_Owners & $FFFF,y
    sta.l SourceVisual_BlockCache+20,x
    rep #$30
.a16
.i16
lda.l SourceVisual_BlockCache+28,x
    and #255
    tay
    sep #$20
.a8
    lda.w SourceCaptureFast_Owners & $FFFF,y
    sta.l SourceVisual_BlockCache+28,x
    rep #$30
.a16
.i16
txa
    clc
    adc #32
    tax
    cpx #512
    bcc SourceCaptureFast_BlocksLoop
sep #$20
.a8
    lda.l SourceVisual_PaletteCache+60
    sta.l SourceVisual_CompletedOwners
    rep #$30
.a16
.i16
ldx #0
SourceCaptureFast_PalettesLoop:
.a16
.i16
lda.l SourceVisual_PaletteCache+4,x
    and #255
    tay
    sep #$20
.a8
    lda.w SourceCaptureFast_Owners & $FFFF,y
    sta.l SourceVisual_PaletteCache+4,x
    rep #$30
.a16
.i16
lda.l SourceVisual_PaletteCache+12,x
    and #255
    tay
    sep #$20
.a8
    lda.w SourceCaptureFast_Owners & $FFFF,y
    sta.l SourceVisual_PaletteCache+12,x
    rep #$30
.a16
.i16
lda.l SourceVisual_PaletteCache+20,x
    and #255
    tay
    sep #$20
.a8
    lda.w SourceCaptureFast_Owners & $FFFF,y
    sta.l SourceVisual_PaletteCache+20,x
    rep #$30
.a16
.i16
lda.l SourceVisual_PaletteCache+28,x
    and #255
    tay
    sep #$20
.a8
    lda.w SourceCaptureFast_Owners & $FFFF,y
    sta.l SourceVisual_PaletteCache+28,x
    rep #$30
.a16
.i16
txa
    clc
    adc #32
    tax
    cpx #64
    bcc SourceCaptureFast_PalettesLoop
sep #$20
.a8
    lda.l SourceVisual_PaletteCache+60
    sta.l SourceVisual_CompletedNewOwners
    rep #$30
.a16
.i16
ldx #(SourceVisual_EntryScratch & $FFFF)
    ldy #(SourceVisual_CompletedEntry & $FFFF)
    lda #23
    mvn $7E,$7E
ldx #(SourceVisual_State & $FFFF)
    ldy #(SourceVisual_CompletedLease & $FFFF)
    lda #31
    mvn $7E,$7E
lda.l SourceVisual_PieceCount
    asl a
    asl a
    asl a
    asl a
    sta.l SourceVisual_CompletedMainBytes
    beq SourceCaptureFast_NoPieces
    dec a
    ldx #(SourceVisual_PieceTable & $FFFF)
    ldy #(SourceVisual_CompletedPieces & $FFFF)
    mvn $7E,$7E
SourceCaptureFast_NoPieces:
.a16
.i16
ldx #(SourceVisual_ActorPieceMap & $FFFF)
    ldy #(SourceVisual_CompletedMap & $FFFF)
    lda #64
    mvn $7E,$7E
lda.l Game_StageIndex
    sta.l SourceVisual_CompletedStage
    lda CHAR_ROSTER_INDEX
    and #255
    sta.l SourceVisual_CompletedRoster
    lda #1
    sta.l SourceVisual_CompletedAwait
    sep #$20
.a8
    sta.l SourceVisual_CompletedLease+28
    rep #$30
.a16
.i16
    lda.l SourceVisual_CompletedCaptures
    inc a
    sta.l SourceVisual_CompletedCaptures
    lda #1
    sta.l SourceVisual_CompletedValid
    plb
    ply
    plx
    pla
    plp
    rep #$31
.a16
.i16
    ldx #65
    lda #1
    jml SourceCaptureFast_Return
SourceCaptureFast_Fallback:
.a16
.i16
    plb
    ply
    plx
    pla
    plp
    rep #$30
.a16
.i16
    lda #0
    sta.l SourceVisual_CompletedValid
    ldx #0
    jml SourceVisual_CompletedCapture__blocks
SourceCaptureFast_CodeEnd:
.assert * <= $398C00, "P1 capture code reaches lookup"
.org $8C00
SourceCaptureFast_Owners:
.db $00,$41,$02,$43,$04,$45,$06,$47,$08,$49,$0A,$4B,$0C,$4D,$0E,$4F
.db $10,$51,$12,$53,$14,$55,$16,$57,$18,$59,$1A,$5B,$1C,$5D,$1E,$5F
.db $20,$61,$22,$63,$24,$65,$26,$67,$28,$69,$2A,$6B,$2C,$6D,$2E,$6F
.db $30,$71,$32,$73,$34,$75,$36,$77,$38,$79,$3A,$7B,$3C,$7D,$3E,$7F
.db $80,$C1,$82,$C3,$84,$C5,$86,$C7,$88,$C9,$8A,$CB,$8C,$CD,$8E,$CF
.db $90,$D1,$92,$D3,$94,$D5,$96,$D7,$98,$D9,$9A,$DB,$9C,$DD,$9E,$DF
.db $A0,$E1,$A2,$E3,$A4,$E5,$A6,$E7,$A8,$E9,$AA,$EB,$AC,$ED,$AE,$EF
.db $B0,$F1,$B2,$F3,$B4,$F5,$B6,$F7,$B8,$F9,$BA,$FB,$BC,$FD,$BE,$FF
.db $00,$41,$02,$43,$04,$45,$06,$47,$08,$49,$0A,$4B,$0C,$4D,$0E,$4F
.db $10,$51,$12,$53,$14,$55,$16,$57,$18,$59,$1A,$5B,$1C,$5D,$1E,$5F
.db $20,$61,$22,$63,$24,$65,$26,$67,$28,$69,$2A,$6B,$2C,$6D,$2E,$6F
.db $30,$71,$32,$73,$34,$75,$36,$77,$38,$79,$3A,$7B,$3C,$7D,$3E,$7F
.db $80,$C1,$82,$C3,$84,$C5,$86,$C7,$88,$C9,$8A,$CB,$8C,$CD,$8E,$CF
.db $90,$D1,$92,$D3,$94,$D5,$96,$D7,$98,$D9,$9A,$DB,$9C,$DD,$9E,$DF
.db $A0,$E1,$A2,$E3,$A4,$E5,$A6,$E7,$A8,$E9,$AA,$EB,$AC,$ED,$AE,$EF
.db $B0,$F1,$B2,$F3,$B4,$F5,$B6,$F7,$B8,$F9,$BA,$FB,$BC,$FD,$BE,$FF
SourceCaptureFast_End:
