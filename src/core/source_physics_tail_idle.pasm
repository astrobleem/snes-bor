; Reuse the original physics saved frame: no extra nested physics call or
; register-save transaction. Width was just restored by original REP #$30.
SourceIdlePhysicsTail_Return:
.a16
.i16
    plb
    pld
    lda.l $7E46DE
    bne SourceIdlePhysicsTail_Pop
    lda.l SourceReserve_Valid
    cmp #$1D1F
    bne SourceIdlePhysicsTail_Pop
    jsl SourceIdleVisit_Check
SourceIdlePhysicsTail_Pop:
.a16
.i16
    ply
    plx
    pla
    plp
    rtl
SourceIdlePhysicsTail_End:
