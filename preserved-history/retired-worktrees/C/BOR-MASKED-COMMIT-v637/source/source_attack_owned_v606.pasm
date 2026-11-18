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
    lda #$B077
    sta.l SourceAttackOwned_InitMagic
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
    php
    rep #$30
    pha
    lda.l SourceAttackTemplate_Base
    cmp #SourceAttackTemplate_Magic
    bne SourceAttackOwned_QueuedDone
    lda.l SourceAttackTemplate_Base+128
    cmp #SourceAttackTemplate_Magic
    bne SourceAttackOwned_QueuedDone
    pla
    plp
    jml SourceAttackOwned_Snapshot
SourceAttackOwned_QueuedDone:
.a16
.i16
    pla
    plp
    rtl
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
    lda.l SourceAttackTemplate_Base+0
    cmp #SourceAttackTemplate_Magic
    beq SourceAttackOwned_G5
    brl SourceAttackOwned_Done
SourceAttackOwned_G5:
.a16
.i16
    lda.l SourceAttackTemplate_Base+2
    cmp #0
    beq SourceAttackOwned_G6
    brl SourceAttackOwned_Done
SourceAttackOwned_G6:
.a16
.i16
    lda.l SourceAttackTemplate_Base+4
    cmp #22
    beq SourceAttackOwned_G7
    brl SourceAttackOwned_Done
SourceAttackOwned_G7:
.a16
.i16
    lda.l SourceAttackTemplate_Base+6
    cmp #534
    beq SourceAttackOwned_G8
    brl SourceAttackOwned_Done
SourceAttackOwned_G8:
.a16
.i16
    lda.l SourceAttackTemplate_Base+8
    cmp #0
    beq SourceAttackOwned_G9
    brl SourceAttackOwned_Done
SourceAttackOwned_G9:
.a16
.i16
    lda.l SourceAttackTemplate_Base+20
    cmp #0
    beq SourceAttackOwned_G10
    brl SourceAttackOwned_Done
SourceAttackOwned_G10:
.a16
.i16
    lda.l SourceAttackTemplate_Base+128
    cmp #SourceAttackTemplate_Magic
    beq SourceAttackOwned_G11
    brl SourceAttackOwned_Done
SourceAttackOwned_G11:
.a16
.i16
    lda.l SourceAttackTemplate_Base+130
    cmp #0
    beq SourceAttackOwned_G12
    brl SourceAttackOwned_Done
SourceAttackOwned_G12:
.a16
.i16
    lda.l SourceAttackTemplate_Base+132
    cmp #22
    beq SourceAttackOwned_G13
    brl SourceAttackOwned_Done
SourceAttackOwned_G13:
.a16
.i16
    lda.l SourceAttackTemplate_Base+134
    cmp #534
    beq SourceAttackOwned_G14
    brl SourceAttackOwned_Done
SourceAttackOwned_G14:
.a16
.i16
    lda.l SourceAttackTemplate_Base+136
    cmp #0
    beq SourceAttackOwned_G15
    brl SourceAttackOwned_Done
SourceAttackOwned_G15:
.a16
.i16
    lda.l SourceAttackTemplate_Base+148
    cmp #0
    beq SourceAttackOwned_G16
    brl SourceAttackOwned_Done
SourceAttackOwned_G16:
.a16
.i16
    lda.l $4119E6
    and #255
    cmp #9
    beq SourceAttackOwned_G17
    brl SourceAttackOwned_Done
SourceAttackOwned_G17:
.a16
.i16
    lda.l $411AE6
    and #255
    cmp #9
    beq SourceAttackOwned_G18
    brl SourceAttackOwned_Done
SourceAttackOwned_G18:
.a16
.i16
    lda.l SourceAttackOwned_Suppressed
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
    cmp #80
    beq SourceAttackOwned_G25
    brl SourceAttackOwned_Done
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
    lda.l SOURCE_PACKET_ACTIVE_META+18
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
    lda.l SOURCE_PACKET_ACTIVE_META+50
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
    ldx #$4F00
    ldy #$7600
    lda #543
    mvn $43,$43
    lda #0
    sta.l SourcePacket_CopyBusy
    sta.l SourceAttackOwned_Busy
    ; State3 means the private base awaits its one bounded NMI patch.
    lda #3
    sta.l SourceAttackOwned_State
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
    lda.l SourceClock4086_FieldsLo
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
    lda.l SourcePacket_RefreshAccepted
    cmp #1
    beq SourceAttackOwned_G37
    brl SourceAttackOwned_Done
SourceAttackOwned_G37:
.a16
.i16
    lda.l SourcePacket_ReadSeq
    bra SourceAttackOwned_SealedSeq
SourceAttackOwned_G38:
.a16
.i16
    lda.l SourcePacket_ReadSeq
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
    lda.l $4119E6
    and #255
    cmp #9
    beq SourceAttackOwned_G44
    brl SourceAttackOwned_Done
SourceAttackOwned_G44:
.a16
.i16
    lda.l $411AE6
    and #255
    cmp #9
    beq SourceAttackOwned_G45
    brl SourceAttackOwned_Done
SourceAttackOwned_G45:
.a16
.i16
    lda.l SourceAttackTemplate_Base+0
    cmp #SourceAttackTemplate_Magic
    beq SourceAttackOwned_G46
    brl SourceAttackOwned_Done
SourceAttackOwned_G46:
.a16
.i16
    lda.l SourceAttackTemplate_Base+128
    cmp #SourceAttackTemplate_Magic
    beq SourceAttackOwned_G47
    brl SourceAttackOwned_Done
SourceAttackOwned_G47:
.a16
.i16
    lda.l SOURCE_PACKET_MOTION+4
    cmp #1
    beq SourceAttackOwned_G48
    brl SourceAttackOwned_Done
SourceAttackOwned_G48:
.a16
.i16
    lda.l SOURCE_PACKET_MOTION+6
    cmp #0
    beq SourceAttackOwned_G49
    brl SourceAttackOwned_Done
SourceAttackOwned_G49:
.a16
.i16
    lda.l SOURCE_PACKET_MOTION+12
    cmp #0
    beq SourceAttackOwned_G50
    brl SourceAttackOwned_Done
SourceAttackOwned_G50:
.a16
.i16
    lda.l SOURCE_PACKET_MOTION+8
    bne SourceAttackOwned_G51
    brl SourceAttackOwned_Done
SourceAttackOwned_G51:
.a16
.i16
    lda.l SOURCE_PACKET_MOTION+10
    and #255
    cmp #2
    beq SourceAttackOwned_G52
    brl SourceAttackOwned_Done
SourceAttackOwned_G52:
.a16
.i16
    lda.l SOURCE_PACKET_MOTION+20
    cmp #1
    beq SourceAttackOwned_G53
    brl SourceAttackOwned_Done
SourceAttackOwned_G53:
.a16
.i16
    lda.l SOURCE_PACKET_MOTION+22
    cmp #0
    beq SourceAttackOwned_G54
    brl SourceAttackOwned_Done
SourceAttackOwned_G54:
.a16
.i16
    lda.l SOURCE_PACKET_MOTION+28
    cmp #133
    beq SourceAttackOwned_G55
    brl SourceAttackOwned_Done
SourceAttackOwned_G55:
.a16
.i16
    lda.l SOURCE_PACKET_MOTION+24
    bne SourceAttackOwned_G56
    brl SourceAttackOwned_Done
SourceAttackOwned_G56:
.a16
.i16
    lda.l SOURCE_PACKET_MOTION+26
    and #255
    cmp #2
    beq SourceAttackOwned_G57
    brl SourceAttackOwned_Done
SourceAttackOwned_G57:
.a16
.i16
    lda.l SOURCE_PACKET_MOTION+14
    sta.l SourceAttackOwned_ReadY0
    lda.l SOURCE_PACKET_MOTION+30
    sta.l SourceAttackOwned_ReadY1
SourceAttackOwned_G58:
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
    lda.l SOURCE_PACKET_MOTION+0
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
    lda.l SOURCE_PACKET_MOTION+16
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
    ldx #$7420
    ldy #$7600
    lda #39
    mvn $43,$43
    ldx #$74A0
    ldy #$7628
    lda #39
    mvn $43,$43
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
    sta.l SourceAttackOwned_Image+40,x
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
    sta.w $782A,y
    rep #$20
.a16
    txa
    clc
    adc #4
    tax
    iny
    cpy #10
    bcc SourceAttackOwned_P2
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
    cpy #5
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
    lda.l $4119E6
    and #255
    cmp #9
    bne SourceAttackOwned_NoPair
    lda.l $411AE6
    and #255
    cmp #9
    beq SourceAttackOwned_CheckAck
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
    lda.l $4119E6
    and #255
    cmp #9
    beq SourceAttackOwned_G73
    brl SourceAttackOwned_Done
SourceAttackOwned_G73:
.a16
.i16
    lda.l $411AE6
    and #255
    cmp #9
    beq SourceAttackOwned_G74
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
    lda.l $4119E6
    and #255
    cmp #9
    bne SourceAttackOwned_ProceedPublish
    lda.l $411AE6
    and #255
    cmp #9
    bne SourceAttackOwned_ProceedPublish
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
    jsl SourcePacket_NmiPublish
    lda.l SourceAttackOwned_Use
    beq SourceAttackOwned_NormalAck
    lda.l SourcePacket_NmiPending
    bne SourceAttackOwned_RestorePending
    lda #2
    sta.l SourceAttackOwned_State
    lda #0
    sta.l $437A96
    lda #3
    sta.l $437A98
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
    lda.l SourceClock4086_FieldsLo
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
    jsl SourceAttackLease_Adopt
    lda.l $437A9A
    beq SourceAttackLease_StillHeld
    lda.l $437A96
    and.l $437A9A
    cmp.l $437A9A
    beq SourceAttackOwned_ReleaseAllowed
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
    lda.l SourcePacket_NmiPending
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
    brl SourceAttackOwned_ServiceDone
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
    jsl SourceAttackLease_Adopt
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
