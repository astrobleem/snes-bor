; Immutable catalog palette32 row+payload, exactly74 bytes. Only data
; transport changes. Original staging, enqueue and retirement remain intact.
SourceRomPalette_Pair:
.a16
.i16
    lda.l SourceVisual_PaletteGlobalIndex
    cmp #32
    beq SourceRomPalette_CheckOffset
SourceRomPalette_Ordinary:
.a16
.i16
    jsl SourceRomPalette_ReadRow
    jsl SourceRomPalette_ReadPayload
    jml SourceRomPalette_PairResume
SourceRomPalette_CheckOffset:
.a16
.i16
    lda.l SourceVisual_Offset
    cmp #60610
    bne SourceRomPalette_Ordinary
    lda.l SourceVisual_Offset+2
    cmp #499
    bne SourceRomPalette_Ordinary
    rep #$31
    ldx #0
    sep #$20
.a8
SourceRomPalette_CopyRow:
.a8
.i16
    lda.l SourceRomPalette_Row,x
    sta.l SourceVisual_RowScratch,x
    inx
    cpx #42
    bcc SourceRomPalette_CopyRow
    lda #$A8
    sta.l SourceVisual_Error
    rep #$31
.a16
.i16
    lda #33998
    sta.l SourceVisual_Offset+0
    sta.l SourceVisual_DebugSeek+0
    lda #568
    sta.l SourceVisual_Offset+2
    sta.l SourceVisual_DebugSeek+2
    lda #11
    sta.l SourceVisual_DebugQueueStage
    ldx #0
SourceRomPalette_CopyPayload:
.a16
.i16
    txa
    sta.l SourceVisual_DebugIndex
    sep #$20
.a8
    lda.l SourceRomPalette_Payload,x
    sta.l SourceVisual_PaletteTemp,x
    rep #$31
.a16
.i16
    inx
    cpx #32
    bcc SourceRomPalette_CopyPayload
    jsl SourceRomPalette_Stage
    jml SourceRomPalette_PairResume
SourceRomPalette_ReadRow:
.a16
.i16
    .db $F4
    .dw ((SourcePalette_Bridge_SVActor_Enabled+2)&$FFFF)
    jml SourceVisual_ReadRow
SourceRomPalette_ReadPayload:
.a16
.i16
    .db $F4
    .dw ((SourcePalette_Bridge_SVActor_Enabled+2)&$FFFF)
    jml SourceVisual_ReadPalettePayload
SourceRomPalette_Stage:
.a16
.i16
    .db $F4
    .dw ((SourcePalette_Bridge_SVActor_Enabled+2)&$FFFF)
    jml SourceRomPalette_StageResume
SourceRomPalette_Row:
    .db $0F,$B0,$54,$2C,$00,$67,$A3,$60,$D7,$2B,$CF,$0D,$A3,$8D,$C2,$95
    .db $5F,$45,$75,$FA,$E7,$78,$A5,$C3,$8E,$C7,$84,$D0,$3F,$90,$F3,$D1
    .db $20,$00,$42,$D8,$5F,$00,$20,$00,$00,$00
SourceRomPalette_Payload:
    .db $1F,$7C,$D5,$30,$52,$24,$2D,$20,$40,$10,$89,$39,$25,$2D,$F2,$66
    .db $55,$6B,$DA,$7B,$DE,$73,$1A,$2B,$32,$36,$5C,$5B,$D2,$39,$55,$4A
SourceRomPalette_End:
