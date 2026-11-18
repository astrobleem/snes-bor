
; TEMPORARY COST DIAGNOSTIC. Reproduce the original queued-flag store,
; reserve and immediately release unpublished next pins, then return with
; identical caller registers/status and all nonstack memory unchanged.
SourceNextPins_Profile:
.a16
.i16
    lda #1
    sta.l SourceVisual_State+4,x
    php
    rep #$30
    pha
    phx
    phy
    jsl SourceNextPins_Acquire
    bcc SourceNextPins_ProfileDone
    lda.l SourceVisual_ActorSlot
    jsl SourceNextPins_ReleaseUnpublished
SourceNextPins_ProfileDone:
.a16
.i16
    ply
    plx
    pla
    plp
    rtl
SourceNextPins_ProfileEnd:
