; Once per foreground gameplay boundary, after original physics and before
; actor processing. Original physics outputs and all caller state stay intact.
; Existing exact paired-idle transaction supplies every ownership/freshness fence.
SourceIdlePhysics_Boundary:
.a16
.i16
    jsl StageBoundsHost_Physics
    php
    rep #$30
    pha
    lda.l $7E46DE
    bne SourceIdlePhysics_Done
    jsl SourceIdleVisit_Check
SourceIdlePhysics_Done:
.a16
.i16
    pla
    plp
    rtl
SourceIdlePhysics_End:
