; Foreground post-reconciliation boundary, before P2 context entry.
; Preserve every input to the original activity test and tail-enter it.
; Only the physical P2 boundary may service the existing paired idle handoff.
SourceIdleReconcile_BeforeActive:
.a16
.i16
    php
    rep #$30
    pha
    tdc
    cmp #$0A85
    bne SourceIdleReconcile_Done
    lda.l $7E46DE
    bne SourceIdleReconcile_Done
    jsl SourceIdleVisit_Check
SourceIdleReconcile_Done:
.a16
.i16
    pla
    plp
    jml StageBounds_IsActive
SourceIdleReconcile_End:
