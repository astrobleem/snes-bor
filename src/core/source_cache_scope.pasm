; A short-lived scope certificate for one foreground tile release only.
; Begin clears before validating; End clears before the original caller resumes.
; Immutable cache eligibility/ID/state/owners/progress/kind/tag are still
; checked for EVERY row. NMI cannot reuse this certificate. No Ready writes.
SourceCache_ReleaseScope = $7E46EE
SourceCache_ReleaseBegin:
.a16
.i16
    php
    rep #$30
    cld
    pha
    phx
    phy
    lda #0
    sta.l SourceCache_ReleaseScope
    jsr SourceIdle_KeepScope
    bcc SourceCache_ReleaseBegin__done
    lda #$B17C
    sta.l SourceCache_ReleaseScope
SourceCache_ReleaseBegin__done:
.a16
.i16
    ply
    plx
    pla
    plp
    rtl
SourceCache_ReleaseEnd:
.a16
.i16
    php
    rep #$20
    pha
    lda #0
    sta.l SourceCache_ReleaseScope
    pla
    plp
    rtl
SourceCache_ReleaseScopeEnd:
.a16
.i16
