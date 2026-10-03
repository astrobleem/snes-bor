; Opt-in source publisher entry-residency implementation.
; S7Pub_State is independently allocated outside OAM and actor contexts.
; Entry runs before the fixture's source-clock epoch. Queue active-bit clearing
; after ProcessQueue is the hardware-completion fence, not a host oracle.
S7Publisher_Reset:
    rep #$30
    .a16
    .i16
    lda #0
    ldx #254
S7Publisher_Reset__loop:
    .a16
    .i16
    sta.l S7Pub_State,x
    dex
    dex
    bpl S7Publisher_Reset__loop
    rtl

S7Publisher_Entry:
    rep #$30
    .a16
    .i16
    lda.l S7Pub_State+2
    beq S7Publisher_Entry__next
    lda.l S7Pub_State+4
    tax
    lda.l DmaQueue+4,x
    and #$0040
    beq S7Publisher_Entry__completed
    clc
    rtl
S7Publisher_Entry__completed:
    .a16
    .i16
    lda #0
    sta.l S7Pub_State+2
    lda.l S7Pub_State
    inc a
    sta.l S7Pub_State
S7Publisher_Entry__next:
    .a16
    .i16
    lda.l S7Pub_State
    cmp #S7Pub_TransferCount
    bcc S7Publisher_Entry__request
    lda #1
    sta.l S7Pub_State+6
S7Publisher_ResourcesReady:
    .a16
    .i16
    sec
    rtl
S7Publisher_Entry__request:
    .a16
    .i16
    asl a
    asl a
    asl a
    tax
    lda.l S7Pub_Transfers+4,x
    clc
    adc.l DmaQueue_BudgetTotal
    cmp #$08C0 ; retain at least544 bytes below the existing exclusive cap
    bcc S7Publisher_Entry__admitted
    clc
    rtl
S7Publisher_Entry__admitted:
    .a16
    .i16
    lda.l S7Pub_Transfers,x
    sta.l DmaRequest_SourceAddrLow
    lda.l S7Pub_Transfers+2,x
    sta.l DmaRequest_TargetAddr
    lda.l S7Pub_Transfers+4,x
    sta.l DmaRequest_Length
    sep #$20
    .a8
    lda.l S7Pub_Transfers+6,x
    sta.l DmaRequest_SourceBank
    lda.l S7Pub_Transfers+7,x
    sta.l DmaRequest_TypeFlags
    rep #$30
    .a16
    .i16
    jsl Core_Dma_Enqueue_Long
    bcc S7Publisher_Entry__retry
    txa
    sta.l S7Pub_State+4
    lda #1
    sta.l S7Pub_State+2
S7Publisher_Entry__retry:
    .a16
    .i16
    clc
    rtl

; D is the real production entity slot. No accepted fallback for an exact
; actor whose snapshot has no admitted source asset.
S7Publisher_RenderOrCompat:
    php
    rep #$30
    .a16
    .i16
    tdc
    sec
    sbc #$0A00
    tax
    lda.l S6Bridge_Policy,x
    and #255
    cmp #1
    beq S7Publisher_RenderOrCompat__source
    plp
    jml Character_RenderFrame
S7Publisher_RenderOrCompat__source:
    .a16
    .i16
    phx
    phy
    ; Resolve the production slot, not a source model-name branch.
    ldy #0
    txa
S7Publisher_RenderOrCompat__slot:
    .a16
    .i16
    cmp #0
    beq S7Publisher_RenderOrCompat__found
    sec
    sbc #CHAR_ZP_LEN
    iny
    bra S7Publisher_RenderOrCompat__slot
S7Publisher_RenderOrCompat__found:
    .a16
    .i16
    tya
    asl a
    asl a
    asl a
    asl a
    asl a
    tax
    txa
    sta.l S7Pub_State+12
    lda.l S7Pub_State+32+6,x
    beq S7Publisher_RenderOrCompat__done
    jsr S7Publisher_EmitPieces
S7Publisher_RenderOrCompat__done:
    .a16
    .i16
    ply
    plx
    plp
    rtl
