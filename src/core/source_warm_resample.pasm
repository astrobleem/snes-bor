; Bounded resample only for an in-flight independently published SA1 motion
; header. Coherent fast path is byte/instruction identical. No fields waited,
; no acceptance, key, queue, ownership or publication rule is bypassed.
SourceWarmRetry_Header:
.a16
.i16
    lda.l $434E7C
    bne SourceWarmRetry_Header_bounded
    jmp SourceWarm_ReadAttack__pop_miss
SourceWarmRetry_Header_bounded:
.a16
.i16
    ldx #128
SourceWarmRetry_Header_poll:
.a16
.i16
    lda.l $434E7E
    cmp #$4D50
    beq SourceWarmRetry_Header_sequence
    cmp #0
    beq SourceWarmRetry_Header_next
    jmp SourceWarm_ReadAttack__pop_miss
SourceWarmRetry_Header_sequence:
.a16
.i16
    lda.l $434E7C
    and #1
    beq SourceWarmRetry_Header_ready
SourceWarmRetry_Header_next:
.a16
.i16
    dex
    bne SourceWarmRetry_Header_poll
    jmp SourceWarm_ReadAttack__pop_miss
SourceWarmRetry_Header_ready:
.a16
.i16
    jmp SourceWarm_ReadAttack__even
SourceWarmRetry_CapturedSlot:
.a16
.i16
    lda.l $434E7C
    bne SourceWarmRetry_CapturedSlot_bounded
    jmp SourceWarm_ReadAttack__miss
SourceWarmRetry_CapturedSlot_bounded:
.a16
.i16
    ldx #128
SourceWarmRetry_CapturedSlot_poll:
.a16
.i16
    lda.l $434E7E
    cmp #$4D50
    beq SourceWarmRetry_CapturedSlot_sequence
    cmp #0
    beq SourceWarmRetry_CapturedSlot_next
    jmp SourceWarm_ReadAttack__miss
SourceWarmRetry_CapturedSlot_sequence:
.a16
.i16
    lda.l $434E7C
    sta.l SourceWarm_Seq
    and #1
    beq SourceWarmRetry_CapturedSlot_ready
SourceWarmRetry_CapturedSlot_next:
.a16
.i16
    dex
    bne SourceWarmRetry_CapturedSlot_poll
    jmp SourceWarm_ReadAttack__miss
SourceWarmRetry_CapturedSlot_ready:
.a16
.i16
    jmp SourceWarm_ReadAttack__seq
SourceWarmRetry_End:
