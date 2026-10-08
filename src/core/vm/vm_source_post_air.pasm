; B628 closed empty-geometry source POST with retained self across landing.
; A=0 complete; other A is the actual required landing/frame service ticket.
; State2 requires both complete gravity and complete movement. No world Ack.
; Exclusive with B61A stationary POST. New state follows B627 at $43FDC8.
SourcePostAir4086_Ready = $43FDC8
SourcePostAir4086_State = $43FDCA
SourcePostAir4086_Slot = $43FDCC
SourcePostAir4086_Service = $43FDCE
SourcePostAir4086_OldSelf = $43FDD0
SourcePostAir4086_Token = $43FDD4
SourcePostAir4086_Time = $43FDD8
SourcePostAir4086_End = $43FDDC

SourcePostAir4086_Begin:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourcePostAir4086_Ready
 cmp #$B628
 beq SourcePostAir4086_Lease
 jmp SourcePostAir4086_Bad
SourcePostAir4086_Lease:
.a16
.i16
 lda.l SourcePostAir4086_State
 beq SourcePostAir4086_Idle
 jmp SourcePostAir4086_Bad
SourcePostAir4086_Idle:
.a16
.i16
 lda.l SourcePostStationary4086_Ready
 beq SourcePostAir4086_Exclusive
 jmp SourcePostAir4086_Bad
SourcePostAir4086_Exclusive:
.a16
.i16
 jsr SourcePostAir4086_Context
 bcc SourcePostAir4086_ContextGood
 jmp SourcePostAir4086_Bad
SourcePostAir4086_ContextGood:
.a16
.i16
 lda.l SourceSelf4086_Ready
 cmp #$B4F6
 beq SourcePostAir4086_SelfLease
 jmp SourcePostAir4086_Bad
SourcePostAir4086_SelfLease:
.a16
.i16
 jsl SourceSelf4086_CheckIdle
 bcc SourcePostAir4086_SelfIdle
 jmp SourcePostAir4086_Bad
SourcePostAir4086_SelfIdle:
.a16
.i16
 lda.l SourceSelf4086_GlobalHigh
 beq SourcePostAir4086_SelfNull
 cmp #$41
 beq SourcePostAir4086_SelfMapped
 jmp SourcePostAir4086_Bad
SourcePostAir4086_SelfNull:
.a16
.i16
 lda.l SourceSelf4086_GlobalLow
 beq SourcePostAir4086_SaveSelf
 jmp SourcePostAir4086_Bad
SourcePostAir4086_SelfMapped:
.a16
.i16
 lda.l SourceSelf4086_GlobalLow
 cmp #$4000
 bcs SourcePostAir4086_SelfLower
 jmp SourcePostAir4086_Bad
SourcePostAir4086_SelfLower:
.a16
.i16
 cmp #$6800
 bcc SourcePostAir4086_SelfUpper
 jmp SourcePostAir4086_Bad
SourcePostAir4086_SelfUpper:
.a16
.i16
 sec
 sbc #$4000
 ldx #0
SourcePostAir4086_SelfSlot:
.a16
.i16
 cmp #80
 bcc SourcePostAir4086_SelfRemainder
 sec
 sbc #80
 inx
 bra SourcePostAir4086_SelfSlot
SourcePostAir4086_SelfRemainder:
.a16
.i16
 cmp #0
 beq SourcePostAir4086_SelfAligned
 jmp SourcePostAir4086_Bad
SourcePostAir4086_SelfAligned:
.a16
.i16
 txa
 cmp.l VmSourceWorld_Count
 bcc SourcePostAir4086_SaveSelf
 jmp SourcePostAir4086_Bad
SourcePostAir4086_SaveSelf:
.a16
.i16
 ; Reject stale subordinate ownership before borrowing the source global.
 lda.l SourceGravityAir4086_Status
 cmp #0
 beq SourcePostAir4086_GravityFresh
 cmp #2
 beq SourcePostAir4086_GravityFresh
 jmp SourcePostAir4086_Bad
SourcePostAir4086_GravityFresh:
.a16
.i16
 lda.l SourceCheckMove4086_Status
 cmp #0
 beq SourcePostAir4086_MoveFresh
 cmp #2
 beq SourcePostAir4086_MoveFresh
 jmp SourcePostAir4086_Bad
SourcePostAir4086_MoveFresh:
.a16
.i16
 lda.l SourceSelf4086_GlobalLow
 sta.l SourcePostAir4086_OldSelf
 lda.l SourceSelf4086_GlobalHigh
 sta.l SourcePostAir4086_OldSelf+2
 lda.l SourcePostAir4086_Slot
 asl a
 asl a
 asl a
 asl a
 tax
 asl a
 asl a
 sta.l SourcePostAir4086_Token
 txa
 clc
 adc.l SourcePostAir4086_Token
 clc
 adc #$4000
 sta.l SourcePostAir4086_Token
 sta.l SourceSelf4086_GlobalLow
 lda #$41
 sta.l SourcePostAir4086_Token+2
 sta.l SourceSelf4086_GlobalHigh
 lda.l VmSourceWorld_Time
 sta.l SourcePostAir4086_Time
 lda.l VmSourceWorld_Time+2
 sta.l SourcePostAir4086_Time+2
 lda #1
 sta.l SourcePostAir4086_State
 lda #0
 sta.l SourcePostAir4086_Service
 sta.l SourceGravityAir4086_Status
 sta.l SourceGravityAir4086_LandingNeeded
 sta.l SourceLandingVelocity4086_Status
 sta.l SourceGravityLanding4086_State
 sta.l SourceGravityLanding4086_Service
 sta.l SourceCheckMove4086_Status
 lda.l SourcePostAir4086_Slot
 sta.l SourceLandingVelocity4086_Slot
 sta.l SourceGravityLanding4086_Slot
 jsl SourceGravityAir4086_Execute
 bcc SourcePostAir4086_AirRan
 jmp SourcePostAir4086_RestoreBad
SourcePostAir4086_AirRan:
.a16
.i16
 lda.l SourceGravityAir4086_Status
 cmp #2
 bne SourcePostAir4086_AirNotComplete
 jmp SourcePostAir4086_Move
SourcePostAir4086_AirNotComplete:
.a16
.i16
 cmp #1
 beq SourcePostAir4086_Landing
 jmp SourcePostAir4086_RestoreBad
SourcePostAir4086_Landing:
.a16
.i16
 jsl SourceLandingVelocity4086_Execute
 bcc SourcePostAir4086_VelocityRan
 jmp SourcePostAir4086_RestoreBad
SourcePostAir4086_VelocityRan:
.a16
.i16
 lda #1
 sta.l SourcePostAir4086_Service
 jsl SourceGravityLanding4086_Begin
 bcc SourcePostAir4086_LandingStarted
 jmp SourcePostAir4086_RestoreBad
SourcePostAir4086_LandingStarted:
.a16
.i16
 jmp SourcePostAir4086_LandingProgress

SourcePostAir4086_Continue:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourcePostAir4086_Ready
 cmp #$B628
 beq SourcePostAir4086_ResumeLease
 jmp SourcePostAir4086_Bad
SourcePostAir4086_ResumeLease:
.a16
.i16
 lda.l SourcePostAir4086_State
 cmp #1
 beq SourcePostAir4086_ResumePending
 jmp SourcePostAir4086_Bad
SourcePostAir4086_ResumePending:
.a16
.i16
 jsr SourcePostAir4086_Context
 bcc SourcePostAir4086_ResumeContext
 jmp SourcePostAir4086_Bad
SourcePostAir4086_ResumeContext:
.a16
.i16
 lda.l VmSourceWorld_Time
 cmp.l SourcePostAir4086_Time
 beq SourcePostAir4086_ResumeTimeLow
 jmp SourcePostAir4086_Bad
SourcePostAir4086_ResumeTimeLow:
.a16
.i16
 lda.l VmSourceWorld_Time+2
 cmp.l SourcePostAir4086_Time+2
 beq SourcePostAir4086_ResumeTime
 jmp SourcePostAir4086_Bad
SourcePostAir4086_ResumeTime:
.a16
.i16
 lda.l SourcePostStationary4086_Ready
 beq SourcePostAir4086_ResumeExclusive
 jmp SourcePostAir4086_Bad
SourcePostAir4086_ResumeExclusive:
.a16
.i16
 lda.l SourceSelf4086_Ready
 cmp #$B4F6
 beq SourcePostAir4086_ResumeSelf
 jmp SourcePostAir4086_Bad
SourcePostAir4086_ResumeSelf:
.a16
.i16
 lda.l SourceSelf4086_Fault
 beq SourcePostAir4086_ResumeSelfValid
 jmp SourcePostAir4086_Bad
SourcePostAir4086_ResumeSelfValid:
.a16
.i16
 lda.l SourceSelf4086_Active
 beq SourcePostAir4086_ResumeParent
 cmp #1
 beq SourcePostAir4086_ResumeFrame
 jmp SourcePostAir4086_Bad
SourcePostAir4086_ResumeFrame:
.a16
.i16
 ; Nested script self belongs to the real captured landing frame.
 lda.l SourceGravityLanding4086_Service
 cmp #1
 beq SourcePostAir4086_ResumeFrameSlot
 jmp SourcePostAir4086_Bad
SourcePostAir4086_ResumeFrameSlot:
.a16
.i16
 lda.l SourceUpdateFrame4086_Slot
 cmp.l SourcePostAir4086_Slot
 beq SourcePostAir4086_ResumeService
 jmp SourcePostAir4086_Bad
SourcePostAir4086_ResumeParent:
.a16
.i16
 lda.l SourceSelf4086_GlobalLow
 cmp.l SourcePostAir4086_Token
 beq SourcePostAir4086_ResumeParentLow
 jmp SourcePostAir4086_Bad
SourcePostAir4086_ResumeParentLow:
.a16
.i16
 lda.l SourceSelf4086_GlobalHigh
 cmp.l SourcePostAir4086_Token+2
 beq SourcePostAir4086_ResumeService
 jmp SourcePostAir4086_Bad
SourcePostAir4086_ResumeService:
.a16
.i16
 lda.l SourcePostAir4086_Service
 cmp #1
 beq SourcePostAir4086_ResumeLanding
 jmp SourcePostAir4086_Bad
SourcePostAir4086_ResumeLanding:
.a16
.i16
 jsl SourceGravityLanding4086_Continue
 bcc SourcePostAir4086_LandingProgress
 jmp SourcePostAir4086_RestoreBad
SourcePostAir4086_LandingProgress:
.a16
.i16
 cmp #0
 beq SourcePostAir4086_Move
 jmp SourcePostAir4086_Return
SourcePostAir4086_Move:
.a16
.i16
 lda.l SourceGravityAir4086_Status
 cmp #2
 beq SourcePostAir4086_GravityDone
 jmp SourcePostAir4086_RestoreBad
SourcePostAir4086_GravityDone:
.a16
.i16
 jsl SourceSelf4086_CheckIdle
 bcc SourcePostAir4086_FrameIdle
 jmp SourcePostAir4086_Bad
SourcePostAir4086_FrameIdle:
.a16
.i16
 lda.l SourceSelf4086_GlobalLow
 cmp.l SourcePostAir4086_Token
 beq SourcePostAir4086_TokenLow
 jmp SourcePostAir4086_RestoreBad
SourcePostAir4086_TokenLow:
.a16
.i16
 lda.l SourceSelf4086_GlobalHigh
 cmp.l SourcePostAir4086_Token+2
 beq SourcePostAir4086_TokenHigh
 jmp SourcePostAir4086_RestoreBad
SourcePostAir4086_TokenHigh:
.a16
.i16
 jsl SourceCheckMove4086_Execute
 bcc SourcePostAir4086_MoveRan
 jmp SourcePostAir4086_RestoreBad
SourcePostAir4086_MoveRan:
.a16
.i16
 lda.l SourceCheckMove4086_Status
 cmp #2
 beq SourcePostAir4086_MoveDone
 jmp SourcePostAir4086_RestoreBad
SourcePostAir4086_MoveDone:
.a16
.i16
 jsr SourcePostAir4086_Restore
 lda #2
 sta.l SourcePostAir4086_State
 lda #0
 sta.l SourcePostAir4086_Service
SourcePostAir4086_Return:
.a16
.i16
 ply
 plx
 plp
 clc
 rtl
SourcePostAir4086_RestoreBad:
.a16
.i16
 ; A faulted frame still owns its snapshot. Retain parent ownership until
 ; its real unwind; never publish a fabricated restoration through it.
 jsl SourceSelf4086_CheckIdle
 bcs SourcePostAir4086_Bad
 jsr SourcePostAir4086_Restore
SourcePostAir4086_Bad:
.a16
.i16
 lda #3
 sta.l SourcePostAir4086_State
 ply
 plx
 plp
 sec
 rtl
SourcePostAir4086_Restore:
.a16
.i16
 lda.l SourcePostAir4086_OldSelf
 sta.l SourceSelf4086_GlobalLow
 lda.l SourcePostAir4086_OldSelf+2
 sta.l SourceSelf4086_GlobalHigh
 rts

SourcePostAir4086_Context:
.a16
.i16
 lda.l VmSourceWorld_PoolBase
 cmp #$4000
 beq SourcePostAir4086_ContextPool
 jmp SourcePostAir4086_ContextBad
SourcePostAir4086_ContextPool:
.a16
.i16
 lda.l VmSourceWorld_SideBase
 cmp #$6800
 beq SourcePostAir4086_ContextSide
 jmp SourcePostAir4086_ContextBad
SourcePostAir4086_ContextSide:
.a16
.i16
 lda.l VmSourceWorld_Ready
 cmp #$B4A3
 bne SourcePostAir4086_ContextBad
 lda.l SourceWorldTick4086_Ready
 cmp #$B4D5
 bne SourcePostAir4086_ContextBad
 lda.l SourceWorldTick4086_State
 cmp #2
 bne SourcePostAir4086_ContextBad
 lda.l SourceWorldTick4086_Phase
 cmp #11
 bne SourcePostAir4086_ContextBad
 lda.l SourceWorldTick4086_Pending
 cmp #1
 bne SourcePostAir4086_ContextBad
 lda.l SourceWorldTick4086_Fault
 bne SourcePostAir4086_ContextBad
 lda.l SourcePostAir4086_Slot
 cmp.l SourceWorldTick4086_Slot
 bne SourcePostAir4086_ContextBad
 cmp.l VmSourceWorld_Count
 bcs SourcePostAir4086_ContextBad
 lda.l VmSourceWorld_Count
 cmp #129
 bcs SourcePostAir4086_ContextBad
 lda.l SourceWorldTick4086_TimeLo
 cmp.l VmSourceWorld_Time
 bne SourcePostAir4086_ContextBad
 lda.l SourceWorldTick4086_TimeHi
 cmp.l VmSourceWorld_Time+2
 bne SourcePostAir4086_ContextBad
 clc
 rts
SourcePostAir4086_ContextBad:
.a16
.i16
 sec
 rts

; World service gate. Cold-disabled for existing static source profiles.
; A is preserved, no implicit execution or acknowledgement.
SourcePostAir4086_Issue:
.a16
.i16
 php
 rep #$38
 pha
 cmp #11
 beq SourcePostAir4086_IssuePost
 jmp SourcePostAir4086_ControlGood
SourcePostAir4086_IssuePost:
.a16
.i16
 lda.l SourcePostAir4086_Ready
 bne SourcePostAir4086_IssueEnabled
 jmp SourcePostAir4086_ControlGood
SourcePostAir4086_IssueEnabled:
.a16
.i16
 cmp #$B628
 beq SourcePostAir4086_IssueLease
 jmp SourcePostAir4086_ControlBad
SourcePostAir4086_IssueLease:
.a16
.i16
 lda.l SourcePostStationary4086_Ready
 bne SourcePostAir4086_ControlBad
 lda.l SourcePostAir4086_State
 cmp #0
 beq SourcePostAir4086_IssueFresh
 cmp #2
 bne SourcePostAir4086_ControlBad
SourcePostAir4086_IssueFresh:
.a16
.i16
 lda.l SourceWorldTick4086_Slot
 sta.l SourcePostAir4086_Slot
 lda #0
 sta.l SourcePostAir4086_State
 sta.l SourcePostAir4086_Service
 bra SourcePostAir4086_ControlGood
SourcePostAir4086_CheckAck:
.a16
.i16
 php
 rep #$38
 pha
 lda.l SourceWorldTick4086_Phase
 cmp #11
 bne SourcePostAir4086_ControlGood
 lda.l SourcePostAir4086_Ready
 beq SourcePostAir4086_ControlGood
 cmp #$B628
 bne SourcePostAir4086_ControlBad
 lda.l SourcePostAir4086_State
 cmp #2
 bne SourcePostAir4086_ControlBad
 lda.l SourcePostAir4086_Slot
 cmp.l SourceWorldTick4086_Slot
 bne SourcePostAir4086_ControlBad
 lda.l SourceGravityAir4086_Status
 cmp #2
 bne SourcePostAir4086_ControlBad
 lda.l SourceCheckMove4086_Status
 cmp #2
 bne SourcePostAir4086_ControlBad
 jsl SourceSelf4086_CheckIdle
 bcs SourcePostAir4086_ControlBad
 lda.l SourceSelf4086_GlobalLow
 cmp.l SourcePostAir4086_OldSelf
 bne SourcePostAir4086_ControlBad
 lda.l SourceSelf4086_GlobalHigh
 cmp.l SourcePostAir4086_OldSelf+2
 bne SourcePostAir4086_ControlBad
SourcePostAir4086_ControlGood:
.a16
.i16
 pla
 plp
 clc
 rtl
SourcePostAir4086_ControlBad:
.a16
.i16
 pla
 plp
 sec
 rtl
