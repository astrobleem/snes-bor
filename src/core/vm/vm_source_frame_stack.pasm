; Foreground frame-effect continuation stack, NOT a recursive interpreter.
; Push is permitted only after a parent's animation scripts completed, while
; its remaining effects are pending. Child frame/scripts/effects must finish
; before Pop. Live entity mutations and shared cached model data are retained.
; B4ED exclusive lease: eight 512-byte rows at $40F000..$40FFFF.
; Snapshot $7FFB50..$7FFD3F (496 bytes) includes frame/motion/callback/model
; initialization owners. $7FFD40..$7FFD5F stays reserved; stack controls follow.
SourceFrameStack4086_Ready = $7FFD60
SourceFrameStack4086_Depth = $7FFD62
SourceFrameStack4086_Fault = $7FFD64
SourceFrameStack4086_Row = $7FFD66
SourceFrameStack4086_Status = $7FFD68

SourceFrameStack4086_CheckIdle:
.a16
.i16
    php
    rep #$38
    pha
    lda.l SourceFrameStack4086_Ready
    beq SourceFrameStack4086_IdleGood
    cmp #$B4ED
    bne SourceFrameStack4086_IdleBad
    lda.l SourceFrameStack4086_Depth
    ora.l SourceFrameStack4086_Fault
    bne SourceFrameStack4086_IdleBad
SourceFrameStack4086_IdleGood:
.a16
.i16
    pla
    plp
    clc
    rtl
SourceFrameStack4086_IdleBad:
.a16
.i16
    pla
    plp
    sec
    rtl

SourceFrameStack4086_Push:
.a16
.i16
    php
    rep #$38
    phb
    phx
    phy
    jsr SourceFrameStack4086_CheckBoundary
    bcc SourceFrameStack4086_Relaxed_1
    jmp SourceFrameStack4086_Bad
SourceFrameStack4086_Relaxed_1:
.a16
.i16
    lda.l SourceFrameStack4086_Depth
    cmp #8
    bcc SourceFrameStack4086_Relaxed_2
    jmp SourceFrameStack4086_Bad
SourceFrameStack4086_Relaxed_2:
.a16
.i16
    lda.l SourceUpdateFrame4086_Ready
    cmp #$B4E3
    beq SourceFrameStack4086_Relaxed_3
    jmp SourceFrameStack4086_Bad
SourceFrameStack4086_Relaxed_3:
.a16
.i16
    lda.l SourceUpdateFrame4086_State
    cmp #1
    beq SourceFrameStack4086_Relaxed_4
    jmp SourceFrameStack4086_Bad
SourceFrameStack4086_Relaxed_4:
.a16
.i16
    lda.l SourceUpdateFrame4086_Pending
    cmp #2
    beq SourceFrameStack4086_Relaxed_5
    jmp SourceFrameStack4086_Bad
SourceFrameStack4086_Relaxed_5:
.a16
.i16
    lda.l SourceFrameMotion4086_Ready
    beq SourceFrameStack4086_PushMotionDone
    cmp #$B4E8
    beq SourceFrameStack4086_Relaxed_6
    jmp SourceFrameStack4086_Bad
SourceFrameStack4086_Relaxed_6:
.a16
.i16
    lda.l SourceFrameMotion4086_Status
    cmp #1
    beq SourceFrameStack4086_Relaxed_7
    jmp SourceFrameStack4086_Bad
SourceFrameStack4086_Relaxed_7:
.a16
.i16
SourceFrameStack4086_PushMotionDone:
.a16
.i16
    lda.l SourceAnimationInit4086_Ready
    beq SourceFrameStack4086_PushInitDone
    cmp #$B4EC
    beq SourceFrameStack4086_Relaxed_8
    jmp SourceFrameStack4086_Bad
SourceFrameStack4086_Relaxed_8:
.a16
.i16
    lda.l SourceAnimationInit4086_State
    cmp #3
    bcc SourceFrameStack4086_Relaxed_9
    jmp SourceFrameStack4086_Bad
SourceFrameStack4086_Relaxed_9:
.a16
.i16
SourceFrameStack4086_PushInitDone:
.a16
.i16
    lda.l SourceFrameStack4086_Depth
    jsr SourceFrameStack4086_RowOffset
    tay
    ldx #$FB50
    lda #495
    mvn $40,$7F
    lda.l SourceFrameStack4086_Depth
    inc a
    sta.l SourceFrameStack4086_Depth
    lda #0
    sta.l SourceUpdateFrame4086_State
    sta.l SourceUpdateFrame4086_Pending
    sta.l SourceFrameMotion4086_Status
    sta.l SourceAnimationCallback4086_State
    sta.l SourceAnimationInit4086_State
    sta.l SourceAnimationInit4086_Issued
    jmp SourceFrameStack4086_Good

SourceFrameStack4086_Pop:
.a16
.i16
    php
    rep #$38
    phb
    phx
    phy
    jsr SourceFrameStack4086_CheckBoundary
    bcc SourceFrameStack4086_Relaxed_10
    jmp SourceFrameStack4086_Bad
SourceFrameStack4086_Relaxed_10:
.a16
.i16
    lda.l SourceFrameStack4086_Depth
    bne SourceFrameStack4086_Relaxed_11
    jmp SourceFrameStack4086_Bad
SourceFrameStack4086_Relaxed_11:
.a16
.i16
    cmp #9
    bcc SourceFrameStack4086_Relaxed_12
    jmp SourceFrameStack4086_Bad
SourceFrameStack4086_Relaxed_12:
.a16
.i16
    lda.l SourceUpdateFrame4086_Ready
    cmp #$B4E3
    beq SourceFrameStack4086_Relaxed_13
    jmp SourceFrameStack4086_Bad
SourceFrameStack4086_Relaxed_13:
.a16
.i16
    lda.l SourceUpdateFrame4086_State
    cmp #2
    beq SourceFrameStack4086_Relaxed_14
    jmp SourceFrameStack4086_Bad
SourceFrameStack4086_Relaxed_14:
.a16
.i16
    lda.l SourceUpdateFrame4086_Pending
    beq SourceFrameStack4086_Relaxed_15
    jmp SourceFrameStack4086_Bad
SourceFrameStack4086_Relaxed_15:
.a16
.i16
    jsl SourceAnimationInit4086_CheckIdle
    bcc SourceFrameStack4086_Relaxed_16
    jmp SourceFrameStack4086_Bad
SourceFrameStack4086_Relaxed_16:
.a16
.i16
    lda.l SourceFrameStack4086_Depth
    dec a
    jsr SourceFrameStack4086_RowOffset
    tax
    ldy #$FB50
    lda #495
    mvn $7F,$40
    lda.l SourceFrameStack4086_Depth
    dec a
    sta.l SourceFrameStack4086_Depth
SourceFrameStack4086_Good:
.a16
.i16
    lda #1
    sta.l SourceFrameStack4086_Status
    ply
    plx
    plb
    plp
    clc
    rtl
SourceFrameStack4086_Bad:
.a16
.i16
    lda #1
    sta.l SourceFrameStack4086_Fault
    lda #2
    sta.l SourceFrameStack4086_Status
    ply
    plx
    plb
    plp
    sec
    rtl

SourceFrameStack4086_RowOffset:
.a16
.i16
    xba
    asl a
    clc
    adc #$F000
    sta.l SourceFrameStack4086_Row
    rts

SourceFrameStack4086_CheckBoundary:
.a16
.i16
    lda.l SourceFrameStack4086_Ready
    cmp #$B4ED
    bne SourceFrameStack4086_BoundaryBad
    lda.l SourceFrameStack4086_Fault
    bne SourceFrameStack4086_BoundaryBad
    lda.l SourceVMRun4086_Busy
    ora.l VmSourceCallback_Active
    bne SourceFrameStack4086_BoundaryBad
    lda.l VmState_Status
    and #$00FF
    cmp #VMSTAT_RUNNING
    beq SourceFrameStack4086_BoundaryBad
    cmp #VMSTAT_YIELDED
    beq SourceFrameStack4086_BoundaryBad
    cmp #VMSTAT_FAULT
    beq SourceFrameStack4086_BoundaryBad
    lda.l SourceAnimationCallback4086_Ready
    beq SourceFrameStack4086_BoundaryGood
    cmp #$B4E6
    bne SourceFrameStack4086_BoundaryBad
    lda.l SourceAnimationCallback4086_State
    beq SourceFrameStack4086_BoundaryGood
    cmp #3
    bne SourceFrameStack4086_BoundaryBad
SourceFrameStack4086_BoundaryGood:
.a16
.i16
    clc
    rts
SourceFrameStack4086_BoundaryBad:
.a16
.i16
    sec
    rts
