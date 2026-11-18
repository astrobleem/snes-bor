; Exact immutable metadata transport for Kula A1-000, entry 781.
; Normal MSU path remains the fallback on every identity or scope mismatch.
SourceAttackRom_Eligible:
.a16
.i16
    lda.l Game_CampaignId
    and #$00FF
    cmp #3
    bne SourceAttackRom_Eligible__no
    lda.l Game_StageIndex
    bne SourceAttackRom_Eligible__no
    lda.l SourceVisual_ActorSlot
    cmp #2
    bcs SourceAttackRom_Eligible__no
    lda.l SourceVisual_EntryIndexSaved
    cmp #781
    bne SourceAttackRom_Eligible__no
    lda.l SourceVisual_Record
    tax
    lda.l SourceVisual_State,x
    cmp #781
    bne SourceAttackRom_Eligible__no
    ldx #0
SourceAttackRom_Eligible__header:
    lda.l SourceVisual_EntryScratch,x
    cmp.l SourceAttackRom_Header,x
    bne SourceAttackRom_Eligible__no
    inx
    inx
    cpx #24
    bcc SourceAttackRom_Eligible__header
    sec
    rts
SourceAttackRom_Eligible__no:
    clc
    rts

SourceAttackRom_ReadRow:
    jsr SourceAttackRom_Eligible
    bcc SourceAttackRom_ReadRow__no
    ldx #0
    sep #$20
.a8
SourceAttackRom_ReadRow__copy:
    lda.l SourceAttackRom_Row,x
    sta.l SourceVisual_RowScratch,x
    inx
    cpx #42
    bcc SourceAttackRom_ReadRow__copy
    rep #$31
.a16
.i16
    sec
    rtl
SourceAttackRom_ReadRow__no:
    clc
    rtl

SourceAttackRom_ReadPieces:
    jsr SourceAttackRom_Eligible
    bcc SourceAttackRom_ReadPieces__no
    lda.l SourceVisual_PieceCount
    cmp #10
    bne SourceAttackRom_ReadPieces__no
    ldx #0
    sep #$20
.a8
SourceAttackRom_ReadPieces__copy:
    lda.l SourceAttackRom_Pieces,x
    sta.l SourceVisual_PieceTable,x
    inx
    cpx #160
    bcc SourceAttackRom_ReadPieces__copy
    rep #$31
.a16
.i16
    sec
    rtl
SourceAttackRom_ReadPieces__no:
    ; Byte-for-byte equivalent of the former selected-piece stream offset.
    lda.l SourceVisual_EntryScratch+16
    sta.l SourceVisual_Temp
    asl a
    asl a
    asl a
    asl a
    sta.l SourceVisual_Offset
    lda.l SourceVisual_Temp
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    sta.l SourceVisual_Offset+2
    lda.l SourceVisual_Offset
    clc
    adc #SOURCE_VISUAL_PIECE_OFFSET
    sta.l SourceVisual_Offset
    sep #$20
.a8
    lda.l SourceVisual_Offset+2
    adc #((SOURCE_VISUAL_PIECE_OFFSET >> 16) & $FF)
    sta.l SourceVisual_Offset+2
    lda #((SOURCE_VISUAL_PIECE_OFFSET >> 24) & $FF)
    adc #0
    sta.l SourceVisual_Offset+3
    rep #$31
.a16
.i16
    lda.l SourceVisual_Offset
    clc
    adc #SOURCE_VISUAL_MSU_OFFSET_LO
    sta.l SourceVisual_Offset
    sep #$20
.a8
    lda.l SourceVisual_Offset+2
    adc #SOURCE_VISUAL_MSU_OFFSET_MID
    sta.l SourceVisual_Offset+2
    lda.l SourceVisual_Offset+3
    adc #SOURCE_VISUAL_MSU_OFFSET_HI
    sta.l SourceVisual_Offset+3
    rep #$31
.a16
.i16
    clc
    rtl

SourceAttackRom_Header:
    .db $16,$02,$00,$00,$62,$00,$68,$00,$17,$00,$65,$00,$0A,$00,$01,$00
    .db $0D,$2B,$00,$00,$67,$04,$00,$00
SourceAttackRom_Row:
    .db $EE,$24,$2E,$35,$6A,$F3,$7C,$3D,$91,$68,$45,$84,$46,$A2,$2D,$E0
    .db $FD,$29,$89,$A5,$B8,$60,$0B,$BE,$47,$F9,$DC,$98,$D9,$67,$C0,$0B
    .db $00,$10,$22,$FE,$B2,$00,$00,$10,$00,$00
SourceAttackRom_Pieces:
    .db $E9,$FF,$AB,$FF,$08,$00,$AB,$FF,$00,$00,$69,$01,$70,$2B,$00,$00
    .db $E9,$FF,$E3,$FF,$08,$00,$E3,$FF,$00,$00,$69,$01,$75,$17,$02,$00
    .db $F1,$FF,$9B,$FF,$00,$00,$9B,$FF,$00,$00,$69,$01,$8D,$11,$04,$00
    .db $F9,$FF,$B3,$FF,$F8,$FF,$B3,$FF,$00,$00,$69,$01,$7C,$3A,$06,$00
    .db $F9,$FF,$C3,$FF,$F8,$FF,$C3,$FF,$00,$00,$69,$01,$91,$35,$08,$00
    .db $F9,$FF,$E3,$FF,$F8,$FF,$E3,$FF,$00,$00,$69,$01,$EF,$31,$0A,$00
    .db $01,$00,$9B,$FF,$F0,$FF,$9B,$FF,$00,$00,$69,$01,$C9,$2C,$0C,$00
    .db $09,$00,$BB,$FF,$E8,$FF,$BB,$FF,$00,$00,$69,$01,$5F,$3D,$0E,$00
    .db $09,$00,$C3,$FF,$E8,$FF,$C3,$FF,$00,$00,$69,$01,$E6,$18,$40,$00
    .db $09,$00,$E3,$FF,$E8,$FF,$E3,$FF,$00,$00,$69,$01,$CB,$00,$42,$00
