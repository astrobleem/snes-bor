; Exact private-OAM physical completion, never a tile/palette Ready path.
; 12 bytes in the verified gap after MainRetryRemaining and before NPC Build.
SourceTicket_Row = $435474
SourceTicket_Pass = $435476
SourceTicket_State = $435478
SourceTicket_Camera = $43547A
SourceTicket_Stage = $43547C
SourceTicket_Magic = $43547E
SourceTicket_Scope:
.a16
.i16
    lda.l Game_CampaignId
    and #255
    cmp #3
    beq SourceTicket_G1
    brl SourceTicket_ScopeNo
SourceTicket_G1:
.a16
.i16
    lda.l Game_State
    cmp #0
    beq SourceTicket_G2
    brl SourceTicket_ScopeNo
SourceTicket_G2:
.a16
.i16
    lda.l Game_StageIndex
    cmp #0
    beq SourceTicket_G3
    brl SourceTicket_ScopeNo
SourceTicket_G3:
.a16
.i16
    lda.l Stage_Mirror
    and #255
    cmp #0
    beq SourceTicket_G4
    brl SourceTicket_ScopeNo
SourceTicket_G4:
.a16
.i16
    lda.l $7E175E
    cmp #2
    beq SourceTicket_G5
    brl SourceTicket_ScopeNo
SourceTicket_G5:
.a16
.i16
    lda.l $7E1760
    cmp #1
    beq SourceTicket_G6
    brl SourceTicket_ScopeNo
SourceTicket_G6:
.a16
.i16
    lda.l $7E46DC
    cmp #1
    beq SourceTicket_G7
    brl SourceTicket_ScopeNo
SourceTicket_G7:
.a16
.i16
    lda.l $7E46DE
    cmp #0
    beq SourceTicket_G8
    brl SourceTicket_ScopeNo
SourceTicket_G8:
.a16
.i16
    lda.l SourceInput_Magic
    cmp #6752
    beq SourceTicket_G9
    brl SourceTicket_ScopeNo
SourceTicket_G9:
.a16
.i16
    lda.l SourceVisual_CompletedMagic
    cmp #49229
    beq SourceTicket_G10
    brl SourceTicket_ScopeNo
SourceTicket_G10:
.a16
.i16
    lda.l SVActor_Magic
    cmp #44057
    beq SourceTicket_G11
    brl SourceTicket_ScopeNo
SourceTicket_G11:
.a16
.i16
    sec
    rts
SourceTicket_ScopeNo:
.a16
.i16
    clc
    rts
SourceTicket_RawFields:
.a16
.i16
    txa
    cmp #64
    bcs SourceTicket_RawNo
    and #7
    bne SourceTicket_RawNo
    lda.l DmaQueue+7,x
    and #255
    cmp #67
    beq SourceTicket_G12
    brl SourceTicket_RawNo
SourceTicket_G12:
.a16
.i16
    lda.l DmaQueue+5,x
    cmp #20224
    beq SourceTicket_G13
    brl SourceTicket_RawNo
SourceTicket_G13:
.a16
.i16
    lda.l DmaQueue,x
    cmp #544
    beq SourceTicket_G14
    brl SourceTicket_RawNo
SourceTicket_G14:
.a16
.i16
    lda.l DmaQueue+2,x
    cmp #0
    beq SourceTicket_G15
    brl SourceTicket_RawNo
SourceTicket_G15:
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
    cmp #0
    bne SourceTicket_RawNo
    sec
    rts
SourceTicket_RawNo:
.a16
.i16
    clc
    rts
SourceTicket_RawActive:
.a16
.i16
    txa
    cmp #64
    bcc SourceTicket_RawInRange
    brl SourceTicket_RawNo
SourceTicket_RawInRange:
.a16
.i16
    and #7
    beq SourceTicket_RawAligned
    brl SourceTicket_RawNo
SourceTicket_RawAligned:
.a16
.i16
    lda.l DmaQueue+4,x
    and #255
    cmp #65
    beq SourceTicket_G16
    brl SourceTicket_RawNo
SourceTicket_G16:
.a16
.i16
    jmp SourceTicket_RawFields
SourceTicket_IsOwnRow:
.a16
.i16
    jsr SourceTicket_RawFields
    bcs SourceTicket_OwnFields
    clc
    rtl
SourceTicket_OwnFields:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$00FF
    cmp #$41
    bne SourceTicket_OwnReceipt
    lda #0
    sec
    rtl
SourceTicket_OwnReceipt:
.a16
.i16
    cmp #0
    beq SourceTicket_OwnInactive
    clc
    rtl
SourceTicket_OwnInactive:
.a16
.i16
    jsr SourceTicket_Scope
    bcs SourceTicket_OwnScope
    clc
    rtl
SourceTicket_OwnScope:
.a16
.i16
    lda.l SourceVisual_CompletedHeld
    and #255
    cmp #1
    beq SourceTicket_G17
    brl SourceTicket_OwnNo
SourceTicket_G17:
.a16
.i16
    lda.l Nmi_FrameBusy
    and #255
    cmp #1
    beq SourceTicket_G18
    brl SourceTicket_OwnNo
SourceTicket_G18:
.a16
.i16
    lda.l SourcePacket_ThisFrame
    cmp #1
    beq SourceTicket_G19
    brl SourceTicket_OwnNo
SourceTicket_G19:
.a16
.i16
    lda.l SourcePacket_ActiveValid
    cmp #1
    beq SourceTicket_G20
    brl SourceTicket_OwnNo
SourceTicket_G20:
.a16
.i16
    lda.l SourcePacket_CopyBusy
    cmp #0
    beq SourceTicket_G21
    brl SourceTicket_OwnNo
SourceTicket_G21:
.a16
.i16
    lda.l SourceTicket_Magic
    cmp #20559
    beq SourceTicket_G22
    brl SourceTicket_OwnNo
SourceTicket_G22:
.a16
.i16
    lda.l SourceTicket_State
    cmp #2
    beq SourceTicket_G23
    brl SourceTicket_OwnNo
SourceTicket_G23:
.a16
.i16
    txa
    cmp.l SourceTicket_Row
    bne SourceTicket_OwnNo
    lda.l SourceTicket_Pass
    cmp.l SourceVisual_AfterPassCount
    bne SourceTicket_OwnNo
    lda.l SourceTicket_Stage
    cmp.l Game_StageIndex
    bne SourceTicket_OwnNo
    lda.l SourceTicket_Camera
    cmp.l SourcePacket_ActiveCamera
    bne SourceTicket_OwnNo
    cmp.l Screen_PosX
    bne SourceTicket_OwnNo
SourceTicket_OwnYes:
.a16
.i16
    lda #0
    sec
    rtl
SourceTicket_OwnNo:
.a16
.i16
    clc
    rtl
SourceTicket_Begin:
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
    sep #$20
.a8
    lda #0
    pha
    plb
    rep #$30
.a16
    jsr SourceTicket_Scope
    bcc SourceTicket_BeginReturn
    lda #0
    sta.l SourceTicket_State
    sta.l SourceTicket_Magic
SourceTicket_BeginReturn:
.a16
.i16
    rep #$30
    pld
    plb
    ply
    plx
    pla
    plp
    rtl
SourceTicket_Issue:
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
    sep #$20
.a8
    lda #0
    pha
    plb
    rep #$30
.a16
    jsr SourceTicket_Scope
    bcs SourceTicket_IssueScope
    brl SourceTicket_IssueReturn
SourceTicket_IssueScope:
.a16
.i16
    lda.l SourceVisual_CompletedHeld
    and #255
    cmp #1
    beq SourceTicket_G24
    brl SourceTicket_IssueReturn
SourceTicket_G24:
.a16
.i16
    lda.l Nmi_FrameBusy
    and #255
    cmp #1
    beq SourceTicket_G25
    brl SourceTicket_IssueReturn
SourceTicket_G25:
.a16
.i16
    lda.l SourcePacket_ThisFrame
    cmp #1
    beq SourceTicket_G26
    brl SourceTicket_IssueReturn
SourceTicket_G26:
.a16
.i16
    lda.l SourcePacket_ActiveValid
    cmp #1
    beq SourceTicket_G27
    brl SourceTicket_IssueReturn
SourceTicket_G27:
.a16
.i16
    lda.l SourcePacket_CopyBusy
    cmp #0
    beq SourceTicket_G28
    brl SourceTicket_IssueReturn
SourceTicket_G28:
.a16
.i16
    lda #0
    sta.l SourceTicket_State
    sta.l SourceTicket_Magic
    ldy #$FFFF
    ldx #0
SourceTicket_IssueLoop:
.a16
.i16
    jsr SourceTicket_RawActive
    bcc SourceTicket_IssueNext
    tya
    cmp #$FFFF
    beq SourceTicket_IssueFirst
    brl SourceTicket_IssueReturn
SourceTicket_IssueFirst:
.a16
.i16
    txa
    tay
SourceTicket_IssueNext:
.a16
.i16
    txa
    clc
    adc #8
    tax
    cpx #64
    bcc SourceTicket_IssueLoop
    tya
    cmp #$FFFF
    bne SourceTicket_IssueFound
    brl SourceTicket_IssueReturn
SourceTicket_IssueFound:
.a16
.i16
    sta.l SourceTicket_Row
    lda.l SourceVisual_AfterPassCount
    sta.l SourceTicket_Pass
    lda.l SourcePacket_ActiveCamera
    sta.l SourceTicket_Camera
    lda.l Game_StageIndex
    sta.l SourceTicket_Stage
    lda #$504F
    sta.l SourceTicket_Magic
    lda #1
    sta.l SourceTicket_State
SourceTicket_IssueReturn:
.a16
.i16
    rep #$30
    pld
    plb
    ply
    plx
    pla
    plp
    rtl
SourceTicket_NmiSkip:
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
    sep #$20
.a8
    lda #0
    pha
    plb
    rep #$30
.a16
    sep #$20
.a8
    lda #2
    sta.l Nmi_FrameOver
    rep #$30
.a16
    jsr SourceTicket_Scope
    bcs SourceTicket_NmiScope
    brl SourceTicket_NmiReturn
SourceTicket_NmiScope:
.a16
.i16
    lda.l Nmi_Busy
    and #255
    cmp #0
    beq SourceTicket_G29
    brl SourceTicket_NmiReturn
SourceTicket_G29:
.a16
.i16
    lda.l Nmi_FrameBusy
    and #255
    cmp #1
    beq SourceTicket_G30
    brl SourceTicket_NmiReturn
SourceTicket_G30:
.a16
.i16
    lda.l SourceVisual_CompletedHeld
    and #255
    cmp #1
    beq SourceTicket_G31
    brl SourceTicket_NmiReturn
SourceTicket_G31:
.a16
.i16
    lda.l SourceVisual_CompletedSavedBusy
    and #255
    cmp #0
    beq SourceTicket_G32
    brl SourceTicket_NmiReturn
SourceTicket_G32:
.a16
.i16
    lda.l SourceVisual_CompletedEarly
    cmp #0
    beq SourceTicket_G33
    brl SourceTicket_NmiReturn
SourceTicket_G33:
.a16
.i16
    lda.l Oam_UploadFlag
    cmp #1
    beq SourceTicket_G34
    brl SourceTicket_NmiReturn
SourceTicket_G34:
.a16
.i16
    lda.l SourcePacket_ThisFrame
    cmp #1
    beq SourceTicket_G35
    brl SourceTicket_NmiReturn
SourceTicket_G35:
.a16
.i16
    lda.l SourcePacket_ActiveValid
    cmp #1
    beq SourceTicket_G36
    brl SourceTicket_NmiReturn
SourceTicket_G36:
.a16
.i16
    lda.l SourcePacket_CopyBusy
    cmp #0
    beq SourceTicket_G37
    brl SourceTicket_NmiReturn
SourceTicket_G37:
.a16
.i16
    lda.l SourceTicket_Magic
    cmp #20559
    beq SourceTicket_G38
    brl SourceTicket_NmiReturn
SourceTicket_G38:
.a16
.i16
    lda.l SourceTicket_State
    cmp #1
    beq SourceTicket_G39
    brl SourceTicket_NmiReturn
SourceTicket_G39:
.a16
.i16
    lda.l Nmi_HdmaEnableCurrent
    and #255
    cmp #0
    beq SourceTicket_G40
    brl SourceTicket_NmiReturn
SourceTicket_G40:
.a16
.i16
    lda.l StageWater_Dirty
    cmp #0
    beq SourceTicket_G41
    brl SourceTicket_NmiReturn
SourceTicket_G41:
.a16
.i16
    lda.l Screen_PosY
    cmp #0
    beq SourceTicket_G42
    brl SourceTicket_NmiReturn
SourceTicket_G42:
.a16
.i16
    lda.l Nmi_Bg1ScrollY
    cmp #0
    beq SourceTicket_G43
    brl SourceTicket_NmiReturn
SourceTicket_G43:
.a16
.i16
    lda.l SourceVisual_CompletedAwait
    ora.l SourceVisual_CompletedRetire
    bne SourceTicket_NmiPending
    brl SourceTicket_NmiReturn
SourceTicket_NmiPending:
.a16
.i16
    lda.l SourceTicket_Pass
    cmp.l SourceVisual_AfterPassCount
    beq SourceTicket_G44
    brl SourceTicket_NmiReturn
SourceTicket_G44:
.a16
.i16
    lda.l SourceTicket_Stage
    cmp.l Game_StageIndex
    beq SourceTicket_G45
    brl SourceTicket_NmiReturn
SourceTicket_G45:
.a16
.i16
    lda.l SourceTicket_Camera
    cmp.l SourcePacket_ActiveCamera
    beq SourceTicket_G46
    brl SourceTicket_NmiReturn
SourceTicket_G46:
.a16
.i16
    lda.l SourceTicket_Camera
    cmp.l Screen_PosX
    beq SourceTicket_G47
    brl SourceTicket_NmiReturn
SourceTicket_G47:
.a16
.i16
    lda.l SourceTicket_Camera
    cmp.l Nmi_Bg1ScrollX
    beq SourceTicket_G48
    brl SourceTicket_NmiReturn
SourceTicket_G48:
.a16
.i16
    lda.l SourceTicket_Row
    tax
    jsr SourceTicket_RawActive
    bcs SourceTicket_NmiRow
    brl SourceTicket_NmiReturn
SourceTicket_NmiRow:
.a16
.i16
    ldy #0
    ldx #0
SourceTicket_NmiQueueLoop:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$0040
    bne SourceTicket_NmiQueueActive
    brl SourceTicket_NmiQueueNext
SourceTicket_NmiQueueActive:
.a16
.i16
    txa
    cmp.l SourceTicket_Row
    beq SourceTicket_NmiQueueSum
    lda.l DmaQueue+4,x
    and #$00FF
    cmp #$40
    beq SourceTicket_NmiQueueSum
    cmp #$42
    beq SourceTicket_NmiQueueSum
    cmp #$43
    beq SourceTicket_NmiQueueSum
    cmp #$41
    beq SourceTicket_NmiLegacyHi
    brl SourceTicket_NmiReturn
SourceTicket_NmiLegacyHi:
.a16
.i16
    lda.l DmaQueue+7,x
    and #255
    cmp #126
    beq SourceTicket_G49
    brl SourceTicket_NmiReturn
SourceTicket_G49:
.a16
.i16
    lda.l DmaQueue+5,x
    cmp #21248
    beq SourceTicket_G50
    brl SourceTicket_NmiReturn
SourceTicket_G50:
.a16
.i16
    lda.l DmaQueue+2,x
    cmp #256
    beq SourceTicket_G51
    brl SourceTicket_NmiReturn
SourceTicket_G51:
.a16
.i16
    lda.l DmaQueue,x
    cmp #33
    bcc SourceTicket_G52
    brl SourceTicket_NmiReturn
SourceTicket_G52:
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
    cmp #0
    beq SourceTicket_NmiQueueSum
    brl SourceTicket_NmiReturn
SourceTicket_NmiQueueSum:
.a16
.i16
    lda.l DmaQueue,x
    cmp #0
    bne SourceTicket_G53
    brl SourceTicket_NmiReturn
SourceTicket_G53:
.a16
.i16
    tya
    clc
    adc.l DmaQueue,x
    bcc SourceTicket_NmiQueueNoWrap
    brl SourceTicket_NmiReturn
SourceTicket_NmiQueueNoWrap:
.a16
.i16
    tay
SourceTicket_NmiQueueNext:
.a16
.i16
    txa
    clc
    adc #8
    tax
    cpx #64
    bcs SourceTicket_NmiQueueDone
    brl SourceTicket_NmiQueueLoop
SourceTicket_NmiQueueDone:
.a16
.i16
    tya
    cmp.l DmaQueue_BudgetTotal
    beq SourceTicket_NmiBudgetMatches
    brl SourceTicket_NmiReturn
SourceTicket_NmiBudgetMatches:
.a16
.i16
    lda.l DmaQueue_BudgetTotal
    cmp #2817
    bcc SourceTicket_G54
    brl SourceTicket_NmiReturn
SourceTicket_G54:
.a16
.i16
    sep #$20
.a8
    lda $4212
    and #$80
    bne SourceTicket_NmiVblank
    brl SourceTicket_NmiReturn
SourceTicket_NmiVblank:
.a16
.i16
    sep #$20
.a8
    lda $4213
    and #$80
    bne SourceTicket_NmiLatchEnabled
    brl SourceTicket_NmiReturn
SourceTicket_NmiLatchEnabled:
.a8
.i16
    lda $2137
    lda $213F
    lda $213D
    rep #$20
.a16
    and #$00FF
    tay
    sep #$20
.a8
    lda $213D
    and #1
    beq SourceTicket_NmiCounterLow
    brl SourceTicket_NmiReturn
SourceTicket_NmiCounterLow:
.a16
.i16
    rep #$30
    tya
    cmp #224
    bcs SourceTicket_NmiCounterStart
    brl SourceTicket_NmiReturn
SourceTicket_NmiCounterStart:
.a16
.i16
    cmp #246
    bcc SourceTicket_NmiCounterSafe
    brl SourceTicket_NmiReturn
SourceTicket_NmiCounterSafe:
.a16
.i16
    lda.l SourceTicket_State
    cmp #1
    beq SourceTicket_G55
    brl SourceTicket_NmiReturn
SourceTicket_G55:
.a16
.i16
    lda.l SourceTicket_Row
    tax
    jsr SourceTicket_RawActive
    bcs SourceTicket_NmiPhysical
    brl SourceTicket_NmiReturn
SourceTicket_NmiPhysical:
.a16
.i16
    sep #$20
.a8
    lda #1
    sta.l Nmi_Busy
    rep #$30
.a16
    jsl Core_Dma_TransferOam
    sep #$20
.a8
    lda $4212
    and #$80
    bne SourceTicket_NmiCompleted
    brl SourceTicket_NmiReleaseBusy
SourceTicket_NmiCompleted:
.a16
.i16
    sep #$20
.a8
    lda #0
    sta.l DmaQueue+4,x
    rep #$30
.a16
    lda.l DmaQueue_BudgetTotal
    sec
    sbc #544
    sta.l DmaQueue_BudgetTotal
    lda #2
    sta.l SourceTicket_State
SourceTicket_NmiReleaseBusy:
.a16
.i16
    sep #$20
.a8
    lda #0
    sta.l Nmi_Busy
    rep #$30
.a16
SourceTicket_NmiReturn:
.a16
.i16
    rep #$30
    pld
    plb
    ply
    plx
    pla
    plp
    rtl
SourceTicket_End:
.a16
.i16
