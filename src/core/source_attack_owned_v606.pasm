SourceAttackOwned_Motion = $437B40
SourceAttackOwned_ReadSeq = $437B60
SourceAttackOwned_ReadStage = $437B62
; Paired attack-0 early scene. Independent full544 image and pending state.
; The ordinary NMI publisher remains the only beam/queue/DMA authority.
SourceAttackOwned_Image = $437600
SourceAttackOwned_High = $437820
SourceAttackOwned_InitMagic = $437A60
SourceAttackOwned_Busy = $437A62
SourceAttackOwned_State = $437A64 ; 0 absent, 1 ready, 2 physically published
SourceAttackOwned_GenLow = $437A66
SourceAttackOwned_GenHigh = $437A68
SourceAttackOwned_Camera = $437A6A
SourceAttackOwned_Hold = $437A6C
SourceAttackOwned_Ack = $437A6E
SourceAttackOwned_PhysicalLow = $437A70
SourceAttackOwned_PhysicalHigh = $437A72
SourceAttackOwned_Use = $437A74
SourceAttackOwned_SourceHi = $437A76
SourceAttackOwned_SavedPending = $437A78
SourceAttackOwned_Suppressed = $437A7A
SourceAttackOwned_Delta0 = $437A7C
SourceAttackOwned_Delta1 = $437A7E
SourceAttackOwned_Work = $437A80
SourceAttackOwned_HighBit = $437A82
SourceAttackOwned_PhysicalAcks = $437A84
SourceAttackOwned_Stages = $437A86
SourceAttackOwned_Rejects = $437A88
SourceAttackOwned_LatePhase = $437A8A
SourceAttackOwned_AckField = $437A8C
SourceAttackOwned_ReadY0 = $437A8E
SourceAttackOwned_ReadY1 = $437A90
SourceAttackOwned_NewDelta0 = $437A92
SourceAttackOwned_NewDelta1 = $437A94
SourceAttackOwned_Init:
.a16
.i16
    jsl SourcePrefetch_Init
    php
    rep #$30
    pha
    phx
    phy
    phb
    phd
    cld
    lda #0
    ldx #0
SourceAttackOwned_InitLoop:
.a16
.i16
    sta.l SourceAttackOwned_InitMagic,x
    inx
    inx
    cpx #54
    bcc SourceAttackOwned_InitLoop
    sta.l SourceAttackTemplate_Base
    sta.l SourceAttackTemplate_Base+128
    sta.l $437A96
    sta.l $437A98
    sta.l $437A9A
    sta.l $437A9C
    sta.l $437A9E
    sta.l $437B3C
    lda #$B077
    jsl SourceStandby_Init
    lda #$4F
    sta.l SourceAttackOwned_SourceHi
    pld
    plb
    ply
    plx
    pla
    plp
    rtl
SourceAttackOwned_Queued:
.a16
.i16
    jsl SourceNextScene_Queued
    jml SourceAttackOwned_Snapshot
SourceAttackOwned_Snapshot:
.a16
.i16
    php
    rep #$30
    pha
    phx
    phy
    phb
    phd
    cld
    lda.l SourceAttackOwned_InitMagic
    cmp #$B077
    beq SourceAttackOwned_G1
    brl SourceAttackOwned_Done
SourceAttackOwned_G1:
.a16
.i16
    lda.l SourcePacket_CopyBusy
    beq SourceAttackOwned_G2
    brl SourceAttackOwned_Done
SourceAttackOwned_G2:
.a16
.i16
    lda.l SourcePacket_ActiveValid
    cmp #1
    beq SourceAttackOwned_G3
    brl SourceAttackOwned_Done
SourceAttackOwned_G3:
.a16
.i16
    lda.l Game_StageIndex
    beq SourceAttackOwned_G4
    brl SourceAttackOwned_Done
SourceAttackOwned_G4:
.a16
.i16
    jsl SourceAttackMask_Reset
SourceAttackMask_CanSnapshot:
.a16
.i16
    jsl SourceAttackMask_Ready
    bne SourceAttackMask_HaveReady
    brl SourceAttackOwned_Done
SourceAttackMask_HaveReady:
.a16
.i16
    sta.l $437A9C
    lda.l $437A98
    beq SourceAttackJoint_CanSnapshot
    and.l $437A9C
    bne SourceAttackJoint_RejectSnapshot
    lda.l SourceAttackOwned_Hold
    cmp #1
    bne SourceAttackJoint_RejectSnapshot
    jsl SourceAttackMask_PhysicalLive
    bcc SourceAttackJoint_RejectSnapshot
    lda.l SourceNextScene_Low
    cmp.l SourceAttackOwned_PhysicalLow
    bne SourceAttackJoint_RejectSnapshot
    lda.l SourceNextScene_High
    cmp.l SourceAttackOwned_PhysicalHigh
    beq SourceAttackJoint_CanSnapshot
SourceAttackJoint_RejectSnapshot:
.a16
.i16
    brl SourceAttackOwned_Done
SourceAttackJoint_CanSnapshot:
.a16
.i16
    lda.l $437A9C
    cmp #3
    beq SourceAttackOwned_G19
    jsl SourceLayout_FirstEnd
    cmp #40
    beq SourceAttackOwned_G19
    brl SourceAttackOwned_Done
SourceAttackOwned_G19:
.a16
.i16
    lda.l SOURCE_PACKET_ACTIVE_META
    beq SourceAttackOwned_G20
    brl SourceAttackOwned_Done
SourceAttackOwned_G20:
.a16
.i16
    lda.l SOURCE_PACKET_ACTIVE_META+2
    cmp.l SOURCE_PACKET_ACTIVE_META+32
    beq SourceAttackOwned_G21
    brl SourceAttackOwned_Done
SourceAttackOwned_G21:
.a16
.i16
    lda.l SOURCE_PACKET_ACTIVE_META+2
    cmp #4
    bcs SourceAttackOwned_G22
    brl SourceAttackOwned_Done
SourceAttackOwned_G22:
.a16
.i16
    lda.l SOURCE_PACKET_ACTIVE_META+2
    cmp #77
    bcc SourceAttackOwned_G23
    brl SourceAttackOwned_Done
SourceAttackOwned_G23:
.a16
.i16
    lda.l SOURCE_PACKET_ACTIVE_META+2
    and #3
    beq SourceAttackOwned_G24
    brl SourceAttackOwned_Done
SourceAttackOwned_G24:
.a16
.i16
    lda.l SOURCE_PACKET_ACTIVE_META+34
    jml SourceShape_Gate
    nop
    nop
    nop
    nop
SourceAttackOwned_G25:
.a16
.i16
    lda.l SOURCE_PACKET_ACTIVE_META+16
    cmp #1
    beq SourceAttackOwned_G26
    brl SourceAttackOwned_Done
SourceAttackOwned_G26:
.a16
.i16
    lda.l SOURCE_PACKET_ACTIVE_META+8
    cmp #22
    beq SourceAttackOwned_G27
    brl SourceAttackOwned_Done
SourceAttackOwned_G27:
.a16
.i16
    lda.l SOURCE_PACKET_ACTIVE_META+10
    beq SourceAttackOwned_G28
    brl SourceAttackOwned_Done
SourceAttackOwned_G28:
.a16
.i16
    jsl SourceFacing_Meta0
    beq SourceAttackOwned_G29
    brl SourceAttackOwned_Done
SourceAttackOwned_G29:
.a16
.i16
    lda.l SOURCE_PACKET_ACTIVE_META+48
    cmp #1
    beq SourceAttackOwned_G30
    brl SourceAttackOwned_Done
SourceAttackOwned_G30:
.a16
.i16
    lda.l SOURCE_PACKET_ACTIVE_META+40
    cmp #22
    beq SourceAttackOwned_G31
    brl SourceAttackOwned_Done
SourceAttackOwned_G31:
.a16
.i16
    lda.l SOURCE_PACKET_ACTIVE_META+42
    beq SourceAttackOwned_G32
    brl SourceAttackOwned_Done
SourceAttackOwned_G32:
.a16
.i16
    jsl SourceFacing_Meta1
    beq SourceAttackOwned_G33
    brl SourceAttackOwned_Done
SourceAttackOwned_G33:
.a16
.i16
    lda.l SOURCE_PACKET_ACTIVE_META+12
    cmp #$0216
    bne SourceAttackOwned_NeedSnapshot
    lda.l SOURCE_PACKET_ACTIVE_META+44
    cmp #$0216
    bne SourceAttackOwned_NeedSnapshot
    brl SourceAttackOwned_Done
SourceAttackOwned_NeedSnapshot:
.a16
.i16
    lda #1
    sta.l SourceAttackOwned_Busy
    sta.l SourcePacket_CopyBusy
    lda #0
    sta.l SourceAttackOwned_State
    lda.l SourceNextScene_Low
    sta.l SourceAttackOwned_GenLow
    lda.l SourceNextScene_High
    sta.l SourceAttackOwned_GenHigh
    lda.l Screen_PosX
    sta.l SourceAttackOwned_Camera
    lda.l SourceAttackOwned_Hold
    beq SourceAttackMask_NewBase
    lda.l SourceNextScene_Low
    cmp.l SourceAttackOwned_PhysicalLow
    bne SourceAttackMask_NewBase
    lda.l SourceNextScene_High
    cmp.l SourceAttackOwned_PhysicalHigh
    bne SourceAttackMask_NewBase
    lda.l $437A9A
    ora.l $437A9C
    sta.l $437B38
    bra SourceAttackMask_BaseReady
SourceAttackMask_NewBase:
.a16
.i16
    lda.l $437A9C
    sta.l $437B38
    jsl SourceLayout_CopyBase
    nop
    nop
    nop
    nop
    nop
    nop
    nop
    nop
SourceAttackMask_BaseReady:
.a16
.i16
    jsl SourceAttackMask_SeedHigh
    lda #0
    sta.l SourcePacket_CopyBusy
    sta.l SourceAttackOwned_Busy
    ; State3 means the private base awaits its one bounded NMI patch.
    lda #3
    sta.l SourceAttackOwned_State
    ; Prepare against the current coherent seal before the next NMI deadline.
    jsl SourceAttackOwned_PatchNow
    brl SourceAttackOwned_Done
SourceAttackOwned_Prepare:
.a16
.i16
    php
    rep #$30
    pha
    lda.l SourceAttackOwned_InitMagic
    cmp #$B077
    bne SourceAttackOwned_FastPrepareDone
    lda.l SourceAttackOwned_State
    ora.l SourceAttackOwned_Hold
    ora.l SourceAttackOwned_Suppressed
    bne SourceAttackOwned_FullPrepare
SourceAttackOwned_FastPrepareDone:
.a16
.i16
    pla
    plp
    jml SourcePacket_NmiPrepare
SourceAttackOwned_FullPrepare:
.a16
.i16
    pla
    plp
    jsl SourcePacket_NmiPrepare
SourceAttackOwned_PatchNow:
.a16
.i16
    php
    rep #$30
    pha
    phx
    phy
    phb
    phd
    cld
    jsl SourceAttackOwned_Collect
    lda.l SourceAttackOwned_InitMagic
    cmp #$B077
    beq SourceAttackOwned_G34
    brl SourceAttackOwned_Done
SourceAttackOwned_G34:
.a16
.i16
    lda.l SourceAttackOwned_State
    cmp #3
    beq SourceAttackOwned_PrepareState
    cmp #1
    beq SourceAttackOwned_PrepareState
    cmp #2
    bne SourceAttackOwned_PrepareNo
    lda.l SourceAttackOwned_Hold
    cmp #1
    bne SourceAttackOwned_PrepareNo
    lda.l $437A98
    bne SourceAttackOwned_PrepareNo
    lda.l StageTimer_FieldCounter
    cmp.l SourceAttackOwned_AckField
    bne SourceAttackOwned_PrepareState
SourceAttackOwned_PrepareNo:
.a16
.i16
    brl SourceAttackOwned_Done
SourceAttackOwned_PrepareState:
.a16
.i16
    lda.l SourceAttackOwned_Busy
    beq SourceAttackOwned_G35
    brl SourceAttackOwned_Done
SourceAttackOwned_G35:
.a16
.i16
    lda.l SourcePacket_CopyBusy
    beq SourceAttackOwned_G36
    brl SourceAttackOwned_Done
SourceAttackOwned_G36:
.a16
.i16
    lda.l $437B3C
    cmp #$A55E
    bne SourceAttackMask_SealNo
    lda.l $437B3A
    cmp.l StageTimer_FieldCounter
    bne SourceAttackMask_SealNo
    lda.l SourceAttackOwned_ReadStage
    cmp.l Game_StageIndex
    beq SourceAttackOwned_G37
SourceAttackMask_SealNo:
.a16
.i16
    brl SourceAttackOwned_Done
SourceAttackOwned_G37:
.a16
.i16
    lda.l SourceAttackOwned_ReadSeq
    bra SourceAttackOwned_SealedSeq
SourceAttackOwned_G38:
.a16
.i16
    lda.l SourceAttackOwned_ReadSeq
SourceAttackOwned_SealedSeq:
.a16
.i16
    and #1
    beq SourceAttackOwned_G39
    brl SourceAttackOwned_Done
SourceAttackOwned_G39:
.a16
.i16
    lda.l SourceNextScene_Magic
    cmp #$5343
    beq SourceAttackOwned_G40
    brl SourceAttackOwned_Done
SourceAttackOwned_G40:
.a16
.i16
    lda.l SourceNextScene_Low
    cmp.l SourceAttackOwned_GenLow
    beq SourceAttackOwned_G41
    brl SourceAttackOwned_Done
SourceAttackOwned_G41:
.a16
.i16
    lda.l SourceNextScene_High
    cmp.l SourceAttackOwned_GenHigh
    beq SourceAttackOwned_G42
    brl SourceAttackOwned_Done
SourceAttackOwned_G42:
.a16
.i16
    lda.l SourceAttackOwned_Camera
    cmp.l Screen_PosX
    beq SourceAttackOwned_G43
    brl SourceAttackOwned_Done
SourceAttackOwned_G43:
.a16
.i16
    jsl SourceAttackMask_Motion
    bcs SourceAttackOwned_G57
    brl SourceAttackOwned_Done
SourceAttackOwned_G57:
.a16
.i16
    lda.l SourceAttackOwned_Motion+14
    sta.l SourceAttackOwned_ReadY0
    lda.l SourceAttackOwned_Motion+30
    sta.l SourceAttackOwned_ReadY1
SourceAttackOwned_G58:
.a16
.i16
    lda.l SourceAttackOwned_Delta0
    sta.l SourceAttackOwned_NewDelta0
    lda.l SourceAttackOwned_Delta1
    sta.l SourceAttackOwned_NewDelta1
    lda.l $437A9C
    and #1
    bne SourceAttackMask_ProjectP1
    brl SourceAttackMask_ProjectP2Check
SourceAttackMask_ProjectP1:
.a16
.i16
    lda.l SourceAttackOwned_ReadY0
    jsl SourceAttackOwned_ProjectX
    bcs SourceAttackOwned_G59
    brl SourceAttackOwned_Done
SourceAttackOwned_G59:
.a16
.i16
    cmp.l SourceAttackTemplate_Base+16
    beq SourceAttackOwned_G60
    brl SourceAttackOwned_Done
SourceAttackOwned_G60:
.a16
.i16
    lda.l SourceAttackOwned_Motion+0
    jsl SourceAttackOwned_ProjectX
    bcs SourceAttackOwned_G61
    brl SourceAttackOwned_Done
SourceAttackOwned_G61:
.a16
.i16
    sec
    sbc.l Screen_PosX
    sec
    sbc.l SourceAttackTemplate_Base+14
    clc
    adc.l SourceAttackTemplate_Base+18
    sta.l SourceAttackOwned_NewDelta0
SourceAttackMask_ProjectP2Check:
.a16
.i16
    lda.l $437A9C
    and #2
    bne SourceAttackMask_ProjectP2
    brl SourceAttackMask_Projected
SourceAttackMask_ProjectP2:
.a16
.i16
    lda.l SourceAttackOwned_ReadY1
    jsl SourceAttackOwned_ProjectX
    bcs SourceAttackOwned_G62
    brl SourceAttackOwned_Done
SourceAttackOwned_G62:
.a16
.i16
    cmp.l SourceAttackTemplate_Base+144
    beq SourceAttackOwned_G63
    brl SourceAttackOwned_Done
SourceAttackOwned_G63:
.a16
.i16
    lda.l SourceAttackOwned_Motion+16
    jsl SourceAttackOwned_ProjectX
    bcs SourceAttackOwned_G64
    brl SourceAttackOwned_Done
SourceAttackOwned_G64:
.a16
.i16
    sec
    sbc.l Screen_PosX
    sec
    sbc.l SourceAttackTemplate_Base+142
    clc
    adc.l SourceAttackTemplate_Base+146
    sta.l SourceAttackOwned_NewDelta1
SourceAttackMask_Projected:
.a16
.i16
    lda.l SourceAttackOwned_State
    cmp #3
    beq SourceAttackOwned_RebaseChanged
    lda.l SourceAttackOwned_NewDelta0
    cmp.l SourceAttackOwned_Delta0
    bne SourceAttackOwned_RebaseChanged
    lda.l SourceAttackOwned_NewDelta1
    cmp.l SourceAttackOwned_Delta1
    bne SourceAttackOwned_RebaseChanged
    brl SourceAttackOwned_Done
SourceAttackOwned_RebaseChanged:
.a16
.i16
    lda #1
    sta.l SourceAttackOwned_Busy
    lda.l SourceAttackOwned_NewDelta0
    sta.l SourceAttackOwned_Delta0
    lda.l SourceAttackOwned_NewDelta1
    sta.l SourceAttackOwned_Delta1
    sep #$20
.a8
    lda #$43
    pha
    plb
    rep #$30
.a16
    lda.l $437A9C
    and #1
    beq SourceAttackMask_CopyP2
    ldx #$7420
    ldy #$7600
    lda #39
    mvn $43,$43
SourceAttackMask_CopyP2:
.a16
.i16
    lda.l $437A9C
    and #2
    beq SourceAttackMask_RebaseP1Check
    ldx #$74A0
    ldy.w $7BC0
    lda #39
    mvn $43,$43
SourceAttackMask_RebaseP1Check:
.a16
.i16
    lda.l $437A9C
    and #1
    bne SourceAttackMask_RebaseP1
    brl SourceAttackMask_RebaseP2Check
SourceAttackMask_RebaseP1:
.a16
.i16
    ldx #0
    ldy #0
SourceAttackOwned_P1:
.a16
.i16
    lda.w $7448,y
    and #1
    xba
    sta.l SourceAttackOwned_Work
    lda.l SourceAttackTemplate_Base+32,x
    and #$00FF
    ora.l SourceAttackOwned_Work
    clc
    adc.l SourceAttackOwned_Delta0
    and #$01FF
    sta.l SourceAttackOwned_Work
    sep #$20
.a8
    sta.l SourceAttackOwned_Image,x
    rep #$20
.a16
    lda.l SourceAttackOwned_Work
    xba
    and #1
    sta.l SourceAttackOwned_HighBit
    lda.w $7448,y
    and #2
    ora.l SourceAttackOwned_HighBit
    sep #$20
.a8
    sta.w $7820,y
    rep #$20
.a16
    txa
    clc
    adc #4
    tax
    iny
    cpy #10
    bcc SourceAttackOwned_P1
SourceAttackMask_RebaseP2Check:
.a16
.i16
    lda.l $437A9C
    and #2
    bne SourceAttackMask_RebaseP2
    brl SourceAttackMask_PackBoth
SourceAttackMask_RebaseP2:
.a16
.i16
    ldx #0
    ldy #0
SourceAttackOwned_P2:
.a16
.i16
    lda.w $74C8,y
    and #1
    xba
    sta.l SourceAttackOwned_Work
    lda.l SourceAttackTemplate_Base+128+32,x
    and #$00FF
    ora.l SourceAttackOwned_Work
    clc
    adc.l SourceAttackOwned_Delta1
    and #$01FF
    sta.l SourceAttackOwned_Work
    sep #$20
.a8
    jsl SourceLayout_StoreLow
    rep #$20
.a16
    lda.l SourceAttackOwned_Work
    xba
    and #1
    sta.l SourceAttackOwned_HighBit
    lda.w $74C8,y
    and #2
    ora.l SourceAttackOwned_HighBit
    sep #$20
.a8
    jsr SourceLayout_StoreHigh
    rep #$20
.a16
    txa
    clc
    adc #4
    tax
    iny
    cpy #10
    bcc SourceAttackOwned_P2
SourceAttackMask_PackBoth:
.a16
.i16
    ldx #0
    ldy #0
SourceAttackOwned_Pack:
.a16
.i16
    lda.w $7820,x
    and #3
    sta.l SourceAttackOwned_Work
    lda.w $7821,x
    and #3
    asl a
    asl a
    ora.l SourceAttackOwned_Work
    sta.l SourceAttackOwned_Work
    lda.w $7822,x
    and #3
    asl a
    asl a
    asl a
    asl a
    ora.l SourceAttackOwned_Work
    sta.l SourceAttackOwned_Work
    lda.w $7823,x
    and #3
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    ora.l SourceAttackOwned_Work
    sta.l SourceAttackOwned_Work
    sep #$20
.a8
    sta.w $7800,y
    rep #$20
.a16
    txa
    clc
    adc #4
    tax
    iny
    jsr SourceLayout_PackCompare
    bcc SourceAttackOwned_Pack
    lda #0
    sta.l SourceAttackOwned_Busy
    lda #1
    sta.l SourceAttackOwned_State
    lda.l SourceAttackOwned_Stages
    inc a
    sta.l SourceAttackOwned_Stages
    brl SourceAttackOwned_Done
SourceAttackOwned_Collect:
.a16
.i16
    php
    rep #$30
    pha
    phx
    phy
    phb
    phd
    cld
    lda.l SourceAttackOwned_InitMagic
    cmp #$B077
    beq SourceAttackOwned_CollectInitialized
    brl SourceAttackOwned_CollectDone
SourceAttackOwned_CollectInitialized:
.a16
.i16
    jsl SourceAttackMask_Reset
    jsl SourceStandby_FaceLive
    bcs SourceAttackOwned_CheckAck
SourceAttackOwned_NoPair:
.a16
.i16
    lda #0
    sta.l SourceAttackOwned_Suppressed
    sta.l SourceAttackOwned_State
SourceAttackOwned_CheckAck:
.a16
.i16
    lda.l SourceAttackOwned_Hold
    beq SourceAttackOwned_CollectDone
    lda.l SourceVisual_CompletedAcks
    cmp.l SourceAttackOwned_Ack
    beq SourceAttackOwned_CollectDone
    lda.l SourceNextScene_Low
    cmp.l SourceAttackOwned_PhysicalLow
    bne SourceAttackOwned_Released
    lda.l SourceNextScene_High
    cmp.l SourceAttackOwned_PhysicalHigh
    beq SourceAttackOwned_CollectDone
SourceAttackOwned_Released:
.a16
.i16
    lda #0
    sta.l SourceAttackOwned_Hold
    sta.l $437A96
    sta.l $437A98
SourceAttackOwned_CollectDone:
.a16
.i16
    pld
    plb
    ply
    plx
    pla
    plp
    rtl
SourceAttackOwned_Publish:
.a16
.i16
    php
    rep #$30
    pha
    phx
    phy
    phb
    phd
    cld
    jsl SourceAttackOwned_Collect
    lda #$4F
    sta.l SourceAttackOwned_SourceHi
    lda #0
    sta.l SourceAttackOwned_Use
    lda.l SourcePacket_NmiPending
    sta.l SourceAttackOwned_SavedPending
    lda.l SourceAttackOwned_InitMagic
    cmp #$B077
    beq SourceAttackOwned_G65
    brl SourceAttackOwned_Done
SourceAttackOwned_G65:
.a16
.i16
    lda.l SourcePacket_NmiPending
    beq SourceAttackOwned_PendingAccepted
    lda.l SourceAttackOwned_Hold
    cmp #1
    beq SourceAttackOwned_PendingAccepted
    lda.l SourceAttackOwned_State
    cmp #1
    beq SourceAttackOwned_PendingAccepted
    brl SourceAttackOwned_Done
SourceAttackOwned_PendingAccepted:
.a16
.i16
    lda.l SourceAttackOwned_State
    cmp #1
    beq SourceAttackOwned_G66
    brl SourceAttackOwned_Done
SourceAttackOwned_G66:
.a16
.i16
    lda.l SourceAttackOwned_Busy
    beq SourceAttackOwned_G67
    brl SourceAttackOwned_Done
SourceAttackOwned_G67:
.a16
.i16
    lda.l SourcePacket_CopyBusy
    beq SourceAttackOwned_G68
    brl SourceAttackOwned_Done
SourceAttackOwned_G68:
.a16
.i16
    lda.l SourceNextScene_Magic
    cmp #$5343
    beq SourceAttackOwned_G69
    brl SourceAttackOwned_Done
SourceAttackOwned_G69:
.a16
.i16
    lda.l SourceNextScene_Low
    cmp.l SourceAttackOwned_GenLow
    beq SourceAttackOwned_G70
    brl SourceAttackOwned_Done
SourceAttackOwned_G70:
.a16
.i16
    lda.l SourceNextScene_High
    cmp.l SourceAttackOwned_GenHigh
    beq SourceAttackOwned_G71
    brl SourceAttackOwned_Done
SourceAttackOwned_G71:
.a16
.i16
    lda.l Screen_PosX
    cmp.l SourceAttackOwned_Camera
    beq SourceAttackOwned_G72
    brl SourceAttackOwned_Done
SourceAttackOwned_G72:
.a16
.i16
    jsl SourceStandby_FaceLive
    bcs SourceAttackOwned_G74
    brl SourceAttackOwned_Done
SourceAttackOwned_G74:
.a16
.i16
    lda #$76
    sta.l SourceAttackOwned_SourceHi
    lda #1
    sta.l SourceAttackOwned_Use
    sta.l SourcePacket_NmiPending
    brl SourceAttackOwned_Done
SourceAttackOwned_Done:
.a16
.i16
    pld
    plb
    ply
    plx
    pla
    plp
    rtl
SourceAttackOwned_NmiPublish:
.a16
.i16
    php
    rep #$30
    pha
    lda.l SourceAttackOwned_InitMagic
    cmp #$B077
    bne SourceAttackOwned_FastNormal
    lda.l SourceAttackOwned_State
    ora.l SourceAttackOwned_Hold
    bne SourceAttackOwned_FullPublish
SourceAttackOwned_FastNormal:
.a16
.i16
    pla
    plp
    jml SourcePacket_NmiPublish
SourceAttackOwned_FullPublish:
.a16
.i16
    pla
    plp
    php
    rep #$30
    pha
    phx
    phy
    phb
    phd
    cld
    lda.l SourceAttackOwned_InitMagic
    cmp #$B077
    beq SourceAttackOwned_PublishInitialized
    pld
    plb
    ply
    plx
    pla
    plp
    jml SourcePacket_NmiPublish
SourceAttackOwned_PublishInitialized:
.a16
.i16
    lda.l SourceAttackOwned_Hold
    beq SourceAttackOwned_ProceedPublish
    lda.l SourceAttackOwned_Suppressed
    bne SourceAttackOwned_ProceedPublish
    lda.l SourceNextScene_Low
    cmp.l SourceAttackOwned_PhysicalLow
    bne SourceAttackOwned_ProceedPublish
    lda.l SourceNextScene_High
    cmp.l SourceAttackOwned_PhysicalHigh
    bne SourceAttackOwned_ProceedPublish
    jsl SourceAttackMask_PhysicalLive
    bcc SourceAttackOwned_ProceedPublish
    lda.l SourceAttackOwned_State
    cmp #1
    beq SourceAttackOwned_ProceedPublish
    pld
    plb
    ply
    plx
    pla
    plp
    rtl
SourceAttackOwned_ProceedPublish:
.a16
.i16
    jsl SourceAttackOwned_Publish
    jsl SourceOwnedRefresh_NmiTransfer
    lda.l SourceAttackOwned_Use
    beq SourceAttackOwned_NormalAck
    lda.l SourcePacket_NmiPending
    bne SourceAttackOwned_RestorePending
    lda #2
    sta.l SourceAttackOwned_State
    lda.l $437A96
    and.l $437B38
    sta.l $437A96
    lda.l $437A9C
    ora.l $437A98
    sta.l $437A98
    ora.l $437A9E
    sta.l $437A9E
    lda.l $437B38
    sta.l $437A9A
    lda #1
    sta.l SourceAttackOwned_Hold
    lda.l SourceVisual_CompletedAcks
    sta.l SourceAttackOwned_Ack
    lda.l SourceNextScene_Low
    sta.l SourceAttackOwned_PhysicalLow
    lda.l SourceNextScene_High
    sta.l SourceAttackOwned_PhysicalHigh
    lda.l SourceAttackOwned_PhysicalAcks
    inc a
    sta.l SourceAttackOwned_PhysicalAcks
    lda.l StageTimer_FieldCounter
    sta.l SourceAttackOwned_AckField
SourceAttackOwned_RestorePending:
.a16
.i16
    lda.l SourceAttackOwned_SavedPending
    sta.l SourcePacket_NmiPending
    bra SourceAttackOwned_PublishEnd
SourceAttackOwned_NormalAck:
.a16
.i16
    lda.l SourceAttackOwned_SavedPending
    beq SourceAttackOwned_PublishEnd
    lda.l SourcePacket_NmiPending
    bne SourceAttackOwned_PublishEnd
    lda #0
    sta.l SourceAttackOwned_Hold
    sta.l $437A96
    sta.l $437A98
SourceAttackOwned_PublishEnd:
.a16
.i16
    pld
    plb
    ply
    plx
    pla
    plp
    rtl
SourceAttackOwned_ReleasePressure:
.a16
.i16
    php
    rep #$30
    pha
    phx
    phy
    phb
    phd
    cld
    lda.l SourceAttackOwned_InitMagic
    cmp #$B077
    bne SourceAttackOwned_CanRelease
    lda.l SourceAttackOwned_Hold
    beq SourceAttackOwned_CanRelease
    lda #0
    sta.l SourceAttackOwned_State
    lda #1
    sta.l SourceAttackOwned_Suppressed
    lda.l SourcePacket_CopyBusy
    bne SourceAttackOwned_PressureWait
    lda.l SourcePacket_ActiveValid
    cmp #1
    bne SourceAttackOwned_PressureWait
    lda #1
    sta.l SourcePacket_NmiPending
SourceAttackOwned_PressureWait:
.a16
.i16
    pld
    plb
    ply
    plx
    pla
    plp
    clc
    rtl
SourceAttackOwned_CanRelease:
.a16
.i16
    lda #0
    sta.l SourceAttackOwned_State
    pld
    plb
    ply
    plx
    pla
    plp
    jml SourceAttackTemplate_ReleasePressure
SourceAttackOwned_MayRelease:
.a16
.i16
    php
    rep #$30
    pha
    phx
    phy
    phb
    phd
    cld
    lda.l SourceAttackOwned_InitMagic
    cmp #$B077
    bne SourceAttackOwned_ReleaseAllowed
    lda.l SourceAttackOwned_Hold
    beq SourceAttackOwned_ReleaseCancel
    jsl SourceAttackJoint_Defer
    bcs SourceAttackOwned_ReleaseWait
    jsl SourceAttackLease_Adopt
    lda.l $437A9A
    beq SourceAttackLease_StillHeld
    lda.l $437A96
    and.l $437A9A
    cmp.l $437A9A
    bne SourceAttackLease_StillHeld
    lda #0
    sta.l SourceAttackOwned_State
    brl SourceAttackOwned_ReleaseAllowed
SourceAttackLease_StillHeld:
.a16
.i16
    lda #0
    sta.l SourceAttackOwned_State
    lda #1
    sta.l SourceAttackOwned_Suppressed
    lda.l SourcePacket_CopyBusy
    bne SourceAttackOwned_ReleaseWait
    lda.l SourcePacket_ActiveValid
    cmp #1
    bne SourceAttackOwned_ReleaseWait
    lda #1
    sta.l SourcePacket_NmiPending
SourceAttackOwned_ReleaseWait:
.a16
.i16
    pld
    plb
    ply
    plx
    pla
    plp
    clc
    rtl
SourceAttackOwned_ReleaseCancel:
.a16
.i16
    lda #0
    sta.l SourceAttackOwned_State
SourceAttackOwned_ReleaseAllowed:
.a16
.i16
    pld
    plb
    ply
    plx
    pla
    plp
    sec
    rtl
; A8 publisher ABI. Default source is always the ordinary image, even
; before BW-RAM initialization or when startup writes are unavailable.
SourceAttackOwned_SourceSelect:
.a16
.i16
    php
    rep #$30
.a16
.i16
    pha
    lda.l SourceAttackOwned_InitMagic
    cmp #$B077
    bne SourceAttackOwned_SourceNormal
    lda.l SourceAttackOwned_Use
    cmp #1
    bne SourceAttackOwned_SourceNormal
    lda.l SourceAttackOwned_State
    cmp #1
    bne SourceAttackOwned_SourceNormal
    pla
    sep #$20
.a8
    lda #$76
    plp
    rtl
SourceAttackOwned_SourceNormal:
.a16
.i16
    pla
    sep #$20
.a8
    lda #$4F
    plp
    rtl
SourceAttackOwned_End:
.a16
.i16
; Stage0 normal frontpanel has its own beam-latched column window.
; After DMA/BG1, only that guarded column and register tail remain. Permit
; the existing <=245 OAM bound here; the earlier entry bound remains <=240.
SourceAttackOwned_AfterNormal:
.a16
.i16
    php
    rep #$30
    pha
    jsl SourceAttackOwned_HasLatePacket
    cmp #1
    bne SourceAttackOwned_AfterNormalDone
    lda.l SourceAttackOwned_InitMagic
    cmp #$B077
    bne SourceAttackOwned_AfterNormalDone
    lda.l Game_StageIndex
    bne SourceAttackOwned_AfterNormalDone
    lda.l StageFp_ModeMap
    and #255
    beq SourceAttackOwned_AfterNormalDone
    ; Reject the entire expensive publication attempt before queue scans
    ; when only the PPU register tail can still fit in this vblank.
    jsl SourceFp_ColumnWindow
    bcc SourceAttackOwned_AfterNormalDone
    lda #1
    sta.l SourceAttackOwned_LatePhase
    pla
    plp
    jsl SourceAttackOwned_NmiPublish
    php
    rep #$30
    pha
    lda #0
    sta.l SourceAttackOwned_LatePhase
SourceAttackOwned_AfterNormalDone:
.a16
.i16
    pla
    plp
    jml StageFp_BG2CommitDispatch
SourceAttackOwned_DeadlineMode:
.a16
.i16
    php
    rep #$30
.a16
.i16
    pha
    lda.l SourceAttackOwned_InitMagic
    cmp #$B077
    bne SourceAttackOwned_DeadlineOriginal
    lda.l SourceAttackOwned_LatePhase
    cmp #1
    bne SourceAttackOwned_DeadlineOriginal
    lda.l Game_StageIndex
    bne SourceAttackOwned_DeadlineOriginal
    lda.l StageFp_ModeMap
    and #255
    beq SourceAttackOwned_DeadlineOriginal
    pla
    sep #$20
.a8
    lda #1
    plp
    rtl
SourceAttackOwned_DeadlineOriginal:
.a16
.i16
    pla
    sep #$20
.a8
    lda.l SourcePacket_NmiMainBusy
    plp
    rtl
SourceAttackOwned_ProjectX:
.a16
.i16
    sta.l SourcePacket_ProjectInput
    lda #0
    sta.l SourcePacket_ProjectSign
    lda.l SourcePacket_ProjectInput
    bmi SourceAttackOwned_ProjectBranch24
    brl SourceAttackOwned_ProjectX__absolute
SourceAttackOwned_ProjectBranch24:
.a16
.i16
    lda #1
    sta.l SourcePacket_ProjectSign
    lda.l SourcePacket_ProjectInput
    eor #$FFFF
    inc a
SourceAttackOwned_ProjectX__absolute:
.a16
.i16
    cmp #$4000
    bcs SourceAttackOwned_ProjectBranch25
    brl SourceAttackOwned_ProjectX__valid
SourceAttackOwned_ProjectBranch25:
.a16
.i16
    clc
    rtl
SourceAttackOwned_ProjectX__valid:
.a16
.i16
    sta.l SourcePacket_ProjectInput
    and #$00FF
    tax
    lda.l SourcePacket_QLo,x
    and #$00FF
    sta.l SourcePacket_ProjectQ
    lda.l SourcePacket_RLo,x
    and #$00FF
    sta.l SourcePacket_ProjectR
    lda.l SourcePacket_ProjectInput
    xba
    and #$00FF
    asl a
    tax
    lda.l SourcePacket_QHi,x
    clc
    adc.l SourcePacket_ProjectQ
    sta.l SourcePacket_ProjectQ
    txa
    lsr a
    tax
    lda.l SourcePacket_RHi,x
    and #$00FF
    clc
    adc.l SourcePacket_ProjectR
    clc
    adc #2
    tax
    lda.l SourcePacket_Carry,x
    and #$00FF
    clc
    adc.l SourcePacket_ProjectQ
    sta.l SourcePacket_ProjectQ
    lda.l SourcePacket_ProjectSign
    bne SourceAttackOwned_ProjectBranch26
    brl SourceAttackOwned_ProjectX__positive
SourceAttackOwned_ProjectBranch26:
.a16
.i16
    lda.l SourcePacket_ProjectQ
    eor #$FFFF
    inc a
    sec
    rtl
SourceAttackOwned_ProjectX__positive:
.a16
.i16
    lda.l SourcePacket_ProjectQ
    sec
    rtl
; Private service-only capture. Ordinary scene bytes are restored before unlock.
SourceAttackOwned_ServiceCapture:
.a16
.i16
    lda.l SourceVisual_ServiceOnly
    bne SourceAttackOwned_ServiceStart
    clc
    rtl
SourceAttackOwned_ServiceStart:
.a16
.i16
    php
    rep #$30
    pha
    phx
    phy
    phb
    lda.l SourceAttackOwned_InitMagic
    cmp #$B077
    beq SourceAttackOwned_ServiceInitialized
    brl SourceAttackOwned_ServiceDone
SourceAttackOwned_ServiceInitialized:
.a16
.i16
    lda.l SourcePacket_CopyBusy
    ora.l SourceAttackOwned_Busy
    beq SourceAttackOwned_ServiceFree
    brl SourceAttackOwned_ServiceDone
SourceAttackOwned_ServiceFree:
.a16
.i16
    lda.l SourceVisual_Key
    cmp #$0216
    beq SourceAttackOwned_ServiceKey
    brl SourceAttackOwned_ServiceDone
SourceAttackOwned_ServiceKey:
.a16
.i16
    lda.l SourceVisual_Key+2
    beq SourceAttackOwned_ServiceKeyHigh
    brl SourceAttackOwned_ServiceDone
SourceAttackOwned_ServiceKeyHigh:
.a16
.i16
    lda.l SourceVisual_PieceCount
    cmp #10
    beq SourceAttackOwned_ServicePieces
    brl SourceAttackOwned_ServiceDone
SourceAttackOwned_ServicePieces:
.a16
.i16
    lda.l SourceVisual_ActorSlot
    cmp #2
    bcc SourceAttackOwned_ServicePlayer
    brl SourceAttackOwned_ServiceDone
SourceAttackOwned_ServicePlayer:
.a16
.i16
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    tax
    lda.l SourceAttackTemplate_Base,x
    cmp #SourceAttackTemplate_Magic
    bne SourceAttackOwned_ServiceQueue
    brl SourceAttackMask_ServiceSnapshot
SourceAttackOwned_ServiceQueue:
.a16
.i16
    ldx #0
SourceAttackOwned_ServiceQueueNext:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$00FF
    cmp #$41
    bne SourceAttackOwned_ServiceQueueAdvance
    lda.l DmaQueue+7,x
    and #$00FF
    cmp #$7E
    bne SourceAttackOwned_ServiceQueueAdvance
    brl SourceAttackOwned_ServiceDone
SourceAttackOwned_ServiceQueueAdvance:
.a16
.i16
    txa
    clc
    adc #8
    tax
    cpx #64
    bcc SourceAttackOwned_ServiceQueueNext
    lda #1
    sta.l SourcePacket_CopyBusy
    sta.l SourceAttackOwned_Busy
    ldx #$52D8
    ldy #$7AA0
    lda #39
    mvn $43,$7E
    ldx #$5396
    ldy #$7AC8
    lda #9
    mvn $43,$7E
    ldx #$53A0
    ldy #$7AD2
    lda #1
    mvn $43,$7E
    ldx #$53AB
    ldy #$7AD4
    lda #5
    mvn $43,$7E
    ldx #$5340
    ldy #$7AE0
    lda #63
    mvn $43,$43
    sep #$20
.a8
    lda #0
    pha
    plb
    rep #$30
.a16
.i16
    lda #472
    sta.l Oam_CurrentSlot
    jsl SourceAttackOwned_CallEmitter
    bcc SourceAttackOwned_ServiceRestore
    jsl SourceAttackTemplate_Capture
SourceAttackOwned_ServiceRestore:
.a16
.i16
    ldx #$7AA0
    ldy #$52D8
    lda #39
    mvn $7E,$43
    ldx #$7AC8
    ldy #$5396
    lda #9
    mvn $7E,$43
    ldx #$7AD2
    ldy #$53A0
    lda #1
    mvn $7E,$43
    ldx #$7AD4
    ldy #$53AB
    lda #5
    mvn $7E,$43
    ldx #$7AE0
    ldy #$5340
    lda #63
    mvn $43,$43
    lda #0
    sta.l SourceAttackOwned_Busy
    sta.l SourcePacket_CopyBusy
    brl SourceAttackMask_ServiceSnapshot
SourceAttackMask_ServiceSnapshot:
.a16
.i16
    jsl SourceAttackOwned_CaptureSeal
    jsl SourceAttackOwned_Snapshot
SourceAttackOwned_ServiceDone:
.a16
.i16
    plb
    ply
    plx
    pla
    plp
    sec
    rtl
; RTS-to-RTL bridge: checked against linked ROM before native execution.
SourceAttackOwned_CallEmitter:
.a16
.i16
SourceAttackOwned_EmitRtl = (SourcePacket_EmitStart__done+5)&$FFFF
    pea SourceAttackOwned_EmitRtl
    jml SourceVisual_Emit
; Same EmitFinish stack ABI; suppress only the private emitter's idle dispatcher.
SourceAttackOwned_ServiceEmitDone:
.a16
.i16
    lda.l SourceVisual_ServiceOnly
    bne SourceAttackOwned_ServiceEmitReturn
    jml SourceSecond_EmitDone
SourceAttackOwned_ServiceEmitReturn:
.a16
.i16
    pld
    plb
    ply
    plx
    pla
    plp
    rtl
; Inside the original source sequence transaction. X=motion,Y=source,DB=$43.
SourceAttackOwned_ReadActorTail:
.a16
.i16
    lda.w $4E4A,y
    sta.w $53CA,x
    lda.w $4E36,y
    sta.w $53CE,x
    rtl

; Per-player immutable media lease records reuse unhooked NextFrame storage.
; Adopted=$437A96, pending physical mask=$437A98, committed mask=$437A9A.
SourceAttackLease_Observe:
.a16
.i16
    lda.l $437A98
    beq SourceAttackMask_ObserveNormal
    jsl SourceAttackJoint_Defer
    bcs SourceAttackMask_ObserveNormal
    jsl SourceAttackLease_Adopt
SourceAttackMask_ObserveNormal:
.a16
.i16
    jml SourceVisual_CompletedObserve
SourceAttackLease_Capture:
.a16
.i16
    php
    rep #$30
    pha
    phx
    phy
    phb
    lda.l SourceVisual_ActorSlot
    cmp #2
    bcc SourceAttackLease_CapturePlayer
    brl SourceAttackLease_CaptureDone
SourceAttackLease_CapturePlayer:
.a16
.i16
    xba
    asl a
    asl a
    sta.l $437B34
    tax
    lda #0
    sta.l $436C00,x
    lda.l Game_StageIndex
    sta.l $436C02,x
    lda #22
    sta.l $436C04,x
    lda.l SourceVisual_Key
    sta.l $436C06,x
    lda.l SourceVisual_PieceCount
    sta.l $436C08,x
    lda.l SourceVisual_EntryIndexSaved
    sta.l $436C0A,x
    lda.l $437B34
    clc
    adc #$6C20
    tay
    ldx #(SourceVisual_EntryScratch&$FFFF)
    lda #23
    mvn $43,$7E
    lda.l $437B34
    clc
    adc #$6C38
    tay
    lda.l SourceVisual_Record
    clc
    adc #(SourceVisual_State&$FFFF)
    tax
    lda #31
    mvn $43,$7E
    lda.l $437B34
    clc
    adc #$6C58
    tay
    ldx #$4000
    lda #159
    mvn $43,$7E
    lda.l $437B34
    clc
    adc #$6CF8
    tay
    lda.l SourceVisual_ActorMapBase
    clc
    adc #(SourceVisual_ActorPieceMap&$FFFF)
    tax
    lda #64
    mvn $43,$7E
    lda.l $437B34
    tax
    lda #$A66C
    sta.l $436C00,x
SourceAttackLease_CaptureDone:
.a16
.i16
    plb
    ply
    plx
    pla
    plp
    rtl
SourceAttackLease_Adopt:
.a16
.i16
    php
    rep #$30
    pha
    phx
    phy
    phb
    lda.l $437A98
    bne SourceAttackLease_Pending
    brl SourceAttackLease_Done
SourceAttackLease_Pending:
.a16
.i16
    sta.l $437B20
    cmp #4
    bcc SourceAttackLease_Check1
    brl SourceAttackLease_Abort
SourceAttackLease_Check1:
.a16
.i16
    lda.l SourceAttackOwned_InitMagic
    cmp #$B077
    beq SourceAttackLease_Check2
    brl SourceAttackLease_Abort
SourceAttackLease_Check2:
.a16
.i16
    lda.l SourceAttackOwned_Hold
    cmp #1
    beq SourceAttackLease_Check3
    brl SourceAttackLease_Abort
SourceAttackLease_Check3:
.a16
.i16
    lda.l SourceAttackOwned_Busy
    beq SourceAttackLease_Check4
    brl SourceAttackLease_Abort
SourceAttackLease_Check4:
.a16
.i16
    lda.l SourceVisual_CompletedAcks
    cmp.l SourceAttackOwned_Ack
    beq SourceAttackLease_Check5
    brl SourceAttackLease_Abort
SourceAttackLease_Check5:
.a16
.i16
    lda.l SourceNextScene_Low
    cmp.l SourceAttackOwned_PhysicalLow
    beq SourceAttackLease_Check6
    brl SourceAttackLease_Abort
SourceAttackLease_Check6:
.a16
.i16
    lda.l SourceNextScene_High
    cmp.l SourceAttackOwned_PhysicalHigh
    beq SourceAttackLease_Check7
    brl SourceAttackLease_Abort
SourceAttackLease_Check7:
.a16
.i16
    lda.l SourceNextScene_Magic
    cmp #$5343
    beq SourceAttackLease_Check8
    brl SourceAttackLease_Abort
SourceAttackLease_Check8:
.a16
.i16
    lda.l $437B20
    and #1
    bne SourceAttackLease_Validate0
    brl SourceAttackLease_Validated0
SourceAttackLease_Validate0:
.a16
.i16
    lda.l $436C00
    cmp #$A66C
    beq SourceAttackLease_Check9
    brl SourceAttackLease_Abort
SourceAttackLease_Check9:
.a16
.i16
    lda.l $436C02
    cmp #$0000
    beq SourceAttackLease_Check10
    brl SourceAttackLease_Abort
SourceAttackLease_Check10:
.a16
.i16
    lda.l $436C04
    cmp #$0016
    beq SourceAttackLease_Check11
    brl SourceAttackLease_Abort
SourceAttackLease_Check11:
.a16
.i16
    lda.l $436C06
    cmp #$0216
    beq SourceAttackLease_Check12
    brl SourceAttackLease_Abort
SourceAttackLease_Check12:
.a16
.i16
    lda.l $436C08
    cmp #$000A
    beq SourceAttackLease_Check13
    brl SourceAttackLease_Abort
SourceAttackLease_Check13:
.a16
.i16
    lda #0
    sta.l $437B28
SourceAttackLease_Piece0:
.a16
.i16
    lda.l $437B28
    asl a
    asl a
    asl a
    asl a
    tax
    lda.l $436C64,x
    sta.l $437B2A
    lda.l $436C60,x
    and #255
    sta.l $437B2C
    lda.l $436C62,x
    sta.l $437B2E
    lda.l $437B28
    tax
    lda.l $436CF8,x
    and #255
    cmp #64
    bcc SourceAttackLease_Check14
    brl SourceAttackLease_Abort
SourceAttackLease_Check14:
.a16
.i16
    asl a
    asl a
    asl a
    tax
    lda.l SourceVisual_BlockCache,x
    cmp.l $437B2A
    beq SourceAttackLease_Check15
    brl SourceAttackLease_Abort
SourceAttackLease_Check15:
.a16
.i16
    lda.l SourceVisual_BlockCache+2,x
    cmp #2
    beq SourceAttackLease_Check16
    brl SourceAttackLease_Abort
SourceAttackLease_Check16:
.a16
.i16
    lda.l SVActor_HeldBlocks,x
    and #64
    bne SourceAttackLease_Check17
    brl SourceAttackLease_Abort
SourceAttackLease_Check17:
.a16
.i16
    lda.l $437B2C
    cmp #8
    bcc SourceAttackLease_Check18
    brl SourceAttackLease_Abort
SourceAttackLease_Check18:
.a16
.i16
    tax
    lda.l $436C48,x
    and #255
    dec a
    cmp #8
    bcc SourceAttackLease_Check19
    brl SourceAttackLease_Abort
SourceAttackLease_Check19:
.a16
.i16
    asl a
    asl a
    asl a
    tax
    lda.l SourceVisual_PaletteCache,x
    cmp.l $437B2E
    beq SourceAttackLease_Check20
    brl SourceAttackLease_Abort
SourceAttackLease_Check20:
.a16
.i16
    lda.l SourceVisual_PaletteCache+3,x
    and #255
    cmp #1
    beq SourceAttackLease_Check21
    brl SourceAttackLease_Abort
SourceAttackLease_Check21:
.a16
.i16
    lda.l SVActor_HeldPalettes,x
    and #64
    bne SourceAttackLease_Check22
    brl SourceAttackLease_Abort
SourceAttackLease_Check22:
.a16
.i16
    lda.l $437B28
    inc a
    sta.l $437B28
    cmp #10
    bcs SourceAttackLease_Validated0
    brl SourceAttackLease_Piece0
SourceAttackLease_Validated0:
.a16
.i16
    lda.l $437B20
    and #2
    bne SourceAttackLease_Validate1
    brl SourceAttackLease_Validated1
SourceAttackLease_Validate1:
.a16
.i16
    lda.l $437000
    cmp #$A66C
    beq SourceAttackLease_Check23
    brl SourceAttackLease_Abort
SourceAttackLease_Check23:
.a16
.i16
    lda.l $437002
    cmp #$0000
    beq SourceAttackLease_Check24
    brl SourceAttackLease_Abort
SourceAttackLease_Check24:
.a16
.i16
    lda.l $437004
    cmp #$0016
    beq SourceAttackLease_Check25
    brl SourceAttackLease_Abort
SourceAttackLease_Check25:
.a16
.i16
    lda.l $437006
    cmp #$0216
    beq SourceAttackLease_Check26
    brl SourceAttackLease_Abort
SourceAttackLease_Check26:
.a16
.i16
    lda.l $437008
    cmp #$000A
    beq SourceAttackLease_Check27
    brl SourceAttackLease_Abort
SourceAttackLease_Check27:
.a16
.i16
    lda #0
    sta.l $437B28
SourceAttackLease_Piece1:
.a16
.i16
    lda.l $437B28
    asl a
    asl a
    asl a
    asl a
    tax
    lda.l $437064,x
    sta.l $437B2A
    lda.l $437060,x
    and #255
    sta.l $437B2C
    lda.l $437062,x
    sta.l $437B2E
    lda.l $437B28
    tax
    lda.l $4370F8,x
    and #255
    cmp #64
    bcc SourceAttackLease_Check28
    brl SourceAttackLease_Abort
SourceAttackLease_Check28:
.a16
.i16
    asl a
    asl a
    asl a
    tax
    lda.l SourceVisual_BlockCache,x
    cmp.l $437B2A
    beq SourceAttackLease_Check29
    brl SourceAttackLease_Abort
SourceAttackLease_Check29:
.a16
.i16
    lda.l SourceVisual_BlockCache+2,x
    cmp #2
    beq SourceAttackLease_Check30
    brl SourceAttackLease_Abort
SourceAttackLease_Check30:
.a16
.i16
    lda.l SVActor_HeldBlocks,x
    and #128
    bne SourceAttackLease_Check31
    brl SourceAttackLease_Abort
SourceAttackLease_Check31:
.a16
.i16
    lda.l $437B2C
    cmp #8
    bcc SourceAttackLease_Check32
    brl SourceAttackLease_Abort
SourceAttackLease_Check32:
.a16
.i16
    tax
    lda.l $437048,x
    and #255
    dec a
    cmp #8
    bcc SourceAttackLease_Check33
    brl SourceAttackLease_Abort
SourceAttackLease_Check33:
.a16
.i16
    asl a
    asl a
    asl a
    tax
    lda.l SourceVisual_PaletteCache,x
    cmp.l $437B2E
    beq SourceAttackLease_Check34
    brl SourceAttackLease_Abort
SourceAttackLease_Check34:
.a16
.i16
    lda.l SourceVisual_PaletteCache+3,x
    and #255
    cmp #1
    beq SourceAttackLease_Check35
    brl SourceAttackLease_Abort
SourceAttackLease_Check35:
.a16
.i16
    lda.l SVActor_HeldPalettes,x
    and #128
    bne SourceAttackLease_Check36
    brl SourceAttackLease_Abort
SourceAttackLease_Check36:
.a16
.i16
    lda.l $437B28
    inc a
    sta.l $437B28
    cmp #10
    bcs SourceAttackLease_Validated1
    brl SourceAttackLease_Piece1
SourceAttackLease_Validated1:
.a16
.i16
    lda.l SourcePacket_CopyBusy
    sta.l $437B26
    lda #1
    sta.l SourcePacket_CopyBusy
    sta.l SourceAttackOwned_Busy
    lda.l $437B20
    and #1
    beq SourceAttackLease_InvalidateP2
    lda #0
    sta.l SourceVisual_CompletedValid
SourceAttackLease_InvalidateP2:
.a16
.i16
    lda.l $437B20
    and #2
    beq SourceAttackLease_Invalidated
    lda #0
    sta.l SVActor_Data+SVActor_Valid
SourceAttackLease_Invalidated:
.a16
.i16
    lda #255
    sta.l $437B22
    sta.l $437B24
    lda.l $437B20
    and #1
    beq SourceAttackLease_KeepP1
    lda #63
    sta.l $437B22
SourceAttackLease_KeepP1:
.a16
.i16
    lda.l $437B20
    and #2
    beq SourceAttackLease_KeepP2
    lda #253
    sta.l $437B24
SourceAttackLease_KeepP2:
.a16
.i16
    ldx #0
SourceAttackLease_ClearBlocks:
.a16
.i16
    sep #$20
.a8
    lda.l SourceVisual_BlockCache+4,x
    and.l $437B22
    sta.l SourceVisual_BlockCache+4,x
    lda.l SVActor_HeldBlocks,x
    and.l $437B24
    sta.l SVActor_HeldBlocks,x
    lda.l SVActor_OldBlocks,x
    and.l $437B24
    sta.l SVActor_OldBlocks,x
    rep #$30
.a16
.i16
    txa
    clc
    adc #8
    tax
    cpx #512
    bcc SourceAttackLease_ClearBlocks
    ldx #0
SourceAttackLease_ClearPalettes:
.a16
.i16
    sep #$20
.a8
    lda.l SourceVisual_PaletteCache+4,x
    and.l $437B22
    sta.l SourceVisual_PaletteCache+4,x
    lda.l SVActor_HeldPalettes,x
    and.l $437B24
    sta.l SVActor_HeldPalettes,x
    lda.l SVActor_OldPalettes,x
    and.l $437B24
    sta.l SVActor_OldPalettes,x
    rep #$30
.a16
.i16
    txa
    clc
    adc #8
    tax
    cpx #64
    bcc SourceAttackLease_ClearPalettes
    lda.l $437B20
    and #1
    bne SourceAttackLease_Install0
    brl SourceAttackLease_Installed0
SourceAttackLease_Install0:
.a16
.i16
    lda #0
    sta.l $437B28
SourceAttackLease_InstallPiece0:
.a16
.i16
    lda.l $437B28
    tax
    lda.l $436CF8,x
    and #255
    asl a
    asl a
    asl a
    tax
    sep #$20
.a8
    lda.l SourceVisual_BlockCache+4,x
    ora #64
    sta.l SourceVisual_BlockCache+4,x
    rep #$30
.a16
.i16
    lda.l $437B28
    asl a
    asl a
    asl a
    asl a
    tax
    lda.l $436C60,x
    and #255
    tax
    lda.l $436C48,x
    and #255
    dec a
    asl a
    asl a
    asl a
    tax
    sep #$20
.a8
    lda.l SourceVisual_PaletteCache+4,x
    ora #64
    sta.l SourceVisual_PaletteCache+4,x
    rep #$30
.a16
.i16
    lda.l $437B28
    inc a
    sta.l $437B28
    cmp #10
    bcs SourceAttackLease_Copy0
    brl SourceAttackLease_InstallPiece0
SourceAttackLease_Copy0:
.a16
.i16
    lda #0
    sta.l SourceVisual_CompletedValid
    ldx #$6C20
    ldy #$EB00
    lda #23
    mvn $7E,$43
    ldx #$6C38
    ldy #$EB18
    lda #31
    mvn $7E,$43
    ldx #$6C58
    ldy #$EB40
    lda #159
    mvn $7E,$43
    ldx #$6CF8
    ldy #$EF50
    lda #64
    mvn $7E,$43
    lda #0
    sta.l SourceVisual_CompletedStage
    sta.l SourceVisual_CompletedAwait
    sta.l SourceVisual_CompletedRetire
    sta.l SourceVisual_CompletedCommitRetire
    lda #22
    sta.l SourceVisual_CompletedRoster
    sep #$20
.a8
    lda #1
    sta.l SourceVisual_CompletedLease+28
    rep #$30
.a16
.i16
    lda #1
    sta.l SourceVisual_CompletedValid
    lda.l SourceVisual_State+0
    cmp.l $436C38
    bne SourceAttackMask_RequestDone0
    lda.l SourceVisual_State+6
    cmp #2
    bne SourceAttackMask_RequestDone0
    sep #$20
.a8
    lda #1
    sta.l SourceVisual_State+28
    rep #$30
.a16
.i16
SourceAttackMask_RequestDone0:
.a16
.i16
SourceAttackLease_Installed0:
.a16
.i16
    lda.l $437B20
    and #2
    bne SourceAttackLease_Install1
    brl SourceAttackLease_Installed1
SourceAttackLease_Install1:
.a16
.i16
    lda #0
    sta.l $437B28
SourceAttackLease_InstallPiece1:
.a16
.i16
    lda.l $437B28
    tax
    lda.l $4370F8,x
    and #255
    asl a
    asl a
    asl a
    tax
    sep #$20
.a8
    lda.l SVActor_HeldBlocks,x
    ora #2
    sta.l SVActor_HeldBlocks,x
    rep #$30
.a16
.i16
    lda.l $437B28
    asl a
    asl a
    asl a
    asl a
    tax
    lda.l $437060,x
    and #255
    tax
    lda.l $437048,x
    and #255
    dec a
    asl a
    asl a
    asl a
    tax
    sep #$20
.a8
    lda.l SVActor_HeldPalettes,x
    ora #2
    sta.l SVActor_HeldPalettes,x
    rep #$30
.a16
.i16
    lda.l $437B28
    inc a
    sta.l $437B28
    cmp #10
    bcs SourceAttackLease_Copy1
    brl SourceAttackLease_InstallPiece1
SourceAttackLease_Copy1:
.a16
.i16
    lda #0
    sta.l SVActor_Data+SVActor_Valid
    ldx #$7020
    ldy #$0000
    lda #23
    mvn $43,$43
    ldx #$7038
    ldy #$0018
    lda #31
    mvn $43,$43
    ldx #$7058
    ldy #$0038
    lda #159
    mvn $43,$43
    ldx #$70F8
    ldy #$0448
    lda #64
    mvn $43,$43
    lda #0
    sta.l SVActor_Data+SVActor_Stage
    lda #22
    sta.l SVActor_Data+SVActor_Roster
    lda.l SVActor_Await
    and #$FFFD
    sta.l SVActor_Await
    lda.l SVActor_Pending
    and #$FFFD
    sta.l SVActor_Pending
    sep #$20
.a8
    lda #1
    sta.l SVActor_Data+24+28
    rep #$30
.a16
.i16
    lda #1
    sta.l SVActor_Data+SVActor_Valid
    lda.l SourceVisual_State+32
    cmp.l $437038
    bne SourceAttackMask_RequestDone1
    lda.l SourceVisual_State+38
    cmp #2
    bne SourceAttackMask_RequestDone1
    sep #$20
.a8
    lda #1
    sta.l SourceVisual_State+60
    rep #$30
.a16
.i16
SourceAttackMask_RequestDone1:
.a16
.i16
SourceAttackLease_Installed1:
.a16
.i16
    lda.l $437A96
    ora.l $437B20
    sta.l $437A96
    lda #0
    sta.l $437A98
    sta.l SourceAttackOwned_Busy
    lda.l $437B26
    sta.l SourcePacket_CopyBusy
SourceAttackLease_Abort:
.a16
.i16
SourceAttackLease_Done:
.a16
.i16
    plb
    ply
    plx
    pla
    plp
    rtl

SourceAttackMask_Reset:
.a16
.i16
    lda.l $437A9E
    beq SourceAttackMask_ResetDone
    lda.l $4119E6
    and #255
    cmp #9
    beq SourceAttackMask_ResetNext0
    lda.l $437A9E
    and #$FFFE
    sta.l $437A9E
SourceAttackMask_ResetNext0:
.a16
.i16
    lda.l $411AE6
    and #255
    cmp #9
    beq SourceAttackMask_ResetNext1
    lda.l $437A9E
    and #$FFFD
    sta.l $437A9E
SourceAttackMask_ResetNext1:
.a16
.i16
SourceAttackMask_ResetDone:
.a16
.i16
    rtl
SourceAttackMask_Ready:
.a16
.i16
    lda #0
    sta.l $437B36
    lda.l $437A9E
    and #1
    beq SourceAttackMask_Test1
    brl SourceAttackMask_ReadyNext0
SourceAttackMask_Test1:
.a16
.i16
    lda.l $4119E6
    and #255
    cmp #$0009
    beq SourceAttackMask_Test2
    brl SourceAttackMask_ReadyNext0
SourceAttackMask_Test2:
.a16
.i16
    lda.l $437400
    cmp #$A770
    beq SourceAttackMask_Test3
    brl SourceAttackMask_ReadyNext0
SourceAttackMask_Test3:
.a16
.i16
    lda.l $437402
    cmp #$0000
    beq SourceAttackMask_Test4
    brl SourceAttackMask_ReadyNext0
SourceAttackMask_Test4:
.a16
.i16
    lda.l $437404
    cmp #$0016
    beq SourceAttackMask_Test5
    brl SourceAttackMask_ReadyNext0
SourceAttackMask_Test5:
.a16
.i16
    lda.l $437406
    cmp #$0216
    beq SourceAttackMask_Test6
    brl SourceAttackMask_ReadyNext0
SourceAttackMask_Test6:
.a16
.i16
    lda.l $437408
    cmp #$0000
    beq SourceAttackMask_Test7
    brl SourceAttackMask_ReadyNext0
SourceAttackMask_Test7:
.a16
.i16
    jsl SourceFacing_Match0
    nop
    nop
    nop
    beq SourceAttackMask_Test8
    brl SourceAttackMask_ReadyNext0
SourceAttackMask_Test8:
.a16
.i16
    lda.l $436C00
    cmp #$A66C
    beq SourceAttackMask_Test9
    brl SourceAttackMask_ReadyNext0
SourceAttackMask_Test9:
.a16
.i16
    lda.l $436C02
    cmp #$0000
    beq SourceAttackMask_Record0_0
    brl SourceAttackMask_ReadyNext0
SourceAttackMask_Record0_0:
.a16
.i16
    lda.l $436C04
    cmp #$0016
    beq SourceAttackMask_Record0_1
    brl SourceAttackMask_ReadyNext0
SourceAttackMask_Record0_1:
.a16
.i16
    lda.l $436C06
    cmp #$0216
    beq SourceAttackMask_Record0_2
    brl SourceAttackMask_ReadyNext0
SourceAttackMask_Record0_2:
.a16
.i16
    lda.l $436C08
    cmp #$000A
    beq SourceAttackMask_Record0_3
    brl SourceAttackMask_ReadyNext0
SourceAttackMask_Record0_3:
.a16
.i16
    lda.l $436C0A
    cmp.l $437416
    beq SourceAttackMask_RecordIndex0
    brl SourceAttackMask_ReadyNext0
SourceAttackMask_RecordIndex0:
.a16
.i16
    lda.l $437B36
    ora #1
    sta.l $437B36
SourceAttackMask_ReadyNext0:
.a16
.i16
    lda.l $437A9E
    and #2
    beq SourceAttackMask_Test10
    brl SourceAttackMask_ReadyNext1
SourceAttackMask_Test10:
.a16
.i16
    lda.l $411AE6
    and #255
    cmp #$0009
    beq SourceAttackMask_Test11
    brl SourceAttackMask_ReadyNext1
SourceAttackMask_Test11:
.a16
.i16
    lda.l $437480
    cmp #$A770
    beq SourceAttackMask_Test12
    brl SourceAttackMask_ReadyNext1
SourceAttackMask_Test12:
.a16
.i16
    lda.l $437482
    cmp #$0000
    beq SourceAttackMask_Test13
    brl SourceAttackMask_ReadyNext1
SourceAttackMask_Test13:
.a16
.i16
    lda.l $437484
    cmp #$0016
    beq SourceAttackMask_Test14
    brl SourceAttackMask_ReadyNext1
SourceAttackMask_Test14:
.a16
.i16
    lda.l $437486
    cmp #$0216
    beq SourceAttackMask_Test15
    brl SourceAttackMask_ReadyNext1
SourceAttackMask_Test15:
.a16
.i16
    lda.l $437488
    cmp #$0000
    beq SourceAttackMask_Test16
    brl SourceAttackMask_ReadyNext1
SourceAttackMask_Test16:
.a16
.i16
    jsl SourceFacing_Match1
    nop
    nop
    nop
    beq SourceAttackMask_Test17
    brl SourceAttackMask_ReadyNext1
SourceAttackMask_Test17:
.a16
.i16
    lda.l $437000
    cmp #$A66C
    beq SourceAttackMask_Test18
    brl SourceAttackMask_ReadyNext1
SourceAttackMask_Test18:
.a16
.i16
    lda.l $437002
    cmp #$0000
    beq SourceAttackMask_Record1_0
    brl SourceAttackMask_ReadyNext1
SourceAttackMask_Record1_0:
.a16
.i16
    lda.l $437004
    cmp #$0016
    beq SourceAttackMask_Record1_1
    brl SourceAttackMask_ReadyNext1
SourceAttackMask_Record1_1:
.a16
.i16
    lda.l $437006
    cmp #$0216
    beq SourceAttackMask_Record1_2
    brl SourceAttackMask_ReadyNext1
SourceAttackMask_Record1_2:
.a16
.i16
    lda.l $437008
    cmp #$000A
    beq SourceAttackMask_Record1_3
    brl SourceAttackMask_ReadyNext1
SourceAttackMask_Record1_3:
.a16
.i16
    lda.l $43700A
    cmp.l $437496
    beq SourceAttackMask_RecordIndex1
    brl SourceAttackMask_ReadyNext1
SourceAttackMask_RecordIndex1:
.a16
.i16
    lda.l $437B36
    ora #2
    sta.l $437B36
SourceAttackMask_ReadyNext1:
.a16
.i16
    lda.l $437B36
    rtl
SourceAttackMask_PatchLive:
.a16
.i16
    lda.l $437A9C
    beq SourceAttackMask_No
    lda.l $437A9C
    and #1
    beq SourceAttackMask_LiveNext0
    lda.l $4119E6
    and #255
    cmp #9
    beq SourceAttackMask_Test19
    brl SourceAttackMask_No
SourceAttackMask_Test19:
.a16
.i16
SourceAttackMask_LiveNext0:
.a16
.i16
    lda.l $437A9C
    and #2
    beq SourceAttackMask_LiveNext1
    lda.l $411AE6
    and #255
    cmp #9
    beq SourceAttackMask_Test20
    brl SourceAttackMask_No
SourceAttackMask_Test20:
.a16
.i16
SourceAttackMask_LiveNext1:
.a16
.i16
    sec
    rtl
SourceAttackMask_No:
.a16
.i16
    clc
    rtl
SourceAttackMask_PhysicalLive:
.a16
.i16
    lda.l $437A9A
    and #1
    beq SourceAttackMask_PhysicalNext0
    lda.l $4119E6
    and #255
    cmp #9
    beq SourceAttackMask_Yes
SourceAttackMask_PhysicalNext0:
.a16
.i16
    lda.l $437A9A
    and #2
    beq SourceAttackMask_PhysicalNext1
    lda.l $411AE6
    and #255
    cmp #9
    beq SourceAttackMask_Yes
SourceAttackMask_PhysicalNext1:
.a16
.i16
    clc
    rtl
SourceAttackMask_Yes:
.a16
.i16
    sec
    rtl
SourceAttackMask_Motion:
.a16
.i16
    jsl SourceStandby_FaceLive
    bcs SourceAttackMask_MotionLive
    clc
    rtl
SourceAttackMask_MotionLive:
.a16
.i16
    lda.l $437A9C
    and #1
    bne SourceAttackMask_MotionPlayer0
    brl SourceAttackMask_MotionNext0
SourceAttackMask_MotionPlayer0:
.a16
.i16
    lda.l $437400
    cmp #$A770
    beq SourceAttackMask_TemplateValid0
    lda.l $437A96
    and #1
    bne SourceAttackMask_Test21
    brl SourceAttackMask_No
SourceAttackMask_Test21:
.a16
.i16
SourceAttackMask_TemplateValid0:
.a16
.i16
    lda.l SourceAttackOwned_Motion+4
    cmp #1
    beq SourceAttackMask_Test22
    brl SourceAttackMask_No
SourceAttackMask_Test22:
.a16
.i16
    lda.l SourceAttackOwned_Motion+6
    cmp #0
    beq SourceAttackMask_Test23
    brl SourceAttackMask_No
SourceAttackMask_Test23:
.a16
.i16
    lda.l SourceAttackOwned_Motion+12
    cmp #0
    beq SourceAttackMask_Test24
    brl SourceAttackMask_No
SourceAttackMask_Test24:
.a16
.i16
    lda.l SourceAttackOwned_Motion+10
    and #255
    cmp #2
    beq SourceAttackMask_Test25
    brl SourceAttackMask_No
SourceAttackMask_Test25:
.a16
.i16
    lda.l SourceAttackOwned_Motion+8
    bne SourceAttackMask_Test26
    brl SourceAttackMask_No
SourceAttackMask_Test26:
.a16
.i16
SourceAttackMask_MotionNext0:
.a16
.i16
    lda.l $437A9C
    and #2
    bne SourceAttackMask_MotionPlayer1
    brl SourceAttackMask_MotionNext1
SourceAttackMask_MotionPlayer1:
.a16
.i16
    lda.l $437480
    cmp #$A770
    beq SourceAttackMask_TemplateValid1
    lda.l $437A96
    and #2
    bne SourceAttackMask_Test27
    brl SourceAttackMask_No
SourceAttackMask_Test27:
.a16
.i16
SourceAttackMask_TemplateValid1:
.a16
.i16
    lda.l SourceAttackOwned_Motion+20
    cmp #1
    beq SourceAttackMask_Test28
    brl SourceAttackMask_No
SourceAttackMask_Test28:
.a16
.i16
    lda.l SourceAttackOwned_Motion+22
    cmp #0
    beq SourceAttackMask_Test29
    brl SourceAttackMask_No
SourceAttackMask_Test29:
.a16
.i16
    lda.l SourceAttackOwned_Motion+28
    cmp #133
    beq SourceAttackMask_Test30
    brl SourceAttackMask_No
SourceAttackMask_Test30:
.a16
.i16
    lda.l SourceAttackOwned_Motion+26
    and #255
    cmp #2
    beq SourceAttackMask_Test31
    brl SourceAttackMask_No
SourceAttackMask_Test31:
.a16
.i16
    lda.l SourceAttackOwned_Motion+24
    bne SourceAttackMask_Test32
    brl SourceAttackMask_No
SourceAttackMask_Test32:
.a16
.i16
SourceAttackMask_MotionNext1:
.a16
.i16
    sec
    rtl
SourceAttackMask_SealStage:
.a16
.i16
    php
    rep #$30
    pha
    phx
    phy
    phb
    lda.l SourceAttackOwned_Busy
    bne SourceAttackOwned_NmiSealDone
    lda #0
    sta.l $437B3C
    ldx #$53C0
    ldy #$7B40
    lda #31
    mvn $43,$43
    lda.l SourcePacket_ReadSeq
    sta.l SourceAttackOwned_ReadSeq
    lda.l SourcePacket_ReadStage
    sta.l SourceAttackOwned_ReadStage
    lda.l StageTimer_FieldCounter
    sta.l $437B3A
    lda #$A55E
    sta.l $437B3C
SourceAttackOwned_NmiSealDone:
.a16
.i16
    plb
    ply
    plx
    pla
    plp
    lda.l SourcePacket_ReadStage
    rtl

SourceAttackOwned_CaptureSeal:
.a16
.i16
    php
    rep #$30
    pha
    phx
    lda.l SourceAttackOwned_Busy
    ora.l SourcePacket_CopyBusy
    beq SourceAttackOwned_SealFree
    brl SourceAttackOwned_SealDone
SourceAttackOwned_SealFree:
.a16
.i16
    lda #1
    sta.l SourceAttackOwned_Busy
    lda #0
    sta.l $437B3C
    lda.l StageTimer_FieldCounter
    sta.l $437B3A
    lda.l $434E7E
    cmp #$4D50
    beq SourceAttackOwned_SealMagic
    brl SourceAttackOwned_SealReject
SourceAttackOwned_SealMagic:
.a16
.i16
    lda.l $434E7C
    sta.l SourceAttackOwned_ReadSeq
    and #1
    beq SourceAttackOwned_SealEven
    brl SourceAttackOwned_SealReject
SourceAttackOwned_SealEven:
.a16
.i16
    lda.l $434E2C
    sta.l SourceAttackOwned_ReadStage
    lda.l $434E34
    sta.l SourceAttackOwned_Motion+0
    lda.l $434E3C
    sta.l SourceAttackOwned_Motion+2
    lda.l $434E40
    sta.l SourceAttackOwned_Motion+4
    lda.l $434E42
    sta.l SourceAttackOwned_Motion+6
    lda.l $434E44
    sta.l SourceAttackOwned_Motion+8
    lda.l $434E4A
    sta.l SourceAttackOwned_Motion+10
    lda.l $434E9C
    sta.l SourceAttackOwned_Motion+12
    lda.l $434E36
    sta.l SourceAttackOwned_Motion+14
    lda.l $434E58
    sta.l SourceAttackOwned_Motion+16
    lda.l $434E60
    sta.l SourceAttackOwned_Motion+18
    lda.l $434E64
    sta.l SourceAttackOwned_Motion+20
    lda.l $434E66
    sta.l SourceAttackOwned_Motion+22
    lda.l $434E68
    sta.l SourceAttackOwned_Motion+24
    lda.l $434E6E
    sta.l SourceAttackOwned_Motion+26
    lda.l $434E9E
    sta.l SourceAttackOwned_Motion+28
    lda.l $434E5A
    sta.l SourceAttackOwned_Motion+30
    lda.l $434E7C
    cmp.l SourceAttackOwned_ReadSeq
    bne SourceAttackOwned_SealReject
    lda.l $434E7E
    cmp #$4D50
    bne SourceAttackOwned_SealReject
    lda.l StageTimer_FieldCounter
    cmp.l $437B3A
    bne SourceAttackOwned_SealReject
    lda #$A55E
    sta.l $437B3C
SourceAttackOwned_SealReject:
.a16
.i16
    lda #0
    sta.l SourceAttackOwned_Busy
SourceAttackOwned_SealDone:
.a16
.i16
    plx
    pla
    plp
    rtl

SourceAttackMask_SeedHigh:
.a16
.i16
    ldy #0
SourceAttackMask_SeedNext:
.a16
.i16
    tya
    lsr a
    lsr a
    tax
    lda.l SourceAttackOwned_Image+512,x
    and #255
    sta.l $437B3E
    tya
    and #3
    tax
    beq SourceAttackMask_SeedStore
SourceAttackMask_SeedShift:
.a16
.i16
    lda.l $437B3E
    lsr a
    lsr a
    sta.l $437B3E
    dex
    bne SourceAttackMask_SeedShift
SourceAttackMask_SeedStore:
.a16
.i16
    lda.l $437B3E
    and #3
    tyx
    sep #$20
.a8
    sta.l SourceAttackOwned_High,x
    rep #$30
.a16
.i16
    iny
    jsr SourceLayout_SeedCompare
    bcc SourceAttackMask_SeedNext
    rtl

; Foreground-only: retain all old/new pins while the other accepted attack
; awaits its template. No resource mutation or gameplay/input delay.
SourceAttackJoint_Defer:
.a16
.i16
    php
    rep #$30
    pha
    lda.l SourceAttackOwned_InitMagic
    cmp #$B077
    bne SourceAttackJoint_No
    lda.l SourceAttackOwned_Hold
    cmp #1
    bne SourceAttackJoint_No
    lda.l $437A98
    cmp.l $437A9A
    bne SourceAttackJoint_No
    cmp #1
    beq SourceAttackJoint_WaitP2
    cmp #2
    bne SourceAttackJoint_No
    lda.l $4119E6
    and #255
    cmp #9
    bne SourceAttackJoint_No
    lda.l SourceAttackTemplate_Base
    cmp #SourceAttackTemplate_Magic
    beq SourceAttackJoint_No
    bra SourceAttackJoint_Active
SourceAttackJoint_WaitP2:
.a16
.i16
    lda.l $411AE6
    and #255
    cmp #9
    bne SourceAttackJoint_No
    lda.l SourceAttackTemplate_Base+128
    cmp #SourceAttackTemplate_Magic
    beq SourceAttackJoint_No
SourceAttackJoint_Active:
.a16
.i16
    jsl SourceAttackMask_PhysicalLive
    bcc SourceAttackJoint_No
    lda.l SourceNextScene_Low
    cmp.l SourceAttackOwned_PhysicalLow
    bne SourceAttackJoint_No
    lda.l SourceNextScene_High
    cmp.l SourceAttackOwned_PhysicalHigh
    bne SourceAttackJoint_No
    pla
    plp
    sec
    rtl
SourceAttackJoint_No:
.a16
.i16
    pla
    plp
    clc
    rtl

; Extend the existing guarded relay turn to an exact accepted pending attack0.
; X is the normal player's32-byte desired-record offset, preserved.
SourceAttackOwned_PendingWarmRole:
.a16
.i16
    lda.l SourceVisual_State+30,x
    and #255
    cmp #2
    bcc SourceAttackOwned_PendingWarmYes
    bne SourceAttackOwned_PendingWarmNo
    lda.l SourceVisual_State+6,x
    cmp #1
    bne SourceAttackOwned_PendingWarmNo
    lda.l SourceVisual_State,x
    cmp #781
    bne SourceAttackOwned_PendingWarmNo
    lda.l SourceVisual_State+28,x
    and #255
    bne SourceAttackOwned_PendingWarmNo
SourceAttackOwned_PendingWarmYes:
.a16
.i16
    sec
    rtl
SourceAttackOwned_PendingWarmNo:
.a16
.i16
    clc
    rtl

; A completed old jump/action picture does not make the current grounded,
; coherently accepted exact pending attack a jump. Outer native/peer jump,
; stage, binding, mirror-height/profile and producer-sequence checks remain.
SourceAttackOwned_PendingWarmPicture:
.a16
.i16
    and #255
    cmp #2
    bcc SourceAttackOwned_PendingWarmPictureYes
    lda.l SourceVisual_State+30,x
    and #255
    cmp #2
    bne SourceAttackOwned_PendingWarmPictureNo
    jsl SourceAttackOwned_PendingWarmRole
    rtl
SourceAttackOwned_PendingWarmPictureYes:
.a16
.i16
    sec
    rtl
SourceAttackOwned_PendingWarmPictureNo:
.a16
.i16
    clc
    rtl

; A private immutable packet is independent of the ordinary scene's pending
; flag. Retry it after DMA retirement through all existing transport guards.
SourceAttackOwned_HasLatePacket:
.a16
.i16
    lda.l SourcePacket_NmiPending
    cmp #1
    beq SourceAttackOwned_LatePacketYes
    lda.l SourceAttackOwned_InitMagic
    cmp #$B077
    bne SourceAttackOwned_LatePacketNo
    lda.l SourceAttackOwned_State
    cmp #1
    beq SourceAttackOwned_LatePacketYes
SourceAttackOwned_LatePacketNo:
.a16
.i16
    lda #0
    rtl
SourceAttackOwned_LatePacketYes:
.a16
.i16
    lda #1
    rtl

SourceStandby_Header:
    .db $16,$02,$00,$00,$62,$00,$68,$00,$17,$00,$65,$00,$0A,$00,$01,$00
    .db $0D,$2B,$00,$00,$67,$04,$00,$00
SourceStandby_Pieces:
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
SourceStandby_State:
    .db $0D,$03,$00,$00,$01,$00,$02,$00,$00,$00,$00,$00,$00,$00,$01,$00
    .db $00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$16,$02,$01
SourceStandby_TemplateHeader:
    .db $00,$00,$00,$00,$16,$00,$16,$02,$00,$00,$D8,$01,$00,$02,$80,$00
    .db $96,$00,$00,$00,$00,$00,$0D,$03
SourceStandby_PiecesLong = $3D0000 | (SourceStandby_Pieces & $FFFF)
; Independent default-stage standby pose. No input, normal desired-state,
; Ready, DMA, OAM, actor/world, or physical-ACK writes occur here.
; Both complete images must exist before speculative resources can be pinned.
; Header/pieces are compiler-owned metadata, checked against the immutable MSU.
SourceStandby_Target = $437B64
SourceStandby_Seq = $437B66
SourceStandby_Pin = $437B68
SourceStandby_Lease = $437B6A
SourceStandby_Template = $437B6C
SourceStandby_Piece = $437B6E
SourceStandby_Palette = $437B70
SourceStandby_PalRecord = $437B72
SourceStandby_Block = $437B74
SourceStandby_Tile = $437B76
SourceStandby_Attr = $437B78
SourceStandby_PosX = $437B7A
SourceStandby_PosY = $437B7C
SourceStandby_Map = $437B80 ; ten validated physical cache slots
SourceStandby_FaceMask = $437B8E
SourceStandby_Result = $437B8A
SourceStandby_Missing = $437B8C
SourceStandby_Service:
.a16
.i16
    jsl SourceWarm_SettleThenPrepare
    jml SourceVisual_ServiceNpcsAfterSubmit
SourceStandby_Prepare:
.a16
.i16
    php
    rep #$30
    pha
    phx
    phy
    phb
    cld
    lda #0
    sta.l SourceStandby_Result
    sta.l SourceStandby_Target
    lda.l SourceAttackOwned_InitMagic
    cmp #$B077
    beq SourceStandby_G1
    brl SourceStandby_Done
SourceStandby_G1:
.a16
.i16
    lda.l SourceVisual_CompletedMagic
    cmp #$C04D
    beq SourceStandby_G2
    brl SourceStandby_Done
SourceStandby_G2:
.a16
.i16
    lda.l SVActor_Magic
    cmp #$AC19
    beq SourceStandby_G3
    brl SourceStandby_Done
SourceStandby_G3:
.a16
.i16
    lda.l SourceInput_Magic
    cmp #$1A60
    beq SourceStandby_G4
    brl SourceStandby_Done
SourceStandby_G4:
.a16
.i16
    lda.l Game_State
    cmp #$0000
    beq SourceStandby_G5
    brl SourceStandby_Done
SourceStandby_G5:
.a16
.i16
    lda.l Game_StageIndex
    cmp #$0000
    beq SourceStandby_G6
    brl SourceStandby_Done
SourceStandby_G6:
.a16
.i16
    lda.l Screen_PosX
    cmp #$0000
    beq SourceStandby_G7
    brl SourceStandby_Done
SourceStandby_G7:
.a16
.i16
    lda.l SourceAttackOwned_State
    cmp #$0000
    beq SourceStandby_G8
    brl SourceStandby_Done
SourceStandby_G8:
.a16
.i16
    lda.l SourceAttackOwned_Hold
    cmp #$0000
    beq SourceStandby_G9
    brl SourceStandby_Done
SourceStandby_G9:
.a16
.i16
    lda.l SourceAttackOwned_Busy
    cmp #$0000
    beq SourceStandby_G10
    brl SourceStandby_Done
SourceStandby_G10:
.a16
.i16
    lda.l SourcePacket_CopyBusy
    cmp #$0000
    beq SourceStandby_G11
    brl SourceStandby_Done
SourceStandby_G11:
.a16
.i16
    jsl SourceRewarm_Closed
    cmp #$0000
    beq SourceStandby_G12
    brl SourceStandby_Done
SourceStandby_G12:
.a16
.i16
    lda.l $437A96
    cmp #$0000
    beq SourceStandby_G13
    brl SourceStandby_Done
SourceStandby_G13:
.a16
.i16
    lda.l $437A98
    cmp #$0000
    beq SourceStandby_G14
    brl SourceStandby_Done
SourceStandby_G14:
.a16
.i16
    jsl SourceRewarm_PhysicalMask
    cmp #$0000
    beq SourceStandby_G15
    brl SourceStandby_Done
SourceStandby_G15:
.a16
.i16
    lda.l SourceVisual_CompletedValid
    cmp #$0001
    beq SourceStandby_G16
    brl SourceStandby_Done
SourceStandby_G16:
.a16
.i16
    lda.l SVActor_Data+SVActor_Valid
    cmp #$0001
    beq SourceStandby_G17
    brl SourceStandby_Done
SourceStandby_G17:
.a16
.i16
    lda.l Game_CampaignId
    and #255
    cmp #3
    beq SourceStandby_G18
    brl SourceStandby_Done
SourceStandby_G18:
.a16
.i16
    lda.l $7E175E
    cmp #$0002
    beq SourceStandby_G19
    brl SourceStandby_Done
SourceStandby_G19:
.a16
.i16
    lda.l $7E1760
    cmp #$0001
    beq SourceStandby_G20
    brl SourceStandby_Done
SourceStandby_G20:
.a16
.i16
    lda.l $7E46DC
    cmp #$0001
    beq SourceStandby_G21
    brl SourceStandby_Done
SourceStandby_G21:
.a16
.i16
    lda.l $7E46DE
    cmp #$0000
    beq SourceStandby_G22
    brl SourceStandby_Done
SourceStandby_G22:
.a16
.i16
    lda.l $434E7E
    cmp #$4D50
    beq SourceStandby_G23
    brl SourceStandby_Done
SourceStandby_G23:
.a16
.i16
    lda.l $434E2C
    cmp #$0000
    beq SourceStandby_G24
    brl SourceStandby_Done
SourceStandby_G24:
.a16
.i16
    lda.l $434E7C
    sta.l SourceStandby_Seq
    and #1
    beq SourceStandby_G25
    brl SourceStandby_Done
SourceStandby_G25:
.a16
.i16
    lda.l SourcePrefetch_Cursor
    cmp #10
    bcs SourceStandby_G26
    brl SourceStandby_Done
SourceStandby_G26:
.a16
.i16
    lda.l SourcePrefetch_PhysicalPending
    cmp #0
    beq SourceStandby_G27
    brl SourceStandby_Done
SourceStandby_G27:
.a16
.i16
    lda.l $7E0A00+CHAR_INPUT_DRIVEN
    and #255
    cmp #1
    beq SourceStandby_G28
    brl SourceStandby_Done
SourceStandby_G28:
.a16
.i16
    lda.l $7E0A00+CHAR_ROSTER_INDEX
    and #255
    cmp #22
    beq SourceStandby_G29
    brl SourceStandby_Done
SourceStandby_G29:
.a16
.i16
    lda.l $7E0A00+CHAR_MAP_INDEX
    and #255
    cmp #0
    beq SourceStandby_G30
    brl SourceStandby_Done
SourceStandby_G30:
.a16
.i16
    lda.l $7E0A00+CHAR_HP
    and #255
    bne SourceStandby_G31
    brl SourceStandby_Done
SourceStandby_G31:
.a16
.i16
    lda.l StageBounds_State+0
    cmp #0
    beq SourceStandby_G32
    brl SourceStandby_Done
SourceStandby_G32:
.a16
.i16
    lda.l $434E40
    cmp #1
    beq SourceStandby_G33
    brl SourceStandby_Done
SourceStandby_G33:
.a16
.i16
    lda.l $434E42
    cmp #0
    beq SourceStandby_G34
    brl SourceStandby_Done
SourceStandby_G34:
.a16
.i16
    lda.l $434E4A
    and #255
    cmp #2
    beq SourceStandby_G35
    brl SourceStandby_Done
SourceStandby_G35:
.a16
.i16
    lda.l $434E50
    and #255
    cmp #0
    beq SourceStandby_G36
    brl SourceStandby_Done
SourceStandby_G36:
.a16
.i16
    lda.l $434E54
    and #255
    cmp #8
    beq SourceStandby_G37
    brl SourceStandby_Done
SourceStandby_G37:
.a16
.i16
    lda.l $434E36
    cmp #188
    beq SourceStandby_G38
    brl SourceStandby_Done
SourceStandby_G38:
.a16
.i16
    lda.l $434E44
    bne SourceStandby_G39
    brl SourceStandby_Done
SourceStandby_G39:
.a16
.i16
    lda.l $434E44
    cmp #256
    bcc SourceStandby_G40
    brl SourceStandby_Done
SourceStandby_G40:
.a16
.i16
    lda.l $434E9C
    cmp #0
    beq SourceStandby_G41
    brl SourceStandby_Done
SourceStandby_G41:
.a16
.i16
SourceStandby_TemplateCheck0:
.a16
.i16
    lda.l SourceAttackTemplate_Base+0
    cmp #$A770
    beq SourceStandby_Have0
    lda.l SourceStandby_Target
    ora #1
    sta.l SourceStandby_Target
SourceStandby_Have0:
.a16
.i16
    lda.l $7E0A85+CHAR_INPUT_DRIVEN
    and #255
    cmp #1
    beq SourceStandby_G42
    brl SourceStandby_Done
SourceStandby_G42:
.a16
.i16
    lda.l $7E0A85+CHAR_ROSTER_INDEX
    and #255
    cmp #22
    beq SourceStandby_G43
    brl SourceStandby_Done
SourceStandby_G43:
.a16
.i16
    lda.l $7E0A85+CHAR_MAP_INDEX
    and #255
    cmp #0
    beq SourceStandby_G44
    brl SourceStandby_Done
SourceStandby_G44:
.a16
.i16
    lda.l $7E0A85+CHAR_HP
    and #255
    bne SourceStandby_G45
    brl SourceStandby_Done
SourceStandby_G45:
.a16
.i16
    lda.l StageBounds_State+133
    cmp #0
    beq SourceStandby_G46
    brl SourceStandby_Done
SourceStandby_G46:
.a16
.i16
    lda.l $434E64
    cmp #1
    beq SourceStandby_G47
    brl SourceStandby_Done
SourceStandby_G47:
.a16
.i16
    lda.l $434E66
    cmp #0
    beq SourceStandby_G48
    brl SourceStandby_Done
SourceStandby_G48:
.a16
.i16
    lda.l $434E6E
    and #255
    cmp #2
    beq SourceStandby_G49
    brl SourceStandby_Done
SourceStandby_G49:
.a16
.i16
    lda.l $434E74
    and #255
    cmp #0
    beq SourceStandby_G50
    brl SourceStandby_Done
SourceStandby_G50:
.a16
.i16
    lda.l $434E78
    and #255
    cmp #8
    beq SourceStandby_G51
    brl SourceStandby_Done
SourceStandby_G51:
.a16
.i16
    lda.l $434E5A
    cmp #188
    beq SourceStandby_G52
    brl SourceStandby_Done
SourceStandby_G52:
.a16
.i16
    lda.l $434E68
    bne SourceStandby_G53
    brl SourceStandby_Done
SourceStandby_G53:
.a16
.i16
    lda.l $434E68
    cmp #256
    bcc SourceStandby_G54
    brl SourceStandby_Done
SourceStandby_G54:
.a16
.i16
    lda.l $434E9E
    cmp #133
    beq SourceStandby_G55
    brl SourceStandby_Done
SourceStandby_G55:
.a16
.i16
SourceStandby_TemplateCheck1:
.a16
.i16
    lda.l SourceAttackTemplate_Base+128
    cmp #$A770
    beq SourceStandby_Have1
    lda.l SourceStandby_Target
    ora #2
    sta.l SourceStandby_Target
SourceStandby_Have1:
.a16
.i16
    lda.l SourceStandby_Target
    bne SourceStandby_G56
    brl SourceStandby_Done
SourceStandby_G56:
.a16
.i16
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    sta.l SourceStandby_Pin
    ; Never compete with a still-unpublished first NPC picture.
    lda.l SVActor_LoadOwner
    cmp #3
    bcc SourceStandby_NoFirstNpc
    cmp #7
    bcs SourceStandby_NoFirstNpc
    dec a
    dec a
    asl a
    tax
    lda.l SVActor_Bases,x
    tax
    lda.l SVActor_Data+SVActor_Valid,x
    cmp #1
    beq SourceStandby_G57
    brl SourceStandby_Done
SourceStandby_G57:
.a16
.i16
SourceStandby_NoFirstNpc:
.a16
.i16
    ldx #0
SourceStandby_EmptyBlocks:
.a16
.i16
    lda.l SVActor_HeldBlocks,x
    and.l SourceStandby_Pin
    beq SourceStandby_G58
    brl SourceStandby_Done
SourceStandby_G58:
.a16
.i16
    txa
    clc
    adc #8
    tax
    cpx #512
    bcc SourceStandby_EmptyBlocks
    ldx #0
SourceStandby_EmptyPalettes:
.a16
.i16
    lda.l SVActor_HeldPalettes,x
    and.l SourceStandby_Pin
    beq SourceStandby_G59
    brl SourceStandby_Done
SourceStandby_G59:
.a16
.i16
    txa
    clc
    adc #8
    tax
    cpx #64
    bcc SourceStandby_EmptyPalettes
    ldx #0
SourceStandby_Queue:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$40
    beq SourceStandby_QueueNext
    lda.l DmaQueue+4,x
    and #255
    cmp #$41
    beq SourceStandby_G60
    brl SourceStandby_Done
SourceStandby_G60:
.a16
.i16
    lda.l DmaQueue+7,x
    and #255
    cmp #$43
    beq SourceStandby_PrivateOam
    cmp #$7E
    beq SourceStandby_LegacyOam
    brl SourceStandby_Done
SourceStandby_PrivateOam:
.a16
.i16
    lda.l DmaQueue+5,x
    cmp #$4F00
    beq SourceStandby_G61
    brl SourceStandby_Done
SourceStandby_G61:
.a16
.i16
    lda.l DmaQueue,x
    cmp #544
    beq SourceStandby_G62
    brl SourceStandby_Done
SourceStandby_G62:
.a16
.i16
    lda.l DmaQueue+2,x
    cmp #0
    beq SourceStandby_G63
    brl SourceStandby_Done
SourceStandby_G63:
.a16
.i16
    brl SourceStandby_QueueNext
SourceStandby_LegacyOam:
.a16
.i16
    lda.l DmaQueue+5,x
    cmp #$5100
    beq SourceStandby_QueueNext
    cmp #$5300
    beq SourceStandby_QueueNext
    brl SourceStandby_Done
SourceStandby_QueueNext:
.a16
.i16
    txa
    clc
    adc #8
    tax
    cpx #64
    bcc SourceStandby_Queue
    ldx #0
SourceStandby_FindPalette:
.a16
.i16
    lda.l SourceVisual_PaletteCache,x
    cmp #361
    bne SourceStandby_NextPalette
    lda.l SourceVisual_PaletteCache+3,x
    and #255
    cmp #1
    beq SourceStandby_PaletteFound
SourceStandby_NextPalette:
.a16
.i16
    txa
    clc
    adc #8
    tax
    cpx #64
    bcc SourceStandby_FindPalette
    brl SourceStandby_Done
SourceStandby_PaletteFound:
.a16
.i16
    txa
    sta.l SourceStandby_PalRecord
    lsr a
    lsr a
    lsr a
    sta.l SourceStandby_Palette
    lda #0
    sta.l SourceStandby_Piece
SourceStandby_FindPiece:
.a16
.i16
    lda.l SourceStandby_Piece
    asl a
    asl a
    asl a
    asl a
    tax
    lda.l SourceStandby_PiecesLong+12,x
    sta.l SourceStandby_Missing
    ldx #0
SourceStandby_FindBlock:
.a16
.i16
    lda.l SourceVisual_BlockCache,x
    cmp.l SourceStandby_Missing
    bne SourceStandby_NextBlock
    lda.l SourceVisual_BlockCache+2,x
    cmp #2
    beq SourceStandby_BlockFound
SourceStandby_NextBlock:
.a16
.i16
    txa
    clc
    adc #8
    tax
    cpx #512
    bcc SourceStandby_FindBlock
    brl SourceStandby_Done
SourceStandby_BlockFound:
.a16
.i16
    txa
    lsr a
    lsr a
    lsr a
    pha
    lda.l SourceStandby_Piece
    tax
    pla
    sep #$20
.a8
    sta.l SourceStandby_Map,x
    rep #$30
.a16
.i16
    lda.l SourceStandby_Piece
    inc a
    sta.l SourceStandby_Piece
    cmp #10
    bcc SourceStandby_FindPiece
    jsl SourceStandby_FreshScope
    bcs SourceStandby_G64
    brl SourceStandby_Done
SourceStandby_G64:
.a16
.i16
    lda.l Game_StageIndex
    cmp #0
    beq SourceStandby_G65
    brl SourceStandby_Done
SourceStandby_G65:
.a16
.i16
    ; All physical identities are ready. NMI cannot reallocate any cache row.
    ; Commit pins first, publish lease/template magic last, while writer-busy.
    lda #1
    sta.l SourceAttackOwned_Busy
    lda #0
    sta.l SourceStandby_Piece
SourceStandby_PinBlocks:
.a16
.i16
    lda.l SourceStandby_Piece
    tax
    lda.l SourceStandby_Map,x
    and #255
    asl a
    asl a
    asl a
    tax
    lda.l SVActor_HeldBlocks,x
    ora.l SourceStandby_Pin
    sta.l SVActor_HeldBlocks,x
    lda.l SourceStandby_Piece
    inc a
    sta.l SourceStandby_Piece
    cmp #10
    bcc SourceStandby_PinBlocks
    lda.l SourceStandby_PalRecord
    tax
    lda.l SVActor_HeldPalettes,x
    ora.l SourceStandby_Pin
    sta.l SVActor_HeldPalettes,x
    sep #$20
.a8
    lda #$30
    jsl StageFp_BG2OamAttr
    rep #$30
.a16
.i16
    and #255
    sta.l SourceStandby_Attr
    lda.l SourceStandby_Target
    and #1
    beq SourceStandby_Built0
    lda #0
    sta.l SourceStandby_Lease
    lda #0
    sta.l SourceStandby_Template
    jsr SourceStandby_BuildOne
SourceStandby_Built0:
.a16
.i16
    lda.l SourceStandby_Target
    and #2
    beq SourceStandby_Built1
    lda #1024
    sta.l SourceStandby_Lease
    lda #128
    sta.l SourceStandby_Template
    jsr SourceStandby_BuildOne
SourceStandby_Built1:
.a16
.i16
    lda.l SourceStandby_Target
    ora.l SourceStandby_FaceMask
    sta.l SourceStandby_FaceMask
    lda.l SourceStandby_Target
    sta.l SourceStandby_Result
    lda #0
    sta.l SourceAttackOwned_Busy
SourceStandby_Done:
.a16
.i16
    plb
    ply
    plx
    pla
    plp
    rtl
SourceStandby_BuildOne:
.a16
.i16
    lda.l SourceStandby_Lease
    tax
    lda #0
    sta.l $436C00,x
    sta.l $436C02,x
    lda #22
    sta.l $436C04,x
    lda #$0216
    sta.l $436C06,x
    lda #10
    sta.l $436C08,x
    lda #781
    sta.l $436C0A,x
    txa
    clc
    adc #$6C20
    tay
    ldx #SourceStandby_Header & $FFFF
    lda #23
    mvn $43,$3D
    lda.l SourceStandby_Lease
    clc
    adc #$6C38
    tay
    ldx #SourceStandby_State & $FFFF
    lda #31
    mvn $43,$3D
    lda.l SourceStandby_Lease
    tax
    lda.l SourceStandby_Palette
    inc a
    sta.l $436C48,x
    lda.l SourceStandby_Lease
    clc
    adc #$6C58
    tay
    ldx #SourceStandby_Pieces & $FFFF
    lda #159
    mvn $43,$3D
    lda.l SourceStandby_Template
    clc
    adc #$7400
    tay
    ldx #SourceStandby_TemplateHeader & $FFFF
    lda #23
    mvn $43,$3D
    lda #0
    sta.l SourceStandby_Piece
SourceStandby_FormatPiece:
.a16
.i16
    lda.l SourceStandby_Piece
    tax
    lda.l SourceStandby_Map,x
    and #255
    sta.l SourceStandby_Block
    and #7
    asl a
    sta.l SourceStandby_Tile
    lda.l SourceStandby_Block
    lsr a
    lsr a
    lsr a
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    clc
    adc.l SourceStandby_Tile
    sta.l SourceStandby_Tile
    lda.l SourceStandby_Piece
    clc
    adc.l SourceStandby_Lease
    tax
    lda.l SourceStandby_Block
    sep #$20
.a8
    sta.l $436CF8,x
    rep #$30
.a16
.i16
    lda.l SourceStandby_Piece
    asl a
    asl a
    asl a
    asl a
    tax
    lda.l SourceStandby_PiecesLong,x
    clc
    adc #128
    sta.l SourceStandby_PosX
    lda.l SourceStandby_PiecesLong+2,x
    clc
    adc #150
    sta.l SourceStandby_PosY
    txa
    clc
    adc.l SourceStandby_Lease
    tax
    lda.l SourceStandby_Tile
    sta.l $436C66,x
    lda.l SourceStandby_Piece
    asl a
    asl a
    clc
    adc.l SourceStandby_Template
    tax
    sep #$20
.a8
    lda.l SourceStandby_PosX
    sta.l $437420,x
    lda.l SourceStandby_PosY
    sta.l $437421,x
    lda.l SourceStandby_Tile
    sta.l $437422,x
    rep #$30
.a16
.i16
    lda.l SourceStandby_Palette
    asl a
    ora.l SourceStandby_Attr
    sta.l SourceStandby_Block
    lda.l SourceStandby_Tile
    xba
    and #1
    ora.l SourceStandby_Block
    sep #$20
.a8
    sta.l $437423,x
    rep #$30
.a16
.i16
    lda.l SourceStandby_Piece
    clc
    adc.l SourceStandby_Template
    tax
    lda #0
    sep #$20
.a8
    sta.l $437448,x
    rep #$30
.a16
.i16
    lda.l SourceStandby_Piece
    inc a
    sta.l SourceStandby_Piece
    cmp #10
    bcs SourceStandby_FormatDone
    brl SourceStandby_FormatPiece
SourceStandby_FormatDone:
.a16
.i16
    lda.l SourceStandby_Lease
    tax
    lda #$A66C
    sta.l $436C00,x
    lda.l SourceStandby_Template
    tax
    lda #$A770
    sta.l $437400,x
    rts

; Initialize both new foreground authorities before the original owner magic.
SourceStandby_Init:
.a16
.i16
    php
    pha
    lda #0
    sta.l SourceStandby_FaceMask
    sta.l $437BFE
    sta.l $437BA6
    sta.l $437BA8
    sta.l $437BAC
    jsl SourceLayout_Defaults
    sta.l $437BC8
    sta.l $437BCE
    pla
    plp
    sta.l SourceAttackOwned_InitMagic
    rtl
; Only standby-created face0 templates need this additional native-face fence.
; The original accepted-source-role predicate remains authoritative.
SourceStandby_FaceLive:
.a16
.i16
    jsl SourceAttackMask_PatchLive
    bcs SourceStandby_FaceCheck
    rtl
SourceStandby_FaceCheck:
.a16
.i16
    php
    pha
    lda #$FFFF
    nop
    and.l $437A9C
    and #1
    beq SourceStandby_FaceNext
    jsl SourceGroundRoot_Face0
    and #255
    cmp.l SourceAttackTemplate_Base+20
    bne SourceStandby_FaceNo
SourceStandby_FaceNext:
.a16
.i16
    lda #$FFFF
    nop
    and.l $437A9C
    and #2
    beq SourceStandby_FaceYes
    jsl SourceGroundRoot_Face1
    and #255
    cmp.l SourceAttackTemplate_Base+148
    bne SourceStandby_FaceNo
SourceStandby_FaceYes:
.a16
.i16
    pla
    plp
    sec
    rtl
SourceStandby_FaceNo:
.a16
.i16
    pla
    plp
    clc
    rtl

; Bounded optional first-pose media after ordinary foreground work.
SourcePrefetch_TailBatch:
    jsl Tad_StreamLatePump
    php
    rep #$30
    pha
    phx
    phy
    phb
    phd
    lda.l Game_CampaignId
    and #$00FF
    cmp #3
    beq SourcePrefetch_TailScope
    brl SourcePrefetch_TailDone
SourcePrefetch_TailScope:
.a16
.i16
    lda.l SourceAttackOwned_InitMagic
    cmp #$B077
    beq SourcePrefetch_TailInitialized
    brl SourcePrefetch_TailDone
SourcePrefetch_TailInitialized:
.a16
.i16
    lda #0
    sta.l $437BFE
    sta.l $437B9A
    jsl SourceRewarm_Closed
    cmp #0
    beq SourcePrefetch_WarmGuard0
    brl SourcePrefetch_TailDone
SourcePrefetch_WarmGuard0:
.a16
.i16
    lda.l Screen_PosX
    cmp #0
    beq SourcePrefetch_WarmGuard1
    brl SourcePrefetch_TailDone
SourcePrefetch_WarmGuard1:
.a16
.i16
    lda.l SourceVisual_CompletedValid
    cmp #1
    beq SourcePrefetch_WarmGuard2
    brl SourcePrefetch_TailDone
SourcePrefetch_WarmGuard2:
.a16
.i16
    lda.l SVActor_Data+SVActor_Valid
    cmp #1
    beq SourcePrefetch_WarmGuard3
    brl SourcePrefetch_TailDone
SourcePrefetch_WarmGuard3:
.a16
.i16
    lda.l SourceVisual_LatchedInput
    ora.l SourceVisual_LatchedInput2
    and #$F0FF
    beq SourcePrefetch_WarmGuard4
    brl SourcePrefetch_TailDone
SourcePrefetch_WarmGuard4:
.a16
.i16
    lda.l SourcePrefetch_PhysicalPending
    cmp #5
    bcc SourcePrefetch_WarmGuard5
    brl SourcePrefetch_TailDone
SourcePrefetch_WarmGuard5:
.a16
.i16
    lda.l SourceAttackTemplate_Base

    cmp #$A770

    bne SourcePrefetch_WarmNeeded

    lda.l SourceAttackTemplate_Base+128

    cmp #$A770

    bne SourcePrefetch_WarmNeeded

    brl SourcePrefetch_TailDone

SourcePrefetch_WarmNeeded:

.a16

.i16

    lda.l SourcePrefetch_Cursor
    cmp #10
    bcc SourcePrefetch_TailCursor
    lda #0
    sta.l SourcePrefetch_Cursor
SourcePrefetch_TailCursor:
.a16
.i16
    lda.l DmaQueue_BudgetTotal
    cmp #1601
    bcc SourcePrefetch_TailBudget
    brl SourcePrefetch_TailDone
SourcePrefetch_TailBudget:
.a16
.i16
    lda.l SourcePrefetch_Cursor
    pha
    lda #$B6A5
    sta.l $437BFE
    jsl SourceWarm_FirstAttempt
    pla
    cmp.l SourcePrefetch_Cursor
    beq SourcePrefetch_TailClear
    ldy #6
    lda.l $437B96
    beq SourceWarm_FullAttemptBudget
    dey
SourceWarm_FullAttemptBudget:
.a16
.i16
SourcePrefetch_TailNext:
.a16
.i16
    lda.l $437B9A
    cmp #5
    bcc SourceWarm_JobBudgetOpen
    brl SourcePrefetch_TailClear
SourceWarm_JobBudgetOpen:
.a16
.i16
    jsl SourceWarm_NoPendingInput
    bcs SourceWarm_TailMayRetry
    brl SourcePrefetch_TailClear
SourceWarm_TailMayRetry:
.a16
.i16
    lda.l SourcePrefetch_PhysicalPending
    cmp #5
    bcs SourcePrefetch_TailClear
    lda.l SourcePrefetch_Cursor
    cmp #10
    bcs SourcePrefetch_TailClear
    lda.l DmaQueue_BudgetTotal
    cmp #1601
    bcs SourcePrefetch_TailClear
    lda.l SourcePrefetch_Cursor
    jsl SourceWarm_TryOne
    bcc SourcePrefetch_TailStatus
    lda.l SourcePrefetch_Submitted
    inc a
    sta.l SourcePrefetch_Submitted
SourcePrefetch_TailStatus:
.a16
.i16
    lda.l SourcePrefetch_Plan+20
    beq SourceWarm_TailRetry
    lda.l SourcePrefetch_Cursor
    inc a
    cmp #22
    bcc SourcePrefetch_TailSave
    lda #0
SourcePrefetch_TailSave:
.a16
.i16
    sta.l SourcePrefetch_Cursor
SourceWarm_TailRetry:
.a16
.i16
    dey
    bne SourcePrefetch_TailNext
SourcePrefetch_TailClear:
.a16
.i16
    lda #0
    sta.l $437BFE
SourcePrefetch_TailDone:
.a16
.i16
    pld
    plb
    ply
    plx
    pla
    plp
    rtl

SourcePrefetch_BatchPending:
.a16
.i16
    php
    rep #$30
    pha
    lda.l SourcePrefetch_PhysicalPending
    beq SourcePrefetch_BatchPendingYes
    cmp #5
    bcs SourcePrefetch_BatchPendingNo
    lda.l SourceAttackOwned_InitMagic
    cmp #$B077
    bne SourcePrefetch_BatchPendingNo
    lda.l $437BFE
    cmp #$B6A5
    bne SourcePrefetch_BatchPendingNo
SourcePrefetch_BatchPendingYes:
.a16
.i16
    pla
    plp
    sec
    rtl
SourcePrefetch_BatchPendingNo:
.a16
.i16
    pla
    plp
    clc
    rtl

; Rejoin the existing planner only after authenticating a private type43.
SourcePrefetch_QueueBatchDispatch:
.a16
.i16
    cmp #$42
    beq SourcePrefetch_QueueBatchCgram
    cmp #$43
    bne SourcePrefetch_QueueBatchNo
    lda.l $437BFE
    cmp #$B6A5
    bne SourcePrefetch_QueueBatchNo
    jsl SourcePrefetch_ValidateJob
    bcc SourcePrefetch_QueueBatchNo
    rep #$20
    pla
    sep #$20
.a8
    pla
    rep #$20
.a16
    jml SourcePrefetch_PlanOnly__queue_add
SourcePrefetch_QueueBatchCgram:
.a16
.i16
    rep #$20
    pla
    sep #$20
.a8
    pla
    rep #$20
.a16
    jml SourcePrefetch_PlanOnly__guard33
SourcePrefetch_QueueBatchNo:
.a16
.i16
    rep #$20
    pla
    sep #$20
.a8
    pla
    rep #$20
.a16
    jml SourcePrefetch_PlanOnly__no

; Loading A6 rows are safe only when a matching live private descriptor
; authenticates the exact cache record. Never invent a completion cookie.
SourcePrefetch_BatchLoadingDispatch:
.a16
.i16
    lda.l SourceVisual_BlockCache+6,x
    cmp #1
    beq SourcePrefetch_BatchLoadingPresent
    cmp #2
    beq SourcePrefetch_BatchLoadingPresent
    cmp #$A702
    beq SourcePrefetch_BatchLoadingPresent
    cmp #$A602
    bne SourcePrefetch_BatchLoadingNo
    lda.l $437BFE
    cmp #$B6A5
    bne SourcePrefetch_BatchLoadingNo
    phx
    phy
    ldx #0
SourcePrefetch_BatchLoadingScan:
.a16
.i16
    jsl SourcePrefetch_ValidateJob
    bcc SourcePrefetch_BatchLoadingNext
    cmp 3,s
    beq SourcePrefetch_BatchLoadingFound
SourcePrefetch_BatchLoadingNext:
.a16
.i16
    txa
    clc
    adc #8
    tax
    cpx #64
    bcc SourcePrefetch_BatchLoadingScan
    ply
    plx
    bra SourcePrefetch_BatchLoadingNo
SourcePrefetch_BatchLoadingFound:
.a16
.i16
    ply
    plx
SourcePrefetch_BatchLoadingPresent:
.a16
.i16
    rep #$20
    pla
    sep #$20
.a8
    pla
    rep #$20
.a16
    jml SourcePrefetch_PlanOnly__present
SourcePrefetch_BatchLoadingNo:
.a16
.i16
    rep #$20
    pla
    sep #$20
.a8
    pla
    rep #$20
.a16
    jml SourcePrefetch_PlanOnly__no

SourceStandby_BudgetCompare:
.a16
.i16
    lda.l $437BFE
    cmp #$B6A5
    bne SourceStandby_BudgetOrdinary
    lda.l DmaQueue_BudgetTotal
    cmp #1601
    rtl
SourceStandby_BudgetOrdinary:
.a16
.i16
    lda.l DmaQueue_BudgetTotal
    cmp #1025
    rtl
SourceStandby_QueueBudget:
.a16
.i16
    jsl SourceStandby_BudgetCompare
    bcs SourceStandby_QueueNo
    rep #$20
    pla
    sep #$20
.a8
    pla
    rep #$20
.a16
    jml SourcePrefetch_PlanOnly__guard47
SourceStandby_QueueNo:
.a16
.i16
    rep #$20
    pla
    sep #$20
.a8
    pla
    rep #$20
.a16
    jml SourcePrefetch_PlanOnly__no

; Read-only cache/NPC/free-slot scan precedes fresh source/input/queue proof.

SourceWarm_Dispatch:
.a16
.i16
    php
    pha
    lda.l $437BFE
    cmp #$B6A5
    beq SourceWarm_DispatchYes
    pla
    plp
    jml SourcePrefetch_PlanOnly
SourceWarm_DispatchYes:
.a16
.i16
    pla
    plp
    jml SourceWarm_Plan
SourceWarm_Plan:
.a16
.i16
    php
    rep #$30
    cld
    pha
    phx
    phy
    phb
    phd
    lda #0
    sta.l $437B94
    sta.l $437B98
    lda 8,s
    cmp #10
    bcc SourceWarm_Index
    brl SourceWarm_Plan__no
SourceWarm_Index:
.a16
.i16
    lda.l $437BFE
    cmp #$B6A5
    beq SourceWarm_Authorized
    brl SourceWarm_Plan__no
SourceWarm_Authorized:
.a16
.i16
    jsl SourceRewarm_Closed
    ora.l Screen_PosX
    beq SourceWarm_Cold
    brl SourceWarm_Plan__no
SourceWarm_Cold:
.a16
.i16
    lda.l $434E50
    ora.l $434E74
    and #255
    beq SourceWarm_Idle
    brl SourceWarm_Plan__no
SourceWarm_Idle:
.a16
.i16
    lda #0
    sta.l SourcePrefetch_Plan+20
    lda 8,s
    asl a
    tax
    lda.l SourcePrefetch_HotIds,x
    sta.l SourcePrefetch_Plan
    lda.l SourcePrefetch_HotBanks,x
    sta.l SourcePrefetch_Plan+2
    lda.l SourcePrefetch_HotAddresses,x
    sta.l SourcePrefetch_Plan+4
SourceWarm_Plan__guard49:
.a16
.i16
    ldx #0
SourceWarm_Plan__cache:
.a16
.i16
    lda.l SourceVisual_BlockCache+2,x
    beq SourceWarm_Plan__cache_next
    cmp #1
    beq SourceWarm_Plan__pending
    cmp #2
    beq SourceWarm_Plan__guard50
    brl SourceWarm_Plan__no
SourceWarm_Plan__guard50:
.a16
.i16
    bra SourceWarm_Plan__present
SourceWarm_Plan__pending:
.a16
.i16
    lda.l SourceVisual_BlockCache+5,x
    and #$00FF
    cmp #4
    beq SourceWarm_Plan__guard51
    brl SourceWarm_Plan__no
SourceWarm_Plan__guard51:
.a16
.i16
    jsl SourceWarm_LoadingDispatch
    nop
    nop
    nop
    nop
    nop
    nop
    nop
    nop
    nop
    nop
    nop
    nop
    nop
    nop
    nop
    nop
    nop
    nop
SourceWarm_Plan__guard52:
.a16
.i16
SourceWarm_Plan__present:
.a16
.i16
    lda.l SourceVisual_BlockCache,x
    cmp.l SourcePrefetch_Plan
    bne SourceWarm_Plan__guard53
    lda #1
    sta.l SourcePrefetch_Plan+20
    brl SourceWarm_Plan__no
SourceWarm_Plan__guard53:
.a16
.i16
SourceWarm_Plan__cache_next:
.a16
.i16
    txa
    clc
    adc #8
    tax
    cpx #512
    bcs SourceWarm_Plan__cache_done
    brl SourceWarm_Plan__cache
SourceWarm_Plan__cache_done:
.a16
.i16
    lda #64
    sta.l SourcePrefetch_Plan+24
    lda #266
    sta.l SourcePrefetch_Plan+26
    lda #1280
    sta.l SourcePrefetch_Plan+28
SourceWarm_Plan__npc:
.a16
.i16
    lda.l SourcePrefetch_Plan+24
    tax
    lda.l SourceVisual_State+6,x
    beq SourceWarm_Plan__npc_next
    lda.l SourcePrefetch_Plan+26
    tax
    lda.l $7E0A00+CHAR_HP,x
    and #$00FF
    beq SourceWarm_Plan__npc_next
    lda.l SourceVisual_Sa1OwnerPolicy,x
    and #$00FF
    cmp #2
    bne SourceWarm_Plan__npc_next
    lda.l SourcePrefetch_Plan+28
    tax
    lda.l SVActor_Data+SVActor_Valid,x
    cmp #1
    beq SourceWarm_Plan__guard54
    brl SourceWarm_Plan__no
SourceWarm_Plan__guard54:
.a16
.i16
SourceWarm_Plan__npc_next:
.a16
.i16
    lda.l SourcePrefetch_Plan+26
    clc
    adc #133
    sta.l SourcePrefetch_Plan+26
    lda.l SourcePrefetch_Plan+28
    clc
    adc #1280
    sta.l SourcePrefetch_Plan+28
    lda.l SourcePrefetch_Plan+24
    clc
    adc #32
    sta.l SourcePrefetch_Plan+24
    cmp #192
    bcs SourceWarm_Plan__find_empty
    brl SourceWarm_Plan__npc
SourceWarm_Plan__find_empty:
.a16
.i16
    ldx #504
SourceWarm_Plan__empty:
.a16
.i16
    lda.l SourceVisual_BlockCache+2,x
    bne SourceWarm_Plan__empty_next
    lda.l SourceVisual_BlockCache+4,x
    and #$00FF
    bne SourceWarm_Plan__empty_next
    lda.l SVActor_HeldBlocks,x
    ora.l SVActor_OldBlocks,x
    and #$00FF
    beq SourceWarm_Plan__found
SourceWarm_Plan__empty_next:
.a16
.i16
    txa
    sec
    sbc #8
    bcc SourceWarm_Plan__no_near
    tax
    bra SourceWarm_Plan__empty
SourceWarm_Plan__no_near:
.a16
.i16
    brl SourceWarm_Plan__no
SourceWarm_Plan__found:
.a16
.i16
    txa
    sta.l SourcePrefetch_Plan+6
    lsr a
    lsr a
    lsr a
    sta.l SourcePrefetch_Plan+8
    lda 8,s
    cmp #22
    bcc SourceWarm_Plan__guard0
    brl SourceWarm_Plan__no
SourceWarm_Plan__guard0:
.a16
.i16
    lda.l $7E46DE
    beq SourceWarm_Plan__guard1
    brl SourceWarm_Plan__no
SourceWarm_Plan__guard1:
.a16
.i16
    jsr SourceWarm_Scope
    bcs SourceWarm_Plan__guard2
    brl SourceWarm_Plan__no
SourceWarm_Plan__guard2:
.a16
.i16
    lda.l Game_StageIndex
    beq SourceWarm_Plan__guard3
    brl SourceWarm_Plan__no
SourceWarm_Plan__guard3:
.a16
.i16
    lda.l Nmi_FrameBusy
    and #$00FF
    cmp #2
    bcc SourceWarm_Plan__guard4
    brl SourceWarm_Plan__no
SourceWarm_Plan__guard4:
.a16
.i16
    jsl SourcePrefetch_BatchPending
    bcs SourceWarm_Plan__guard5
    brl SourceWarm_Plan__no
SourceWarm_Plan__guard5:
.a16
.i16
    lda.l $7E0A00+0+CHAR_INPUT_DRIVEN
    and #$00FF
    cmp #1
    beq SourceWarm_Plan__guard6
    brl SourceWarm_Plan__no
SourceWarm_Plan__guard6:
.a16
.i16
    lda.l $7E0A00+0+CHAR_ROSTER_INDEX
    and #$00FF
    cmp #22
    beq SourceWarm_Plan__guard7
    brl SourceWarm_Plan__no
SourceWarm_Plan__guard7:
.a16
.i16
    lda.l $7E0A00+0+CHAR_MAP_INDEX
    and #$00FF
    cmp #0
    beq SourceWarm_Plan__guard8
    brl SourceWarm_Plan__no
SourceWarm_Plan__guard8:
.a16
.i16
    lda.l $7E0A00+0+CHAR_HP
    and #$00FF
    bne SourceWarm_Plan__guard9
    brl SourceWarm_Plan__no
SourceWarm_Plan__guard9:
.a16
.i16
    lda.l $7E0A00+0+CHAR_SELECTED
    and #$00FF
    cmp #3
    bcc SourceWarm_Plan__guard10
    brl SourceWarm_Plan__no
SourceWarm_Plan__guard10:
.a16
.i16
    lda.l SourceVisual_Sa1OwnerPolicy+0
    and #$00FF
    cmp #2
    beq SourceWarm_Plan__guard11
    brl SourceWarm_Plan__no
SourceWarm_Plan__guard11:
.a16
.i16
SourceWarm_Plan__guard15:
.a16
.i16
    lda.l $7E0A00+133+CHAR_INPUT_DRIVEN
    and #$00FF
    cmp #1
    beq SourceWarm_Plan__guard16
    brl SourceWarm_Plan__no
SourceWarm_Plan__guard16:
.a16
.i16
    lda.l $7E0A00+133+CHAR_ROSTER_INDEX
    and #$00FF
    cmp #22
    beq SourceWarm_Plan__guard17
    brl SourceWarm_Plan__no
SourceWarm_Plan__guard17:
.a16
.i16
    lda.l $7E0A00+133+CHAR_MAP_INDEX
    and #$00FF
    cmp #0
    beq SourceWarm_Plan__guard18
    brl SourceWarm_Plan__no
SourceWarm_Plan__guard18:
.a16
.i16
    lda.l $7E0A00+133+CHAR_HP
    and #$00FF
    bne SourceWarm_Plan__guard19
    brl SourceWarm_Plan__no
SourceWarm_Plan__guard19:
.a16
.i16
    lda.l $7E0A00+133+CHAR_SELECTED
    and #$00FF
    cmp #3
    bcc SourceWarm_Plan__guard20
    brl SourceWarm_Plan__no
SourceWarm_Plan__guard20:
.a16
.i16
    lda.l SourceVisual_Sa1OwnerPolicy+133
    and #$00FF
    cmp #2
    beq SourceWarm_Plan__guard21
    brl SourceWarm_Plan__no
SourceWarm_Plan__guard21:
.a16
.i16
SourceWarm_Plan__guard25:
.a16
.i16
    lda.l SourceVisual_CompletedValid
    cmp #1
    beq SourceWarm_Plan__guard26
    brl SourceWarm_Plan__no
SourceWarm_Plan__guard26:
.a16
.i16
    lda.l SVActor_Data+SVActor_Valid
    cmp #1
    beq SourceWarm_Plan__guard27
    brl SourceWarm_Plan__no
SourceWarm_Plan__guard27:
.a16
.i16
    lda.l $434E7E
    cmp #$4D50
    beq SourceWarm_Plan__snapshot_magic
    brl SourceWarm_Plan__no
SourceWarm_Plan__snapshot_magic:
.a16
.i16
    lda.l $434E2C
    cmp #0
    beq SourceWarm_Plan__snapshot0
    brl SourceWarm_Plan__no
SourceWarm_Plan__snapshot0:
.a16
.i16
    lda.l $434E9C
    cmp #0
    beq SourceWarm_Plan__snapshot1
    brl SourceWarm_Plan__no
SourceWarm_Plan__snapshot1:
.a16
.i16
    lda.l $434E9E
    cmp #133
    beq SourceWarm_Plan__snapshot2
    brl SourceWarm_Plan__no
SourceWarm_Plan__snapshot2:
.a16
.i16
    lda.l $434E3C
    cmp #9
    beq SourceWarm_Plan__snapshot3
    brl SourceWarm_Plan__no
SourceWarm_Plan__snapshot3:
.a16
.i16
    lda.l $434E40
    cmp #1
    beq SourceWarm_Plan__snapshot4
    brl SourceWarm_Plan__no
SourceWarm_Plan__snapshot4:
.a16
.i16
    lda.l $434E42
    cmp #0
    beq SourceWarm_Plan__snapshot5
    brl SourceWarm_Plan__no
SourceWarm_Plan__snapshot5:
.a16
.i16
    lda.l $434E4A
    and #$00FF ; snapshot policy/role is a packed byte mirror
    cmp #2
    beq SourceWarm_Plan__snapshot6
    brl SourceWarm_Plan__no
SourceWarm_Plan__snapshot6:
.a16
.i16
    lda.l $434E50
    and #$00FF ; snapshot policy/role is a packed byte mirror
    cmp #0
    beq SourceWarm_Plan__snapshot7
    brl SourceWarm_Plan__no
SourceWarm_Plan__snapshot7:
.a16
.i16
    lda.l $434E54
    cmp #8
    beq SourceWarm_Plan__snapshot8
    brl SourceWarm_Plan__no
SourceWarm_Plan__snapshot8:
.a16
.i16
    lda.l $434E60
    cmp #9
    beq SourceWarm_Plan__snapshot9
    brl SourceWarm_Plan__no
SourceWarm_Plan__snapshot9:
.a16
.i16
    lda.l $434E64
    cmp #1
    beq SourceWarm_Plan__snapshot10
    brl SourceWarm_Plan__no
SourceWarm_Plan__snapshot10:
.a16
.i16
    lda.l $434E66
    cmp #0
    beq SourceWarm_Plan__snapshot11
    brl SourceWarm_Plan__no
SourceWarm_Plan__snapshot11:
.a16
.i16
    lda.l $434E6E
    and #$00FF ; snapshot policy/role is a packed byte mirror
    cmp #2
    beq SourceWarm_Plan__snapshot12
    brl SourceWarm_Plan__no
SourceWarm_Plan__snapshot12:
.a16
.i16
    lda.l $434E74
    and #$00FF ; snapshot policy/role is a packed byte mirror
    cmp #0
    beq SourceWarm_Plan__snapshot13
    brl SourceWarm_Plan__no
SourceWarm_Plan__snapshot13:
.a16
.i16
    lda.l $434E78
    cmp #8
    beq SourceWarm_Plan__snapshot14
    brl SourceWarm_Plan__no
SourceWarm_Plan__snapshot14:
.a16
.i16
    lda.l $434E44
    bne SourceWarm_Plan__source_hp0
    brl SourceWarm_Plan__no
SourceWarm_Plan__source_hp0:
.a16
.i16
    lda.l $434E68
    bne SourceWarm_Plan__source_hp1
    brl SourceWarm_Plan__no
SourceWarm_Plan__source_hp1:
.a16
.i16
    lda.l $434E7C
    bit #1
    beq SourceWarm_Plan__snapshot_even
    brl SourceWarm_Plan__no
SourceWarm_Plan__snapshot_even:
.a16
.i16
    sta.l SourcePrefetch_Plan+30
    lda #0
    sta.l SourcePrefetch_Plan+20
    lda 8,s
    asl a
    tax
    lda.l SourcePrefetch_HotIds,x
    sta.l SourcePrefetch_Plan
    lda.l SourcePrefetch_HotBanks,x
    sta.l SourcePrefetch_Plan+2
    lda.l SourcePrefetch_HotAddresses,x
    sta.l SourcePrefetch_Plan+4
    lda.l SourceInput_Producer
    cmp #64
    bcc SourceWarm_Plan__guard28
    brl SourceWarm_Plan__no
SourceWarm_Plan__guard28:
.a16
.i16
    sta.l SourcePrefetch_Plan+12
    lda.l SourceInput_Consumer
    cmp #64
    bcc SourceWarm_Plan__guard29
    brl SourceWarm_Plan__no
SourceWarm_Plan__guard29:
.a16
.i16
    sta.l SourcePrefetch_Plan+14
SourceWarm_Plan__input:
.a16
.i16
    lda.l SourcePrefetch_Plan+14
    cmp.l SourcePrefetch_Plan+12
    beq SourceWarm_Plan__latest
    asl a
    asl a
    tax
    lda.l SourceInput_Ring,x
    ora.l SourceInput_Ring+2,x
    and #$F0FF
    beq SourceWarm_Plan__guard30
    brl SourceWarm_Plan__no
SourceWarm_Plan__guard30:
.a16
.i16
    lda.l SourcePrefetch_Plan+14
    inc a
    and #63
    sta.l SourcePrefetch_Plan+14
    brl SourceWarm_Plan__input
SourceWarm_Plan__latest:
.a16
.i16
    lda.l SourcePrefetch_Plan+12
    dec a
    and #63
    asl a
    asl a
    tax
    lda.l SourceInput_Ring,x
    ora.l SourceInput_Ring+2,x
    beq SourceWarm_Plan__guard31
    brl SourceWarm_Plan__no
SourceWarm_Plan__guard31:
.a16
.i16
    lda #0
    sta.l SourcePrefetch_Plan+16
    sta.l SourcePrefetch_Plan+18
    ldx #0
SourceWarm_Plan__queue:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$0040
    bne SourceWarm_Plan__queue_active
    brl SourceWarm_Plan__queue_next
SourceWarm_Plan__queue_active:
.a16
.i16
    phx
    txa
    lsr a
    lsr a
    lsr a
    tax
    lda.l DmaQueue_Owner,x
    and #$00FF
    plx
    cmp #0 ; PLX changes Z: compare the saved owner after restoring X
    beq SourceWarm_Plan__guard32
    brl SourceWarm_Plan__no
SourceWarm_Plan__guard32:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$00FF
    cmp #$40
    beq SourceWarm_Plan__vram
    cmp #$41
    beq SourceWarm_Plan__oam
    jsl SourceWarm_QueueDispatch
    nop
    nop
    nop
    nop
SourceWarm_Plan__guard33:
.a16
.i16
    lda.l DmaQueue,x
    cmp #1
    bcs SourceWarm_Plan__guard34
    brl SourceWarm_Plan__no
SourceWarm_Plan__guard34:
.a16
.i16
    cmp #33
    bcc SourceWarm_Plan__guard35
    brl SourceWarm_Plan__no
SourceWarm_Plan__guard35:
.a16
.i16
    clc
    adc.l DmaQueue+2,x
    bcc SourceWarm_Plan__guard36
    brl SourceWarm_Plan__no
SourceWarm_Plan__guard36:
.a16
.i16
    cmp #513
    bcc SourceWarm_Plan__guard37
    brl SourceWarm_Plan__no
SourceWarm_Plan__guard37:
.a16
.i16
    brl SourceWarm_Plan__queue_add
SourceWarm_Plan__oam:
.a16
.i16
    lda.l DmaQueue,x
    cmp #1
    bcs SourceWarm_Plan__guard38
    brl SourceWarm_Plan__no
SourceWarm_Plan__guard38:
.a16
.i16
    cmp #545
    bcc SourceWarm_Plan__guard39
    brl SourceWarm_Plan__no
SourceWarm_Plan__guard39:
.a16
.i16
    lda.l DmaQueue+2,x
    beq SourceWarm_Plan__guard40
    brl SourceWarm_Plan__no
SourceWarm_Plan__guard40:
.a16
.i16
    brl SourceWarm_Plan__queue_add
SourceWarm_Plan__vram:
.a16
.i16
    lda.l DmaQueue,x
    cmp #1
    bcs SourceWarm_Plan__guard41
    brl SourceWarm_Plan__no
SourceWarm_Plan__guard41:
.a16
.i16
    cmp #257
    bcc SourceWarm_Plan__guard42
    brl SourceWarm_Plan__no
SourceWarm_Plan__guard42:
.a16
.i16
    dec a
    clc
    adc.l DmaQueue+2,x
    bcc SourceWarm_Plan__guard43
    brl SourceWarm_Plan__no
SourceWarm_Plan__guard43:
.a16
.i16
    cmp #$8000
    bcc SourceWarm_Plan__queue_add
    lda.l DmaQueue+2,x
    cmp #$C000
    bcs SourceWarm_Plan__guard44
    brl SourceWarm_Plan__no
SourceWarm_Plan__guard44:
.a16
.i16
SourceWarm_Plan__queue_add:
.a16
.i16
    lda.l DmaQueue,x
    bit #1
    beq SourceWarm_Plan__even_length
    brl SourceWarm_Plan__no
SourceWarm_Plan__even_length:
.a16
.i16
    lda.l DmaQueue+7,x
    and #$00FF
    cmp #$43
    bne SourceWarm_Plan__not_private_oam
    lda.l DmaQueue+4,x
    and #$00FF
    cmp #$41
    bne SourceWarm_Plan__bad_source
    lda.l DmaQueue,x
    cmp #544
    bne SourceWarm_Plan__bad_source
    lda.l DmaQueue+5,x
    cmp #$4F00
    beq SourceWarm_Plan__source_checked
    bra SourceWarm_Plan__bad_source
SourceWarm_Plan__not_private_oam:
.a16
.i16
    cmp #$7E
    beq SourceWarm_Plan__source_span
    cmp #$7F
    beq SourceWarm_Plan__source_span
    cmp #$40
    bcs SourceWarm_Plan__bad_source
    lda.l DmaQueue+5,x
    cmp #$8000
    bcs SourceWarm_Plan__source_span
SourceWarm_Plan__bad_source:
.a16
.i16
    brl SourceWarm_Plan__no
SourceWarm_Plan__source_span:
.a16
.i16
    lda.l DmaQueue,x
    dec a
    clc
    adc.l DmaQueue+5,x
    bcc SourceWarm_Plan__source_checked
    brl SourceWarm_Plan__no
SourceWarm_Plan__source_checked:
.a16
.i16
    lda.l DmaQueue,x
    clc
    adc.l SourcePrefetch_Plan+16
    bcc SourceWarm_Plan__guard45
    brl SourceWarm_Plan__no
SourceWarm_Plan__guard45:
.a16
.i16
    sta.l SourcePrefetch_Plan+16
    lda.l SourcePrefetch_Plan+18
    inc a
    sta.l SourcePrefetch_Plan+18
SourceWarm_Plan__queue_next:
.a16
.i16
    txa
    clc
    adc #8
    tax
    cpx #64
    bcs SourceWarm_Plan__queue_done
    brl SourceWarm_Plan__queue
SourceWarm_Plan__queue_done:
.a16
.i16
    lda.l SourcePrefetch_Plan+16
    cmp.l DmaQueue_BudgetTotal
    beq SourceWarm_Plan__guard46
    brl SourceWarm_TransientNo
SourceWarm_Plan__guard46:
.a16
.i16
    jsl SourceWarm_BudgetDispatch
    nop
    nop
    nop
    nop
SourceWarm_Plan__guard47:
.a16
.i16
    lda.l SourcePrefetch_Plan+18
    cmp #7
    bcc SourceWarm_Plan__guard48
    brl SourceWarm_Plan__no
SourceWarm_Plan__guard48:
.a16
.i16
    lda.l DmaQueue_CurrentSlot
    and #7
    beq SourceWarm_Plan__Commit
    brl SourceWarm_Plan__no
SourceWarm_Plan__Commit:
.a16
.i16
    lda.l SourceInput_Producer
    cmp.l SourcePrefetch_Plan+12
    beq SourceWarm_Plan__guard55
    brl SourceWarm_TransientNo
SourceWarm_Plan__guard55:
.a16
.i16
    lda.l $434E7C
    cmp.l SourcePrefetch_Plan+30
    beq SourceWarm_Plan__snapshot_still_current
    brl SourceWarm_TransientNo
SourceWarm_Plan__snapshot_still_current:
.a16
.i16
    lda #1
    sta.l $437B98
    pld
    plb
    ply
    plx
    pla
    plp
    sec
    rtl
SourceWarm_Plan__no:
.a16
.i16
    pld
    plb
    ply
    plx
    pla
    plp
    clc
    rtl
SourceWarm_QueueDispatch:
.a16
.i16
    cmp #$42
    beq SourceWarm_QueueCgram
    cmp #$43
    bne SourceWarm_QueueNo
    lda.l $437BFE
    cmp #$B6A5
    bne SourceWarm_QueueNo
    jsl SourcePrefetch_ValidateJob
    bcc SourceWarm_QueueNo
    rep #$20
    pla
    sep #$20
.a8
    pla
    rep #$20
.a16
    jml SourceWarm_Plan__queue_add
SourceWarm_QueueCgram:
.a16
.i16
    rep #$20
    pla
    sep #$20
.a8
    pla
    rep #$20
.a16
    jml SourceWarm_Plan__guard33
SourceWarm_QueueNo:
.a16
.i16
    rep #$20
    pla
    sep #$20
.a8
    pla
    rep #$20
.a16
    jml SourceWarm_Plan__no

SourceWarm_LoadingDispatch:
.a16
.i16
    lda.l SourceVisual_BlockCache+6,x
    cmp #1
    beq SourceWarm_LoadingPresent
    cmp #2
    beq SourceWarm_LoadingPresent
    cmp #$A702
    beq SourceWarm_LoadingPresent
    cmp #$A602
    bne SourceWarm_LoadingNo
    lda.l $437BFE
    cmp #$B6A5
    bne SourceWarm_LoadingNo
    phx
    phy
    ldx #0
SourceWarm_LoadingScan:
.a16
.i16
    jsl SourcePrefetch_ValidateJob
    bcc SourceWarm_LoadingNext
    cmp 3,s
    beq SourceWarm_LoadingFound
SourceWarm_LoadingNext:
.a16
.i16
    txa
    clc
    adc #8
    tax
    cpx #64
    bcc SourceWarm_LoadingScan
    ply
    plx
    bra SourceWarm_LoadingNo
SourceWarm_LoadingFound:
.a16
.i16
    ply
    plx
SourceWarm_LoadingPresent:
.a16
.i16
    rep #$20
    pla
    sep #$20
.a8
    pla
    rep #$20
.a16
    jml SourceWarm_Plan__present
SourceWarm_LoadingNo:
.a16
.i16
    rep #$20
    pla
    sep #$20
.a8
    pla
    rep #$20
.a16
    jml SourceWarm_Plan__no

SourceWarm_BudgetDispatch:
.a16
.i16
    jsl SourceStandby_BudgetCompare
    bcs SourceWarm_BudgetNo
    rep #$20
    pla
    sep #$20
.a8
    pla
    rep #$20
.a16
    jml SourceWarm_Plan__guard47
SourceWarm_BudgetNo:
.a16
.i16
    rep #$20
    pla
    sep #$20
.a8
    pla
    rep #$20
.a16
    jml SourceWarm_Plan__no
SourceWarm_Scope:
.a16
.i16
    lda.l Game_CampaignId
    and #$00FF
    cmp #3
beq SourceWarm_Scope__guard0
    brl SourceWarm_Scope__no
SourceWarm_Scope__guard0:
.a16
.i16
    lda.l Game_State
    cmp #0
beq SourceWarm_Scope__guard1
    brl SourceWarm_Scope__no
SourceWarm_Scope__guard1:
.a16
.i16
    lda.l $7E175E
    cmp #2
beq SourceWarm_Scope__guard2
    brl SourceWarm_Scope__no
SourceWarm_Scope__guard2:
.a16
.i16
    lda.l $7E1760
    cmp #1
beq SourceWarm_Scope__guard3
    brl SourceWarm_Scope__no
SourceWarm_Scope__guard3:
.a16
.i16
    lda.l $7E46DC
    cmp #1
beq SourceWarm_Scope__guard4
    brl SourceWarm_Scope__no
SourceWarm_Scope__guard4:
.a16
.i16
    lda.l SourceInput_Magic
    cmp #$1A60
beq SourceWarm_Scope__guard5
    brl SourceWarm_Scope__no
SourceWarm_Scope__guard5:
.a16
.i16
    lda.l SourceVisual_CompletedMagic
    cmp #$C04D
beq SourceWarm_Scope__guard6
    brl SourceWarm_Scope__no
SourceWarm_Scope__guard6:
.a16
.i16
    lda.l SVActor_Magic
    cmp #$AC19
beq SourceWarm_Scope__guard7
    brl SourceWarm_Scope__no
SourceWarm_Scope__guard7:
.a16
.i16
    sec
    rts
SourceWarm_Scope__no:
.a16
.i16
    clc
    rts

; Retry eligibility only. The full relocated plan and original TryOne commit
; still authenticate every resource and queue job before any allocation.
SourceWarm_NoPendingInput:
.a16
.i16
    php
    rep #$30
    pha
    phx
    phy
    lda #1
    pha
SourceWarm_InputRetry:
.a16
.i16
    lda.l SourceInput_Magic
    cmp #$1A60
    beq SourceWarm_InputGuard0
    brl SourceWarm_NoInputNo
SourceWarm_InputGuard0:
.a16
.i16
    lda.l SourceInput_Overflows
    beq SourceWarm_InputGuard1
    brl SourceWarm_NoInputNo
SourceWarm_InputGuard1:
.a16
.i16
    lda.l SourceVisual_LatchedInput
    ora.l SourceVisual_LatchedInput2
    and #$F0FF
    beq SourceWarm_InputGuard2
    brl SourceWarm_NoInputNo
SourceWarm_InputGuard2:
.a16
.i16
    lda.l $434E50
    ora.l $434E74
    and #255
    beq SourceWarm_InputGuard3
    brl SourceWarm_NoInputNo
SourceWarm_InputGuard3:
.a16
.i16
    lda.l SourceInput_Producer
    cmp #64
    bcc SourceWarm_InputGuard4
    brl SourceWarm_NoInputNo
SourceWarm_InputGuard4:
.a16
.i16
    sta.l $437B90
    lda.l SourceInput_Consumer
    cmp #64
    bcc SourceWarm_InputGuard5
    brl SourceWarm_NoInputNo
SourceWarm_InputGuard5:
.a16
.i16
    tay
    lda.l $437B90
    dec a
    and #63
    asl a
    asl a
    tax
    lda.l SourceInput_Ring,x
    ora.l SourceInput_Ring+2,x
    beq SourceWarm_InputGuard6
    brl SourceWarm_NoInputNo
SourceWarm_InputGuard6:
.a16
.i16
SourceWarm_NoInputLoop:
.a16
.i16
    tya
    cmp.l $437B90
    beq SourceWarm_NoInputEnd
    asl a
    asl a
    tax
    lda.l SourceInput_Ring,x
    ora.l SourceInput_Ring+2,x
    and #$F0FF
    beq SourceWarm_InputGuard7
    brl SourceWarm_NoInputNo
SourceWarm_InputGuard7:
.a16
.i16
    tya
    inc a
    and #63
    tay
    brl SourceWarm_NoInputLoop
SourceWarm_NoInputEnd:
.a16
.i16
    lda.l SourceInput_Producer
    cmp.l $437B90
    beq SourceWarm_NoInputYes
    lda 1,s
    beq SourceWarm_NoInputNo
    dec a
    sta 1,s
    brl SourceWarm_InputRetry
SourceWarm_NoInputYes:
.a16
.i16
    pla
    ply
    plx
    pla
    plp
    sec
    rtl
SourceWarm_NoInputNo:
.a16
.i16
    pla
    ply
    plx
    pla
    plp
    clc
    rtl
; Foreground wait entry: finish the ten-block root transaction before optional
; later-frame prefetch. Never run in NMI or change input/presentation state.
SourceWarm_WaitEntry:
.a16
.i16
    php
    pha
    lda.l SourceAttackOwned_InitMagic
    cmp #$B077
    bne SourceWarm_WaitOrdinary
    jsl SourceRewarm_Closed
    bne SourceWarm_WaitOrdinary
    lda.l SourcePrefetch_Cursor
    cmp #10
    bcc SourceWarm_WaitOrdinary
    lda.l SourceAttackTemplate_Base
    cmp #$A770
    bne SourceWarm_WaitPrepare
    lda.l SourceAttackTemplate_Base+128
    cmp #$A770
    bne SourceWarm_WaitPrepare
SourceWarm_WaitOrdinary:
.a16
.i16
    pla
    plp
    jml SourcePrefetch_DuringWait
SourceWarm_WaitPrepare:
.a16
.i16
    pla
    plp
    jml SourceWarm_SettleThenPrepare
; Original wait has restored caller ABI and CMP flags. Prepare preserves them.
; Actual NMI retirement precedes this foreground-only handoff.
SourceWarm_WaitReturn:
.a16
.i16
    jsl SourceWarm_PostWaitService
    jml Core_Nmi_WaitFrame__return

; The explicit bounded batch must not inherit DuringWait's single-visit stamp.
; Exactly the same TryOne plan/commit and status/cursor accounting are used.
SourceWarm_FirstAttempt:
.a16
.i16
    php
    pha
    lda #0
    sta.l $437B96
    lda.l SourcePrefetch_Cursor
    jsl SourceWarm_TryOne
    bcs SourceWarm_FirstSubmitted
    lda.l SourcePrefetch_Plan+20
    bne SourceWarm_FirstStatus
    lda.l $437B94
    cmp #1
    bne SourceWarm_FirstDone
    jsl SourceWarm_NoPendingInput
    bcc SourceWarm_FirstDone
    lda #1
    sta.l $437B96
    lda.l SourcePrefetch_Cursor
    jsl SourceWarm_TryOne
    bcc SourceWarm_FirstStatus
SourceWarm_FirstSubmitted:
.a16
.i16
    lda.l SourcePrefetch_Submitted
    inc a
    sta.l SourcePrefetch_Submitted
SourceWarm_FirstStatus:
.a16
.i16
    lda.l SourcePrefetch_Plan+20
    beq SourceWarm_FirstDone
    lda.l SourcePrefetch_Cursor
    inc a
    cmp #22
    bcc SourceWarm_FirstSave
    lda #0
SourceWarm_FirstSave:
.a16
.i16
    sta.l SourcePrefetch_Cursor
SourceWarm_FirstDone:
.a16
.i16
    pla
    plp
    rtl
; Foreground settlement of PRIVATE root jobs whose FOUR physical transfers
; already earned A7. Use the established CanRetire authority; do not publish
; actor/pose readiness, consume input, allocate, enqueue, or manufacture ACKs.
SourceWarm_SettleThenPrepare:
.a16
.i16
    jsl SourceWarm_SettleCompleted
    jml SourceStandby_Prepare
SourceWarm_SettleCompleted:
.a16
.i16
    php
    rep #$30
    pha
    phx
    phy
    lda #0
    sta.l $437B92
    lda.l SourceAttackOwned_InitMagic
    cmp #$B077
    beq SourceWarm_SettleInit
    brl SourceWarm_SettleDone
SourceWarm_SettleInit:
.a16
.i16
    jsl SourceRewarm_Closed
    ora.l Game_StageIndex
    ora.l Screen_PosX
    ora.l SourcePrefetch_PhysicalPending
    beq SourceWarm_SettleCold
    brl SourceWarm_SettleDone
SourceWarm_SettleCold:
.a16
.i16
    lda.l SourcePrefetch_Cursor
    cmp #10
    bcs SourceWarm_SettleQueueStart
    brl SourceWarm_SettleDone
SourceWarm_SettleQueueStart:
.a16
.i16
    ldx #0
SourceWarm_SettleQueue:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$40
    beq SourceWarm_SettleQueueNext
    lda.l DmaQueue+4,x
    and #255
    cmp #$41
    beq SourceWarm_SettleQueueNext
    brl SourceWarm_SettleDone
SourceWarm_SettleQueueNext:
.a16
.i16
    txa
    clc
    adc #8
    tax
    cpx #64
    bcc SourceWarm_SettleQueue
    ldx #0
    phx
SourceWarm_SettleSlot:
.a16
.i16
    lda.l SourceVisual_BlockCache+2,x
    cmp #1
    bne SourceWarm_SettleNext
    lda.l SourceVisual_BlockCache+4,x
    and #255
    bne SourceWarm_SettleNext
    lda.l SourceVisual_BlockCache+5,x
    cmp #$0204
    bne SourceWarm_SettleNext
    lda.l SourceVisual_BlockCache+7,x
    and #255
    cmp #$A7
    bne SourceWarm_SettleNext
    ldy #0
SourceWarm_SettleIdentity:
.a16
.i16
    phy
    tyx
    lda.l SourcePrefetch_HotIds,x
    ply
    ; Recover real cache-byte X from the bounded scan counter on the stack.
    plx
    phx
    cmp.l SourceVisual_BlockCache,x
    beq SourceWarm_SettleKnown
    iny
    iny
    cpy #20
    bcc SourceWarm_SettleIdentity
    bra SourceWarm_SettleNext
SourceWarm_SettleKnown:
.a16
.i16
    jsl SourcePrefetch_CanRetire
    bcc SourceWarm_SettleNext
    lda #2
    sta.l SourceVisual_BlockCache+2,x
    lda.l $437B92
    inc a
    sta.l $437B92
SourceWarm_SettleNext:
.a16
.i16
    plx
    txa
    clc
    adc #8
    tax
    cpx #512
    bcs SourceWarm_SettleDone
    phx
    brl SourceWarm_SettleSlot
SourceWarm_SettleDone:
.a16
.i16
    ply
    plx
    pla
    plp
    rtl

SourceWarm_PostWaitService:
.a16
.i16
    php
    pha
    jsl SourceRewarm_Arm
    lda.l SourceAttackOwned_InitMagic
    cmp #$B077
    bne SourceWarm_PostWaitNoBurst
    jsl SourceRewarm_Closed
    ora.l Game_StageIndex
    ora.l Screen_PosX
    bne SourceWarm_PostWaitNoBurst
    lda.l SourcePrefetch_Cursor
    cmp #10
    bcs SourceWarm_PostWaitNoBurst
    pla
    plp
    jsl SourceWarm_BurstAfterPump
    jml SourceWarm_SettleThenPrepare
SourceWarm_PostWaitNoBurst:
.a16
.i16
    pla
    plp
    jml SourceWarm_SettleThenPrepare
SourceWarm_BurstAfterPumpTarget = $3D0000 | ((SourcePrefetch_TailBatch+4) & $FFFF)
SourceWarm_BurstAfterPump:
.a16
.i16
    jml SourceWarm_BurstAfterPumpTarget
SourceStandby_FreshScope:
.a16
.i16
    php
    rep #$30
    pha
    lda.l $434E7C
    sta.l SourceStandby_Seq
    and #1

    beq SourceStandby_Fresh0
    brl SourceStandby_FreshNo
SourceStandby_Fresh0:
.a16
.i16
    lda.l SourceAttackOwned_InitMagic
    cmp #$B077
    beq SourceStandby_Fresh1
    brl SourceStandby_FreshNo
SourceStandby_Fresh1:
.a16
.i16
    lda.l SourceVisual_CompletedMagic
    cmp #$C04D
    beq SourceStandby_Fresh2
    brl SourceStandby_FreshNo
SourceStandby_Fresh2:
.a16
.i16
    lda.l SVActor_Magic
    cmp #$AC19
    beq SourceStandby_Fresh3
    brl SourceStandby_FreshNo
SourceStandby_Fresh3:
.a16
.i16
    lda.l SourceInput_Magic
    cmp #$1A60
    beq SourceStandby_Fresh4
    brl SourceStandby_FreshNo
SourceStandby_Fresh4:
.a16
.i16
    lda.l Game_State
    cmp #$0000
    beq SourceStandby_Fresh5
    brl SourceStandby_FreshNo
SourceStandby_Fresh5:
.a16
.i16
    lda.l Game_StageIndex
    cmp #$0000
    beq SourceStandby_Fresh6
    brl SourceStandby_FreshNo
SourceStandby_Fresh6:
.a16
.i16
    lda.l Screen_PosX
    cmp #$0000
    beq SourceStandby_Fresh7
    brl SourceStandby_FreshNo
SourceStandby_Fresh7:
.a16
.i16
    lda.l SourceAttackOwned_State
    cmp #$0000
    beq SourceStandby_Fresh8
    brl SourceStandby_FreshNo
SourceStandby_Fresh8:
.a16
.i16
    lda.l SourceAttackOwned_Hold
    cmp #$0000
    beq SourceStandby_Fresh9
    brl SourceStandby_FreshNo
SourceStandby_Fresh9:
.a16
.i16
    lda.l SourceAttackOwned_Busy
    cmp #$0000
    beq SourceStandby_Fresh10
    brl SourceStandby_FreshNo
SourceStandby_Fresh10:
.a16
.i16
    lda.l SourcePacket_CopyBusy
    cmp #$0000
    beq SourceStandby_Fresh11
    brl SourceStandby_FreshNo
SourceStandby_Fresh11:
.a16
.i16
    jsl SourceRewarm_Closed
    cmp #$0000
    beq SourceStandby_Fresh12
    brl SourceStandby_FreshNo
SourceStandby_Fresh12:
.a16
.i16
    lda.l $437A96
    cmp #$0000
    beq SourceStandby_Fresh13
    brl SourceStandby_FreshNo
SourceStandby_Fresh13:
.a16
.i16
    lda.l $437A98
    cmp #$0000
    beq SourceStandby_Fresh14
    brl SourceStandby_FreshNo
SourceStandby_Fresh14:
.a16
.i16
    jsl SourceRewarm_PhysicalMask
    cmp #$0000
    beq SourceStandby_Fresh15
    brl SourceStandby_FreshNo
SourceStandby_Fresh15:
.a16
.i16
    lda.l SourceVisual_CompletedValid
    cmp #$0001
    beq SourceStandby_Fresh16
    brl SourceStandby_FreshNo
SourceStandby_Fresh16:
.a16
.i16
    lda.l SVActor_Data+SVActor_Valid
    cmp #$0001
    beq SourceStandby_Fresh17
    brl SourceStandby_FreshNo
SourceStandby_Fresh17:
.a16
.i16
    lda.l SourcePrefetch_PhysicalPending
    cmp #$0000
    beq SourceStandby_Fresh18
    brl SourceStandby_FreshNo
SourceStandby_Fresh18:
.a16
.i16
    lda.l Game_CampaignId
    and #255
    cmp #3
    beq SourceStandby_Fresh19
    brl SourceStandby_FreshNo
SourceStandby_Fresh19:
.a16
.i16
    lda.l $7E175E
    cmp #$0002
    beq SourceStandby_Fresh20
    brl SourceStandby_FreshNo
SourceStandby_Fresh20:
.a16
.i16
    lda.l $7E1760
    cmp #$0001
    beq SourceStandby_Fresh21
    brl SourceStandby_FreshNo
SourceStandby_Fresh21:
.a16
.i16
    lda.l $7E46DC
    cmp #$0001
    beq SourceStandby_Fresh22
    brl SourceStandby_FreshNo
SourceStandby_Fresh22:
.a16
.i16
    lda.l $7E46DE
    cmp #$0000
    beq SourceStandby_Fresh23
    brl SourceStandby_FreshNo
SourceStandby_Fresh23:
.a16
.i16
    lda.l $434E7E
    cmp #$4D50
    beq SourceStandby_Fresh24
    brl SourceStandby_FreshNo
SourceStandby_Fresh24:
.a16
.i16
    lda.l $434E2C
    cmp #$0000
    beq SourceStandby_Fresh25
    brl SourceStandby_FreshNo
SourceStandby_Fresh25:
.a16
.i16
    lda.l SourcePrefetch_Cursor
    cmp #10
    bcs SourceStandby_Fresh26
    brl SourceStandby_FreshNo
SourceStandby_Fresh26:
.a16
.i16
    lda.l $7E0A00+CHAR_INPUT_DRIVEN
    and #255
    cmp #1
    beq SourceStandby_Fresh27
    brl SourceStandby_FreshNo
SourceStandby_Fresh27:
.a16
.i16
    lda.l $7E0A00+CHAR_ROSTER_INDEX
    and #255
    cmp #22
    beq SourceStandby_Fresh28
    brl SourceStandby_FreshNo
SourceStandby_Fresh28:
.a16
.i16
    lda.l $7E0A00+CHAR_MAP_INDEX
    and #255
    cmp #0
    beq SourceStandby_Fresh29
    brl SourceStandby_FreshNo
SourceStandby_Fresh29:
.a16
.i16
    lda.l $7E0A00+CHAR_HP
    and #255
    bne SourceStandby_Fresh30
    brl SourceStandby_FreshNo
SourceStandby_Fresh30:
.a16
.i16
    lda.l StageBounds_State+0
    cmp #0
    beq SourceStandby_Fresh31
    brl SourceStandby_FreshNo
SourceStandby_Fresh31:
.a16
.i16
    lda.l $434E40
    cmp #1
    beq SourceStandby_Fresh32
    brl SourceStandby_FreshNo
SourceStandby_Fresh32:
.a16
.i16
    lda.l $434E42
    cmp #0
    beq SourceStandby_Fresh33
    brl SourceStandby_FreshNo
SourceStandby_Fresh33:
.a16
.i16
    lda.l $434E4A
    and #255
    cmp #2
    beq SourceStandby_Fresh34
    brl SourceStandby_FreshNo
SourceStandby_Fresh34:
.a16
.i16
    lda.l $434E50
    and #255
    cmp #0
    beq SourceStandby_Fresh35
    brl SourceStandby_FreshNo
SourceStandby_Fresh35:
.a16
.i16
    lda.l $434E54
    and #255
    cmp #8
    beq SourceStandby_Fresh36
    brl SourceStandby_FreshNo
SourceStandby_Fresh36:
.a16
.i16
    lda.l $434E36
    cmp #188
    beq SourceStandby_Fresh37
    brl SourceStandby_FreshNo
SourceStandby_Fresh37:
.a16
.i16
    lda.l $434E44
    bne SourceStandby_Fresh38
    brl SourceStandby_FreshNo
SourceStandby_Fresh38:
.a16
.i16
    lda.l $434E44
    cmp #256
    bcc SourceStandby_Fresh39
    brl SourceStandby_FreshNo
SourceStandby_Fresh39:
.a16
.i16
    lda.l $434E9C
    cmp #0
    beq SourceStandby_Fresh40
    brl SourceStandby_FreshNo
SourceStandby_Fresh40:
.a16
.i16
    lda.l $7E0A85+CHAR_INPUT_DRIVEN
    and #255
    cmp #1
    beq SourceStandby_Fresh41
    brl SourceStandby_FreshNo
SourceStandby_Fresh41:
.a16
.i16
    lda.l $7E0A85+CHAR_ROSTER_INDEX
    and #255
    cmp #22
    beq SourceStandby_Fresh42
    brl SourceStandby_FreshNo
SourceStandby_Fresh42:
.a16
.i16
    lda.l $7E0A85+CHAR_MAP_INDEX
    and #255
    cmp #0
    beq SourceStandby_Fresh43
    brl SourceStandby_FreshNo
SourceStandby_Fresh43:
.a16
.i16
    lda.l $7E0A85+CHAR_HP
    and #255
    bne SourceStandby_Fresh44
    brl SourceStandby_FreshNo
SourceStandby_Fresh44:
.a16
.i16
    lda.l StageBounds_State+133
    cmp #0
    beq SourceStandby_Fresh45
    brl SourceStandby_FreshNo
SourceStandby_Fresh45:
.a16
.i16
    lda.l $434E64
    cmp #1
    beq SourceStandby_Fresh46
    brl SourceStandby_FreshNo
SourceStandby_Fresh46:
.a16
.i16
    lda.l $434E66
    cmp #0
    beq SourceStandby_Fresh47
    brl SourceStandby_FreshNo
SourceStandby_Fresh47:
.a16
.i16
    lda.l $434E6E
    and #255
    cmp #2
    beq SourceStandby_Fresh48
    brl SourceStandby_FreshNo
SourceStandby_Fresh48:
.a16
.i16
    lda.l $434E74
    and #255
    cmp #0
    beq SourceStandby_Fresh49
    brl SourceStandby_FreshNo
SourceStandby_Fresh49:
.a16
.i16
    lda.l $434E78
    and #255
    cmp #8
    beq SourceStandby_Fresh50
    brl SourceStandby_FreshNo
SourceStandby_Fresh50:
.a16
.i16
    lda.l $434E5A
    cmp #188
    beq SourceStandby_Fresh51
    brl SourceStandby_FreshNo
SourceStandby_Fresh51:
.a16
.i16
    lda.l $434E68
    bne SourceStandby_Fresh52
    brl SourceStandby_FreshNo
SourceStandby_Fresh52:
.a16
.i16
    lda.l $434E68
    cmp #256
    bcc SourceStandby_Fresh53
    brl SourceStandby_FreshNo
SourceStandby_Fresh53:
.a16
.i16
    lda.l $434E9E
    cmp #133
    beq SourceStandby_Fresh54
    brl SourceStandby_FreshNo
SourceStandby_Fresh54:
.a16
.i16
    lda.l $434E7C
    cmp.l SourceStandby_Seq
    beq SourceStandby_Fresh55
    brl SourceStandby_FreshNo
SourceStandby_Fresh55:
.a16
.i16
    pla
    plp
    sec
    rtl
SourceStandby_FreshNo:
.a16
.i16
    pla
    plp
    clc
    rtl

SourceWarm_TransientNo:
.a16
.i16
    lda #1
    sta.l $437B94
    jml SourceWarm_Plan__no
SourceWarm_TryOne:
.a16
.i16
    php
    pha
    lda #0
    sta.l $437B94
    sta.l $437B98
    pla
    plp
    jsl SourcePrefetch_TryOne
    bcc SourceWarm_TryRejected
    php
    pha
    lda.l $437B9A
    inc a
    sta.l $437B9A
    pla
    plp
    rtl
SourceWarm_TryRejected:
.a16
.i16
    php
    pha
    lda.l $437B98
    cmp #1
    bne SourceWarm_TryDone
    lda.l SourceInput_Producer
    cmp.l SourcePrefetch_Plan+12
    bne SourceWarm_TryEpoch
    lda.l $434E7C
    cmp.l SourcePrefetch_Plan+30
    beq SourceWarm_TryDone
SourceWarm_TryEpoch:
.a16
.i16
    lda #1
    sta.l $437B94
SourceWarm_TryDone:
.a16
.i16
    pla
    plp
    rtl

; Preserve the original retirement observer's complete return contract.
; Only already-pinned ready templates are captured, independent of actor visit.
SourceReady_Observe:
.a16
.i16
    jsl SourceAttackLease_Observe
    jml SourceReady_Capture
SourceReady_Capture:
.a16
.i16
    php
    rep #$30
    pha
    phx
    phy
    phb
    phd
    lda.l SourceAttackOwned_InitMagic
    cmp #$B077
    beq SourceReady_Init
    brl SourceReady_Done
SourceReady_Init:
.a16
.i16
    lda.l SourceAttackOwned_Busy
    ora.l SourcePacket_CopyBusy
    ora.l Game_StageIndex
    ora.l Screen_PosX
    beq SourceReady_Free
    brl SourceReady_Done
SourceReady_Free:
.a16
.i16
    lda.l SourceAttackOwned_State
    beq SourceReady_State
    cmp #2
    beq SourceReady_State
    brl SourceReady_Done
SourceReady_State:
.a16
.i16
    jsl SourceFacing_AdaptStatic
    lda.l SourcePacket_ActiveValid
    cmp #1
    beq SourceReady_Active
    brl SourceReady_Done
SourceReady_Active:
.a16
.i16
    lda.l $437A96
    and #1
    bne SourceReady_Player2
    lda.l SourceAttackTemplate_Base
    cmp #$A770
    bne SourceReady_Player2
    lda.l $4119E6
    and #255
    cmp #9
    beq SourceReady_Eligible
SourceReady_Player2:
.a16
.i16
    lda.l $437A96
    and #2
    bne SourceReady_Done
    lda.l SourceAttackTemplate_Base+128
    cmp #$A770
    bne SourceReady_Done
    lda.l $411AE6
    and #255
    cmp #9
    bne SourceReady_Done
SourceReady_Eligible:
.a16
.i16
    lda.l $437BA6
    cmp #1
    bne SourceReady_NewField
    lda.l StageTimer_FieldCounter
    cmp.l $437B9C
    beq SourceReady_Done
SourceReady_NewField:
.a16
.i16
    lda.l StageTimer_FieldCounter
    sta.l $437B9C
    lda #1
    sta.l $437BA6
    lda.l $437BA8
    inc a
    sta.l $437BA8
    ; Snapshot uses the shared 8-byte projection scratch. Preserve it across
    ; this cooperative entry, just as all machine registers are preserved.
    ldx #0
SourceReady_SaveProjection:
.a16
.i16
    lda.l SourcePacket_ProjectInput,x
    sta.l $437B9E,x
    inx
    inx
    cpx #8
    bcc SourceReady_SaveProjection
    jsl SourceAttackOwned_CaptureSeal
    lda.l $437B3C
    cmp #$A55E
    bne SourceReady_RestoreStart
    jsl SourceAttackOwned_Snapshot
SourceReady_RestoreStart:
.a16
.i16
    ldx #0
SourceReady_RestoreProjection:
.a16
.i16
    lda.l $437B9E,x
    sta.l SourcePacket_ProjectInput,x
    inx
    inx
    cpx #8
    bcc SourceReady_RestoreProjection
SourceReady_Done:
.a16
.i16
    pld
    plb
    ply
    plx
    pla
    plp
    rtl

; 0 initial; 1 pressure requested; 2 bounded refill active; 3 completed.
SourceRewarm_Closed:
.a16
.i16
    lda.l SourceAttackOwned_PhysicalAcks
    beq SourceRewarm_Open
    lda.l $437BAC
    cmp #2
    beq SourceRewarm_Open
    lda #1
    rtl
SourceRewarm_Open:
.a16
.i16
    lda #0
    rtl
; Historical physical-mask bits have no live owner once the full ownership
; transaction has returned to absent/unheld. Never alter the ACK or mask.
SourceRewarm_PhysicalMask:
.a16
.i16
    lda.l $437BAC
    cmp #2
    bne SourceRewarm_OriginalMask
    lda.l SourceAttackOwned_State
    ora.l SourceAttackOwned_Hold
    ora.l $437A96
    ora.l $437A98
    bne SourceRewarm_OriginalMask
    lda #0
    rtl
SourceRewarm_OriginalMask:
.a16
.i16
    lda.l $437A9A
    rtl
SourceRewarm_Invalidate:
.a16
.i16
    jsl SourceAttackTemplate_Invalidate
    php
    rep #$20
    pha
    lda #1
    sta.l $437BAC
    pla
    plp
    rtl
SourceRewarm_Arm:
.a16
.i16
    php
    rep #$30
    pha
    phx
    phy
    phb
    phd
    lda.l $437BAC
    cmp #2
    bne SourceRewarm_CheckRequest
    lda.l SourceAttackTemplate_Base
    cmp #$A770
    beq SourceRewarm_Template0
    brl SourceRewarm_Done
SourceRewarm_Template0:
.a16
.i16
    lda.l SourceAttackTemplate_Base+128
    cmp #$A770
    beq SourceRewarm_Template1
    brl SourceRewarm_Done
SourceRewarm_Template1:
.a16
.i16
    lda #3
    sta.l $437BAC
    brl SourceRewarm_Done
SourceRewarm_CheckRequest:
.a16
.i16
    cmp #1
    beq SourceRewarm_Requested
    brl SourceRewarm_Done
SourceRewarm_Requested:
.a16
.i16
    lda.l SourceAttackOwned_InitMagic
    cmp #$B077
    beq SourceRewarm_ArmGuard0
    brl SourceRewarm_Done
SourceRewarm_ArmGuard0:
.a16
.i16
    lda.l SourceAttackOwned_PhysicalAcks
    bne SourceRewarm_ArmGuard1
    brl SourceRewarm_Done
SourceRewarm_ArmGuard1:
.a16
.i16
    lda.l SourceAttackOwned_State
    ora.l SourceAttackOwned_Hold
    ora.l SourceAttackOwned_Busy
    ora.l SourcePacket_CopyBusy
    ora.l SourcePrefetch_PhysicalPending
    ora.l Game_StageIndex
    ora.l Screen_PosX
    ora.l $437A96
    ora.l $437A98
    beq SourceRewarm_ArmGuard2
    brl SourceRewarm_Done
SourceRewarm_ArmGuard2:
.a16
.i16
    lda.l $7E0A00+0+CHAR_SELECTED
    and #255
    cmp #3
    bcc SourceRewarm_ArmGuard3
    brl SourceRewarm_Done
SourceRewarm_ArmGuard3:
.a16
.i16
    lda.l $7E0A00+0+CHAR_THROW_ZPOS
    beq SourceRewarm_ArmGuard4
    brl SourceRewarm_Done
SourceRewarm_ArmGuard4:
.a16
.i16
    lda.l $7E0A00+133+CHAR_SELECTED
    and #255
    cmp #3
    bcc SourceRewarm_ArmGuard5
    brl SourceRewarm_Done
SourceRewarm_ArmGuard5:
.a16
.i16
    lda.l $7E0A00+133+CHAR_THROW_ZPOS
    beq SourceRewarm_ArmGuard6
    brl SourceRewarm_Done
SourceRewarm_ArmGuard6:
.a16
.i16
    jsl SourceWarm_NoPendingInput
    bcs SourceRewarm_ArmGuard7
    brl SourceRewarm_Done
SourceRewarm_ArmGuard7:
.a16
.i16
    lda #0
    sta.l SourcePrefetch_Cursor
    lda #2
    sta.l $437BAC
SourceRewarm_Done:
.a16
.i16
    pld
    plb
    ply
    plx
    pla
    plp
    rtl

SourceShape_CanSnapshot:
.a16
.i16
    pha
    jsl SourceLayout_Dynamic2
    bcc SourceLayout_OriginalEnd
    pla
    sec
    rtl
SourceLayout_OriginalEnd:
.a16
.i16
    jsl SourceNormalize_Partial1
    bcc SourceNormalize_OriginalEnd
    pla
    sec
    rtl
SourceNormalize_OriginalEnd:
.a16
.i16
    pla
    cmp #80
    bne SourceShape_Nonstandard
    brl SourceShape_Yes
SourceShape_Nonstandard:
.a16
.i16
    cmp #72
    beq SourceShape_Check0
    cmp #96
    beq SourceShape_Check0
    brl SourceShape_No
SourceShape_Check0:
.a16
.i16
    lda.l $437A9C
    cmp #3
    beq SourceShape_Check1
    brl SourceShape_No
SourceShape_Check1:
.a16
.i16
    lda.l SOURCE_PACKET_ACTIVE_META+34
    cmp #96
    bne SourceShape_JumpLayout
    jml SourceFacing_WalkLayout
SourceShape_JumpLayout:
.a16
.i16
    lda.l SOURCE_PACKET_ACTIVE_META+2
    cmp #36
    beq SourceShape_Check2
    brl SourceShape_No
SourceShape_Check2:
.a16
.i16
    lda.l SOURCE_PACKET_ACTIVE_META+12
    cmp #$0716
    beq SourceShape_Check3
    brl SourceShape_No
SourceShape_Check3:
.a16
.i16
    lda.l SOURCE_PACKET_ACTIVE_META+44
    cmp #$0716
    beq SourceShape_Check4
    brl SourceShape_No
SourceShape_Check4:
.a16
.i16
    lda.l $7E0A00+CHAR_SELECTED
    and #255
    cmp #3
    bcc SourceShape_Check5
    brl SourceShape_No
SourceShape_Check5:
.a16
.i16
    lda.l $7E0A00+133+CHAR_SELECTED
    and #255
    cmp #3
    bcc SourceShape_Check6
    brl SourceShape_No
SourceShape_Check6:
.a16
.i16
    lda.l $7E0A00+CHAR_THROW_ZPOS
    ora.l $7E0A00+133+CHAR_THROW_ZPOS
    beq SourceShape_Check7
    brl SourceShape_No
SourceShape_Check7:
.a16
.i16
    lda.l $434F00+504
    cmp #$E0C0
    beq SourceShape_Check8
    brl SourceShape_No
SourceShape_Check8:
.a16
.i16
    lda.l $434F00+508
    cmp #$E0C0
    beq SourceShape_Check9
    brl SourceShape_No
SourceShape_Check9:
.a16
.i16
    lda.l $434F00+506
    ora.l $434F00+510
    beq SourceShape_Check10
    brl SourceShape_No
SourceShape_Check10:
.a16
.i16
    lda.l $434F00+543
    and #$00F0
    cmp #$0050
    beq SourceShape_Check11
    brl SourceShape_No
SourceShape_Check11:
.a16
.i16
SourceShape_Yes:
.a16
.i16
    sec
    rtl
SourceShape_No:
.a16
.i16
    clc
    rtl
SourceShape_CopyBase:
.a16
.i16
    jsl SourceFastBase_Copy544
    nop
    nop
    nop
    nop
    nop
    nop
    nop
    nop
    php
    rep #$30
    pha
    phx
    phy
    lda.l SOURCE_PACKET_ACTIVE_META+34
    cmp #72
    beq SourceFacing_CopyJump
    cmp #96
    bne SourceFacing_CopyUnchanged
    brl SourceFacing_ClearWalkTail
SourceFacing_CopyUnchanged:
.a16
.i16
    brl SourceShape_CopyDone
SourceFacing_CopyJump:
.a16
.i16
    ; Backward memmove: original sprite18..125 -> private sprite20..127.
    ; No current hardware/normal OAM, VRAM or cache ownership is modified.
    ldx #502
    ldy #510
SourceShape_MoveLow:
.a16
.i16
    lda.l SourceAttackOwned_Image,x
    sta.w $7600,y
    dex
    dex
    dey
    dey
    jsr SourceNormalize_LowCompare
    bcs SourceShape_MoveLow
    ; Shift packed high bits by two sprites. Descending order retains both
    ; source nibbles; the attack emitter replaces the first 20 flags later.
    ldx #31
SourceShape_MoveHigh:
.a16
.i16
    lda.l SourceAttackOwned_Image+512,x
    and #15
    asl a
    asl a
    asl a
    asl a
    sta.l $437BAE
    dex
    lda.l SourceAttackOwned_Image+512,x
    and #255
    lsr a
    lsr a
    lsr a
    lsr a
    ora.l $437BAE
    inx
    sep #$20
.a8
    sta.l SourceAttackOwned_Image+512,x
    rep #$20
.a16
    dex
    jsr SourceNormalize_HighCompare
    bcs SourceShape_MoveHigh
    brl SourceShape_CopyDone
SourceFacing_ClearWalkTail:
.a16
.i16
    ldx #80
SourceFacing_HideWalkSlot:
.a16
.i16
    lda #$E0C0
    sta.l SourceAttackOwned_Image,x
    lda #0
    sta.l SourceAttackOwned_Image+2,x
    txa
    clc
    adc #4
    tax
    cpx #96
    bcc SourceFacing_HideWalkSlot
    sep #$20
.a8
    lda #$55
    sta.l SourceAttackOwned_Image+517
    rep #$30
.a16
.i16
SourceShape_CopyDone:
.a16
.i16
    ply
    plx
    pla
    plp
    rtl
SourceShape_Gate:
.a16
.i16
    jsl SourceShape_CanSnapshot
    bcc SourceShape_GateNo
    jml SourceAttackOwned_G25
SourceShape_GateNo:
.a16
.i16
    jml SourceAttackOwned_Done

; The physically acknowledged private lease must be offered to the normal
; renderer while its source scene generation still matches. Do not weaken
; any existing resource, pending-player or physical acknowledgement check.
SourceAttackLease_BeforeScene:
.a16
.i16
    php
    rep #$30
    pha
    jsl SourceAttackJoint_Defer
    bcs SourceAttackLease_BeforeSceneDone
    jsl SourceAttackLease_Adopt
SourceAttackLease_BeforeSceneDone:
.a16
.i16
    jsl SourcePriority_Observe
    pla
    plp
    jml SourceNextScene_Begin
SourceFacing_OldShapeKey:
.a16
.i16
    cmp #$0716
    beq SourceFacing_KeyYes
    cmp #$0116
    beq SourceFacing_KeyYes
    clc
    rtl
SourceFacing_KeyYes:
.a16
.i16
    sec
    rtl

SourceFacing_Meta0:
.a16
.i16
    lda.l $437A9C
    and #1
    bne SourceFacing_Match0
    lda.l $7E0A00+CHAR_FACING_LEFT
    and #255
    cmp #2
    bcs SourceFacing_No0
    cmp.l SOURCE_PACKET_ACTIVE_META+18
    beq SourceFacing_Yes0
    bra SourceFacing_No0
SourceFacing_Match0:
.a16
.i16
    jsl SourceGroundRoot_Face0
    and #255
    cmp #2
    bcs SourceFacing_No0
    cmp.l SourceAttackTemplate_Base+20
    beq SourceFacing_Yes0
SourceFacing_No0:
.a16
.i16
    lda #1
    sec
    rtl
SourceFacing_Yes0:
.a16
.i16
    lda #0
    sec
    rtl

SourceFacing_Meta1:
.a16
.i16
    lda.l $437A9C
    and #2
    bne SourceFacing_Match1
    lda.l $7E0A85+CHAR_FACING_LEFT
    and #255
    cmp #2
    bcs SourceFacing_No1
    cmp.l SOURCE_PACKET_ACTIVE_META+50
    beq SourceFacing_Yes1
    bra SourceFacing_No1
SourceFacing_Match1:
.a16
.i16
    jsl SourceGroundRoot_Face1
    and #255
    cmp #2
    bcs SourceFacing_No1
    cmp.l SourceAttackTemplate_Base+148
    beq SourceFacing_Yes1
SourceFacing_No1:
.a16
.i16
    lda #1
    sec
    rtl
SourceFacing_Yes1:
.a16
.i16
    lda #0
    sec
    rtl

; Only static immutable root templates are turned. Current hardware, normal
; packets, tile/palette identities, pins, gameplay and input are untouched.
; Full capture/seal/generation checks run again after this foreground adapter.
SourceFacing_AdaptStatic:
.a16
.i16
    php
    rep #$30
    pha
    phx
    phy
    phb
    phd
    cld
    lda.l SourceAttackOwned_State
    ora.l SourceAttackOwned_Hold
    ora.l SourceAttackOwned_Busy
    ora.l SourcePacket_CopyBusy
    ora.l Game_StageIndex
    ora.l Screen_PosX
    beq SourceFacing_Free
    brl SourceFacing_Done
SourceFacing_Free:
.a16
.i16
    lda.l SourceStandby_FaceMask
    and #1
    bne SourceFacing_Adapt0Guard0
    brl SourceFacing_SlotDone0
SourceFacing_Adapt0Guard0:
.a16
.i16
    lda.l SourceAttackTemplate_Base+0
    cmp #$A770
    beq SourceFacing_Adapt0Guard1
    brl SourceFacing_SlotDone0
SourceFacing_Adapt0Guard1:
.a16
.i16
    lda.l $4119E6
    and #255
    cmp #9
    beq SourceFacing_Adapt0Guard2
    brl SourceFacing_SlotDone0
SourceFacing_Adapt0Guard2:
.a16
.i16
    lda.l $7E0A00+CHAR_THROW_ZPOS
    beq SourceFacing_Adapt0Guard3
    brl SourceFacing_SlotDone0
SourceFacing_Adapt0Guard3:
.a16
.i16
    lda.l $7E0A00+CHAR_SELECTED
    and #255
    cmp #3
    bcc SourceFacing_Adapt0Guard4
    brl SourceFacing_SlotDone0
SourceFacing_Adapt0Guard4:
.a16
.i16
    lda.l SourceAttackTemplate_Base+6
    cmp #534
    beq SourceFacing_Adapt0Guard5
    brl SourceFacing_SlotDone0
SourceFacing_Adapt0Guard5:
.a16
.i16
    lda.l SourceAttackTemplate_Base+8
    cmp #0
    beq SourceFacing_Adapt0Guard6
    brl SourceFacing_SlotDone0
SourceFacing_Adapt0Guard6:
.a16
.i16
    lda.l SourceAttackTemplate_Base+14
    cmp #128
    beq SourceFacing_Adapt0Guard7
    brl SourceFacing_SlotDone0
SourceFacing_Adapt0Guard7:
.a16
.i16
    lda.l SourceAttackTemplate_Base+16
    cmp #150
    beq SourceFacing_Adapt0Guard8
    brl SourceFacing_SlotDone0
SourceFacing_Adapt0Guard8:
.a16
.i16
    lda.l SourceAttackTemplate_Base+18
    cmp #0
    beq SourceFacing_Adapt0Guard9
    brl SourceFacing_SlotDone0
SourceFacing_Adapt0Guard9:
.a16
.i16
    lda.l SourceAttackTemplate_Base+22
    cmp #781
    beq SourceFacing_Adapt0Guard10
    brl SourceFacing_SlotDone0
SourceFacing_Adapt0Guard10:
.a16
.i16
    lda.l $7E0A00+CHAR_FACING_LEFT
    and #255
    cmp #2
    bcc SourceFacing_Adapt0Guard11
    brl SourceFacing_SlotDone0
SourceFacing_Adapt0Guard11:
.a16
.i16
    sta.l $437BB0
    cmp.l SourceAttackTemplate_Base+20
    bne SourceFacing_Adapt0Guard12
    brl SourceFacing_SlotDone0
SourceFacing_Adapt0Guard12:
.a16
.i16
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    sta.l $437BB4
    lda #1
    sta.l SourceAttackOwned_Busy
    sta.l SourcePacket_CopyBusy
    lda #0
    sta.l SourceAttackTemplate_Base+0
    ldx #0
SourceFacing_Piece0:
.a16
.i16
    lda.l $437BB0
    beq SourceFacing_Unflipped0
    lda.l SourceStandby_PiecesLong+4,x
    bra SourceFacing_Offset0
SourceFacing_Unflipped0:
.a16
.i16
    lda.l SourceStandby_PiecesLong,x
SourceFacing_Offset0:
.a16
.i16
    clc
    adc #128
    and #511
    sta.l $437BB2
    txa
    lsr a
    lsr a
    tax
    sep #$20
.a8
    lda.l $437BB2
    sta.l SourceAttackTemplate_Base+32,x
    lda.l SourceAttackTemplate_Base+35,x
    and #$BF
    ora.l $437BB4
    sta.l SourceAttackTemplate_Base+35,x
    rep #$30
.a16
.i16
    txa
    lsr a
    lsr a
    tax
    lda.l SourceAttackTemplate_Base+72,x
    and #2
    sta.l $437BB6
    lda.l $437BB2
    and #256
    xba
    ora.l $437BB6
    sep #$20
.a8
    sta.l SourceAttackTemplate_Base+72,x
    rep #$30
.a16
.i16
    txa
    asl a
    asl a
    asl a
    asl a
    clc
    adc #16
    tax
    cpx #160
    bcs SourceFacing_PiecesDone0
    brl SourceFacing_Piece0
SourceFacing_PiecesDone0:
.a16
.i16
    lda.l $437BB0
    sta.l SourceAttackTemplate_Base+20
    lda #$A770
    sta.l SourceAttackTemplate_Base+0
    lda #0
    sta.l SourceAttackOwned_Busy
    sta.l SourcePacket_CopyBusy
SourceFacing_SlotDone0:
.a16
.i16
    lda.l SourceStandby_FaceMask
    and #2
    bne SourceFacing_Adapt1Guard0
    brl SourceFacing_SlotDone1
SourceFacing_Adapt1Guard0:
.a16
.i16
    lda.l SourceAttackTemplate_Base+128
    cmp #$A770
    beq SourceFacing_Adapt1Guard1
    brl SourceFacing_SlotDone1
SourceFacing_Adapt1Guard1:
.a16
.i16
    lda.l $411AE6
    and #255
    cmp #9
    beq SourceFacing_Adapt1Guard2
    brl SourceFacing_SlotDone1
SourceFacing_Adapt1Guard2:
.a16
.i16
    lda.l $7E0A85+CHAR_THROW_ZPOS
    beq SourceFacing_Adapt1Guard3
    brl SourceFacing_SlotDone1
SourceFacing_Adapt1Guard3:
.a16
.i16
    lda.l $7E0A85+CHAR_SELECTED
    and #255
    cmp #3
    bcc SourceFacing_Adapt1Guard4
    brl SourceFacing_SlotDone1
SourceFacing_Adapt1Guard4:
.a16
.i16
    lda.l SourceAttackTemplate_Base+134
    cmp #534
    beq SourceFacing_Adapt1Guard5
    brl SourceFacing_SlotDone1
SourceFacing_Adapt1Guard5:
.a16
.i16
    lda.l SourceAttackTemplate_Base+136
    cmp #0
    beq SourceFacing_Adapt1Guard6
    brl SourceFacing_SlotDone1
SourceFacing_Adapt1Guard6:
.a16
.i16
    lda.l SourceAttackTemplate_Base+142
    cmp #128
    beq SourceFacing_Adapt1Guard7
    brl SourceFacing_SlotDone1
SourceFacing_Adapt1Guard7:
.a16
.i16
    lda.l SourceAttackTemplate_Base+144
    cmp #150
    beq SourceFacing_Adapt1Guard8
    brl SourceFacing_SlotDone1
SourceFacing_Adapt1Guard8:
.a16
.i16
    lda.l SourceAttackTemplate_Base+146
    cmp #0
    beq SourceFacing_Adapt1Guard9
    brl SourceFacing_SlotDone1
SourceFacing_Adapt1Guard9:
.a16
.i16
    lda.l SourceAttackTemplate_Base+150
    cmp #781
    beq SourceFacing_Adapt1Guard10
    brl SourceFacing_SlotDone1
SourceFacing_Adapt1Guard10:
.a16
.i16
    lda.l $7E0A85+CHAR_FACING_LEFT
    and #255
    cmp #2
    bcc SourceFacing_Adapt1Guard11
    brl SourceFacing_SlotDone1
SourceFacing_Adapt1Guard11:
.a16
.i16
    sta.l $437BB0
    cmp.l SourceAttackTemplate_Base+148
    bne SourceFacing_Adapt1Guard12
    brl SourceFacing_SlotDone1
SourceFacing_Adapt1Guard12:
.a16
.i16
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    sta.l $437BB4
    lda #1
    sta.l SourceAttackOwned_Busy
    sta.l SourcePacket_CopyBusy
    lda #0
    sta.l SourceAttackTemplate_Base+128
    ldx #0
SourceFacing_Piece1:
.a16
.i16
    lda.l $437BB0
    beq SourceFacing_Unflipped1
    lda.l SourceStandby_PiecesLong+4,x
    bra SourceFacing_Offset1
SourceFacing_Unflipped1:
.a16
.i16
    lda.l SourceStandby_PiecesLong,x
SourceFacing_Offset1:
.a16
.i16
    clc
    adc #128
    and #511
    sta.l $437BB2
    txa
    lsr a
    lsr a
    tax
    sep #$20
.a8
    lda.l $437BB2
    sta.l SourceAttackTemplate_Base+160,x
    lda.l SourceAttackTemplate_Base+163,x
    and #$BF
    ora.l $437BB4
    sta.l SourceAttackTemplate_Base+163,x
    rep #$30
.a16
.i16
    txa
    lsr a
    lsr a
    tax
    lda.l SourceAttackTemplate_Base+200,x
    and #2
    sta.l $437BB6
    lda.l $437BB2
    and #256
    xba
    ora.l $437BB6
    sep #$20
.a8
    sta.l SourceAttackTemplate_Base+200,x
    rep #$30
.a16
.i16
    txa
    asl a
    asl a
    asl a
    asl a
    clc
    adc #16
    tax
    cpx #160
    bcs SourceFacing_PiecesDone1
    brl SourceFacing_Piece1
SourceFacing_PiecesDone1:
.a16
.i16
    lda.l $437BB0
    sta.l SourceAttackTemplate_Base+148
    lda #$A770
    sta.l SourceAttackTemplate_Base+128
    lda #0
    sta.l SourceAttackOwned_Busy
    sta.l SourcePacket_CopyBusy
SourceFacing_SlotDone1:
.a16
.i16
SourceFacing_Done:
.a16
.i16
    pld
    plb
    ply
    plx
    pla
    plp
    rtl
SourceFacing_CaptureLive:
.a16
.i16
    jsl SourceAttackLease_Capture
    php
    rep #$30
    pha
    phx
    lda.l SourceVisual_ActorSlot
    cmp #2
    bcs SourceFacing_CaptureDone
    tax
    lda #$FFFE
    cpx #0
    beq SourceFacing_ClearMarker
    lda #$FFFD
SourceFacing_ClearMarker:
.a16
.i16
    and.l SourceStandby_FaceMask
    sta.l SourceStandby_FaceMask
SourceFacing_CaptureDone:
.a16
.i16
    plx
    pla
    plp
    rtl

SourceFacing_WalkLayout:
.a16
.i16
    lda.l SOURCE_PACKET_ACTIVE_META+2
    cmp #48
    bne SourceFacing_WalkNo
    lda.l SOURCE_PACKET_ACTIVE_META+12
    cmp #$0116
    bne SourceFacing_WalkNo
    lda.l SOURCE_PACKET_ACTIVE_META+44
    cmp #$0116
    bne SourceFacing_WalkNo
    jml SourceShape_Check4
SourceFacing_WalkNo:
.a16
.i16
    jml SourceShape_No

; The caller is the bank43 A8 private image rebaser. Preserve its exact ABI.
SourceLayout_StoreLow:
.a8
.i16
    php
    rep #$30
.a16
.i16
    pha
    phx
    txa
    clc
    adc.l $437BC0
    tax
    lda $03,s
    sep #$20
.a8
    sta.w $0000,x
    rep #$30
.a16
.i16
    plx
    pla
    plp
    rtl
SourceLayout_StoreHigh:
.a8
.i16
    php
    rep #$30
.a16
.i16
    pha
    phx
    tya
    clc
    adc.l $437BC2
    tax
    lda $03,s
    sep #$20
.a8
    sta.w $0000,x
    rep #$30
.a16
.i16
    plx
    pla
    plp
    rts
; Only Carry is consumed by the original BCC loop. All registers preserved.
SourceLayout_SeedCompare:
.a16
.i16
    pha
    tya
    cmp.l $437BC6
    pla
    rts
SourceLayout_PackCompare:
.a16
.i16
    pha
    tya
    cmp.l $437BC4
    pla
    rts

SourceNormalize_LowCompare:
.a16
.i16
    pha
    txa
    cmp.l $437BB8
    pla
    rts
SourceNormalize_HighCompare:
.a16
.i16
    pha
    txa
    cmp.l $437BBA
    pla
    rts

; A ground root may never replace a player who has accepted jump/air.
; Facing2 is an impossible template face, rejected by both existing guards.
SourceGroundRoot_Face0:
.a16
.i16
    lda.l $7E0A00+CHAR_SELECTED
    and #255
    cmp #3
    bcs SourceGroundRoot_No0
    lda.l $7E0A00+67
    bne SourceGroundRoot_No0
    lda.l $7E0A00+CHAR_FACING_LEFT
    and #255
    rtl
SourceGroundRoot_No0:
.a16
.i16
    lda #2
    rtl
SourceGroundRoot_Face1:
.a16
.i16
    lda.l $7E0A85+CHAR_SELECTED
    and #255
    cmp #3
    bcs SourceGroundRoot_No1
    lda.l $7E0A85+67
    bne SourceGroundRoot_No1
    lda.l $7E0A85+CHAR_FACING_LEFT
    and #255
    rtl
SourceGroundRoot_No1:
.a16
.i16
    lda #2
    rtl
