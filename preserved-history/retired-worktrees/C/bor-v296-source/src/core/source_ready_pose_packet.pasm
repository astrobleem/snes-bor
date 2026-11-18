; Ready-only whole-picture publication, outside the depth-sorted pass.
; No allocation, input, actor/world writes or completion shortcuts. All
; captures and full544-byte enqueue/retirement use the original protocol.
; $436000..4363FF is disjoint from raw metadata, motion, packet, geometry,
; signed-X and compiled choice tables. Only foreground owns this scratch.
SourceFastPose_SaveShadow = $436000 ;672 bytes: main/packed/expanded OAM
SourceFastPose_SaveBuild = $4362A0 ;64 player build metadata bytes
SourceFastPose_SaveNpc = $4362E0 ;128 NPC build metadata bytes
SourceFastPose_Slot = $436380
SourceFastPose_Native = $436382
SourceFastPose_Meta = $436384
SourceFastPose_Raw = $436386
SourceFastPose_Begin = $436388
SourceFastPose_End = $43638A
SourceFastPose_Changed = $43638C
SourceFastPose_Seq = $43638E
SourceFastPose_Temp = $436390
SourceFastPose_Shift = $436392
SourceFastPose_OldEarly = $436394
SourceFastPose_OldHigh = $436396
SourceFastPose_OldNeed = $436398
SourceFastPose_OldThis = $43639A
SourceFastPose_OldCursor = $43639C
SourceFastPose_OldService = $43639E

SourceFastPose_DuringWait:
    php
    rep #$30
.a16
.i16
    pha
    phx
    phy
    phb
    phd
    cld
    lda.l SourceVisual_State+6
    cmp #2
    bne SourceFastPose_CheckP2
    lda.l SourceVisual_State+28
    and #255
    beq SourceFastPose_Scope
SourceFastPose_CheckP2:
.a16
.i16
    lda.l SourceVisual_State+38
    cmp #2
    bne SourceFastPose_NoCandidate
    lda.l SourceVisual_State+60
    and #255
    beq SourceFastPose_Scope
SourceFastPose_NoCandidate:
.a16
.i16
    brl SourceFastPose_Done
SourceFastPose_Scope:
.a16
.i16
    lda.l Game_CampaignId
    cmp #3
    beq SourceFastPose_G1
    brl SourceFastPose_Done
SourceFastPose_G1:
.a16
.i16
    lda.l Game_State
    cmp #0
    beq SourceFastPose_G2
    brl SourceFastPose_Done
SourceFastPose_G2:
.a16
.i16
    lda.l Game_StageIndex
    cmp #0
    beq SourceFastPose_G3
    brl SourceFastPose_Done
SourceFastPose_G3:
.a16
.i16
    lda.l $7E175E
    cmp #2
    beq SourceFastPose_G4
    brl SourceFastPose_Done
SourceFastPose_G4:
.a16
.i16
    lda.l $7E1760
    cmp #1
    beq SourceFastPose_G5
    brl SourceFastPose_Done
SourceFastPose_G5:
.a16
.i16
    lda.l $7E46DC
    cmp #1
    beq SourceFastPose_G6
    brl SourceFastPose_Done
SourceFastPose_G6:
.a16
.i16
    lda.l $7E46DE
    cmp #0
    beq SourceFastPose_G7
    brl SourceFastPose_Done
SourceFastPose_G7:
.a16
.i16
    lda.l SourceInput_Magic
    cmp #6752
    beq SourceFastPose_G8
    brl SourceFastPose_Done
SourceFastPose_G8:
.a16
.i16
    lda.l SourceVisual_CompletedMagic
    cmp #49229
    beq SourceFastPose_G9
    brl SourceFastPose_Done
SourceFastPose_G9:
.a16
.i16
    lda.l SVActor_Magic
    cmp #44057
    beq SourceFastPose_G10
    brl SourceFastPose_Done
SourceFastPose_G10:
.a16
.i16
    lda.l SourcePacket_ActiveValid
    cmp #1
    beq SourceFastPose_G11
    brl SourceFastPose_Done
SourceFastPose_G11:
.a16
.i16
    lda.l SourcePacket_CopyBusy
    cmp #0
    beq SourceFastPose_G12
    brl SourceFastPose_Done
SourceFastPose_G12:
.a16
.i16
    lda.l SourcePacket_NmiPending
    cmp #2
    bcc SourceFastPose_G13
    brl SourceFastPose_Done
SourceFastPose_G13:
.a16
.i16
    lda.l SourceVisual_CompletedHeld
    and #255
    cmp #0
    beq SourceFastPose_G14
    brl SourceFastPose_Done
SourceFastPose_G14:
.a16
.i16
    lda.l SourceVisual_AfterPassCount
    cmp #1
    beq SourceFastPose_G15
    brl SourceFastPose_Done
SourceFastPose_G15:
.a16
.i16
    lda.l Oam_CurrentSlot
    cmp #0
    beq SourceFastPose_G16
    brl SourceFastPose_Done
SourceFastPose_G16:
.a16
.i16
    lda.l Oam_UploadFlag
    cmp #0
    beq SourceFastPose_G17
    brl SourceFastPose_Done
SourceFastPose_G17:
.a16
.i16
    lda.l Nmi_HdmaEnableCurrent
    and #255
    cmp #0
    beq SourceFastPose_G18
    brl SourceFastPose_Done
SourceFastPose_G18:
.a16
.i16
    lda.l SourcePacket_ActiveCamera
    cmp.l Screen_PosX
    beq SourceFastPose_G19
    brl SourceFastPose_Done
SourceFastPose_G19:
.a16
.i16
    jsr SourceFastPose_Coherent
    bcs SourceFastPose_CoherentStage
    brl SourceFastPose_Done
SourceFastPose_CoherentStage:
.a16
.i16
    lda.l $434E2C
    beq SourceFastPose_MotionStage
    brl SourceFastPose_Done
SourceFastPose_MotionStage:
.a16
.i16
    lda.l $434E7E
    cmp #$4D50
    beq SourceFastPose_G20
    brl SourceFastPose_Done
SourceFastPose_G20:
.a16
.i16
    lda.l $434E7C
    and #1
    beq SourceFastPose_G21
    brl SourceFastPose_Done
SourceFastPose_G21:
.a16
.i16
    lda.l SOURCE_PACKET_ACTIVE_META+16
    cmp #1
    beq SourceFastPose_G22
    brl SourceFastPose_Done
SourceFastPose_G22:
.a16
.i16
    lda.l SOURCE_PACKET_ACTIVE_META+8
    cmp #22
    beq SourceFastPose_G23
    brl SourceFastPose_Done
SourceFastPose_G23:
.a16
.i16
    lda.l SOURCE_PACKET_ACTIVE_META+10
    cmp #0
    beq SourceFastPose_G24
    brl SourceFastPose_Done
SourceFastPose_G24:
.a16
.i16
    lda.l SOURCE_PACKET_ACTIVE_META+0
    ora.l SOURCE_PACKET_ACTIVE_META+2
    and #3
    beq SourceFastPose_G25
    brl SourceFastPose_Done
SourceFastPose_G25:
.a16
.i16
    lda.l SOURCE_PACKET_ACTIVE_META+2
    cmp #513
    bcc SourceFastPose_G26
    brl SourceFastPose_Done
SourceFastPose_G26:
.a16
.i16
    lda.l SOURCE_PACKET_ACTIVE_META+0
    cmp.l SOURCE_PACKET_ACTIVE_META+2
    bcc SourceFastPose_G27
    brl SourceFastPose_Done
SourceFastPose_G27:
.a16
.i16
    lda.l SOURCE_PACKET_ACTIVE_META+48
    cmp #1
    beq SourceFastPose_G28
    brl SourceFastPose_Done
SourceFastPose_G28:
.a16
.i16
    lda.l SOURCE_PACKET_ACTIVE_META+40
    cmp #22
    beq SourceFastPose_G29
    brl SourceFastPose_Done
SourceFastPose_G29:
.a16
.i16
    lda.l SOURCE_PACKET_ACTIVE_META+42
    cmp #0
    beq SourceFastPose_G30
    brl SourceFastPose_Done
SourceFastPose_G30:
.a16
.i16
    lda.l SOURCE_PACKET_ACTIVE_META+32
    ora.l SOURCE_PACKET_ACTIVE_META+34
    and #3
    beq SourceFastPose_G31
    brl SourceFastPose_Done
SourceFastPose_G31:
.a16
.i16
    lda.l SOURCE_PACKET_ACTIVE_META+34
    cmp #513
    bcc SourceFastPose_G32
    brl SourceFastPose_Done
SourceFastPose_G32:
.a16
.i16
    lda.l SOURCE_PACKET_ACTIVE_META+32
    cmp.l SOURCE_PACKET_ACTIVE_META+34
    bcc SourceFastPose_G33
    brl SourceFastPose_Done
SourceFastPose_G33:
.a16
.i16
    lda.l SOURCE_PACKET_ACTIVE_META+2
    cmp.l SOURCE_PACKET_ACTIVE_META+32
    bcc SourceFastPose_Ranges
    beq SourceFastPose_Ranges
    lda.l SOURCE_PACKET_ACTIVE_META+34
    cmp.l SOURCE_PACKET_ACTIVE_META
    bcc SourceFastPose_Ranges
    beq SourceFastPose_Ranges
    brl SourceFastPose_Done
SourceFastPose_Ranges:
.a16
.i16
    lda.l DmaQueue_BudgetTotal
    clc
    adc #576
    cmp #DMA_TRANSFER_MAX_BYTES
    bcc SourceFastPose_G34
    brl SourceFastPose_Done
SourceFastPose_G34:
.a16
.i16
    ldx #0
    ldy #0
SourceFastPose_Queue:
.a16
.i16
    lda.l DmaQueue+4,x
    and #64
    bne SourceFastPose_QueueActive
    iny
    bra SourceFastPose_QueueNext
SourceFastPose_QueueActive:
.a16
.i16
    lda.l DmaQueue+4,x
    and #31
    cmp #1
    bne SourceFastPose_G35
    brl SourceFastPose_Done
SourceFastPose_G35:
.a16
.i16
    lda.l DmaQueue+7,x
    and #255
    cmp #$43
    bne SourceFastPose_G36
    brl SourceFastPose_Done
SourceFastPose_G36:
.a16
.i16
    cmp #$7E
    bne SourceFastPose_QueueNext
    lda.l DmaQueue,x
    cmp #0
    bne SourceFastPose_G37
    brl SourceFastPose_Done
SourceFastPose_G37:
.a16
.i16
    bra SourceFastPose_ShadowEnd
SourceFastPose_ShadowEnd:
.a16
.i16
    lda.l DmaQueue+5,x
    clc
    adc.l DmaQueue,x
    bcs SourceFastPose_ShadowBlocked
    cmp #$5101
    bcc SourceFastPose_QueueNext
    lda.l DmaQueue+5,x
    cmp #$53A0
    bcs SourceFastPose_QueueNext
SourceFastPose_ShadowBlocked:
.a16
.i16
    brl SourceFastPose_Done
SourceFastPose_QueueNext:
.a16
.i16
    txa
    clc
    adc #8
    tax
    cpx #64
    bcs SourceFastPose_QueueDone
    brl SourceFastPose_Queue
SourceFastPose_QueueDone:
.a16
.i16
    cpy #2
    bcs SourceFastPose_G39
    brl SourceFastPose_Done
SourceFastPose_G39:
.a16
.i16
    lda.l SourceVisual_State+6
    cmp #2
    bne SourceFastPose_PaletteNext0
    lda.l SourceVisual_State+28
    and #255
    bne SourceFastPose_PaletteNext0
    lda.l SourceVisual_State+16
    and #255
    beq SourceFastPose_PaletteNext0
    dec a
    cmp #8
    bcs SourceFastPose_PaletteNext0
    asl a
    asl a
    asl a
    tax
    lda.l SourceVisual_PaletteCache+3,x
    and #255
    cmp #1
    beq SourceFastPose_HasReadyPalette
SourceFastPose_PaletteNext0:
.a16
.i16
    lda.l SourceVisual_State+38
    cmp #2
    bne SourceFastPose_PaletteNext1
    lda.l SourceVisual_State+60
    and #255
    bne SourceFastPose_PaletteNext1
    lda.l SourceVisual_State+48
    and #255
    beq SourceFastPose_PaletteNext1
    dec a
    cmp #8
    bcs SourceFastPose_PaletteNext1
    asl a
    asl a
    asl a
    tax
    lda.l SourceVisual_PaletteCache+3,x
    and #255
    cmp #1
    beq SourceFastPose_HasReadyPalette
SourceFastPose_PaletteNext1:
.a16
.i16
    brl SourceFastPose_Done
SourceFastPose_HasReadyPalette:
.a16
.i16
    lda #0
    tcd
    sep #$20
.a8
    pha
    plb
    rep #$30
.a16
.i16
    lda #1
    sta.l SourcePacket_CopyBusy
    jsl SourceFastPose_Bridge_SourceVisual_CompletedObserve
    lda.l SourceVisual_CompletedAwait
    beq SourceFastPose_G40
    brl SourceFastPose_Unlock
SourceFastPose_G40:
.a16
.i16
    lda.l SourceVisual_CompletedPending
    beq SourceFastPose_G41
    brl SourceFastPose_Unlock
SourceFastPose_G41:
.a16
.i16
    lda.l SourceVisual_CompletedRetire
    beq SourceFastPose_G42
    brl SourceFastPose_Unlock
SourceFastPose_G42:
.a16
.i16
    lda.l SVActor_Await
    beq SourceFastPose_G43
    brl SourceFastPose_Unlock
SourceFastPose_G43:
.a16
.i16
    lda.l SVActor_Pending
    beq SourceFastPose_G44
    brl SourceFastPose_Unlock
SourceFastPose_G44:
.a16
.i16
    jsr SourceFastPose_Coherent
    bcs SourceFastPose_SeqValid
    brl SourceFastPose_Unlock
SourceFastPose_SeqValid:
.a16
.i16
    lda.l $434E7C
    sta.l SourceFastPose_Seq
    lda.l SourceVisual_CompletedEarly
    sta.l SourceFastPose_OldEarly
    lda.l Oam_HighWaterSlot
    sta.l SourceFastPose_OldHigh
    lda.l Oam_NeedFullUpload
    sta.l SourceFastPose_OldNeed
    lda.l Oam_CurrentSlot
    sta.l SourceFastPose_OldCursor
    lda.l SourcePacket_ThisFrame
    sta.l SourceFastPose_OldThis
    lda.l SourceVisual_ServiceOnly
    sta.l SourceFastPose_OldService
    lda #0
    sta.l SourceVisual_CompletedEarly
    sta.l SourceVisual_ServiceOnly
    sta.l SourceFastPose_Changed
    jsl SourceVisual_CompletedOamBegin
    phb
SourceFastPose_SaveShadowLoop:
.a16
.i16
    ldx #(Oam_Buffer&$FFFF)
    ldy #(SourceFastPose_SaveShadow&$FFFF)
    lda #671
    mvn $43,$7E
    plb
    phb
SourceFastPose_SaveBuildLoop:
.a16
.i16
    ldx #(SOURCE_PACKET_BUILD_META&$FFFF)
    ldy #(SourceFastPose_SaveBuild&$FFFF)
    lda #63
    mvn $43,$43
    plb
    phb
SourceFastPose_SaveNpcLoop:
.a16
.i16
    ldx #(SourceNpc_Build&$FFFF)
    ldy #(SourceFastPose_SaveNpc&$FFFF)
    lda #127
    mvn $43,$43
    plb
    phb
SourceFastPose_BaseLoop:
.a16
.i16
    ldx #(SOURCE_PACKET_BASE&$FFFF)
    ldy #(Oam_Buffer&$FFFF)
    lda #543
    mvn $7E,$43
    plb
    phb
SourceFastPose_MetaLoop:
.a16
.i16
    ldx #(SOURCE_PACKET_ACTIVE_META&$FFFF)
    ldy #(SOURCE_PACKET_BUILD_META&$FFFF)
    lda #63
    mvn $43,$43
    plb
    phb
SourceFastPose_NpcLoop:
.a16
.i16
    ldx #(SourceNpc_Active&$FFFF)
    ldy #(SourceNpc_Build&$FFFF)
    lda #127
    mvn $43,$43
    plb
    ldx #0
    ldy #0
SourceFastPose_Unpack:
.a16
.i16
    lda.l SOURCE_PACKET_BASE+512,x
    sta.l SourceFastPose_Temp
    lda.l SourceFastPose_Temp
    and #3
    sep #$20
.a8
    phx
    tyx
    sta.l Oam_ExpandedHi,x
    plx
    rep #$30
.a16
.i16
    iny
    lda.l SourceFastPose_Temp
    lsr a
    lsr a
    sta.l SourceFastPose_Temp
    lda.l SourceFastPose_Temp
    and #3
    sep #$20
.a8
    phx
    tyx
    sta.l Oam_ExpandedHi,x
    plx
    rep #$30
.a16
.i16
    iny
    lda.l SourceFastPose_Temp
    lsr a
    lsr a
    sta.l SourceFastPose_Temp
    lda.l SourceFastPose_Temp
    and #3
    sep #$20
.a8
    phx
    tyx
    sta.l Oam_ExpandedHi,x
    plx
    rep #$30
.a16
.i16
    iny
    lda.l SourceFastPose_Temp
    lsr a
    lsr a
    sta.l SourceFastPose_Temp
    lda.l SourceFastPose_Temp
    and #3
    sep #$20
.a8
    phx
    tyx
    sta.l Oam_ExpandedHi,x
    plx
    rep #$30
.a16
.i16
    iny
    lda.l SourceFastPose_Temp
    lsr a
    lsr a
    sta.l SourceFastPose_Temp
    inx
    cpx #32
    bcs SourceFastPose_Unpacked
    brl SourceFastPose_Unpack
SourceFastPose_Unpacked:
.a16
.i16
    lda #0
    sta.l SourceFastPose_Slot
SourceFastPose_Slots:
.a16
.i16
    jsr SourceFastPose_TrySlot
    lda.l SourceFastPose_Slot
    inc a
    sta.l SourceFastPose_Slot
    cmp #2
    bcc SourceFastPose_Slots
    lda #0
    tcd ; the normal whole-scene submit has bank-zero DP, not actor DP
    lda.l SourceFastPose_Changed
    beq SourceFastPose_Restore
    lda #512
    sta.l Oam_CurrentSlot
    lda #1
    sta.l Oam_NeedFullUpload
    jsl SourceVisual_CompletedSubmit
SourceFastPose_Restore:
.a16
.i16
    phb
SourceFastPose_RestoreShadow:
.a16
.i16
    ldx #(SourceFastPose_SaveShadow&$FFFF)
    ldy #(Oam_Buffer&$FFFF)
    lda #671
    mvn $7E,$43
    plb
    phb
SourceFastPose_RestoreBuild:
.a16
.i16
    ldx #(SourceFastPose_SaveBuild&$FFFF)
    ldy #(SOURCE_PACKET_BUILD_META&$FFFF)
    lda #63
    mvn $43,$43
    plb
    phb
SourceFastPose_RestoreNpc:
.a16
.i16
    ldx #(SourceFastPose_SaveNpc&$FFFF)
    ldy #(SourceNpc_Build&$FFFF)
    lda #127
    mvn $43,$43
    plb
    lda.l SourceFastPose_OldCursor
    sta.l Oam_CurrentSlot
    lda.l SourceFastPose_OldHigh
    sta.l Oam_HighWaterSlot
    lda.l SourceFastPose_OldNeed
    sta.l Oam_NeedFullUpload
    jsl SourceVisual_CompletedOamEnd
    lda.l SourceFastPose_OldEarly
    sta.l SourceVisual_CompletedEarly
    lda.l SourceFastPose_OldThis
    sta.l SourcePacket_ThisFrame
    lda.l SourceFastPose_OldService
    sta.l SourceVisual_ServiceOnly
SourceFastPose_Unlock:
.a16
.i16
    lda #0
    sta.l SourcePacket_CopyBusy
SourceFastPose_Done:
.a16
.i16
    pld
    plb
    ply
    plx
    pla
    plp
    rtl

SourceFastPose_TrySlot:
.a16
.i16
    lda.l SourceFastPose_Slot
    asl a
    tax
    lda.l SourceFastPose_Natives,x
    sta.l SourceFastPose_Native
    lda.l $434E9C,x
    cmp.l SourceFastPose_Native
    beq SourceFastPose_BoundPlayer
    brl SourceFastPose_SlotNo
SourceFastPose_BoundPlayer:
.a16
.i16
    lda.l SourceFastPose_Native
    clc
    adc #$0A00
    tcd
    lda.l SourceFastPose_Metas,x
    sta.l SourceFastPose_Meta
    sta.l SourceVisual_Record
    lda.l SourceFastPose_Raws,x
    sta.l SourceFastPose_Raw
    lda.l SourceFastPose_Slot
    sta.l SourceVisual_ActorSlot
    lda.l SourceFastPose_Meta
    tax
    lda.l SourceVisual_State+6,x
    cmp #2
    beq SourceFastPose_G45
    brl SourceFastPose_SlotNo
SourceFastPose_G45:
.a16
.i16
    lda.l SourceVisual_State+28,x
    and #255
    beq SourceFastPose_G46
    brl SourceFastPose_SlotNo
SourceFastPose_G46:
.a16
.i16
    lda.l SourceVisual_State+29,x
    and #255
    cmp #22
    beq SourceFastPose_G47
    brl SourceFastPose_SlotNo
SourceFastPose_G47:
.a16
.i16
    lda.l SourceVisual_State+30,x
    and #255
    cmp #3
    bcc SourceFastPose_G48
    brl SourceFastPose_SlotNo
SourceFastPose_G48:
.a16
.i16
    lda.l SourceFastPose_Native
    tax
    lda.l $7E0A00+CHAR_HP,x
    and #255
    cmp #0
    bne SourceFastPose_G49
    brl SourceFastPose_SlotNo
SourceFastPose_G49:
.a16
.i16
    lda.l $7E0A00+CHAR_INPUT_DRIVEN,x
    and #255
    cmp #1
    beq SourceFastPose_G50
    brl SourceFastPose_SlotNo
SourceFastPose_G50:
.a16
.i16
    lda.l $7E0A00+CHAR_ROSTER_INDEX,x
    and #255
    cmp #22
    beq SourceFastPose_G51
    brl SourceFastPose_SlotNo
SourceFastPose_G51:
.a16
.i16
    lda.l $7E0A00+CHAR_MAP_INDEX,x
    and #255
    cmp #0
    beq SourceFastPose_G52
    brl SourceFastPose_SlotNo
SourceFastPose_G52:
.a16
.i16
    lda.l $7E0A00+CHAR_SELECTED,x
    and #255
    cmp #3
    bcc SourceFastPose_G53
    brl SourceFastPose_SlotNo
SourceFastPose_G53:
.a16
.i16
    lda.l SourceVisual_Sa1OwnerPolicy,x
    and #255
    cmp #2
    beq SourceFastPose_OwnerPolicy
    brl SourceFastPose_SlotNo
SourceFastPose_OwnerPolicy:
.a16
.i16
    lda.l SourceVisual_Sa1RuntimeRole,x
    and #255
    sta.l SourceFastPose_Temp
    lda.l SourceFastPose_Meta
    tax
    lda.l SourceVisual_State+30,x
    and #255
    cmp.l SourceFastPose_Temp
    beq SourceFastPose_G54
    brl SourceFastPose_SlotNo
SourceFastPose_G54:
.a16
.i16
    lda.l SourceFastPose_Slot
    asl a
    tax
    lda.l SourceFastPose_Motions,x
    tax
    lda.l $434E00+12,x
    cmp #1
    beq SourceFastPose_MotionActive
    brl SourceFastPose_SlotNo
SourceFastPose_MotionActive:
.a16
.i16
    lda.l $434E00+14,x
    beq SourceFastPose_MotionMap
    brl SourceFastPose_SlotNo
SourceFastPose_MotionMap:
.a16
.i16
    lda.l $434E00+22,x
    and #255
    cmp #2
    beq SourceFastPose_MotionOwner
    brl SourceFastPose_SlotNo
SourceFastPose_MotionOwner:
.a16
.i16
    lda.l $434E00+4,x
    beq SourceFastPose_GroundHeight
    brl SourceFastPose_SlotNo
SourceFastPose_GroundHeight:
.a16
.i16
    lda.l $434E00+16,x
    beq SourceFastPose_DeadSource
    cmp #256
    bcc SourceFastPose_SourceAlive
SourceFastPose_DeadSource:
.a16
.i16
    brl SourceFastPose_SlotNo
SourceFastPose_SourceAlive:
.a16
.i16
    lda.l $434E00+28,x
    cmp.l SourceFastPose_Temp
    beq SourceFastPose_G55
    brl SourceFastPose_SlotNo
SourceFastPose_G55:
.a16
.i16
    lda.l $434E7C
    cmp.l SourceFastPose_Seq
    beq SourceFastPose_G56
    brl SourceFastPose_SlotNo
SourceFastPose_G56:
.a16
.i16
    lda.l SourceFastPose_Raw
    tax
    lda.l SVActor_MetaData+SVActor_MetaValid,x
    cmp #1
    beq SourceFastPose_G57
    brl SourceFastPose_SlotNo
SourceFastPose_G57:
.a16
.i16
    lda.l SVActor_MetaData+SVActor_MetaStage,x
    beq SourceFastPose_G58
    brl SourceFastPose_SlotNo
SourceFastPose_G58:
.a16
.i16
    lda.l SVActor_MetaData,x
    sta.l SourceVisual_EntryIndexSaved
    lda.l SourceFastPose_Meta
    tay
    phx
    tyx
    lda.l SourceVisual_State,x
    plx
    cmp.l SourceVisual_EntryIndexSaved
    beq SourceFastPose_G59
    brl SourceFastPose_SlotNo
SourceFastPose_G59:
.a16
.i16
    lda.l SVActor_MetaData+2,x
    cmp #0
    bne SourceFastPose_G60
    brl SourceFastPose_SlotNo
SourceFastPose_G60:
.a16
.i16
    cmp #66
    bcc SourceFastPose_G61
    brl SourceFastPose_SlotNo
SourceFastPose_G61:
.a16
.i16
    sta.l SourceVisual_PieceCount
    asl a
    asl a
    sta.l SourceFastPose_Temp
    lda.l SourceFastPose_Meta
    tax
    lda.l SOURCE_PACKET_ACTIVE_META,x
    sta.l SourceFastPose_Begin
    lda.l SOURCE_PACKET_ACTIVE_META+2,x
    sta.l SourceFastPose_End
    sec
    sbc.l SourceFastPose_Begin
    cmp.l SourceFastPose_Temp
    bcs SourceFastPose_G62
    brl SourceFastPose_SlotNo
SourceFastPose_G62:
.a16
.i16
    lda.l SourceFastPose_Raw
    tax
    ldy #0
SourceFastPose_Header:
.a16
.i16
    lda.l SVActor_MetaData+4,x
    phx
    tyx
    sta.l SourceVisual_EntryScratch,x
    plx
    inx
    inx
    iny
    iny
    cpy #24
    bcc SourceFastPose_Header
    lda.l SourceVisual_EntryScratch
    sta.l SourceVisual_Key
    sta.l SourceVisual_KeySaved
    lda.l SourceVisual_EntryScratch+2
    sta.l SourceVisual_Key+2
    sta.l SourceVisual_KeySaved+2
    and #$FF00
    beq SourceFastPose_G63
    brl SourceFastPose_SlotNo
SourceFastPose_G63:
.a16
.i16
    lda.l SourceVisual_EntryScratch+12
    and #255
    cmp.l SourceVisual_PieceCount
    beq SourceFastPose_G64
    brl SourceFastPose_SlotNo
SourceFastPose_G64:
.a16
.i16
    lda.l SourceFastPose_Meta
    tax
    lda.l SourceVisual_State+29,x
    and #$FFFF
    cmp.l SourceVisual_Key
    beq SourceFastPose_G65
    brl SourceFastPose_SlotNo
SourceFastPose_G65:
.a16
.i16
    lda.l SourceVisual_Key+1
    and #255
    asl a
    tax
    lda.l SourceVisual_Key+2
    and #255
    cmp.l SourceFastPose_FrameLimits,x
    bcc SourceFastPose_FrameBounded
    brl SourceFastPose_SlotNo
SourceFastPose_FrameBounded:
.a16
.i16
    asl a
    clc
    adc.l SourceFastPose_EntryBases,x
    cmp.l SourceVisual_EntryIndexSaved
    beq SourceFastPose_EntryBounded
    brl SourceFastPose_SlotNo
SourceFastPose_EntryBounded:
.a16
.i16
    jsl SourceCritical_Bridge_ReadIdlePieces
    jsl SourceFastPose_Bridge_SVActor_ReadyLease
    bcs SourceFastPose_ReadyValidated
    brl SourceFastPose_SlotNo
SourceFastPose_ReadyValidated:
.a16
.i16
    jsr SourceFastPose_PhysicalFence
    bcs SourceFastPose_PhysicalReady
    brl SourceFastPose_SlotNo
SourceFastPose_PhysicalReady:
.a16
.i16
    jsl SourceFastPose_Bridge_SourceVisual_CompletedCanPublish
    bcs SourceFastPose_CanCapture
    brl SourceFastPose_SlotNo
SourceFastPose_CanCapture:
.a16
.i16
    lda.l $434E7E
    cmp #$4D50
    beq SourceFastPose_FinalMagic
    brl SourceFastPose_SlotNo
SourceFastPose_FinalMagic:
.a16
.i16
    lda.l $434E7C
    cmp.l SourceFastPose_Seq
    beq SourceFastPose_FinalSeq
    brl SourceFastPose_SlotNo
SourceFastPose_FinalSeq:
.a16
.i16
    lda.l SourceFastPose_Begin
    sta.l Oam_CurrentSlot
    jsl SourceFastPose_Bridge_SourceVisual_Emit
    bcs SourceFastPose_Emitted
    brl SourceFastPose_RestoreSlot
SourceFastPose_Emitted:
.a16
.i16
    lda.l Oam_CurrentSlot
    cmp.l SourceFastPose_Begin
    bne SourceFastPose_HasRows
    brl SourceFastPose_RestoreSlot
SourceFastPose_HasRows:
.a16
.i16
    lda.l Oam_CurrentSlot
    tax
SourceFastPose_HideTail:
.a16
.i16
    txa
    cmp.l SourceFastPose_End
    bcs SourceFastPose_TailHidden
    lda #(OAM_DEFAULT_Y*256+OAM_HIDDEN_X)
    sta.l Oam_Buffer,x
    lda #0
    sta.l Oam_Buffer+2,x
    phx
    txa
    lsr a
    lsr a
    tax
    sep #$20
.a8
    lda #1
    sta.l Oam_ExpandedHi,x
    rep #$30
.a16
.i16
    plx
    txa
    clc
    adc #4
    tax
    bra SourceFastPose_HideTail
SourceFastPose_TailHidden:
.a16
.i16
    jsl SourceFastPose_Bridge_SourceVisual_CompletedCapture
    lda.l SourceFastPose_Meta
    tax
    sep #$20
.a8
    lda #1
    sta.l SourceVisual_State+28,x
    rep #$30
.a16
.i16
    lda #1
    sta.l SourceFastPose_Changed
SourceFastPose_SlotNo:
.a16
.i16
    rts

; An emission failure cannot leak partial rows into the other player's commit.
SourceFastPose_RestoreSlot:
.a16
.i16
    lda.l SourceFastPose_Begin
    tax
