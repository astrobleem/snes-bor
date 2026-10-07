; Complete admitted scroller invocation with explicit constructor handoff.
; Queue constructors/properties/music are real external services, never skipped.
; Begin/Continue return A=1 pending constructor, A=0 invocation done; C=fault.
; No input, AI, combat, rendering or full-world-tick certificate is implied.
SourceScrollerOwner4086_Ready = $43BC4A
SourceScrollerOwner4086_State = $43BC4C
SourceScrollerOwner4086_Time = $43BC4E
SourceScrollerOwner4086_End = $43BC52
SourceScrollerOwner4086_Begin:
.a16
.i16
 php
 rep #$38
 phx
 phy
 jsr SourceScrollerOwner4086_CheckLease
 bcc SourceScrollerOwner4086_BeginLease
 jmp SourceScrollerOwner4086_Bad
SourceScrollerOwner4086_BeginLease:
.a16
.i16
 lda.l SourceScrollerOwner4086_State
 beq SourceScrollerOwner4086_PreviousDone
 cmp #4
 beq SourceScrollerOwner4086_PreviousDone
 jmp SourceScrollerOwner4086_Bad
SourceScrollerOwner4086_PreviousDone:
.a16
.i16
 lda.l SourceCtorOwner4086_Phase
 beq SourceScrollerOwner4086_PreviousCtor
 cmp #2
 beq SourceScrollerOwner4086_PreviousCtor
 jmp SourceScrollerOwner4086_Bad
SourceScrollerOwner4086_PreviousCtor:
.a16
.i16
 lda.l SourceDefaultInit4086_Phase
 beq SourceScrollerOwner4086_PreviousDefault
 cmp #6
 beq SourceScrollerOwner4086_PreviousDefault
 jmp SourceScrollerOwner4086_Bad
SourceScrollerOwner4086_PreviousDefault:
.a16
.i16
 lda.l SourceSmartSpawn4086_Status
 beq SourceScrollerOwner4086_PreviousProperties
 cmp #2
 beq SourceScrollerOwner4086_PreviousProperties
 jmp SourceScrollerOwner4086_Bad
SourceScrollerOwner4086_PreviousProperties:
.a16
.i16
 lda.l VmSourceWorld_Time
 sta.l SourceScrollerOwner4086_Time
 lda.l VmSourceWorld_Time+2
 sta.l SourceScrollerOwner4086_Time+2
 jsl SourceScrollerPrefix4086_Begin
 bcc SourceScrollerOwner4086_PrefixOK
 jmp SourceScrollerOwner4086_Bad
SourceScrollerOwner4086_PrefixOK:
.a16
.i16
 cmp #0
 bne SourceScrollerOwner4086_ContinuePrefix
 ; The source returned before WAIT or camera. State 4 means skipped here,
 ; distinct from service state 2 (executed). Clock admission must check prefix.
 lda #4
 sta.l SourceWait4086_Status
 sta.l SourceCameraMotion4086_Status
 jmp SourceScrollerOwner4086_Done
SourceScrollerOwner4086_ContinuePrefix:
.a16
.i16
 lda #0
 sta.l SourceWait4086_Status
 sta.l SourceCameraMotion4086_Status
 jsl SourceStageCompletion4086_Check
 bcc SourceScrollerOwner4086_CompletionOK
 jmp SourceScrollerOwner4086_Bad
SourceScrollerOwner4086_CompletionOK:
.a16
.i16
 jmp SourceScrollerOwner4086_Next
SourceScrollerOwner4086_Continue:
.a16
.i16
 php
 rep #$38
 phx
 phy
 jsr SourceScrollerOwner4086_CheckLease
 bcc SourceScrollerOwner4086_ContinueLease
 jmp SourceScrollerOwner4086_Bad
SourceScrollerOwner4086_ContinueLease:
.a16
.i16
 lda.l SourceScrollerOwner4086_State
 cmp #1
 beq SourceScrollerOwner4086_Handoff
 jmp SourceScrollerOwner4086_Bad
SourceScrollerOwner4086_Handoff:
.a16
.i16
 lda.l VmSourceWorld_Time
 cmp.l SourceScrollerOwner4086_Time
 beq SourceScrollerOwner4086_TimeLow
 jmp SourceScrollerOwner4086_Bad
SourceScrollerOwner4086_TimeLow:
.a16
.i16
 lda.l VmSourceWorld_Time+2
 cmp.l SourceScrollerOwner4086_Time+2
 beq SourceScrollerOwner4086_TimePaired
 jmp SourceScrollerOwner4086_Bad
SourceScrollerOwner4086_TimePaired:
.a16
.i16
 jsl SourceStageProducer4086_AckSpawn
 bcc SourceScrollerOwner4086_Next
 jmp SourceScrollerOwner4086_Bad
SourceScrollerOwner4086_Next:
.a16
.i16
 jsl SourceStageProducer4086_Next
 bcc SourceScrollerOwner4086_QueueOK
 jmp SourceScrollerOwner4086_Bad
SourceScrollerOwner4086_QueueOK:
.a16
.i16
 cmp #0
 beq SourceScrollerOwner4086_QueueDone
 cmp #1
 beq SourceScrollerOwner4086_Request
 jmp SourceScrollerOwner4086_Bad
SourceScrollerOwner4086_Request:
.a16
.i16
 lda #1
 sta.l SourceScrollerOwner4086_State
 bra SourceScrollerOwner4086_Return
SourceScrollerOwner4086_QueueDone:
.a16
.i16
 jsl SourceWait4086_Release
 bcc SourceScrollerOwner4086_WaitDone
 jmp SourceScrollerOwner4086_Bad
SourceScrollerOwner4086_WaitDone:
.a16
.i16
 jsl SourceCameraBounds4086_Collect
 bcc SourceScrollerOwner4086_BoundsDone
 jmp SourceScrollerOwner4086_Bad
SourceScrollerOwner4086_BoundsDone:
.a16
.i16
 jsl SourceCameraMotion4086_Move
 bcc SourceScrollerOwner4086_Done
 jmp SourceScrollerOwner4086_Bad
SourceScrollerOwner4086_Done:
.a16
.i16
 lda #4
 sta.l SourceScrollerOwner4086_State
 lda #0
SourceScrollerOwner4086_Return:
.a16
.i16
 ply
 plx
 plp
 clc
 rtl
SourceScrollerOwner4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceScrollerOwner4086_State
 sta.l SourceStageProducer4086_State
 ply
 plx
 plp
 sec
 rtl
SourceScrollerOwner4086_CheckLease:
.a16
.i16
 lda.l SourceScrollerOwner4086_Ready
 cmp #$B5DD
 bne SourceScrollerOwner4086_LeaseBad
 lda.l SourceWait4086_Ready
 cmp #$B5D9
 bne SourceScrollerOwner4086_LeaseBad
 lda.l SourceCameraBounds4086_Ready
 cmp #$B5DA
 bne SourceScrollerOwner4086_LeaseBad
 lda.l SourceCameraMotion4086_Ready
 cmp #$B5DB
 bne SourceScrollerOwner4086_LeaseBad
 clc
 rts
SourceScrollerOwner4086_LeaseBad:
.a16
.i16
 sec
 rts
