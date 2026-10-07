; Generic constructor control owner before smartspawn overrides/onspawn.
; Four ticket bytes in verified frame-snapshot gaps, restored with the existing
; default-init slot/WALK ticket. Not callable inside a live script interpreter.
; Caller installs role/time/stage and body position inputs for the requested
; model before Begin. A=derived WALK ID, X/Y=checked B5DC current-stage context.
; A1 pending: execute actual StartFrame/callbacks/effects, then Continue.
; A0 completed: caller may return the chosen token (or EMPTY for null model).
; B503 time/JUMP and stage X/Y must be republished before each Continue.
SourceCtorOwner4086_Phase = $7FFCBC ; 0 idle,1 pending,2 done,3 fault
SourceCtorOwner4086_Model = $7FFCBE
SourceCtorOwner4086_Begin:
.a16
.i16
 php
 rep #$38
 phx
 phy
 pha
 lda.l SourceCtorOwner4086_Phase
 bne SourceCtorOwner4086_Guard_1
 jmp SourceCtorOwner4086_BeginIdle
SourceCtorOwner4086_Guard_1:
.a16
.i16
 cmp #2
 beq SourceCtorOwner4086_Guard_2
 jmp SourceCtorOwner4086_BeginBad
SourceCtorOwner4086_Guard_2:
.a16
.i16
SourceCtorOwner4086_BeginIdle:
.a16
.i16
 jsl SourceUpdateFrame4086_CheckIdle
 bcc SourceCtorOwner4086_Guard_3
 jmp SourceCtorOwner4086_BeginBad
SourceCtorOwner4086_Guard_3:
.a16
.i16
 jsl SourceAnimationInit4086_CheckIdle
 bcc SourceCtorOwner4086_Guard_4
 jmp SourceCtorOwner4086_BeginBad
SourceCtorOwner4086_Guard_4:
.a16
.i16
 lda.l SourceVMRun4086_Busy
 beq SourceCtorOwner4086_Guard_5
 jmp SourceCtorOwner4086_BeginBad
SourceCtorOwner4086_Guard_5:
.a16
.i16
 lda.l VmSourceCallback_Active
 beq SourceCtorOwner4086_Guard_6
 jmp SourceCtorOwner4086_BeginBad
SourceCtorOwner4086_Guard_6:
.a16
.i16
 lda.l VmState_Status
 and #$00FF
 cmp #VMSTAT_RUNNING
 bne SourceCtorOwner4086_NotRunning
 jmp SourceCtorOwner4086_BeginBad
SourceCtorOwner4086_NotRunning:
.a16
.i16
 cmp #VMSTAT_YIELDED
 bne SourceCtorOwner4086_NotYielded
 jmp SourceCtorOwner4086_BeginBad
SourceCtorOwner4086_NotYielded:
.a16
.i16
 cmp #VMSTAT_FAULT
 bne SourceCtorOwner4086_VmIdle
 jmp SourceCtorOwner4086_BeginBad
SourceCtorOwner4086_VmIdle:
.a16
.i16
 lda.l SourceDefaultInit4086_Phase
 beq SourceCtorOwner4086_DefaultIdle
 cmp #6
 beq SourceCtorOwner4086_DefaultIdle
 jmp SourceCtorOwner4086_BeginBad
SourceCtorOwner4086_DefaultIdle:
.a16
.i16
 lda.l SourceSpawnSlot4086_Model
 sta.l SourceCtorOwner4086_Model
 jsl SourceSpawnSlot4086_Select
 bcc SourceCtorOwner4086_Guard_7
 jmp SourceCtorOwner4086_BeginBad
SourceCtorOwner4086_Guard_7:
.a16
.i16
 lda.l SourceSpawnSlot4086_Slot
 sta.l SourceDefaultInit4086_OwnerSlot
 cmp #$FFFF
 bne SourceCtorOwner4086_Guard_8
 jmp SourceCtorOwner4086_Null
SourceCtorOwner4086_Guard_8:
.a16
.i16
 sta.l SourceScriptClone4086_Slot
 sta.l SourceDefaultChoice4086_Slot
 sta.l SourceDefaultPlayer4086_Slot
 lda.l SourceCtorOwner4086_Model
 sta.l SourceScriptClone4086_Model
 lda.l SourceSpawnSlot4086_NeedKill
 bne SourceCtorOwner4086_Guard_9
 jmp SourceCtorOwner4086_Cleanup
SourceCtorOwner4086_Guard_9:
.a16
.i16
 lda.l SourceSpawnSlot4086_Slot
 sta.l SourceRetirement4086_Slot
 jsl SourceRetirement4086_ApplyNoEvents
 bcc SourceCtorOwner4086_Guard_10
 jmp SourceCtorOwner4086_BeginBad
SourceCtorOwner4086_Guard_10:
.a16
.i16
SourceCtorOwner4086_Cleanup:
.a16
.i16
 jsl SourceScriptClone4086_Clear
 bcc SourceCtorOwner4086_Guard_11
 jmp SourceCtorOwner4086_BeginBad
SourceCtorOwner4086_Guard_11:
.a16
.i16
 jsl SourceFactors4086_Apply
 bcc SourceCtorOwner4086_Guard_12
 jmp SourceCtorOwner4086_BeginBad
SourceCtorOwner4086_Guard_12:
.a16
.i16
 lda #0
 sta.l SourceCtorState4086_Status
 jsl SourceCtorState4086_Begin
 bcc SourceCtorOwner4086_Guard_13
 jmp SourceCtorOwner4086_BeginBad
SourceCtorOwner4086_Guard_13:
.a16
.i16
 pla
 jsl SourceDefaultInit4086_Begin
 bcc SourceCtorOwner4086_Guard_14
 jmp SourceCtorOwner4086_Bad
SourceCtorOwner4086_Guard_14:
.a16
.i16
 cmp #1
 bne SourceCtorOwner4086_Guard_15
 jmp SourceCtorOwner4086_Pending
SourceCtorOwner4086_Guard_15:
.a16
.i16
 cmp #0
 beq SourceCtorOwner4086_Guard_16
 jmp SourceCtorOwner4086_Bad
SourceCtorOwner4086_Guard_16:
.a16
.i16
 jmp SourceCtorOwner4086_Done
SourceCtorOwner4086_Null:
.a16
.i16
 pla
 jmp SourceCtorOwner4086_Done
SourceCtorOwner4086_BeginBad:
.a16
.i16
 pla
 jmp SourceCtorOwner4086_Bad

SourceCtorOwner4086_Continue:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceCtorOwner4086_Phase
 cmp #1
 beq SourceCtorOwner4086_Guard_17
 jmp SourceCtorOwner4086_Bad
SourceCtorOwner4086_Guard_17:
.a16
.i16
 lda.l VmSourceWorld_Ready
 cmp #$B4A3
 beq SourceCtorOwner4086_ContinueWorld
 jmp SourceCtorOwner4086_Bad
SourceCtorOwner4086_ContinueWorld:
.a16
.i16
 lda.l VmSourceWorld_SideBase
 cmp #$6800
 beq SourceCtorOwner4086_ContinueSide
 jmp SourceCtorOwner4086_Bad
SourceCtorOwner4086_ContinueSide:
.a16
.i16
 lda.l SourceDefaultInit4086_OwnerSlot
 cmp.l VmSourceWorld_Count
 bcc SourceCtorOwner4086_ContinueCount
 jmp SourceCtorOwner4086_Bad
SourceCtorOwner4086_ContinueCount:
.a16
.i16
 cmp #128
 bcc SourceCtorOwner4086_ContinueSlot
 jmp SourceCtorOwner4086_Bad
SourceCtorOwner4086_ContinueSlot:
.a16
.i16
 phx
 asl a
 asl a
 asl a
 asl a
 asl a
 asl a
 tax
 lda.l $416800,x
 plx
 cmp.l SourceCtorOwner4086_Model
 beq SourceCtorOwner4086_ContinueModel
 jmp SourceCtorOwner4086_Bad
SourceCtorOwner4086_ContinueModel:
.a16
.i16
 ; Actual default-init owner checks matching completed frame-zero context,
 ; acknowledges it and advances the next real initializer service.
 jsl SourceDefaultInit4086_Continue
 bcc SourceCtorOwner4086_Guard_18
 jmp SourceCtorOwner4086_Bad
SourceCtorOwner4086_Guard_18:
.a16
.i16
 cmp #1
 bne SourceCtorOwner4086_Guard_19
 jmp SourceCtorOwner4086_Pending
SourceCtorOwner4086_Guard_19:
.a16
.i16
 cmp #0
 beq SourceCtorOwner4086_Guard_20
 jmp SourceCtorOwner4086_Bad
SourceCtorOwner4086_Guard_20:
.a16
.i16
SourceCtorOwner4086_Done:
.a16
.i16
 lda #2
 sta.l SourceCtorOwner4086_Phase
 lda #0
 ply
 plx
 plp
 clc
 rtl
SourceCtorOwner4086_Pending:
.a16
.i16
 lda #1
 sta.l SourceCtorOwner4086_Phase
 ply
 plx
 plp
 clc
 rtl
SourceCtorOwner4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceCtorOwner4086_Phase
 lda #0
 ply
 plx
 plp
 sec
 rtl
