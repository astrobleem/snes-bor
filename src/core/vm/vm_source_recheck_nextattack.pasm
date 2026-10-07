; Literal source recheck_nextattack(target): unsigned nextattack timer.
; Entity core+92 was zeroed by both birth paths and preserved by model copy.
; It is now assigned to this actual dynamic entity field, not modeldata.
SOURCE_ENTITY_NEXTATTACK = $40C05C
SourceRecheckNextAttack4086_Ready = $43BDD4
SourceRecheckNextAttack4086_Status = $43BDD6
SourceRecheckNextAttack4086_SelfCore = $43BDD8
SourceRecheckNextAttack4086_TargetCore = $43BDDA
SourceRecheckNextAttack4086_TargetFlags = $43BDDC
SourceRecheckNextAttack4086_Target = $43BDDE
SourceRecheckNextAttack4086_Result = $43BDE0
SourceRecheckNextAttack4086_End = $43BDE4
; A = physical target slot. Do not insert an exists/dead recheck.
SourceRecheckNextAttack4086_Execute:
.a16
.i16
 php
 rep #$38
 phx
 phy
 sta.l SourceRecheckNextAttack4086_Target
 lda.l SourceRecheckNextAttack4086_Ready
 cmp #$B5F6
 beq SourceRecheckNextAttack4086_Lease
 jmp SourceRecheckNextAttack4086_Bad
SourceRecheckNextAttack4086_Lease:
.a16
.i16
 lda.l SourceRecheckNextAttack4086_Status
 beq SourceRecheckNextAttack4086_Idle
 cmp #2
 beq SourceRecheckNextAttack4086_Idle
 jmp SourceRecheckNextAttack4086_Bad
SourceRecheckNextAttack4086_Idle:
.a16
.i16
 lda #1
 sta.l SourceRecheckNextAttack4086_Status
 jsl SourceNormalAttack4086_CheckOwner
 bcc SourceRecheckNextAttack4086_Owner
 jmp SourceRecheckNextAttack4086_Bad
SourceRecheckNextAttack4086_Owner:
.a16
.i16
 lda.l SourceNormalAttack4086_State
 cmp #1
 bcs SourceRecheckNextAttack4086_ActiveLow
 jmp SourceRecheckNextAttack4086_Bad
SourceRecheckNextAttack4086_ActiveLow:
.a16
.i16
 cmp #7
 bcc SourceRecheckNextAttack4086_Active
 jmp SourceRecheckNextAttack4086_Bad
SourceRecheckNextAttack4086_Active:
.a16
.i16
 lda.l SourceModelEntityCopy4086_Ready
 cmp #$B4EB
 beq SourceRecheckNextAttack4086_CoreReady
 jmp SourceRecheckNextAttack4086_Bad
SourceRecheckNextAttack4086_CoreReady:
.a16
.i16
 lda.l SourceModelEntityCopy4086_Entities
 cmp.l VmSourceWorld_Count
 beq SourceRecheckNextAttack4086_CoreCount
 jmp SourceRecheckNextAttack4086_Bad
SourceRecheckNextAttack4086_CoreCount:
.a16
.i16
 lda.l SourceRecheckNextAttack4086_Target
 cmp.l VmSourceWorld_Count
 bcc SourceRecheckNextAttack4086_TargetValid
 jmp SourceRecheckNextAttack4086_Bad
SourceRecheckNextAttack4086_TargetValid:
.a16
.i16
 ; Validate the stable physical pointer, including for retired target rows.
 asl a
 asl a
 asl a
 asl a
 pha
 asl a
 asl a
 clc
 adc 1,s
 clc
 adc #$4000
 tax
 pla
 txa
 cmp.l $410000,x
 beq SourceRecheckNextAttack4086_TokenLow
 jmp SourceRecheckNextAttack4086_Bad
SourceRecheckNextAttack4086_TokenLow:
.a16
.i16
 lda.l $410002,x
 cmp #$0041
 beq SourceRecheckNextAttack4086_TokenHigh
 jmp SourceRecheckNextAttack4086_Bad
SourceRecheckNextAttack4086_TokenHigh:
.a16
.i16
 lda.l SourceRecheckNextAttack4086_Target
 jsr SourceRecheckNextAttack4086_CoreOffset
 txa
 sta.l SourceRecheckNextAttack4086_TargetCore
 lda.l SourceAI4086_Slot
 jsr SourceRecheckNextAttack4086_CoreOffset
 txa
 sta.l SourceRecheckNextAttack4086_SelfCore
 lda.l SourceRecheckNextAttack4086_Target
 asl a
 asl a
 asl a
 asl a
 asl a
 sta.l SourceRecheckNextAttack4086_TargetFlags
 tax
 lda.l $43EB0C,x
 ora.l $43EB0E,x
 beq SourceRecheckNextAttack4086_Attacking
 lda #0
 bra SourceRecheckNextAttack4086_StoreLow
SourceRecheckNextAttack4086_Attacking:
.a16
.i16
 lda.l SourceRecheckNextAttack4086_TargetCore
 tax
 lda.l $40C058,x
 ora.l $40C05A,x
 beq SourceRecheckNextAttack4086_Jumping
 lda.l SourceRecheckNextAttack4086_SelfCore
 tax
 lda.l SOURCE_ENTITY_NEXTATTACK+2,x
 bne SourceRecheckNextAttack4086_SubFour
 lda.l SOURCE_ENTITY_NEXTATTACK,x
 cmp #5
 bcc SourceRecheckNextAttack4086_Jumping
SourceRecheckNextAttack4086_SubFour:
.a16
.i16
 lda #4
 bra SourceRecheckNextAttack4086_Subtract
SourceRecheckNextAttack4086_Jumping:
.a16
.i16
 lda.l SourceRecheckNextAttack4086_TargetFlags
 tax
 lda.l $43EB08,x
 ora.l $43EB0A,x
 beq SourceRecheckNextAttack4086_ResultRead
 lda.l SourceRecheckNextAttack4086_SelfCore
 tax
 lda.l SOURCE_ENTITY_NEXTATTACK+2,x
 bne SourceRecheckNextAttack4086_SubSixteen
 lda.l SOURCE_ENTITY_NEXTATTACK,x
 cmp #17
 bcc SourceRecheckNextAttack4086_ResultRead
SourceRecheckNextAttack4086_SubSixteen:
.a16
.i16
 lda #16
SourceRecheckNextAttack4086_Subtract:
.a16
.i16
 pha
 lda.l SourceRecheckNextAttack4086_SelfCore
 tax
 lda.l SOURCE_ENTITY_NEXTATTACK,x
 sec
 sbc 1,s
 sta.l SOURCE_ENTITY_NEXTATTACK,x
 lda.l SOURCE_ENTITY_NEXTATTACK+2,x
 sbc #0
 sta.l SOURCE_ENTITY_NEXTATTACK+2,x
 pla
 bra SourceRecheckNextAttack4086_ResultRead
SourceRecheckNextAttack4086_StoreLow:
.a16
.i16
 pha
 lda.l SourceRecheckNextAttack4086_SelfCore
 tax
 pla
 sta.l SOURCE_ENTITY_NEXTATTACK,x
 sta.l SOURCE_ENTITY_NEXTATTACK+2,x
SourceRecheckNextAttack4086_ResultRead:
.a16
.i16
 lda.l SourceRecheckNextAttack4086_SelfCore
 tax
 lda.l SOURCE_ENTITY_NEXTATTACK,x
 sta.l SourceRecheckNextAttack4086_Result
 lda.l SOURCE_ENTITY_NEXTATTACK+2,x
 sta.l SourceRecheckNextAttack4086_Result+2
 lda #2
 sta.l SourceRecheckNextAttack4086_Status
 ply
 plx
 plp
 clc
 rtl
SourceRecheckNextAttack4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceRecheckNextAttack4086_Status
 ply
 plx
 plp
 sec
 rtl
SourceRecheckNextAttack4086_CoreOffset:
.a16
.i16
 asl a
 asl a
 asl a
 asl a
 asl a
 pha
 asl a
 clc
 adc 1,s
 tax
 pla
 rts
