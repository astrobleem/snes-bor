; Closed animation-only script descriptor proves think_script uninitialized.
; Source calls this after think even if think retires the actor. Empty/animation
; masks are valid; another initialized method is an explicit admission fault.
SourceAI4086_ThinkScriptAbsent:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceAI4086_State
 cmp #3
 beq SourceAIRun4086_Far1
 jmp SourceAI4086_ThinkScriptBad
SourceAIRun4086_Far1:
.a16
.i16
 jsl SourceAI4086_CheckOwner
 bcc SourceAIRun4086_Far2
 jmp SourceAI4086_ThinkScriptBad
SourceAIRun4086_Far2:
.a16
.i16
 lda.l SourceAI4086_Slot
 sta.l SourceScriptClone4086_Slot
 lda.l SourceAI4086_Side
 tax
 lda.l $416800,x
 sta.l SourceScriptClone4086_Model
 jsl SourceScriptClone4086_CheckModelProgram
 bcc SourceAIRun4086_Far3
 jmp SourceAI4086_ThinkScriptBad
SourceAIRun4086_Far3:
.a16
.i16
 lda.l SourceScriptClone4086_Relation
 tax
 lda.l $40902C,x
 cmp #2
 bcc SourceAIRun4086_Far4
 jmp SourceAI4086_ThinkScriptBad
SourceAIRun4086_Far4:
.a16
.i16
 lda.l $40902E,x
 beq SourceAIRun4086_Far5
 jmp SourceAI4086_ThinkScriptBad
SourceAIRun4086_Far5:
.a16
.i16
 ply
 plx
 plp
 clc
 rtl
SourceAI4086_ThinkScriptBad:
.a16
.i16
 ply
 plx
 plp
 sec
 rtl

; Actual generic callback dispatcher. A=1 requires real frame-zero execution.
; Continue acknowledges that frame through the actual animation owner, then
; resumes check_ai. Unbound action/think identities fault, never a no-op.
SourceAIRun4086_Ready = $43BD38
SourceAIRun4086_State = $43BD3A
SourceAIRun4086_PendingKind = $43BD3C
SourceAIRun4086_End = $43BD3E
SourceAIRun4086_Begin:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceAIRun4086_Ready
 cmp #$B5E6
 beq SourceAIRun4086_Far6
 jmp SourceAIRun4086_Bad
SourceAIRun4086_Far6:
.a16
.i16
 lda.l SourceAIRun4086_State
 bne SourceAIRun4086_Far7
 jmp SourceAIRun4086_Start
SourceAIRun4086_Far7:
.a16
.i16
 cmp #2
 beq SourceAIRun4086_Far8
 jmp SourceAIRun4086_Bad
SourceAIRun4086_Far8:
.a16
.i16
SourceAIRun4086_Start:
.a16
.i16
 jsl SourceAI4086_Begin
 bcc SourceAIRun4086_Far9
 jmp SourceAIRun4086_Bad
SourceAIRun4086_Far9:
.a16
.i16
 jmp SourceAIRun4086_Dispatch
SourceAIRun4086_Continue:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceAIRun4086_Ready
 cmp #$B5E6
 beq SourceAIRun4086_Far10
 jmp SourceAIRun4086_Bad
SourceAIRun4086_Far10:
.a16
.i16
 lda.l SourceAIRun4086_State
 cmp #1
 beq SourceAIRun4086_Far11
 jmp SourceAIRun4086_Bad
SourceAIRun4086_Far11:
.a16
.i16
 jsl SourceAI4086_CheckOwner
 bcc SourceAIRun4086_Far12
 jmp SourceAIRun4086_Bad
SourceAIRun4086_Far12:
.a16
.i16
 lda.l SourceAIRun4086_PendingKind
 cmp #1
 bne SourceAIRun4086_Far13
 jmp SourceAIRun4086_SpawnFrame
SourceAIRun4086_Far13:
.a16
.i16
 cmp #4
 beq SourceAIRun4086_Far14
 jmp SourceAIRun4086_Bad
SourceAIRun4086_Far14:
.a16
.i16
 lda.l SourceAI4086_State
 cmp #4
 beq SourceAIRun4086_Far15
 jmp SourceAIRun4086_Bad
SourceAIRun4086_Far15:
.a16
.i16
 lda.l SourceAI4086_Slot
 cmp.l SourceAnimationInit4086_Slot
 beq SourceAIRun4086_Far16
 jmp SourceAIRun4086_Bad
SourceAIRun4086_Far16:
.a16
.i16
 jsl SourceUpdateFrame4086_CheckIdle
 bcc SourceAIRun4086_Far17
 jmp SourceAIRun4086_Bad
SourceAIRun4086_Far17:
.a16
.i16
 jsl SourceAnimationInit4086_Ack
 bcc SourceAIRun4086_Far18
 jmp SourceAIRun4086_Bad
SourceAIRun4086_Far18:
.a16
.i16
 lda #4
 jmp SourceAIRun4086_Resume
SourceAIRun4086_SpawnFrame:
.a16
.i16
 jsl SourceCommonSpawn4086_Continue
 bcc SourceAIRun4086_Far19
 jmp SourceAIRun4086_Bad
SourceAIRun4086_Far19:
.a16
.i16
 lda #1
 jmp SourceAIRun4086_Resume
SourceAIRun4086_Dispatch:
.a16
.i16
 cmp #0
 bne SourceAIRun4086_Far20
 jmp SourceAIRun4086_Done
SourceAIRun4086_Far20:
.a16
.i16
 cmp #1
 bne SourceAIRun4086_Far21
 jmp SourceAIRun4086_Action
SourceAIRun4086_Far21:
.a16
.i16
 cmp #2
 bne SourceAIRun4086_Far22
 jmp SourceAIRun4086_Think
SourceAIRun4086_Far22:
.a16
.i16
 cmp #3
 bne SourceAIRun4086_Far23
 jmp SourceAIRun4086_Script
SourceAIRun4086_Far23:
.a16
.i16
 cmp #4
 bne SourceAIRun4086_Far24
 jmp SourceAIRun4086_Idle
SourceAIRun4086_Far24:
.a16
.i16
 jmp SourceAIRun4086_Bad
SourceAIRun4086_Action:
.a16
.i16
 lda.l SourceAI4086_Callback+2
 beq SourceAIRun4086_Far25
 jmp SourceAIRun4086_Bad
SourceAIRun4086_Far25:
.a16
.i16
 lda.l SourceAI4086_Callback
 cmp #4
 bne SourceAIRun4086_Far26
 jmp SourceAIRun4086_Spawn
SourceAIRun4086_Far26:
.a16
.i16
 cmp #5
 beq SourceAIRun4086_Far27
 jmp SourceAIRun4086_Bad
SourceAIRun4086_Far27:
.a16
.i16
 lda #0
 sta.l SourceCommonDrop4086_Status
 jsl SourceCommonDrop4086_Execute
 bcc SourceAIRun4086_Far28
 jmp SourceAIRun4086_Bad
SourceAIRun4086_Far28:
.a16
.i16
 lda #1
 jmp SourceAIRun4086_Resume
SourceAIRun4086_Spawn:
.a16
.i16
 lda #0
 sta.l SourceCommonSpawn4086_State
 jsl SourceCommonSpawn4086_Begin
 bcc SourceAIRun4086_Far29
 jmp SourceAIRun4086_Bad
SourceAIRun4086_Far29:
.a16
.i16
 cmp #1
 bne SourceAIRun4086_Far30
 jmp SourceAIRun4086_SpawnPending
SourceAIRun4086_Far30:
.a16
.i16
 lda #1
 jmp SourceAIRun4086_Resume
SourceAIRun4086_SpawnPending:
.a16
.i16
 lda #1
 jmp SourceAIRun4086_Pending
SourceAIRun4086_Think:
.a16
.i16
 lda.l SourceAI4086_Callback+2
 beq SourceAIRun4086_Far31
 jmp SourceAIRun4086_Bad
SourceAIRun4086_Far31:
.a16
.i16
 lda.l SourceAI4086_Callback
 cmp #15
 beq SourceAIRun4086_Far32
 jmp SourceAIRun4086_Bad
SourceAIRun4086_Far32:
.a16
.i16
 lda #0
 sta.l SourceAnythingWalk4086_Status
 jsl SourceAnythingWalk4086_Execute
 bcc SourceAIRun4086_Far33
 jmp SourceAIRun4086_Bad
SourceAIRun4086_Far33:
.a16
.i16
 lda #2
 jmp SourceAIRun4086_Resume
SourceAIRun4086_Script:
.a16
.i16
 jsl SourceAI4086_ThinkScriptAbsent
 bcc SourceAIRun4086_Far34
 jmp SourceAIRun4086_Bad
SourceAIRun4086_Far34:
.a16
.i16
 lda #3
 jmp SourceAIRun4086_Resume
SourceAIRun4086_Idle:
.a16
.i16
 lda.l SourceAI4086_Slot
 sta.l SourceIdle4086_Slot
 jsl SourceSetIdle4086_Begin
 bcc SourceAIRun4086_Far35
 jmp SourceAIRun4086_Bad
SourceAIRun4086_Far35:
.a16
.i16
 cmp #1
 bne SourceAIRun4086_Far36
 jmp SourceAIRun4086_IdlePending
SourceAIRun4086_Far36:
.a16
.i16
 lda #4
 jmp SourceAIRun4086_Resume
SourceAIRun4086_IdlePending:
.a16
.i16
 lda #4
SourceAIRun4086_Pending:
.a16
.i16
 sta.l SourceAIRun4086_PendingKind
 lda #1
 sta.l SourceAIRun4086_State
 jmp SourceAIRun4086_Good
SourceAIRun4086_Resume:
.a16
.i16
 jsl SourceAI4086_Continue
 bcc SourceAIRun4086_Far37
 jmp SourceAIRun4086_Bad
SourceAIRun4086_Far37:
.a16
.i16
 jmp SourceAIRun4086_Dispatch
SourceAIRun4086_Done:
.a16
.i16
 lda #2
 sta.l SourceAIRun4086_State
 lda #0
 sta.l SourceAIRun4086_PendingKind
SourceAIRun4086_Good:
.a16
.i16
 ply
 plx
 plp
 clc
 rtl
SourceAIRun4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceAIRun4086_State
 ply
 plx
 plp
 sec
 rtl
