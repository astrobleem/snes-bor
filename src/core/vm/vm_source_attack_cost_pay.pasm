; Actual common_attack_proc tocost block. Synchronous, no callback/yield.
; check_energy uses the current cached role; subtraction uses self->animation.
; These handles may differ after mutable model-cache inheritance.
SourceAttackCostPay4086_Ready = $43BF72
SourceAttackCostPay4086_Status = $43BF74
SourceAttackCostPay4086_Cost = $43BF76
SourceAttackCostPay4086_End = $43BF7A
SourceAttackCostPay4086_Execute:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceAttackCostPay4086_Ready
 cmp #$B60A
 beq SourceAttackCostPay4086_Guard1
 jmp SourceAttackCostPay4086_Bad
SourceAttackCostPay4086_Guard1:
.a16
.i16
 lda.l SourceAttackCostPay4086_Status
 beq SourceAttackCostPay4086_Start
 cmp #2
 beq SourceAttackCostPay4086_Guard2
 jmp SourceAttackCostPay4086_Bad
SourceAttackCostPay4086_Guard2:
.a16
.i16
SourceAttackCostPay4086_Start:
.a16
.i16
 lda #1
 sta.l SourceAttackCostPay4086_Status
 jsl SourceAI4086_CheckOwner
 bcc SourceAttackCostPay4086_Guard3
 jmp SourceAttackCostPay4086_Bad
SourceAttackCostPay4086_Guard3:
.a16
.i16
 lda.l SourceAI4086_State
 cmp #1
 beq SourceAttackCostPay4086_Guard4
 jmp SourceAttackCostPay4086_Bad
SourceAttackCostPay4086_Guard4:
.a16
.i16
 lda.l SourceAI4086_Callback
 cmp #17
 beq SourceAttackCostPay4086_Guard5
 jmp SourceAttackCostPay4086_Bad
SourceAttackCostPay4086_Guard5:
.a16
.i16
 lda.l SourceAI4086_Callback+2
 beq SourceAttackCostPay4086_Guard6
 jmp SourceAttackCostPay4086_Bad
SourceAttackCostPay4086_Guard6:
.a16
.i16
 lda.l SourceAttackCostState4086_Ready
 cmp #$B609
 beq SourceAttackCostPay4086_Guard7
 jmp SourceAttackCostPay4086_Bad
SourceAttackCostPay4086_Guard7:
.a16
.i16
 lda.l SourceAI4086_Slot
 jsl SourceAttackCostState4086_PreflightBirth
 bcc SourceAttackCostPay4086_Guard8
 jmp SourceAttackCostPay4086_Bad
SourceAttackCostPay4086_Guard8:
.a16
.i16
 lda.l SourceAI4086_Slot
 asl a
 asl a
 tax
 lda.l SOURCE_ENTITY_ATTACK_COST,x
 ora.l SOURCE_ENTITY_ATTACK_COST+2,x
 bne SourceAttackCostPay4086_Guard9
 jmp SourceAttackCostPay4086_Done
SourceAttackCostPay4086_Guard9:
.a16
.i16
 lda.l SourceAI4086_View
 tax
 lda.l $410010,x
 cmp #BOR_VT_INTEGER
 beq SourceAttackCostPay4086_Guard10
 jmp SourceAttackCostPay4086_Bad
SourceAttackCostPay4086_Guard10:
.a16
.i16
 lda.l $410012,x
 ora.l $410016,x
 beq SourceAttackCostPay4086_Guard11
 jmp SourceAttackCostPay4086_Bad
SourceAttackCostPay4086_Guard11:
.a16
.i16
 lda.l $410014,x
 sta.l SourceEntityEnergy4086_Role
 lda.l $410020,x
 cmp #BOR_VT_INTEGER
 beq SourceAttackCostPay4086_Guard12
 jmp SourceAttackCostPay4086_Bad
SourceAttackCostPay4086_Guard12:
.a16
.i16
 lda.l $410022,x
 beq SourceAttackCostPay4086_Guard13
 jmp SourceAttackCostPay4086_Bad
SourceAttackCostPay4086_Guard13:
.a16
.i16
 lda.l SourceAI4086_Side
 tax
 lda.l $416804,x
 jsl SourceAnimationEnergy4086_Query
 bcc SourceAttackCostPay4086_Guard14
 jmp SourceAttackCostPay4086_Bad
SourceAttackCostPay4086_Guard14:
.a16
.i16
 lda.l SourceCheckEnergy4086_Cost
 sta.l SourceAttackCostPay4086_Cost
 lda.l SourceCheckEnergy4086_Cost+2
 sta.l SourceAttackCostPay4086_Cost+2
 lda #1 ; exact source CHECK_MP enum
 sta.l SourceEntityEnergy4086_Which
 lda #0
 sta.l SourceEntityEnergy4086_Which+2
 jsl SourceEntityEnergy4086_Execute
 bcc SourceAttackCostPay4086_Guard15
 jmp SourceAttackCostPay4086_Bad
SourceAttackCostPay4086_Guard15:
.a16
.i16
 lda.l SourceEntityEnergy4086_Result
 ora.l SourceEntityEnergy4086_Result+2
 beq SourceAttackCostPay4086_Health
 ; Dynamic core MP, independent of whether cached role was present.
 lda.l SourceAI4086_Slot
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
 lda.l $40C04C,x
 sec
 sbc.l SourceAttackCostPay4086_Cost
 sta.l $40C04C,x
 lda.l $40C04E,x
 sbc.l SourceAttackCostPay4086_Cost+2
 sta.l $40C04E,x
 bra SourceAttackCostPay4086_Clear
SourceAttackCostPay4086_Health:
.a16
.i16
 lda.l SourceAI4086_View
 tax
 lda.l $410024,x
 sec
 sbc.l SourceAttackCostPay4086_Cost
 sta.l $410024,x
 lda.l $410026,x
 sbc.l SourceAttackCostPay4086_Cost+2
 sta.l $410026,x
SourceAttackCostPay4086_Clear:
.a16
.i16
 lda.l SourceAI4086_Slot
 asl a
 asl a
 tax
 lda #0
 sta.l SOURCE_ENTITY_ATTACK_COST,x
 sta.l SOURCE_ENTITY_ATTACK_COST+2,x
SourceAttackCostPay4086_Done:
.a16
.i16
 lda #2
 sta.l SourceAttackCostPay4086_Status
 ply
 plx
 plp
 clc
 rtl
SourceAttackCostPay4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceAttackCostPay4086_Status
 ply
 plx
 plp
 sec
 rtl
