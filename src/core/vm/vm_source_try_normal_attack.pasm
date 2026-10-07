; common_try_normalattack(NULL): execute the real unbounded target query.
; No target returns literal false before recheck_nextattack/random/mutations.
; Present-target combo/range/timer/mutation body remains explicitly unbound.
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
 bne SourceTryNormalAttack4086_Bad
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
