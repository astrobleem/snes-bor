; Synchronous common_think dispatcher for the currently executable predicates.
; No fabricated service responses. Unbound true/grounded paths fail explicitly.
SourceCommonRun4086_Ready = $43BD52
SourceCommonRun4086_State = $43BD54 ; 0 idle,2 done,3 fault
SourceCommonRun4086_End = $43BD56
SourceCommonRun4086_Begin:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceCommonRun4086_Ready
 cmp #$B5E9
 bne SourceCommonRun4086_LongGuard1
 jmp SourceCommonRun4086_Lease
SourceCommonRun4086_LongGuard1:
.a16
.i16
 jmp SourceCommonRun4086_Bad
SourceCommonRun4086_Lease:
.a16
.i16
 lda.l SourceCommonRun4086_State
 bne SourceCommonRun4086_LongGuard2
 jmp SourceCommonRun4086_Start
SourceCommonRun4086_LongGuard2:
.a16
.i16
 cmp #2
 bne SourceCommonRun4086_LongGuard3
 jmp SourceCommonRun4086_Start
SourceCommonRun4086_LongGuard3:
.a16
.i16
 jmp SourceCommonRun4086_Bad
SourceCommonRun4086_Start:
.a16
.i16
 lda #0
 sta.l SourceCommonThink4086_State
 jsl SourceCommonThink4086_Begin
 bcs SourceCommonRun4086_LongGuard4
 jmp SourceCommonRun4086_Dispatch
SourceCommonRun4086_LongGuard4:
.a16
.i16
 jmp SourceCommonRun4086_Bad
SourceCommonRun4086_Dispatch:
.a16
.i16
 lda.l SourceCommonThink4086_State
 cmp #9
 bne SourceCommonRun4086_LongGuard5
 jmp SourceCommonRun4086_Done
SourceCommonRun4086_LongGuard5:
.a16
.i16
 cmp #1
 bcs SourceCommonRun4086_LongGuard6
 jmp SourceCommonRun4086_Bad
SourceCommonRun4086_LongGuard6:
.a16
.i16
 cmp #9
 bcc SourceCommonRun4086_LongGuard7
 jmp SourceCommonRun4086_Bad
SourceCommonRun4086_LongGuard7:
.a16
.i16
 lda #0
 sta.l SourceAIReadonly4086_Status
 jsl SourceAIReadonly4086_Execute
 bcc SourceCommonRun4086_LongGuard8
 jmp SourceCommonRun4086_Bad
SourceCommonRun4086_LongGuard8:
.a16
.i16
 lda.l SourceAIReadonly4086_Status
 cmp #1
 bne SourceCommonRun4086_LongGuard9
 jmp SourceCommonRun4086_Pending
SourceCommonRun4086_LongGuard9:
.a16
.i16
SourceCommonRun4086_Resume:
.a16
.i16
 lda.l SourceCommonThink4086_State
 jsl SourceCommonThink4086_Continue
 bcc SourceCommonRun4086_LongGuard10
 jmp SourceCommonRun4086_Bad
SourceCommonRun4086_LongGuard10:
.a16
.i16
 jmp SourceCommonRun4086_Dispatch
SourceCommonRun4086_Pending:
.a16
.i16
 lda #1
 sta.l SourceCommonRun4086_State
 ply
 plx
 plp
 clc
 rtl
SourceCommonRun4086_Continue:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceCommonRun4086_Ready
 cmp #$B5E9
 beq SourceCommonRun4086_LongGuard11
 jmp SourceCommonRun4086_Bad
SourceCommonRun4086_LongGuard11:
.a16
.i16
 lda.l SourceCommonRun4086_State
 cmp #1
 beq SourceCommonRun4086_LongGuard12
 jmp SourceCommonRun4086_Bad
SourceCommonRun4086_LongGuard12:
.a16
.i16
 jsl SourceAIReadonly4086_Continue
 bcc SourceCommonRun4086_LongGuard13
 jmp SourceCommonRun4086_Bad
SourceCommonRun4086_LongGuard13:
.a16
.i16
 jmp SourceCommonRun4086_Resume
SourceCommonRun4086_Done:
.a16
.i16
 lda #2
 sta.l SourceCommonRun4086_State
 lda #0
 ply
 plx
 plp
 clc
 rtl
SourceCommonRun4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceCommonRun4086_State
 ply
 plx
 plp
 sec
 rtl
