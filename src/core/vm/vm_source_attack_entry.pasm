; Literal common_try_upper(NULL)/common_try_runattack(NULL) early false gates.
; Any branch needing target/range/mutation services is explicitly unbound.
SourceAttackEntry4086_Ready = $43BD7A
SourceAttackEntry4086_Status = $43BD7C ; 0 idle,2 false complete,3 fault
SourceAttackEntry4086_End = $43BD7E
SourceAttackEntry4086_Execute:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceAttackEntry4086_Ready
 cmp #$B5ED
 beq SourceAttackEntry4086_Lease
 jmp SourceAttackEntry4086_Bad
SourceAttackEntry4086_Lease:
.a16
.i16
 lda.l SourceAttackEntry4086_Status
 beq SourceAttackEntry4086_Idle
 jmp SourceAttackEntry4086_Bad
SourceAttackEntry4086_Idle:
.a16
.i16
 jsl SourceNormalAttack4086_CheckOwner
 bcc SourceAttackEntry4086_Owner
 jmp SourceAttackEntry4086_Bad
SourceAttackEntry4086_Owner:
.a16
.i16
 lda.l SourceNormalAttack4086_State
 cmp #2
 beq SourceAttackEntry4086_Upper
 cmp #4
 beq SourceAttackEntry4086_Run
 jmp SourceAttackEntry4086_Bad
SourceAttackEntry4086_Run:
.a16
.i16
 lda.l SourceAI4086_Slot
 asl a
 asl a
 asl a
 pha
 asl a
 clc
 adc 1,s
 tax
 pla
 lda.l SOURCE_ENTITY_AI_STATE+4,x
 ora.l SOURCE_ENTITY_AI_STATE+6,x
 beq SourceAttackEntry4086_False
 lda #38
 bra SourceAttackEntry4086_Animation
SourceAttackEntry4086_Upper:
.a16
.i16
 lda #12
SourceAttackEntry4086_Animation:
.a16
.i16
 cmp.l SourceModelAnimationCopy4086_Maximum
 bcc SourceAttackEntry4086_Bounded
 jmp SourceAttackEntry4086_Bad
SourceAttackEntry4086_Bounded:
.a16
.i16
 asl a
 clc
 adc.l SourceAI4086_ModelOffset
 tax
 lda.l SOURCE_MODEL_ANIMATION_CACHE,x
 beq SourceAttackEntry4086_False
 jmp SourceAttackEntry4086_Bad
SourceAttackEntry4086_False:
.a16
.i16
 lda #0
 sta.l SourceNormalAttack4086_Response
 sta.l SourceNormalAttack4086_Response+2
 lda #2
 sta.l SourceAttackEntry4086_Status
 ply
 plx
 plp
 clc
 rtl
SourceAttackEntry4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceAttackEntry4086_Status
 ply
 plx
 plp
 sec
 rtl
