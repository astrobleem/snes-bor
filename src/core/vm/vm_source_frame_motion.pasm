; Checked movement/base/facing prefix of the pinned update_frame effect service.
; Generic B4FE inputs; source integer movement becomes exact Q16.16 here.
; B4E8 lease is cold-disabled. Begin of each admitted update_frame retires the
; previous motion status. One call is permitted in pending service 2. Weapon,
; quake, births, audio and projectiles must still finish before that service Ack.
SourceFrameMotion4086_Ready = $7FFC30
SourceFrameMotion4086_Status = $7FFC32 ; 0 not applied,1 applied,2 fault
SourceFrameMotion4086_Base = $7FFC34
SourceFrameMotion4086_X = $7FFC36
SourceFrameMotion4086_Y = $7FFC38
SourceFrameMotion4086_Z = $7FFC3A

SourceFrameMotion4086_Apply:
.a16
.i16
    php
    rep #$38
    phx
    phy
    lda.l SourceFrameMotion4086_Ready
    cmp #$B4E8
    beq SourceFrameMotion4086_Branch_1
    jmp SourceFrameMotion4086_Bad
SourceFrameMotion4086_Branch_1:
.a16
.i16
    lda.l SourceFrameMotion4086_Status
    beq SourceFrameMotion4086_Branch_2
    jmp SourceFrameMotion4086_Bad
SourceFrameMotion4086_Branch_2:
.a16
.i16
    lda.l SourceUpdateFrame4086_Ready
    cmp #$B4E3
    beq SourceFrameMotion4086_Branch_3
    jmp SourceFrameMotion4086_Bad
SourceFrameMotion4086_Branch_3:
.a16
.i16
    lda.l SourceUpdateFrame4086_State
    cmp #1
    beq SourceFrameMotion4086_Branch_4
    jmp SourceFrameMotion4086_Bad
SourceFrameMotion4086_Branch_4:
.a16
.i16
    lda.l SourceUpdateFrame4086_Pending
    cmp #2
    beq SourceFrameMotion4086_Branch_5
    jmp SourceFrameMotion4086_Bad
SourceFrameMotion4086_Branch_5:
.a16
.i16
    ; Preflight every converted integer before mutating a live entity.
    lda.l SourceUpdateFrame4086_FirstFrame
    tax
    jsr SourceFrameMotion4086_Integer
    bcc SourceFrameMotion4086_Branch_6
    jmp SourceFrameMotion4086_Bad
SourceFrameMotion4086_Branch_6:
.a16
.i16
    sta.l SourceFrameMotion4086_Base
    lda.l SourceUpdateFrame4086_FrameData
    clc
    adc #4
    tax
    jsr SourceFrameMotion4086_Integer
    bcc SourceFrameMotion4086_Branch_7
    jmp SourceFrameMotion4086_Bad
SourceFrameMotion4086_Branch_7:
.a16
.i16
    sta.l SourceFrameMotion4086_X
    inx
    inx
    jsr SourceFrameMotion4086_Integer
    bcc SourceFrameMotion4086_Branch_8
    jmp SourceFrameMotion4086_Bad
SourceFrameMotion4086_Branch_8:
.a16
.i16
    sta.l SourceFrameMotion4086_Y
    inx
    inx
    jsr SourceFrameMotion4086_Integer
    bcc SourceFrameMotion4086_Branch_9
    jmp SourceFrameMotion4086_Bad
SourceFrameMotion4086_Branch_9:
.a16
.i16
    sta.l SourceFrameMotion4086_Z
    lda.l SourceUpdateFrame4086_View
    tax
    lda.l $41001C,x                ; source direction, INTEGER low word
    ora.l $41001E,x                ; full integer truth value
    beq SourceFrameMotion4086_Branch_10
    jmp SourceFrameMotion4086_DirectionReady
SourceFrameMotion4086_Branch_10:
.a16
.i16
    lda.l SourceFrameMotion4086_X
    cmp #$8000                    ; negation cannot fit signed Q16.16
    bne SourceFrameMotion4086_Branch_11
    jmp SourceFrameMotion4086_Bad
SourceFrameMotion4086_Branch_11:
.a16
.i16
    eor #$FFFF
    inc a
    sta.l SourceFrameMotion4086_X
SourceFrameMotion4086_DirectionReady:
.a16
.i16
    jsr SourceFrameMotion4086_CheckSums
    bcs SourceFrameMotion4086_Branch_12
    jmp SourceFrameMotion4086_SumsReady
SourceFrameMotion4086_Branch_12:
.a16
.i16
    jmp SourceFrameMotion4086_Bad
SourceFrameMotion4086_SumsReady:
.a16
.i16
    lda.l VmSourceWorld_Level
    bne SourceFrameMotion4086_Branch_13
    jmp SourceFrameMotion4086_BaseWork
SourceFrameMotion4086_Branch_13:
.a16
.i16
    lda.l SourceUpdateFrame4086_Aux
    tax
    lda.l $410002,x
    clc
    adc.l SourceFrameMotion4086_X
    sta.l $410002,x
    lda.l $410006,x
    clc
    adc.l SourceFrameMotion4086_Z
    sta.l $410006,x
SourceFrameMotion4086_BaseWork:
.a16
.i16
    lda.l SourceFrameMotion4086_Base
    bne SourceFrameMotion4086_Branch_14
    jmp SourceFrameMotion4086_AddBase
SourceFrameMotion4086_Branch_14:
.a16
.i16
    bpl SourceFrameMotion4086_Branch_15
    jmp SourceFrameMotion4086_AddBase
SourceFrameMotion4086_Branch_15:
.a16
.i16
    lda.l SourceUpdateFrame4086_Side
    tax
    lda.l $410032,x               ; side base Q16.16 high
    bpl SourceFrameMotion4086_Branch_16
    jmp SourceFrameMotion4086_SetBase
SourceFrameMotion4086_Branch_16:
.a16
.i16
    ora.l $410030,x
    beq SourceFrameMotion4086_Branch_17
    jmp SourceFrameMotion4086_Flip
SourceFrameMotion4086_Branch_17:
.a16
.i16
SourceFrameMotion4086_SetBase:
.a16
.i16
    lda #0
    sta.l $410030,x
    lda.l SourceFrameMotion4086_Base
    sta.l $410032,x
    jmp SourceFrameMotion4086_Flip
SourceFrameMotion4086_AddBase:
.a16
.i16
    lda.l SourceUpdateFrame4086_Side
    tax
    lda.l $410032,x
    clc
    adc.l SourceFrameMotion4086_Y
    sta.l $410032,x
    lda.l SourceUpdateFrame4086_Aux
    tax
    lda.l SourceFrameMotion4086_Y
    bne SourceFrameMotion4086_Branch_18
    jmp SourceFrameMotion4086_ClearAlt
SourceFrameMotion4086_Branch_18:
.a16
.i16
    clc
    adc.l $41000A,x
    sta.l $41000A,x
    jmp SourceFrameMotion4086_Flip
SourceFrameMotion4086_ClearAlt:
.a16
.i16
    lda #0
    sta.l $410008,x
    sta.l $41000A,x
SourceFrameMotion4086_Flip:
.a16
.i16
    lda.l SourceUpdateFrame4086_AnimationData
    tax
    jsr SourceUpdateFrame4086_Read
    cmp.l SourceUpdateFrame4086_Request
    beq SourceFrameMotion4086_Branch_19
    jmp SourceFrameMotion4086_Done
SourceFrameMotion4086_Branch_19:
.a16
.i16
    inx
    inx
    jsr SourceUpdateFrame4086_Read
    bne SourceFrameMotion4086_Done ; full 32-bit frame event comparison
    lda.l SourceUpdateFrame4086_View
    tax
    lda.l $41001C,x
    ora.l $41001E,x
    bne SourceFrameMotion4086_Branch_20
    jmp SourceFrameMotion4086_FlipOne
SourceFrameMotion4086_Branch_20:
.a16
.i16
    lda #0
    jmp SourceFrameMotion4086_FlipWrite
SourceFrameMotion4086_FlipOne:
.a16
.i16
    lda #1
SourceFrameMotion4086_FlipWrite:
.a16
.i16
    sta.l $41001C,x
    lda #0
    sta.l $41001E,x
SourceFrameMotion4086_Done:
.a16
.i16
    lda #1
    sta.l SourceFrameMotion4086_Status
    ply
    plx
    plp
    clc
    rtl
SourceFrameMotion4086_Bad:
.a16
.i16
    lda #2
    sta.l SourceFrameMotion4086_Status
    ply
    plx
    plp
    sec
    rtl

; Read a source int32 that is exactly representable after integer -> Q16.16.
; Return A=int16, X points to high word, C=1 outside the admitted domain.
SourceFrameMotion4086_Integer:
.a16
.i16
    jsr SourceUpdateFrame4086_Read
    pha
    inx
    inx
    jsr SourceUpdateFrame4086_Read
    pha
    lda 3,s
    bpl SourceFrameMotion4086_Branch_21
    jmp SourceFrameMotion4086_IntegerNegative
SourceFrameMotion4086_Branch_21:
.a16
.i16
    pla
    cmp #0
    jmp SourceFrameMotion4086_IntegerCompare
SourceFrameMotion4086_IntegerNegative:
.a16
.i16
    pla
    cmp #$FFFF
SourceFrameMotion4086_IntegerPositive:
.a16
.i16
SourceFrameMotion4086_IntegerCompare:
.a16
.i16
    beq SourceFrameMotion4086_Branch_22
    jmp SourceFrameMotion4086_IntegerBad
SourceFrameMotion4086_Branch_22:
.a16
.i16
    pla
    clc
    rts
SourceFrameMotion4086_IntegerBad:
.a16
.i16
    pla
    sec
    rts

; Preflight all fixed-point sums so overflow rejects before any live write.
SourceFrameMotion4086_CheckSums:
.a16
.i16
    lda.l VmSourceWorld_Level
    bne SourceFrameMotion4086_Branch_23
    jmp SourceFrameMotion4086_CheckBase
SourceFrameMotion4086_Branch_23:
.a16
.i16
    lda.l SourceUpdateFrame4086_Aux
    tax
    lda.l $410002,x
    clc
    adc.l SourceFrameMotion4086_X
    bvc SourceFrameMotion4086_Branch_24
    jmp SourceFrameMotion4086_SumBad
SourceFrameMotion4086_Branch_24:
.a16
.i16
    lda.l $410006,x
    clc
    adc.l SourceFrameMotion4086_Z
    bvc SourceFrameMotion4086_Branch_25
    jmp SourceFrameMotion4086_SumBad
SourceFrameMotion4086_Branch_25:
.a16
.i16
SourceFrameMotion4086_CheckBase:
.a16
.i16
    lda.l SourceFrameMotion4086_Base
    bne SourceFrameMotion4086_Branch_26
    jmp SourceFrameMotion4086_CheckAddBase
SourceFrameMotion4086_Branch_26:
.a16
.i16
    bmi SourceFrameMotion4086_Branch_27
    jmp SourceFrameMotion4086_SumGood
SourceFrameMotion4086_Branch_27:
.a16
.i16
SourceFrameMotion4086_CheckAddBase:
.a16
.i16
    lda.l SourceUpdateFrame4086_Side
    tax
    lda.l $410032,x
    clc
    adc.l SourceFrameMotion4086_Y
    bvc SourceFrameMotion4086_Branch_28
    jmp SourceFrameMotion4086_SumBad
SourceFrameMotion4086_Branch_28:
.a16
.i16
    lda.l SourceFrameMotion4086_Y
    bne SourceFrameMotion4086_Branch_29
    jmp SourceFrameMotion4086_SumGood
SourceFrameMotion4086_Branch_29:
.a16
.i16
    lda.l SourceUpdateFrame4086_Aux
    tax
    lda.l $41000A,x
    clc
    adc.l SourceFrameMotion4086_Y
    bvc SourceFrameMotion4086_Branch_30
    jmp SourceFrameMotion4086_SumBad
SourceFrameMotion4086_Branch_30:
.a16
.i16
SourceFrameMotion4086_SumGood:
.a16
.i16
    clc
    rts
SourceFrameMotion4086_SumBad:
.a16
.i16
    sec
    rts
