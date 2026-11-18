; Dormant prerequisite for reserve/seal/publish. Not an ownership grant.
; The single foreground producer already owns an inactive reserved row X,
; whose length equals A16. It must keep that row and image immutable until
; publication/cancellation. NMI ONLY drains; it never creates descriptors.
; Count actual active bytes as well as the legacy counter: the latter can
; undercount after its charge-before-Active race. Interrupted scans remain
; conservative because NMI can only remove rows. No persistent scratch.
; Return CF=1 iff max(active sum,counter)+length < established $0B00 cap.
; Preserve A/X/Y/D/DB/P except CF. No queue, resource, image or ACK writes.
.bank 39
.org $A100
SourceQueueBudget_ReservedFits:
.a16
.i16
    php
    rep #$31
    cld
    pha
    phx
    phy
    txa
    cmp #64
    bcc SourceQueueBudget_Range
    brl SourceQueueBudget_No
SourceQueueBudget_Range:
.a16
.i16
    and #7
    beq SourceQueueBudget_Aligned
    brl SourceQueueBudget_No
SourceQueueBudget_Aligned:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$00FF
    cmp #DMA_OPT_RESERVED
    beq SourceQueueBudget_Reserved
    brl SourceQueueBudget_No
SourceQueueBudget_Reserved:
.a16
.i16
    lda 5,s
    bne SourceQueueBudget_Nonzero
    brl SourceQueueBudget_No
SourceQueueBudget_Nonzero:
.a16
.i16
    cmp #DMA_TRANSFER_MAX_BYTES
    bcc SourceQueueBudget_Bounded
    brl SourceQueueBudget_No
SourceQueueBudget_Bounded:
.a16
.i16
    cmp.l DmaQueue,x
    beq SourceQueueBudget_LengthMatches
    brl SourceQueueBudget_No
SourceQueueBudget_LengthMatches:
.a16
.i16
    pha
    ldx #0
    ldy #0
SourceQueueBudget_SumLoop:
.a16
.i16
    lda.l DmaQueue+4,x
    and #DMA_OPT_ACTIVE
    beq SourceQueueBudget_SumNext
    lda.l DmaQueue,x
    beq SourceQueueBudget_NoExtra
    tya
    clc
    adc.l DmaQueue,x
    bcs SourceQueueBudget_NoExtra
    cmp #DMA_TRANSFER_MAX_BYTES
    bcs SourceQueueBudget_NoExtra
    tay
SourceQueueBudget_SumNext:
.a16
.i16
    txa
    clc
    adc #8
    tax
    cpx #64
    bcc SourceQueueBudget_SumLoop
    tya
    cmp.l DmaQueue_BudgetTotal
    bcs SourceQueueBudget_HaveMaximum
    lda.l DmaQueue_BudgetTotal
SourceQueueBudget_HaveMaximum:
.a16
.i16
    clc
    adc 1,s
    bcs SourceQueueBudget_NoExtra
    cmp #DMA_TRANSFER_MAX_BYTES
    bcs SourceQueueBudget_NoExtra
    pla
    ply
    plx
    pla
    plp
    sec
    rtl
SourceQueueBudget_NoExtra:
.a16
.i16
    pla
SourceQueueBudget_No:
.a16
.i16
    ply
    plx
    pla
    plp
    clc
    rtl
SourceQueueBudget_ReservedFitsEnd:
.assert * <= $27A300, "reserved budget predicate exceeds blank ROM"
