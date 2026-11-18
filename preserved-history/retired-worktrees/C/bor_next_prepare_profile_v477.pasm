
; Temporary foreground measurement only. Never publish this private image.
SourceNextPrepare_Profile:
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
    bcc SourceNextPrepare_ProfileDone
    lda.l Oam_CurrentSlot
    sta.l SourceNextEmit_Cursor
    jsl SourceNextEmit_Build
SourceNextPrepare_Composed:
.a16
.i16
    rep #$30
    lda.l SourceVisual_ActorSlot
    jsl SourceNextPins_ReleaseUnpublished
SourceNextPrepare_ProfileDone:
.a16
.i16
    ply
    plx
    pla
    plp
    rtl
SourceNextPrepare_ProfileEnd:
