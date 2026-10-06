; Weapon/idle operation continuation, captured in the complete frame
; snapshot. Begin resolves source policy and starts the native model/animation
; owners. Finish requires their matching completed ticket before cursor Ack.
; The caller still must bind all model transition services and nested frame 0.
; DROP_WEAPON here is the exact flag=2/no-attached-weapon branch; an attached
; item requires a separate admitted release/platform service, never a no-op.
SourceFrameEffectBinding4086_Ready = $7FFE34 ; B4F5 immutable admission lease

SourceFrameEffectBinding4086_Check:
.a16
.i16
    lda.l SourceFrameEffectBinding4086_Ready
    cmp #$B4F5
    bne SourceFrameEffectBinding4086_CheckBad
    lda.l SourceUpdateFrame4086_Ready
    cmp #$B4E3
    bne SourceFrameEffectBinding4086_CheckBad
    lda.l SourceUpdateFrame4086_State
    cmp #1
    bne SourceFrameEffectBinding4086_CheckBad
    lda.l SourceUpdateFrame4086_Pending
    cmp #2
    bne SourceFrameEffectBinding4086_CheckBad
    lda.l SourceFrameEffectPlan4086_Ready
    cmp #$B4F2
    bne SourceFrameEffectBinding4086_CheckBad
    lda.l SourceFrameEffectPlan4086_State
    cmp #1
    bne SourceFrameEffectBinding4086_CheckBad
    lda.l SourceFrameEffectPlan4086_Slot
    cmp.l SourceUpdateFrame4086_Slot
    bne SourceFrameEffectBinding4086_CheckBad
    lda.l SourceFrameEffectPlan4086_Handle
    cmp.l SourceUpdateFrame4086_Handle
    bne SourceFrameEffectBinding4086_CheckBad
    lda.l SourceFrameEffectPlan4086_Frame
    cmp.l SourceUpdateFrame4086_Request
    bne SourceFrameEffectBinding4086_CheckBad
    lda.l SourceFrameEffectPlan4086_Count
    cmp #2
    bcc SourceFrameEffectBinding4086_CheckBad
    cmp #33
    bcs SourceFrameEffectBinding4086_CheckBad
    lda.l SourceFrameEffectPlan4086_Index
    cmp #32
    bcs SourceFrameEffectBinding4086_CheckBad
    inc a
    cmp.l SourceFrameEffectPlan4086_Count
    bcs SourceFrameEffectBinding4086_CheckBad
    jmp SourceFrameEffectBinding4086_CheckWorld
SourceFrameEffectBinding4086_CheckBad:
.a16
.i16
    sec
    rts
SourceFrameEffectBinding4086_CheckWorld:
.a16
.i16
    lda.l VmSourceWorld_Ready
    cmp #$B4A3
    bne SourceFrameEffectBinding4086_CheckBad
    lda.l VmSourceWorld_PoolBase
    cmp #$4000
    bne SourceFrameEffectBinding4086_CheckBad
    lda.l VmSourceWorld_SideBase
    cmp #$6800
    bne SourceFrameEffectBinding4086_CheckBad
    lda.l VmSourceWorld_Count
    beq SourceFrameEffectBinding4086_CheckBad
    cmp #129
    bcs SourceFrameEffectBinding4086_CheckBad
    cmp.l SourceUpdateFrame4086_Slot
    bcc SourceFrameEffectBinding4086_CheckBad
    beq SourceFrameEffectBinding4086_CheckBad
    lda.l SourceUpdateFrame4086_Bank
    cmp #64
    bcs SourceFrameEffectBinding4086_CheckBad
    lda.l SourceUpdateFrame4086_Base
    cmp #$8000
    bcc SourceFrameEffectBinding4086_CheckBad
    lda.l SourceUpdateFrame4086_AnimationData
    cmp.l SourceUpdateFrame4086_Base
    bcc SourceFrameEffectBinding4086_CheckBad
    sec
    sbc.l SourceUpdateFrame4086_Base
    clc
    adc #128
    bcs SourceFrameEffectBinding4086_CheckBad
    cmp.l SourceUpdateFrame4086_Bytes
    bcc SourceFrameEffectBinding4086_CheckCursor
    beq SourceFrameEffectBinding4086_CheckCursor
    jmp SourceFrameEffectBinding4086_CheckBad
SourceFrameEffectBinding4086_CheckCursor:
.a16
.i16
    lda.l SourceFrameEffectPlan4086_Bank
    cmp #64
    bcs SourceFrameEffectBinding4086_CheckCursorBad
    lda.l SourceFrameEffectPlan4086_Base
    cmp #$8000
    bcc SourceFrameEffectBinding4086_CheckCursorBad
    lda.l SourceFrameEffectPlan4086_Pool
    clc
    adc.l SourceFrameEffectPlan4086_Count
    bcs SourceFrameEffectBinding4086_CheckCursorBad
    cmp.l SourceFrameEffectPlan4086_Bytes
    bcc SourceFrameEffectBinding4086_CheckCursorBounds
    beq SourceFrameEffectBinding4086_CheckCursorBounds
SourceFrameEffectBinding4086_CheckCursorBad:
.a16
.i16
    sec
    rts
SourceFrameEffectBinding4086_CheckCursorBounds:
.a16
.i16
    dec a
    clc
    adc.l SourceFrameEffectPlan4086_Base
    bcs SourceFrameEffectBinding4086_CheckCursorBad
    lda.l SourceFrameEffectPlan4086_Index
    inc a
    clc
    adc.l SourceFrameEffectPlan4086_Pool
    clc
    adc.l SourceFrameEffectPlan4086_Base
    tax
    jsr SourceFrameEffectPlan4086_ReadByte
    cmp #2
    bcc SourceFrameEffectBinding4086_CheckCursorBad
    cmp #5
    bcc SourceFrameEffectBinding4086_CheckGood
    cmp #7
    bcc SourceFrameEffectBinding4086_CheckCursorBad
    cmp #12
    bcc SourceFrameEffectBinding4086_CheckGood
    cmp #15
    bcc SourceFrameEffectBinding4086_CheckCursorBad
    cmp #24
    bcs SourceFrameEffectBinding4086_CheckCursorBad
SourceFrameEffectBinding4086_CheckGood:
.a16
.i16
    clc
    rts

SourceFrameEffectBinding4086_Begin:
.a16
.i16
    php
    rep #$38
    phx
    phy
    jsr SourceFrameEffectBinding4086_Check
    bcc SourceFrameEffectBinding4086_BeginState
    jmp SourceFrameEffectBinding4086_Bad
SourceFrameEffectBinding4086_BeginState:
.a16
.i16
    lda.l SourceFrameEffectBinding4086_State
    beq SourceFrameEffectBinding4086_BeginOp
    jmp SourceFrameEffectBinding4086_Bad
SourceFrameEffectBinding4086_BeginOp:
.a16
.i16
    lda.l SourceFrameEffectPlan4086_Service
    sta.l SourceFrameEffectBinding4086_Issued
    cmp #2
    bne SourceFrameEffectBinding4086_BeginNotDrop
    jmp SourceFrameEffectBinding4086_Drop
SourceFrameEffectBinding4086_BeginNotDrop:
.a16
.i16
    cmp #3
    bne SourceFrameEffectBinding4086_BeginNotWeapon
    jmp SourceFrameEffectBinding4086_Weapon
SourceFrameEffectBinding4086_BeginNotWeapon:
.a16
.i16
    cmp #4
    beq SourceFrameEffectBinding4086_Idle
    jmp SourceFrameEffectBinding4086_Bad
SourceFrameEffectBinding4086_Idle:
.a16
.i16
    lda.l SourceUpdateFrame4086_Slot
    sta.l SourceIdle4086_Slot
    jsl SourceIdle4086_Prepare
    bcc SourceFrameEffectBinding4086_IdlePrepared
    jmp SourceFrameEffectBinding4086_Bad
SourceFrameEffectBinding4086_IdlePrepared:
.a16
.i16
    lda #2
    sta.l SourceFrameEffectBinding4086_State
    jsl SourceAnimationInit4086_Begin
    bcc SourceFrameEffectBinding4086_IdleStarted
    jmp SourceFrameEffectBinding4086_Bad
SourceFrameEffectBinding4086_IdleStarted:
.a16
.i16
    lda.l SourceAnimationInit4086_State
    cmp #2
    beq SourceFrameEffectBinding4086_IdleImmediate
    jmp SourceFrameEffectBinding4086_Good
SourceFrameEffectBinding4086_IdleImmediate:
.a16
.i16
    jmp SourceFrameEffectBinding4086_Complete

SourceFrameEffectBinding4086_Drop:
.a16
.i16
    lda.l SourceIdle4086_Ready
    cmp #$B4F3
    beq SourceFrameEffectBinding4086_DropWorld
    jmp SourceFrameEffectBinding4086_Bad
SourceFrameEffectBinding4086_DropWorld:
.a16
.i16
    lda.l VmSourceWorld_Ready
    cmp #$B4A3
    beq SourceFrameEffectBinding4086_DropCount
    jmp SourceFrameEffectBinding4086_Bad
SourceFrameEffectBinding4086_DropCount:
.a16
.i16
    lda.l VmSourceWorld_Count
    beq SourceFrameEffectBinding4086_DropReject
    cmp #129
    bcs SourceFrameEffectBinding4086_DropReject
    cmp.l SourceUpdateFrame4086_Slot
    bcc SourceFrameEffectBinding4086_DropReject
    beq SourceFrameEffectBinding4086_DropReject
    lda.l SourceUpdateFrame4086_Slot
    asl a
    asl a
    asl a
    asl a
    asl a
    tax
    lda.l $43EB1C,x
    ora.l $43EB1E,x
    bne SourceFrameEffectBinding4086_DropReject
    lda.l SourceWeapon4086_Ready
    cmp #$B4F1
    bne SourceFrameEffectBinding4086_DropReject
    lda.l SourceUpdateFrame4086_Slot
    sta.l SourceWeapon4086_Slot
    phx
    jsr SourceWeapon4086_CheckLease
    plx
    bcs SourceFrameEffectBinding4086_DropReject
    txa
    lsr a
    tax
    lda.l $43E208,x
    sta.l SourceWeapon4086_NumberLo
    lda.l $43E20A,x
    sta.l SourceWeapon4086_NumberHi
    bmi SourceFrameEffectBinding4086_DropNoSwitch
    ora.l SourceWeapon4086_NumberLo
    bne SourceFrameEffectBinding4086_Select
SourceFrameEffectBinding4086_DropNoSwitch:
.a16
.i16
    jmp SourceFrameEffectBinding4086_Complete
SourceFrameEffectBinding4086_DropReject:
.a16
.i16
    jmp SourceFrameEffectBinding4086_Bad

SourceFrameEffectBinding4086_Weapon:
.a16
.i16
    lda.l SourceUpdateFrame4086_AnimationData
    clc
    adc #12
    tax
    jsr SourceUpdateFrame4086_Read
    sta.l SourceWeapon4086_NumberLo
    inx
    inx
    jsr SourceUpdateFrame4086_Read
    sta.l SourceWeapon4086_NumberHi
SourceFrameEffectBinding4086_Select:
.a16
.i16
    lda.l SourceUpdateFrame4086_Slot
    sta.l SourceWeapon4086_Slot
    lda #0
    sta.l SourceWeapon4086_AnimFlagLo
    sta.l SourceWeapon4086_AnimFlagHi
    jsl SourceWeapon4086_Resolve
    bcc SourceFrameEffectBinding4086_Selected
    jmp SourceFrameEffectBinding4086_Bad
SourceFrameEffectBinding4086_Selected:
.a16
.i16
    lda.l SourceWeapon4086_Selected
    sta.l SourceFrameEffectBinding4086_Target
    sta.l SourceModelTransition4086_New
    lda.l SourceUpdateFrame4086_Slot
    sta.l SourceModelTransition4086_Slot
    lda.l SourceWeapon4086_Sync
    sta.l SourceModelAnimation4086_Sync
    lda #1
    sta.l SourceFrameEffectBinding4086_State
    jsl SourceModelTransition4086_Begin
    bcc SourceFrameEffectBinding4086_ModelStarted
    jmp SourceFrameEffectBinding4086_Bad
SourceFrameEffectBinding4086_ModelStarted:
.a16
.i16
    lda.l SourceModelTransition4086_State
    cmp #2
    beq SourceFrameEffectBinding4086_ModelImmediate
    jmp SourceFrameEffectBinding4086_Good
SourceFrameEffectBinding4086_ModelImmediate:
.a16
.i16
    jmp SourceFrameEffectBinding4086_Complete

SourceFrameEffectBinding4086_Finish:
.a16
.i16
    php
    rep #$38
    phx
    phy
    jsr SourceFrameEffectBinding4086_Check
    bcc SourceFrameEffectBinding4086_FinishOp
    jmp SourceFrameEffectBinding4086_Bad
SourceFrameEffectBinding4086_FinishOp:
.a16
.i16
    lda.l SourceFrameEffectBinding4086_Issued
    cmp.l SourceFrameEffectPlan4086_Service
    beq SourceFrameEffectBinding4086_FinishState
    jmp SourceFrameEffectBinding4086_Bad
SourceFrameEffectBinding4086_FinishState:
.a16
.i16
    lda.l SourceFrameEffectBinding4086_State
    cmp #1
    bne SourceFrameEffectBinding4086_FinishNotModel
    lda.l SourceModelTransition4086_Ready
    cmp #$B4F0
    bne SourceFrameEffectBinding4086_FinishReject
    lda.l SourceModelTransition4086_State
    cmp #2
    bne SourceFrameEffectBinding4086_FinishReject
    lda.l SourceModelTransition4086_Service
    bne SourceFrameEffectBinding4086_FinishReject
    lda.l SourceModelTransition4086_Slot
    cmp.l SourceUpdateFrame4086_Slot
    bne SourceFrameEffectBinding4086_FinishReject
    lda.l SourceModelTransition4086_New
    cmp.l SourceFrameEffectBinding4086_Target
    bne SourceFrameEffectBinding4086_FinishReject
    jmp SourceFrameEffectBinding4086_Complete
SourceFrameEffectBinding4086_FinishNotModel:
.a16
.i16
    cmp #2
    bne SourceFrameEffectBinding4086_FinishReject
    lda.l SourceFrameEffectPlan4086_Service
    cmp #4
    bne SourceFrameEffectBinding4086_FinishReject
    lda.l SourceAnimationInit4086_Ready
    cmp #$B4EC
    bne SourceFrameEffectBinding4086_FinishReject
    lda.l SourceAnimationInit4086_State
    cmp #2
    bne SourceFrameEffectBinding4086_FinishReject
    lda.l SourceAnimationInit4086_Slot
    cmp.l SourceUpdateFrame4086_Slot
    bne SourceFrameEffectBinding4086_FinishReject
    lda.l SourceAnimationInit4086_Number
    ora.l SourceAnimationInit4086_Reset
    bne SourceFrameEffectBinding4086_FinishReject
    jmp SourceFrameEffectBinding4086_Complete
SourceFrameEffectBinding4086_FinishReject:
.a16
.i16
    jmp SourceFrameEffectBinding4086_Bad
SourceFrameEffectBinding4086_Complete:
.a16
.i16
    lda.l SourceFrameEffectPlan4086_Service
    sta.l SourceFrameEffectPlan4086_Acknowledged
    jsl SourceFrameEffectPlan4086_Ack
    bcc SourceFrameEffectBinding4086_Good
    jmp SourceFrameEffectBinding4086_Bad
SourceFrameEffectBinding4086_Good:
.a16
.i16
    ply
    plx
    plp
    clc
    rtl
SourceFrameEffectBinding4086_Bad:
.a16
.i16
    lda #3
    sta.l SourceFrameEffectBinding4086_State
    sta.l SourceFrameEffectPlan4086_State
    ply
    plx
    plp
    sec
    rtl
