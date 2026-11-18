; Immutable catalog transport only. All original physical critical checks,
; loader/palette admission, pinning and publication stay authoritative.
; Copy only the exact canonical idle0 row and its ten pieces to ordinary raw
; metadata; preserve the other actor and tail; commit Valid last. Then enter
; the ORIGINAL ReadIdlePieces bridge, which still fills the normal piece table.
SourceIdleRom_WarmAndRead:
.a16
.i16
    php
    rep #$30
    cld
    pha
    phx
    phy
    phb
    lda.l SourceVisual_ServiceOnly
    cmp #0
    beq SourceIdleRom_G1
    brl SourceIdleRom_Restore
SourceIdleRom_G1:
.a16
.i16
    lda.l SourceVisual_Key
    cmp #22
    beq SourceIdleRom_G2
    brl SourceIdleRom_Restore
SourceIdleRom_G2:
.a16
.i16
    lda.l SourceVisual_Key+2
    cmp #0
    beq SourceIdleRom_G3
    brl SourceIdleRom_Restore
SourceIdleRom_G3:
.a16
.i16
    lda.l SourceVisual_EntryIndexSaved
    cmp #923
    beq SourceIdleRom_G4
    brl SourceIdleRom_Restore
SourceIdleRom_G4:
.a16
.i16
    jsl SourceIdle_CanFinish
    bcs SourceIdleRom_Eligible
    brl SourceIdleRom_Restore
SourceIdleRom_Eligible:
.a16
.i16
    lda.l SourceVisual_Record
    tax
    lda.l SourceVisual_State+29,x
    cmp #22
    beq SourceIdleRom_Header
    brl SourceIdleRom_Restore
SourceIdleRom_Header:
.a16
.i16
    ldx #0
SourceIdleRom_HeaderLoop:
.a16
.i16
    lda.l SourceVisual_EntryScratch,x
    cmp.l SourceIdleRom_Data+4,x
    beq SourceIdleRom_HeaderNext
    brl SourceIdleRom_Restore
SourceIdleRom_HeaderNext:
.a16
.i16
    inx
    inx
    cpx #24
    bcc SourceIdleRom_HeaderLoop
    jsl SourceCritical_Bridge_SVActor_MetaMatch
    bcc SourceIdleRom_Miss
    brl SourceIdleRom_Restore
SourceIdleRom_Miss:
.a16
.i16
    lda.l SourceVisual_ActorSlot
    beq SourceIdleRom_P1
    ldx #1280
    ldy #((SVActor_MetaData&$FFFF)+1280)
    bra SourceIdleRom_Copy
SourceIdleRom_P1:
.a16
.i16
    ldx #0
    ldy #(SVActor_MetaData&$FFFF)
SourceIdleRom_Copy:
.a16
.i16
    lda #0
    sta.l SVActor_MetaData+SVActor_MetaValid,x
    ldx #(SourceIdleRom_Data&$FFFF)
    lda #187
    mvn $43,$3C
SourceIdleRom_Copied:
.a16
.i16
    tya
    sec
    sbc #((SVActor_MetaData&$FFFF)+188)
    tax
    lda #0
    sta.l SVActor_MetaData+SVActor_MetaStage,x
    lda #1
    sta.l SVActor_MetaData+SVActor_MetaValid,x
SourceIdleRom_Restore:
.a16
.i16
    plb
    ply
    plx
    pla
    plp
SourceIdleRom_OriginalRead:
.a16
.i16
    jml SourceCritical_Bridge_ReadIdlePieces
SourceIdleRom_Data:
    .db $9B,$03,$0A,$00,$16,$00,$00,$00,$30,$00,$6A,$00,$17,$00,$67,$00
    .db $0A,$00,$01,$00,$6B,$34,$00,$00,$A2,$03,$00,$00,$E9,$FF,$C9,$FF
    .db $08,$00,$C9,$FF,$00,$00,$69,$01,$8A,$22,$00,$00,$E9,$FF,$E9,$FF
    .db $08,$00,$E9,$FF,$00,$00,$69,$01,$49,$0A,$02,$00,$F1,$FF,$99,$FF
    .db $00,$00,$99,$FF,$00,$00,$69,$01,$FE,$16,$04,$00,$F1,$FF,$A9,$FF
    .db $00,$00,$A9,$FF,$00,$00,$69,$01,$F8,$33,$06,$00,$F9,$FF,$C1,$FF
    .db $F8,$FF,$C1,$FF,$00,$00,$69,$01,$38,$06,$08,$00,$F9,$FF,$E1,$FF
    .db $F8,$FF,$E1,$FF,$00,$00,$69,$01,$C4,$2F,$0A,$00,$01,$00,$99,$FF
    .db $F0,$FF,$99,$FF,$00,$00,$69,$01,$49,$1C,$0C,$00,$01,$00,$B9,$FF
    .db $F0,$FF,$B9,$FF,$00,$00,$69,$01,$2F,$02,$0E,$00,$09,$00,$C1,$FF
    .db $E8,$FF,$C1,$FF,$00,$00,$69,$01,$22,$0E,$40,$00,$09,$00,$E1,$FF
    .db $E8,$FF,$E1,$FF,$00,$00,$69,$01,$4F,$2C,$42,$00
SourceIdleRom_End:
