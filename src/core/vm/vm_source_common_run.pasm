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
 beq SourceCommonRun4086_Lease
 jmp SourceCommonRun4086_Bad
SourceCommonRun4086_Lease:
.a16
.i16
 lda.l SourceCommonRun4086_State
 beq SourceCommonRun4086_Start
 cmp #2
 beq SourceCommonRun4086_Start
 jmp SourceCommonRun4086_Bad
SourceCommonRun4086_Start:
.a16
.i16
 lda #0
 sta.l SourceCommonThink4086_State
 jsl SourceCommonThink4086_Begin
 bcc SourceCommonRun4086_Dispatch
 jmp SourceCommonRun4086_Bad
SourceCommonRun4086_Dispatch:
.a16
.i16
 lda.l SourceCommonThink4086_State
 cmp #9
 beq SourceCommonRun4086_Done
 cmp #1
 bcc SourceCommonRun4086_Bad
 cmp #9
 bcs SourceCommonRun4086_Bad
 lda #0
 sta.l SourceAIReadonly4086_Status
 jsl SourceAIReadonly4086_Execute
 bcs SourceCommonRun4086_Bad
 lda.l SourceCommonThink4086_State
 jsl SourceCommonThink4086_Continue
 bcs SourceCommonRun4086_Bad
 bra SourceCommonRun4086_Dispatch
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