SourceFastPose_RestoreSlotLoop:
.a16
.i16
    lda.l SOURCE_PACKET_BASE,x
    sta.l Oam_Buffer,x
    lda.l SOURCE_PACKET_BASE+2,x
    sta.l Oam_Buffer+2,x
    phx
    txa
    lsr a
    lsr a
    tay
    and #3
    sta.l SourceFastPose_Shift
    tya
    lsr a
    lsr a
    tax
    lda.l SOURCE_PACKET_BASE+512,x
    sta.l SourceFastPose_Temp
SourceFastPose_ShiftLoop:
.a16
.i16
    lda.l SourceFastPose_Shift
    beq SourceFastPose_ShiftDone
    dec a
    sta.l SourceFastPose_Shift
    lda.l SourceFastPose_Temp
    lsr a
    lsr a
    sta.l SourceFastPose_Temp
    bra SourceFastPose_ShiftLoop
SourceFastPose_ShiftDone:
.a16
.i16
    lda.l SourceFastPose_Temp
    and #3
    sep #$20
.a8
    phx
    tyx
    sta.l Oam_ExpandedHi,x
    plx
    rep #$30
.a16
.i16
    plx
    txa
    clc
    adc #4
    tax
    cmp.l SourceFastPose_End
    bcs SourceFastPose_RestoreSlotRowsDone
    brl SourceFastPose_RestoreSlotLoop
SourceFastPose_RestoreSlotRowsDone:
.a16
.i16
    lda.l SourceFastPose_Meta
    tax
    ldy #0
SourceFastPose_RestoreSlotMeta:
.a16
.i16
    lda.l SOURCE_PACKET_ACTIVE_META,x
    sta.l SOURCE_PACKET_BUILD_META,x
    inx
    inx
    iny
    iny
    cpy #32
    bcc SourceFastPose_RestoreSlotMeta
    rts
SourceFastPose_Natives:
    .dw 0,133
SourceFastPose_Metas:
    .dw 0,32
SourceFastPose_Raws:
    .dw 0,1280
SourceFastPose_Motions:
    .dw 52,88
SourceFastPose_PhysicalFence:
.a16
.i16
    jsl SourcePalette_Bridge_SourceRom_HasPaletteDma
    bcc SourceFastPose_NoPaletteDma
    clc
    rts
SourceFastPose_NoPaletteDma:
.a16
.i16
    lda #0
    sta.l SourceVisual_PieceIndex
SourceFastPose_FencePiece:
.a16
.i16
    lda.l SourceVisual_PieceIndex
    cmp.l SourceVisual_PieceCount
    bcc SourceFastPose_FencePresent
    sec
    rts
SourceFastPose_FencePresent:
.a16
.i16
    clc
    adc.l SourceVisual_ActorMapBase
    tax
    lda.l SourceVisual_ActorPieceMap,x
    and #255
    asl a
    asl a
    asl a
    tax
    lda.l SourceVisual_BlockCache+5,x
    and #255
    cmp #4
    bne SourceFastPose_FenceNo
    lda.l SourceVisual_BlockCache+6,x
    and #255
    cmp #2
    beq SourceFastPose_FenceRom
    cmp #1
    bne SourceFastPose_FenceNo
    jsl SourceCritical_Bridge_SourceRom_HasStagingDma
    bcs SourceFastPose_FenceNo
    bra SourceFastPose_FenceNext
SourceFastPose_FenceRom:
.a16
.i16
    lda.l SourceVisual_PieceIndex
    asl a
    asl a
    asl a
    asl a
    tax
    lda.l SourceVisual_PieceTable+12,x
    sta.l SourceVisual_BlockIndex
    jsl SourceCritical_Bridge_SourceRom_ResolveTagged
    bcc SourceFastPose_FenceNo
    jsl SourceCritical_Bridge_SourceRom_HasBlockDma
    bcs SourceFastPose_FenceNo
SourceFastPose_FenceNext:
.a16
.i16
    lda.l SourceVisual_PieceIndex
    inc a
    sta.l SourceVisual_PieceIndex
    brl SourceFastPose_FencePiece
SourceFastPose_FenceNo:
.a16
.i16
    clc
    rts
SourceFastPose_EntryBases:
    .dw 923,1043,781
SourceFastPose_FrameLimits:
    .dw 18,10,6
; Foreground only. Bound a publication already in progress; never accept odd/torn rows.
SourceFastPose_Coherent:
.a16
.i16
    ldy #64
SourceFastPose_CoherentPoll:
.a16
.i16
    lda.l $434E7E
    cmp #$4D50
    bne SourceFastPose_CoherentNext
    lda.l $434E7C
    and #1
    beq SourceFastPose_CoherentYes
SourceFastPose_CoherentNext:
.a16
.i16
    dey
    bne SourceFastPose_CoherentPoll
    clc
    rts
SourceFastPose_CoherentYes:
.a16
.i16
    sec
    rts
SourceFastPose_EndCode:
