; common_try_normalattack(NULL): execute the real unbounded target query.
; No target returns literal false before recheck_nextattack/random/mutations.
; Present targets execute both timer rechecks and the real test-only picker.
; Positive selections inspect actual combo state and execute source chance.
; Rejected chance publishes nextattack through the literal-C delay schedule.
; Successful preparation yields until actual idle frame-zero effects complete.
SourceTryNormalAttack4086_Ready = $43BDCC
SourceTryNormalAttack4086_Status = $43BDCE
SourceTryNormalAttack4086_End = $43BDD0
SourceTryNormalAttack4086_Execute:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceTryNormalAttack4086_Ready
 cmp #$B5F4
 beq SourceTryNormalAttack4086_Lease
 jmp SourceTryNormalAttack4086_Bad
SourceTryNormalAttack4086_Lease:
.a16
.i16
 lda.l SourceTryNormalAttack4086_Status
 beq SourceTryNormalAttack4086_Idle
 jmp SourceTryNormalAttack4086_Bad
SourceTryNormalAttack4086_Idle:
.a16
.i16
 jsl SourceNormalAttack4086_CheckOwner
 bcc SourceTryNormalAttack4086_Owner
 jmp SourceTryNormalAttack4086_Bad
SourceTryNormalAttack4086_Owner:
.a16
.i16
 lda.l SourceNormalAttack4086_State
 cmp #5
 beq SourceTryNormalAttack4086_Query
 jmp SourceTryNormalAttack4086_Bad
SourceTryNormalAttack4086_Query:
.a16
.i16
 jsl SourceAITarget4086_Unbounded
 bcc SourceTryNormalAttack4086_Target
 jmp SourceTryNormalAttack4086_Bad
SourceTryNormalAttack4086_Target:
.a16
.i16
 lda.l SourceAITarget4086_Result
 ora.l SourceAITarget4086_Result+2
 bne SourceTryNormalAttack4086_Recheck
 jmp SourceTryNormalAttack4086_False
SourceTryNormalAttack4086_Recheck:
.a16
.i16
 lda.l SourceAITarget4086_Selected
 jsl SourceRecheckNextAttack4086_Execute
 bcc SourceTryNormalAttack4086_RecheckAgain
 jmp SourceTryNormalAttack4086_Bad
SourceTryNormalAttack4086_RecheckAgain:
.a16
.i16
 ; The first call is not redundant: both mutate the actual source timer.
 lda.l SourceAITarget4086_Selected
 jsl SourceRecheckNextAttack4086_Execute
 bcc SourceTryNormalAttack4086_Delay
 jmp SourceTryNormalAttack4086_Bad
SourceTryNormalAttack4086_Delay:
.a16
.i16
 lda.l SourceRecheckNextAttack4086_Result+2
 cmp.l VmSourceWorld_Time+2
 bcc SourceTryNormalAttack4086_BodyUnbound
 beq SourceTryNormalAttack4086_DelayLow
 jmp SourceTryNormalAttack4086_False
SourceTryNormalAttack4086_DelayLow:
.a16
.i16
 lda.l SourceRecheckNextAttack4086_Result
 cmp.l VmSourceWorld_Time
 bcc SourceTryNormalAttack4086_BodyUnbound
 beq SourceTryNormalAttack4086_BodyUnbound
 jmp SourceTryNormalAttack4086_False
SourceTryNormalAttack4086_BodyUnbound:
.a16
.i16
 ; The source vulnerability condition is determined without DROP/RISE
 ; services when actual target.attacking is true. These are pure reads.
 lda.l SourceTarget4086_SelectedMeta
 tax
 lda.l SOURCE_TARGET_META+8,x
 bne SourceTryNormalAttack4086_Pick
 lda.l SourceRecheckNextAttack4086_TargetCore
 tax
 lda.l $40C058,x
 ora.l $40C05A,x
 beq SourceTryNormalAttack4086_RejectContinueA
 jmp SourceTryNormalAttack4086_False
SourceTryNormalAttack4086_RejectContinueA:
.a16
.i16
 ; Dynamic target.drop is independent of the sealtime timer and action ID.
 lda.l SourceAITarget4086_Selected
 asl a
 asl a
 pha
 asl a
 asl a
 clc
 adc 1,s
 tax
 pla
 lda.l SOURCE_ENTITY_COMBAT+16,x
 cmp #$B5FB
 beq SourceTryNormalAttack4086_Combat
 jmp SourceTryNormalAttack4086_Bad
SourceTryNormalAttack4086_Combat:
.a16
.i16
 lda.l SOURCE_ENTITY_COMBAT+18,x
 beq SourceTryNormalAttack4086_Drop
 jmp SourceTryNormalAttack4086_Bad
SourceTryNormalAttack4086_Drop:
.a16
.i16
 lda.l SOURCE_ENTITY_COMBAT,x
 ora.l SOURCE_ENTITY_COMBAT+2,x
 beq SourceTryNormalAttack4086_RejectContinueB
 jmp SourceTryNormalAttack4086_False
SourceTryNormalAttack4086_RejectContinueB:
.a16
.i16
 ; NULL cannot equal common_rise. Non-NULL action comparison remains
 ; explicit until that callback has a source-derived registered identity.
 lda.l SourceAITarget4086_Selected
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
 lda.l $43900C,x
 ora.l $43900E,x
 beq SourceTryNormalAttack4086_Pick
 jmp SourceTryNormalAttack4086_Bad
SourceTryNormalAttack4086_Pick:
.a16
.i16
 lda.l SourceAITarget4086_Selected
 sta.l SourceAttackPicker4086_Target
 lda #1
 sta.l SourceAttackPicker4086_TestOnly
 lda #0
 sta.l SourceAttackPicker4086_TestOnly+2
 jsl SourceAttackPicker4086_Execute
 bcc SourceTryNormalAttack4086_Picked
 jmp SourceTryNormalAttack4086_Bad
SourceTryNormalAttack4086_Picked:
.a16
.i16
 lda.l SourceAttackPicker4086_Result+2
 bpl SourceTryNormalAttack4086_RejectContinueC
 jmp SourceTryNormalAttack4086_False
SourceTryNormalAttack4086_RejectContinueC:
.a16
.i16
SourceTryNormalAttack4086_ComboUnbound:
.a16
.i16
 lda.l SourceAI4086_Slot
 asl a
 asl a
 pha
 asl a
 asl a
 clc
 adc 1,s
 tax
 pla
 lda.l SOURCE_ENTITY_COMBAT+16,x
 cmp #$B5FB
 beq SourceTryNormalAttack4086_ComboRow
 jmp SourceTryNormalAttack4086_Bad
SourceTryNormalAttack4086_ComboRow:
.a16
.i16
 lda.l SOURCE_ENTITY_COMBAT+18,x
 beq SourceTryNormalAttack4086_ComboStep
 jmp SourceTryNormalAttack4086_Bad
SourceTryNormalAttack4086_ComboStep:
.a16
.i16
 lda.l SOURCE_ENTITY_COMBAT+8,x
 ora.l SOURCE_ENTITY_COMBAT+10,x
 beq SourceTryNormalAttack4086_Chance
 lda.l SOURCE_ENTITY_COMBAT+14,x
 cmp.l VmSourceWorld_Time+2
 bcc SourceTryNormalAttack4086_Chance
 beq SourceTryNormalAttack4086_ComboLow
 jmp SourceTryNormalAttack4086_ComboPrepare
SourceTryNormalAttack4086_ComboLow:
.a16
.i16
 lda.l SOURCE_ENTITY_COMBAT+12,x
 cmp.l VmSourceWorld_Time
 bcc SourceTryNormalAttack4086_Chance
 beq SourceTryNormalAttack4086_Chance
 jmp SourceTryNormalAttack4086_ComboPrepare
SourceTryNormalAttack4086_Chance:
.a16
.i16
 jsl SourceEntityNormalChance4086_Execute
 bcc SourceTryNormalAttack4086_ChanceResult
 jmp SourceTryNormalAttack4086_Bad
SourceTryNormalAttack4086_ChanceResult:
.a16
.i16
 lda.l SourceEntityNormalChance4086_Result
 ora.l SourceEntityNormalChance4086_Result+2
 beq SourceTryNormalAttack4086_ChanceFalse
 jmp SourceTryNormalAttack4086_ChancePrepare
SourceTryNormalAttack4086_ChanceFalse:
.a16
.i16
 lda #0
 sta.l SourceAttackDelay4086_Kind
 jsl SourceAttackDelay4086_Execute
 bcc SourceTryNormalAttack4086_ChanceRejected
 jmp SourceTryNormalAttack4086_Bad
SourceTryNormalAttack4086_ChanceRejected:
.a16
.i16
 lda.l SourceAI4086_Flags
 asl a
 clc
 adc.l SourceAI4086_Flags
 tax
 lda.l SourceAttackDelay4086_Result
 sta.l $40C05C,x
 lda.l SourceAttackDelay4086_Result+2
 sta.l $40C05E,x
 jmp SourceTryNormalAttack4086_False
SourceTryNormalAttack4086_ChancePrepare:
.a16
.i16
 lda #1
 sta.l SourceAttackDelay4086_Kind
 jsl SourceAttackDelay4086_Execute
 bcc SourceTryNormalAttack4086_ChanceStall
 jmp SourceTryNormalAttack4086_Bad
SourceTryNormalAttack4086_ChanceStall:
.a16
.i16
 lda.l SourceAttackDelay4086_Result
 pha
 lda.l SourceAttackDelay4086_Result+2
 bra SourceTryNormalAttack4086_StoreStall
SourceTryNormalAttack4086_ComboPrepare:
.a16
.i16
 lda.l VmSourceWorld_Time
 clc
 adc #1
 pha
 lda.l VmSourceWorld_Time+2
 adc #0
SourceTryNormalAttack4086_StoreStall:
.a16
.i16
 pha
 lda.l SourceAI4086_Freeze
 tax
 pla
 sta.l $42E00A,x
 pla
 sta.l $42E008,x
 lda.l SourceAI4086_Life
 tax
 lda #16
 sta.l $43900C,x
 lda #0
 sta.l $43900E,x
 lda.l SourceAI4086_Side
 tax
 lda #0
 sta.l $416824,x
 sta.l $416826,x
 sta.l $416828,x
 sta.l $41682A,x
 lda.l SourceAI4086_Slot
 sta.l SourceIdle4086_Slot
 jsl SourceSetIdle4086_Begin
 bcc SourceTryNormalAttack4086_IdleStarted
 jmp SourceTryNormalAttack4086_Bad
SourceTryNormalAttack4086_IdleStarted:
.a16
.i16
 cmp #0
 beq SourceTryNormalAttack4086_PostIdle
 cmp #1
 beq SourceTryNormalAttack4086_Pending
 jmp SourceTryNormalAttack4086_Bad
SourceTryNormalAttack4086_Pending:
.a16
.i16
 lda #1
 sta.l SourceTryNormalAttack4086_Status
 ply
 plx
 plp
 clc
 rtl
; Only the actual animation owner may acknowledge the idle frame-zero run.
SourceTryNormalAttack4086_Continue:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceTryNormalAttack4086_Ready
 cmp #$B5F4
 beq SourceTryNormalAttack4086_ContinueReady
 jmp SourceTryNormalAttack4086_Bad
SourceTryNormalAttack4086_ContinueReady:
.a16
.i16
 lda.l SourceTryNormalAttack4086_Status
 cmp #1
 beq SourceTryNormalAttack4086_ContinuePending
 jmp SourceTryNormalAttack4086_Bad
SourceTryNormalAttack4086_ContinuePending:
.a16
.i16
 jsl SourceNormalAttack4086_CheckOwner
 bcc SourceTryNormalAttack4086_ContinueOwner
 jmp SourceTryNormalAttack4086_Bad
SourceTryNormalAttack4086_ContinueOwner:
.a16
.i16
 lda.l SourceNormalAttack4086_State
 cmp #5
 beq SourceTryNormalAttack4086_ContinuePhase
 jmp SourceTryNormalAttack4086_Bad
SourceTryNormalAttack4086_ContinuePhase:
.a16
.i16
 lda.l SourceAI4086_Slot
 cmp.l SourceAnimationInit4086_Slot
 beq SourceTryNormalAttack4086_ContinueSlot
 jmp SourceTryNormalAttack4086_Bad
SourceTryNormalAttack4086_ContinueSlot:
.a16
.i16
 jsl SourceUpdateFrame4086_CheckIdle
 bcc SourceTryNormalAttack4086_ContinueFrame
 jmp SourceTryNormalAttack4086_Bad
SourceTryNormalAttack4086_ContinueFrame:
.a16
.i16
 jsl SourceAnimationInit4086_Ack
 bcc SourceTryNormalAttack4086_PostIdle
 jmp SourceTryNormalAttack4086_Bad
SourceTryNormalAttack4086_PostIdle:
.a16
.i16
 lda.l SourceAI4086_Flags
 tax
 lda #0
 sta.l $43EB00,x
 sta.l $43EB02,x
 lda.l SourceAI4086_Flags
 asl a
 clc
 adc.l SourceAI4086_Flags
 tax
 lda #$FFFF
 sta.l $40C058,x
 sta.l $40C05A,x
 lda #1
 sta.l SourceNormalAttack4086_Response
 lda #0
 sta.l SourceNormalAttack4086_Response+2
 lda #2
 sta.l SourceTryNormalAttack4086_Status
 lda #0
 ply
 plx
 plp
 clc
 rtl
SourceTryNormalAttack4086_False:
.a16
.i16
 lda #0
 sta.l SourceNormalAttack4086_Response
 sta.l SourceNormalAttack4086_Response+2
 lda #2
 sta.l SourceTryNormalAttack4086_Status
 lda #0
 ply
 plx
 plp
 clc
 rtl
SourceTryNormalAttack4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceTryNormalAttack4086_Status
 lda #0
 ply
 plx
 plp
 sec
 rtl
