; Reuse immutable exact live ground-walk metadata already loaded by a peer.
; Copy header+active piece rows only; preserve tail/prefetch/lease/pin state.
; Commit metadata Valid last. Original Critical checks ALL physical resources
; and DMA fences, then the ordinary loader maps/pins/palettes/publishes.
SourceWalkMeta_Dest = $7E46EE
SourceWalkMeta_Peer = $7E46F0
SourceWalkMeta_Count = $7E46F2
SourceWalkMeta_TryPeer:
.a16
.i16
    php
    rep #$30
    cld
    pha
    phx
    phy
    phb
    lda.l SourceCritical_Role
    cmp #1
    beq SourceWalkMeta_G1
    brl SourceWalkMeta_No
SourceWalkMeta_G1:
.a16
.i16
    lda.l $7E46DE
    cmp #0
    beq SourceWalkMeta_G2
    brl SourceWalkMeta_No
SourceWalkMeta_G2:
.a16
.i16
    jsr SourceNpc_Scope
    bcs SourceWalkMeta_Scope
    brl SourceWalkMeta_No
SourceWalkMeta_Scope:
.a16
.i16
    lda.l Game_StageIndex
    cmp #0
    beq SourceWalkMeta_G3
    brl SourceWalkMeta_No
SourceWalkMeta_G3:
.a16
.i16
    lda.l SourceVisual_Key
    cmp #278
    beq SourceWalkMeta_G4
    brl SourceWalkMeta_No
SourceWalkMeta_G4:
.a16
.i16
    lda.l SourceVisual_Key+2
    cmp.l SourceVisual_EntryScratch+2
    beq SourceWalkMeta_G5
    brl SourceWalkMeta_No
SourceWalkMeta_G5:
.a16
.i16
    lda.l SourceVisual_EntryScratch
    cmp #278
    beq SourceWalkMeta_G6
    brl SourceWalkMeta_No
SourceWalkMeta_G6:
.a16
.i16
    lda.l SourceVisual_EntryScratch+2
    cmp.l SourceVisual_Key+2
    beq SourceWalkMeta_G7
    brl SourceWalkMeta_No
SourceWalkMeta_G7:
.a16
.i16
    lda.l SourceVisual_EntryIndexSaved
    cmp #SOURCE_VISUAL_CATALOG_COUNT
    bcc SourceWalkMeta_G8
    brl SourceWalkMeta_No
SourceWalkMeta_G8:
.a16
.i16
    tdc
    cmp #$0A00
    beq SourceWalkMeta_P1
    cmp #$0A85
    beq SourceWalkMeta_P2
    brl SourceWalkMeta_No
SourceWalkMeta_P1:
.a16
.i16
    lda.l SourceVisual_ActorSlot
    cmp #0
    beq SourceWalkMeta_G9
    brl SourceWalkMeta_No
SourceWalkMeta_G9:
.a16
.i16
    lda.l SourceVisual_Record
    cmp #0
    beq SourceWalkMeta_G10
    brl SourceWalkMeta_No
SourceWalkMeta_G10:
.a16
.i16
    ldx #0
    brl SourceWalkMeta_Actor
SourceWalkMeta_P2:
.a16
.i16
    lda.l SourceVisual_ActorSlot
    cmp #1
    beq SourceWalkMeta_G11
    brl SourceWalkMeta_No
SourceWalkMeta_G11:
.a16
.i16
    lda.l SourceVisual_Record
    cmp #32
    beq SourceWalkMeta_G12
    brl SourceWalkMeta_No
SourceWalkMeta_G12:
.a16
.i16
    ldx #133
SourceWalkMeta_Actor:
.a16
.i16
    lda.l $7E0A00+CHAR_HP,x
    and #255
    cmp #0
    bne SourceWalkMeta_G13
    brl SourceWalkMeta_No
SourceWalkMeta_G13:
.a16
.i16
    lda.l $7E0A00+CHAR_INPUT_DRIVEN,x
    and #255
    cmp #1
    beq SourceWalkMeta_G14
    brl SourceWalkMeta_No
SourceWalkMeta_G14:
.a16
.i16
    lda.l $7E0A00+CHAR_ROSTER_INDEX,x
    and #255
    cmp #22
    beq SourceWalkMeta_G15
    brl SourceWalkMeta_No
SourceWalkMeta_G15:
.a16
.i16
    lda.l $7E0A00+CHAR_MAP_INDEX,x
    and #255
    cmp #0
    beq SourceWalkMeta_G16
    brl SourceWalkMeta_No
SourceWalkMeta_G16:
.a16
.i16
    lda.l $7E0A00+CHAR_SELECTED,x
    and #255
    cmp #3
    bcc SourceWalkMeta_G17
    brl SourceWalkMeta_No
SourceWalkMeta_G17:
.a16
.i16
    lda.l SourceVisual_Sa1OwnerPolicy,x
    and #255
    cmp #2
    beq SourceWalkMeta_G18
    brl SourceWalkMeta_No
SourceWalkMeta_G18:
.a16
.i16
    lda.l SourceVisual_Sa1RuntimeRole,x
    and #255
    cmp #1
    beq SourceWalkMeta_G19
    brl SourceWalkMeta_No
SourceWalkMeta_G19:
.a16
.i16
    lda.l SourceVisual_Record
    tax
    lda.l SourceVisual_State+6,x
    cmp #1
    beq SourceWalkMeta_G20
    brl SourceWalkMeta_No
SourceWalkMeta_G20:
.a16
.i16
    lda.l SourceVisual_State+28,x
    and #255
    cmp #0
    beq SourceWalkMeta_G21
    brl SourceWalkMeta_No
SourceWalkMeta_G21:
.a16
.i16
    lda.l SourceVisual_State+29,x
    cmp #278
    beq SourceWalkMeta_G22
    brl SourceWalkMeta_No
SourceWalkMeta_G22:
.a16
.i16
    lda.l SourceVisual_State,x
    cmp.l SourceVisual_EntryIndexSaved
    beq SourceWalkMeta_Desired
    brl SourceWalkMeta_No
SourceWalkMeta_Desired:
.a16
.i16
    lda.l SourceVisual_ActorSlot
    beq SourceWalkMeta_RowsP1
    lda #1280
    sta.l SourceWalkMeta_Dest
    lda #0
    sta.l SourceWalkMeta_Peer
    bra SourceWalkMeta_Rows
SourceWalkMeta_RowsP1:
.a16
.i16
    lda #0
    sta.l SourceWalkMeta_Dest
    lda #1280
    sta.l SourceWalkMeta_Peer
SourceWalkMeta_Rows:
.a16
.i16
    lda.l SourceWalkMeta_Dest
    tax
    lda.l SVActor_MetaData+SVActor_MetaValid,x
    cmp #1
    bne SourceWalkMeta_CheckPeer
    lda.l SVActor_MetaData+SVActor_MetaStage,x
    cmp #0
    bne SourceWalkMeta_CheckPeer
    lda.l SVActor_MetaData,x
    cmp.l SourceVisual_EntryIndexSaved
    bne SourceWalkMeta_CheckPeer
    brl SourceWalkMeta_No
SourceWalkMeta_CheckPeer:
.a16
.i16
    lda.l SourceWalkMeta_Peer
    tax
    lda.l SVActor_MetaData+SVActor_MetaValid,x
    cmp #1
    beq SourceWalkMeta_G23
    brl SourceWalkMeta_No
SourceWalkMeta_G23:
.a16
.i16
    lda.l SVActor_MetaData+SVActor_MetaStage,x
    cmp #0
    beq SourceWalkMeta_G24
    brl SourceWalkMeta_No
SourceWalkMeta_G24:
.a16
.i16
    lda.l SVActor_MetaData,x
    cmp.l SourceVisual_EntryIndexSaved
    beq SourceWalkMeta_PeerEntry
    brl SourceWalkMeta_No
SourceWalkMeta_PeerEntry:
.a16
.i16
    lda.l SVActor_MetaData+2,x
    cmp #0
    bne SourceWalkMeta_G25
    brl SourceWalkMeta_No
SourceWalkMeta_G25:
.a16
.i16
    lda.l SVActor_MetaData+2,x
    cmp #66
    bcc SourceWalkMeta_G26
    brl SourceWalkMeta_No
SourceWalkMeta_G26:
.a16
.i16
    lda.l SVActor_MetaData+2,x
    sta.l SourceWalkMeta_Count
    and #$00FF
    cmp.l SourceVisual_EntryScratch+12
    beq SourceWalkMeta_CountValid
    brl SourceWalkMeta_No
SourceWalkMeta_CountValid:
.a16
.i16
    lda.l SVActor_MetaData+4,x
    cmp.l SourceVisual_EntryScratch+0
    beq SourceWalkMeta_Header0
    brl SourceWalkMeta_No
SourceWalkMeta_Header0:
.a16
.i16
    lda.l SVActor_MetaData+6,x
    cmp.l SourceVisual_EntryScratch+2
    beq SourceWalkMeta_Header2
    brl SourceWalkMeta_No
SourceWalkMeta_Header2:
.a16
.i16
    lda.l SVActor_MetaData+8,x
    cmp.l SourceVisual_EntryScratch+4
    beq SourceWalkMeta_Header4
    brl SourceWalkMeta_No
SourceWalkMeta_Header4:
.a16
.i16
    lda.l SVActor_MetaData+10,x
    cmp.l SourceVisual_EntryScratch+6
    beq SourceWalkMeta_Header6
    brl SourceWalkMeta_No
SourceWalkMeta_Header6:
.a16
.i16
    lda.l SVActor_MetaData+12,x
    cmp.l SourceVisual_EntryScratch+8
    beq SourceWalkMeta_Header8
    brl SourceWalkMeta_No
SourceWalkMeta_Header8:
.a16
.i16
    lda.l SVActor_MetaData+14,x
    cmp.l SourceVisual_EntryScratch+10
    beq SourceWalkMeta_Header10
    brl SourceWalkMeta_No
SourceWalkMeta_Header10:
.a16
.i16
    lda.l SVActor_MetaData+16,x
    cmp.l SourceVisual_EntryScratch+12
    beq SourceWalkMeta_Header12
    brl SourceWalkMeta_No
SourceWalkMeta_Header12:
.a16
.i16
    lda.l SVActor_MetaData+18,x
    cmp.l SourceVisual_EntryScratch+14
    beq SourceWalkMeta_Header14
    brl SourceWalkMeta_No
SourceWalkMeta_Header14:
.a16
.i16
    lda.l SVActor_MetaData+20,x
    cmp.l SourceVisual_EntryScratch+16
    beq SourceWalkMeta_Header16
    brl SourceWalkMeta_No
SourceWalkMeta_Header16:
.a16
.i16
    lda.l SVActor_MetaData+22,x
    cmp.l SourceVisual_EntryScratch+18
    beq SourceWalkMeta_Header18
    brl SourceWalkMeta_No
SourceWalkMeta_Header18:
.a16
.i16
    lda.l SVActor_MetaData+24,x
    cmp.l SourceVisual_EntryScratch+20
    beq SourceWalkMeta_Header20
    brl SourceWalkMeta_No
SourceWalkMeta_Header20:
.a16
.i16
    lda.l SVActor_MetaData+26,x
    cmp.l SourceVisual_EntryScratch+22
    beq SourceWalkMeta_Header22
    brl SourceWalkMeta_No
SourceWalkMeta_Header22:
.a16
.i16
    lda.l SourceWalkMeta_Count
    asl a
    asl a
    asl a
    asl a
    clc
    adc #28
    sta.l SourceWalkMeta_Count
    lda.l SourceWalkMeta_Dest
    tax
    lda #0
    sta.l SVActor_MetaData+SVActor_MetaValid,x
    txa
    clc
    adc #(SVActor_MetaData & $FFFF)
    tay
    lda.l SourceWalkMeta_Peer
    clc
    adc #(SVActor_MetaData & $FFFF)
    tax
    lda.l SourceWalkMeta_Count
    dec a
SourceWalkMeta_Copy:
.a16
.i16
    mvn $43,$43
    lda.l SourceWalkMeta_Dest
    tax
    lda #0
    sta.l SVActor_MetaData+SVActor_MetaStage,x
    lda #1
    sta.l SVActor_MetaData+SVActor_MetaValid,x
SourceWalkMeta_Copied:
.a16
.i16
    plb
    ply
    plx
    pla
    plp
    sec
    rtl
SourceWalkMeta_No:
.a16
.i16
    plb
    ply
    plx
    pla
    plp
    clc
    rtl
SourceWalkMeta_End:
