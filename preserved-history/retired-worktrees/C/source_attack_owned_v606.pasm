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
    lda.l $434E7C
    cmp.l SourcePacket_ReadSeq
    beq SourceAttackOwned_G38
    brl SourceAttackOwned_Done
SourceAttackOwned_G38:
.a16
.i16
    lda.l $434E7C
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
    lda.l $434E36
    sta.l SourceAttackOwned_ReadY0
    lda.l $434E5A
    sta.l SourceAttackOwned_ReadY1
    lda.l $434E7C
    cmp.l SourcePacket_ReadSeq
    beq SourceAttackOwned_G58
    brl SourceAttackOwned_Done
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
