; Initial live transport slice: existing normal image and resource protocol.
; No accepted-pose graft, independent next-lease adoption or damage changes.
; One SCPU producer; SA1 never writes this record. Existing CopyBusy excludes
; the other image writers. Reserved/active alias scans exclude queue writers.
SourceQueueTx_Magic = $434EA0
SourceQueueTx_Phase = $434EA2
SourceQueueTx_TicketLow = $434EA4
SourceQueueTx_TicketHigh = $434EA6
SourceQueueTx_EpochLow = $434EA8
SourceQueueTx_EpochHigh = $434EAA
SourceQueueTx_Row = $434EAC
SourceQueueTx_SceneLow = $434EAE
SourceQueueTx_SceneHigh = $434EB0
SourceQueueTx_SealTicketLow = $434EB2
SourceQueueTx_SealTicketHigh = $434EB4
SourceQueueTx_SealEpochLow = $434EB6
SourceQueueTx_SealEpochHigh = $434EB8
SourceQueueTx_AckTicketLow = $434EBA
SourceQueueTx_AckTicketHigh = $434EBC
SourceQueueTx_AckEpochLow = $434EBE
SourceQueueTx_AckEpochHigh = $434EC0
SourceQueueTx_AckRow = $434EC2
SourceQueueTx_SealMagic = $434EC4
SourceQueueTx_Published = $434EC6
SourceQueueTx_Acknowledged = $434EC8
SourceQueueTx_Cancelled = $434ECA
SourceQueueTx_Fault = $434ECC
; Phases:0 free,1 reserved,2 sealed,3 published,4 physically ACKed,
; 5 fault (fail closed),6 aborted before publication. No pin writes here.
.bank 39
.org $A300
SourceQueueTx_Init:
.a16
.i16
    jsl SourceAttackOwned_Init
    php
    rep #$30
    pha
    phx
    lda.l Game_CampaignId
    and #255
    cmp #3
    bne SourceQueueTx_InitDone
    lda.l Game_StageIndex
    bne SourceQueueTx_InitDone
    lda.l SourceQueueTx_Magic
    cmp #$5451
    bne SourceQueueTx_InitClear
    lda.l SourceQueueTx_Phase
    beq SourceQueueTx_InitClear
    cmp #4
    bne SourceQueueTx_InitDone
SourceQueueTx_InitClear:
.a16
.i16
    ldx #0
    lda #0
SourceQueueTx_InitLoop:
.a16
.i16
    sta.l SourceQueueTx_Magic,x
    inx
    inx
    cpx #48
    bcc SourceQueueTx_InitLoop
    lda #1
    sta.l SourceQueueTx_EpochLow
    lda #$5451
    sta.l SourceQueueTx_Magic
SourceQueueTx_InitDone:
.a16
.i16
    plx
    pla
    plp
    rtl

SourceQueueTx_Main:
.a16
.i16
    php
    rep #$30
    pha
    lda.l SourceQueueTx_Magic
    cmp #$5451
    bne SourceQueueTx_MainGo
    lda.l SourceQueueTx_Phase
    beq SourceQueueTx_MainGo
    cmp #4
    bne SourceQueueTx_MainHold
    jsr SourceQueueTx_Receipt
    bcs SourceQueueTx_MainGo
SourceQueueTx_MainHold:
.a16
.i16
    ; Never rewrite an image with an outstanding or failed receipt.
    pla
    plp
    clc
    rtl
SourceQueueTx_MainGo:
.a16
.i16
    pla
    plp
    jml SourcePacket_EnqueueMain

SourceQueueTx_Begin:
.a16
.i16
    jsl SourceAttackLease_BeforeScene
    php
    rep #$30
    cld
    pha
    phx
    phy
    jsl SourceQueueTx_Reserve
    ply
    plx
    pla
    plp
    rtl

SourceQueueTx_Reserve:
.a16
.i16
    lda.l Game_StageIndex
    bne SourceQueueTx_ReserveReturn
    lda.l SourceQueueTx_Magic
    cmp #$5451
    bne SourceQueueTx_ReserveReturn
    lda.l SourceQueueTx_Phase
    beq SourceQueueTx_ReserveReady
    cmp #4
    bne SourceQueueTx_ReserveReturn
    jsr SourceQueueTx_Receipt
    bcc SourceQueueTx_ReserveFault
SourceQueueTx_ReserveReady:
.a16
.i16
    lda.l SourcePacket_CopyBusy
    cmp #1
    bne SourceQueueTx_ReserveFault
    lda #6
    sta.l SourceQueueTx_Phase
    jsl Core_Dma_HasFreeSlot_Long
    bcc SourceQueueTx_ReserveReturn
    ; X already names the free row; no scratch is needed below.
    lda.l SourceQueueTx_TicketLow
    inc a
    sta.l SourceQueueTx_TicketLow
    bne SourceQueueTx_ReserveTicket
    lda.l SourceQueueTx_TicketHigh
    inc a
    sta.l SourceQueueTx_TicketHigh
    bne SourceQueueTx_ReserveTicket
    lda.l SourceQueueTx_EpochLow
    inc a
    sta.l SourceQueueTx_EpochLow
    bne SourceQueueTx_ReserveTicket
    lda.l SourceQueueTx_EpochHigh
    inc a
    sta.l SourceQueueTx_EpochHigh
    beq SourceQueueTx_ReserveFault
SourceQueueTx_ReserveTicket:
.a16
.i16
    txa
    sta.l SourceQueueTx_Row
    lda.l SourceNextScene_Low
    sta.l SourceQueueTx_SceneLow
    lda.l SourceNextScene_High
    sta.l SourceQueueTx_SceneHigh
    lda #0
    sta.l SourceQueueTx_SealMagic
    sta.l DmaQueue+2,x
    lda #544
    sta.l DmaQueue,x
    lda #$4F00
    sta.l DmaQueue+5,x
    sep #$20
.a8
    lda #$43
    sta.l DmaQueue+7,x
    phx
    rep #$30
.a16
    txa
    lsr a
    lsr a
    lsr a
    tax
    sep #$20
.a8
    lda #0
    sta.l DmaQueue_Owner,x
    rep #$30
.a16
    plx
    lda #1
    sta.l SourceQueueTx_Phase
    sep #$20
.a8
    lda #DMA_OPT_RESERVED
    sta.l DmaQueue+4,x
    rep #$30
.a16
    rtl
SourceQueueTx_ReserveFault:
.a16
.i16
    lda #5
    sta.l SourceQueueTx_Phase
SourceQueueTx_ReserveReturn:
.a16
.i16
    rtl

SourceQueueTx_SealGeometry:
.a16
.i16
    jsl SourcePacket_PrepareGeometry
    php
    rep #$30
    cld
    pha
    phx
    phy
    jsl SourceQueueTx_Seal
    ply
    plx
    pla
    plp
    rtl
SourceQueueTx_Seal:
.a16
.i16
    lda.l SourceQueueTx_Magic
    cmp #$5451
    bne SourceQueueTx_SealReturn
    lda.l SourceQueueTx_Phase
    cmp #1
    bne SourceQueueTx_SealReturn
    lda.l SourcePacket_MainRetryNeeded
    bne SourceQueueTx_SealAbort
    jsr SourceQueueTx_ReservedRow
    bcc SourceQueueTx_SealAbort
    lda.l SourceNextScene_Low
    cmp.l SourceQueueTx_SceneLow
    bne SourceQueueTx_SealAbort
    lda.l SourceNextScene_High
    cmp.l SourceQueueTx_SceneHigh
    bne SourceQueueTx_SealAbort
    lda.l SourceQueueTx_TicketLow
    sta.l SourceQueueTx_SealTicketLow
    lda.l SourceQueueTx_TicketHigh
    sta.l SourceQueueTx_SealTicketHigh
    lda.l SourceQueueTx_EpochLow
    sta.l SourceQueueTx_SealEpochLow
    lda.l SourceQueueTx_EpochHigh
    sta.l SourceQueueTx_SealEpochHigh
    lda #$CAFE
    sta.l SourceQueueTx_SealMagic
    lda #2
    sta.l SourceQueueTx_Phase
SourceQueueTx_SealReturn:
.a16
.i16
    rtl
SourceQueueTx_SealAbort:
.a16
.i16
    jsl SourceQueueTx_Cancel
    rtl

SourceQueueTx_ReservedRow:
.a16
.i16
    lda.l SourcePacket_CopyBusy
    cmp #1
    bne SourceQueueTx_RowNo
    lda.l SourceQueueTx_Row
    cmp #64
    bcs SourceQueueTx_RowNo
    and #7
    bne SourceQueueTx_RowNo
    lda.l SourceQueueTx_Row
    tax
    lda.l DmaQueue+4,x
    and #255
    cmp #DMA_OPT_RESERVED
    bne SourceQueueTx_RowNo
    jsr SourceQueueTx_RowFields
    rts
SourceQueueTx_RowFields:
.a16
.i16
    lda.l DmaQueue,x
    cmp #544
    bne SourceQueueTx_RowNo
    lda.l DmaQueue+2,x
    bne SourceQueueTx_RowNo
    lda.l DmaQueue+5,x
    cmp #$4F00
    bne SourceQueueTx_RowNo
    sep #$20
.a8
    lda.l DmaQueue+7,x
    cmp #$43
    rep #$30
.a16
    bne SourceQueueTx_RowNo
    phx
    txa
    lsr a
    lsr a
    lsr a
    tax
    sep #$20
.a8
    lda.l DmaQueue_Owner,x
    cmp #0
    rep #$30
.a16
    ; PLX changes NZ, so restore the comparison after the byte read.
    and #255
    plx
    cmp #0
    bne SourceQueueTx_RowNo
    sec
    rts
SourceQueueTx_RowNo:
.a16
.i16
    clc
    rts

SourceQueueTx_SealedIdentity:
.a16
.i16
    lda.l SourceQueueTx_SealMagic
    cmp #$CAFE
    bne SourceQueueTx_IdentityNo
    lda.l SourceQueueTx_TicketLow
    cmp.l SourceQueueTx_SealTicketLow
    bne SourceQueueTx_IdentityNo
    lda.l SourceQueueTx_TicketHigh
    cmp.l SourceQueueTx_SealTicketHigh
    bne SourceQueueTx_IdentityNo
    lda.l SourceQueueTx_EpochLow
    cmp.l SourceQueueTx_SealEpochLow
    bne SourceQueueTx_IdentityNo
    lda.l SourceQueueTx_EpochHigh
    cmp.l SourceQueueTx_SealEpochHigh
    bne SourceQueueTx_IdentityNo
    sec
    rts
SourceQueueTx_IdentityNo:
.a16
.i16
    clc
    rts

SourceQueueTx_Publish:
.a16
.i16
    lda.l SourceQueueTx_Magic
    cmp #$5451
    bne SourceQueueTx_PublishLegacy
    lda.l SourceQueueTx_Phase
    cmp #2
    beq SourceQueueTx_PublishOwned
    cmp #6
    beq SourceQueueTx_PublishNo
SourceQueueTx_PublishLegacy:
.a16
.i16
    jml Core_Dma_Enqueue_Long
SourceQueueTx_PublishOwned:
.a16
.i16
    php
    rep #$30
    cld
    phy
    jsr SourceQueueTx_ReservedRow
    bcc SourceQueueTx_PublishFail
    jsr SourceQueueTx_SealedIdentity
    bcc SourceQueueTx_PublishFail
    lda.l DmaRequest_TypeFlags
    and #255
    cmp #1
    bne SourceQueueTx_PublishFail
    lda.l DmaRequest_SourceBank
    and #255
    cmp #$43
    bne SourceQueueTx_PublishFail
    lda.l DmaRequest_SourceAddrLow
    cmp #$4F00
    bne SourceQueueTx_PublishFail
    lda.l DmaRequest_TargetAddr
    bne SourceQueueTx_PublishFail
    lda.l DmaRequest_Length
    cmp #544
    bne SourceQueueTx_PublishFail
    jsl SourceQueueBudget_ReservedFits
    bcc SourceQueueTx_PublishFail
    lda.l SourceQueueTx_Published
    inc a
    sta.l SourceQueueTx_Published
    ; All immutable identity/state must precede the Active byte. No record
    ; writes after publication: NMI may already have completed and ACKed it.
    lda #3
    sta.l SourceQueueTx_Phase
    lda #544
    jsl SourceQueueBudget_Publish
    ply
    plp
    sec
    rtl
SourceQueueTx_PublishFail:
.a16
.i16
    jsl SourceQueueTx_Cancel
    ply
    plp
SourceQueueTx_PublishNo:
.a16
.i16
    clc
    rtl

SourceQueueTx_Cancel:
.a16
.i16
    lda.l SourceQueueTx_Phase
    cmp #1
    beq SourceQueueTx_CancelRow
    cmp #2
    bne SourceQueueTx_CancelReturn
SourceQueueTx_CancelRow:
.a16
.i16
    jsr SourceQueueTx_ReservedRow
    bcc SourceQueueTx_CancelFault
    sep #$20
.a8
    lda #0
    sta.l DmaQueue+4,x
    rep #$30
.a16
    lda.l SourceQueueTx_Cancelled
    inc a
    sta.l SourceQueueTx_Cancelled
    lda #6
    sta.l SourceQueueTx_Phase
SourceQueueTx_CancelReturn:
.a16
.i16
    rtl
SourceQueueTx_CancelFault:
.a16
.i16
    lda #5
    sta.l SourceQueueTx_Phase
    rtl

SourceQueueTx_QueueResult:
.a16
.i16
    php
    rep #$30
    phx
    lda.l SourceQueueTx_Magic
    cmp #$5451
    bne SourceQueueTx_ResultClear
    lda.l SourceQueueTx_Phase
    cmp #3
    beq SourceQueueTx_ResultHold
    cmp #5
    beq SourceQueueTx_ResultHold
    cmp #4
    bne SourceQueueTx_ResultUnpublished
    jsr SourceQueueTx_Receipt
    bcc SourceQueueTx_ResultHold
    bra SourceQueueTx_ResultClear
SourceQueueTx_ResultUnpublished:
.a16
.i16
    cmp #1
    beq SourceQueueTx_ResultCancel
    cmp #2
    beq SourceQueueTx_ResultCancel
    cmp #6
    bne SourceQueueTx_ResultClear
SourceQueueTx_ResultReset:
.a16
.i16
    lda #0
    sta.l SourceQueueTx_Phase
    bra SourceQueueTx_ResultClear
SourceQueueTx_ResultCancel:
.a16
.i16
    jsl SourceQueueTx_Cancel
    lda.l SourceQueueTx_Phase
    cmp #5
    beq SourceQueueTx_ResultHold
    bra SourceQueueTx_ResultReset
SourceQueueTx_ResultClear:
.a16
.i16
    lda #0
    sta.l SourcePacket_CopyBusy
    bra SourceQueueTx_ResultReturn
SourceQueueTx_ResultHold:
.a16
.i16
    lda #1
    sta.l SourcePacket_CopyBusy
SourceQueueTx_ResultReturn:
.a16
.i16
    plx
    lda #0
    plp
    rtl

; Replaces the final8 bytes of the real OAM handler. Hardware write remains
; first; the receipt is impossible before the blocking DMA write returns.
SourceQueueTx_OamPhysical:
.a8
.i16
    lda #$80
    sta $420B
    rep #$31
.a16
.i16
    php
    pha
    lda.l SourceQueueTx_Phase
    cmp #3
    bne SourceQueueTx_PhysicalReturn
    lda.l SourceQueueTx_Magic
    cmp #$5451
    bne SourceQueueTx_PhysicalReturn
    txa
    cmp.l SourceQueueTx_Row
    bne SourceQueueTx_PhysicalReturn
    cmp #64
    bcs SourceQueueTx_PhysicalReturn
    and #7
    bne SourceQueueTx_PhysicalReturn
    lda.l DmaQueue+4,x
    and #255
    cmp #$41
    bne SourceQueueTx_PhysicalReturn
    jsr SourceQueueTx_RowFields
    bcc SourceQueueTx_PhysicalReturn
    jsr SourceQueueTx_SealedIdentity
    bcc SourceQueueTx_PhysicalReturn
    lda.l SourceQueueTx_SealTicketLow
    sta.l SourceQueueTx_AckTicketLow
    lda.l SourceQueueTx_SealTicketHigh
    sta.l SourceQueueTx_AckTicketHigh
    lda.l SourceQueueTx_SealEpochLow
    sta.l SourceQueueTx_AckEpochLow
    lda.l SourceQueueTx_SealEpochHigh
    sta.l SourceQueueTx_AckEpochHigh
    txa
    sta.l SourceQueueTx_AckRow
    lda.l SourceQueueTx_Acknowledged
    inc a
    sta.l SourceQueueTx_Acknowledged
    lda #4
    sta.l SourceQueueTx_Phase
    lda #0
    sta.l SourcePacket_CopyBusy
SourceQueueTx_PhysicalReturn:
.a16
.i16
    pla
    plp
    jml Core_Dma_SourceBlock_Return

SourceQueueTx_Receipt:
.a16
.i16
    jsr SourceQueueTx_SealedIdentity
    bcc SourceQueueTx_ReceiptNo
    lda.l SourceQueueTx_AckTicketLow
    cmp.l SourceQueueTx_SealTicketLow
    bne SourceQueueTx_ReceiptNo
    lda.l SourceQueueTx_AckTicketHigh
    cmp.l SourceQueueTx_SealTicketHigh
    bne SourceQueueTx_ReceiptNo
    lda.l SourceQueueTx_AckEpochLow
    cmp.l SourceQueueTx_SealEpochLow
    bne SourceQueueTx_ReceiptNo
    lda.l SourceQueueTx_AckEpochHigh
    cmp.l SourceQueueTx_SealEpochHigh
    bne SourceQueueTx_ReceiptNo
    lda.l SourceQueueTx_AckRow
    cmp.l SourceQueueTx_Row
    bne SourceQueueTx_ReceiptNo
    sec
    rts
SourceQueueTx_ReceiptNo:
.a16
.i16
    clc
    rts

SourceQueueTx_Observe:
.a16
.i16
    php
    rep #$30
    pha
    lda.l SourceQueueTx_Magic
    cmp #$5451
    bne SourceQueueTx_ObserveLegacy
    lda.l SourceQueueTx_Phase
    beq SourceQueueTx_ObserveLegacy
    cmp #6
    beq SourceQueueTx_ObserveLegacy
    cmp #4
    bne SourceQueueTx_ObserveHold
    jsr SourceQueueTx_Receipt
    bcc SourceQueueTx_ObserveHold
SourceQueueTx_ObserveLegacy:
.a16
.i16
    pla
    plp
    jml SourceVisual_CompletedObserve
SourceQueueTx_ObserveHold:
.a16
.i16
    pla
    plp
    rep #$31
    rtl
SourceQueueTx_End:
.assert * <= $27B000, "queue transaction exceeds verified ROM gap"
