; Original-BOR private immutable OAM image. This is an initial publication
; primitive, not a per-field geometry publisher. Its sole writer is the
; gated main compositor. DMA owns it until no active descriptor overlaps.
; $434F00..$43511F is beyond metadata ending $434DFF and below the compiled
; attack-choice tables at $435800. No MSU, PCM, tile or palette allocation.
SOURCE_PACKET_BUFFER = $434F00
SOURCE_PACKET_BYTES = 544

SourcePacket_IsQueueRow:
.a16
.i16
    txa
    cmp #64
    bcs SourcePacket_IsQueueRow__no
    and #7
    bne SourcePacket_IsQueueRow__no
    lda.l DmaQueue+4,x
    and #$00FF
    cmp #$0041
    bne SourcePacket_IsQueueRow__no
    lda.l DmaQueue+7,x
    and #$00FF
    cmp #$0043
    bne SourcePacket_IsQueueRow__no
    lda.l DmaQueue+5,x
    cmp #$4F00
    bne SourcePacket_IsQueueRow__no
    lda.l DmaQueue,x
    cmp #SOURCE_PACKET_BYTES
    bne SourcePacket_IsQueueRow__no
    lda.l DmaQueue+2,x
    bne SourcePacket_IsQueueRow__no
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
    bne SourcePacket_IsQueueRow__no
    sec
    rts
SourcePacket_IsQueueRow__no:
.a16
.i16
    clc
    rts

; Preserve the ordinary enqueue ABI and caller request cells. Call only from
; Core_Oam_Play after the hi-table transform; other callers never enter here.
SourcePacket_EnqueueMain:
.a16
.i16
    lda.l SourceVisual_CompletedMagic
    cmp #$C04D
    beq SourcePacket_EnqueueMain__guard0
    brl SourcePacket_EnqueueMain__fallback_near
SourcePacket_EnqueueMain__guard0:
.a16
.i16
    lda.l SVActor_Magic
    cmp #$AC19
    beq SourcePacket_EnqueueMain__guard1
    brl SourcePacket_EnqueueMain__fallback_near
SourcePacket_EnqueueMain__guard1:
.a16
.i16
    lda.l SourceInput_Magic
    cmp #$1A60
    beq SourcePacket_EnqueueMain__guard2
    brl SourcePacket_EnqueueMain__fallback_near
SourcePacket_EnqueueMain__guard2:
.a16
.i16
    lda.l Game_CampaignId
    and #$00FF
    cmp #3
    beq SourcePacket_EnqueueMain__guard3
    brl SourcePacket_EnqueueMain__fallback_near
SourcePacket_EnqueueMain__guard3:
.a16
.i16
    lda.l $7E1760
    cmp #1
    beq SourcePacket_EnqueueMain__guard4
    brl SourcePacket_EnqueueMain__fallback_near
SourcePacket_EnqueueMain__guard4:
.a16
.i16
    lda.l $7E46DC
    cmp #1
    beq SourcePacket_EnqueueMain__guard5
    brl SourcePacket_EnqueueMain__fallback_near
SourcePacket_EnqueueMain__guard5:
.a16
.i16
    lda.l Nmi_FrameBusy
    and #$00FF
    cmp #1
    beq SourcePacket_EnqueueMain__guard6
    brl SourcePacket_EnqueueMain__fallback_near
SourcePacket_EnqueueMain__guard6:
.a16
.i16
    lda.l SourceVisual_CompletedHeld
    and #$00FF
    cmp #1
    beq SourcePacket_EnqueueMain__guard7
    brl SourcePacket_EnqueueMain__fallback_near
SourcePacket_EnqueueMain__guard7:
.a16
.i16
    brl SourcePacket_EnqueueMain__request
SourcePacket_EnqueueMain__fallback_near:
.a16
.i16
    jml Core_Dma_Enqueue_Long
SourcePacket_EnqueueMain__request:
.a16
.i16
    lda.l DmaRequest_TypeFlags
    and #$00FF
    cmp #1
    beq SourcePacket_EnqueueMain__guard8
    brl SourcePacket_EnqueueMain__fallback_near
SourcePacket_EnqueueMain__guard8:
.a16
.i16
    lda.l DmaRequest_SourceBank
    and #$00FF
    cmp #$7E
    beq SourcePacket_EnqueueMain__guard9
    brl SourcePacket_EnqueueMain__fallback_near
SourcePacket_EnqueueMain__guard9:
.a16
.i16
    lda.l DmaRequest_SourceAddrLow
    cmp #$5100
    beq SourcePacket_EnqueueMain__guard10
    brl SourcePacket_EnqueueMain__fallback_near
SourcePacket_EnqueueMain__guard10:
.a16
.i16
    lda.l DmaRequest_TargetAddr
    beq SourcePacket_EnqueueMain__guard11
    brl SourcePacket_EnqueueMain__fallback_near
SourcePacket_EnqueueMain__guard11:
.a16
.i16
    lda.l DmaRequest_Length
    bne SourcePacket_EnqueueMain__guard12
    brl SourcePacket_EnqueueMain__fallback_near
SourcePacket_EnqueueMain__guard12:
.a16
.i16
    cmp #513
    bcc SourcePacket_EnqueueMain__guard13
    brl SourcePacket_EnqueueMain__fallback_near
SourcePacket_EnqueueMain__guard13:
.a16
.i16
    lda.l DmaQueue_BudgetTotal
    clc
    adc #(SOURCE_PACKET_BYTES+32) ; includes worst-case legacy hi-table row
    bcc SourcePacket_EnqueueMain__guard14
    brl SourcePacket_EnqueueMain__fallback_near
SourcePacket_EnqueueMain__guard14:
.a16
.i16
    cmp #DMA_TRANSFER_MAX_BYTES
    bcc SourcePacket_EnqueueMain__guard15
    brl SourcePacket_EnqueueMain__fallback_near
SourcePacket_EnqueueMain__guard15:
.a16
.i16
    ; Refuse any active descriptor that could read or write these bytes,
    ; including malformed flags and noncanonical subranges.
    phx
    ldx #0
SourcePacket_EnqueueMain__scan:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$0040
    beq SourcePacket_EnqueueMain__next
    lda.l DmaQueue+7,x
    and #$00FF
    cmp #$43
    bne SourcePacket_EnqueueMain__next
    lda.l DmaQueue,x
    bne SourcePacket_EnqueueMain__pending_guard0
    brl SourcePacket_EnqueueMain__busy
SourcePacket_EnqueueMain__pending_guard0:
.a16
.i16
    lda.l DmaQueue+5,x
    clc
    adc.l DmaQueue,x
    bcs SourcePacket_EnqueueMain__wrapped
    cmp #$4F01
    bcc SourcePacket_EnqueueMain__next
    lda.l DmaQueue+5,x
    cmp #$5120
    bcs SourcePacket_EnqueueMain__next
    brl SourcePacket_EnqueueMain__busy
SourcePacket_EnqueueMain__wrapped:
.a16
.i16
    cmp #$4F01
    bcc SourcePacket_EnqueueMain__pending_guard1
    brl SourcePacket_EnqueueMain__busy
SourcePacket_EnqueueMain__pending_guard1:
.a16
.i16
    lda.l DmaQueue+5,x
    cmp #$5120
    bcs SourcePacket_EnqueueMain__pending_guard2
    brl SourcePacket_EnqueueMain__busy
SourcePacket_EnqueueMain__pending_guard2:
.a16
.i16
SourcePacket_EnqueueMain__next:
.a16
.i16
    txa
    clc
    adc #8
    tax
    cpx #64
    bcc SourcePacket_EnqueueMain__scan
    plx
    ; The existing compositor gate excludes NMI clearing its source mid-copy.
    ; Keep the caller's DBR/Y and exact request length; MVN changes DBR.
    phb
    phy
    lda.l DmaRequest_Length
    pha
    ldx #$5100
    ldy #$4F00
    lda #SOURCE_PACKET_BYTES-1
    mvn $43,$7E
    lda #SOURCE_PACKET_BYTES
    sta.l DmaRequest_Length
    lda #$4F00
    sta.l DmaRequest_SourceAddrLow
    sep #$20
.a8
    lda #$43
    sta.l DmaRequest_SourceBank
    rep #$30
.a16
.i16
    ; The ordinary DMA routine uses bank-zero WRAM mirrors. MVN changed DBR.
    sep #$20
.a8
    lda #0
    pha
    plb
    rep #$30
.a16
.i16
    jsl Core_Dma_Enqueue_Long
    php
    rep #$30
    ; Carry is restored after request restoration; X remains enqueue's result.
    lda #$5100
    sta.l DmaRequest_SourceAddrLow
    sep #$20
.a8
    lda #$7E
    sta.l DmaRequest_SourceBank
    rep #$30
.a16
.i16
    plp
    ; Pop the length without changing the enqueue carry.
    pla
    sta.l DmaRequest_Length
    ply
    plb
    rtl
SourcePacket_EnqueueMain__busy:
.a16
.i16
    ; Never enqueue a newer mutable frame ahead of the still-owned image.
    ; The completed-pose pending gate keeps its resources held for retry.
    plx
    clc
    rtl
