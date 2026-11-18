; Exact immutable Kula walk1 metadata cache fill. No frame selection,
; tile/palette/queue/owner/Ready or simulation changes. Ordinary cache lookup
; remains first; only its miss may populate the existing raw metadata row.
SourceRowMeta_Pieces:
.a16
.i16
    jsl SVActor_MetaPieces
    bcs SourceRowMeta_Done
    jsr SourceRowMeta_Prime
    bcc SourceRowMeta_Done
    jml SVActor_MetaPieces
SourceRowMeta_Done:
.a16
.i16
    rtl
SourceRowMeta_Prime:
.a16
.i16
    php
    rep #$30
    pha
    phx
    phy
    phb
    jsr SourceNpc_Scope
    bcs SourceRowMeta_Scope
    brl SourceRowMeta_No
SourceRowMeta_Scope:
.a16
.i16
    lda.l Game_StageIndex
    beq SourceRowMeta_Stage
    brl SourceRowMeta_No
SourceRowMeta_Stage:
.a16
.i16
    lda.l SourceVisual_ActorSlot
    cmp #2
    bcc SourceRowMeta_Actor
    brl SourceRowMeta_No
SourceRowMeta_Actor:
.a16
.i16
    lda.l SourceVisual_EntryIndexSaved
    cmp #1045
    beq SourceRowMeta_Entry
    brl SourceRowMeta_No
SourceRowMeta_Entry:
.a16
.i16
    lda.l SourceVisual_PieceCount
    cmp #10
    beq SourceRowMeta_Count
    brl SourceRowMeta_No
SourceRowMeta_Count:
.a16
.i16
    ldx #0
SourceRowMeta_Header:
.a16
.i16
    lda.l SourceVisual_EntryScratch,x
    cmp.l SourceRowMeta_HeaderData,x
    beq SourceRowMeta_NextWord
    brl SourceRowMeta_No
SourceRowMeta_NextWord:
.a16
.i16
    inx
    inx
    cpx #24
    bcc SourceRowMeta_Header
    lda.l SourceVisual_ActorSlot
    beq SourceRowMeta_P1
    ldx #1280
    bra SourceRowMeta_Copy
SourceRowMeta_P1:
.a16
.i16
    ldx #0
SourceRowMeta_Copy:
.a16
.i16
    lda #0
    sta.l SVActor_MetaData+SVActor_MetaValid,x
    phx
    txa
    clc
    adc #(SVActor_MetaData & $FFFF)
    tay
    ldx #(SourceRowMeta_Data & $FFFF)
    lda #187
SourceRowMeta_CopyBytes:
.a16
.i16
    mvn $43,$3C
    plx
    lda #0
    sta.l SVActor_MetaData+SVActor_MetaStage,x
    lda #1
    sta.l SVActor_MetaData+SVActor_MetaValid,x
SourceRowMeta_Committed:
.a16
.i16
    plb
    ply
    plx
    pla
    plp
    sec
    rts
SourceRowMeta_No:
.a16
.i16
    plb
    ply
    plx
    pla
    plp
    clc
    rts
SourceRowMeta_Data:
    .db $15,$04,$0A,$00
SourceRowMeta_HeaderData:
    .db $16,$01,$01,$00,$37,$00,$6A,$00,$1A,$00,$68,$00
    .db $0A,$00,$01,$00,$15,$39,$00,$00,$19,$02,$00,$00,$DE,$FF,$A8,$FF
    .db $13,$00,$A8,$FF,$00,$00,$20,$00,$22,$1D,$00,$00,$E6,$FF,$B8,$FF
    .db $0B,$00,$B8,$FF,$00,$00,$20,$00,$49,$15,$02,$00,$EE,$FF,$98,$FF
    .db $03,$00,$98,$FF,$00,$00,$20,$00,$56,$15,$04,$00,$EE,$FF,$E0,$FF
    .db $03,$00,$E0,$FF,$00,$00,$20,$00,$36,$07,$06,$00,$F6,$FF,$B8,$FF
    .db $FB,$FF,$B8,$FF,$00,$00,$20,$00,$64,$2D,$08,$00,$FE,$FF,$98,$FF
    .db $F3,$FF,$98,$FF,$00,$00,$20,$00,$41,$21,$0A,$00,$FE,$FF,$C8,$FF
    .db $F3,$FF,$C8,$FF,$00,$00,$20,$00,$B5,$2E,$0C,$00,$FE,$FF,$E8,$FF
    .db $F3,$FF,$E8,$FF,$00,$00,$20,$00,$57,$19,$0E,$00,$06,$00,$B0,$FF
    .db $EB,$FF,$B0,$FF,$00,$00,$20,$00,$A1,$0A,$40,$00,$0E,$00,$F0,$FF
    .db $E3,$FF,$F0,$FF,$00,$00,$20,$00,$67,$41,$42,$00
SourceRowMeta_End:
