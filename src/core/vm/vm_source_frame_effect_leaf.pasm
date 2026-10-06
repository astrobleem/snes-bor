; Synchronous captured-frame handlers for QUAKE, JUMP_VELOCITY and REACTIVE.
; Each successful call performs the source mutation and acknowledges exactly
; that cursor operation. No scratch survives a yield or nested frame call.
; Shared animation quake counters: $43FB00..$43FCFF, 128*int32. The old
; $41FF00 reservation is not used. Level quake is a source int32, not camera
; presentation; the eventual level renderer must consume it explicitly.
SourceFrameEffectLeaf4086_Ready = $7FFDE0
SourceFrameEffectLeaf4086_Status = $7FFDE2
SourceFrameEffectLeaf4086_Side = $7FFDE4
SourceFrameEffectLeaf4086_Flags = $7FFDE6
SourceFrameEffectLeaf4086_QuakeOffset = $7FFDE8
SourceFrameEffectLeaf4086_StartLo = $7FFDEA
SourceFrameEffectLeaf4086_StartHi = $7FFDEC
SourceFrameEffectLeaf4086_RepeatLo = $7FFDEE
SourceFrameEffectLeaf4086_RepeatHi = $7FFDF0
SourceFrameEffectLeaf4086_ValueLo = $7FFDF2
SourceFrameEffectLeaf4086_ValueHi = $7FFDF4
SourceFrameEffectLeaf4086_CountLo = $7FFDF6
SourceFrameEffectLeaf4086_CountHi = $7FFDF8
SourceFrameEffectLeaf4086_NextLo = $7FFDFA
SourceFrameEffectLeaf4086_NextHi = $7FFDFC
SourceFrameEffectLeaf4086_Temp = $7FFDFE
SourceFrameEffectLeaf4086_LevelQuakeLo = $7FFE30
SourceFrameEffectLeaf4086_LevelQuakeHi = $7FFE32

SourceFrameEffectLeaf4086_Apply:
.a16
.i16
    php
    rep #$38
    phx
    phy
    lda.l SourceFrameEffectLeaf4086_Ready
    cmp #$B4F4
    beq SourceFrameEffectLeaf4086_PrefixLease
    jmp SourceFrameEffectLeaf4086_Bad
SourceFrameEffectLeaf4086_PrefixLease:
.a16
.i16
    lda.l SourceUpdateFrame4086_Ready
    cmp #$B4E3
    beq SourceFrameEffectLeaf4086_PrefixState
    jmp SourceFrameEffectLeaf4086_Bad
SourceFrameEffectLeaf4086_PrefixState:
.a16
.i16
    lda.l SourceUpdateFrame4086_State
    cmp #1
    beq SourceFrameEffectLeaf4086_PrefixPending
    jmp SourceFrameEffectLeaf4086_Bad
SourceFrameEffectLeaf4086_PrefixPending:
.a16
.i16
    lda.l SourceUpdateFrame4086_Pending
    cmp #2
    beq SourceFrameEffectLeaf4086_CursorLease
    jmp SourceFrameEffectLeaf4086_Bad
SourceFrameEffectLeaf4086_CursorLease:
.a16
.i16
    lda.l SourceFrameEffectPlan4086_Ready
    cmp #$B4F2
    beq SourceFrameEffectLeaf4086_CursorState
    jmp SourceFrameEffectLeaf4086_Bad
SourceFrameEffectLeaf4086_CursorState:
.a16
.i16
    lda.l SourceFrameEffectPlan4086_State
    cmp #1
    beq SourceFrameEffectLeaf4086_CursorSlot
    jmp SourceFrameEffectLeaf4086_Bad
SourceFrameEffectLeaf4086_CursorSlot:
.a16
.i16
    lda.l SourceFrameEffectPlan4086_Slot
    cmp.l SourceUpdateFrame4086_Slot
    beq SourceFrameEffectLeaf4086_CursorHandle
    jmp SourceFrameEffectLeaf4086_Bad
SourceFrameEffectLeaf4086_CursorHandle:
.a16
.i16
    lda.l SourceFrameEffectPlan4086_Handle
    cmp.l SourceUpdateFrame4086_Handle
    beq SourceFrameEffectLeaf4086_CursorFrame
    jmp SourceFrameEffectLeaf4086_Bad
SourceFrameEffectLeaf4086_CursorFrame:
.a16
.i16
    lda.l SourceFrameEffectPlan4086_Frame
    cmp.l SourceUpdateFrame4086_Request
    beq SourceFrameEffectLeaf4086_CursorIndex
    jmp SourceFrameEffectLeaf4086_Bad
SourceFrameEffectLeaf4086_CursorIndex:
.a16
.i16
    lda.l SourceFrameEffectPlan4086_Count
    cmp #2
    bcc SourceFrameEffectLeaf4086_CursorBad
    cmp #33
    bcs SourceFrameEffectLeaf4086_CursorBad
    lda.l SourceFrameEffectPlan4086_Index
    cmp #32
    bcs SourceFrameEffectLeaf4086_CursorBad
    inc a
    cmp.l SourceFrameEffectPlan4086_Count
    bcs SourceFrameEffectLeaf4086_CursorBad
    lda.l SourceFrameEffectPlan4086_Bank
    cmp #64
    bcs SourceFrameEffectLeaf4086_CursorBad
    lda.l SourceFrameEffectPlan4086_Base
    cmp #$8000
    bcc SourceFrameEffectLeaf4086_CursorBad
    lda.l SourceFrameEffectPlan4086_Pool
    clc
    adc.l SourceFrameEffectPlan4086_Count
    bcs SourceFrameEffectLeaf4086_CursorBad
    cmp.l SourceFrameEffectPlan4086_Bytes
    bcc SourceFrameEffectLeaf4086_CursorBounds
    beq SourceFrameEffectLeaf4086_CursorBounds
SourceFrameEffectLeaf4086_CursorBad:
.a16
.i16
    jmp SourceFrameEffectLeaf4086_Bad
SourceFrameEffectLeaf4086_CursorBounds:
.a16
.i16
    dec a
    clc
    adc.l SourceFrameEffectPlan4086_Base
    bcs SourceFrameEffectLeaf4086_CursorBad
    lda.l SourceFrameEffectPlan4086_Index
    inc a
    clc
    adc.l SourceFrameEffectPlan4086_Pool
    clc
    adc.l SourceFrameEffectPlan4086_Base
    tax
    jsr SourceFrameEffectPlan4086_ReadByte
    cmp #2
    bcc SourceFrameEffectLeaf4086_CursorBad
    cmp #5
    bcc SourceFrameEffectLeaf4086_World
    cmp #7
    bcc SourceFrameEffectLeaf4086_CursorBad
    cmp #12
    bcc SourceFrameEffectLeaf4086_World
    cmp #15
    bcc SourceFrameEffectLeaf4086_CursorBad
    cmp #24
    bcs SourceFrameEffectLeaf4086_CursorBad
SourceFrameEffectLeaf4086_World:
.a16
.i16
    lda.l VmSourceWorld_Ready
    cmp #$B4A3
    beq SourceFrameEffectLeaf4086_Pool
    jmp SourceFrameEffectLeaf4086_Bad
SourceFrameEffectLeaf4086_Pool:
.a16
.i16
    lda.l VmSourceWorld_PoolBase
    cmp #$4000
    beq SourceFrameEffectLeaf4086_SideLease
    jmp SourceFrameEffectLeaf4086_Bad
SourceFrameEffectLeaf4086_SideLease:
.a16
.i16
    lda.l VmSourceWorld_SideBase
    cmp #$6800
    beq SourceFrameEffectLeaf4086_Count
    jmp SourceFrameEffectLeaf4086_Bad
SourceFrameEffectLeaf4086_Count:
.a16
.i16
    lda.l VmSourceWorld_Count
    beq SourceFrameEffectLeaf4086_CountBad
    cmp #129
    bcs SourceFrameEffectLeaf4086_CountBad
    cmp.l SourceUpdateFrame4086_Slot
    bcc SourceFrameEffectLeaf4086_CountBad
    beq SourceFrameEffectLeaf4086_CountBad
    lda.l SourceUpdateFrame4086_Handle
    beq SourceFrameEffectLeaf4086_CountBad
    cmp #129
    bcs SourceFrameEffectLeaf4086_CountBad
    cmp.l SourceUpdateFrame4086_Animations
    bcc SourceFrameEffectLeaf4086_Table
    beq SourceFrameEffectLeaf4086_Table
SourceFrameEffectLeaf4086_CountBad:
.a16
.i16
    jmp SourceFrameEffectLeaf4086_Bad
SourceFrameEffectLeaf4086_Table:
.a16
.i16
    lda.l SourceUpdateFrame4086_Bank
    cmp #64
    bcs SourceFrameEffectLeaf4086_CountBad
    lda.l SourceUpdateFrame4086_Base
    cmp #$8000
    bcc SourceFrameEffectLeaf4086_CountBad
    lda.l SourceUpdateFrame4086_AnimationData
    cmp.l SourceUpdateFrame4086_Base
    bcc SourceFrameEffectLeaf4086_CountBad
    sec
    sbc.l SourceUpdateFrame4086_Base
    clc
    adc #128
    bcs SourceFrameEffectLeaf4086_CountBad
    cmp.l SourceUpdateFrame4086_Bytes
    bcc SourceFrameEffectLeaf4086_Offsets
    beq SourceFrameEffectLeaf4086_Offsets
    jmp SourceFrameEffectLeaf4086_Bad
SourceFrameEffectLeaf4086_Offsets:
.a16
.i16
    lda.l SourceUpdateFrame4086_Slot
    asl a
    asl a
    asl a
    asl a
    asl a
    sta.l SourceFrameEffectLeaf4086_Flags
    asl a
    sta.l SourceFrameEffectLeaf4086_Side
    lsr a
    lsr a
    clc
    adc.l SourceFrameEffectLeaf4086_Side
    clc
    adc #$4000
    cmp.l SourceUpdateFrame4086_View
    beq SourceFrameEffectLeaf4086_Operation
    jmp SourceFrameEffectLeaf4086_Bad
SourceFrameEffectLeaf4086_Operation:
.a16
.i16
    lda.l SourceFrameEffectPlan4086_Service
    cmp #17
    bne SourceFrameEffectLeaf4086_CheckJump
    jmp SourceFrameEffectLeaf4086_Quake
SourceFrameEffectLeaf4086_CheckJump:
.a16
.i16
    cmp #19
    bne SourceFrameEffectLeaf4086_CheckReactive
    jmp SourceFrameEffectLeaf4086_Jump
SourceFrameEffectLeaf4086_CheckReactive:
.a16
.i16
    cmp #22
    beq SourceFrameEffectLeaf4086_Reactive
    jmp SourceFrameEffectLeaf4086_Bad
SourceFrameEffectLeaf4086_Reactive:
.a16
.i16
    lda.l SourceIdle4086_Ready
    cmp #$B4F3
    beq SourceFrameEffectLeaf4086_ReactiveLease
    jmp SourceFrameEffectLeaf4086_Bad
SourceFrameEffectLeaf4086_ReactiveLease:
.a16
.i16
    lda.l SourceFrameEffectLeaf4086_Flags
    tax
    lda #1
    sta.l $43EB10,x
    lda #0
    sta.l $43EB12,x
    jmp SourceFrameEffectLeaf4086_Ack

SourceFrameEffectLeaf4086_Jump:
.a16
.i16
    lda.l SourceUpdateFrame4086_AnimationData
    clc
    adc #40
    tax
    jsr SourceUpdateFrame4086_Read
    sta.l SourceFrameEffectLeaf4086_StartLo
    inx
    inx
    jsr SourceUpdateFrame4086_Read
    sta.l SourceFrameEffectLeaf4086_StartHi
    inx
    inx
    jsr SourceUpdateFrame4086_Read
    sta.l SourceFrameEffectLeaf4086_RepeatLo
    inx
    inx
    jsr SourceUpdateFrame4086_Read
    sta.l SourceFrameEffectLeaf4086_RepeatHi
    lda.l SourceUpdateFrame4086_View
    tax
    lda.l $41001C,x
    ora.l $41001E,x
    bne SourceFrameEffectLeaf4086_JumpStore
    lda #0
    sec
    sbc.l SourceFrameEffectLeaf4086_StartLo
    sta.l SourceFrameEffectLeaf4086_StartLo
    lda #0
    sbc.l SourceFrameEffectLeaf4086_StartHi
    bvc SourceFrameEffectLeaf4086_JumpNegated
    jmp SourceFrameEffectLeaf4086_Bad
SourceFrameEffectLeaf4086_JumpNegated:
.a16
.i16
    sta.l SourceFrameEffectLeaf4086_StartHi
SourceFrameEffectLeaf4086_JumpStore:
.a16
.i16
    lda.l SourceFrameEffectLeaf4086_Side
    tax
    lda.l SourceFrameEffectLeaf4086_StartLo
    sta.l $416824,x
    lda.l SourceFrameEffectLeaf4086_StartHi
    sta.l $416826,x
    lda.l SourceFrameEffectLeaf4086_RepeatLo
    sta.l $416828,x
    lda.l SourceFrameEffectLeaf4086_RepeatHi
    sta.l $41682A,x
    jmp SourceFrameEffectLeaf4086_Ack

SourceFrameEffectLeaf4086_Quake:
.a16
.i16
    lda.l SourceUpdateFrame4086_Handle
    dec a
    asl a
    asl a
    sta.l SourceFrameEffectLeaf4086_QuakeOffset
    tax
    lda.l $43FB00,x
    sta.l SourceFrameEffectLeaf4086_CountLo
    lda.l $43FB02,x
    bpl SourceFrameEffectLeaf4086_QuakeCount
    jmp SourceFrameEffectLeaf4086_Bad
SourceFrameEffectLeaf4086_QuakeCount:
.a16
.i16
    sta.l SourceFrameEffectLeaf4086_CountHi
    lda.l SourceUpdateFrame4086_AnimationData
    clc
    adc #20
    tax
    jsr SourceUpdateFrame4086_Read
    sta.l SourceFrameEffectLeaf4086_StartLo
    inx
    inx
    jsr SourceUpdateFrame4086_Read
    sta.l SourceFrameEffectLeaf4086_StartHi
    inx
    inx
    jsr SourceUpdateFrame4086_Read
    sta.l SourceFrameEffectLeaf4086_RepeatLo
    inx
    inx
    jsr SourceUpdateFrame4086_Read
    sta.l SourceFrameEffectLeaf4086_RepeatHi
    inx
    inx
    jsr SourceUpdateFrame4086_Read
    sta.l SourceFrameEffectLeaf4086_ValueLo
    inx
    inx
    jsr SourceUpdateFrame4086_Read
    sta.l SourceFrameEffectLeaf4086_ValueHi
    lda.l SourceFrameEffectLeaf4086_StartLo
    clc
    adc.l SourceFrameEffectLeaf4086_CountLo
    sta.l SourceFrameEffectLeaf4086_NextLo
    lda.l SourceFrameEffectLeaf4086_StartHi
    adc.l SourceFrameEffectLeaf4086_CountHi
    bvc SourceFrameEffectLeaf4086_QuakeSum
    jmp SourceFrameEffectLeaf4086_Bad
SourceFrameEffectLeaf4086_QuakeSum:
.a16
.i16
    beq SourceFrameEffectLeaf4086_QuakeLow
    jmp SourceFrameEffectLeaf4086_Ack
SourceFrameEffectLeaf4086_QuakeLow:
.a16
.i16
    lda.l SourceFrameEffectLeaf4086_NextLo
    cmp.l SourceUpdateFrame4086_Request
    beq SourceFrameEffectLeaf4086_QuakeRepeat
    jmp SourceFrameEffectLeaf4086_Ack
SourceFrameEffectLeaf4086_QuakeRepeat:
.a16
.i16
    lda.l SourceFrameEffectLeaf4086_RepeatLo
    sec
    sbc.l SourceFrameEffectLeaf4086_CountLo
    sta.l SourceFrameEffectLeaf4086_NextLo
    lda.l SourceFrameEffectLeaf4086_RepeatHi
    sbc.l SourceFrameEffectLeaf4086_CountHi
    bvc SourceFrameEffectLeaf4086_QuakeDifference
    jmp SourceFrameEffectLeaf4086_Bad
SourceFrameEffectLeaf4086_QuakeDifference:
.a16
.i16
    bmi SourceFrameEffectLeaf4086_QuakeReset
    bne SourceFrameEffectLeaf4086_QuakeIncrement
    lda.l SourceFrameEffectLeaf4086_NextLo
    cmp #2
    bcc SourceFrameEffectLeaf4086_QuakeReset
SourceFrameEffectLeaf4086_QuakeIncrement:
.a16
.i16
    lda.l SourceFrameEffectLeaf4086_CountLo
    clc
    adc #1
    sta.l SourceFrameEffectLeaf4086_NextLo
    lda.l SourceFrameEffectLeaf4086_CountHi
    adc #0
    sta.l SourceFrameEffectLeaf4086_NextHi
    bra SourceFrameEffectLeaf4086_QuakeValue
SourceFrameEffectLeaf4086_QuakeReset:
.a16
.i16
    lda #0
    sta.l SourceFrameEffectLeaf4086_NextLo
    sta.l SourceFrameEffectLeaf4086_NextHi
SourceFrameEffectLeaf4086_QuakeValue:
.a16
.i16
    lda.l VmSourceWorld_Level
    beq SourceFrameEffectLeaf4086_QuakeStore
    lda.l SourceFrameEffectLeaf4086_CountLo
    and #1
    bne SourceFrameEffectLeaf4086_QuakeStore
    lda.l SourceFrameEffectLeaf4086_ValueHi
    bmi SourceFrameEffectLeaf4086_QuakeNegate
    ora.l SourceFrameEffectLeaf4086_ValueLo
    bne SourceFrameEffectLeaf4086_QuakeStore
SourceFrameEffectLeaf4086_QuakeNegate:
.a16
.i16
    lda #0
    sec
    sbc.l SourceFrameEffectLeaf4086_ValueLo
    sta.l SourceFrameEffectLeaf4086_ValueLo
    lda #0
    sbc.l SourceFrameEffectLeaf4086_ValueHi
    bvc SourceFrameEffectLeaf4086_QuakeNegated
    jmp SourceFrameEffectLeaf4086_Bad
SourceFrameEffectLeaf4086_QuakeNegated:
.a16
.i16
    sta.l SourceFrameEffectLeaf4086_ValueHi
SourceFrameEffectLeaf4086_QuakeStore:
.a16
.i16
    lda.l SourceFrameEffectLeaf4086_QuakeOffset
    tax
    lda.l SourceFrameEffectLeaf4086_NextLo
    sta.l $43FB00,x
    lda.l SourceFrameEffectLeaf4086_NextHi
    sta.l $43FB02,x
    lda.l VmSourceWorld_Level
    beq SourceFrameEffectLeaf4086_Ack
    lda.l SourceFrameEffectLeaf4086_ValueLo
    sta.l SourceFrameEffectLeaf4086_LevelQuakeLo
    lda.l SourceFrameEffectLeaf4086_ValueHi
    sta.l SourceFrameEffectLeaf4086_LevelQuakeHi
SourceFrameEffectLeaf4086_Ack:
.a16
.i16
    lda.l SourceFrameEffectPlan4086_Service
    sta.l SourceFrameEffectPlan4086_Acknowledged
    jsl SourceFrameEffectPlan4086_Ack
    bcc SourceFrameEffectLeaf4086_Done
    jmp SourceFrameEffectLeaf4086_Bad
SourceFrameEffectLeaf4086_Done:
.a16
.i16
    lda #1
    sta.l SourceFrameEffectLeaf4086_Status
    ply
    plx
    plp
    clc
    rtl
SourceFrameEffectLeaf4086_Bad:
.a16
.i16
    lda #2
    sta.l SourceFrameEffectLeaf4086_Status
    ply
    plx
    plp
    sec
    rtl
