; Private Core_Oam_Play continuation only. X is the SUCCESSFUL main enqueue
; result from this same call; no foreground producer runs before hi enqueue.
; NMI may clear Active/owner but leaves the descriptor body and restores X.
; A canonical full544 main already includes all32 packed-high bytes. A later
; legacy upload from mutable7E:5300 can corrupt its signed-X/size bits.
; Suppress only that duplicate. No ACK, pin, queue, budget or request write.
.bank 39
.org $A300
SourceFullOam_EnqueueHigh:
.a8
.i16
    rep #$31
.a16
.i16
    php
    pha
    phx
    phy
    txa
    cmp #64
    bcs SourceFullOam_Legacy
    and #7
    bne SourceFullOam_Legacy
    lda.l DmaQueue,x
    cmp #544
    bne SourceFullOam_Legacy
    lda.l DmaQueue+2,x
    bne SourceFullOam_Legacy
    lda.l DmaQueue+5,x
    cmp #$4F00
    bne SourceFullOam_Legacy
    sep #$20
.a8
    lda.l DmaQueue+7,x
    cmp #$43
    rep #$30
.a16
    bne SourceFullOam_Legacy
    lda.l DmaQueue+4,x
    and #255
    beq SourceFullOam_MainBody
    cmp #$41
    bne SourceFullOam_Legacy
SourceFullOam_MainBody:
.a16
.i16
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
    bne SourceFullOam_Legacy
    lda.l DmaRequest_TypeFlags
    and #255
    cmp #1
    bne SourceFullOam_Legacy
    lda.l DmaRequest_SourceAddrLow
    cmp #$5300
    bne SourceFullOam_Legacy
    sep #$20
.a8
    lda.l DmaRequest_SourceBank
    cmp #$7E
    rep #$30
.a16
    bne SourceFullOam_Legacy
    lda.l DmaRequest_TargetAddr
    cmp #$0100
    bne SourceFullOam_Legacy
    lda.l DmaRequest_Length
    beq SourceFullOam_Legacy
    cmp #33
    bcs SourceFullOam_Legacy
    ply
    plx
    pla
    plp
    sec
    rtl
SourceFullOam_Legacy:
.a16
.i16
    ply
    plx
    pla
    plp
    jml Core_Dma_Enqueue_Long
SourceFullOam_End:
.assert * <= $27A600, "full OAM hi continuation exceeds blank ROM"
