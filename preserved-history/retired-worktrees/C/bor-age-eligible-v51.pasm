; The stamp advanced exactly once (ExhaustedValid proves this). Compare
; against the one modular threshold instead of subtracting for every slot.
; Eight slots share each loop-control step. Matches still use the original
; reservation/state/age predicate and original bit mapper unchanged.
Core_StreamCache_AgeEligible:
.a16
.i16
    phx
    phy
    lda.l StreamCache_Candidate
    pha
    ldx #0
    sep #$20
.a8
    lda.l StreamCache_CurrentStamp
    sec
    sbc #STREAM_CACHE_PROTECT_WINDOW
Core_StreamCache_AgeEligible__scan:
.a8
.i16
    cpx #0
    beq Core_StreamCache_AgeEligible__next0
    cmp.l StreamCache_SlotStamp+0,x
    bne Core_StreamCache_AgeEligible__next0
    pha
    rep #$30
.a16
.i16
    phx
    txa
    clc
    adc #0
    sta.l StreamCache_Candidate
    jsr Core_StreamCache_IsEligible
    bcc Core_StreamCache_AgeEligible__restore0
    jsr Core_StreamCache_EligibleBit
    sep #$20
.a8
    ora.l StreamCache_EligibleBits,x
    sta.l StreamCache_EligibleBits,x
    rep #$30
.a16
.i16
Core_StreamCache_AgeEligible__restore0:
.a16
.i16
    plx
    sep #$20
.a8
    pla
Core_StreamCache_AgeEligible__next0:
.a8
.i16
    cmp.l StreamCache_SlotStamp+1,x
    bne Core_StreamCache_AgeEligible__next1
    pha
    rep #$30
.a16
.i16
    phx
    txa
    clc
    adc #1
    sta.l StreamCache_Candidate
    jsr Core_StreamCache_IsEligible
    bcc Core_StreamCache_AgeEligible__restore1
    jsr Core_StreamCache_EligibleBit
    sep #$20
.a8
    ora.l StreamCache_EligibleBits,x
    sta.l StreamCache_EligibleBits,x
    rep #$30
.a16
.i16
Core_StreamCache_AgeEligible__restore1:
.a16
.i16
    plx
    sep #$20
.a8
    pla
Core_StreamCache_AgeEligible__next1:
.a8
.i16
    cmp.l StreamCache_SlotStamp+2,x
    bne Core_StreamCache_AgeEligible__next2
    pha
    rep #$30
.a16
.i16
    phx
    txa
    clc
    adc #2
    sta.l StreamCache_Candidate
    jsr Core_StreamCache_IsEligible
    bcc Core_StreamCache_AgeEligible__restore2
    jsr Core_StreamCache_EligibleBit
    sep #$20
.a8
    ora.l StreamCache_EligibleBits,x
    sta.l StreamCache_EligibleBits,x
    rep #$30
.a16
.i16
Core_StreamCache_AgeEligible__restore2:
.a16
.i16
    plx
    sep #$20
.a8
    pla
Core_StreamCache_AgeEligible__next2:
.a8
.i16
    cmp.l StreamCache_SlotStamp+3,x
    bne Core_StreamCache_AgeEligible__next3
    pha
    rep #$30
.a16
.i16
    phx
    txa
    clc
    adc #3
    sta.l StreamCache_Candidate
    jsr Core_StreamCache_IsEligible
    bcc Core_StreamCache_AgeEligible__restore3
    jsr Core_StreamCache_EligibleBit
    sep #$20
.a8
    ora.l StreamCache_EligibleBits,x
    sta.l StreamCache_EligibleBits,x
    rep #$30
.a16
.i16
Core_StreamCache_AgeEligible__restore3:
.a16
.i16
    plx
    sep #$20
.a8
    pla
Core_StreamCache_AgeEligible__next3:
.a8
.i16
    cmp.l StreamCache_SlotStamp+4,x
    bne Core_StreamCache_AgeEligible__next4
    pha
    rep #$30
.a16
.i16
    phx
    txa
    clc
    adc #4
    sta.l StreamCache_Candidate
    jsr Core_StreamCache_IsEligible
    bcc Core_StreamCache_AgeEligible__restore4
    jsr Core_StreamCache_EligibleBit
    sep #$20
.a8
    ora.l StreamCache_EligibleBits,x
    sta.l StreamCache_EligibleBits,x
    rep #$30
.a16
.i16
Core_StreamCache_AgeEligible__restore4:
.a16
.i16
    plx
    sep #$20
.a8
    pla
Core_StreamCache_AgeEligible__next4:
.a8
.i16
    cmp.l StreamCache_SlotStamp+5,x
    bne Core_StreamCache_AgeEligible__next5
    pha
    rep #$30
.a16
.i16
    phx
    txa
    clc
    adc #5
    sta.l StreamCache_Candidate
    jsr Core_StreamCache_IsEligible
    bcc Core_StreamCache_AgeEligible__restore5
    jsr Core_StreamCache_EligibleBit
    sep #$20
.a8
    ora.l StreamCache_EligibleBits,x
    sta.l StreamCache_EligibleBits,x
    rep #$30
.a16
.i16
Core_StreamCache_AgeEligible__restore5:
.a16
.i16
    plx
    sep #$20
.a8
    pla
Core_StreamCache_AgeEligible__next5:
.a8
.i16
    cmp.l StreamCache_SlotStamp+6,x
    bne Core_StreamCache_AgeEligible__next6
    pha
    rep #$30
.a16
.i16
    phx
    txa
    clc
    adc #6
    sta.l StreamCache_Candidate
    jsr Core_StreamCache_IsEligible
    bcc Core_StreamCache_AgeEligible__restore6
    jsr Core_StreamCache_EligibleBit
    sep #$20
.a8
    ora.l StreamCache_EligibleBits,x
    sta.l StreamCache_EligibleBits,x
    rep #$30
.a16
.i16
Core_StreamCache_AgeEligible__restore6:
.a16
.i16
    plx
    sep #$20
.a8
    pla
Core_StreamCache_AgeEligible__next6:
.a8
.i16
    cmp.l StreamCache_SlotStamp+7,x
    bne Core_StreamCache_AgeEligible__next7
    pha
    rep #$30
.a16
.i16
    phx
    txa
    clc
    adc #7
    sta.l StreamCache_Candidate
    jsr Core_StreamCache_IsEligible
    bcc Core_StreamCache_AgeEligible__restore7
    jsr Core_StreamCache_EligibleBit
    sep #$20
.a8
    ora.l StreamCache_EligibleBits,x
    sta.l StreamCache_EligibleBits,x
    rep #$30
.a16
.i16
Core_StreamCache_AgeEligible__restore7:
.a16
.i16
    plx
    sep #$20
.a8
    pla
Core_StreamCache_AgeEligible__next7:
.a8
.i16
    rep #$30
.a16
.i16
    txa
    clc
    adc #8
    tax
    cpx #1024
    bcs Core_StreamCache_AgeEligible__done
    sep #$20
.a8
    brl Core_StreamCache_AgeEligible__scan
Core_StreamCache_AgeEligible__done:
.a16
.i16
    pla
    sta.l StreamCache_Candidate
    ply
    plx
    rts
