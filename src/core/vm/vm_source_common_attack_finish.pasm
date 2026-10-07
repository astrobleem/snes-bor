; Literal player / NULL-opponent attack finish. Source idle precedes stall.
; NPC runoff remains explicit. Captured player branch survives frame-zero.
SourceCommonAttackFinish4086_Ready = $43BF64
SourceCommonAttackFinish4086_Status = $43BF66
SourceCommonAttackFinish4086_Player = $43BF68
SourceCommonAttackFinish4086_Timing = $43BF6A
SourceCommonAttackFinish4086_Delay = $43BF6C
SourceCommonAttackFinish4086_End = $43BF70
SourceCommonAttackFinish4086_Execute:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceCommonAttackFinish4086_Ready
 cmp #$B608
 beq SourceCommonAttackFinish4086_ReadyChecked
 jmp SourceCommonAttackFinish4086_Bad
SourceCommonAttackFinish4086_ReadyChecked:
.a16
.i16
 lda.l SourceCommonAttackFinish4086_Status
 beq SourceCommonAttackFinish4086_Start
 cmp #2
 beq SourceCommonAttackFinish4086_Start
 jmp SourceCommonAttackFinish4086_Bad
SourceCommonAttackFinish4086_Start:
.a16
.i16
 jsl SourceAI4086_CheckOwner
 bcc SourceCommonAttackFinish4086_OwnerChecked
 jmp SourceCommonAttackFinish4086_Bad
SourceCommonAttackFinish4086_OwnerChecked:
.a16
.i16
 lda.l SourceAI4086_State
 cmp #1
 beq SourceCommonAttackFinish4086_ActionChecked
 jmp SourceCommonAttackFinish4086_Bad
SourceCommonAttackFinish4086_ActionChecked:
.a16
.i16
 lda.l SourceAI4086_Callback
 cmp #17
 beq SourceCommonAttackFinish4086_CallbackChecked
 jmp SourceCommonAttackFinish4086_Bad
SourceCommonAttackFinish4086_CallbackChecked:
.a16
.i16
 lda.l SourceAI4086_Callback+2
 beq SourceCommonAttackFinish4086_CallbackHighChecked
 jmp SourceCommonAttackFinish4086_Bad
SourceCommonAttackFinish4086_CallbackHighChecked:
.a16
.i16
 lda.l SourceAI4086_Life
 tax
 lda.l $43900C,x
 cmp #17
 beq SourceCommonAttackFinish4086_LiveChecked
 jmp SourceCommonAttackFinish4086_Bad
SourceCommonAttackFinish4086_LiveChecked:
.a16
.i16
 lda.l $43900E,x
 beq SourceCommonAttackFinish4086_LiveHighChecked
 jmp SourceCommonAttackFinish4086_Bad
SourceCommonAttackFinish4086_LiveHighChecked:
.a16
.i16
 lda.l SourceModelEntityCopy4086_Ready
 cmp #$B4EB
 beq SourceCommonAttackFinish4086_ModelLease
 jmp SourceCommonAttackFinish4086_Bad
SourceCommonAttackFinish4086_ModelLease:
.a16
.i16
 lda.l SourceModelEntityCopy4086_Models
 beq SourceCommonAttackFinish4086_BadModels
 cmp #17
 bcc SourceCommonAttackFinish4086_ModelCountChecked
SourceCommonAttackFinish4086_BadModels:
.a16
.i16
 jmp SourceCommonAttackFinish4086_Bad
SourceCommonAttackFinish4086_ModelCountChecked:
.a16
.i16
 lda.l SourceAI4086_Side
 tax
 lda.l $416800,x
 cmp.l SourceModelEntityCopy4086_Models
 bcc SourceCommonAttackFinish4086_ModelChecked
 jmp SourceCommonAttackFinish4086_Bad
SourceCommonAttackFinish4086_ModelChecked:
.a16
.i16
 asl a
 asl a
 asl a
 asl a
 asl a
 pha
 asl a
 asl a
 clc
 adc 1,s
 tax
 pla
 lda.l $40B09C,x
 and #1
 sta.l SourceCommonAttackFinish4086_Player
 bne SourceCommonAttackFinish4086_Apply
 lda.l SourceAI4086_Side
 tax
 lda.l $40900C,x
 ora.l $40900E,x
 beq SourceCommonAttackFinish4086_OpponentChecked
 jmp SourceCommonAttackFinish4086_Bad
SourceCommonAttackFinish4086_OpponentChecked:
.a16
.i16
 jsr SourceCommonAttackFinish4086_TimingRow
 bcc SourceCommonAttackFinish4086_Apply
 jmp SourceCommonAttackFinish4086_Bad
SourceCommonAttackFinish4086_Apply:
.a16
.i16
 lda #1
 sta.l SourceCommonAttackFinish4086_Status
 lda.l SourceAI4086_Side
 tax
 lda #0
 sta.l $416824,x
 sta.l $416826,x
 sta.l $416828,x
 sta.l $41682A,x
 lda.l SourceAI4086_Life
 tax
 lda #0
 sta.l $43900C,x
 sta.l $43900E,x
 lda.l SourceAI4086_Slot
 sta.l SourceIdle4086_Slot
 jsl SourceSetIdle4086_Begin
 bcc SourceCommonAttackFinish4086_IdleStarted
 jmp SourceCommonAttackFinish4086_Bad
SourceCommonAttackFinish4086_IdleStarted:
.a16
.i16
 cmp #0
 bne SourceCommonAttackFinish4086_Pending
 jmp SourceCommonAttackFinish4086_PostIdle
SourceCommonAttackFinish4086_Pending:
.a16
.i16
 cmp #1
 beq SourceCommonAttackFinish4086_Yield
 jmp SourceCommonAttackFinish4086_Bad
SourceCommonAttackFinish4086_Yield:
.a16
.i16
 lda #1
 ply
 plx
 plp
 clc
 rtl
SourceCommonAttackFinish4086_Continue:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceCommonAttackFinish4086_Ready
 cmp #$B608
 beq SourceCommonAttackFinish4086_ContinueReady
 jmp SourceCommonAttackFinish4086_Bad
SourceCommonAttackFinish4086_ContinueReady:
.a16
.i16
 lda.l SourceCommonAttackFinish4086_Status
 cmp #1
 beq SourceCommonAttackFinish4086_ContinuePending
 jmp SourceCommonAttackFinish4086_Bad
SourceCommonAttackFinish4086_ContinuePending:
.a16
.i16
 jsl SourceAI4086_CheckOwner
 bcc SourceCommonAttackFinish4086_ContinueOwner
 jmp SourceCommonAttackFinish4086_Bad
SourceCommonAttackFinish4086_ContinueOwner:
.a16
.i16
 lda.l SourceAI4086_State
 cmp #1
 beq SourceCommonAttackFinish4086_ContinueAction
 jmp SourceCommonAttackFinish4086_Bad
SourceCommonAttackFinish4086_ContinueAction:
.a16
.i16
 lda.l SourceAI4086_Slot
 cmp.l SourceAnimationInit4086_Slot
 beq SourceCommonAttackFinish4086_ContinueSlot
 jmp SourceCommonAttackFinish4086_Bad
SourceCommonAttackFinish4086_ContinueSlot:
.a16
.i16
 jsl SourceUpdateFrame4086_CheckIdle
 bcc SourceCommonAttackFinish4086_ContinueFrame
 jmp SourceCommonAttackFinish4086_Bad
SourceCommonAttackFinish4086_ContinueFrame:
.a16
.i16
 jsl SourceAnimationInit4086_Ack
 bcc SourceCommonAttackFinish4086_PostIdle
 jmp SourceCommonAttackFinish4086_Bad
SourceCommonAttackFinish4086_PostIdle:
.a16
.i16
 lda.l SourceCommonAttackFinish4086_Player
 bne SourceCommonAttackFinish4086_Done
 jsr SourceCommonAttackFinish4086_TimingRow
 bcc SourceCommonAttackFinish4086_PostTiming
 jmp SourceCommonAttackFinish4086_Bad
SourceCommonAttackFinish4086_PostTiming:
.a16
.i16
 lda #200
 sec
 sbc.l SOURCE_ENTITY_ATTACK_TIMING,x
 sta.l SourceCommonAttackFinish4086_Delay
 lda #0
 sbc.l SOURCE_ENTITY_ATTACK_TIMING+2,x
 sta.l SourceCommonAttackFinish4086_Delay+2
 bmi SourceCommonAttackFinish4086_Clamp
 bne SourceCommonAttackFinish4086_Stall
 lda.l SourceCommonAttackFinish4086_Delay
 cmp #100
 bcs SourceCommonAttackFinish4086_Stall
SourceCommonAttackFinish4086_Clamp:
.a16
.i16
 lda #100
 sta.l SourceCommonAttackFinish4086_Delay
 lda #0
 sta.l SourceCommonAttackFinish4086_Delay+2
SourceCommonAttackFinish4086_Stall:
.a16
.i16
 lda.l SourceAI4086_Freeze
 tax
 lda.l VmSourceWorld_Time
 clc
 adc.l SourceCommonAttackFinish4086_Delay
 sta.l $42E008,x
 lda.l VmSourceWorld_Time+2
 adc.l SourceCommonAttackFinish4086_Delay+2
 sta.l $42E00A,x
SourceCommonAttackFinish4086_Done:
.a16
.i16
 lda #2
 sta.l SourceCommonAttackFinish4086_Status
 lda #0
 ply
 plx
 plp
 clc
 rtl
SourceCommonAttackFinish4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceCommonAttackFinish4086_Status
 lda #0
 ply
 plx
 plp
 sec
 rtl
; Re-read the actual row after idle scripts; aggression is not pre-captured.
SourceCommonAttackFinish4086_TimingRow:
.a16
.i16
 lda.l SourceAttackTiming4086_Ready
 cmp #$B603
 bne SourceCommonAttackFinish4086_TimingBad
 lda.l SourceAttackTiming4086_Status
 cmp #2
 bne SourceCommonAttackFinish4086_TimingBad
 lda.l SourceAttackTiming4086_Models
 cmp.l SourceModelEntityCopy4086_Models
 bne SourceCommonAttackFinish4086_TimingBad
 lda.l SourceAI4086_Slot
 asl a
 pha
 asl a
 asl a
 asl a
 sec
 sbc 1,s
 tax
 pla
 txa
 sta.l SourceCommonAttackFinish4086_Timing
 lda.l SOURCE_ENTITY_ATTACK_TIMING+12,x
 cmp #$B603
 bne SourceCommonAttackFinish4086_TimingBad
 clc
 rts
SourceCommonAttackFinish4086_TimingBad:
.a16
.i16
 sec
 rts
