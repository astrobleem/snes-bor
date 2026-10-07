; Execute the ordered normal_attack owner with real selector bodies.
; Unsupported target/mutation branches propagate faults, never fake responses.
SourceNormalAttackRun4086_Ready = $43BDD0
SourceNormalAttackRun4086_Status = $43BDD2 ; 0 idle,1 busy,2 done,3 fault
SourceNormalAttackRun4086_End = $43BDD4
SourceNormalAttackRun4086_Execute:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceNormalAttackRun4086_Ready
 cmp #$B5F5
 bne SourceNormalAttackRun4086_LongGuard1
 jmp SourceNormalAttackRun4086_Lease
SourceNormalAttackRun4086_LongGuard1:
.a16
.i16
 jmp SourceNormalAttackRun4086_Bad
SourceNormalAttackRun4086_Lease:
.a16
.i16
 lda.l SourceNormalAttackRun4086_Status
 bne SourceNormalAttackRun4086_LongGuard2
 jmp SourceNormalAttackRun4086_Idle
SourceNormalAttackRun4086_LongGuard2:
.a16
.i16
 cmp #2
 bne SourceNormalAttackRun4086_LongGuard3
 jmp SourceNormalAttackRun4086_Idle
SourceNormalAttackRun4086_LongGuard3:
.a16
.i16
 jmp SourceNormalAttackRun4086_Bad
SourceNormalAttackRun4086_Idle:
.a16
.i16
 lda #1
 sta.l SourceNormalAttackRun4086_Status
 jsl SourceNormalAttack4086_Begin
 bcs SourceNormalAttackRun4086_LongGuard4
 jmp SourceNormalAttackRun4086_Loop
SourceNormalAttackRun4086_LongGuard4:
.a16
.i16
 jmp SourceNormalAttackRun4086_Bad
SourceNormalAttackRun4086_Loop:
.a16
.i16
 lda.l SourceNormalAttack4086_State
 cmp #7
 bne SourceNormalAttackRun4086_LongGuard5
 jmp SourceNormalAttackRun4086_Done
SourceNormalAttackRun4086_LongGuard5:
.a16
.i16
 cmp #1
 bne SourceNormalAttackRun4086_LongGuard6
 jmp SourceNormalAttackRun4086_Grab
SourceNormalAttackRun4086_LongGuard6:
.a16
.i16
 cmp #2
 bne SourceNormalAttackRun4086_LongGuard7
 jmp SourceNormalAttackRun4086_Entry
SourceNormalAttackRun4086_LongGuard7:
.a16
.i16
 cmp #3
 bne SourceNormalAttackRun4086_LongGuard8
 jmp SourceNormalAttackRun4086_Block
SourceNormalAttackRun4086_LongGuard8:
.a16
.i16
 cmp #4
 bne SourceNormalAttackRun4086_LongGuard9
 jmp SourceNormalAttackRun4086_Entry
SourceNormalAttackRun4086_LongGuard9:
.a16
.i16
 cmp #5
 bne SourceNormalAttackRun4086_LongGuard10
 jmp SourceNormalAttackRun4086_Normal
SourceNormalAttackRun4086_LongGuard10:
.a16
.i16
 cmp #6
 bne SourceNormalAttackRun4086_LongGuard11
 jmp SourceNormalAttackRun4086_Entry
SourceNormalAttackRun4086_LongGuard11:
.a16
.i16
 jmp SourceNormalAttackRun4086_Bad
SourceNormalAttackRun4086_Grab:
.a16
.i16
 lda.l SourceTryGrab4086_Status
 jsr SourceNormalAttackRun4086_Reusable
 bcc SourceNormalAttackRun4086_LongGuard12
 jmp SourceNormalAttackRun4086_Bad
SourceNormalAttackRun4086_LongGuard12:
.a16
.i16
 sta.l SourceTryGrab4086_Status
 jsl SourceTryGrab4086_Execute
 jmp SourceNormalAttackRun4086_Resume
SourceNormalAttackRun4086_Entry:
.a16
.i16
 lda.l SourceAttackEntry4086_Status
 jsr SourceNormalAttackRun4086_Reusable
 bcc SourceNormalAttackRun4086_LongGuard13
 jmp SourceNormalAttackRun4086_Bad
SourceNormalAttackRun4086_LongGuard13:
.a16
.i16
 sta.l SourceAttackEntry4086_Status
 jsl SourceAttackEntry4086_Execute
 jmp SourceNormalAttackRun4086_Resume
SourceNormalAttackRun4086_Block:
.a16
.i16
 lda.l SourceTryBlock4086_Status
 jsr SourceNormalAttackRun4086_Reusable
 bcc SourceNormalAttackRun4086_LongGuard14
 jmp SourceNormalAttackRun4086_Bad
SourceNormalAttackRun4086_LongGuard14:
.a16
.i16
 sta.l SourceTryBlock4086_Status
 jsl SourceTryBlock4086_Execute
 jmp SourceNormalAttackRun4086_Resume
SourceNormalAttackRun4086_Normal:
.a16
.i16
 lda.l SourceTryNormalAttack4086_Status
 jsr SourceNormalAttackRun4086_Reusable
 bcc SourceNormalAttackRun4086_LongGuard15
 jmp SourceNormalAttackRun4086_Bad
SourceNormalAttackRun4086_LongGuard15:
.a16
.i16
 sta.l SourceTryNormalAttack4086_Status
 jsl SourceTryNormalAttack4086_Execute
SourceNormalAttackRun4086_Resume:
.a16
.i16
 bcc SourceNormalAttackRun4086_LongGuard16
 jmp SourceNormalAttackRun4086_Bad
SourceNormalAttackRun4086_LongGuard16:
.a16
.i16
 lda.l SourceNormalAttack4086_State
 cmp #5
 beq SourceNormalAttackRun4086_LongGuard17
 jmp SourceNormalAttackRun4086_CompletedSelector
SourceNormalAttackRun4086_LongGuard17:
.a16
.i16
 lda.l SourceTryNormalAttack4086_Status
 cmp #1
 bne SourceNormalAttackRun4086_LongGuard18
 jmp SourceNormalAttackRun4086_Pending
SourceNormalAttackRun4086_LongGuard18:
.a16
.i16
SourceNormalAttackRun4086_CompletedSelector:
.a16
.i16
 lda.l SourceNormalAttack4086_State
 jsl SourceNormalAttack4086_Continue
 bcc SourceNormalAttackRun4086_LongGuard19
 jmp SourceNormalAttackRun4086_Bad
SourceNormalAttackRun4086_LongGuard19:
.a16
.i16
 jmp SourceNormalAttackRun4086_Loop
SourceNormalAttackRun4086_Pending:
.a16
.i16
 lda #1
 ply
 plx
 plp
 clc
 rtl
SourceNormalAttackRun4086_Continue:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceNormalAttackRun4086_Ready
 cmp #$B5F5
 beq SourceNormalAttackRun4086_LongGuard20
 jmp SourceNormalAttackRun4086_Bad
SourceNormalAttackRun4086_LongGuard20:
.a16
.i16
 lda.l SourceNormalAttackRun4086_Status
 cmp #1
 beq SourceNormalAttackRun4086_LongGuard21
 jmp SourceNormalAttackRun4086_Bad
SourceNormalAttackRun4086_LongGuard21:
.a16
.i16
 jsl SourceTryNormalAttack4086_Continue
 jmp SourceNormalAttackRun4086_Resume
SourceNormalAttackRun4086_Done:
.a16
.i16
 lda #2
 sta.l SourceNormalAttackRun4086_Status
 lda #0
 ply
 plx
 plp
 clc
 rtl
SourceNormalAttackRun4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceNormalAttackRun4086_Status
 lda #0
 ply
 plx
 plp
 sec
 rtl
SourceNormalAttackRun4086_Reusable:
.a16
.i16
 cmp #0
 bne SourceNormalAttackRun4086_LongGuard22
 jmp SourceNormalAttackRun4086_ReusableGood
SourceNormalAttackRun4086_LongGuard22:
.a16
.i16
 cmp #2
 beq SourceNormalAttackRun4086_LongGuard23
 jmp SourceNormalAttackRun4086_ReusableBad
SourceNormalAttackRun4086_LongGuard23:
.a16
.i16
SourceNormalAttackRun4086_ReusableGood:
.a16
.i16
 lda #0
 clc
 rts
SourceNormalAttackRun4086_ReusableBad:
.a16
.i16
 sec
 rts
