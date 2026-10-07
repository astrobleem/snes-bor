; Closed source execute_updateentity_script capability. B5SC v1 admits
; animation methods only: update_script is uninitialized. Validate the current
; model's immutable program row and full instance mask before completing.
; No initialized update callback is skipped; unsupported methods fail compile.
SourceUpdateScript4086_Ready = $43BCF6
SourceUpdateScript4086_Status = $43BCF8
SourceUpdateScript4086_End = $43BCFA
SourceUpdateScript4086_Execute:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceUpdateScript4086_Ready
 cmp #$B5E1
 beq SourceUpdateScript4086_Guard0
 jmp SourceUpdateScript4086_Bad
SourceUpdateScript4086_Guard0:
.a16
.i16
 lda.l SourceUpdateScript4086_Status
 cmp #0
 beq SourceUpdateScript4086_Guard1
 jmp SourceUpdateScript4086_Bad
SourceUpdateScript4086_Guard1:
.a16
.i16
 lda.l SourceWorldTick4086_Ready
 cmp #$B4D5
 beq SourceUpdateScript4086_Guard2
 jmp SourceUpdateScript4086_Bad
SourceUpdateScript4086_Guard2:
.a16
.i16
 lda.l SourceWorldTick4086_State
 cmp #1
 beq SourceUpdateScript4086_Guard3
 jmp SourceUpdateScript4086_Bad
SourceUpdateScript4086_Guard3:
.a16
.i16
 lda.l SourceWorldTick4086_Pending
 cmp #1
 beq SourceUpdateScript4086_Guard4
 jmp SourceUpdateScript4086_Bad
SourceUpdateScript4086_Guard4:
.a16
.i16
 lda.l SourceWorldTick4086_Phase
 cmp #5
 beq SourceUpdateScript4086_Guard5
 jmp SourceUpdateScript4086_Bad
SourceUpdateScript4086_Guard5:
.a16
.i16
 lda.l SourceWorldTick4086_TimeLo
 cmp.l VmSourceWorld_Time
 beq SourceUpdateScript4086_Guard6
 jmp SourceUpdateScript4086_Bad
SourceUpdateScript4086_Guard6:
.a16
.i16
 lda.l SourceWorldTick4086_TimeHi
 cmp.l VmSourceWorld_Time+2
 beq SourceUpdateScript4086_Guard7
 jmp SourceUpdateScript4086_Bad
SourceUpdateScript4086_Guard7:
.a16
.i16
 jsl SourceUpdateFrame4086_CheckIdle
 bcc SourceUpdateScript4086_FrameIdle
 jmp SourceUpdateScript4086_Bad
SourceUpdateScript4086_FrameIdle:
.a16
.i16
 lda.l SourceSelf4086_Ready
 cmp #$B4F6
 beq SourceUpdateScript4086_SelfLease
 jmp SourceUpdateScript4086_Bad
SourceUpdateScript4086_SelfLease:
.a16
.i16
 jsl SourceSelf4086_CheckIdle
 bcc SourceUpdateScript4086_SelfIdle
 jmp SourceUpdateScript4086_Bad
SourceUpdateScript4086_SelfIdle:
.a16
.i16
 lda.l SourceWorldTick4086_Slot
 sta.l SourceScriptClone4086_Slot
 asl a
 asl a
 asl a
 asl a
 asl a
 asl a
 tax
 lda.l $416800,x
 sta.l SourceScriptClone4086_Model
 jsl SourceScriptClone4086_CheckModelProgram
 bcc SourceUpdateScript4086_Metadata
 jmp SourceUpdateScript4086_Bad
SourceUpdateScript4086_Metadata:
.a16
.i16
 lda.l SourceScriptClone4086_Token
 cmp.l SourceSelf4086_GlobalLow
 beq SourceUpdateScript4086_SelfLow
 jmp SourceUpdateScript4086_Bad
SourceUpdateScript4086_SelfLow:
.a16
.i16
 lda.l SourceSelf4086_GlobalHigh
 cmp #$0041
 beq SourceUpdateScript4086_SelfHigh
 jmp SourceUpdateScript4086_Bad
SourceUpdateScript4086_SelfHigh:
.a16
.i16
 lda.l SourceScriptClone4086_Token
 tax
 lda.l $410004,x
 cmp #1
 beq SourceUpdateScript4086_Exists
 jmp SourceUpdateScript4086_Bad
SourceUpdateScript4086_Exists:
.a16
.i16
 lda.l $410006,x
 beq SourceUpdateScript4086_ExistsHigh
 jmp SourceUpdateScript4086_Bad
SourceUpdateScript4086_ExistsHigh:
.a16
.i16
 lda.l SourceScriptClone4086_Relation
 tax
 lda.l $40902C,x
 cmp.l SourceScriptClone4086_Mask
 beq SourceUpdateScript4086_Mask
 jmp SourceUpdateScript4086_Bad
SourceUpdateScript4086_Mask:
.a16
.i16
 lda.l $40902E,x
 beq SourceUpdateScript4086_Good
SourceUpdateScript4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceUpdateScript4086_Status
 ply
 plx
 plp
 sec
 rtl
SourceUpdateScript4086_Good:
.a16
.i16
 lda #2
 sta.l SourceUpdateScript4086_Status
 ply
 plx
 plp
 clc
 rtl
