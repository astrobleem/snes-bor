; This helper replaces only the existing LDA State+6,X at the P1 normal
; compositor cold-lease deferral gate. That site has already selected and
; validated the actor, entry and lease. Return 2 solely to permit the existing
; loader visit for Kula's exact unarmed attack0; never publish or mark Ready.
; The ordinary loader still owns every admission and resource check.
SourceColdAttack_Mode:
.a16
.i16
    php
    lda.l SourceVisual_State+6,x
    pha
    cmp #1
    bne SourceColdAttack_Original
    lda.l SourceVisual_Key
    cmp #$0216
    bne SourceColdAttack_Original
    lda.l SourceVisual_Key+2
    bne SourceColdAttack_Original
    pla
    plp
    lda #2
    rtl
SourceColdAttack_Original:
.a16
.i16
    pla
    plp
    ora #0
    rtl
SourceColdAttack_End:
