; UNHOOKED compact index for the same full physical-resource witness.
; Every listed tile ID, held bit, Ready2 and four-quarter stamp is rechecked.
; The palette tail is the unchanged original full witness implementation.
; This never authorizes pose publication or resource retirement on its own.
SourceNextCompact_Capture:
.a16
.i16
    jsl SourceNextWitness_Capture
    bcs SourceNextCompact_CaptureStart
    rtl
SourceNextCompact_CaptureStart:
.a16
.i16
    php
    rep #$30
    cld
    pha
    phx
    phy
    phb
    xba
    asl a
    pha
    lda #0
    pha
    sep #$20
.a8
    lda #$43
    pha
    plb
    rep #$20
.a16
    lda 3,s
    tax
    lda #0
    sta.w $680C,x
SourceNextCompact_CaptureLoop:
.a16
.i16
    lda.w $6812,x
    cmp #1
    bne SourceNextCompact_CaptureNext
    lda 1,s
    asl a
    clc
    adc 3,s
    tay
    txa
    and #255
    asl a
    sta.w $6930,y
    lda 1,s
    inc a
    sta 1,s
SourceNextCompact_CaptureNext:
.a16
.i16
    inx
    inx
    inx
    inx
    txa
    and #255
    bne SourceNextCompact_CaptureLoop
    lda 3,s
    tax
    lda 1,s
    sta.w $680A,x
    lda #$5243
    sta.w $680C,x
    pla
    pla
    plb
    ply
    plx
    pla
    plp
    rtl
SourceNextCompact_Ready:
.a16
.i16
    php
    rep #$30
    cld
    pha
    phx
    phy
    phb
    cmp #2
    bcc SourceNextCompact_ReadySlot
    brl SourceNextWitness_ReadyNoEarly
SourceNextCompact_ReadySlot:
.a16
.i16
    tax
    lda #0
    pha
    pha
    txa
    xba
    asl a
    pha
    txa
    beq SourceNextCompact_ReadyP1
    lda #128
    bra SourceNextCompact_ReadyBit
SourceNextCompact_ReadyP1:
.a16
.i16
    lda #64
SourceNextCompact_ReadyBit:
.a16
.i16
    pha
    sep #$20
.a8
    lda #$43
    pha
    plb
    rep #$20
.a16
    lda 3,s
    tay
    lda.l SVActor_Magic
    cmp #$AC19
    beq SourceNextCompact_ReadyMagic
    brl SourceNextWitness_ReadyNo
SourceNextCompact_ReadyMagic:
.a16
.i16
    lda.w $6800,y
    cmp #$4E50
    beq SourceNextCompact_ReadyWitness
    brl SourceNextWitness_ReadyNo
SourceNextCompact_ReadyWitness:
.a16
.i16
    lda.w $680C,y
    cmp #$5243
    beq SourceNextCompact_ReadyStamp
    brl SourceNextWitness_ReadyNo
SourceNextCompact_ReadyStamp:
.a16
.i16
    lda.w $6804,y
    cmp 1,s
    beq SourceNextCompact_ReadyBitChecked
    brl SourceNextWitness_ReadyNo
SourceNextCompact_ReadyBitChecked:
.a16
.i16
    lda.w $680A,y
    bne SourceNextCompact_Guard1
    brl SourceNextCompact_ReadyNo
SourceNextCompact_Guard1:
.a16
.i16
    cmp #65
    bcc SourceNextCompact_Guard2
    brl SourceNextCompact_ReadyNo
SourceNextCompact_Guard2:
.a16
.i16
    cmp.w $6806,y
    beq SourceNextCompact_Guard3
    brl SourceNextCompact_ReadyNo
SourceNextCompact_Guard3:
.a16
.i16
    sta 5,s
SourceNextCompact_ReadyLoop:
.a16
.i16
    lda.w $6930,y
    cmp #512
    bcc SourceNextCompact_Guard4
    brl SourceNextCompact_ReadyNo
SourceNextCompact_Guard4:
.a16
.i16
    and #7
    beq SourceNextCompact_Guard5
    brl SourceNextCompact_ReadyNo
SourceNextCompact_Guard5:
.a16
.i16
    lda.w $6930,y
    cmp 7,s
    bcs SourceNextCompact_Guard6
    brl SourceNextCompact_ReadyNo
SourceNextCompact_Guard6:
.a16
.i16
    inc a
    sta 7,s
    dec a
    tax
    lda.l SVActor_HeldBlocks,x
    and 1,s
    bne SourceNextCompact_Guard7
    brl SourceNextCompact_ReadyNo
SourceNextCompact_Guard7:
.a16
.i16
    lda.l SourceVisual_BlockCache+2,x
    cmp #2
    beq SourceNextCompact_Guard8
    brl SourceNextCompact_ReadyNo
SourceNextCompact_Guard8:
.a16
.i16
    lda.l SourceVisual_BlockCache+5,x
    and #255
    cmp #4
    beq SourceNextCompact_Guard9
    brl SourceNextCompact_ReadyNo
SourceNextCompact_Guard9:
.a16
.i16
    lda.l SourceVisual_BlockCache,x
    pha
    txa
    lsr a
    clc
    adc 5,s
    tax
    lda.w $6810,x
    cmp 1,s
    bne SourceNextCompact_ReadyPopNo
    lda.w $6812,x
    cmp #1
    bne SourceNextCompact_ReadyPopNo
    pla
    iny
    iny
    lda 5,s
    dec a
    sta 5,s
    beq SourceNextCompact_Guard10
    brl SourceNextCompact_ReadyLoop
SourceNextCompact_Guard10:
.a16
.i16
    lda 3,s
    tay
    lda.w $6806,y
    sta 5,s
    lda #0
    sta 7,s
    jmp SourceNextWitness_ReadyPaletteTail
SourceNextCompact_ReadyPopNo:
.a16
.i16
    pla
SourceNextCompact_ReadyNo:
.a16
.i16
    brl SourceNextWitness_ReadyNo
SourceNextCompact_End:
