; Exact P1->P2 immutable first-attack metadata reuse. No resources, pins,
; DMA, OAM, input or actor/world state are copied. Raw Valid publishes last.
SourcePeerMeta_Match:
.a16
.i16
    php
    rep #$30
    pha
    phx
    phy
    phb
    tdc
    cmp #$0A85
    beq SourcePeerMeta_P2
    brl SourcePeerMeta_Done
SourcePeerMeta_P2:
.a16
.i16
    lda.l SourceVisual_ActorSlot
    cmp #1
    beq SourcePeerMeta_G1
    brl SourcePeerMeta_Done
SourcePeerMeta_G1:
.a16
.i16
    lda.l SourceVisual_Record
    cmp #32
    beq SourcePeerMeta_G2
    brl SourcePeerMeta_Done
SourcePeerMeta_G2:
.a16
.i16
    lda.l SourceCritical_Role
    cmp #2
    beq SourcePeerMeta_G3
    brl SourcePeerMeta_Done
SourcePeerMeta_G3:
.a16
.i16
    lda.l SourceVisual_Key
    cmp #534
    beq SourcePeerMeta_G4
    brl SourcePeerMeta_Done
SourcePeerMeta_G4:
.a16
.i16
    lda.l SourceVisual_Key+2
    cmp #0
    beq SourcePeerMeta_G5
    brl SourcePeerMeta_Done
SourcePeerMeta_G5:
.a16
.i16
    lda.l Game_StageIndex
    cmp #0
    beq SourcePeerMeta_G6
    brl SourcePeerMeta_Done
SourcePeerMeta_G6:
.a16
.i16
    lda.l $7E46DE
    cmp #0
    beq SourcePeerMeta_G7
    brl SourcePeerMeta_Done
SourcePeerMeta_G7:
.a16
.i16
    lda.l SVActor_MetaData+SVActor_MetaValid
    cmp #1
    beq SourcePeerMeta_G8
    brl SourcePeerMeta_Done
SourcePeerMeta_G8:
.a16
.i16
    lda.l SVActor_MetaData+SVActor_MetaStage
    cmp #0
    beq SourcePeerMeta_G9
    brl SourcePeerMeta_Done
SourcePeerMeta_G9:
.a16
.i16
    lda.l SVActor_MetaData
    cmp.l SourceVisual_EntryIndexSaved
    beq SourcePeerMeta_Entry
    brl SourcePeerMeta_Done
SourcePeerMeta_Entry:
.a16
.i16
    lda.l SVActor_MetaData+2
    cmp #1
    bcs SourcePeerMeta_G10
    brl SourcePeerMeta_Done
SourcePeerMeta_G10:
.a16
.i16
    lda.l SVActor_MetaData+2
    cmp #66
    bcc SourcePeerMeta_G11
    brl SourcePeerMeta_Done
SourcePeerMeta_G11:
.a16
.i16
    lda.l SourceVisual_EntryScratch+12
    and #255
    cmp.l SVActor_MetaData+2
    beq SourcePeerMeta_Count
    brl SourcePeerMeta_Done
SourcePeerMeta_Count:
.a16
.i16
    ldx #0
SourcePeerMeta_Header:
.a16
.i16
    lda.l SVActor_MetaData+4,x
    cmp.l SourceVisual_EntryScratch,x
    beq SourcePeerMeta_HeaderWord
    brl SourcePeerMeta_Done
SourcePeerMeta_HeaderWord:
.a16
.i16
    inx
    inx
    cpx #24
    bcc SourcePeerMeta_Header
    lda.l SVActor_MetaData+$0500+SVActor_MetaValid
    cmp #1
    bne SourcePeerMeta_Copy
    lda.l SVActor_MetaData+$0500+SVActor_MetaStage
    bne SourcePeerMeta_Copy
    lda.l SVActor_MetaData+$0500
    cmp.l SourceVisual_EntryIndexSaved
    beq SourcePeerMeta_Done
SourcePeerMeta_Copy:
.a16
.i16
    lda #0
    sta.l SVActor_MetaData+$0500+SVActor_MetaValid
    lda.l SVActor_MetaData+2
    asl a
    asl a
    asl a
    asl a
    clc
    adc #28
    dec a
    ldx #(SVActor_MetaData&$FFFF)
    ldy #((SVActor_MetaData+$0500)&$FFFF)
    mvn $43,$43
    lda #0
    sta.l SVActor_MetaData+$0500+SVActor_MetaStage
    lda #1
    sta.l SVActor_MetaData+$0500+SVActor_MetaValid
SourcePeerMeta_Copied:
SourcePeerMeta_Done:
.a16
.i16
    plb
    ply
    plx
    pla
    plp
    jml SourceCritical_Bridge_SVActor_MetaMatch
SourcePeerMeta_End:
