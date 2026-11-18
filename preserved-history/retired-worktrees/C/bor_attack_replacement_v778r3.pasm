
; Request-scoped replacement check. Original hot same-generation hold path
; and its instructions remain byte-identical. No work on ordinary frames.
.bank 39
.org $A400
SourceAttackReplacement_Proceed:
.a16
.i16
    php
    rep #$30
    pha
    lda.l SourceAttackOwned_Hold
    cmp #1
    bne SourceAttackReplacement_Allow
    lda.l SourceAttackOwned_Suppressed
    bne SourceAttackReplacement_Allow
    lda.l SourceAttackOwned_State
    cmp #2
    bne SourceAttackReplacement_Allow
    lda.l SourceNextScene_Low
    cmp.l SourceAttackOwned_PhysicalLow
    bne SourceAttackReplacement_CheckCross
    lda.l SourceNextScene_High
    cmp.l SourceAttackOwned_PhysicalHigh
    beq SourceAttackReplacement_Allow
SourceAttackReplacement_CheckCross:
    jsl SourceAttackReplacement_Generation
    bcc SourceAttackReplacement_Allow
    jsl SourceAttackMask_PhysicalLive
    bcc SourceAttackReplacement_Allow
    pla
    plp
    jml SourceAttackOwned_PublishEnd
SourceAttackReplacement_Allow:
    pla
    plp
    jsl SourceAttackOwned_Publish
    jsl SourceOwnedRefresh_NmiTransfer
    jml SourceAttackReplacement_PostTransfer
SourceAttackReplacement_ProceedEnd:
.assert * <= $27A800, "scoped replacement check exceeds blank ROM"
