; Generic actual update_frame callback/effects owner. No host acknowledgement.
; A=0 complete; $8001 source script/native continuation yielded; other A values
; are the actual B4EP external effect ticket. Caller executes required services.
; Uses only the existing captured frame and callback state; bank0 grows zero.
SourceFrameOwner4086_Run:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceUpdateFrame4086_Ready
 cmp #$B4E3
 beq SourceFrameOwner4086_Lease
 jmp SourceFrameOwner4086_Bad
SourceFrameOwner4086_Lease:
.a16
.i16
 lda.l SourceUpdateFrame4086_State
 cmp #2
 beq SourceFrameOwner4086_Completed
 cmp #1
 beq SourceFrameOwner4086_Active
 jmp SourceFrameOwner4086_Bad
SourceFrameOwner4086_Completed:
.a16
.i16
 lda.l SourceUpdateFrame4086_Pending
 beq SourceFrameOwner4086_CompletedIdle
 jmp SourceFrameOwner4086_Bad
SourceFrameOwner4086_CompletedIdle:
.a16
.i16
 jsl SourceSelf4086_CheckIdle
 bcc SourceFrameOwner4086_ReturnZero
 jmp SourceFrameOwner4086_Bad
SourceFrameOwner4086_Active:
.a16
.i16
 lda.l SourceUpdateFrame4086_Pending
 cmp #2
 beq SourceFrameOwner4086_Effects
 cmp #1
 beq SourceFrameOwner4086_Script
 jmp SourceFrameOwner4086_Bad
SourceFrameOwner4086_Script:
.a16
.i16
 lda.l SourceAnimationCallback4086_Ready
 cmp #$B4E6
 beq SourceFrameOwner4086_CallbackLease
 jmp SourceFrameOwner4086_Bad
SourceFrameOwner4086_CallbackLease:
.a16
.i16
 lda.l VmSourceCallback_Active
 cmp #$B4A6
 beq SourceFrameOwner4086_Resume
 cmp #0
 beq SourceFrameOwner4086_Begin
 jmp SourceFrameOwner4086_Bad
SourceFrameOwner4086_Begin:
.a16
.i16
 jsl SourceAnimationCallback4086_Begin
 bcs SourceFrameOwner4086_Bad
SourceFrameOwner4086_Resume:
.a16
.i16
 jsl SourceAnimationCallback4086_Run
SourceFrameOwner4086_AfterCallback:
.a16
.i16
 bcs SourceFrameOwner4086_Bad
 cmp #VMSTAT_YIELDED
 beq SourceFrameOwner4086_Yielded
 cmp #VMSTAT_DONE
 bne SourceFrameOwner4086_Bad
 lda #1
 jsl SourceUpdateFrame4086_Ack
 bcs SourceFrameOwner4086_Bad
 cmp #2
 bne SourceFrameOwner4086_Bad
SourceFrameOwner4086_Effects:
.a16
.i16
 jsl SourceFrameEffects4086_Run
 bcs SourceFrameOwner4086_Bad
 jmp SourceFrameOwner4086_Return
SourceFrameOwner4086_Yielded:
.a16
.i16
 lda #$8001
 jmp SourceFrameOwner4086_Return
SourceFrameOwner4086_ReturnZero:
.a16
.i16
 lda #0
SourceFrameOwner4086_Return:
.a16
.i16
 ply
 plx
 plp
 clc
 rtl
SourceFrameOwner4086_Bad:
.a16
.i16
 ply
 plx
 plp
 sec
 rtl
