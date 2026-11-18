
; Temporary timing diagnostic: leave every acquired image unpublished.
SourceNextFrame_Profile:
.a16
.i16
    lda #1
    sta.l SourceVisual_State+4,x
    php
    rep #$30
    pha
    phx
    phy
    jsl SourceNextFrame_Prepare
SourceNextFrame_ProfilePrepared:
.a16
.i16
    bcc SourceNextFrame_ProfileDone
    lda.l SourceVisual_ActorSlot
    jsl SourceNextWitness_Ready
SourceNextFrame_ProfileReadiness:
.a16
.i16
    lda.l SourceVisual_ActorSlot
    jsl SourceNextFrame_CancelUnpublished
SourceNextFrame_ProfileDone:
.a16
.i16
    ply
    plx
    pla
    plp
    rtl
SourceNextFrame_ProfileEnd:
