; Reuse only immutable exact default-model ground metadata loaded by a peer.
; Copy header+active piece rows only; preserve tail/prefetch/lease/pin state.
; Commit metadata Valid last. Original Critical checks ALL physical resources
; and DMA fences, then the ordinary loader maps/pins/palettes/publishes.
SourceMeta_Dest = $7E46EE
SourceMeta_Peer = $7E46F0
SourceMeta_Count = $7E46F2
SourceMeta_TryPeer:
.a16
.i16
    php
    rep #$30
    cld
    pha
    phx
    phy
    phb
    ; Exact immutable ground pose, no predicted frame or input substitution.
    lda.l SourceVisual_Key
    and #$00FF
    cmp #22
    beq SourceMeta_Model
    brl SourceMeta_No
SourceMeta_Model:
.a16
.i16
    lda.l SourceVisual_Key+1
    and #$00FF
    cmp #3
    bcc SourceMeta_Ground
    brl SourceMeta_No
SourceMeta_Ground:
.a16
.i16
    lda.l $7E46DE
    cmp #0
    beq SourceMeta_G2
    brl SourceMeta_No
SourceMeta_G2:
.a16
.i16
    jsr SourceNpc_Scope
    bcs SourceMeta_Scope
    brl SourceMeta_No
SourceMeta_Scope:
.a16
.i16
    lda.l Game_StageIndex
    cmp #0
    beq SourceMeta_G3
    brl SourceMeta_No
SourceMeta_G3:
.a16
.i16
    lda.l SourceVisual_Key+3
    and #$00FF
    beq SourceMeta_Map
    brl SourceMeta_No
SourceMeta_Map:
.a16
.i16
    lda.l SourceVisual_EntryScratch
    cmp.l SourceVisual_Key
    beq SourceMeta_HeaderKey
    brl SourceMeta_No
SourceMeta_HeaderKey:
.a16
.i16
    lda.l SourceVisual_EntryScratch+2
    cmp.l SourceVisual_Key+2
    beq SourceMeta_HeaderFrame
    brl SourceMeta_No
SourceMeta_HeaderFrame:
.a16
.i16
    lda.l SourceVisual_Key+1
    and #255
    beq SourceMeta_IndexIdle
    cmp #1
    beq SourceMeta_IndexWalk
    lda.l SourceVisual_Key+2
    and #255
    cmp #6
    bcc SourceMeta_IndexAttackValid
    brl SourceMeta_No
SourceMeta_IndexAttackValid:
.a16
.i16
    asl a
    clc
    adc #781
    bra SourceMeta_IndexCheck
SourceMeta_IndexIdle:
.a16
.i16
    lda.l SourceVisual_Key+2
    and #255
    cmp #18
    bcc SourceMeta_IndexIdleValid
    brl SourceMeta_No
SourceMeta_IndexIdleValid:
.a16
.i16
    asl a
    clc
    adc #923
    bra SourceMeta_IndexCheck
SourceMeta_IndexWalk:
.a16
.i16
    lda.l SourceVisual_Key+2
    and #255
    cmp #10
    bcc SourceMeta_IndexWalkValid
    brl SourceMeta_No
SourceMeta_IndexWalkValid:
.a16
.i16
    asl a
    clc
    adc #1043
SourceMeta_IndexCheck:
.a16
.i16
    cmp.l SourceVisual_EntryIndexSaved
    beq SourceMeta_IndexValid
    brl SourceMeta_No
SourceMeta_IndexValid:
.a16
.i16
    lda.l SourceVisual_EntryIndexSaved
    cmp #SOURCE_VISUAL_CATALOG_COUNT
    bcc SourceMeta_G8
    brl SourceMeta_No
SourceMeta_G8:
.a16
.i16
    tdc
    cmp #$0A00
    beq SourceMeta_P1
    cmp #$0A85
    beq SourceMeta_P2
    brl SourceMeta_No
SourceMeta_P1:
.a16
.i16
    lda.l SourceVisual_ActorSlot
    cmp #0
    beq SourceMeta_G9
    brl SourceMeta_No
SourceMeta_G9:
.a16
.i16
    lda.l SourceVisual_Record
    cmp #0
    beq SourceMeta_G10
    brl SourceMeta_No
SourceMeta_G10:
.a16
.i16
    ldx #0
    brl SourceMeta_Actor
SourceMeta_P2:
.a16
.i16
    lda.l SourceVisual_ActorSlot
    cmp #1
    beq SourceMeta_G11
    brl SourceMeta_No
SourceMeta_G11:
.a16
.i16
    lda.l SourceVisual_Record
    cmp #32
    beq SourceMeta_G12
    brl SourceMeta_No
SourceMeta_G12:
.a16
.i16
    ldx #133
SourceMeta_Actor:
.a16
.i16
    lda.l $7E0A00+CHAR_HP,x
    and #255
    cmp #0
    bne SourceMeta_G13
    brl SourceMeta_No
SourceMeta_G13:
.a16
.i16
    lda.l $7E0A00+CHAR_INPUT_DRIVEN,x
    and #255
    cmp #1
    beq SourceMeta_G14
    brl SourceMeta_No
SourceMeta_G14:
.a16
.i16
    lda.l $7E0A00+CHAR_ROSTER_INDEX,x
    and #255
    cmp #22
    beq SourceMeta_G15
    brl SourceMeta_No
SourceMeta_G15:
.a16
.i16
    lda.l $7E0A00+CHAR_MAP_INDEX,x
    and #255
    cmp #0
    beq SourceMeta_G16
    brl SourceMeta_No
SourceMeta_G16:
.a16
.i16
    lda.l $7E0A00+CHAR_SELECTED,x
    and #255
    cmp #3
    bcc SourceMeta_G17
    brl SourceMeta_No
SourceMeta_G17:
.a16
.i16
    lda.l SourceVisual_Sa1OwnerPolicy,x
    and #255
    cmp #2
    beq SourceMeta_G18
    brl SourceMeta_No
SourceMeta_G18:
.a16
.i16
    lda.l SourceVisual_Key+1
    and #255
    sta.l SourceMeta_Count
    lda.l SourceVisual_Sa1RuntimeRole,x
    and #255
    cmp.l SourceMeta_Count
    beq SourceMeta_G19
    brl SourceMeta_No
SourceMeta_G19:
.a16
.i16
    lda.l SourceVisual_Record
    tax
    lda.l SourceVisual_State+6,x
    cmp #1
    beq SourceMeta_G20
    brl SourceMeta_No
SourceMeta_G20:
.a16
.i16
    lda.l SourceVisual_State+28,x
    and #255
    cmp #0
    beq SourceMeta_G21
    brl SourceMeta_No
SourceMeta_G21:
.a16
.i16
    lda.l SourceVisual_State+29,x
    cmp.l SourceVisual_Key
    beq SourceMeta_G22
    brl SourceMeta_No
SourceMeta_G22:
.a16
.i16
    lda.l SourceVisual_State,x
    cmp.l SourceVisual_EntryIndexSaved
    beq SourceMeta_Desired
    brl SourceMeta_No
SourceMeta_Desired:
.a16
.i16
    lda.l SourceVisual_ActorSlot
    beq SourceMeta_RowsP1
    lda #1280
    sta.l SourceMeta_Dest
    lda #0
    sta.l SourceMeta_Peer
    bra SourceMeta_Rows
SourceMeta_RowsP1:
.a16
.i16
    lda #0
    sta.l SourceMeta_Dest
    lda #1280
    sta.l SourceMeta_Peer
SourceMeta_Rows:
.a16
.i16
    lda.l SourceMeta_Dest
    tax
    lda.l SVActor_MetaData+SVActor_MetaValid,x
    cmp #1
    bne SourceMeta_CheckPeer
    lda.l SVActor_MetaData+SVActor_MetaStage,x
    cmp #0
    bne SourceMeta_CheckPeer
    lda.l SVActor_MetaData,x
    cmp.l SourceVisual_EntryIndexSaved
    bne SourceMeta_CheckPeer
    brl SourceMeta_No
SourceMeta_CheckPeer:
.a16
.i16
    lda.l SourceMeta_Peer
    tax
    lda.l SVActor_MetaData+SVActor_MetaValid,x
    cmp #1
    beq SourceMeta_G23
    brl SourceMeta_No
SourceMeta_G23:
.a16
.i16
    lda.l SVActor_MetaData+SVActor_MetaStage,x
    cmp #0
    beq SourceMeta_G24
    brl SourceMeta_No
SourceMeta_G24:
.a16
.i16
    lda.l SVActor_MetaData,x
    cmp.l SourceVisual_EntryIndexSaved
    beq SourceMeta_PeerEntry
    brl SourceMeta_No
SourceMeta_PeerEntry:
.a16
.i16
    lda.l SVActor_MetaData+2,x
    cmp #0
    bne SourceMeta_G25
    brl SourceMeta_No
SourceMeta_G25:
.a16
.i16
    lda.l SVActor_MetaData+2,x
    cmp #66
    bcc SourceMeta_G26
    brl SourceMeta_No
