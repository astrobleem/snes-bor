; common_try_normalattack(NULL): execute the real unbounded target query.
; No target returns literal false before recheck_nextattack/random/mutations.
; Present targets execute both timer rechecks and the real test-only picker.
; Positive selections inspect actual combo state and execute source chance.
; Rejected chance publishes nextattack through the literal-C delay schedule.
; Successful preparation remains explicit until idle/frame-zero is bound.
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
 jmp SourceTryNormalAttack4086_PrepareUnbound
SourceTryNormalAttack4086_ComboLow:
.a16
.i16
 lda.l SOURCE_ENTITY_COMBAT+12,x
 cmp.l VmSourceWorld_Time
 bcc SourceTryNormalAttack4086_Chance
 beq SourceTryNormalAttack4086_Chance
 jmp SourceTryNormalAttack4086_PrepareUnbound
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
 bne SourceTryNormalAttack4086_PrepareUnbound
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
SourceTryNormalAttack4086_PrepareUnbound:
.a16
.i16
 jmp SourceTryNormalAttack4086_Bad
SourceTryNormalAttack4086_False:
.a16
.i16
 lda #0
 sta.l SourceNormalAttack4086_Response
 sta.l SourceNormalAttack4086_Response+2
 lda #2
 sta.l SourceTryNormalAttack4086_Status
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
 ply
 plx
 plp
 sec
 rtl
