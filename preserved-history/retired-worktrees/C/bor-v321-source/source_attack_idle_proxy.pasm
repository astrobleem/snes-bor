SourceIdleFitProxy:
.a16
.i16
    php
    rep #$30
    pha
    lda.l SourceVisual_Key+1
    and #$00FF
    bne SourceIdleFitProxy_NonIdle
    lda.l SourceVisual_Key+2
    and #$00FF
    beq SourceIdleFitProxy__done
    phx
    phy
    jsr SourceIdle_Eligible
    bcc SourceIdleFitProxy__restore
    sep #$20
.a8
    lda #0
    sta.l SourceVisual_Key+2
SourceIdleFitProxy__changed:
.a8
.i16
    rep #$30
.a16
.i16
SourceIdleFitProxy__restore:
.a16
.i16
    ply
    plx
SourceIdleFitProxy__done:
.a16
.i16
    pla
    plp
    rtl

SourceIdleFitProxy_NonIdle:
.a16
.i16
    cmp #2
    bne SourceIdleFitProxy__done
    lda.l SourceVisual_Key+2
    cmp #1
    bne SourceIdleFitProxy__done
    tdc
    cmp #$0A85
    bne SourceIdleFitProxy__done
    lda.l Spawn_Index
    cmp #3
    bcc SourceIdleFitProxy__done
    pla
    plp
    jml SourceAttackFit_Prefer
SourceIdleFitProxy_End:
