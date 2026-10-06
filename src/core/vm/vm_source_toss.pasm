; Pinned openbor_tossentity + toss. Source velocity order is x,z,y. A zero
; lift changes x/z only: it does NOT replace y, advance toss_time or lift a.
; Non-numeric optional numbers retain their initialized zero values. Q16.16
; and its bounded altitude domain are explicit ACCEPTED_COMPAT, not binary64.
; The additional BW array lease is exclusive and must be initialized by the
; foreign owner. Gravity/landing are separate services, not implicit here.
SourceToss4086_Ready = $7FFB38
SourceToss4086_Values = $7FFB3A ; lift,x,z: three Q16.16 values
SourceToss4086_AltitudeLo = $7FFB46
SourceToss4086_AltitudeHi = $7FFB48
SourceToss4086_TimeOffset = $7FFB4A
SourceToss4086_Argument = $7FFB4C
SourceToss4086_ArgCount = $7FFB4E
SourceToss4086_ScratchEnd = $7FFB50
SOURCE_WORLD_TOSS_TIMES = $41F300 ; 128*4 bytes, after pointer order

Vm_SourceToss:
.a16
.i16
    php
    rep #$38
    lda.l VmNativeVariant_ContextValid
    cmp #$B48F
    beq Vm_SourceToss_Branch_1
    jmp Vm_SourceToss_Bad
Vm_SourceToss_Branch_1:
.a16
.i16
    lda.l VmCall_Argc
    and #$00FF
    sta.l SourceToss4086_ArgCount
    cmp #1
    bcc Vm_SourceToss_ArityBad
    cmp #5
    bcc Vm_SourceToss_Branch_2
Vm_SourceToss_ArityBad:
.a16
.i16
    jmp Vm_SourceToss_Bad
Vm_SourceToss_Branch_2:
.a16
.i16
    lda.l VmSourceMutation_Ready
    cmp #$B4A2
    beq Vm_SourceToss_Branch_3
    jmp Vm_SourceToss_Bad
Vm_SourceToss_Branch_3:
.a16
.i16
    lda.l SourceToss4086_Ready
    cmp #$B4E2
    beq Vm_SourceToss_Branch_4
    jmp Vm_SourceToss_Bad
Vm_SourceToss_Branch_4:
.a16
.i16
    jsr Vm_SourceEntityLocate
    bcc Vm_SourceToss_Branch_5
    jmp Vm_SourceToss_Bad
Vm_SourceToss_Branch_5:
.a16
.i16
    cmp #1
    beq Vm_SourceToss_Branch_6
    jmp Vm_SourceToss_Bad
Vm_SourceToss_Branch_6:
.a16
.i16
    lda.l VmSourceWorld_Ready
    cmp #$B4A3
    beq Vm_SourceToss_Branch_7
    jmp Vm_SourceToss_Bad
Vm_SourceToss_Branch_7:
.a16
.i16
    lda.l VmSourceEntity_Base
    cmp #$4000
    beq Vm_SourceToss_Branch_8
    jmp Vm_SourceToss_Bad
Vm_SourceToss_Branch_8:
.a16
.i16
    lda.l VmSourceWorld_PoolBase
    cmp #$4000
    beq Vm_SourceToss_Branch_9
    jmp Vm_SourceToss_Bad
Vm_SourceToss_Branch_9:
.a16
.i16
    lda.l VmSourceWorld_SideBase
    cmp #$6800
    beq Vm_SourceToss_Branch_10
    jmp Vm_SourceToss_Bad
Vm_SourceToss_Branch_10:
.a16
.i16
    lda.l VmSourceEntity_Bank
    and #$00FF
    cmp #$41
    beq Vm_SourceToss_Branch_11
    jmp Vm_SourceToss_Bad
Vm_SourceToss_Branch_11:
.a16
.i16
    lda.l VmSourceWorld_Count
    bne Vm_SourceToss_Branch_12
    jmp Vm_SourceToss_Bad
Vm_SourceToss_Branch_12:
.a16
.i16
    cmp #129
    bcc Vm_SourceToss_Branch_13
    jmp Vm_SourceToss_Bad
Vm_SourceToss_Branch_13:
.a16
.i16
    cmp.l VmSourceEntity_Count
    beq Vm_SourceToss_Branch_14
    jmp Vm_SourceToss_Bad
Vm_SourceToss_Branch_14:
.a16
.i16
    lda.l VmSourceEntity_Index
    cmp.l VmSourceWorld_Count
    bcc Vm_SourceToss_Branch_15
    jmp Vm_SourceToss_Bad
Vm_SourceToss_Branch_15:
.a16
.i16
    asl a
    asl a
    sta.l SourceToss4086_TimeOffset
    asl a
    asl a
    asl a
    asl a
    sta.l SourceMotionProperty_Side
    lda #0
    ldx #0
Vm_SourceToss_ClearValues:
.a16
.i16
    sta.l SourceToss4086_Values,x
    inx
    inx
    cpx #12
    bcc Vm_SourceToss_ClearValues
    lda #1
    sta.l SourceToss4086_Argument
    lda #2
    sta.l VmSourceMutation_Tag
Vm_SourceToss_Number:
.a16
.i16
    lda.l SourceToss4086_Argument
    cmp.l SourceToss4086_ArgCount
    bcc Vm_SourceToss_NumberArgument
    jmp Vm_SourceToss_NumbersReady
Vm_SourceToss_NumberArgument:
.a16
.i16
    jsr Vm_SourceEntityArgSlot
    jsr Vm_SourceMutationNumber
    bcs Vm_SourceToss_Branch_16
    jmp Vm_SourceToss_NumberConverted
Vm_SourceToss_Branch_16:
.a16
.i16
    cmp #$FFFF
    bne Vm_SourceToss_Branch_17
    jmp Vm_SourceToss_Bad
Vm_SourceToss_Branch_17:
.a16
.i16
    lda #0
    sta.l VmSourceMutation_Lo
    sta.l VmSourceMutation_Hi
Vm_SourceToss_NumberConverted:
.a16
.i16
    lda.l SourceToss4086_Argument
    dec a
    asl a
    asl a
    tax
    lda.l VmSourceMutation_Lo
    sta.l SourceToss4086_Values,x
    lda.l VmSourceMutation_Hi
    sta.l SourceToss4086_Values+2,x
    lda.l SourceToss4086_Argument
    inc a
    sta.l SourceToss4086_Argument
    cmp.l SourceToss4086_ArgCount
    bcs Vm_SourceToss_Branch_18
    jmp Vm_SourceToss_Number
Vm_SourceToss_Branch_18:
.a16
.i16
Vm_SourceToss_NumbersReady:
.a16
.i16
    lda.l SourceToss4086_Values
    ora.l SourceToss4086_Values+2
    bne Vm_SourceToss_Branch_19
    jmp Vm_SourceToss_WriteHorizontal
Vm_SourceToss_Branch_19:
.a16
.i16
    ldy #8
    jsr Vm_SourceEntityRead16
    cmp #BOR_VT_DECIMAL
    beq Vm_SourceToss_Branch_20
    jmp Vm_SourceToss_Bad
Vm_SourceToss_Branch_20:
.a16
.i16
    ldy #10
    jsr Vm_SourceEntityRead16
    beq Vm_SourceToss_Branch_21
    jmp Vm_SourceToss_Bad
Vm_SourceToss_Branch_21:
.a16
.i16
    ldy #12
    jsr Vm_SourceEntityRead16
    clc
    adc #$8000
    sta.l SourceToss4086_AltitudeLo
    ldy #14
    jsr Vm_SourceEntityRead16 ; this helper preserves carry
    sta.l SourceToss4086_AltitudeHi
    adc #0
    pha
    lda.l SourceToss4086_AltitudeHi
    bpl Vm_SourceToss_Branch_22
    jmp Vm_SourceToss_AltitudeFits
Vm_SourceToss_Branch_22:
.a16
.i16
    pla
    bpl Vm_SourceToss_Branch_23
    jmp Vm_SourceToss_Bad
Vm_SourceToss_Branch_23:
.a16
.i16
    bra Vm_SourceToss_AltitudeChecked
Vm_SourceToss_AltitudeFits:
.a16
.i16
    pla
Vm_SourceToss_AltitudeChecked:
.a16
.i16
    sta.l SourceToss4086_AltitudeHi
Vm_SourceToss_WriteHorizontal:
.a16
.i16
    lda.l SourceMotionProperty_Side
    tax
    lda.l SourceToss4086_Values+4
    sta.l SOURCE_WORLD_SIDES+36,x
    lda.l SourceToss4086_Values+6
    sta.l SOURCE_WORLD_SIDES+38,x
    lda.l SourceToss4086_Values+8
    sta.l SOURCE_WORLD_SIDES+40,x
    lda.l SourceToss4086_Values+10
    sta.l SOURCE_WORLD_SIDES+42,x
    lda.l SourceToss4086_Values
    ora.l SourceToss4086_Values+2
    bne Vm_SourceToss_Branch_24
    jmp Vm_SourceToss_Success
Vm_SourceToss_Branch_24:
.a16
.i16
    lda.l SourceToss4086_Values
    sta.l SOURCE_WORLD_SIDES+44,x
    lda.l SourceToss4086_Values+2
    sta.l SOURCE_WORLD_SIDES+46,x
    lda.l SourceToss4086_TimeOffset
    tax
    lda.l VmSourceWorld_Time
    clc
    adc #1
    sta.l SOURCE_WORLD_TOSS_TIMES,x
    lda.l VmSourceWorld_Time+2
    adc #0
    sta.l SOURCE_WORLD_TOSS_TIMES+2,x
    ldy #12
    lda.l SourceToss4086_AltitudeLo
    sta.l VmSourceMutation_Write
    jsr Vm_SourceEntityWrite16
    ldy #14
    lda.l SourceToss4086_AltitudeHi
    sta.l VmSourceMutation_Write
    jsr Vm_SourceEntityWrite16
Vm_SourceToss_Success:
.a16
.i16
    lda #BOR_VT_INTEGER
    sta.l VmNativeVariant_Result
    lda #0
    sta.l VmNativeVariant_Result+2
    sta.l VmNativeVariant_Result+6
    lda #1
    sta.l VmNativeVariant_Result+4
    plp
    clc
    rtl
Vm_SourceToss_Bad:
.a16
.i16
    plp
    lda #VMERR_BAD_NATIVE
    sec
    rtl
