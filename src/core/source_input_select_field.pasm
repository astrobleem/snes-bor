; A16 is the physical field being replayed by the bounded source catch-up
; batch. Preserve caller state and queue-row X. Drain sampling remains separate:
; each source tick receives that field's held pads, not the latest pad repeated
; over the entire backlog. Multiple 200-Hz ticks within one field get one edge.
SourceInput_SelectField:
    php
    rep #$30
.a16
.i16
    pha
    phx
    phy
    sta.l SourceInput_ReplayTemp
    lda.l SourceInput_Samples
    bne SourceInput_SelectField__sampled
    brl SourceInput_SelectField__miss
SourceInput_SelectField__sampled:
.a16
.i16
    lda.l StageTimer_FieldCounter
    sec
    sbc.l SourceInput_ReplayTemp
    cmp #63
    bcc SourceInput_SelectField__recent
    brl SourceInput_SelectField__miss
SourceInput_SelectField__recent:
.a16
.i16
    lda.l SourceInput_ReplayTemp
    sec
    sbc.l SourceInput_BaseField
    dec a
    cmp #$8000
    bcc SourceInput_SelectField__in_epoch
    brl SourceInput_SelectField__miss
SourceInput_SelectField__in_epoch:
.a16
.i16
    and #63
    asl a
    asl a
    tax
    lda.l SourceInput_Ring,x
    sta.l SourceInput_Selected1
    lda.l SourceInput_Ring+2,x
    sta.l SourceInput_Selected2
    lda.l SourceInput_ReplayTemp
    cmp.l SourceInput_ReplayField
    beq SourceInput_SelectField__same
    sta.l SourceInput_ReplayField
    lda.l SourceInput_ReplayHeld1
    eor #$FFFF
    and.l SourceInput_Selected1
    sta.l $412016
    lda.l SourceInput_ReplayHeld2
    eor #$FFFF
    and.l SourceInput_Selected2
    sta.l $41201A
    bra SourceInput_SelectField__held
SourceInput_SelectField__same:
.a16
.i16
    lda #0
    sta.l $412016
    sta.l $41201A
SourceInput_SelectField__held:
.a16
.i16
    lda.l SourceInput_Selected1
    sta.l SourceInput_ReplayHeld1
    sta.l $412014
    lda.l SourceInput_Selected2
    sta.l SourceInput_ReplayHeld2
    sta.l $412018
    bra SourceInput_SelectField__done
SourceInput_SelectField__miss:
.a16
.i16
    ; Startup before the first sample or an older-than-ring backlog retains
    ; the existing sampled fallback, with an explicit diagnostic count.
    lda.l SourceInput_HistoryMisses
    inc a
    sta.l SourceInput_HistoryMisses
SourceInput_SelectField__done:
.a16
.i16
    ply
    plx
    pla
    plp
    rtl
