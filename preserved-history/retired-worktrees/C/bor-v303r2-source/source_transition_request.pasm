; Normal accepted-transition request consumer. Producer writes two32byte
; rows436000/436020 while existing434E7C isodd/magic0. No resource ownership.
; Both service and normal first-attack admission reuse the original complete
; SourceWarm predicate and its final coherent sequence/magic/stage checks.
SourceRequest_PreferFirst:
.a16
.i16
    jsl SourceIdle_PreferFirst
    php
    rep #$30
    pha
    phx
    lda.l SourceVisual_Key
    cmp #$0216
    bne SourceRequest_PreferDone
    lda.l SourceVisual_Key+2
    and #$FF00
    bne SourceRequest_PreferDone
    lda.l SourceVisual_ServiceOnly
    bne SourceRequest_PreferDone
    tdc
    cmp #$0A00
    beq SourceRequest_Player0
    cmp #$0A85
    bne SourceRequest_PreferDone
    ldx #32
    bra SourceRequest_PlayerReady
SourceRequest_Player0:
.a16
.i16
    ldx #0
SourceRequest_PlayerReady:
.a16
.i16
    lda.l SourceVisual_State+30,x
    and #255
    cmp #2
    bcs SourceRequest_PreferDone
    txa
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    jsl SourceWarm_ReadAttack
    bcc SourceRequest_PreferDone
    sep #$20
.a8
    lda.l SourceWarm_Frame
    sta.l SourceVisual_Key+2
    rep #$30
.a16
.i16
SourceRequest_PreferDone:
.a16
.i16
    plx
    pla
    plp
    rtl

; Drop-in for the original STA SourceWarm_Frame. Preserve complete caller
; registers/flags; the old reader still rejects a changing snapshot afterward.
SourceRequest_ReadFrame:
.a16
.i16
    sta.l SourceWarm_Frame
    php
    rep #$30
    pha
    phx
    cld
    lda.l SourceWarm_Slot
    cmp #2
    bcc SourceRequest_Guard0
    brl SourceRequest_ReadDone
SourceRequest_Guard0:
.a16
.i16
    asl a
    asl a
    asl a
    asl a
    asl a
    tax
    lda.l $436000,x
    cmp #2
    beq SourceRequest_Guard1
    brl SourceRequest_ReadDone
SourceRequest_Guard1:
.a16
.i16
    lda.l $436010,x
    bne SourceRequest_Guard2
    brl SourceRequest_ReadDone
SourceRequest_Guard2:
.a16
.i16
    lda.l $436004,x
    cmp.l SourceWarm_Native
    beq SourceRequest_Guard3
    brl SourceRequest_ReadDone
SourceRequest_Guard3:
.a16
.i16
    lda.l $43600A,x
    cmp.l SourceWarm_Stage
    beq SourceRequest_Guard4
    brl SourceRequest_ReadDone
SourceRequest_Guard4:
.a16
.i16
    lda.l $436006,x
    cmp.w $4E42,y
    beq SourceRequest_Guard5
    brl SourceRequest_ReadDone
SourceRequest_Guard5:
.a16
.i16
    lda.l $436008,x
    cmp.w $4E3C,y
    beq SourceRequest_Guard6
    brl SourceRequest_ReadDone
SourceRequest_Guard6:
.a16
.i16
    lda.l $43600C,x
    cmp.w $4E40,y
    beq SourceRequest_Guard7
    brl SourceRequest_ReadDone
SourceRequest_Guard7:
.a16
.i16
    lda.l $43600E,x
    cmp #2
    beq SourceRequest_Guard8
    brl SourceRequest_ReadDone
SourceRequest_Guard8:
.a16
.i16
    lda.l $436002,x
    cmp #6
    bcc SourceRequest_Guard10
    brl SourceRequest_ReadDone
SourceRequest_Guard10:
.a16
.i16
    sta.l SourceWarm_Frame
SourceRequest_ReadDone:
.a16
.i16
    plx
    pla
    plp
    rtl
SourceRequest_End:
