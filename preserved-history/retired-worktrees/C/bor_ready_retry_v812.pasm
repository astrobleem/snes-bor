; Tail entry preserves the enclosing SourceReady_Capture save frame.
; BA6 owns throttle state:0 first,1 attempted,3 retried,bit15 pending seal.
; Pending stores producer sequence low14bits. Aliasing at wrap delays retry
; conservatively until the next field. No new memory or producer writes.
SourceReady_BoundedBegin:
.a16
.i16
    lda.l StageTimer_FieldCounter
    cmp.l $437B9C
    bne SourceReady_BoundedNew
    lda.l $437BA6
    beq SourceReady_BoundedFirst
    bit #$8000
    bne SourceReady_BoundedPending
    jml SourceReady_Done
SourceReady_BoundedPending:
.a16
.i16
    lda.l $434E7C
    bit #1
    bne SourceReady_BoundedDone
    and #$3FFE
    ora #$8000
    cmp.l $437BA6
    beq SourceReady_BoundedDone
    lda #3
    bra SourceReady_BoundedMark
SourceReady_BoundedNew:
.a16
.i16
    sta.l $437B9C
SourceReady_BoundedFirst:
.a16
.i16
    lda #1
SourceReady_BoundedMark:
.a16
.i16
    sta.l $437BA6
    lda.l $437BA8
    inc a
    sta.l $437BA8
    jml SourceReady_ProjectionStart
SourceReady_BoundedDone:
.a16
.i16
    jml SourceReady_Done
SourceReady_BoundedGateEnd:
.assert SourceReady_BoundedGateEnd <= $27B000, "bounded ready gate exceeds helper gap"
.org $A600
SourceReady_BoundedSeal:
.a16
.i16
    lda.l $437B3C
    cmp #$A55E
    beq SourceReady_BoundedReturn
    lda.l $437BA6
    cmp #1
    bne SourceReady_BoundedReload
    lda.l $434E7C
    and #$3FFE
    ora #$8000
    sta.l $437BA6
SourceReady_BoundedReload:
.a16
.i16
    lda.l $437B3C
SourceReady_BoundedReturn:
.a16
.i16
    rtl
SourceReady_BoundedEnd:
.assert SourceReady_BoundedEnd <= $27A700, "bounded ready finalizer exceeds helper gap"
