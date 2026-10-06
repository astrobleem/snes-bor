; Engine-global BOR self, separate from script-local VmNativeVariant_Self.
; B4F6 admits NULL or aligned physical entity tokens in the $414000 pool.
; Low-word saving is lossless in this admitted pointer domain. Ticket occupies
; unused model-transition words within the 528-byte nested frame snapshot.
SourceSelf4086_OldLow = $7FFD1A
SourceSelf4086_Active = $7FFD1C
SourceSelf4086_Fault = $7FFD1E
SourceSelf4086_SuspendLow = $7FFD5E ; cursor pool-end scratch is dead while pending
SourceSelf4086_Ready = $7FFE36
SourceSelf4086_GlobalLow = $7FFE38
SourceSelf4086_GlobalHigh = $7FFE3A

SourceSelf4086_CheckIdle:
.a16
.i16
    php
    rep #$38
    pha
    lda.l SourceSelf4086_Ready
    beq SourceSelf4086_IdleGood
    cmp #$B4F6
    bne SourceSelf4086_IdleBad
    lda.l SourceSelf4086_Active
    ora.l SourceSelf4086_Fault
    bne SourceSelf4086_IdleBad
SourceSelf4086_IdleGood:
.a16
.i16
    pla
    plp
    clc
    rtl
SourceSelf4086_IdleBad:
.a16
.i16
    pla
    plp
    sec
    rtl

SourceSelf4086_ValidateLow:
.a16
.i16
    pha
    lda.l VmSourceWorld_Ready
    cmp #$B4A3
    bne SourceSelf4086_LowBad
    lda.l VmSourceWorld_PoolBase
    cmp #$4000
    bne SourceSelf4086_LowBad
    lda.l VmSourceWorld_Count
    beq SourceSelf4086_LowBad
    cmp #129
    bcs SourceSelf4086_LowBad
    pla
    beq SourceSelf4086_LowGood
    cmp #$4000
    bcc SourceSelf4086_LowReject
    cmp #$6800
    bcs SourceSelf4086_LowReject
    sec
    sbc #$4000
    ldx #0
SourceSelf4086_LowSlot:
.a16
.i16
    cmp #80
    bcc SourceSelf4086_LowRemainder
    sec
    sbc #80
    inx
    bra SourceSelf4086_LowSlot
SourceSelf4086_LowRemainder:
.a16
.i16
    ora #0
    bne SourceSelf4086_LowReject
    txa
    cmp.l VmSourceWorld_Count
    bcs SourceSelf4086_LowReject
SourceSelf4086_LowGood:
.a16
.i16
    clc
    rts
SourceSelf4086_LowBad:
.a16
.i16
    pla
SourceSelf4086_LowReject:
.a16
.i16
    sec
    rts

SourceSelf4086_Enter:
.a16
.i16
    php
    rep #$38
    phx
    phy
    lda.l SourceSelf4086_Ready
    beq SourceSelf4086_EnterDisabled
    cmp #$B4F6
    beq SourceSelf4086_EnterIdle
    jmp SourceSelf4086_Bad
SourceSelf4086_EnterDisabled:
.a16
.i16
    jmp SourceSelf4086_Good
SourceSelf4086_EnterIdle:
.a16
.i16
    lda.l SourceSelf4086_Active
    ora.l SourceSelf4086_Fault
    beq SourceSelf4086_EnterHigh
    jmp SourceSelf4086_Bad
SourceSelf4086_EnterHigh:
.a16
.i16
    lda.l SourceSelf4086_GlobalHigh
    cmp #$41
    beq SourceSelf4086_EnterMapped
    ora.l SourceSelf4086_GlobalLow
    beq SourceSelf4086_EnterLow
    jmp SourceSelf4086_Bad
SourceSelf4086_EnterMapped:
.a16
.i16
    lda.l SourceSelf4086_GlobalLow
    bne SourceSelf4086_EnterLow
    jmp SourceSelf4086_Bad
SourceSelf4086_EnterLow:
.a16
.i16
    lda.l SourceSelf4086_GlobalLow
    jsr SourceSelf4086_ValidateLow
    bcc SourceSelf4086_EnterSlot
    jmp SourceSelf4086_Bad
SourceSelf4086_EnterSlot:
.a16
.i16
    lda.l SourceUpdateFrame4086_Slot
    cmp.l VmSourceWorld_Count
    bcc SourceSelf4086_EnterPublish
    jmp SourceSelf4086_Bad
SourceSelf4086_EnterPublish:
.a16
.i16
    lda.l SourceSelf4086_GlobalLow
    sta.l SourceSelf4086_OldLow
    lda.l SourceUpdateFrame4086_Slot
    asl a
    asl a
    asl a
    asl a
    tax
    asl a
    asl a
    sta.l SourceSelf4086_GlobalLow
    txa
    clc
    adc.l SourceSelf4086_GlobalLow
    clc
    adc #$4000
    sta.l SourceSelf4086_GlobalLow
    lda #$41
    sta.l SourceSelf4086_GlobalHigh
    lda #1
    sta.l SourceSelf4086_Active
    jmp SourceSelf4086_Good

SourceSelf4086_Leave:
.a16
.i16
    php
    rep #$38
    phx
    phy
    lda.l SourceSelf4086_Ready
    beq SourceSelf4086_LeaveDisabled
    cmp #$B4F6
    beq SourceSelf4086_LeaveFault
    jmp SourceSelf4086_Bad
SourceSelf4086_LeaveDisabled:
.a16
.i16
    jmp SourceSelf4086_Good
SourceSelf4086_LeaveFault:
.a16
.i16
    lda.l SourceSelf4086_Fault
    beq SourceSelf4086_LeaveActive
    jmp SourceSelf4086_Bad
SourceSelf4086_LeaveActive:
.a16
.i16
    lda.l SourceSelf4086_Active
    beq SourceSelf4086_LeaveDisabled
    cmp #1
    beq SourceSelf4086_LeaveValidate
    jmp SourceSelf4086_Bad
SourceSelf4086_LeaveValidate:
.a16
.i16
    lda.l SourceSelf4086_OldLow
    jsr SourceSelf4086_ValidateLow
    bcc SourceSelf4086_LeaveRestore
    jmp SourceSelf4086_Bad
SourceSelf4086_LeaveRestore:
.a16
.i16
    lda.l SourceSelf4086_OldLow
    sta.l SourceSelf4086_GlobalLow
    beq SourceSelf4086_LeaveNull
    lda #$41
SourceSelf4086_LeaveNull:
.a16
.i16
    sta.l SourceSelf4086_GlobalHigh
    lda #0
    sta.l SourceSelf4086_Active
SourceSelf4086_Good:
.a16
.i16
    ply
    plx
    plp
    clc
    rtl
SourceSelf4086_Bad:
.a16
.i16
    lda #1
    sta.l SourceSelf4086_Fault
    ply
    plx
    plp
    sec
    rtl

SourceSelf4086_RestoreEffect:
.a16
.i16
    php
    rep #$38
    phx
    phy
    lda.l SourceSelf4086_Ready
    cmp #$B4F6
    beq SourceSelf4086_RestoreLease
    jmp SourceSelf4086_RestoreBad
SourceSelf4086_RestoreLease:
.a16
.i16
    lda.l SourceSelf4086_Active
    cmp #1
    beq SourceSelf4086_RestoreActive
    jmp SourceSelf4086_RestoreBad
SourceSelf4086_RestoreActive:
.a16
.i16
    lda.l SourceSelf4086_Fault
    bne SourceSelf4086_RestoreBad
    lda.l SourceUpdateFrame4086_Ready
    cmp #$B4E3
    bne SourceSelf4086_RestoreBad
    lda.l SourceUpdateFrame4086_State
    cmp #1
    bne SourceSelf4086_RestoreBad
    lda.l SourceUpdateFrame4086_Pending
    cmp #2
    bne SourceSelf4086_RestoreBad
    lda.l SourceFrameEffectPlan4086_Ready
    cmp #$B4F2
    bne SourceSelf4086_RestoreBad
    lda.l SourceFrameEffectPlan4086_State
    cmp #1
    bne SourceSelf4086_RestoreBad
    lda.l SourceFrameEffectPlan4086_Service
    cmp #23
    bne SourceSelf4086_RestoreBad
    lda.l SourceFrameEffectPlan4086_Slot
    cmp.l SourceUpdateFrame4086_Slot
    bne SourceSelf4086_RestoreBad
    lda.l SourceFrameEffectPlan4086_Handle
    cmp.l SourceUpdateFrame4086_Handle
    bne SourceSelf4086_RestoreBad
    lda.l SourceFrameEffectPlan4086_Frame
    cmp.l SourceUpdateFrame4086_Request
    bne SourceSelf4086_RestoreBad
    lda.l SourceFrameEffectPlan4086_Index
    cmp #32
    bcs SourceSelf4086_RestoreBad
    inc a
    cmp.l SourceFrameEffectPlan4086_Count
    bne SourceSelf4086_RestoreBad
    jsl SourceSelf4086_Leave
    bcs SourceSelf4086_RestoreBad
    lda #23
    sta.l SourceFrameEffectPlan4086_Acknowledged
    jsl SourceFrameEffectPlan4086_Ack
    bcs SourceSelf4086_RestoreBad
    jmp SourceSelf4086_Good
SourceSelf4086_RestoreBad:
.a16
.i16
    lda #3
    sta.l SourceFrameEffectPlan4086_State
    jmp SourceSelf4086_Bad

; The suspended context may deliberately be another entity (e.g. unsummon
; damage), so do not infer it from the parent's captured frame slot.
SourceSelf4086_Suspend:
.a16
.i16
    php
    rep #$38
    phx
    phy
    lda.l SourceSelf4086_Ready
    beq SourceSelf4086_SuspendDisabled
    cmp #$B4F6
    beq SourceSelf4086_SuspendActive
    jmp SourceSelf4086_Bad
SourceSelf4086_SuspendDisabled:
.a16
.i16
    jmp SourceSelf4086_Good
SourceSelf4086_SuspendActive:
.a16
.i16
    lda.l SourceSelf4086_Fault
    bne SourceSelf4086_SuspendBad
    lda.l SourceSelf4086_Active
    cmp #1
    bne SourceSelf4086_SuspendBad
    lda.l SourceSelf4086_GlobalHigh
    cmp #$41
    beq SourceSelf4086_SuspendMapped
    ora.l SourceSelf4086_GlobalLow
    beq SourceSelf4086_SuspendValidate
    bra SourceSelf4086_SuspendBad
SourceSelf4086_SuspendMapped:
.a16
.i16
    lda.l SourceSelf4086_GlobalLow
    beq SourceSelf4086_SuspendBad
SourceSelf4086_SuspendValidate:
.a16
.i16
    lda.l SourceSelf4086_GlobalLow
    jsr SourceSelf4086_ValidateLow
    bcs SourceSelf4086_SuspendBad
    lda.l SourceSelf4086_GlobalLow
    sta.l SourceSelf4086_SuspendLow
    jmp SourceSelf4086_Good
SourceSelf4086_SuspendBad:
.a16
.i16
    jmp SourceSelf4086_Bad

; X is the selected $40F000 frame row. Check before restoring any snapshot.
SourceSelf4086_CheckResume:
.a16
.i16
    php
    rep #$38
    phx
    phy
    lda.l SourceSelf4086_Ready
    beq SourceSelf4086_ResumeDisabled
    cmp #$B4F6
    beq SourceSelf4086_ResumeIdle
    jmp SourceSelf4086_Bad
SourceSelf4086_ResumeDisabled:
.a16
.i16
    jmp SourceSelf4086_Good
SourceSelf4086_ResumeIdle:
.a16
.i16
    jsl SourceSelf4086_CheckIdle
    bcs SourceSelf4086_ResumeBad
    lda.l $4001CC,x
    cmp #1
    bne SourceSelf4086_ResumeBad
    lda.l $4001CE,x
    bne SourceSelf4086_ResumeBad
    phx
    lda.l SourceFrameStack4086_TailRow
    tax
    lda.l $43000E,x
    plx
    cmp.l SourceSelf4086_GlobalLow
    bne SourceSelf4086_ResumeBad
    beq SourceSelf4086_ResumeHigh
SourceSelf4086_ResumeHigh:
.a16
.i16
    cmp #0
    beq SourceSelf4086_ResumeNull
    lda.l SourceSelf4086_GlobalHigh
    cmp #$41
    bne SourceSelf4086_ResumeBad
    bra SourceSelf4086_ResumeValidate
SourceSelf4086_ResumeNull:
.a16
.i16
    lda.l SourceSelf4086_GlobalHigh
    bne SourceSelf4086_ResumeBad
SourceSelf4086_ResumeValidate:
.a16
.i16
    phx
    lda.l SourceFrameStack4086_TailRow
    tax
    lda.l $43000E,x
    jsr SourceSelf4086_ValidateLow
    plx
    bcs SourceSelf4086_ResumeBad
    lda.l $4001CA,x
    jsr SourceSelf4086_ValidateLow
    bcs SourceSelf4086_ResumeBad
    jmp SourceSelf4086_Good
SourceSelf4086_ResumeBad:
.a16
.i16
    jmp SourceSelf4086_Bad
