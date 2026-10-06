; Foreground captured-frame effect driver, no new persistent scratch lease.
; Caller has completed SCRIPT and supplies pending update_frame service 2.
; A=0 complete; A=raw B4EP service means REQUIRED external continuation.
; C=1 fault. No external service is acknowledged by this driver. Caller must
; execute it, publish its exact Acknowledged ticket and call cursor Ack, or
; complete a model/init binding ticket,
; before resuming. All persistent state lives in the 528-byte frame snapshot.
; This does not grant foreign gameplay admission or implement external effects.
SourceFrameEffects4086_Run:
.a16
.i16
    php
    rep #$38
    phx
    phy
    lda.l SourceUpdateFrame4086_Ready
    cmp #$B4E3
    beq SourceFrameEffects4086_Branch_1
    jmp SourceFrameEffects4086_Bad
SourceFrameEffects4086_Branch_1:
.a16
.i16
    lda.l SourceUpdateFrame4086_State
    cmp #1
    beq SourceFrameEffects4086_Branch_2
    jmp SourceFrameEffects4086_Bad
SourceFrameEffects4086_Branch_2:
.a16
.i16
    lda.l SourceUpdateFrame4086_Pending
    cmp #2
    beq SourceFrameEffects4086_Branch_3
    jmp SourceFrameEffects4086_Bad
SourceFrameEffects4086_Branch_3:
.a16
.i16
    lda.l SourceFrameMotion4086_Status
    bne SourceFrameEffects4086_Branch_4
    jmp SourceFrameEffects4086_Motion
SourceFrameEffects4086_Branch_4:
.a16
.i16
    cmp #1
    beq SourceFrameEffects4086_Branch_5
    jmp SourceFrameEffects4086_Bad
SourceFrameEffects4086_Branch_5:
.a16
.i16
    jmp SourceFrameEffects4086_Plan
SourceFrameEffects4086_Motion:
.a16
.i16
    jsl SourceFrameMotion4086_Apply
    bcc SourceFrameEffects4086_Branch_6
    jmp SourceFrameEffects4086_Bad
SourceFrameEffects4086_Branch_6:
.a16
.i16
SourceFrameEffects4086_Plan:
.a16
.i16
    lda.l SourceFrameEffectPlan4086_State
    bne SourceFrameEffects4086_Branch_7
    jmp SourceFrameEffects4086_Start
SourceFrameEffects4086_Branch_7:
.a16
.i16
    cmp #1
    beq SourceFrameEffects4086_Branch_8
    jmp SourceFrameEffects4086_Bad
SourceFrameEffects4086_Branch_8:
.a16
.i16
    jmp SourceFrameEffects4086_Next
SourceFrameEffects4086_Start:
.a16
.i16
    jsl SourceFrameEffectPlan4086_Begin
    bcc SourceFrameEffects4086_Branch_9
    jmp SourceFrameEffects4086_Bad
SourceFrameEffects4086_Branch_9:
.a16
.i16
SourceFrameEffects4086_Next:
.a16
.i16
    jsr SourceFrameEffects4086_CheckTicket
    bcc SourceFrameEffects4086_TicketGood
    jmp SourceFrameEffects4086_Bad
SourceFrameEffects4086_TicketGood:
.a16
.i16
    lda.l SourceFrameEffectPlan4086_Service
    cmp #23
    bne SourceFrameEffects4086_Branch_10
    jmp SourceFrameEffects4086_Restore
SourceFrameEffects4086_Branch_10:
.a16
.i16
    cmp #17
    bne SourceFrameEffects4086_Branch_11
    jmp SourceFrameEffects4086_Leaf
SourceFrameEffects4086_Branch_11:
.a16
.i16
    cmp #19
    bne SourceFrameEffects4086_Branch_12
    jmp SourceFrameEffects4086_Leaf
SourceFrameEffects4086_Branch_12:
.a16
.i16
    cmp #22
    bne SourceFrameEffects4086_Branch_13
    jmp SourceFrameEffects4086_Leaf
SourceFrameEffects4086_Branch_13:
.a16
.i16
    cmp #2
    bne SourceFrameEffects4086_Branch_14
    jmp SourceFrameEffects4086_Binding
SourceFrameEffects4086_Branch_14:
.a16
.i16
    cmp #3
    bne SourceFrameEffects4086_Branch_15
    jmp SourceFrameEffects4086_Binding
SourceFrameEffects4086_Branch_15:
.a16
.i16
    cmp #4
    bne SourceFrameEffects4086_Branch_16
    jmp SourceFrameEffects4086_Binding
SourceFrameEffects4086_Branch_16:
.a16
.i16
    ; External operation: returned verbatim, cursor remains pending.
    jmp SourceFrameEffects4086_Return
SourceFrameEffects4086_Leaf:
.a16
.i16
    jsl SourceFrameEffectLeaf4086_Apply
    bcc SourceFrameEffects4086_Branch_17
    jmp SourceFrameEffects4086_Bad
SourceFrameEffects4086_Branch_17:
.a16
.i16
    jmp SourceFrameEffects4086_Next
SourceFrameEffects4086_Binding:
.a16
.i16
    lda.l SourceFrameEffectBinding4086_State
    bne SourceFrameEffects4086_Branch_18
    jmp SourceFrameEffects4086_BindingStart
SourceFrameEffects4086_Branch_18:
.a16
.i16
    cmp #1
    bne SourceFrameEffects4086_Branch_19
    jmp SourceFrameEffects4086_ModelPending
SourceFrameEffects4086_Branch_19:
.a16
.i16
    cmp #2
    beq SourceFrameEffects4086_Branch_20
    jmp SourceFrameEffects4086_Bad
SourceFrameEffects4086_Branch_20:
.a16
.i16
    lda.l SourceAnimationInit4086_State
    cmp #2
    bne SourceFrameEffects4086_Branch_21
    jmp SourceFrameEffects4086_BindingFinish
SourceFrameEffects4086_Branch_21:
.a16
.i16
    cmp #1
    beq SourceFrameEffects4086_InitWaiting
    jmp SourceFrameEffects4086_Bad
SourceFrameEffects4086_InitWaiting:
.a16
.i16
    jmp SourceFrameEffects4086_Yield
SourceFrameEffects4086_ModelPending:
.a16
.i16
    lda.l SourceModelTransition4086_State
    cmp #2
    bne SourceFrameEffects4086_Branch_22
    jmp SourceFrameEffects4086_BindingFinish
SourceFrameEffects4086_Branch_22:
.a16
.i16
    cmp #1
    beq SourceFrameEffects4086_ModelWaiting
    jmp SourceFrameEffects4086_Bad
SourceFrameEffects4086_ModelWaiting:
.a16
.i16
    jmp SourceFrameEffects4086_Yield
SourceFrameEffects4086_BindingStart:
.a16
.i16
    jsl SourceFrameEffectBinding4086_Begin
    bcc SourceFrameEffects4086_Branch_23
    jmp SourceFrameEffects4086_Bad
SourceFrameEffects4086_Branch_23:
.a16
.i16
    lda.l SourceFrameEffectBinding4086_State
    bne SourceFrameEffects4086_Branch_24
    jmp SourceFrameEffects4086_Next
SourceFrameEffects4086_Branch_24:
.a16
.i16
    jmp SourceFrameEffects4086_Yield
SourceFrameEffects4086_BindingFinish:
.a16
.i16
    jsl SourceFrameEffectBinding4086_Finish
    bcc SourceFrameEffects4086_Branch_25
    jmp SourceFrameEffects4086_Bad
SourceFrameEffects4086_Branch_25:
.a16
.i16
    jmp SourceFrameEffects4086_Next
SourceFrameEffects4086_Restore:
.a16
.i16
    jsl SourceSelf4086_RestoreEffect
    bcc SourceFrameEffects4086_Branch_26
    jmp SourceFrameEffects4086_Bad
SourceFrameEffects4086_Branch_26:
.a16
.i16
    lda #2
    jsl SourceUpdateFrame4086_Ack
    bcc SourceFrameEffects4086_Branch_27
    jmp SourceFrameEffects4086_Bad
SourceFrameEffects4086_Branch_27:
.a16
.i16
    lda #0
    jmp SourceFrameEffects4086_Return
SourceFrameEffects4086_Yield:
.a16
.i16
    lda.l SourceFrameEffectBinding4086_Issued
    cmp.l SourceFrameEffectPlan4086_Service
    beq SourceFrameEffects4086_YieldGood
    jmp SourceFrameEffects4086_Bad
SourceFrameEffects4086_YieldGood:
.a16
.i16
    lda.l SourceFrameEffectPlan4086_Service
SourceFrameEffects4086_Return:
.a16
.i16
    ply
    plx
    plp
    clc
    rtl
SourceFrameEffects4086_Bad:
.a16
.i16
    lda #3
    sta.l SourceUpdateFrame4086_State
    sta.l SourceFrameEffectPlan4086_State
    lda #1
    sta.l SourceUpdateFrame4086_Fault
    ply
    plx
    plp
    sec
    rtl

SourceFrameEffects4086_CheckTicket:
.a16
.i16
    lda.l SourceFrameMotion4086_Ready
    cmp #$B4E8
    bne SourceFrameEffects4086_TicketBad
    lda.l SourceSelf4086_Ready
    cmp #$B4F6
    bne SourceFrameEffects4086_TicketBad
    lda.l SourceSelf4086_Active
    cmp #1
    bne SourceFrameEffects4086_TicketBad
    lda.l SourceSelf4086_Fault
    bne SourceFrameEffects4086_TicketBad
    lda.l SourceFrameEffectPlan4086_Ready
    cmp #$B4F2
    bne SourceFrameEffects4086_TicketBad
    lda.l SourceFrameEffectPlan4086_State
    cmp #1
    bne SourceFrameEffects4086_TicketBad
    lda.l SourceFrameEffectPlan4086_Slot
    cmp.l SourceUpdateFrame4086_Slot
    bne SourceFrameEffects4086_TicketBad
    lda.l SourceFrameEffectPlan4086_Handle
    cmp.l SourceUpdateFrame4086_Handle
    bne SourceFrameEffects4086_TicketBad
    lda.l SourceFrameEffectPlan4086_Frame
    cmp.l SourceUpdateFrame4086_Request
    bne SourceFrameEffects4086_TicketBad
    lda.l SourceFrameEffectPlan4086_Count
    beq SourceFrameEffects4086_TicketBad
    cmp #33
    bcs SourceFrameEffects4086_TicketBad
    lda.l SourceFrameEffectPlan4086_Index
    cmp.l SourceFrameEffectPlan4086_Count
    bcs SourceFrameEffects4086_TicketBad
    jmp SourceFrameEffects4086_TicketBounds
SourceFrameEffects4086_TicketBad:
.a16
.i16
    sec
    rts
SourceFrameEffects4086_TicketBounds:
.a16
.i16
    lda.l SourceFrameEffectPlan4086_Bank
    cmp #64
    bcs SourceFrameEffects4086_TicketBad
    lda.l SourceFrameEffectPlan4086_Base
    cmp #$8000
    bcc SourceFrameEffects4086_TicketBad
    lda.l SourceFrameEffectPlan4086_Pool
    clc
    adc.l SourceFrameEffectPlan4086_Count
    bcs SourceFrameEffects4086_TicketBad
    cmp.l SourceFrameEffectPlan4086_Bytes
    bcc SourceFrameEffects4086_TicketSpan
    bne SourceFrameEffects4086_TicketBad
SourceFrameEffects4086_TicketSpan:
.a16
.i16
    dec a
    clc
    adc.l SourceFrameEffectPlan4086_Base
    bcs SourceFrameEffects4086_TicketBad
    lda.l SourceFrameEffectPlan4086_Index
    clc
    adc.l SourceFrameEffectPlan4086_Pool
    clc
    adc.l SourceFrameEffectPlan4086_Base
    tax
    jsr SourceFrameEffectPlan4086_ReadByte
    cmp.l SourceFrameEffectPlan4086_Service
    bne SourceFrameEffects4086_TicketBad
    cmp #2
    bcc SourceFrameEffects4086_TicketBad
    cmp #5
    bcc SourceFrameEffects4086_TicketOk
    cmp #7
    bcc SourceFrameEffects4086_TicketBad
    cmp #12
    bcc SourceFrameEffects4086_TicketOk
    cmp #15
    bcc SourceFrameEffects4086_TicketBad
    cmp #24
    bcs SourceFrameEffects4086_TicketBad
SourceFrameEffects4086_TicketOk:
.a16
.i16
    clc
    rts
