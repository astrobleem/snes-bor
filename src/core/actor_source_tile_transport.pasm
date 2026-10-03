; Bounded two4KiB-frame transport. Generated admission requires <=16 SMALL
; pieces/frame. Entry owns both buffers before the source epoch. During play,
; Retiring-buffer uploads are queued AFTER the new OAM at the actual game
; service tail. A required final half is queued BEFORE its dependent OAM.
; Neither operation depends on Nmi_FrameBusy (production does not set it).
S7Tile_Init:
    rep #$30
    .a16
    .i16
    lda #1
    sta.l S7Pub_State+$E2
    lda #$FFFF
    sta.l S7Pub_State+$E4
    rtl

S7Tile_Service:
    rep #$30
    .a16
    .i16
    lda.l Oam_UploadFlag
    bne S7Tile_Service__poll
    lda.l Nmi_FrameCounter
    cmp.l S7Pub_State+$F6
    beq S7Tile_Service__poll
    lda.l S7Pub_State+$F8
    sta.l S7Pub_State+$FA
S7Tile_Service__poll:
    .a16
    .i16
    lda.l S7Pub_State+$EA
    beq S7Tile_Service__select
    lda.l S7Pub_State+$E8
    tax
    lda.l DmaQueue+4,x
    and #$40
    beq S7Tile_Service__completed
    jmp S7Tile_Service__select
S7Tile_Service__completed:
    .a16
    .i16
    lda #0
    sta.l S7Pub_State+$EA
    lda.l S7Pub_State+$E6
    inc a
    sta.l S7Pub_State+$E6
    cmp #2
    bne S7Tile_Service__select
    lda.l S7Pub_State+$E4
    and #1
    asl a
    tax
    lda.l S7Pub_State+$E4
    sta.l S7Pub_State+$E0,x
    lda #$FFFF
    sta.l S7Pub_State+$E4
S7Tile_Service__select:
    .a16
    .i16
    lda #0
    sta.l S7Pub_State+$FC
    ldx #0
S7Tile_Service__find:
    .a16
    .i16
    lda.l S7Pub_State+38,x
    bne S7Tile_Service__found
    txa
    clc
    adc #32
    tax
    cpx #192
    bcc S7Tile_Service__find
    rtl
S7Tile_Service__found:
    .a16
    .i16
    lda.l S7Pub_State+42,x
    sta.l S7Pub_State+$EE
    ; This bounded linked transport admits a shared-frame cohort. Independent
    ; animation timelines need separate leases, not silent parity aliasing.
    ldx #0
S7Tile_Service__cohort:
    .a16
    .i16
    lda.l S7Pub_State+38,x
    beq S7Tile_Service__cohort_next
    lda.l S7Pub_State+42,x
    cmp.l S7Pub_State+$EE
    beq S7Tile_Service__cohort_next
    lda #$D702
    sta.l S7Pub_State+$FE
    jmp S7Tile_Service__miss
S7Tile_Service__cohort_next:
    .a16
    .i16
    txa
    clc
    adc #32
    tax
    cpx #192
    bcc S7Tile_Service__cohort
    lda.l S7Pub_State+$EE
    and #1
    asl a
    tax
    lda.l S7Pub_State+$E0,x
    cmp.l S7Pub_State+$EE
    beq S7Tile_Service__resident
    ; Only a final half already staged or queued may precede new OAM in
    ; this field's ordered transaction. Other misses fail visibly, not hold.
    lda.l S7Pub_State+$E4
    cmp.l S7Pub_State+$EE
    bne S7Tile_Service__miss
    lda.l S7Pub_State+$E6
    cmp #1
    bne S7Tile_Service__miss
    lda #1
    sta.l S7Pub_State+$FC ; tail must queue completion BEFORE current OAM
    rtl
S7Tile_Service__miss:
    .a16
    .i16
    lda.l S7Pub_State+$FE
    bne S7Tile_Service__count_miss
    lda #$D703
    sta.l S7Pub_State+$FE
S7Tile_Service__count_miss:
    .a16
    .i16
    lda.l S7Pub_State+$F0
    inc a
    sta.l S7Pub_State+$F0
    ldx #0
    lda #0
S7Tile_Service__hide:
    .a16
    .i16
    sta.l S7Pub_State+38,x
    pha
    txa
    clc
    adc #32
    tax
    pla
    cpx #192
    bcc S7Tile_Service__hide
    rtl
S7Tile_Service__resident:
    .a16
    .i16
    lda.l S7Pub_State+$EE
    inc a
    cmp #6
    bcs S7Tile_Service__done
    sta.l S7Pub_State+$F2
    and #1
    asl a
    tax
    lda.l S7Pub_State+$E0,x
    cmp.l S7Pub_State+$F2
    beq S7Tile_Service__done
    lda.l S7Pub_State+$E4
    cmp #$FFFF
    bne S7Tile_Service__continue
    lda.l S7Pub_State+$F2
    sta.l S7Pub_State+$E4
    lda #0
    sta.l S7Pub_State+$E6
S7Tile_Service__continue:
    .a16
    .i16
    lda #2
    sta.l S7Pub_State+$FC ; tail queues prefetch AFTER current OAM
S7Tile_Service__done:
    .a16
    .i16
    rtl

S7Tile_QueueHalf:
    rep #$30
    .a16
    .i16
    lda.l S7Pub_State+$EA
    bne S7Tile_QueueHalf__no
    lda.l DmaQueue_BudgetTotal
    clc
    adc #2048
    cmp #$08C0
    bcs S7Tile_QueueHalf__no
    lda.l S7Pub_State+$E6
    xba
    asl a
    asl a
    asl a
    sta.l S7Pub_State+$F4
    lda.l S7Pub_State+$E4
    xba
    asl a
    asl a
    asl a
    asl a
    clc
    adc #$8000
    adc.l S7Pub_State+$F4
    sta.l DmaRequest_SourceAddrLow
    lda.l S7Pub_State+$E4
    and #1
    xba
    asl a
    asl a
    asl a
    asl a
    clc
    adc #$8000
    adc.l S7Pub_State+$F4
    sta.l DmaRequest_TargetAddr
    lda #2048
    sta.l DmaRequest_Length
    sep #$20
    .a8
    lda #33
    sta.l DmaRequest_SourceBank
    lda #0
    sta.l DmaRequest_TypeFlags
    rep #$30
    .a16
    .i16
    jsl Core_Dma_Enqueue_Long
    bcc S7Tile_QueueHalf__no
    txa
    sta.l S7Pub_State+$E8
    lda #1
    sta.l S7Pub_State+$EA
    sec
    rtl
S7Tile_QueueHalf__no:
    .a16
    .i16
    clc
    rtl

S7Tile_OamTail:
    php
    rep #$30
    .a16
    .i16
    lda.l S7Pub_State+6
    cmp #1
    bne S7Tile_OamTail__ordinary
    lda.l S7Pub_State+$FC
    cmp #1
    bne S7Tile_OamTail__ordinary
    ; Service has proved staging==current and exactly one completed half.
    ; If the final half is already queued, it precedes this OAM submission;
    ; it may also have completed during catch-up before the next poll. Neither
    ; case requires a duplicate enqueue or a false admission fault.
    lda.l S7Pub_State+$EA
    bne S7Tile_OamTail__ordinary
    jsl S7Tile_QueueHalf
    bcs S7Tile_OamTail__ordinary
    ; Missing admission is an explicit diagnostic fault, never wrong tiles.
    lda #$D701
    sta.l S7Pub_State+$FE
    plp
    rtl
S7Tile_OamTail__ordinary:
    .a16
    .i16
    jsl Core_Oam_Play_Long
    lda.l S7Pub_State+6
    cmp #1
    bne S7Tile_OamTail__done
    lda.l S7Pub_State+$FC
    cmp #2
    bne S7Tile_OamTail__done
    ; Both existing OAM transfers must be ahead of this upload in the queue.
    lda.l Oam_UploadFlag
    beq S7Tile_OamTail__done
    jsl S7Tile_QueueHalf
S7Tile_OamTail__done:
    .a16
    .i16
    plp
    rtl
