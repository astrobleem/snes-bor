; B62C: source bounce sound admission; B62D proves pinned control_rumble empty.
; A successful sound start is asynchronous, as source sound_play_sample is.
; Busy is an uncompleted source service, never preemption or a fabricated Ack.
SourceBounceEffects4086_Ready = $7FBF06
SourceBounceEffects4086_State = $7FBF08
SourceBounceEffects4086_Slot = $7FBF0A
SourceBounceEffects4086_SampleFall = $7FBF0C
SourceBounceEffects4086_NoRumbleReady = $7FBF0E
SourceBounceEffects4086_Time = $7FBF10
SourceBounceEffects4086_End = $7FBF14
SourceBounceEffects4086_Execute:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceBounceEffects4086_Ready
 cmp #$B62C
 beq SourceBounceEffects4086_Lease
 jmp SourceBounceEffects4086_Bad
SourceBounceEffects4086_Lease:
.a16
.i16
 lda.l SourceBounceEffects4086_NoRumbleReady
 cmp #$B62D
 beq SourceBounceEffects4086_ControllerBound
 jmp SourceBounceEffects4086_Bad
SourceBounceEffects4086_ControllerBound:
.a16
.i16
 lda.l SourceGravityLanding4086_State
 cmp #1
 beq SourceBounceEffects4086_LandingOwned
 jmp SourceBounceEffects4086_Bad
SourceBounceEffects4086_LandingOwned:
.a16
.i16
 lda.l SourceGravityLanding4086_Service
 cmp #3
 beq SourceBounceEffects4086_ServiceOwned
 jmp SourceBounceEffects4086_Bad
SourceBounceEffects4086_ServiceOwned:
.a16
.i16
 jsr SourceGravityLanding4086_Context
 bcc SourceBounceEffects4086_ContextGood
 jmp SourceBounceEffects4086_Bad
SourceBounceEffects4086_ContextGood:
.a16
.i16
 lda.l SourceLandingVelocity4086_Ready
 cmp #$B626
 beq SourceBounceEffects4086_VelocityLease
 jmp SourceBounceEffects4086_Bad
SourceBounceEffects4086_VelocityLease:
.a16
.i16
 lda.l SourceLandingVelocity4086_Status
 cmp #1
 beq SourceBounceEffects4086_VelocityComplete
 jmp SourceBounceEffects4086_Bad
SourceBounceEffects4086_VelocityComplete:
.a16
.i16
 lda.l SourceLandingVelocity4086_Slot
 cmp.l SourceGravityLanding4086_Slot
 beq SourceBounceEffects4086_VelocitySlot
 jmp SourceBounceEffects4086_Bad
SourceBounceEffects4086_VelocitySlot:
.a16
.i16
 lda.l SourceBounceEffects4086_State
 beq SourceBounceEffects4086_Capture
 cmp #1
 beq SourceBounceEffects4086_Resume
 jmp SourceBounceEffects4086_Bad
SourceBounceEffects4086_Capture:
.a16
.i16
 lda.l SourceGravityLanding4086_Slot
 sta.l SourceBounceEffects4086_Slot
 lda.l VmSourceWorld_Time
 sta.l SourceBounceEffects4086_Time
 lda.l VmSourceWorld_Time+2
 sta.l SourceBounceEffects4086_Time+2
 lda #1
 sta.l SourceBounceEffects4086_State
SourceBounceEffects4086_Resume:
.a16
.i16
 lda.l SourceBounceEffects4086_Slot
 cmp.l SourceGravityLanding4086_Slot
 beq SourceBounceEffects4086_ResumeSlot
 jmp SourceBounceEffects4086_Bad
SourceBounceEffects4086_ResumeSlot:
.a16
.i16
 lda.l SourceBounceEffects4086_Time
 cmp.l VmSourceWorld_Time
 beq SourceBounceEffects4086_ResumeLow
 jmp SourceBounceEffects4086_Bad
SourceBounceEffects4086_ResumeLow:
.a16
.i16
 lda.l SourceBounceEffects4086_Time+2
 cmp.l VmSourceWorld_Time+2
 beq SourceBounceEffects4086_ResumeTime
 jmp SourceBounceEffects4086_Bad
SourceBounceEffects4086_ResumeTime:
.a16
.i16
 lda.l SourceBounceEffects4086_SampleFall
 cmp #$FFFF
 beq SourceBounceEffects4086_Done
 ora #0
 bmi SourceBounceEffects4086_Bad
 jsl SourceAudio_Start
 bcc SourceBounceEffects4086_Done
 lda.l SourceAudio_Status
 cmp #3
 bne SourceBounceEffects4086_Bad
 lda #$8103
 jmp SourceBounceEffects4086_Return
SourceBounceEffects4086_Done:
.a16
.i16
 ; Pinned SDL control_rumble has an empty body for every port/msec argument.
 ; Its optional player call and four-port loop have no observable effect.
 lda #2
 sta.l SourceBounceEffects4086_State
 lda #0
SourceBounceEffects4086_Return:
.a16
.i16
 ply
 plx
 plp
 clc
 rtl
SourceBounceEffects4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceBounceEffects4086_State
 ply
 plx
 plp
 sec
 rtl