SourceMeta_G26:
.a16
.i16
    lda.l SVActor_MetaData+2,x
    sta.l SourceMeta_Count
    and #$00FF
    cmp.l SourceVisual_EntryScratch+12
    beq SourceMeta_CountValid
    brl SourceMeta_No
SourceMeta_CountValid:
.a16
.i16
    lda.l SourceMeta_Count
    cmp.l SourceVisual_PieceCount
    beq SourceMeta_CallerCount
    brl SourceMeta_No
SourceMeta_CallerCount:
.a16
.i16
    lda.l SVActor_MetaData+4,x
    cmp.l SourceVisual_EntryScratch+0
    beq SourceMeta_Header0
    brl SourceMeta_No
SourceMeta_Header0:
.a16
.i16
    lda.l SVActor_MetaData+6,x
    cmp.l SourceVisual_EntryScratch+2
    beq SourceMeta_Header2
    brl SourceMeta_No
SourceMeta_Header2:
.a16
.i16
    lda.l SVActor_MetaData+8,x
    cmp.l SourceVisual_EntryScratch+4
    beq SourceMeta_Header4
    brl SourceMeta_No
SourceMeta_Header4:
.a16
.i16
    lda.l SVActor_MetaData+10,x
    cmp.l SourceVisual_EntryScratch+6
    beq SourceMeta_Header6
    brl SourceMeta_No
SourceMeta_Header6:
.a16
.i16
    lda.l SVActor_MetaData+12,x
    cmp.l SourceVisual_EntryScratch+8
    beq SourceMeta_Header8
    brl SourceMeta_No
SourceMeta_Header8:
.a16
.i16
    lda.l SVActor_MetaData+14,x
    cmp.l SourceVisual_EntryScratch+10
    beq SourceMeta_Header10
    brl SourceMeta_No
SourceMeta_Header10:
.a16
.i16
    lda.l SVActor_MetaData+16,x
    cmp.l SourceVisual_EntryScratch+12
    beq SourceMeta_Header12
    brl SourceMeta_No
SourceMeta_Header12:
.a16
.i16
    lda.l SVActor_MetaData+18,x
    cmp.l SourceVisual_EntryScratch+14
    beq SourceMeta_Header14
    brl SourceMeta_No
SourceMeta_Header14:
.a16
.i16
    lda.l SVActor_MetaData+20,x
    cmp.l SourceVisual_EntryScratch+16
    beq SourceMeta_Header16
    brl SourceMeta_No
SourceMeta_Header16:
.a16
.i16
    lda.l SVActor_MetaData+22,x
    cmp.l SourceVisual_EntryScratch+18
    beq SourceMeta_Header18
    brl SourceMeta_No
SourceMeta_Header18:
.a16
.i16
    lda.l SVActor_MetaData+24,x
    cmp.l SourceVisual_EntryScratch+20
    beq SourceMeta_Header20
    brl SourceMeta_No
SourceMeta_Header20:
.a16
.i16
    lda.l SVActor_MetaData+26,x
    cmp.l SourceVisual_EntryScratch+22
    beq SourceMeta_Header22
    brl SourceMeta_No
SourceMeta_Header22:
.a16
.i16
    lda.l SourceMeta_Count
    asl a
    asl a
    asl a
    asl a
    clc
    adc #28
    sta.l SourceMeta_Count
    lda.l SourceMeta_Dest
    tax
    lda #0
    sta.l SVActor_MetaData+SVActor_MetaValid,x
    txa
    clc
    adc #(SVActor_MetaData & $FFFF)
    tay
    lda.l SourceMeta_Peer
    clc
    adc #(SVActor_MetaData & $FFFF)
    tax
    lda.l SourceMeta_Count
    dec a
SourceMeta_Copy:
.a16
.i16
    mvn $43,$43
    ; The caller's own MetaPieces already missed. Fill its piece table
    ; directly, so the warm-hit path never enters this helper at all.
    lda.l SourceMeta_Peer
    clc
    adc #((SVActor_MetaData+28) & $FFFF)
    tax
    ldy #(SourceVisual_PieceTable & $FFFF)
    lda.l SourceMeta_Count
    sec
    sbc #28
    dec a
    mvn $7E,$43
    lda.l SourceMeta_Dest
    tax
    lda #0
    sta.l SVActor_MetaData+SVActor_MetaStage,x
    lda #1
    sta.l SVActor_MetaData+SVActor_MetaValid,x
SourceMeta_Copied:
.a16
.i16
    plb
    ply
    plx
    pla
    plp
    sec
    rtl
SourceMeta_No:
.a16
.i16
    plb
    ply
    plx
    pla
    plp
    clc
    rtl
SourceMeta_End:
