; One immutable full OAM transaction in the audited gap before tile staging.
; Main owns $7E5100 staging; hardware DMA owns $7F8D00..8F1F until completion.
S7Packet_Init:
    rep #$30
    .a16
    .i16
    lda #0
    sta.l $7F8F20
    ldx #0
S7Packet_Init__copy:
    .a16
    .i16
    lda.l Oam_Buffer,x
    sta.l $7F8D00,x
    inx
    inx
    cpx #544
    bcc S7Packet_Init__copy
    rtl
S7Packet_Begin:
    rep #$30
    .a16
    .i16
    lda.l S7Pub_State+6
    cmp #1
    bne S7Packet_Begin__done
    jsr S7Packet_ClearActive
S7Packet_Begin__done:
    .a16
    .i16
    rtl
S7Packet_Submit:
    rep #$30
    .a16
    .i16
    lda.l S7Pub_State+6
    cmp #1
    beq S7Packet_Submit__source
    jml Core_Oam_Play_Long
S7Packet_Submit__source:
    .a16
    .i16
    lda.l $7F8F20
    beq S7Packet_Submit__free
    lda.l $7F8F22
    tax
    lda.l DmaQueue+4,x
    and #$40
    beq S7Packet_Submit__free
    jmp S7Packet_Submit__fault
S7Packet_Submit__free:
    .a16
    .i16
    lda.l Oam_CurrentSlot
    cmp.l Oam_HighWaterSlot
    bcc S7Packet_Submit__extent
    sta.l Oam_HighWaterSlot
S7Packet_Submit__extent:
    .a16
    .i16
    jsr S7Packet_TransformHiOam
    rep #$30
    .a16
    .i16
    ldx #0
S7Packet_Submit__copy:
    .a16
    .i16
    lda.l Oam_Buffer,x
    sta.l $7F8D00,x
    inx
    inx
    txa
    cmp.l Oam_HighWaterSlot
    bcc S7Packet_Submit__copy
    ldx #0
S7Packet_Submit__hi:
    .a16
    .i16
    lda.l Oam_PackedHi,x
    sta.l $7F8F00,x
    inx
    inx
    cpx #32
    bcc S7Packet_Submit__hi
    lda #544
    sta.l DmaRequest_Length
    ; Identity travels with the immutable packet, not the subsequently mutable
    ; snapshot. Neither word changes until this packet's DMA has completed.
    lda.l S7Pub_State+$E0
    sta.l $7F8F34
    lda.l $7F8F36
    inc a
    sta.l $7F8F36
    lda.l $7F8F28
    sta.l $7F8F26
    lda #$8D00
    sta.l DmaRequest_SourceAddrLow
    lda #0
    sta.l DmaRequest_TargetAddr
    sep #$20
    .a8
    lda #$7F
    sta.l DmaRequest_SourceBank
    lda #1
    sta.l DmaRequest_TypeFlags
    rep #$30
    .a16
    .i16
    jsl Core_Dma_Enqueue_Long
    bcc S7Packet_Submit__fault
    txa
    sta.l $7F8F22
    lda #1
    sta.l $7F8F20
    sec
    rtl
S7Packet_Submit__fault:
    .a16
    .i16
    lda #$D704
    sta.l S7Pub_State+$FE
    clc
    rtl
S7Packet_Poll:
    rep #$30
    .a16
    .i16
    lda.l $7F8F20
    beq S7Packet_Poll__done
    lda.l $7F8F22
    tax
    lda.l DmaQueue+4,x
    and #$40
    beq S7Packet_Poll__complete
    ; The main-thread FIFO may have reused the completed slot before polling.
    ; An unrelated live request does not re-own this unique packet buffer.
    lda.l DmaQueue+5,x
    cmp #$8D00
    bne S7Packet_Poll__complete
    lda.l DmaQueue+7,x
    and #255
    cmp #$7F
    beq S7Packet_Poll__done
S7Packet_Poll__complete:
    .a16
    .i16
    lda.l $7F8F26
    sta.l $7F8F24
    lda #0
    sta.l $7F8F20
S7Packet_Poll__done:
    .a16
    .i16
    rtl
